from django.db import models
import uuid
from core.models import TenantModel

class TenantInvitation(TenantModel):
    lease = models.OneToOneField('leases.Lease', on_delete=models.CASCADE)
    email = models.EmailField()
    invitation_token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired')
    ], default='pending')
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Uzaicinājums: {self.email} ({self.get_status_display()})"
    
    def is_expired(self):
        """Pārbauda vai uzaicinājums ir beidzies"""
        from django.utils import timezone
        return self.expires_at < timezone.now()