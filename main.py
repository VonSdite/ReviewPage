#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.application import Application


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review Page Service")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Configuration file path",
    )
    return parser.parse_args()


def app() -> "Application":
    args = parse_args()
    project_root = Path(__file__).resolve().parent

    if args.config is None:
        config_path = project_root / "config.yaml"
    else:
        candidate = Path(args.config)
        config_path = candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    from src.application import Application

    return Application(config_path)


def main() -> None:
    app().run()


if __name__ == "__main__":
    main()
