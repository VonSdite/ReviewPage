#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.integrations.agents.opencode_agent import OpencodeReviewAgent


class _FakeConfigManager:
    def __init__(self, agent_overrides=None, command_shell_config=None):
        self.updated_models = None
        self._command_shell_config = deepcopy(command_shell_config)
        self._agent_config = {
            "list_models_command": "opencode models",
            "review_command": 'opencode run --model "{model}" "/review {review_url}"',
            "models": ["configured/model"],
            "extra_env": {"OPENCODE_ENV": "1"},
        }
        if agent_overrides:
            self._agent_config.update(agent_overrides)

    def get_agent_config(self, agent_id):
        self._last_agent_id = agent_id
        return dict(self._agent_config)

    def get_command_shell_config(self):
        return deepcopy(self._command_shell_config)

    def update_agent_models(self, agent_id, models):
        self.updated_models = (agent_id, list(models))
        self._agent_config["models"] = list(models)


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeCtx:
    def __init__(self, agent_overrides=None, command_shell_config=None):
        self.logger = logging.getLogger("test.opencode_agent")
        self.config_manager = _FakeConfigManager(
            agent_overrides=agent_overrides,
            command_shell_config=command_shell_config,
        )
        self.root_path = Path(".")


class OpencodeAgentTestCase(unittest.TestCase):
    def test_get_model_catalog_reads_from_config(self):
        agent = OpencodeReviewAgent(_FakeCtx())
        catalog = agent.get_model_catalog()

        self.assertEqual(catalog.source, "config")
        self.assertEqual([item.model_id for item in catalog.models], ["configured/model"])

    def test_refresh_model_catalog_updates_config(self):
        ctx = _FakeCtx()
        agent = OpencodeReviewAgent(ctx)

        with patch("src.integrations.agents.opencode_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="provider/model-a\nprovider/model-b\n",
            )
            catalog = agent.refresh_model_catalog()

        self.assertEqual(catalog.source, "config")
        self.assertEqual([item.model_id for item in catalog.models], ["provider/model-a", "provider/model-b"])
        self.assertEqual(ctx.config_manager.updated_models, ("opencode", ["provider/model-a", "provider/model-b"]))

    def test_refresh_model_catalog_raises_when_command_fails(self):
        agent = OpencodeReviewAgent(_FakeCtx())

        with patch("src.integrations.agents.opencode_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=1,
                stderr="binary missing",
            )
            with self.assertRaisesRegex(ValueError, "binary missing"):
                agent.refresh_model_catalog()

    def test_build_review_command_uses_template(self):
        agent = OpencodeReviewAgent(_FakeCtx())
        command = agent.build_review_command(
            model="provider/model-a",
            review_url="https://gitlab.example.com/group/project/-/merge_requests/8",
            workspace_dir="/tmp/review-8/repo",
        )
        self.assertEqual(
            command.argv,
            [
                "opencode",
                "run",
                "--model",
                "provider/model-a",
                "/review https://gitlab.example.com/group/project/-/merge_requests/8",
            ],
        )
        self.assertEqual(command.env, {"OPENCODE_ENV": "1"})

    def test_refresh_model_catalog_uses_configured_shell(self):
        ctx = _FakeCtx(
            command_shell_config={
                "executable": "C:/Program Files/Git/bin/bash.exe",
                "args": ["-lc"],
            }
        )
        agent = OpencodeReviewAgent(ctx)

        with patch("src.integrations.agents.opencode_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="provider/model-a\n",
            )
            agent.refresh_model_catalog()

        self.assertEqual(
            mocked_run.call_args.args[0],
            ["C:/Program Files/Git/bin/bash.exe", "-lc", "opencode models"],
        )

    def test_build_review_command_wraps_with_configured_shell(self):
        agent = OpencodeReviewAgent(
            _FakeCtx(
                command_shell_config={
                    "executable": "C:/Program Files/Git/bin/bash.exe",
                    "args": ["-lc"],
                }
            )
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
                "opencode run --model provider/model-a '/review https://gitlab.example.com/group/project/-/merge_requests/8'",
            ],
        )
        self.assertEqual(command.env, {"OPENCODE_ENV": "1"})

    def test_global_shell_takes_precedence_over_agent_level_shell(self):
        agent = OpencodeReviewAgent(
            _FakeCtx(
                agent_overrides={
                    "command_shell": {
                        "executable": "C:/legacy-agent-shell.exe",
                        "args": ["-lc"],
                    }
                },
                command_shell_config={
                    "executable": "C:/Program Files/Git/bin/bash.exe",
                    "args": ["-lc"],
                },
            )
        )
        command = agent.build_review_command(
            model="provider/model-a",
            review_url="https://gitlab.example.com/group/project/-/merge_requests/8",
            workspace_dir="/tmp/review-8/repo",
        )

        self.assertEqual(command.argv[0], "C:/Program Files/Git/bin/bash.exe")


if __name__ == "__main__":
    unittest.main()
