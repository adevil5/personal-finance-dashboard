# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Task Management

Please refer to TASKS.md for the complete list of features, tasks, and subtasks for this project. All tasks are organized in dependency order and should be completed following Test-Driven Development (TDD) methodology. Use TASKS.md to:

- Track progress on implementation
- Understand task dependencies
- Follow the correct implementation order
- Ensure all acceptance criteria are met

## Project Overview

Personal Finance Dashboard (PFD) - A secure web application for tracking expenses, managing budgets, and analyzing spending patterns. Built with Django, PostgreSQL, and modern web technologies with a focus on security and PII protection.

## Tech Stack

- **Backend**: Django 5.2.1 LTS, PostgreSQL 17+, Redis 7.0+, Celery
- **Frontend**: Django Templates + HTMX, TypeScript 5.x, Tailwind CSS 4.x, Chart.js 4.x
- **Package Manager**: uv (for Python dependencies)
- **Build Tool**: Vite (for frontend assets)
- **Container**: Docker with multi-stage builds, Docker Compose for development

## Common Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with uv
pip install uv
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env
```

### Database Operations

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Make migrations for app changes
python manage.py makemigrations
```

### Development Server

```bash
# Run Django development server
python manage.py runserver

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f web
```

### Testing

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest path/to/test_file.py

# Run tests for specific app
pytest apps/expenses/tests/

# Run with verbose output
pytest -v

# Run only failing tests
pytest --lf
```

### Code Quality

```bash
# Format code with black
black .

# Sort imports
isort .

# Run flake8 linting
flake8

# Type checking with mypy
mypy .

# Security scanning with bandit
bandit -r . -ll

# Run all pre-commit hooks
pre-commit run --all-files
```

### Frontend Build

```bash
# Install frontend dependencies
npm install

# Run Vite dev server
npm run dev

# Build for production
npm run build

# Type check TypeScript
npm run typecheck
```

## Architecture Overview

### Django Apps Structure

- **users**: Authentication, user profiles, MFA support
- **expenses**: Transaction management, categories, tags, receipts
- **budgets**: Budget creation, tracking, alerts
- **analytics**: Reports, charts, data visualization
- **core**: Shared utilities, PII encryption, audit logging

### Security Considerations

- All PII fields use field-level encryption (EncryptedCharField, EncryptedDecimalField)
- Audit logging tracks all PII access via AuditLog model
- File uploads stored in S3 with KMS encryption or encrypted local storage
- Data masking utilities in core.security.masking for non-prod environments
- Complete audit trail requirements for compliance

#### PII Field Patterns

- Transaction amounts: `EncryptedDecimalField` with `amount_index` for filtering/sorting
- Merchant/notes: `EncryptedCharField` with searchable indexes where needed
- User isolation: Always filter querysets by `user=request.user` in serializers
- Phone fields: `EncryptedPhoneField` with automatic normalization to E.164 format
- Custom User model extends AbstractUser with encrypted phone, timezone, currency fields

### API Structure

- RESTful API under `/api/v1/`
- Authentication via Django REST Framework Token Auth
- ViewSets for all major resources
- Pagination, filtering, and sorting support

#### Transaction API Patterns

- Dual-field amount filtering: `amount_min/max` for ranges, `amount_index` for sorting
- Currency formatting via `formatted_amount` SerializerMethodField
- Nested category serialization (read-only) with write-only `category_id`
- Bulk operations via dedicated serializers with proper context passing
- Custom decimal validation: max 2 decimal places via `validate_amount`
- CSV/Excel import via file upload with validation and error reporting
- Recurring transactions automated via Celery periodic tasks

### Testing Strategy

- TDD approach is mandatory
- Minimum 90% coverage target
- Use factory-boy for test data
- Performance tests for API endpoints
- Security tests for PII handling

#### Serializer Testing Patterns

- Test both serialization and deserialization
- Validate all field constraints (decimal places, required fields, etc.)
- Test user isolation in querysets
- Test currency formatting with different currencies
- Use `APIRequestFactory` for request context in serializer tests

#### Django Validation Error Handling

- Model validation errors in `create()` must be caught and converted to DRF ValidationError
- Use `try/except ValidationError` around `super().create()` in serializers
- Convert Django `message_dict` to DRF format for proper API error responses
- Check `field == "__all__"` for non-field errors and provide user-friendly messages

#### Budget Management Patterns

- Budget alerts with configurable threshold monitoring (warning/critical percentages)
- Dynamic spent amount calculations using aggregated transactions
- Period-based budget tracking with date range validation
- Alert notifications integrated with Celery for background processing

#### Budget API Patterns

- Calculated fields: `spent_amount`, `remaining_amount`, `utilization_percentage`, `is_over_budget`
- Period-based filtering with `period_start_after/before` and `period_end_after/before`
- Statistics endpoint for aggregate budget analytics across user's budgets
- Current budgets endpoint for active period filtering via classmethods
- Django Filters integration for category and date range filtering
- User-scoped queries with proper security isolation in ViewSet
- Soft delete pattern using `is_active=False` in `perform_destroy`

#### Budget Analytics API Patterns

- **Analytics endpoint** (`/analytics/`): Enhanced analytics with optional features
  - Previous period comparison via `compare_previous=true` parameter
  - Category breakdown via `category_breakdown=true` parameter
  - Period filtering with automatic previous period calculation
- **Performance endpoint** (`/performance/`): Budget performance categorization
  - Configurable performance thresholds (default 80% for "good" performance)
  - Performance categories: excellent (<60%), good (<80%), warning (<100%), over_budget (>100%)
  - Best/worst performers ranking with top 3 budgets by utilization
- **Trends endpoint** (`/trends/`): Multi-period trend analysis
  - Up to 24 months of historical data via `months` parameter
  - Category filtering via `category_id` parameter
  - Trend indicators: budget_growth, spending_growth, utilization_change
- **Shared analytics patterns**: Helper methods for period calculations
  - `_calculate_period_analytics()`: Reusable analytics computation
  - `_calculate_percentage_change()`: Safe percentage change with zero-division handling
  - User isolation enforced in all analytics queries

### Key Files to Check

- `config/settings/base.py` - Core Django settings
- `docker-compose.yml` - Local development setup
- `pytest.ini` - Test configuration
- `.pre-commit-config.yaml` - Code quality hooks
- `apps/core/security/` - PII encryption and masking utilities
- `apps/expenses/serializers.py` - Transaction serialization patterns
- `apps/budgets/models.py` - Budget model with alert configurations
- `apps/budgets/serializers.py` - Budget API serialization with calculated fields
- `apps/budgets/views.py` - Budget ViewSet with statistics, filtering, and analytics endpoints
- `tests/expenses/test_serializers.py` - Comprehensive serializer test examples
- `tests/budgets/test_views.py` - Budget ViewSet test patterns and CRUD operations
- `tests/budgets/test_analytics.py` - Budget analytics endpoint tests with 27 comprehensive test cases

## Development Notes

- Use uv (not standard pip) to manage python packages in this project
