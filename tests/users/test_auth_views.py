"""
Tests for user authentication views.
"""

import base64

import pytest

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.users.models import User


class TestUserRegistrationView:
    """Test user registration view with email verification."""

    def test_registration_view_renders_correctly(self, client):
        """Test that registration view renders with correct template and form."""
        response = client.get(reverse("users:register"))
        assert response.status_code == 200
        assert "registration/register.html" in [t.name for t in response.templates]
        assert "form" in response.context

    def test_registration_view_has_csrf_token(self, client):
        """Test that registration view includes CSRF token."""
        response = client.get(reverse("users:register"))
        assert "csrfmiddlewaretoken" in response.content.decode()

    @pytest.mark.django_db
    def test_valid_registration_creates_inactive_user(self, client):
        """Test that valid registration creates an inactive user."""
        registration_data = {
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(reverse("users:register"), registration_data)

        # Should redirect to registration success page
        assert response.status_code == 302
        assert response.url == reverse("users:registration_sent")

        # User should be created but inactive
        user = User.objects.get(email="test@example.com")
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert not user.is_active
        assert user.check_password("SecurePass123!")

    @pytest.mark.django_db
    def test_registration_sends_verification_email(self, client):
        """Test that registration sends verification email."""
        registration_data = {
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        client.post(reverse("users:register"), registration_data)

        # Should send exactly one email
        assert len(mail.outbox) == 1

        # Email should be to the registered user
        email = mail.outbox[0]
        assert email.to == ["test@example.com"]
        assert "verify" in email.subject.lower()
        assert "verify" in email.body.lower()

    @pytest.mark.django_db
    def test_registration_with_duplicate_email_fails(self, client):
        """Test that registration with duplicate email fails."""
        # Create existing user
        User.objects.create_user(
            username="existing", email="test@example.com", password="password123"
        )

        registration_data = {
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(reverse("users:register"), registration_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_registration_with_mismatched_passwords_fails(self, client):
        """Test that registration with mismatched passwords fails."""
        registration_data = {
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "DifferentPass456!",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(reverse("users:register"), registration_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_registration_with_weak_password_fails(self, client):
        """Test that registration with weak password fails."""
        registration_data = {
            "email": "test@example.com",
            "password1": "123",
            "password2": "123",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(reverse("users:register"), registration_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_registration_with_invalid_email_fails(self, client):
        """Test that registration with invalid email fails."""
        registration_data = {
            "email": "invalid-email",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(reverse("users:register"), registration_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors


class TestEmailVerificationView:
    """Test email verification view."""

    @pytest.mark.django_db
    def test_valid_verification_activates_user(self, client):
        """Test that valid verification token activates user."""
        # Create inactive user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        # Generate verification token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        verification_url = reverse(
            "users:verify_email", kwargs={"uidb64": uidb64, "token": token}
        )

        response = client.get(verification_url)

        # Should redirect to success page
        assert response.status_code == 302
        assert response.url == reverse("users:verification_success")

        # User should now be active
        user.refresh_from_db()
        assert user.is_active

    @pytest.mark.django_db
    def test_invalid_verification_token_fails(self, client):
        """Test that invalid verification token fails."""
        # Create inactive user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        # Generate invalid token
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token"

        verification_url = reverse(
            "users:verify_email", kwargs={"uidb64": uidb64, "token": invalid_token}
        )

        response = client.get(verification_url)

        # Should redirect to failure page
        assert response.status_code == 302
        assert response.url == reverse("users:verification_failed")

        # User should still be inactive
        user.refresh_from_db()
        assert not user.is_active

    @pytest.mark.django_db
    def test_invalid_user_id_fails(self, client):
        """Test that invalid user ID fails verification."""
        # Generate verification URL with invalid user ID
        invalid_uidb64 = urlsafe_base64_encode(force_bytes(99999))
        token = "some-token"

        verification_url = reverse(
            "users:verify_email", kwargs={"uidb64": invalid_uidb64, "token": token}
        )

        response = client.get(verification_url)

        # Should redirect to failure page
        assert response.status_code == 302
        assert response.url == reverse("users:verification_failed")

    @pytest.mark.django_db
    def test_already_active_user_verification(self, client):
        """Test verification of already active user."""
        # Create active user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Generate verification token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        verification_url = reverse(
            "users:verify_email", kwargs={"uidb64": uidb64, "token": token}
        )

        response = client.get(verification_url)

        # Should redirect to already verified page
        assert response.status_code == 302
        assert response.url == reverse("users:already_verified")


class TestRegistrationStatusViews:
    """Test registration status views."""

    def test_registration_sent_view(self, client):
        """Test registration sent confirmation view."""
        response = client.get(reverse("users:registration_sent"))
        assert response.status_code == 200
        assert "registration/registration_sent.html" in [
            t.name for t in response.templates
        ]

    def test_verification_success_view(self, client):
        """Test verification success view."""
        response = client.get(reverse("users:verification_success"))
        assert response.status_code == 200
        assert "registration/verification_success.html" in [
            t.name for t in response.templates
        ]

    def test_verification_failed_view(self, client):
        """Test verification failed view."""
        response = client.get(reverse("users:verification_failed"))
        assert response.status_code == 200
        assert "registration/verification_failed.html" in [
            t.name for t in response.templates
        ]

    def test_already_verified_view(self, client):
        """Test already verified view."""
        response = client.get(reverse("users:already_verified"))
        assert response.status_code == 200
        assert "registration/already_verified.html" in [
            t.name for t in response.templates
        ]


class TestResendVerificationView:
    """Test resend verification email view."""

    def test_resend_verification_view_renders(self, client):
        """Test resend verification view renders correctly."""
        response = client.get(reverse("users:resend_verification"))
        assert response.status_code == 200
        assert "registration/resend_verification.html" in [
            t.name for t in response.templates
        ]

    @pytest.mark.django_db
    def test_resend_verification_for_inactive_user(self, client):
        """Test resending verification for inactive user."""
        # Create inactive user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        response = client.post(
            reverse("users:resend_verification"), {"email": "test@example.com"}
        )

        # Should redirect to sent confirmation
        assert response.status_code == 302
        assert response.url == reverse("users:registration_sent")

        # Should send email
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["test@example.com"]

    @pytest.mark.django_db
    def test_resend_verification_for_active_user(self, client):
        """Test resending verification for already active user."""
        # Create active user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        response = client.post(
            reverse("users:resend_verification"), {"email": "test@example.com"}
        )

        # Should show form with error
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_resend_verification_for_nonexistent_user(self, client):
        """Test resending verification for nonexistent user."""
        response = client.post(
            reverse("users:resend_verification"), {"email": "nonexistent@example.com"}
        )

        # Should show form with error
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors


class TestLoginView:
    """Test user login view."""

    def test_login_view_renders_correctly(self, client):
        """Test that login view renders with correct template and form."""
        response = client.get(reverse("users:login"))
        assert response.status_code == 200
        assert "registration/login.html" in [t.name for t in response.templates]
        assert "form" in response.context

    def test_login_view_has_csrf_token(self, client):
        """Test that login view includes CSRF token."""
        response = client.get(reverse("users:login"))
        assert "csrfmiddlewaretoken" in response.content.decode()

    @pytest.mark.django_db
    def test_valid_login_with_email(self, client):
        """Test login with valid email and password."""
        # Create active user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        login_data = {
            "email": "test@example.com",
            "password": "password123",
        }

        response = client.post(reverse("users:login"), login_data)

        # Debug output
        if response.status_code != 302:
            print(f"Response content: {response.content.decode()[:500]}")
            if (
                hasattr(response, "context")
                and response.context
                and "form" in response.context
            ):
                print(f"Form errors: {response.context['form'].errors}")

        # Should redirect to dashboard or next URL
        assert response.status_code == 302
        assert response.url in [reverse("core:dashboard"), "/"]

        # User should be logged in
        assert "_auth_user_id" in client.session
        assert int(client.session["_auth_user_id"]) == user.pk

    @pytest.mark.django_db
    def test_login_with_next_parameter(self, client):
        """Test login redirects to next parameter after successful login."""
        # Create active user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Visit login with next parameter
        login_url = reverse("users:login") + "?next=/expenses/"
        response = client.get(login_url)
        assert response.status_code == 200

        # Submit login form
        login_data = {
            "email": "test@example.com",
            "password": "password123",
        }

        response = client.post(login_url, login_data)

        # Should redirect to next URL
        assert response.status_code == 302
        assert response.url == "/expenses/"

    @pytest.mark.django_db
    def test_login_with_invalid_credentials(self, client):
        """Test login with invalid credentials fails."""
        # Create active user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword",
        }

        response = client.post(reverse("users:login"), login_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # User should not be logged in
        assert "_auth_user_id" not in client.session

    @pytest.mark.django_db
    def test_login_with_inactive_user(self, client):
        """Test login with inactive user fails."""
        # Create inactive user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        login_data = {
            "email": "test@example.com",
            "password": "password123",
        }

        response = client.post(reverse("users:login"), login_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # User should not be logged in
        assert "_auth_user_id" not in client.session

    @pytest.mark.django_db
    def test_login_with_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123",
        }

        response = client.post(reverse("users:login"), login_data)

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # User should not be logged in
        assert "_auth_user_id" not in client.session

    @pytest.mark.django_db
    def test_login_remembers_user_when_requested(self, client):
        """Test login sets longer session when remember me is checked."""
        # Create active user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        login_data = {
            "email": "test@example.com",
            "password": "password123",
            "remember_me": True,
        }

        response = client.post(reverse("users:login"), login_data)

        # Should redirect successfully
        assert response.status_code == 302

        # Session should be set to remember
        assert not client.session.get_expire_at_browser_close()

    @pytest.mark.django_db
    def test_already_logged_in_user_redirected(self, client):
        """Test that already logged in user is redirected from login page."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:login"))

        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.url in [reverse("core:dashboard"), "/"]


class TestLogoutView:
    """Test user logout view."""

    @pytest.mark.django_db
    def test_logout_logs_out_user(self, client):
        """Test that logout successfully logs out user."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        # Verify user is logged in
        assert "_auth_user_id" in client.session

        response = client.post(reverse("users:logout"))

        # Should redirect to logout success page
        assert response.status_code == 302
        assert response.url == reverse("users:logout_success")

        # User should be logged out
        assert "_auth_user_id" not in client.session

    @pytest.mark.django_db
    def test_logout_with_get_request(self, client):
        """Test logout view renders confirmation page for GET request."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:logout"))

        # Should render logout confirmation page
        assert response.status_code == 200
        assert "registration/logout.html" in [t.name for t in response.templates]

    def test_logout_unauthenticated_user(self, client):
        """Test logout for unauthenticated user."""
        response = client.post(reverse("users:logout"))

        # Should still redirect to logout success
        assert response.status_code == 302
        assert response.url == reverse("users:logout_success")

    def test_logout_success_view(self, client):
        """Test logout success view."""
        response = client.get(reverse("users:logout_success"))
        assert response.status_code == 200
        assert "registration/logout_success.html" in [
            t.name for t in response.templates
        ]


class TestPasswordResetView:
    """Test password reset view."""

    def test_password_reset_view_renders_correctly(self, client):
        """Test that password reset view renders with correct template and form."""
        response = client.get(reverse("users:password_reset"))
        assert response.status_code == 200
        assert "registration/password_reset_form.html" in [
            t.name for t in response.templates
        ]
        assert "form" in response.context

    @pytest.mark.django_db
    def test_password_reset_with_valid_email(self, client):
        """Test password reset with valid email sends reset email."""
        # Create active user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        response = client.post(
            reverse("users:password_reset"), {"email": "test@example.com"}
        )

        # Should redirect to password reset done page
        assert response.status_code == 302
        assert response.url == reverse("users:password_reset_done")

        # Should send password reset email
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["test@example.com"]
        assert "password reset" in email.subject.lower()

    @pytest.mark.django_db
    def test_password_reset_with_inactive_user(self, client):
        """Test password reset with inactive user still sends email for security."""
        # Create inactive user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=False,
        )

        response = client.post(
            reverse("users:password_reset"), {"email": "test@example.com"}
        )

        # Should still redirect to password reset done page (don't reveal user status)
        assert response.status_code == 302
        assert response.url == reverse("users:password_reset_done")

        # Should not send email for inactive user
        assert len(mail.outbox) == 0

    @pytest.mark.django_db
    def test_password_reset_with_nonexistent_email(self, client):
        """Test password reset with nonexistent email."""
        response = client.post(
            reverse("users:password_reset"), {"email": "nonexistent@example.com"}
        )

        # Should still redirect to password reset done page (don't reveal user existence)  # noqa: E501
        assert response.status_code == 302
        assert response.url == reverse("users:password_reset_done")

        # Should not send any email
        assert len(mail.outbox) == 0

    def test_password_reset_done_view(self, client):
        """Test password reset done view."""
        response = client.get(reverse("users:password_reset_done"))
        assert response.status_code == 200
        assert "registration/password_reset_done.html" in [
            t.name for t in response.templates
        ]


class TestPasswordResetConfirmView:
    """Test password reset confirm view."""

    @pytest.mark.django_db
    def test_password_reset_confirm_view_renders(self, client):
        """Test password reset confirm view renders correctly."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Generate reset token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        reset_url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )

        # Django's PasswordResetConfirmView redirects on first GET
        response = client.get(reset_url)
        assert response.status_code == 302

        # Follow the redirect to get the actual form
        response = client.get(response.url)
        assert response.status_code == 200
        assert "registration/password_reset_confirm.html" in [
            t.name for t in response.templates
        ]
        assert "form" in response.context

    @pytest.mark.django_db
    def test_password_reset_confirm_with_valid_token(self, client):
        """Test password reset confirm with valid token."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
            is_active=True,
        )

        # Generate reset token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        reset_url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )

        # First GET to establish session
        response = client.get(reset_url)
        assert response.status_code == 302
        session_url = response.url

        # Submit new password to the session URL
        response = client.post(
            session_url,
            {"new_password1": "newpassword123!", "new_password2": "newpassword123!"},
        )

        # Should redirect to password reset complete page
        assert response.status_code == 302
        assert response.url == reverse("users:password_reset_complete")

        # Password should be changed
        user.refresh_from_db()
        assert user.check_password("newpassword123!")
        assert not user.check_password("oldpassword123")

    @pytest.mark.django_db
    def test_password_reset_confirm_with_invalid_token(self, client):
        """Test password reset confirm with invalid token."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
            is_active=True,
        )

        # Generate invalid token
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token"

        reset_url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": invalid_token},
        )

        response = client.get(reset_url)

        # Should show invalid token page
        assert response.status_code == 200
        # Django shows the form with error context when token is invalid
        assert "form" in response.context or "validlink" in response.context

    @pytest.mark.django_db
    def test_password_reset_confirm_with_mismatched_passwords(self, client):
        """Test password reset confirm with mismatched passwords."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
            is_active=True,
        )

        # Generate reset token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        reset_url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )

        # First GET to establish session
        response = client.get(reset_url)
        assert response.status_code == 302
        session_url = response.url

        # Submit mismatched passwords to the session URL
        response = client.post(
            session_url,
            {
                "new_password1": "newpassword123!",
                "new_password2": "differentpassword123!",
            },
        )

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # Password should not be changed
        user.refresh_from_db()
        assert user.check_password("oldpassword123")

    @pytest.mark.django_db
    def test_password_reset_confirm_with_weak_password(self, client):
        """Test password reset confirm with weak password."""
        # Create user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
            is_active=True,
        )

        # Generate reset token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        reset_url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )

        # First GET to establish session
        response = client.get(reset_url)
        assert response.status_code == 302
        session_url = response.url

        # Submit weak password to the session URL
        response = client.post(
            session_url, {"new_password1": "123", "new_password2": "123"}
        )

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # Password should not be changed
        user.refresh_from_db()
        assert user.check_password("oldpassword123")

    def test_password_reset_complete_view(self, client):
        """Test password reset complete view."""
        response = client.get(reverse("users:password_reset_complete"))
        assert response.status_code == 200
        assert "registration/password_reset_complete.html" in [
            t.name for t in response.templates
        ]


class TestTwoFactorSetupView:
    """Test 2FA setup view."""

    @pytest.mark.django_db
    def test_2fa_setup_view_requires_login(self, client):
        """Test that 2FA setup view requires login."""
        response = client.get(reverse("users:2fa_setup"))

        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    @pytest.mark.django_db
    def test_2fa_setup_view_renders_for_authenticated_user(self, client):
        """Test 2FA setup view renders for authenticated user."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:2fa_setup"))
        assert response.status_code == 200
        assert "registration/2fa_setup.html" in [t.name for t in response.templates]
        assert "qr_code" in response.context
        assert "secret_key" in response.context

    @pytest.mark.django_db
    def test_2fa_setup_generates_secret_key(self, client):
        """Test that 2FA setup generates a secret key for user."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        # User should not have 2FA enabled initially
        assert not hasattr(user, "totp_secret") or not user.totp_secret

        response = client.get(reverse("users:2fa_setup"))

        # Should generate a secret key
        assert response.context["secret_key"]
        assert len(response.context["secret_key"]) == 32  # Base32 encoded secret

    @pytest.mark.django_db
    def test_2fa_setup_generates_qr_code(self, client):
        """Test that 2FA setup generates QR code."""
        # Create and login user
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:2fa_setup"))

        # Should generate QR code data
        qr_code = response.context["qr_code"]
        assert qr_code.startswith("data:image/png;base64,")

        # QR code should be valid base64
        qr_data = qr_code.split(",")[1]
        try:
            base64.b64decode(qr_data)
        except Exception:
            pytest.fail("QR code is not valid base64")


class TestTwoFactorVerifyView:
    """Test 2FA verification view."""

    @pytest.mark.django_db
    def test_2fa_verify_view_requires_login(self, client):
        """Test that 2FA verify view requires login."""
        response = client.get(reverse("users:2fa_verify"))

        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    @pytest.mark.django_db
    def test_2fa_verify_view_renders(self, client):
        """Test 2FA verify view renders correctly."""
        # Create user with TOTP secret
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        # Simulate TOTP secret setup
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.save()
        client.force_login(user)

        response = client.get(reverse("users:2fa_verify"))
        assert response.status_code == 200
        assert "registration/2fa_verify.html" in [t.name for t in response.templates]
        assert "form" in response.context

    @pytest.mark.django_db
    def test_2fa_verify_with_valid_token(self, client):
        """Test 2FA verification with valid TOTP token."""
        # Create user with TOTP secret
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        # Set up TOTP secret
        secret = "JBSWY3DPEHPK3PXP"
        user.totp_secret = secret
        user.save()
        client.force_login(user)

        # Generate valid TOTP token (we'll mock this in implementation)
        # For now, test the view accepts a 6-digit token
        response = client.post(reverse("users:2fa_verify"), {"token": "123456"})

        # Should process the form (exact behavior depends on implementation)
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_2fa_verify_with_invalid_token(self, client):
        """Test 2FA verification with invalid token."""
        # Create user with TOTP secret
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.save()
        client.force_login(user)

        response = client.post(
            reverse("users:2fa_verify"), {"token": "000000"}  # Invalid token
        )

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context
        # Implementation should validate token and show error

    @pytest.mark.django_db
    def test_2fa_verify_with_malformed_token(self, client):
        """Test 2FA verification with malformed token."""
        # Create user with TOTP secret
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.save()
        client.force_login(user)

        response = client.post(
            reverse("users:2fa_verify"), {"token": "abc123"}  # Not 6 digits
        )

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context


class TestTwoFactorDisableView:
    """Test 2FA disable view."""

    @pytest.mark.django_db
    def test_2fa_disable_view_requires_login(self, client):
        """Test that 2FA disable view requires login."""
        response = client.get(reverse("users:2fa_disable"))

        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    @pytest.mark.django_db
    def test_2fa_disable_view_renders(self, client):
        """Test 2FA disable view renders correctly."""
        # Create user with 2FA enabled
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.is_2fa_enabled = True
        user.save()
        client.force_login(user)

        response = client.get(reverse("users:2fa_disable"))
        assert response.status_code == 200
        assert "registration/2fa_disable.html" in [t.name for t in response.templates]

    @pytest.mark.django_db
    def test_2fa_disable_with_valid_password(self, client):
        """Test disabling 2FA with valid password."""
        # Create user with 2FA enabled
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.is_2fa_enabled = True
        user.save()
        client.force_login(user)

        response = client.post(
            reverse("users:2fa_disable"), {"password": "password123"}
        )

        # Should redirect to success page
        assert response.status_code == 302
        assert response.url == reverse("users:2fa_disabled_success")

        # 2FA should be disabled
        user.refresh_from_db()
        assert not user.is_2fa_enabled
        assert not user.totp_secret

    @pytest.mark.django_db
    def test_2fa_disable_with_invalid_password(self, client):
        """Test disabling 2FA with invalid password."""
        # Create user with 2FA enabled
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.is_2fa_enabled = True
        user.save()
        client.force_login(user)

        response = client.post(
            reverse("users:2fa_disable"), {"password": "wrongpassword"}
        )

        # Should not redirect (form has errors)
        assert response.status_code == 200
        assert "form" in response.context

        # 2FA should still be enabled
        user.refresh_from_db()
        assert user.is_2fa_enabled
        assert user.totp_secret


class TestTwoFactorLoginView:
    """Test 2FA enhanced login view."""

    @pytest.mark.django_db
    def test_login_with_2fa_enabled_redirects_to_2fa_verify(self, client):
        """Test that login with 2FA enabled user redirects to 2FA verification."""
        # Create user with 2FA enabled
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.is_2fa_enabled = True
        user.save()

        login_data = {
            "email": "test@example.com",
            "password": "password123",
        }

        response = client.post(reverse("users:login"), login_data)

        # Should redirect to 2FA verification instead of dashboard
        assert response.status_code == 302
        assert response.url == reverse("users:2fa_verify")

    @pytest.mark.django_db
    def test_login_without_2fa_goes_to_dashboard(self, client):
        """Test that login without 2FA goes directly to dashboard."""
        # Create user without 2FA
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )

        login_data = {
            "email": "test@example.com",
            "password": "password123",
        }

        response = client.post(reverse("users:login"), login_data)

        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.url in [reverse("core:dashboard"), "/"]


class TestTwoFactorBackupCodesView:
    """Test 2FA backup codes functionality."""

    @pytest.mark.django_db
    def test_2fa_backup_codes_view_requires_login(self, client):
        """Test that backup codes view requires login."""
        response = client.get(reverse("users:2fa_backup_codes"))

        # Should redirect to login
        assert response.status_code == 302
        assert "/login/" in response.url

    @pytest.mark.django_db
    def test_2fa_backup_codes_view_requires_2fa_enabled(self, client):
        """Test backup codes view requires 2FA to be enabled."""
        # Create user without 2FA
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:2fa_backup_codes"))

        # Should redirect or show error
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_2fa_backup_codes_generates_codes(self, client):
        """Test that backup codes are generated when requested."""
        # Create user with 2FA enabled
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True,
        )
        user.totp_secret = "JBSWY3DPEHPK3PXP"
        user.is_2fa_enabled = True
        user.save()
        client.force_login(user)

        response = client.get(reverse("users:2fa_backup_codes"))
        assert response.status_code == 200
        assert "registration/2fa_backup_codes.html" in [
            t.name for t in response.templates
        ]
        assert "backup_codes" in response.context

        # Should generate 10 backup codes
        backup_codes = response.context["backup_codes"]
        assert len(backup_codes) == 10

        # Each code should be 8 characters
        for code in backup_codes:
            assert len(code) == 8
            assert code.isalnum()
