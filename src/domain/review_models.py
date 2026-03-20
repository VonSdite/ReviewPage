#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelChoice:
    model_id: str
    label: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.model_id,
            "label": self.label or self.model_id,
        }


@dataclass(frozen=True)
class AgentModelCatalog:
    models: list[ModelChoice]
    source: str
    error: str | None = None


@dataclass(frozen=True)
class ReviewCommandSpec:
    argv: list[str]
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeRequestTarget:
    hub_id: str
    review_url: str
    repo_url: str
    source_branch: str
    target_branch: str
    title: str | None = None
    author_name: str | None = None
    web_url: str | None = None
