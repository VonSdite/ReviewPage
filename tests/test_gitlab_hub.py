#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from src.integrations.hubs.gitlab_hub import GitLabReviewHub


class _FakeConfigManager:
    def get_hub_config(self, hub_id):
        self._last_hub_id = hub_id
        return {
            "web_base_url": "https://gitlab.example.com",
            "api_base_url": "https://gitlab.example.com/api/v4",
            "private_token": "secret-token",
            "clone_url_preference": "http",
            "verify_ssl": True,
            "timeout_seconds": 10,
        }


class _FakeCtx:
    def __init__(self):
        self.logger = logging.getLogger("test.gitlab_hub")
        self.config_manager = _FakeConfigManager()
        self.root_path = Path(".")


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class GitLabHubTestCase(unittest.TestCase):
    def test_resolve_review_target_uses_source_project(self):
        hub = GitLabReviewHub(_FakeCtx())

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
        self.assertEqual(target.hub_id, "gitlab")

    def test_supports_url_matches_configured_host(self):
        hub = GitLabReviewHub(_FakeCtx())
        self.assertTrue(hub.supports_url("https://gitlab.example.com/group/project/-/merge_requests/1"))
        self.assertFalse(hub.supports_url("https://other.example.com/group/project/-/merge_requests/1"))


if __name__ == "__main__":
    unittest.main()
