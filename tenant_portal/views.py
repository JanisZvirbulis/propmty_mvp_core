from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import TenantInvitation
from .forms import TenantRegistrationForm, IssueReportForm
from inspections.models import Issue, IssueImage
from properties.forms import MeterReadingForm
from properties.models import UnitMeter
from invoices.models import Invoice


def lease_invitation(request, token):
    invitation = get_object_or_404(
        TenantInvitation.objects.select_related('lease', 'lease__unit', 'company'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Šis uzaicinājums ir beidzies.')
        return redirect('users:home')
    
    # Pārbaudam vai līgums vēl ir pieejams pieņemšanai
    lease = invitation.lease
    if lease.status != 'draft' or lease.tenant is not None:
        messages.error(request, 'Šis īres līgums vairs nav pieejams.')
        return redirect('users:home')
    
    if request.user.is_authenticated:
        # Ja lietotājs jau pieteicies, piedāvājam divas iespējas:
        # 1. Izrakstīties un reģistrēties kā īrnieks
        # 2. Izmantot pašreizējo kontu (ja e-pasts sakrīt)
        if request.user.email == invitation.email:
            # Ja e-pasts sakrīt, varam uzreiz piesaistīt
            if request.method == 'POST' and 'accept_with_current' in request.POST:
                # Aktivizējam līgumu
                lease.tenant = request.user
                lease.status = 'active'
                lease.save()
                
                # Atjaunojam ielūguma statusu
                invitation.status = 'accepted'
                invitation.save()
                
                # Atjaunojam unit statusu
                lease.unit.status = 'rented'
                lease.unit.save()
                
                messages.success(request, 'Īres līgums veiksmīgi akceptēts!')
                return redirect('tenant_portal:dashboard')
            
            return render(request, 'tenant_portal/invitation_existing_user.html', {
                'invitation': invitation,
                'lease': lease
            })
        else:
            messages.warning(request, 'Lūdzu, izrakstieties, lai reģistrētos kā īrnieks ar šo uzaicinājumu.')
            return redirect('users:logout')
    
    return render(request, 'partials/invitation_landing.html', {
        'invitation': invitation,
        'lease': lease
    })

def tenant_register(request, token):
    invitation = get_object_or_404(
        TenantInvitation.objects.select_related('lease', 'lease__unit', 'company'),
        invitation_token=token,
        status='pending'
    )
    
    # Pārbaudam vai ielūgums nav beidzies
    if invitation.expires_at < timezone.now():
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, 'Šis uzaicinājums ir beidzies.')
        return redirect('users:home')
    
    # Pārbaudam vai līgums vēl ir pieejams pieņemšanai
    lease = invitation.lease
    if lease.status != 'draft' or lease.tenant is not None:
        messages.error(request, 'Šis īres līgums vairs nav pieejams.')
        return redirect('users:home')
    
    if request.user.is_authenticated:
        messages.warning(request, 'Lūdzu, izrakstieties, lai reģistrētos kā īrnieks.')
        return redirect('users:logout')
    
    if request.method == 'POST':
        form = TenantRegistrationForm(request.POST, initial={'email': invitation.email})
        if form.is_valid():
            # Saglabājam lietotāju
            user = form.save(commit=False)
            # Papildus saglabājam e-pastu, jo disabled lauks netiek apstrādāts
            user.email = invitation.email
            user.save()
            
            # Aktivizējam līgumu
            lease.tenant = user
            lease.status = 'active'
            lease.save()
            
            # Atjaunojam ielūguma statusu
            invitation.status = 'accepted'
            invitation.save()
            
            # Atjaunojam unit statusu
            lease.unit.status = 'rented'
            lease.unit.save()
            
            # Automātiski pieteicam jauno lietotāju
            # login(request, user)
            # Vai arī novirzām uz login lapu
            messages.success(request, 'Reģistrācija veiksmīga! Tagad varat pieteikties sistēmā.')
            return redirect('users:login')
    else:
        form = TenantRegistrationForm(initial={'email': invitation.email})
    
    return render(request, 'tenant_portal/tenant_register.html', {
        'form': form,
        'invitation': invitation,
        'lease': lease
    })

@login_required
def tenant_dashboard(request):
    # Tikai īrniekam var būt piekļuve šai lapai
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka panelim.')
        return redirect('users:home')
    
    # Atrodam visus aktīvos līgumus priekš šī īrnieka
    leases = request.user.leases.filter(status='active')
    
    return render(request, 'tenant_portal/dashboard.html', {
        'leases': leases,
        'active_page': 'tenant_dashboard',
    })


@login_required
def tenant_meter_readings(request):
    """Parāda visus īrnieka īrēto telpu skaitītājus"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka skaitītāju panelim.')
        return redirect('users:home')
    
    # Atrodam visus aktīvos līgumus ar to telpām un skaitītājiem
    active_leases = request.user.leases.filter(status='active').select_related(
        'unit', 'unit__property', 'company'
    )
    
    # Izveidojam struktūru, kur katram līgumam ir tā telpas skaitītāji
    leases_with_meters = []
    for lease in active_leases:
        active_meters = UnitMeter.objects.filter(
            unit=lease.unit,
            status='active'
        ).prefetch_related('readings')
        
        for meter in active_meters:
            # Pievienojam pēdējo rādījumu
            last_reading = meter.readings.order_by('-reading_date').first()
            meter.last_reading = last_reading
            
            # Pārbaudam vai rādījumi tekošajam mēnesim jau ir iesniegti
            # Mēnesis tiek definēts kā tekošā mēneša 1. datums līdz nākošā mēneša 1. datums
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            if today.month == 12:
                next_month = 1
                next_month_year = today.year + 1
            else:
                next_month = today.month + 1
                next_month_year = today.year
            
            next_month_start = today.replace(day=1, month=next_month, year=next_month_year)
            
            # Pārbaudam vai tekošajā mēnesī jau ir iesniegts rādījums
            current_month_reading = meter.readings.filter(
                reading_date__gte=current_month_start,
                reading_date__lt=next_month_start
            ).first()
            
            meter.current_month_reading = current_month_reading
        
        leases_with_meters.append({
            'lease': lease,
            'meters': active_meters
        })
    
    return render(request, 'tenant_portal/meter_readings.html', {
        'leases_with_meters': leases_with_meters,
        'today': timezone.now().date(),
        'active_page': 'tenant_meter_readings',
    })

@login_required
def submit_reading(request, lease_id, meter_id):
    """Ļauj īrniekam iesniegt skaitītāja rādījumu"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka skaitītāju panelim.')
        return redirect('users:home')
    
    # Pārbaudam vai līgums pieder lietotājam
    lease = get_object_or_404(request.user.leases.filter(status='active'), id=lease_id)
    meter = get_object_or_404(UnitMeter, id=meter_id, unit=lease.unit, status='active')
    
    # Iegūstam pēdējo rādījumu
    last_reading = meter.readings.order_by('-reading_date').first()
    
    if request.method == 'POST':
        form = MeterReadingForm(request.POST, meter=meter)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.meter = meter
            reading.submitted_by = request.user
            reading.company = lease.company
            reading.save()
            
            messages.success(request, f"{meter.get_meter_type_display()} skaitītāja rādījums veiksmīgi iesniegts.")
            return redirect('tenant_portal:meter_readings')
    else:
        # Uzstādam šodienas datumu kā sākotnējo
        form = MeterReadingForm(meter=meter)
    
    return render(request, 'tenant_portal/submit_reading.html', {
        'form': form,
        'lease': lease,
        'meter': meter,
        'last_reading': last_reading,
        'active_page': 'tenant_meter_readings',
    })

@login_required
def unit_meter_readings_history(request, lease_id, meter_id):
    """Parāda skaitītāja rādījumu vēsturi"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka skaitītāju panelim.')
        return redirect('users:home')
    
    # Pārbaudam vai līgums pieder lietotājam
    lease = get_object_or_404(request.user.leases.filter(status='active'), id=lease_id)
    meter = get_object_or_404(UnitMeter, id=meter_id, unit=lease.unit)
    
    # Iegūstam visus rādījumus, kārtotus pēc datuma (jaunākie pirmie)
    readings = meter.readings.order_by('-reading_date')
    
    # Aprēķinam patēriņu
    readings_list = list(readings)
    for i in range(len(readings_list)):
        if i < len(readings_list) - 1:
            # Atņemam no tekošā rādījuma iepriekšējo rādījumu
            # Rādījumi ir sakārtoti - jaunākais pirmais
            consumption = readings_list[i].reading - readings_list[i + 1].reading
            readings_list[i].consumption = max(0, round(consumption, 2))
        else:
            readings_list[i].consumption = None
    
    return render(request, 'tenant_portal/readings_history.html', {
        'lease': lease,
        'meter': meter,
        'readings': readings_list,
        'active_page': 'tenant_meter_readings',
    })


@login_required
def tenant_issues(request):
    """Parāda īrnieka ziņotās problēmas"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka problēmu panelim.')
        return redirect('users:home')
    
    # Atrodam aktīvos īres līgumus
    leases = request.user.leases.filter(status='active').select_related(
        'unit', 'unit__property', 'company'
    )
    
    # Atrodam visas īrnieka problēmas
    issues = Issue.objects.filter(
        reported_by=request.user
    ).select_related(
        'unit', 'unit__property'
    ).order_by('-created_at')
    
    return render(request, 'tenant_portal/tenant_issues.html', {
        'leases': leases,
        'issues': issues,
        'active_page': 'tenant_issues',
    })

@login_required
def report_issue(request, lease_id):
    """Ļauj īrniekam ziņot par problēmu"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka problēmu panelim.')
        return redirect('users:home')
    
    # Pārbaudam vai īres līgums pieder lietotājam
    lease = get_object_or_404(request.user.leases.filter(status='active'), id=lease_id)
    unit = lease.unit
    company = lease.company
    
    if request.method == 'POST':
        form = IssueReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Saglabājam problēmu
            issue = form.save(commit=False)
            issue.unit = unit
            issue.company = company
            issue.reported_by = request.user
            issue.status = 'reported'
            issue.save()
            
            # Saglabājam attēlus, ja tādi ir
            for image in request.FILES.getlist('images'):
                issue_image = IssueImage.objects.create(
                    image=image,
                    issue=issue,
                    company=company,
                    uploaded_by=request.user
                )
                issue.images.add(issue_image)
            
            messages.success(request, 'Problēma veiksmīgi pieteikta.')
            return redirect('tenant_portal:tenant_issues')
    else:
        form = IssueReportForm()
    
    return render(request, 'tenant_portal/report_issue.html', {
        'form': form,
        'lease': lease,
        'unit': unit,
        'company': company,
        'active_page': 'tenant_issues',
    })

@login_required
def tenant_issue_detail(request, issue_id):
    """Parāda detalizētu informāciju par problēmu"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka problēmu panelim.')
        return redirect('users:home')
    
    # Pārbaudam vai problēma pieder lietotājam
    issue = get_object_or_404(Issue.objects.select_related(
        'unit', 'unit__property', 'resolved_by'
    ), id=issue_id, reported_by=request.user)
    
    return render(request, 'tenant_portal/issue_detail.html', {
        'issue': issue,
        'active_page': 'tenant_issues',
    })

@login_required
def tenant_invoices(request):
    """Parāda īrnieka rēķinus"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka rēķinu panelim.')
        return redirect('users:home')
    
    # Atrodam visus īrnieka rēķinus
    invoices = Invoice.objects.filter(
        lease__tenant=request.user
    ).select_related(
        'lease', 'lease__unit', 'lease__unit__property', 'company'
    ).order_by('-issue_date')
    
    # Filtri
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    # Sadalīsim rēķinus pa kategorijām
    unpaid_invoices = invoices.filter(status__in=['sent', 'overdue'])
    paid_invoices = invoices.filter(status='paid')
    other_invoices = invoices.filter(status__in=['draft', 'cancelled'])
    
    return render(request, 'tenant_portal/tenant_invoices.html', {
        'unpaid_invoices': unpaid_invoices,
        'paid_invoices': paid_invoices,
        'other_invoices': other_invoices,
        'active_page': 'tenant_invoices',
        'filters': {
            'status': status
        }
    })

@login_required
def tenant_invoice_detail(request, invoice_id):
    """Parāda detalizētu īrnieka rēķina informāciju"""
    # Pārbaudam vai lietotājs ir īrnieks
    if request.user.role != 'tenant':
        messages.error(request, 'Jums nav piekļuves īrnieka rēķinu panelim.')
        return redirect('users:home')
    
    # Atrodam rēķinu
    invoice = get_object_or_404(Invoice.objects.select_related(
        'lease', 'lease__unit', 'lease__unit__property', 'company'
    ), id=invoice_id, lease__tenant=request.user)
    
    # Iegūstam rēķina pozīcijas
    items = invoice.items.all()
    
    return render(request, 'tenant_portal/tenant_invoice_detail.html', {
        'invoice': invoice,
        'items': items,
        'active_page': 'tenant_invoices'
    })