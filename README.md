# Personal Finance Dashboard

A secure web application for tracking expenses, managing budgets, and analyzing spending patterns. Built with Django, PostgreSQL, and modern web technologies with a focus on security and PII protection.

## Features

- **Expense Tracking**: Record and categorize all your transactions
- **Budget Management**: Set and monitor budgets by category
- **Analytics & Insights**: Visualize spending patterns with charts and reports
- **Data Security**: Field-level encryption for all PII data
- **Import/Export**: Bulk import from bank statements, export to various formats
- **Multi-Currency Support**: Handle transactions in different currencies

## Tech Stack

- **Backend**: Django 5.2 LTS, PostgreSQL, Redis, Celery
- **Frontend**: Django Templates + HTMX, TypeScript, Tailwind CSS, Chart.js
- **Security**: Field-level encryption, audit logging, PII detection
- **Testing**: pytest, 90%+ coverage requirement, TDD methodology

## Getting Started

Choose **one** of the following setup methods:

### Option 1: Docker Setup (Recommended)

**Prerequisites**: Docker Desktop installed on your machine

**Best for**: Quick setup, consistent environment, local development

1. Clone the repository:

```bash
git clone https://github.com/alex-devillier/personal-finance-dashboard.git
cd personal-finance-dashboard
```

2. Copy the environment file and start services:

```bash
cp .env.example .env  # Edit for full Docker setup (change localhost to db/redis)
make build
make up
make migrate
make createsuperuser
```

3. Access the application:
   - Web app: http://localhost:8000
   - Admin panel: http://localhost:8000/admin

### Option 2: Manual Setup

**Prerequisites**: Python 3.11+, Docker (for PostgreSQL & Redis), Node.js 18+

**Best for**: Local development with direct Python execution, debugging

**Note**: This setup still requires Docker for PostgreSQL and Redis services

1. Clone the repository:

```bash
git clone https://github.com/alex-devillier/personal-finance-dashboard.git
cd personal-finance-dashboard
```

2. Create and activate a virtual environment:

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install uv
uv pip install -e .
uv pip install -e ".[dev]"
```

4. Start the database services:

```bash
docker-compose up -d db redis  # Start only PostgreSQL and Redis
```

5. Set up environment variables:

```bash
cp .env.example .env  # Pre-configured for local development
# Edit .env if needed (defaults should work)
```

6. Run migrations:

```bash
python manage.py migrate
```

7. Create a superuser:

```bash
python manage.py createsuperuser
```

8. Run the development server:

```bash
python manage.py runserver
```

### Database Options

- **Default**: Uses PostgreSQL from Docker container (requires `docker-compose up -d db`)
- **SQLite mode**: For offline development, use `USE_SQLITE=true python manage.py runserver`
- **Connection**: The manual setup connects to Docker PostgreSQL on `localhost:5432`

## Development

See [TASKS.md](TASKS.md) for the complete development roadmap and task list.

### Docker Commands

The project includes a Makefile for common Docker operations:

- `make up` - Start all services
- `make down` - Stop all services
- `make logs` - View logs
- `make shell` - Open Django shell
- `make test` - Run tests
- `make help` - Show all available commands

For more details, see [docker/README.md](docker/README.md).

### Environment Configuration

The project uses a single `.env.example` template that works for both setups:

```bash
cp .env.example .env  # Copy template
# Edit .env based on your setup:
# - Local Development: Keep DB_HOST=localhost, REDIS_HOST=localhost
# - Full Docker: Change to DB_HOST=db, REDIS_HOST=redis
```

The template includes clear comments explaining when to use each value.

## Testing

Run tests with coverage:

```bash
pytest --cov=. --cov-report=html
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
