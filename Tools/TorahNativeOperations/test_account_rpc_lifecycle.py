"""Rejection controls for the lifecycle evidence gate; these are not native races."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_account_rpc_lifecycle as lane


def trace(stages, root="private-root", target="document"):
    values = []
    for index, stage in enumerate(stages, 1):
        identity = ("" if stage in {"app-lease-held", "stop-lock-attempt", "stop-lock-acquired"}
                    else root if stage.startswith("commit-") else target)
        qualifier = ("basic.Unlinkable" if stage.startswith("delete-lock-")
                     else "write" if stage in {"prelease", "append-native-return"} else "")
        values.append(dict(sequence=index, stage=stage, id=identity, qualifier=qualifier))
    return dict(events=values, counts={name: 1 for name in stages}, gate_timeouts=[])


def report():
    history = {"private-root": "a" * 64, "original-change": "b" * 64, "new-change": "c" * 64}
    return dict(protocol=lane.PROTOCOL, nonce="owned-invocation", pid=43210, heart_sha=lane.base.HEART,
                fixture_sha256=lane.CANDIDATE_SHA, status="PASS_THREE_REAL_ACCOUNT_BYTE_LIFECYCLE_CASES",
                account_stop_verified=True, instrumentation="SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT",
                **lane.LIMITS, cases={
        "delete_wins_first_add": dict(trace=trace(["prelease"]), request_sha256="1" * 64,
                                      response="TARGET_UNAVAILABLE_NO_RECEIPT", private_root="ABSENT"),
        "commit_wins_block_delete": dict(trace=trace(["commit-before-storage", "delete-lock-attempt",
                                                      "commit-after-storage", "delete-lock-acquired"]),
            request_sha256="2" * 64, raw_changes_sha256=history, heads=["new-change"], private_history_count=3,
            target_pointer_identity="EXACT_SAME_LIVE_SMARTBLOCK", post_delete_read_and_retry="TARGET_UNAVAILABLE_NO_RESULT"),
        "commit_wins_account_stop": dict(trace=trace(["app-lease-held", "commit-before-storage", "stop-lock-attempt",
                                                      "commit-after-storage", "append-native-return", "stop-lock-acquired"]),
            request_sha256="3" * 64, raw_changes_sha256_before_append={k: v for k, v in history.items() if k != "new-change"},
            heads_before_append=["original-change"], raw_changes_sha256_at_durable_boundary=dict(history),
            heads_at_durable_boundary=["new-change"], application_service_identity="EXACT_SAME_LIVE_INSTANCE",
            account_stop="PASS_ORIGINAL_STOP", after_stop_read_and_retry="NOT_LOGGED_IN_NO_RESULT")})


NATIVE_LOG = "=== RUN   " + lane.METHOD + "\n--- PASS: " + lane.METHOD + " (1.25s)\nPASS\n"


class LifecycleEvidenceGateTests(unittest.TestCase):
    def check(self, value):
        lane.validate_report(value, "owned-invocation", 43210)

    def test_exact_three_case_report_is_accepted_without_changing_original_evidence(self):
        value = report()
        original = deepcopy(value)
        self.check(value)
        self.assertEqual(value, original)

    def test_every_missing_case_and_extra_case_are_rejected(self):
        for name in lane.CASES:
            value = report()
            del value["cases"][name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                self.check(value)
        value = report()
        value["cases"]["claimed-other-case"] = deepcopy(value["cases"]["delete_wins_first_add"])
        with self.assertRaises(ValueError):
            self.check(value)

    def test_process_nonce_source_and_final_status_cannot_be_substituted(self):
        changes = {"pid": [43211, True], "nonce": ["other-invocation"], "heart_sha": ["f" * 40],
                   "fixture_sha256": ["e" * 64], "status": ["RUNNING", "SKIP", "FAIL"],
                   "account_stop_verified": [False, 1], "protocol": ["other-protocol"]}
        for name, values in changes.items():
            for mutation in values:
                value = report()
                value[name] = mutation
                with self.subTest(field=name, value=mutation), self.assertRaises(ValueError):
                    self.check(value)

    def test_each_unproved_scope_remains_explicit_and_cannot_be_promoted_to_pass(self):
        for key in lane.LIMITS:
            value = report()
            value[key] = "PASS"
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.check(value)

    def test_every_event_is_required_once_in_original_order_with_no_timeout(self):
        for name, case in report()["cases"].items():
            for index in range(len(case["trace"]["events"])):
                for mutation in ["missing", "duplicate", "wrong-stage", "wrong-sequence", "boolean-count", "timeout"]:
                    value = report()
                    observation = value["cases"][name]["trace"]
                    event = observation["events"][index]
                    if mutation == "missing":
                        observation["events"].pop(index)
                    elif mutation == "duplicate":
                        observation["events"].append(deepcopy(event))
                    elif mutation == "wrong-stage":
                        event["stage"] = "other-stage"
                    elif mutation == "wrong-sequence":
                        event["sequence"] = 0
                    elif mutation == "boolean-count":
                        observation["counts"][event["stage"]] = True
                    else:
                        observation["gate_timeouts"].append(event["stage"])
                    with self.subTest(case=name, index=index, mutation=mutation), self.assertRaises(ValueError):
                        self.check(value)

    def test_deletion_and_stop_cannot_use_foreign_objects_or_lock_interfaces(self):
        mutations = [
            ("commit_wins_block_delete", 3, "id", "other-document"),
            ("commit_wins_block_delete", 2, "id", "other-root"),
            ("commit_wins_block_delete", 1, "qualifier", "other.Interface"),
            ("commit_wins_account_stop", 3, "id", "other-root"),
            ("commit_wins_account_stop", 5, "id", "rpc-supplied-service"),
            ("commit_wins_account_stop", 4, "qualifier", "read")]
        for name, index, field, replacement in mutations:
            value = report()
            value["cases"][name]["trace"]["events"][index][field] = replacement
            with self.subTest(case=name, index=index, field=field), self.assertRaises(ValueError):
                self.check(value)
        for name, field in [("commit_wins_block_delete", "target_pointer_identity"),
                            ("commit_wins_account_stop", "application_service_identity")]:
            value = report()
            value["cases"][name][field] = "SAME_ID_DIFFERENT_INSTANCE"
            with self.subTest(case=name), self.assertRaises(ValueError):
                self.check(value)

    def test_both_original_signed_hashes_must_survive_the_account_stop_commit(self):
        for key in ["private-root", "original-change"]:
            for mutation in ["changed", "removed"]:
                value = report()
                history = value["cases"]["commit_wins_account_stop"]["raw_changes_sha256_at_durable_boundary"]
                if mutation == "changed":
                    history[key] = "f" * 64
                else:
                    del history[key]
                with self.subTest(key=key, mutation=mutation), self.assertRaises(ValueError):
                    self.check(value)

    def test_history_counts_and_heads_require_an_actual_new_commit(self):
        for heads in [[], ["private-root"], ["unrecorded-change"], ["new-change", "original-change"], ["original-change"]]:
            value = report()
            value["cases"]["commit_wins_account_stop"]["heads_at_durable_boundary"] = heads
            with self.subTest(heads=heads), self.assertRaises(ValueError):
                self.check(value)
        value = report()
        value["cases"]["commit_wins_block_delete"]["private_history_count"] = True
        with self.assertRaises(ValueError):
            self.check(value)

    def test_first_root_or_denial_receipt_cannot_be_substituted(self):
        mutations = [("delete_wins_first_add", "private_root", "PRESENT"),
                     ("delete_wins_first_add", "response", "CREATED"),
                     ("commit_wins_block_delete", "post_delete_read_and_retry", "CREATED"),
                     ("commit_wins_account_stop", "after_stop_read_and_retry", "ALREADY_EXISTS")]
        for name, key, replacement in mutations:
            value = report()
            value["cases"][name][key] = replacement
            with self.subTest(case=name, field=key), self.assertRaises(ValueError):
                self.check(value)

    def test_native_log_requires_the_original_named_pass_and_rejects_missing_duplicate_failed_or_skipped(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "native.log"
            path.write_text(NATIVE_LOG)
            lane.validate_test_log(path)
            for value in ["", NATIVE_LOG.replace(lane.METHOD, "OtherTest"), NATIVE_LOG + NATIVE_LOG,
                          NATIVE_LOG.replace("--- PASS:", "--- FAIL:"), NATIVE_LOG + "--- SKIP: OtherTest (0.0s)\n",
                          NATIVE_LOG.replace("\nPASS\n", "\n"), NATIVE_LOG.replace("=== RUN", "=== PAUSE")]:
                path.write_text(value)
                with self.subTest(log=value), self.assertRaises(ValueError):
                    lane.validate_test_log(path)


class LifecycleOwnershipAndSourceTests(unittest.TestCase):
    def make_work(self, directory):
        work = directory / "work"
        work.mkdir(mode=0o700)
        for name in ["ownership.json", "result.json", "lifecycle.json"]:
            (work / name).write_text("{}\n")
        (work / "native.log").write_text(NATIVE_LOG)
        secret = work / "sensitive-needles.private"
        secret.write_text(json.dumps(["synthetic-private-key-value", "synthetic-private-mnemonic-value"]))
        secret.chmod(0o600)
        return work

    def test_only_four_exact_secret_scanned_original_files_are_published(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            work = self.make_work(directory)
            (work / "account-root").mkdir()
            (work / "account-root/private-wallet").write_text("synthetic-private-key-value")
            (work / "unrecognized.log").write_text("unreviewed native data")
            expected = {name: (work / name).read_bytes() for name in ["ownership.json", "result.json", "lifecycle.json", "native.log"]}
            result = lane.preserve_evidence(work, directory / "published")
            self.assertEqual(result["secret_scan"], "PASS")
            self.assertEqual(set(result["files_sha256"]), set(expected))
            self.assertEqual({path.name: path.read_bytes() for path in (directory / "published").iterdir()}, expected)

    def test_missing_secret_inventory_withholds_all_native_output(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            work = self.make_work(directory)
            (work / "sensitive-needles.private").unlink()
            result = lane.preserve_evidence(work, directory / "published")
            self.assertEqual(result["secret_scan"], "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY")
            self.assertEqual(set(result["files_sha256"]), {"ownership.json", "result.json"})

    def test_secret_and_symlink_rejection_publish_no_partial_evidence(self):
        for mutation in ["secret-log", "secret-report", "symlink", "public-secret-inventory"]:
            with self.subTest(mutation=mutation), TemporaryDirectory() as temporary:
                directory = Path(temporary)
                work = self.make_work(directory)
                if mutation.startswith("secret-"):
                    target = work / ("native.log" if mutation == "secret-log" else "lifecycle.json")
                    target.write_text("synthetic-private-key-value")
                elif mutation == "symlink":
                    (work / "native.log").unlink()
                    (work / "native.log").symlink_to(work / "result.json")
                else:
                    (work / "sensitive-needles.private").chmod(0o644)
                with self.assertRaises(ValueError):
                    lane.preserve_evidence(work, directory / "published")
                self.assertFalse((directory / "published").exists())

    def test_nonzero_timeout_and_cancel_report_unknown_spawn_count_and_clean_only_owned_directory(self):
        errors = [ValueError("Native command failed"), subprocess.TimeoutExpired(["owned-child"], 330), KeyboardInterrupt()]
        for error in errors:
            with self.subTest(error=type(error).__name__), TemporaryDirectory() as temporary:
                directory = Path(temporary)
                binary = directory / "owned-binary"
                binary.write_bytes(b"controller-test-binary-not-native-acceptance")
                identity = dict(binary=str(binary), binary_sha256=lane.digest(binary))
                evidence = directory / "evidence"
                evidence.mkdir()
                unrelated = directory / "unrelated"
                unrelated.mkdir()
                (unrelated / "preserve").write_text("original")
                with patch.object(lane.base, "run_process", side_effect=error), \
                        patch.object(lane.shutil, "disk_usage", return_value=SimpleNamespace(free=2 * lane.base.RESERVE)), \
                        self.assertRaises(type(error)):
                    lane.run_races(identity, directory / "race-work", evidence, set())
                self.assertFalse((directory / "race-work").exists())
                self.assertEqual((unrelated / "preserve").read_text(), "original")
                cleanup = json.loads((evidence / "lifecycle-cleanup.json").read_text())
                self.assertTrue(cleanup["path_absent"])
                self.assertEqual(cleanup["status"], "PASS_REMOVED_OWNED_DISPOSABLE_ACCOUNT")
                self.assertIsNone(cleanup["process_exit_observed"])
                private = json.loads((evidence / "lifecycle-sequence/result.json").read_text())
                self.assertEqual(private["status"], "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL")
                self.assertTrue(private["launch_requested"])
                self.assertIsNone(private["native_processes"])
                self.assertIsNone(private["process_exit_observed"])
                self.assertNotIn("pid", private)

    def test_native_claim_without_original_secret_scanned_artifact_cannot_pass(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binary = directory / "owned-binary"
            binary.write_bytes(b"controller-test-binary-not-native-acceptance")
            identity = dict(binary=str(binary), binary_sha256=lane.digest(binary))
            evidence = directory / "evidence"
            evidence.mkdir()
            def fake_process(command, cwd, env, log, timeout):
                value = report()
                value["nonce"] = env["PINKHA_T2_LIFECYCLE_NONCE"]
                (cwd / "lifecycle.json").write_text(json.dumps(value))
                log.write_text(NATIVE_LOG)
                return value["pid"]
            with patch.object(lane.base, "run_process", side_effect=fake_process), \
                    patch.object(lane.shutil, "disk_usage", return_value=SimpleNamespace(free=2 * lane.base.RESERVE)), \
                    self.assertRaises(ValueError):
                lane.run_races(identity, directory / "race-work", evidence, set())
            self.assertFalse((directory / "race-work").exists())
            self.assertFalse((evidence / "lifecycle-sequence/lifecycle.json").exists())
            self.assertFalse((evidence / "lifecycle-sequence/native.log").exists())
            private = json.loads((evidence / "lifecycle-sequence/result.json").read_text())
            self.assertEqual(private["pid"], 43210)
            self.assertEqual(private["native_processes"], 1)
            self.assertTrue(private["process_exit_observed"])
            cleanup = json.loads((evidence / "lifecycle-cleanup.json").read_text())
            self.assertTrue(cleanup["process_exit_observed"])

    def test_every_reviewed_source_input_and_the_manifest_are_exactly_pinned(self):
        control = Path(__file__).resolve().parents[2]
        tools = control / "Tools/TorahNativeOperations"
        manifest_path = tools / "account_rpc_lifecycle_lane.json"
        manifest = json.loads(manifest_path.read_text())
        lane.source_inputs(control)
        with TemporaryDirectory() as temporary:
            copy = Path(temporary) / "control"
            target_tools = copy / "Tools/TorahNativeOperations"
            target_tools.mkdir(parents=True)
            names = [*manifest["base_inputs_sha256"], *manifest["candidate_inputs_sha256"]]
            for name in [*names, manifest_path.name]:
                destination = target_tools / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tools / name, destination)
            lane.source_inputs(copy)
            for name in [*names, manifest_path.name]:
                target = target_tools / name
                original = target.read_bytes()
                target.write_bytes(original + b"\ncontrol mutation\n")
                with self.subTest(path=name), self.assertRaises((ValueError, json.JSONDecodeError)):
                    lane.source_inputs(copy)
                target.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
