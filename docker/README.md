# Docker Setup for Personal Finance Dashboard

## Quick Start

1. Copy environment file:

   ```bash
   cp .env.docker .env
   ```

2. Build and start services:

   ```bash
   make build
   make up
   ```

3. Run migrations:

   ```bash
   make migrate
   ```

4. Create superuser:

   ```bash
   make createsuperuser
   ```

5. Access the application:
   - Web app: <http://localhost:8000>
   - Admin panel: <http://localhost:8000/admin>

## Available Commands

Run `make help` to see all available commands.

### Common Operations

- `make up` - Start all services
- `make down` - Stop all services
- `make logs` - View logs
- `make shell` - Open Django shell
- `make test` - Run tests
- `make migrate` - Run migrations
- `make dev-tools` - Start MailHog and pgAdmin

### Development Tools

- MailHog (email testing): <http://localhost:8025>
- pgAdmin (database management): <http://localhost:5050>

## Docker Compose Files

- `docker-compose.yml` - Base configuration
- `docker-compose.override.yml` - Development overrides (auto-loaded)
- `docker-compose.prod.yml` - Production configuration

## Volumes

Data is persisted in named volumes:

- `postgres_data` - PostgreSQL database
- `redis_data` - Redis cache
- `media_volume` - User uploads
- `static_volume` - Static files
- `logs_volume` - Application logs

## Troubleshooting

### Port conflicts

If you get port binding errors, either:

1. Stop conflicting services
2. Change ports in `.env` file

### Permission errors

The application runs as non-root user (uid 1000). If you have permission issues:

```bash
sudo chown -R 1000:1000 media/ logs/
```

### Database connection errors

Ensure the database is healthy:

```bash
docker-compose ps
docker-compose logs db
```
