#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review workflows and settings management."""

from __future__ import annotations

from copy import deepcopy
import os
import shutil
import stat
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from ..application.app_context import AppContext
from ..domain import ReviewAgent, ReviewHub, get_registered_hub_types
from ..integrations import build_config_driven_agents, build_configured_hubs
from ..integrations.agents import ConfigDrivenReviewAgent
from ..utils import CommandCancelledError, format_command, stream_command


class ReviewCancelledError(RuntimeError):
    def __init__(self, output: str = "", message: str = "任务已取消"):
        super().__init__(message)
        self.output = output


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
        self._execution_lock = threading.Lock()
        self._active_review_id: int | None = None
        self._active_cancel_event: threading.Event | None = None
        self._requested_cancel_ids: set[int] = set()

    def get_metadata(self) -> dict[str, object]:
        agents_meta = [agent.to_metadata() for agent in self._agents.values()]
        hubs_meta = [hub.to_metadata() for hub in self._hubs.values()]
        return {
            "agents": sorted(agents_meta, key=lambda item: str(item["id"])),
            "hubs": sorted(hubs_meta, key=lambda item: str(item["id"])),
            "defaults": {
                "agent_id": self._config_manager.get_configured_default_agent_id(),
                "hub_id": self._config_manager.get_configured_default_hub_id(),
            },
        }

    def get_settings(self) -> dict[str, object]:
        agents = [self._serialize_agent_settings(agent_id) for agent_id in sorted(self._agents)]
        hubs = [self._serialize_hub_settings(hub_id) for hub_id in sorted(self._hubs)]
        return {
            "defaults": {
                "agent_id": self._config_manager.get_configured_default_agent_id(),
                "hub_id": self._config_manager.get_configured_default_hub_id(),
            },
            "agents": sorted(agents, key=lambda item: str(item["id"])),
            "hubs": sorted(hubs, key=lambda item: str(item["id"])),
            "hub_types": sorted(get_registered_hub_types()),
        }

    def create_review(self, payload: dict[str, object]) -> dict[str, object]:
        mr_url = str(payload.get("mr_url") or "").strip()
        hub_id = str(payload.get("hub_id") or "").strip()
        agent_id = str(payload.get("agent_id") or "").strip()
        model_id = str(payload.get("model_id") or "").strip()

        if not mr_url:
            raise ValueError("MR 检视地址不能为空")
        if not hub_id:
            raise ValueError("平台不能为空")
        if not agent_id:
            raise ValueError("Agent 不能为空")
        if not model_id:
            raise ValueError("模型不能为空")
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")

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

    def cancel_review(self, review_id: int) -> dict[str, object]:
        cancel_message = "任务已取消"
        row = self._review_repository.get_review(review_id)
        if row is None:
            raise ValueError("review record not found")

        status = str(row.get("status") or "")
        runtime_state = str(row.get("runtime_state") or "")
        if status == "cancelled":
            return self._serialize_review_row(row, self._review_repository.get_queue_positions())
        if status != "pending":
            raise ValueError("当前任务已结束，无法取消")

        if runtime_state == "queued":
            cancelled_row = self._review_repository.cancel_queued_review(review_id, cancel_message)
            if cancelled_row is not None:
                return self._serialize_review_row(cancelled_row, self._review_repository.get_queue_positions())

            row = self._review_repository.get_review(review_id)
            if row is None:
                raise ValueError("review record not found")
            status = str(row.get("status") or "")
            runtime_state = str(row.get("runtime_state") or "")
            if status == "cancelled":
                return self._serialize_review_row(row, self._review_repository.get_queue_positions())
            if status != "pending":
                raise ValueError("当前任务已结束，无法取消")

        if runtime_state in {"running", "canceling"}:
            self._request_review_cancel(review_id)
            updated_row = self._review_repository.request_running_review_cancel(review_id)
            if updated_row is None:
                row = self._review_repository.get_review(review_id)
                if row is None:
                    raise ValueError("review record not found")
                if str(row.get("status") or "") == "cancelled":
                    return self._serialize_review_row(row, self._review_repository.get_queue_positions())
                raise ValueError("当前任务已结束，无法取消")
            return self._serialize_review_row(updated_row, self._review_repository.get_queue_positions())

        raise ValueError("当前任务状态不支持取消")

    def refresh_agent_models(self, agent_id: str) -> dict[str, object]:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"未注册的 Agent：{agent_id}")
        agent.refresh_model_catalog()
        return self._serialize_agent_settings(agent_id)

    def fetch_agent_models_preview(self, agent_id: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        if payload is not None:
            preview_agent_id = self._normalize_settings_entity_id(payload.get("agent_id") or agent_id, "Agent")
            settings = self._normalize_agent_model_preview_payload(payload)
            catalog = self._build_preview_agent(preview_agent_id, settings).refresh_model_catalog()
            fetched_models = [item.model_id for item in catalog.models]
            return {
                "agent_id": preview_agent_id,
                "fetched_models": fetched_models,
            }

        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        previous_config = self._config_manager.get_raw_config()
        try:
            catalog = agent.refresh_model_catalog()
            fetched_models = [item.model_id for item in catalog.models]
        except Exception:
            self._config_manager.replace_raw_config(previous_config)
            self._reload_integrations()
            raise

        self._config_manager.replace_raw_config(previous_config)
        self._reload_integrations()
        return {
            "agent_id": agent_id,
            "fetched_models": fetched_models,
        }

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
        agent_id = self._normalize_settings_entity_id(agent_id, "Agent")
        next_agent_id = self._normalize_settings_entity_id(payload.get("agent_id") or agent_id, "Agent")
        settings = self._normalize_agent_settings_payload(payload)
        agent_exists = agent_id in self._agents
        is_renaming = agent_exists and next_agent_id != agent_id
        if not agent_exists and next_agent_id != agent_id:
            raise ValueError("不能重命名一个不存在的 Agent")
        if is_renaming and next_agent_id in self._agents:
            raise ValueError(f"Agent 已存在：{next_agent_id}")

        previous_config = self._config_manager.get_raw_config()
        renamed_reviews = False
        try:
            if is_renaming:
                self._config_manager.rename_agent(agent_id, next_agent_id)
                self._config_manager.update_agent_settings(next_agent_id, settings)
                self._review_repository.rename_agent(agent_id, next_agent_id)
                renamed_reviews = True
            else:
                self._config_manager.update_agent_settings(agent_id, settings)
            self._reload_integrations()
        except Exception:
            self._config_manager.replace_raw_config(previous_config)
            if renamed_reviews:
                self._review_repository.rename_agent(next_agent_id, agent_id)
            self._reload_integrations()
            raise

        result = self._serialize_agent_settings(next_agent_id if is_renaming else agent_id)
        if is_renaming:
            result["previous_id"] = agent_id
        return result

    def set_default_agent(self, agent_id: str) -> dict[str, object]:
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        self._config_manager.update_default_agent_id(agent_id)
        return {
            "agent_id": agent_id,
            "hub_id": self._config_manager.get_default_hub_id(),
        }

    def delete_agent_settings(self, agent_id: str) -> dict[str, object]:
        if agent_id not in self._agents:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        self._apply_config_change(lambda: self._config_manager.delete_agent(agent_id))
        return {
            "agent_id": self._config_manager.get_default_agent_id(),
            "hub_id": self._config_manager.get_default_hub_id(),
        }

    def save_hub_settings(self, hub_id: str, payload: dict[str, object]) -> dict[str, object]:
        hub_id = self._normalize_settings_entity_id(hub_id, "平台")
        next_hub_id = self._normalize_settings_entity_id(payload.get("hub_id") or hub_id, "平台")
        settings = self._normalize_hub_settings_payload(payload)
        hub_exists = hub_id in self._hubs
        is_renaming = hub_exists and next_hub_id != hub_id
        if not hub_exists and next_hub_id != hub_id:
            raise ValueError("不能重命名一个不存在的平台")
        if is_renaming and next_hub_id in self._hubs:
            raise ValueError(f"平台已存在：{next_hub_id}")

        previous_config = self._config_manager.get_raw_config()
        renamed_reviews = False
        try:
            if is_renaming:
                self._config_manager.rename_hub(hub_id, next_hub_id)
                self._config_manager.update_hub_settings(next_hub_id, settings)
                self._review_repository.rename_hub(hub_id, next_hub_id)
                renamed_reviews = True
            else:
                self._config_manager.update_hub_settings(hub_id, settings)
            self._reload_integrations()
        except Exception:
            self._config_manager.replace_raw_config(previous_config)
            if renamed_reviews:
                self._review_repository.rename_hub(next_hub_id, hub_id)
            self._reload_integrations()
            raise

        result = self._serialize_hub_settings(next_hub_id if is_renaming else hub_id)
        if is_renaming:
            result["previous_id"] = hub_id
        return result

    def set_default_hub(self, hub_id: str) -> dict[str, object]:
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")

        self._config_manager.update_default_hub_id(hub_id)
        return {
            "agent_id": self._config_manager.get_default_agent_id(),
            "hub_id": hub_id,
        }

    def delete_hub_settings(self, hub_id: str) -> dict[str, object]:
        if hub_id not in self._hubs:
            raise ValueError(f"未注册的 Hub：{hub_id}")

        self._apply_config_change(lambda: self._config_manager.delete_hub(hub_id))
        return {
            "agent_id": self._config_manager.get_default_agent_id(),
            "hub_id": self._config_manager.get_default_hub_id(),
        }

    def reset_running_reviews(self) -> None:
        with self._execution_lock:
            self._active_review_id = None
            self._active_cancel_event = None
            self._requested_cancel_ids.clear()
        self._review_repository.reset_running_pending_reviews()

    def _request_review_cancel(self, review_id: int) -> None:
        with self._execution_lock:
            self._requested_cancel_ids.add(review_id)
            if self._active_review_id == review_id and self._active_cancel_event is not None:
                self._active_cancel_event.set()

    def _activate_review(self, review_id: int) -> threading.Event:
        cancel_event = threading.Event()
        with self._execution_lock:
            if review_id in self._requested_cancel_ids:
                cancel_event.set()
            self._active_review_id = review_id
            self._active_cancel_event = cancel_event
        return cancel_event

    def _clear_active_review(self, review_id: int) -> None:
        with self._execution_lock:
            self._requested_cancel_ids.discard(review_id)
            if self._active_review_id == review_id:
                self._active_review_id = None
                self._active_cancel_event = None

    @staticmethod
    def _raise_if_cancel_requested(cancel_event: threading.Event) -> None:
        if cancel_event.is_set():
            raise ReviewCancelledError()

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
        cancel_event = self._activate_review(review_id)

        log_sequence = int(row.get("last_log_seq") or 0)
        review_output = ""

        def append_log(line: str) -> None:
            nonlocal log_sequence
            log_sequence += 1
            normalized = line.rstrip("\n")
            self._review_repository.append_review_log(review_id, log_sequence, normalized)
            self._logger.info("[review:%s] %s", review_id, normalized)

        try:
            self._raise_if_cancel_requested(cancel_event)
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
            self._raise_if_cancel_requested(cancel_event)
            append_log(f"[command] {format_command(clone_command)}")
            clone_result = stream_command(
                clone_command,
                cwd=workspace_dir,
                on_output=append_log,
                cancel_requested=cancel_event.is_set,
            )
            if clone_result.returncode != 0:
                review_output = clone_result.output.strip()
                raise RuntimeError(f"git clone 失败，退出码 {clone_result.returncode}")

            self._raise_if_cancel_requested(cancel_event)
            append_log(f"[command] {format_command(command_spec.argv)}")
            review_result = stream_command(
                command_spec.argv,
                cwd=repo_dir,
                env=command_spec.env,
                on_output=append_log,
                cancel_requested=cancel_event.is_set,
            )
            review_output = review_result.output.strip()
            if review_result.returncode != 0:
                raise RuntimeError(f"Agent 命令执行失败，退出码 {review_result.returncode}")

            append_log("[system] 检视执行完成")
            result_text = review_output or "检视已完成，但命令没有输出结果。"
            self._review_repository.mark_review_completed(review_id, result_text)
        except CommandCancelledError as exc:
            review_output = exc.output.strip()
            message = "任务已取消"
            append_log(f"[system] {message}")
            self._review_repository.mark_review_cancelled(review_id, review_output, message)
        except ReviewCancelledError as exc:
            review_output = exc.output.strip()
            message = str(exc) or "任务已取消"
            append_log(f"[system] {message}")
            self._review_repository.mark_review_cancelled(review_id, review_output, message)
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            append_log(f"[system] 检视失败：{message}")
            self._review_repository.mark_review_failed(review_id, review_output, message)
        finally:
            self._clear_active_review(review_id)
            self._cleanup_workspace(workspace_dir, temp_root, append_log)

    def _cleanup_workspace(
        self,
        workspace_dir: Path,
        temp_root: Path,
        append_log: Callable[[str], None],
    ) -> None:
        if self._remove_directory_tree(workspace_dir):
            append_log(f"[system] 临时目录已清理：{workspace_dir}")
        else:
            append_log(f"[system] 临时目录清理失败，仍有残留：{workspace_dir}")

        try:
            temp_root.rmdir()
        except OSError:
            return

        append_log(f"[system] 临时根目录已清理：{temp_root}")

    def _remove_directory_tree(
        self,
        path: Path,
        *,
        attempts: int = 3,
        retry_delay_seconds: float = 0.2,
    ) -> bool:
        if not path.exists():
            return True

        last_error: OSError | None = None
        for attempt in range(attempts):
            try:
                shutil.rmtree(path, onerror=self._handle_rmtree_error)
            except FileNotFoundError:
                return True
            except OSError as exc:
                last_error = exc

            if self._prune_empty_directories(path):
                return True

            try:
                path.rmdir()
            except FileNotFoundError:
                return True
            except OSError as exc:
                last_error = exc
            else:
                return True

            if attempt + 1 < attempts:
                time.sleep(retry_delay_seconds)

        if path.exists():
            self._logger.warning("Failed to fully remove workspace directory %s: %s", path, last_error)
            return False
        return True

    @staticmethod
    def _handle_rmtree_error(func, failed_path, exc_info) -> None:
        error = exc_info[1]
        if isinstance(error, FileNotFoundError):
            return

        try:
            current_mode = os.stat(failed_path).st_mode
            os.chmod(failed_path, current_mode | stat.S_IWRITE)
        except OSError:
            pass

        try:
            func(failed_path)
        except FileNotFoundError:
            return
        except OSError:
            return

    @staticmethod
    def _prune_empty_directories(path: Path) -> bool:
        if not path.exists():
            return True

        directories: list[Path] = []
        for child in path.rglob("*"):
            try:
                if child.is_dir():
                    directories.append(child)
            except OSError:
                continue

        directories.sort(key=lambda item: len(item.parts), reverse=True)
        for directory in directories:
            try:
                directory.rmdir()
            except OSError:
                continue

        try:
            path.rmdir()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return True

    def _serialize_review_row(
        self,
        row: dict[str, object],
        queue_positions: dict[int, int],
    ) -> dict[str, object]:
        record_id = int(row["id"])
        status = str(row.get("status") or "pending")
        runtime_state = str(row.get("runtime_state") or "queued")

        if status == "cancelled":
            status_label = "已取消"
        elif status == "pending" and runtime_state == "running":
            status_label = "执行中"
        elif status == "pending" and runtime_state == "canceling":
            status_label = "停止中"
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
            raise ValueError(f"Agent {agent_id} 的模型列表必须是数组。")

        metadata = agent.to_metadata()
        metadata["is_default"] = agent_id == self._config_manager.get_configured_default_agent_id()
        metadata["config"] = {
            "list_models_command": str(config.get("list_models_command") or ""),
            "review_command": str(config.get("review_command") or ""),
            "models": [str(item).strip() for item in raw_models if str(item or "").strip()],
            "default_model": str(config.get("default_model") or "").strip(),
            "extra_env": {str(key): str(value) for key, value in (config.get("extra_env") or {}).items()},
        }
        return metadata

    def _serialize_hub_settings(self, hub_id: str) -> dict[str, object]:
        hub = self._hubs[hub_id]
        config = self._config_manager.get_hub_config(hub_id)
        metadata = hub.to_metadata()
        metadata["type"] = str(config.get("type") or "").strip()
        metadata["is_default"] = hub_id == self._config_manager.get_configured_default_hub_id()
        metadata["config"] = {
            "type": str(config.get("type") or "").strip(),
            "web_base_url": str(config.get("web_base_url") or "").strip(),
            "api_base_url": str(config.get("api_base_url") or "").strip(),
            "private_token": str(config.get("private_token") or "").strip(),
            "clone_url_preference": str(config.get("clone_url_preference") or "http").strip().lower(),
            "verify_ssl": bool(config.get("verify_ssl", True)),
            "timeout_seconds": max(int(float(config.get("timeout_seconds") or 20)), 1),
        }
        return metadata

    def _normalize_agent_settings_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("请求体必须是对象。")

        list_models_command = str(payload.get("list_models_command") or "").strip()
        if not list_models_command:
            raise ValueError("拉模型命令不能为空。")

        review_command = str(payload.get("review_command") or "").strip()
        if not review_command:
            raise ValueError("检视命令不能为空。")

        raw_models = payload.get("models") or []
        if not isinstance(raw_models, list):
            raise ValueError("模型列表必须是数组。")
        models = self._normalize_model_ids(raw_models)

        default_model = str(payload.get("default_model_id") or payload.get("default_model") or "").strip()
        if default_model and default_model not in models:
            raise ValueError("默认模型必须出现在模型列表中。")

        extra_env = payload.get("extra_env") or {}
        if not isinstance(extra_env, dict):
            raise ValueError("额外环境变量必须是对象。")

        return {
            "list_models_command": list_models_command,
            "review_command": review_command,
            "models": models,
            "default_model": default_model,
            "extra_env": {str(key): str(value) for key, value in extra_env.items()},
        }

    def _normalize_agent_model_preview_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("请求体必须是对象。")

        list_models_command = str(payload.get("list_models_command") or "").strip()
        if not list_models_command:
            raise ValueError("拉模型命令不能为空。")

        extra_env = payload.get("extra_env") or {}
        if not isinstance(extra_env, dict):
            raise ValueError("额外环境变量必须是对象。")

        return {
            "list_models_command": list_models_command,
            "review_command": str(payload.get("review_command") or "").strip(),
            "extra_env": {str(key): str(value) for key, value in extra_env.items()},
        }

    def _normalize_hub_settings_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise ValueError("请求体必须是对象。")

        hub_type = str(payload.get("type") or "").strip()
        if not hub_type:
            raise ValueError("Hub 类型不能为空")
        if hub_type not in get_registered_hub_types():
            raise ValueError(f"未注册的 Hub 类型：{hub_type}")

        clone_url_preference = str(payload.get("clone_url_preference") or "http").strip().lower() or "http"
        if clone_url_preference not in {"http", "ssh"}:
            raise ValueError("克隆地址优先级只能是 http 或 ssh。")

        try:
            raw_timeout_seconds = float(payload.get("timeout_seconds") or 20)
        except (TypeError, ValueError) as exc:
            raise ValueError("超时时间必须是数字。") from exc
        if not raw_timeout_seconds.is_integer():
            raise ValueError("请求超时秒数必须是整数。")
        timeout_seconds = max(int(raw_timeout_seconds), 1)

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

    def _normalize_settings_entity_id(self, raw_id: object, label: str) -> str:
        normalized = str(raw_id or "").strip()
        if not normalized:
            raise ValueError(f"{label} ID 不能为空")
        if normalized == "default":
            raise ValueError(f"{label} ID 不能使用保留字 default")
        return normalized

    def _build_preview_agent(self, agent_id: str, settings: dict[str, object]) -> ConfigDrivenReviewAgent:
        agent_config = self._config_manager.get_agent_config(agent_id)
        preview_config = deepcopy(agent_config)
        preview_config["list_models_command"] = str(settings.get("list_models_command") or "").strip()
        preview_config["review_command"] = (
            str(settings.get("review_command") or "").strip()
            or str(preview_config.get("review_command") or "").strip()
            or "echo"
        )
        preview_config["extra_env"] = {
            str(key): str(value)
            for key, value in (settings.get("extra_env") or {}).items()
        }

        preview_config_manager = _PreviewAgentConfigManager(
            base_config_manager=self._config_manager,
            agent_id=agent_id,
            agent_config=preview_config,
        )
        preview_ctx = SimpleNamespace(
            logger=self._logger,
            config_manager=preview_config_manager,
            root_path=self._ctx.root_path,
        )
        return ConfigDrivenReviewAgent(preview_ctx, agent_id)

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
        self._agents.update(build_config_driven_agents(self._ctx))
        self._hubs.clear()
        self._hubs.update(build_configured_hubs(self._ctx))


class _PreviewAgentConfigManager:
    def __init__(self, *, base_config_manager, agent_id: str, agent_config: dict[str, object]):
        self._base_config_manager = base_config_manager
        self._agent_id = str(agent_id or "").strip()
        self._agent_config = deepcopy(agent_config)

    def get_agent_config(self, agent_id: str) -> dict[str, object]:
        if str(agent_id or "").strip() != self._agent_id:
            return {}
        return deepcopy(self._agent_config)

    def get_command_shell_config(self):
        return self._base_config_manager.get_command_shell_config()

    def get_agent_default_model_id(self, agent_id: str) -> str | None:
        if str(agent_id or "").strip() != self._agent_id:
            return None
        value = str(self._agent_config.get("default_model") or "").strip()
        return value or None

    def update_agent_models(self, agent_id: str, models: list[str]) -> list[str]:
        if str(agent_id or "").strip() != self._agent_id:
            raise ValueError(f"未注册的 Agent：{agent_id}")

        normalized = self._normalize_model_ids(models)
        self._agent_config["models"] = normalized
        current_default = str(self._agent_config.get("default_model") or "").strip()
        if current_default and current_default not in normalized:
            self._agent_config.pop("default_model", None)
        return normalized

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
