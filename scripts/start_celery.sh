#!/bin/bash
# Start Celery worker for Personal Finance Dashboard

# Load virtual environment
source venv/bin/activate

# Start Celery worker
echo "Starting Celery worker..."
celery -A config worker --loglevel=info
