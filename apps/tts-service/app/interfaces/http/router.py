from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.application.job_service import JobService
from app.config.settings import Settings, get_settings
from app.domain.entities import LmSelection, TtsSelection
from app.domain.model_registry import list_tts_models
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository
from app.infrastructure.lm_studio_client import LmStudioClient
from app.interfaces.http.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    JobItemResponse,
    JobStatusResponse,
    LmValidateRequest,
    LmValidateResponse,
)

router = APIRouter()


def get_repo(request: Request) -> SQLiteJobRepository:
    return request.app.state.repository


def get_lm_client(request: Request) -> LmStudioClient:
    return request.app.state.lm_client


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.get("/health")
def health(
    repo: SQLiteJobRepository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    repo.healthcheck()
    if not settings.firecrawl_api_key:
        return {"status": "degraded"}
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


@router.post("/v1/jobs", response_model=CreateJobResponse)
def create_job(
    request: CreateJobRequest,
    service: JobService = Depends(get_job_service),
) -> CreateJobResponse:
    tts = TtsSelection(
        model_id=request.tts.model_id,
        voice=request.tts.voice,
        speed=request.tts.speed,
    )
    lm = LmSelection(
        summary_model_id=request.lm.summary_model_id,
        filename_model_id=request.lm.filename_model_id,
    )

    job_id = service.create_job(
        chat_id=request.chat_id,
        urls=[str(url) for url in request.urls],
        tts=tts,
        lm=lm,
    )
    return CreateJobResponse(job_id=job_id, status="queued")


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, repo: SQLiteJobRepository = Depends(get_repo)) -> JobStatusResponse:
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = []
    for item in repo.get_job_items(job_id):
        artifact = None
        if item.get("artifact_path"):
            artifact = {
                "kind": item.get("artifact_kind"),
                "mime_type": item.get("mime_type"),
                "size_bytes": item.get("size_bytes"),
                "download_url": f"/v1/jobs/{job_id}/items/{item['id']}/artifact",
            }

        items.append(
            JobItemResponse(
                item_id=item["id"],
                url=item["url"],
                status=item["status"],
                summary=item.get("summary"),
                filename=item.get("filename"),
                artifact=artifact,
                error=item.get("error_message"),
            )
        )

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        error_message=job.get("error_message"),
        items=items,
    )


@router.get("/v1/jobs/{job_id}/items/{item_id}/artifact")
def download_artifact(
    job_id: str,
    item_id: str,
    repo: SQLiteJobRepository = Depends(get_repo),
):
    item = repo.get_job_item(job_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    artifact_path = item.get("artifact_path")
    if not artifact_path:
        raise HTTPException(status_code=404, detail="Artifact already acknowledged or missing")

    path = Path(artifact_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")

    extension = path.suffix.lower()
    filename = f"{item.get('filename') or item_id}{extension}"
    return FileResponse(path, media_type=item.get("mime_type") or "application/octet-stream", filename=filename)


@router.post("/v1/jobs/{job_id}/items/{item_id}/ack-sent")
def ack_sent(
    job_id: str,
    item_id: str,
    service: JobService = Depends(get_job_service),
) -> dict[str, bool]:
    ok = service.acknowledge_sent(job_id, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: str, service: JobService = Depends(get_job_service)) -> dict[str, bool]:
    ok = service.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}
