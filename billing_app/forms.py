from django import forms
from .models import BillingEntry, PatientPackage, PackagePayment


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
    # Not a PatientPackage field -- how much the patient is paying right
    # now at booking. Left at 0 (the default), the package is booked
    # fully unpaid; entering the full total_amount here books it as
    # fully paid; anything in between is a partial payment, logged as
    # this package's first PackagePayment so the rest shows as due.
    amount_paid_now = forms.DecimalField(
        required=False, min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
        label='Amount Paid Now',
        help_text='Leave as 0 if nothing is being paid today.',
    )

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

    def clean(self):
        cleaned_data = super().clean()
        amount_paid_now = cleaned_data.get('amount_paid_now') or 0
        total_amount = cleaned_data.get('total_amount')
        if total_amount is not None and amount_paid_now > total_amount:
            self.add_error('amount_paid_now', 'Cannot be more than the total package amount.')
        return cleaned_data


class PackagePaymentForm(forms.ModelForm):
    class Meta:
        model = PackagePayment
        fields = ['amount', 'payment_mode', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'NPR', 'step': '0.01', 'min': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional notes'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than 0.')
        return amount
