#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子进程执行工具。"""

from __future__ import annotations

import locale
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class CommandRunResult:
    returncode: int
    output: str


def format_command(argv: list[str]) -> str:
    return shlex.join(argv)


def decode_command_output(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data

    candidates: list[str] = []
    for encoding in ("utf-8", locale.getpreferredencoding(False), os.device_encoding(1)):
        normalized = str(encoding or "").strip()
        if not normalized:
            continue
        if normalized.lower() in {item.lower() for item in candidates}:
            continue
        candidates.append(normalized)

    for encoding in candidates:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    fallback_encoding = candidates[0] if candidates else "utf-8"
    return data.decode(fallback_encoding, errors="replace")


def resolve_command_argv(argv: list[str]) -> list[str]:
    if not argv:
        return []

    executable = str(argv[0] or "")
    if not executable:
        return list(argv)

    if os.path.sep in executable or (os.path.altsep and os.path.altsep in executable):
        return list(argv)

    resolved = shutil.which(executable)
    if not resolved:
        return list(argv)

    return [resolved, *argv[1:]]


def stream_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    on_output: Callable[[str], None] | None = None,
) -> CommandRunResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    resolved_argv = resolve_command_argv(argv)

    try:
        process = subprocess.Popen(
            resolved_argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=1,
            env=merged_env,
        )
    except FileNotFoundError as exc:
        message = f"命令不存在：{exc}"
        if on_output:
            on_output(message)
        return CommandRunResult(returncode=127, output=message)
    except Exception as exc:
        message = f"命令启动失败：{exc}"
        if on_output:
            on_output(message)
        return CommandRunResult(returncode=1, output=message)

    lines: list[str] = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = decode_command_output(raw_line).rstrip("\r\n")
        lines.append(line)
        if on_output:
            on_output(line)

    returncode = process.wait()
    return CommandRunResult(returncode=returncode, output="\n".join(lines))
