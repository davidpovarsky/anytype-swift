"""Focused controls for the original Release cleanup failure; no product execution."""
import argparse
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import coherent_heart_release as coherent
import coherent_release_cleanup as recovery
import run_owned_single_lane as supervisor
import run_t5_apple_pair as pair
import wave15_batch as batch
import test_wave15_batch as fixtures

PROFILE = batch.COHERENT_HEART_PROFILE
DEVICE = copy.deepcopy(fixtures.DEVICE)


def owned_receipt(root, name="boot"):
    root.mkdir(parents=True, exist_ok=True)
    path = root / (name + ".owned.command.json")
    row = dict(worker_pid=987654, owned_group_cleanup="TERM_THEN_KILL", status="COMPLETE",
               argv=["xcrun", "simctl", "boot", DEVICE["udid"]], cwd=str(root),
               return_code=0)
    batch.write(path, row)
    return path, row


def failed_projection(root):
    path, row = owned_receipt(root)
    projection = root / "boot.command.json"
    batch.write(projection, dict(status="FAILED_PROCESS_CLEANUP", argv=row["argv"],
        cwd=row["cwd"], return_code=0, controller_process_id=row["worker_pid"],
        owned_group_termination="TERM_THEN_KILL", original_owned_command=path.name,
        original_owned_command_sha256=batch.digest(path), cleanup_error_type="TimeoutExpired",
        cleanup_error="original ps inventory timed out", cleanup_probe_timeouts=[
            {"observation": 1, "timeout_seconds": 2}]))
    return path, projection


class ReleaseCleanupControls(unittest.TestCase):
    def test_coherent_probe_uses_remaining_ten_seconds_and_requires_actual_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _ = owned_receipt(Path(temporary))
            with patch.object(supervisor.time, "monotonic", side_effect=[0, 3]), \
                 patch.object(supervisor.subprocess, "check_output", return_value="1 1 Ss\n") as probe:
                actual = supervisor.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            self.assertEqual(probe.call_args.kwargs["timeout"], 7)
            self.assertEqual(actual["budget_seconds"], 10)
            self.assertEqual(actual["live_members"], 0)
            self.assertEqual(actual["observations"], 1)

    def test_coherent_timeout_does_not_reset_budget_or_imply_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _ = owned_receipt(Path(temporary))
            error = subprocess.TimeoutExpired(["ps"], 10)
            with patch.object(supervisor.time, "monotonic", side_effect=[0, 0, 10]), \
                 patch.object(supervisor.subprocess, "check_output", side_effect=error) as probe:
                with self.assertRaises(subprocess.TimeoutExpired) as failed:
                    supervisor.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            self.assertIs(failed.exception, error)
            self.assertEqual(probe.call_count, 1)
            self.assertEqual(error.timeout_observations, [{"observation": 1, "timeout_seconds": 10}])
            for kwargs in ({"cleanup_profile": "another-profile"}, {"cleanup_profile": PROFILE, "seconds": 11}):
                with self.assertRaises(RuntimeError):
                    supervisor.verify_owned_group_stopped(path, **kwargs)

    def test_coherent_actual_live_or_malformed_inventory_remains_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _ = owned_receipt(Path(temporary))
            for value in ("bad inventory", "555 987654 S\n"):
                with self.subTest(value=value), \
                     patch.object(supervisor.time, "monotonic", side_effect=[0, 0, 10, 10]), \
                     patch.object(supervisor.time, "sleep"), \
                     patch.object(supervisor.subprocess, "check_output", return_value=value):
                    with self.assertRaises(RuntimeError):
                        supervisor.verify_owned_group_stopped(path, cleanup_profile=PROFILE)

    def test_only_coherent_readiness_adapter_opts_into_longer_single_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); evidence = root / "evidence"; evidence.mkdir()
            device = {**DEVICE, "lane": "editor"}
            batch.write(evidence / "owned-simulator.json", device)
            context = replace(fixtures.frozen(root, device), profile=PROFILE)
            with patch("owned_simulator_readiness.ensure_ready") as ready, patch.object(pair, "run_logged") as logged:
                context.prepare_fresh_device(device["udid"], evidence)
                adapter = ready.call_args.kwargs["pair"]
                adapter.run_logged(["xcrun", "simctl", "boot", device["udid"]], root, evidence, "boot", 120)
                self.assertEqual(logged.call_args.kwargs, {"cleanup_profile": PROFILE})
                self.assertTrue(ready.call_args.kwargs["require_initial_shutdown"])

    def test_t5_projection_keeps_original_cleanup_error_and_each_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            error = subprocess.TimeoutExpired(["ps", "-axo", "pid=,pgid=,stat="], 10)
            error.timeout_observations = [{"observation": 1, "timeout_seconds": 10}]
            def worker(argv, cwd, output, timeout):
                output.write_text("original successful boot\n")
                row = dict(worker_pid=987654, owned_group_cleanup="TERM_THEN_KILL", status="COMPLETE",
                           argv=argv, cwd=str(cwd), return_code=0)
                batch.write(output.with_suffix(".command.json"), row)
                return row
            with patch.object(batch, "run_worker_command", side_effect=worker), \
                 patch.object(supervisor, "verify_owned_group_stopped", side_effect=error) as check:
                with self.assertRaises(subprocess.TimeoutExpired):
                    pair.run_logged(["xcrun", "simctl", "boot", DEVICE["udid"]], root, root,
                                    "boot", 120, cleanup_profile=PROFILE)
            projection = json.loads((root / "boot.command.json").read_bytes())
            original = root / projection["original_owned_command"]
            self.assertEqual(check.call_args.kwargs, {"cleanup_profile": PROFILE})
            self.assertEqual(projection["status"], "FAILED_PROCESS_CLEANUP")
            self.assertEqual(projection["cleanup_error"], str(error))
            self.assertEqual(projection["cleanup_probe_timeouts"], error.timeout_observations)
            self.assertEqual(projection["original_owned_command_sha256"], batch.digest(original))
            self.assertEqual(json.loads(original.read_bytes())["return_code"], 0)

    def test_nested_cleanup_rechecks_pinned_original_once_and_preserves_failed_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary); root = app / "owned"
            original, projection = failed_projection(root)
            before = {path: path.read_bytes() for path in (original, projection)}
            report = {"groups_checked": 0}
            with patch.object(supervisor, "verify_owned_group_stopped",
                              return_value={"status": "PASS", "live_members": 0, "pgid": 987654}) as probe:
                recovery.audit_nested_receipts([root], app, root, report)
            probe.assert_called_once_with(original.resolve(), cleanup_profile=PROFILE)
            self.assertEqual(report["groups_checked"], 1)
            self.assertEqual(report["original_owned_commands"][0]["projections"][0]["status"],
                             "FAILED_PROCESS_CLEANUP")
            for path, content in before.items(): self.assertEqual(path.read_bytes(), content)

    def test_nested_projection_rejects_escape_symlink_changed_hash_identity_or_command(self):
        mutations = [
            ("original_owned_command", "../boot.owned.command.json"),
            ("original_owned_command_sha256", "0" * 64),
            ("controller_process_id", 123456),
            ("argv", ["another", "command"]),
            ("cwd", "/another/work"),
            ("return_code", 9),
            ("owned_group_termination", "NONE"),
        ]
        for key, changed in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                app = Path(temporary); root = app / "owned"
                original, projection = failed_projection(root)
                row = json.loads(projection.read_bytes()); row[key] = changed; batch.write(projection, row)
                with patch.object(supervisor, "verify_owned_group_stopped") as probe, self.assertRaises(RuntimeError):
                    recovery.audit_nested_receipts([root], app, root, {})
                probe.assert_not_called()
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary); root = app / "owned"; original, projection = failed_projection(root)
            moved = root / "actual-original.json"; original.rename(moved); original.symlink_to(moved)
            with patch.object(supervisor, "verify_owned_group_stopped") as probe, self.assertRaises(RuntimeError):
                recovery.audit_nested_receipts([root], app, root, {})
            probe.assert_not_called()

    def test_nested_failed_reobservation_writes_failure_without_relabelling_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary); evidence = app / "evidence"; derived = app / "build/derived"
            root = evidence / "lanes/editor/owned-readiness"
            original, projection = failed_projection(root); before = projection.read_bytes()
            error = subprocess.TimeoutExpired(["ps"], 10)
            error.timeout_observations = [{"observation": 1, "timeout_seconds": 10}]
            args = argparse.Namespace(app=app, evidence=evidence, derived=derived)
            with patch.object(supervisor, "verify_owned_group_stopped", side_effect=error), \
                 self.assertRaises(subprocess.TimeoutExpired):
                coherent.nested_cleanup(args)
            result = json.loads((evidence / "coherent-nested-cleanup.json").read_bytes())
            self.assertEqual(result["status"], "FAIL"); self.assertEqual(result["groups_checked"], 0)
            self.assertEqual(result["original_owned_commands"][0]["timeout_observations"], error.timeout_observations)
            self.assertEqual(projection.read_bytes(), before)

    def clean(self, root, inventories, *, second_result=None, profile=PROFILE):
        clock = [0.0]; queries = []; actions = []
        error = subprocess.TimeoutExpired(["xcrun", "simctl", "delete", DEVICE["udid"]], 20)
        def query(device, *, timeout, observation):
            queries.append((copy.deepcopy(device), timeout))
            clock[0] += 118 if len(queries) == 1 else 4
            result = inventories[len(queries)-1]
            if isinstance(result, BaseException): raise result
            observation.update(status="RETURNED_VALID_SCOPED_INVENTORY", selector=device["udid"])
            return result
        def action(argv, **kwargs):
            actions.append((argv, kwargs["timeout"]))
            if len(actions) == 1:
                clock[0] += 20; raise error
            clock[0] += 1
            if isinstance(second_result, BaseException): raise second_result
            return second_result or subprocess.CompletedProcess(argv, 0)
        intent = dict(profile=profile, preflight_devices=[DEVICE], lane_devices=[], baseline_udids=[])
        patches = [patch.object(batch.time, "monotonic", side_effect=lambda: clock[0]),
                   patch.object(batch, "scoped_device_inventory", side_effect=query),
                   patch.object(batch.subprocess, "run", side_effect=action)]
        return intent, queries, actions, error, patches

    def test_timed_out_delete_is_only_qualified_by_actual_same_uuid_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent, queries, actions, error, patches = self.clean(root, [fixtures.inventory([DEVICE]), fixtures.inventory([])])
            with patches[0], patches[1], patches[2]:
                report = batch.cleanup_owned(intent, root)
            self.assertEqual(report["status"], "PASS"); self.assertEqual(len(actions), 1)
            self.assertEqual([q[0]["udid"] for q in queries], [DEVICE["udid"]]*2)
            self.assertEqual([q[1] for q in queries], [120, 42])
            detail = report["devices"][0]["delete_timeout_reconciliation"]
            self.assertEqual(detail["status"], "DELETION_PROVED_BY_ACTUAL_SCOPED_ABSENCE")
            self.assertEqual(detail["original_error"], str(error)); self.assertFalse(detail["deadline_reset"])
            self.assertNotIn("delete_exit_code", report["devices"][0])

    def test_present_owned_device_gets_only_one_bounded_revalidated_delete_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent, queries, actions, _, patches = self.clean(root, [fixtures.inventory([DEVICE])]*2)
            with patches[0], patches[1], patches[2]:
                report = batch.cleanup_owned(intent, root)
            self.assertEqual(actions, [(["xcrun", "simctl", "delete", DEVICE["udid"]], 20)]*2)
            detail = report["devices"][0]["delete_timeout_reconciliation"]
            self.assertEqual(detail["retry_commands"], 1)
            self.assertEqual(detail["revalidated_identity"]["udid"], DEVICE["udid"])

    def test_delete_reconciliation_rejects_changed_identity_and_does_not_retry(self):
        for field, value in [("name", "foreign"), ("deviceTypeIdentifier", "different"),
                             ("isAvailable", False), ("state", "Deleting")]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); changed = fixtures.inventory([DEVICE])
                changed["devices"][DEVICE["runtime"]["identifier"]][0][field] = value
                intent, _, actions, _, patches = self.clean(root, [fixtures.inventory([DEVICE]), changed])
                with patches[0], patches[1], patches[2], self.assertRaises(RuntimeError):
                    batch.cleanup_owned(intent, root)
                self.assertEqual(len(actions), 1)
                self.assertEqual(json.loads((root / "batch-cleanup.json").read_bytes())["status"], "FAIL")

    def test_failed_requery_or_second_delete_timeout_stays_failed_without_more_actions(self):
        for phase in ["query", "second-delete"]:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); failure = subprocess.TimeoutExpired(["fixture"], 4)
                inventories = [fixtures.inventory([DEVICE]),
                               failure if phase == "query" else fixtures.inventory([DEVICE])]
                intent, _, actions, _, patches = self.clean(root, inventories,
                    second_result=failure if phase == "second-delete" else None)
                with patches[0], patches[1], patches[2], self.assertRaises(subprocess.TimeoutExpired):
                    batch.cleanup_owned(intent, root)
                self.assertEqual(len(actions), 1 if phase == "query" else 2)
                report = json.loads((root / "batch-cleanup.json").read_bytes())
                self.assertEqual(report["status"], "FAIL")
                self.assertEqual(report["devices"][0]["delete_timeout_reconciliation"]["status"], "FAIL")

    def test_late_requery_or_retry_return_cannot_extend_original_cleanup_deadline(self):
        for late in ("requery", "retry"):
            with self.subTest(late=late):
                clock = [170]
                error = subprocess.TimeoutExpired(["xcrun", "simctl", "delete", DEVICE["udid"]], 20)
                def query(*args, **kwargs):
                    clock[0] = 181 if late == "requery" else 175
                    return fixtures.inventory([] if late == "requery" else [DEVICE])
                def action(*args, **kwargs):
                    clock[0] = 181
                    return subprocess.CompletedProcess(args[0], 0)
                entry = {}
                with patch.object(recovery.time, "monotonic", side_effect=lambda: clock[0]), \
                     patch.object(batch, "scoped_device_inventory", side_effect=query), \
                     patch.object(recovery.subprocess, "run", side_effect=action), \
                     self.assertRaisesRegex(RuntimeError, "cleanup budget exhausted"):
                    recovery.reconcile_delete_timeout(DEVICE, error, entry=entry,
                        report={"inventory_queries": []}, baseline_udids=[], deadline=180)
                self.assertEqual(entry["delete_timeout_reconciliation"]["status"], "FAIL")

    def test_expired_budget_baseline_uuid_or_noncoherent_profile_never_enables_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            error = subprocess.TimeoutExpired(["xcrun", "simctl", "delete", DEVICE["udid"]], 20)
            for baseline, clock in [([], 180), ([DEVICE["udid"]], 10)]:
                with self.subTest(baseline=baseline), patch.object(recovery.time, "monotonic", return_value=clock), \
                     patch.object(batch, "scoped_device_inventory") as query, self.assertRaises(RuntimeError):
                    recovery.reconcile_delete_timeout(DEVICE, error, entry={}, report={"inventory_queries": []},
                                                       baseline_udids=baseline, deadline=180)
                query.assert_not_called()
            intent, _, actions, _, patches = self.clean(root, [fixtures.inventory([DEVICE])], profile=batch.PROFILE)
            with patches[0], patches[1], patches[2], self.assertRaises(subprocess.TimeoutExpired):
                batch.cleanup_owned(intent, root)
            self.assertEqual(len(actions), 1)


if __name__ == "__main__":
    unittest.main()
