import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.detectors.project import check_commands, detect_technology
from src.processor.engine import process
from src.queue.store import QueueStore, RepositoryRecord
from src.validators.safety import SafetyViolation, validate_change_paths, validate_push_command


class PipelineTests(unittest.TestCase):
    def test_sync_filters_archived_automation_and_assigns_positions(self):
        with TemporaryDirectory() as directory:
            store = QueueStore(Path(directory) / "repos.json")
            records = store.sync([
                {"id": 1, "name": "one", "full_name": "octo/one", "default_branch": "main", "archived": False},
                {"id": 2, "name": "old", "full_name": "octo/old", "default_branch": "main", "archived": True},
                {"id": 3, "name": "pipeline", "full_name": "octo/pipeline", "default_branch": "main", "archived": False},
            ], "octo/pipeline")
            self.assertEqual([record.full_name for record in records], ["octo/one"])
            self.assertEqual(records[0].queue_position, 1)
            self.assertEqual(store.next_eligible().name, "one")

    def test_new_repository_is_discovered_without_code_change(self):
        with TemporaryDirectory() as directory:
            store = QueueStore(Path(directory) / "repos.json")
            store.sync([{ "id": 1, "name": "first", "full_name": "octo/first", "default_branch": "main", "archived": False }], "octo/pipeline")
            store.sync([
                {"id": 1, "name": "first", "full_name": "octo/first", "default_branch": "main", "archived": False},
                {"id": 2, "name": "new", "full_name": "octo/new", "default_branch": "main", "archived": False},
            ], "octo/pipeline")
            self.assertEqual(len(store.load()["repositories"]), 2)

    def test_detector_and_check_commands(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}")
            (root / "tsconfig.json").write_text("{}")
            self.assertEqual(detect_technology(root), ["Node.js", "TypeScript"])
            self.assertEqual(check_commands(root, ["Node.js"])[0], ["npm", "test", "--if-present"])

    def test_dry_run_never_clones_or_pushes(self):
        record = RepositoryRecord("demo", 1, "octo/demo", "main")
        status, action = process(record, True, __import__("logging").getLogger("test"))
        self.assertEqual(status, "no_action_needed")
        self.assertIn("Dry run", action)

    def test_safety_gates(self):
        with self.assertRaises(SafetyViolation):
            validate_push_command(["git", "push", "--force"])
        with self.assertRaises(SafetyViolation):
            validate_change_paths([".env"])


if __name__ == "__main__":
    unittest.main()
