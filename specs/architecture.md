# Architecture

## System Overview
The solution is split into two local services:
1. `telegram-bot` (TypeScript, Telegraf): user interaction and delivery.
2. `tts-service` (Python, FastAPI): parsing, synthesis, summarization, job orchestration.

The bot never runs ML workloads. The Python service never speaks directly to Telegram.

## Primary Use Cases
1. User configures settings via buttons (TTS model, voice, speed, LM models).
2. User sends one or more URLs.
3. Bot creates one async job in TTS service.
4. TTS service processes URLs in parallel (limit 2) and generates one artifact per URL.
5. Bot polls job status, sends artifacts, then acknowledges delivery for cleanup.

## Sequence (URL -> Audio)
1. Telegram message arrives in webhook handler.
2. Bot extracts URLs and reads chat settings from SQLite.
3. Bot calls `POST /v1/jobs`.
4. TTS service stores `jobs` + `job_items` and schedules async processing.
5. Worker pipeline per URL:
- Firecrawl parse -> markdown.
- MLX TTS generation.
- LM summary + LM filename (parallel tasks).
6. TTS service exposes each artifact via download endpoint.
7. Bot downloads and sends:
- `send_voice` for `voice` artifacts.
- `send_document` for oversized fallback.
8. Bot calls `ack-sent`; service deletes artifact immediately.

## Edge Cases
1. URL parse failure:
- Item marked `failed`, other items continue.
- Job may become `partial_failed`.
2. LM summary or filename generation fails:
- Deterministic fallback text/filename used.
- Item can still be `completed` if TTS succeeded.
3. TTS generation fails:
- Item marked `failed`.
- Failure reason persisted in `job_items.error_message`.
4. Oversized voice artifact:
- Service generates document artifact (`mp3`) and marks kind `document`.
5. LM model incompatible with chat/completions:
- Model rejected during UI selection via smoke-check endpoint.
6. User sends text without URLs:
- Bot responds with instructions and keeps current settings.
7. Job cancelled:
- Job status -> `cancelled`, queued/processing items move to `cancelled`.

## Non-Goals (V1)
- Speech-to-text (STT).
- Distributed queues/workers.
- Multi-tenant auth.
- Cloud deployment automation.

## Reliability Notes
- DB-backed state enables restart-safe status retrieval.
- Immediate artifact cleanup minimizes disk pressure.
- Polling model keeps inter-service API simple and explicit.
