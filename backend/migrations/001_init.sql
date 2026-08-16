-- 001_init.sql
CREATE TYPE conversation_status AS ENUM ('open', 'pending', 'closed');
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE author_type AS ENUM ('customer', 'human_moderator', 'llm_agent', 'system');
CREATE TYPE message_source AS ENUM ('meta_webhook', 'api_send', 'llm_worker');
CREATE TYPE send_status AS ENUM ('received', 'queued', 'sent', 'failed');

CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    channel VARCHAR(32) NOT NULL DEFAULT 'instagram',
    customer_platform_id VARCHAR(128) NOT NULL,
    page_platform_id VARCHAR(128) NOT NULL,
    status conversation_status NOT NULL DEFAULT 'open',
    llm_paused BOOLEAN NOT NULL DEFAULT FALSE,
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_conversation_party UNIQUE (channel, customer_platform_id, page_platform_id)
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    platform_message_id VARCHAR(191) UNIQUE,
    direction message_direction NOT NULL,
    author_type author_type NOT NULL,
    author_id VARCHAR(128) NOT NULL,
    text TEXT,
    attachments_json JSONB,
    source message_source NOT NULL DEFAULT 'meta_webhook',
    send_status send_status NOT NULL DEFAULT 'received',
    reply_to_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_events (
    id BIGSERIAL PRIMARY KEY,
    event_key VARCHAR(191) NOT NULL UNIQUE,
    object_type VARCHAR(64) NOT NULL,
    payload_json JSONB NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE message_summaries (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    covered_until_message_id BIGINT NOT NULL,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE llm_turns (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    inbound_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    model_name VARCHAR(128) NOT NULL,
    intent VARCHAR(64),
    confidence DOUBLE PRECISION,
    requires_human BOOLEAN NOT NULL DEFAULT TRUE,
    reply_text TEXT,
    required_capabilities_json JSONB,
    next_actions_json JSONB,
    safety_flags_json JSONB,
    input_messages_count INTEGER,
    latency_ms INTEGER,
    run_mode VARCHAR(32) NOT NULL DEFAULT 'shadow',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_conversations_last_message_at ON conversations(last_message_at);
CREATE INDEX ix_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX ix_message_summaries_conversation ON message_summaries(conversation_id);
CREATE INDEX ix_llm_turns_conversation_created ON llm_turns(conversation_id, created_at);
CREATE INDEX ix_llm_turns_inbound_message ON llm_turns(inbound_message_id);
