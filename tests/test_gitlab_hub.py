#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from src.integrations.hubs import build_configured_hubs, register_builtin_hub_types
from src.integrations.hubs.gitlab_hub import GitLabReviewHub


class _FakeConfigManager:
    def __init__(self, hub_configs=None):
        self._hub_configs = hub_configs or {
            "gitlab-primary": {
                "type": "gitlab",
                "web_base_url": "https://gitlab.example.com",
                "api_base_url": "https://gitlab.example.com/api/v4",
                "private_token": "secret-token",
                "clone_url_preference": "http",
                "verify_ssl": True,
                "timeout_seconds": 10,
            }
        }

    def get_hub_ids(self):
        return list(self._hub_configs)

    def get_hub_config(self, hub_id):
        self._last_hub_id = hub_id
        return dict(self._hub_configs[hub_id])


class _FakeCtx:
    def __init__(self, hub_configs=None):
        self.logger = logging.getLogger("test.gitlab_hub")
        self.config_manager = _FakeConfigManager(hub_configs=hub_configs)
        self.root_path = Path(".")


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class GitLabHubTestCase(unittest.TestCase):
    def test_build_configured_hubs_supports_multiple_gitlab_instances(self):
        register_builtin_hub_types()
        ctx = _FakeCtx(
            hub_configs={
                "gitlab-public": {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.example.com",
                    "api_base_url": "https://gitlab.example.com/api/v4",
                },
                "gitlab-internal": {
                    "type": "gitlab",
                    "web_base_url": "https://gitlab.intra.example.com",
                    "api_base_url": "https://gitlab.intra.example.com/api/v4",
                },
            }
        )

        hubs = build_configured_hubs(ctx)

        self.assertEqual(sorted(hubs), ["gitlab-internal", "gitlab-public"])
        self.assertTrue(all(isinstance(hub, GitLabReviewHub) for hub in hubs.values()))

    def test_resolve_review_target_uses_source_project(self):
        hub = GitLabReviewHub(_FakeCtx(), "gitlab-primary")

        with patch("src.integrations.hubs.gitlab_hub.requests.get") as mocked_get:
            mocked_get.side_effect = [
                _FakeResponse(
                    200,
                    {
                        "title": "Improve review queue",
                        "source_project_id": 9001,
                        "source_branch": "feature/review-page",
                        "target_branch": "main",
                        "author": {"name": "Von"},
                        "web_url": "https://gitlab.example.com/group/project/-/merge_requests/12",
                    },
                ),
                _FakeResponse(
                    200,
                    {
                        "http_url_to_repo": "https://gitlab.example.com/group/project.git",
                        "ssh_url_to_repo": "git@gitlab.example.com:group/project.git",
                    },
                ),
            ]

            target = hub.resolve_review_target(
                "https://gitlab.example.com/group/project/-/merge_requests/12"
            )

        self.assertEqual(target.repo_url, "https://gitlab.example.com/group/project.git")
        self.assertEqual(target.source_branch, "feature/review-page")
        self.assertEqual(target.target_branch, "main")
        self.assertEqual(target.author_name, "Von")
        self.assertEqual(target.hub_id, "gitlab-primary")

    def test_supports_url_matches_configured_host(self):
        hub = GitLabReviewHub(_FakeCtx(), "gitlab-primary")
        self.assertTrue(hub.supports_url("https://gitlab.example.com/group/project/-/merge_requests/1"))
        self.assertFalse(hub.supports_url("https://other.example.com/group/project/-/merge_requests/1"))


if __name__ == "__main__":
    unittest.main()
