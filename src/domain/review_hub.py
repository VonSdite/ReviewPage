#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .review_models import MergeRequestTarget


class ReviewHub(ABC):
    hub_id: str

    @abstractmethod
    def supports_url(self, review_url: str) -> bool:
        """判断是否支持给定 MR 地址。"""

    @abstractmethod
    def resolve_review_target(self, review_url: str) -> MergeRequestTarget:
        """解析 MR 地址并返回代码仓与分支。"""

    def to_metadata(self) -> dict[str, str]:
        return {
            "id": self.hub_id,
        }
