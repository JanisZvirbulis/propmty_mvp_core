from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from core.decorators import tenant_required
from .models import Invoice
from .forms import InvoiceForm, InvoiceItemFormSet
from leases.models import Lease

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
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Vispirms izveidojam rēķinu, bet vēl nesaglabājam
            invoice = form.save(commit=False)
            invoice.company = company
            invoice.lease = lease
            
            # Ģenerējam rēķina numuru
            current_year = timezone.now().year
            current_month = timezone.now().month
            # Atrodam rēķinu skaitu šajā mēnesī
            month_invoice_count = Invoice.objects.filter(
                company=company,
                issue_date__year=current_year,
                issue_date__month=current_month
            ).count()
            
            # Formāts: YYYY-MM-COUNT (piemēram, 2023-01-0001)
            invoice.number = f"{current_year}-{current_month:02d}-{month_invoice_count+1:04d}"
            
            # Aprēķinam kopējo summu no formset datiem, pirms saglabājam rēķinu
            total_amount = 0
            for form in formset:
                if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                    quantity = form.cleaned_data.get('quantity', 0)
                    unit_price = form.cleaned_data.get('unit_price', 0)
                    if quantity and unit_price:
                        total_amount += quantity * unit_price
            
            # Iestatām total_amount pirms saglabāšanas
            invoice.total_amount = total_amount
            
            # Tagad varam droši saglabāt rēķinu
            invoice.save()
            
            # Manuāli saglabājam rēķina pozīcijas, iestatot company_id
            for form in formset:
                if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                    item = form.save(commit=False)
                    item.invoice = invoice
                    item.company = company  # Svarīgākā daļa - iestatām company_id
                    
                    # Aprēķinam amount, ja tas nav norādīts
                    if not item.amount:
                        item.amount = item.quantity * item.unit_price
                        
                    item.save()
            
            messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi izveidots.")
            return redirect('invoices:invoice_detail', company_slug=company_slug, pk=invoice.id)
    else:
        # Izveidojam noklusējuma rēķina pozīciju ar īres maksu
        form = InvoiceForm()
        invoice = Invoice(company=company, lease=lease)
        formset = InvoiceItemFormSet(instance=invoice)
        
        # Pievienojam noklusējuma rēķina pozīciju ar īres maksu
        formset.forms[0].initial = {
            'description': f"Īres maksa - {lease.unit.property.address}, {lease.unit.unit_number}",
            'quantity': 1,
            'unit_price': lease.rent_amount
        }
    
    return render(request, 'invoices/invoice_form.html', {
        'form': form,
        'formset': formset,
        'company': company,
        'lease': lease,
        'action': 'create',
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
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        
        if form.is_valid() and formset.is_valid():
            # Saglabājam rēķinu
            form.save()
            formset.save()
            
            # Aprēķinām kopējo summu
            total = 0
            for item in invoice.items.all():
                total += item.amount
            
            invoice.total_amount = total
            invoice.save()
            
            messages.success(request, f"Rēķins Nr. {invoice.number} veiksmīgi atjaunināts.")
            return redirect('invoices:invoice_detail', company_slug=company_slug, pk=invoice.id)
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)
    
    return render(request, 'invoices/invoice_form.html', {
        'form': form,
        'formset': formset,
        'company': company,
        'invoice': invoice,
        'lease': invoice.lease,
        'action': 'edit',
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