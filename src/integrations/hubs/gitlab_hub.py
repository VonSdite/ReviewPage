#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Request Hub 实现。"""

from __future__ import annotations

import re
from urllib.parse import quote, urlparse

import requests

from ...domain import MergeRequestTarget, ReviewHub, register_hub_type


GITLAB_MR_PATTERN = re.compile(r"^(?P<project>.+?)(?:/-)?/merge_requests/(?P<iid>\d+)(?:$|/)")


class GitLabReviewHub(ReviewHub):
    hub_type = "gitlab"

    def __init__(self, ctx: object, hub_id: str):
        self._ctx = ctx
        self._logger = ctx.logger
        self.hub_id = str(hub_id or "").strip()
        if not self.hub_id:
            raise ValueError("hub_id cannot be empty")
        self._config = ctx.config_manager.get_hub_config(self.hub_id)
        self._web_base_url = str(self._config.get("web_base_url") or "").rstrip("/")
        self._api_base_url = str(self._config.get("api_base_url") or "").rstrip("/")
        self._private_token = str(self._config.get("private_token") or "").strip()
        self._clone_url_preference = str(self._config.get("clone_url_preference") or "http").strip().lower()
        self._verify_ssl = bool(self._config.get("verify_ssl", True))
        self._timeout_seconds = max(float(self._config.get("timeout_seconds", 20)), 1.0)

    def supports_url(self, review_url: str) -> bool:
        if not self._web_base_url:
            return True
        try:
            review_host = urlparse(review_url).netloc
            base_host = urlparse(self._web_base_url).netloc
            return bool(review_host) and review_host == base_host
        except Exception:
            return False

    def resolve_review_target(self, review_url: str) -> MergeRequestTarget:
        if self._web_base_url and not self.supports_url(review_url):
            raise ValueError(f"Hub API基地址与MR地址不同， 不支持该MR：{review_url}")

        project_path, merge_request_iid = self._parse_merge_request_url(review_url)
        merge_request = self._get_json(
            f"/projects/{quote(project_path, safe='')}/merge_requests/{merge_request_iid}"
        )

        source_project_id = merge_request.get("source_project_id") or merge_request.get("project_id")
        if not source_project_id:
            raise RuntimeError("API 未返回 source_project_id")

        project = self._get_json(f"/projects/{source_project_id}")
        repo_url = self._pick_repo_url(project)
        source_branch = str(merge_request.get("source_branch") or "").strip()
        target_branch = str(merge_request.get("target_branch") or "").strip()

        if not repo_url or not source_branch:
            raise RuntimeError("MR 信息不完整，缺少仓库地址或 source branch")

        author = merge_request.get("author") or {}
        author_name = author.get("name") or author.get("username")
        web_url = merge_request.get("web_url") or review_url

        return MergeRequestTarget(
            hub_id=self.hub_id,
            review_url=review_url,
            repo_url=repo_url,
            source_branch=source_branch,
            target_branch=target_branch,
            title=merge_request.get("title"),
            author_name=author_name,
            web_url=web_url,
        )

    def _parse_merge_request_url(self, review_url: str) -> tuple[str, str]:
        parsed = urlparse(review_url)
        path = parsed.path.lstrip("/")
        matched = GITLAB_MR_PATTERN.match(path)
        if not matched:
            raise ValueError(f"无法解析 Merge Request 地址：{review_url}")
        project_path = matched.group("project").strip("/")
        iid = matched.group("iid")
        return project_path, iid

    def _pick_repo_url(self, project: dict[str, object]) -> str:
        http_url = str(project.get("http_url_to_repo") or "").strip()
        ssh_url = str(project.get("ssh_url_to_repo") or "").strip()
        if self._clone_url_preference == "ssh":
            return ssh_url or http_url
        return http_url or ssh_url

    def _get_json(self, api_path: str) -> dict[str, object]:
        if not self._api_base_url:
            raise ValueError("Hub 缺少 api_base_url 配置")

        headers = {}
        if self._private_token:
            headers["PRIVATE-TOKEN"] = self._private_token

        url = f"{self._api_base_url}{api_path}"
        response = requests.get(
            url,
            headers=headers,
            timeout=self._timeout_seconds,
            verify=self._verify_ssl,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"API 请求失败：{response.status_code} {response.text.strip()}")

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("API 返回了非对象结构")
        return payload


def register_gitlab_hub() -> None:
    register_hub_type(GitLabReviewHub.hub_type, GitLabReviewHub)
