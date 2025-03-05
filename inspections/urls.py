from django.urls import path
from . import views

app_name = 'inspections'
urlpatterns = [
    path('issues/', views.company_issues, name='company_issues'),
    path('issues/<uuid:pk>/', views.issue_detail, name='issue_detail'),
    path('issues/<uuid:pk>/update-status/', views.update_issue_status, name='update_issue_status'),
    path('issues/<uuid:pk>/assign-maintenance/', views.assign_maintenance, name='assign_maintenance'),
]