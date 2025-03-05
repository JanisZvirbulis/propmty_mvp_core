from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/manager/', views.register_manager, name='register_manager'),
    path('register/tenant/', views.register_tenant, name='register_tenant'),
    path('profile/', views.profile, name='profile'),
    path('redirect/', views.redirect_after_login, name='redirect_after_login'),
    path('invitation/<uuid:token>/', views.company_invitation, name='company_invitation'),
    path('invitation/<uuid:token>/register/', views.company_register, name='company_register'),
    path('invitation/<uuid:token>/accept/', views.accept_company_invitation, name='accept_company_invitation'),
    # path('company/', views.company_list, name='company_list'),
    # path('company/create/', views.company_create, name='company_create'),
    # path('company/<uuid:pk>/', views.company_detail, name='company_detail'),
    # path('company/<uuid:pk>/edit/', views.company_edit, name='company_edit'),
    # path('invitation/<uuid:token>/', views.lease_invitation, name='lease_invitation'),
    # path('invitation/<uuid:token>/register/', views.tenant_register, name='tenant_register'),
]