# clinicform.py
from django import forms
from .models import Clinic

class ClinicForm(forms.ModelForm):
    class Meta:
        model = Clinic
        fields = ['clinic_name', 'pan_number', 'address', 'phone']
        # created_by, created_at, updated_at are handled elsewhere

        widgets = {
            'clinic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Clinic name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PAN / Tax number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'}),
        }

    def clean_clinic_name(self):
        name = self.cleaned_data.get('clinic_name')
        if len(name) < 2:
            raise forms.ValidationError('Clinic name must be at least 2 characters long.')
        return name

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number')
        # Example: only digits and length up to 10 (adjust as needed)
        if pan and not pan.isdigit():
            raise forms.ValidationError('PAN number must contain only digits.')
        if pan and len(pan) > 10:
            raise forms.ValidationError('PAN number cannot exceed 10 digits.')
        return pan

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError('Phone number must contain only digits.')
        if len(phone) < 10:
            raise forms.ValidationError('Enter a valid phone number (at least 10 digits).')
        return phone

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if len(address) < 5:
            raise forms.ValidationError('Address must be at least 5 characters.')
        return address