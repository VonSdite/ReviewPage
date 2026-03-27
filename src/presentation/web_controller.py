#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Page and API controller."""

from __future__ import annotations

from flask import Response, jsonify, render_template, request

from ..application.app_context import AppContext
from ..services import ReviewQueueWorker, ReviewService


class WebController:
    """Handle page rendering and JSON APIs."""

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
        self._app.route("/api/settings", methods=["GET"])(self.get_settings)
        self._app.route("/api/agents/<string:agent_id>/models/fetch", methods=["POST"])(self.fetch_agent_models_preview)
        self._app.route("/api/agents/<string:agent_id>/models/refresh", methods=["POST"])(self.refresh_agent_models)
        self._app.route("/api/agents/<string:agent_id>/default-model", methods=["POST"])(self.set_agent_default_model)
        self._app.route("/api/settings/agents/<string:agent_id>", methods=["POST"])(self.save_agent_settings)
        self._app.route("/api/settings/agents/<string:agent_id>", methods=["DELETE"])(self.delete_agent_settings)
        self._app.route("/api/settings/agents/<string:agent_id>/default", methods=["POST"])(self.set_default_agent)
        self._app.route("/api/settings/hubs/<string:hub_id>", methods=["POST"])(self.save_hub_settings)
        self._app.route("/api/settings/hubs/<string:hub_id>", methods=["DELETE"])(self.delete_hub_settings)
        self._app.route("/api/settings/hubs/<string:hub_id>/default", methods=["POST"])(self.set_default_hub)
        self._app.route("/api/reviews", methods=["GET"])(self.list_reviews)
        self._app.route("/api/reviews", methods=["POST"])(self.create_review)
        self._app.route("/api/reviews/<int:review_id>", methods=["GET"])(self.get_review_detail)
        self._app.route("/api/reviews/<int:review_id>/cancel", methods=["POST"])(self.cancel_review)

    def index(self) -> str:
        return render_template("review.html")

    def get_meta(self) -> Response:
        try:
            return jsonify(self._review_service.get_metadata())
        except Exception as exc:
            self._logger.exception("Failed to get review metadata")
            return jsonify({"error": str(exc)}), 500

    def get_settings(self) -> Response:
        try:
            return jsonify(self._review_service.get_settings())
        except Exception as exc:
            self._logger.exception("Failed to get settings metadata")
            return jsonify({"error": str(exc)}), 500

    def fetch_agent_models_preview(self, agent_id: str) -> Response:
        payload = request.get_json(silent=True)
        if payload is not None and not isinstance(payload, dict):
            return jsonify({"error": "请求体必须是对象。"}), 400

        try:
            return jsonify(self._review_service.fetch_agent_models_preview(agent_id, payload))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to fetch agent models preview")
            return jsonify({"error": str(exc)}), 500

    def refresh_agent_models(self, agent_id: str) -> Response:
        try:
            return jsonify(self._review_service.refresh_agent_models(agent_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to refresh agent models")
            return jsonify({"error": str(exc)}), 500

    def set_agent_default_model(self, agent_id: str) -> Response:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "请求体必须是对象。"}), 400

        try:
            return jsonify(self._review_service.set_agent_default_model(agent_id, str(payload.get("model_id") or "")))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to set agent default model")
            return jsonify({"error": str(exc)}), 500

    def save_agent_settings(self, agent_id: str) -> Response:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "请求体必须是对象。"}), 400

        try:
            return jsonify(self._review_service.save_agent_settings(agent_id, payload))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to save agent settings")
            return jsonify({"error": str(exc)}), 500

    def set_default_agent(self, agent_id: str) -> Response:
        try:
            return jsonify(self._review_service.set_default_agent(agent_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to set default agent")
            return jsonify({"error": str(exc)}), 500

    def delete_agent_settings(self, agent_id: str) -> Response:
        try:
            return jsonify(self._review_service.delete_agent_settings(agent_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to delete agent settings")
            return jsonify({"error": str(exc)}), 500

    def save_hub_settings(self, hub_id: str) -> Response:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "请求体必须是对象。"}), 400

        try:
            return jsonify(self._review_service.save_hub_settings(hub_id, payload))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to save hub settings")
            return jsonify({"error": str(exc)}), 500

    def set_default_hub(self, hub_id: str) -> Response:
        try:
            return jsonify(self._review_service.set_default_hub(hub_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to set default hub")
            return jsonify({"error": str(exc)}), 500

    def delete_hub_settings(self, hub_id: str) -> Response:
        try:
            return jsonify(self._review_service.delete_hub_settings(hub_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            self._logger.exception("Failed to delete hub settings")
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
            return jsonify({"error": "请求体必须是对象。"}), 400

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

    def cancel_review(self, review_id: int) -> Response:
        try:
            detail = self._review_service.cancel_review(review_id)
            self._queue_worker.wake_up()
            return jsonify(detail)
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "not found" in message.lower() else 400
            return jsonify({"error": message}), status_code
        except Exception as exc:
            self._logger.exception("Failed to cancel review")
            return jsonify({"error": str(exc)}), 500
