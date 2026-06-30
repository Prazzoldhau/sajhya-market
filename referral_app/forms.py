from django import forms
from .models import Referral
from django.contrib.auth import get_user_model

User = get_user_model()


class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = [
            'patient_name', 'patient_contact', 'patient_diagnosis',
            'referred_to', 'referred_to_clinic',
            'reason', 'notes',
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Patient full name',
            }),
            'patient_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Patient phone number (optional)',
            }),
            'patient_diagnosis': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Diagnosis / condition',
            }),
            'referred_to': forms.Select(attrs={'class': 'form-select'}),
            'referred_to_clinic': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Why is the patient being referred?',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['referred_to'].queryset = User.objects.all()
        self.fields['referred_to'].empty_label = '— Select physio / user —'
        self.fields['referred_to'].required = False
        self.fields['referred_to_clinic'].required = False
        self.fields['referred_to_clinic'].empty_label = '— No clinic —'
        self.fields['patient_contact'].required = False
