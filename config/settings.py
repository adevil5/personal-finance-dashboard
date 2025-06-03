"""
Django settings module that loads the appropriate settings based on environment.
"""

import os

# Determine which settings module to use
ENVIRONMENT = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development")

if ENVIRONMENT == "config.settings.production":
    from .production import *  # noqa
elif ENVIRONMENT == "config.settings.testing":
    from .testing import *  # noqa
else:
    from .development import *  # noqa
