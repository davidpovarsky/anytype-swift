"""New process receipt/admission controls using explicit synthetic fixtures.
No Swift code, Keychain operation, native RPC, simulator, app or XCTest runs here.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

SOURCE = Path(os.environ["STAGEB_COLLECTOR_SOURCE"]).resolve()
spec = importlib.util.spec_from_file_location("stageb_original_native_driver", SOURCE)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class ProcessReceiptControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="stageb-process-receipt-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        driver.OUT = self.root / "evidence"
        driver.OUT.mkdir()
        self.first_name = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
        self.second_name = "BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB"
        self.first = driver.OUT / "native/qualification" / self.first_name
        self.second = driver.OUT / "native/qualification" / self.second_name
        self.checkpoint = driver.OUT / "native/process-checkpoint"
        self.archive = b"explicit synthetic archive fixture; not a native export"
        archive_sha = hashlib.sha256(self.archive).hexdigest()
        common = {
            "schema": 2, "qualification": driver.MARKER, "bundle_id": driver.BUNDLE,
            "annotation_uuid": "CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC",
            "annotation_id": 41, "profile_id": "DDDDDDDD-DDDD-4DDD-8DDD-DDDDDDDDDDDD",
            "source_witness_sha256": "1" * 64, "initial_revision": 0,
            "initial_note_blank": True, "initial_rich_body_absent": True,
            "original_object_id": "original-first-page", "original_space_id": "original-first-space",
            "preview_derived_from_native_body": False, "process_id": 101,
            "process_mode": "prepare-owned-once"
        }
        self.reports = {}
        opened = {**common, "stage": "editing"}
        saved = {
            **common, "stage": "saved", "commit_revision": 1, "commit_replayed": False,
            "commit_delivery": "committed", "payload_digest": "2" * 64,
            "native_archive_sha256": archive_sha, "native_body_bytes": 512,
            "native_exported_object_count": 1
        }
        reopened = {
            **saved, "stage": "reopened", "reopened_revision": 1,
            "reopened_annotation_uuid": common["annotation_uuid"], "reopened_annotation_id": 41,
            "reopened_payload_digest": saved["payload_digest"],
            "reopened_source_witness_sha256": common["source_witness_sha256"],
            "reopened_space_id": "original-restored-space", "reopened_object_id": "original-restored-page",
            "durable_body_verified_by_original_reopen": True
        }
        process = {
            "process_runtime_nonce": "FFFFFFFF-FFFF-4FFF-8FFF-FFFFFFFFFFFF",
            "process_account_id": "original-owned-account",
            "process_space_id": reopened["reopened_space_id"],
            "process_object_id": reopened["reopened_object_id"],
            "process_workspace_namespace": "EEEEEEEE-EEEE-4EEE-8EEE-EEEEEEEEEEEE",
            "process_saved_body_sha256": "3" * 64,
            "process_saved_archive_sha256": archive_sha,
            "process_annotation_uuid": common["annotation_uuid"],
            "process_annotation_id": 41, "process_profile_id": common["profile_id"],
            "process_payload_digest": saved["payload_digest"],
            "process_source_witness_sha256": common["source_witness_sha256"],
            "process_revision": 1, "process_prepared_pid": 101
        }
        prepared = {**reopened, **process, "stage": "process-resume-prepared",
                    "process_credential_consumed": False, "process_current_pid": 101}
        resumed = {
            **common, **process, "stage": "process-resumed", "process_id": 202,
            "process_mode": "resume-owned-once", "process_credential_consumed": True,
            "process_current_pid": 202, "initial_revision": 1,
            "initial_rich_body_absent": False,
            "original_space_id": process["process_space_id"], "original_object_id": process["process_object_id"]
        }
        closed = {**resumed, "stage": "closed", "credential_cleanup_status": "OWNED_QUERY_ABSENCE_VERIFIED"}
        for value in [opened, saved, reopened, prepared, resumed, closed]:
            self.reports[value["stage"]] = value
            directory = self.second if value["stage"] in {"process-resumed", "closed"} else self.first
            self.write(directory / (value["stage"] + ".json"), value)
        self.cleanup = {
            "schema": 1, "qualification": driver.MARKER, "presentation_id": self.second_name,
            "process_id": 202, "process_mode": "resume-owned-once",
            "scope": "only the original factory-owned qualification query",
            "status": "OWNED_QUERY_ABSENCE_VERIFIED"
        }
        self.write(self.second / "credential-cleanup.json", self.cleanup)
        self.write(driver.OUT / "native-evidence-collection.json",
                   {"status": "NAMED_EVIDENCE_RETAINED", "account_repository_collected": False})
        self.write(self.checkpoint / "OriginalEditorQualificationClaim.json", {
            "runtimeNonce": process["process_runtime_nonce"],
            "scope": "fresh local-only original editor acceptance; no account reset or repository reuse"
        })
        self.request = {
            "workspaceNamespace": process["process_workspace_namespace"], "hostProfileID": common["profile_id"],
            "annotationUUID": common["annotation_uuid"], "legacyAnnotationID": 41, "revision": 1,
            "sourceWitnessSHA256": common["source_witness_sha256"], "payloadDigest": saved["payload_digest"],
            "nativeArchiveSHA256": archive_sha, "nativeBodySHA256": process["process_saved_body_sha256"]
        }
        self.checkpoint_value = {
            "schema": "original-editor-owned-process-resume/1", "runtimeNonce": process["process_runtime_nonce"],
            "bundleID": driver.BUNDLE, "accountID": process["process_account_id"],
            "spaceID": process["process_space_id"], "objectID": process["process_object_id"],
            "spaceCreationResponseSHA256": "4" * 64, "preparedProcessID": 101,
            "parentIdentity": {"device": 7, "inode": 11},
            "repositoryIdentity": {"device": 7, "inode": 12},
            "accountRepositoryIdentity": {"device": 7, "inode": 13}, "request": self.request
        }
        self.write(self.checkpoint / "OriginalEditorQualificationResume.json", self.checkpoint_value)
        self.attempt = {
            "schema": "original-editor-owned-process-resume-attempt/1",
            "runtimeNonce": process["process_runtime_nonce"], "preparedProcessID": 101, "resumingProcessID": 202
        }
        self.write(self.checkpoint / "OriginalEditorQualificationResumeAttempt.json", self.attempt)
        self.snapshots = driver.OUT / "native/snapshots"
        self.page = self.snapshots / "anytype-original-snapshot-11111111-1111-4111-8111-111111111111"
        self.export = self.snapshots / "anytype-original-snapshot-22222222-2222-4222-8222-222222222222"
        self.imported = self.snapshots / "anytype-original-snapshot-33333333-3333-4333-8333-333333333333"
        self.resumed_native = self.snapshots / "anytype-original-snapshot-44444444-4444-4444-8444-444444444444"
        for directory in [self.page, self.export, self.imported, self.resumed_native]:
            directory.mkdir(parents=True)
        for path in [
            self.page / "original-empty-page-create.pb", self.page / "original-empty-page-show.pb",
            self.export / "native-export-report.pb", self.imported / "original-restored-object-show.pb",
            self.resumed_native / "original-process-resume-object-show.pb"
        ]:
            path.write_bytes(b"explicit opaque synthetic response fixture")
        (self.export / "fixture.zip").write_bytes(self.archive)
        (self.imported / "original-native-import.zip").write_bytes(self.archive)
        self.write(self.imported / "native-root-map.json", {
            "archiveSHA256": archive_sha, "sourceObjectID": common["original_object_id"],
            "sourceSpaceID": common["original_space_id"], "mappedObjectID": process["process_object_id"],
            "targetSpaceID": process["process_space_id"]
        })

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def report(self, stage, **changes):
        value = copy.deepcopy(self.reports[stage])
        value.update(changes)
        self.write((self.second if stage in {"process-resumed", "closed"} else self.first) / (stage + ".json"), value)

    def denied(self):
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            driver.verify_native_receipts()

    def test_valid_distinct_processes_remain_observation_without_body_ack(self):
        result = driver.verify_native_receipts()
        self.assertEqual(result["process_ids"], [101, 202])
        self.assertEqual(result["original_object_id"], "original-restored-page")
        self.assertIsNone(result["native_snapshot_digest"])
        self.assertIs(result["body_acknowledgement_granted"], False)

    def test_same_pid_cannot_claim_process_restart(self):
        self.report("process-resumed", process_id=101)
        self.denied()

    def test_boolean_pid_is_not_an_integer_process(self):
        self.report("process-resumed", process_id=True)
        self.denied()

    def test_wrong_workspace_request_is_refused(self):
        self.request["workspaceNamespace"] = "99999999-9999-4999-8999-999999999999"
        self.write(self.checkpoint / "OriginalEditorQualificationResume.json", self.checkpoint_value)
        self.denied()

    def test_changed_saved_body_cannot_reuse_checkpoint(self):
        self.report("process-resumed", process_saved_body_sha256="9" * 64)
        self.denied()

    def test_foreign_annotation_cannot_reuse_native_object(self):
        self.report("process-resumed", annotation_uuid="99999999-9999-4999-8999-999999999999")
        self.denied()

    def test_unconsumed_credential_is_not_success(self):
        self.report("process-resumed", process_credential_consumed=False)
        self.denied()

    def test_never_owned_query_is_not_an_absence_receipt(self):
        self.cleanup["status"] = "NO_OWNED_QUERY"
        self.write(self.second / "credential-cleanup.json", self.cleanup)
        self.denied()

    def test_checkpoint_unknown_fields_are_refused(self):
        self.checkpoint_value["unreviewedMarker"] = True
        self.write(self.checkpoint / "OriginalEditorQualificationResume.json", self.checkpoint_value)
        self.denied()

    def test_duplicate_json_key_is_refused(self):
        path = self.first / "process-resume-prepared.json"
        raw = path.read_text()
        path.write_text('{"schema":2,' + raw.lstrip()[1:], encoding="utf-8")
        self.denied()

    def test_missing_original_show_cannot_claim_native_resume(self):
        (self.resumed_native / "original-process-resume-object-show.pb").unlink()
        self.denied()

    def test_extra_presentation_is_refused(self):
        (driver.OUT / "native/qualification/99999999-9999-4999-8999-999999999999").mkdir()
        self.denied()

    def test_real_symlink_report_is_refused(self):
        path = self.first / "saved.json"
        target = self.root / "outside-owned-report.json"
        path.replace(target)
        path.symlink_to(target)
        self.assertTrue(path.is_symlink())
        self.denied()

    def test_changed_export_bytes_cannot_reuse_archive_digest(self):
        (self.export / "fixture.zip").write_bytes(self.archive + b"changed")
        self.denied()

    def test_cleanup_for_another_process_is_refused(self):
        self.cleanup["process_id"] = 303
        self.write(self.second / "credential-cleanup.json", self.cleanup)
        self.denied()

    def test_wrong_one_shot_attempt_nonce_is_refused(self):
        self.attempt["runtimeNonce"] = "99999999-9999-4999-8999-999999999999"
        self.write(self.checkpoint / "OriginalEditorQualificationResumeAttempt.json", self.attempt)
        self.denied()

    def test_duplicate_native_response_is_refused(self):
        (self.export / "original-process-resume-object-show.pb").write_bytes(b"explicit extra synthetic response")
        self.denied()

    def capture_fixture(self, mutate=None):
        original_out = driver.OUT
        udid = "55555555-5555-4555-8555-555555555555"
        container = self.root / udid / "data/Containers/Data/Application/Fixture"
        shutil.copytree(original_out / "native/qualification", container / "Documents/original-editor-qualification")
        shutil.copytree(original_out / "native/process-checkpoint", container / "Library/Application Support/Anytype")
        shutil.copytree(original_out / "native/snapshots", container / "tmp")
        private = container / "Library/Application Support/Anytype/middleware-go/private-account"
        private.mkdir(parents=True)
        (private / "never-copy.fixture").write_text("SYNTHETIC_PRIVATE_DIRECTORY_SENTINEL", encoding="utf-8")
        if mutate:
            mutate(container)
        driver.OUT = self.root / "captured"
        evidence = driver.OriginalEditorEvidence()
        evidence.stage(udid, container, "11-reader", [driver.SELECTOR])
        def container_probe(command, **kwargs):
            self.assertEqual(command, ["xcrun", "simctl", "get_app_container", udid, driver.BUNDLE, "data"])
            self.assertEqual(kwargs, {"text": True, "timeout": 45})
            return str(container) + "\n"
        with mock.patch.object(driver.subprocess, "check_output", side_effect=container_probe) as command:
            with mock.patch.object(driver.subprocess, "run", side_effect=AssertionError("No subprocess may execute")):
                evidence.capture(udid, "11-reader")
        self.assertEqual(command.call_count, 1)
        return evidence, container

    def test_callback_retains_primary_failure_before_witness_rejection(self):
        failure_bytes = b'{"stage":"failed","failure_type":"SyntheticPrimaryFailure","schema":2}\n'
        def fail_first(container):
            first = container / "Documents/original-editor-qualification" / self.first_name
            (first / "failed.json").write_bytes(failure_bytes)
        evidence, _ = self.capture_fixture(fail_first)
        retained = driver.OUT / "native/qualification" / self.first_name / "failed.json"
        self.assertEqual(retained.read_bytes(), failure_bytes)
        self.assertEqual(evidence.state["status"], "NAMED_EVIDENCE_RETAINED")
        self.denied()
        self.assertEqual(retained.read_bytes(), failure_bytes)

    def test_callback_excludes_private_native_repository(self):
        evidence, _ = self.capture_fixture()
        self.assertFalse(evidence.state["account_repository_collected"])
        self.assertTrue(evidence.state["files"])
        for path in driver.OUT.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"SYNTHETIC_PRIVATE_DIRECTORY_SENTINEL", path.read_bytes())
        self.assertFalse(any("middleware-go" in item["path"] for item in evidence.state["files"]))

    def test_unknown_capture_file_is_refused_before_account_copy(self):
        def unexpected(container):
            (container / "tmp" / self.page.name / "unreviewed-native-output.bin").write_bytes(b"unreviewed")
        with self.assertRaisesRegex(RuntimeError, "Unexpected original native snapshot output"):
            self.capture_fixture(unexpected)
        collection = json.loads((driver.OUT / "native-evidence-collection.json").read_text())
        self.assertEqual(collection["status"], "COLLECTION_FAILED")
        self.assertFalse(collection["account_repository_collected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
