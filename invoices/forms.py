from django import forms
from .models import Invoice, InvoiceItem
from django.utils import timezone
import datetime

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['issue_date', 'due_date', 'notes']
        widgets = {
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Uzstāda noklusējuma vērtības datumiem
        if not self.instance.pk:  # Ja tiek veidots jauns rēķins
            self.fields['issue_date'].initial = timezone.now().date()
            # Maksājuma termiņš pēc noklusējuma ir 14 dienas
            self.fields['due_date'].initial = (timezone.now().date() + datetime.timedelta(days=14))

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

InvoiceItemFormSet = forms.inlineformset_factory(
    Invoice, InvoiceItem, form=InvoiceItemForm, 
    extra=1, can_delete=True
)