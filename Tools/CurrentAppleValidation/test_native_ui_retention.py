"""Real process-group and journal controls for completed-root retention."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import retain_native_ui as r

class RetentionOwnershipControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.context = {"profile": "native-ui-failed", "runID": "control"}
    def tearDown(self):
        self.directory.cleanup()
    def record(self, pgid, context=None):
        path = self.root / "owned.started.json"
        path.write_text(json.dumps({"context": context or self.context, "pgid": pgid}))
        return path
    def test_completed_actual_process_group_is_retained_as_absent(self):
        process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
        process.wait(timeout=10)
        self.record(process.pid)
        result = r.absent_groups(self.root, self.context)
        self.assertEqual(result[0]["kernelObservation"], "ABSENT_ESRCH")
    def test_live_actual_owned_process_group_refuses_retention(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
        try:
            self.record(process.pid)
            with self.assertRaisesRegex(RuntimeError, "still_exists"):
                r.absent_groups(self.root, self.context)
        finally:
            process.terminate()
            process.wait(timeout=10)
    def test_foreign_context_cannot_grant_ownership(self):
        self.record(2, {"runID": "foreign"})
        with self.assertRaisesRegex(ValueError, "foreign_command_context"):
            r.absent_groups(self.root, self.context)
    def test_symlink_journal_cannot_grant_ownership(self):
        target = self.root / "other.json"
        target.write_text(json.dumps({"context": self.context, "pgid": 2}))
        (self.root / "owned.started.json").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "nonregular"):
            r.absent_groups(self.root, self.context)

if __name__ == "__main__":
    unittest.main()
