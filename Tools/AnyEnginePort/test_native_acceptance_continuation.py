"""Focused source/admission adversarial controls; no product or native test runs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings
import zipfile

import continue_native_acceptance as admission
import native_continuation_sources as source
import verify_custom_type as custom
import verify_native_test_execution as execution

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = Path(os.environ.get("PINKHA_CONTINUATION_CANDIDATE_ROOT", ROOT))
BASELINE = os.environ.get("PINKHA_CONTINUATION_BASELINE_ROOT")


def original(path):
    return (Path(BASELINE) / path).read_bytes() if BASELINE else source.source(source.PRODUCER, path, ROOT)


def candidate_review():
    review = json.loads((ROOT / source.REVIEW).read_bytes())
    before, after, old, new = {}, {}, {}, {}
    for entry in review["reviewedChanges"]:
        path = entry["path"]
        new[path] = (CANDIDATE / path).read_bytes()
        after[path] = source.blob(new[path])
        if entry["beforeSHA256"] is not None:
            old[path] = original(path)
            before[path] = source.blob(old[path])
    return before, after, review, old, new


def rebind(review, after, new, path):
    entry = next(value for value in review["reviewedChanges"] if value["path"] == path)
    entry["afterSHA256"] = source.sha(new[path])
    entry["afterGitBlob"] = after[path] = source.blob(new[path])


def results(methods, failed=()):
    cases = {name + "()": ("Failed" if name in failed else "Passed") for name in methods}
    device = {"deviceId": "1234", "deviceName": "AnyNativePort-" + admission.RUN,
              "architecture": "arm64", "osVersion": "27.2", "osBuildNumber": "24B8117",
              "platform": "iOS Simulator"}
    summary = {"totalTestCount": len(cases), "passedTests": len(cases) - len(failed),
               "failedTests": len(failed), "skippedTests": 0,
               "devicesAndConfigurations": [{"device": device}]}
    tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": name, "result": result}
                          for name, result in cases.items()]}
    return cases, summary, tree


def log_bytes(cases):
    lines = []
    for name, status in cases.items():
        suite, method = name.removesuffix("()").split("/")
        prefix = "Test Case '-[TestModule." + suite + " " + method + "]' "
        lines += [prefix + "started.", prefix + status.lower() + " (0.1 seconds)."]
    return ("\n".join(lines) + "\n").encode()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())


def raw_fixture(root):
    admission.focus.register_profile()
    write(root / "simulator.json", {"ownedUDID": "1234"})
    for stem, profile, methods, failed in (
        ("ui-focus-handoff", admission.focus.PROFILE, execution.expected_methods(admission.focus.PROFILE), set()),
        ("native-ui", "native-ui-entry", {admission.ENTRY}, set()),
        ("native-ui-followup", "native-ui-followup", admission.SIX | {admission.QUOTE}, admission.SIX),
    ):
        cases, summary, tree = results(methods, failed)
        write(root / (stem + "-test-counts.json"), summary)
        write(root / (stem + "-test-methods.json"), tree)
        write(root / (stem + ".log"), log_bytes(cases))
        receipt = {"status": "FAIL" if failed else "PASS", "profile": profile, "commit": source.PRODUCER,
                   "observationOnly": False, "scope": "actual_named_apple_test_execution",
                   "summarySHA256": source.sha((root / (stem + "-test-counts.json")).read_bytes()),
                   "testTreeSHA256": source.sha((root / (stem + "-test-methods.json")).read_bytes())}
        if not failed:
            receipt.update(execution.validate(summary, tree, profile, "1234"))
        write(root / (stem + "-named-execution.json"), receipt)


class NativeAcceptanceContinuationTests(unittest.TestCase):
    def test_exact_review_accepts_actual_twelve_frozen_sources_and_preserves_passed_declarations(self):
        before, after, review, old, new = candidate_review()
        proof = source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)
        self.assertTrue(proof["testDeclarationProof"]["retainedEntryQuoteAndCommonHelpersByteIdentical"])
        self.assertTrue(proof["historyTargetRegistration"]["productionTargetsAndSettingsByteIdentical"])
        self.assertEqual(12, len(review["reviewedChanges"]))

    def test_changed_passed_entry_or_common_helper_cannot_be_excused_by_new_review_hashes(self):
        for name in ("testCreateEditHanlinConsentBackgroundAndColdReopen", "tapWhenEnabled"):
            with self.subTest(name=name):
                before, after, review, old, new = candidate_review()
                begin, _ = source.declaration(new[source.TEST], name)
                point = new[source.TEST].index(b"{", begin) + 1
                new[source.TEST] = new[source.TEST][:point] + b"\n        // Unreviewed mutation\n" + new[source.TEST][point:]
                rebind(review, after, new, source.TEST)
                with self.assertRaisesRegex(ValueError, "retained_methods_or_common_helpers_changed"):
                    source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)

    def test_hanlin_helper_must_have_only_the_failed_journey_as_caller(self):
        before, after, review, old, new = candidate_review()
        begin, _ = source.declaration(new[source.TEST], "testCreateEditHanlinConsentBackgroundAndColdReopen")
        point = new[source.TEST].index(b"{", begin) + 1
        new[source.TEST] = new[source.TEST][:point] + b"\n        configureHanlinThroughNormalFields()\n" + new[source.TEST][point:]
        rebind(review, after, new, source.TEST)
        with self.assertRaisesRegex(ValueError, "exclusive_to_failed_method"):
            source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)

    def test_unreviewed_source_additions_and_scope_relabel_are_rejected(self):
        before, after, review, old, new = candidate_review()
        after["Modules/PinkhaAnyUI/Sources/NewAuthority.swift"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "unexpected_source"):
            source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)
        del after["Modules/PinkhaAnyUI/Sources/NewAuthority.swift"]
        review["reviewedChanges"][0]["scope"] = "unchanged_and_passed_in_current_run"
        with self.assertRaisesRegex(ValueError, "incomplete_bounded_source_review"):
            source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)

    def test_source_and_review_digests_cannot_drift(self):
        before, after, review, old, new = candidate_review()
        path = next(iter(new))
        new[path] += b"\n// Drift\n"
        after[path] = source.blob(new[path])
        with self.assertRaisesRegex(ValueError, "reviewed_source_bytes_changed"):
            source.verify_maps(before, after, review, old.__getitem__, new.__getitem__)

    def test_history_registration_rejects_any_production_target_change(self):
        before = original(source.PROJECT)
        after = (CANDIDATE / source.PROJECT).read_bytes()
        after = after.replace(b"productName = PinkhaAnyNative;", b"productName = WrongNative;")
        self.assertNotEqual(after, (CANDIDATE / source.PROJECT).read_bytes())
        with self.assertRaisesRegex(ValueError, "production_target"):
            source.verify_history_registration(before, after)

    def test_original_run_artifact_identity_rejects_wrong_origin_or_relabel(self):
        contract = admission.manifest()
        run = {"id": int(admission.RUN), "head_sha": source.PRODUCER, "head_branch": admission.BRANCH,
               "run_attempt": 1, "event": "workflow_dispatch", "status": "completed", "conclusion": "failure",
               "path": ".github/workflows/pinkha-any-engine-port.yml",
               "repository": {"full_name": admission.REPOSITORY}, "head_repository": {"full_name": admission.REPOSITORY}}
        artifact = {"id": contract["artifactID"], "expired": False,
                    "name": "any-engine-port-ios-patched-runtime-" + source.PRODUCER,
                    "size_in_bytes": contract["archiveBytes"], "digest": "sha256:" + contract["archiveSHA256"],
                    "workflow_run": {"id": int(admission.RUN), "head_sha": source.PRODUCER}}
        admission.verify_api(run, artifact, contract)
        for key, value in (("conclusion", "success"), ("head_sha", "a" * 40), ("run_attempt", 2),
                           ("head_branch", "main"), ("head_repository", {"full_name": "other/repo"})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                admission.verify_api({**run, key: value}, artifact, contract)
        for key, value in (("expired", True), ("size_in_bytes", 1), ("digest", "sha256:" + "0" * 64),
                           ("workflow_run", {"id": 1, "head_sha": source.PRODUCER})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                admission.verify_api(run, {**artifact, key: value}, contract)

    def test_original_manifest_cannot_be_replaced_with_other_passed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / admission.MANIFEST, b"{}")
            with self.assertRaisesRegex(ValueError, "manifest_changed"):
                admission.manifest(root)

    def test_zip_rejects_traversal_symlink_duplicates_and_changed_bytes(self):
        for name, mode, duplicate in (("../proof.json", None, False), ("proof.json", stat.S_IFLNK, False),
                                      ("proof.json", None, True), ("PROOF.json", None, True)):
            with self.subTest(name=name, mode=mode, duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); archive = root / "evidence.zip"
                with warnings.catch_warnings(), zipfile.ZipFile(archive, "w") as zipped:
                    warnings.simplefilter("ignore", UserWarning)
                    info = zipfile.ZipInfo(name)
                    if mode: info.external_attr = mode << 16
                    zipped.writestr(info, b"{}")
                    if duplicate: zipped.writestr("proof.json", b"{}")
                contract = {"archiveBytes": archive.stat().st_size, "archiveSHA256": source.sha(archive.read_bytes()),
                            "files": {"proof.json": {"bytes": 2, "sha256": source.sha(b"{}")}}}
                with self.assertRaises(ValueError):
                    admission.extract_selected(archive, root / "out", contract)

    def test_zip_exact_file_binding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); archive = root / "evidence.zip"
            with zipfile.ZipFile(archive, "w") as zipped: zipped.writestr("proof.json", b"{}")
            contract = {"archiveBytes": archive.stat().st_size, "archiveSHA256": source.sha(archive.read_bytes()),
                        "files": {"proof.json": {"bytes": 2, "sha256": source.sha(b"{}")}}}
            admission.extract_selected(archive, root / "out", contract)
            self.assertEqual(b"{}", (root / "out/proof.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "must_be_new"):
                admission.extract_selected(archive, root / "out", contract)
            for corrupt in ({**contract, "archiveSHA256": "0" * 64},
                            {**contract, "files": {"proof.json": {"bytes": 2, "sha256": "0" * 64}}}):
                with self.assertRaises(ValueError):
                    admission.extract_selected(archive, root / "rejected", corrupt)

    def test_original_failed_seven_remains_failed_with_only_quote_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); raw_fixture(root)
            proof = admission.verify_raw_results(root)
            self.assertEqual({admission.QUOTE + "()": "Passed"}, proof["quote"])
            self.assertEqual(6, sum(status == "Failed" for status in proof["originalFailedBatch"].values()))
            path = root / "native-ui-followup-named-execution.json"
            receipt = json.loads(path.read_bytes()); receipt["status"] = "PASS"; write(path, receipt)
            with self.assertRaisesRegex(ValueError, "must_remain_failed"):
                admission.verify_raw_results(root)

    def test_raw_log_rejects_duplicates_missing_terminals_and_skips(self):
        cases = {admission.ENTRY + "()": "Passed"}
        raw = log_bytes(cases)
        admission.verify_log(raw, cases)
        for changed in (raw + raw, raw.replace(b"passed", b"skipped"), raw.splitlines(keepends=True)[0]):
            with self.subTest(changed=changed[:30]), self.assertRaises(ValueError):
                admission.verify_log(changed, cases)

    def test_new_exact_profiles_reject_old_quote_extra_cases_and_skips(self):
        self.assertEqual(admission.SIX, execution.expected_methods(admission.PROFILE))
        self.assertNotIn(admission.ENTRY, admission.SIX); self.assertNotIn(admission.QUOTE, admission.SIX)
        _, summary, tree = results(admission.SIX)
        execution.validate(summary, tree, admission.PROFILE, "1234")
        _, summary, tree = results(admission.SIX | {admission.QUOTE})
        with self.assertRaises(RuntimeError): execution.validate(summary, tree, admission.PROFILE, "1234")
        _, summary, tree = results({admission.HISTORY})
        execution.validate(summary, tree, admission.HISTORY_PROFILE, "1234")
        summary["skippedTests"] = 1
        with self.assertRaises(RuntimeError): execution.validate(summary, tree, admission.HISTORY_PROFILE, "1234")

    def test_frozen_build_binds_explicit_continuation_and_old_shape_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "admission.json"; receipt.write_bytes(b"retained proof")
            args = SimpleNamespace(simulator_receipt=Path("sim"), derived=Path("build"), continuation=receipt)
            with mock.patch.object(custom, "current_context", return_value={"commit": "head"}), \
                 mock.patch.object(custom, "validate_sources", return_value={"file": "hash"}) as verify, \
                 mock.patch.object(custom, "product_identity", return_value={"app": "hash"}):
                frozen = custom.capture(args)
                verify.assert_called_with(continuation=receipt)
                self.assertEqual(source.sha(b"retained proof"), frozen["continuationAdmissionSHA256"])
                receipt.write_bytes(b"different proof")
                with self.assertRaisesRegex(ValueError, "changed"): custom.validate_frozen(frozen, custom.capture(args))
                args.continuation = None
                self.assertNotIn("continuationAdmissionSHA256", custom.capture(args))

    def test_product_identity_code_is_byte_identical_to_original_five_control_scope(self):
        before = source.source(source.PRODUCER, "Tools/AnyEnginePort/verify_custom_type.py", ROOT) if not BASELINE else (
            ROOT / ".baseline/Tools/AnyEnginePort/verify_custom_type.py").read_bytes()
        after = (ROOT / "Tools/AnyEnginePort/verify_custom_type.py").read_bytes()
        def mask(raw):
            for name in ("validate_sources", "capture", "postflight", "main"):
                start = raw.index(("\ndef " + name + "(").encode()) + 1
                following = raw.find(b"\ndef ", start + 1)
                if following < 0: following = raw.index(b'\nif __name__ == "__main__":', start)
                raw = raw[:start] + ("# REVIEWED " + name + "\n").encode() + raw[following:]
            return raw
        self.assertEqual(mask(before), mask(after))

    def test_current_named_stage_requires_current_source_commit_and_raw_terminals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); evidence = root / "evidence"; stem = "native-ui-continuation"
            cases, summary, tree = results(admission.SIX)
            write(evidence / (stem + "-test-counts.json"), summary); write(evidence / (stem + "-test-methods.json"), tree)
            write(evidence / (stem + ".log"), log_bytes(cases))
            write(root / "Tools/AnyEnginePort/verify_native_test_execution.py", b"verifier")
            write(root / source.TEST, b"actual current test")
            record = {"status": "PASS", "commit": "current", "profile": admission.PROFILE,
                      "observationOnly": False, "scope": "actual_named_apple_test_execution",
                      "runnerSHA256": source.sha(b"verifier"), "testSources": {source.TEST: source.sha(b"actual current test")},
                      "summarySHA256": source.sha((evidence / (stem + "-test-counts.json")).read_bytes()),
                      "testTreeSHA256": source.sha((evidence / (stem + "-test-methods.json")).read_bytes()),
                      **execution.validate(summary, tree, admission.PROFILE, "1234")}
            path = evidence / (stem + "-named-execution.json"); write(path, record)
            context = {"consumerCommit": "current", "ownedSimulatorUDID": "1234"}
            admission.current_stage(evidence, stem, admission.PROFILE, context, root)
            write(path, {**record, "commit": source.PRODUCER})
            with self.assertRaises(ValueError): admission.current_stage(evidence, stem, admission.PROFILE, context, root)
            write(path, record); write(root / source.TEST, b"changed assertion")
            with self.assertRaises(ValueError): admission.current_stage(evidence, stem, admission.PROFILE, context, root)


if __name__ == "__main__":
    unittest.main()
