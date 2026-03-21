#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from src.config.config_manager import ConfigManager


class ConfigManagerTestCase(unittest.TestCase):
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
