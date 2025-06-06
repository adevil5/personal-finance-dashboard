"""
Tests for expense models.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save
from django.test import TestCase
from django.utils import timezone

from apps.expenses.default_categories import DEFAULT_CATEGORIES
from apps.expenses.models import Category, Transaction
from apps.expenses.signals import create_default_categories_for_new_user
from tests.factories import CategoryFactory, UserFactory

User = get_user_model()


class CategoryModelTestCase(TestCase):
    """Test case for Category model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()

    def test_category_creation(self):
        """Test basic category creation."""
        category = Category.objects.create(
            name="Groceries", user=self.user1, color="#FF0000", icon="shopping-cart"
        )

        self.assertEqual(category.name, "Groceries")
        self.assertEqual(category.user, self.user1)
        self.assertEqual(category.color, "#FF0000")
        self.assertEqual(category.icon, "shopping-cart")
        self.assertIsNone(category.parent)
        self.assertTrue(category.is_active)
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)

    def test_category_str_representation(self):
        """Test string representation of category."""
        category = Category.objects.create(name="Transportation", user=self.user1)
        self.assertEqual(str(category), "Transportation")

    def test_hierarchical_categories(self):
        """Test parent-child relationships."""
        parent = Category.objects.create(name="Transportation", user=self.user1)
        child = Category.objects.create(name="Gas", user=self.user1, parent=parent)

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_user_specific_categories(self):
        """Test that categories are user-specific."""
        category1 = Category.objects.create(name="Personal", user=self.user1)
        category2 = Category.objects.create(name="Personal", user=self.user2)

        # Both users can have categories with the same name
        self.assertEqual(category1.name, category2.name)
        self.assertNotEqual(category1.user, category2.user)

    def test_category_tree_operations(self):
        """Test category tree operations."""
        # Create a tree: Food -> Groceries -> Produce
        food = Category.objects.create(name="Food", user=self.user1)
        groceries = Category.objects.create(
            name="Groceries", user=self.user1, parent=food
        )
        produce = Category.objects.create(
            name="Produce", user=self.user1, parent=groceries
        )

        # Test getting children
        self.assertIn(groceries, food.children.all())
        self.assertIn(produce, groceries.children.all())

        # Test getting descendants
        food_descendants = food.get_descendants()
        self.assertIn(groceries, food_descendants)
        self.assertIn(produce, food_descendants)

        # Test getting ancestors
        produce_ancestors = produce.get_ancestors()
        self.assertIn(groceries, produce_ancestors)
        self.assertIn(food, produce_ancestors)

    def test_category_level_calculation(self):
        """Test category level calculation."""
        level0 = Category.objects.create(name="Root", user=self.user1)
        level1 = Category.objects.create(name="Level1", user=self.user1, parent=level0)
        level2 = Category.objects.create(name="Level2", user=self.user1, parent=level1)

        self.assertEqual(level0.get_level(), 0)
        self.assertEqual(level1.get_level(), 1)
        self.assertEqual(level2.get_level(), 2)

    def test_prevent_circular_references(self):
        """Test that circular references are prevented."""
        parent = Category.objects.create(name="Parent", user=self.user1)
        child = Category.objects.create(name="Child", user=self.user1, parent=parent)

        # Try to make parent a child of child (circular reference)
        parent.parent = child
        with self.assertRaises(ValidationError):
            parent.full_clean()

    def test_prevent_self_as_parent(self):
        """Test that a category cannot be its own parent."""
        category = Category.objects.create(name="Test", user=self.user1)
        category.parent = category

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_cross_user_parent_restriction(self):
        """Test that users cannot set categories from other users as parents."""
        user1_category = Category.objects.create(name="User1 Category", user=self.user1)

        # Try to create a category for user2 with user1's category as parent
        user2_category = Category(
            name="User2 Category", user=self.user2, parent=user1_category
        )

        with self.assertRaises(ValidationError):
            user2_category.full_clean()

    def test_get_root_categories(self):
        """Test getting root categories for a user."""
        # Clear existing categories (from signal) to test root functionality
        Category.objects.filter(user=self.user1).delete()
        Category.objects.filter(user=self.user2).delete()

        # Create some categories for user1
        root1 = Category.objects.create(name="Root1", user=self.user1)
        root2 = Category.objects.create(name="Root2", user=self.user1)
        child = Category.objects.create(name="Child", user=self.user1, parent=root1)

        # Create category for user2
        Category.objects.create(name="User2 Root", user=self.user2)

        # Get root categories for user1
        user1_roots = Category.get_root_categories(self.user1)

        self.assertIn(root1, user1_roots)
        self.assertIn(root2, user1_roots)
        self.assertNotIn(child, user1_roots)  # Not a root
        self.assertEqual(user1_roots.count(), 2)  # Only user1's roots

    def test_get_category_tree(self):
        """Test getting the complete category tree for a user."""
        # Create a tree structure
        food = Category.objects.create(name="Food", user=self.user1)
        groceries = Category.objects.create(
            name="Groceries", user=self.user1, parent=food
        )
        Category.objects.create(name="Produce", user=self.user1, parent=groceries)

        transport = Category.objects.create(name="Transport", user=self.user1)
        Category.objects.create(name="Gas", user=self.user1, parent=transport)

        # Create category for another user (should not be included)
        Category.objects.create(name="Other User Category", user=self.user2)

        tree = Category.get_category_tree(self.user1)
        user1_categories = [cat.name for cat in tree]

        self.assertIn("Food", user1_categories)
        self.assertIn("Groceries", user1_categories)
        self.assertIn("Produce", user1_categories)
        self.assertIn("Transport", user1_categories)
        self.assertIn("Gas", user1_categories)
        self.assertNotIn("Other User Category", user1_categories)

    def test_color_field_validation(self):
        """Test color field accepts valid hex colors."""
        # Valid hex colors
        valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFF", "#000"]

        for color in valid_colors:
            category = Category(name=f"Test {color}", user=self.user1, color=color)
            # Should not raise validation error
            category.full_clean()

    def test_icon_field(self):
        """Test icon field functionality."""
        category = Category.objects.create(
            name="Test Icon", user=self.user1, icon="home"
        )
        self.assertEqual(category.icon, "home")

    def test_category_ordering(self):
        """Test that categories are ordered by name by default."""
        # Clear existing categories (from signal) to test ordering
        Category.objects.filter(user=self.user1).delete()

        Category.objects.create(name="Zebra", user=self.user1)
        Category.objects.create(name="Alpha", user=self.user1)
        Category.objects.create(name="Beta", user=self.user1)

        categories = list(Category.objects.filter(user=self.user1))
        names = [cat.name for cat in categories]

        self.assertEqual(names, ["Alpha", "Beta", "Zebra"])

    def test_soft_delete_functionality(self):
        """Test that categories can be soft deleted."""
        category = Category.objects.create(name="To Delete", user=self.user1)

        # Soft delete
        category.is_active = False
        category.save()

        # Should still exist in database but be inactive
        self.assertFalse(category.is_active)

        # Test that active categories don't include soft deleted ones
        active_categories = Category.objects.filter(user=self.user1, is_active=True)
        self.assertNotIn(category, active_categories)


class DefaultCategoriesTestCase(TestCase):
    """Test case for default category functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()

    def test_default_categories_structure(self):
        """Test that DEFAULT_CATEGORIES has the correct structure."""
        self.assertIsInstance(DEFAULT_CATEGORIES, list)
        self.assertGreater(len(DEFAULT_CATEGORIES), 0)

        # Test structure of first category
        first_category = DEFAULT_CATEGORIES[0]
        self.assertIn("name", first_category)
        self.assertIn("color", first_category)
        self.assertIn("icon", first_category)
        self.assertIn("children", first_category)

        # Test child structure
        if first_category["children"]:
            first_child = first_category["children"][0]
            self.assertIn("name", first_child)
            self.assertIn("color", first_child)
            self.assertIn("icon", first_child)

    def test_create_default_categories_for_user(self):
        """Test creating default categories for a user."""
        # Temporarily disconnect the signal to test manual creation
        post_save.disconnect(create_default_categories_for_new_user, sender=User)

        try:
            # Create a user without triggering the signal
            test_user = User.objects.create_user(
                username="testuser_manual",
                email="manual@example.com",
                password="testpass123",
            )

            # Before creation, user should have no categories
            self.assertEqual(Category.objects.filter(user=test_user).count(), 0)

            # Create default categories
            Category.create_default_categories(test_user)

            # Check that categories were created
            categories = Category.objects.filter(user=test_user)
            self.assertGreater(categories.count(), 0)

            # Check that we have the expected number of root categories
            root_categories = Category.objects.filter(user=test_user, parent=None)
            expected_root_count = len(DEFAULT_CATEGORIES)
            self.assertEqual(root_categories.count(), expected_root_count)

        finally:
            # Reconnect the signal
            post_save.connect(create_default_categories_for_new_user, sender=User)

    def test_default_categories_hierarchy(self):
        """Test that default categories are created with correct hierarchy."""
        Category.create_default_categories(self.user)

        # Test a specific category hierarchy
        food_category = Category.objects.get(
            user=self.user, name="Food & Dining", parent=None
        )
        groceries_category = Category.objects.get(
            user=self.user, name="Groceries", parent=food_category
        )

        # Verify parent-child relationship
        self.assertEqual(groceries_category.parent, food_category)
        self.assertIn(groceries_category, food_category.children.all())

    def test_default_categories_colors_and_icons(self):
        """Test that default categories have correct colors and icons."""
        Category.create_default_categories(self.user)

        # Test specific category
        food_category = Category.objects.get(user=self.user, name="Food & Dining")

        # Find the expected data
        expected_data = next(
            (cat for cat in DEFAULT_CATEGORIES if cat["name"] == "Food & Dining"), None
        )
        self.assertIsNotNone(expected_data)

        self.assertEqual(food_category.color, expected_data["color"])
        self.assertEqual(food_category.icon, expected_data["icon"])

    def test_default_categories_user_isolation(self):
        """Test that default categories are user-specific."""
        user2 = UserFactory()

        # Create default categories for both users
        Category.create_default_categories(self.user)
        Category.create_default_categories(user2)

        # Check that each user has their own categories
        user1_categories = Category.objects.filter(user=self.user)
        user2_categories = Category.objects.filter(user=user2)

        self.assertGreater(user1_categories.count(), 0)
        self.assertGreater(user2_categories.count(), 0)

        # Ensure no overlap
        user1_ids = set(user1_categories.values_list("id", flat=True))
        user2_ids = set(user2_categories.values_list("id", flat=True))
        self.assertEqual(len(user1_ids.intersection(user2_ids)), 0)

    def test_create_default_categories_idempotent(self):
        """Test creating default categories multiple times doesn't create duplicates."""
        # Create default categories twice
        Category.create_default_categories(self.user)
        initial_count = Category.objects.filter(user=self.user).count()

        Category.create_default_categories(self.user)
        final_count = Category.objects.filter(user=self.user).count()

        # Should have same count
        self.assertEqual(initial_count, final_count)

    def test_all_default_categories_created(self):
        """Test that all categories from DEFAULT_CATEGORIES are created."""
        Category.create_default_categories(self.user)

        # Check each root category
        for category_data in DEFAULT_CATEGORIES:
            root_category = Category.objects.get(
                user=self.user, name=category_data["name"], parent=None
            )
            self.assertEqual(root_category.color, category_data["color"])
            self.assertEqual(root_category.icon, category_data["icon"])

            # Check children
            for child_data in category_data["children"]:
                child_category = Category.objects.get(
                    user=self.user, name=child_data["name"], parent=root_category
                )
                self.assertEqual(child_category.color, child_data["color"])
                self.assertEqual(child_category.icon, child_data["icon"])

    def test_new_user_gets_default_categories(self):
        """Test that new users automatically get default categories."""
        # Create a new user - signal should automatically create default categories
        new_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Check if default categories were created
        categories = Category.objects.filter(user=new_user)
        expected_count = sum(1 + len(cat["children"]) for cat in DEFAULT_CATEGORIES)

        # Signal should have created default categories
        self.assertEqual(categories.count(), expected_count)

    @patch("apps.expenses.models.Category.create_default_categories")
    def test_create_default_categories_called_on_user_creation(
        self, mock_create_defaults
    ):
        """Test that create_default_categories is called when a user is created."""
        # This test verifies the signal is working
        User.objects.create_user(
            username="signaltest", email="signal@example.com", password="testpass123"
        )

        # Should be called once for the new user
        mock_create_defaults.assert_called_once()


class TransactionModelTestCase(TestCase):
    """Test case for Transaction model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        # Create categories for testing
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")
        self.category2 = CategoryFactory(user=self.user1, name="Transportation")
        self.category_user2 = CategoryFactory(user=self.user2, name="User2 Category")

    def test_transaction_creation_expense(self):
        """Test basic expense transaction creation."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("25.50"),
            category=self.category1,
            description="Grocery shopping",
            date=timezone.now().date(),
            merchant="Local Store",
        )

        self.assertEqual(transaction.user, self.user1)
        self.assertEqual(transaction.transaction_type, Transaction.EXPENSE)
        self.assertEqual(transaction.amount, Decimal("25.50"))
        self.assertEqual(transaction.category, self.category1)
        self.assertEqual(transaction.description, "Grocery shopping")
        self.assertEqual(transaction.merchant, "Local Store")
        self.assertIsNotNone(transaction.date)
        self.assertTrue(transaction.is_active)
        self.assertIsNotNone(transaction.created_at)
        self.assertIsNotNone(transaction.updated_at)

    def test_transaction_creation_income(self):
        """Test basic income transaction creation."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.INCOME,
            amount=Decimal("1500.00"),
            description="Salary payment",
            date=timezone.now().date(),
        )

        self.assertEqual(transaction.transaction_type, Transaction.INCOME)
        self.assertEqual(transaction.amount, Decimal("1500.00"))
        self.assertIsNone(transaction.category)  # Income doesn't require category

    def test_transaction_creation_transfer(self):
        """Test basic transfer transaction creation."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.TRANSFER,
            amount=Decimal("100.00"),
            description="Savings transfer",
            date=timezone.now().date(),
        )

        self.assertEqual(transaction.transaction_type, Transaction.TRANSFER)
        self.assertEqual(transaction.amount, Decimal("100.00"))

    def test_transaction_str_representation(self):
        """Test string representation of transaction."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Test transaction",
            date=timezone.now().date(),
        )

        expected_str = (
            f"{transaction.get_transaction_type_display()} - $50.00 - Test transaction"
        )
        self.assertEqual(str(transaction), expected_str)

    def test_encrypted_amount_field(self):
        """Test that amount field is encrypted in database."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("123.45"),
            category=self.category1,
            description="Test encryption",
            date=timezone.now().date(),
        )

        # Verify the amount is correctly stored and retrieved
        self.assertEqual(transaction.amount, Decimal("123.45"))

        # Verify that the raw database value is encrypted (not the actual decimal)
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT amount FROM expenses_transaction WHERE id = %s",
                [transaction.id],
            )
            raw_value = cursor.fetchone()[0]
            self.assertNotEqual(raw_value, "123.45")
            self.assertIsInstance(raw_value, str)  # Encrypted values are strings

    def test_encrypted_notes_field(self):
        """Test that notes field is encrypted in database."""
        notes_text = "Sensitive information about transaction"
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Test transaction",
            notes=notes_text,
            date=timezone.now().date(),
        )

        # Verify the notes are correctly stored and retrieved
        self.assertEqual(transaction.notes, notes_text)

        # Verify that the raw database value is encrypted
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT notes FROM expenses_transaction WHERE id = %s", [transaction.id]
            )
            raw_value = cursor.fetchone()[0]
            self.assertNotEqual(raw_value, notes_text)
            self.assertIsInstance(raw_value, str)

    def test_encrypted_merchant_field(self):
        """Test that merchant field is encrypted in database."""
        merchant_name = "Sensitive Merchant Name"
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("75.00"),
            category=self.category1,
            description="Test transaction",
            merchant=merchant_name,
            date=timezone.now().date(),
        )

        # Verify the merchant is correctly stored and retrieved
        self.assertEqual(transaction.merchant, merchant_name)

        # Verify that the raw database value is encrypted
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT merchant FROM expenses_transaction WHERE id = %s",
                [transaction.id],
            )
            raw_value = cursor.fetchone()[0]
            self.assertNotEqual(raw_value, merchant_name)
            self.assertIsInstance(raw_value, str)

    def test_user_data_isolation(self):
        """Test that users can only access their own transactions."""
        transaction1 = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category1,
            description="User 1 transaction",
            date=timezone.now().date(),
        )

        transaction2 = Transaction.objects.create(
            user=self.user2,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            category=self.category_user2,
            description="User 2 transaction",
            date=timezone.now().date(),
        )

        # Verify user1 transactions
        user1_transactions = Transaction.objects.filter(user=self.user1)
        self.assertIn(transaction1, user1_transactions)
        self.assertNotIn(transaction2, user1_transactions)

        # Verify user2 transactions
        user2_transactions = Transaction.objects.filter(user=self.user2)
        self.assertIn(transaction2, user2_transactions)
        self.assertNotIn(transaction1, user2_transactions)

    def test_amount_validation_positive(self):
        """Test that amount must be positive for all transaction types."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("-50.00"),
                category=self.category1,
                description="Invalid negative amount",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_amount_validation_zero(self):
        """Test that amount cannot be zero."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("0.00"),
                category=self.category1,
                description="Invalid zero amount",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_expense_requires_category(self):
        """Test that expense transactions require a category."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                description="Expense without category",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_income_category_optional(self):
        """Test that income transactions can have optional category."""
        # Income without category should be valid
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.INCOME,
            amount=Decimal("1000.00"),
            description="Salary",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

        # Income with category should also be valid
        transaction_with_category = Transaction(
            user=self.user1,
            transaction_type=Transaction.INCOME,
            amount=Decimal("500.00"),
            category=self.category1,
            description="Freelance income",
            date=timezone.now().date(),
        )
        transaction_with_category.full_clean()  # Should not raise ValidationError

    def test_transfer_category_optional(self):
        """Test that transfer transactions can have optional category."""
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.TRANSFER,
            amount=Decimal("200.00"),
            description="Account transfer",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_cross_user_category_restriction(self):
        """Test that users cannot assign categories from other users."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category_user2,  # Category belongs to user2
                description="Invalid category assignment",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_date_validation_future_date(self):
        """Test validation for future dates."""
        from datetime import date, timedelta

        future_date = date.today() + timedelta(days=1)

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Future transaction",
                date=future_date,
            )
            transaction.full_clean()

    def test_date_validation_valid_dates(self):
        """Test validation for valid dates (today and past)."""
        from datetime import date, timedelta

        # Today should be valid
        today_transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Today transaction",
            date=date.today(),
        )
        today_transaction.full_clean()  # Should not raise ValidationError

        # Past date should be valid
        past_date = date.today() - timedelta(days=30)
        past_transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Past transaction",
            date=past_date,
        )
        past_transaction.full_clean()  # Should not raise ValidationError

    def test_receipt_file_upload(self):
        """Test receipt file handling."""
        # Create a simple test file
        test_file = SimpleUploadedFile(
            "receipt.txt", b"Test receipt content", content_type="text/plain"
        )

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Transaction with receipt",
            date=timezone.now().date(),
            receipt=test_file,
        )

        self.assertIsNotNone(transaction.receipt)
        # The upload_to function modifies the path, so just check that the file
        # exists and has some content based on our upload_to pattern:
        # receipts/{user_id}/{filename}. Django may add random suffixes to
        # avoid filename conflicts
        self.assertTrue(transaction.receipt.name)
        self.assertIn(str(self.user1.id), transaction.receipt.name)
        self.assertIn("receipt", transaction.receipt.name)
        self.assertTrue(transaction.receipt.name.endswith(".txt"))

    def test_receipt_file_optional(self):
        """Test that receipt file is optional."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Transaction without receipt",
            date=timezone.now().date(),
        )

        self.assertFalse(transaction.receipt)  # Should be falsy (empty)

    def test_transaction_ordering(self):
        """Test that transactions are ordered by date (newest first) by default."""
        from datetime import date, timedelta

        # Create transactions with different dates
        old_transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category1,
            description="Old transaction",
            date=date.today() - timedelta(days=2),
        )

        new_transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            category=self.category1,
            description="New transaction",
            date=date.today(),
        )

        middle_transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            category=self.category1,
            description="Middle transaction",
            date=date.today() - timedelta(days=1),
        )

        # Get all transactions for user1
        transactions = list(Transaction.objects.filter(user=self.user1))

        # Should be ordered by date descending (newest first)
        self.assertEqual(transactions[0], new_transaction)
        self.assertEqual(transactions[1], middle_transaction)
        self.assertEqual(transactions[2], old_transaction)

    def test_soft_delete_functionality(self):
        """Test that transactions can be soft deleted."""
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="To be deleted",
            date=timezone.now().date(),
        )

        # Soft delete
        transaction.is_active = False
        transaction.save()

        # Should still exist in database but be inactive
        self.assertFalse(transaction.is_active)

        # Test that active transactions don't include soft deleted ones
        active_transactions = Transaction.objects.filter(
            user=self.user1, is_active=True
        )
        self.assertNotIn(transaction, active_transactions)

    def test_transaction_type_choices(self):
        """Test that transaction type choices are correctly defined."""
        # Test all valid transaction types can be created
        expense = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Expense",
            date=timezone.now().date(),
        )

        income = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.INCOME,
            amount=Decimal("1000.00"),
            description="Income",
            date=timezone.now().date(),
        )

        transfer = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.TRANSFER,
            amount=Decimal("200.00"),
            description="Transfer",
            date=timezone.now().date(),
        )

        self.assertEqual(expense.get_transaction_type_display(), "Expense")
        self.assertEqual(income.get_transaction_type_display(), "Income")
        self.assertEqual(transfer.get_transaction_type_display(), "Transfer")

    def test_transaction_meta_properties(self):
        """Test transaction model meta properties."""
        Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Test meta",
            date=timezone.now().date(),
        )

        meta = Transaction._meta
        self.assertEqual(meta.db_table, "expenses_transaction")
        self.assertEqual(meta.verbose_name, "Transaction")
        self.assertEqual(meta.verbose_name_plural, "Transactions")

    def test_amount_decimal_precision(self):
        """Test that amount field handles decimal precision correctly."""
        # Test valid decimal amounts
        valid_amounts = [
            Decimal("0.01"),  # Minimum amount
            Decimal("9999.99"),  # Large amount
            Decimal("123.45"),  # Exactly 2 decimal places
        ]

        for amount in valid_amounts:
            transaction = Transaction.objects.create(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=amount,
                category=self.category1,
                description=f"Test amount {amount}",
                date=timezone.now().date(),
            )

            # Verify amount is stored correctly
            saved_transaction = Transaction.objects.get(id=transaction.id)
            self.assertEqual(saved_transaction.amount, amount)

        # Test invalid decimal amount (too many decimal places)
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("123.456"),  # 3 decimal places should fail
                category=self.category1,
                description="Invalid precision",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_transaction_unicode_handling(self):
        """Test that transaction handles unicode characters in text fields."""
        unicode_text = "Test with émojis 🛒 and special characters: café, naïve, résumé"

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description=unicode_text,
            notes=unicode_text,
            merchant=unicode_text,
            date=timezone.now().date(),
        )

        # Verify unicode text is stored and retrieved correctly
        saved_transaction = Transaction.objects.get(id=transaction.id)
        self.assertEqual(saved_transaction.description, unicode_text)
        self.assertEqual(saved_transaction.notes, unicode_text)
        self.assertEqual(saved_transaction.merchant, unicode_text)


class TransactionValidationEdgeCasesTestCase(TestCase):
    """Test case for Transaction model validation edge cases (Task 2.1.2)."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")
        self.category_user2 = CategoryFactory(user=self.user2, name="User2 Category")

    def test_amount_validation_extremely_small_values(self):
        """Test validation with extremely small positive amounts."""
        # Test minimum valid amount (0.01)
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("0.01"),
            category=self.category1,
            description="Minimum amount",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_amount_validation_large_values(self):
        """Test validation with large amounts within field limits."""
        # Test large valid amount (8 digits before decimal)
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("99999999.99"),
            category=self.category1,
            description="Large amount",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_amount_validation_string_values(self):
        """Test validation rejects string values for amount."""
        with self.assertRaises((ValidationError, TypeError, ValueError)):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount="not_a_number",
                category=self.category1,
                description="String amount",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_date_validation_none_value(self):
        """Test validation when date is None."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="None date",
                date=None,
            )
            transaction.full_clean()

    def test_date_validation_far_past_date(self):
        """Test validation allows dates far in the past."""
        from datetime import date

        # Test a date 100 years ago
        old_date = date(1920, 1, 1)
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Very old transaction",
            date=old_date,
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_date_validation_year_boundary(self):
        """Test validation around year boundaries."""
        from datetime import date

        # Test December 31st of current year
        dec_31 = date(timezone.now().year, 12, 31)
        if dec_31 <= date.today():
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Year end transaction",
                date=dec_31,
            )
            transaction.full_clean()  # Should not raise ValidationError

    def test_user_isolation_category_validation_detailed(self):
        """Test detailed user isolation validation for categories."""
        # Create multiple categories for different users
        user1_category1 = CategoryFactory(user=self.user1, name="User1 Cat1")
        user2_category1 = CategoryFactory(user=self.user2, name="User2 Cat1")

        # Valid: User1 transaction with User1 category
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=user1_category1,
            description="Valid user1 transaction",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

        # Invalid: User1 transaction with User2 category
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=user2_category1,
                description="Invalid cross-user transaction",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_category_validation_inactive_category(self):
        """Test validation with inactive (soft-deleted) categories."""
        # Create an inactive category
        inactive_category = CategoryFactory(
            user=self.user1, name="Inactive", is_active=False
        )

        # Transaction should still be valid with inactive category
        # (business rule: don't prevent using inactive categories for
        # existing transactions)
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=inactive_category,
            description="Transaction with inactive category",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_transaction_type_validation_required(self):
        """Test that transaction_type is required."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=None,
                amount=Decimal("50.00"),
                category=self.category1,
                description="No transaction type",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_transaction_type_validation_invalid_choice(self):
        """Test validation rejects invalid transaction types."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type="invalid_type",
                amount=Decimal("50.00"),
                category=self.category1,
                description="Invalid transaction type",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_description_validation_required(self):
        """Test that description field is required."""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="",  # Empty description
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_description_validation_max_length(self):
        """Test description field max length validation."""
        # Create a description that exceeds 255 characters
        long_description = "x" * 256

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description=long_description,
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_category_validation_cross_user_child_category(self):
        """Test validation prevents using child categories from other users."""
        # Create parent and child categories for user2
        parent_cat = CategoryFactory(user=self.user2, name="Parent")
        child_cat = CategoryFactory(user=self.user2, name="Child", parent=parent_cat)

        # User1 should not be able to use user2's child category
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=child_cat,
                description="Cross-user child category",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_amount_validation_different_transaction_types(self):
        """Test amount validation applies to all transaction types."""
        transaction_types = [
            Transaction.EXPENSE,
            Transaction.INCOME,
            Transaction.TRANSFER,
        ]

        for trans_type in transaction_types:
            # Test negative amount fails for all types
            with self.assertRaises(ValidationError):
                transaction = Transaction(
                    user=self.user1,
                    transaction_type=trans_type,
                    amount=Decimal("-50.00"),
                    category=self.category1
                    if trans_type == Transaction.EXPENSE
                    else None,
                    description=f"Negative {trans_type}",
                    date=timezone.now().date(),
                )
                transaction.full_clean()

            # Test zero amount fails for all types
            with self.assertRaises(ValidationError):
                transaction = Transaction(
                    user=self.user1,
                    transaction_type=trans_type,
                    amount=Decimal("0.00"),
                    category=self.category1
                    if trans_type == Transaction.EXPENSE
                    else None,
                    description=f"Zero {trans_type}",
                    date=timezone.now().date(),
                )
                transaction.full_clean()

    def test_category_requirement_edge_cases(self):
        """Test category requirement edge cases for different transaction types."""
        # Income with category should be valid
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.INCOME,
            amount=Decimal("1000.00"),
            category=self.category1,
            description="Income with category",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

        # Transfer with category should be valid
        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.TRANSFER,
            amount=Decimal("500.00"),
            category=self.category1,
            description="Transfer with category",
            date=timezone.now().date(),
        )
        transaction.full_clean()  # Should not raise ValidationError

        # Expense without category should fail
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=None,
                description="Expense without category",
                date=timezone.now().date(),
            )
            transaction.full_clean()

    def test_validation_with_all_optional_fields_populated(self):
        """Test validation when all optional fields are provided."""
        # Create a test file for receipt
        from django.core.files.uploadedfile import SimpleUploadedFile

        test_file = SimpleUploadedFile(
            "test_receipt.txt", b"Test receipt content", content_type="text/plain"
        )

        transaction = Transaction(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("123.45"),
            category=self.category1,
            description="Complete transaction",
            notes="Detailed notes about this transaction",
            merchant="Test Merchant Name",
            date=timezone.now().date(),
            receipt=test_file,
        )
        transaction.full_clean()  # Should not raise ValidationError

    def test_validation_preserves_encrypted_field_data(self):
        """Test that validation doesn't corrupt encrypted field data."""
        sensitive_notes = "Sensitive financial information"
        sensitive_merchant = "Private merchant name"

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category1,
            description="Encryption test",
            notes=sensitive_notes,
            merchant=sensitive_merchant,
            date=timezone.now().date(),
        )

        # Retrieve and validate again to ensure encryption is preserved
        saved_transaction = Transaction.objects.get(id=transaction.id)
        saved_transaction.full_clean()  # Should not raise ValidationError

        # Verify encrypted data is still correctly retrieved
        self.assertEqual(saved_transaction.notes, sensitive_notes)
        self.assertEqual(saved_transaction.merchant, sensitive_merchant)


class RecurringTransactionTestCase(TestCase):
    """Test case for recurring transaction functionality (Task 2.1.3)."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")
        self.category2 = CategoryFactory(user=self.user1, name="Rent")

    def test_recurring_transaction_creation_basic(self):
        """Test basic recurring transaction creation."""
        from datetime import date

        start_date = date.today()
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Weekly groceries",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        self.assertTrue(transaction.is_recurring)
        self.assertEqual(transaction.recurring_frequency, Transaction.WEEKLY)
        self.assertEqual(transaction.recurring_interval, 1)
        self.assertEqual(transaction.recurring_start_date, start_date)
        self.assertIsNotNone(transaction.next_occurrence)

    def test_recurring_frequency_choices(self):
        """Test all recurring frequency options."""
        from datetime import date

        frequencies = [
            Transaction.DAILY,
            Transaction.WEEKLY,
            Transaction.MONTHLY,
            Transaction.YEARLY,
        ]

        for frequency in frequencies:
            transaction = Transaction.objects.create(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("100.00"),
                category=self.category1,
                description=f"Test {frequency} transaction",
                date=date.today(),
                is_recurring=True,
                recurring_frequency=frequency,
                recurring_interval=1,
                recurring_start_date=date.today(),
            )

            self.assertEqual(transaction.recurring_frequency, frequency)

    def test_next_occurrence_calculation_daily(self):
        """Test next occurrence calculation for daily frequency."""
        from datetime import date, timedelta

        start_date = date.today()
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("10.00"),
            category=self.category1,
            description="Daily coffee",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        expected_next = start_date + timedelta(days=1)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_next_occurrence_calculation_weekly(self):
        """Test next occurrence calculation for weekly frequency."""
        from datetime import date, timedelta

        start_date = date.today()
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Weekly groceries",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        expected_next = start_date + timedelta(weeks=1)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_next_occurrence_calculation_monthly(self):
        """Test next occurrence calculation for monthly frequency."""
        from datetime import date

        from dateutil.relativedelta import relativedelta

        start_date = date(2024, 1, 15)  # Use specific date for predictable testing
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("1200.00"),
            category=self.category2,
            description="Monthly rent",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.MONTHLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        expected_next = start_date + relativedelta(months=1)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_next_occurrence_calculation_yearly(self):
        """Test next occurrence calculation for yearly frequency."""
        from datetime import date

        from dateutil.relativedelta import relativedelta

        start_date = date(2024, 3, 15)  # Use specific date for predictable testing
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("500.00"),
            category=self.category1,
            description="Annual subscription",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.YEARLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        expected_next = start_date + relativedelta(years=1)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_recurring_interval_handling(self):
        """Test different interval values for recurring transactions."""
        from datetime import date, timedelta

        start_date = date.today()

        # Every 2 weeks
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category1,
            description="Bi-weekly expense",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=2,
            recurring_start_date=start_date,
        )

        expected_next = start_date + timedelta(weeks=2)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_recurring_with_end_date(self):
        """Test recurring transactions with end dates."""
        from datetime import date, timedelta

        start_date = date.today()
        end_date = start_date + timedelta(days=30)

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("25.00"),
            category=self.category1,
            description="Limited time subscription",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=start_date,
            recurring_end_date=end_date,
        )

        self.assertEqual(transaction.recurring_end_date, end_date)

    def test_generate_next_transaction(self):
        """Test generating the next transaction in a recurring series."""
        from datetime import date, timedelta

        start_date = date.today()
        original_transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Weekly groceries",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        # Generate next transaction
        next_transaction = original_transaction.generate_next_transaction()

        # Verify new transaction properties
        self.assertEqual(next_transaction.user, self.user1)
        self.assertEqual(next_transaction.transaction_type, Transaction.EXPENSE)
        self.assertEqual(next_transaction.amount, Decimal("50.00"))
        self.assertEqual(next_transaction.category, self.category1)
        self.assertEqual(next_transaction.description, "Weekly groceries")
        self.assertEqual(next_transaction.date, start_date + timedelta(weeks=1))
        self.assertFalse(
            next_transaction.is_recurring
        )  # Generated transactions are not recurring
        self.assertEqual(next_transaction.parent_transaction, original_transaction)

    def test_update_next_occurrence_after_generation(self):
        """Test that next_occurrence is updated after generating a transaction."""
        from datetime import date, timedelta

        start_date = date.today()
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("30.00"),
            category=self.category1,
            description="Daily coffee",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        original_next = transaction.next_occurrence
        transaction.generate_next_transaction()

        # Refresh from database
        transaction.refresh_from_db()

        # Next occurrence should be updated
        expected_new_next = original_next + timedelta(days=1)
        self.assertEqual(transaction.next_occurrence, expected_new_next)

    def test_recurring_transaction_validation_requires_frequency(self):
        """Test that recurring transactions require frequency."""
        from datetime import date

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Invalid recurring transaction",
                date=date.today(),
                is_recurring=True,
                # Missing recurring_frequency
                recurring_interval=1,
                recurring_start_date=date.today(),
            )
            transaction.full_clean()

    def test_recurring_transaction_validation_requires_interval(self):
        """Test that recurring transactions require positive interval."""
        from datetime import date

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Invalid recurring transaction",
                date=date.today(),
                is_recurring=True,
                recurring_frequency=Transaction.WEEKLY,
                recurring_interval=0,  # Invalid interval
                recurring_start_date=date.today(),
            )
            transaction.full_clean()

    def test_recurring_transaction_validation_requires_start_date(self):
        """Test that recurring transactions require start date."""
        from datetime import date

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Invalid recurring transaction",
                date=date.today(),
                is_recurring=True,
                recurring_frequency=Transaction.WEEKLY,
                recurring_interval=1,
                # Missing recurring_start_date
            )
            transaction.full_clean()

    def test_recurring_end_date_after_start_date(self):
        """Test that recurring end date must be after start date."""
        from datetime import date, timedelta

        start_date = date.today()
        end_date = start_date - timedelta(days=1)  # End before start

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user1,
                transaction_type=Transaction.EXPENSE,
                amount=Decimal("50.00"),
                category=self.category1,
                description="Invalid date range",
                date=start_date,
                is_recurring=True,
                recurring_frequency=Transaction.DAILY,
                recurring_interval=1,
                recurring_start_date=start_date,
                recurring_end_date=end_date,
            )
            transaction.full_clean()

    def test_non_recurring_transaction_ignores_recurring_fields(self):
        """Test that non-recurring transactions ignore recurring fields."""
        from datetime import date

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("25.00"),
            category=self.category1,
            description="One-time transaction",
            date=date.today(),
            is_recurring=False,
            # These fields should be ignored
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        self.assertFalse(transaction.is_recurring)
        self.assertIsNone(transaction.next_occurrence)

    def test_recurring_transaction_month_end_edge_case(self):
        """Test recurring transactions on month-end dates."""
        from datetime import date

        # Start on January 31st
        start_date = date(2024, 1, 31)
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("1000.00"),
            category=self.category2,
            description="Month-end rent",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.MONTHLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        # Next occurrence should handle February (28/29 days)
        expected_next = date(2024, 2, 29)  # 2024 is a leap year
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_recurring_transaction_leap_year_handling(self):
        """Test recurring transactions handle leap years correctly."""
        from datetime import date

        # Start on February 29th (leap year)
        start_date = date(2024, 2, 29)
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category1,
            description="Leap year transaction",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.YEARLY,
            recurring_interval=1,
            recurring_start_date=start_date,
        )

        # Next occurrence should be February 28, 2025 (non-leap year)
        expected_next = date(2025, 2, 28)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_stop_recurring_transaction(self):
        """Test stopping a recurring transaction."""
        from datetime import date

        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Weekly groceries",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        # Stop the recurring transaction
        transaction.stop_recurring()

        self.assertFalse(transaction.is_recurring)
        self.assertIsNone(transaction.next_occurrence)

    def test_parent_transaction_relationship(self):
        """Test parent-child relationship for recurring transactions."""
        from datetime import date

        parent_transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Weekly groceries",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        # Generate child transaction
        child_transaction = parent_transaction.generate_next_transaction()

        # Verify relationship
        self.assertEqual(child_transaction.parent_transaction, parent_transaction)
        self.assertIn(child_transaction, parent_transaction.recurring_children.all())

    def test_user_isolation_recurring_transactions(self):
        """Test that recurring transactions respect user isolation."""
        from datetime import date

        # Create recurring transaction for user1
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="User1 recurring",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        # Generate next transaction - should belong to user1
        next_transaction = transaction.generate_next_transaction()
        self.assertEqual(next_transaction.user, self.user1)

        # Verify user2 cannot access this transaction
        user2_transactions = Transaction.objects.filter(user=self.user2)
        self.assertNotIn(transaction, user2_transactions)
        self.assertNotIn(next_transaction, user2_transactions)


class RecurringTransactionTasksTestCase(TestCase):
    """Test case for recurring transaction Celery tasks (Task 2.1.3)."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")
        self.category2 = CategoryFactory(user=self.user2, name="Rent")

    def test_generate_recurring_transactions_task(self):
        """Test the Celery task for generating recurring transactions."""
        from datetime import date, timedelta

        from apps.expenses.tasks import generate_recurring_transactions

        # Create a recurring transaction that's due
        yesterday = date.today() - timedelta(days=1)
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Daily coffee",
            date=yesterday,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=yesterday,
            next_occurrence=yesterday,  # Due yesterday
        )

        # Run the task
        result = generate_recurring_transactions()

        # Verify results
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["generated"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["user_count"], 1)

        # Verify the new transaction was created
        generated_transactions = Transaction.objects.filter(
            parent_transaction=transaction,
            is_recurring=False,
        )
        self.assertEqual(generated_transactions.count(), 1)

    def test_generate_user_specific_recurring_transactions(self):
        """Test generating recurring transactions for a specific user."""
        from datetime import date, timedelta

        from apps.expenses.tasks import generate_recurring_transactions

        yesterday = date.today() - timedelta(days=1)

        # Create transactions for both users
        transaction1 = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="User1 transaction",
            date=yesterday,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=yesterday,
            next_occurrence=yesterday,
        )

        transaction2 = Transaction.objects.create(
            user=self.user2,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            category=self.category2,
            description="User2 transaction",
            date=yesterday,
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=yesterday,
            next_occurrence=yesterday,
        )

        # Generate only for user1
        result = generate_recurring_transactions(user_id=self.user1.id)

        # Verify only user1's transaction was processed
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["generated"], 1)
        self.assertEqual(result["user_count"], 1)

        # Verify correct transaction was generated
        user1_generated = Transaction.objects.filter(
            parent_transaction=transaction1,
            is_recurring=False,
        )
        user2_generated = Transaction.objects.filter(
            parent_transaction=transaction2,
            is_recurring=False,
        )

        self.assertEqual(user1_generated.count(), 1)
        self.assertEqual(user2_generated.count(), 0)

    def test_cleanup_expired_recurring_transactions_task(self):
        """Test the task for cleaning up expired recurring transactions."""
        from datetime import date, timedelta

        from apps.expenses.tasks import cleanup_expired_recurring_transactions

        start_date = date.today() - timedelta(days=10)
        past_end_date = date.today() - timedelta(days=5)

        # Create an expired recurring transaction
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Expired subscription",
            date=start_date,
            is_recurring=True,
            recurring_frequency=Transaction.MONTHLY,
            recurring_interval=1,
            recurring_start_date=start_date,
            recurring_end_date=past_end_date,  # Already expired
        )

        # Run the cleanup task
        result = cleanup_expired_recurring_transactions()

        # Verify results
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["stopped"], 1)

        # Verify transaction was stopped
        transaction.refresh_from_db()
        self.assertFalse(transaction.is_recurring)
        self.assertIsNone(transaction.next_occurrence)

    def test_generate_upcoming_recurring_transactions_task(self):
        """Test pre-generating upcoming recurring transactions."""
        from datetime import date, timedelta

        from apps.expenses.tasks import generate_upcoming_recurring_transactions

        tomorrow = date.today() + timedelta(days=1)

        # Create a transaction due tomorrow
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Future transaction",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=date.today(),
            next_occurrence=tomorrow,
        )

        # Generate upcoming transactions for next 7 days
        result = generate_upcoming_recurring_transactions(days_ahead=7)

        # Verify results
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["generated"], 1)
        self.assertEqual(result["errors"], 0)

        # Verify the future transaction was created
        generated_transactions = Transaction.objects.filter(
            parent_transaction=transaction,
            date=tomorrow,
            is_recurring=False,
        )
        self.assertEqual(generated_transactions.count(), 1)

    def test_validate_recurring_transactions_task(self):
        """Test the validation task for recurring transactions."""
        from datetime import date, timedelta

        from apps.expenses.tasks import validate_recurring_transactions

        # Create a recurring transaction with incorrect next_occurrence
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Invalid next occurrence",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.WEEKLY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        # Manually set incorrect next_occurrence
        Transaction.objects.filter(id=transaction.id).update(
            next_occurrence=date.today() + timedelta(days=10)  # Should be 7 days
        )

        # Run validation task
        result = validate_recurring_transactions()

        # Verify results
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["fixed"], 1)
        self.assertEqual(result["invalid"], 0)

        # Verify next_occurrence was corrected
        transaction.refresh_from_db()
        expected_next = date.today() + timedelta(weeks=1)
        self.assertEqual(transaction.next_occurrence, expected_next)

    def test_task_handles_invalid_recurring_transactions(self):
        """Test that tasks handle invalid recurring transactions gracefully."""
        from datetime import date

        from apps.expenses.tasks import validate_recurring_transactions

        # Create a valid transaction first, then make it invalid
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Initially valid recurring",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=date.today(),
        )

        # Make it invalid by removing required fields using update (bypasses validation)
        Transaction.objects.filter(id=transaction.id).update(
            recurring_frequency=None,
            recurring_interval=None,
            recurring_start_date=None,
        )

        # Run validation task
        result = validate_recurring_transactions()

        # Verify invalid transaction was caught
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["valid"], 0)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["transaction_id"], transaction.id)

    def test_task_prevents_duplicate_generation(self):
        """Test that upcoming generation doesn't create duplicates."""
        from datetime import date, timedelta

        from apps.expenses.tasks import generate_upcoming_recurring_transactions

        tomorrow = date.today() + timedelta(days=1)

        # Create a transaction due tomorrow
        transaction = Transaction.objects.create(
            user=self.user1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            category=self.category1,
            description="Future transaction",
            date=date.today(),
            is_recurring=True,
            recurring_frequency=Transaction.DAILY,
            recurring_interval=1,
            recurring_start_date=date.today(),
            next_occurrence=tomorrow,
        )

        # Generate once
        result1 = generate_upcoming_recurring_transactions(days_ahead=7)
        self.assertEqual(result1["generated"], 1)

        # Reset next_occurrence to test duplicate prevention logic
        Transaction.objects.filter(id=transaction.id).update(next_occurrence=tomorrow)

        # Generate again - should not create duplicates
        result2 = generate_upcoming_recurring_transactions(days_ahead=7)
        self.assertEqual(result2["generated"], 0)
        self.assertEqual(result2["processed"], 1)

        # Verify only one transaction was created
        generated_transactions = Transaction.objects.filter(
            parent_transaction=transaction,
            date=tomorrow,
            is_recurring=False,
        )
        self.assertEqual(generated_transactions.count(), 1)
