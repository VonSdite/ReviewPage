#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件模块加载。"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path


def load_plugin_modules(modules: list[str], *, root_path: Path, logger) -> None:
    for entry in modules:
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (root_path / candidate).resolve()

        if candidate.exists():
            spec = importlib.util.spec_from_file_location(candidate.stem, candidate)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"无法加载插件文件：{candidate}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info("Plugin module loaded from file: %s", candidate)
            continue

        importlib.import_module(entry)
        logger.info("Plugin module loaded by name: %s", entry)
