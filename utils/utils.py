from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.conf import settings

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


def tenant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'tenant':
            messages.error(request, 'Access denied. Tenant privileges required.')
            return redirect('users:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
