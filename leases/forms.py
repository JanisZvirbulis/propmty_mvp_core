from django import forms
from django.utils import timezone
from .models import Lease
from users.models import User

class LeaseCreateForm(forms.ModelForm):
    tenant_email = forms.EmailField(
        label='Tenant Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Lease
        fields = ['start_date', 'end_date', 'rent_amount', 'security_deposit']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'rent_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'security_deposit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("End date must be after start date")
            
            if start_date < timezone.now().date():
                raise forms.ValidationError("Start date cannot be in the past")

        return cleaned_data
    

class LeaseEditForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ['start_date', 'end_date', 'rent_amount', 'security_deposit']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control'})
        }

class LeaseTerminateForm(forms.Form):
    termination_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    unit_status = forms.ChoiceField(
        choices=[
            ('available', 'Available'),
            ('maintenance', 'Under Maintenance')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

