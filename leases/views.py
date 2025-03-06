# leases/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Lease
from .forms import LeaseCreateForm, LeaseEditForm, LeaseTerminateForm
from properties.models import Unit, Property
from tenant_portal.models import TenantInvitation
from utils.utils import send_lease_invitation_email
from core.decorators import tenant_required

@login_required
@tenant_required
def company_lease_list(request, company_slug):
    company = request.tenant  # Iegūstam tenant no request objekta
    
    # Pārbaudam vai lietotājam ir tiesības skatīt uzņēmuma līgumus
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt uzņēmuma īres līgumus.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam filtrus no request
    status = request.GET.get('status')
    property_id = request.GET.get('property')
    unit_id = request.GET.get('unit')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset - izmantojam company no request.tenant
    leases = Lease.objects.filter(company=company).select_related(
        'unit', 
        'unit__property', 
        'tenant'
    ).order_by('-created_at')  # Izmantojam created_at no TenantModel
    
    # Pielietojam filtrus
    if status:
        leases = leases.filter(status=status)
    if property_id:
        leases = leases.filter(unit__property_id=property_id)
    if unit_id:
        leases = leases.filter(unit_id=unit_id)
    if date_from:
        leases = leases.filter(start_date__gte=date_from)
    if date_to:
        leases = leases.filter(end_date__lte=date_to)
    
    # Lapošana
    paginator = Paginator(leases, 20)  # 20 līgumi lapā
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Iegūstam unikālos īpašumus priekš filtra - izmantojam filtru pēc company
    properties = Property.objects.filter(company=company)
    
    return render(request, 'leases/lease_list.html', {
        'company': company,
        'page_obj': page_obj,
        'properties': properties,
        'active_page': 'tenant_leases',  # Mainām uz 'leases' tā vietā, lai lietotu 'properties'
        'filters': {
            'status': status,
            'property_id': property_id,
            'unit_id': unit_id,
            'date_from': date_from,
            'date_to': date_to
        }
    })

@login_required
@tenant_required
def lease_create(request, company_slug, property_pk, unit_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=unit_pk, property=property, company=company)
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību izveidot īres līgumus.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
    
    # Pārbaudam vai telpa ir pieejama
    if unit.status != 'available':
        messages.error(request, "Šī telpa nav pieejama īrei.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
    
    if request.method == 'POST':
        form = LeaseCreateForm(request.POST)
        if form.is_valid():
            lease = form.save(commit=False)
            lease.unit = unit
            lease.company = company  # Piesaistām tenant
            lease.status = 'draft'
            lease.save()
            
            # Izveidojam ielūgumu - piesaistām tenant
            invitation = TenantInvitation(
                lease=lease,
                email=form.cleaned_data['tenant_email'],
                status='pending',
                expires_at=timezone.now() + timedelta(days=7),
                company=company  # Piesaistām tenant
            )
            invitation.save()
            
            # Nosūtam e-pastu
            send_lease_invitation_email(invitation)
            
            # Atjaunojam unit statusu
            unit.status = 'reserved'
            unit.save()
            
            messages.success(request, "Īres līgums izveidots un uzaicinājums nosūtīts īrniekam.")
            return redirect('leases:lease_detail', company_slug=company_slug, pk=lease.id)
    else:
        form = LeaseCreateForm()
    
    return render(request, 'leases/lease_form.html', {
        'form': form,
        'company': company,
        'property': property,
        'unit': unit,
        'active_page': 'properties',
        'action': 'Create'
    })

@login_required
@tenant_required
def lease_detail(request, company_slug, pk):
    company = request.tenant
    lease = get_object_or_404(Lease.objects.select_related(
        'unit', 'unit__property', 'tenant'
    ), id=pk, company=company)
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or 
            request.user.company_memberships.filter(company=company, role__in=['ADMIN', 'MANAGER']).exists() or 
            lease.tenant == request.user):
        messages.error(request, "Jums nav tiesību skatīt šo īres līgumu.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam saistītus datus
    try:
        invitation = TenantInvitation.objects.get(lease=lease)
    except TenantInvitation.DoesNotExist:
        invitation = None
    
    return render(request, 'leases/lease_detail.html', {
        'lease': lease,
        'company': company,
        'invitation': invitation,
        'active_page': 'tenant_leases'
    })

@login_required
@tenant_required
def lease_edit(request, company_slug, pk):
    company = request.tenant
    lease = get_object_or_404(Lease.objects.select_related(
        'unit', 'unit__property', 'tenant'
    ), id=pk, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību rediģēt šo īres līgumu.")
        return redirect('leases:lease_detail', company_slug=company_slug, pk=pk)
    
    if request.method == 'POST':
        form = LeaseEditForm(request.POST, instance=lease)
        if form.is_valid():
            form.save()
            messages.success(request, "Īres līgums veiksmīgi atjaunināts!")
            return redirect('leases:lease_detail', company_slug=company_slug, pk=pk)
    else:
        form = LeaseEditForm(instance=lease)
    
    return render(request, 'leases/lease_form.html', {
        'form': form,
        'lease': lease,
        'company': company,
        'active_page': 'tenant_leases',
        'action': 'Edit'
    })

@login_required
@tenant_required
def lease_terminate(request, company_slug, pk):
    company = request.tenant
    lease = get_object_or_404(Lease, id=pk, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību izbeigt šo īres līgumu.")
        return redirect('leases:lease_detail', company_slug=company_slug, pk=pk)
    
    if request.method == 'POST':
        form = LeaseTerminateForm(request.POST)
        if form.is_valid():
            termination_date = form.cleaned_data['termination_date']
            unit_status = form.cleaned_data['unit_status']
            notes = form.cleaned_data.get('notes', '')
            
            # Atjaunojam līguma statusu
            lease.status = 'terminated'
            lease.end_date = termination_date
            lease.save()
            
            # Atjaunojam unit statusu
            lease.unit.status = unit_status
            lease.unit.save()
            
            messages.success(request, "Īres līgums veiksmīgi izbeigts.")
            return redirect('leases:lease_detail', company_slug=company_slug, pk=pk)
    else:
        form = LeaseTerminateForm()
    
    return render(request, 'leases/lease_terminate.html', {
        'form': form,
        'lease': lease,
        'company': company,
        'active_page': 'tenant_leases',
    })

@login_required
@tenant_required
def lease_delete(request, company_slug, pk):
    company = request.tenant
    lease = get_object_or_404(Lease.objects.select_related('unit'), id=pk, company=company)
    
    # Pārbaudam vai lietotājs ir kompānijas īpašnieks
    if lease.company.owner != request.user:
        messages.error(request, "Tikai uzņēmuma īpašnieks var dzēst īres līgumus.")
        return redirect('leases:lease_detail', company_slug=company_slug, pk=pk)
    
    if request.method == 'POST':
        # Atjaunojam unit statusu uz available
        unit = lease.unit
        unit.status = 'available'
        unit.save()
        
        # Dzēšam lease
        lease.delete()
        
        messages.success(request, "Īres līgums veiksmīgi dzēsts.")
        return redirect('leases:lease_list', company_slug=company_slug)
    
    return render(request, 'leases/lease_delete.html', {
        'lease': lease,
        'company': company,
        'active_page': 'tenant_leases'
    })


def lease_invitation(request, token):
    invitation = get_object_or_404(
        TenantInvitation.objects.select_related('lease', 'lease__unit'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'This invitation has expired.')
        return redirect('users:home')
    
    if request.user.is_authenticated:
        messages.warning(request, 'Please logout first to register as a tenant.')
        return redirect('users:logout') ## so vajadzes partaisit uz gadijumiem kad ir jau lietotajs
    
    return render(request, 'partials/invitation_landing.html', {
        'invitation': invitation
    })

