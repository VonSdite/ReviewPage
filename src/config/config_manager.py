#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理。"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """加载并访问配置项。"""

    def __init__(self, config_path: Path, root_path: Path):
        self._config_path = config_path.resolve()
        self._root_path = root_path.resolve()
        self.reload()

    def reload(self) -> None:
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

    def get_plugin_modules(self) -> list[str]:
        modules = self._get_section("plugins").get("modules") or []
        return [str(item).strip() for item in modules if str(item).strip()]

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

    def _get_section(self, name: str) -> dict[str, Any]:
        section = self._config.get(name) or {}
        if not isinstance(section, dict):
            raise ValueError(f"{name} must be a mapping")
        return section

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
