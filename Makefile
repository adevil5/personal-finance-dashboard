.PHONY: help build up down restart logs shell test migrate makemigrations

# Default target
help:
	@echo "Personal Finance Dashboard - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build         Build Docker images"
	@echo "  up            Start all services"
	@echo "  down          Stop all services"
	@echo "  restart       Restart all services"
	@echo "  logs          View logs (follow mode)"
	@echo "  shell         Open Django shell"
	@echo "  bash          Open bash shell in web container"
	@echo "  test          Run tests"
	@echo "  migrate       Run database migrations"
	@echo "  makemigrations Create new migrations"
	@echo "  collectstatic Collect static files"
	@echo "  createsuperuser Create superuser account"
	@echo "  dev-tools     Start development tools (mailhog, pgadmin)"
	@echo "  clean         Remove containers and volumes"

# Build Docker images
build:
	COMPOSE_BAKE=true docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart: down up

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-%:
	docker-compose logs -f $*

# Open Django shell
shell:
	docker-compose exec web python manage.py shell

# Open bash shell in web container
bash:
	docker-compose exec web bash

# Run tests
test:
	docker-compose exec web pytest

# Run tests with coverage
test-coverage:
	docker-compose exec web pytest --cov=. --cov-report=html

# Run database migrations
migrate:
	docker-compose exec web python manage.py migrate

# Create new migrations
makemigrations:
	docker-compose exec web python manage.py makemigrations

# Collect static files
collectstatic:
	docker-compose exec web python manage.py collectstatic --noinput

# Create superuser
createsuperuser:
	docker-compose exec -it web python manage.py createsuperuser

# Start development tools
dev-tools:
	docker-compose --profile dev-tools up -d

# Database operations
db-backup:
	docker-compose exec db pg_dump -U $${DB_USER:-pfd_user} -d $${DB_NAME:-personal_finance} > backups/postgres/backup_$$(date +%Y%m%d_%H%M%S).sql

db-shell:
	docker-compose exec db psql -U $${DB_USER:-pfd_user} -d $${DB_NAME:-personal_finance}

# Redis operations
redis-cli:
	docker-compose exec redis redis-cli -a $${REDIS_PASSWORD:-redis_password}

# Clean up
clean:
	docker-compose down -v
	docker system prune -f

# Production commands
prod-build:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
