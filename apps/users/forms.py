"""
User authentication forms.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class UserRegistrationForm(UserCreationForm):
    """User registration form with email verification."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Enter your email address"}
        ),
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "First name"}
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Last name"}
        ),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Create a password"}
        ),
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Confirm your password"}
        ),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field
        if "username" in self.fields:
            del self.fields["username"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]  # Use email as username
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    """Login form using email instead of username."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Enter your email address"}
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Enter your password"}
        )
    )

    remember_me = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"})
    )


class TwoFactorVerifyForm(forms.Form):
    """2FA token verification form."""

    token = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-input text-center",
                "placeholder": "000000",
                "maxlength": "6",
                "pattern": "[0-9]{6}",
                "autocomplete": "one-time-code",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data.get("token")
        if not token.isdigit():
            raise ValidationError("Token must be 6 digits.")
        return token


class TwoFactorDisableForm(forms.Form):
    """Form to disable 2FA with password confirmation."""

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Enter your current password"}
        )
    )


class ResendVerificationForm(forms.Form):
    """Form to resend email verification."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Enter your email address"}
        )
    )
