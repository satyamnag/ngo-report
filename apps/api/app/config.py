"""Application configuration loaded from environment variables.

All secrets are injected via environment / .env. No secrets are hardcoded.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "NGO Report API"
    debug: bool = False

    # --- Database ---
    database_url: str = (
        "postgresql+psycopg://ngo_app:ngo_app_dev_password@localhost:5432/ngo_report"
    )

    # --- Celery / Redis ---
    redis_url: str = "redis://localhost:6379/0"
    celery_task_eager: bool = False

    # --- Auth ---
    jwt_secret: str = "dev-only-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # When False, authentication is disabled: every request acts as the demo
    # user/org. Used until Clerk auth is integrated.
    auth_enabled: bool = True

    # --- AI content generation (OpenAI) ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    youtube_api_key: str = ""

    # --- Object storage ---
    # "local"  -> filesystem under storage_local_dir (dev, no MinIO needed)
    # "minio"  -> S3-compatible object store
    storage_backend: str = "local"
    storage_local_dir: str = "data/storage"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "ngo-report"
    public_base_url: str = "http://localhost:8000"

    # --- Uploads / security ---
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_image_types: list[str] = [
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    ]

    # --- CORS ---
    frontend_origin: str = "http://localhost:3000"

    # --- Templates ---
    template_assets_dir: str = "templates"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()