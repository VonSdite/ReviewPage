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
        self.assertEqual(manager.get_plugin_modules(), [])
        self.assertEqual(manager.get_default_agent_id(), "opencode")
        self.assertEqual(manager.get_default_hub_id(), "gitlab")

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


if __name__ == "__main__":
    unittest.main()
