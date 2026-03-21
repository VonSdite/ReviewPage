#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from src.integrations.agents.opencode_agent import OpencodeReviewAgent


class _FakeConfigManager:
    def get_agent_config(self, agent_id):
        self._last_agent_id = agent_id
        return {
            "binary": "opencode",
            "list_models_command": ["models"],
            "review_command": ["run", "--model", "{model}", "{prompt}"],
            "prompt_template": "/review {review_url}",
            "model_list": ["fallback/model"],
            "extra_env": {"OPENCODE_ENV": "1"},
        }


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
    def test_get_model_catalog_from_command(self):
        agent = OpencodeReviewAgent(_FakeCtx())

        with patch("src.integrations.agents.opencode_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=0,
                stdout="provider/model-a\nprovider/model-b\n",
            )
            catalog = agent.get_model_catalog()

        self.assertEqual(catalog.source, "command")
        self.assertEqual([item.model_id for item in catalog.models], ["provider/model-a", "provider/model-b"])

    def test_get_model_catalog_falls_back_to_config(self):
        agent = OpencodeReviewAgent(_FakeCtx())

        with patch("src.integrations.agents.opencode_agent.subprocess.run") as mocked_run:
            mocked_run.return_value = _FakeCompletedProcess(
                returncode=1,
                stderr="binary missing",
            )
            catalog = agent.get_model_catalog()

        self.assertEqual(catalog.source, "config-fallback")
        self.assertEqual([item.model_id for item in catalog.models], ["fallback/model"])
        self.assertIn("binary missing", catalog.error)

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
