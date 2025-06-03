#!/bin/bash
# Start Celery beat scheduler for Personal Finance Dashboard

# Load virtual environment
source venv/bin/activate

# Start Celery beat
echo "Starting Celery beat scheduler..."
celery -A config beat --loglevel=info
