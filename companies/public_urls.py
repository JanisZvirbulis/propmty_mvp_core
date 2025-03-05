from django.urls import path
from companies import views

app_name = 'companies_public'
urlpatterns = [
    path('', views.company_list, name='company_list'),
    path('create/', views.company_create, name='company_create'),
]