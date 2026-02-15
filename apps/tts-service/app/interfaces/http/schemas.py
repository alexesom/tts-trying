from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class LmValidateRequest(BaseModel):
    model_id: str = Field(min_length=1)


class LmValidateResponse(BaseModel):
    valid: bool
    reason: str | None = None


class TtsSelectionRequest(BaseModel):
    model_id: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    speed: float = Field(gt=0)


class LmSelectionRequest(BaseModel):
    summary_model_id: str = Field(min_length=1)
    filename_model_id: str = Field(min_length=1)


class DeliveryRequest(BaseModel):
    prefer: Literal["voice", "document"] = "voice"
    fallback: Literal["voice", "document"] = "document"


class CreateJobRequest(BaseModel):
    chat_id: str = Field(min_length=1)
    urls: list[HttpUrl] = Field(min_length=1)
    tts: TtsSelectionRequest
    lm: LmSelectionRequest
    delivery: DeliveryRequest = DeliveryRequest()


class CreateJobResponse(BaseModel):
    job_id: str
    status: str


class JobItemResponse(BaseModel):
    item_id: str
    url: str
    status: str
    summary: str | None = None
    filename: str | None = None
    artifact: dict | None = None
    error: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error_message: str | None = None
    items: list[JobItemResponse]
