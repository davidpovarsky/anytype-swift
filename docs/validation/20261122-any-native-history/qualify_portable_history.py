#!/usr/bin/env python3
"""Qualify preserved original history controls without executing product tests."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "validation/portable-originals"
EXPECTED_XCTEST = {
    "testReaderKeepsNativeOrderOpaqueFieldsAndReaderAuthority",
    "testDenialBeforeAndAfterReadNeverReturnsPayload",
    "testNativeDocumentGenerationChangeRejectsHistoricalReply",
    "testCursorCannotCrossObjectAccountSpaceGenerationOrRun",
    "testDuplicateAndStalledPagesAreExplicitFailures",
    "testVersionKeepsUnknownDatasetsBlockTypesAndIntegerValues",
    "testMissingTruncatedOversizeAndPermissionRemainDistinct",
    "testVersionAndRecordBoundsDoNotPretendDataIsEmpty",
    "testRevokedSessionDoesNotDeliverAReplyThatIgnoresCancellation",
}
EXPECTED_TESTING = {
    "supersededVersionCannotReplaceTheCurrentSelection",
    "pageFailureRetiresAnInFlightVersionEvenWhenItIgnoresCancellation",
    "refreshCannotBeRepopulatedByThePreviousPreview",
    "MountedOwnerRevocationClearsAllHistoricalData",
    "missingTruncatedAndLargeVersionsNeverBecomeEmptySuccess",
    "paginationStopsAtTwentyPagesAndKeepsNativeOrder",
    "listedTruncationDoesNotDispatchACompleteVersionRead",
}
EXPECTED_DEPENDENCIES = {
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "torahinspectorkit": "511454e49450cb2581ddf77f644146ff3e30dbef",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def qualify():
    original_manifest = json.loads((ORIGINAL / "ORIGINALS_MANIFEST.json").read_text())
    for item in original_manifest["files"]:
        data = (ORIGINAL / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"]
    receipt_bytes = (ORIGINAL / "attempt-4/result.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    before_bytes = (ORIGINAL / "attempt-4/source-before.json").read_bytes()
    before = json.loads(before_bytes)
    log_bytes = (ORIGINAL / "attempt-4/swift-test.log").read_bytes()
    log = log_bytes.decode("utf-8")
    assert sha(log_bytes) == receipt["raw_log_sha256"] == "68aa337fe3ffcf434a7847e0577d90d14252a1939c910b6d27c0376fe8b27055"
    assert receipt["status"] == "PASS" and receipt["exit_code"] == 0 and receipt["attempt"] == 4
    assert receipt["command"][-2:] == ["--filter", "NativeHistoryReaderTests|AnyNativeHistoryPresentationTests"]
    assert receipt["app_sha"] == before["app_sha"] == "bf5b2fb4e0b446f8e13c04c8f9d8c16a44b41345"
    assert receipt["git_tracked_sources_unchanged"] is True
    assert receipt["git_tracked_source_count"] == len(before["git_tracked_sources"]) == 233
    assert receipt["source_before"] == receipt["source_after"] == before["new_sources"]
    assert len(receipt["source_before"]) == 6
    owned = json.loads((ROOT / "APP01_HISTORY_FILES.json").read_text())["files"]
    assert len(owned) == 6
    for item in owned:
        data = (ROOT / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"]
    assert sorted(item["sha256"] for item in owned) == sorted(receipt["source_before"].values())
    dependencies = {
        item["path"].replace("\\", "/").rsplit("/", 1)[-1].lower(): item["sha"]
        for item in receipt["dependencies"]
    }
    assert dependencies == EXPECTED_DEPENDENCIES
    assert all(item["tracked_clean"] is True for item in receipt["dependencies"])
    pins = json.loads((ORIGINAL / "Package.resolved").read_text())["pins"]
    assert {item["identity"]: item["state"]["revision"] for item in pins} == EXPECTED_DEPENDENCIES
    x_started = re.findall(r"Test Case 'NativeHistoryReaderTests\.(\w+)' started", log)
    x_passed = re.findall(r"Test Case 'NativeHistoryReaderTests\.(\w+)' passed", log)
    s_started = re.findall(r"◊ Test (\w+)\(\) started\.", log)
    s_passed = re.findall(r"√ Test (\w+)\(\) passed after", log)
    assert len(x_started) == len(x_passed) == 9 and set(x_started) == set(x_passed) == EXPECTED_XCTEST
    assert len(s_started) == len(s_passed) == 7 and set(s_started) == set(s_passed) == EXPECTED_TESTING
    assert "Executed 9 tests, with 0 failures (0 unexpected)" in log
    assert "Test run with 7 tests in 1 suite passed" in log
    assert not re.search(r"Test Case .+ (?:failed|skipped)|Test \w+\(\) (?:failed|skipped)|✘", log)
    assert "Build complete!" in log
    for attempt in (1, 2, 3):
        prior = json.loads((ORIGINAL / f"attempt-{attempt}/result.json").read_text())
        assert prior["exit_code"] == 124
        assert not re.search(r"Test Case .+ started|◊ Test \w+\(\) started", (ORIGINAL / f"attempt-{attempt}/swift-test.log").read_text())
    return {
        "schema_version": 1,
        "status": "PASS_FOCUSED_PORTABLE_HISTORY_CONTROLS",
        "sentinel_job_id": "job_82914797a4fc",
        "runtime": "Swift 6.3.3, x86_64-unknown-windows-msvc",
        "executed_methods": 16, "passed_methods": 16, "failed_methods": 0, "skipped_methods": 0,
        "xctest_methods": sorted(EXPECTED_XCTEST), "swift_testing_methods": sorted(EXPECTED_TESTING),
        "original_receipt_sha256": sha(receipt_bytes), "raw_log_sha256": sha(log_bytes),
        "source_before_sha256": sha(before_bytes), "git_tracked_source_count": 233,
        "baseline_app_sha": receipt["app_sha"], "owned_source_sha256": receipt["source_before"],
        "dependencies": dependencies,
        "prior_attempts": "Three dependency/build timeouts, no test methods executed; originals retained without relabeling.",
        "harness": "Exact production Host/Engine/Integration/Kit sources with local package wiring and two selected new test suites. No dependency stubs.",
        "apple_typecheck": "NOT_RUN", "native_history_http": "NOT_RUN", "native_acl_transition": "NOT_RUN",
        "mounted_history_acceptance": "NOT_RUN", "physical_device": "NOT_RUN", "full_APP01": "OPEN",
        "scope": "Scripted transport and authority controls for actual history reader, session, model, and publication lifecycle. Windows excludes conditional SwiftUI/UIKit view bodies.",
    }


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2, sort_keys=True))
