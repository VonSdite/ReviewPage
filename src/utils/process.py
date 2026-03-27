#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子进程执行工具。"""

from __future__ import annotations

import locale
import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class CommandRunResult:
    returncode: int
    output: str


class CommandCancelledError(RuntimeError):
    def __init__(self, output: str = "", message: str = "命令执行已取消"):
        super().__init__(message)
        self.output = output


def format_command(argv: list[str]) -> str:
    return shlex.join(argv)


_TERMINAL_ESCAPE_RE = re.compile(
    r"""
    (?:\x1B\][^\x07\x1B]*(?:\x07|\x1B\\))
    |(?:\x1B[@-_][0-?]*[ -/]*[@-~])
    |(?:\x9B[0-?]*[ -/]*[@-~])
    """,
    re.VERBOSE,
)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def strip_terminal_control_sequences(text: str) -> str:
    if not text:
        return ""

    without_escape_sequences = _TERMINAL_ESCAPE_RE.sub("", text)
    return _CONTROL_CHAR_RE.sub("", without_escape_sequences)


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


def build_hidden_subprocess_kwargs(*, new_process_group: bool = False) -> dict[str, object]:
    if os.name != "nt":
        if new_process_group:
            return {"start_new_session": True}
        return {}

    kwargs: dict[str, object] = {}
    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo

    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0) or 0)
    if new_process_group:
        creationflags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) or 0)
    if creationflags:
        kwargs["creationflags"] = creationflags

    return kwargs


def kill_subprocess_tree(process: subprocess.Popen[bytes], *, grace_period_seconds: float = 1.5) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        _kill_windows_process_tree(process, grace_period_seconds=grace_period_seconds)
        return

    _kill_posix_process_tree(process, grace_period_seconds=grace_period_seconds)


def _kill_windows_process_tree(process: subprocess.Popen[bytes], *, grace_period_seconds: float) -> None:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **build_hidden_subprocess_kwargs(),
        )
    except Exception:
        try:
            process.terminate()
        except OSError:
            return

    try:
        process.wait(timeout=grace_period_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        return

    try:
        process.kill()
    except OSError:
        return

    try:
        process.wait(timeout=grace_period_seconds)
    except (subprocess.TimeoutExpired, OSError):
        return


def _kill_posix_process_tree(process: subprocess.Popen[bytes], *, grace_period_seconds: float) -> None:
    process_group_id: int | None = None
    try:
        process_group_id = os.getpgid(process.pid)
    except OSError:
        process_group_id = None

    if process_group_id is not None:
        try:
            os.killpg(process_group_id, signal.SIGTERM)
        except OSError:
            process_group_id = None

    if process_group_id is None:
        try:
            process.terminate()
        except OSError:
            return

    try:
        process.wait(timeout=grace_period_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        return

    if process_group_id is not None:
        try:
            os.killpg(process_group_id, signal.SIGKILL)
        except OSError:
            process_group_id = None

    if process_group_id is None:
        try:
            process.kill()
        except OSError:
            return

    try:
        process.wait(timeout=grace_period_seconds)
    except (subprocess.TimeoutExpired, OSError):
        return


def _read_process_output(stdout, output_queue: "queue.Queue[bytes | None]") -> None:
    try:
        for raw_line in stdout:
            output_queue.put(raw_line)
    finally:
        output_queue.put(None)


def stream_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    on_output: Callable[[str], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
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
            bufsize=-1,
            env=merged_env,
            **build_hidden_subprocess_kwargs(new_process_group=True),
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

    output_queue: queue.Queue[bytes | None] = queue.Queue()
    reader_thread = threading.Thread(
        target=_read_process_output,
        args=(process.stdout, output_queue),
        name="command-output-reader",
        daemon=True,
    )
    reader_thread.start()

    try:
        while True:
            if cancel_requested and cancel_requested():
                kill_subprocess_tree(process)
                raise CommandCancelledError(output="\n".join(lines))

            try:
                raw_line = output_queue.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None and not reader_thread.is_alive():
                    break
                continue

            if raw_line is None:
                if process.poll() is not None:
                    break
                continue

            line = strip_terminal_control_sequences(decode_command_output(raw_line)).rstrip("\r\n")
            if not line and raw_line.rstrip(b"\r\n"):
                continue
            lines.append(line)
            if on_output:
                on_output(line)
    finally:
        try:
            process.stdout.close()
        except (AttributeError, OSError):
            pass
        reader_thread.join(timeout=0.5)

    returncode = process.wait()
    return CommandRunResult(returncode=returncode, output="\n".join(lines))
