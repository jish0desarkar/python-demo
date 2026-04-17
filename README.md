# python-demo

A small event processing playground. It takes in messages (events) from fake outside systems like Salesforce or Slack, writes short summaries using a local LLM, stores embeddings for those summaries, lets you search across events using both keywords and meaning, and runs a simple rule engine that can forward matching events to a webhook.

Everything runs locally in Docker. No paid APIs are used.

## Stack

- Python 3.12
- FastAPI and Uvicorn for the web server
- SQLAlchemy 2 with SQLite for storage
- Alembic for database migrations
- Jinja2 and HTMX for the UI
- Celery for background jobs, with Redis as the broker
- Celery Beat for recurring jobs
- Ollama for the local LLM (`phi3:mini`) and the embedding model (`nomic-embed-text`)
- FAISS for the vector index
- `bm25s` for keyword ranking
- `rapidfuzz` for rule matching

## Run

```bash
docker compose up --build
```

The app is served at http://localhost:8000. Ollama is exposed on http://localhost:11434.

The Ollama container pulls `phi3:mini`, `nomic-embed-text`, and `mxbai-embed-large` on first start. The first boot can take a few minutes while the models download.

Compose brings up five services:

- `web`: the FastAPI app
- `worker`: the Celery worker that runs background jobs
- `beat`: the Celery Beat scheduler that fires recurring jobs
- `ollama`: the local LLM and embedding server
- `redis`: the broker and result backend for Celery

## Project layout

```
app/
  main.py              FastAPI app, registers routers, serves the base page
  config.py            Settings loaded from env (pydantic_settings)
  database.py          SQLAlchemy engine, session, Base
  models.py            ORM models
  api/
    routes/            One file per resource (accounts, sources, users, events, rules)
    schemas.py         Pydantic input models
  services/            Business logic kept out of the route layer
    hybrid_search.py   BM25 + vector search merged with RRF
    embedding_store.py FAISS index writer and reader
    event_filter.py    Fuzzy rule matcher
    event_summary.py   Calls Ollama to summarize payloads
    phrase_generator.py Calls Ollama to create fake event payloads
    llm.py             Embedding model registry
    ollama_client.py   Thin factory for the Ollama client
    webhook.py         Signs and posts webhook bodies
  templates/           Jinja2 and HTMX templates
alembic/               Database migrations
tasks/                 Celery tasks (events, embeddings, event generator)
celery_app.py          Celery config and beat schedule
seed_events.py         Optional script that creates sample accounts, sources, and 200 events
clear_event_data.py    Wipes events, queued requests, summaries, and the FAISS folder
```

## Data model

The main tables live in `app/models.py`.

- `accounts`: a tenant. Holds a free text `keywords` field used for a simple substring search on the accounts list.
- `users`: belongs to an account.
- `sources`: an external system such as Salesforce or Slack.
- `account_sources`: a join table that says which accounts are linked to which sources. Events can only be ingested for linked pairs.
- `events`: the raw payload we received. Has an `is_filtered` flag set by the rule job.
- `event_summary`: the short summary written by the LLM. One per event.
- `event_summary_embeddings`: tracks which `(model_key, event_summary_id)` pairs already have a vector in FAISS. The actual vectors live in the FAISS file on disk, not in SQLite.
- `queued_event_requests`: the inbox for incoming events. Each row has a status of `queued`, `processing`, `completed`, or `failed`.
- `rules`: a rule belongs to a source and has a `rule_text` (the phrase to match against the event summary) plus a human friendly `name`.
- `event_filter_logs`: one row per event, records whether it passed or failed the rules, the score, and which rule matched.

## The flows

### 1. Ingesting an event

There are two ways an event enters the system:

1. A POST to `/events/webhook` with JSON `{account_id, source_id, payload}`.
2. The form at the Events page which hits POST `/events`.

Both paths do the same three things:

1. Validate the account exists.
2. Validate the source exists and is linked to that account.
3. Insert a `queued_event_requests` row with status `queued` and enqueue `tasks.events.process_queued_event_request` on Celery.

The HTTP response returns right away. The heavy work happens in the worker.

### 2. Processing a queued event

The worker task `process_queued_event_request` lives in `tasks/events.py` and runs these steps:

1. Mark the request `processing`.
2. Validate the account and source again (things may have changed since it was queued).
3. Create the `events` row if it does not exist yet.
4. Call the summary service, which asks `phi3:mini` to write a short summary of at most 30 words. The prompt tells the model to use only facts in the payload and to skip bullets, quotes, headings, and JSON. The service has a small retry loop (up to 3 attempts) so a flaky LLM call does not lose the event.
5. If the summary is created, enqueue `tasks.embeddings.store_event_summary_embedding` for that summary.
6. Mark the request `completed`. On any error the request is marked `failed` with a short error message.

### 3. Generating fake traffic

`celery_app.py` schedules `tasks.generate_event.generate_random_event` every 30 seconds (the task name still says 20s for historical reasons). It picks a random linked account and source, and 80 percent of the time it also picks a random rule for that source and passes the rule text as a hint to the phrase generator. The phrase generator asks `phi3:mini` for a realistic 50 to 70 word paragraph, then posts it back to the same `/events/webhook` endpoint. This way the system produces a steady stream of events that sometimes match rules and sometimes do not, which is useful for watching the filter pipeline work.

### 4. Writing embeddings

`tasks/embeddings.py` has two tasks.

- `store_event_summary_embedding(event_summary_id)` runs right after a summary is written. It loads the active embedding model from `LLMService.active_embedder()`, embeds the summary text, and adds the vector to the FAISS index on disk.
- `backfill_active_model_embeddings` finds summaries that do not yet have an embedding for the active model and processes them in batches of 50. It re queues itself when a batch is done so it keeps draining without blocking the worker.

The backfill task is also kicked off once on worker startup via the `worker_ready` Celery signal. This means if you change `EMBEDDING_MODEL` and restart, the worker will quietly build the new index in the background while the app keeps serving.

Why a separate FAISS file instead of putting vectors in SQLite? SQLite has no vector search. FAISS does exact nearest neighbor search in memory and is tiny to set up. The on disk format is a single file per model, stored at `/app/data/faiss/<model_key>.faiss`. This also makes it easy to support more than one embedding model: each model gets its own file and the row in `event_summary_embeddings` uses `(model_key, event_summary_id)` as a composite primary key.

### 5. Filtering events against rules

Celery Beat runs `tasks.events.filter_unprocessed_events` every 60 seconds. It looks at every event where `is_filtered` is false and that already has a summary. For each event it loads the rules that belong to the same source and runs them through `EventFilter.match`.

The filter uses `rapidfuzz.fuzz.partial_token_set_ratio` between the rule text and the event summary, both lowercased. A score of 75 or more (on a 0 to 100 scale) counts as a pass. The first rule that passes wins. If no rule passes, the event is logged as `failed`.

Why this algorithm?

- It is a token set ratio, so it ignores word order. A rule like "webhook failure in billing" matches a summary like "billing webhook is failing" without extra work.
- It is a partial match, so a short rule can match a long summary. The score is the best alignment of the rule inside the summary.
- `rapidfuzz` is written in C++ and is much faster than `fuzzywuzzy`.
- 0.75 is a pragmatic threshold: strict enough to avoid obvious false positives on unrelated text, loose enough to tolerate small wording differences from an LLM generated summary.

When a rule passes, we write an `event_filter_logs` row with status `passed`, the score, and the matched rule. We also POST the event and rule to the webhook endpoint configured in settings, signed with an HMAC SHA 256 signature in the `X-Signature-256` header. The signing key is `settings.webhook_secret`.

### 6. Searching events

The events page has a search box. The handler is `event_panel_context` in `app/api/routes/events.py` which calls `HybridSearch.search`.

Hybrid search runs two rankers in parallel on a thread pool:

1. **Vector search** over the FAISS index. We embed the query with the active model and pull the top 20 nearest summary ids by L2 distance.
2. **Keyword search** using BM25. We load all summaries from SQLite, tokenize them with `bm25s`, build a BM25L index in memory, and retrieve the top 20 summary ids. Summaries with a zero score are dropped.

The two ranked lists are merged using **Reciprocal Rank Fusion** with `k = 60`. For each list, a document in position `rank` adds `1 / (60 + rank)` to its score. The final list is sorted by the combined score and the top `k` (default 10) is returned.

Why this mix?

- Keyword search is great when the user types a specific identifier or phrase that appears literally in a summary. Vector search misses those because the summaries are short.
- Vector search is great when the user types something related in meaning but with different words ("deployment problem" vs a summary that says "rollback initiated due to high error rates"). Keyword search misses those.
- Reciprocal Rank Fusion is simple, needs no score calibration between the two rankers, and is a well known baseline that often beats more involved blends. The `k = 60` constant is the common default: it softens the weight of top ranks just enough that a document high in one list is not automatically the winner if the other list disagrees.

Why BM25L instead of plain BM25 Okapi? BM25L tweaks the term frequency saturation so longer documents are not penalized as hard. Our summaries are short but variable in length, and rules and user queries are often very short, so BM25L tends to give steadier results.

Why FAISS `IndexFlatL2` and not an approximate index like IVF or HNSW? At this scale (thousands to tens of thousands of summaries) a flat index is fast enough and returns exact results. We avoid the cost and tuning pain of approximate indexes until we have a reason to pay it.

The keyword index is rebuilt on every query. That is cheap at this scale and saves us from keeping a BM25 index in sync with the database. If the corpus grows, the natural next step is to cache the index and invalidate it on writes.

After the fused summary ids come back, the route turns them into event ids and the existing events query filters by that list, so all the usual filters (for example "source = Slack") still apply on top of search.

### 7. Account keyword search

The accounts page supports a separate text box that does a plain SQL `LIKE` against the `keywords` column on `accounts`. It is literal substring matching, intentionally simple. Keywords are normalized at write time (lowercased, de duplicated, comma separated) by `AccountCreate._normalize_keywords`.

## Settings

All settings are in `app/config.py` and can be overridden by environment variables. The ones worth knowing:

- `DATABASE_URL`: defaults to SQLite at `/app/data/app.db`.
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`: Redis URLs.
- `OLLAMA_BASE_URL` and `OLLAMA_MODEL`: where the LLM lives and which chat model to use.
- `EMBEDDING_MODEL`: must be a key in `AVAILABLE_EMBEDDING_MODELS` (`nomic-embed-text` or `mxbai-embed-large`). Each model has its own dimension and its own FAISS file on disk.
- `APP_BASE_URL`: used by the fake event generator to POST back into the app.
- `WEBHOOK_URL` and `WEBHOOK_SECRET`: where to send matched events and the HMAC key used to sign them.

## Handy commands

```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f beat
docker compose logs -f ollama

docker compose exec ollama ollama list
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama run phi3:mini
```

Seed some sample data (accounts, sources, links, and 200 events queued for processing):

```bash
docker exec python-demo-web python seed_events.py
```

Wipe all events, queued requests, summaries, filter logs, and the FAISS folder:

```bash
docker compose run --rm --no-deps web python clear_event_data.py
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

Migrations run automatically against the mounted SQLite file. The `alembic/versions/` folder holds the history.

## Where to start reading the code

If you are new to the project, a good path through the code is:

1. `app/main.py` to see how routes are wired up.
2. `app/models.py` for the schema.
3. `app/api/routes/events.py` for the main HTTP flow.
4. `tasks/events.py` for the background pipeline.
5. `app/services/hybrid_search.py` and `app/services/embedding_store.py` for search.
6. `app/services/event_filter.py` and `tasks/events.py::filter_unprocessed_events` for the rule engine.
7. `celery_app.py` for the periodic schedule.
