from django import forms
from .models import Company, CompanyMember
from invoices.models import Tax

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'registration_number', 'vat_number', 'email', 'phone', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class CompanyInvitationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='E-pasta adrese, uz kuru nosūtīt uzaicinājumu'
    )
    role = forms.ChoiceField(
        choices=CompanyMember.Roles.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=CompanyMember.Roles.MEMBER,
        help_text='Loma, kāda tiks piešķirta lietotājam uzņēmumā'
    )

class CompanyMemberRoleForm(forms.ModelForm):
    class Meta:
        model = CompanyMember
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'registration_number', 'vat_number', 'email', 'phone', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

# Forma nodokļu pievienošanai/rediģēšanai
class TaxForm(forms.ModelForm):
    class Meta:
        model = Tax
        fields = ['name', 'code', 'rate', 'category', 'description', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }