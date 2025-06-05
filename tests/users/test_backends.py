"""
Tests for authentication backends.
"""

import pytest

from django.contrib.auth import authenticate

from apps.users.models import User


class TestEmailBackend:
    """Test email authentication backend."""

    @pytest.mark.django_db
    def test_authenticate_with_email_and_password(self):
        """Test authentication with email and password."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Test authentication
        authenticated_user = authenticate(
            username="test@example.com", password="password123"
        )

        assert authenticated_user is not None
        assert authenticated_user == user

    @pytest.mark.django_db
    def test_authenticate_with_wrong_password(self):
        """Test authentication with wrong password fails."""
        # Create user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Test authentication with wrong password
        authenticated_user = authenticate(
            username="test@example.com", password="wrongpassword"
        )

        assert authenticated_user is None

    @pytest.mark.django_db
    def test_authenticate_with_nonexistent_user(self):
        """Test authentication with nonexistent user fails."""
        authenticated_user = authenticate(
            username="nonexistent@example.com", password="password123"
        )

        assert authenticated_user is None

    @pytest.mark.django_db
    def test_authenticate_with_inactive_user(self):
        """Test authentication with inactive user fails."""
        # Create inactive user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        authenticated_user = authenticate(
            username="test@example.com", password="password123"
        )

        assert authenticated_user is None
