---
name: tts_repo_agent
description: Implementation and maintenance agent for the Telegraf client + Python TTS service monorepo
---

## Commands (Run First)
- Telegram client install: `cd /Users/alex/Documents/tts-trying/apps/telegram-bot && npm install`
- Telegram client dev: `cd /Users/alex/Documents/tts-trying/apps/telegram-bot && npm run dev`
- Telegram client test: `cd /Users/alex/Documents/tts-trying/apps/telegram-bot && npm run test`
- Telegram client build: `cd /Users/alex/Documents/tts-trying/apps/telegram-bot && npm run build`
- TTS service setup: `cd /Users/alex/Documents/tts-trying/apps/tts-service && python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e .[dev]`
- TTS service run: `cd /Users/alex/Documents/tts-trying/apps/tts-service && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000`
- TTS service tests: `cd /Users/alex/Documents/tts-trying/apps/tts-service && . .venv/bin/activate && python -m pytest -q`

## Testing Expectations
- Run relevant tests before every commit.
- For Telegram-side changes: run `npm run test` and `npm run build`.
- For Python-side changes: run `python -m pytest -q`.
- For cross-service changes: run both stacks’ tests.

## Project Structure
- `/Users/alex/Documents/tts-trying/apps/telegram-bot`: TypeScript Telegraf webhook client.
- `/Users/alex/Documents/tts-trying/apps/tts-service`: Python FastAPI TTS service.
- `/Users/alex/Documents/tts-trying/specs`: implementation specs and architecture notes.
- `/Users/alex/Documents/tts-trying/.env.example`: required runtime env vars.

## Code Style Rules
- Keep use-case logic in application layer, adapters in infrastructure layer, HTTP handlers thin.
- Prefer explicit typed data objects over ad-hoc dictionaries on TypeScript side.
- Prefer small pure helper functions for parsing/sanitization.

## Good vs Bad Example
```ts
// Good: explicit validation and clear branch behavior
const urls = extractUrls(text);
if (!urls.length) {
  await ctx.reply("Send one or more URLs.");
  return;
}

// Bad: implicit assumptions and hidden failure
const firstUrl = text.split(" ")[0];
await submit(firstUrl);
```

## Git Workflow
- Structure work into small commits by concern.
- Commit and push frequently after each logically complete step.
- Preferred pattern for this repo:
1. infra/config changes
2. python service changes
3. telegram client changes
4. tests
5. docs
- Commit message style: `type(scope): summary`.

## Boundaries
- ✅ Always:
- Preserve clean architecture boundaries.
- Keep credentials in env vars.
- Add/adjust tests when behavior changes.
- ⚠️ Ask first:
- Major API contract changes.
- Database schema rewrites or data migrations.
- Adding heavy dependencies or changing runtime topology.
- 🚫 Never:
- Commit secrets, tokens, or local credential files.
- Edit generated lockfiles manually.
- Remove failing tests to make CI pass.

## Security Constraints
- Never print bot token, Firecrawl key, or other secrets in logs.
- Keep `.env` out of git.
- Validate external input (URLs, callback payloads, filenames).

## Scope Rules for This Repo
- V1 scope is TTS-only (no STT).
- URL input maps to async jobs in TTS service.
- Multi-URL messages produce one artifact per URL.
- Artifact cleanup is immediate after `ack-sent`.
