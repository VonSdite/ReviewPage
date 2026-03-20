#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""注册中心。"""

from __future__ import annotations

from typing import Callable


AgentFactory = Callable[[object], object]
HubFactory = Callable[[object], object]

_AGENT_FACTORIES: dict[str, AgentFactory] = {}
_HUB_FACTORIES: dict[str, HubFactory] = {}


def register_agent_factory(agent_id: str, factory: AgentFactory) -> None:
    if agent_id in _AGENT_FACTORIES:
        return
    _AGENT_FACTORIES[agent_id] = factory


def register_hub_factory(hub_id: str, factory: HubFactory) -> None:
    if hub_id in _HUB_FACTORIES:
        return
    _HUB_FACTORIES[hub_id] = factory


def get_registered_agent_factories() -> dict[str, AgentFactory]:
    return dict(_AGENT_FACTORIES)


def get_registered_hub_factories() -> dict[str, HubFactory]:
    return dict(_HUB_FACTORIES)
