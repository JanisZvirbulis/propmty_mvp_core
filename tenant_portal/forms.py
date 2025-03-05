from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms.widgets import ClearableFileInput
from users.models import User
from inspections.models import Issue


class BaseUserRegistrationForm(forms.ModelForm):
    """Bāzes klase kopīgai e-pasta validācijai"""
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Lietotājs ar šādu e-pastu jau eksistē.')
        return email
    
class TenantRegistrationForm(UserCreationForm, BaseUserRegistrationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        disabled=True  # E-pasts būs nofiksēts no uzaicinājuma
    )
    phone = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    personal_code = forms.CharField(
        max_length=50, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'personal_code', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Atjauninām paroles laukus ar Bootstrap klasēm
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
        
        # Ja e-pasts jau ir zināms (no uzaicinājuma), to nevar mainīt
        if 'email' in self.initial:
            self.fields['email'].disabled = True
            # Tā kā lauks ir disabled, tas netiks iekļauts POST datu validācijā,
            # tāpēc vajag apiet e-pasta unikalitātes pārbaudi
            self.fields['email'].validators = []
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'tenant'  # Iestatām tenant lomu
        
        if commit:
            user.save()
        return user
    

class MultipleImageInput(ClearableFileInput):
    allow_multiple_selected = True

class IssueReportForm(forms.ModelForm):

    class Meta:
        model = Issue
        fields = ['issue_type', 'priority', 'description']
        widgets = {
            'issue_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Lūdzu, aprakstiet problēmu detalizēti...'
            })
        }
        images = forms.FileField(
        required=False,
        widget=MultipleImageInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'  # Atļaut tikai attēlu failus
        })
    )
    