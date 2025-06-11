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

## Development Setup

For detailed setup instructions and command reference, see [docs/development-commands.md](docs/development-commands.md).

### Recommended Development Approach

#### Primary: Docker-first development (recommended)

- Use `make` commands as the primary interface
- All development happens in containers with live code sync via volume mounts
- Consistent environment across all developers
- Examples: `make up`, `make migrate`, `make test`, `make shell`

#### Alternative: Local development with external services

- Run Django directly on host with `python manage.py ...`
- Use Docker only for PostgreSQL/Redis: `docker-compose up -d db redis`
- Good for debugging, IDE integration, faster iteration
- Note: Ports remapped to avoid conflicts (PostgreSQL on 5433, Redis on 6380)

#### Emergency: Fully offline

- Use SQLite mode: `USE_SQLITE=true python manage.py ...`
- No Docker dependency, limited functionality

### Docker Compose Architecture

The project uses a 3-file Docker Compose structure:

1. **`docker-compose.yml`** - Base configuration (shared by dev/prod)
2. **`docker-compose.override.yml`** - Development overrides (auto-loaded)
   - Port remapping to avoid conflicts (5433, 6380)
   - Volume mounts for live code reloading
   - Development tools (mailhog, pgadmin)
3. **`docker-compose.prod.yml`** - Production overrides (explicit)
   - No volume mounts (code baked into image)
   - Nginx reverse proxy, security hardening
   - Usage: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`

### Quick Reference Commands

- **Setup**: `python -m venv venv && source venv/bin/activate && pip install uv && uv pip install -r requirements.txt`
- **Testing**: `pytest --cov=. --cov-report=html` or `make test`
- **Development**: `make up` (Docker) or `python manage.py runserver` (local)
- **Code Quality**: `black . && isort . && flake8 && mypy .`

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

#### File Upload Security Patterns

- **File validation layers**: Multi-layer security approach for receipt uploads
  - File type validation using magic bytes detection (not just extensions)
  - File size enforcement (10MB limit) with proper error messages
  - Content validation to prevent executable/script content in image files
  - Malware scanning integration with fallback behavior
- **Security validator architecture**: `ReceiptFileValidator` class in `apps/core/security/validators.py`
  - Configurable validation components (size, types, malware scanning)
  - Proper exception handling with security-first failure modes
  - Path traversal and filename security validation
- **Test mocking patterns**: Mock placement for imported functions
  - Mock at import location: `@patch('apps.core.security.validators.scan_file')` not source
  - Handle Django's filename sanitization in tests (use direct validator calls)
  - Test both success and failure paths with proper error message validation

#### Secure File Storage Patterns

- **Dual storage architecture**: Environment-aware backend selection via `get_storage_backend()`
  - Local development: `SecureLocalStorage` with direct media URLs
  - Production: `SecureS3Storage` with KMS encryption and pre-signed URLs
  - Both extend `BaseSecureStorage` for common security features
- **Security-first design**: All storage operations include comprehensive validation
  - Path traversal prevention via filename sanitization and secure path generation
  - User isolation with `receipts/{user_id}/` directory structure
  - Magic bytes validation, not just file extension checking
- **File cleanup policies**: Automated cleanup with safety checks
  - Orphaned files: Remove unreferenced files with 1-day grace period
  - Expired files: Configurable retention periods (default 365 days)
  - User data deletion: Complete file removal on user account deletion
- **Test validation bypass**: Use `Transaction.objects.filter().update()` to bypass field validation
  - Required when tests need specific file paths that would fail `validate_receipt_file`
  - Pattern: Create transaction normally, then update receipt path directly

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
- `apps/core/security/validators.py` - File upload security validation with multi-layer approach
- `apps/core/security/malware.py` - Malware scanning utilities with ClamAV integration
- `apps/expenses/storage.py` - Secure file storage backends with dual architecture (local/S3)
- `tests/expenses/test_serializers.py` - Comprehensive serializer test examples
- `tests/budgets/test_views.py` - Budget ViewSet test patterns and CRUD operations
- `tests/budgets/test_analytics.py` - Budget analytics endpoint tests with 27 comprehensive test cases
- `tests/expenses/test_receipt_security.py` - 23 comprehensive file upload security tests
- `tests/expenses/test_secure_storage.py` - 18 comprehensive secure storage tests with local/S3 coverage

## Database Configuration

### Development Database Strategy

The project uses a dual-database approach for flexibility:

1. **PostgreSQL (Default)**: Matches production environment
   - Uses Docker PostgreSQL container
   - Required for features like field-level encryption, complex queries
   - Connect via `localhost:5432` when running Django locally
   - No configuration needed - uses settings from `.env`

2. **SQLite (Offline Mode)**: For quick development without Docker
   - Enable with `USE_SQLITE=true` environment variable
   - Example: `USE_SQLITE=true python manage.py runserver`
   - Limited functionality - some PostgreSQL-specific features may not work
   - Useful for UI development, quick prototyping

### Running Migrations

```bash
# Default (PostgreSQL via Docker)
python manage.py migrate

# With SQLite
USE_SQLITE=true python manage.py migrate

# Inside Docker container
make migrate
```

## Development Notes

- Use uv (not standard pip) to manage python packages in this project
