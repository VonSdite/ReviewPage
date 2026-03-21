#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页面与 API 控制器。"""

from __future__ import annotations

from flask import Response, jsonify, render_template, request

from ..application.app_context import AppContext
from ..services import ReviewQueueWorker, ReviewService


class WebController:
    """处理页面渲染、任务提交与查询。"""

    def __init__(self, ctx: AppContext, review_service: ReviewService, queue_worker: ReviewQueueWorker):
        self._ctx = ctx
        self._app = ctx.flask_app
        self._logger = ctx.logger
        self._review_service = review_service
        self._queue_worker = queue_worker
        self._register_routes()

    def _register_routes(self) -> None:
        self._app.route("/")(self.index)
        self._app.route("/api/meta", methods=["GET"])(self.get_meta)
        self._app.route("/api/reviews", methods=["GET"])(self.list_reviews)
        self._app.route("/api/reviews", methods=["POST"])(self.create_review)
        self._app.route("/api/reviews/<int:review_id>", methods=["GET"])(self.get_review_detail)
        self._app.route("/api/reviews/<int:review_id>/retry", methods=["POST"])(self.retry_review)

    def index(self) -> str:
        return render_template("review.html")

    def get_meta(self) -> Response:
        try:
            return jsonify(self._review_service.get_metadata())
        except Exception as exc:
            self._logger.exception("Failed to get review metadata")
            return jsonify({"error": str(exc)}), 500

    def list_reviews(self) -> Response:
        try:
            page = max(int(request.args.get("page", 1)), 1)
            page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
            return jsonify(self._review_service.list_reviews(page=page, page_size=page_size))
        except ValueError:
            return jsonify({"error": "page and page_size must be integers"}), 400
        except Exception as exc:
            self._logger.exception("Failed to list reviews")
            return jsonify({"error": str(exc)}), 500

    def create_review(self) -> Response:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "request body must be an object"}), 400

        try:
            review = self._review_service.create_review(payload)
            self._queue_worker.wake_up()
            return jsonify(review), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to create review")
            return jsonify({"error": str(exc)}), 500

    def get_review_detail(self, review_id: int) -> Response:
        try:
            detail = self._review_service.get_review_detail(review_id)
            if detail is None:
                return jsonify({"error": "review record not found"}), 404
            return jsonify(detail)
        except Exception as exc:
            self._logger.exception("Failed to get review detail")
            return jsonify({"error": str(exc)}), 500

    def retry_review(self, review_id: int) -> Response:
        try:
            review = self._review_service.retry_review(review_id)
            if review is None:
                return jsonify({"error": "review record not found"}), 404
            self._queue_worker.wake_up()
            return jsonify(review), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to retry review")
            return jsonify({"error": str(exc)}), 500
