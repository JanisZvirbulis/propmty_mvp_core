from django import forms
from .models import Company, CompanyMember

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'registration_number', 'vat_number', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'})
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