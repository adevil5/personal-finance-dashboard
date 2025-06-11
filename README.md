# Personal Finance Dashboard

A secure web application for tracking expenses, managing budgets, and analyzing spending patterns. Built with Django, PostgreSQL, and modern web technologies with a focus on security and PII protection.

## Features

- **Expense Tracking**: Record and categorize transactions with receipt upload support
- **Budget Management**: Set budgets with intelligent alerts and threshold monitoring
- **Analytics & Insights**: Advanced analytics with trend analysis and performance metrics
- **Receipt Processing**: OCR text extraction with PII detection and malware scanning
- **Data Security**: Field-level encryption, audit logging, and comprehensive PII protection
- **Import/Export**: Bulk import from bank statements, export to various formats
- **Multi-Currency Support**: Handle transactions in different currencies with formatting

## Tech Stack

- **Backend**: Django 5.2.1 LTS, PostgreSQL 17+, Redis 7.0+, Celery
- **Frontend**: Django Templates + HTMX, TypeScript 5.x, Tailwind CSS 4.x, Chart.js 4.x
- **Security**: Field-level encryption, audit logging, OCR-based PII detection, malware scanning
- **Testing**: pytest, 90%+ coverage requirement, TDD methodology, 516 tests
- **Build**: Docker multi-stage builds, Vite for frontend assets, uv for Python dependencies

## Quick Start

**Prerequisites**: Docker Desktop installed

```bash
git clone https://github.com/alex-devillier/personal-finance-dashboard.git
cd personal-finance-dashboard
cp .env.example .env
make up
make migrate
make createsuperuser
```

**Access**: http://localhost:8000 (Web) | http://localhost:8000/admin (Admin)

## Development Setup

The project supports multiple development approaches. For detailed instructions, see [docs/development-commands.md](docs/development-commands.md).

### Primary: Docker-First (Recommended)

Uses Docker for all services with live code reloading:

```bash
make up        # Start all services
make migrate   # Run migrations
make test      # Run tests
make shell     # Django shell
```

**Ports**: PostgreSQL on 5433, Redis on 6380 (to avoid local conflicts)

### Alternative: Local + External Services

Run Django locally with Docker databases:

```bash
docker-compose up -d db redis  # Start databases only
python manage.py runserver     # Run Django locally
```

**Benefits**: Better IDE integration, easier debugging

### Emergency: Fully Offline

Uses SQLite when Docker unavailable:

```bash
USE_SQLITE=true python manage.py runserver
```

**Limitations**: Some PostgreSQL features disabled

## Development

See [TASKS.md](TASKS.md) for the complete development roadmap and [docs/development-commands.md](docs/development-commands.md) for detailed setup instructions.

### Architecture

**3-File Docker Compose Structure**:
- `docker-compose.yml` - Base configuration
- `docker-compose.override.yml` - Development overrides (auto-loaded)
- `docker-compose.prod.yml` - Production overrides (explicit)

**Key Benefits**:
- Volume mounts enable live code reloading in containers
- Port remapping prevents conflicts with local services
- Production builds use multi-stage Dockerfiles

### Common Commands

```bash
make help          # Show all available commands
make up            # Start all services
make logs          # View logs
make shell         # Django shell
make test-coverage # Run tests with coverage report
```

## Testing

Current status: **516 tests passing** with 75% coverage (target: 90%)

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific tests
pytest apps/expenses/tests/
```

## Security

This application implements comprehensive security measures:

- Field-level encryption for all PII data
- Complete audit logging of PII access
- Data masking in non-production environments
- Secure file handling with malware scanning
- OWASP Top 10 compliance

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Alex Devillier (<alex.devillier@gmail.com>)
