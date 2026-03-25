#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Config-driven CLI review agent."""

from __future__ import annotations

import os
import shlex
import subprocess

from ...domain import AgentModelCatalog, ModelChoice, ReviewAgent, ReviewCommandSpec
from ...utils import decode_command_output, resolve_command_argv, strip_terminal_control_sequences


DEFAULT_OUTPUT_ENV = {
    "NO_COLOR": "1",
    "FORCE_COLOR": "0",
    "CLICOLOR": "0",
    "CLICOLOR_FORCE": "0",
}


class ConfigDrivenReviewAgent(ReviewAgent):
    def __init__(self, ctx: object, agent_id: str):
        self._ctx = ctx
        self._logger = ctx.logger
        self.agent_id = str(agent_id or "").strip()
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")

        self._config = ctx.config_manager.get_agent_config(self.agent_id)
        self._list_models_command = self._read_required_command("list_models_command")
        self._review_command = self._read_required_command("review_command")
        global_command_shell = ctx.config_manager.get_command_shell_config()
        self._command_shell = self._parse_command_shell(global_command_shell or self._config.get("command_shell"))
        self._extra_env = {str(k): str(v) for k, v in (self._config.get("extra_env") or {}).items()}

    def get_model_catalog(self) -> AgentModelCatalog:
        models = self._load_config_models()
        if not models:
            return AgentModelCatalog(models=[], source="config", error="当前 Agent 还没有配置模型，请先点击刷新模型")
        return AgentModelCatalog(models=[ModelChoice(model_id=item) for item in models], source="config")

    def refresh_model_catalog(self) -> AgentModelCatalog:
        argv = self._build_command_argv(self._list_models_command, command_name="list_models_command")
        try:
            completed = subprocess.run(
                resolve_command_argv(argv),
                cwd=str(self._ctx.root_path),
                capture_output=True,
                text=False,
                check=False,
                env=self._build_subprocess_env(),
            )
        except FileNotFoundError as exc:
            raise ValueError(f"未找到 Agent 命令：{exc}") from exc
        except Exception as exc:
            raise ValueError(f"获取模型列表失败：{exc}") from exc

        if completed.returncode != 0:
            stderr = (
                strip_terminal_control_sequences(decode_command_output(completed.stderr))
                or strip_terminal_control_sequences(decode_command_output(completed.stdout))
            ).strip()
            message = stderr or f"命令退出码 {completed.returncode}"
            raise ValueError(f"获取模型列表失败：{message}")

        stdout_text = strip_terminal_control_sequences(decode_command_output(completed.stdout))
        model_ids: list[str] = []
        seen: set[str] = set()
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("available models"):
                continue
            normalized = line.lstrip("-*").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            model_ids.append(normalized)

        if not model_ids:
            raise ValueError("Agent 未返回任何模型")

        self._ctx.config_manager.update_agent_models(self.agent_id, model_ids)
        return self.get_model_catalog()

    def build_review_command(self, *, model: str, review_url: str, workspace_dir: str) -> ReviewCommandSpec:
        argv = self._build_command_argv(
            self._review_command,
            command_name="review_command",
            model=model,
            review_url=review_url,
            workspace_dir=workspace_dir,
        )
        return ReviewCommandSpec(argv=argv, env=self._build_command_env())

    def get_default_model_id(self) -> str | None:
        return self._ctx.config_manager.get_agent_default_model_id(self.agent_id)

    def _read_required_command(self, key: str) -> str:
        value = str(self._config.get(key) or "").strip()
        if value:
            return value
        raise ValueError(f"agents.{self.agent_id}.{key} cannot be empty")

    def _load_config_models(self) -> list[str]:
        agent_config = self._ctx.config_manager.get_agent_config(self.agent_id)
        raw_models = agent_config.get("models") or []
        if not isinstance(raw_models, list):
            raise ValueError(f"agents.{self.agent_id}.models must be a list")

        seen: set[str] = set()
        models: list[str] = []
        for item in raw_models:
            model_id = str(item or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            models.append(model_id)
        return models

    def _parse_command_string(self, template: str, *, command_name: str, **values: str) -> list[str]:
        command_text = str(template or "").strip()
        if not command_text:
            raise ValueError(f"{command_name} 不能为空")

        try:
            rendered = command_text.format(**values)
        except KeyError as exc:
            raise ValueError(f"{command_name} 包含未知占位符：{exc}") from exc

        try:
            argv = shlex.split(rendered)
        except ValueError as exc:
            raise ValueError(f"{command_name} 解析失败：{exc}") from exc

        if not argv:
            raise ValueError(f"{command_name} 不能为空")
        return argv

    def _build_command_argv(self, template: str, *, command_name: str, **values: str) -> list[str]:
        argv = self._parse_command_string(template, command_name=command_name, **values)
        if not self._command_shell:
            return argv

        return [
            self._command_shell["executable"],
            *self._command_shell["args"],
            shlex.join(argv),
        ]

    def _parse_command_shell(self, raw_shell: object) -> dict[str, object] | None:
        if raw_shell in (None, "", {}):
            return None

        if isinstance(raw_shell, str):
            executable = raw_shell.strip()
            if not executable:
                return None
            return {"executable": executable, "args": ["-lc"]}

        if not isinstance(raw_shell, dict):
            raise ValueError("command_shell must be a string or mapping")

        executable = str(raw_shell.get("executable") or "").strip()
        if not executable:
            raise ValueError("command_shell.executable cannot be empty")

        raw_args = raw_shell.get("args")
        if raw_args is None:
            args = ["-lc"]
        elif not isinstance(raw_args, list):
            raise ValueError("command_shell.args must be a list")
        else:
            args = [str(item).strip() for item in raw_args if str(item or "").strip()]

        if not args:
            args = ["-lc"]

        return {"executable": executable, "args": args}

    def _build_command_env(self) -> dict[str, str]:
        env = dict(DEFAULT_OUTPUT_ENV)
        env.update(self._extra_env)
        return env

    def _build_subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self._build_command_env())
        return env
