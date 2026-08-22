import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.pipeline import QueueStore, RepositoryRecord, detect_technology, process_repository


class FakeClient:
    pass


class PipelineTests(unittest.TestCase):
    def test_sync_filters_archived_and_automation_repo(self):
        with TemporaryDirectory() as directory:
            store = QueueStore(Path(directory) / "queue.json")
            records = store.sync_repositories([
                {"id": 1, "name": "one", "full_name": "octo/one", "default_branch": "main", "archived": False},
                {"id": 2, "name": "old", "full_name": "octo/old", "default_branch": "main", "archived": True},
                {"id": 3, "name": "pipeline", "full_name": "octo/pipeline", "default_branch": "main", "archived": False},
            ], "octo/pipeline")
            self.assertEqual([record.full_name for record in records], ["octo/one"])

    def test_new_repositories_are_pending_and_next_is_oldest(self):
        with TemporaryDirectory() as directory:
            store = QueueStore(Path(directory) / "queue.json")
            store.sync_repositories([
                {"id": 1, "name": "first", "full_name": "octo/first", "default_branch": "main", "archived": False},
                {"id": 2, "name": "second", "full_name": "octo/second", "default_branch": "main", "archived": False},
            ], "octo/pipeline")
            self.assertEqual(store.next_eligible().name, "first")

    def test_detect_technology(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}")
            (root / "tsconfig.json").write_text("{}")
            self.assertEqual(detect_technology(root), ["Node.js", "TypeScript"])

    def test_dry_run_never_clones_or_pushes(self):
        record = RepositoryRecord("demo", 1, "octo/demo", "main")
        status, action = process_repository(record, FakeClient(), True, __import__("logging").getLogger("test"))
        self.assertEqual(status, "no_action_needed")
        self.assertIn("Dry run", action)

    def test_store_round_trip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            store = QueueStore(path)
            record = RepositoryRecord("demo", 1, "octo/demo", "main")
            store.save({"repositories": [record.__dict__], "runs": []})
            self.assertEqual(json.loads(path.read_text())["repositories"][0]["name"], "demo")


if __name__ == "__main__":
    unittest.main()
