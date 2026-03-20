#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenCode Agent 实现。"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

from ...domain import AgentModelCatalog, ModelChoice, ReviewAgent, ReviewCommandSpec, register_agent_factory


class OpencodeReviewAgent(ReviewAgent):
    agent_id = "opencode"

    def __init__(self, ctx: object):
        self._ctx = ctx
        self._logger = ctx.logger
        self._config = ctx.config_manager.get_agent_config(self.agent_id)
        self.display_name = str(self._config.get("display_name") or "OpenCode")
        self._binary = str(self._config.get("binary") or "opencode")
        self._list_models_command = [str(item) for item in (self._config.get("list_models_command") or ["models"])]
        self._review_command = [str(item) for item in (self._config.get("review_command") or ["run", "--model", "{model}", "{prompt}"])]
        self._prompt_template = str(self._config.get("prompt_template") or "/review {review_url}")
        self._fallback_models = [str(item).strip() for item in (self._config.get("model_list") or []) if str(item).strip()]
        self._extra_env = {str(k): str(v) for k, v in (self._config.get("extra_env") or {}).items()}
        self._catalog_cache: AgentModelCatalog | None = None
        self._catalog_cache_at = 0.0
        self._cache_lock = threading.Lock()

    def get_model_catalog(self) -> AgentModelCatalog:
        with self._cache_lock:
            if self._catalog_cache is not None and time.time() - self._catalog_cache_at < 60:
                return self._catalog_cache

            catalog = self._discover_model_catalog()
            self._catalog_cache = catalog
            self._catalog_cache_at = time.time()
            return catalog

    def _discover_model_catalog(self) -> AgentModelCatalog:
        argv = [self._binary, *self._list_models_command]
        try:
            completed = subprocess.run(
                argv,
                cwd=str(self._ctx.root_path),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            return self._fallback_catalog(f"未找到 Agent 命令：{exc}")
        except Exception as exc:
            return self._fallback_catalog(f"获取模型列表失败：{exc}")

        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            message = stderr or f"命令退出码 {completed.returncode}"
            return self._fallback_catalog(message)

        models: list[ModelChoice] = []
        seen: set[str] = set()
        for raw_line in (completed.stdout or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("available models"):
                continue
            normalized = line.lstrip("-*").strip()
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                models.append(ModelChoice(model_id=normalized))

        if not models:
            return self._fallback_catalog("Agent 未返回任何模型")

        return AgentModelCatalog(models=models, source="command")

    def _fallback_catalog(self, error: str) -> AgentModelCatalog:
        if self._fallback_models:
            return AgentModelCatalog(
                models=[ModelChoice(model_id=item) for item in self._fallback_models],
                source="config-fallback",
                error=error,
            )
        return AgentModelCatalog(models=[], source="command", error=error)

    def build_review_command(self, *, model: str, review_url: str, workspace_dir: str) -> ReviewCommandSpec:
        prompt = self._prompt_template.format(
            model=model,
            review_url=review_url,
            workspace_dir=workspace_dir,
        )
        argv = [
            self._binary,
            *[
                item.format(
                    model=model,
                    prompt=prompt,
                    review_url=review_url,
                    workspace_dir=workspace_dir,
                )
                for item in self._review_command
            ],
        ]
        return ReviewCommandSpec(argv=argv, env=dict(self._extra_env))


def register_opencode_agent() -> None:
    register_agent_factory("opencode", OpencodeReviewAgent)
