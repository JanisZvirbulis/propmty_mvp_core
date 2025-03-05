from django.contrib import admin
from .models import SubscriptionPlan, CompanySubscription

# Register your models here.
admin.site.register(SubscriptionPlan)
admin.site.register(CompanySubscription)