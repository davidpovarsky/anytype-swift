#!/usr/bin/env python3
"""Verify prior UIKit execution and unchanged tested sources; never report a rerun."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import verify_native_test_execution as execution

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "ui-ios-remaining"
RECEIPT = "ui-ios-named-execution.json"
FILES = (RECEIPT, "ui-ios-test-counts.json", "ui-ios-test-methods.json",
         "source-sha.txt", "simulator.json", "xcode-version.txt")
# These cover the actual UITextView subclass, focus/composition/markdown code,
# common rendering policy, native identity types, editor models and package pins.
# The archive sheet has no execution path in these fourteen component methods;
# any change there must still compile and run in the separate native UI gate.
EXCLUDED_SOURCE = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift"
PROTECTED_PATHS = [
    "Modules/PinkhaAnyUI/Sources",
    "Modules/PinkhaAnyEngine/Sources",
    "Modules/PinkhaAnyHost/Sources",
    "Modules/PinkhaKit/Sources/PinkhaKit/Editor",
    "Modules/PinkhaKit/Sources/PinkhaKit/RTL",
    *execution.SOURCE_PATHS[PROFILE],
    "Modules/PinkhaAnyUI/Package.swift", "Modules/PinkhaAnyUI/Package.resolved",
    "Modules/PinkhaAnyEngine/Package.swift", "Modules/PinkhaAnyHost/Package.swift",
    "Modules/PinkhaAnyIntegration/Package.swift", "Modules/PinkhaAnyHanlin/Package.swift",
    "Modules/PinkhaTorahPresentation/Package.swift", "Modules/PinkhaKit/Package.swift",
]


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(*args: str, root: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def producer_file(commit: str, path: str, root: Path = ROOT) -> bytes:
    return git("show", commit + ":" + path, root=root)


def verify_evidence(directory: Path, producer: str, run_id: str, read_source=producer_file) -> dict:
    require(re.fullmatch(r"[0-9a-f]{40}", producer) is not None, "invalid_producer_commit")
    require(run_id.isdigit(), "invalid_producer_run")
    original = read_json(directory / RECEIPT)
    require((directory / "source-sha.txt").read_text().strip() == producer,
            "artifact_source_identity_mismatch")
    require(original.get("status") == "PASS" and original.get("profile") == PROFILE and
            original.get("commit") == producer and
            original.get("scope") == "actual_named_apple_test_execution" and
            original.get("observationOnly") is False, "original_execution_not_accepted")
    require(original.get("runnerSHA256") ==
            digest(read_source(producer, "Tools/AnyEnginePort/verify_native_test_execution.py")),
            "producer_verifier_identity_mismatch")
    expected_sources = {path: digest(read_source(producer, path))
                        for path in execution.SOURCE_PATHS[PROFILE]}
    require(original.get("testSources") == expected_sources, "producer_test_sources_mismatch")
    require(original.get("summarySHA256") == digest((directory / FILES[1]).read_bytes()) and
            original.get("testTreeSHA256") == digest((directory / FILES[2]).read_bytes()),
            "original_result_digest_mismatch")
    simulator = read_json(directory / "simulator.json")
    udid = simulator.get("ownedUDID")
    require(isinstance(udid, str) and udid, "original_simulator_missing")
    validated = execution.validate(read_json(directory / FILES[1]),
                                   read_json(directory / FILES[2]), PROFILE, udid)
    require(validated["counts"]["totalTestCount"] == 14 and len(validated["actualCases"]) == 14,
            "original_execution_count_mismatch")
    require(validated["device"].get("deviceName") == "AnyNativePort-" + run_id,
            "original_execution_run_mismatch")
    for key, value in validated.items():
        require(original.get(key) == value, "original_receipt_result_mismatch_" + key)
    return original


def source_tree(commit: str, root: Path = ROOT) -> dict[str, str]:
    result = {}
    for record in git("ls-tree", "-rz", commit, "--", *PROTECTED_PATHS, root=root).split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, kind, object_id = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        if path == EXCLUDED_SOURCE:
            continue
        require(kind == "blob" and mode in {"100644", "100755"}, "unsupported_source_entry")
        result[path] = object_id
    require(all(path in result for path in execution.SOURCE_PATHS[PROFILE]),
            "protected_test_source_missing")
    return result


def verify_sources(producer: str, consumer: str, root: Path = ROOT) -> dict[str, str]:
    original = source_tree(producer, root)
    current = source_tree(consumer, root)
    require(original == current, "tested_source_or_dependency_changed_requires_new_execution")
    dirty = git("diff", "--name-only", "-z", "HEAD", "--", *PROTECTED_PATHS, root=root)
    untracked = git("ls-files", "--others", "--exclude-standard", "-z",
                    "--", *PROTECTED_PATHS, root=root)
    require(all(not path or path.decode("utf-8") == EXCLUDED_SOURCE
                for path in (dirty + untracked).split(b"\0")), "tested_worktree_source_is_dirty")
    return current


# Only individually reviewed, unexecuted files may differ in this component
# profile. No directory wildcard or changed renderer/focus/test source can be
# excused by a review record. Every permitted difference is bound to both blobs.
REVIEWABLE_UNEXECUTED_PATHS = frozenset({
    "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSerialTextEditQueue.swift",
    "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift",
    "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift",
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyHostAuthorizedTorahOperationReader.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertiesView.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditorDiagnostics.swift",
    # Exact related-authority source and pin changes reviewed at Kit511454.
    "Modules/PinkhaAnyUI/Package.resolved",
    "Modules/PinkhaAnyUI/Package.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyTorahPresentationBridge.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyTorahRelatedReadFailure.swift",
    "Modules/PinkhaKit/Package.swift",
    "Modules/PinkhaTorahPresentation/Package.swift",
})
REVIEW_CLAIM = "not_executed_by_original_fourteen_methods"


def verify_reviewed_source_maps(original: dict[str, str], current: dict[str, str],
                                review: dict, producer: str, run_id: str) -> tuple[dict, list]:
    require(review.get("schemaVersion") == 1 and review.get("profile") == PROFILE and
            review.get("producerCommit") == producer and review.get("producerRunID") == run_id,
            "review_producer_or_profile_mismatch")
    require(review.get("claim") == REVIEW_CLAIM, "review_cannot_relabel_changed_source_as_passed")
    require(review.get("requiredMethods") == sorted(execution.expected_methods(PROFILE)),
            "review_required_methods_changed")
    expected_tests = {path: original.get(path) for path in execution.SOURCE_PATHS[PROFILE]}
    require(all(expected_tests.values()) and review.get("testSourceGitBlobs") == expected_tests,
            "review_test_sources_mismatch")
    entries = review.get("reviewedChanges")
    require(isinstance(entries, list) and entries, "missing_reviewed_changes")
    paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    require(len(paths) == len(entries) and len(paths) == len(set(paths)) and
            set(paths) <= REVIEWABLE_UNEXECUTED_PATHS, "unreviewable_or_duplicate_source_change")
    changed = {path for path in original.keys() | current.keys()
               if original.get(path) != current.get(path)}
    require(changed == set(paths), "new_or_missing_source_difference_requires_review")
    for entry in entries:
        path = entry["path"]
        require(set(entry) == {"path", "beforeGitBlob", "afterGitBlob", "claim", "reason"} and
                entry["claim"] == REVIEW_CLAIM and isinstance(entry["reason"], str) and
                len(entry["reason"]) >= 60, "incomplete_or_relabelled_source_review")
        before, after = original.get(path), current.get(path)
        require(entry["beforeGitBlob"] == before and entry["afterGitBlob"] == after and
                isinstance(after, str) and re.fullmatch(r"[0-9a-f]{40}", after) is not None and
                before != after, "reviewed_source_blob_mismatch")
    # These are the only entries described as unchanged in the new consumer.
    return {path: blob for path, blob in current.items() if path not in changed}, entries


def verify_reviewed_sources(producer: str, consumer: str, run_id: str, review_path: Path,
                            root: Path = ROOT) -> tuple[dict, dict]:
    original, current = source_tree(producer, root), source_tree(consumer, root)
    data = review_path.read_bytes()
    sources, entries = verify_reviewed_source_maps(original, current, json.loads(data), producer, run_id)
    dirty = git("diff", "--name-only", "-z", "HEAD", "--", *PROTECTED_PATHS, root=root)
    untracked = git("ls-files", "--others", "--exclude-standard", "-z",
                    "--", *PROTECTED_PATHS, root=root)
    require(all(not path or path.decode("utf-8") == EXCLUDED_SOURCE
                for path in (dirty + untracked).split(b"\0")), "tested_worktree_source_is_dirty")
    return sources, {"reviewSHA256": digest(data), "claim": REVIEW_CLAIM,
                     "reviewedDifferentSource": entries,
                     "executedChangedSourceCountInOriginalRun": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--producer-run", required=True)
    parser.add_argument("--consumer-simulator", required=True, type=Path)
    parser.add_argument("--consumer-xcode-version", required=True, type=Path)
    parser.add_argument("--reviewed-source-changes", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL",
              "scope": "verified_prior_uikit_execution_reuse",
              "testsExecutedThisRun": 0, "fullAcceptance": False,
              "claimBoundary": "Fourteen unchanged component methods executed only in the original producer run.",
              "producerCommit": args.producer_commit, "producerRunID": args.producer_run,
              "runnerSHA256": digest(Path(__file__).read_bytes())}
    try:
        consumer = git("rev-parse", "HEAD").decode("ascii").strip()
        record["consumerCommit"] = consumer
        original = verify_evidence(args.evidence, args.producer_commit, args.producer_run)
        reviewed = None
        if args.reviewed_source_changes is not None:
            sources, reviewed = verify_reviewed_sources(args.producer_commit, consumer,
                args.producer_run, args.reviewed_source_changes)
        else:
            sources = verify_sources(args.producer_commit, consumer)
        previous_simulator = read_json(args.evidence / "simulator.json")
        current_simulator = read_json(args.consumer_simulator)
        require(all(previous_simulator.get(key) and
                    previous_simulator[key] == current_simulator.get(key)
                    for key in ("runtime", "deviceType")), "simulator_platform_changed_requires_new_execution")
        require((args.evidence / "xcode-version.txt").read_text().strip() ==
                args.consumer_xcode_version.read_text().strip(),
                "apple_toolchain_changed_requires_new_execution")
        destination = args.output.parent / "reused-ui-ios"
        require(destination.resolve() != args.evidence.resolve(), "original_evidence_must_be_preserved")
        destination.mkdir(parents=True, exist_ok=True)
        original_files = {}
        for name in FILES:
            shutil.copyfile(args.evidence / name, destination / name)
            original_files[name] = digest((destination / name).read_bytes())
        record.update(status="VERIFIED_REUSE", originalExecutedCount=14,
                      originalMethods=original["requiredMethods"], originalFiles=original_files,
                      originalReceiptPath="reused-ui-ios/" + RECEIPT,
                      unchangedSourceGitBlobs=sources, excludedUnexecutedSource=EXCLUDED_SOURCE,
                      originalDevice=original["device"])
        if reviewed is not None:
            record["sourceReview"] = reviewed
            record["claimBoundary"] = (
                "Fourteen unchanged component methods executed only in the original producer. "
                "The exact reviewed different files were not executed by those methods; "
                "their changed behavior is not covered by the original PASS."
            )
    except Exception as error:
        record["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record.items()
                      if key not in {"unchangedSourceGitBlobs", "originalMethods"}}, indent=2))
    return 0 if record["status"] == "VERIFIED_REUSE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
