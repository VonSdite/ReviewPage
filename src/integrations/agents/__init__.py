"""Agent integrations."""

from __future__ import annotations

from .config_driven_agent import ConfigDrivenReviewAgent


def build_config_driven_agents(ctx: object) -> dict[str, ConfigDrivenReviewAgent]:
    return {
        agent_id: ConfigDrivenReviewAgent(ctx, agent_id)
        for agent_id in ctx.config_manager.get_agent_ids()
    }


__all__ = ["ConfigDrivenReviewAgent", "build_config_driven_agents"]
