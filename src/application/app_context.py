#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用上下文。"""

from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import ConfigManager

if TYPE_CHECKING:
    from flask import Flask


@dataclass(frozen=True)
class AppContext:
    logger: Logger
    config_manager: ConfigManager
    root_path: Path
    flask_app: "Flask"
