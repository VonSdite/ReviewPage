#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .review_queue_worker import ReviewQueueWorker
    from .review_service import ReviewService

__all__ = ["ReviewService", "ReviewQueueWorker"]


def __getattr__(name: str):
    if name == "ReviewService":
        from .review_service import ReviewService

        return ReviewService
    if name == "ReviewQueueWorker":
        from .review_queue_worker import ReviewQueueWorker

        return ReviewQueueWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
