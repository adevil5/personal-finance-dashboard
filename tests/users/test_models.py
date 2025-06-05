"""
Tests for user models.
"""

import pytest

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from apps.core.security.fields import EncryptedPhoneField


class TestUserModel:
    """Test the custom User model with encrypted fields."""

    def test_user_model_extends_abstract_user(self):
        """Test that User model extends Django's AbstractUser."""
        from apps.users.models import User

        assert issubclass(User, models.Model)
        assert hasattr(User, "username")
        assert hasattr(User, "email")
        assert hasattr(User, "first_name")
        assert hasattr(User, "last_name")

    def test_user_has_encrypted_phone_field(self):
        """Test that User model has an encrypted phone field."""
        from apps.users.models import User

        phone_field = User._meta.get_field("phone")
        assert isinstance(phone_field, EncryptedPhoneField)
        assert (
            phone_field.max_length >= 150
        )  # Should be large enough for encrypted data
        assert phone_field.blank is True
        assert phone_field.null is True

    def test_user_has_timezone_field(self):
        """Test that User model has a timezone field."""
        from apps.users.models import User

        timezone_field = User._meta.get_field("timezone")
        assert isinstance(timezone_field, models.CharField)
        assert timezone_field.max_length == 50
        assert timezone_field.default == "UTC"

    def test_user_has_currency_field(self):
        """Test that User model has a currency field."""
        from apps.users.models import User

        currency_field = User._meta.get_field("currency")
        assert isinstance(currency_field, models.CharField)
        assert currency_field.max_length == 3
        assert currency_field.default == "USD"

    def test_currency_choices(self):
        """Test that currency field has proper choices."""
        from apps.users.models import User

        currency_field = User._meta.get_field("currency")
        choices = dict(currency_field.choices)
        assert "USD" in choices
        assert "EUR" in choices
        assert "GBP" in choices
        assert "JPY" in choices
        assert "CAD" in choices
        assert "AUD" in choices

    @pytest.mark.django_db
    def test_user_creation_with_encrypted_phone(self):
        """Test creating a user with an encrypted phone number."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            phone="+1-555-123-4567",
        )

        # Phone should be accessible as plain text
        assert user.phone == "15551234567"  # Normalized format

        # Reload from database to ensure encryption
        user_from_db = User.objects.get(pk=user.pk)
        assert user_from_db.phone == "15551234567"

        # Check that the value is encrypted in the database
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT phone FROM users_user WHERE id = %s", [user.id])
            encrypted_phone = cursor.fetchone()[0]
            # Encrypted value should be different from plain text
            assert encrypted_phone != "15551234567"
            assert encrypted_phone is not None
            assert len(encrypted_phone) > 20  # Encrypted data is longer

    @pytest.mark.django_db
    def test_user_creation_without_phone(self):
        """Test creating a user without a phone number."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )
        assert user.phone is None

    @pytest.mark.django_db
    def test_user_creation_with_timezone_and_currency(self):
        """Test creating a user with timezone and currency preferences."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser3",
            email="test3@example.com",
            password="testpass123",
            timezone="America/New_York",
            currency="EUR",
        )
        assert user.timezone == "America/New_York"
        assert user.currency == "EUR"

    @pytest.mark.django_db
    def test_user_default_timezone_and_currency(self):
        """Test that users have default timezone and currency."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser4", email="test4@example.com", password="testpass123"
        )
        assert user.timezone == "UTC"
        assert user.currency == "USD"

    @pytest.mark.django_db
    def test_invalid_phone_number_validation(self):
        """Test that invalid phone numbers are rejected."""
        from apps.users.models import User

        user = User(
            username="testuser5", email="test5@example.com", phone="123"  # Too short
        )
        with pytest.raises(ValidationError) as exc_info:
            user.full_clean()
        assert "phone" in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_phone_normalization(self):
        """Test that phone numbers are normalized before encryption."""
        from apps.users.models import User

        test_cases = [
            ("+1 (555) 123-4567", "15551234567"),
            ("555-123-4567", "5551234567"),
            ("+44 20 7946 0958", "442079460958"),
            ("(123) 456-7890", "1234567890"),
        ]

        for input_phone, expected_normalized in test_cases:
            user = User.objects.create_user(
                username=f"user_{expected_normalized}",
                email=f"{expected_normalized}@example.com",
                password="testpass123",
                phone=input_phone,
            )
            assert user.phone == expected_normalized

    @pytest.mark.django_db
    def test_user_str_representation(self):
        """Test the string representation of the User model."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser6",
            email="test6@example.com",
            first_name="John",
            last_name="Doe",
        )
        assert str(user) == "testuser6"

    @pytest.mark.django_db
    def test_user_get_full_name(self):
        """Test getting the full name of a user."""
        from apps.users.models import User

        user = User.objects.create_user(
            username="testuser7",
            email="test7@example.com",
            first_name="Jane",
            last_name="Smith",
        )
        assert user.get_full_name() == "Jane Smith"

    def test_get_user_model_returns_custom_user(self):
        """Test that get_user_model returns our custom User model."""
        from apps.users.models import User

        assert get_user_model() == User

    @pytest.mark.django_db
    def test_currency_validation(self):
        """Test that only valid currency codes are accepted."""
        from apps.users.models import User

        user = User(
            username="testuser8",
            email="test8@example.com",
            currency="XXX",  # Invalid currency code
        )
        with pytest.raises(ValidationError) as exc_info:
            user.full_clean()
        assert "currency" in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_timezone_validation(self):
        """Test timezone validation."""
        from apps.users.models import User

        # Valid timezone
        user = User.objects.create_user(
            username="testuser9",
            email="test9@example.com",
            password="testpass123",
            timezone="Europe/London",
        )
        assert user.timezone == "Europe/London"

        # Invalid timezone should raise validation error
        user2 = User(
            username="testuser10",
            email="test10@example.com",
            timezone="Invalid/Timezone",
        )
        with pytest.raises(ValidationError) as exc_info:
            user2.full_clean()
        assert "timezone" in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_multiple_users_with_different_phones(self):
        """Test that multiple users can have different encrypted phone numbers."""
        from apps.users.models import User

        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            phone="5551111111",
        )

        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            phone="5552222222",
        )

        assert user1.phone == "5551111111"
        assert user2.phone == "5552222222"
        assert user1.phone != user2.phone


# Keep existing test case for compatibility
User = get_user_model()


class UserModelTestCase(TestCase):
    """Test case for User model."""

    def test_user_creation(self):
        """Test user creation."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))


class TestUserProfileModel:
    """Test the UserProfile model with encrypted fields."""

    def test_user_profile_model_fields(self):
        """Test that UserProfile model has all required fields."""
        from apps.users.models import UserProfile

        assert hasattr(UserProfile, "user")
        assert hasattr(UserProfile, "monthly_income")
        assert hasattr(UserProfile, "financial_goals")
        assert hasattr(UserProfile, "created_at")
        assert hasattr(UserProfile, "updated_at")

    def test_user_profile_has_encrypted_monthly_income(self):
        """Test that UserProfile has encrypted monthly_income field."""
        from apps.core.security.fields import EncryptedDecimalField
        from apps.users.models import UserProfile

        monthly_income_field = UserProfile._meta.get_field("monthly_income")
        assert isinstance(monthly_income_field, EncryptedDecimalField)
        assert monthly_income_field.null is True
        assert monthly_income_field.blank is True

    def test_user_profile_has_encrypted_goals(self):
        """Test that UserProfile has encrypted financial_goals field."""
        from apps.core.security.fields import EncryptedTextField
        from apps.users.models import UserProfile

        goals_field = UserProfile._meta.get_field("financial_goals")
        assert isinstance(goals_field, EncryptedTextField)
        assert goals_field.null is True
        assert goals_field.blank is True

    def test_user_profile_one_to_one_relationship(self):
        """Test that UserProfile has one-to-one relationship with User."""
        from django.db import models

        from apps.users.models import UserProfile

        user_field = UserProfile._meta.get_field("user")
        assert isinstance(user_field, models.OneToOneField)
        assert user_field.related_model._meta.label == "users.User"
        assert user_field.remote_field.on_delete == models.CASCADE

    @pytest.mark.django_db
    def test_user_profile_creation(self):
        """Test creating a UserProfile with encrypted fields."""
        from decimal import Decimal

        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(
            user=user,
            monthly_income=Decimal("5000.50"),
            financial_goals="Save for house down payment and emergency fund",
        )

        assert profile.user == user
        assert profile.monthly_income == Decimal("5000.50")
        assert (
            profile.financial_goals == "Save for house down payment and emergency fund"
        )

    @pytest.mark.django_db
    def test_user_profile_encryption_in_database(self):
        """Test that UserProfile fields are encrypted in the database."""
        from decimal import Decimal

        from django.db import connection

        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(
            user=user,
            monthly_income=Decimal("7500.25"),
            financial_goals="Retire early and travel the world",
        )

        # Check encryption in database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT monthly_income, financial_goals FROM users_userprofile "
                "WHERE id = %s",
                [profile.id],
            )
            encrypted_income, encrypted_goals = cursor.fetchone()

            # Values should be encrypted (different from plain text)
            assert encrypted_income != "7500.25"
            assert encrypted_goals != "Retire early and travel the world"
            assert encrypted_income is not None
            assert encrypted_goals is not None

    @pytest.mark.django_db
    def test_user_profile_creation_without_optional_fields(self):
        """Test creating a UserProfile without optional fields."""
        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser3", email="test3@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(user=user)
        assert profile.user == user
        assert profile.monthly_income is None
        assert profile.financial_goals is None

    @pytest.mark.django_db
    def test_user_profile_update(self):
        """Test updating UserProfile fields."""
        from decimal import Decimal

        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser4", email="test4@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(
            user=user, monthly_income=Decimal("3000.00")
        )

        # Update the profile
        profile.monthly_income = Decimal("3500.00")
        profile.financial_goals = "Buy a new car"
        profile.save()

        # Reload from database
        updated_profile = UserProfile.objects.get(pk=profile.pk)
        assert updated_profile.monthly_income == Decimal("3500.00")
        assert updated_profile.financial_goals == "Buy a new car"

    @pytest.mark.django_db
    def test_user_profile_str_representation(self):
        """Test the string representation of UserProfile."""
        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser5", email="test5@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(user=user)
        assert str(profile) == "Profile for testuser5"

    @pytest.mark.django_db
    def test_user_profile_timestamps(self):
        """Test that UserProfile has created_at and updated_at timestamps."""
        import time

        from django.utils import timezone

        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser6", email="test6@example.com", password="testpass123"
        )

        before_creation = timezone.now()
        profile = UserProfile.objects.create(user=user)
        after_creation = timezone.now()

        assert before_creation <= profile.created_at <= after_creation
        assert before_creation <= profile.updated_at <= after_creation

        # Test that updated_at changes on save
        time.sleep(0.1)  # Ensure some time passes
        original_updated_at = profile.updated_at
        profile.financial_goals = "New goal"
        profile.save()

        assert profile.updated_at > original_updated_at

    @pytest.mark.django_db
    def test_user_profile_cascade_delete(self):
        """Test that UserProfile is deleted when User is deleted."""
        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser7", email="test7@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(user=user)
        profile_id = profile.id

        # Delete the user
        user.delete()

        # Profile should be deleted too
        assert not UserProfile.objects.filter(id=profile_id).exists()

    @pytest.mark.django_db
    def test_user_profile_related_name(self):
        """Test accessing UserProfile from User instance."""
        from apps.users.models import User, UserProfile

        user = User.objects.create_user(
            username="testuser8", email="test8@example.com", password="testpass123"
        )

        profile = UserProfile.objects.create(user=user)

        # Should be able to access profile from user
        assert user.profile == profile

    def test_user_profile_verbose_names(self):
        """Test UserProfile model verbose names."""
        from apps.users.models import UserProfile

        assert UserProfile._meta.verbose_name == "User Profile"
        assert UserProfile._meta.verbose_name_plural == "User Profiles"
