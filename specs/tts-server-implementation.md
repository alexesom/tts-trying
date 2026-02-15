# TTS Server Implementation

## Goal
Provide an async job API that parses URL content with Firecrawl, synthesizes speech with MLX Audio, creates summary/filename with LM Studio, and exposes downloadable artifacts.

## Stack
- Runtime: Python 3.10+
- API: FastAPI
- Storage: SQLite (`sqlite3`)
- Web parsing: Firecrawl Python SDK
- TTS: `mlx-audio`
- LM: LM Studio OpenAI-compatible endpoint

## Module Layout
- `app/main.py`: composition root and dependency wiring.
- `app/config/settings.py`: environment config.
- `app/domain/entities.py`: job and selection entities.
- `app/domain/model_registry.py`: static TTS model registry.
- `app/domain/ports.py`: parser/TTS/LM contracts.
- `app/application/job_service.py`: async job orchestration.
- `app/infrastructure/db/sqlite_repository.py`: persistent job state.
- `app/infrastructure/firecrawl_parser.py`: URL -> markdown adapter.
- `app/infrastructure/mlx_tts_engine.py`: chunk, synthesize, merge, transcode.
- `app/infrastructure/lm_studio_client.py`: models, smoke-check, text generation.
- `app/interfaces/http/router.py`: API endpoints.
- `app/interfaces/http/schemas.py`: request/response schemas.

## Endpoints
- `GET /health`
- `GET /v1/tts/models`
- `GET /v1/lm/models`
- `POST /v1/lm/models/validate`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/items/{item_id}/artifact`
- `POST /v1/jobs/{job_id}/items/{item_id}/ack-sent`
- `POST /v1/jobs/{job_id}/cancel`

## Job Execution
1. Create job + job_items rows in `queued` state.
2. Schedule async processing task.
3. Process items with semaphore (`TTS_URL_CONCURRENCY=2`).
4. For each item:
- Scrape markdown via Firecrawl (`only_main_content=True`).
- Start three tasks in parallel:
  - TTS generation (chunk + merge + transcode).
  - Summary generation.
  - Filename generation.
- If summary/filename fails, use deterministic fallback.
- If TTS fails, mark item failed.
5. Aggregate item statuses into job status: `completed`, `partial_failed`, `failed`, or `cancelled`.

## TTS Behavior
- Input markdown normalized to plain text.
- No truncation policy for full content; large text is chunked.
- Output path strategy:
- Generate `.wav` intermediate.
- Transcode to `.ogg` for voice delivery.
- If voice file exceeds `VOICE_MAX_BYTES`, transcode to `.mp3` and mark artifact as `document`.

## LM Behavior
- `GET /v1/models` is proxied from LM Studio.
- Smoke-check attempts multiple request shapes to tolerate model template differences.
- Summary and filename endpoints are not public; used internally by job service.

## Persistence
## Tables
- `jobs`
- `job_items`
- `job_events`

## Cleanup Policy
- `ack-sent` deletes artifact file immediately.
- DB record keeps metadata but clears `artifact_path`.

## Test Coverage
- Repository CRUD (`tests/unit/test_repository.py`)
- Fallback utility behavior (`tests/unit/test_job_service_utils.py`)
- End-to-end job lifecycle with fake adapters (`tests/integration/test_job_lifecycle.py`)
