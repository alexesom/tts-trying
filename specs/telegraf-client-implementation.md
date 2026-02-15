# Telegraf Client Implementation

## Goal
Implement a TypeScript Telegram client that uses button-driven settings, accepts URL messages, and delegates synthesis to the Python TTS API.

## Stack
- Runtime: Node.js 22+
- Framework: Telegraf (webhook mode)
- Storage: SQLite (`better-sqlite3`)
- HTTP client: Axios

## Module Layout
- `src/main.ts`: process bootstrap and webhook launch.
- `src/config/env.ts`: strict environment loading.
- `src/domain/types.ts`: shared client-side domain types.
- `src/infrastructure/db/sqliteRepository.ts`: persistence adapter.
- `src/infrastructure/http/ttsServiceClient.ts`: API adapter to Python service.
- `src/interfaces/telegraf/bot.ts`: UI handlers and bot orchestration.
- `src/application/url.ts`: URL extraction utility.

## Data Persistence
## Tables
- `user_settings(chat_id, tts_model, voice, speed, lm_summary_model, lm_filename_model, updated_at)`
- `pending_jobs(job_id, chat_id, status, created_at, updated_at)`

## UI and Handlers
## Reply Keyboard
- `Select TTS Model`
- `Select Voice`
- `Select Speed`
- `Select LM Summary Model`
- `Select LM Filename Model`
- `Show Current Settings`

## Inline Callback Patterns
- `tts_model:{index}`
- `voice_preset:{voice}`
- `voice_custom`
- `speed:{value}`
- `lm_summary:{index}`
- `lm_filename:{index}`

## URL Message Flow
1. Extract URLs from plain text.
2. Ensure settings exist for chat (lazy defaults from API).
3. `POST /v1/jobs` with selected models and TTS options.
4. Store pending job in SQLite.
5. Poll `GET /v1/jobs/{job_id}` every 3 seconds.
6. For completed items:
- Download artifact.
- Send as `voice` if kind is `voice`.
- Send as `document` if kind is `document`.
- Send summary as caption.
- Call `ack-sent`.
7. Remove pending job when terminal status is reached.

## LM Model Validation
- Before saving LM model from buttons, call `POST /v1/lm/models/validate`.
- Reject and show reason if smoke-check fails.

## Error Handling
- No models available -> user-facing setup error.
- Validation failure -> keep old setting and display reason.
- Poll timeout -> mark as failed and notify user.
- Partial failed job -> send failed URL list.

## Runtime Requirements
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_DOMAIN`
- `TELEGRAM_WEBHOOK_PORT`
- `TELEGRAM_WEBHOOK_PATH`
- `TTS_SERVICE_BASE_URL`
- `BOT_DB_PATH`

## Test Coverage
- URL extraction (`tests/url.test.ts`)
- SQLite repository read/write (`tests/sqliteRepository.test.ts`)
