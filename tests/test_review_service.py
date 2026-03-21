#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.domain import AgentModelCatalog, MergeRequestTarget, ModelChoice, ReviewCommandSpec
from src.repositories import ReviewRepository
from src.services.review_service import ReviewService
from src.utils import create_connection_factory


class _FakeConfigManager:
    def __init__(self, temp_root="/tmp/review-service-tests"):
        self._temp_root = temp_root

    def get_default_agent_id(self):
        return "opencode"

    def get_default_hub_id(self):
        return "gitlab"

    def get_workspace_temp_root(self):
        return self._temp_root


class _FakeCtx:
    def __init__(self, temp_root="/tmp/review-service-tests"):
        self.logger = logging.getLogger("test.review_service")
        self.config_manager = _FakeConfigManager(temp_root=temp_root)


class _FakeAgent:
    agent_id = "opencode"

    def get_model_catalog(self):
        return AgentModelCatalog(models=[ModelChoice(model_id="provider/model-a")], source="test")

    def build_review_command(self, *, model, review_url, workspace_dir):
        return ReviewCommandSpec(argv=["echo", model, review_url, workspace_dir], env={})

    def to_metadata(self):
        return {
            "id": self.agent_id,
            "name": self.agent_id,
            "models": [{"id": "provider/model-a", "label": "provider/model-a"}],
            "model_source": "test",
            "model_error": None,
        }


class _FakeHub:
    hub_id = "gitlab"

    def supports_url(self, review_url):
        return review_url.startswith("https://gitlab.example.com/")

    def resolve_review_target(self, review_url):
        raise NotImplementedError

    def to_metadata(self):
        return {"id": self.hub_id, "name": self.hub_id}


class _ResolvableFakeHub(_FakeHub):
    def resolve_review_target(self, review_url):
        return MergeRequestTarget(
            hub_id="gitlab",
            review_url=review_url,
            repo_url="https://gitlab.example.com/group/project.git",
            source_branch="feature/review-page",
            target_branch="main",
        )


class ReviewServiceTestCase(unittest.TestCase):
    def test_list_reviews_returns_pagination_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ReviewRepository(create_connection_factory(Path(tmpdir) / "review.db"))
            service = ReviewService(
                _FakeCtx(),
                review_repository=repository,
                agents={"opencode": _FakeAgent()},
                hubs={"gitlab": _FakeHub()},
            )

            for index in range(5):
                service.create_review(
                    {
                        "mr_url": f"https://gitlab.example.com/group/project/-/merge_requests/{index + 1}",
                        "hub_id": "gitlab",
                        "agent_id": "opencode",
                        "model_id": "provider/model-a",
                    }
                )

            second_page = service.list_reviews(page=2, page_size=2)
            overflow_page = service.list_reviews(page=9, page_size=2)

        self.assertEqual(second_page["pagination"]["page"], 2)
        self.assertEqual(second_page["pagination"]["page_size"], 2)
        self.assertEqual(second_page["pagination"]["total"], 5)
        self.assertEqual(second_page["pagination"]["total_pages"], 3)
        self.assertTrue(second_page["pagination"]["has_prev"])
        self.assertTrue(second_page["pagination"]["has_next"])
        self.assertEqual(len(second_page["records"]), 2)

        self.assertEqual(overflow_page["pagination"]["page"], 3)
        self.assertFalse(overflow_page["pagination"]["has_next"])
        self.assertEqual(len(overflow_page["records"]), 1)

    def test_retry_review_creates_new_pending_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ReviewRepository(create_connection_factory(Path(tmpdir) / "review.db"))
            service = ReviewService(
                _FakeCtx(),
                review_repository=repository,
                agents={"opencode": _FakeAgent()},
                hubs={"gitlab": _FakeHub()},
            )

            first = service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/11",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )
            retried = service.retry_review(first["id"])

        self.assertIsNotNone(retried)
        assert retried is not None
        self.assertNotEqual(first["id"], retried["id"])
        self.assertEqual(retried["mr_url"], first["mr_url"])
        self.assertEqual(retried["hub_id"], first["hub_id"])
        self.assertEqual(retried["agent_id"], first["agent_id"])
        self.assertEqual(retried["model_id"], first["model_id"])
        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["runtime_state"], "queued")

    def test_retry_review_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repository = ReviewRepository(create_connection_factory(Path(tmpdir) / "review.db"))
            service = ReviewService(
                _FakeCtx(),
                review_repository=repository,
                agents={"opencode": _FakeAgent()},
                hubs={"gitlab": _FakeHub()},
            )

            result = service.retry_review(9999)

        self.assertIsNone(result)

    def test_execute_review_always_deletes_workspace_on_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir) / "workspaces"
            repository = ReviewRepository(create_connection_factory(Path(tmpdir) / "review.db"))
            service = ReviewService(
                _FakeCtx(temp_root=str(temp_root)),
                review_repository=repository,
                agents={"opencode": _FakeAgent()},
                hubs={"gitlab": _ResolvableFakeHub()},
            )

            service.create_review(
                {
                    "mr_url": "https://gitlab.example.com/group/project/-/merge_requests/11",
                    "hub_id": "gitlab",
                    "agent_id": "opencode",
                    "model_id": "provider/model-a",
                }
            )

            class _FakeResult:
                def __init__(self, returncode, output):
                    self.returncode = returncode
                    self.output = output

            with patch("src.services.review_service.stream_command") as mocked_stream_command:
                mocked_stream_command.side_effect = [
                    _FakeResult(0, "clone ok"),
                    _FakeResult(1, "review failed"),
                ]
                handled = service.execute_next_review()
                self.assertTrue(handled)
                self.assertTrue(temp_root.exists())
                self.assertEqual(list(temp_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
