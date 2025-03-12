from django.db import models
from core.models import TenantModel
from core.storage import IssueImageStorage


def get_report_Issue_image_upload_path(instance, filename):
    company_id = instance.company_id  # Izmantojam _id, lai piekļūtu tieši foreign key vērtībai
    issue_id = instance.issue_id
    return f'company/{company_id}/issueimages/{issue_id}/{filename}'

class Inspection(TenantModel):
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='inspections')
    inspector = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='conducted_inspections')
    inspection_type = models.CharField(max_length=20, choices=[
        ('routine', 'Routine'),
        ('move_in', 'Move In'),
        ('move_out', 'Move Out'),
        ('complaint', 'Complaint'),
        ('maintenance', 'Maintenance')
    ])
    scheduled_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ])
    notes = models.TextField(blank=True)

class Issue(TenantModel):
    inspection = models.ForeignKey(
        Inspection, 
        on_delete=models.CASCADE, 
        related_name='issues',
        null=True,  # Ļaujam būt null, jo ne visas problēmas būs saistītas ar inspekciju
        blank=True
    )
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reported_issues')
    issue_type = models.CharField(max_length=20, choices=[
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('structural', 'Structural'),
        ('appliance', 'Appliance'),
        ('heating', 'Heating'),
        ('water', 'Water Supply'),
        ('ventilation', 'Ventilation'),
        ('security', 'Security'),
        ('other', 'Other')
    ])
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    status = models.CharField(max_length=20, choices=[
        ('reported', 'Reported'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ])
    description = models.TextField()
    expected_completion = models.DateField(null=True, blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_issues'
    )
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    show_estimated_cost = models.BooleanField(default=True)

class IssueImage(TenantModel):
    image = models.ImageField(upload_to=get_report_Issue_image_upload_path, storage=IssueImageStorage(), max_length=255)
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='images'
    )
    uploaded_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
class Maintenance(TenantModel):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='maintenance_records')
    assigned_to = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='assigned_maintenance')
    scheduled_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ])
    notes = models.TextField(blank=True)