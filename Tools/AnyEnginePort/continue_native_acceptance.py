#!/usr/bin/env python3
"""Retain exact original passes and qualify only newly executed Any UI journeys."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

import native_continuation_sources as sources
import reuse_uikit_execution as original
import reuse_uikit_unaffected_eight as eight
import verify_focus_handoff_execution as focus
import verify_native_test_execution as execution
from verify_archive_roundtrip import strict_json

ROOT = sources.ROOT
RUN = "45038244641"
REPOSITORY = "davidpovarsky/anytype-swift"
BRANCH = "codex/chatgpt-wave15-shared-20261121"
CONTINUATION_BRANCH = "codex/chatgpt-wave15-acceptance-continuation-20261122"
MANIFEST = "Tools/AnyEnginePort/reviews/native-ui-continuation-450382-originals.json"
MANIFEST_SHA = "1f8d5aedfa8bb16fc7eb7ed21cef45376897f6d2ddd305642cac5c77a33cbb93"
SELF = "Tools/AnyEnginePort/continue_native_acceptance.py"
HELPERS = (SELF, "Tools/AnyEnginePort/native_continuation_sources.py",
           "Tools/AnyEnginePort/verify_native_test_execution.py",
           "Tools/AnyEnginePort/verify_custom_type.py")
PROFILE = "native-ui-continuation-six"
HISTORY_PROFILE = "native-history"
ENTRY = "NativeLaunchTests/testCreateEditHanlinConsentBackgroundAndColdReopen"
QUOTE = "NativeLaunchTests/testSourceInspectorQuoteAndNoteSurviveColdReopen"
FILES = "NativeLaunchTests/" + sources.FILES_NAME
CUSTOM = "NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen"
HISTORY = "NativeHistoryTests/" + sources.HISTORY_NAME
SIX = {"NativeLaunchTests/" + name for name in sources.FAILED_NAMES}
RETAINED_DIR = "retained-450382-originals"
sha, require = sources.sha, sources.require


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8 * 1024 * 1024,
            "regular_bounded_evidence_file_required")
    return path.read_bytes()


def data(path):
    return strict_json(read(path))


def manifest(root=ROOT):
    raw = read(root / MANIFEST)
    require(sha(raw) == MANIFEST_SHA, "original_evidence_manifest_changed")
    return strict_json(raw)


def verify_api(run, artifact, contract):
    require(run.get("id") == int(RUN) and run.get("head_sha") == sources.PRODUCER and
            run.get("head_branch") == BRANCH and run.get("run_attempt") == 1 and
            run.get("event") == "workflow_dispatch" and run.get("status") == "completed" and
            run.get("conclusion") == "failure" and
            run.get("path") == ".github/workflows/pinkha-any-engine-port.yml" and
            run.get("repository", {}).get("full_name") == REPOSITORY and
            run.get("head_repository", {}).get("full_name") == REPOSITORY,
            "original_failed_run_identity_mismatch")
    require(artifact.get("id") == contract["artifactID"] and artifact.get("expired") is False and
            artifact.get("name") == "any-engine-port-ios-patched-runtime-" + sources.PRODUCER and
            artifact.get("size_in_bytes") == contract["archiveBytes"] and
            artifact.get("digest") == "sha256:" + contract["archiveSHA256"] and
            artifact.get("workflow_run", {}).get("id") == int(RUN) and
            artifact.get("workflow_run", {}).get("head_sha") == sources.PRODUCER,
            "original_artifact_identity_mismatch")


def extract_selected(archive, destination, contract):
    require(not destination.exists() and not destination.is_symlink(), "original_destination_must_be_new")
    require(archive.stat().st_size == contract["archiveBytes"], "original_zip_size_mismatch")
    digest = __import__("hashlib").sha256()
    with archive.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    require(digest.hexdigest() == contract["archiveSHA256"], "original_zip_digest_mismatch")
    with zipfile.ZipFile(archive) as container:
        infos = container.infolist()
        require(0 < len(infos) <= 6000 and sum(item.file_size for item in infos) <= 2 * 1024**3,
                "original_zip_limits")
        seen = set()
        for item in infos:
            name = item.filename
            path = PurePosixPath(name)
            require(name and "\\" not in name and "\0" not in name and not path.is_absolute() and
                    all(part not in {"", ".", ".."} for part in name.rstrip("/").split("/")) and
                    name.casefold() not in seen and
                    stat.S_IFMT(item.external_attr >> 16) in {0, stat.S_IFREG, stat.S_IFDIR},
                    "unsafe_or_duplicate_original_zip_entry")
            seen.add(name.casefold())
        names = {item.filename: item for item in infos}
        require(set(contract["files"]) <= names.keys(), "original_proof_files_missing")
        destination.mkdir(parents=True)
        for name, expected in contract["files"].items():
            item = names[name]
            require(not item.is_dir() and item.file_size == expected["bytes"] <= 8 * 1024 * 1024,
                    "original_proof_entry_size_mismatch")
            raw = container.read(item)
            require(sha(raw) == expected["sha256"], "original_proof_entry_digest_mismatch")
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(raw)


def fetch_originals(download, destination, root=ROOT):
    contract = manifest(root)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "unexpected_consumer_repository")
    download.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, route in (("run", "runs/" + RUN), ("artifact", "artifacts/" + str(contract["artifactID"]))):
        raw = subprocess.check_output(["gh", "api", "repos/" + REPOSITORY + "/actions/" + route])
        records[name] = strict_json(raw)
        (download / (name + ".json")).write_bytes(raw)
    verify_api(records["run"], records["artifact"], contract)
    archive = download / "original.zip"
    with archive.open("xb") as stream:
        subprocess.run(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" +
                        str(contract["artifactID"]) + "/zip"], stdout=stream, check=True)
    extract_selected(archive, destination, contract)
    for name in records:
        (destination / (name + "-metadata.json")).write_bytes(read(download / (name + ".json")))


def verify_log(raw, cases):
    text = raw.decode("utf-8")
    pattern = r"Test Case '-\[[^.]+\.(\w+) (\w+)\]' (started|passed|failed|skipped)"
    found = re.findall(pattern, text)
    starts, finishes = [], {}
    for suite, method, outcome in found:
        name = suite + "/" + method
        if outcome == "started":
            starts.append(name)
        else:
            require(name not in finishes, "duplicate_original_terminal")
            finishes[name] = outcome.capitalize()
    expected = {name.removesuffix("()"): result for name, result in cases.items()}
    require(len(starts) == len(expected) and set(starts) == set(expected) and finishes == expected,
            "raw_terminal_inventory_mismatch")


def verify_raw_results(directory):
    simulator = data(directory / "simulator.json")
    udid = simulator["ownedUDID"]
    verified = {}
    for stem, profile in (("ui-focus-handoff", focus.PROFILE), ("native-ui", "native-ui-entry")):
        receipt = data(directory / (stem + "-named-execution.json"))
        summary, tree = (data(directory / (stem + suffix)) for suffix in ("-test-counts.json", "-test-methods.json"))
        actual = focus.validate(summary, tree, udid) if profile == focus.PROFILE else execution.validate(summary, tree, profile, udid)
        require(receipt.get("status") == "PASS" and receipt.get("commit") == sources.PRODUCER and
                receipt.get("profile") == profile and receipt.get("observationOnly") is False and
                receipt.get("scope") == "actual_named_apple_test_execution" and
                actual["device"].get("deviceName") == "AnyNativePort-" + RUN and
                all(receipt.get(key) == value for key, value in actual.items()), "original_execution_receipt_mismatch")
        require(receipt.get("summarySHA256") == sha(read(directory / (stem + "-test-counts.json"))) and
                receipt.get("testTreeSHA256") == sha(read(directory / (stem + "-test-methods.json"))),
                "original_result_receipt_binding_mismatch")
        verify_log(read(directory / (stem + ".log")), actual["actualCases"])
        verified[stem] = actual
    receipt = data(directory / "native-ui-followup-named-execution.json")
    summary = data(directory / "native-ui-followup-test-counts.json")
    cases = execution.test_cases(data(directory / "native-ui-followup-test-methods.json"))
    expected = {name + "()": "Failed" for name in SIX} | {QUOTE + "()": "Passed"}
    require(receipt.get("status") == "FAIL" and receipt.get("commit") == sources.PRODUCER and
            receipt.get("profile") == "native-ui-followup" and
            {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")} ==
            {"totalTestCount": 7, "passedTests": 1, "failedTests": 6, "skippedTests": 0} and cases == expected,
            "original_failed_seven_batch_must_remain_failed")
    require(summary.get("devicesAndConfigurations", [{}])[0].get("device") == verified["native-ui"]["device"] and
            len(summary.get("devicesAndConfigurations", [])) == 1, "original_batch_destination_mismatch")
    for key, suffix in (("summarySHA256", "-test-counts.json"), ("testTreeSHA256", "-test-methods.json")):
        require(receipt.get(key) == sha(read(directory / ("native-ui-followup" + suffix))), "failed_batch_digest_mismatch")
    verify_log(read(directory / "native-ui-followup.log"), cases)
    return {**verified, "quote": {QUOTE + "()": "Passed"}, "originalFailedBatch": cases}


def verify_originals(directory, root=ROOT):
    contract = manifest(root)
    verify_api(data(directory / "run-metadata.json"), data(directory / "artifact-metadata.json"), contract)
    for name, expected in contract["files"].items():
        raw = read(directory / name)
        require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"], "original_bytes_changed_" + name)
    require(read(directory / "source-sha.txt").decode().strip() == sources.PRODUCER, "original_source_identity_mismatch")
    raw_results = verify_raw_results(directory)
    reused = data(directory / "ui-ios-reuse.json")
    focus.verify_retained_record(reused, sources.PRODUCER)
    older = original.verify_evidence(directory / "reused-ui-ios-unaffected-eight",
                                     "96173b0afc6b360c8f780ae70c6c80042fda98da", "44942212731",
                                     read_source=lambda commit, path: sources.source(commit, path, root))
    selected = eight.selected_original_cases(older)
    require(selected == reused.get("reusedOriginalCases"), "older_retained_subset_changed")
    focus_receipt = data(directory / "ui-focus-handoff-named-execution.json")
    require(focus_receipt.get("retainedEightReceiptSHA256") == sha(read(directory / "ui-ios-reuse.json")) and
            focus_receipt.get("sourceClosureGitBlobs") == original.source_tree(sources.PRODUCER, root),
            "original_focus_source_closure_mismatch")
    for name in ("ui-focus-handoff", "native-ui", "native-ui-followup"):
        receipt = data(directory / (name + "-named-execution.json"))
        runner = "verify_focus_handoff_execution.py" if name == "ui-focus-handoff" else "verify_native_test_execution.py"
        require(receipt.get("runnerSHA256") == sha(sources.source(sources.PRODUCER, "Tools/AnyEnginePort/" + runner, root)),
                "original_runner_source_mismatch")
        for field in ("testSources", "productionSources", "verificationSources"):
            for path, digest in receipt.get(field, {}).items():
                require(digest == sha(sources.source(sources.PRODUCER, path, root)), "original_bound_source_mismatch")
    frozen = data(directory / "native-shared-products.json")
    require(frozen.get("status") == "FROZEN_BUILD_INPUTS" and frozen.get("commit") == sources.PRODUCER and
            frozen.get("githubRunID") == RUN and
            frozen.get("sourceInputs", {}).get(sources.TEST) == sha(sources.source(sources.PRODUCER, sources.TEST, root)),
            "original_native_product_source_binding_mismatch")
    origins = {name.removesuffix("()"): {"runID": RUN, "commit": sources.PRODUCER}
               for group in (raw_results["ui-focus-handoff"]["actualCases"], raw_results["native-ui"]["actualCases"], raw_results["quote"])
               for name in group}
    origins.update({name.removesuffix("()"): {"runID": "44942212731", "commit": older["commit"]} for name in selected})
    require(len(origins) == 20, "retained_method_count_mismatch")
    return {"retainedMethodsWithOrigins": origins, "retainedMethodCount": 20,
            "originalFailedBatchStatus": "FAIL", "originalFailedBatchCounts": {"passed": 1, "failed": 6, "skipped": 0},
            "originalFiles": contract["files"], "originalArtifactID": contract["artifactID"],
            "originalArchiveSHA256": contract["archiveSHA256"], "originalArchiveBytes": contract["archiveBytes"],
            "originalRunMetadataSHA256": sha(read(directory / "run-metadata.json")),
            "originalArtifactMetadataSHA256": sha(read(directory / "artifact-metadata.json")),
            "originalDevice": raw_results["native-ui"]["device"]}


def context(evidence, root=ROOT):
    from hanlin_fixture_ci import github_context, verify_simulator
    run, commit, _ = github_context()
    udid, simulator, _ = verify_simulator(evidence / "simulator.json", run)
    require(run != RUN and os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and
            os.environ.get("GITHUB_REF") in {"refs/heads/" + BRANCH, "refs/heads/" + CONTINUATION_BRANCH},
            "consumer_run_scope_mismatch")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(attempt.isdigit() and int(attempt) > 0, "consumer_attempt_missing")
    return {"consumerCommit": commit, "consumerRunID": run, "ownedSimulatorUDID": udid,
            "consumerRunAttempt": int(attempt),
            "consumerSimulatorSHA256": sha(read(evidence / "simulator.json")),
            "consumerXcodeSHA256": sha(read(evidence / "xcode-version.txt"))}, simulator


def qualify_retention(evidence, root=ROOT):
    ctx, simulator = context(evidence, root)
    directory = evidence / RETAINED_DIR
    originals = verify_originals(directory, root)
    require(all(simulator.get(key) == data(directory / "simulator.json").get(key) for key in ("runtime", "deviceType")) and
            read(evidence / "xcode-version.txt") == read(directory / "xcode-version.txt"),
            "retained_platform_or_toolchain_changed")
    runtimes = strict_json(subprocess.check_output(["xcrun", "simctl", "list", "runtimes", "--json"]))
    matching = [value for value in runtimes.get("runtimes", []) if value.get("identifier") == simulator["runtime"]]
    require(len(matching) == 1 and matching[0].get("isAvailable") is True and
            matching[0].get("buildversion") == originals["originalDevice"]["osBuildNumber"] and
            matching[0].get("version") == originals["originalDevice"]["osVersion"], "retained_runtime_build_changed")
    current_binding = data(root / "Modules/PinkhaAnyRuntime/Vendor/consumer-binding.json")
    prior_binding = data(directory / "native-reuse.json")
    require(current_binding == {**prior_binding, "consumerCommit": ctx["consumerCommit"]} and
            sha(read(root / "Modules/PinkhaAnyRuntime/Vendor/native-artifact.json")) == prior_binding["artifactReceiptSHA256"],
            "retained_native_binary_or_source_binding_changed")
    return {"schemaVersion": 1, "status": "VERIFIED_REUSE", "scope": "verified_original_any_acceptance_subset",
            "fullAcceptance": False, "testsExecutedThisRun": 0, **ctx, **originals,
            "sourceProof": sources.verify_sources(ctx["consumerCommit"], root),
            "verificationSources": {path: sha(read(root / path)) for path in HELPERS},
            "claimBoundary": "Twenty methods retain their actual original run and source. No original failed batch is relabeled and no current execution is inferred."}


def validate_admission(path, root=ROOT):
    receipt = data(path)
    expected = qualify_retention(path.parent, root)
    require(receipt == expected, "retained_admission_changed_or_not_current")
    return receipt


def current_stage(evidence, stem, profile, ctx, root=ROOT):
    record = data(evidence / (stem + "-named-execution.json"))
    actual = execution.validate(data(evidence / (stem + "-test-counts.json")),
                                data(evidence / (stem + "-test-methods.json")), profile, ctx["ownedSimulatorUDID"])
    require(record.get("status") == "PASS" and record.get("commit") == ctx["consumerCommit"] and
            record.get("profile") == profile and record.get("observationOnly") is False and
            record.get("scope") == "actual_named_apple_test_execution" and
            record.get("runnerSHA256") == sha(read(root / "Tools/AnyEnginePort/verify_native_test_execution.py")) and
            all(record.get(key) == value for key, value in actual.items()), "current_named_execution_mismatch_" + stem)
    require(record.get("testSources") == {path: sha(read(root / path)) for path in execution.SOURCE_PATHS[profile]},
            "current_test_sources_mismatch")
    for key, suffix in (("summarySHA256", "-test-counts.json"), ("testTreeSHA256", "-test-methods.json")):
        require(record.get(key) == sha(read(evidence / (stem + suffix))), "current_execution_digest_mismatch")
    verify_log(read(evidence / (stem + ".log")), actual["actualCases"])
    return {"receiptSHA256": sha(read(evidence / (stem + "-named-execution.json"))), "execution": actual}


def previous_stages(evidence, admission, root=ROOT):
    retained = validate_admission(admission, root)
    six = current_stage(evidence, "native-ui-continuation", PROFILE, retained, root)
    files = current_stage(evidence, "archive-roundtrip", "archive-roundtrip", retained, root)
    proof = data(evidence / "archive-roundtrip/postflight.json")
    require(proof.get("status") == "PASS" and proof.get("commit") == retained["consumerCommit"] and
            proof.get("githubRunID") == retained["consumerRunID"] and proof.get("uiMethodExecutions") == 1 and
            proof.get("summarySHA256") == sha(read(evidence / "archive-roundtrip-test-counts.json")) and
            proof.get("testTreeSHA256") == sha(read(evidence / "archive-roundtrip-test-methods.json")),
            "current_files_postflight_missing")
    provider = data(evidence / "hanlin-provider/verify.json")
    transcript = data(evidence / "hanlin-provider/provider-contract.json")
    require(provider.get("status") == "FINITE_PROVIDER_CONTRACT_VERIFIED" and
            provider.get("sourceCommit") == retained["consumerCommit"] and
            provider.get("githubRunID") == retained["consumerRunID"] and
            transcript.get("complete") is True and transcript.get("state") == "complete" and
            transcript.get("phase") == 6 and transcript.get("responsesDelivered") == 6,
            "current_hanlin_provider_contract_incomplete")
    return {"retainedAdmissionSHA256": sha(read(admission)), "retainedEntryAndQuoteExecutedThisRun": 0,
            "currentSix": six, "currentFiles": files,
            "currentProviderContractSHA256": sha(read(evidence / "hanlin-provider/provider-contract.json")),
            "currentFilesPostflightSHA256": sha(read(evidence / "archive-roundtrip/postflight.json"))}


def aggregate(evidence, admission, include_history, root=ROOT):
    retained = validate_admission(admission, root)
    stages = previous_stages(evidence, admission, root)
    stages["currentCustomType"] = current_stage(evidence, "custom-type", "native-custom-type", retained, root)
    custom = data(evidence / "custom-type/postflight.json")
    require(custom.get("status") == "PASS" and custom.get("commit") == retained["consumerCommit"] and
            custom.get("githubRunID") == retained["consumerRunID"] and
            custom.get("continuationAdmissionSHA256") == sha(read(admission)), "custom_type_continuation_not_qualified")
    if include_history:
        stages["currentHistory"] = current_stage(evidence, "native-history", HISTORY_PROFILE, retained, root)
    return {"schemaVersion": 1, "status": "PASS_CONTINUATION", "scope": "qualified_missing_native_ui_journeys",
            "consumerCommit": retained["consumerCommit"], "consumerRunID": retained["consumerRunID"],
            "retainedMethodCount": 20, "retainedMethodsExecutedThisRun": 0,
            "retainedMethodsWithOrigins": retained["retainedMethodsWithOrigins"],
            "currentExecutedMethodCount": 9 if include_history else 8,
            "historyExecution": "PASS" if include_history else "NOT_RUN",
            "originalFailedBatchStatus": "FAIL", "fullAcceptance": False,
            "wholeAPP01": "OPEN", "physicalDeviceAcceptance": "NOT_RUN", "stages": stages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("retain", "aggregate"))
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--download", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--include-history", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "action": args.action, "fullAcceptance": False}
    require(not args.output.exists(), "cannot_replace_original_continuation_receipt")
    try:
        if args.action == "retain":
            fetch_originals(args.download, args.evidence / RETAINED_DIR)
            record = qualify_retention(args.evidence)
        else:
            record = aggregate(args.evidence, args.admission, args.include_history)
    except Exception as error:
        record["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2); stream.write("\n")
    print(json.dumps({key: record[key] for key in ("status", "scope", "error") if key in record}))
    return 0 if record["status"] in {"VERIFIED_REUSE", "PASS_CONTINUATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
