"""New controls for explicit current evidence roots and original coherent cwd."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

import coherent_heart_release as coherent
import coherent_original_products as original
import run_t5_apple_pair as pair
import wave15_batch as batch


class OriginalProductsNestedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pinkha-original-nested-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.control = self.root / "control"
        self.app = self.control / "build/current/private/App"
        self.evidence = self.control / "build/current/evidence"
        self.derived = self.app / "build/derived"
        self.derived.mkdir(parents=True)
        self.evidence.mkdir(parents=True)
        self.args = SimpleNamespace(control=self.control, app=self.app,
                                    evidence=self.evidence, derived=self.derived)
        self.origin = original.ContinuationOrigin.__new__(original.ContinuationOrigin)
        self.origin.args = self.args
        self.origin.control = self.control
        self.origin.app = self.app
        self.origin.evidence = self.evidence
        self.origin.control_sha = "a" * 40
        self.env = mock.patch.dict(os.environ, {
            "GITHUB_RUN_ID": "45111287072", "GITHUB_RUN_ATTEMPT": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.control_check = mock.patch.object(self.origin, "verify_control", return_value={})
        self.control_check.start()
        self.addCleanup(self.control_check.stop)
        intent = self.origin.bind_intent({
            "run_id": "45111287072", "run_attempt": "1",
            "profile": batch.COHERENT_HEART_PROFILE})
        batch.write(self.evidence / "batch-intent.json", intent)
        self.readiness = self.evidence / "lanes/editor/owned-readiness"
        self.readiness.mkdir(parents=True)

    def test_current_fixed_roots_reject_foreign_origin_symlink_and_forged_cwd(self):
        command = self.readiness / "probe.owned.command.json"
        projected = self.readiness / "probe.command.json"
        data = dict(worker_pid=800000001, argv=["owned-fixture-command"],
                    cwd=str(self.app), return_code=0, status="COMPLETE",
                    owned_group_cleanup="TERM_THEN_KILL")
        batch.write(command, data)
        projection = dict(argv=data["argv"], cwd=data["cwd"], return_code=0,
                          controller_process_id=data["worker_pid"], status="SUCCESS",
                          owned_group_termination="TERM_THEN_KILL",
                          original_owned_command=command.name,
                          original_owned_command_sha256=batch.digest(command))
        batch.write(projected, projection)
        original_bytes = command.read_bytes()
        archived = self.evidence / "original-products/originals/lanes/editor/owned-readiness"
        archived.mkdir(parents=True)
        (archived / "old.command.json").write_text("not current command evidence")
        state = dict(status="PASS", live_members=0, pgid=data["worker_pid"],
                     budget_seconds=10, observations=1, timeout_observations=[])
        with mock.patch("run_owned_single_lane.verify_owned_group_stopped", return_value=state) as stopped:
            result = coherent.nested_cleanup(self.args, origin=self.origin)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["groups_checked"], 1)
            stopped.assert_called_once_with(command, cleanup_profile=coherent.PROFILE)
            rows = json.loads((self.evidence / "coherent-nested-cleanup.json").read_text())
            self.assertEqual(rows["original_owned_commands"][0]["path"],
                             command.relative_to(self.control).as_posix())
            self.assertEqual(command.read_bytes(), original_bytes)
            stopped.reset_mock()
            with self.assertRaisesRegex(RuntimeError, "escaped the owned App"):
                coherent.nested_cleanup(self.args)
            stopped.assert_not_called()
            foreign_args = SimpleNamespace(**vars(self.args))
            with self.assertRaisesRegex(RuntimeError, "arguments differ"):
                coherent.nested_cleanup(foreign_args, origin=self.origin)
            intent_path = self.evidence / "batch-intent.json"
            current_intent = intent_path.read_bytes()
            wrong = json.loads(current_intent)
            wrong["run_id"] = "45095838065"
            batch.write(intent_path, wrong)
            with self.assertRaisesRegex(RuntimeError, "worker intent differs"):
                coherent.nested_cleanup(self.args, origin=self.origin)
            intent_path.write_bytes(current_intent)
            external = self.root / "foreign-evidence"
            external.mkdir()
            (external / "batch-intent.json").write_bytes(current_intent)
            self.args.evidence = self.origin.evidence = external
            try:
                with self.assertRaisesRegex(RuntimeError, "separately owned"):
                    coherent.nested_cleanup(self.args, origin=self.origin)
            finally:
                self.args.evidence = self.origin.evidence = self.evidence
            moved = self.readiness.with_name("retained-current-originals")
            self.readiness.rename(moved)
            self.readiness.symlink_to(external, target_is_directory=True)
            try:
                with self.assertRaisesRegex(RuntimeError, "escaped the owned App"):
                    coherent.nested_cleanup(self.args, origin=self.origin)
            finally:
                self.readiness.unlink()
                moved.rename(self.readiness)
            projection["cwd"] = str(external)
            batch.write(projected, projection)
            with self.assertRaisesRegex(RuntimeError, "projection differs"):
                coherent.nested_cleanup(self.args, origin=self.origin)
            self.assertEqual(command.read_bytes(), original_bytes)
            stopped.assert_not_called()

    def test_future_coherent_original_records_actual_cwd_without_changing_default(self):
        command = [sys.executable, "-c", "import os; print(os.getcwd())"]
        with mock.patch.object(batch, "run_worker_command", wraps=batch.run_worker_command) as launched:
            pair.run_logged(command, self.app, self.readiness, "actual", 5,
                            cleanup_profile=coherent.PROFILE)
            self.assertEqual(launched.call_args.kwargs, {"record_cwd": True})
        original_path = self.readiness / "actual.owned.command.json"
        projected_path = self.readiness / "actual.command.json"
        raw = original_path.read_bytes()
        original_record = json.loads(raw)
        projected = json.loads(projected_path.read_bytes())
        self.assertEqual(original_record["cwd"], str(self.app))
        self.assertEqual(projected["cwd"], original_record["cwd"])
        self.assertEqual((self.readiness / "actual.log").read_text().strip(), str(self.app))
        self.assertEqual(projected["original_owned_command_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(projected["owned_group_quiescence"]["live_members"], 0)
        nested = coherent.nested_cleanup(self.args, origin=self.origin)
        self.assertEqual(nested["status"], "PASS")
        self.assertEqual(nested["groups_checked"], 1)
        self.assertEqual(original_path.read_bytes(), raw)
        default_dir = self.evidence / "ordinary-command-outside-fixed-nested-roots"
        with mock.patch.object(batch, "run_worker_command", wraps=batch.run_worker_command) as launched:
            pair.run_logged(command, self.app, default_dir, "ordinary", 5)
            self.assertEqual(launched.call_args.kwargs, {})
        ordinary = json.loads((default_dir / "ordinary.owned.command.json").read_bytes())
        self.assertNotIn("cwd", ordinary)
        self.assertEqual(ordinary["return_code"], 0)
        self.assertEqual(original_record["return_code"], 0)
        self.assertNotEqual(ordinary["worker_pid"], original_record["worker_pid"])
        retained = os.environ.get("PINKHA_NESTED_REPAIR_CONTROL_EVIDENCE")
        if retained:
            destination = Path(retained) / "actual-owned-commands"
            destination.mkdir(parents=True, exist_ok=False)
            for source, name in [
                (original_path, "coherent.owned.command.json"),
                (projected_path, "coherent.command.json"),
                (self.readiness / "actual.log", "coherent.log"),
                (self.evidence / "coherent-nested-cleanup.json", "coherent-nested-cleanup.json"),
                (default_dir / "ordinary.owned.command.json", "ordinary.owned.command.json"),
                (default_dir / "ordinary.command.json", "ordinary.command.json"),
                (default_dir / "ordinary.log", "ordinary.log"),
            ]:
                shutil.copyfile(source, destination / name)
        print("COHERENT_ORIGINAL_CWD_CONTROL " + json.dumps({
            "coherentOwnedPID": original_record["worker_pid"],
            "coherentReturnCode": original_record["return_code"],
            "originalSHA256": hashlib.sha256(raw).hexdigest(),
            "originalCwdMatchesActualProcess": True,
            "originalBytesUnchangedAfterNestedCleanup": True,
            "nestedGroupsChecked": 1,
            "nestedCleanup": nested["status"],
            "defaultOwnedPID": ordinary["worker_pid"],
            "defaultOriginalCwdFieldAbsent": True,
            "productTestsExecuted": 0,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    unittest.main()
