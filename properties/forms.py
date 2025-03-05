from django import forms
from .models import Property, Unit, UnitMeter, MeterReading
import datetime

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['address', 'building_type', 'total_area', 'floor_count', 'year_built', 
                'cadastral_number', 'has_building_water_meter', 'has_building_gas_meter', 
                'has_building_electricity_meter', 'has_building_heating_meter']
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'building_type': forms.Select(attrs={'class': 'form-select'}),
            'total_area': forms.NumberInput(attrs={'class': 'form-control'}),
            'floor_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'year_built': forms.NumberInput(attrs={'class': 'form-control'}),
            'cadastral_number': forms.TextInput(attrs={'class': 'form-control'}),
            'has_building_water_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_building_gas_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_building_electricity_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_building_heating_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ['unit_number', 'floor', 'area', 'rooms', 'unit_type', 'status',
                  'has_water_meter', 'has_gas_meter', 'has_electricity_meter', 'has_heating_meter',
                  'bathroom_count', 'has_balcony', 'has_storage', 'parking_spots', 'notes']
        widgets = {
            'unit_number': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'area': forms.NumberInput(attrs={'class': 'form-control'}),
            'rooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'has_water_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_gas_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_electricity_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_heating_meter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'bathroom_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'has_balcony': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_storage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parking_spots': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class UnitMeterForm(forms.ModelForm):
    class Meta:
        model = UnitMeter
        fields = ['meter_type', 'meter_number', 'status', 'expire_date', 'notes']
        widgets = {
            'meter_type': forms.Select(attrs={'class': 'form-select'}),
            'meter_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'expire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.unit = kwargs.pop('unit', None)
        super().__init__(*args, **kwargs)
        
        # Ja veido jaunu mērītāju, pārbauda, vai konkrētā mērītāja tips jau eksistē
        if not self.instance.pk and self.unit:
            existing_meter_types = self.unit.meters.filter(status='active').values_list('meter_type', flat=True)
            valid_choices = []
            for choice in self.fields['meter_type'].choices:
                if choice[0] and choice[0] not in existing_meter_types:
                    valid_choices.append(choice)
            self.fields['meter_type'].choices = valid_choices
            
            # Ja nav neviena pieejama mērītāja tipa
            if not valid_choices:
                self.fields['meter_type'].choices = [('', '--- Visi mērītāju tipi jau ir pievienoti ---')]
                self.fields['meter_type'].help_text = 'Lai pievienotu jaunu mērītāju, vispirms deaktivizējiet esošo.'

class MeterReadingForm(forms.ModelForm):
    class Meta:
        model = MeterReading
        fields = ['reading', 'reading_date', 'notes']
        widgets = {
            'reading': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reading_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.meter = kwargs.pop('meter', None)
        super().__init__(*args, **kwargs)
        
        # Iestatām noklusējuma datumu kā šodiena
        self.fields['reading_date'].initial = datetime.date.today()
        
        # Ja izveide, pievienojam palīdzības tekstu
        if self.meter:
            # Atrodam pēdējo rādījumu
            last_reading = self.meter.readings.order_by('-reading_date').first()
            if last_reading:
                self.fields['reading'].help_text = f"Pēdējais rādījums: {last_reading.reading} ({last_reading.reading_date})"
    
    def clean(self):
        cleaned_data = super().clean()
        reading = cleaned_data.get('reading')
        reading_date = cleaned_data.get('reading_date')
        
        if reading is not None and reading_date and self.meter:
            # Atrodam jaunākos rādījumus pirms šī datuma
            newer_readings = self.meter.readings.filter(
                reading_date__gt=reading_date
            ).order_by('reading_date')
            
            if newer_readings.exists():
                first_newer = newer_readings.first()
                if reading > first_newer.reading:
                    self.add_error('reading', f"Rādījums nevar būt lielāks par nākamo rādījumu ({first_newer.reading} no {first_newer.reading_date})")
            
            # Atrodam vecākos rādījumus pēc šī datuma
            older_readings = self.meter.readings.filter(
                reading_date__lt=reading_date
            ).order_by('-reading_date')
            
            if older_readings.exists():
                first_older = older_readings.first()
                if reading < first_older.reading:
                    self.add_error('reading', f"Rādījums nevar būt mazāks par iepriekšējo rādījumu ({first_older.reading} no {first_older.reading_date})")
        
        return cleaned_data