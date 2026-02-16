from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
SERVICE_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

# Load monorepo-level env first, then service-local env (service file overrides shared values).
load_dotenv(REPO_ROOT_ENV_PATH, override=False)
load_dotenv(SERVICE_ENV_PATH, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

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
    parse_timeout_seconds: int = Field(default=60, alias="PARSE_TIMEOUT_SECONDS")
    tts_task_timeout_seconds: int = Field(default=900, alias="TTS_TASK_TIMEOUT_SECONDS")
    lm_task_timeout_seconds: int = Field(default=45, alias="LM_TASK_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
