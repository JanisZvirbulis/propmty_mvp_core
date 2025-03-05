from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Property, Unit
from .forms import PropertyForm, UnitForm
from core.decorators import tenant_required
from datetime import timedelta
from django.utils import timezone
from tenant_portal.models import TenantInvitation
from utils.utils import send_lease_invitation_email
from leases.forms import LeaseCreateForm

@login_required
@tenant_required
def property_list(request, company_slug):
    properties = Property.objects.filter(company=request.tenant)
    
    return render(request, 'properties/property_list.html', {
        'properties': properties,
        'company': request.tenant,
        'active_page': 'properties'  # Aktīvā sidebar sadaļa
    })

# @login_required
# @tenant_required
# def property_create(request, company_slug):
#     # Pārbaudam vai lietotājam ir tiesības pievienot īpašumu
#     if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
#             company=request.tenant, role__in=['ADMIN', 'MANAGER']).exists()):
#         messages.error(request, "Jums nav tiesību pievienot īpašumus šim uzņēmumam.")
#         return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
#     if request.method == 'POST':
#         form = PropertyForm(request.POST)
#         if form.is_valid():
#             property = form.save(commit=False)
#             property.company = request.tenant  # Automātiski piesaistam tenant
#             property.save()
            
#             messages.success(request, f"Īpašums '{property.address}' veiksmīgi pievienots!")
#             return redirect('properties:property_list', company_slug=company_slug)
#     else:
#         form = PropertyForm()
    
#     return render(request, 'properties/property_form.html', {
#         'form': form,
#         'company': request.tenant,
#         'active_page': 'properties',
#         'is_creating': True
#     })

@login_required
@tenant_required
def property_create(request, company_slug):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības pievienot īpašumu
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību pievienot īpašumus šim uzņēmumam.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam current un max īpašumu skaitu
    current_properties_count = Property.objects.filter(company=company).count()
    
    # Pārbaudam subscription ierobežojumus
    max_properties = None
    progress_percentage = 0
    
    # Ja ir implementēta subscription sistēma, veicam pārbaudes
    if hasattr(company, 'get_subscription') and callable(getattr(company, 'get_subscription')):
        subscription = company.get_subscription()
        if subscription and hasattr(subscription, 'plan') and hasattr(subscription.plan, 'max_properties'):
            max_properties = subscription.plan.max_properties
            
            # Pārbaudam vai var pievienot jaunu īpašumu
            if current_properties_count >= max_properties:
                current_plan_name = subscription.plan.name
                messages.error(
                    request, 
                    f"Jūsu abonements '{current_plan_name}' ļauj pievienot tikai {max_properties} īpašumus. "
                    f"Lai pievienotu vairāk īpašumus, lūdzu, atjauniniet savu abonementu."
                )
                return redirect('properties:property_list', company_slug=company_slug)
            
            # Aprēķinām progresu
            if max_properties > 0:
                progress_percentage = (current_properties_count / max_properties) * 100
    
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            property = form.save(commit=False)
            property.company = company
            property.save()
            
            messages.success(request, f"Īpašums '{property.address}' veiksmīgi pievienots!")
            return redirect('properties:property_list', company_slug=company_slug)
    else:
        form = PropertyForm()
    
    return render(request, 'properties/property_form.html', {
        'form': form,
        'company': company,
        'active_page': 'properties',
        'is_creating': True,
        'current_properties_count': current_properties_count,
        'max_properties': max_properties,
        'progress_percentage': progress_percentage
    })

@login_required
@tenant_required
def property_detail(request, company_slug, pk):
    # Atrodam īpašumu, kas pieder current tenant
    property = get_object_or_404(Property, id=pk, company=request.tenant)
    # Iegūstam statistiku par unitiem
    total_units = property.units.count()
    available_units = property.units.filter(status='available').count()
    rented_units = property.units.filter(status='rented').count()
    maintenance_units = property.units.filter(status='maintenance').count()
    reserved_units = property.units.filter(status='reserved').count()
    
    # Aprēķinām kopējo platību
    total_area = sum(unit.area for unit in property.units.all())
    # Aprēķinām vidējo platību, ja ir vismaz viena telpa
    average_area = 0
    if total_units > 0:
        average_area = total_area / total_units

    
    # Iegūstam visus unitus
    units = property.units.all().order_by('unit_number')
    
    context = {
        'property': property,
        'company': request.tenant,
        'active_page': 'properties',
        'units': units,
        'total_units': total_units,
        'available_units': available_units,
        'rented_units': rented_units,
        'maintenance_units': maintenance_units,
        'reserved_units': reserved_units,
        'total_area': total_area,
        'average_area': average_area,
    }
    
    return render(request, 'properties/property_detail.html', context)


@login_required
@tenant_required
def property_edit(request, company_slug, pk):
    # Atrodam īpašumu, kas pieder current tenant
    property = get_object_or_404(Property, id=pk, company=request.tenant)
    # Pārbaudam vai lietotājam ir tiesības rediģēt īpašumu
    if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
            company=request.tenant, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību rediģēt šo īpašumu.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
    
        # Pārbaudam subscription ierobežojumus

   
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property)
        if form.is_valid():
            form.save()
            messages.success(request, f"Īpašums '{property.address}' veiksmīgi atjaunināts!")
            return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
    else:
        form = PropertyForm(instance=property)
    
    return render(request, 'properties/property_form.html', {
        'form': form,
        'company': request.tenant,
        'property': property,
        'active_page': 'properties',
        'is_creating': False,  # Norādam, ka šis nav jauna īpašuma izveides skats
    })

@login_required
@tenant_required
def property_delete(request, company_slug, pk):
    property = get_object_or_404(Property, id=pk, company=request.tenant)
    
    # Pārbaudam vai lietotājam ir tiesības dzēst īpašumu
    if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
            company=request.tenant, role='ADMIN').exists()):
        messages.error(request, "Jums nav tiesību dzēst šo īpašumu.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
    
    if request.method == 'POST':
        # Pārbaudam vai ir apstiprināts dzēšanas action
        if request.POST.get('confirm_delete') == 'yes':
            property_address = property.address
            property.delete()
            messages.success(request, f"Īpašums '{property_address}' veiksmīgi dzēsts!")
            return redirect('properties:property_list', company_slug=company_slug)
        else:
            return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
            
    return render(request, 'properties/property_delete.html', {
        'property': property,
        'company': request.tenant,
        'active_page': 'properties'
    })


@login_required
@tenant_required
def unit_create(request, company_slug, pk):
    # Atrodam īpašumu
    property = get_object_or_404(Property, id=pk, company=request.tenant)
    company = request.tenant
    # Pārbaudam vai lietotājam ir tiesības pievienot telpu
    if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
            company=request.tenant, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību pievienot telpas šim īpašumam.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
    
    total_units = property.units.count()
    max_units = None
    progress_percentage = 0
    
    # Ja ir implementēta subscription sistēma, veicam pārbaudes
    if hasattr(company, 'get_subscription') and callable(getattr(company, 'get_subscription')):
        subscription = company.get_subscription()
        if subscription and hasattr(subscription, 'plan') and hasattr(subscription.plan, 'max_properties'):
            max_units = subscription.plan.max_units
            
            # Pārbaudam vai var pievienot jaunu īpašumu
            if total_units >= max_units:
                current_plan_name = subscription.plan.name
                messages.error(
                    request, 
                    f"Jūsu abonements '{current_plan_name}' ļauj pievienot tikai {max_units} telpas šim īpašumam. "
                    f"Lai pievienotu vairāk telpas, lūdzu, atjauniniet savu abonementu."
                )
                return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
            
            # Aprēķinām progresu
            if max_units > 0:
                progress_percentage = (total_units / max_units) * 100
    
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.property = property
            unit.company = request.tenant  # Piesaistām tenant
            unit.save()
            
            messages.success(request, f"Telpa {unit.unit_number} veiksmīgi pievienota!")
            return redirect('properties:property_detail', company_slug=company_slug, pk=pk)
    else:
        form = UnitForm()
    
    return render(request, 'properties/unit_form.html', {
        'form': form,
        'company': request.tenant,
        'property': property,
        'active_page': 'properties',
        'is_creating': True,
        'progress_percentage': progress_percentage
    })

@login_required
@tenant_required
def unit_detail(request, company_slug, property_pk, pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    
    # Atrodam aktīvos īres līgumus
    active_leases = unit.leases.filter(status='active')
    draft_leases = unit.leases.filter(status='draft')
    
    # Pārbaudam vai ir aktīvi uzaicinājumi
    invitation = None
    if draft_leases.exists():
        try:
            invitation = TenantInvitation.objects.get(lease=draft_leases.first())
        except TenantInvitation.DoesNotExist:
            pass
    
    # Formu loģika īrnieka uzaicināšanai
    if request.method == 'POST' and 'invite_tenant' in request.POST:
        if unit.status != 'available':
            messages.error(request, "Šī telpa nav pieejama īrei.")
            return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)
        
        form = LeaseCreateForm(request.POST)
        if form.is_valid():
            # Izveidojam jaunu līgumu
            lease = form.save(commit=False)
            lease.unit = unit
            lease.company = company
            lease.status = 'draft'
            lease.save()
            
            # Izveidojam uzaicinājumu
            tenant_email = form.cleaned_data['tenant_email']
            invitation = TenantInvitation(
                lease=lease,
                email=tenant_email,
                company=company,
                status='pending',
                expires_at=timezone.now() + timedelta(days=7)
            )
            invitation.save()
            
            # Atjaunojam unit statusu
            unit.status = 'reserved'
            unit.save()
            
            # Nosūtam e-pastu (funkcija jau ir definēta)
            send_lease_invitation_email(invitation)
            
            messages.success(request, f"Uzaicinājums nosūtīts uz e-pastu {tenant_email}.")
            return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)
    else:
        form = LeaseCreateForm()
    
    return render(request, 'properties/unit_detail.html', {
        'unit': unit,
        'property': property,
        'company': company,
        'active_leases': active_leases,
        'draft_leases': draft_leases,
        'invitation': invitation,
        'form': form,
        'active_page': 'properties'
    })

@login_required
@tenant_required
def unit_edit(request, company_slug, property_pk, unit_pk):
    # Atrodam īpašumu un telpu
    property = get_object_or_404(Property, id=property_pk, company=request.tenant)
    unit = get_object_or_404(Unit, id=unit_pk, property=property, company=request.tenant)
    
    # Pārbaudam vai lietotājam ir tiesības rediģēt telpu
    if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
            company=request.tenant, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību rediģēt telpas šim īpašumam.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
    
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, f"Telpa {unit.unit_number} veiksmīgi atjaunināta!")
            return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
    else:
        form = UnitForm(instance=unit)
    
    return render(request, 'properties/unit_form.html', {
        'form': form,
        'company': request.tenant,
        'property': property,
        'unit': unit,
        'active_page': 'properties',
        'is_creating': False
    })


@login_required
@tenant_required
def unit_delete(request, company_slug, property_pk, unit_pk):
    property = get_object_or_404(Property, id=property_pk, company=request.tenant)
    unit = get_object_or_404(Unit, id=unit_pk, property=property, company=request.tenant)
    
    # Pārbaudam vai lietotājam ir tiesības dzēst telpu
    if not (request.user == request.tenant.owner or request.user.company_memberships.filter(
            company=request.tenant, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību dzēst šo telpu.")
        return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
    
    if request.method == 'POST':
        # Pārbaudam vai ir apstiprināts dzēšanas action
        if request.POST.get('confirm_delete') == 'yes':
            unit_number = unit.unit_number
            unit.delete()
            messages.success(request, f"Telpa {unit_number} veiksmīgi dzēsta!")
            return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
        else:
            return redirect('properties:property_detail', company_slug=company_slug, pk=property_pk)
            
    return render(request, 'properties/unit_delete.html', {
        'unit': unit,
        'property': property,
        'company': request.tenant,
        'active_page': 'properties'
    })


# properties/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Property, Unit, UnitMeter, MeterReading
from .forms import UnitMeterForm, MeterReadingForm
from core.decorators import tenant_required

@login_required
@tenant_required
def unit_meter_add(request, company_slug, property_pk, pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību pievienot skaitītājus.")
        return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)

    if request.method == 'POST':
        form = UnitMeterForm(unit=unit, data=request.POST)
        if form.is_valid():
            meter = form.save(commit=False)
            meter.unit = unit
            meter.company = company  # Piesaistām tenant
            
            # Ja ir esošs skaitītājs, atzīmējam to kā expired ar šodienas datumu
            existing_meter = unit.meters.filter(
                meter_type=meter.meter_type, 
                status='active'
            ).first()
            if existing_meter:
                existing_meter.status = 'expired'
                existing_meter.expire_date = timezone.now().date()
                existing_meter.save()
            
            meter.save()
            messages.success(request, 'Skaitītājs veiksmīgi pievienots.')
            return redirect('properties:unit_meters', company_slug=company_slug, property_pk=property_pk, pk=pk)
    else:
        form = UnitMeterForm(unit=unit)

    return render(request, 'properties/unit_meter_form.html', {
        'form': form,
        'unit': unit,
        'property': property,
        'company': company,
        'action': 'Add',
        'active_page': 'properties'
    })

@login_required
@tenant_required
def unit_meters(request, company_slug, property_pk, pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt skaitītājus.")
        return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)

    # Iegūstam visus aktīvos un vecākos skaitītājus
    active_meters = unit.meters.filter(status='active')
    inactive_meters = unit.meters.exclude(status='active')
    
    return render(request, 'properties/unit_meters.html', {
        'unit': unit,
        'property': property,
        'company': company,
        'active_meters': active_meters,
        'inactive_meters': inactive_meters,
        'active_page': 'properties'
    })

@login_required
@tenant_required
def unit_meter_detail(request, company_slug, property_pk, pk, meter_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    meter = get_object_or_404(UnitMeter, id=meter_pk, unit=unit, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt skaitītāja detaļas.")
        return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)

    # Filtrēšana
    readings = meter.readings.select_related('submitted_by', 'verified_by')
    
    # Datumu filtri
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        readings = readings.filter(reading_date__gte=date_from)
    if date_to:
        readings = readings.filter(reading_date__lte=date_to)

    # Verifikācijas statusa filtrs
    verification = request.GET.get('verification')
    if verification == 'verified':
        readings = readings.filter(is_verified=True)
    elif verification == 'unverified':
        readings = readings.filter(is_verified=False)

    # Kārtošana
    sort = request.GET.get('sort', '-reading_date')
    readings = readings.order_by(sort)

    # Aprēķinam patēriņu
    readings_list = list(readings)
    for i in range(len(readings_list)):
        if i < len(readings_list) - 1:
            consumption = readings_list[i].reading - readings_list[i + 1].reading
            readings_list[i].consumption = round(consumption, 2)
        else:
            readings_list[i].consumption = None

    return render(request, 'properties/unit_meter_detail.html', {
        'unit': unit,
        'property': property,
        'company': company,
        'meter': meter,
        'readings': readings_list,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'verification': verification,
            'sort': sort
        },
        'active_page': 'properties'
    })

@login_required
@tenant_required
def unit_meter_edit(request, company_slug, property_pk, pk, meter_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    meter = get_object_or_404(UnitMeter, id=meter_pk, unit=unit, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību rediģēt skaitītāju.")
        return redirect('properties:unit_meter_detail', 
                       company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)

    if request.method == 'POST':
        form = UnitMeterForm(request.POST, instance=meter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skaitītājs veiksmīgi atjaunināts.')
            return redirect('properties:unit_meter_detail', 
                          company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)
    else:
        form = UnitMeterForm(instance=meter)

    return render(request, 'properties/unit_meter_form.html', {
        'form': form,
        'unit': unit,
        'property': property,
        'company': company,
        'meter': meter,
        'action': 'Edit',
        'active_page': 'properties'
    })

@login_required
@tenant_required
def unit_meter_delete(request, company_slug, property_pk, pk, meter_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    meter = get_object_or_404(UnitMeter, id=meter_pk, unit=unit, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību dzēst skaitītāju.")
        return redirect('properties:unit_meter_detail', 
                       company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)

    if request.method == 'POST':
        # Skaitītājs tiks dzēsts kopā ar visiem tā rādījumiem (CASCADE)
        meter.delete()
        messages.success(request, 'Skaitītājs un visi tā rādījumi ir veiksmīgi dzēsti.')
        return redirect('properties:unit_meters', 
                       company_slug=company_slug, property_pk=property_pk, pk=pk)

    return render(request, 'properties/delete_confirm.html', {
        'object': meter,
        'object_name': f"{meter.get_meter_type_display()} skaitītājs ({meter.meter_number})",
        'warning_message': 'Šī darbība dzēsīs skaitītāju un visus tā rādījumus. Šo darbību nevar atsaukt.',
        'back_url': reverse('properties:unit_meter_detail', 
                          kwargs={'company_slug': company_slug, 'property_pk': property_pk, 
                                 'pk': pk, 'meter_pk': meter_pk}),
        'company': company,
        'active_page': 'properties'
    })

@login_required
@tenant_required
def meter_reading_add(request, company_slug, property_pk, pk, meter_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    meter = get_object_or_404(UnitMeter, id=meter_pk, unit=unit, company=company)
    
    # Pārbaudam tiesības - šeit var atļaut arī īrniekam pievienot rādījumus
    is_admin_or_manager = (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists())
    is_tenant = False
    
    # Pārbaudam vai lietotājs ir telpas īrnieks
    active_leases = unit.leases.filter(status='active', tenant=request.user)
    if active_leases.exists():
        is_tenant = True
    
    if not (is_admin_or_manager or is_tenant):
        messages.error(request, "Jums nav tiesību pievienot rādījumus.")
        return redirect('properties:unit_detail', company_slug=company_slug, property_pk=property_pk, pk=pk)

    if request.method == 'POST':
        form = MeterReadingForm(meter=meter, data=request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.meter = meter
            reading.submitted_by = request.user
            reading.company = company  # Piesaistām tenant
            
            # Ja ievada property manager vai owner, automātiski verificējam
            if is_admin_or_manager:
                reading.is_verified = True
                reading.verified_by = request.user
                reading.verification_date = timezone.now()
            
            reading.save()
            
            messages.success(request, 'Rādījums veiksmīgi pievienots.')
            
            # Atkarībā no lietotāja lomas, novirzām uz dažādām lapām
            if is_tenant:
                return redirect('tenant_portal:dashboard')
            else:
                return redirect('properties:unit_meter_detail', 
                              company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)
    else:
        form = MeterReadingForm(meter=meter)

    return render(request, 'properties/meter_reading_form.html', {
        'form': form,
        'unit': unit,
        'property': property,
        'company': company,
        'meter': meter,
        'action': 'Add',
        'active_page': 'properties' if not is_tenant else 'tenant_dashboard'
    })

@login_required
@tenant_required
def meter_reading_delete(request, company_slug, property_pk, pk, meter_pk, reading_pk):
    company = request.tenant
    property = get_object_or_404(Property, id=property_pk, company=company)
    unit = get_object_or_404(Unit, id=pk, property=property, company=company)
    meter = get_object_or_404(UnitMeter, id=meter_pk, unit=unit, company=company)
    reading = get_object_or_404(MeterReading, id=reading_pk, meter=meter, company=company)
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību dzēst rādījumus.")
        return redirect('properties:unit_meter_detail', 
                       company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)

    if request.method == 'POST':
        reading.delete()
        messages.success(request, 'Rādījums veiksmīgi dzēsts.')
        return redirect('properties:unit_meter_detail', 
                       company_slug=company_slug, property_pk=property_pk, pk=pk, meter_pk=meter_pk)

    return render(request, 'properties/delete_confirm.html', {
        'object': reading,
        'object_name': f"Rādījums {reading.reading} no {reading.reading_date}",
        'warning_message': 'Vai tiešām vēlaties dzēst šo rādījumu? Šo darbību nevar atsaukt.',
        'back_url': reverse('properties:unit_meter_detail', 
                          kwargs={'company_slug': company_slug, 'property_pk': property_pk, 
                                 'pk': pk, 'meter_pk': meter_pk}),
        'company': company,
        'active_page': 'properties'
    })

@login_required
@tenant_required
def company_meter_readings(request, company_slug):
    company = request.tenant
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, 'Jums nav tiesību skatīt skaitītāju rādījumus.')
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Base queryset ar visiem saistītajiem datiem
    readings = MeterReading.objects.filter(
        company=company
    ).select_related(
        'meter',
        'meter__unit',
        'meter__unit__property',
        'submitted_by',
        'verified_by'
    ).order_by('-reading_date')
    
    # Filtrēšana
    property_id = request.GET.get('property')
    verification = request.GET.get('verification')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if property_id:
        readings = readings.filter(meter__unit__property_id=property_id)
        # Get units for selected property
        units = Unit.objects.filter(property_id=property_id, company=company)
        unit_id = request.GET.get('unit')
        if unit_id:
            readings = readings.filter(meter__unit_id=unit_id)
    
    if verification:
        if verification == 'verified':
            readings = readings.filter(is_verified=True)
        elif verification == 'unverified':
            readings = readings.filter(is_verified=False)
    
    if date_from:
        readings = readings.filter(reading_date__gte=date_from)
    if date_to:
        readings = readings.filter(reading_date__lte=date_to)
    
    # Get properties for filter
    properties = Property.objects.filter(company=company)
    
    # Pagination
    paginator = Paginator(readings, 20)
    page = request.GET.get('page')
    readings = paginator.get_page(page)
    
    return render(request, 'properties/company_meter_readings.html', {
        'readings': readings,
        'company': company,
        'properties': properties,
        'units': units if 'units' in locals() else None,
        'filters': {
            'property_id': property_id,
            'unit_id': unit_id if 'unit_id' in locals() else None,
            'verification': verification,
            'date_from': date_from,
            'date_to': date_to
        },
        'active_page': 'meters'  # Izmantojam 'meters' lai aktivizētu skaitītāju sadaļu sidebarā
    })

@login_required
@tenant_required
def verify_meter_reading(request, company_slug, pk):
    company = request.tenant
    
    # Pārbaudam tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, 'Jums nav tiesību verificēt rādījumus.')
        return redirect('properties:company_meter_readings', company_slug=company_slug)
    
    reading = get_object_or_404(MeterReading, 
        id=pk,
        company=company
    )
    
    if request.method == 'POST':
        reading.is_verified = True
        reading.verified_by = request.user
        reading.verification_date = timezone.now()
        reading.save()
        
        messages.success(request, 'Skaitītāja rādījums veiksmīgi verificēts.')
    
    return redirect('properties:company_meter_readings', company_slug=company_slug)