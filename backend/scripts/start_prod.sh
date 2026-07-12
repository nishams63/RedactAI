#!/bin/bash
# Production startup script for FastAPI RedactAI API

# Fail fast on error
set -e

# Run database migrations
echo "Running alembic database migrations..."
alembic upgrade head || echo "Migration command skipped/failed (non-blocking)"

# Start FastAPI application gateway
echo "Starting production ASGI server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-4} --proxy-headers
