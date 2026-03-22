#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils.process import decode_command_output, resolve_command_argv, stream_command


class ProcessTestCase(unittest.TestCase):
    def test_resolve_command_argv_uses_path_lookup(self):
        with patch("src.utils.process.shutil.which") as mocked_which:
            mocked_which.return_value = "C:/Users/Von/AppData/Roaming/npm/opencode.CMD"

            argv = resolve_command_argv(["opencode", "models"])

        self.assertEqual(argv, ["C:/Users/Von/AppData/Roaming/npm/opencode.CMD", "models"])

    def test_resolve_command_argv_keeps_explicit_path(self):
        with patch("src.utils.process.shutil.which") as mocked_which:
            argv = resolve_command_argv(["C:/Program Files/Git/bin/bash.exe", "-lc", "opencode models"])

        self.assertEqual(argv, ["C:/Program Files/Git/bin/bash.exe", "-lc", "opencode models"])
        mocked_which.assert_not_called()

    def test_decode_command_output_prefers_utf8(self):
        with patch("src.utils.process.locale.getpreferredencoding") as mocked_getpreferredencoding:
            mocked_getpreferredencoding.return_value = "gbk"

            decoded = decode_command_output("build ✓ maas-glm-4.7".encode("utf-8"))

        self.assertEqual(decoded, "build ✓ maas-glm-4.7")

    def test_decode_command_output_falls_back_to_system_encoding(self):
        with patch("src.utils.process.locale.getpreferredencoding") as mocked_getpreferredencoding:
            mocked_getpreferredencoding.return_value = "gbk"

            decoded = decode_command_output("中文输出".encode("gbk"))

        self.assertEqual(decoded, "中文输出")

    def test_stream_command_uses_resolved_executable(self):
        process = MagicMock()
        process.stdout = iter(["provider/model-a\n".encode("utf-8")])
        process.wait.return_value = 0

        with patch("src.utils.process.resolve_command_argv") as mocked_resolve:
            mocked_resolve.return_value = ["C:/Users/Von/AppData/Roaming/npm/opencode.CMD", "models"]
            with patch("src.utils.process.subprocess.Popen") as mocked_popen:
                mocked_popen.return_value = process

                result = stream_command(["opencode", "models"], cwd=Path("."))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.output, "provider/model-a")
        mocked_popen.assert_called_once()
        self.assertEqual(
            mocked_popen.call_args.args[0],
            ["C:/Users/Von/AppData/Roaming/npm/opencode.CMD", "models"],
        )
        self.assertEqual(mocked_popen.call_args.kwargs["bufsize"], -1)


if __name__ == "__main__":
    unittest.main()
