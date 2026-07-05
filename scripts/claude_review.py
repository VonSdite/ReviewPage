#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run Claude Code review with streaming output."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from string import Template
from typing import Any


DEFAULT_MODELS = ("sonnet", "opus", "fable")
DEFAULT_DISALLOWED_TOOLS = "Edit,MultiEdit,Write,NotebookEdit"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "claude_code_review_prompt.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Claude Code for MR review.")
    parser.add_argument("--list-models", action="store_true", help="Print supported Claude model aliases and exit.")
    parser.add_argument("--review-url", default="", help="Merge Request URL.")
    parser.add_argument("--workspace-dir", default=".", help="Repository directory Claude should run in.")
    parser.add_argument("--repo-url", default="", help="Repository clone URL.")
    parser.add_argument("--source-branch", default="", help="MR source branch.")
    parser.add_argument("--target-branch", default="", help="MR target branch.")
    parser.add_argument("--model", default="", help="Claude model or alias.")
    parser.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"), help="Claude Code executable.")
    parser.add_argument("--prompt-file", default=str(PROMPT_PATH), help="Prompt template path.")
    parser.add_argument(
        "--permission-mode",
        default=os.environ.get("CLAUDE_REVIEW_PERMISSION_MODE", "bypassPermissions"),
        help="Claude Code permission mode.",
    )
    return parser.parse_args(argv)


def get_model_ids() -> list[str]:
    raw_models = os.environ.get("CLAUDE_REVIEW_MODELS", "")
    if not raw_models.strip():
        return list(DEFAULT_MODELS)

    models: list[str] = []
    seen: set[str] = set()
    for item in raw_models.replace(",", "\n").splitlines():
        model = item.strip()
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return models or list(DEFAULT_MODELS)


def build_prompt(args: argparse.Namespace) -> str:
    prompt_template = Path(args.prompt_file).read_text(encoding="utf-8")
    workspace_dir = str(Path(args.workspace_dir).resolve())
    return Template(prompt_template).safe_substitute(
        REVIEW_URL=str(args.review_url or ""),
        WORKSPACE_DIR=workspace_dir,
        REPO_URL=str(args.repo_url or ""),
        SOURCE_BRANCH=str(args.source_branch or ""),
        TARGET_BRANCH=str(args.target_branch or ""),
        MODEL=str(args.model or ""),
    )


def build_claude_argv(args: argparse.Namespace, prompt: str) -> list[str]:
    workspace_dir = str(Path(args.workspace_dir).resolve())
    command = [
        str(args.claude_bin or "claude"),
        "-p",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--no-session-persistence",
        "--add-dir",
        workspace_dir,
        "--permission-mode",
        str(args.permission_mode or "bypassPermissions"),
        "--disallowedTools",
        DEFAULT_DISALLOWED_TOOLS,
    ]
    if str(args.model or "").strip():
        command.extend(["--model", str(args.model).strip()])
    command.append(prompt)
    return command


def extract_text_from_message(message: dict[str, Any]) -> tuple[str, str]:
    message_id = str(message.get("id") or "")
    content = message.get("content") or []
    if not isinstance(content, list):
        return message_id, ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return message_id, "".join(parts)


def emit_text(text: str) -> None:
    if not text:
        return
    for line in text.splitlines() or [text]:
        if line:
            print(line, flush=True)


def emit_stream_event(event: dict[str, Any], state: dict[str, Any]) -> None:
    event_type = str(event.get("type") or "")
    if event_type == "assistant" and isinstance(event.get("message"), dict):
        message_id, text = extract_text_from_message(event["message"])
        if not text:
            return

        previous_text = state.setdefault("messages", {}).get(message_id, "")
        if text.startswith(previous_text):
            delta = text[len(previous_text):]
        elif text != previous_text:
            delta = text
        else:
            delta = ""
        state["messages"][message_id] = text
        if delta:
            state["emitted_text"] = True
            emit_text(delta)
        return

    if event_type in {"content_block_delta", "text_delta"}:
        delta = event.get("delta") or {}
        text = ""
        if isinstance(delta, dict):
            text = str(delta.get("text") or "")
        if text:
            state["emitted_text"] = True
            emit_text(text)
        return

    if event_type == "system" and event.get("subtype") == "init":
        print("[claude] 会话已启动", flush=True)
        return

    if event_type == "result" and not state.get("emitted_text"):
        emit_text(str(event.get("result") or ""))
        return

    if event_type == "error":
        message = event.get("error") or event.get("message") or event
        print(f"[claude:error] {message}", flush=True)


def stream_stderr(stderr) -> None:
    for line in stderr:
        normalized = line.rstrip("\r\n")
        if normalized:
            print(f"[claude:stderr] {normalized}", flush=True)


def run_claude(args: argparse.Namespace) -> int:
    workspace_dir = Path(args.workspace_dir).resolve()
    if not workspace_dir.is_dir():
        print(f"workspace directory not found: {workspace_dir}", file=sys.stderr, flush=True)
        return 2

    prompt = build_prompt(args)
    command = build_claude_argv(args, prompt)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(workspace_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        print(f"claude executable not found: {args.claude_bin}", file=sys.stderr, flush=True)
        return 127

    assert process.stdout is not None
    assert process.stderr is not None
    stderr_thread = threading.Thread(target=stream_stderr, args=(process.stderr,), daemon=True)
    stderr_thread.start()

    state: dict[str, Any] = {"messages": {}, "emitted_text": False}
    for raw_line in process.stdout:
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(line, flush=True)
            continue
        if isinstance(event, dict):
            emit_stream_event(event, state)

    returncode = process.wait()
    stderr_thread.join(timeout=1)
    return int(returncode or 0)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_models:
        for model in get_model_ids():
            print(model)
        return 0
    return run_claude(args)


if __name__ == "__main__":
    raise SystemExit(main())
