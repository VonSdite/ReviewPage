#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""注册中心。"""

from __future__ import annotations

from typing import Callable


HubFactory = Callable[[object, str], object]
_HUB_TYPES: dict[str, HubFactory] = {}

def register_hub_type(hub_type: str, factory: HubFactory) -> None:
    if hub_type in _HUB_TYPES:
        return
    _HUB_TYPES[hub_type] = factory

def get_registered_hub_types() -> dict[str, HubFactory]:
    return dict(_HUB_TYPES)
