# forms.py
from django import forms
from .models import Maintenance
from users.models import User
from companies.models import CompanyMember

class MaintenanceAssignForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['assigned_to', 'scheduled_date', 'description', 'cost']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Atlasam tikai konkrētā uzņēmuma lietotājus
        if company:
            # Ietver uzņēmuma īpašnieku
            company_users = [company.owner]
            
            # Ietver uzņēmuma dalībniekus
            company_members = CompanyMember.objects.filter(
                company=company, 
                is_active=True
            ).select_related('user')
            
            for member in company_members:
                company_users.append(member.user)
            
            # Uztaisam unikālu sarakstu
            company_users = list(set(company_users))
            
            # Iestatām izvēles
            self.fields['assigned_to'].queryset = User.objects.filter(
                id__in=[user.id for user in company_users]
            )
        else:
            # Ja nav norādīts uzņēmums, atlasām visus lietotājus (var noderēt testēšanai)
            self.fields['assigned_to'].queryset = User.objects.all()