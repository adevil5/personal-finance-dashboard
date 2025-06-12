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

### API Structure

- RESTful API under `/api/v1/`
- Authentication via Django REST Framework Token Auth
- ViewSets for all major resources
- Pagination, filtering, and sorting support

For detailed API documentation including endpoints, authentication, and usage examples, see [docs/api-reference.md](docs/api-reference.md).

### Development Patterns

This project uses sophisticated patterns for security, testing, and modern web development. For comprehensive implementation details, see [docs/development-patterns.md](docs/development-patterns.md), which covers:

- **PII Protection**: Field-level encryption, audit logging, user isolation
- **File Upload Security**: Multi-layer validation, malware scanning, secure storage
- **Budget Management**: Dynamic calculations, threshold monitoring, alert systems
- **Analytics Engine**: Database-agnostic analytics, performance optimization
- **HTMX Integration**: Progressive enhancement, custom template tags, event handling
- **Testing Strategies**: TDD methodology, security testing, performance validation

### Testing Strategy

- TDD approach is mandatory
- Minimum 90% coverage target
- Use factory-boy for test data
- Performance tests for API endpoints
- Security tests for PII handling

Detailed testing patterns and examples are documented in [docs/development-patterns.md](docs/development-patterns.md).

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
- `apps/analytics/models.py` - SpendingAnalytics engine with database-agnostic trend analysis
- `tests/analytics/test_analytics_engine.py` - 14 core analytics functionality tests
- `tests/analytics/test_analytics_scenarios.py` - 11 comprehensive scenario and edge case tests
- `tests/analytics/test_api_endpoints.py` - 24 analytics API endpoint tests covering all 5 data visualization endpoints
- `tests/analytics/test_dashboard_metrics.py` - 15 dashboard metrics tests including performance and caching validation
- `apps/core/templatetags/htmx_tags.py` - Custom HTMX template tags for DRY dynamic UI patterns
- `tests/core/test_htmx_tags.py` - 20 comprehensive HTMX template tag tests
- `templates/htmx/` - Reusable HTMX components (loading indicators, error containers)
- `apps/expenses/views.py` - Frontend views with TransactionListView and HTMX partials
- `tests/expenses/test_frontend_views.py` - 17 comprehensive frontend view tests with HTMX coverage
- `templates/expenses/` - Complete transaction frontend templates with inline editing
- `apps/expenses/forms.py` - Django forms with encrypted field handling and user-scoped validation
- `tests/expenses/test_forms.py` - 30 comprehensive form tests including integration tests
- `templates/expenses/transaction_form.html` - Transaction creation form with HTMX and file upload
- `static/src/utils/currency.ts` - CurrencyFormatter class with multi-currency and locale support
- `static/src/utils/validation.ts` - FormValidator with async rules and comprehensive validation helpers
- `static/src/api/client.ts` - Type-safe APIClient with CSRF handling and complete endpoint coverage
- `static/src/types/api.ts` - Complete TypeScript interfaces for all Django models and API responses
- `static/src/main.ts` - Enhanced main application with TypeScript utility integration
- `static/src/__tests__/` - 59 comprehensive TypeScript tests with TDD approach

### Form Development

The project implements sophisticated form handling with encrypted fields, HTMX integration, and comprehensive validation. For detailed patterns including Django forms with encrypted fields, frontend form integration, and testing strategies, see the **Frontend Form Patterns** section in [docs/development-patterns.md](docs/development-patterns.md).

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

## Frontend Development

### Template Architecture

- **Base Template**: `templates/base.html` provides responsive navigation, footer, and Tailwind CSS integration
- **Template Inheritance**: All page templates extend `base.html` using `{% extends 'base.html' %}`
- **Navigation**: Alpine.js powered responsive navigation with authentication state detection
- **Assets**: Vite builds CSS/JS assets, Django serves them via static files

### Docker Volume Mount Gotcha

**Critical Issue**: Docker Compose volume precedence can break static asset serving in development.

- **Problem**: Named volumes override bind mounts for the same path
- **Symptom**: Local static file changes not visible in container (e.g., built CSS/JS missing)
- **Root Cause**: `static_volume:/app/static` in base docker-compose.yml masks `.:/app` bind mount
- **Solution**: Override volumes in `docker-compose.override.yml` to remove conflicting named volumes

```yaml
# In docker-compose.override.yml - Remove static_volume to allow bind mount
volumes:
  - .:/app
  - /app/node_modules
  # DO NOT include: static_volume:/app/static (conflicts with bind mount)
```

### Asset Build Process

- **Development**: Vite builds assets locally (`npm run build`), volume mount syncs to container
- **Production**: Assets built during Docker image creation
- **File Paths**: Built assets in `static/dist/assets/` with hashed filenames for cache-busting

### Template Patterns

- **URL Namespacing**: Use app namespaces in URLs (`expenses:transaction-list`, `users:profile`)
- **Authentication Display**: `{% if user.is_authenticated %}` blocks for conditional content
- **Responsive Design**: Tailwind CSS mobile-first approach with `md:` breakpoints
- **Message Framework**: Django messages automatically styled with Tailwind alert classes

### Frontend Development Integration

The project uses modern frontend technologies with Django integration. For comprehensive documentation on HTMX patterns, TypeScript integration, frontend view architecture, and testing strategies, see the **HTMX Integration Patterns** and **TypeScript Integration Patterns** sections in [docs/development-patterns.md](docs/development-patterns.md).

## Development Notes

- Use uv (not standard pip) to manage python packages in this project
- Docker volume conflicts common with static files - check volume precedence in compose files
