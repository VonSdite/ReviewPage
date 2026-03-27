#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检视记录仓储。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewRepository:
    """负责 ReviewRecord / ReviewLog 的持久化。"""

    def __init__(self, connection_factory):
        self._connection_factory = connection_factory
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._connection_factory() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mr_url TEXT NOT NULL,
                    hub_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    runtime_state TEXT NOT NULL,
                    result_text TEXT,
                    error_message TEXT,
                    command_line TEXT,
                    working_directory TEXT,
                    repo_url TEXT,
                    source_branch TEXT,
                    target_branch TEXT,
                    title TEXT,
                    author_name TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_log_seq INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    line TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(review_id) REFERENCES review_records(id)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_review_logs_review_seq
                ON review_logs(review_id, sequence)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_review_records_status_runtime_created
                ON review_records(status, runtime_state, created_at, id)
                """
            )

    def reset_running_pending_reviews(self) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                UPDATE review_records
                SET status = 'cancelled',
                    runtime_state = 'finished',
                    error_message = '任务已取消',
                    finished_at = ?,
                    updated_at = ?
                WHERE status = 'pending' AND runtime_state = 'canceling'
                """,
                (now, now),
            )
            conn.execute(
                """
                UPDATE review_records
                SET runtime_state = 'queued', started_at = NULL, updated_at = ?
                WHERE status = 'pending' AND runtime_state = 'running'
                """,
                (now,),
            )

    def create_review(
        self,
        *,
        mr_url: str,
        hub_id: str,
        agent_id: str,
        model_id: str,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connection_factory() as conn:
            cursor = conn.execute(
                """
                INSERT INTO review_records (
                    mr_url,
                    hub_id,
                    agent_id,
                    model_id,
                    status,
                    runtime_state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, 'pending', 'queued', ?, ?)
                """,
                (mr_url, hub_id, agent_id, model_id, now, now),
            )
            review_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def claim_next_pending_review(self) -> dict[str, Any] | None:
        now = _utc_now()
        with self._connection_factory() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE status = 'pending' AND runtime_state = 'queued'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            review_id = int(row["id"])

            conn.execute(
                """
                UPDATE review_records
                SET runtime_state = 'running', started_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, review_id),
            )
            claimed = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            return dict(claimed) if claimed is not None else None

    def update_execution_context(
        self,
        review_id: int,
        *,
        command_line: str | None = None,
        working_directory: str | None = None,
        repo_url: str | None = None,
        source_branch: str | None = None,
        target_branch: str | None = None,
        title: str | None = None,
        author_name: str | None = None,
    ) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                UPDATE review_records
                SET command_line = ?,
                    working_directory = ?,
                    repo_url = ?,
                    source_branch = ?,
                    target_branch = ?,
                    title = ?,
                    author_name = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    command_line,
                    working_directory,
                    repo_url,
                    source_branch,
                    target_branch,
                    title,
                    author_name,
                    now,
                    review_id,
                ),
            )

    def append_review_log(self, review_id: int, sequence: int, line: str) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                INSERT INTO review_logs (review_id, sequence, line, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (review_id, sequence, line, now),
            )
            conn.execute(
                """
                UPDATE review_records
                SET last_log_seq = ?, updated_at = ?
                WHERE id = ?
                """,
                (sequence, now, review_id),
            )

    def mark_review_completed(self, review_id: int, result_text: str) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                UPDATE review_records
                SET status = 'completed',
                    runtime_state = 'finished',
                    result_text = ?,
                    error_message = NULL,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (result_text, now, now, review_id),
            )

    def mark_review_failed(self, review_id: int, result_text: str, error_message: str) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                UPDATE review_records
                SET status = 'failed',
                    runtime_state = 'finished',
                    result_text = ?,
                    error_message = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (result_text, error_message, now, now, review_id),
            )

    def mark_review_cancelled(self, review_id: int, result_text: str, error_message: str) -> None:
        now = _utc_now()
        with self._connection_factory() as conn:
            conn.execute(
                """
                UPDATE review_records
                SET status = 'cancelled',
                    runtime_state = 'finished',
                    result_text = ?,
                    error_message = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (result_text, error_message, now, now, review_id),
            )

    def cancel_queued_review(self, review_id: int, error_message: str) -> dict[str, Any] | None:
        now = _utc_now()
        with self._connection_factory() as conn:
            cursor = conn.execute(
                """
                UPDATE review_records
                SET status = 'cancelled',
                    runtime_state = 'finished',
                    error_message = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'pending' AND runtime_state = 'queued'
                """,
                (error_message, now, now, review_id),
            )
            if int(cursor.rowcount or 0) <= 0:
                return None

            row = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def request_running_review_cancel(self, review_id: int) -> dict[str, Any] | None:
        now = _utc_now()
        with self._connection_factory() as conn:
            cursor = conn.execute(
                """
                UPDATE review_records
                SET runtime_state = 'canceling', updated_at = ?
                WHERE id = ? AND status = 'pending' AND runtime_state IN ('running', 'canceling')
                """,
                (now, review_id),
            )
            if int(cursor.rowcount or 0) <= 0:
                return None

            row = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def delete_review(self, review_id: int) -> bool:
        with self._connection_factory() as conn:
            row = conn.execute(
                """
                SELECT status, runtime_state
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            if row is None:
                return False

            status = str(row["status"] or "")
            runtime_state = str(row["runtime_state"] or "")
            if status == "pending" and runtime_state in {"running", "canceling"}:
                return False

            conn.execute(
                """
                DELETE FROM review_logs
                WHERE review_id = ?
                """,
                (review_id,),
            )
            cursor = conn.execute(
                """
                DELETE FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            )
            return int(cursor.rowcount or 0) > 0

    def rename_agent(self, agent_id: str, new_agent_id: str) -> int:
        now = _utc_now()
        with self._connection_factory() as conn:
            cursor = conn.execute(
                """
                UPDATE review_records
                SET agent_id = ?, updated_at = ?
                WHERE agent_id = ?
                """,
                (new_agent_id, now, agent_id),
            )
            return int(cursor.rowcount or 0)

    def rename_hub(self, hub_id: str, new_hub_id: str) -> int:
        now = _utc_now()
        with self._connection_factory() as conn:
            cursor = conn.execute(
                """
                UPDATE review_records
                SET hub_id = ?, updated_at = ?
                WHERE hub_id = ?
                """,
                (new_hub_id, now, hub_id),
            )
            return int(cursor.rowcount or 0)

    def list_reviews(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        page = max(int(page), 1)
        page_size = max(int(page_size), 1)
        offset = (page - 1) * page_size

        with self._connection_factory() as conn:
            total_row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM review_records
                """
            ).fetchone()
            total = int(total_row["total"] or 0) if total_row is not None else 0

            rows = conn.execute(
                """
                SELECT *
                FROM review_records
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
            return {
                "records": [dict(row) for row in rows],
                "total": total,
            }

    def get_review(self, review_id: int) -> dict[str, Any] | None:
        with self._connection_factory() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM review_records
                WHERE id = ?
                """,
                (review_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def list_review_logs(self, review_id: int) -> list[dict[str, Any]]:
        with self._connection_factory() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM review_logs
                WHERE review_id = ?
                ORDER BY sequence ASC, id ASC
                """,
                (review_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_queue_positions(self) -> dict[int, int]:
        with self._connection_factory() as conn:
            rows = conn.execute(
                """
                SELECT id
                FROM review_records
                WHERE status = 'pending' AND runtime_state = 'queued'
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
            return {int(row["id"]): index + 1 for index, row in enumerate(rows)}

    def get_review_stats(self) -> dict[str, int]:
        with self._connection_factory() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'pending' AND runtime_state = 'queued' THEN 1 ELSE 0 END) AS queued,
                    SUM(CASE WHEN status = 'pending' AND runtime_state IN ('running', 'canceling') THEN 1 ELSE 0 END) AS running,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
                FROM review_records
                """
            ).fetchone()
            if row is None:
                return {
                    "total": 0,
                    "queued": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0,
                    "cancelled": 0,
                }
            return {key: int(row[key] or 0) for key in row.keys()}
