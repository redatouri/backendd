# Moviecam Backend

FastAPI backend for [api.moviecam.ma](https://api.moviecam.ma).

## Stack

- FastAPI, Uvicorn
- SQLAlchemy 2 (async) + Alembic
- PostgreSQL (`moviecam`)

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed.seed_data
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Environment

See `.env.example`. Production database (Easypanel internal):

```
DATABASE_URL=postgresql+asyncpg://moviecam:moviecam@moviecam_database:5432/moviecam
```

## Docker

```bash
docker build -t moviecam-api .
docker run -p 8000:8000 --env-file .env moviecam-api
```

Migrations and seed run automatically via `entrypoint.sh`.

## Production

- **Domain:** api.moviecam.ma
- Mount volume at `/app/media` for product uploads
