from django.db import models
import uuid
from core.models import TenantModel

class Lease(TenantModel):
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='leases')
    tenant = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='leases',
        null=True,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('terminated', 'Terminated'),
        ('expired', 'Expired')
    ])
    
    def __str__(self):
        tenant_name = self.tenant.get_full_name() if self.tenant else "Nav īrnieka"
        return f"{self.unit.property.address} - {self.unit.unit_number} ({tenant_name})"


class LeaseBilling(TenantModel):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='billings')
    period_start = models.DateField()
    period_end = models.DateField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    utility_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ])
    
    def __str__(self):
        return f"Rēķins {self.lease} ({self.period_start} - {self.period_end})"
    
    def save(self, *args, **kwargs):
        # Automātiski aprēķināt total_amount, ja nav norādīts
        if not self.total_amount:
            self.total_amount = self.rent_amount + self.utility_amount + self.other_charges
        super().save(*args, **kwargs)


class LeaseDocument(TenantModel):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='lease_documents/')
    document_type = models.CharField(max_length=50, choices=[
        ('contract', 'Contract'),
        ('amendment', 'Amendment'),
        ('termination', 'Termination'),
        ('other', 'Other')
    ])
    title = models.CharField(max_length=255)  # Pievienots title lauks
    description = models.TextField(blank=True)  # Pievienots apraksts
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.title}"