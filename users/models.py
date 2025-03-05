from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    id = models.UUIDField(default=uuid.uuid4 ,unique=True, primary_key=True, editable=False)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True, max_length=254)
    role = models.CharField(max_length=20, choices=[
        ('company_owner', 'Company Owner'),
        ('manager', 'Manager'),
        ('tenant', 'Tenant'),
    ])
    personal_code = models.CharField(max_length=50, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Pievienojam related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set'
    )

    def __str__(self):
        return str(self.first_name + ' ' + self.last_name + ' (' + self.role + ')')
    
    class Meta:
        db_table = 'users'