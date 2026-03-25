"""Agent integrations."""

from __future__ import annotations

from .configured_agent import ConfiguredReviewAgent


def build_configured_agents(ctx: object) -> dict[str, ConfiguredReviewAgent]:
    return {
        agent_id: ConfiguredReviewAgent(ctx, agent_id)
        for agent_id in ctx.config_manager.get_agent_ids()
    }


__all__ = ["ConfiguredReviewAgent", "build_configured_agents"]
