from django.urls import path
from . import views

app_name = 'tenant_portal'
urlpatterns = [
    path('dashboard/', views.tenant_dashboard, name='dashboard'),
    path('invitation/<uuid:token>/', views.lease_invitation, name='lease_invitation'),
    path('invitation/<uuid:token>/register/', views.tenant_register, name='tenant_register'),
    path('issues/', views.tenant_issues, name='tenant_issues'),
    path('issues/report/<uuid:lease_id>/', views.report_issue, name='report_issue'),
    path('issues/<uuid:issue_id>/', views.tenant_issue_detail, name='tenant_issue_detail'),
    path('meter_readings/', views.tenant_meter_readings, name='meter_readings'),
    path('meter_readings/<uuid:lease_id>/<uuid:meter_id>/submit/', views.submit_reading, name='submit_reading'),
    path('meter_readings/<uuid:lease_id>/<uuid:meter_id>/history/', views.unit_meter_readings_history, name='readings_history'),
]