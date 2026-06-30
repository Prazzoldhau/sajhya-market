from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    
    phone = forms.CharField(
        max_length=15, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class':'form_control',
            'placeholder':'phone number',
        })
    )
    license_number = forms.CharField(
        max_length=20, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class':'form_control',
            'placeholder':'license number',
        })
    )
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields+('phone', 'license_number', 'email', 'first_name', 'last_name')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes or custom styling
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label
            
class CustomUserChangeForm(UserChangeForm):
    """
    A form for updating users.
    """
    class Meta:
        model = User
        fields = ('username', 'license_number', 'email', 'first_name', 'last_name', 'phone', 'is_active', 'is_staff')