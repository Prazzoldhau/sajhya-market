from django import forms
from .models import BillingEntry, PatientPackage


class BillingEntryForm(forms.ModelForm):
    class Meta:
        model = BillingEntry
        fields = ['entry_date', 'patient_name', 'age', 'sex', 'contact_number', 'service', 'rate', 'payment_mode', 'notes']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'patient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number (optional)'}),
            'service': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Physiotherapy'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount', 'step': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        }

    def clean_patient_name(self):
        name = self.cleaned_data.get('patient_name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Name must be at least 2 characters long.')
        return name

    def clean_rate(self):
        rate = self.cleaned_data.get('rate')
        if rate is not None and rate < 0:
            raise forms.ValidationError('Amount cannot be negative.')
        return rate


class PatientPackageForm(forms.ModelForm):
    class Meta:
        model = PatientPackage
        fields = ['duration', 'total_sessions', 'total_amount', 'start_date', 'notes']
        widgets = {
            'duration': forms.Select(attrs={'class': 'form-control'}),
            'total_sessions': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 8', 'min': 1}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount (NPR)', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional notes'}),
        }

    def clean_total_sessions(self):
        total_sessions = self.cleaned_data.get('total_sessions')
        if total_sessions is not None and total_sessions < 1:
            raise forms.ValidationError('Must cover at least 1 session.')
        return total_sessions

    def clean_total_amount(self):
        total_amount = self.cleaned_data.get('total_amount')
        if total_amount is not None and total_amount < 0:
            raise forms.ValidationError('Amount cannot be negative.')
        return total_amount
