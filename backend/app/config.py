from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Page Moderator Backend"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/page_moderator"
    meta_verify_token: str = "change-me"
    meta_app_secret: str = "change-me"
    meta_page_access_token: str = ""
    meta_graph_version: str = "v23.0"
    instagram_business_account_id: str = ""
    moderator_shared_password: str = "change-me"
    session_secret_key: str = "change-me"
    retention_days: int = 90
    raw_event_retention_days: int = 14
    timezone_name: str = "Africa/Cairo"

    llm_enabled: bool = False
    llm_shadow_mode: bool = True
    llm_provider: str = "gemini"
    llm_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: int = 20
    llm_history_limit: int = 20
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    llm_allowed_autoreply_intents: str = "price_inquiry"
    llm_price_inquiry_min_confidence: float = 0.80

    openai_api_key: str = ""
    gemini_api_key: str = ""

    policy_require_whatsapp_verification: bool = True
    policy_require_deposit_verification: bool = True

    worker_poll_seconds: int = 2
    worker_batch_size: int = 20
    outbound_max_attempts: int = 5

    global_llm_paused: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
