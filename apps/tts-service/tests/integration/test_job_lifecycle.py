import asyncio
from pathlib import Path

from app.application.job_service import JobService
from app.domain.entities import ArtifactMeta, LmSelection, TtsSelection
from app.domain.ports import ParsedArticle
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository


class FakeParser:
    def parse(self, url: str) -> ParsedArticle:
        return ParsedArticle(url=url, markdown="Some content for testing.", title="Title")


class FakeTtsEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def synthesize(self, text: str, selection: TtsSelection, output_basename: str) -> ArtifactMeta:
        path = self.root / f"{output_basename}.ogg"
        path.write_bytes(b"audio")
        return ArtifactMeta(path=str(path), kind="voice", mime_type="audio/ogg", size_bytes=5)


class FakeLmClient:
    def list_models(self) -> list[str]:
        return ["fake"]

    def validate_model(self, model_id: str):  # type: ignore[no-untyped-def]
        return True, None

    def summarize(self, text: str, selection: LmSelection) -> str:
        return "summary"

    def filename(self, text: str, url: str, selection: LmSelection) -> str:
        return "file-name"


def test_job_lifecycle(tmp_path: Path) -> None:
    repo = SQLiteJobRepository(tmp_path / "tts.db")
    repo.init_schema()

    service = JobService(
        repository=repo,
        parser=FakeParser(),
        tts_engine=FakeTtsEngine(tmp_path),
        lm_client=FakeLmClient(),
        url_concurrency=2,
    )

    async def run_job_and_wait() -> str:
        job_id = await service.create_job(
            chat_id="chat-1",
            urls=["https://example.com", "https://example.org"],
            tts=TtsSelection(model_id="m", voice="v", speed=1.0),
            lm=LmSelection(summary_model_id="s", filename_model_id="f"),
        )
        for _ in range(100):
            job = repo.get_job(job_id)
            if job and job["status"] in {"completed", "partial_failed", "failed", "cancelled"}:
                items = repo.get_job_items(job_id)
                assert len(items) == 2
                assert all(item["status"] == "completed" for item in items)
                return job["status"]
            await asyncio.sleep(0.05)
        return "timeout"

    status = asyncio.run(run_job_and_wait())
    assert status == "completed"
