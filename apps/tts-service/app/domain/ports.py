from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.entities import ArtifactMeta, LmSelection, TtsSelection


@dataclass(slots=True)
class ParsedArticle:
    url: str
    markdown: str
    title: str | None


class ArticleParserPort(Protocol):
    def parse(self, url: str) -> ParsedArticle:
        ...


class TtsEnginePort(Protocol):
    def synthesize(self, text: str, selection: TtsSelection, output_basename: str) -> ArtifactMeta:
        ...


class LmClientPort(Protocol):
    def list_models(self) -> list[str]:
        ...

    def validate_model(self, model_id: str) -> tuple[bool, str | None]:
        ...

    def summarize(self, text: str, selection: LmSelection) -> str:
        ...

    def filename(self, text: str, url: str, selection: LmSelection) -> str:
        ...
