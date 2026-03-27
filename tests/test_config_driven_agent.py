#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.integrations.agents import ConfigDrivenReviewAgent, build_config_driven_agents


class _FakeConfigManager:
    def __init__(self, agent_configs=None, command_shell_config=None):
        self.updated_models = None
        self._command_shell_config = deepcopy(command_shell_config)
        self._agent_configs = deepcopy(
            agent_configs
            or {
                "demo-agent": {
                    "list_models_command": "demo models",
                    "review_command": 'demo review --model "{model}" "{review_url}"',
                    "models": ["configured/model"],
                    "extra_env": {"DEMO_AGENT_ENV": "1"},
                }
            }
        )

    def get_agent_ids(self):
        return list(self._agent_configs)

    def get_agent_config(self, agent_id):
        self._last_agent_id = agent_id
        return deepcopy(self._agent_configs[agent_id])

    def get_agent_default_model_id(self, agent_id):
        agent_config = self._agent_configs.get(agent_id, {})
        return str(agent_config.get("default_model") or "").strip() or None

    def get_command_shell_config(self):
        return deepcopy(self._command_shell_config)

    def update_agent_models(self, agent_id, models):
        self.updated_models = (agent_id, list(models))
        self._agent_configs[agent_id]["models"] = list(models)


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeCtx:
    def __init__(self, agent_configs=None, command_shell_config=None):
        self.logger = logging.getLogger("test.config_driven_agent")
        self.config_manager = _FakeConfigManager(
            agent_configs=agent_configs,
            command_shell_config=command_shell_config,
        )
        self.root_path = Path(".")


class ConfigDrivenAgentTestCase(unittest.TestCase):
    def test_build_config_driven_agents_reads_all_agent_ids(self):
        ctx = _FakeCtx(
            agent_configs={
                "agent-a": {
                    "list_models_command": "agent-a models",
                    "review_command": "agent-a review",
                    "models": ["a/model"],
                },
                "agent-b": {
                    "list_models_command": "agent-b models",
                    "review_command": "agent-b review",
                    "models": ["b/model"],
                },
            }
        )

        agents = build_config_driven_agents(ctx)

        self.assertEqual(sorted(agents), ["agent-a", "agent-b"])
        self.assertTrue(all(isinstance(agent, ConfigDrivenReviewAgent) for agent in agents.values()))

    def test_get_model_catalog_reads_from_config(self):
        agent = ConfigDrivenReviewAgent(_FakeCtx(), "demo-agent")
        catalog = agent.get_model_catalog()

        self.assertEqual(catalog.source, "config")
        self.assertEqual([item.model_id for item in catalog.models], ["configured/model"])

    def test_get_default_model_id_reads_from_config(self):
        agent = ConfigDrivenReviewAgent(
            _FakeCtx(
                agent_configs={
                    "demo-agent": {
                        "list_models_command": "demo models",
                        "review_command": "demo review",
                        "models": ["configured/model"],
                        "default_model": "configured/model",
                    }
                }
            ),
            "demo-agent",
        )

        self.assertEqual(agent.get_default_model_id(), "configured/model")

    def test_refresh_model_catalog_updates_config(self):
        ctx = _FakeCtx()
        agent = ConfigDrivenReviewAgent(ctx, "demo-agent")

        with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="provider/model-a\nprovider/model-b\n",
            )
            catalog = agent.refresh_model_catalog()

        self.assertEqual(catalog.source, "config")
        self.assertEqual([item.model_id for item in catalog.models], ["provider/model-a", "provider/model-b"])
        self.assertEqual(ctx.config_manager.updated_models, ("demo-agent", ["provider/model-a", "provider/model-b"]))

    def test_refresh_model_catalog_strips_terminal_control_sequences(self):
        ctx = _FakeCtx()
        agent = ConfigDrivenReviewAgent(ctx, "demo-agent")

        with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="\x1b[32mprovider/model-a\x1b[0m\n",
            )
            catalog = agent.refresh_model_catalog()

        self.assertEqual([item.model_id for item in catalog.models], ["provider/model-a"])
        self.assertEqual(ctx.config_manager.updated_models, ("demo-agent", ["provider/model-a"]))

    def test_refresh_model_catalog_raises_when_command_fails(self):
        agent = ConfigDrivenReviewAgent(_FakeCtx(), "demo-agent")

        with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=1,
                stderr="binary missing",
            )
            with self.assertRaisesRegex(ValueError, "binary missing"):
                agent.refresh_model_catalog()

    def test_build_review_command_uses_template(self):
        agent = ConfigDrivenReviewAgent(_FakeCtx(), "demo-agent")
        command = agent.build_review_command(
            model="provider/model-a",
            review_url="https://gitlab.example.com/group/project/-/merge_requests/8",
            workspace_dir="/tmp/review-8/repo",
        )
        self.assertEqual(
            command.argv,
            [
                "demo",
                "review",
                "--model",
                "provider/model-a",
                "https://gitlab.example.com/group/project/-/merge_requests/8",
            ],
        )
        self.assertEqual(
            command.env,
            {
                "NO_COLOR": "1",
                "FORCE_COLOR": "0",
                "CLICOLOR": "0",
                "CLICOLOR_FORCE": "0",
                "DEMO_AGENT_ENV": "1",
            },
        )

    def test_refresh_model_catalog_uses_configured_shell(self):
        ctx = _FakeCtx(
            command_shell_config={
                "executable": "C:/Program Files/Git/bin/bash.exe",
                "args": ["-lc"],
            }
        )
        agent = ConfigDrivenReviewAgent(ctx, "demo-agent")

        with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="provider/model-a\n",
            )
            agent.refresh_model_catalog()

        self.assertEqual(
            mocked_run.call_args.args[0],
            ["C:/Program Files/Git/bin/bash.exe", "-lc", "demo models"],
        )

    def test_refresh_model_catalog_disables_color_output_by_default(self):
        agent = ConfigDrivenReviewAgent(_FakeCtx(), "demo-agent")

        with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(returncode=0, stdout="provider/model-a\n")
            agent.refresh_model_catalog()

        env = mocked_run.call_args.kwargs["env"]
        self.assertEqual(env["NO_COLOR"], "1")
        self.assertEqual(env["FORCE_COLOR"], "0")
        self.assertEqual(env["CLICOLOR"], "0")
        self.assertEqual(env["CLICOLOR_FORCE"], "0")
        self.assertEqual(env["DEMO_AGENT_ENV"], "1")

    def test_build_review_command_wraps_with_configured_shell(self):
        agent = ConfigDrivenReviewAgent(
            _FakeCtx(
                command_shell_config={
                    "executable": "C:/Program Files/Git/bin/bash.exe",
                    "args": ["-lc"],
                }
            ),
            "demo-agent",
        )
        command = agent.build_review_command(
            model="provider/model-a",
            review_url="https://gitlab.example.com/group/project/-/merge_requests/8",
            workspace_dir="/tmp/review-8/repo",
        )

        self.assertEqual(
            command.argv,
            [
                "C:/Program Files/Git/bin/bash.exe",
                "-lc",
                "demo review --model provider/model-a https://gitlab.example.com/group/project/-/merge_requests/8",
            ],
        )
        self.assertEqual(
            command.env,
            {
                "NO_COLOR": "1",
                "FORCE_COLOR": "0",
                "CLICOLOR": "0",
                "CLICOLOR_FORCE": "0",
                "DEMO_AGENT_ENV": "1",
            },
        )

    def test_agent_level_shell_is_ignored(self):
        agent = ConfigDrivenReviewAgent(
            _FakeCtx(
                agent_configs={
                    "demo-agent": {
                        "list_models_command": "demo models",
                        "review_command": "demo review",
                        "models": ["configured/model"],
                        "command_shell": {
                            "executable": "C:/legacy-agent-shell.exe",
                            "args": ["-lc"],
                        },
                    }
                },
            ),
            "demo-agent",
        )
        command = agent.build_review_command(
            model="provider/model-a",
            review_url="https://gitlab.example.com/group/project/-/merge_requests/8",
            workspace_dir="/tmp/review-8/repo",
        )

        self.assertEqual(
            command.argv,
            [
                "demo",
                "review",
            ],
        )

    def test_command_env_keeps_process_environment_available(self):
        agent = ConfigDrivenReviewAgent(_FakeCtx(), "demo-agent")

        with patch.dict(os.environ, {"PATH": "C:/Windows/System32"}, clear=True):
            with patch("src.integrations.agents.config_driven_agent.subprocess.run") as mocked_run:
                mocked_run.return_value = _FakeCompletedProcess(returncode=0, stdout="provider/model-a\n")
                agent.refresh_model_catalog()

        self.assertEqual(mocked_run.call_args.kwargs["env"]["PATH"], "C:/Windows/System32")

    def test_missing_list_models_command_raises(self):
        with self.assertRaisesRegex(ValueError, "agents.demo-agent.list_models_command cannot be empty"):
            ConfigDrivenReviewAgent(
                _FakeCtx(
                    agent_configs={
                        "demo-agent": {
                            "review_command": "demo review",
                            "models": ["configured/model"],
                        }
                    }
                ),
                "demo-agent",
            )


if __name__ == "__main__":
    unittest.main()
