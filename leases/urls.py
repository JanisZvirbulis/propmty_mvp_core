from django.urls import path
from . import views

app_name = 'leases'
urlpatterns = [
    path('', views.company_lease_list, name='lease_list'),
    path('<uuid:property_pk>/units/<uuid:unit_pk>/create/', views.lease_create, name='lease_create'),
    path('<uuid:pk>/', views.lease_detail, name='lease_detail'),
    path('<uuid:pk>/edit/', views.lease_edit, name='lease_edit'),
    path('<uuid:pk>/terminate/', views.lease_terminate, name='lease_terminate'),
    path('<uuid:pk>/delete/', views.lease_delete, name='lease_delete'),
]