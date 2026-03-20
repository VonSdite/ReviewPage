#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后台串行任务 worker。"""

from __future__ import annotations

import threading

from ..application.app_context import AppContext


class ReviewQueueWorker:
    """轮询 pending 队列，并保证同一时刻仅执行一个任务。"""

    def __init__(self, ctx: AppContext, review_service, poll_interval_seconds: float = 2.0):
        self._ctx = ctx
        self._logger = ctx.logger
        self._review_service = review_service
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._review_service.reset_running_reviews()
        self._thread = threading.Thread(target=self._run_loop, name="review-queue-worker", daemon=True)
        self._thread.start()
        self._logger.info("Review queue worker started")

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def wake_up(self) -> None:
        self._wake_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                handled = self._review_service.execute_next_review()
            except Exception:
                self._logger.exception("Review queue worker crashed while executing task")
                handled = False

            if handled:
                continue

            self._wake_event.wait(timeout=self._poll_interval_seconds)
            self._wake_event.clear()
