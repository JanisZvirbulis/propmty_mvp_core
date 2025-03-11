from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from core.decorators import tenant_required
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm
from leases.models import Lease
from inspections.models import Maintenance
from properties.models import UnitMeter, MeterReading
import datetime
from decimal import Decimal

@login_required
@tenant_required
def invoice_list(request, company_slug):
    """Rāda visu rēķinu sarakstu"""
    company = request.tenant
    
    # Pārbaudām vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt rēķinus.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Filtri
    status = request.GET.get('status')
    lease_id = request.GET.get('lease')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Bāzes vaicājums
    invoices = Invoice.objects.filter(company=company).select_related(
        'lease', 'lease__unit', 'lease__tenant', 'lease__unit__property'
    ).order_by('-issue_date')
    
    # Piemērojam filtrus
    if status:
        invoices = invoices.filter(status=status)
    
    if lease_id:
        invoices = invoices.filter(lease_id=lease_id)
    
    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)
    
    # Iegūstam visus aktīvos līgumus filtram
    active_leases = Lease.objects.filter(
        company=company,
        status='active'
    ).select_related('unit', 'tenant', 'unit__property')
    
    return render(request, 'invoices/invoice_list.html', {
        'invoices': invoices,
        'company': company,
        'active_leases': active_leases,
        'active_page': 'invoices',
        'filters': {
            'status': status,
            'lease_id': lease_id,
            'date_from': date_from,
            'date_to': date_to
        }
    })

@login_required
@tenant_required
def invoice_create(request, company_slug, lease_id):
    """Jauna rēķina izveide"""
    company = request.tenant
    
    # Pārbaudām vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību izveidot rēķinus.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    # Pārbaudām vai līgums ir aktīvs
    lease = get_object_or_404(Lease, id=lease_id, company=company, status='active')
    
    # Pārbaudām, vai ir jau izveidots rēķins šim mēnesim
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    
    # Ja šis ir decembris, nākamais mēnesis ir janvāris nākamajā gadā
    if today.month == 12:
        next_month = 1
        next_month_year = today.year + 1
    else:
        next_month = today.month + 1
        next_month_year = today.year
    
    next_month_start = datetime.date(next_month_year, next_month, 1)
    
    # Meklējam, vai jau ir šī mēneša rēķins
    existing_invoice = Invoice.objects.filter(
        lease=lease,
        status__in=['Sent', 'Paid', 'OverDue'],
        issue_date__gte=current_month_start,
        issue_date__lt=next_month_start
    ).first()
    
    if existing_invoice:
        messages.warning(
            request, 
            f"Šim mēnesim jau ir izveidots rēķins (Nr. {existing_invoice.number}). "
            f"Varat to rediģēt vai izveidot rēķinu citam periodam."
        )
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=existing_invoice.id)
    
    # Aprēķinam potenciālās rēķina pozīcijas
    items_to_include = []
    
    # 1. Īres maksa (vienmēr tiek iekļauta)
    items_to_include.append({
        'description': f"Īres maksa par {today.strftime('%Y.g. %B')}",
        'quantity': 1,
        'unit_price': lease.rent_amount
    })
    
    # 2. Komunālo pakalpojumu maksājumi - aprēķinām no skaitītāju rādījumiem
    active_meters = UnitMeter.objects.filter(
        unit=lease.unit,
        status='active'
    )
    
    for meter in active_meters:
        # Atrodam pēdējos divus rādījumus, lai aprēķinātu patēriņu
        readings = MeterReading.objects.filter(
            meter=meter
        ).order_by('-reading_date')[:2]
        
        if len(readings) >= 2:
            # Aprēķinam patēriņu (jaunākais rādījums - vecākais rādījums)
            consumption = readings[0].reading - readings[1].reading
            
            # Izmantojam tarifu no mērītāja datu bāzes, ar noklusējuma vērtībām, ja tarifs nav iestatīts
            tariff = meter.tariff
            
            # Ja tarifs nav iestatīts, izmantojam noklusējuma vērtības
            if tariff == 0:
                default_tariffs = {
                    'water_cold': Decimal('1.20'),
                    'water_hot': Decimal('4.50'),
                    'gas': Decimal('0.65'),
                    'electricity': Decimal('0.15'),
                    'heating': Decimal('60.00')
                }
                tariff = default_tariffs.get(meter.meter_type, Decimal('0.00'))
            
            if consumption > 0:
                amount = consumption * tariff
                
                meter_type_display = meter.get_meter_type_display()
                
                items_to_include.append({
                    'description': f"{meter_type_display} patēriņš: {consumption} vienības ({readings[1].reading_date.strftime('%d.%m.%Y')} - {readings[0].reading_date.strftime('%d.%m.%Y')})",
                    'quantity': consumption,
                    'unit_price': tariff
                })
    
    # 3. Remontdarbi, kas veikti šajā mēnesī un ir par maksu
    maintenance_works = Maintenance.objects.filter(
        issue__unit=lease.unit,
        status='completed',
        completed_date__gte=current_month_start,
        completed_date__lt=next_month_start,
        cost__gt=0
    )
    
    for work in maintenance_works:
        items_to_include.append({
            'description': f"Remontdarbi: {work.description} ({work.completed_date.strftime('%d.%m.%Y')})",
            'quantity': 1,
            'unit_price': work.cost
        })
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        
        # Apstrādājam rēķina izveidi
        if 'create_invoice' in request.POST:
            # Iegūstam atlasītās pozīcijas
            selected_items_indices = request.POST.getlist('selected_items', [])
            selected_items = []
            
            for idx in selected_items_indices:
                try:
                    item_index = int(idx)
                    if item_index < len(items_to_include):
                        selected_items.append(items_to_include[item_index])
                except ValueError:
                    continue
            
            if not selected_items:
                messages.error(request, "Lūdzu, atlasiet vismaz vienu pozīciju rēķinam.")
                return render(request, 'invoices/invoice_create.html', {
                    'form': form,
                    'company': company,
                    'lease': lease,
                    'items_to_include': items_to_include,
                    'active_page': 'invoices'
                })
                
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Vispirms izveidojam rēķinu, bet vēl nesaglabājam
                        invoice = form.save(commit=False)
                        invoice.company = company
                        invoice.lease = lease
                        
                        # Ģenerējam rēķina numuru
                        current_year = timezone.now().year
                        current_month = timezone.now().month
                        month_invoice_count = Invoice.objects.filter(
                            company=company,
                            issue_date__year=current_year,
                            issue_date__month=current_month
                        ).count()
                        
                        invoice.number = f"{current_year}-{current_month:02d}-{month_invoice_count+1:04d}"
                        
                        # Aprēķinam kopējo summu
                        total_amount = Decimal('0.00')
                        
                        # Pagaidām nesaglabājam rēķinu, lai izvairītos no not-null ierobežojuma problēmas
                        # Saglabāsim tikai pēc kopējās summas aprēķināšanas
                        
                        # Aprēķinam kopējo summu no atlasītajām pozīcijām
                        for item_data in selected_items:
                            quantity = Decimal(str(item_data['quantity']))
                            unit_price = Decimal(str(item_data['unit_price']))
                            amount = quantity * unit_price
                            total_amount += amount
                        
                        # Tagad iestatām kopējo summu un saglabājam rēķinu
                        invoice.total_amount = total_amount
                        invoice.save()
                        
                        # Pēc tam pievienojam visas pozīcijas
                        for item_data in selected_items:
                            quantity = Decimal(str(item_data['quantity']))
                            unit_price = Decimal(str(item_data['unit_price']))
                            amount = quantity * unit_price
                            
                            # Izveidojam un saglabājam pozīciju
                            item = InvoiceItem(
                                invoice=invoice,
                                company=company,
                                description=item_data['description'],
                                quantity=quantity,
                                unit_price=unit_price,
                                amount=amount
                            )
                            item.save()
                        
                        messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi izveidots.")
                        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=invoice.id)
                except Exception as e:   
                    print(f"Invoice creation error: {str(e)}")
                    # Cilvēkam saprotams kļūdas ziņojums
                    messages.error(request, "Kļūda izveidojot rēķinu. Lūdzu, pārbaudiet ievadītos datus un mēģiniet vēlreiz.")
                    
            else:
                messages.error(request, "Lūdzu, izlabojiet kļūdas formā.")
        else:
            messages.error(request, "Nederīgs pieprasījums.")
    else:
        # Noklusējuma vērtības jaunam rēķinam
        form = InvoiceForm(initial={
            'issue_date': today,
            'due_date': today + datetime.timedelta(days=14)
        })
    
    return render(request, 'invoices/invoice_create.html', {
        'form': form,
        'company': company,
        'lease': lease,
        'items_to_include': items_to_include,
        'active_page': 'invoices'
    })

@login_required
@tenant_required
def invoice_detail(request, company_slug, pk):
    """Rāda detalizētu rēķina informāciju"""
    company = request.tenant
    
    # Vispārējas atļaujas pārbaude
    is_company_admin = (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists())
    
    # Meklējam rēķinu
    invoice = get_object_or_404(Invoice.objects.select_related(
        'lease', 'lease__unit', 'lease__tenant', 'lease__unit__property'
    ), id=pk, company=company)
    
    # Papildu piekļuves pārbaude īrniekam
    is_tenant = (request.user.role == 'tenant' and request.user == invoice.lease.tenant)
    
    if not (is_company_admin or is_tenant):
        messages.error(request, "Jums nav tiesību aplūkot šo rēķinu.")
        if request.user.role == 'tenant':
            return redirect('tenant_portal:dashboard')
        else:
            return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam rēķina pozīcijas
    items = invoice.items.all()
    
    return render(request, 'invoices/invoice_detail.html', {
        'invoice': invoice,
        'items': items,
        'company': company,
        'is_company_admin': is_company_admin,
        'is_tenant': is_tenant,
        'active_page': 'invoices' if is_company_admin else 'tenant_dashboard'
    })

@login_required
@tenant_required
def invoice_edit(request, company_slug, pk):
    """Rēķina rediģēšana"""
    company = request.tenant
    
    # Pārbaudām vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību rediģēt rēķinus.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    invoice = get_object_or_404(Invoice, id=pk, company=company)
    
    # Pārbaudām vai rēķinu vēl var rediģēt
    if invoice.status != 'draft':
        messages.error(request, "Tikai melnraksta statusā esošu rēķinu var rediģēt.")
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)
    
    # Iegūstam visas esošās rēķina pozīcijas
    invoice_items = InvoiceItem.objects.filter(invoice=invoice).order_by('id')
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        
        if 'save_changes' in request.POST and form.is_valid():
            try:
                with transaction.atomic():
                    # Saglabājam rēķina pamatinformāciju
                    invoice = form.save()
                    
                    # Apstrādājam pozīciju izmaiņas
                    items_to_update = []
                    items_to_delete = []
                    new_items = []
                    
                    # Apstrādājam esošās pozīcijas - atjaunināšana vai dzēšana
                    for item in invoice_items:
                        item_id_str = str(item.id)
                        
                        # Ja pozīcija ir atzīmēta dzēšanai
                        if f"delete_{item_id_str}" in request.POST:
                            items_to_delete.append(item.id)
                        else:
                            # Citādi atjauninam datus, ja tie ir mainīti
                            description = request.POST.get(f"description_{item_id_str}", "")
                            quantity = request.POST.get(f"quantity_{item_id_str}", "0")
                            unit_price = request.POST.get(f"unit_price_{item_id_str}", "0")
                            
                            try:
                                quantity = Decimal(quantity)
                                unit_price = Decimal(unit_price)
                                amount = quantity * unit_price
                                
                                # Ja dati ir mainīti, atjauninam
                                if (description != item.description or 
                                    quantity != item.quantity or 
                                    unit_price != item.unit_price or 
                                    amount != item.amount):
                                    item.description = description
                                    item.quantity = quantity
                                    item.unit_price = unit_price
                                    item.amount = amount
                                    items_to_update.append(item)
                            except (ValueError, TypeError, Decimal.InvalidOperation):
                                messages.error(request, f"Nekorektas vērtības pozīcijai: {description}")
                    
                    # Apstrādājam jaunas pozīcijas
                    new_item_count = int(request.POST.get("new_item_count", "0"))
                    for i in range(new_item_count):
                        description = request.POST.get(f"new_description_{i}", "")
                        quantity_str = request.POST.get(f"new_quantity_{i}", "")
                        unit_price_str = request.POST.get(f"new_unit_price_{i}", "")
                        
                        # Pārbaudam vai ir ievadīti dati
                        if description and quantity_str and unit_price_str:
                            try:
                                quantity = Decimal(quantity_str)
                                unit_price = Decimal(unit_price_str)
                                amount = quantity * unit_price
                                
                                # Izveidojam jaunu pozīciju
                                new_items.append(InvoiceItem(
                                    invoice=invoice,
                                    company=company,
                                    description=description,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    amount=amount
                                ))
                            except (ValueError, TypeError, Decimal.InvalidOperation):
                                messages.error(request, f"Nekorektas vērtības jaunai pozīcijai: {description}")
                    
                    # Izdzēšam atzīmētās pozīcijas
                    if items_to_delete:
                        InvoiceItem.objects.filter(id__in=items_to_delete).delete()
                    
                    # Atjauninam pozīcijas
                    for item in items_to_update:
                        item.save()
                    
                    # Saglabājam jaunas pozīcijas
                    if new_items:
                        InvoiceItem.objects.bulk_create(new_items)
                    
                    # Pārrēķinam kopējo summu
                    total_amount = sum(item.amount for item in InvoiceItem.objects.filter(invoice=invoice))
                    invoice.total_amount = total_amount
                    invoice.save(update_fields=['total_amount'])
                    
                    messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi atjaunināts.")
                    return redirect('invoices:invoice_detail', company_slug=company_slug, pk=invoice.id)
            except Exception as e:
                messages.error(request, f"Kļūda saglabājot rēķinu: {str(e)}")
        else:
            messages.error(request, "Lūdzu, izlabojiet kļūdas formā.")
    else:
        form = InvoiceForm(instance=invoice)
    
    return render(request, 'invoices/invoice_edit.html', {
        'form': form,
        'invoice': invoice,
        'invoice_items': invoice_items,
        'company': company,
        'active_page': 'invoices'
    })

@login_required
@tenant_required
def invoice_send(request, company_slug, pk):
    """Nosūta rēķinu īrniekam uz e-pastu"""
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību nosūtīt rēķinus.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    invoice = get_object_or_404(Invoice.objects.select_related(
        'lease', 'lease__tenant', 'lease__unit', 'lease__unit__property'
    ), id=pk, company=company)
    
    # Pārbaudam vai rēķinu vēl var nosūtīt
    if invoice.status not in ['draft', 'sent', 'overdue']:
        messages.error(request, "Šo rēķinu vairs nevar nosūtīt (atcelts vai apmaksāts).")
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)
    
    # Pārbaudam vai ir īrnieks
    if not invoice.lease.tenant:
        messages.error(request, "Šim līgumam nav piesaistīts īrnieks.")
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)
    
    # Sagatvojam URL priekš e-pasta
    tenant = invoice.lease.tenant
    view_url = f"{settings.SITE_URL}/tenant/invoices/{invoice.id}/"
    
    try:
        # Izmantojam jauno funkciju no utils
        from utils.utils import send_invoice_email
        send_invoice_email(invoice, tenant, company, view_url)
        
        # Atjauninam rēķina statusu
        invoice.send_to_tenant()
        
        messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi nosūtīts uz {tenant.email}.")
    except Exception as e:
        messages.error(request, f"Kļūda sūtot e-pastu: {str(e)}")
    
    return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)

@login_required
@tenant_required
def invoice_mark_paid(request, company_slug, pk):
    """Atzīmē rēķinu kā apmaksātu"""
    company = request.tenant
    
    # Pārbaudām vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību mainīt rēķina statusu.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    invoice = get_object_or_404(Invoice, id=pk, company=company)
    
    # Pārbaudām vai rēķinu var atzīmēt kā apmaksātu
    if invoice.status not in ['sent', 'overdue']:
        messages.error(request, "Tikai nosūtītu vai kavētu rēķinu var atzīmēt kā apmaksātu.")
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)
    
    # Atzīmējam kā apmaksātu
    invoice.mark_as_paid()
    messages.success(request, f"Rēķins Nr. {invoice.number} atzīmēts kā apmaksāts.")
    
    return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)

@login_required
@tenant_required
def invoice_cancel(request, company_slug, pk):
    """Atceļ rēķinu"""
    company = request.tenant
    
    # Pārbaudām vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību atcelt rēķinus.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    invoice = get_object_or_404(Invoice, id=pk, company=company)
    
    # Pārbaudām vai rēķinu var atcelt
    if invoice.status == 'paid':
        messages.error(request, "Apmaksātu rēķinu nevar atcelt.")
        return redirect('invoices:invoice_detail', company_slug=company_slug, pk=pk)
    
    if request.method == 'POST' and 'confirm_cancel' in request.POST:
        # Atceļam rēķinu
        invoice.status = 'cancelled'
        invoice.save()
        messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi atcelts.")
        return redirect('invoices:invoice_list', company_slug=company_slug)
    
    return render(request, 'invoices/invoice_cancel.html', {
        'invoice': invoice,
        'company': company,
        'active_page': 'invoices'
    })

@login_required
@tenant_required
def invoice_print(request, company_slug, pk):
    """Rēķina izdruka/PDF skats"""
    company = request.tenant
    
    # Vispārējas atļaujas pārbaude
    is_company_admin = (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists())
    
    # Meklējam rēķinu
    invoice = get_object_or_404(Invoice.objects.select_related(
        'lease', 'lease__unit', 'lease__tenant', 'lease__unit__property'
    ), id=pk, company=company)
    
    # Papildu piekļuves pārbaude īrniekam
    is_tenant = (request.user.role == 'tenant' and request.user == invoice.lease.tenant)
    
    if not (is_company_admin or is_tenant):
        messages.error(request, "Jums nav tiesību aplūkot šo rēķinu.")
        if request.user.role == 'tenant':
            return redirect('tenant_portal:dashboard')
        else:
            return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Iegūstam rēķina pozīcijas
    items = invoice.items.all()
    
    return render(request, 'invoices/invoice_print.html', {
        'invoice': invoice,
        'items': items,
        'company': company
    })