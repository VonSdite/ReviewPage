#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理。"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import threading
from typing import Any

import yaml


class ConfigManager:
    """加载并访问配置项。"""

    def __init__(self, config_path: Path, root_path: Path):
        self._config_path = config_path.resolve()
        self._root_path = root_path.resolve()
        self._lock = threading.RLock()
        self.reload()

    def reload(self) -> None:
        with self._lock:
            with self._config_path.open("r", encoding="utf-8") as handle:
                raw = yaml.safe_load(handle) or {}
            if not isinstance(raw, dict):
                raise ValueError("config root must be a mapping")
            self._config = raw

    def get_server_host(self) -> str:
        return str(self._get_section("server").get("host") or "0.0.0.0")

    def get_server_port(self) -> int:
        return int(self._get_section("server").get("port") or 8091)

    def get_database_path(self) -> str:
        database_dir = self._resolve_database_dir(self._get_section("database").get("path") or "data")
        return str((database_dir / "review_page.sqlite3").resolve())

    def get_log_path(self) -> str:
        return str(self._resolve_path(self._get_section("logging").get("path") or "data/logs"))

    def get_log_level(self) -> str:
        return str(self._get_section("logging").get("level") or "INFO")

    def get_workspace_temp_root(self) -> str:
        return str(self._resolve_path(self._get_section("workspace").get("temp_root") or "data/tmp/reviews"))

    def get_queue_poll_interval_seconds(self) -> float:
        value = self._get_section("queue").get("poll_interval_seconds", 2)
        return max(float(value), 0.5)

    def get_command_shell_config(self) -> Any:
        value = self._config.get("command_shell")
        if value is None:
            return None
        if not isinstance(value, (str, dict)):
            raise ValueError("command_shell must be a string or mapping")
        return deepcopy(value)

    def get_default_agent_id(self) -> str:
        return str(self._get_section("agents").get("default") or "opencode")

    def get_default_hub_id(self) -> str:
        return str(self._get_section("hubs").get("default") or "gitlab")

    def is_agent_enabled(self, agent_id: str) -> bool:
        return bool(self.get_agent_config(agent_id).get("enabled", True))

    def is_hub_enabled(self, hub_id: str) -> bool:
        return bool(self.get_hub_config(hub_id).get("enabled", True))

    def get_agent_config(self, agent_id: str) -> dict[str, Any]:
        agent_cfg = self._get_section("agents").get(agent_id) or {}
        if not isinstance(agent_cfg, dict):
            raise ValueError(f"agents.{agent_id} must be a mapping")
        return deepcopy(agent_cfg)

    def get_hub_config(self, hub_id: str) -> dict[str, Any]:
        hub_cfg = self._get_section("hubs").get(hub_id) or {}
        if not isinstance(hub_cfg, dict):
            raise ValueError(f"hubs.{hub_id} must be a mapping")
        return deepcopy(hub_cfg)

    def get_raw_config(self) -> dict[str, Any]:
        return deepcopy(self._config)

    def update_agent_models(self, agent_id: str, models: list[str]) -> list[str]:
        normalized = self._normalize_model_ids(models)
        with self._lock:
            agents = self._ensure_section("agents")
            agent_cfg = agents.setdefault(agent_id, {})
            if not isinstance(agent_cfg, dict):
                raise ValueError(f"agents.{agent_id} must be a mapping")
            agent_cfg["models"] = normalized
            agent_cfg.pop("model_list", None)
            self._write_config()
        return normalized

    def _get_section(self, name: str) -> dict[str, Any]:
        section = self._config.get(name) or {}
        if not isinstance(section, dict):
            raise ValueError(f"{name} must be a mapping")
        return section

    def _ensure_section(self, name: str) -> dict[str, Any]:
        section = self._config.get(name)
        if section is None:
            section = {}
            self._config[name] = section
        if not isinstance(section, dict):
            raise ValueError(f"{name} must be a mapping")
        return section

    def _write_config(self) -> None:
        with self._config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(
                self._config,
                handle,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    def _normalize_model_ids(self, models: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in models:
            model_id = str(item or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            normalized.append(model_id)
        return normalized

    def _resolve_database_dir(self, value: str | Path) -> Path:
        candidate = Path(value)
        if candidate.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("database.path must be a directory, not a sqlite file path")
        return self._resolve_path(candidate)

    def _resolve_path(self, value: str | Path) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
        return (self._root_path / candidate).resolve()
