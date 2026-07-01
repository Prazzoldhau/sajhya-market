from django import forms
from .models import BookingRequest, PhysioProfile, PhysioAvailability


class BookingForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = [
            'patient_name', 'patient_contact', 'patient_email',
            'condition', 'preferred_date', 'preferred_time',
            'booking_type', 'address',
        ]
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
            'condition': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['patient_name'].widget.attrs['placeholder'] = 'Your full name'
        self.fields['patient_contact'].widget.attrs['placeholder'] = 'Phone number'
        self.fields['patient_email'].widget.attrs['placeholder'] = 'Email (optional)'
        self.fields['condition'].widget.attrs['placeholder'] = 'Describe your condition or reason for visit'
        self.fields['address'].widget.attrs['placeholder'] = 'Home address (required for home visit)'


class PhysioProfileForm(forms.ModelForm):
    class Meta:
        model = PhysioProfile
        fields = [
            'bio', 'photo', 'experience_years', 'location',
            'consultation_fee', 'home_visit_fee', 'platform_fee',
            'travel_cost', 'specializations',
            'is_home_visit', 'is_clinic_visit', 'is_public',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'specializations': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_fields = [
            'bio', 'experience_years', 'location',
            'consultation_fee', 'home_visit_fee', 'platform_fee', 'travel_cost',
        ]
        for f in text_fields:
            self.fields[f].widget.attrs.setdefault('class', 'form-control')


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = PhysioAvailability
        fields = ['day_of_week', 'start_time', 'end_time', 'is_home']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
        }
