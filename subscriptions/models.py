from django.db import models
import uuid

class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(max_length=20, choices=[
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], default='monthly')
    
    # Ierobežojumi
    max_properties = models.IntegerField(default=5)
    max_units = models.IntegerField(default=50)
    max_users = models.IntegerField(default=3)
    
    # Funkcionalitāte
    enable_invoicing = models.BooleanField(default=False)
    enable_reports = models.BooleanField(default=False)
    enable_tenant_portal = models.BooleanField(default=False)
    enable_document_storage = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_billing_period_display()})"
    

    # subscriptions/models.py
class CompanySubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField('companies.Company', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='company_subscriptions')
    
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
    ], default='trialing')
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Payment tracking (simplified for example)
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"
    
    def is_active(self):
        import datetime
        return self.status == 'active' and self.end_date >= datetime.date.today()