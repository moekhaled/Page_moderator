-- Async queue and control tables for production workers
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'done', 'failed');

CREATE TABLE IF NOT EXISTS llm_jobs (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    inbound_message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    status job_status NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outbound_jobs (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    llm_turn_id BIGINT REFERENCES llm_turns(id) ON DELETE SET NULL,
    recipient_platform_id VARCHAR(128) NOT NULL,
    reply_text TEXT NOT NULL,
    idempotency_key VARCHAR(191) NOT NULL UNIQUE,
    status job_status NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    meta_response_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_llm_jobs_status_created ON llm_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS ix_outbound_jobs_status_created ON outbound_jobs(status, created_at);
