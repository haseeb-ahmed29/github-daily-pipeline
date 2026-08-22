import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.queue.store import QueueStore


def repo(repo_id: int, name: str):
    return {"id": repo_id, "name": name, "full_name": f"octo/{name}", "default_branch": "main", "archived": False}


class RotationTests(unittest.TestCase):
    def make_store(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return QueueStore(Path(directory.name) / "repos.json")

    def test_first_repository(self):
        store = self.make_store()
        records = store.sync([repo(1, "one"), repo(2, "two"), repo(3, "three")], "octo/pipeline")
        self.assertEqual(store.select_for_day("2026-08-23").full_name, "octo/one")
        self.assertEqual([r.queue_position for r in records], [1, 2, 3])

    def test_next_repository(self):
        store = self.make_store()
        store.sync([repo(1, "one"), repo(2, "two"), repo(3, "three")], "octo/pipeline")
        first = store.select_for_day("2026-08-23")
        store.begin_run(first, "2026-08-23")
        store.finish_run(first, "no_action_needed", "No approved update", "2026-08-23")
        self.assertEqual(store.select_for_day("2026-08-24").full_name, "octo/two")

    def test_last_repository_and_loop_back(self):
        store = self.make_store()
        store.sync([repo(1, "one"), repo(2, "two")], "octo/pipeline")
        first = store.select_for_day("2026-08-23")
        store.begin_run(first, "2026-08-23")
        store.finish_run(first, "no_action_needed", "No approved update", "2026-08-23")
        second = store.select_for_day("2026-08-24")
        store.begin_run(second, "2026-08-24")
        store.finish_run(second, "no_action_needed", "No approved update", "2026-08-24")
        self.assertEqual(store.select_for_day("2026-08-25").full_name, "octo/one")

    def test_new_repository_is_appended(self):
        store = self.make_store()
        store.sync([repo(1, "one"), repo(2, "two")], "octo/pipeline")
        store.sync([repo(1, "one"), repo(2, "two"), repo(3, "new")], "octo/pipeline")
        records = store.load()["repositories"]
        self.assertEqual([(r["full_name"], r["queue_position"]) for r in records], [("octo/one", 1), ("octo/two", 2), ("octo/new", 3)])

    def test_repository_already_processed_today_is_not_selected_twice(self):
        store = self.make_store()
        store.sync([repo(1, "one")], "octo/pipeline")
        selected = store.select_for_day("2026-08-23")
        store.begin_run(selected, "2026-08-23")
        store.finish_run(selected, "no_action_needed", "No approved update", "2026-08-23")
        self.assertIsNone(store.select_for_day("2026-08-23"))

    def test_failed_repository_advances_rotation(self):
        store = self.make_store()
        store.sync([repo(1, "one"), repo(2, "two")], "octo/pipeline")
        selected = store.select_for_day("2026-08-23")
        store.begin_run(selected, "2026-08-23")
        store.record_failure(selected, "2026-08-23", "Processing failed", "test failure")
        self.assertEqual(store.select_for_day("2026-08-24").full_name, "octo/two")

    def test_three_failures_require_manual_review(self):
        store = self.make_store()
        store.sync([repo(1, "one")], "octo/pipeline")
        selected = store.select_for_day("2026-08-23")
        for day in ["2026-08-23", "2026-08-24", "2026-08-25"]:
            if day != "2026-08-23":
                selected = store.select_for_day(day)
            store.begin_run(selected, day)
            store.record_failure(selected, day, "Processing failed", "test failure")
        saved = store.load()["repositories"][0]
        self.assertTrue(saved["manual_review"])
        self.assertEqual(saved["failure_count"], 3)

    def test_empty_repository_list(self):
        store = self.make_store()
        self.assertEqual(store.sync([], "octo/pipeline"), [])
        self.assertIsNone(store.select_for_day("2026-08-23"))


if __name__ == "__main__":
    unittest.main()
