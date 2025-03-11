# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserLoginForm, ManagerRegistrationForm, TenantRegistrationForm, UserProfileForm
from .models import User
from companies.models import Company, CompanyMember, CompanyInvitation
from django.utils import timezone


def home(request):
    return render(request, 'landing.html', {'PAGE': 'home'})

def login_user(request):
    if request.user.is_authenticated:
        return redirect('users:redirect_after_login')
    
    if request.method == 'POST':
        form = UserLoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Sveiki, {user.first_name}!")
                return redirect('users:redirect_after_login')
        else:
            messages.error(request, "Lietotājvārds vai parole nav pareiza.")
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})

@login_required
def redirect_after_login(request):
    """Novirza lietotāju pēc pieteikšanās atkarībā no lomas"""
    print(request.user.role)
    if request.user.role == 'company_owner' or request.user.role == 'manager':
        return redirect('companies_public:company_list')
    elif request.user.role == 'tenant':
        # Pagaidām vienkārši novirzām uz profilu
        return redirect('users:profile')
    else:
        return redirect('users:profile')

def register_manager(request):
    if request.user.is_authenticated:
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = ManagerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Konts veiksmīgi izveidots! Sveiki, {user.first_name}!")
            return redirect('companies_public:company_create')  # Pēc reģistrācijas uzreiz var izveidot uzņēmumu
    else:
        form = ManagerRegistrationForm()
    
    return render(request, 'users/register.html', {
        'form': form,
        'user_type': 'manager'
    })

def register_tenant(request):
    if request.user.is_authenticated:
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = TenantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Konts veiksmīgi izveidots! Sveiki, {user.first_name}!")
            return redirect('users:profile')
    else:
        form = TenantRegistrationForm()
    
    return render(request, 'users/register.html', {
        'form': form,
        'user_type': 'tenant'
    })

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, 'Jūs esat veiksmīgi atteicies.')
    return redirect('users:login')

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profils atjaunināts!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Atrodam kompānijas, kur lietotājs ir īpašnieks vai biedrs
    owned_companies = Company.objects.filter(owner=request.user)
    member_companies = Company.objects.filter(members__user=request.user).exclude(owner=request.user)
    
    return render(request, 'users/profile.html', {
        'form': form,
        'owned_companies': owned_companies,
        'member_companies': member_companies
    })


#  Company member invitaiton and registration

def company_invitation(request, token):
    """Skats uzaicinājuma aplūkošanai un reģistrācijai"""
    invitation = get_object_or_404(
        CompanyInvitation.objects.select_related('company'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Šis uzaicinājums ir beidzies.')
        return redirect('users:home')
    
    if request.user.is_authenticated:
        # Ja lietotājs jau pieteicies, virzām uz pieņemšanas skatu
        return redirect('users:accept_company_invitation', token=token)
    
    return render(request, 'users/company_invitation.html', {
        'invitation': invitation
    })

def company_register(request, token):
    """Skats jaunam lietotājam reģistrēties un pieņemt uzaicinājumu"""
    invitation = get_object_or_404(
        CompanyInvitation.objects.select_related('company'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Šis uzaicinājums ir beidzies.')
        return redirect('users:home')
    
    if request.user.is_authenticated:
        messages.warning(request, 'Lūdzu, izrakstieties, lai reģistrētos kā jauns lietotājs.')
        return redirect('users:logout')
    
    if request.method == 'POST':
        form = ManagerRegistrationForm(request.POST, initial={'email': invitation.email})
        if form.is_valid():
            # Saglabājam lietotāju
            user = form.save(commit=False)
            # Papildus saglabājam e-pastu, jo disabled lauks netiek apstrādāts
            user.email = invitation.email
            user.save()
            
            # Pievienojam lietotāju uzņēmumam
            member = CompanyMember(
                company=invitation.company,
                user=user,
                role=invitation.role
            )
            member.save()
            
            # Atjauninām uzaicinājuma statusu
            invitation.status = 'accepted'
            invitation.save()
            
            messages.success(request, 'Reģistrācija veiksmīga! Tagad varat pieteikties sistēmā.')
            return redirect('users:login')
    else:
        form = ManagerRegistrationForm(initial={'email': invitation.email})
    
    return render(request, 'users/company_invitation_register.html', {
        'form': form,
        'invitation': invitation
    })

@login_required
def accept_company_invitation(request, token):
    """Skats uzaicinājuma pieņemšanai, kad lietotājs jau ir reģistrēts"""
    invitation = get_object_or_404(
        CompanyInvitation.objects.select_related('company'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Šis uzaicinājums ir beidzies.')
        return redirect('users:home')
    
    # Pārbaudam, vai e-pasts sakrīt ar lietotāja e-pastu
    if request.user.email != invitation.email:
        messages.error(request, 'Uzaicinājums ir nosūtīts uz citu e-pasta adresi.')
        return redirect('users:home')
    
    # Pārbaudam, vai lietotājs jau ir uzņēmuma dalībnieks
    is_member = CompanyMember.objects.filter(
        company=invitation.company,
        user=request.user
    ).exists()
    
    if is_member:
        messages.error(request, 'Jūs jau esat šī uzņēmuma dalībnieks.')
        return redirect('companies_tenant:company_detail', company_slug=invitation.company.slug)
    
    # Pārbaudam, vai lietotājs ir īrnieks (tenant)
    if request.user.role == 'tenant':
        messages.error(request, 'Jūs esat reģistrēts kā īrnieks. Īrnieki nevar kļūt par uzņēmuma dalībniekiem.')
        return redirect('users:home')
    
    # Pievienojam lietotāju uzņēmumam
    member = CompanyMember(
        company=invitation.company,
        user=request.user,
        role=invitation.role
    )
    member.save()
    
    # Atjauninām uzaicinājuma statusu
    invitation.status = 'accepted'
    invitation.save()
    
    messages.success(request, f"Jūs esat veiksmīgi pievienojies uzņēmumam {invitation.company.name}.")
    return redirect('companies_tenant:company_detail', company_slug=invitation.company.slug)