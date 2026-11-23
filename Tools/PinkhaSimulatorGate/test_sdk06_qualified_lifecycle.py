"""New sdk06-qualified lifecycle/transport controls; no Apple commands are run."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

import coherent_original_preflight as lifecycle
import coherent_release_cleanup
import run_owned_single_lane as groups
import sdk06_qualified_continuation as current
import wave15_batch as batch
# Reuse fixture definitions only. No existing test method is loaded or executed.
from test_coherent_original_preflight import Machine, BINDING, PHONE, PAD, BASE, present

APP = Path(__file__).resolve().parents[2]


class SDKMachine(Machine):
    def factory(self, control, directory, receipt, checkpoint, *, clock, profile):
        assert profile == "sdk06-qualified"
        return lifecycle.Commands(control, directory, receipt, checkpoint, clock=clock,
            execute=self.execute, stopped=self.stopped, profile=profile)

    def stopped(self, path, *, cleanup_profile):
        assert cleanup_profile == "sdk06-qualified"
        self.group_calls.append(path)
        return dict(status="PASS", live_members=0, pgid=601)


class QualifiedLifecycleControls(unittest.TestCase):
    def test_explicit_sdk_quiescence_uses_same_ten_seconds_and_rejects_late_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "owned.command.json"
            path.write_text(json.dumps(dict(worker_pid=92001, owned_group_cleanup="TERM_THEN_KILL")))
            for final, expected in [(4.0, "PASS"), (11.0, "FAIL_DEADLINE")]:
                with self.subTest(final=final), mock.patch.object(groups.time, "monotonic", side_effect=[0.0, 1.0, 2.0, 3.0, final]), \
                     mock.patch.object(groups.os, "killpg", return_value=None), \
                     mock.patch.object(groups.subprocess, "check_output", return_value="") as query:
                    if expected == "PASS":
                        result = groups.verify_owned_group_stopped(path, cleanup_profile="sdk06-qualified")
                        self.assertEqual(result["status"], expected)
                    else:
                        with self.assertRaises(RuntimeError) as caught:
                            groups.verify_owned_group_stopped(path, cleanup_profile="sdk06-qualified")
                        self.assertEqual(caught.exception.quiescence_observation["status"], expected)
                        self.assertEqual(caught.exception.quiescence_observation["live_members"], 0)
                    self.assertEqual(query.call_args.kwargs["timeout"], 7)
            with self.assertRaises(RuntimeError):
                groups.verify_owned_group_stopped(path, cleanup_profile="arbitrary")

    def test_sdk_supervisor_preserves_first_failure_and_late_group_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp)
            primary = subprocess.TimeoutExpired(["synthetic-worker"], 6300)
            late = RuntimeError("synthetic late zero")
            late.timeout_observations = [{"observation": 1, "timeout_seconds": 10}]
            late.quiescence_observation = dict(status="FAIL_DEADLINE", live_members=0, pgid=92001)
            def execute(argv, cwd, path, timeout):
                path.write_text("synthetic worker timeout")
                path.with_suffix(".command.json").write_text(json.dumps(dict(argv=argv, worker_pid=92001,
                    return_code=-9, owned_group_cleanup="TERM_THEN_KILL")))
                raise primary
            with mock.patch.object(groups.owned, "run_worker_command", side_effect=execute), \
                 mock.patch.object(groups, "verify_owned_group_stopped", side_effect=late) as stopped, \
                 mock.patch("builtins.print"), \
                 mock.patch.object(current, "cleanup", return_value={"status": "PASS"}) as cleanup:
                code = groups.supervise(["synthetic-worker"], evidence, evidence, context=BINDING,
                    cleanup=lambda: cleanup(evidence, evidence), cleanup_profile="sdk06-qualified")
            self.assertEqual(code, 1)
            observed = json.loads((evidence / "single-lane-supervisor.json").read_text())
            self.assertEqual(observed["status"], "TIMED_OUT")
            self.assertEqual(observed["error_type"], "TimeoutExpired")
            self.assertEqual(observed["owned_group_quiescence"]["timeout_observations"], late.timeout_observations)
            self.assertEqual(observed["owned_group_quiescence"]["quiescence_observation"], late.quiescence_observation)
            self.assertEqual(stopped.call_args.kwargs["cleanup_profile"], "sdk06-qualified")
            cleanup.assert_called_once()

    def test_sdk_journal_uses_own_protocol_and_never_reuses_coherent_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); machine = SDKMachine(root)
            with mock.patch.dict(os.environ, {"GITHUB_ENV": str(root / "job.env")}):
                prepared = lifecycle.prepare(root, root, BINDING, factory=machine.factory,
                    host=lambda: None, clock=lambda: machine.time, profile="sdk06-qualified")
            self.assertEqual(prepared["status"], "PREFLIGHT_PASS_UI_NOT_RUN")
            self.assertEqual(prepared["protocol"], lifecycle.SDK_PROTOCOL)
            intent, known, attempted = lifecycle.admitted_journal(root / "preflight", BINDING, profile="sdk06-qualified")
            self.assertEqual(intent["profile"], "sdk06-qualified")
            self.assertEqual((attempted, {row["udid"] for row in known}), (2, {PHONE, PAD}))
            with self.assertRaises(RuntimeError): lifecycle.admitted_journal(root / "preflight", BINDING)
            seen = []
            def policy(actual_intent, directory):
                seen.append(actual_intent)
                result = dict(status="PASS", devices=[dict(udid=row["udid"], status="DELETED_OWNED_SIMULATOR")
                                                     for row in known])
                lifecycle.save(directory / "batch-cleanup.json", result, original=True)
                return result
            with mock.patch.object(lifecycle.subprocess, "check_output", return_value=BINDING["source_sha"] + "\n"), \
                 mock.patch.object(lifecycle, "prior_batch_cleanup", side_effect=AssertionError("coherent borrowing")) as prior:
                result = lifecycle.cleanup(root, root, BINDING, policy=policy, host=lambda: None,
                    profile="sdk06-qualified")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(seen[0]["profile"], "sdk06-qualified")
            self.assertEqual(result["known_owned_udids"], [PHONE, PAD])
            self.assertEqual(result["prior_batch_cleanup_admission"]["status"],
                             "SDK_PROFILE_REQUIRES_ITS_OWN_JOURNAL_CLEANUP")
            prior.assert_not_called()

    def test_sdk_delete_timeout_routes_same_owner_and_original180_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            device = dict(name="Pinkha-UI27-Synthetic-ipad", udid=PAD,
                          runtime={"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0"},
                          device={"identifier": "pad-type"})
            intent = dict(profile="sdk06-qualified", baseline_udids=[BASE],
                          preflight_devices=[device], lane_devices=[])
            timeout = subprocess.TimeoutExpired(["xcrun", "simctl", "delete", PAD], 20)
            seen = []
            def reconcile(actual, error, *, entry, report, baseline_udids, deadline):
                seen.append((actual, error, baseline_udids, deadline))
                entry["delete_timeout_reconciliation"] = {"status": "SYNTHETIC_SAME_OWNED_UUID_CONTROL"}
            with mock.patch.object(batch, "scoped_device_inventory", return_value=present(device)), \
                 mock.patch.object(batch.subprocess, "run", side_effect=timeout) as command, \
                 mock.patch.object(batch.time, "monotonic", side_effect=[0, 1, 2, 3]), \
                 mock.patch.object(coherent_release_cleanup, "reconcile_delete_timeout", side_effect=reconcile):
                result = batch.cleanup_owned(intent, root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(seen, [(device, timeout, [BASE], 180)])
            self.assertEqual(command.call_args.args[0], ["xcrun", "simctl", "delete", PAD])
            self.assertEqual(command.call_args.kwargs["timeout"], 20)

    def test_sdk_cleanup_rejects_delete_success_after_original_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            device = dict(name="Pinkha-UI27-Synthetic-ipad", udid=PAD,
                          runtime={"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0"},
                          device={"identifier": "pad-type"})
            intent = dict(profile="sdk06-qualified", baseline_udids=[BASE],
                          preflight_devices=[device], lane_devices=[])
            with mock.patch.object(batch, "scoped_device_inventory", return_value=present(device)), \
                 mock.patch.object(batch.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                 mock.patch.object(batch.time, "monotonic", side_effect=[0, 1, 2, 181]):
                with self.assertRaises(RuntimeError): batch.cleanup_owned(intent, root)
            report = json.loads((root / "batch-cleanup.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["devices"][0]["delete_exit_code"], 0)
            self.assertEqual(report["devices"][0]["udid"], PAD)

    def test_later_ui_archive_survives_exact_transport_and_other_archives_stay_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); derived = root / "derived"; evidence = root / "evidence"
            products = derived / "Build/Products"; products.mkdir(parents=True)
            evidence.mkdir()
            (products / "Synthetic.xctestrun").write_bytes(b"original descriptor")
            executable = products / "SyntheticRunner.app/SyntheticRunner"
            executable.parent.mkdir(); executable.write_bytes(b"original runner executable"); executable.chmod(0o755)
            receipt = current.capture_later_ui(derived, evidence, source_sha="c" * 40,
                run_id="999000001", run_attempt="1", build_flags=["synthetic-control-only"])
            archive = evidence / receipt["archive_path"]; manifest = evidence / receipt["manifest_path"]
            self.assertEqual(receipt["archive_path"], "sdk06-ui/sdk06-early-products/BuildProducts.tar.gz")
            self.assertEqual(current.owned.digest(archive), receipt["archive_sha256"])
            self.assertEqual(current.owned.digest(manifest), receipt["manifest_sha256"])
            self.assertFalse(receipt["acceptance_reused"])
            (evidence / "unapproved.tar.gz").write_bytes(archive.read_bytes())
            result = subprocess.run([__import__("sys").executable, "-B",
                str(APP / "Tools/PinkhaNativeDerived/package_evidence.py"), str(evidence)],
                capture_output=True, text=True, timeout=15, check=True)
            with zipfile.ZipFile(evidence / "Pinkha-Native-Derived-Evidence.zip") as packed:
                self.assertEqual(packed.read(receipt["archive_path"]), archive.read_bytes())
                self.assertEqual(packed.read(receipt["manifest_path"]), manifest.read_bytes())
                self.assertNotIn("unapproved.tar.gz", packed.namelist())

    def test_workflow_admits_before_build_and_cannot_repeat_five_qualified_control_files(self):
        source = (APP / ".github/workflows/pinkha-sdk06-qualified-continuation.yml").read_text()
        self.assertIn("workflow_call: {}", source); self.assertIn("workflow_dispatch: {}", source)
        for forbidden in ("test_hanlin_ui_runtime.py", "test_hanlin_acceptance_evidence.py",
            "test_text_native_ack.py", "test_shared_editor_existing_build.py",
            "test_acceptance_continuation_branch.py", "build_custom_heart.py", "go test", "cache/save"):
            self.assertNotIn(forbidden, source)
        self.assertLess(source.index("sdk06_qualified_continuation.py admit"), source.index("actions/cache/restore"))
        self.assertIn("--source-run-id 45091223011", source)
        self.assertIn(current.CACHE_KEY, source)
        self.assertEqual(source.count("if: always()"), 3)


if __name__ == "__main__":
    unittest.main()
