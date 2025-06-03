# Personal Finance Dashboard - Product Requirements Document

**Document Version:** 1.0
**Last Updated:** June 3, 2025
**Project Code:** PFD
**Target Release:** MVP v1.0

## Executive Summary

The Personal Finance Dashboard (PFD) is a secure, web-based application designed to help users track expenses, manage budgets, and gain insights into their spending patterns. Built with modern web technologies and security best practices, the application serves as both a practical tool and a demonstration of full-stack development capabilities.

## Product Overview

### Vision Statement
Empower users to take control of their personal finances through intuitive expense tracking, insightful analytics, and secure data management.

### Target Audience
- **Primary:** Individual users seeking personal expense management
- **Secondary:** Small business owners tracking business expenses
- **Technical:** Hiring managers and technical evaluators assessing development skills

### Success Metrics
- User registration and retention rates
- Daily/weekly active usage
- Data entry accuracy and completeness
- System uptime and performance
- Security audit compliance

## Technical Architecture

### Technology Stack

#### Backend
- **Framework:** Django 5.2.1 (LTS)
- **Database:** PostgreSQL 17+
- **Authentication:** Django Allauth with MFA support
- **API:** Django REST Framework (DRF) 3.14+
- **Caching:** Redis 7.0+
- **Task Queue:** Celery with Redis broker
- **File Storage:** AWS S3 with KMS encryption or local storage with encryption at rest
- **PII Protection:** Field-level encryption, data masking, audit logging
- **Package Management:** uv for fast, reliable dependency management

#### Frontend
- **Base:** Django Templates with HTMX
- **JavaScript:** TypeScript 5.x with strict mode enabled
- **Build Tool:** Vite for fast development and optimized builds
- **Type Checking:** ESLint + TypeScript ESLint rules
- **CSS Framework:** Tailwind CSS 4.x
- **Charts:** Chart.js 4.x with TypeScript definitions
- **Icons:** Heroicons or Feather Icons
- **Forms:** Django Crispy Forms with TypeScript validation

#### Testing & Quality Assurance
- **Unit/Integration Testing:** pytest with Django test framework
- **API Testing:** pytest with DRF test client and factory-boy
- **E2E Testing:** Playwright with TypeScript for cross-browser testing
- **Visual Regression:** Playwright screenshots and visual comparisons
- **Performance Testing:** Locust for load testing API endpoints
- **Security Testing:** OWASP ZAP integration in CI/CD pipeline
- **Code Coverage:** pytest-cov with 90% minimum coverage requirement
- **Type Checking:** mypy for Python, TypeScript strict mode for frontend

#### Security
- **HTTPS:** TLS 1.3 minimum
- **CSRF Protection:** Django built-in middleware
- **SQL Injection:** Django ORM with parameterized queries
- **XSS Protection:** Content Security Policy headers
- **Rate Limiting:** Django RateLimit
- **PII Encryption:** Field-level encryption for sensitive data
- **File Security:** S3 KMS encryption, pre-signed URLs
- **Data Masking:** PII redaction in logs and non-prod environments
- **Audit Logging:** Complete audit trail for PII access and modifications

## System Requirements

### Functional Requirements

#### User Management (AUTH)
- **AUTH-001:** User registration with email verification
- **AUTH-002:** Secure login with optional 2FA (TOTP)
- **AUTH-003:** Password reset functionality
- **AUTH-004:** User profile management
- **AUTH-005:** Account deactivation/deletion with data retention policies

#### Expense Management (EXP)
- **EXP-001:** Create, read, update, delete expense transactions
- **EXP-002:** Categorize expenses with hierarchical categories
- **EXP-003:** Add receipts/attachments to transactions
- **EXP-004:** Bulk import via CSV/Excel files
- **EXP-005:** Recurring expense templates
- **EXP-006:** Multi-currency support with exchange rates

#### Budget Management (BUD)
- **BUD-001:** Create monthly/yearly budgets by category
- **BUD-002:** Budget vs. actual spending alerts
- **BUD-003:** Budget rollover and adjustments
- **BUD-004:** Savings goals tracking

#### Analytics & Reporting (ANA)
- **ANA-001:** Spending trends over time
- **ANA-002:** Category-wise expense breakdown
- **ANA-003:** Monthly/yearly expense reports
- **ANA-004:** Export reports to PDF/Excel
- **ANA-005:** Real-time dashboard with key metrics

#### Data Management (DATA)
- **DATA-001:** CSV/Excel import with validation
- **DATA-002:** Data export in multiple formats
- **DATA-003:** Data backup and restore
- **DATA-004:** Data archival policies

### Non-Functional Requirements

#### Performance
- **PERF-001:** Page load times < 2 seconds
- **PERF-002:** API response times < 500ms
- **PERF-003:** Support 100+ concurrent users
- **PERF-004:** Database queries optimized with proper indexing

#### Security
- **SEC-001:** OWASP Top 10 compliance
- **SEC-002:** PII encryption at rest and in transit (AES-256)
- **SEC-003:** Regular security audits and vulnerability scans
- **SEC-004:** GDPR/CCPA compliance for PII handling
- **SEC-005:** Session management and timeout policies
- **SEC-006:** Complete audit logging for PII access
- **SEC-007:** Data masking in non-production environments
- **SEC-008:** Secure file storage with KMS encryption

#### Scalability
- **SCALE-001:** Horizontal scaling capability
- **SCALE-002:** Database sharding readiness
- **SCALE-003:** CDN integration for static assets
- **SCALE-004:** Caching strategy implementation

#### Reliability
- **REL-001:** 99.5% uptime SLA
- **REL-002:** Automated backups with point-in-time recovery
- **REL-003:** Error handling and graceful degradation
- **REL-004:** Health checks and monitoring

## Database Schema

### Core Models

```python
# users/models.py
class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = EncryptedCharField(max_length=20, blank=True)  # PII - encrypted
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    monthly_income = EncryptedDecimalField(max_digits=12, decimal_places=2, null=True)  # PII
    financial_goals = EncryptedTextField(blank=True)  # PII
    ssn_last_four = EncryptedCharField(max_length=4, blank=True)  # PII - encrypted

# expenses/models.py
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
        ('transfer', 'Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    amount = EncryptedDecimalField(max_digits=12, decimal_places=2)  # PII - financial data
    currency = models.CharField(max_length=3, default='USD')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    notes = EncryptedTextField(blank=True)  # PII - may contain sensitive info
    date = models.DateField()
    receipt = models.FileField(upload_to='receipts/', blank=True)  # PII - receipts contain personal info
    merchant_name = EncryptedCharField(max_length=100, blank=True)  # PII - location/behavior data
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(max_length=20, blank=True)
    tags = models.ManyToManyField('Tag', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['category']),
        ]

# audit/models.py
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # CREATE, READ, UPDATE, DELETE
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    pii_fields_accessed = models.JSONField(default=list)  # Track which PII fields were accessed
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['model_name', 'action']),
        ]
```

### Indexing Strategy

```sql
-- Critical indexes for performance
CREATE INDEX idx_transaction_user_date ON expenses_transaction(user_id, date DESC);
CREATE INDEX idx_transaction_category ON expenses_transaction(category_id);
CREATE INDEX idx_budget_user_period ON budgets_budget(user_id, period_start, period_end);
CREATE INDEX idx_category_user_parent ON expenses_category(user_id, parent_id);
```

## API Design

### RESTful Endpoints

```python
# API URL Structure
/api/v1/
├── auth/
│   ├── register/
│   ├── login/
│   ├── logout/
│   ├── refresh/
│   └── password/reset/
├── users/
│   ├── profile/
│   └── preferences/
├── transactions/
│   ├── GET,POST /
│   ├── GET,PUT,DELETE /{id}/
│   ├── POST /bulk-import/
│   └── GET /export/
├── categories/
│   ├── GET,POST /
│   ├── GET,PUT,DELETE /{id}/
│   └── GET /tree/
├── budgets/
│   ├── GET,POST /
│   ├── GET,PUT,DELETE /{id}/
│   └── GET /summary/
└── analytics/
    ├── GET /spending-trends/
    ├── GET /category-breakdown/
    └── GET /budget-performance/
```

### Response Format

```json
{
  "success": true,
  "data": {
    "id": 123,
    "amount": "25.50",
    "currency": "USD",
    "description": "Coffee at Starbucks",
    "category": {
      "id": 5,
      "name": "Food & Drinks",
      "color": "#EF4444"
    },
    "date": "2025-06-03",
    "created_at": "2025-06-03T10:30:00Z"
  },
  "meta": {
    "timestamp": "2025-06-03T10:30:00Z",
    "version": "1.0"
  }
}
```

## Security Implementation

### Authentication & Authorization

```python
# settings/security.py
AUTHENTICATION_BACKENDS = [
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"]

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
```

### Data Protection & PII Security

```python
# utils/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models
import json

class PIIFieldEncryption:
    """
    Dedicated encryption for PII fields with key rotation support
    """
    def __init__(self):
        self.primary_key = settings.PII_ENCRYPTION_KEY
        self.cipher = Fernet(self.primary_key)
        # Support for key rotation
        self.old_keys = getattr(settings, 'PII_OLD_ENCRYPTION_KEYS', [])

    def encrypt(self, data):
        if data is None or data == '':
            return data
        return self.cipher.encrypt(str(data).encode()).decode()

    def decrypt(self, encrypted_data):
        if encrypted_data is None or encrypted_data == '':
            return encrypted_data

        # Try primary key first
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # Try old keys for migration scenarios
            for old_key in self.old_keys:
                try:
                    old_cipher = Fernet(old_key)
                    decrypted = old_cipher.decrypt(encrypted_data.encode()).decode()
                    # Re-encrypt with new key
                    return self.encrypt(decrypted)
                except Exception:
                    continue
            raise ValueError("Unable to decrypt PII data")

# Custom encrypted field types
class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        self.encryptor = PIIFieldEncryption()
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encryptor.decrypt(value)

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        return self.encryptor.encrypt(value)

class EncryptedDecimalField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        self.encryptor = PIIFieldEncryption()
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        decrypted = self.encryptor.decrypt(value)
        return Decimal(decrypted) if decrypted else None

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryptor.encrypt(str(value))

class EncryptedTextField(models.TextField):
    def __init__(self, *args, **kwargs):
        self.encryptor = PIIFieldEncryption()
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encryptor.decrypt(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        return self.encryptor.encrypt(value)

# utils/pii_utils.py
import re
from django.conf import settings

class PIIDetector:
    """
    Detect and mask PII in logs and non-production environments
    """

    # Regex patterns for common PII
    PATTERNS = {
        'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone': re.compile(r'\b\d{3}[- ]?\d{3}[- ]?\d{4}\b'),
        'account_number': re.compile(r'\b\d{8,17}\b'),
    }

    @classmethod
    def mask_pii(cls, text):
        """Mask PII in text for logging"""
        if not text:
            return text

        masked_text = str(text)
        for pii_type, pattern in cls.PATTERNS.items():
            masked_text = pattern.sub(f'[MASKED_{pii_type.upper()}]', masked_text)

        return masked_text

    @classmethod
    def contains_pii(cls, text):
        """Check if text contains PII"""
        if not text:
            return False

        for pattern in cls.PATTERNS.values():
            if pattern.search(str(text)):
                return True
        return False

# middleware/audit_middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from audit.models import AuditLog
import json

class PIIAuditMiddleware(MiddlewareMixin):
    """
    Middleware to log all PII access and modifications
    """

    def process_request(self, request):
        request.pii_accessed = []
        return None

    def process_response(self, request, response):
        # Log PII access if any occurred
        if hasattr(request, 'pii_accessed') and request.pii_accessed:
            if not isinstance(request.user, AnonymousUser):
                AuditLog.objects.create(
                    user=request.user,
                    action='ACCESS',
                    model_name='PII_FIELDS',
                    object_id='multiple',
                    pii_fields_accessed=request.pii_accessed,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                )
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# utils/data_masking.py
class DataMasker:
    """
    Mask PII data in non-production environments
    """

    @staticmethod
    def mask_for_environment():
        """Mask PII data based on environment"""
        if not settings.DEBUG and settings.ENVIRONMENT != 'production':
            # Development/staging environment - mask real PII
            from django.contrib.auth import get_user_model
            from expenses.models import Transaction

            User = get_user_model()

            # Mask user PII
            for user in User.objects.all():
                if user.phone:
                    user.phone = 'XXX-XXX-' + user.phone[-4:] if len(user.phone) >= 4 else 'XXX-XXX-XXXX'
                if user.email and '@' in user.email:
                    local, domain = user.email.split('@', 1)
                    user.email = f"{local[:2]}***@{domain}"
                user.save()

            # Mask transaction descriptions that might contain merchant names/locations
            Transaction.objects.filter(
                description__icontains='personal'
            ).update(description='[MASKED PERSONAL TRANSACTION]')
```

## Frontend Architecture

### TypeScript Architecture

```typescript
// types/api.ts - Type definitions for API responses
export interface User {
    id: number;
    email: string;
    phone: string;
    timezone: string;
    currency: string;
    created_at: string;
}

export interface Transaction {
    id: number;
    user: number;
    category: Category;
    amount: string; // Decimal as string from Django
    currency: string;
    transaction_type: 'expense' | 'income' | 'transfer';
    description: string;
    notes: string;
    date: string; // ISO date string
    receipt?: string; // URL to receipt file
    created_at: string;
    updated_at: string;
}

export interface Category {
    id: number;
    name: string;
    parent?: Category;
    icon: string;
    color: string;
    is_active: boolean;
}

export interface Budget {
    id: number;
    category: Category;
    amount: string;
    period_start: string;
    period_end: string;
    spent_amount: string; // Calculated field
    remaining_amount: string; // Calculated field
    is_active: boolean;
}

export interface APIResponse<T> {
    success: boolean;
    data: T;
    meta: {
        timestamp: string;
        version: string;
    };
}

export interface APIError {
    success: false;
    error: {
        code: string;
        message: string;
        details?: Record<string, string[]>;
    };
}

// utils/api-client.ts - Type-safe API client
class APIClient {
    private baseURL: string = '/api/v1';
    private csrfToken: string;

    constructor() {
        const csrfElement = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
        if (!csrfElement) {
            throw new Error('CSRF token not found');
        }
        this.csrfToken = csrfElement.value;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<APIResponse<T>> {
        const config: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);

            if (!response.ok) {
                const errorData: APIError = await response.json();
                throw new APIError(errorData.error.message, errorData.error.code);
            }

            return await response.json() as APIResponse<T>;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async getTransactions(params?: {
        page?: number;
        category?: number;
        date_from?: string;
        date_to?: string;
    }): Promise<APIResponse<Transaction[]>> {
        const queryString = params ? '?' + new URLSearchParams(
            Object.entries(params).map(([k, v]) => [k, String(v)])
        ).toString() : '';

        return this.request<Transaction[]>(`/transactions/${queryString}`);
    }

    async createTransaction(data: Omit<Transaction, 'id' | 'user' | 'created_at' | 'updated_at'>): Promise<APIResponse<Transaction>> {
        return this.request<Transaction>('/transactions/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateTransaction(id: number, data: Partial<Transaction>): Promise<APIResponse<Transaction>> {
        return this.request<Transaction>(`/transactions/${id}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteTransaction(id: number): Promise<APIResponse<null>> {
        return this.request<null>(`/transactions/${id}/`, {
            method: 'DELETE'
        });
    }
}

// Custom error class for API errors
export class APIError extends Error {
    constructor(
        message: string,
        public code: string,
        public details?: Record<string, string[]>
    ) {
        super(message);
        this.name = 'APIError';
    }
}

// utils/currency-formatter.ts - Type-safe currency formatting
export class CurrencyFormatter {
    private formatter: Intl.NumberFormat;

    constructor(private currency: string = 'USD', private locale: string = 'en-US') {
        this.formatter = new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    format(amount: string | number): string {
        const numericAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

        if (isNaN(numericAmount)) {
            throw new Error(`Invalid amount: ${amount}`);
        }

        return this.formatter.format(numericAmount);
    }

    parse(formattedAmount: string): number {
        // Remove currency symbols and spaces, handle locale-specific formatting
        const cleaned = formattedAmount
            .replace(/[$,\s]/g, '')
            .replace(/[^\d.-]/g, '');

        const parsed = parseFloat(cleaned);

        if (isNaN(parsed)) {
            throw new Error(`Cannot parse currency amount: ${formattedAmount}`);
        }

        return parsed;
    }
}

// components/transaction-form.ts - Type-safe form handling
export class TransactionForm {
    private form: HTMLFormElement;
    private apiClient: APIClient;
    private currencyFormatter: CurrencyFormatter;

    constructor(formSelector: string) {
        const form = document.querySelector(formSelector) as HTMLFormElement;
        if (!form) {
            throw new Error(`Form not found: ${formSelector}`);
        }

        this.form = form;
        this.apiClient = new APIClient();
        this.currencyFormatter = new CurrencyFormatter();

        this.bindEvents();
    }

    private bindEvents(): void {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));

        const amountInput = this.form.querySelector('[name="amount"]') as HTMLInputElement;
        if (amountInput) {
            amountInput.addEventListener('blur', this.formatAmount.bind(this));
        }
    }

    private async handleSubmit(event: Event): Promise<void> {
        event.preventDefault();

        try {
            const formData = new FormData(this.form);
            const transactionData = this.validateAndTransformFormData(formData);

            const response = await this.apiClient.createTransaction(transactionData);

            if (response.success) {
                this.showSuccess('Transaction created successfully');
                this.form.reset();
                // Trigger page refresh or update UI
                window.dispatchEvent(new CustomEvent('transactionCreated', {
                    detail: response.data
                }));
            }
        } catch (error) {
            if (error instanceof APIError) {
                this.showErrors(error.details || { general: [error.message] });
            } else {
                this.showErrors({ general: ['An unexpected error occurred'] });
            }
        }
    }

    private validateAndTransformFormData(formData: FormData): Omit<Transaction, 'id' | 'user' | 'created_at' | 'updated_at'> {
        const amount = formData.get('amount') as string;
        const description = formData.get('description') as string;
        const transactionType = formData.get('transaction_type') as Transaction['transaction_type'];
        const date = formData.get('date') as string;
        const categoryId = formData.get('category') as string;

        // Validate required fields
        if (!amount || !description || !transactionType || !date || !categoryId) {
            throw new APIError('All required fields must be filled', 'VALIDATION_ERROR');
        }

        // Validate amount
        const numericAmount = this.currencyFormatter.parse(amount);
        if (numericAmount <= 0 && transactionType === 'expense') {
            throw new APIError('Expense amount must be positive', 'VALIDATION_ERROR');
        }

        return {
            amount: numericAmount.toFixed(2),
            description: description.trim(),
            transaction_type: transactionType,
            date: date,
            category: { id: parseInt(categoryId) } as Category,
            notes: (formData.get('notes') as string || '').trim(),
            currency: 'USD' // TODO: Get from user preferences
        };
    }

    private formatAmount(event: Event): void {
        const input = event.target as HTMLInputElement;
        try {
            const parsed = this.currencyFormatter.parse(input.value);
            input.value = parsed.toFixed(2);
        } catch (error) {
            // Invalid input, let validation handle it
        }
    }

    private showSuccess(message: string): void {
        // Implementation for success notification
        console.log('Success:', message);
    }

    private showErrors(errors: Record<string, string[]>): void {
        // Implementation for error display
        console.error('Validation errors:', errors);
    }
}
```

## Docker Configuration

### Python Project Configuration

```toml
# pyproject.toml
[project]
name = "finance-dashboard"
version = "1.0.0"
description = "Personal Finance Dashboard with PII Protection"
authors = [
    {name = "Development Team", email = "dev@company.com"}
]
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.11"

dependencies = [
    "django>=5.2.1,<5.3",
    "djangorestframework>=3.14.0",
    "django-allauth>=0.57.0",
    "psycopg[binary]>=3.1.0",
    "redis>=5.0.0",
    "celery>=5.3.0",
    "django-cors-headers>=4.3.0",
    "django-ratelimit>=4.1.0",
    "cryptography>=41.0.0",
    "pillow>=10.0.0",
    "django-storages[s3]>=1.14.0",
    "boto3>=1.34.0",
    "django-crispy-forms>=2.1",
    "crispy-tailwind>=0.5.0",
    "gunicorn>=21.2.0",
    "python-magic>=0.4.27",
    "pytesseract>=0.3.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-django>=4.7.0",
    "pytest-cov>=4.1.0",
    "black>=23.9.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.6.0",
    "django-stubs>=4.2.0",
    "djangorestframework-stubs>=3.14.0",
    "factory-boy>=3.3.0",
    "coverage>=7.3.0",
    "bandit>=1.7.5",
    "safety>=2.3.0",
    "pre-commit>=3.5.0",
]

test = [
    "pytest>=7.4.0",
    "pytest-django>=4.7.0",
    "pytest-xdist>=3.3.0",
    "pytest-mock>=3.12.0",
    "freezegun>=1.2.2",
]

docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.4.0",
    "mkdocstrings[python]>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-django>=4.7.0",
    "pytest-cov>=4.1.0",
    "black>=23.9.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.6.0",
    "django-stubs>=4.2.0",
    "factory-boy>=3.3.0",
    "coverage>=7.3.0",
    "bandit>=1.7.5",
    "safety>=2.3.0",
    "pre-commit>=3.5.0",
]

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM base as dependencies

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as production

RUN adduser --disabled-password --no-create-home django

WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

COPY . .
RUN python manage.py collectstatic --noinput

USER django

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: finance_dashboard
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/finance_dashboard
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - media_data:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - media_data:/app/media
    depends_on:
      - web

  celery:
    build: .
    command: celery -A config worker -l info
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/finance_dashboard
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
  media_data:
```

## Development Methodology

### Test-Driven Development (TDD) Approach

This project **mandates Test-Driven Development** for all features. Every component must be built following the Red-Green-Refactor cycle to ensure reliability, maintainability, and confidence in the financial data handling.

#### TDD Workflow
1. **Red:** Write a failing test that defines the desired behavior
2. **Green:** Write the minimum code to make the test pass
3. **Refactor:** Improve the code while keeping tests green
4. **Repeat:** Continue for each small feature increment

#### TDD Implementation Strategy

**Phase 1: Core Models (Week 1)**
```python
# tests/test_models/test_user_model.py
class TestUserModel(TestCase):
    def test_user_creation_with_encrypted_phone(self):
        """Test that user phone numbers are encrypted in database"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone='555-123-4567',
            password='testpass123'
        )

        # Verify phone is encrypted in database
        raw_phone = User.objects.extra(
            select={'raw_phone': 'phone'}
        ).get(id=user.id).raw_phone

        self.assertNotEqual(raw_phone, '555-123-4567')
        self.assertEqual(user.phone, '555-123-4567')  # Decrypted access

    def test_user_phone_encryption_with_empty_value(self):
        """Test encryption handles empty phone numbers"""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            phone='',
            password='testpass123'
        )
        self.assertEqual(user.phone, '')

# tests/test_models/test_transaction_model.py
class TestTransactionModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )

    def test_transaction_amount_encryption(self):
        """Test that transaction amounts are encrypted"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('123.45'),
            transaction_type='expense',
            description='Test purchase',
            date='2025-06-03'
        )

        # Verify amount is encrypted in database
        raw_amount = Transaction.objects.extra(
            select={'raw_amount': 'amount'}
        ).get(id=transaction.id).raw_amount

        self.assertNotEqual(raw_amount, '123.45')
        self.assertEqual(transaction.amount, Decimal('123.45'))

    def test_transaction_notes_encryption(self):
        """Test that transaction notes are encrypted"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.00'),
            transaction_type='expense',
            description='Coffee',
            notes='Met with John about project',
            date='2025-06-03'
        )

        self.assertEqual(transaction.notes, 'Met with John about project')

    def test_transaction_validation(self):
        """Test transaction field validation"""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user,
                category=self.category,
                amount=Decimal('-123.45'),  # Negative amount should fail
                transaction_type='expense',
                description='',  # Empty description should fail
                date='2025-06-03'
            )
            transaction.full_clean()
```

**Phase 2: API Endpoints (Week 2)**
```python
# tests/test_api/test_transaction_api.py
class TestTransactionAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transaction_success(self):
        """Test successful transaction creation via API"""
        data = {
            'amount': '25.50',
            'description': 'Coffee at Starbucks',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id,
            'notes': 'Morning coffee'
        }

        response = self.client.post('/api/v1/transactions/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.count(), 1)

        transaction = Transaction.objects.first()
        self.assertEqual(transaction.amount, Decimal('25.50'))
        self.assertEqual(transaction.description, 'Coffee at Starbucks')
        self.assertEqual(transaction.user, self.user)

    def test_create_transaction_validates_amount(self):
        """Test that API validates transaction amounts"""
        data = {
            'amount': '-25.50',  # Negative amount
            'description': 'Invalid transaction',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        response = self.client.post('/api/v1/transactions/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_user_can_only_access_own_transactions(self):
        """Test that users can only access their own transactions"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_category = Category.objects.create(name='Other', user=other_user)

        # Create transaction for other user
        other_transaction = Transaction.objects.create(
            user=other_user,
            category=other_category,
            amount=Decimal('100.00'),
            transaction_type='expense',
            description='Other user transaction',
            date='2025-06-03'
        )

        # Try to access other user's transaction
        response = self.client.get(f'/api/v1/transactions/{other_transaction.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

# tests/test_api/test_audit_logging.py
class TestAuditLogging(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_pii_access_is_logged(self):
        """Test that PII access is properly logged"""
        initial_audit_count = AuditLog.objects.count()

        # Access user profile (contains PII)
        response = self.client.get('/api/v1/users/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AuditLog.objects.count(), initial_audit_count + 1)

        audit_log = AuditLog.objects.latest('timestamp')
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'ACCESS')
        self.assertIn('phone', audit_log.pii_fields_accessed)
```

**Phase 3: Security Features (Week 3)**
```python
# tests/test_security/test_encryption.py
class TestPIIEncryption(TestCase):
    def setUp(self):
        self.encryptor = PIIFieldEncryption()

    def test_encrypt_decrypt_cycle(self):
        """Test that encryption/decryption preserves data"""
        original_data = "555-123-4567"

        encrypted = self.encryptor.encrypt(original_data)
        decrypted = self.encryptor.decrypt(encrypted)

        self.assertNotEqual(encrypted, original_data)
        self.assertEqual(decrypted, original_data)

    def test_encryption_handles_none_values(self):
        """Test encryption gracefully handles None values"""
        self.assertIsNone(self.encryptor.encrypt(None))
        self.assertIsNone(self.encryptor.decrypt(None))

    def test_encryption_key_rotation(self):
        """Test that old encrypted data can be decrypted with key rotation"""
        # This would test the key rotation functionality
        pass

# tests/test_security/test_pii_detection.py
class TestPIIDetection(TestCase):
    def test_detects_phone_numbers(self):
        """Test PII detector identifies phone numbers"""
        text = "Call me at 555-123-4567 tomorrow"
        self.assertTrue(PIIDetector.contains_pii(text))

        masked = PIIDetector.mask_pii(text)
        self.assertIn('[MASKED_PHONE]', masked)
        self.assertNotIn('555-123-4567', masked)

    def test_detects_credit_cards(self):
        """Test PII detector identifies credit card numbers"""
        text = "My card number is 4532-1234-5678-9012"
        self.assertTrue(PIIDetector.contains_pii(text))

        masked = PIIDetector.mask_pii(text)
        self.assertIn('[MASKED_CREDIT_CARD]', masked)

    def test_handles_clean_text(self):
        """Test PII detector handles text without PII"""
        text = "This is a clean message with no sensitive data"
        self.assertFalse(PIIDetector.contains_pii(text))
        self.assertEqual(PIIDetector.mask_pii(text), text)

# tests/test_security/test_file_security.py
class TestFileSecurityScanning(TestCase):
    def setUp(self):
        self.scanner = PIIFileScanner()

    @patch('pytesseract.image_to_string')
    def test_receipt_scanning_detects_account_numbers(self, mock_ocr):
        """Test that receipt scanning detects PII in images"""
        mock_ocr.return_value = "Account: 1234567890123456\nAmount: $25.50"

        # Create a test image file
        test_image_path = 'test_receipt.jpg'

        findings = self.scanner.scan_receipt(test_image_path)

        self.assertTrue(findings['pii_detected'])
        self.assertIn('account_number', findings['pii_types'])
        self.assertEqual(findings['risk_level'], 'high')
        self.assertTrue(findings['redaction_needed'])
```

**Phase 4: Frontend Integration (Week 4)**
```python
# tests/test_frontend/test_transaction_form.py
class TestTransactionForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Food', user=self.user)

    def test_transaction_form_validation(self):
        """Test transaction form validates input correctly"""
        form_data = {
            'amount': '25.50',
            'description': 'Coffee',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        form = TransactionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_rejects_negative_amounts_for_expenses(self):
        """Test form validation rejects negative expense amounts"""
        form_data = {
            'amount': '-25.50',
            'description': 'Invalid',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        form = TransactionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

# tests/test_frontend/test_dashboard_views.py
class TestDashboardViews(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_requires_authentication(self):
        """Test dashboard redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/auth/login/?next=/dashboard/')

    def test_dashboard_shows_user_transactions(self):
        """Test dashboard displays user's transactions"""
        # Create test data
        category = Category.objects.create(name='Food', user=self.user)
        Transaction.objects.create(
            user=self.user,
            category=category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Coffee',
            date='2025-06-03'
        )

        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coffee')
        self.assertContains(response, '$25.50')
```

### TDD Test Coverage Requirements

**Mandatory Test Coverage by Component:**

#### Models (95% coverage required)
- [ ] User model encryption/decryption
- [ ] Transaction CRUD operations
- [ ] Category hierarchical relationships
- [ ] Budget calculations and validations
- [ ] Audit log creation and queries
- [ ] Data retention policy enforcement

#### API Endpoints (90% coverage required)
- [ ] Authentication and authorization
- [ ] CRUD operations for all resources
- [ ] Input validation and error handling
- [ ] Rate limiting functionality
- [ ] Response format consistency
- [ ] Cross-user data isolation

#### Security Features (100% coverage required)
- [ ] PII encryption/decryption cycles
- [ ] Audit logging for all PII access
- [ ] File upload security scanning
- [ ] Data masking in non-production
- [ ] GDPR compliance operations
- [ ] Session security and timeout

#### Frontend Components (85% coverage required)
- [ ] Form validation and submission
- [ ] Chart rendering with real data
- [ ] User interaction workflows
- [ ] Error handling and display
- [ ] Responsive design breakpoints

#### Integration Tests (80% coverage required)
- [ ] End-to-end user workflows
- [ ] Database transaction integrity
- [ ] File upload and processing
- [ ] Email notifications
- [ ] Background task processing

### TDD Development Workflow

#### Daily TDD Cycle
```bash
# 1. Start with failing test
python manage.py test tests.test_models.test_user_model.TestUserModel.test_user_creation_with_encrypted_phone --keepdb --debug-mode

# 2. Write minimum code to pass
# Edit models.py, add EncryptedCharField

# 3. Run test again (should pass)
python manage.py test tests.test_models.test_user_model.TestUserModel.test_user_creation_with_encrypted_phone --keepdb

# 4. Refactor and run full test suite
python manage.py test tests.test_models --keepdb

# 5. Check coverage
coverage run --source='.' manage.py test
coverage report --show-missing
```

#### Test Organization Structure
```
tests/
├── __init__.py
├── test_models/
│   ├── __init__.py
│   ├── test_user_model.py
│   ├── test_transaction_model.py
│   ├── test_category_model.py
│   └── test_budget_model.py
├── test_api/
│   ├── __init__.py
│   ├── test_auth_api.py
│   ├── test_transaction_api.py
│   ├── test_category_api.py
│   ├── test_budget_api.py
│   └── test_analytics_api.py
├── test_security/
│   ├── __init__.py
│   ├── test_encryption.py
│   ├── test_pii_detection.py
│   ├── test_audit_logging.py
│   ├── test_file_security.py
│   └── test_compliance.py
├── test_frontend/
│   ├── __init__.py
│   ├── test_forms.py
│   ├── test_views.py
│   ├── test_templates.py
│   └── test_javascript.py
├── test_integration/
│   ├── __init__.py
│   ├── test_user_workflows.py
│   ├── test_file_processing.py
│   ├── test_background_tasks.py
│   └── test_performance.py
└── fixtures/
    ├── users.json
    ├── categories.json
    └── transactions.json
```

#### Continuous Testing Setup
```python
# conftest.py - pytest configuration
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from expenses.models import Category, Transaction
from decimal import Decimal

User = get_user_model()

@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def category(user):
    """Create a test category"""
    return Category.objects.create(
        name='Test Category',
        user=user
    )

@pytest.fixture
def transaction(user, category):
    """Create a test transaction"""
    return Transaction.objects.create(
        user=user,
        category=category,
        amount=Decimal('25.50'),
        transaction_type='expense',
        description='Test transaction',
        date='2025-06-03'
    )

# settings/testing.py - Test-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_finance_dashboard',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'test_finance_dashboard',
        }
    }
}

# Disable encryption in tests for easier debugging
PII_ENCRYPTION_KEY = Fernet.generate_key()

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
```

### Test Strategy

```python
# tests/test_models.py
import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from expenses.models import Category, Transaction

User = get_user_model()

class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Lunch',
            date='2025-06-03'
        )
        self.assertEqual(transaction.amount, Decimal('25.50'))
        self.assertEqual(transaction.user, self.user)

    def test_transaction_str_representation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Lunch',
            date='2025-06-03'
        )
        expected = f"Lunch - $25.50 ({self.category.name})"
        self.assertEqual(str(transaction), expected)

# tests/test_api.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

class TransactionAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transaction(self):
        data = {
            'amount': '25.50',
            'description': 'Coffee',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }
        response = self.client.post('/api/v1/transactions/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### Performance Testing

```python
# tests/test_performance.py
import time
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import cache

class PerformanceTest(TestCase):
    def test_transaction_list_performance(self):
        # Create test data
        start_time = time.time()
        response = self.client.get('/api/v1/transactions/')
        end_time = time.time()

        response_time = end_time - start_time
        self.assertLess(response_time, 0.5, "API response time should be under 500ms")
        self.assertEqual(response.status_code, 200)
```

## Deployment Pipeline

### CI/CD Configuration

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.11

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        python manage.py test
        coverage run --source='.' manage.py test
        coverage report --fail-under=80

    - name: Run security checks
      run: |
        bandit -r . -x tests/
        safety check

    - name: Run linting
      run: |
        black --check .
        flake8 .
        isort --check-only .

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t finance-dashboard:${{ github.sha }} .
        docker tag finance-dashboard:${{ github.sha }} finance-dashboard:latest
```

## Monitoring & Observability

### Logging Configuration

```python
# settings/logging.py
import logging
from utils.pii_utils import PIIDetector

class PIISafeFormatter(logging.Formatter):
    """
    Custom formatter that masks PII in log messages
    """
    def format(self, record):
        # Mask PII in the log message
        if hasattr(record, 'msg') and record.msg:
            record.msg = PIIDetector.mask_pii(record.msg)

        # Mask PII in arguments
        if hasattr(record, 'args') and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, (str, int, float)):
                    masked_args.append(PIIDetector.mask_pii(str(arg)))
                else:
                    masked_args.append(arg)
            record.args = tuple(masked_args)

        return super().format(record)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json_pii_safe': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'pii_safe': {
            '()': PIISafeFormatter,
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'pii_safe',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json_pii_safe',
        },
        'security': {
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'formatter': 'json_pii_safe',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'pii_access': {
            'handlers': ['security', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'expenses': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Health Checks

```python
# health/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        health_status['checks']['cache'] = 'healthy'
    except Exception as e:
        health_status['checks']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

## Project Structure

```
finance-dashboard/
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── __init__.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests/
│   ├── expenses/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests/
│   ├── budgets/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests/
│   └── analytics/
│       ├── __init__.py
│       ├── views.py
│       ├── serializers.py
│       ├── urls.py
│       └── tests/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── transactions/
│   └── budgets/
├── utils/
│   ├── __init__.py
│   ├── encryption.py
│   ├── validators.py
│   └── permissions.py
├── scripts/
│   ├── init.sql
│   ├── backup.sh
│   └── deploy.sh
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── contributing.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── manage.py
├── .env.example
├── .gitignore
├── .dockerignore
├── README.md
└── LICENSE
```

## Implementation Timeline

### Implementation Timeline with TDD

### Phase 1: Core Foundation with TDD (Week 1)

**Day 1-2: User Model & Authentication**
- Write tests for user creation, encryption, authentication
- Implement encrypted user fields (phone, profile data)
- Build authentication views with test coverage
- Target: 95% model coverage, 90% auth coverage

**Day 3-4: Category System**
- Test hierarchical category relationships
- Implement category CRUD with user isolation
- Build category API endpoints
- Target: 95% category model coverage

**Day 5-7: Basic Transaction Model**
- Test transaction encryption, validation, relationships
- Implement transaction CRUD operations
- Add basic transaction API endpoints
- Target: 95% transaction model coverage

### Phase 2: API Development with TDD (Week 2)

**Day 8-10: Transaction API**
- Test all CRUD operations, validation, filtering
- Implement transaction list/create/update/delete endpoints
- Add pagination, sorting, search functionality
- Target: 90% API endpoint coverage

**Day 11-12: Security & Audit Logging**
- Test PII access logging, audit trail creation
- Implement audit middleware and logging systems
- Add security headers and rate limiting
- Target: 100% security feature coverage

**Day 13-14: File Upload & Processing**
- Test file validation, PII scanning, secure storage
- Implement receipt upload with security scanning
- Add file management and cleanup
- Target: 90% file processing coverage

### Phase 3: Advanced Features with TDD (Week 3)

**Day 15-17: Budget System**
- Test budget calculations, period validation, alerts
- Implement budget CRUD operations and tracking
- Add budget vs. actual spending analytics
- Target: 95% budget system coverage

**Day 18-19: Analytics & Reporting**
- Test chart data generation, filtering, performance
- Implement analytics endpoints and calculations
- Add report generation and export functionality
- Target: 85% analytics coverage

**Day 20-21: Data Import/Export**
- Test CSV parsing, validation, bulk operations
- Implement import/export functionality
- Add data transformation and error handling
- Target: 90% import/export coverage

### Phase 4: Frontend & Integration with TDD (Week 4)

**Day 22-24: Frontend Components**
- Test form validation, user interactions, error handling
- Implement responsive UI with HTMX interactions
- Add chart visualization and real-time updates
- Target: 85% frontend coverage

**Day 25-26: Integration Testing**
- Test complete user workflows end-to-end
- Implement performance optimizations
- Add comprehensive error handling
- Target: 80% integration coverage

**Day 27-28: Production Readiness**
- Test deployment pipeline, monitoring, health checks
- Implement CI/CD with automated testing
- Add comprehensive documentation
- Target: Overall 90% coverage

### TDD Success Metrics

**Code Quality Gates:**
- [ ] All tests must pass before any commit
- [ ] Minimum coverage thresholds enforced by CI
- [ ] No production deployment without test coverage
- [ ] Automated testing in pull request workflow

**Daily TDD Metrics:**
- Tests written before implementation: 100%
- Test coverage maintained above thresholds
- Red-Green-Refactor cycles documented
- Test execution time under 2 minutes for full suite

## Risk Assessment

### Technical Risks
- **Database Performance:** Large transaction datasets may impact query performance
  - *Mitigation:* Implement proper indexing, pagination, and caching
- **Security Vulnerabilities:** Financial data requires high security standards
  - *Mitigation:* Regular security audits, penetration testing, OWASP compliance
- **Data Loss:** User financial data is critical
  - *Mitigation:* Automated backups, transaction logs, disaster recovery plan

### Business Risks
- **User Adoption:** Competition with established financial apps
  - *Mitigation:* Focus on simplicity, security, and unique features
- **Scalability:** Growing user base may outpace infrastructure
  - *Mitigation:* Cloud-native architecture, horizontal scaling design

## Success Criteria

### Technical Excellence
- [ ] 90%+ test coverage
- [ ] Sub-500ms API response times
- [ ] Zero critical security vulnerabilities
- [ ] 99.5% uptime in production

### User Experience
- [ ] Intuitive navigation and workflow
- [ ] Mobile-responsive design
- [ ] Fast page load times
- [ ] Accessibility compliance (WCAG 2.1 AA)

### Code Quality
- [ ] Clean, documented, maintainable code
- [ ] Consistent coding standards
- [ ] Comprehensive API documentation
- [ ] Effective error handling and logging

This PRD serves as a comprehensive guide for building a production-ready personal finance dashboard that demonstrates full-stack development expertise while solving real user problems in financial management.
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | migrations
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_django = "django"
known_first_party = ["apps", "config", "utils"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "DJANGO", "FIRSTPARTY", "LOCALFOLDER"]

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
ignore_missing_imports = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unused_configs = true
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "config.settings.development"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.testing"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
addopts = [
    "--strict-markers",
    "--disable-warnings",
    "--reuse-db",
    "--cov=apps",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=90",
]

[tool.coverage.run]
source = ["apps"]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/venv/*",
    "manage.py",
    "config/wsgi.py",
    "config/asgi.py",
]

[tool.bandit]
exclude_dirs = ["tests", "migrations"]
skips = ["B101", "B601"]  # Skip assert_used and shell=True in tests
```

### Development Workflow with uv

```bash
# Project initialization
uv init finance-dashboard
cd finance-dashboard

# Add dependencies
uv add django djangorestframework psycopg[binary]
uv add --dev pytest pytest-django black isort mypy

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install all dependencies
uv sync

# Run development server
uv run python manage.py runserver

# Run tests with coverage
uv run pytest

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy .

# Security scanning
uv run bandit -r apps/
uv run safety check

# Add new dependency
uv add redis celery

# Add development dependency
uv add --dev factory-boy

# Update all dependencies
uv lock --upgrade

# Export for Docker (if needed)
uv export --format requirements-txt --output-file requirements.txt
```

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM base as dependencies

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as production

RUN adduser --disabled-password --no-create-home django

WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

COPY . .
RUN python manage.py collectstatic --noinput

USER django

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: finance_dashboard
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/finance_dashboard
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - media_data:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - media_data:/app/media
    depends_on:
      - web

  celery:
    build: .
    command: celery -A config worker -l info
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/finance_dashboard
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
  media_data:
```

## Development Methodology

### Test-Driven Development (TDD) Approach

This project **mandates Test-Driven Development** for all features. Every component must be built following the Red-Green-Refactor cycle to ensure reliability, maintainability, and confidence in the financial data handling.

#### TDD Workflow
1. **Red:** Write a failing test that defines the desired behavior
2. **Green:** Write the minimum code to make the test pass
3. **Refactor:** Improve the code while keeping tests green
4. **Repeat:** Continue for each small feature increment

#### TDD Implementation Strategy

**Phase 1: Core Models (Week 1)**
```python
# tests/test_models/test_user_model.py
class TestUserModel(TestCase):
    def test_user_creation_with_encrypted_phone(self):
        """Test that user phone numbers are encrypted in database"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone='555-123-4567',
            password='testpass123'
        )

        # Verify phone is encrypted in database
        raw_phone = User.objects.extra(
            select={'raw_phone': 'phone'}
        ).get(id=user.id).raw_phone

        self.assertNotEqual(raw_phone, '555-123-4567')
        self.assertEqual(user.phone, '555-123-4567')  # Decrypted access

    def test_user_phone_encryption_with_empty_value(self):
        """Test encryption handles empty phone numbers"""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            phone='',
            password='testpass123'
        )
        self.assertEqual(user.phone, '')

# tests/test_models/test_transaction_model.py
class TestTransactionModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )

    def test_transaction_amount_encryption(self):
        """Test that transaction amounts are encrypted"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('123.45'),
            transaction_type='expense',
            description='Test purchase',
            date='2025-06-03'
        )

        # Verify amount is encrypted in database
        raw_amount = Transaction.objects.extra(
            select={'raw_amount': 'amount'}
        ).get(id=transaction.id).raw_amount

        self.assertNotEqual(raw_amount, '123.45')
        self.assertEqual(transaction.amount, Decimal('123.45'))

    def test_transaction_notes_encryption(self):
        """Test that transaction notes are encrypted"""
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.00'),
            transaction_type='expense',
            description='Coffee',
            notes='Met with John about project',
            date='2025-06-03'
        )

        self.assertEqual(transaction.notes, 'Met with John about project')

    def test_transaction_validation(self):
        """Test transaction field validation"""
        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user,
                category=self.category,
                amount=Decimal('-123.45'),  # Negative amount should fail
                transaction_type='expense',
                description='',  # Empty description should fail
                date='2025-06-03'
            )
            transaction.full_clean()
```

**Phase 2: API Endpoints (Week 2)**
```python
# tests/test_api/test_transaction_api.py
class TestTransactionAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transaction_success(self):
        """Test successful transaction creation via API"""
        data = {
            'amount': '25.50',
            'description': 'Coffee at Starbucks',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id,
            'notes': 'Morning coffee'
        }

        response = self.client.post('/api/v1/transactions/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Transaction.objects.count(), 1)

        transaction = Transaction.objects.first()
        self.assertEqual(transaction.amount, Decimal('25.50'))
        self.assertEqual(transaction.description, 'Coffee at Starbucks')
        self.assertEqual(transaction.user, self.user)

    def test_create_transaction_validates_amount(self):
        """Test that API validates transaction amounts"""
        data = {
            'amount': '-25.50',  # Negative amount
            'description': 'Invalid transaction',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        response = self.client.post('/api/v1/transactions/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_user_can_only_access_own_transactions(self):
        """Test that users can only access their own transactions"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_category = Category.objects.create(name='Other', user=other_user)

        # Create transaction for other user
        other_transaction = Transaction.objects.create(
            user=other_user,
            category=other_category,
            amount=Decimal('100.00'),
            transaction_type='expense',
            description='Other user transaction',
            date='2025-06-03'
        )

        # Try to access other user's transaction
        response = self.client.get(f'/api/v1/transactions/{other_transaction.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

# tests/test_api/test_audit_logging.py
class TestAuditLogging(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_pii_access_is_logged(self):
        """Test that PII access is properly logged"""
        initial_audit_count = AuditLog.objects.count()

        # Access user profile (contains PII)
        response = self.client.get('/api/v1/users/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AuditLog.objects.count(), initial_audit_count + 1)

        audit_log = AuditLog.objects.latest('timestamp')
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'ACCESS')
        self.assertIn('phone', audit_log.pii_fields_accessed)
```

**Phase 3: Security Features (Week 3)**
```python
# tests/test_security/test_encryption.py
class TestPIIEncryption(TestCase):
    def setUp(self):
        self.encryptor = PIIFieldEncryption()

    def test_encrypt_decrypt_cycle(self):
        """Test that encryption/decryption preserves data"""
        original_data = "555-123-4567"

        encrypted = self.encryptor.encrypt(original_data)
        decrypted = self.encryptor.decrypt(encrypted)

        self.assertNotEqual(encrypted, original_data)
        self.assertEqual(decrypted, original_data)

    def test_encryption_handles_none_values(self):
        """Test encryption gracefully handles None values"""
        self.assertIsNone(self.encryptor.encrypt(None))
        self.assertIsNone(self.encryptor.decrypt(None))

    def test_encryption_key_rotation(self):
        """Test that old encrypted data can be decrypted with key rotation"""
        # This would test the key rotation functionality
        pass

# tests/test_security/test_pii_detection.py
class TestPIIDetection(TestCase):
    def test_detects_phone_numbers(self):
        """Test PII detector identifies phone numbers"""
        text = "Call me at 555-123-4567 tomorrow"
        self.assertTrue(PIIDetector.contains_pii(text))

        masked = PIIDetector.mask_pii(text)
        self.assertIn('[MASKED_PHONE]', masked)
        self.assertNotIn('555-123-4567', masked)

    def test_detects_credit_cards(self):
        """Test PII detector identifies credit card numbers"""
        text = "My card number is 4532-1234-5678-9012"
        self.assertTrue(PIIDetector.contains_pii(text))

        masked = PIIDetector.mask_pii(text)
        self.assertIn('[MASKED_CREDIT_CARD]', masked)

    def test_handles_clean_text(self):
        """Test PII detector handles text without PII"""
        text = "This is a clean message with no sensitive data"
        self.assertFalse(PIIDetector.contains_pii(text))
        self.assertEqual(PIIDetector.mask_pii(text), text)

# tests/test_security/test_file_security.py
class TestFileSecurityScanning(TestCase):
    def setUp(self):
        self.scanner = PIIFileScanner()

    @patch('pytesseract.image_to_string')
    def test_receipt_scanning_detects_account_numbers(self, mock_ocr):
        """Test that receipt scanning detects PII in images"""
        mock_ocr.return_value = "Account: 1234567890123456\nAmount: $25.50"

        # Create a test image file
        test_image_path = 'test_receipt.jpg'

        findings = self.scanner.scan_receipt(test_image_path)

        self.assertTrue(findings['pii_detected'])
        self.assertIn('account_number', findings['pii_types'])
        self.assertEqual(findings['risk_level'], 'high')
        self.assertTrue(findings['redaction_needed'])
```

**Phase 4: Frontend Integration (Week 4)**
```python
# tests/test_frontend/test_transaction_form.py
class TestTransactionForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Food', user=self.user)

    def test_transaction_form_validation(self):
        """Test transaction form validates input correctly"""
        form_data = {
            'amount': '25.50',
            'description': 'Coffee',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        form = TransactionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_rejects_negative_amounts_for_expenses(self):
        """Test form validation rejects negative expense amounts"""
        form_data = {
            'amount': '-25.50',
            'description': 'Invalid',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }

        form = TransactionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

# tests/test_frontend/test_dashboard_views.py
class TestDashboardViews(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_requires_authentication(self):
        """Test dashboard redirects unauthenticated users"""
        self.client.logout()
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/auth/login/?next=/dashboard/')

    def test_dashboard_shows_user_transactions(self):
        """Test dashboard displays user's transactions"""
        # Create test data
        category = Category.objects.create(name='Food', user=self.user)
        Transaction.objects.create(
            user=self.user,
            category=category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Coffee',
            date='2025-06-03'
        )

        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coffee')
        self.assertContains(response, '$25.50')
```

### TDD Test Coverage Requirements

**Mandatory Test Coverage by Component:**

#### Models (95% coverage required)
- [ ] User model encryption/decryption
- [ ] Transaction CRUD operations
- [ ] Category hierarchical relationships
- [ ] Budget calculations and validations
- [ ] Audit log creation and queries
- [ ] Data retention policy enforcement

#### API Endpoints (90% coverage required)
- [ ] Authentication and authorization
- [ ] CRUD operations for all resources
- [ ] Input validation and error handling
- [ ] Rate limiting functionality
- [ ] Response format consistency
- [ ] Cross-user data isolation

#### Security Features (100% coverage required)
- [ ] PII encryption/decryption cycles
- [ ] Audit logging for all PII access
- [ ] File upload security scanning
- [ ] Data masking in non-production
- [ ] GDPR compliance operations
- [ ] Session security and timeout

#### Frontend Components (85% coverage required)
- [ ] Form validation and submission
- [ ] Chart rendering with real data
- [ ] User interaction workflows
- [ ] Error handling and display
- [ ] Responsive design breakpoints

#### Integration Tests (80% coverage required)
- [ ] End-to-end user workflows
- [ ] Database transaction integrity
- [ ] File upload and processing
- [ ] Email notifications
- [ ] Background task processing

### TDD Development Workflow

#### Daily TDD Cycle
```bash
# 1. Start with failing test
python manage.py test tests.test_models.test_user_model.TestUserModel.test_user_creation_with_encrypted_phone --keepdb --debug-mode

# 2. Write minimum code to pass
# Edit models.py, add EncryptedCharField

# 3. Run test again (should pass)
python manage.py test tests.test_models.test_user_model.TestUserModel.test_user_creation_with_encrypted_phone --keepdb

# 4. Refactor and run full test suite
python manage.py test tests.test_models --keepdb

# 5. Check coverage
coverage run --source='.' manage.py test
coverage report --show-missing
```

#### Test Organization Structure
```
tests/
├── __init__.py
├── test_models/
│   ├── __init__.py
│   ├── test_user_model.py
│   ├── test_transaction_model.py
│   ├── test_category_model.py
│   └── test_budget_model.py
├── test_api/
│   ├── __init__.py
│   ├── test_auth_api.py
│   ├── test_transaction_api.py
│   ├── test_category_api.py
│   ├── test_budget_api.py
│   └── test_analytics_api.py
├── test_security/
│   ├── __init__.py
│   ├── test_encryption.py
│   ├── test_pii_detection.py
│   ├── test_audit_logging.py
│   ├── test_file_security.py
│   └── test_compliance.py
├── test_frontend/
│   ├── __init__.py
│   ├── test_forms.py
│   ├── test_views.py
│   ├── test_templates.py
│   └── test_javascript.py
├── test_integration/
│   ├── __init__.py
│   ├── test_user_workflows.py
│   ├── test_file_processing.py
│   ├── test_background_tasks.py
│   └── test_performance.py
└── fixtures/
    ├── users.json
    ├── categories.json
    └── transactions.json
```

#### Continuous Testing Setup
```python
# conftest.py - pytest configuration
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from expenses.models import Category, Transaction
from decimal import Decimal

User = get_user_model()

@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def category(user):
    """Create a test category"""
    return Category.objects.create(
        name='Test Category',
        user=user
    )

@pytest.fixture
def transaction(user, category):
    """Create a test transaction"""
    return Transaction.objects.create(
        user=user,
        category=category,
        amount=Decimal('25.50'),
        transaction_type='expense',
        description='Test transaction',
        date='2025-06-03'
    )

# settings/testing.py - Test-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_finance_dashboard',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'test_finance_dashboard',
        }
    }
}

# Disable encryption in tests for easier debugging
PII_ENCRYPTION_KEY = Fernet.generate_key()

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
```

### Test Strategy

```python
# tests/test_models.py
import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from expenses.models import Category, Transaction

User = get_user_model()

class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Lunch',
            date='2025-06-03'
        )
        self.assertEqual(transaction.amount, Decimal('25.50'))
        self.assertEqual(transaction.user, self.user)

    def test_transaction_str_representation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('25.50'),
            transaction_type='expense',
            description='Lunch',
            date='2025-06-03'
        )
        expected = f"Lunch - $25.50 ({self.category.name})"
        self.assertEqual(str(transaction), expected)

# tests/test_api.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

class TransactionAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transaction(self):
        data = {
            'amount': '25.50',
            'description': 'Coffee',
            'transaction_type': 'expense',
            'date': '2025-06-03',
            'category': self.category.id
        }
        response = self.client.post('/api/v1/transactions/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### Performance Testing

```python
# tests/test_performance.py
import time
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import cache

class PerformanceTest(TestCase):
    def test_transaction_list_performance(self):
        # Create test data
        start_time = time.time()
        response = self.client.get('/api/v1/transactions/')
        end_time = time.time()

        response_time = end_time - start_time
        self.assertLess(response_time, 0.5, "API response time should be under 500ms")
        self.assertEqual(response.status_code, 200)
```

## Deployment Pipeline

### CI/CD Configuration

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.11

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        python manage.py test
        coverage run --source='.' manage.py test
        coverage report --fail-under=80

    - name: Run security checks
      run: |
        bandit -r . -x tests/
        safety check

    - name: Run linting
      run: |
        black --check .
        flake8 .
        isort --check-only .

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t finance-dashboard:${{ github.sha }} .
        docker tag finance-dashboard:${{ github.sha }} finance-dashboard:latest
```

## Monitoring & Observability

### Logging Configuration

```python
# settings/logging.py
import logging
from utils.pii_utils import PIIDetector

class PIISafeFormatter(logging.Formatter):
    """
    Custom formatter that masks PII in log messages
    """
    def format(self, record):
        # Mask PII in the log message
        if hasattr(record, 'msg') and record.msg:
            record.msg = PIIDetector.mask_pii(record.msg)

        # Mask PII in arguments
        if hasattr(record, 'args') and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, (str, int, float)):
                    masked_args.append(PIIDetector.mask_pii(str(arg)))
                else:
                    masked_args.append(arg)
            record.args = tuple(masked_args)

        return super().format(record)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json_pii_safe': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'pii_safe': {
            '()': PIISafeFormatter,
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'pii_safe',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json_pii_safe',
        },
        'security': {
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
            'formatter': 'json_pii_safe',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'pii_access': {
            'handlers': ['security', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'expenses': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Health Checks

```python
# health/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        health_status['checks']['cache'] = 'healthy'
    except Exception as e:
        health_status['checks']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

## Project Structure

```
finance-dashboard/
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── __init__.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests/
│   ├── expenses/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests/
│   ├── budgets/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests/
│   └── analytics/
│       ├── __init__.py
│       ├── views.py
│       ├── serializers.py
│       ├── urls.py
│       └── tests/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── transactions/
│   └── budgets/
├── utils/
│   ├── __init__.py
│   ├── encryption.py
│   ├── validators.py
│   └── permissions.py
├── scripts/
│   ├── init.sql
│   ├── backup.sh
│   └── deploy.sh
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── contributing.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── manage.py
├── .env.example
├── .gitignore
├── .dockerignore
├── README.md
└── LICENSE
```

## Implementation Timeline

### Implementation Timeline with TDD

### Phase 1: Core Foundation with TDD (Week 1)

**Day 1-2: User Model & Authentication**
- Write tests for user creation, encryption, authentication
- Implement encrypted user fields (phone, profile data)
- Build authentication views with test coverage
- Target: 95% model coverage, 90% auth coverage

**Day 3-4: Category System**
- Test hierarchical category relationships
- Implement category CRUD with user isolation
- Build category API endpoints
- Target: 95% category model coverage

**Day 5-7: Basic Transaction Model**
- Test transaction encryption, validation, relationships
- Implement transaction CRUD operations
- Add basic transaction API endpoints
- Target: 95% transaction model coverage

### Phase 2: API Development with TDD (Week 2)

**Day 8-10: Transaction API**
- Test all CRUD operations, validation, filtering
- Implement transaction list/create/update/delete endpoints
- Add pagination, sorting, search functionality
- Target: 90% API endpoint coverage

**Day 11-12: Security & Audit Logging**
- Test PII access logging, audit trail creation
- Implement audit middleware and logging systems
- Add security headers and rate limiting
- Target: 100% security feature coverage

**Day 13-14: File Upload & Processing**
- Test file validation, PII scanning, secure storage
- Implement receipt upload with security scanning
- Add file management and cleanup
- Target: 90% file processing coverage

### Phase 3: Advanced Features with TDD (Week 3)

**Day 15-17: Budget System**
- Test budget calculations, period validation, alerts
- Implement budget CRUD operations and tracking
- Add budget vs. actual spending analytics
- Target: 95% budget system coverage

**Day 18-19: Analytics & Reporting**
- Test chart data generation, filtering, performance
- Implement analytics endpoints and calculations
- Add report generation and export functionality
- Target: 85% analytics coverage

**Day 20-21: Data Import/Export**
- Test CSV parsing, validation, bulk operations
- Implement import/export functionality
- Add data transformation and error handling
- Target: 90% import/export coverage

### Phase 4: Frontend & Integration with TDD (Week 4)

**Day 22-24: Frontend Components**
- Test form validation, user interactions, error handling
- Implement responsive UI with HTMX interactions
- Add chart visualization and real-time updates
- Target: 85% frontend coverage

**Day 25-26: Integration Testing**
- Test complete user workflows end-to-end
- Implement performance optimizations
- Add comprehensive error handling
- Target: 80% integration coverage

**Day 27-28: Production Readiness**
- Test deployment pipeline, monitoring, health checks
- Implement CI/CD with automated testing
- Add comprehensive documentation
- Target: Overall 90% coverage

### TDD Success Metrics

**Code Quality Gates:**
- [ ] All tests must pass before any commit
- [ ] Minimum coverage thresholds enforced by CI
- [ ] No production deployment without test coverage
- [ ] Automated testing in pull request workflow

**Daily TDD Metrics:**
- Tests written before implementation: 100%
- Test coverage maintained above thresholds
- Red-Green-Refactor cycles documented
- Test execution time under 2 minutes for full suite

## Risk Assessment

### Technical Risks
- **Database Performance:** Large transaction datasets may impact query performance
  - *Mitigation:* Implement proper indexing, pagination, and caching
- **Security Vulnerabilities:** Financial data requires high security standards
  - *Mitigation:* Regular security audits, penetration testing, OWASP compliance
- **Data Loss:** User financial data is critical
  - *Mitigation:* Automated backups, transaction logs, disaster recovery plan

### Business Risks
- **User Adoption:** Competition with established financial apps
  - *Mitigation:* Focus on simplicity, security, and unique features
- **Scalability:** Growing user base may outpace infrastructure
  - *Mitigation:* Cloud-native architecture, horizontal scaling design

## Success Criteria

### Technical Excellence
- [ ] 90%+ test coverage
- [ ] Sub-500ms API response times
- [ ] Zero critical security vulnerabilities
- [ ] 99.5% uptime in production

### User Experience
- [ ] Intuitive navigation and workflow
- [ ] Mobile-responsive design
- [ ] Fast page load times
- [ ] Accessibility compliance (WCAG 2.1 AA)

### Code Quality
- [ ] Clean, documented, maintainable code
- [ ] Consistent coding standards
- [ ] Comprehensive API documentation
- [ ] Effective error handling and logging

This PRD serves as a comprehensive guide for building a production-ready personal finance dashboard that demonstrates full-stack development expertise while solving real user problems in financial management.
