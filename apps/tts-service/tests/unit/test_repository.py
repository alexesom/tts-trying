from pathlib import Path

from app.infrastructure.db.sqlite_repository import SQLiteJobRepository


def test_repository_create_and_update_job(tmp_path: Path) -> None:
    repo = SQLiteJobRepository(tmp_path / "tts.db")
    repo.init_schema()

    job_id, item_ids = repo.create_job("chat-1", ["https://example.com"])
    assert len(item_ids) == 1

    job = repo.get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"

    repo.update_job_status(job_id, "processing")
    updated = repo.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "processing"
