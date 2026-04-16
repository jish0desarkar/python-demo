# python-demo

FastAPI + SQLite + HTMX + Alembic, Dockerized.

## Stack
- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2.x + SQLite
- Alembic (migrations)
- Jinja2 + HTMX (UI)

## Run

```bash
docker compose up --build
```

App is served at http://localhost:8000.
Ollama is served at http://localhost:11434.

The Ollama container auto-pulls `phi3:mini` and `nomic-embed-text` on first start. The first boot can take a few minutes while the models download.

## Event Payload Summaries

Open an event detail page and click `Generate summary` to summarize the payload with the local `phi3:mini` model running in Ollama.

Useful commands:

```bash
docker compose logs -f ollama
docker compose exec ollama ollama list
docker compose exec ollama ollama run phi3:mini
docker compose exec ollama ollama pull nomic-embed-text
```

## Migrations

Create a new revision from model changes:

```bash
docker compose run --rm web alembic revision --autogenerate -m "your message"
```

Apply migrations:

```bash
docker compose run --rm web alembic upgrade head
```

## Layout

```
app/
  main.py         FastAPI app + routes
  config.py       Settings (pydantic-settings)
  database.py     SQLAlchemy engine/session/Base
  models.py       ORM models
  templates/      Jinja2 + HTMX templates
alembic/          Migration scripts
alembic.ini
Dockerfile
docker-compose.yml
requirements.txt
```
