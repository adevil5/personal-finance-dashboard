# Multi-stage Dockerfile for Personal Finance Dashboard

# Stage 1: Python dependencies
FROM python:3.12-slim as python-deps
COPY --from=ghcr.io/astral-sh/uv:0.7.11 /uv /uvx /bin

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache .

# Stage 2: Frontend builder
FROM node:20-slim as frontend-builder

WORKDIR /app

# Copy frontend dependency files
COPY package*.json ./
RUN npm ci --no-audit

# Copy frontend source files
COPY vite.config.ts tsconfig.json tailwind.config.js postcss.config.js ./
COPY static/ ./static/
COPY templates/ ./templates/

# Build frontend assets
RUN npm run build

# Stage 3: Final runtime image
FROM python:3.12-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy virtual environment from python-deps stage
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser . .

# Copy built frontend assets from frontend-builder stage
COPY --from=frontend-builder --chown=appuser:appuser /app/static/dist ./static/dist

# Create necessary directories
RUN mkdir -p logs media static/collected && \
    chown -R appuser:appuser logs media static

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--worker-class", "gthread", "--log-file", "-", "--access-logfile", "-", "--error-logfile", "-"]
