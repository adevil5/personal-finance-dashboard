# Development Commands Reference

This document contains common development commands for the Personal Finance Dashboard project.

## Development Approaches

### Primary: Docker-first Development (Recommended)

Use `make` commands for a consistent containerized development experience:

```bash
# Start all services (PostgreSQL, Redis, Django, Celery)
make up

# Run database migrations
make migrate

# Create superuser account
make createsuperuser

# Run tests with coverage
make test-coverage

# Open Django shell
make shell

# View logs
make logs

# Stop all services
make down
```

**Benefits**: Consistent environment, matches production, automatic port conflict resolution

### Alternative: Local Development with External Services

Run Django locally while using Docker for databases:

```bash
# Start only PostgreSQL and Redis containers
docker-compose up -d db redis

# Run Django locally (connects to containers on localhost:5433, localhost:6380)
python manage.py runserver

# Run migrations locally
python manage.py migrate

# Run tests locally
pytest --cov=. --cov-report=html
```

**Benefits**: Better IDE integration, faster iteration, easier debugging

### Emergency: Fully Offline Development

Use SQLite when Docker is unavailable:

```bash
# All commands with SQLite
USE_SQLITE=true python manage.py migrate
USE_SQLITE=true python manage.py runserver
USE_SQLITE=true pytest
```

**Limitations**: Some PostgreSQL-specific features may not work

## Docker Compose File Structure

The project uses a 3-file Docker Compose architecture:

### 1. `docker-compose.yml` (Base Configuration)

- Defines core services: web, db, redis, celery, celery-beat
- Shared configuration used by both development and production
- Uses `Dockerfile.dev` for development builds

### 2. `docker-compose.override.yml` (Development Overrides)

**Automatically loaded** in development to avoid port conflicts:

- PostgreSQL: `localhost:5433` (instead of 5432)
- Redis: `localhost:6380` (instead of 6379)
- Adds development tools: mailhog (email testing), pgadmin (database UI)
- Enables volume mounts for live code reloading

### 3. `docker-compose.prod.yml` (Production Overrides)

Must be explicitly specified:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

- Uses production `Dockerfile` with multi-stage builds
- Adds Nginx reverse proxy
- Removes port exposure for databases (security)
- No volume mounts (code baked into images)

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
