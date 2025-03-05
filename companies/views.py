from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Company, CompanyMember, CompanyInvitation
from .forms import CompanyForm, CompanyInvitationForm, CompanyMemberRoleForm
from core.decorators import tenant_required
from utils.utils import send_company_invitation_email
from properties.models import Property
from users.models import User



@login_required
def company_list(request):
    # Atrodam uzņēmumus, kur lietotājs ir īpašnieks
    owned_companies = Company.objects.filter(owner=request.user)
    
    # Atrodam uzņēmumus, kur lietotājs ir dalībnieks (bet ne īpašnieks)
    member_companies = Company.objects.filter(
        members__user=request.user
    ).exclude(owner=request.user)
    page = 'company_list'
    
    return render(request, 'companies/company_list.html', {
        'owned_companies': owned_companies,
        'member_companies': member_companies,
        'PAGE': page,
    })

@login_required
def company_create(request):
    # Pārbaudam vai lietotājam ir tiesības izveidot uzņēmumu
    if request.user.role != 'company_owner':
        messages.error(request, "Tikai uzņēmuma īpašnieki var izveidot jaunus uzņēmumus.")
        return redirect('companies_public:company_list')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            
            # Pievienojam automātiski bezmaksas abonementu (ja ir subscription modelis)
            # Šo daļu var pievienot, kad subscriptions modelis ir gatavs
            
            messages.success(request, f"Uzņēmums '{company.name}' veiksmīgi izveidots!")
            return redirect('companies_tenant:company_detail', company_slug=company.slug)
    else:
        form = CompanyForm()
    
    return render(request, 'companies/company_form.html', {
        'form': form,
        'is_creating': True
    })


@login_required
@tenant_required
def company_detail(request, company_slug):
    company = request.tenant  # Jau ir pārbaudīts, ka lietotājs ir dalībnieks

     # Iegūstam lietotāja dalībnieka ierakstu šim uzņēmumam
    user_membership = None
    if request.user != company.owner:
        user_membership = CompanyMember.objects.filter(
            company=company,
            user=request.user
        ).first()
    
    # Pārbaudam tiesības
    is_admin = user_membership and user_membership.role == 'ADMIN'
    is_manager = user_membership and user_membership.role == 'MANAGER'
    can_manage_members = request.user == company.owner or is_admin
    can_edit_data = request.user == company.owner or is_admin or is_manager
    
    # Atrodam uzņēmuma dalībniekus
    members = CompanyMember.objects.filter(company=company)
    
    # Atrodam uzņēmuma īpašumus (kad būs izveidoti)
    properties = Property.objects.filter(company=company)
    
    return render(request, 'companies/company_dashboard.html', {
        'company': company,
        'members': members,
        'properties': properties,
        'can_manage_members': can_manage_members,
        'can_edit_data': can_edit_data,
        'active_page': 'dashboard'  # Norādam, kura navigācijas sadaļa ir aktīva
    })

@login_required
@tenant_required
def company_members(request, company_slug):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.is_company_owner or request.is_company_admin):
        messages.error(request, "Jums nav tiesību pārvaldīt uzņēmuma dalībniekus.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam dalībniekus un aktīvos uzaicinājumus
    members = CompanyMember.objects.filter(company=company).select_related('user')
    pending_invitations = CompanyInvitation.objects.filter(
        company=company, 
        status='pending'
    ).exclude(expires_at__lt=timezone.now())
    
    return render(request, 'companies/company_members.html', {
        'company': company,
        'members': members,
        'pending_invitations': pending_invitations,
        'active_page': 'members'
    })

@login_required
@tenant_required
def change_member_role(request, company_slug, member_id):
    """Skats dalībnieka lomas mainīšanai"""
    company = request.tenant
    
    # Tikai uzņēmuma īpašnieks var mainīt lomas
    if request.user != company.owner:
        messages.error(request, "Tikai uzņēmuma īpašnieks var mainīt dalībnieku lomas.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    member = get_object_or_404(CompanyMember, id=member_id, company=company)
    
    # Neļaujam mainīt īpašnieka lomu
    if member.user == company.owner:
        messages.error(request, "Uzņēmuma īpašnieka lomu nevar mainīt.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    if request.method == 'POST':
        form = CompanyMemberRoleForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dalībnieka {member.user.get_full_name()} loma veiksmīgi atjaunināta.")
            return redirect('companies_tenant:company_members', company_slug=company_slug)
    else:
        form = CompanyMemberRoleForm(instance=member)
    
    return render(request, 'companies/change_member_role.html', {
        'company': company,
        'member': member,
        'form': form,
        'active_page': 'members'
    })

@login_required
@tenant_required
def invite_member(request, company_slug):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role='ADMIN').exists()):
        messages.error(request, "Jums nav tiesību pievienot dalībniekus.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Pārbaudam abonementu ierobežojumus
    if not company.can_add_member():
        messages.error(request, "Jūsu abonements neļauj pievienot vairāk dalībniekus.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    if request.method == 'POST':
        form = CompanyInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            role = form.cleaned_data['role']
            
            # Pārbaudam, vai lietotājs ar šādu e-pastu jau eksistē
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                # Pārbaudam, vai lietotājs jau ir uzņēmuma dalībnieks
                is_member = CompanyMember.objects.filter(
                    company=company,
                    user=existing_user
                ).exists()
                
                if is_member:
                    messages.error(request, f"Lietotājs ar e-pastu {email} jau ir uzņēmuma dalībnieks.")
                    return redirect('companies_tenant:company_members', company_slug=company_slug)
                
                # Pārbaudam, vai lietotājs ir uzņēmuma īpašnieks
                if existing_user == company.owner:
                    messages.error(request, f"Lietotājs ar e-pastu {email} ir uzņēmuma īpašnieks.")
                    return redirect('companies_tenant:company_members', company_slug=company_slug)
                
                # Pārbaudam, vai lietotājs ir īrnieks (tenant)
                if existing_user.role == 'tenant':
                    messages.error(request, f"Lietotājs ar e-pastu {email} ir reģistrēts kā īrnieks. Īrniekus nevar uzaicināt kā uzņēmuma dalībniekus.")
                    return redirect('companies_tenant:company_members', company_slug=company_slug)
            
            # Pārbaudam, vai nav aktīva uzaicinājuma uz šo e-pastu
            existing_invitation = CompanyInvitation.objects.filter(
                company=company,
                email=email,
                status='pending',
                expires_at__gt=timezone.now()
            ).first()
            
            if existing_invitation:
                messages.error(request, f"Uzaicinājums uz e-pastu {email} jau ir nosūtīts.")
                return redirect('companies_tenant:company_members', company_slug=company_slug)
            
            # Izveidojam jaunu uzaicinājumu
            invitation = CompanyInvitation(
                company=company,
                email=email,
                role=role,
                expires_at=timezone.now() + timedelta(days=7)  # Derīgs 7 dienas
            )
            invitation.save()
            
            # Nosūtam e-pastu
            send_company_invitation_email(invitation)
            
            messages.success(request, f"Uzaicinājums nosūtīts uz e-pastu {email}.")
            return redirect('companies_tenant:company_members', company_slug=company_slug)
    else:
        form = CompanyInvitationForm()
    
    return render(request, 'companies/invite_member.html', {
        'company': company,
        'form': form,
        'active_page': 'members'
    })


@login_required
@tenant_required
def remove_member(request, company_slug, member_id):
    """Skats dalībnieka noņemšanai no uzņēmuma"""
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role='ADMIN').exists()):
        messages.error(request, "Jums nav tiesību noņemt dalībniekus.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    member = get_object_or_404(CompanyMember, id=member_id, company=company)
    
    # Neļaujam noņemt uzņēmuma īpašnieku
    if member.user == company.owner:
        messages.error(request, "Uzņēmuma īpašnieku nevar noņemt.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    if request.method == 'POST':
        member.delete()
        messages.success(request, f"Dalībnieks {member.user.get_full_name()} ir noņemts no uzņēmuma.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    return render(request, 'companies/remove_member_confirm.html', {
        'company': company,
        'member': member,
        'active_page': 'members'
    })

@login_required
@tenant_required
def cancel_invitation(request, company_slug, invitation_id):
    """Skats uzaicinājuma atcelšanai"""
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role='ADMIN').exists()):
        messages.error(request, "Jums nav tiesību atcelt uzaicinājumus.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    invitation = get_object_or_404(CompanyInvitation, id=invitation_id, company=company)
    
    if request.method == 'POST':
        invitation.status = 'expired'
        invitation.save()
        messages.success(request, f"Uzaicinājums uz e-pastu {invitation.email} ir atcelts.")
        return redirect('companies_tenant:company_members', company_slug=company_slug)
    
    return render(request, 'companies/cancel_invitation_confirm.html', {
        'company': company,
        'invitation': invitation,
        'active_page': 'members'
    })