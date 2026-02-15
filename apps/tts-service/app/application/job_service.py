from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.domain.entities import LmSelection, TtsSelection
from app.domain.ports import ArticleParserPort, LmClientPort, TtsEnginePort
from app.infrastructure.db.sqlite_repository import SQLiteJobRepository


class JobService:
    def __init__(
        self,
        repository: SQLiteJobRepository,
        parser: ArticleParserPort,
        tts_engine: TtsEnginePort,
        lm_client: LmClientPort,
        url_concurrency: int,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._tts_engine = tts_engine
        self._lm_client = lm_client
        self._url_concurrency = max(1, url_concurrency)
        self._running_jobs: dict[str, asyncio.Task[None]] = {}

    async def create_job(
        self,
        *,
        chat_id: str,
        urls: list[str],
        tts: TtsSelection,
        lm: LmSelection,
    ) -> str:
        job_id, _ = self._repository.create_job(chat_id, urls)
        task = asyncio.create_task(self._process_job(job_id=job_id, tts=tts, lm=lm), name=f"job-{job_id}")
        self._running_jobs[job_id] = task
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        job = self._repository.get_job(job_id)
        if not job:
            return False
        self._repository.mark_cancelled(job_id)
        task = self._running_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
        return True

    async def _process_job(self, *, job_id: str, tts: TtsSelection, lm: LmSelection) -> None:
        self._repository.update_job_status(job_id, "processing")
        self._repository.add_event(job_id, "info", "Job started")

        items = self._repository.get_job_items(job_id)
        semaphore = asyncio.Semaphore(self._url_concurrency)

        async def run_item(item: dict) -> None:
            async with semaphore:
                await self._process_item(job_id=job_id, item=item, tts=tts, lm=lm)

        try:
            await asyncio.gather(*(run_item(item) for item in items), return_exceptions=False)
        except asyncio.CancelledError:
            self._repository.add_event(job_id, "warning", "Job cancelled")
            self._repository.mark_cancelled(job_id)
            raise
        finally:
            self._running_jobs.pop(job_id, None)

        if self._repository.is_cancelled(job_id):
            return

        final_items = self._repository.get_job_items(job_id)
        statuses = {item["status"] for item in final_items}
        if statuses == {"completed"}:
            final_status = "completed"
        elif "completed" in statuses:
            final_status = "partial_failed"
        elif statuses == {"cancelled"}:
            final_status = "cancelled"
        else:
            final_status = "failed"

        self._repository.update_job_status(job_id, final_status)
        self._repository.add_event(job_id, "info", f"Job finished with status={final_status}")

    async def _process_item(
        self,
        *,
        job_id: str,
        item: dict,
        tts: TtsSelection,
        lm: LmSelection,
    ) -> None:
        item_id = item["id"]

        if self._repository.is_cancelled(job_id):
            self._repository.update_item_status(item_id, "cancelled")
            return

        self._repository.update_item_status(item_id, "processing")
        self._repository.add_event(job_id, "info", "Item processing started", item_id)

        try:
            article = await asyncio.to_thread(self._parser.parse, item["url"])

            tts_task = asyncio.to_thread(
                self._tts_engine.synthesize,
                article.markdown,
                tts,
                f"{job_id}-{item_id}",
            )
            summary_task = asyncio.to_thread(self._lm_client.summarize, article.markdown, lm)
            filename_task = asyncio.to_thread(self._lm_client.filename, article.markdown, article.url, lm)

            tts_result, summary_result, filename_result = await asyncio.gather(
                tts_task,
                summary_task,
                filename_task,
                return_exceptions=True,
            )

            if isinstance(tts_result, Exception):
                raise tts_result

            summary = (
                self._fallback_summary(article.markdown)
                if isinstance(summary_result, Exception)
                else str(summary_result).strip()
            )
            filename_raw = (
                self._fallback_filename(article.url)
                if isinstance(filename_result, Exception)
                else str(filename_result).strip()
            )
            filename = self._sanitize_filename(filename_raw, article.url)

            self._repository.set_item_result(
                item_id,
                summary=summary,
                filename=filename,
                artifact_path=tts_result.path,
                artifact_kind=tts_result.kind,
                mime_type=tts_result.mime_type,
                size_bytes=tts_result.size_bytes,
            )
            self._repository.add_event(job_id, "info", "Item processing completed", item_id)
        except Exception as exc:  # noqa: BLE001
            self._repository.update_item_status(item_id, "failed", str(exc))
            self._repository.add_event(job_id, "error", f"Item failed: {exc}", item_id)

    def acknowledge_sent(self, job_id: str, item_id: str) -> bool:
        item = self._repository.get_job_item(job_id, item_id)
        if not item:
            return False

        artifact_path = item.get("artifact_path")
        if artifact_path:
            path = Path(artifact_path)
            if path.exists():
                path.unlink(missing_ok=True)

        self._repository.clear_item_artifact(item_id)
        self._repository.add_event(job_id, "info", "Artifact acknowledged and deleted", item_id)
        return True

    @staticmethod
    def _fallback_summary(markdown: str) -> str:
        text = re.sub(r"\s+", " ", markdown).strip()
        if not text:
            return "No summary available."
        return text[:480]

    @staticmethod
    def _fallback_filename(url: str) -> str:
        host = urlparse(url).netloc or "audio"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{host}-{ts}"

    @staticmethod
    def _sanitize_filename(candidate: str, url: str) -> str:
        fallback = JobService._fallback_filename(url)
        base = candidate.strip().lower() or fallback
        base = base.replace(".mp3", "").replace(".ogg", "")
        base = re.sub(r"[^a-z0-9\-\s_]", "", base)
        base = re.sub(r"[\s_]+", "-", base)
        base = re.sub(r"-+", "-", base).strip("-")
        if not base:
            return fallback
        return base[:96]
