#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from src.config.config_manager import ConfigManager


class ConfigManagerTestCase(unittest.TestCase):
    def test_empty_config_uses_getter_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text("", encoding="utf-8")

            manager = ConfigManager(config_path, root)

        self.assertEqual(manager.get_server_host(), "0.0.0.0")
        self.assertEqual(manager.get_server_port(), 8091)
        self.assertEqual(manager.get_database_path(), str((root / "data" / "review_page.sqlite3").resolve()))
        self.assertEqual(manager.get_log_path(), str((root / "data" / "logs").resolve()))
        self.assertEqual(manager.get_log_level(), "INFO")
        self.assertEqual(manager.get_workspace_temp_root(), str((root / "data" / "tmp" / "reviews").resolve()))
        self.assertEqual(manager.get_queue_poll_interval_seconds(), 2.0)
        self.assertIsNone(manager.get_command_shell_config())
        self.assertEqual(manager.get_default_agent_id(), "opencode")
        self.assertEqual(manager.get_default_hub_id(), "gitlab")
        self.assertIsNone(manager.get_agent_default_model_id("opencode"))

    def test_database_path_accepts_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text("database:\n  path: data\n", encoding="utf-8")

            manager = ConfigManager(config_path, root)

        self.assertEqual(manager.get_database_path(), str((root / "data" / "review_page.sqlite3").resolve()))

    def test_database_path_rejects_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text("database:\n  path: data/custom.db\n", encoding="utf-8")

            manager = ConfigManager(config_path, root)

            with self.assertRaisesRegex(ValueError, "database.path must be a directory"):
                manager.get_database_path()

    def test_update_agent_models_persists_to_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "agents:\n  default: opencode\n  opencode:\n    enabled: true\n    models:\n      - stale/model\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            written = manager.update_agent_models("opencode", ["provider/model-a", "", "provider/model-a", "provider/model-b"])
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(written, ["provider/model-a", "provider/model-b"])
        self.assertEqual(
            reloaded.get_agent_config("opencode").get("models"),
            ["provider/model-a", "provider/model-b"],
        )

    def test_update_agent_default_model_persists_to_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "agents:\n  opencode:\n    enabled: true\n    models:\n      - provider/model-a\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            written = manager.update_agent_default_model("opencode", "provider/model-a")
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(written, "provider/model-a")
        self.assertEqual(reloaded.get_agent_default_model_id("opencode"), "provider/model-a")

    def test_update_agent_models_clears_invalid_default_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "agents:\n  opencode:\n    enabled: true\n    default_model: stale/model\n    models:\n      - stale/model\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.update_agent_models("opencode", ["provider/model-a"])
            reloaded = ConfigManager(config_path, root)

        self.assertIsNone(reloaded.get_agent_default_model_id("opencode"))

    def test_get_command_shell_config_reads_top_level_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "command_shell:\n  executable: C:/Program Files/Git/bin/bash.exe\n  args:\n    - -lc\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)

        self.assertEqual(
            manager.get_command_shell_config(),
            {
                "executable": "C:/Program Files/Git/bin/bash.exe",
                "args": ["-lc"],
            },
        )


if __name__ == "__main__":
    unittest.main()
