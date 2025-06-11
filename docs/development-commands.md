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

# Copy environment variables
cp .env.example .env
```

## Database Operations

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Make migrations for app changes
python manage.py makemigrations
```

## Development Server

```bash
# Run Django development server
python manage.py runserver

# Run with Docker Compose
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
