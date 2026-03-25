#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review workflows and settings management."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Callable

from ..application.app_context import AppContext
from ..domain import ReviewAgent, ReviewHub, get_registered_hub_types
from ..integrations import build_configured_agents, build_configured_hubs
from ..utils import format_command, stream_command


class ReviewService:
    """Encapsulate review execution and runtime settings workflows."""

    def __init__(
        self,
        ctx: AppContext,
        *,
        review_repository,
        agents: dict[str, ReviewAgent],
        hubs: dict[str, ReviewHub],
    ):
        self._ctx = ctx
        self._logger = ctx.logger
        self._config_manager = ctx.config_manager
        self._review_repository = review_repository
        self._agents = agents
        self._hubs = hubs

    def get_metadata(self) -> dict[str, object]:
        agents_meta = [agent.to_metadata() for agent in self._agents.values()]
        hubs_meta = [hub.to_metadata() for hub in self._hubs.values()]
        return {
            "agents": sorted(agents_meta, key=lambda item: item["name"]),
            "hubs": sorted(hubs_meta, key=lambda item: item["name"]),
            "defaults": {
                "agent_id": self._config_manager.get_default_agent_id(),
                "hub_id": self._config_manager.get_default_hub_id(),
            },
        }

    def get_settings(self) -> dict[str, object]:
        agents = [self._serialize_agent_settings(agent_id) for agent_id in sorted(self._agents)]
        hubs = [self._serialize_hub_settings(hub_id) for hub_id in sorted(self._hubs)]
        return {
            "defaults": {
                "agent_id": self._config_manager.get_default_agent_id(),
                "hub_id": self._config_manager.get_default_hub_id(),
            },
            "agents": sorted(agents, key=lambda item: str(item["name"])),
            "hubs": sorted(hubs, key=lambda item: str(item["name"])),
            "hub_types": sorted(get_registered_hub_types()),
        }

    def create_review(self, payload: dict[str, object]) -> dict[str, object]:
        mr_url = str(payload.get("mr_url") or "").strip()
        hub_id = str(payload.get("hub_id") or self._config_manager.get_default_hub_id()).strip()
        agent_id = str(payload.get("agent_id") or self._config_manager.get_default_agent_id()).strip()
        model_id = str(payload.get("model_id") or self._config_manager.get_agent_default_model_id(agent_id) or "").strip()

        if not mr_url:
            raise ValueError("MR 检视地址不能为空")
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")
        if not model_id:
            raise ValueError("模型不能为空")

        agent = self._agents[agent_id]
        hub = self._hubs[hub_id]
        available_model_ids = {item.model_id for item in agent.get_model_catalog().models}
        if available_model_ids and model_id not in available_model_ids:
            raise ValueError(f"模型不属于当前 Agent：{model_id}")
        if not hub.supports_url(mr_url):
            raise ValueError(f"所选 Hub 不支持该 MR 地址：{mr_url}")

        row = self._review_repository.create_review(
            mr_url=mr_url,
            hub_id=hub_id,
            agent_id=agent_id,
            model_id=model_id,
        )
        queue_positions = self._review_repository.get_queue_positions()
        return self._serialize_review_row(row, queue_positions)

    def list_reviews(self, page: int = 1, page_size: int = 50) -> dict[str, object]:
        page = max(int(page), 1)
        page_size = min(max(int(page_size), 1), 200)
        queue_positions = self._review_repository.get_queue_positions()
        paged = self._review_repository.list_reviews(page=page, page_size=page_size)
        total = int(paged["total"])
        total_pages = max((total + page_size - 1) // page_size, 1)
        current_page = min(page, total_pages)

        if current_page != page:
            paged = self._review_repository.list_reviews(page=current_page, page_size=page_size)

        rows = paged["records"]
        return {
            "records": [self._serialize_review_row(row, queue_positions) for row in rows],
            "stats": self._review_repository.get_review_stats(),
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_prev": current_page > 1,
                "has_next": current_page < total_pages,
            },
        }

    def get_review_detail(self, review_id: int) -> dict[str, object] | None:
        row = self._review_repository.get_review(review_id)
        if row is None:
            return None
        queue_positions = self._review_repository.get_queue_positions()
        detail = self._serialize_review_row(row, queue_positions)
        detail["logs"] = self._review_repository.list_review_logs(review_id)
        return detail

    def refresh_agent_models(self, agent_id: str) -> dict[str, object]:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"未注册的 Agent：{agent_id}")
        agent.refresh_model_catalog()
        return self._serialize_agent_settings(agent_id)

    def set_agent_default_model(self, agent_id: str, model_id: str) -> dict[str, object]:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        normalized_model_id = str(model_id or "").strip()
        if not normalized_model_id:
            raise ValueError("默认模型不能为空")

        catalog = agent.get_model_catalog()
        valid_model_ids = {item.model_id for item in catalog.models}
        if normalized_model_id not in valid_model_ids:
            raise ValueError(f"默认模型不属于当前 Agent：{normalized_model_id}")

        self._config_manager.update_agent_default_model(agent_id, normalized_model_id)
        return self._serialize_agent_settings(agent_id)

    def save_agent_settings(self, agent_id: str, payload: dict[str, object]) -> dict[str, object]:
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        settings = self._normalize_agent_settings_payload(payload)
        self._apply_config_change(lambda: self._config_manager.update_agent_settings(agent_id, settings))
        return self._serialize_agent_settings(agent_id)

    def set_default_agent(self, agent_id: str) -> dict[str, object]:
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        self._config_manager.update_default_agent_id(agent_id)
        return {
            "agent_id": agent_id,
            "hub_id": self._config_manager.get_default_hub_id(),
        }

    def save_hub_settings(self, hub_id: str, payload: dict[str, object]) -> dict[str, object]:
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")

        settings = self._normalize_hub_settings_payload(payload)
        self._apply_config_change(lambda: self._config_manager.update_hub_settings(hub_id, settings))
        return self._serialize_hub_settings(hub_id)

    def set_default_hub(self, hub_id: str) -> dict[str, object]:
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")

        self._config_manager.update_default_hub_id(hub_id)
        return {
            "agent_id": self._config_manager.get_default_agent_id(),
            "hub_id": hub_id,
        }

    def reset_running_reviews(self) -> None:
        self._review_repository.reset_running_pending_reviews()

    def execute_next_review(self) -> bool:
        row = self._review_repository.claim_next_pending_review()
        if row is None:
            return False

        self._execute_review(row)
        return True

    def _execute_review(self, row: dict[str, object]) -> None:
        review_id = int(row["id"])
        hub = self._hubs[str(row["hub_id"])]
        agent = self._agents[str(row["agent_id"])]
        temp_root = Path(self._config_manager.get_workspace_temp_root())
        temp_root.mkdir(parents=True, exist_ok=True)
        workspace_dir = Path(tempfile.mkdtemp(prefix=f"review-{review_id}-", dir=str(temp_root)))
        repo_dir = workspace_dir / "repo"

        log_sequence = int(row.get("last_log_seq") or 0)
        review_output = ""

        def append_log(line: str) -> None:
            nonlocal log_sequence
            log_sequence += 1
            normalized = line.rstrip("\n")
            self._review_repository.append_review_log(review_id, log_sequence, normalized)
            self._logger.info("[review:%s] %s", review_id, normalized)

        try:
            append_log("[system] 开始解析检视地址")
            target = hub.resolve_review_target(str(row["mr_url"]))
            command_spec = agent.build_review_command(
                model=str(row["model_id"]),
                review_url=target.review_url,
                workspace_dir=str(repo_dir),
            )

            self._review_repository.update_execution_context(
                review_id,
                command_line=format_command(command_spec.argv),
                working_directory=str(repo_dir),
                repo_url=target.repo_url,
                source_branch=target.source_branch,
                target_branch=target.target_branch,
                title=target.title,
                author_name=target.author_name,
            )

            append_log(f"[system] 临时目录：{workspace_dir}")
            append_log(f"[system] 代码仓库：{target.repo_url}")
            append_log(f"[system] 检视分支：{target.source_branch}")
            if target.target_branch:
                append_log(f"[system] 目标分支：{target.target_branch}")

            clone_command = [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                target.source_branch,
                "--single-branch",
                target.repo_url,
                str(repo_dir),
            ]
            append_log(f"[command] {format_command(clone_command)}")
            clone_result = stream_command(clone_command, cwd=workspace_dir, on_output=append_log)
            if clone_result.returncode != 0:
                review_output = clone_result.output.strip()
                raise RuntimeError(f"git clone 失败，退出码 {clone_result.returncode}")

            append_log(f"[command] {format_command(command_spec.argv)}")
            review_result = stream_command(
                command_spec.argv,
                cwd=repo_dir,
                env=command_spec.env,
                on_output=append_log,
            )
            review_output = review_result.output.strip()
            if review_result.returncode != 0:
                raise RuntimeError(f"Agent 命令执行失败，退出码 {review_result.returncode}")

            append_log("[system] 检视执行完成")
            result_text = review_output or "检视已完成，但命令没有输出结果。"
            self._review_repository.mark_review_completed(review_id, result_text)
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            append_log(f"[system] 检视失败：{message}")
            self._review_repository.mark_review_failed(review_id, review_output, message)
        finally:
            shutil.rmtree(workspace_dir, ignore_errors=True)
            try:
                temp_root.rmdir()
            except OSError:
                pass
            else:
                append_log(f"[system] 临时根目录已清理：{temp_root}")
            append_log(f"[system] 临时目录已清理：{workspace_dir}")

    def _serialize_review_row(
        self,
        row: dict[str, object],
        queue_positions: dict[int, int],
    ) -> dict[str, object]:
        record_id = int(row["id"])
        status = str(row.get("status") or "pending")
        runtime_state = str(row.get("runtime_state") or "queued")

        if status == "pending" and runtime_state == "running":
            status_label = "执行中"
        elif status == "pending":
            status_label = "待执行"
        elif status == "completed":
            status_label = "成功"
        else:
            status_label = "失败"

        return {
            "id": record_id,
            "mr_url": row.get("mr_url"),
            "hub_id": row.get("hub_id"),
            "agent_id": row.get("agent_id"),
            "model_id": row.get("model_id"),
            "status": status,
            "runtime_state": runtime_state,
            "status_label": status_label,
            "queue_position": queue_positions.get(record_id),
            "title": row.get("title"),
            "author_name": row.get("author_name"),
            "repo_url": row.get("repo_url"),
            "source_branch": row.get("source_branch"),
            "target_branch": row.get("target_branch"),
            "command_line": row.get("command_line"),
            "working_directory": row.get("working_directory"),
            "result_text": row.get("result_text"),
            "error_message": row.get("error_message"),
            "created_at": row.get("created_at"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "updated_at": row.get("updated_at"),
            "last_log_seq": row.get("last_log_seq"),
        }

    def _serialize_agent_settings(self, agent_id: str) -> dict[str, object]:
        agent = self._agents[agent_id]
        config = self._config_manager.get_agent_config(agent_id)
        raw_models = config.get("models") or []
        if not isinstance(raw_models, list):
            raise ValueError(f"agents.{agent_id}.models must be a list")

        command_shell = config.get("command_shell")
        if command_shell is not None and not isinstance(command_shell, (str, dict)):
            raise ValueError(f"agents.{agent_id}.command_shell must be a string or mapping")

        metadata = agent.to_metadata()
        metadata["is_default"] = agent_id == self._config_manager.get_default_agent_id()
        metadata["config"] = {
            "list_models_command": str(config.get("list_models_command") or ""),
            "review_command": str(config.get("review_command") or ""),
            "models": [str(item).strip() for item in raw_models if str(item or "").strip()],
            "default_model": str(config.get("default_model") or "").strip(),
            "extra_env": {str(key): str(value) for key, value in (config.get("extra_env") or {}).items()},
            "command_shell": command_shell,
        }
        return metadata

    def _serialize_hub_settings(self, hub_id: str) -> dict[str, object]:
        hub = self._hubs[hub_id]
        config = self._config_manager.get_hub_config(hub_id)
        metadata = hub.to_metadata()
        metadata["type"] = str(config.get("type") or "").strip()
        metadata["is_default"] = hub_id == self._config_manager.get_default_hub_id()
        metadata["config"] = {
            "type": str(config.get("type") or "").strip(),
            "web_base_url": str(config.get("web_base_url") or "").strip(),
            "api_base_url": str(config.get("api_base_url") or "").strip(),
            "private_token": str(config.get("private_token") or "").strip(),
            "clone_url_preference": str(config.get("clone_url_preference") or "http").strip().lower(),
            "verify_ssl": bool(config.get("verify_ssl", True)),
            "timeout_seconds": float(config.get("timeout_seconds") or 20),
        }
        return metadata

    def _normalize_agent_settings_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")

        list_models_command = str(payload.get("list_models_command") or "").strip()
        if not list_models_command:
            raise ValueError("list_models_command 不能为空")

        review_command = str(payload.get("review_command") or "").strip()
        if not review_command:
            raise ValueError("review_command 不能为空")

        raw_models = payload.get("models") or []
        if not isinstance(raw_models, list):
            raise ValueError("models must be a list")
        models = self._normalize_model_ids(raw_models)

        default_model = str(payload.get("default_model_id") or payload.get("default_model") or "").strip()
        if default_model and default_model not in models:
            raise ValueError("默认模型必须出现在 models 列表里")

        extra_env = payload.get("extra_env") or {}
        if not isinstance(extra_env, dict):
            raise ValueError("extra_env must be a mapping")

        return {
            "list_models_command": list_models_command,
            "review_command": review_command,
            "models": models,
            "default_model": default_model,
            "extra_env": {str(key): str(value) for key, value in extra_env.items()},
            "command_shell": self._normalize_command_shell_payload(payload.get("command_shell")),
        }

    def _normalize_hub_settings_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")

        hub_type = str(payload.get("type") or "").strip()
        if not hub_type:
            raise ValueError("Hub 类型不能为空")
        if hub_type not in get_registered_hub_types():
            raise ValueError(f"未注册的 Hub 类型：{hub_type}")

        clone_url_preference = str(payload.get("clone_url_preference") or "http").strip().lower() or "http"
        if clone_url_preference not in {"http", "ssh"}:
            raise ValueError("clone_url_preference must be http or ssh")

        try:
            timeout_seconds = max(float(payload.get("timeout_seconds") or 20), 1.0)
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout_seconds must be a number") from exc

        api_base_url = str(payload.get("api_base_url") or "").strip()
        if hub_type == "gitlab" and not api_base_url:
            raise ValueError("GitLab Hub 的 api_base_url 不能为空")

        return {
            "type": hub_type,
            "web_base_url": str(payload.get("web_base_url") or "").strip(),
            "api_base_url": api_base_url,
            "private_token": str(payload.get("private_token") or "").strip(),
            "clone_url_preference": clone_url_preference,
            "verify_ssl": bool(payload.get("verify_ssl", True)),
            "timeout_seconds": timeout_seconds,
        }

    def _normalize_command_shell_payload(self, raw_shell: object) -> str | dict[str, object] | None:
        if raw_shell in (None, "", {}):
            return None

        if isinstance(raw_shell, str):
            executable = raw_shell.strip()
            return executable or None

        if not isinstance(raw_shell, dict):
            raise ValueError("command_shell must be a string or mapping")

        executable = str(raw_shell.get("executable") or "").strip()
        if not executable:
            return None

        raw_args = raw_shell.get("args")
        if raw_args is None:
            args: list[str] = []
        elif not isinstance(raw_args, list):
            raise ValueError("command_shell.args must be a list")
        else:
            args = [str(item).strip() for item in raw_args if str(item or "").strip()]

        return {
            "executable": executable,
            "args": args,
        }

    def _normalize_model_ids(self, models: list[object]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in models:
            model_id = str(item or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            normalized.append(model_id)
        return normalized

    def _apply_config_change(self, mutator: Callable[[], object]) -> None:
        previous_config = self._config_manager.get_raw_config()
        try:
            mutator()
            self._reload_integrations()
        except Exception:
            self._config_manager.replace_raw_config(previous_config)
            self._reload_integrations()
            raise

    def _reload_integrations(self) -> None:
        self._agents.clear()
        self._agents.update(build_configured_agents(self._ctx))
        self._hubs.clear()
        self._hubs.update(build_configured_hubs(self._ctx))
