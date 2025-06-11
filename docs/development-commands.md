# Development Commands Reference

This document contains common development commands for the Personal Finance Dashboard project.

## Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with uv
pip install uv
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env: use localhost for local dev, or db/redis for full Docker
```

## Database Operations

### Prerequisites

```bash
# Start PostgreSQL and Redis containers (required for default setup)
docker-compose up -d db redis
```

### Migration Commands

```bash
# Run migrations (default - uses PostgreSQL)
python manage.py migrate

# Run migrations with SQLite (offline mode)
USE_SQLITE=true python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Make migrations for app changes
python manage.py makemigrations

# Check migration status
python manage.py showmigrations
```

### Database Connection

- **Default**: Connects to PostgreSQL on `localhost:5432` (requires Docker)
- **SQLite mode**: Set `USE_SQLITE=true` for offline development
- **Docker mode**: Use `make migrate` to run inside container

## Development Server

```bash
# Run Django development server (default - uses PostgreSQL)
python manage.py runserver

# Run with SQLite (offline mode)
USE_SQLITE=true python manage.py runserver

# Run with Docker Compose (all services)
docker-compose up -d

# View logs
docker-compose logs -f web
```

## Testing

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

## Code Quality

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

## Frontend Build

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
