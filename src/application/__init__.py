#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .application import Application

__all__ = ["Application"]


def __getattr__(name: str):
    if name == "Application":
        from .application import Application

        return Application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
