"""
URL configuration for users app.
"""

from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
)
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    # Registration
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "registration-sent/",
        views.RegistrationSentView.as_view(),
        name="registration_sent",
    ),
    path(
        "verify-email/<uidb64>/<token>/",
        views.EmailVerificationView.as_view(),
        name="verify_email",
    ),
    path(
        "verification-success/",
        views.VerificationSuccessView.as_view(),
        name="verification_success",
    ),
    path(
        "verification-failed/",
        views.VerificationFailedView.as_view(),
        name="verification_failed",
    ),
    path(
        "already-verified/",
        views.AlreadyVerifiedView.as_view(),
        name="already_verified",
    ),
    path(
        "resend-verification/",
        views.ResendVerificationView.as_view(),
        name="resend_verification",
    ),
    # Authentication
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-success/", views.LogoutSuccessView.as_view(), name="logout_success"),
    # Password Reset
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/auth/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Two-Factor Authentication
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa_setup"),
    path("2fa/verify/", views.TwoFactorVerifyView.as_view(), name="2fa_verify"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa_disable"),
    path(
        "2fa/disabled-success/",
        views.TwoFactorDisabledSuccessView.as_view(),
        name="2fa_disabled_success",
    ),
    path(
        "2fa/backup-codes/",
        views.TwoFactorBackupCodesView.as_view(),
        name="2fa_backup_codes",
    ),
    # Profile and Settings (temporary placeholder views)
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
