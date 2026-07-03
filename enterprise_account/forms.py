from django import forms
from .models import Enterprise, Department


class EnterpriseForm(forms.ModelForm):
    class Meta:
        model = Enterprise
        fields = ['enterprise_name', 'registration_number', 'address', 'phone', 'email']
        widgets = {
            'enterprise_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enterprise name'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registration / PAN number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact email'}),
        }

    def clean_enterprise_name(self):
        name = self.cleaned_data.get('enterprise_name')
        if len(name) < 2:
            raise forms.ValidationError('Enterprise name must be at least 2 characters long.')
        return name

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


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name']
        widgets = {
            'department_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department name'}),
        }

    def clean_department_name(self):
        name = self.cleaned_data.get('department_name')
        if len(name) < 2:
            raise forms.ValidationError('Department name must be at least 2 characters long.')
        return name
