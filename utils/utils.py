from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.conf import settings
from datetime import date, datetime, timedelta
import calendar

def send_lease_invitation_email(invitation):
    subject = 'Invitation to sign lease agreement'
    invitation_url = reverse('tenant_portal:lease_invitation', args=[invitation.invitation_token])
    full_url = f"{settings.SITE_URL}{invitation_url}"
    
    context = {
        'invitation': invitation,
        'invitation_url': full_url,
        'expires_at': invitation.expires_at,
    }
    
    html_message = render_to_string('partials/email/invitation.html', context)
    plain_message = render_to_string('partials/email/invitation.txt', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        html_message=html_message
    )

def send_company_invitation_email(invitation):
    subject = 'Invitation to join company'
    invitation_url = reverse('users:company_invitation', args=[invitation.invitation_token])
    full_url = f"{settings.SITE_URL}{invitation_url}"
    
    context = {
        'invitation': invitation,
        'invitation_url': full_url,
        'expires_at': invitation.expires_at,
    }
    
    html_message = render_to_string('partials/email/company_invitation.html', context)
    plain_message = render_to_string('partials/email/company_invitation.txt', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        html_message=html_message
    )

def send_invoice_email(invoice, tenant, company, view_url):
    """
    Nosūta e-pastu īrniekam par jaunu vai kavētu rēķinu.
    
    Args:
        invoice: Invoice objekts
        tenant: User objekts (īrnieks)
        company: Company objekts
        view_url: URL uz rēķina skatu īrnieka portālā
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings
    
    subject = f"Rēķins Nr.{invoice.number} no {company.name}"
    
    # Sagatavojam kontekstu šablonam
    context = {
        'invoice': invoice,
        'tenant': tenant,
        'company': company,
        'items': invoice.items.all(),
        'view_url': view_url
    }
    
    # Iegūstam HTML un teksta saturu
    html_content = render_to_string('partials/email/invoice_email.html', context)
    text_content = render_to_string('partials/email/invoice_email.txt', context)
    
    # Izveidojam e-pasta ziņojumu
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[tenant.email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Nosūtām e-pastu
    email.send()
    
    return True

def get_previous_month():
    today = date.today()

    # Iepriekšējais mēnesis un gads
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1

    # Iepriekšējā mēneša pirmā diena
    period_start = date(prev_year, prev_month, 1)

    # Iepriekšējā mēneša pēdējā diena
    last_day = calendar.monthrange(prev_year, prev_month)[1]
    period_end = date(prev_year, prev_month, last_day)

    return period_start, period_end



def tenant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'tenant':
            messages.error(request, 'Access denied. Tenant privileges required.')
            return redirect('users:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
