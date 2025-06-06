"""
Tests for expense models.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.test import TestCase

from apps.expenses.default_categories import DEFAULT_CATEGORIES
from apps.expenses.models import Category
from apps.expenses.signals import create_default_categories_for_new_user
from tests.factories import UserFactory

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
