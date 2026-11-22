"""New controller controls only; no Apple, native SDK or retained product test runs."""
from __future__ import annotations

import contextlib
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import contract
import execution
import proof
import run_host

UDID = "BAFA2C41-7334-4049-95AE-582A6418CEAC"


def sample_observation():
    generations = [f"00000000-0000-0000-0000-{i:012d}" for i in range(1, 7)]
    owners = [f"10000000-0000-0000-0000-{i:012d}" for i in range(1, 7)]
    rows = []
    for i, phase in enumerate(proof.PHASES[:-1]):
        generation = (0, 1, 2, 3, 3, 4, 5, 5)[i]
        block = i in (4, 5, 7)
        stage = ("root-prepared", "root-committed", "bootstrap-prepared", "complete", "block-prepared", "complete", "complete", "complete")[i]
        record = "block-record" if block else "object-root"
        change = "block-cid" if block else ("root-cid" if i < 2 else "bootstrap-cid")
        row = dict(phase=phase, runtimeVersion="any " + contract.VERSION + " (commit 88fae2e)",
                   engineGeneration=generations[generation], ownerGeneration=owners[generation],
                   contract="pinkha-native-prepared-migration-v1", intentId=("a" if block else "b") * 64,
                   fingerprint=("c" if block else "d") * 64, specSHA256=("e" if block else "f") * 64,
                   stage=stage, outcome="committed" if stage == "complete" else "prepared",
                   objectId="object-root", changeId=change, recordIds=[] if i < 2 else [record],
                   accountId="disposable-account", spaceId="disposable-space", storeId="disposable-store",
                   planId="1" * 64, planSHA256=proof.PLAN_SHA, readback=None)
        if i in (3, 5, 6, 7):
            dataset = "editor_blocks" if block else "objects"
            history = dict(version=change, author=row["accountId"], timestamp=123, dataset=dataset, groupSize=1,
                           touched=[dict(dataset=dataset, recordId=record, ops=["$set"])])
            value = dict(dataset=dataset, recordId=record, nativeHistoryEntry=history)
            if block:
                value.update(currentBodyUTF8SHA256=proof.BODY_SHA, historicalBodyUTF8SHA256=proof.BODY_SHA, currentRecordCount=1)
            else:
                value.update(currentNameUTF8SHA256=proof.NAME_SHA, historicalNameUTF8SHA256=proof.NAME_SHA)
            row["readback"] = value
        rows.append(row)
    rows.append(dict(phase="revoked-owner-refused", error="AnyHostError.sessionClosed",
                     authorityScope="application-owner-lifetime; native ACL mutation not exercised"))
    return dict(status="OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED", completedCleanup=True, processId=1234,
                runtimeGenerations=generations, observations=rows, nameUTF8SHA256=proof.NAME_SHA,
                bodyUTF8SHA256=proof.BODY_SHA, **proof.LIMITS)


def producer_fixture():
    commit, run, attempt = "a" * 40, "1234", "2"
    names = ["xcode-version", "device-sdk-version", "simulator-sdk-version", "go-version",
             "apply-exact-native-candidate", "native-build-both-slices", "record-exact-native-artifact"]
    build = dict(status=contract.BUILD_PASS, app_sha=commit, run_id=run, run_attempt=attempt, source_unchanged=True,
                 version=contract.VERSION, manifest_sha256=contract.MANIFEST_SHA, native_tests_executed=0, apple_tests_executed=0,
                 archive_sha256="c" * 64, artifact_name=contract.artifact_name(run, attempt, commit),
                 commands=[dict(name=n, status="PASS_EXIT_0", pid=12) for n in names])
    artifact = dict(schemaVersion=1, version=contract.VERSION, sourceCommit=commit, sourceManifestSHA256=contract.MANIFEST_SHA,
                    archive="any.xcframework.zip", archiveSHA256="c" * 64)
    observed = dict(id=int(run), run_attempt=int(attempt), head_sha=commit, event="workflow_dispatch", path=contract.WORKFLOW,
                    repository=dict(full_name=contract.REPOSITORY), head_repository=dict(full_name=contract.REPOSITORY),
                    status="completed", conclusion="failure")
    jobs = [dict(id=1, name="Prepared Apple / " + contract.PRODUCER_JOB, status="completed", conclusion="success",
                 run_id=int(run), run_attempt=int(attempt), head_sha=commit)]
    return build, artifact, observed, jobs, run, attempt, commit


class PreparedAppleControls(unittest.TestCase):
    def test_exact_one_original_terminal_and_owned_destination_required(self):
        summary = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                       devicesAndConfigurations=[dict(device=dict(deviceId=UDID, osVersion="27.2", architecture="arm64", osBuildNumber="24C1"))])
        tree = {contract.SELECTOR + "()": "Passed"}
        result = proof.exact_execution(summary, tree, UDID, lambda value: value)
        self.assertEqual(result["selected_method"], contract.SELECTOR)
        mutations = [lambda s, t: s.update(passedTests=True), lambda s, t: s.update(skippedTests=1),
                     lambda s, t: s.update(totalTestCount=2),
                     lambda s, t: s["devicesAndConfigurations"][0]["device"].update(deviceId="00000000-0000-0000-0000-000000000000"),
                     lambda s, t: s["devicesAndConfigurations"][0]["device"].update(architecture="x86_64"),
                     lambda s, t: s["devicesAndConfigurations"][0]["device"].update(osVersion="26.2"),
                     lambda s, t: t.update({contract.SELECTOR + "()": "Skipped"}),
                     lambda s, t: (t.clear(), t.update({"Other/testOther()": "Passed"}))]
        for mutation in mutations:
            s, t = deepcopy(summary), deepcopy(tree)
            mutation(s, t)
            with self.assertRaises(ValueError):
                proof.exact_execution(s, t, UDID, lambda value: value)

    def test_complete_observation_stays_within_actual_native_scope(self):
        value = sample_observation()
        result = proof.observation(value)
        self.assertEqual(len(result["runtime_generations"]), 6)
        self.assertFalse(result["full_migration_accepted"])
        self.assertEqual(result["limits"]["nativeACLMutation"], "NOT_RUN")

    def test_missing_reordered_or_reused_generations_and_scope_are_refused(self):
        mutations = [lambda v: v["observations"].pop(1), lambda v: v["observations"].reverse(),
                     lambda v: v["runtimeGenerations"].__setitem__(5, v["runtimeGenerations"][0]),
                     lambda v: v["observations"][4].update(ownerGeneration=v["observations"][0]["ownerGeneration"]),
                     lambda v: v["observations"][6].update(spaceId="another-space"),
                     lambda v: v["observations"][6].update(planSHA256="0" * 64),
                     lambda v: v["observations"][5].update(runtimeVersion="any v0.5.0-pinkha.1 old")]
        for mutation in mutations:
            value = sample_observation(); mutation(value)
            with self.assertRaises(ValueError): proof.observation(value)

    def test_altered_immutable_intents_cids_and_record_mappings_are_refused(self):
        mutations = [lambda v: v["observations"][1].update(changeId="replacement-root"),
                     lambda v: v["observations"][6].update(changeId="replacement-bootstrap"),
                     lambda v: v["observations"][7].update(fingerprint="0" * 64),
                     lambda v: v["observations"][7].update(intentId="0" * 64),
                     lambda v: v["observations"][3].update(specSHA256="0" * 64),
                     lambda v: v["observations"][7].update(recordIds=["replacement-block"]),
                     lambda v: v["observations"][2].update(recordIds=[]),
                     lambda v: v["observations"][0].update(recordIds=["object-root"]),
                     lambda v: v["observations"][3].update(outcome="committed_modified")]
        for mutation in mutations:
            value = sample_observation(); mutation(value)
            with self.assertRaises(ValueError): proof.observation(value)

    def test_semantically_reused_uuid_with_different_case_is_refused(self):
        duplicate = "abcdef00-0000-0000-0000-000000000001"
        for field in ("engineGeneration", "ownerGeneration"):
            value = sample_observation()
            original = value["observations"][0][field]
            final = value["observations"][6][field]
            if field == "engineGeneration":
                value["runtimeGenerations"][0] = duplicate
                value["runtimeGenerations"][5] = duplicate.upper()
            for row in value["observations"][:-1]:
                if row[field] == original:
                    row[field] = duplicate
                elif row[field] == final:
                    row[field] = duplicate.upper()
            with self.assertRaisesRegex(ValueError, "distinct"):
                proof.observation(value)

    def test_current_historical_bytes_author_and_touched_records_are_required(self):
        mutations = [lambda r: r.update(currentRecordCount=2), lambda r: r.update(currentRecordCount=True),
                     lambda r: r.update(historicalBodyUTF8SHA256="0" * 64),
                     lambda r: r["nativeHistoryEntry"].update(author="other-account"),
                     lambda r: r["nativeHistoryEntry"].update(version="other-cid"),
                     lambda r: r["nativeHistoryEntry"].update(touched=[]),
                     lambda r: r["nativeHistoryEntry"]["touched"][0].update(recordId="foreign-record"),
                     lambda r: r["nativeHistoryEntry"].update(truncated=True)]
        for mutation in mutations:
            value = sample_observation(); mutation(value["observations"][5]["readback"])
            with self.assertRaises(ValueError): proof.observation(value)

    def test_partial_cleanup_broadened_claims_or_extra_private_fields_are_refused(self):
        mutations = [lambda v: v.update(completedCleanup=False), lambda v: v.update(processId=True),
                     lambda v: v.update(networkSynchronization="PASS"), lambda v: v.update(inlineFiles="PASS"),
                     lambda v: v.update(fullSpaceMigration="PASS"), lambda v: v.update(recoveryPhrase="synthetic-forbidden-field"),
                     lambda v: v["observations"][0].update(authenticationResponse={}),
                     lambda v: v["observations"][-1].update(authorityScope="native ACL proved")]
        for mutation in mutations:
            value = sample_observation(); mutation(value)
            with self.assertRaises(ValueError): proof.observation(value)

    def test_original_failed_consumer_run_can_reuse_only_its_successful_native_job(self):
        fixture = producer_fixture()
        result = run_host.validate_producer(*fixture)
        self.assertEqual(result["original_run_conclusion"], "failure")
        self.assertEqual(result["producer_job_conclusion"], "success")
        mutations = [lambda v: v[3][0].update(conclusion="failure"), lambda v: v[3][0].update(status="in_progress"),
                     lambda v: v[3].append(deepcopy(v[3][0])), lambda v: v[2].update(run_attempt=3),
                     lambda v: v[2].update(head_sha="b" * 40), lambda v: v[2].update(path="unrelated.yml"),
                     lambda v: v[0].update(source_unchanged=False), lambda v: v[0].update(apple_tests_executed=False),
                     lambda v: v[0]["commands"][5].update(status="FAIL"), lambda v: v[1].update(archiveSHA256="0" * 64)]
        for mutation in mutations:
            value = list(deepcopy(fixture)); mutation(value)
            with self.assertRaises(ValueError): run_host.validate_producer(*value)

    def test_partial_or_ambiguous_reuse_inputs_refuse_before_download(self):
        self.assertFalse(contract.reuse_inputs("", "", ""))
        self.assertTrue(contract.reuse_inputs("1234", "2", "a" * 40))
        for row in [("1234", "", "a" * 40), ("", "2", "a" * 40), ("1234", "2", ""),
                    ("../1", "2", "a" * 40), ("1234", "0", "a" * 40), ("1234", "2", "branch")]:
            with self.assertRaises(ValueError): contract.reuse_inputs(*row)

    def _orchestration_failure(self, *, where, cancelled=False):
        with tempfile.TemporaryDirectory(prefix="prepared-controller-control-") as temporary:
            root = Path(temporary); calls = []
            primary = KeyboardInterrupt("synthetic cancellation") if cancelled else subprocess.TimeoutExpired([where], 180)
            def process(argv, cwd, env, log, timeout):
                calls.append((argv, timeout))
                if argv[:3] == ["xcrun", "simctl", "create"]:
                    raw = (UDID + "\n").encode()
                elif argv[:3] == ["xcrun", "simctl", "list"]:
                    raw = b"{}\n"
                else: raw = b""
                log.write_bytes(raw)
                if where == "test" and argv[:2] == ["xcodebuild", "test-without-building"]:
                    Path(argv[argv.index("-resultBundlePath") + 1]).mkdir()
                    raise primary
                if where == "bootstatus" and argv[:3] == ["xcrun", "simctl", "bootstatus"]:
                    raise primary
                if argv[:3] in (["xcrun", "simctl", "shutdown"], ["xcrun", "simctl", "delete"]):
                    raise RuntimeError("synthetic cleanup failure")
                if argv[:2] == ["xcrun", "xcresulttool"] or argv[0] == "/usr/bin/log":
                    raise RuntimeError("synthetic diagnostic failure")
                return 42
            selector = SimpleNamespace(choose_pair=lambda *a, **k: dict(runtime=dict(identifier="ios27"),
                device=dict(identifier="ipad-type"), selection=dict(productFamily="iPad", architecture="arm64")))
            args = SimpleNamespace(control=root, work=root / "work", evidence=root / "evidence", expected_app_sha="a" * 40)
            def action(args, receipt, run):
                run_host.run_simulator(root, args.work, args.evidence, receipt, run, {}, root, contract.PACKAGE, [])
            previous = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGINT)}
            with patch.object(contract, "load_module", return_value=selector), \
                 patch.dict(os.environ, GITHUB_RUN_ID="1234", GITHUB_RUN_ATTEMPT="1"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(execution.run_stage(args, action, process=process), 1)
            receipt = json.loads((args.evidence / "receipt.json").read_bytes())
            self.assertEqual(receipt["primary_failure"], dict(error_type=type(primary).__name__, error=str(primary)))
            self.assertEqual(receipt["error"], str(primary))
            self.assertEqual(receipt["status"], "CANCELLED" if cancelled else "FAIL")
            names = [row["name"] for row in receipt["commands"]]
            self.assertLess(names.index("boot-owned-simulator"), names.index("ios-build-for-testing"))
            self.assertLess(names.index("ios-build-for-testing"), names.index("wait-owned-simulator"))
            self.assertEqual(names.count("ios-build-for-testing"), 1)
            self.assertEqual(receipt["harness_build"]["tests_executed"], 0)
            build = next(row for row in receipt["commands"] if row["name"] == "ios-build-for-testing")
            self.assertEqual([v for v in build["argv"] if v.startswith("-only-testing:")], ["-only-testing:" + contract.SELECTOR])
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
            self.assertEqual(set(receipt["owned_simulator_cleanup"]), {"shutdown", "delete"})
            self.assertEqual([(a[-1], t) for a, t in calls if a[:3] in
                             (["xcrun", "simctl", "shutdown"], ["xcrun", "simctl", "delete"])], [(UDID, 30), (UDID, 30)])
            self.assertEqual({n: signal.getsignal(n) for n in previous}, previous)
            if where == "bootstatus":
                self.assertNotIn("ios-test-without-building", names)
                failed = next(row for row in receipt["commands"] if row["name"] == "wait-owned-simulator")
                self.assertEqual(failed["log_bytes"], 0)
                self.assertEqual(failed["log_sha256"], hashlib.sha256(b"").hexdigest())
            else:
                self.assertTrue(receipt["result_bundle_present"])
                self.assertEqual(names.count("ios-test-without-building"), 1)
                self.assertEqual(set(receipt["result_export_failures"]), {"summary", "tests", "attachments"})
            self.assertNotIn("actual_execution", receipt)

    def test_readiness_failure_preserves_empty_original_log_and_blocks_test_execution(self):
        self._orchestration_failure(where="bootstatus")

    def test_test_failure_preserves_primary_and_attempts_all_original_result_exports(self):
        self._orchestration_failure(where="test")

    def test_cancellation_keeps_primary_and_bounded_owned_cleanup(self):
        self._orchestration_failure(where="bootstatus", cancelled=True)

    def test_source_change_is_reported_without_replacing_an_earlier_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); receipt = {}
            with patch.object(contract, "snapshot", return_value={"file": "new"}):
                contract.source_after(root, {"file": "old"}, root, receipt, RuntimeError("primary"))
                self.assertIn("source_verification_failure", receipt)
                with self.assertRaises(ValueError): contract.source_after(root, {"file": "old"}, root, {}, None)

    def test_installed_archive_byte_change_or_extra_member_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); vendor = root / "Modules/PinkhaAnyRuntime/Vendor"
            binary = vendor / "any.xcframework/ios-arm64-simulator/anylib.a"
            binary.parent.mkdir(parents=True); binary.write_bytes(b"synthetic archive member")
            name = str(binary.relative_to(vendor)); artifact = dict(filesSHA256={name: contract.digest(binary)})
            native = SimpleNamespace(safe_relative=PurePosixPath)
            run_host.installed_fingerprints(root, artifact, native)
            binary.write_bytes(b"different")
            with self.assertRaises(ValueError): run_host.installed_fingerprints(root, artifact, native)
            binary.write_bytes(b"synthetic archive member")
            (binary.parent / "unexpected.a").write_bytes(b"extra")
            with self.assertRaises(ValueError): run_host.installed_fingerprints(root, artifact, native)

    def test_product_source_census_refuses_an_untracked_compilation_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = [contract.HERE + "/run_host.py", contract.HELPER, contract.MANIFEST, contract.WORKFLOW,
                     contract.TEST_SOURCE, "Modules/PinkhaAnyRuntime/Sources/PinkhaAnyRuntime/Runtime.swift"]
            for name in names:
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text("synthetic source\n")
            (root / contract.MANIFEST).write_text(json.dumps({"any": {"patch": "any.patch"}, "sdk": {"patch": "sdk.patch"}}))
            with patch.object(contract.subprocess, "check_output", return_value=("\0".join(names) + "\0").encode()):
                contract.snapshot(root)
                (root / names[-1]).with_name("Untracked.swift").write_text("synthetic extra source\n")
                with self.assertRaises(ValueError): contract.snapshot(root)

    def test_dependency_revision_or_tracked_source_change_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in contract.PINS:
                (root / "SourcePackages/checkouts" / name).mkdir(parents=True)
            def fake_git(path, *args):
                if args == ("rev-parse", "HEAD"): return contract.PINS[path.name]
                if args == ("rev-parse", "HEAD^{tree}"): return "1" * 40
                return ""
            with patch.object(contract, "git", side_effect=fake_git):
                self.assertEqual(set(contract.dependency_checkouts(root)), set(contract.PINS))
            def changed(path, *args):
                return "M Sources/Changed.swift" if args[0] == "status" else fake_git(path, *args)
            with patch.object(contract, "git", side_effect=changed):
                with self.assertRaises(ValueError): contract.dependency_checkouts(root)


if __name__ == "__main__":
    unittest.main()
