# properties/urls.py
from django.urls import path
from . import views

app_name = 'properties'
urlpatterns = [
    path('', views.property_list, name='property_list'),
    path('create/', views.property_create, name='property_create'),
    path('<uuid:pk>/', views.property_detail, name='property_detail'),
    path('<uuid:pk>/edit/', views.property_edit, name='property_edit'),
    path('<uuid:pk>/delete/', views.property_delete, name='property_delete'),
    path('<uuid:pk>/units/create/', views.unit_create, name='unit_create'),
    path('<uuid:property_pk>/units/<uuid:pk>/', views.unit_detail, name='unit_detail'),
    path('<uuid:property_pk>/units/<uuid:unit_pk>/edit/', views.unit_edit, name='unit_edit'),
    path('<uuid:property_pk>/units/<uuid:unit_pk>/delete/', views.unit_delete, name='unit_delete'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/', views.unit_meters, name='unit_meters'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/add/', views.unit_meter_add, name='unit_meter_add'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/<uuid:meter_pk>/', views.unit_meter_detail, name='unit_meter_detail'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/<uuid:meter_pk>/edit/', views.unit_meter_edit, name='unit_meter_edit'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/<uuid:meter_pk>/delete/', views.unit_meter_delete, name='unit_meter_delete'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/<uuid:meter_pk>/readings/add/', views.meter_reading_add, name='meter_reading_add'),
    path('<uuid:property_pk>/units/<uuid:pk>/meters/<uuid:meter_pk>/readings/<uuid:reading_pk>/delete/', views.meter_reading_delete, name='meter_reading_delete'),
    path('meters/readings/', views.company_meter_readings, name='company_meter_readings'),
    path('meters/readings/<uuid:pk>/verify/', views.verify_meter_reading, name='verify_meter_reading'),
]