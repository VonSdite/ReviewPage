#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from src.repositories import ReviewRepository
from src.utils import create_connection_factory


class ReviewRepositoryTestCase(unittest.TestCase):
    def test_review_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.db"
            repository = ReviewRepository(create_connection_factory(db_path))

            created = repository.create_review(
                mr_url="https://gitlab.example.com/group/project/-/merge_requests/3",
                hub_id="gitlab",
                hub_name="GitLab Merge Request",
                agent_id="opencode",
                agent_name="OpenCode",
                model_id="provider/model-a",
            )
            self.assertEqual(created["status"], "pending")
            self.assertEqual(created["runtime_state"], "queued")

            claimed = repository.claim_next_pending_review()
            self.assertEqual(claimed["id"], created["id"])
            self.assertEqual(claimed["runtime_state"], "running")
            self.assertIsNotNone(claimed["started_at"])

            repository.update_execution_context(
                claimed["id"],
                command_line="opencode run --model provider/model-a /review url",
                working_directory="/tmp/review-3/repo",
                repo_url="https://gitlab.example.com/group/project.git",
                source_branch="feature/review-page",
                target_branch="main",
                title="Improve review queue",
                author_name="Von",
            )
            repository.append_review_log(claimed["id"], 1, "[system] started")
            repository.mark_review_completed(claimed["id"], "Review completed")

            detail = repository.get_review(claimed["id"])
            logs = repository.list_review_logs(claimed["id"])
            stats = repository.get_review_stats()
            paged = repository.list_reviews(page=1, page_size=10)

        self.assertEqual(detail["status"], "completed")
        self.assertEqual(detail["runtime_state"], "finished")
        self.assertEqual(detail["result_text"], "Review completed")
        self.assertEqual(logs[0]["line"], "[system] started")
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["running"], 0)
        self.assertEqual(paged["total"], 1)
        self.assertEqual(len(paged["records"]), 1)

    def test_list_reviews_supports_pagination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "review.db"
            repository = ReviewRepository(create_connection_factory(db_path))

            for index in range(5):
                repository.create_review(
                    mr_url=f"https://gitlab.example.com/group/project/-/merge_requests/{index + 1}",
                    hub_id="gitlab",
                    hub_name="GitLab Merge Request",
                    agent_id="opencode",
                    agent_name="OpenCode",
                    model_id=f"provider/model-{index + 1}",
                )

            first_page = repository.list_reviews(page=1, page_size=2)
            second_page = repository.list_reviews(page=2, page_size=2)

        self.assertEqual(first_page["total"], 5)
        self.assertEqual(len(first_page["records"]), 2)
        self.assertEqual(first_page["records"][0]["model_id"], "provider/model-5")
        self.assertEqual(second_page["records"][0]["model_id"], "provider/model-3")


if __name__ == "__main__":
    unittest.main()
