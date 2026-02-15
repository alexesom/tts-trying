from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_host: str = Field(default="127.0.0.1", alias="TTS_SERVICE_HOST")
    service_port: int = Field(default=8000, alias="TTS_SERVICE_PORT")

    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")
    lm_studio_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LM_STUDIO_BASE_URL")

    db_path: Path = Field(
        default=Path("/Users/alex/Documents/tts-trying/apps/tts-service/data/tts.db"),
        alias="TTS_DB_PATH",
    )
    artifacts_dir: Path = Field(
        default=Path("/Users/alex/Documents/tts-trying/apps/tts-service/data/artifacts"),
        alias="TTS_ARTIFACTS_DIR",
    )

    url_concurrency: int = Field(default=2, alias="TTS_URL_CONCURRENCY")
    voice_max_bytes: int = Field(default=45_000_000, alias="VOICE_MAX_BYTES")
    lm_http_timeout_seconds: int = Field(default=30, alias="LM_HTTP_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
