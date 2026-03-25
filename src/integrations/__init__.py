#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .agents import build_configured_agents
from .hubs import build_configured_hubs, register_builtin_hub_types


def register_builtin_integrations() -> None:
    register_builtin_hub_types()


__all__ = ["build_configured_agents", "build_configured_hubs", "register_builtin_integrations"]
