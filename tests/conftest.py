"""
Test configuration for Personal Finance Dashboard.
"""

import pytest

from django.test import TestCase


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Enable database access for all tests.
    """
    pass


@pytest.fixture
def client():
    """
    Django test client.
    """
    from django.test import Client

    return Client()


@pytest.fixture
def user():
    """
    Create a test user using factory.
    """
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def admin_user():
    """
    Create an admin user using factory.
    """
    from tests.factories import AdminUserFactory

    return AdminUserFactory()


@pytest.fixture
def authenticated_client(client, user):
    """
    Authenticated test client.
    """
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """
    Admin authenticated test client.
    """
    client.force_login(admin_user)
    return client


class BaseTestCase(TestCase):
    """
    Base test case with common functionality.
    """

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()
