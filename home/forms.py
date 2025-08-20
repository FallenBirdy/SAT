# forms.py

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile
import re

class RegisterForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Profile
        fields = ['dob']  # only Profile fields go here

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')

        if password != confirm:
            self.add_error('confirm_password', "Passwords do not match.")

        if password and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            self.add_error('password', "Password must contain at least one symbol.")

        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password']
        )

        profile = Profile(user=user, dob=self.cleaned_data['dob'])

        if commit:
            user.save()
            profile.save()

        return profile