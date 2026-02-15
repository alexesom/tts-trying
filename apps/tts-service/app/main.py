from fastapi import FastAPI

from app.application.job_service import JobService
from app.config.settings import get_settings
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository
from app.infrastructure.firecrawl_parser import FirecrawlArticleParser
from app.infrastructure.lm_studio_client import LmStudioClient
from app.infrastructure.mlx_tts_engine import MlxTtsEngine
from app.interfaces.http.router import router

settings = get_settings()

repository = SQLiteJobRepository(settings.db_path)
repository.init_schema()

lm_client = LmStudioClient(
    base_url=settings.lm_studio_base_url,
    timeout_seconds=settings.lm_http_timeout_seconds,
)

article_parser = FirecrawlArticleParser(api_key=settings.firecrawl_api_key) if settings.firecrawl_api_key else None
tts_engine = MlxTtsEngine(settings.artifacts_dir, settings.voice_max_bytes)

if article_parser is None:
    # Delay hard failure; health endpoint will be degraded until key is provided.
    class _MissingParser:  # noqa: D401
        def parse(self, url: str):  # type: ignore[no-untyped-def]
            raise RuntimeError("FIRECRAWL_API_KEY is missing")

    article_parser = _MissingParser()

job_service = JobService(
    repository=repository,
    parser=article_parser,
    tts_engine=tts_engine,
    lm_client=lm_client,
    url_concurrency=settings.url_concurrency,
)

app = FastAPI(title="TTS Service", version="0.1.0")
app.state.repository = repository
app.state.lm_client = lm_client
app.state.job_service = job_service
app.include_router(router)
