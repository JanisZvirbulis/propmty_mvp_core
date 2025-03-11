from django.urls import path, include
from companies import views

app_name = 'companies_tenant'
urlpatterns = [
    path('', views.company_detail, name='company_detail'),
    path('members/', views.company_members, name='company_members'),
    path('members/invite/', views.invite_member, name='invite_member'),
    path('members/role/<uuid:member_id>/', views.change_member_role, name='change_member_role'),
    path('members/remove/<uuid:member_id>/', views.remove_member, name='remove_member'),
    path('members/invitations/cancel/<uuid:invitation_id>/', views.cancel_invitation, name='cancel_invitation'),
    path('settings/', views.company_settings, name='company_settings'),
    path('settings/tax/add/', views.company_add_tax, name='company_add_tax'),
    path('settings/tax/<uuid:tax_id>/edit/', views.company_edit_tax, name='company_edit_tax'),
    path('settings/tax/<uuid:tax_id>/delete/', views.company_delete_tax, name='company_delete_tax'),
    # path('edit/', views.company_edit, name='company_edit'),
    # path('members/', views.company_members, name='company_members'),
    # path('settings/', views.company_settings, name='company_settings'),
    
    # Tenant-specific app URL includes
    # path('tenants/', include('tenants.urls')),
    # path('meters/', include('meters.urls')),
    # path('invoices/', include('invoices.urls')),
]