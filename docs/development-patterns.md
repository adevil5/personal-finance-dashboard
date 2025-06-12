# Development Patterns

This document outlines the specific development patterns and architectural decisions used in the Personal Finance Dashboard project. These patterns extend Django's standard practices to meet the unique requirements of secure financial data handling.

## Table of Contents

1. [PII Protection Patterns](#pii-protection-patterns)
2. [File Upload Security Patterns](#file-upload-security-patterns)
3. [Budget Management Patterns](#budget-management-patterns)
4. [Analytics Engine Patterns](#analytics-engine-patterns)
5. [HTMX Integration Patterns](#htmx-integration-patterns)
6. [Frontend Form Patterns](#frontend-form-patterns)
7. [API Design Patterns](#api-design-patterns)
8. [Testing Patterns](#testing-patterns)

## PII Protection Patterns

### Encrypted Field Architecture

All PII fields use field-level encryption with a dual-field approach for maintaining queryability:

```python
# Model Definition
class Transaction(models.Model):
    amount = EncryptedDecimalField(max_digits=10, decimal_places=2)
    amount_index = models.DecimalField(max_digits=10, decimal_places=2)  # For filtering/sorting
    merchant = EncryptedCharField(max_length=200)
    notes = EncryptedTextField(blank=True)

    def save(self, *args, **kwargs):
        # Always sync index field for queries
        self.amount_index = self.amount
        super().save(*args, **kwargs)
```

### PII Field Patterns

- **Transaction amounts**: `EncryptedDecimalField` with `amount_index` for filtering/sorting
- **Merchant/notes**: `EncryptedCharField` with searchable indexes where needed
- **User isolation**: Always filter querysets by `user=request.user` in serializers
- **Phone fields**: `EncryptedPhoneField` with automatic normalization to E.164 format
- **Custom User model**: Extends AbstractUser with encrypted phone, timezone, currency fields

### Audit Logging Pattern

```python
# Automatic PII access logging
class PIIAccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    accessed_field = models.CharField(max_length=100)
    accessed_value_hash = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20)

    @classmethod
    def log_access(cls, user, field_name, value, action='read'):
        """Log PII field access for compliance"""
        value_hash = hashlib.sha256(str(value).encode()).hexdigest()
        cls.objects.create(
            user=user,
            accessed_field=field_name,
            accessed_value_hash=value_hash,
            action=action
        )
```

## File Upload Security Patterns

### Multi-Layer Validation Architecture

File uploads use a comprehensive security validator with multiple validation layers:

```python
# File validation layers in apps/core/security/validators.py
class ReceiptFileValidator:
    def __init__(self, max_size=10*1024*1024, allowed_types=None, scan_malware=True):
        self.max_size = max_size
        self.allowed_types = allowed_types or ['image/jpeg', 'image/png', 'application/pdf']
        self.scan_malware = scan_malware

    def __call__(self, file):
        self._validate_size(file)
        self._validate_type(file)
        if self.scan_malware:
            self._scan_malware(file)

    def _validate_type(self, file):
        # Use magic bytes detection, not just file extensions
        file_type = magic.from_buffer(file.read(1024), mime=True)
        if file_type not in self.allowed_types:
            raise ValidationError(f"File type {file_type} not allowed")
```

### Security Validator Components

- **File type validation**: Magic bytes detection (not just extensions)
- **File size enforcement**: 10MB limit with proper error messages
- **Content validation**: Prevent executable/script content in image files
- **Malware scanning**: ClamAV integration with fallback behavior
- **Path traversal prevention**: Filename sanitization and secure path generation

### Test Mocking Patterns

Mock placement for imported functions:

```python
# Mock at import location, not source
@patch('apps.core.security.validators.scan_file')  # Not at source location
def test_malware_detection(self, mock_scan):
    mock_scan.return_value = False  # Clean file
    # Test logic here
```

## Budget Management Patterns

### Budget Alert Configuration

Budget alerts with configurable threshold monitoring:

```python
class Budget(models.Model):
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=80.00)
    critical_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)

    def check_thresholds(self):
        """Generate alerts based on spending thresholds"""
        utilization = self.get_utilization_percentage()

        if utilization >= self.critical_threshold:
            BudgetAlert.objects.get_or_create(
                budget=self,
                alert_type='critical',
                defaults={'message': f'Budget exceeded: {utilization:.1f}%'}
            )
        elif utilization >= self.warning_threshold:
            BudgetAlert.objects.get_or_create(
                budget=self,
                alert_type='warning',
                defaults={'message': f'Budget warning: {utilization:.1f}%'}
            )
```

### Dynamic Calculation Patterns

- **Spent amount calculations**: Aggregated transactions with user isolation
- **Period-based tracking**: Date range validation with overlap detection
- **Alert notifications**: Celery integration for background processing
- **Performance optimization**: Cached calculations with Redis

## Analytics Engine Patterns

### Database-Agnostic Analytics

The `SpendingAnalytics` class provides database-agnostic analytics:

```python
class SpendingAnalytics:
    def __init__(self, user, start_date=None, end_date=None):
        self.user = user
        self.start_date = start_date or timezone.now().date().replace(day=1)
        self.end_date = end_date or timezone.now().date()

    def get_spending_trends(self, period='monthly'):
        """Get spending trends with database-agnostic date truncation"""
        if connection.vendor == 'postgresql':
            date_trunc = "DATE_TRUNC(%s, date)"
        else:  # SQLite
            date_trunc = "DATE(date, 'start of month')" if period == 'monthly' else "DATE(date)"

        return Transaction.objects.filter(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            date__range=[self.start_date, self.end_date]
        ).extra(
            select={'period': date_trunc},
            select_params=[period] if connection.vendor == 'postgresql' else []
        ).values('period').annotate(
            total=Sum('amount_index')
        ).order_by('period')
```

### Analytics Testing Patterns

Use specific settings for reliable test execution:

```bash
# Run analytics tests with consistent settings
pytest apps/analytics/ --settings=config.settings.testing
```

## HTMX Integration Patterns

### Custom Template Tags

DRY HTMX patterns through custom template tags in `apps/core/templatetags/htmx_tags.py`:

```django
<!-- GET request with target -->
{% htmx_get "/api/data/" "#target" %}

<!-- POST with CSRF protection -->
{% htmx_post "/api/create/" "#result" %}

<!-- DELETE with confirmation -->
{% htmx_delete "/api/delete/1/" "#item" "Confirm deletion?" %}

<!-- Form with automatic CSRF headers -->
{% htmx_form "/api/update/" "#container" %}

<!-- Loading indicators -->
{% htmx_loading "target-id" "Loading..." %}

<!-- Error containers -->
{% htmx_error_container "form-errors" %}
```

### JavaScript Utilities

Global `htmxUtils` object for programmatic control:

```javascript
// Loading state management
htmxUtils.showLoading('target-id', 'Processing...');
htmxUtils.hideLoading('target-id');

// Error display management
htmxUtils.showError('form-errors', 'Validation failed');
htmxUtils.hideError('form-errors');

// CSRF token retrieval
const token = htmxUtils.getCSRFToken();
```

### Event Handling Pattern

Automatic HTMX event listeners for enhanced UX:

```javascript
// Comprehensive error handling for API responses
document.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.xhr.status >= 400) {
        let errorMessage = 'An error occurred';
        try {
            const response = JSON.parse(evt.detail.xhr.responseText);
            errorMessage = response.detail || response.message || errorMessage;
        } catch (e) {
            errorMessage = evt.detail.xhr.statusText || errorMessage;
        }
        htmxUtils.showError('global-errors', errorMessage);
    }
});
```

## Frontend Form Patterns

### Django Forms with Encrypted Fields

Model clean methods must handle both string and Decimal types:

```python
class TransactionForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            # Filter categories by user for data isolation
            self.fields['category'].queryset = Category.objects.filter(user=user)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # Handle encrypted field type conversion
        if isinstance(amount, str):
            try:
                amount = Decimal(amount)
            except (InvalidOperation, TypeError):
                raise ValidationError("Invalid amount format")
        return amount

    def _post_clean(self):
        # Set user context before model validation
        if self.user:
            self.instance.user = self.user
        super()._post_clean()
```

### HTMX Form Integration

Dual template responses for regular vs HTMX requests:

```python
class TransactionCreateView(LoginRequiredMixin, CreateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('HX-Request'):
            # Return success partial for HTMX
            return render(self.request, 'expenses/_transaction_success.html', {
                'transaction': self.object
            })
        return response

    def form_invalid(self, form):
        if self.request.headers.get('HX-Request'):
            # Return form with errors for HTMX
            return render(self.request, 'expenses/_transaction_form.html', {
                'form': form
            })
        return super().form_invalid(form)
```

## API Design Patterns

### Transaction API Patterns

Dual-field amount filtering and currency formatting:

```python
class TransactionSerializer(serializers.ModelSerializer):
    formatted_amount = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    def get_formatted_amount(self, obj):
        """Format amount with user's currency preference"""
        return f"{obj.user.currency} {obj.amount:.2f}"

    def validate_amount(self, value):
        """Ensure decimal precision for financial data"""
        if value.as_tuple().exponent < -2:
            raise serializers.ValidationError("Amount cannot have more than 2 decimal places")
        return value
```

### Budget API Patterns

Calculated fields with user isolation:

```python
class BudgetSerializer(serializers.ModelSerializer):
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    is_over_budget = serializers.SerializerMethodField()

    def get_queryset(self):
        # Always filter by user for security
        return Budget.objects.filter(user=self.request.user)
```

## Testing Patterns

### Serializer Testing Patterns

Test both serialization and deserialization:

```python
class TransactionSerializerTest(TestCase):
    def test_serialization_with_currency_formatting(self):
        transaction = TransactionFactory(amount=Decimal('123.45'))
        serializer = TransactionSerializer(transaction)
        self.assertIn('formatted_amount', serializer.data)
        self.assertEqual(serializer.data['formatted_amount'], 'USD 123.45')

    def test_deserialization_with_validation(self):
        data = {'amount': '123.456', 'category_id': self.category.id}
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
```

### Django Validation Error Handling

Convert Django validation errors to DRF format:

```python
def create(self, validated_data):
    try:
        return super().create(validated_data)
    except ValidationError as e:
        # Convert Django validation errors to DRF format
        if hasattr(e, 'message_dict'):
            drf_errors = {}
            for field, messages in e.message_dict.items():
                if field == '__all__':
                    drf_errors['non_field_errors'] = messages
                else:
                    drf_errors[field] = messages
            raise serializers.ValidationError(drf_errors)
        raise serializers.ValidationError(str(e))
```

### File Upload Testing

Override storage settings and use proper mocking:

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadTest(TestCase):
    def test_secure_file_upload(self):
        # Create test file
        test_file = SimpleUploadedFile(
            "receipt.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )

        # Test with proper mocking
        with patch('apps.core.security.validators.scan_file') as mock_scan:
            mock_scan.return_value = True  # Clean file
            # Test upload logic
```

### Performance Testing Patterns

Test API response times with realistic data:

```python
def test_analytics_performance_with_large_dataset(self):
    # Create 500+ transactions for performance testing
    TransactionFactory.create_batch(500, user=self.user)

    start_time = time.time()
    response = self.client.get(self.url)
    end_time = time.time()

    self.assertEqual(response.status_code, 200)
    self.assertLess(end_time - start_time, 2.0)  # Under 2 seconds
```

---

## Key Principles

1. **Security First**: All patterns prioritize data protection and user isolation
2. **Performance Aware**: Patterns consider query optimization and caching
3. **Test Coverage**: All patterns include comprehensive test examples
4. **Type Safety**: TypeScript integration ensures frontend type safety
5. **Progressive Enhancement**: HTMX patterns enhance traditional Django without SPA complexity
6. **Maintainability**: Clear separation of concerns and DRY principles throughout

These patterns have evolved through real-world usage and comprehensive testing to provide a secure, performant foundation for financial data handling in Django applications.
