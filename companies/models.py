# companies/models.py
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from core.storage import CompanyStorage
import uuid

def get_company_logo_upload_path(instance, filename):
    return f'company/{instance.id}/logo/{filename}'


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_companies'
    )
    address = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to=get_company_logo_upload_path, blank=True, null=True, storage=CompanyStorage())
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"
    
    def get_subscription(self):
        try:
            return self.subscription
        except:
            return None
    
    def can_add_property(self):
        subscription = self.get_subscription()
        if not subscription or not subscription.is_active():
            return False
        
        property_count = self.properties.count()
        return property_count < subscription.plan.max_properties
    
    def can_add_unit(self):
        subscription = self.get_subscription()
        if not subscription or not subscription.is_active():
            return False
        
        unit_count = 0
        for prop in self.properties.all():
            unit_count += prop.units.count()
        
        return unit_count < subscription.plan.max_units
    
    def can_add_member(self):
        subscription = self.get_subscription()
        if not subscription or not subscription.is_active():
            return False
        
        # +1 par īpašnieku
        member_count = self.members.count() + 1
        return member_count < subscription.plan.max_users

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Automātiski ģenerēt slug, ja tas vēl nav norādīts
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class CompanyMember(models.Model):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        MANAGER = 'MANAGER', 'Manager'
        MEMBER = 'MEMBER', 'Member'
        TECHNICIAN = 'TECHNICIAN', 'Technician'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.MEMBER
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'user']
        
    def __str__(self):
        return f"{self.user} - {self.company} ({self.get_role_display()})"
    

class CompanyInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    invitation_token = models.UUIDField(default=uuid.uuid4, unique=True)
    role = models.CharField(max_length=20, choices=CompanyMember.Roles.choices, default=CompanyMember.Roles.MEMBER)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired')
    ], default='pending')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Uzaicinājums: {self.email} ({self.get_status_display()})"
    
    def is_expired(self):
        return self.expires_at < timezone.now()