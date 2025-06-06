"""
Factory classes for creating test data.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False


class AdminUserFactory(UserFactory):
    """Factory for creating admin User instances."""

    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class CategoryFactory(DjangoModelFactory):
    """Factory for creating Category instances."""

    class Meta:
        model = "expenses.Category"

    name = factory.Faker("word")
    user = factory.SubFactory(UserFactory)
    color = factory.Faker("hex_color")
    icon = factory.Faker("word")
    is_active = True


class TransactionFactory(DjangoModelFactory):
    """Factory for creating Transaction instances."""

    class Meta:
        model = "expenses.Transaction"

    user = factory.SubFactory(UserFactory)
    transaction_type = "expense"  # Default to expense
    amount = factory.LazyFunction(lambda: Decimal("25.50"))
    category = factory.SubFactory(CategoryFactory)
    description = factory.Faker("sentence", nb_words=4)
    date = factory.LazyFunction(lambda: timezone.now().date())
    merchant = factory.Faker("company")
    is_active = True
