#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration access and persistence helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import threading
from typing import Any

import yaml


class ConfigManager:
    """Load and persist application configuration."""

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

    def get_agent_ids(self) -> list[str]:
        agent_section = self._get_section("agents")
        agent_ids: list[str] = []
        for raw_agent_id, agent_cfg in agent_section.items():
            agent_id = str(raw_agent_id or "").strip()
            if agent_id == "default":
                continue
            if not agent_id:
                raise ValueError("agents contains an empty agent id")
            if not isinstance(agent_cfg, dict):
                raise ValueError(f"agents.{agent_id} must be a mapping")
            agent_ids.append(agent_id)
        return agent_ids

    def get_default_agent_id(self) -> str:
        configured_default = str(self._get_section("agents").get("default") or "").strip()
        if configured_default:
            return configured_default

        agent_ids = self.get_agent_ids()
        return agent_ids[0] if agent_ids else ""

    def get_hub_ids(self) -> list[str]:
        hub_section = self._get_section("hubs")
        hub_ids: list[str] = []
        for raw_hub_id, hub_cfg in hub_section.items():
            hub_id = str(raw_hub_id or "").strip()
            if hub_id == "default":
                continue
            if not hub_id:
                raise ValueError("hubs contains an empty hub id")
            if not isinstance(hub_cfg, dict):
                raise ValueError(f"hubs.{hub_id} must be a mapping")
            hub_ids.append(hub_id)
        return hub_ids

    def get_default_hub_id(self) -> str:
        configured_default = str(self._get_section("hubs").get("default") or "").strip()
        if configured_default:
            return configured_default

        hub_ids = self.get_hub_ids()
        return hub_ids[0] if hub_ids else ""

    def get_agent_config(self, agent_id: str) -> dict[str, Any]:
        agent_cfg = self._get_section("agents").get(agent_id) or {}
        if not isinstance(agent_cfg, dict):
            raise ValueError(f"agents.{agent_id} must be a mapping")
        return deepcopy(agent_cfg)

    def get_agent_default_model_id(self, agent_id: str) -> str | None:
        model_id = str(self.get_agent_config(agent_id).get("default_model") or "").strip()
        return model_id or None

    def get_hub_config(self, hub_id: str) -> dict[str, Any]:
        hub_cfg = self._get_section("hubs").get(hub_id) or {}
        if not isinstance(hub_cfg, dict):
            raise ValueError(f"hubs.{hub_id} must be a mapping")
        return deepcopy(hub_cfg)

    def get_raw_config(self) -> dict[str, Any]:
        return deepcopy(self._config)

    def replace_raw_config(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw_config, dict):
            raise ValueError("config root must be a mapping")
        with self._lock:
            self._config = deepcopy(raw_config)
            self._write_config()
        return self.get_raw_config()

    def update_agent_models(self, agent_id: str, models: list[str]) -> list[str]:
        normalized = self._normalize_model_ids(models)
        with self._lock:
            agents = self._ensure_section("agents")
            agent_cfg = agents.setdefault(agent_id, {})
            if not isinstance(agent_cfg, dict):
                raise ValueError(f"agents.{agent_id} must be a mapping")
            agent_cfg["models"] = normalized
            current_default = str(agent_cfg.get("default_model") or "").strip()
            if current_default and current_default not in normalized:
                agent_cfg.pop("default_model", None)
            agent_cfg.pop("model_list", None)
            self._write_config()
        return normalized

    def update_agent_default_model(self, agent_id: str, model_id: str | None) -> str | None:
        normalized = str(model_id or "").strip() or None
        with self._lock:
            agents = self._ensure_section("agents")
            agent_cfg = agents.setdefault(agent_id, {})
            if not isinstance(agent_cfg, dict):
                raise ValueError(f"agents.{agent_id} must be a mapping")
            if normalized is None:
                agent_cfg.pop("default_model", None)
            else:
                agent_cfg["default_model"] = normalized
            self._write_config()
        return normalized

    def update_default_agent_id(self, agent_id: str | None) -> str:
        normalized = str(agent_id or "").strip()
        with self._lock:
            agents = self._ensure_section("agents")
            if normalized:
                agents["default"] = normalized
            else:
                agents.pop("default", None)
            self._write_config()
        return normalized

    def update_default_hub_id(self, hub_id: str | None) -> str:
        normalized = str(hub_id or "").strip()
        with self._lock:
            hubs = self._ensure_section("hubs")
            if normalized:
                hubs["default"] = normalized
            else:
                hubs.pop("default", None)
            self._write_config()
        return normalized

    def update_agent_settings(self, agent_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            agents = self._ensure_section("agents")
            agent_cfg = agents.setdefault(agent_id, {})
            if not isinstance(agent_cfg, dict):
                raise ValueError(f"agents.{agent_id} must be a mapping")

            if "list_models_command" in settings:
                agent_cfg["list_models_command"] = str(settings.get("list_models_command") or "").strip()
            if "review_command" in settings:
                agent_cfg["review_command"] = str(settings.get("review_command") or "").strip()
            if "models" in settings:
                agent_cfg["models"] = self._normalize_model_ids(settings.get("models") or [])
            if "default_model" in settings:
                normalized_default = str(settings.get("default_model") or "").strip()
                if normalized_default:
                    agent_cfg["default_model"] = normalized_default
                else:
                    agent_cfg.pop("default_model", None)
            if "extra_env" in settings:
                raw_extra_env = settings.get("extra_env") or {}
                if not isinstance(raw_extra_env, dict):
                    raise ValueError("agents.extra_env must be a mapping")
                agent_cfg["extra_env"] = {str(key): str(value) for key, value in raw_extra_env.items()}
            if "command_shell" in settings:
                raw_command_shell = settings.get("command_shell")
                if raw_command_shell in (None, "", {}):
                    agent_cfg.pop("command_shell", None)
                else:
                    agent_cfg["command_shell"] = deepcopy(raw_command_shell)

            current_default = str(agent_cfg.get("default_model") or "").strip()
            models = [str(item).strip() for item in (agent_cfg.get("models") or []) if str(item or "").strip()]
            if current_default and current_default not in models:
                agent_cfg.pop("default_model", None)

            agent_cfg.pop("model_list", None)
            self._write_config()
        return self.get_agent_config(agent_id)

    def update_hub_settings(self, hub_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            hubs = self._ensure_section("hubs")
            hub_cfg = hubs.setdefault(hub_id, {})
            if not isinstance(hub_cfg, dict):
                raise ValueError(f"hubs.{hub_id} must be a mapping")

            if "type" in settings:
                hub_cfg["type"] = str(settings.get("type") or "").strip()
            if "web_base_url" in settings:
                hub_cfg["web_base_url"] = str(settings.get("web_base_url") or "").strip()
            if "api_base_url" in settings:
                hub_cfg["api_base_url"] = str(settings.get("api_base_url") or "").strip()
            if "private_token" in settings:
                normalized_token = str(settings.get("private_token") or "").strip()
                hub_cfg["private_token"] = normalized_token or None
            if "clone_url_preference" in settings:
                hub_cfg["clone_url_preference"] = str(settings.get("clone_url_preference") or "").strip().lower()
            if "verify_ssl" in settings:
                hub_cfg["verify_ssl"] = bool(settings.get("verify_ssl"))
            if "timeout_seconds" in settings:
                hub_cfg["timeout_seconds"] = float(settings.get("timeout_seconds"))

            self._write_config()
        return self.get_hub_config(hub_id)

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
