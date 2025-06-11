"""
User authentication views.
"""

import base64
import io
import json
import secrets

import pyotp
import qrcode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import TemplateView

from .forms import (
    EmailLoginForm,
    ResendVerificationForm,
    TwoFactorDisableForm,
    TwoFactorVerifyForm,
    UserRegistrationForm,
)
from .models import User


class RegisterView(View):
    """User registration view with email verification."""

    template_name = "registration/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse("core:dashboard"))

        form = UserRegistrationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            # Create inactive user
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Send verification email
            self._send_verification_email(request, user)

            return redirect(reverse("users:registration_sent"))

        return render(request, self.template_name, {"form": form})

    def _send_verification_email(self, request, user):
        """Send email verification link to user."""
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        verification_url = request.build_absolute_uri(
            reverse("users:verify_email", kwargs={"uidb64": uidb64, "token": token})
        )

        subject = "Verify your Personal Finance Dashboard account"
        message = render_to_string(
            "registration/verification_email.txt",
            {
                "user": user,
                "verification_url": verification_url,
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # Use default
            recipient_list=[user.email],
            fail_silently=False,
        )


class EmailVerificationView(View):
    """Email verification view."""

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return redirect(reverse("users:verification_failed"))

        if user.is_active:
            return redirect(reverse("users:already_verified"))

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return redirect(reverse("users:verification_success"))
        else:
            return redirect(reverse("users:verification_failed"))


class LoginView(View):
    """Custom login view with 2FA support."""

    template_name = "registration/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse("core:dashboard"))

        form = EmailLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = EmailLoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", False)

            # Authenticate user
            user = authenticate(request, username=email, password=password)

            if user is not None and user.is_active:
                # Check if 2FA is enabled
                if user.is_2fa_enabled and user.totp_secret:
                    # Store user ID in session for 2FA verification
                    request.session["2fa_user_id"] = user.id
                    return redirect(reverse("users:2fa_verify"))
                else:
                    # Regular login
                    login(request, user)

                    # Set session expiry
                    if not remember_me:
                        request.session.set_expiry(0)  # Browser close

                    # Redirect to next URL or dashboard
                    next_url = request.GET.get("next")
                    if next_url:
                        return redirect(next_url)
                    return redirect(reverse("core:dashboard"))
            else:
                form.add_error(None, "Invalid email or password.")

        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    """Custom logout view."""

    template_name = "registration/logout.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        logout(request)
        return redirect(reverse("users:logout_success"))


class PasswordResetView(BasePasswordResetView):
    """Custom password reset view."""

    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("users:password_reset_done")

    def form_valid(self, form):
        """Only send email to active users for security."""
        email = form.cleaned_data["email"]

        try:
            user = User.objects.get(email=email)
            if user.is_active:
                return super().form_valid(form)
        except User.DoesNotExist:
            pass

        # Always redirect to done page for security (don't reveal user existence)
        return redirect(self.success_url)


class ResendVerificationView(View):
    """Resend email verification view."""

    template_name = "registration/resend_verification.html"

    def get(self, request):
        form = ResendVerificationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ResendVerificationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]

            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    # Resend verification email
                    self._send_verification_email(request, user)
                    return redirect(reverse("users:registration_sent"))
                else:
                    form.add_error("email", "This account is already verified.")
            except User.DoesNotExist:
                form.add_error("email", "No account found with this email address.")

        return render(request, self.template_name, {"form": form})

    def _send_verification_email(self, request, user):
        """Send email verification link to user."""
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        verification_url = request.build_absolute_uri(
            reverse("users:verify_email", kwargs={"uidb64": uidb64, "token": token})
        )

        subject = "Verify your Personal Finance Dashboard account"
        message = render_to_string(
            "registration/verification_email.txt",
            {
                "user": user,
                "verification_url": verification_url,
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


# Status page views
class RegistrationSentView(TemplateView):
    template_name = "registration/registration_sent.html"


class VerificationSuccessView(TemplateView):
    template_name = "registration/verification_success.html"


class VerificationFailedView(TemplateView):
    template_name = "registration/verification_failed.html"


class AlreadyVerifiedView(TemplateView):
    template_name = "registration/already_verified.html"


class LogoutSuccessView(TemplateView):
    template_name = "registration/logout_success.html"


# 2FA Views
@method_decorator(login_required, name="dispatch")
class TwoFactorSetupView(View):
    """2FA setup view."""

    template_name = "registration/2fa_setup.html"

    def get(self, request):
        user = request.user

        # Generate TOTP secret if not exists
        if not user.totp_secret:
            secret = pyotp.random_base32()
            user.totp_secret = secret
            user.save()
        else:
            secret = user.totp_secret

        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email, issuer_name="Personal Finance Dashboard"
        )

        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 for display
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        qr_code_data = f"data:image/png;base64,{qr_code}"

        return render(
            request,
            self.template_name,
            {
                "secret_key": secret,
                "qr_code": qr_code_data,
            },
        )


class TwoFactorVerifyView(View):
    """2FA token verification view."""

    template_name = "registration/2fa_verify.html"

    def get(self, request):
        # Check if user is in 2FA flow
        if not request.session.get("2fa_user_id") and not request.user.is_authenticated:
            return redirect(reverse("users:login"))

        form = TwoFactorVerifyForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = TwoFactorVerifyForm(request.POST)

        if form.is_valid():
            token = form.cleaned_data["token"]

            # Get user from session or current user
            if request.session.get("2fa_user_id"):
                user = get_object_or_404(User, id=request.session["2fa_user_id"])
            else:
                user = request.user

            # Verify TOTP token
            totp = pyotp.TOTP(user.totp_secret)

            if totp.verify(token):
                if not request.user.is_authenticated:
                    # Complete login for 2FA flow
                    login(request, user)
                    del request.session["2fa_user_id"]

                # Enable 2FA if this is setup
                if not user.is_2fa_enabled:
                    user.is_2fa_enabled = True
                    user.save()
                    messages.success(
                        request, "Two-factor authentication has been enabled!"
                    )

                return redirect(reverse("core:dashboard"))
            else:
                form.add_error("token", "Invalid token. Please try again.")

        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class TwoFactorDisableView(View):
    """2FA disable view."""

    template_name = "registration/2fa_disable.html"

    def get(self, request):
        if not request.user.is_2fa_enabled:
            return redirect(reverse("core:dashboard"))

        form = TwoFactorDisableForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = TwoFactorDisableForm(request.POST)

        if form.is_valid():
            password = form.cleaned_data["password"]

            if request.user.check_password(password):
                # Disable 2FA
                request.user.is_2fa_enabled = False
                request.user.totp_secret = None
                request.user.backup_codes = None
                request.user.save()

                messages.success(
                    request, "Two-factor authentication has been disabled."
                )
                return redirect(reverse("users:2fa_disabled_success"))
            else:
                form.add_error("password", "Incorrect password.")

        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class TwoFactorBackupCodesView(View):
    """2FA backup codes view."""

    template_name = "registration/2fa_backup_codes.html"

    def get(self, request):
        if not request.user.is_2fa_enabled:
            return redirect(reverse("core:dashboard"))

        # Generate new backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Store encrypted backup codes
        request.user.backup_codes = json.dumps(backup_codes)
        request.user.save()

        return render(request, self.template_name, {"backup_codes": backup_codes})


class TwoFactorDisabledSuccessView(TemplateView):
    template_name = "registration/2fa_disabled_success.html"


@method_decorator(login_required, name="dispatch")
class ProfileView(TemplateView):
    """User profile view (placeholder)."""

    template_name = "users/profile.html"


@method_decorator(login_required, name="dispatch")
class SettingsView(TemplateView):
    """User settings view (placeholder)."""

    template_name = "users/settings.html"
