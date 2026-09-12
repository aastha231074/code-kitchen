"""Environment-driven config shared by every service.

Every service reads the same handful of env vars so local docker-compose
and Cloud Run deployment use identical code paths -- only the values differ.
"""
import os


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://codekitchen:codekitchen@localhost:5432/codekitchen"
    )

    # Pub/Sub
    pubsub_project_id: str = os.getenv("PUBSUB_PROJECT_ID", "codekitchen-local")
    pubsub_emulator_host: str | None = os.getenv("PUBSUB_EMULATOR_HOST")  # e.g. "pubsub:8085" locally
    topic_ingestion_trigger: str = os.getenv("TOPIC_INGESTION_TRIGGER", "ingestion-trigger")
    topic_jobs_raw: str = os.getenv("TOPIC_JOBS_RAW", "jobs-raw")
    topic_jobs_raw_dlq: str = os.getenv("TOPIC_JOBS_RAW_DLQ", "jobs-raw-dlq")

    # Storage (local dev falls back to a filesystem directory; GCS in prod)
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")  # "local" | "gcs"
    local_storage_root: str = os.getenv("LOCAL_STORAGE_ROOT", "/data/storage")
    gcs_bucket_raw_jobs: str = os.getenv("GCS_BUCKET_RAW_JOBS", "")
    gcs_bucket_resumes: str = os.getenv("GCS_BUCKET_RESUMES", "")

    # AI
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_flash_model: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
    gemini_pro_model: str = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))
    use_mock_ai: bool = _bool("USE_MOCK_AI", default=not os.getenv("GEMINI_API_KEY"))

    # Ingestion
    enable_linkedin_scrape: bool = _bool("ENABLE_LINKEDIN_SCRAPE", default=False)
    indeed_api_key: str = os.getenv("INDEED_API_KEY", "")
    indeed_publisher_id: str = os.getenv("INDEED_PUBLISHER_ID", "")

    # Auth
    auth_mode: str = os.getenv("AUTH_MODE", "dev")  # "dev" (accepts X-User-Email header) | "firebase"
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")

    # Rate limiting / quotas
    match_requests_per_hour: int = int(os.getenv("MATCH_REQUESTS_PER_HOUR", "30"))
    generate_requests_per_day: int = int(os.getenv("GENERATE_REQUESTS_PER_DAY", "20"))

    # Referral contact retention (days) -- placeholder pending legal sign-off,
    # see db/migrations/002_referral_contacts.sql
    referral_retention_days: int = int(os.getenv("REFERRAL_RETENTION_DAYS", "90"))

    # Vector-search migration trigger, monitored not hardcoded -- see ADR-02
    pgvector_row_ceiling: int = int(os.getenv("PGVECTOR_ROW_CEILING", "5000000"))
    pgvector_latency_ceiling_ms: int = int(os.getenv("PGVECTOR_LATENCY_CEILING_MS", "300"))


settings = Settings()
