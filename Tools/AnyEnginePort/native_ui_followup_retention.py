#!/usr/bin/env python3
"""Retain two actual UI passes from the failed 450876 batch without relabelling it."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import native_continuation_sources as sources
import verify_native_test_execution as execution
from verify_archive_roundtrip import strict_json

RUN = "45087682296"
SOURCE = "7293e4fd0bcabdcdb643d5768b777b8e87ff1b73"
REPOSITORY = "davidpovarsky/anytype-swift"
BRANCH = "codex/chatgpt-wave15-acceptance-continuation-20261122"
MANIFEST = "Tools/AnyEnginePort/reviews/native-ui-followup-450876-originals.json"
MANIFEST_SHA = "5f6bc04960dd861cd8a81b38f74a5758c9279ef775a2d05cad1d068033422ea4"
REVIEW = "Tools/AnyEnginePort/reviews/native-ui-followup-450876-sources.json"
DIRECTORY = "retained-450876-originals"
PROFILE = "native-ui-continuation-four"
PASSED_NAMES = (
    "testExplicitHebrewDirectionAndAlignmentSurviveColdReopen",
    "testTopicAndWordLinksDriveDerivedRelatedDocumentsAfterColdReopen",
)
PASSED = {"NativeLaunchTests/" + name for name in PASSED_NAMES}
FAILED_NAMES = tuple(name for name in sources.FAILED_NAMES if name not in PASSED_NAMES)
FAILED = {"NativeLaunchTests/" + name for name in FAILED_NAMES}
ARCHIVE_VIEW = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift"
ALLOWED_INACTIVE = {ARCHIVE_VIEW}
sha, require = sources.sha, sources.require


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8 * 1024**2,
            "followup_regular_bounded_file_required")
    return path.read_bytes()


def data(path):
    return strict_json(read(path))


def manifest(root=sources.ROOT):
    raw = read(root / MANIFEST)
    require(sha(raw) == MANIFEST_SHA, "followup_original_manifest_changed")
    return strict_json(raw)


def verify_api(run, artifact, expected):
    require(type(run.get("id")) is int and run["id"] == int(RUN)
            and type(run.get("run_attempt")) is int and run["run_attempt"] == 1
            and run.get("head_sha") == SOURCE and run.get("head_branch") == BRANCH
            and run.get("status") == "completed" and run.get("conclusion") == "failure"
            and run.get("event") == "workflow_dispatch"
            and run.get("path") == ".github/workflows/pinkha-any-engine-port.yml"
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("head_repository", {}).get("full_name") == REPOSITORY,
            "followup_original_failed_run_identity_changed")
    require(type(artifact.get("id")) is int and artifact["id"] == expected["artifactID"]
            and artifact.get("expired") is False and artifact.get("name") == expected["artifactName"]
            and artifact.get("digest") == "sha256:" + expected["archiveSHA256"]
            and artifact.get("size_in_bytes") == expected["archiveBytes"]
            and artifact.get("workflow_run", {}).get("id") == int(RUN)
            and artifact.get("workflow_run", {}).get("head_sha") == SOURCE,
            "followup_original_artifact_identity_changed")


def fetch_originals(download, destination, legacy_destination, base, root=sources.ROOT):
    """Download once; the new original also contains the exact earlier retained proof."""
    expected = manifest(root)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "unexpected_followup_repository")
    download.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, route in (("run", "runs/" + RUN + "/attempts/1"),
                        ("artifact", "artifacts/" + str(expected["artifactID"]))):
        raw = subprocess.check_output(["gh", "api", "repos/" + REPOSITORY + "/actions/" + route])
        records[name] = strict_json(raw)
        (download / (name + ".json")).write_bytes(raw)
    verify_api(records["run"], records["artifact"], expected)
    archive = download / "original.zip"
    with archive.open("xb") as stream:
        subprocess.run(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" +
                        str(expected["artifactID"]) + "/zip"], stdout=stream, check=True)
    base.extract_selected(archive, destination, expected)
    for name in records:
        shutil.copyfile(download / (name + ".json"), destination / (name + "-metadata.json"))
    require(not legacy_destination.exists(), "legacy_retained_destination_must_be_new")
    shutil.copytree(destination / base.RETAINED_DIR, legacy_destination)
    # This validates the same original20 and its original8 lineage before the
    # consumer's existing admission independently checks it again.
    base.verify_originals(legacy_destination, root)


def verify_raw_results(summary, tree, record, simulator, raw_log, base):
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(value) is int for value in counts.values())
            and counts == dict(totalTestCount=6, passedTests=2, failedTests=4, skippedTests=0),
            "original_followup_failed_batch_must_remain_two_pass_four_fail")
    expected = {name + "()": "Passed" for name in PASSED} | {name + "()": "Failed" for name in FAILED}
    cases = execution.test_cases(tree)
    require(cases == expected, "original_followup_named_terminal_inventory_changed")
    configurations = summary.get("devicesAndConfigurations")
    require(isinstance(configurations, list) and len(configurations) == 1, "one_original_followup_device_required")
    device = configurations[0].get("device", {})
    require(isinstance(device.get("deviceId"), str)
            and device["deviceId"].lower() == simulator["ownedUDID"].lower()
            and str(device.get("osVersion", "")).split(".")[0] == "27"
            and device.get("architecture") == "arm64" and device.get("osBuildNumber"),
            "original_followup_owned_simulator_changed")
    require(record.get("status") == "FAIL" and record.get("profile") == "native-ui-continuation-six"
            and record.get("commit") == SOURCE and record.get("scope") == "actual_named_apple_test_execution"
            and record.get("observationOnly") is False and record.get("fullAcceptance") is False,
            "original_followup_failure_receipt_relabelled")
    base.verify_log(raw_log, cases)
    return dict(device=device, originalCases=cases, counts=counts, retainedMethods=sorted(PASSED))


def verify_originals(directory, base, root=sources.ROOT):
    expected = manifest(root)
    verify_api(data(directory / "run-metadata.json"), data(directory / "artifact-metadata.json"), expected)
    for name, identity in expected["files"].items():
        raw = read(directory / name)
        require(len(raw) == identity["bytes"] and sha(raw) == identity["sha256"],
                "original_followup_file_changed_" + name)
    require(read(directory / "source-sha.txt").decode().strip() == SOURCE, "original_followup_source_changed")
    stem = "native-ui-continuation"
    record = data(directory / (stem + "-named-execution.json"))
    summary = data(directory / (stem + "-test-counts.json"))
    tree = data(directory / (stem + "-test-methods.json"))
    simulator = data(directory / "simulator.json")
    observed = verify_raw_results(summary, tree, record, simulator, read(directory / (stem + ".log")), base)
    for field, path in (("summarySHA256", stem + "-test-counts.json"),
                        ("testTreeSHA256", stem + "-test-methods.json")):
        require(record.get(field) == sha(read(directory / path)), "original_followup_result_binding_changed")
    require(record.get("runnerSHA256") == sha(sources.source(SOURCE, "Tools/AnyEnginePort/verify_native_test_execution.py", root))
            and record.get("testSources") == {sources.TEST: sha(sources.source(SOURCE, sources.TEST, root))},
            "original_followup_test_or_verifier_source_changed")
    frozen = data(directory / "native-shared-products.json")
    retained = data(directory / "native-continuation-retained.json")
    preflight = data(directory / "native-ui-continuation-products-preflight.json")
    require(frozen.get("status") == "FROZEN_BUILD_INPUTS" and frozen.get("commit") == SOURCE
            and frozen.get("githubRunID") == RUN and frozen.get("ownedSimulatorUDID") == simulator["ownedUDID"]
            and frozen.get("continuationAdmissionSHA256") == sha(read(directory / "native-continuation-retained.json"))
            and preflight.get("status") == "UNCHANGED_BUILD_INPUTS"
            and preflight.get("frozenBuildSHA256") == sha(read(directory / "native-shared-products.json")),
            "original_followup_compiled_product_preflight_changed")
    require(retained.get("status") == "VERIFIED_REUSE" and retained.get("consumerCommit") == SOURCE
            and retained.get("consumerRunID") == RUN and retained.get("retainedMethodCount") == 20
            and retained.get("testsExecutedThisRun") == 0, "original_followup_previous_retention_changed")
    for path, expected_sha in frozen["sourceInputs"].items():
        require(sha(sources.source(SOURCE, path, root)) == expected_sha,
                "original_followup_frozen_source_changed_" + path)
    return {**observed, "originalArtifactID": expected["artifactID"],
            "originalArchiveSHA256": expected["archiveSHA256"], "originalSourceCommit": SOURCE,
            "originalRunID": RUN, "originalFailedBatchStatus": "FAIL",
            "originalNamedReceiptSHA256": sha(read(directory / (stem + "-named-execution.json")))}


def declaration_proof(before, after):
    masks = (*FAILED_NAMES, sources.FILES_NAME, sources.HANLIN_HELPER)
    for name in PASSED_NAMES:
        a, b = sources.declaration(before, name)
        c, d = sources.declaration(after, name)
        require(before[a:b] == after[c:d], "newly_passed_method_changed_" + name)
    def masked(raw):
        for name in masks:
            a, b = sources.declaration(raw, name)
            raw = raw[:a] + ("    // STILL_PENDING " + name + "\n").encode() + raw[b:]
        return raw
    require(masked(before) == masked(after), "newly_passed_common_helpers_or_other_methods_changed")
    # Existing source admission additionally proves the Hanlin helper has only
    # the one failed Hanlin caller and its own declaration.
    sources.verify_test_declarations(before, after)
    return dict(retainedDeclarationsByteIdentical=list(PASSED_NAMES),
                commonHelpersAndOtherDeclarationsByteIdentical=True,
                unchangedRemainderSHA256=sha(masked(before)),
                remainingFailedDeclarations=list(FAILED_NAMES))


def verify_sources(consumer, root=sources.ROOT):
    before, after = sources.source_tree(SOURCE, root), sources.source_tree(consumer, root)
    review = data(root / REVIEW)
    require(set(review) == {"schemaVersion", "producerCommit", "inactiveSourceChanges"}
            and type(review["schemaVersion"]) is int and review["schemaVersion"] == 1
            and review["producerCommit"] == SOURCE and isinstance(review["inactiveSourceChanges"], list),
            "followup_source_review_shape_changed")
    entries = review["inactiveSourceChanges"]
    names = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    require(len(names) == len(entries) == len(set(names)) and set(names) <= ALLOWED_INACTIVE,
            "followup_source_review_outside_inactive_archive_ui")
    changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    require(changed == {sources.TEST} | set(names), "followup_production_or_dependency_closure_changed")
    for entry in entries:
        name = entry["path"]
        require(set(entry) == {"path", "beforeSHA256", "afterSHA256", "beforeGitBlob", "afterGitBlob", "reason", "declarations"}
                and isinstance(entry["reason"], str) and len(entry["reason"]) >= 160
                and isinstance(entry["declarations"], list) and entry["declarations"],
                "followup_inactive_source_review_incomplete")
        old, new = sources.source(SOURCE, name, root), sources.source(consumer, name, root)
        require(entry["beforeSHA256"] == sha(old) and entry["afterSHA256"] == sha(new)
                and entry["beforeGitBlob"] == before[name] == sources.blob(old)
                and entry["afterGitBlob"] == after[name] == sources.blob(new),
                "followup_inactive_source_bytes_changed")
    test_proof = declaration_proof(sources.source(SOURCE, sources.TEST, root),
                                   sources.source(consumer, sources.TEST, root))
    return dict(producerClosureSHA256=sources.canonical(before), consumerClosureSHA256=sources.canonical(after),
                unchangedProtectedFileCount=len(before) - len(changed), changedProtectedPaths=sorted(changed),
                testDeclarationProof=test_proof, inactiveArchiveSourceReview=entries,
                reviewSHA256=sha(read(root / REVIEW)))


def extend_retention(retained, evidence, base, root=sources.ROOT):
    directory = evidence / DIRECTORY
    observed = verify_originals(directory, base, root)
    simulator = data(evidence / "simulator.json")
    original_simulator = data(directory / "simulator.json")
    require(all(simulator.get(key) == original_simulator.get(key) for key in ("runtime", "deviceType"))
            and read(evidence / "xcode-version.txt") == read(directory / "xcode-version.txt")
            and observed["device"]["osVersion"] == retained["originalDevice"]["osVersion"]
            and observed["device"]["osBuildNumber"] == retained["originalDevice"]["osBuildNumber"],
            "followup_retained_platform_changed")
    current_binding = data(root / "Modules/PinkhaAnyRuntime/Vendor/consumer-binding.json")
    original_binding = data(directory / "native-reuse.json")
    require(current_binding == {**original_binding, "consumerCommit": retained["consumerCommit"]},
            "followup_native_binary_or_source_changed")
    source_proof = verify_sources(retained["consumerCommit"], root)
    origins = dict(retained["retainedMethodsWithOrigins"])
    require(not set(origins).intersection(PASSED) and len(origins) == 20,
            "followup_retained_origin_overlap")
    origins.update({name: dict(runID=RUN, commit=SOURCE) for name in PASSED})
    require(len(origins) == 22, "followup_retained_origin_count_changed")
    return {**retained, "retainedMethodsWithOrigins": origins, "retainedMethodCount": 22,
            "currentProfile": PROFILE, "currentFailedMethods": sorted(FAILED),
            "followupOriginalProof": observed, "followupSourceProof": source_proof,
            "claimBoundary": "Twenty-two methods retain their original run/source. Both failed original batches remain FAIL. Only the four remaining failed native UI methods, Files and unexecuted Type/history may execute in this continuation."}
