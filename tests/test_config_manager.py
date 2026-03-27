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

        self.assertEqual(manager.get_server_host(), "127.0.0.1")
        self.assertEqual(manager.get_server_port(), 8091)
        self.assertEqual(manager.get_database_path(), str((root / "data" / "review_page.sqlite3").resolve()))
        self.assertEqual(manager.get_log_path(), str((root / "data" / "logs").resolve()))
        self.assertEqual(manager.get_log_level(), "INFO")
        self.assertEqual(manager.get_workspace_temp_root(), str((root / "data" / "tmp" / "reviews").resolve()))
        self.assertEqual(manager.get_queue_poll_interval_seconds(), 2.0)
        self.assertIsNone(manager.get_command_shell_config())
        self.assertEqual(manager.get_agent_ids(), [])
        self.assertEqual(manager.get_default_agent_id(), "")
        self.assertEqual(manager.get_configured_default_agent_id(), "")
        self.assertEqual(manager.get_hub_ids(), [])
        self.assertEqual(manager.get_default_hub_id(), "")
        self.assertEqual(manager.get_configured_default_hub_id(), "")
        self.assertIsNone(manager.get_agent_default_model_id("opencode"))

    def test_default_agent_is_empty_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "agents:\n  z-agent:\n    list_models_command: z models\n    review_command: z run\n  a-agent:\n    list_models_command: a models\n    review_command: a run\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)

        self.assertEqual(manager.get_agent_ids(), ["z-agent", "a-agent"])
        self.assertEqual(manager.get_configured_default_agent_id(), "")
        self.assertEqual(manager.get_default_agent_id(), "")

    def test_default_hub_is_empty_when_not_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                "hubs:\n  primary:\n    type: gitlab\n    web_base_url: https://gitlab.one.example.com\n    api_base_url: https://gitlab.one.example.com/api/v4\n  backup:\n    type: gitlab\n    web_base_url: https://gitlab.two.example.com\n    api_base_url: https://gitlab.two.example.com/api/v4\n",
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)

        self.assertEqual(manager.get_hub_ids(), ["primary", "backup"])
        self.assertEqual(manager.get_configured_default_hub_id(), "")
        self.assertEqual(manager.get_default_hub_id(), "")

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
                "agents:\n  default: opencode\n  opencode:\n    models:\n      - stale/model\n",
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
                "agents:\n  opencode:\n    models:\n      - provider/model-a\n",
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
                "agents:\n  opencode:\n    default_model: stale/model\n    models:\n      - stale/model\n",
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

    def test_update_agent_settings_removes_legacy_agent_shell(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                (
                    "agents:\n"
                    "  opencode:\n"
                    "    list_models_command: opencode models\n"
                    "    review_command: opencode run\n"
                    "    models:\n"
                    "      - provider/model-a\n"
                    "    command_shell:\n"
                    "      executable: /bin/bash\n"
                    "      args:\n"
                    "        - -lc\n"
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.update_agent_settings(
                "opencode",
                {
                    "list_models_command": "foo models",
                    "review_command": "foo run",
                    "models": ["provider/model-b"],
                    "default_model": "provider/model-b",
                    "extra_env": {},
                },
            )
            reloaded = ConfigManager(config_path, root)

        self.assertNotIn("command_shell", reloaded.get_agent_config("opencode"))

    def test_rename_agent_updates_key_and_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                (
                    "agents:\n"
                    "  default: opencode\n"
                    "  opencode:\n"
                    "    list_models_command: opencode models\n"
                    "    review_command: opencode run\n"
                    "    models:\n"
                    "      - provider/model-a\n"
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.rename_agent("opencode", "codex")
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(reloaded.get_default_agent_id(), "codex")
        self.assertEqual(reloaded.get_agent_ids(), ["codex"])

    def test_rename_hub_updates_key_and_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                (
                    "hubs:\n"
                    "  default: gitlab\n"
                    "  gitlab:\n"
                    "    type: gitlab\n"
                    "    web_base_url: https://gitlab.example.com\n"
                    "    api_base_url: https://gitlab.example.com/api/v4\n"
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.rename_hub("gitlab", "gitlab-public")
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(reloaded.get_default_hub_id(), "gitlab-public")
        self.assertEqual(reloaded.get_hub_ids(), ["gitlab-public"])

    def test_delete_default_agent_clears_default_instead_of_switching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                (
                    "agents:\n"
                    "  default: opencode\n"
                    "  opencode:\n"
                    "    list_models_command: opencode models\n"
                    "    review_command: opencode run\n"
                    "  codex:\n"
                    "    list_models_command: codex models\n"
                    "    review_command: codex run\n"
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.delete_agent("opencode")
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(reloaded.get_default_agent_id(), "")
        self.assertEqual(reloaded.get_agent_ids(), ["codex"])

    def test_delete_default_hub_clears_default_instead_of_switching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            config_path.write_text(
                (
                    "hubs:\n"
                    "  default: gitlab\n"
                    "  gitlab:\n"
                    "    type: gitlab\n"
                    "    web_base_url: https://gitlab.example.com\n"
                    "    api_base_url: https://gitlab.example.com/api/v4\n"
                    "  backup:\n"
                    "    type: gitlab\n"
                    "    web_base_url: https://gitlab.backup.example.com\n"
                    "    api_base_url: https://gitlab.backup.example.com/api/v4\n"
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(config_path, root)
            manager.delete_hub("gitlab")
            reloaded = ConfigManager(config_path, root)

        self.assertEqual(reloaded.get_default_hub_id(), "")
        self.assertEqual(reloaded.get_hub_ids(), ["backup"])


if __name__ == "__main__":
    unittest.main()
