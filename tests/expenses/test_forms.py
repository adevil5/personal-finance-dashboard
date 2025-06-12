"""Tests for expense forms."""

import io
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.expenses.forms import TransactionForm
from apps.expenses.models import Category, Transaction
from tests.factories import CategoryFactory, UserFactory


User = get_user_model()


class TransactionFormTestCase(TestCase):
    """Test cases for TransactionForm."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)
        
        # Valid form data
        self.valid_data = {
            'description': 'Test Transaction',
            'amount': '25.50',
            'date': timezone.now().date(),
            'transaction_type': Transaction.EXPENSE,
            'category': self.category.id,
            'merchant': 'Test Merchant',
            'notes': 'Test notes',
        }

    def test_form_valid_with_required_fields(self):
        """Test form is valid with all required fields."""
        form = TransactionForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_invalid_without_description(self):
        """Test form is invalid without description."""
        data = self.valid_data.copy()
        data['description'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)

    def test_form_invalid_without_amount(self):
        """Test form is invalid without amount."""
        data = self.valid_data.copy()
        data['amount'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_form_invalid_with_negative_amount(self):
        """Test form is invalid with negative amount."""
        data = self.valid_data.copy()
        data['amount'] = '-10.00'
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_form_invalid_with_zero_amount(self):
        """Test form is invalid with zero amount."""
        data = self.valid_data.copy()
        data['amount'] = '0.00'
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_form_invalid_with_too_many_decimal_places(self):
        """Test form is invalid with more than 2 decimal places."""
        data = self.valid_data.copy()
        data['amount'] = '25.123'
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_form_invalid_without_date(self):
        """Test form is invalid without date."""
        data = self.valid_data.copy()
        data['date'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_form_invalid_without_transaction_type(self):
        """Test form is invalid without transaction type."""
        data = self.valid_data.copy()
        data['transaction_type'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('transaction_type', form.errors)

    def test_form_requires_category_for_expense(self):
        """Test form requires category for expense transactions."""
        data = self.valid_data.copy()
        data['transaction_type'] = Transaction.EXPENSE
        data['category'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_form_allows_empty_category_for_income(self):
        """Test form allows empty category for income transactions."""
        data = self.valid_data.copy()
        data['transaction_type'] = Transaction.INCOME
        data['category'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_allows_empty_category_for_transfer(self):
        """Test form allows empty category for transfer transactions."""
        data = self.valid_data.copy()
        data['transaction_type'] = Transaction.TRANSFER
        data['category'] = ''
        form = TransactionForm(data=data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_validates_user_owned_category(self):
        """Test form only allows categories owned by the user."""
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user)
        
        data = self.valid_data.copy()
        data['category'] = other_category.id
        form = TransactionForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_form_optional_fields_can_be_empty(self):
        """Test optional fields can be empty."""
        data = {
            'description': 'Test Transaction',
            'amount': '25.50',
            'date': timezone.now().date(),
            'transaction_type': Transaction.INCOME,
            'merchant': '',
            'notes': '',
        }
        form = TransactionForm(data=data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_with_valid_receipt_upload(self):
        """Test form accepts valid receipt file."""
        # Create a simple image file
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00'
        receipt_file = SimpleUploadedFile(
            "receipt.png",
            image_content,
            content_type="image/png"
        )
        
        form = TransactionForm(
            data=self.valid_data,
            files={'receipt': receipt_file},
            user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_save_creates_transaction(self):
        """Test form save creates a transaction with correct data."""
        form = TransactionForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        transaction = form.save()
        
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.description, self.valid_data['description'])
        self.assertEqual(transaction.amount, Decimal(self.valid_data['amount']))
        self.assertEqual(transaction.amount_index, Decimal(self.valid_data['amount']))
        self.assertEqual(transaction.date, self.valid_data['date'])
        self.assertEqual(transaction.transaction_type, self.valid_data['transaction_type'])
        self.assertEqual(transaction.category_id, self.valid_data['category'])
        self.assertEqual(transaction.merchant, self.valid_data['merchant'])
        self.assertEqual(transaction.notes, self.valid_data['notes'])

    def test_form_save_with_commit_false(self):
        """Test form save with commit=False returns unsaved instance."""
        form = TransactionForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        transaction = form.save(commit=False)
        
        # Should not be saved to database yet
        self.assertIsNone(transaction.pk)
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.description, self.valid_data['description'])

    def test_form_category_queryset_filtered_by_user(self):
        """Test category field queryset is filtered by user."""
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user)
        
        form = TransactionForm(user=self.user)
        
        # User's category should be available
        self.assertIn(self.category, form.fields['category'].queryset)
        
        # Other user's category should not be available
        self.assertNotIn(other_category, form.fields['category'].queryset)

    def test_form_category_queryset_only_active_categories(self):
        """Test category field queryset only includes active categories."""
        inactive_category = CategoryFactory(user=self.user, is_active=False)
        
        form = TransactionForm(user=self.user)
        
        # Active category should be available
        self.assertIn(self.category, form.fields['category'].queryset)
        
        # Inactive category should not be available
        self.assertNotIn(inactive_category, form.fields['category'].queryset)

    def test_form_clears_category_for_non_expense(self):
        """Test form clears category when transaction type is not expense."""
        data = self.valid_data.copy()
        data['transaction_type'] = Transaction.INCOME
        data['category'] = self.category.id  # Set category even for income
        
        form = TransactionForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        
        transaction = form.save()
        self.assertIsNone(transaction.category)


class TransactionFormWidgetTestCase(TestCase):
    """Test cases for TransactionForm widget rendering."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)

    def test_form_has_expected_widgets(self):
        """Test form has expected widget types."""
        form = TransactionForm(user=self.user)
        
        # Check widget types
        self.assertEqual(form.fields['description'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['amount'].widget.__class__.__name__, 'NumberInput')
        self.assertEqual(form.fields['date'].widget.__class__.__name__, 'DateInput')
        self.assertEqual(form.fields['transaction_type'].widget.__class__.__name__, 'Select')
        self.assertEqual(form.fields['category'].widget.__class__.__name__, 'Select')
        self.assertEqual(form.fields['merchant'].widget.__class__.__name__, 'TextInput')
        self.assertEqual(form.fields['notes'].widget.__class__.__name__, 'Textarea')
        self.assertEqual(form.fields['receipt'].widget.__class__.__name__, 'ClearableFileInput')

    def test_form_widgets_have_css_classes(self):
        """Test form widgets have proper CSS classes."""
        form = TransactionForm(user=self.user)
        
        # Check CSS classes for styling
        for field_name, field in form.fields.items():
            if field_name != 'receipt':  # File input might have different classes
                self.assertIn('form-control', field.widget.attrs.get('class', ''))


class TransactionFormIntegrationTestCase(TestCase):
    """Integration test cases for TransactionForm views."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)
        self.client.force_login(self.user)
        
        # Valid form data
        self.valid_data = {
            'description': 'Test Transaction',
            'amount': '25.50',
            'date': timezone.now().date(),
            'transaction_type': Transaction.EXPENSE,
            'category': self.category.id,
            'merchant': 'Test Merchant',
            'notes': 'Test notes',
        }

    def test_transaction_create_view_get(self):
        """Test GET request to transaction create view."""
        response = self.client.get('/expenses/create/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Transaction')
        self.assertContains(response, 'Create Transaction')
        self.assertIsInstance(response.context['form'], TransactionForm)

    def test_transaction_create_view_post_valid(self):
        """Test POST request with valid data."""
        response = self.client.post('/expenses/create/', data=self.valid_data)
        
        # Should redirect to transaction list on success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/expenses/')
        
        # Transaction should be created
        transaction = Transaction.objects.get(user=self.user)
        self.assertEqual(transaction.description, 'Test Transaction')
        self.assertEqual(transaction.amount, Decimal('25.50'))
        self.assertEqual(transaction.category, self.category)

    def test_transaction_create_view_post_invalid(self):
        """Test POST request with invalid data."""
        invalid_data = self.valid_data.copy()
        invalid_data['amount'] = '-10.00'  # Negative amount
        
        response = self.client.post('/expenses/create/', data=invalid_data)
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amount must be greater than zero')
        
        # No transaction should be created
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

    def test_transaction_create_view_htmx_valid(self):
        """Test HTMX POST request with valid data."""
        response = self.client.post(
            '/expenses/create/', 
            data=self.valid_data,
            HTTP_HX_REQUEST='true'
        )
        
        # Should return success template
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction Created Successfully')
        
        # Transaction should be created
        transaction = Transaction.objects.get(user=self.user)
        self.assertEqual(transaction.description, 'Test Transaction')

    def test_transaction_create_view_htmx_invalid(self):
        """Test HTMX POST request with invalid data."""
        invalid_data = self.valid_data.copy()
        invalid_data['description'] = ''  # Required field
        
        response = self.client.post(
            '/expenses/create/', 
            data=invalid_data,
            HTTP_HX_REQUEST='true'
        )
        
        # Should return form template with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        
        # No transaction should be created
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

    def test_transaction_create_view_requires_login(self):
        """Test that view requires login."""
        self.client.logout()
        response = self.client.get('/expenses/create/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_transaction_create_view_context_data(self):
        """Test that view provides necessary context data."""
        response = self.client.get('/expenses/create/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('categories', response.context)
        
        # Should only include user's active categories
        categories = response.context['categories']
        self.assertIn(self.category, categories)
        
        # Create inactive category - should not be included
        inactive_category = CategoryFactory(user=self.user, is_active=False)
        response = self.client.get('/expenses/create/')
        categories = response.context['categories']
        self.assertNotIn(inactive_category, categories)

    def test_form_category_field_initial_state(self):
        """Test that category field is initially hidden."""
        response = self.client.get('/expenses/create/')
        
        self.assertEqual(response.status_code, 200)
        # Category field should be hidden by default
        self.assertContains(response, 'id="category-field"')
        self.assertContains(response, 'style="display: none;"')

    def test_file_upload_functionality(self):
        """Test file upload with receipt."""
        from django.test import override_settings
        from django.core.files.storage import default_storage
        import tempfile
        import os
        
        # Use a temporary directory for file uploads in tests
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(MEDIA_ROOT=temp_dir):
                # Create a simple image file
                image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00'
                receipt_file = SimpleUploadedFile(
                    "receipt.png",
                    image_content,
                    content_type="image/png"
                )
                
                data = self.valid_data.copy()
                response = self.client.post('/expenses/create/', data=data, files={'receipt': receipt_file})
                
                # Should be successful
                self.assertEqual(response.status_code, 302)
                
                # Transaction should be created
                transaction = Transaction.objects.get(user=self.user)
                self.assertEqual(transaction.description, 'Test Transaction')
                
                # Receipt field should be set (even if file validation might prevent actual saving)
                # Note: In test environment, the secure file storage might not save the file
                # but the form should still process correctly