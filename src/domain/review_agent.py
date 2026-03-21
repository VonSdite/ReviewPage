#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .review_models import AgentModelCatalog, ReviewCommandSpec


class ReviewAgent(ABC):
    agent_id: str

    @abstractmethod
    def get_model_catalog(self) -> AgentModelCatalog:
        """返回当前 Agent 可用模型列表。"""

    @abstractmethod
    def build_review_command(self, *, model: str, review_url: str, workspace_dir: str) -> ReviewCommandSpec:
        """构建单次检视任务命令。"""

    def to_metadata(self) -> dict[str, object]:
        catalog = self.get_model_catalog()
        return {
            "id": self.agent_id,
            "name": self.agent_id,
            "models": [item.to_dict() for item in catalog.models],
            "model_source": catalog.source,
            "model_error": catalog.error,
        }
