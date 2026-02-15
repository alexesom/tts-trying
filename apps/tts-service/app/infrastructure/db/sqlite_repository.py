from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4


class SQLiteJobRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = RLock()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_items (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT,
                    filename TEXT,
                    artifact_path TEXT,
                    artifact_kind TEXT,
                    mime_type TEXT,
                    size_bytes INTEGER,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_events (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    item_id TEXT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_items_job_id ON job_items(job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_items_status ON job_items(status)")

    def healthcheck(self) -> bool:
        with self._lock, self._conn() as conn:
            conn.execute("SELECT 1")
            return True

    def create_job(self, chat_id: str, urls: list[str]) -> tuple[str, list[str]]:
        now = self.now_iso()
        job_id = str(uuid4())
        item_ids = [str(uuid4()) for _ in urls]

        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO jobs (id, chat_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, chat_id, "queued", now, now),
            )
            conn.executemany(
                """
                INSERT INTO job_items (
                    id, job_id, url, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [(item_id, job_id, url, "queued", now, now) for item_id, url in zip(item_ids, urls)],
            )

        return job_id, item_ids

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def get_job_items(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM job_items WHERE job_id = ? ORDER BY created_at ASC",
                (job_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_job_item(self, job_id: str, item_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM job_items WHERE id = ? AND job_id = ?",
                (item_id, job_id),
            ).fetchone()
            return dict(row) if row else None

    def update_job_status(self, job_id: str, status: str, error_message: str | None = None) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status, error_message, self.now_iso(), job_id),
            )

    def update_item_status(self, item_id: str, status: str, error_message: str | None = None) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE job_items SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status, error_message, self.now_iso(), item_id),
            )

    def set_item_result(
        self,
        item_id: str,
        *,
        summary: str,
        filename: str,
        artifact_path: str,
        artifact_kind: str,
        mime_type: str,
        size_bytes: int,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE job_items
                SET
                    status = ?,
                    summary = ?,
                    filename = ?,
                    artifact_path = ?,
                    artifact_kind = ?,
                    mime_type = ?,
                    size_bytes = ?,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "completed",
                    summary,
                    filename,
                    artifact_path,
                    artifact_kind,
                    mime_type,
                    size_bytes,
                    self.now_iso(),
                    item_id,
                ),
            )

    def clear_item_artifact(self, item_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE job_items
                SET artifact_path = NULL, updated_at = ?
                WHERE id = ?
                """,
                (self.now_iso(), item_id),
            )

    def add_event(self, job_id: str, level: str, message: str, item_id: str | None = None) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO job_events (id, job_id, item_id, level, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), job_id, item_id, level, message, self.now_iso()),
            )

    def mark_cancelled(self, job_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                ("cancelled", self.now_iso(), job_id),
            )
            conn.execute(
                """
                UPDATE job_items
                SET status = CASE WHEN status IN ('queued', 'processing') THEN 'cancelled' ELSE status END,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (self.now_iso(), job_id),
            )

    def is_cancelled(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        return bool(job and job["status"] == "cancelled")

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
