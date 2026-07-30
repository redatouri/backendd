#!/bin/sh
set -e

echo "Waiting for database..."
python <<'PY'
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def wait_for_db() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set")
        sys.exit(1)

    last_error = None
    for attempt in range(1, 31):
        engine = create_async_engine(url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("Database is ready")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"Database not ready ({attempt}/30): {exc}")
            await asyncio.sleep(2)
        finally:
            await engine.dispose()

    print(f"Database unavailable after 60s: {last_error}")
    sys.exit(1)

asyncio.run(wait_for_db())
PY

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python -m app.seed.seed_data

echo "Starting API on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
