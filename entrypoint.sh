#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python -m app.seed.seed_data

echo "Starting API on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
