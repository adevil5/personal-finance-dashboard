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

2. Copy the Docker environment file and start services:

```bash
cp .env.docker .env  # Use Docker-specific environment variables
make build
make up
make migrate
make createsuperuser
```

3. Access the application:
   - Web app: http://localhost:8000
   - Admin panel: http://localhost:8000/admin

### Option 2: Manual Setup

**Prerequisites**: Python 3.11+, PostgreSQL 17+, Redis 7.0+, Node.js 18+

**Best for**: Custom development environment, debugging specific issues

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

4. Set up environment variables:

```bash
cp .env.example .env  # Use local development environment variables
# Edit .env with your configuration
```

5. Run migrations:

```bash
python manage.py migrate
```

6. Create a superuser:

```bash
python manage.py createsuperuser
```

7. Run the development server:

```bash
python manage.py runserver
```

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

### Environment Files

The project provides two environment templates (choose one based on your setup):

- **`.env.example`** - Template for manual/local development (uses `localhost` for services)
- **`.env.docker`** - Template for Docker development (uses Docker service names like `db`, `redis`)

Copy the appropriate template to create your `.env` file:

- **For Docker setup**: `cp .env.docker .env`
- **For manual setup**: `cp .env.example .env`

The `.env` file is your actual configuration (not tracked in git). You can only use one setup at a time.

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
