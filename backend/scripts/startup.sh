#!/bin/bash
# Run database migrations, then start the app
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
