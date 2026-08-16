# Backend - Async Production Baseline

Current scope:
- Receive Instagram webhook events from Meta.
- Persist inbound and outbound messages as history.
- Enqueue inbound LLM work (webhook path does not block on LLM calls).
- Process LLM decisions in async worker.
- Enqueue and send eligible outbound replies via async outbound worker.
- Provide moderator UI with global/per-conversation LLM pause controls.

## Architecture
1. Webhook app (`uvicorn app.main:app`)
   - Validates webhook signature.
   - Stores message + webhook event.
   - Enqueues `llm_jobs` for inbound customer messages.
2. LLM worker (`python -m app.workers.llm_worker`)
   - Claims pending `llm_jobs`.
   - Runs LangChain agent asynchronously.
   - Stores `llm_turns`.
   - If active mode and policy allows, enqueues `outbound_jobs`.
3. Outbound worker (`python -m app.workers.outbound_worker`)
   - Claims pending `outbound_jobs`.
   - Sends Meta message with retry/backoff.
   - Stores sent message and provider response metadata.
4. Migrator (`python -m app.run_migrations`)
   - Applies SQL migrations before app/workers start.

## Intent policy
Only `price_inquiry` is eligible for auto reply.
Always blocked from auto-send:
- `hiring_inquiry`
- `model_application`
- `moderator_message`

`unknown` or low-confidence `price_inquiry` => escalate_human (no auto-send).

## LLM response format
The system prompt requires strict JSON with a `messages` array.
Example:
- {"intent":"price_inquiry","messages":["message 1","message 2"], ...}

When auto-reply is allowed, backend enqueues one outbound job per entry in `messages`,
so each message is sent separately in order.

## Environment
Use `.env.example` as baseline. Critical keys:
- DATABASE_URL (async URL, e.g. `postgresql+asyncpg://...`)
- META_VERIFY_TOKEN
- META_APP_SECRET
- META_PAGE_ACCESS_TOKEN
- INSTAGRAM_BUSINESS_ACCOUNT_ID
- GEMINI_API_KEY (when `LLM_PROVIDER=gemini`)

## Local run (multi-process)
1. Init DB once
   - `python -m app.run_migrations`
2. App
   - `uvicorn app.main:app --reload --port 8000`
3. LLM worker
   - `python -m app.workers.llm_worker`
4. Outbound worker
   - `python -m app.workers.outbound_worker`

## Docker Compose run
1. `docker compose up --build`
2. Compose starts services in this order:
   - `postgres` (waits healthy)
   - `migrator` (runs migrations and exits successfully)
   - `app`, `llm-worker`, `outbound-worker`
3. App available on `http://localhost:8000`

## Dry run script
Prerequisites:
- Docker Desktop running
- `.env` file exists with valid values

Run:
- `powershell -ExecutionPolicy Bypass -File scripts/dry_run.ps1`

Script validates:
- Docker daemon + compose config
- Migration startup
- Service health endpoint
- Signed webhook ingestion smoke test

## Moderator controls
- Global pause/resume LLM: moderator conversations page.
- Per-conversation pause/resume LLM: conversation detail page.

## Endpoints
- `GET /health`
- `GET /webhook/meta`
- `POST /webhook/meta`
- `GET /moderator/login`
- `GET /moderator/conversations`
- `GET /moderator/conversations/{conversation_id}`
- `POST /moderator/llm/pause-global`
- `POST /moderator/conversations/{conversation_id}/llm-pause`
- `POST /internal/retention/run`

## Notes
- Keep `LLM_SHADOW_MODE=true` until you validate decisions in `llm_turns`.
- For full production, run behind HTTPS reverse proxy and managed secrets.

## Tests
- `pytest -q`
