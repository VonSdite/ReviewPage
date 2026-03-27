#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import logging
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.domain import AgentModelCatalog, MergeRequestTarget, ModelChoice, ReviewCommandSpec
from src.repositories import ReviewRepository
from src.services.review_service import ReviewService
from src.utils import CommandCancelledError, create_connection_factory


def _build_fake_agents(ctx):
    return {
        agent_id: _ConfigurableFakeAgent(ctx, agent_id)
        for agent_id in ctx.config_manager.get_agent_ids()
    }


def _build_fake_hubs(ctx):
    return {
        hub_id: _ConfigurableFakeHub(ctx, hub_id)
        for hub_id in ctx.config_manager.get_hub_ids()
    }


class _FakeConfigManager:
    def __init__(self, temp_root="/tmp/review-service-tests"):
        self._temp_root = temp_root
        self._config = {
            "agents": {
                "default": "opencode",
                "opencode": {
                    "list_models_command": "opencode models",
                    "review_command": 'opencode run --model "{model}" "/review {review_url}"',
                    "models": ["provider/model-a"],
                    "default_model": "provider/model-a",
                    "extra_env": {},
                },
            },
            "hubs": {
                "default": "gitlab",
                "gitlab": {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.example.com",
                    "api_base_url": "https://gitlab.example.com/api/v4",
                    "private_token": None,
                    "clone_url_preference": "http",
                    "verify_ssl": True,
                    "timeout_seconds": 20,
                },
            },
        }

    def get_default_agent_id(self):
        return str(self._config["agents"].get("default") or "")

    def get_configured_default_agent_id(self):
        return str(self._config["agents"].get("default") or "")

    def get_default_hub_id(self):
        return str(self._config["hubs"].get("default") or "")

    def get_configured_default_hub_id(self):
        return str(self._config["hubs"].get("default") or "")

    def get_workspace_temp_root(self):
        return self._temp_root

    def get_command_shell_config(self):
        return None

    def get_agent_ids(self):
        return [key for key in self._config["agents"] if key != "default"]

    def get_hub_ids(self):
        return [key for key in self._config["hubs"] if key != "default"]

    def get_agent_config(self, agent_id):
        return copy.deepcopy(self._config["agents"].get(agent_id) or {})

    def get_hub_config(self, hub_id):
        return copy.deepcopy(self._config["hubs"][hub_id])

    def get_raw_config(self):
        return copy.deepcopy(self._config)

    def replace_raw_config(self, raw_config):
        self._config = copy.deepcopy(raw_config)
        return self.get_raw_config()

    def get_agent_default_model_id(self, agent_id):
        value = str(self._config["agents"].get(agent_id, {}).get("default_model") or "").strip()
        return value or None

    def update_agent_models(self, agent_id, models):
        normalized = self._normalize_model_ids(models)
        agent_cfg = self._config["agents"][agent_id]
        agent_cfg["models"] = normalized
        default_model = str(agent_cfg.get("default_model") or "").strip()
        if default_model and default_model not in normalized:
            agent_cfg.pop("default_model", None)
        return normalized

    def update_agent_default_model(self, agent_id, model_id):
        normalized = str(model_id or "").strip() or None
        agent_cfg = self._config["agents"][agent_id]
        if normalized:
            agent_cfg["default_model"] = normalized
        else:
            agent_cfg.pop("default_model", None)
        return normalized

    def update_default_agent_id(self, agent_id):
        normalized = str(agent_id or "").strip()
        if normalized:
            self._config["agents"]["default"] = normalized
        else:
            self._config["agents"].pop("default", None)
        return normalized

    def update_default_hub_id(self, hub_id):
        normalized = str(hub_id or "").strip()
        if normalized:
            self._config["hubs"]["default"] = normalized
        else:
            self._config["hubs"].pop("default", None)
        return normalized

    def delete_agent(self, agent_id):
        self._config["agents"].pop(agent_id, None)
        if self.get_default_agent_id() == agent_id:
            self._config["agents"].pop("default", None)
        return self.get_default_agent_id()

    def rename_agent(self, agent_id, new_agent_id):
        if agent_id == new_agent_id:
            return agent_id

        agents = self._config["agents"]
        agent_cfg = agents.pop(agent_id)
        agents[new_agent_id] = agent_cfg
        if self.get_default_agent_id() == agent_id:
            agents["default"] = new_agent_id
        return new_agent_id

    def delete_hub(self, hub_id):
        self._config["hubs"].pop(hub_id, None)
        if self.get_default_hub_id() == hub_id:
            self._config["hubs"].pop("default", None)
        return self.get_default_hub_id()

    def rename_hub(self, hub_id, new_hub_id):
        if hub_id == new_hub_id:
            return hub_id

        hubs = self._config["hubs"]
        hub_cfg = hubs.pop(hub_id)
        hubs[new_hub_id] = hub_cfg
        if self.get_default_hub_id() == hub_id:
            hubs["default"] = new_hub_id
        return new_hub_id

    def update_agent_settings(self, agent_id, settings):
        agent_cfg = self._config["agents"].setdefault(agent_id, {})
        agent_cfg["list_models_command"] = str(settings.get("list_models_command") or "").strip()
        agent_cfg["review_command"] = str(settings.get("review_command") or "").strip()
        agent_cfg["models"] = self._normalize_model_ids(settings.get("models") or [])

        default_model = str(settings.get("default_model") or "").strip()
        if default_model:
            agent_cfg["default_model"] = default_model
        else:
            agent_cfg.pop("default_model", None)

        agent_cfg["extra_env"] = {
            str(key): str(value)
            for key, value in (settings.get("extra_env") or {}).items()
        }
        agent_cfg.pop("command_shell", None)

        if agent_cfg.get("default_model") and agent_cfg["default_model"] not in agent_cfg["models"]:
            agent_cfg.pop("default_model", None)

        return self.get_agent_config(agent_id)

    def update_hub_settings(self, hub_id, settings):
        hub_cfg = self._config["hubs"].setdefault(hub_id, {})
        hub_cfg["type"] = str(settings.get("type") or "").strip()
        hub_cfg["web_base_url"] = str(settings.get("web_base_url") or "").strip()
        hub_cfg["api_base_url"] = str(settings.get("api_base_url") or "").strip()
        hub_cfg["private_token"] = str(settings.get("private_token") or "").strip() or None
        hub_cfg["clone_url_preference"] = str(settings.get("clone_url_preference") or "http").strip().lower()
        hub_cfg["verify_ssl"] = bool(settings.get("verify_ssl", True))
        hub_cfg["timeout_seconds"] = int(settings.get("timeout_seconds") or 20)
        return self.get_hub_config(hub_id)

    def _normalize_model_ids(self, models):
        seen = set()
        normalized = []
        for item in models:
            model_id = str(item or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            normalized.append(model_id)
        return normalized


class _FakeCtx:
    def __init__(self, temp_root="/tmp/review-service-tests"):
        self.logger = logging.getLogger("test.review_service")
        self.config_manager = _FakeConfigManager(temp_root=temp_root)
        self.root_path = Path(temp_root)


class _ConfigurableFakeAgent:
    def __init__(self, ctx, agent_id):
        self._ctx = ctx
        self.agent_id = agent_id

    def get_model_catalog(self):
        model_ids = self._ctx.config_manager.get_agent_config(self.agent_id).get("models") or []
        models = [ModelChoice(model_id=model_id) for model_id in model_ids]
        error = None if models else "no models configured"
        return AgentModelCatalog(models=models, source="config", error=error)

    def get_default_model_id(self):
        return self._ctx.config_manager.get_agent_default_model_id(self.agent_id)

    def build_review_command(self, *, model, review_url, workspace_dir):
        return ReviewCommandSpec(argv=["echo", model, review_url, workspace_dir], env={})

    def refresh_model_catalog(self):
        self._ctx.config_manager.update_agent_models(
            self.agent_id,
            ["provider/model-a", "provider/model-b"],
        )
        return self.get_model_catalog()

    def to_metadata(self):
        catalog = self.get_model_catalog()
        return {
            "id": self.agent_id,
            "models": [{"id": item.model_id, "label": item.model_id} for item in catalog.models],
            "default_model_id": self.get_default_model_id(),
            "model_source": catalog.source,
            "model_error": catalog.error,
        }


class _ConfigurableFakeHub:
    def __init__(self, ctx, hub_id):
        self._ctx = ctx
        self.hub_id = hub_id

    def supports_url(self, review_url):
        web_base_url = str(self._ctx.config_manager.get_hub_config(self.hub_id).get("web_base_url") or "").rstrip("/")
        return review_url.startswith(web_base_url)

    def resolve_review_target(self, review_url):
        return MergeRequestTarget(
            hub_id=self.hub_id,
            review_url=review_url,
            repo_url="https://gitlab.example.com/group/project.git",
            source_branch="feature/review-page",
            target_branch="main",
        )

    def to_metadata(self):
        return {"id": self.hub_id}


class ReviewServiceTestCase(unittest.TestCase):
    def create_service(self, temp_root):
        ctx = _FakeCtx(temp_root=temp_root)
        repository = ReviewRepository(create_connection_factory(Path(temp_root) / "review.db"))

        patchers = [
            patch("src.services.review_service.build_config_driven_agents", side_effect=_build_fake_agents),
            patch("src.services.review_service.build_configured_hubs", side_effect=_build_fake_hubs),
            patch("src.services.review_service.get_registered_hub_types", return_value=["gitlab"]),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        service = ReviewService(
            ctx,
            review_repository=repository,
            agents=_build_fake_agents(ctx),
            hubs=_build_fake_hubs(ctx),
        )
        return service, ctx

    def test_list_reviews_returns_pagination_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            for index in range(5):
                service.create_review(
                    {
                        "mr_url": f"https://gitlab.example.com/group/project/-/merge_requests/{index + 1}",
                        "hub_id": "gitlab",
                        "agent_id": "opencode",
                        "model_id": "provider/model-a",
                    }
                )

            second_page = service.list_reviews(page=2, page_size=2)
            overflow_page = service.list_reviews(page=9, page_size=2)

        self.assertEqual(second_page["pagination"]["page"], 2)
        self.assertEqual(second_page["pagination"]["page_size"], 2)
        self.assertEqual(second_page["pagination"]["total"], 5)
        self.assertEqual(second_page["pagination"]["total_pages"], 3)
        self.assertTrue(second_page["pagination"]["has_prev"])
        self.assertTrue(second_page["pagination"]["has_next"])
        self.assertEqual(len(second_page["records"]), 2)

        self.assertEqual(overflow_page["pagination"]["page"], 3)
        self.assertFalse(overflow_page["pagination"]["has_next"])
        self.assertEqual(len(overflow_page["records"]), 1)

    def test_get_settings_returns_agent_and_hub_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            settings = service.get_settings()

        self.assertEqual(settings["defaults"]["agent_id"], "opencode")
        self.assertEqual(settings["defaults"]["hub_id"], "gitlab")
        self.assertEqual(settings["hub_types"], ["gitlab"])
        self.assertEqual(settings["agents"][0]["config"]["default_model"], "provider/model-a")
        self.assertEqual(settings["hubs"][0]["config"]["type"], "gitlab")

    def test_metadata_and_settings_hide_default_marker_when_default_not_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            ctx.config_manager.update_default_agent_id("")
            ctx.config_manager.update_default_hub_id("")
            service._reload_integrations()

            metadata = service.get_metadata()
            settings = service.get_settings()

        self.assertEqual(metadata["defaults"]["agent_id"], "")
        self.assertEqual(metadata["defaults"]["hub_id"], "")
        self.assertFalse(settings["agents"][0]["is_default"])
        self.assertFalse(settings["hubs"][0]["is_default"])

    def test_cancel_queued_review_marks_record_cancelled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/10",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            cancelled = service.cancel_review(int(created["id"]))
            detail = service.get_review_detail(int(created["id"]))

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["runtime_state"], "finished")
        self.assertIsNone(cancelled["queue_position"])
        self.assertEqual(detail["status"], "cancelled")
        self.assertEqual(detail["error_message"], "任务已取消")

    def test_cancel_running_review_stops_active_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/10-running",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            review_started = threading.Event()

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            def fake_stream_command(argv, cwd, env=None, on_output=None, cancel_requested=None):
                if argv and argv[0] == "git":
                    return _FakeResult(0, "clone ok")

                review_started.set()
                deadline = time.time() + 5
                while time.time() < deadline:
                    if cancel_requested and cancel_requested():
                        raise CommandCancelledError(output="partial output")
                    time.sleep(0.05)
                raise AssertionError("cancel_requested was never observed")

            with patch("src.services.review_service.stream_command", side_effect=fake_stream_command):
                worker = threading.Thread(target=service.execute_next_review, daemon=True)
                worker.start()
                self.assertTrue(review_started.wait(timeout=1))

                cancel_response = service.cancel_review(int(created["id"]))
                worker.join(timeout=2)

            self.assertFalse(worker.is_alive())
            detail = service.get_review_detail(int(created["id"]))

        self.assertIn(cancel_response["runtime_state"], {"canceling", "finished"})
        self.assertEqual(detail["status"], "cancelled")
        self.assertEqual(detail["runtime_state"], "finished")
        self.assertEqual(detail["error_message"], "任务已取消")

    def test_delete_queued_review_removes_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/10-delete",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            payload = service.delete_review(int(created["id"]))
            detail = service.get_review_detail(int(created["id"]))
            listing = service.list_reviews()

        self.assertEqual(
            payload,
            {
                "id": int(created["id"]),
                "deleted": True,
                "stopped": False,
            },
        )
        self.assertIsNone(detail)
        self.assertEqual(listing["pagination"]["total"], 0)

    def test_delete_running_review_waits_for_cleanup_before_removing_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/10-delete-running",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            review_id = int(created["id"])
            review_started = threading.Event()
            cleanup_errors = []
            delete_errors = []
            delete_result = {}

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            def fake_stream_command(argv, cwd, env=None, on_output=None, cancel_requested=None):
                if argv and argv[0] == "git":
                    return _FakeResult(0, "clone ok")

                review_started.set()
                deadline = time.time() + 5
                while time.time() < deadline:
                    if cancel_requested and cancel_requested():
                        raise CommandCancelledError(output="partial output")
                    time.sleep(0.05)
                raise AssertionError("cancel_requested was never observed")

            original_cleanup_workspace = service._cleanup_workspace

            def wrapped_cleanup_workspace(workspace_dir, temp_root, append_log):
                try:
                    if service.get_review_detail(review_id) is None:
                        raise AssertionError("review was deleted before cleanup started")
                    time.sleep(0.2)
                    if service.get_review_detail(review_id) is None:
                        raise AssertionError("review was deleted during cleanup")
                except Exception as exc:  # pragma: no cover - assertion path
                    cleanup_errors.append(exc)
                original_cleanup_workspace(workspace_dir, temp_root, append_log)

            def run_delete_review():
                try:
                    delete_result.update(service.delete_review(review_id))
                except Exception as exc:  # pragma: no cover - assertion path
                    delete_errors.append(exc)

            with patch("src.services.review_service.stream_command", side_effect=fake_stream_command):
                with patch.object(service, "_cleanup_workspace", side_effect=wrapped_cleanup_workspace):
                    worker = threading.Thread(target=service.execute_next_review, daemon=True)
                    worker.start()
                    self.assertTrue(review_started.wait(timeout=1))

                    delete_thread = threading.Thread(target=run_delete_review, daemon=True)
                    delete_thread.start()
                    delete_thread.join(timeout=3)
                    worker.join(timeout=3)

            if cleanup_errors:
                raise cleanup_errors[0]
            if delete_errors:
                raise delete_errors[0]

            detail = service.get_review_detail(review_id)

        self.assertFalse(worker.is_alive())
        self.assertFalse(delete_thread.is_alive())
        self.assertEqual(
            delete_result,
            {
                "id": review_id,
                "deleted": True,
                "stopped": True,
            },
        )
        self.assertIsNone(detail)

    def test_execute_review_always_deletes_workspace_on_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir) / "workspaces"
            service, _ctx = self.create_service(str(temp_root))

            service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/11",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            with patch("src.services.review_service.stream_command") as mocked_stream_command:
                mocked_stream_command.side_effect = [
                    _FakeResult(0, "clone ok"),
                    _FakeResult(1, "review failed"),
                ]
                handled = service.execute_next_review()

        self.assertTrue(handled)
        self.assertFalse(temp_root.exists())

    def test_execute_review_keeps_temp_root_when_other_workspaces_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir) / "workspaces"
            temp_root.mkdir(parents=True)
            sibling_workspace = temp_root / "review-keep-me"
            sibling_workspace.mkdir()
            service, _ctx = self.create_service(str(temp_root))

            service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/12",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            with patch("src.services.review_service.stream_command") as mocked_stream_command:
                mocked_stream_command.side_effect = [
                    _FakeResult(0, "clone ok"),
                    _FakeResult(1, "review failed"),
                ]
                handled = service.execute_next_review()

            self.assertTrue(handled)
            self.assertTrue(temp_root.exists())
            self.assertTrue(sibling_workspace.exists())

    def test_execute_review_prunes_empty_directories_left_by_partial_cleanup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir) / "workspaces"
            service, _ctx = self.create_service(str(temp_root))

            service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/13",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            def partial_rmtree(path, *args, **kwargs):
                workspace_path = Path(path)
                for child in sorted(workspace_path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
                    if child.is_file():
                        child.unlink()

            with patch("src.services.review_service.stream_command") as mocked_stream_command:
                mocked_stream_command.side_effect = [
                    _FakeResult(0, "clone ok"),
                    _FakeResult(1, "review failed"),
                ]
                with patch("src.services.review_service.shutil.rmtree", side_effect=partial_rmtree):
                    handled = service.execute_next_review()

        self.assertTrue(handled)
        self.assertFalse(temp_root.exists())

    def test_refresh_agent_models_returns_latest_settings_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            metadata = service.refresh_agent_models("opencode")

        self.assertEqual(metadata["id"], "opencode")
        self.assertEqual(
            [item["id"] for item in metadata["models"]],
            ["provider/model-a", "provider/model-b"],
        )
        self.assertEqual(metadata["config"]["models"], ["provider/model-a", "provider/model-b"])
        self.assertEqual(metadata["config"]["default_model"], "provider/model-a")

    def test_fetch_agent_models_preview_does_not_persist_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            preview = service.fetch_agent_models_preview("opencode")

        self.assertEqual(preview["agent_id"], "opencode")
        self.assertEqual(preview["fetched_models"], ["provider/model-a", "provider/model-b"])
        self.assertEqual(ctx.config_manager.get_agent_config("opencode")["models"], ["provider/model-a"])
        self.assertEqual(ctx.config_manager.get_agent_config("opencode")["default_model"], "provider/model-a")

    def test_fetch_agent_models_preview_accepts_unsaved_settings_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            with patch(
                "src.services.review_service.ConfigDrivenReviewAgent.refresh_model_catalog",
                return_value=AgentModelCatalog(
                    models=[ModelChoice(model_id="preview/model-a"), ModelChoice(model_id="preview/model-b")],
                    source="command",
                    error=None,
                ),
            ):
                preview = service.fetch_agent_models_preview(
                    "draft-agent",
                    {
                        "agent_id": "draft-agent",
                        "list_models_command": "draft models",
                        "extra_env": {"HTTPS_PROXY": "http://127.0.0.1:7890"},
                    },
                )

        self.assertEqual(preview["agent_id"], "draft-agent")
        self.assertEqual(preview["fetched_models"], ["preview/model-a", "preview/model-b"])
        self.assertNotIn("draft-agent", ctx.config_manager.get_agent_ids())
        self.assertEqual(ctx.config_manager.get_agent_config("opencode")["list_models_command"], "opencode models")

    def test_create_review_requires_explicit_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            ctx.config_manager.update_agent_default_model("opencode", "provider/model-a")

            with self.assertRaisesRegex(ValueError, "模型不能为空"):
                service.create_review(
                    {
                        "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/22",
                        "hub_id": "gitlab",
                        "agent_id": "opencode",
                    }
                )

    def test_create_review_requires_explicit_agent_and_hub(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            with self.assertRaisesRegex(ValueError, "平台不能为空"):
                service.create_review(
                    {
                        "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/22",
                        "agent_id": "opencode",
                        "model_id": "provider/model-a",
                    }
                )

            with self.assertRaisesRegex(ValueError, "Agent 不能为空"):
                service.create_review(
                    {
                        "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/22",
                        "hub_id": "gitlab",
                        "model_id": "provider/model-a",
                    }
                )

    def test_set_agent_default_model_persists_and_returns_settings_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            metadata = service.set_agent_default_model("opencode", "provider/model-a")

        self.assertEqual(ctx.config_manager.get_agent_default_model_id("opencode"), "provider/model-a")
        self.assertEqual(metadata["default_model_id"], "provider/model-a")
        self.assertEqual(metadata["config"]["default_model"], "provider/model-a")

    def test_save_agent_settings_updates_config_and_reloads_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            result = service.save_agent_settings(
                "opencode",
                {
                    "list_models_command": "foo models",
                    "review_command": 'foo review "{review_url}" --model "{model}"',
                    "models": ["provider/model-b", "provider/model-c"],
                    "default_model_id": "provider/model-c",
                    "extra_env": {"HTTP_PROXY": "http://127.0.0.1:7890"},
                },
            )

        saved_config = ctx.config_manager.get_agent_config("opencode")
        self.assertEqual(saved_config["list_models_command"], "foo models")
        self.assertEqual(saved_config["default_model"], "provider/model-c")
        self.assertEqual(result["config"]["models"], ["provider/model-b", "provider/model-c"])
        self.assertEqual(result["config"]["default_model"], "provider/model-c")

    def test_save_agent_settings_missing_list_models_command_uses_user_facing_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            with self.assertRaisesRegex(ValueError, "拉模型命令不能为空"):
                service.save_agent_settings(
                    "opencode",
                    {
                        "list_models_command": "",
                        "review_command": 'foo review "{review_url}" --model "{model}"',
                        "models": ["provider/model-b"],
                        "default_model_id": "provider/model-b",
                        "extra_env": {},
                    },
                )

    def test_save_agent_settings_missing_review_command_uses_user_facing_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            with self.assertRaisesRegex(ValueError, "检视命令不能为空"):
                service.save_agent_settings(
                    "opencode",
                    {
                        "list_models_command": "foo models",
                        "review_command": "",
                        "models": ["provider/model-b"],
                        "default_model_id": "provider/model-b",
                        "extra_env": {},
                    },
                )

    def test_save_agent_settings_removes_legacy_agent_shell_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            ctx.config_manager._config["agents"]["opencode"]["command_shell"] = {
                "executable": "/bin/bash",
                "args": ["-lc"],
            }

            result = service.save_agent_settings(
                "opencode",
                {
                    "list_models_command": "foo models",
                    "review_command": 'foo review "{review_url}" --model "{model}"',
                    "models": ["provider/model-b"],
                    "default_model_id": "provider/model-b",
                    "extra_env": {},
                },
            )

        saved_config = ctx.config_manager.get_agent_config("opencode")
        self.assertNotIn("command_shell", saved_config)
        self.assertNotIn("command_shell", result["config"])

    def test_save_agent_settings_can_create_new_agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            result = service.save_agent_settings(
                "codex",
                {
                    "list_models_command": "codex models",
                    "review_command": 'codex review "{review_url}" --model "{model}"',
                    "models": ["provider/model-x", "provider/model-y"],
                    "default_model_id": "provider/model-y",
                    "extra_env": {"HTTPS_PROXY": "http://127.0.0.1:7890"},
                },
            )

            settings = service.get_settings()

        self.assertIn("codex", [agent["id"] for agent in settings["agents"]])
        saved_config = ctx.config_manager.get_agent_config("codex")
        self.assertEqual(saved_config["list_models_command"], "codex models")
        self.assertEqual(saved_config["default_model"], "provider/model-y")
        self.assertEqual(result["id"], "codex")
        self.assertEqual(result["config"]["models"], ["provider/model-x", "provider/model-y"])
        self.assertEqual(result["config"]["default_model"], "provider/model-y")

    def test_save_agent_settings_can_rename_existing_agent_and_update_reviews(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/12",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            result = service.save_agent_settings(
                "opencode",
                {
                    "agent_id": "codex",
                    "list_models_command": "codex models",
                    "review_command": 'codex review "{review_url}" --model "{model}"',
                    "models": ["provider/model-a"],
                    "default_model_id": "provider/model-a",
                    "extra_env": {},
                },
            )
            detail = service.get_review_detail(int(created["id"]))

        self.assertEqual(result["id"], "codex")
        self.assertEqual(result["previous_id"], "opencode")
        self.assertEqual(ctx.config_manager.get_default_agent_id(), "codex")
        self.assertEqual(detail["agent_id"], "codex")
        self.assertIn("codex", ctx.config_manager.get_agent_ids())
        self.assertNotIn("opencode", ctx.config_manager.get_agent_ids())

    def test_set_default_agent_updates_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            payload = service.set_default_agent("opencode")

        self.assertEqual(ctx.config_manager.get_default_agent_id(), "opencode")
        self.assertEqual(payload, {"agent_id": "opencode", "hub_id": "gitlab"})

    def test_delete_agent_settings_removes_agent_and_updates_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            service.save_agent_settings(
                "codex",
                {
                    "list_models_command": "codex models",
                    "review_command": 'codex review "{review_url}" --model "{model}"',
                    "models": ["provider/model-x"],
                    "default_model_id": "provider/model-x",
                    "extra_env": {},
                },
            )

            payload = service.delete_agent_settings("opencode")
            settings = service.get_settings()

        self.assertEqual(payload, {"agent_id": "", "hub_id": "gitlab"})
        self.assertEqual(ctx.config_manager.get_default_agent_id(), "")
        self.assertEqual([agent["id"] for agent in settings["agents"]], ["codex"])

    def test_save_hub_settings_updates_config_and_reloads_hubs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            result = service.save_hub_settings(
                "gitlab",
                {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.internal.example.com",
                    "api_base_url": "https://gitlab.internal.example.com/api/v4",
                    "private_token": "secret-token",
                    "clone_url_preference": "ssh",
                    "verify_ssl": False,
                    "timeout_seconds": 45,
                },
            )

        saved_config = ctx.config_manager.get_hub_config("gitlab")
        self.assertEqual(saved_config["web_base_url"], "https://gitlab.internal.example.com")
        self.assertEqual(saved_config["clone_url_preference"], "ssh")
        self.assertFalse(saved_config["verify_ssl"])
        self.assertEqual(result["config"]["type"], "gitlab")
        self.assertEqual(result["config"]["timeout_seconds"], 45)

    def test_save_hub_settings_can_create_new_hub(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            result = service.save_hub_settings(
                "gitlab-public-2",
                {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.public-2.example.com",
                    "api_base_url": "https://gitlab.public-2.example.com/api/v4",
                    "private_token": "public-token",
                    "clone_url_preference": "http",
                    "verify_ssl": True,
                    "timeout_seconds": 30,
                },
            )

            settings = service.get_settings()

        self.assertIn("gitlab-public-2", [hub["id"] for hub in settings["hubs"]])
        saved_config = ctx.config_manager.get_hub_config("gitlab-public-2")
        self.assertEqual(saved_config["web_base_url"], "https://gitlab.public-2.example.com")
        self.assertEqual(saved_config["api_base_url"], "https://gitlab.public-2.example.com/api/v4")
        self.assertEqual(result["id"], "gitlab-public-2")
        self.assertEqual(result["config"]["type"], "gitlab")
        self.assertEqual(result["config"]["timeout_seconds"], 30)

    def test_save_hub_settings_can_rename_existing_hub_and_update_reviews(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            created = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/99",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            result = service.save_hub_settings(
                "gitlab",
                {
                    "hub_id": "gitlab-public",
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.public.example.com",
                    "api_base_url": "https://gitlab.public.example.com/api/v4",
                    "private_token": "",
                    "clone_url_preference": "http",
                    "verify_ssl": False,
                    "timeout_seconds": 25,
                },
            )

            settings = service.get_settings()
            detail = service.get_review_detail(int(created["id"]))

        self.assertEqual(result["id"], "gitlab-public")
        self.assertEqual(result["previous_id"], "gitlab")
        self.assertEqual(ctx.config_manager.get_default_hub_id(), "gitlab-public")
        self.assertEqual([hub["id"] for hub in settings["hubs"]], ["gitlab-public"])
        self.assertEqual(detail["hub_id"], "gitlab-public")

    def test_save_hub_settings_rejects_non_integer_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, _ctx = self.create_service(tmpdir)

            with self.assertRaisesRegex(ValueError, "请求超时秒数必须是整数"):
                service.save_hub_settings(
                    "gitlab",
                    {
                        "type": "gitlab",
                        "web_base_url": "https://gitlab.internal.example.com",
                        "api_base_url": "https://gitlab.internal.example.com/api/v4",
                        "private_token": "secret-token",
                        "clone_url_preference": "ssh",
                        "verify_ssl": False,
                        "timeout_seconds": 45.5,
                    },
                )

    def test_set_default_hub_updates_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)

            payload = service.set_default_hub("gitlab")

        self.assertEqual(ctx.config_manager.get_default_hub_id(), "gitlab")
        self.assertEqual(payload, {"agent_id": "opencode", "hub_id": "gitlab"})

    def test_delete_hub_settings_removes_hub_and_updates_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service, ctx = self.create_service(tmpdir)
            service.save_hub_settings(
                "gitlab-public-2",
                {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.public-2.example.com",
                    "api_base_url": "https://gitlab.public-2.example.com/api/v4",
                    "private_token": "public-token",
                    "clone_url_preference": "http",
                    "verify_ssl": True,
                    "timeout_seconds": 30,
                },
            )

            payload = service.delete_hub_settings("gitlab")
            settings = service.get_settings()

        self.assertEqual(payload, {"agent_id": "opencode", "hub_id": ""})
        self.assertEqual(ctx.config_manager.get_default_hub_id(), "")
        self.assertEqual([hub["id"] for hub in settings["hubs"]], ["gitlab-public-2"])


if __name__ == "__main__":
    unittest.main()
