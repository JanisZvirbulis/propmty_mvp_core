from django.db import models
import uuid
from core.models import TenantModel
from django.utils import timezone
from leases.models import Lease

class Tax(TenantModel):
    """Nodokļu definīcijas, ko var pielietot rēķinu pozīcijām"""
    name = models.CharField(max_length=100)  # Piem., "PVN", "Elektroenerģijas nodoklis"
    code = models.CharField(max_length=20, blank=True)  # Piem., "VAT", "ELEC_TAX"
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # Nodokļa likme procentos
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)  # Vai šis ir noklusējuma nodoklis
    
    # Nodokļu kategorijas
    CATEGORY_CHOICES = [
        ('standard', 'Standarta nodoklis'),
        ('reduced', 'Samazinātā likme'),
        ('energy', 'Enerģijas nodoklis'),
        ('water', 'Ūdens nodoklis'),
        ('gas', 'Gāzes nodoklis'),
        ('waste', 'Atkritumu nodoklis'),
        ('other', 'Cits')
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='standard')
    
    class Meta:
        verbose_name = "Nodoklis"
        verbose_name_plural = "Nodokļi"
        
    def __str__(self):
        return f"{self.name} ({self.rate}%)"
    
class Invoice(TenantModel):
    number = models.CharField(max_length=50)  # Rēķina numurs
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    issue_date = models.DateField()
    period_start = models.DateField(default=timezone.now)
    period_end = models.DateField(default=timezone.now)
    due_date = models.DateField()
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Summa bez nodokļiem
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Nodokļu summa
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Kopējā summa ar nodokļiem
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
    
    def update_total(self):
        """Atjaunina rēķina kopsummas, balstoties uz pozīcijām"""
        items = self.items.all()
        subtotal = sum(item.amount for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total = subtotal + tax_amount
        
        self.subtotal_amount = subtotal
        self.tax_amount = tax_amount
        self.total_amount = total
        self.save(update_fields=['subtotal_amount', 'tax_amount', 'total_amount'])
    
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
    # Jaunie lauki
    tax = models.ForeignKey(Tax, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_items')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Nodokļa summa
    type = models.CharField(max_length=50, default='standard', choices=[
        ('standard', 'Standarta'),
        ('rent', 'Īres maksa'),
        ('utility', 'Komunālie maksājumi'),
        ('maintenance', 'Remontdarbi'),
        ('fee', 'Papildu maksa'),
        ('discount', 'Atlaide'),
        ('other', 'Cits')
    ])
    
    def __str__(self):
        return f"{self.description} ({self.amount} €)"
    
    def save(self, *args, **kwargs):
        # Aprēķinām summu, ja tā nav norādīta
        if not self.amount:
            self.amount = self.quantity * self.unit_price
        
        # Aprēķinām nodokli, ja tas ir pievienots
        if self.tax and not self.tax_amount:
            self.tax_amount = (self.amount * self.tax.rate / 100).quantize(Decimal('0.01'))
            
        super().save(*args, **kwargs)
        
        # Atjauninam rēķina kopsummu pēc pozīcijas saglabāšanas
        self.invoice.update_total()
    
    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.update_total()