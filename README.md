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

### Prerequisites

- Python 3.11+
- PostgreSQL 17+
- Redis 7.0+
- Node.js 18+ (for frontend build tools)

### Installation

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
cp .env.example .env
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

Alex Devillier (alex.devillier@gmail.com)
