from django.db import models
import uuid
from core.models import TenantModel
from django.utils import timezone
from leases.models import Lease

class Invoice(TenantModel):
    number = models.CharField(max_length=50)  # Rēķina numurs
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], default='draft')
    is_sent = models.BooleanField(default=False)  # Vai rēķins ir nosūtīts īrniekam
    sent_date = models.DateTimeField(null=True, blank=True)
    paid_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)  # Piezīmes rēķinam
    
    def __str__(self):
        return f"Rēķins Nr.{self.number} ({self.lease})"
    
    def send_to_tenant(self):
        """Nosūta rēķinu īrniekam un atjauno statusu"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_date = timezone.now()
            if self.status == 'draft':
                self.status = 'sent'
            self.save()
            return True
        return False
    
    def mark_as_paid(self):
        """Atzīmē rēķinu kā apmaksātu"""
        self.status = 'paid'
        self.paid_date = timezone.now()
        self.save()
        return True
    
    def update_status(self):
        """Atjauno rēķina statusu balstoties uz due_date"""
        today = timezone.now().date()
        if self.status == 'sent' and self.due_date < today:
            self.status = 'overdue'
            self.save()
        return self.status

class InvoiceItem(TenantModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)  # Pozīcijas apraksts
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Summa
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)  # Daudzums
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Vienības cena
    
    def __str__(self):
        return f"{self.description} ({self.amount} €)"
    
    def save(self, *args, **kwargs):
        # Automātiski aprēķina summu, ja nav norādīta
        if not self.amount:
            self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)