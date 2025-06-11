"""
Development settings for Personal Finance Dashboard project.
"""

from .base import *  # noqa: F403, F401, F405

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Development-specific installed apps
INSTALLED_APPS += [
    "django_extensions",
]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Django Debug Toolbar (optional)
if DEBUG:
    try:
        import debug_toolbar  # noqa

        INSTALLED_APPS += ["debug_toolbar"]
        MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
        INTERNAL_IPS = ["127.0.0.1", "localhost"]
    except ImportError:
        pass

# Disable SSL redirects in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow all origins for HTMX in development
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Media files handling in development
if DEBUG:
    # Use secure local file storage in development
    DEFAULT_FILE_STORAGE = "apps.expenses.storage.SecureLocalStorage"

# File storage security settings (development defaults)
FILE_RETENTION_DAYS = 365
CLEANUP_BATCH_SIZE = 1000

# Simplified password validation for development
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 4,
        },
    },
]

# Development logging
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"

# Celery development settings
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously in development
CELERY_TASK_EAGER_PROPAGATES = True

# Development database configuration
# By default, uses PostgreSQL from Docker container
# Set USE_SQLITE=true to use SQLite for offline development
if os.environ.get("USE_SQLITE", "").lower() == "true":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    print("Using SQLite database for development")
elif not os.environ.get("DATABASE_URL"):
    # Default to PostgreSQL - expects Docker container running
    # Database settings inherit from base.py which reads from .env
    pass

# PII Encryption key for development (if not set)
if not PII_ENCRYPTION_KEY:
    from cryptography.fernet import Fernet

    PII_ENCRYPTION_KEY = Fernet.generate_key()

# Show all SQL queries in development
if DEBUG:
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
    }
