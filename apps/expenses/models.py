import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()


def validate_hex_color(value):
    """Validate that the value is a valid hex color."""
    if value and not re.match(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", value):
        raise ValidationError(f"{value} is not a valid hex color")


class Category(models.Model):
    """
    Category model for organizing expenses.

    Supports hierarchical structure with parent-child relationships
    and user-specific categories for data isolation.
    """

    name = models.CharField(max_length=100, help_text="Category name")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        help_text="User this category belongs to",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category for hierarchical structure",
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[validate_hex_color],
        help_text="Category color in hex format (e.g., #FF0000)",
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon identifier for the category",
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether this category is active (soft delete)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this category was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this category was last updated"
    )

    class Meta:
        db_table = "expenses_category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        unique_together = ["user", "name", "parent"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "parent"]),
        ]

    def __str__(self):
        """Return string representation of the category."""
        return self.name

    def clean(self):
        """Validate the category."""
        super().clean()

        # Prevent self as parent
        if self.parent == self:
            raise ValidationError("A category cannot be its own parent.")

        # Prevent circular references
        if self.parent and self._would_create_cycle():
            raise ValidationError(
                "This parent assignment would create a circular reference."
            )

        # Ensure parent belongs to same user
        if self.parent and self.parent.user != self.user:
            raise ValidationError("Parent category must belong to the same user.")

    def _would_create_cycle(self):
        """Check if setting the current parent would create a circular reference."""
        current = self.parent
        while current:
            if current == self:
                return True
            current = current.parent
        return False

    def get_level(self):
        """Get the level of this category in the hierarchy (0 for root)."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level

    def get_descendants(self):
        """Get all descendants of this category."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_ancestors(self):
        """Get all ancestors of this category."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    @classmethod
    def get_root_categories(cls, user):
        """Get all root categories (no parent) for a user."""
        return cls.objects.filter(user=user, parent=None, is_active=True)

    @classmethod
    def get_category_tree(cls, user):
        """Get all categories for a user ordered for tree display."""
        return cls.objects.filter(user=user, is_active=True).order_by("name")
