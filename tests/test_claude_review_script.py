#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import claude_review


class ClaudeReviewScriptTestCase(unittest.TestCase):
    def test_get_model_ids_uses_default_aliases(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(claude_review.get_model_ids(), ["sonnet", "opus", "fable"])

    def test_get_model_ids_accepts_environment_override(self):
        with patch.dict("os.environ", {"CLAUDE_REVIEW_MODELS": "sonnet,opus\nsonnet\nclaude-custom"}):
            self.assertEqual(claude_review.get_model_ids(), ["sonnet", "opus", "claude-custom"])

    def test_build_prompt_substitutes_review_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "prompt.md"
            prompt_file.write_text(
                "MR=$REVIEW_URL\nWORK=$WORKSPACE_DIR\nSRC=$SOURCE_BRANCH\nDST=$TARGET_BRANCH\n",
                encoding="utf-8",
            )
            workspace = Path(tmpdir) / "repo"
            workspace.mkdir()
            args = argparse.Namespace(
                prompt_file=str(prompt_file),
                review_url="https://gitlab.example.com/group/project/-/merge_requests/1",
                workspace_dir=str(workspace),
                repo_url="https://gitlab.example.com/group/project.git",
                source_branch="feature/demo",
                target_branch="main",
                model="sonnet",
            )

            prompt = claude_review.build_prompt(args)

        self.assertIn("MR=https://gitlab.example.com/group/project/-/merge_requests/1", prompt)
        self.assertIn(f"WORK={workspace.resolve()}", prompt)
        self.assertIn("SRC=feature/demo", prompt)
        self.assertIn("DST=main", prompt)

    def test_build_claude_argv_uses_stream_json_and_review_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "repo"
            workspace.mkdir()
            args = argparse.Namespace(
                claude_bin="claude",
                workspace_dir=str(workspace),
                permission_mode="bypassPermissions",
                model="sonnet",
            )

            command = claude_review.build_claude_argv(args, "review prompt")

        self.assertEqual(command[0], "claude")
        self.assertIn("--output-format", command)
        self.assertIn("stream-json", command)
        self.assertIn("--include-partial-messages", command)
        self.assertIn("--add-dir", command)
        self.assertIn(str(workspace.resolve()), command)
        self.assertIn("--model", command)
        self.assertIn("sonnet", command)
        self.assertEqual(command[-1], "review prompt")

    def test_emit_stream_event_prints_only_new_assistant_delta(self):
        state = {"messages": {}, "emitted_text": False}
        first_event = {
            "type": "assistant",
            "message": {
                "id": "msg_1",
                "content": [{"type": "text", "text": "第一段"}],
            },
        }
        second_event = {
            "type": "assistant",
            "message": {
                "id": "msg_1",
                "content": [{"type": "text", "text": "第一段新增"}],
            },
        }

        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            claude_review.emit_stream_event(first_event, state)
            claude_review.emit_stream_event(second_event, state)

        self.assertEqual(stdout.getvalue(), "第一段\n新增\n")


if __name__ == "__main__":
    unittest.main()
