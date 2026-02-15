from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.domain.model_registry import list_tts_models
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository

router = APIRouter()


def get_repo(settings: Settings = Depends(get_settings)) -> SQLiteJobRepository:
    repo = SQLiteJobRepository(settings.db_path)
    repo.init_schema()
    return repo


@router.get("/health")
def health(repo: SQLiteJobRepository = Depends(get_repo)) -> dict[str, str]:
    repo.healthcheck()
    return {"status": "ok"}


@router.get("/v1/tts/models")
def tts_models() -> dict[str, list[dict[str, object]]]:
    models = [
        {
            "id": model.id,
            "label": model.label,
            "languages": model.languages,
            "voice_presets": model.voice_presets,
            "default_voice": model.default_voice,
            "speed_presets": model.speed_presets,
        }
        for model in list_tts_models()
    ]
    return {"data": models}
