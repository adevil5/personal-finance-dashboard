"""Forms for expense management."""

from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError

from .models import Category, Transaction


class TransactionForm(forms.ModelForm):
    """Form for creating and editing transactions."""

    class Meta:
        model = Transaction
        fields = [
            'description',
            'amount',
            'date',
            'transaction_type',
            'category',
            'merchant',
            'notes',
            'receipt',
        ]
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'Enter transaction description...',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'date': forms.DateInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'type': 'date',
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'onchange': 'toggleCategory(this.value)',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            }),
            'merchant': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'Enter merchant or payee name...',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'rows': 3,
                'placeholder': 'Additional notes about this transaction...',
            }),
            'receipt': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*,.pdf',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        """Initialize the form with user context."""
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Filter categories to user's active categories only
        if self.user:
            self.fields['category'].queryset = Category.objects.filter(
                user=self.user, is_active=True
            ).order_by('name')
        else:
            self.fields['category'].queryset = Category.objects.none()
        
        # Make category field not required initially (will be validated in clean method)
        self.fields['category'].required = False
        
        # Add form-control class to widgets for backward compatibility tests
        for field_name, field in self.fields.items():
            current_class = field.widget.attrs.get('class', '')
            if 'form-control' not in current_class:
                field.widget.attrs['class'] = f'{current_class} form-control'.strip()

    def clean_amount(self):
        """Validate amount field."""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise ValidationError("Amount is required.")
        
        # Convert to Decimal for validation
        try:
            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValidationError("Please enter a valid amount.")
        
        if decimal_amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        
        # Check decimal places
        if decimal_amount.as_tuple().exponent < -2:
            raise ValidationError("Amount cannot have more than 2 decimal places.")
        
        return decimal_amount

    def clean_category(self):
        """Validate category field based on transaction type."""
        category = self.cleaned_data.get('category')
        transaction_type = self.cleaned_data.get('transaction_type')
        
        # Category is required for expense transactions
        if transaction_type == Transaction.EXPENSE and not category:
            raise ValidationError("Category is required for expense transactions.")
        
        # Validate that category belongs to the user
        if category and self.user and category.user != self.user:
            raise ValidationError("Invalid category selected.")
        
        return category

    def clean(self):
        """Perform form-level validation."""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        category = cleaned_data.get('category')
        
        # Clear category for non-expense transactions
        if transaction_type in [Transaction.INCOME, Transaction.TRANSFER]:
            cleaned_data['category'] = None
        
        return cleaned_data

    def _post_clean(self):
        """Prepare instance before model validation."""
        # Set the user before model validation
        if self.user:
            self.instance.user = self.user
        
        # Run normal model validation
        super()._post_clean()

    def save(self, commit=True):
        """Save the transaction with user context."""
        transaction = super().save(commit=False)
        
        # Set the user
        if self.user:
            transaction.user = self.user
        
        # Set amount_index for filtering/sorting
        if transaction.amount is not None:
            transaction.amount_index = transaction.amount
        
        # Clear category for non-expense transactions
        if transaction.transaction_type in [Transaction.INCOME, Transaction.TRANSFER]:
            transaction.category = None
        
        if commit:
            transaction.save()
        
        return transaction