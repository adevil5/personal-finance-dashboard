"""
Testing settings for Personal Finance Dashboard project.
"""

from .base import *  # noqa: F403, F401, F405

# Testing configuration
DEBUG = False
TESTING = True

# Use in-memory SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable cache in tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Media files for testing
MEDIA_ROOT = BASE_DIR / "test_media"

# Static files for testing
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Celery testing settings
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Simplified authentication for tests
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Disable Allauth email verification in tests
ACCOUNT_EMAIL_VERIFICATION = "none"

# PII Encryption key for testing
from cryptography.fernet import Fernet  # noqa: E402

PII_ENCRYPTION_KEY = Fernet.generate_key()

# Logging configuration for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "propagate": False,
        },
        "apps": {
            "handlers": ["null"],
            "propagate": False,
        },
    },
}

# Test-specific settings
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Security settings for tests
SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["*"]

# Disable rate limiting in tests
RATELIMIT_ENABLE = False
