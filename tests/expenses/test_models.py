"""
Tests for expense models.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.expenses.models import Category
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
