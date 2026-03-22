#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from src.integrations.agents.opencode_agent import OpencodeReviewAgent


class _FakeConfigManager:
    def __init__(self):
        self.updated_models = None
        self._agent_config = {
            "list_models_command": "opencode models",
            "review_command": 'opencode run --model "{model}" "/review {review_url}"',
            "models": ["configured/model"],
            "extra_env": {"OPENCODE_ENV": "1"},
        }

    def get_agent_config(self, agent_id):
        self._last_agent_id = agent_id
        return dict(self._agent_config)

    def update_agent_models(self, agent_id, models):
        self.updated_models = (agent_id, list(models))
        self._agent_config["models"] = list(models)


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeCtx:
    def __init__(self):
        self.logger = logging.getLogger("test.opencode_agent")
        self.config_manager = _FakeConfigManager()
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


if __name__ == "__main__":
    unittest.main()
