import pytz

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.security.fields import (
    EncryptedDecimalField,
    EncryptedPhoneField,
    EncryptedTextField,
)

# Currency choices for user preferences
CURRENCY_CHOICES = [
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
    ("JPY", "Japanese Yen"),
    ("CAD", "Canadian Dollar"),
    ("AUD", "Australian Dollar"),
    ("CHF", "Swiss Franc"),
    ("CNY", "Chinese Yuan"),
    ("SEK", "Swedish Krona"),
    ("NZD", "New Zealand Dollar"),
]


def validate_timezone(value):
    """Validate that the timezone is a valid pytz timezone."""
    if value not in pytz.all_timezones:
        raise ValidationError(f"{value} is not a valid timezone")


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    Adds encrypted phone field and user preferences for timezone and currency.
    """

    # Encrypted phone number field
    phone = EncryptedPhoneField(
        blank=True, null=True, help_text="User's phone number (encrypted)"
    )

    # User preferences
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        validators=[validate_timezone],
        help_text="User's preferred timezone",
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text="User's preferred currency",
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "User"
        verbose_name_plural = "Users"


class UserProfile(models.Model):
    """
    User Profile model with encrypted PII fields for financial data.

    Stores sensitive financial information like monthly income and goals
    using field-level encryption.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="User this profile belongs to",
    )

    # Encrypted financial data fields
    monthly_income = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="User's monthly income (encrypted)",
    )

    financial_goals = EncryptedTextField(
        blank=True,
        null=True,
        help_text="User's financial goals and objectives (encrypted)",
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this profile was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this profile was last updated"
    )

    class Meta:
        db_table = "users_userprofile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        """Return string representation of the profile."""
        return f"Profile for {self.user.username}"
