from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobItemStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TtsSelection:
    model_id: str
    voice: str
    speed: float


@dataclass(slots=True)
class LmSelection:
    summary_model_id: str
    filename_model_id: str


@dataclass(slots=True)
class ArtifactMeta:
    path: str
    kind: str
    mime_type: str
    size_bytes: int


@dataclass(slots=True)
class Job:
    id: str
    chat_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
