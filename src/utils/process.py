#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子进程执行工具。"""

from __future__ import annotations

import os
import shlex
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

    try:
        process = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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
        line = raw_line.rstrip("\n")
        lines.append(line)
        if on_output:
            on_output(line)

    returncode = process.wait()
    return CommandRunResult(returncode=returncode, output="\n".join(lines))
