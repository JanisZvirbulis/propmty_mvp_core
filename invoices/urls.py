from django.urls import path
from . import views

app_name = 'invoices'
urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('create/<uuid:lease_id>/', views.invoice_create, name='invoice_create'),
    path('<uuid:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<uuid:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('<uuid:pk>/send/', views.invoice_send, name='invoice_send'),
    path('<uuid:pk>/mark_paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
    path('<uuid:pk>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('<uuid:pk>/print/', views.invoice_print, name='invoice_print'),
]