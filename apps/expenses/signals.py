"""
Signals for the expenses app.
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category

User = get_user_model()


@receiver(post_save, sender=User)
def create_default_categories_for_new_user(sender, instance, created, **kwargs):
    """
    Create default categories when a new user is created.

    This signal is triggered after a User is saved. If the user was just
    created (not updated), we create the default category structure for them.
    """
    if created:
        # Create default categories for the new user
        Category.create_default_categories(instance)
