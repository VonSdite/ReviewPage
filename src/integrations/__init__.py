#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .agents.opencode_agent import register_opencode_agent
from .hubs.gitlab_hub import register_gitlab_hub


def register_builtin_integrations() -> None:
    register_opencode_agent()
    register_gitlab_hub()
