from django import forms
from .models import Invoice, InvoiceItem, Tax
from django.utils import timezone
import datetime

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['issue_date', 'due_date', 'notes', 'period_start', 'period_end']
        widgets = {
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'period_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'period_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Uzstāda noklusējuma vērtības datumiem
        if not self.instance.pk:  # Ja tiek veidots jauns rēķins
            self.fields['issue_date'].initial = timezone.now().date()
            # Maksājuma termiņš pēc noklusējuma ir 14 dienas
            self.fields['due_date'].initial = (timezone.now().date() + datetime.timedelta(days=14))

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

# Papildinājumi esošajām formām
class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price', 'tax', 'type']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            # Filtrējam nodokļus pēc uzņēmuma
            self.fields['tax'].queryset = Tax.objects.filter(company=company)

InvoiceItemFormSet = forms.inlineformset_factory(
    Invoice, InvoiceItem, form=InvoiceItemForm, 
    extra=1, can_delete=True
)