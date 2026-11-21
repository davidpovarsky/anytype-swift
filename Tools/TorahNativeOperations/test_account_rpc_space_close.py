"""Evidence rejection, ownership and failure controls; not native acceptance."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import run_account_rpc_space_close as lane

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("space_close_materializer_controls",
                                            HERE / "account_rpc_space_close/materialize_test_overlay.py")
materializer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materializer)
LOG = "=== RUN   " + lane.METHOD + "\n--- PASS: " + lane.METHOD + " (12.34s)\nPASS\n"


def reports():
    before = {"private-root": "a" * 64, "original-change": "b" * 64}
    durable = {**before, "new-change": "c" * 64}
    stages = ["lease-settings-held", "append-before-native", "cache-entry-closing-target",
              "cache-entry-closing-private", "cache-deadline-target", "cache-deadline-private",
              "client-cache-close-return", "settings-close-attempt", "commit-before-storage",
              "commit-after-storage", "lease-before-release", "settings-close-return",
              "native-storage-close-attempt", "native-storage-close-return", "client-space-close-return"]
    event_ids = ["settings", "private-root", "document", "private-root", "document", "private-root", "space",
                 "settings", "private-root", "private-root", "settings", "settings", "space", "space", "space"]
    events = [dict(sequence=index, stage=stage, id=identity, result=lane.STAGES[stage])
              for index, (stage, identity) in enumerate(zip(stages, event_ids), 1)]
    common = dict(protocol=lane.PROTOCOL, heart_sha=lane.base.HEART, fixture_sha256=lane.CANDIDATE_SHA,
        status="PASS_ORIGINAL_NATIVE_SPACE_CLOSE_PHASE", account_id="account", space_id="space", target_id="document",
        block_id="block", private_root_id="private-root", request_sha256="d" * 64, state_sha256="e" * 64,
        created_claim_id="new-claim", created_change_id="new-change", account_stop_verified=True,
        app_shutdown_verified=True, instrumentation="SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT", **lane.LIMITS)
    race = dict(**common, phase="race", nonce="race-nonce", pid=1234, observation=dict(
        trace=dict(events=events, counts={s: 1 for s in stages}, gate_timeouts=[], gate_cancellations=[], overflow=False),
        identity_checks="ALL_EIGHT_PAIRS_EXACT_SAME_LIVE_INSTANCE", cache_close_timeout_seconds=10,
        both_entries_closing_before_controller_close=True, settings_fence_observed_before_and_after_durable_commit=True,
        post_physical_close_read="DENIED_WITH_LIVE_PROBE_CONTEXT", native_append="CREATED_ORIGINAL_RESPONSE",
        original_controller_close_calls=1, raced_generated_append_calls=1,
        raw_changes_sha256_before_append=before, heads_before_append=["original-change"],
        raw_changes_sha256_at_durable_boundary=durable, heads_at_durable_boundary=["new-change"]))
    reopen = dict(**common, phase="reopen", nonce="reopen-nonce", pid=1235, observation=dict(
        raw_changes_sha256_before_retry=deepcopy(durable), heads_before_retry=["new-change"],
        raw_changes_sha256_after_retry=deepcopy(durable), heads_after_retry=["new-change"],
        read_before_retry="TWO_EXACT_PERSISTED_CLAIMS_LOCAL_VERIFIED_TREE",
        original_byte_retry="ALREADY_EXISTS_SAME_PAYLOAD_NO_CHANGE_ID",
        read_after_retry="PROTO_EQUAL_INCLUDING_LOCAL_WATERMARK", original_request_forwards=1))
    return race, reopen


class NativeEvidenceControls(unittest.TestCase):
    def test_frozen_controller_imports_and_every_native_fixture_match_exact_source_inventory(self):
        value = lane.source_inputs(HERE.parents[1])
        self.assertEqual(value["candidate_sha256"], lane.CANDIDATE_SHA)
        self.assertEqual(len(value["files_sha256"]), 23)

    def check(self, report):
        phase = report["phase"]
        lane.validate_report(report, phase, phase + "-nonce", 1234 if phase == "race" else 1235)

    def test_two_original_phase_reports_are_accepted_without_rewriting_evidence(self):
        values = reports()
        original = deepcopy(values)
        for value in values:
            self.check(value)
        lane.validate_pair(*values)
        self.assertEqual(values, original)

    def test_concurrent_cache_deadlines_may_arrive_in_either_order(self):
        race, _ = reports()
        events = race["observation"]["trace"]["events"]
        events[4], events[5] = events[5], events[4]
        for index, event in enumerate(events, 1):
            event["sequence"] = index
        self.check(race)

    def test_source_process_nonce_and_terminal_state_cannot_be_substituted(self):
        mutations = {"pid": [999, True], "nonce": ["foreign"], "heart_sha": ["f" * 40],
                     "fixture_sha256": ["f" * 64], "status": ["RUNNING", "SKIP", "FAIL"],
                     "account_stop_verified": [False, 1], "app_shutdown_verified": [False, 1],
                     "instrumentation": ["SHIPPED_PRODUCT"], "protocol": ["foreign"]}
        for phase in range(2):
            for key, values in mutations.items():
                for value in values:
                    report = reports()[phase]
                    report[key] = value
                    with self.subTest(phase=phase, key=key, value=value), self.assertRaises(ValueError):
                        self.check(report)

    def test_scope_limits_cannot_be_promoted_to_unproved_acceptance(self):
        for phase in range(2):
            for key in lane.LIMITS:
                value = reports()[phase]
                value[key] = "PASS"
                with self.subTest(phase=phase, key=key), self.assertRaises(ValueError):
                    self.check(value)

    def test_every_native_event_is_required_once_without_timeout_or_cancellation(self):
        for index in range(15):
            for mutation in ["missing", "duplicate", "wrong-result", "wrong-id", "bool-count", "bool-sequence",
                             "timeout", "cancel", "overflow"]:
                value = reports()[0]
                trace = value["observation"]["trace"]
                event = trace["events"][index]
                if mutation == "missing":
                    trace["events"].pop(index)
                elif mutation == "duplicate":
                    trace["events"].append(deepcopy(event))
                elif mutation == "wrong-result":
                    event["result"] = "FOREIGN"
                elif mutation == "wrong-id":
                    event["id"] = "foreign-object"
                elif mutation == "bool-count":
                    trace["counts"][event["stage"]] = True
                elif mutation == "bool-sequence":
                    event["sequence"] = True
                elif mutation == "timeout":
                    trace["gate_timeouts"].append(event["stage"])
                elif mutation == "cancel":
                    trace["gate_cancellations"].append(event["stage"])
                else:
                    trace["overflow"] = True
                with self.subTest(event=index, mutation=mutation), self.assertRaises(ValueError):
                    self.check(value)

    def test_every_required_lifetime_and_durable_commit_order_is_checked(self):
        for sequence in lane.ORDERS:
            for left, right in zip(sequence, sequence[1:]):
                value = reports()[0]
                events = value["observation"]["trace"]["events"]
                a = next(i for i, e in enumerate(events) if e["stage"] == left)
                b = next(i for i, e in enumerate(events) if e["stage"] == right)
                events[a], events[b] = events[b], events[a]
                for index, event in enumerate(events, 1):
                    event["sequence"] = index
                with self.subTest(left=left, right=right), self.assertRaises(ValueError):
                    self.check(value)

    def test_no_same_id_different_instance_or_substitute_close_claim(self):
        mutations = {"identity_checks": "SAME_ID_ONLY", "cache_close_timeout_seconds": 1,
                     "both_entries_closing_before_controller_close": False,
                     "settings_fence_observed_before_and_after_durable_commit": False,
                     "post_physical_close_read": "CONTEXT_CANCELLED", "native_append": "SYNTHETIC_RESPONSE",
                     "original_controller_close_calls": 2, "raced_generated_append_calls": True}
        for key, replacement in mutations.items():
            value = reports()[0]
            value["observation"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(value)

    def test_new_commit_preserves_both_original_signed_history_entries(self):
        for entry in ["private-root", "original-change"]:
            for change in ["remove", "mutate"]:
                value = reports()[0]
                history = value["observation"]["raw_changes_sha256_at_durable_boundary"]
                if change == "remove":
                    del history[entry]
                else:
                    history[entry] = "f" * 64
                with self.subTest(entry=entry, change=change), self.assertRaises(ValueError):
                    self.check(value)

    def test_reused_missing_or_multiple_durable_heads_are_rejected(self):
        for heads in [[], ["private-root"], ["original-change"], ["other"], ["new-change", "original-change"]]:
            value = reports()[0]
            value["observation"]["heads_at_durable_boundary"] = heads
            with self.subTest(heads=heads), self.assertRaises(ValueError):
                self.check(value)

    def test_exact_retry_cannot_change_history_or_skip_watermark_equality(self):
        mutations = [("original_byte_retry", "CREATED"), ("read_before_retry", "UNVERIFIED_TREE"),
                     ("read_after_retry", "HEADS_ONLY"), ("original_request_forwards", 2)]
        for key, replacement in mutations:
            value = reports()[1]
            value["observation"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(value)
        value = reports()[1]
        value["observation"]["raw_changes_sha256_after_retry"]["new-change"] = "f" * 64
        with self.assertRaises(ValueError):
            self.check(value)

    def test_cold_reopen_cannot_substitute_account_request_claim_state_or_durable_bytes(self):
        for key in ["account_id", "space_id", "target_id", "block_id", "private_root_id", "request_sha256",
                    "state_sha256", "created_claim_id", "created_change_id", "heart_sha", "fixture_sha256"]:
            race, reopen = reports()
            reopen[key] = "foreign"
            with self.subTest(key=key), self.assertRaises(ValueError):
                lane.validate_pair(race, reopen)
        race, reopen = reports()
        reopen["observation"]["raw_changes_sha256_before_retry"]["new-change"] = "f" * 64
        with self.assertRaises(ValueError):
            lane.validate_pair(race, reopen)

    def test_cold_reopen_must_use_distinct_process_and_nonce(self):
        for key in ["pid", "nonce"]:
            race, reopen = reports()
            reopen[key] = race[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                lane.validate_pair(race, reopen)

    def test_original_test_log_rejects_skips_failures_missing_or_extra_invocations(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "native.log"
            path.write_text(LOG)
            lane.validate_test_log(path)
            for text in [LOG.replace("--- PASS:", "--- SKIP:"), LOG.replace("--- PASS:", "--- FAIL:"),
                         LOG + LOG, LOG.replace("PASS\n", ""), LOG + "--- PASS: Other (1.0s)\n", "PASS\n"]:
                path.write_text(text)
                with self.subTest(log=text), self.assertRaises(ValueError):
                    lane.validate_test_log(path)


class ProcessAndEvidenceControls(unittest.TestCase):
    def simulate_phase(self, command, cwd, env, log, timeout, entry, checkpoint):
        """Controller-only synthetic output; never used by the native lane."""
        phase = env["PINKHA_T2_SPACE_CLOSE_PHASE"]
        value = reports()[0 if phase == "race" else 1]
        state = b"owned synthetic controller state"
        if phase == "race":
            (cwd / "state.json").write_bytes(state)
            (cwd / "sensitive-needles.private").write_text(json.dumps(["private-key", "private-mnemonic"]))
            (cwd / "sensitive-needles.private").chmod(0o600)
            (cwd / "account-key.private").write_text("private-key")
            (cwd / "race-trace.json").write_text(json.dumps(value["observation"]["trace"]))
        value["nonce"] = env["PINKHA_T2_SPACE_CLOSE_NONCE"]
        value["state_sha256"] = hashlib.sha256(state).hexdigest()
        (cwd / (phase + ".json")).write_text(json.dumps(value))
        log.write_text(LOG)
        entry.update(pid=value["pid"], status="PASS_EXIT_0", exit_code=0,
                     launch_requested=True, process_exit_observed=True)
        checkpoint()
        return value["pid"]

    def sequence_inputs(self, root):
        binary = root / "synthetic-binary"
        binary.write_bytes(b"controller fixture only")
        evidence = root / "evidence"
        evidence.mkdir()
        return {"binary": str(binary), "binary_sha256": lane.digest(binary)}, evidence

    def test_two_phase_controller_retains_only_allowed_evidence_and_removes_owned_private_account(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, evidence = self.sequence_inputs(root)
            work = root / "owned-sequence"
            with patch.object(lane, "run_owned", side_effect=self.simulate_phase), patch.object(lane.base, "RESERVE", 0):
                result = lane.run_sequence(identity, work, evidence, {100, 101, 102, 103})
            self.assertEqual(result["actual_counts"], {"native_processes": 2, "passing_test_invocations": 2})
            self.assertFalse(work.exists())
            self.assertFalse(list(evidence.rglob("*.private")))
            self.assertFalse(list(evidence.rglob("state.json")))
            cleanup = json.loads((evidence / "space-close-cleanup.json").read_text())
            self.assertEqual(cleanup["status"], "PASS_REMOVED_OWNED_DISPOSABLE_ACCOUNT")

    def test_second_phase_failure_retains_first_result_and_observed_failed_process(self):
        def fail_reopen(command, cwd, env, log, timeout, entry, checkpoint):
            if env["PINKHA_T2_SPACE_CLOSE_PHASE"] == "race":
                return self.simulate_phase(command, cwd, env, log, timeout, entry, checkpoint)
            entry.update(pid=1235, status="FAIL", exit_code=7, launch_requested=True, process_exit_observed=True)
            log.write_text("original failed cold process diagnostic")
            checkpoint()
            raise RuntimeError("original native failure")

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, evidence = self.sequence_inputs(root)
            work = root / "owned-sequence"
            with patch.object(lane, "run_owned", side_effect=fail_reopen), patch.object(lane.base, "RESERVE", 0):
                with self.assertRaisesRegex(RuntimeError, "original native failure"):
                    lane.run_sequence(identity, work, evidence, set())
            result = json.loads((evidence / "space-close-sequence/result.json").read_text())
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["actual_counts"], {"native_processes": 2, "passing_test_invocations": 1})
            self.assertEqual(result["phases"][1]["exit_code"], 7)
            self.assertEqual(result["phases"][1]["report_qualification"], "NOT_RUN")
            self.assertFalse(work.exists())

    def test_invalid_original_phase_report_records_failed_qualification_after_observed_exit(self):
        def wrong_report(command, cwd, env, log, timeout, entry, checkpoint):
            pid = self.simulate_phase(command, cwd, env, log, timeout, entry, checkpoint)
            path = cwd / (env["PINKHA_T2_SPACE_CLOSE_PHASE"] + ".json")
            value = json.loads(path.read_text())
            value["nonce"] = "foreign-invocation"
            path.write_text(json.dumps(value))
            return pid

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, evidence = self.sequence_inputs(root)
            with patch.object(lane, "run_owned", side_effect=wrong_report), patch.object(lane.base, "RESERVE", 0):
                with self.assertRaises(ValueError):
                    lane.run_sequence(identity, root / "owned", evidence, set())
            result = json.loads((evidence / "space-close-sequence/result.json").read_text())
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["phases"][0]["status"], "PASS_EXIT_0")
            self.assertEqual(result["phases"][0]["report_qualification"], "FAIL")
            self.assertEqual(result["actual_counts"], {"native_processes": 1, "passing_test_invocations": 0})

    def test_changed_ownership_withholds_cleanup_without_masking_primary_native_failure(self):
        def change_owner(command, cwd, env, log, timeout, entry, checkpoint):
            (cwd / "ownership.json").write_text('{"foreign_owner":true}')
            entry.update(pid=1234, status="FAIL", exit_code=1, process_exit_observed=True)
            log.write_text("failed controller fixture")
            raise RuntimeError("primary native failure")

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, evidence = self.sequence_inputs(root)
            work = root / "owned-sequence"
            with patch.object(lane, "run_owned", side_effect=change_owner), patch.object(lane.base, "RESERVE", 0):
                with self.assertRaisesRegex(RuntimeError, "primary native failure"):
                    lane.run_sequence(identity, work, evidence, set())
            self.assertTrue(work.exists())
            cleanup = json.loads((evidence / "space-close-cleanup.json").read_text())
            self.assertEqual(cleanup["status"], "FAIL_CLEANUP_WITHHELD")
            secondary = json.loads((evidence / "space-close-secondary-error.json").read_text())
            self.assertEqual(secondary["primary_error_type"], "RuntimeError")

    def test_real_failed_process_retains_pid_exit_and_original_log(self):
        with TemporaryDirectory() as temporary:
            root, entry, checkpoints = Path(temporary), {}, []
            with self.assertRaisesRegex(ValueError, "Native command failed"):
                lane.run_owned([sys.executable, "-c", "print('owned diagnostic'); raise SystemExit(7)"], root,
                               os.environ.copy(), root / "failed.log", 5, entry, lambda: checkpoints.append(deepcopy(entry)))
            self.assertEqual(entry["status"], "FAIL")
            self.assertGreater(entry["pid"], 0)
            self.assertEqual(entry["exit_code"], 7)
            self.assertIs(entry["process_exit_observed"], True)
            self.assertIn("owned diagnostic", (root / "failed.log").read_text())
            self.assertIn("STARTED", [p["status"] for p in checkpoints])

    def test_launch_failure_never_claims_an_observed_native_process(self):
        with TemporaryDirectory() as temporary:
            root, entry = Path(temporary), {}
            with self.assertRaises(FileNotFoundError):
                lane.run_owned([str(root / "missing-executable")], root, os.environ.copy(), root / "missing.log",
                               1, entry, lambda: None)
            self.assertEqual(entry["status"], "FAIL")
            self.assertIsNone(entry["pid"])
            self.assertIs(entry["process_exit_observed"], False)

    def test_timed_out_owned_process_is_reaped_with_its_failure_receipt(self):
        with TemporaryDirectory() as temporary:
            root, entry = Path(temporary), {}
            with self.assertRaises(subprocess.TimeoutExpired):
                lane.run_owned([sys.executable, "-c", "import time; time.sleep(10)"], root, os.environ.copy(),
                               root / "timeout.log", 0.05, entry, lambda: None)
            self.assertEqual(entry["status"], "FAIL")
            self.assertEqual(entry["error_type"], "TimeoutExpired")
            self.assertIs(entry["process_exit_observed"], True)
            self.assertIsNotNone(entry["exit_code"])

    def evidence(self, root):
        work = root / "private"
        work.mkdir(mode=0o700)
        (work / "ownership.json").write_text('{"synthetic_only":true}')
        (work / "result.json").write_text('{"status":"FAIL"}')
        (work / "sensitive-needles.private").write_text(json.dumps(["owned-secret-key", "owned-secret-mnemonic"]))
        (work / "sensitive-needles.private").chmod(0o600)
        for name in ["race.json", "race-trace.json", "race.log"]:
            (work / name).write_text("original-observation")
        (work / "account-key.private").write_text("owned-secret-key")
        (work / "state.json").write_text("private-synthetic-state")
        return work

    def test_only_original_allowlisted_secret_scanned_phase_evidence_is_copied(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = self.evidence(root)
            result = lane.preserve_evidence(work, root / "public")
            self.assertEqual(result["secret_scan"], "PASS")
            self.assertEqual(set(result["files_sha256"]), {"ownership.json", "result.json", "race.json", "race-trace.json", "race.log"})
            self.assertFalse((root / "public/account-key.private").exists())
            self.assertFalse((root / "public/state.json").exists())

    def test_any_secret_withholds_the_entire_phase_evidence_copy(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = self.evidence(root)
            (work / "race.log").write_text("failure printed owned-secret-key")
            with self.assertRaisesRegex(ValueError, "all Space.Close phase evidence withheld"):
                lane.preserve_evidence(work, root / "public")
            self.assertFalse((root / "public").exists())

    def test_missing_secret_inventory_withholds_original_native_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = self.evidence(root)
            (work / "sensitive-needles.private").unlink()
            result = lane.preserve_evidence(work, root / "public")
            self.assertEqual(set(result["files_sha256"]), {"ownership.json", "result.json"})
            self.assertEqual(result["secret_scan"], "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY")

    def test_symlink_phase_evidence_is_rejected_before_any_copy(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = self.evidence(root)
            (work / "race.log").unlink()
            outside = root / "outside.log"
            outside.write_text("foreign")
            (work / "race.log").symlink_to(outside)
            with self.assertRaises(ValueError):
                lane.preserve_evidence(work, root / "public")
            self.assertFalse((root / "public").exists())


class MaterializerControls(unittest.TestCase):
    def setup_module(self, root):
        heart, module = root / "heart", root / "module-cache/any-sync@v0.13.8"
        heart.mkdir()
        module.mkdir(parents=True)
        # The real pinned go.mod uses a require block. Keep this unit fixture in
        # that same syntax so validation does not invent a second selector path.
        (heart / "go.mod").write_text("module github.com/anyproto/anytype-heart\nrequire (\n github.com/anyproto/any-sync v0.13.8\n)\n")
        sums = {"Sum": "h1:" + "A" * 43 + "=", "GoModSum": "h1:" + "B" * 43 + "="}
        (heart / "go.sum").write_text("github.com/anyproto/any-sync v0.13.8 " + sums["Sum"] + "\n"
                                     + "github.com/anyproto/any-sync v0.13.8/go.mod " + sums["GoModSum"] + "\n")
        (module / "go.mod").write_text("module github.com/anyproto/any-sync\n")
        selected = dict(Path=materializer.ANY_SYNC, Version=materializer.VERSION, Dir=str(module),
                        GoMod=str(module / "go.mod"), **sums)
        return heart, module, selected

    def test_module_selection_binds_version_sums_and_actual_canonical_directory(self):
        with TemporaryDirectory() as temporary:
            heart, module, selected = self.setup_module(Path(temporary).resolve())
            result = materializer.module_identity(heart, selected)
            self.assertEqual(result["selected_dir"], str(module))
            self.assertEqual(result["reviewed_commit"], materializer.COMMIT)
            self.assertEqual(result["go_mod_sha256"], hashlib.sha256((module / "go.mod").read_bytes()).hexdigest())

    def test_byte_exact_workspace_copy_preserves_readonly_cache_and_detects_later_changes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            heart, module, selected = self.setup_module(root)
            nested = module / "nested/source.go"
            nested.parent.mkdir()
            nested.write_bytes(b"package nested\n")
            nested.chmod(0o444)
            identity = materializer.module_identity(heart, selected)
            before = materializer.module_tree(module)
            copy = materializer.copy_module_for_overlay(identity, root / "owned-copy")
            self.assertEqual(materializer.module_tree(module), before)
            self.assertTrue(materializer.verify_module_copy(identity, copy))
            self.assertEqual(copy["file_count"], 2)
            (Path(copy["copy_dir"]) / "nested/source.go").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Module source/copy changed"):
                materializer.verify_module_copy(identity, copy)
            self.assertEqual(materializer.module_tree(module), before)
            nested.chmod(0o644)  # Permit Windows fixture cleanup.

    def test_module_copy_refuses_existing_destination_before_writing(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            heart, module, selected = self.setup_module(root)
            destination = root / "owned-copy"
            destination.mkdir()
            sentinel = destination / "keep"
            sentinel.write_bytes(b"preexisting bytes")
            with self.assertRaisesRegex(ValueError, "Fresh separate module copy"):
                materializer.copy_module_for_overlay(materializer.module_identity(heart, selected), destination)
            self.assertEqual(sentinel.read_bytes(), b"preexisting bytes")

    def test_module_replacement_version_checksum_origin_and_directory_substitution_are_rejected(self):
        with TemporaryDirectory() as temporary:
            heart, module, original = self.setup_module(Path(temporary).resolve())
            mutations = [("Replace", {}), ("Version", "v0.13.9"), ("Path", "foreign/module"),
                         ("Sum", "h1:" + "C" * 43 + "="), ("GoModSum", "wrong"),
                         ("Origin", {"Hash": "f" * 40}), ("Dir", str(heart)), ("Dir", "relative")]
            for key, value in mutations:
                selected = deepcopy(original)
                selected[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    materializer.module_identity(heart, selected)

    def test_compose_requires_exact_pinned_manifest_and_does_not_write_native_or_cache_files(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            heart, module, selected = self.setup_module(root)
            manifest = json.loads((materializer.HERE / "candidate.json").read_text())
            # Obtain exact before bytes from the local fixture's reviewed patch
            # by reversing it over a fresh copy, never touching native inputs.
            copies = root / "patch-input"
            copies.mkdir()
            for entry in manifest["instrumented"]:
                target = copies / entry["module"] / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(materializer.HERE / "overlay" / entry["module"] / entry["path"], target)
            subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--reverse", "--check", str(materializer.HERE / "test-composition.patch")],
                           cwd=copies, check=True, capture_output=True)
            subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--reverse", str(materializer.HERE / "test-composition.patch")],
                           cwd=copies, check=True, capture_output=True)
            before = {}
            for entry in manifest["instrumented"]:
                target = (heart if entry["module"] == "heart" else module) / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(copies / entry["module"] / entry["path"], target)
                before[str(target)] = lane.digest(target)
                self.assertEqual(before[str(target)], entry["before_sha256"])
            (heart / "util").mkdir(exist_ok=True)
            fixture = root / "original-fixture.go"
            fixture.write_text("package service\n")
            inherited = root / "original-overlay.json"
            inherited.write_text(json.dumps({"Replace": {str(heart / "clientlibrary/service/original_test.go"): str(fixture)}}))
            output = root / "overlay.json"
            result = materializer.prepare(heart, selected, inherited, output)
            self.assertEqual(result["added_overlay_entries"], 10)
            self.assertEqual(result["product_source_mutations"], 0)
            self.assertEqual(result["module_cache_mutations"], 0)
            replacements = json.loads(output.read_text())["Replace"]
            self.assertEqual(len(replacements), 11)
            self.assertFalse(any(Path(name).is_relative_to(module) for name in replacements))
            copy_root = Path(result["any_sync_copy"]["copy_dir"])
            self.assertEqual(sum(Path(name).is_relative_to(copy_root) for name in replacements), 2)
            self.assertTrue(materializer.verify_module_copy(result["any_sync"], result["any_sync_copy"]))
            self.assertEqual(before, {name: lane.digest(Path(name)) for name in before})
            self.assertEqual(list((heart / "util/pinkhat2spaceclosetest").iterdir()), [])
            with self.assertRaisesRegex(ValueError, "Fresh canonical overlay destination"):
                materializer.prepare(heart, selected, inherited, output)


if __name__ == "__main__":
    unittest.main()
