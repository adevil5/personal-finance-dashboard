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

### API Structure
- RESTful API under `/api/v1/`
- Authentication via Django REST Framework Token Auth
- ViewSets for all major resources
- Pagination, filtering, and sorting support

### Testing Strategy
- TDD approach is mandatory
- Minimum 90% coverage target
- Use factory-boy for test data
- Performance tests for API endpoints
- Security tests for PII handling

### Key Files to Check
- `config/settings/base.py` - Core Django settings
- `docker-compose.yml` - Local development setup
- `pytest.ini` - Test configuration
- `.pre-commit-config.yaml` - Code quality hooks
- `apps/core/security/` - PII encryption and masking utilities

## Development Notes
- Use uv (not standard pip) to manage python packages in this project
