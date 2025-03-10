from core.models import TenantModel
from django.db import models
from django.conf import settings
from django.utils import timezone

class Property(TenantModel):
    address = models.CharField(max_length=255)
    cadastral_number = models.CharField(max_length=100, blank=True)
    total_area = models.DecimalField(max_digits=10, decimal_places=2)
    building_type = models.CharField(max_length=20, choices=[
        ('apartment_building', 'Apartment Building'),
        ('commercial_building', 'Commercial Building'),
        ('private_house', 'Private House'),
        ('mixed_use', 'Mixed Use Building')
    ])
    floor_count = models.IntegerField(help_text="Total number of floors")
    year_built = models.IntegerField(null=True, blank=True)
    
    # Pārvaldnieks - izmantojam saiti uz User modeli
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_properties'
    )

    # Skaitītāji visai ēkai
    has_building_water_meter = models.BooleanField(default=False)
    has_building_gas_meter = models.BooleanField(default=False)
    has_building_electricity_meter = models.BooleanField(default=False)
    has_building_heating_meter = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Properties"
        unique_together = ['company', 'address']  # Katrai kompānijai adrese ir unikāla

    def __str__(self):
        return f"{self.address} ({self.get_building_type_display()})"
    

    # properties/models.py
class Unit(TenantModel):
    property = models.ForeignKey(
        Property, 
        on_delete=models.CASCADE, 
        related_name='units'
    )
    unit_number = models.CharField(max_length=10, help_text="Apartment/Unit number")
    floor = models.IntegerField()
    area = models.DecimalField(max_digits=10, decimal_places=2)
    rooms = models.IntegerField()
    unit_type = models.CharField(max_length=20, choices=[
        ('apartment', 'Apartment'),
        ('office', 'Office'),
        ('retail', 'Retail Space'),
        ('warehouse', 'Warehouse'),
        ('other', 'Other')
    ])
    status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved')
    ])

    # Skaitītāji
    has_water_meter = models.BooleanField(default=False)
    has_gas_meter = models.BooleanField(default=False)
    has_electricity_meter = models.BooleanField(default=False)
    has_heating_meter = models.BooleanField(default=False)

    # Papildus parametri
    bathroom_count = models.IntegerField(default=1)
    has_balcony = models.BooleanField(default=False)
    has_storage = models.BooleanField(default=False)
    parking_spots = models.IntegerField(default=0)
    
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['property', 'unit_number']

    def __str__(self):
        return f"{self.property.address} - Unit {self.unit_number}"
    
    # properties/models.py
class UnitMeter(TenantModel):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='meters')
    meter_type = models.CharField(max_length=20, choices=[
        ('water_cold', 'Cold Water'),
        ('water_hot', 'Hot Water'),
        ('gas', 'Gas'),
        ('electricity', 'Electricity'),
        ('heating', 'Heating')
    ])
    meter_number = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired')
    ], default='active')
    expire_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Pievienojam tarifa lauku
    tariff = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, 
                               help_text="Tarifs par vienu vienību (€)")

    class Meta:
        unique_together = ['unit', 'meter_type', 'meter_number']
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'meter_type'],
                condition=models.Q(status='active'),
                name='unique_active_meter_type_per_unit'
            )
        ]

    def update_status(self):
        """Atjaunina skaitītāja statusu balstoties uz expire_date"""
        today = timezone.now().date()
        if self.expire_date and self.expire_date < today and self.status == 'active':
            self.status = 'expired'
            self.save()
        return self.status

    def save(self, *args, **kwargs):
        if self.expire_date:
            today = timezone.now().date()
            if self.expire_date < today and self.status == 'active':
                self.status = 'expired'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_meter_type_display()} - {self.meter_number}"
    

    # properties/models.py
class MeterReading(TenantModel):
    meter = models.ForeignKey(UnitMeter, on_delete=models.CASCADE, related_name='readings')
    reading = models.DecimalField(max_digits=10, decimal_places=2)
    reading_date = models.DateField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_readings'
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_readings'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-reading_date', '-created_at']

    def __str__(self):
        return f"{self.meter} - {self.reading} ({self.reading_date})"

    def save(self, *args, **kwargs):
        if self.is_verified and not self.verification_date:
            self.verification_date = timezone.now()
        super().save(*args, **kwargs)