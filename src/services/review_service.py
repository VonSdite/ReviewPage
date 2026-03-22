#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检视服务。"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ..application.app_context import AppContext
from ..domain import ReviewAgent, ReviewHub
from ..utils import format_command, stream_command


class ReviewService:
    """封装检视任务的创建、查询与执行。"""

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

    def create_review(self, payload: dict[str, object]) -> dict[str, object]:
        mr_url = str(payload.get("mr_url") or "").strip()
        hub_id = str(payload.get("hub_id") or self._config_manager.get_default_hub_id()).strip()
        agent_id = str(payload.get("agent_id") or self._config_manager.get_default_agent_id()).strip()
        model_id = str(payload.get("model_id") or "").strip()

        if not mr_url:
            raise ValueError("MR 检视地址不能为空")
        if agent_id not in self._agents:
            raise ValueError(f"未注册或未启用的 Agent：{agent_id}")
        if hub_id not in self._hubs:
            raise ValueError(f"未注册或未启用的 Hub：{hub_id}")
        if not model_id:
            raise ValueError("模型不能为空")

        agent = self._agents[agent_id]
        hub = self._hubs[hub_id]
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
            raise ValueError(f"未注册或未启用的 Agent：{agent_id}")
        catalog = agent.refresh_model_catalog()
        return {
            "id": agent.agent_id,
            "name": agent.agent_id,
            "models": [item.to_dict() for item in catalog.models],
            "model_source": catalog.source,
            "model_error": catalog.error,
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
            status_label = "未检视"
        elif status == "completed":
            status_label = "已检视"
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
