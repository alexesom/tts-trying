from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.domain.model_registry import list_tts_models
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository
from app.infrastructure.lm_studio_client import LmStudioClient
from app.interfaces.http.schemas import LmValidateRequest, LmValidateResponse

router = APIRouter()


def get_repo(settings: Settings = Depends(get_settings)) -> SQLiteJobRepository:
    repo = SQLiteJobRepository(settings.db_path)
    repo.init_schema()
    return repo


def get_lm_client(settings: Settings = Depends(get_settings)) -> LmStudioClient:
    return LmStudioClient(
        base_url=settings.lm_studio_base_url,
        timeout_seconds=settings.lm_http_timeout_seconds,
    )


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


@router.get("/v1/lm/models")
def lm_models(client: LmStudioClient = Depends(get_lm_client)) -> dict[str, list[dict[str, str]]]:
    models = [{"id": model_id} for model_id in client.list_models()]
    return {"data": models}


@router.post("/v1/lm/models/validate", response_model=LmValidateResponse)
def validate_lm_model(
    request: LmValidateRequest,
    client: LmStudioClient = Depends(get_lm_client),
) -> LmValidateResponse:
    result = client.validate_model(request.model_id)
    return LmValidateResponse(valid=result.valid, reason=result.reason)
