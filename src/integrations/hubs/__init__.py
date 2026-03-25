"""Hub integrations."""

from __future__ import annotations

from ...domain import ReviewHub, get_registered_hub_types
from .gitlab_hub import GitLabReviewHub, register_gitlab_hub


def register_builtin_hub_types() -> None:
    register_gitlab_hub()


def build_configured_hubs(ctx: object) -> dict[str, ReviewHub]:
    hub_types = get_registered_hub_types()
    hubs: dict[str, ReviewHub] = {}
    for hub_id in ctx.config_manager.get_hub_ids():
        hub_config = ctx.config_manager.get_hub_config(hub_id)
        hub_type = str(hub_config.get("type") or "").strip()
        if not hub_type:
            raise ValueError(f"hubs.{hub_id}.type cannot be empty")

        factory = hub_types.get(hub_type)
        if factory is None:
            raise ValueError(f"未注册的 Hub 类型：{hub_type}")

        hubs[hub_id] = factory(ctx, hub_id)
    return hubs


__all__ = ["GitLabReviewHub", "build_configured_hubs", "register_builtin_hub_types"]
