# enterpriseform.py
from django import forms
from django.forms import modelformset_factory
from .models import Enterprise, Ward, PhysioRequest

class EnterpriseForm(forms.ModelForm):
    class Meta:
        model = Enterprise
        fields = ['enterprise_name', 'pan_number', 'address', 'phone']
        # created_by, created_at, updated_at are handled elsewhere

        widgets = {
            'enterprise_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital / Enterprise name'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PAN / Tax number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'}),
        }

    def clean_enterprise_name(self):
        name = self.cleaned_data.get('enterprise_name')
        if len(name) < 2:
            raise forms.ValidationError('Enterprise name must be at least 2 characters long.')
        return name

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number')
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


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['ward_type']
        widgets = {
            'ward_type': forms.Select(attrs={'class': 'form-control'}),
        }


class PhysioRequestForm(forms.ModelForm):
    """One row of the ward's bulk request table (used inside a formset)."""

    class Meta:
        model = PhysioRequest
        fields = ['patient_name', 'bed_number', 'reason', 'urgency']
        widgets = {
            'patient_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Patient name'}),
            'bed_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Bed / room'}),
            'reason': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'urgency': forms.Select(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean_patient_name(self):
        name = self.cleaned_data.get('patient_name')
        if name and len(name) < 2:
            raise forms.ValidationError('Patient name must be at least 2 characters long.')
        return name


PhysioRequestFormSet = modelformset_factory(
    PhysioRequest,
    form=PhysioRequestForm,
    extra=8,
    can_delete=False,
)


class PhysioRequestStatusForm(forms.ModelForm):
    """Physio department's response to a single request -- status +
    an optional message that shows back up on the ward's own table."""

    class Meta:
        model = PhysioRequest
        fields = ['status', 'physio_message']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'physio_message': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Message to ward (optional)'}),
        }
