"""Run the same app source with verified r14/r15 on one fresh OS27 account.

Only this job's compile commands enable the lookup flag. Product enablement and
the wider UI/freshness acceptance remain separate. Native logs stay private
until checked against both disposable credentials; app data is never uploaded.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import zipfile
from uuid import uuid4

PROTOCOL = "pinkha-t5-apple-runtime-pair-v2"
ROOT_RELATIVE_PATH = "Library/Application Support/Anytype/middleware-go"
PAIR_RELATIVE_PATH = "Library/Application Support/pinkha-t5-runtime-pair"
METHOD = "TorahT5RuntimePairTests/realSameAccountRuntimePairPhase"
PHASES = [("old-create", "old"), ("new-upgrade", "new"),
          ("old-edit", "old"), ("new-recover", "new")]
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
NATIVE_SOURCE = "947fbde24d5657d0e1229f45bb3993648884a8a1"
PATCHES = {
    "old": "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
    "new": "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2",
}
INVENTORIES = {
    "old": "952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14",
    "new": "f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7",
}
OLD_RUN = "44203168617"
OLD_ARTIFACT = 14383247626
BUILDER_SHA = "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669"
APPROVAL = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval"
BUNDLE = "io.anytype.app"
FLAGS = [
    "OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1",
    "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone",
    "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
    "PROVISIONING_PROFILE_SPECIFIER=",
]
SLICE_IDENTITIES = {
    ("ios-arm64/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "arm64"),
    ("ios-arm64_x86_64-simulator/Lib.framework/Lib", "x86_64"),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path, normalize=False):
    if normalize:
        return sha_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def is_digest(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf8")
    temporary.replace(path)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def verify_published_source(app, proof):
    source = git(app, "rev-parse", "HEAD")
    expected = os.environ.get("GITHUB_SHA")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    status = git(app, "status", "--porcelain")
    valid = source == expected and not status and run_id.isdigit()
    # Retain the failed predicate before aborting, without weakening the
    # existing tracked-and-untracked cleanliness boundary.
    write(proof / "source-preflight.json", {
        "status": "PASS" if valid else "FAIL",
        "actual_source_sha": source,
        "expected_source_sha": expected,
        "run_id": run_id,
        "tracked_and_untracked_clean": not status,
        "git_porcelain": status,
    })
    require(valid, "Exact clean published App source/run required")
    return source


def runtime_version(role):
    value = "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + PATCHES[role]
    return value + "-pinkha-native-t5-lookup-v1-" + PATCHES[role] if role == "new" else value


def target_key(value):
    return value["objectID"], value.get("blockID") or ""


FRESHNESS_PHASE = ("new-freshness", "new")
FRESHNESS_STATUS = "PASS_ACTUAL_SWIFT_NATIVE_LOOKUP"


def phases(include_freshness=False):
    return PHASES + ([FRESHNESS_PHASE] if include_freshness else [])


def validate_freshness_graph(graph, document, space, reachable):
    require(isinstance(graph, dict) and graph.get("spaceID") == space
            and graph.get("rootID") == document["objectID"]
            and graph.get("targetID") == document.get("blockID")
            and graph.get("targetReachable") is reachable, "Foreign or unproven actual host graph")
    nodes = graph.get("nodes", [])
    require(isinstance(nodes, list) and 0 < len(nodes) <= 10000, "Actual bounded ObjectShow graph required")
    by_id = {}
    for node in nodes:
        require(isinstance(node, dict) and set(node) == {"id", "childIDs"}
                and isinstance(node.get("id"), str) and node["id"] and node["id"] not in by_id
                and isinstance(node["childIDs"], list)
                and all(isinstance(child, str) and child for child in node["childIDs"]),
                "Invalid actual graph node or duplicate identity")
        by_id[node["id"]] = node["childIDs"]
    pending, seen = [document["objectID"]], set()
    require(graph["targetID"] and graph["targetID"] != graph["rootID"], "Original distinct block identity required")
    while pending:
        identifier = pending.pop()
        if identifier in seen:
            continue
        require(identifier in by_id, "Unresolved child in the original native graph")
        seen.add(identifier)
        pending.extend(by_id[identifier])
    require((graph["targetID"] in seen) is reachable, "Claimed target exclusion contradicts the actual live graph")


def validate_host_freshness(freshness, ledger):
    require(isinstance(freshness, dict) and freshness.get("status") == FRESHNESS_STATUS
            and freshness.get("writeOrigin") == "DIRECT_NATIVE_RPC_WITHOUT_EXPLICIT_HOST_INVALIDATION"
            and freshness.get("serviceScope") == "ONE_REUSED_PRODUCTION_SERVICE"
            and freshness.get("coverage") == "indexedTargetsOnly"
            and freshness.get("spaceWideFreshness") == "NOT_PROVEN"
            and freshness.get("navigationStatus") == "NOT_RUN",
            "Actual same-service Swift freshness missing or acceptance scope widened")
    require(freshness.get("nativeMutationCounts") == {
        "ObjectSetDetails": 4, "ObjectListSetIsArchived": 2, "BlockListDelete": 2, "ObjectListDelete": 1},
        "Actual direct-native mutation sequence differs or recreated a fixture")
    documents, original = ledger["documents"], freshness.get("originalCanonical", {})
    ids = [doc["objectID"] for doc in documents]
    require(set(original) == set(ids), "Original native canonical payloads missing")
    parsed = []
    for index, doc in enumerate(documents):
        raw = original[doc["objectID"]]
        require(isinstance(raw, str) and sha_bytes(raw.encode()) == doc["canonicalSHA256"],
                "Freshness substituted the original canonical bytes")
        root = json.loads(raw)
        records = root.get("records", [])
        require(root.get("version") == 2 and len(records) == 1, "One original canonical v2 record required")
        record = records[0]
        require(record.get("spaceId") == ledger["spaceID"] and record.get("objectId") == doc["objectID"]
                and record.get("blockId") == doc.get("blockID")
                and record.get("item", {}).get("kind") == "ref"
                and record["item"].get("providerID") == "sefaria"
                and record["item"].get("canonicalKey") == "Genesis 3:3"
                and record["item"].get("role") == ("sourceQuote" if index == 2 else "context"),
                "Original canonical source/target binding differs")
        parsed.append(root)
    # name, native members, host targets, inspected object, payload, reachable, archived, verse, stale
    spec = [
        ("baseline", [0, 1, 2], [0, 1, 2], None, None, None, False, "Genesis 3:3", False),
        ("note_unlink", [0, 2], [0, 2], 1, "unlink", True, False, "Genesis 3:3", False),
        ("note_restore", [0, 1, 2], [0, 1, 2], 1, "original", True, False, "Genesis 3:3", False),
        ("quote_update_original", [0, 1], [0, 1], 2, "verse", True, False, "Genesis 3:3", False),
        ("quote_update_other", [2], [2], 2, "verse", True, False, "Genesis 3:4", False),
        ("quote_restore", [0, 1, 2], [0, 1, 2], 2, "original", True, False, "Genesis 3:3", False),
        ("note_archive", [0, 2], [0, 2], 1, "original", True, True, "Genesis 3:3", False),
        ("note_unarchive", [0, 1, 2], [0, 1, 2], 1, "original", True, False, "Genesis 3:3", False),
        ("note_block_removed", [0, 1, 2], [0, 2], 1, "original", False, False, "Genesis 3:3", True),
        ("quote_block_removed", [0, 1, 2], [0], 2, "original", False, False, "Genesis 3:3", True),
        ("page_deleted", [1, 2], [], 0, "deleted", None, False, "Genesis 3:3", True),
    ]
    observed = freshness.get("observations", [])
    require(isinstance(observed, list) and [row.get("name") for row in observed] == [row[0] for row in spec],
            "Exactly eleven ordered actual Swift/native observations required")
    for row, (_, native, host, index, payload, reachable, archived, verse, stale) in zip(observed, spec):
        require(row.get("spaceID") == ledger["spaceID"] and row.get("sourceReference") == verse
                and row.get("coverage") == "indexedTargetsOnly", "Host observation source/Space/coverage differs")
        require(row.get("nativeCandidatesBefore") == sorted(ids[i] for i in native)
                and row.get("nativeCandidatesAfter") == sorted(ids[i] for i in native),
                "Actual native membership before and after the production service differs")
        expected_targets = [dict(objectID=ids[i], blockID=documents[i].get("blockID"),
                                 canUnlink=documents[i].get("blockID") is None) for i in host]
        targets = row.get("targets", [])
        require(isinstance(targets, list) and all(type(item.get("canUnlink")) is bool for item in targets)
                and sorted([dict(objectID=item.get("objectID"), blockID=item.get("blockID"),
                                 canUnlink=item["canUnlink"]) for item in targets], key=target_key)
                == sorted(expected_targets, key=target_key), "Actual production service returned an invalid target")
        expected_limits = ["indexFreshnessUnverified"] + (["staleCandidates"] if stale else [])
        require(row.get("limitations") == expected_limits, "Missing exact host incompleteness/stale disclosure")
        if index is None:
            require(all(row.get(key) is None for key in ["objectID", "canonicalRaw", "canonicalSHA256",
                    "objectRetained", "isArchived", "graph", "objectShowError"]),
                    "Baseline claimed an unrelated native mutation/readback")
            continue
        doc = documents[index]
        require(row.get("objectID") == doc["objectID"], "Mutation inspected a different original object")
        if payload == "deleted":
            require(type(row.get("objectShowError")) is int and row["objectShowError"] in [3, 4]
                    and all(row.get(key) is None for key in
                            ["canonicalRaw", "canonicalSHA256", "objectRetained", "isArchived", "graph"]),
                    "Deleted Page did not return a specific native deletion response")
            continue
        require(row.get("objectRetained") is True and row.get("isArchived") is archived
                and row.get("objectShowError") is None, "Unlink/archive mutated or removed the original live object")
        raw = row.get("canonicalRaw")
        require(isinstance(raw, str) and sha_bytes(raw.encode()) == row.get("canonicalSHA256"),
                "Actual canonical mutation bytes and digest differ")
        if payload == "original":
            require(raw == original[doc["objectID"]], "Restoration/removal changed original canonical unknown fields")
        else:
            expected = json.loads(original[doc["objectID"]])
            if payload == "unlink":
                expected["records"] = []
            else:
                expected["records"][0]["item"].update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
            require(json.loads(raw) == expected, "Host observed a different canonical mutation or lost unknown fields")
        validate_freshness_graph(row.get("graph"), doc, ledger["spaceID"], reachable)
    return len(observed)


def validate_ledger(ledger, token, source, phase):
    require(ledger.get("token") == token and ledger.get("appSourceSHA") == source, "Foreign ledger owner/source")
    require(ledger.get("rootRelativePath") == ROOT_RELATIVE_PATH, "Original relative account root changed")
    for key in ["rootPathSHA256", "manifestSHA256"]:
        require(is_digest(ledger.get(key)), "Invalid original ledger digest")
    for key in ["accountID", "spaceID", "manifestID", "canonicalKey"]:
        require(isinstance(ledger.get(key), str) and ledger[key], "Missing original native identity")
    all_phases = phases(True)
    expected_phases = [name for name, _ in all_phases[:[name for name, _ in all_phases].index(phase) + 1]]
    require(ledger.get("completedPhases") == expected_phases, "Actual persisted phase sequence differs")
    documents = ledger.get("documents", [])
    require(len(documents) == 3 and len({item.get("objectID") for item in documents}) == 3,
            "Three distinct original native documents required")
    require(documents[0].get("typeKey") == "ot-page" and documents[1].get("typeKey") == "ot-note"
            and documents[2].get("typeKey") not in [None, "", "ot-page", "ot-note"],
            "Actual Page, Note and custom Type fixture required")
    require(documents[0].get("blockID") is None and documents[0].get("blockText") is None,
            "The first target must be document context only")
    blocks = [item.get("blockID") for item in documents[1:]]
    require(all(isinstance(value, str) and value for value in blocks) and len(set(blocks)) == 2,
            "Two distinct original block identities required")
    for item in documents:
        require(isinstance(item.get("objectID"), str) and item["objectID"]
                and isinstance(item.get("initialName"), str), "Missing actual initial document details")
        require(is_digest(item.get("canonicalSHA256")) and is_digest(item.get("publicSHA256")),
                "Missing original canonical/public baseline")
    return documents


def validate_phase(report, phase, role, token, nonce, source, ledger, ledger_sha, prior=None):
    documents = validate_ledger(ledger, token, source, phase)
    require(report.get("protocolVersion") == PROTOCOL and report.get("status") == "PASS"
            and report.get("phase") == phase and report.get("token") == token
            and report.get("nonce") == nonce and report.get("appSourceSHA") == source,
            "Stale or foreign actual Apple phase receipt")
    require(type(report.get("processID")) is int and report["processID"] > 0, "Actual host process identity missing")
    require(report.get("runtimeVersion") == runtime_version(role), "Actual AppGetVersion differs from installed revision")
    require(report.get("rootRelativePath") == ROOT_RELATIVE_PATH
            and is_digest(report.get("currentRootPathSHA256")), "Actual account root location missing")
    if phase == "old-create":
        require(report["currentRootPathSHA256"] == report.get("rootPathSHA256"),
                "Original account root was not the initial actual location")
    expanded = role == "new"
    require(report.get("actualCapability") == ("verified" if expanded else "unavailable"),
            "Production runtime capability differs; fixture roles must not grant capability")
    require(report.get("coverage") == ("indexedTargetsOnly" if expanded else "indexedDocumentsOnly"),
            "Actual Swift lookup coverage differs")
    expected_limits = {"indexFreshnessUnverified"}
    if not expanded:
        expected_limits |= {"blockAssociationsNotIndexed", "sourceQuotesNotIndexed"}
    require(set(report.get("limitations", [])) == expected_limits, "Actual coverage disclosure changed or widened")
    for key in ["rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
        require(report.get(key) == ledger[key], "Original account, root, Space or manifest changed")
    require(report.get("nextLedgerSHA256") == ledger_sha, "Receipt does not bind the actual persisted ledger")
    require(report.get("previousLedgerSHA256") == (prior["nextLedgerSHA256"] if prior else None),
            "Broken native process/ledger chain")
    if prior:
        for key in ["rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
            require(report[key] == prior[key], "Prior native account or manifest identity changed")
        preserved = ["objectID", "canonicalSHA256", "publicSHA256", "blockID", "blockTextSHA256"]
        require([[item.get(key) for key in preserved] for item in report.get("documents", [])]
                == [[item.get(key) for key in preserved] for item in prior["documents"]],
                "A later ledger attempted to redefine the original canonical/public/block baseline")
    for key in ["accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"]:
        require(report.get(key) is True, "Native account stop/readback boundary was not proven")
    initial = phase == "old-create"
    for key in ["walletCreated", "accountCreated"]:
        require(report.get(key) is initial, "A later phase recreated a native account")
    for key in ["walletRecovered", "accountSelected"]:
        require(report.get(key) is (not initial), "The original native account was not recovered/selected")
    require(type(report.get("migrationPerformed")) is bool
            and (not initial or report["migrationPerformed"] is False), "Invalid migration observation")
    readbacks = report.get("documents", [])
    require(len(readbacks) == 3 and [item.get("objectID") for item in readbacks]
            == [item["objectID"] for item in documents], "Actual live native readbacks are incomplete")
    for index, (item, original) in enumerate(zip(readbacks, documents)):
        for key in ["canonicalSHA256", "publicSHA256", "blockID"]:
            require(item.get(key) == original.get(key), "Canonical, public projection, or actual block changed")
        expected_text = sha_bytes(original["blockText"].encode()) if original.get("blockID") else None
        require(item.get("blockTextSHA256") == expected_text, "Actual block text was not preserved")
        if expanded:
            require(type(item.get("nativeRelatedVersion")) is int and item["nativeRelatedVersion"] == 1,
                    "New native private projection did not recover")
        expected_name = ("T5 ordinary edit by r14" if index == 0 and phase in ["old-edit", "new-recover", "new-freshness"]
                         else original["initialName"])
        require(item.get("title") == expected_name, "Actual initial title or ordinary old-runtime edit was lost")
    expected = [dict(objectID=item["objectID"], blockID=item.get("blockID") if expanded else None,
                     canUnlink=item.get("blockID") is None) for item in documents[:3 if expanded else 1]]
    targets = report.get("targets", [])
    require(len(targets) == len(expected) and
            sorted([dict(objectID=item.get("objectID"), blockID=item.get("blockID"),
                         canUnlink=item.get("canUnlink")) for item in targets], key=target_key)
            == sorted(expected, key=target_key), "Actual app lookup returned the wrong native targets")

    if phase == "new-freshness":
        require(role == "new" and report.get("readbackBoundary") == "BEFORE_FRESHNESS_MUTATIONS",
                "Freshness cannot relabel compatibility readbacks as post-mutation preservation")
        validate_host_freshness(report.get("freshness"), ledger)
    else:
        require(report.get("freshness") is None
                and report.get("readbackBoundary", "BEFORE_ACCOUNT_STOP") == "BEFORE_ACCOUNT_STOP",
                "Default compatibility phase unexpectedly performed freshness mutations")


def validate_xcresult(summary, methods, udid):
    normalized = {name.removesuffix("()"): outcome for name, outcome in methods.items()}
    require(all(type(summary.get(key)) is int for key in ["passedTests", "failedTests", "skippedTests"])
            and summary.get("passedTests") == 1 and summary.get("failedTests") == 0
            and summary.get("skippedTests") == 0 and normalized == {METHOD: "Passed"},
            "Exactly one actual named Swift test must pass without skips")
    devices = [item.get("device", {}) for item in summary.get("devicesAndConfigurations", [])]
    require(devices and all(item.get("deviceId", "").lower() == udid.lower()
            and item.get("osVersion", "").split(".")[0] == "27"
            and item.get("architecture") == "arm64" for item in devices),
            "Actual XCTest device/architecture/runtime differs")


def validate_sequence(reports, build_receipts, include_freshness=False):
    require([report.get("phase") for report in reports] == [name for name, _ in phases(include_freshness)],
            "Exact requested Apple phase sequence is required")
    pids = [report["processID"] for report in reports]
    nonces = [report["nonce"] for report in reports]
    total = 5 if include_freshness else 4
    require(len(set(pids)) == total and len(set(nonces)) == total,
            "Every actual native phase requires a distinct process and nonce")
    for key in ["appSourceSHA", "token", "rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]:
        require(len({report[key] for report in reports}) == 1, "Native account/source continuity was lost")
    preserved = ["objectID", "canonicalSHA256", "publicSHA256", "blockID", "blockTextSHA256"]
    baseline = [[item.get(key) for key in preserved] for item in reports[0]["documents"]]
    for report in reports:
        require([[item.get(key) for key in preserved] for item in report["documents"]] == baseline,
                "Original native canonical/public/block observations changed between processes")
    require(set(build_receipts) == {"old", "new"}, "Both packaged applications must be built")
    old, new = build_receipts["old"], build_receipts["new"]
    for key in ["app_source_sha", "package_lock_hashes", "hanlin_snapshot_sha256", "kit_sha", "flags"]:
        require(old.get(key) == new.get(key), "The two apps used different source, dependencies or flags")
    require(old.get("flags") == FLAGS, "Test-only build flags differ")
    require(old.get("code_sha256") != new.get("code_sha256"), "The supposedly different packaged runtimes are identical")
    for role in ["old", "new"]:
        require(build_receipts[role].get("runtime_version") == runtime_version(role), "Packaged runtime pairing differs")
    counts = dict(app_builds=2, actual_native_processes=total, named_swift_tests_passed=total, failed=0, skipped=0)
    if include_freshness:
        fresh = reports[-1]
        require(fresh.get("readbackBoundary") == "BEFORE_FRESHNESS_MUTATIONS"
                and fresh.get("freshness", {}).get("status") == FRESHNESS_STATUS
                and len(fresh["freshness"].get("observations", [])) == 11,
                "Fifth process lacks actual bounded host freshness")
        counts["host_freshness_observations"] = 11
    return counts


def terminate_owned(process):
    """Signal only the new session created for this command, including its children."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    # A TERM-exited parent does not prove that TERM-ignoring descendants stopped.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def run_logged(argv, cwd, directory, name, timeout, check=True, output=None):
    # Reuse the same owned executor and quiescence check as the package/SDK
    # supervisors. A completed xcodebuild parent can leave compiler children;
    # the next stage and cache publication must wait for its own group only.
    import wave15_batch as owned
    from run_owned_single_lane import verify_owned_group_stopped

    directory.mkdir(parents=True, exist_ok=True)
    log_path = output or directory / (name + ".log")
    command_path = log_path.with_suffix(".command.json")
    original_path = directory / (name + ".owned.command.json")
    metadata_path = directory / (name + ".command.json")
    require(not any(path.exists() for path in (log_path, command_path, original_path, metadata_path)),
            "Refuse stale command output or ownership evidence")
    metadata = dict(argv=[str(item) for item in argv], cwd=str(cwd), status="FAILED",
                    started_at=datetime.now(timezone.utc).isoformat(), timeout_seconds=timeout)
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    previous_env = {key: os.environ.get(key) for key in ("GH_PROMPT_DISABLED", "GH_DEBUG")}
    cancelled = finalizing = False
    failure = cleanup_failure = None
    outcome = None

    def cancel(signum, frame):
        nonlocal cancelled
        if cancelled:
            return
        cancelled = True
        if not finalizing:
            raise KeyboardInterrupt("Owned T5 command cancelled")

    for number in previous:
        signal.signal(number, cancel)
    os.environ["GH_PROMPT_DISABLED"] = "1"
    os.environ.pop("GH_DEBUG", None)
    try:
        outcome = owned.run_worker_command([str(item) for item in argv], cwd, log_path, timeout)
        metadata.update(return_code=outcome["return_code"],
                        status="SUCCESS" if outcome["return_code"] == 0 else "FAILED")
    except BaseException as error:
        failure = error
        metadata.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                        "TIMED_OUT" if isinstance(error, subprocess.TimeoutExpired) else "FAILED",
                        error_type=type(error).__name__, timed_out=isinstance(error, subprocess.TimeoutExpired))
    finally:
        finalizing = True
        try:
            if command_path.is_file():
                original = json.loads(command_path.read_bytes())
                if original.get("worker_pid") is not None:
                    metadata.update(controller_process_id=original["worker_pid"],
                                    return_code=original.get("return_code"),
                                    owned_group_termination=original.get("owned_group_cleanup"))
                    metadata["owned_group_quiescence"] = verify_owned_group_stopped(command_path)
                else:
                    metadata["owned_group_quiescence"] = {"status": "NOT_STARTED"}
        except BaseException as error:
            cleanup_failure = error
            metadata.update(status="FAILED_PROCESS_CLEANUP", cleanup_error_type=type(error).__name__)
        try:
            if command_path.is_file():
                command_path.rename(original_path)
                metadata.update(original_owned_command=original_path.name,
                                original_owned_command_sha256=digest(original_path))
            if cancelled:
                metadata["status"] = "CANCELLED"
                failure = failure or KeyboardInterrupt("Owned T5 command cancelled")
            metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
            write(metadata_path, metadata)
            if cancelled:
                metadata["status"] = "CANCELLED"
                failure = failure or KeyboardInterrupt("Owned T5 command cancelled")
                write(metadata_path, metadata)
        finally:
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            for number, previous_handler in previous.items():
                signal.signal(number, previous_handler)
    if failure is not None:
        raise failure
    if cleanup_failure is not None:
        raise cleanup_failure
    if check:
        require(metadata["return_code"] == 0, name + " failed; original private output retained")
    return metadata, log_path

def download_runtime(role, run_id, work, proof, repo):
    require(run_id.isdigit() and (role != "old" or run_id == OLD_RUN), "Explicit original runtime run IDs required")
    directory = work / ("runtime-" + role)
    directory.mkdir()
    def api(endpoint, name):
        output = directory / (name + ".json")
        run_logged(["gh", "api", "repos/" + repo + "/" + endpoint], work, directory, name, 120, output=output)
        return json.loads(output.read_text(encoding="utf8"))
    run = api("actions/runs/" + run_id, "source-run")
    require(str(run.get("id")) == run_id and run.get("status") == "completed"
            and run.get("conclusion") == "success", "Original runtime build did not complete successfully")
    response = api("actions/runs/" + run_id + "/artifacts?per_page=100", "artifact-list")
    name = "Pinkha-Universal-Verified-Heart-r" + ("14" if role == "old" else "15")
    matches = [item for item in response.get("artifacts", []) if item.get("name") == name]
    require(len(matches) == 1, "Exactly one original runtime artifact is required")
    artifact = matches[0]
    require(not artifact.get("expired") and (role != "old" or artifact.get("id") == OLD_ARTIFACT)
            and artifact.get("workflow_run", {}).get("head_sha") == run.get("head_sha"),
            "Runtime artifact has the wrong source identity")
    expected_digest = artifact.get("digest", "").removeprefix("sha256:")
    require(is_digest(expected_digest), "Original artifact digest is unavailable")
    archive = directory / "original-github-artifact.zip"
    run_logged(["gh", "api", "repos/" + repo + "/actions/artifacts/" + str(artifact["id"]) + "/zip"],
               work, directory, "download-original-artifact", 300, output=archive)
    require(digest(archive) == expected_digest and archive.stat().st_size == artifact.get("size_in_bytes"),
            "Downloaded original artifact bytes differ")
    tar_name = name + ".tar.gz"
    with zipfile.ZipFile(archive) as zipped:
        require(zipped.namelist() == [tar_name], "Unexpected runtime artifact payload")
        zipped.extract(tar_name, directory)
    proof.mkdir(parents=True)
    for filename in ["source-run.json", "artifact-list.json"]:
        shutil.copyfile(directory / filename, proof / filename)
    write(proof / "download.json", dict(source_run_id=run_id, artifact_id=artifact["id"],
          artifact_sha256=expected_digest, runtime_archive_sha256=digest(directory / tar_name),
          original_source_sha=run["head_sha"], runtime_archive_bytes=(directory / tar_name).stat().st_size))
    return directory / tar_name, run


def install_runtime(role, archive, source_run, app, native_source, work, proof, helper):
    revision = "14" if role == "old" else "15"
    approval = native_source / APPROVAL / ("revision-" + revision)
    patch = approval / "native-heart-integration.patch"
    inventory_path = approval / "native-heart-integration.json"
    require(digest(patch, True) == PATCHES[role] and digest(inventory_path, True) == INVENTORIES[role],
            "Immutable native patch or inventory differs")
    inventory = json.loads(inventory_path.read_text(encoding="utf8"))
    require(inventory.get("heart_sha") == HEART and inventory.get("patch_sha256") == PATCHES[role],
            "Unexpected native source pin")
    staging = work / ("unpacked-" + role)
    staging.mkdir()
    with tarfile.open(archive) as packed:
        packed.extractall(staging, filter="data")
    require({path.name for path in staging.iterdir()} == {"Lib.xcframework", "PinkhaNativeHeartBuild.json"},
            "Unexpected native runtime archive content")
    framework = staging / "Lib.xcframework"
    receipt = json.loads((staging / "PinkhaNativeHeartBuild.json").read_text(encoding="utf8"))
    require(receipt.get("status") == "PASS" and receipt.get("target") == "ios"
            and receipt.get("heart_sha") == HEART and receipt.get("patch_sha256") == PATCHES[role]
            and receipt.get("files") == inventory["files"], "Artifact does not bind the exact native inventory")
    if role == "new":
        require(receipt.get("source_sha") == NATIVE_SOURCE
                and receipt.get("integration_sha") == source_run["head_sha"]
                and receipt.get("helper_sha256") == BUILDER_SHA
                and receipt.get("expected_app_get_version") == runtime_version(role)
                and receipt.get("app_get_version_status") == "NOT_RUN_BUILD_ONLY"
                and receipt.get("native_test_invocations") == 0,
                "r15 build-only runtime provenance is incomplete")
    entries = receipt.get("artifacts", [])
    paths = [item.get("path") for item in entries]
    require(len(paths) == len(set(paths)), "Duplicate native artifact paths")
    actual_paths = {str(path.relative_to(framework)) for path in framework.rglob("*") if path.is_file()}
    require(actual_paths == set(paths), "Native framework file inventory differs")
    for item in entries:
        path = (framework / item["path"]).resolve(strict=True)
        require(path.is_relative_to(framework.resolve()) and digest(path) == item["sha256"],
                "Native framework bytes or path differ")
    marker = runtime_version(role) if role == "new" else "pinkha-native-derived-v1-" + PATCHES[role]
    slices = helper.verify_framework_slices(framework, marker)
    require({(item["path"], item["architecture"]) for item in slices} == SLICE_IDENTITIES
            and len(slices) == 3, "All three original Apple architectures must be verified")
    ordering = lambda item: (item["path"], item["architecture"])
    require(sorted(slices, key=ordering) == sorted(receipt.get("binary_slices", []), key=ordering),
            "Actual architecture hashes differ from the original build")
    destination = app / "Dependencies/Middleware"
    require(not destination.exists() or (destination.is_dir() and not any(destination.iterdir())),
            "Refuse to overwrite an unrelated middleware installation")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.move(str(framework), destination / "Lib.xcframework")
    shutil.copyfile(staging / "PinkhaNativeHeartBuild.json", destination / "PinkhaNativeHeartBuild.json")
    shutil.copyfile(staging / "PinkhaNativeHeartBuild.json", proof / "original-runtime-build.json")
    write(proof / "installation.json", dict(role=role, patch_sha256=PATCHES[role],
          inventory_sha256=INVENTORIES[role], binary_slices=slices, heart_sha=HEART,
          app_source_sha=git(app, "rev-parse", "HEAD"), expected_app_get_version=runtime_version(role)))
    return destination


def lock_hashes(app):
    paths = git(app, "ls-files", "-z").split("\0")
    return {path: digest(app / path) for path in paths if path.endswith("Package.resolved")}


def rewrite_product_paths(value, original, snapshot):
    if isinstance(value, str):
        return value.replace(str(original), str(snapshot))
    if isinstance(value, dict):
        return {key: rewrite_product_paths(child, original, snapshot) for key, child in value.items()}
    if isinstance(value, list):
        return [rewrite_product_paths(child, original, snapshot) for child in value]
    return value


def build_runtime_version(role, ui, corrected_r15_binding=None):
    if corrected_r15_binding is None:
        return runtime_version(role)
    require(role == "new" and corrected_r15_binding.get("runtime_profile") == "r15-attachment-v1",
            "Corrected build binding requires the explicit r15 attachment profile")
    marker = ui.heart_profiles.verify_binding(corrected_r15_binding)
    require(marker == ui.heart_profiles.select("r15-attachment-v1").version,
            "Corrected App build must use the complete qualified runtime marker")
    return marker


def build_app(role, app, derived, work, proof, udid, source, helpers, *, corrected_r15_binding=None):
    ui, native = helpers
    expected_version = build_runtime_version(role, ui, corrected_r15_binding)
    product_root = work / role / "Products"
    proof.mkdir(parents=True)
    before_locks = lock_hashes(app)
    hanlin = app / "Dependencies/Hanlin/.pinkha-source.json"
    require(hanlin.is_file(), "Prepared canonical Hanlin SDK is missing")
    hanlin_sha = digest(hanlin)
    native.prepare_source_cache(app, derived)
    command = [
        "xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
        "-configuration", "Release-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
        "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO",
        "-only-testing:AnytypeTests/TorahT5RuntimePairTests", *FLAGS,
    ]
    _, log = run_logged(command, app, proof, "build-" + role, 5400)
    require(git(app, "rev-parse", "HEAD") == source and not git(app, "status", "--porcelain"),
            "Tracked application source changed during build")
    require(before_locks == lock_hashes(app) and digest(hanlin) == hanlin_sha, "Build dependency inputs changed")
    products = derived / "Build/Products"
    source_configuration = ui.test_configuration(products, "AnytypeTests")
    require(not product_root.exists(), "Refuse stale packaged application products")
    shutil.copytree(products, product_root, symlinks=True)
    configuration = product_root / source_configuration.name
    data = plistlib.loads(configuration.read_bytes())
    configuration.write_bytes(plistlib.dumps(rewrite_product_paths(data, products, product_root)))
    built = product_root / "Release-Anytype-iphonesimulator/Anytype.app"
    ui.verify_signed_simulator(built, proof)
    ui.verify_runtime_copies(built, expected_version.encode(), proof)
    (proof / "native-source-marker").mkdir()
    ui.verify_runtime_copies(built, HEART.encode(), proof / "native-source-marker")
    carriers = ui.code_carriers(built)
    lock = json.loads((app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    pins = [item["state"]["revision"] for item in lock["pins"] if item["identity"].lower() == "torahinspectorkit"]
    require(len(pins) == 1, "One exact Kit dependency revision required")
    checkouts = [path for path in (derived / "SourcePackages/checkouts").iterdir()
                 if path.name.lower() == "torahinspectorkit"]
    require(len(checkouts) == 1 and git(checkouts[0], "rev-parse", "HEAD") == pins[0], "Resolved Kit differs from app lock")
    receipt = dict(role=role, app_source_sha=source, flags=FLAGS, runtime_version=expected_version,
                   package_lock_hashes=before_locks, hanlin_snapshot_sha256=hanlin_sha, kit_sha=pins[0],
                   code_sha256=carriers["sha256"], code_carriers=carriers,
                   app=str(built), configuration=str(configuration), build_log_sha256=digest(log))
    if corrected_r15_binding is not None:
        receipt["runtime_binding"] = dict(corrected_r15_binding)
    write(proof / "build.json", receipt)
    return receipt


def app_container(udid, kind, required=True):
    result = subprocess.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, kind],
                            capture_output=True, text=True)
    if not required and result.returncode:
        return None
    require(result.returncode == 0 and result.stdout.strip(), "Owned simulator application container unavailable")
    return Path(result.stdout.strip()).resolve(strict=True)


def account_storage_inventory(container):
    """Hash stopped native data without treating the OS container UUID as identity.

    Apple TN2285 documents that an update changes Application_Home. Compare all
    native files and the private ledger/credentials across the install instead.
    The inventory stays in memory; only its aggregate hash/count is published.
    """
    container = container.resolve(strict=True)
    root = container / ROOT_RELATIVE_PATH
    require(root.is_dir() and not root.is_symlink()
            and root.resolve(strict=True).is_relative_to(container), "Original native account root missing or escaped")
    files, directories = {}, []
    for directory, children, names in os.walk(root, followlinks=False):
        directory = Path(directory)
        for name in children:
            path = directory / name
            require(not path.is_symlink() and path.is_dir(), "Unexpected native account directory entry")
            directories.append(path.relative_to(root).as_posix())
        for name in names:
            path = directory / name
            require(not path.is_symlink() and path.is_file(), "Unexpected native account file entry")
            files[path.relative_to(root).as_posix()] = dict(bytes=path.stat().st_size, sha256=digest(path))
    require(files, "Original native account store is empty")
    private = {}
    for name in ["ledger.json", "secrets.json"]:
        path = container / PAIR_RELATIVE_PATH / name
        require(not path.is_symlink() and path.is_file()
                and path.resolve(strict=True).is_relative_to(container), "Original private account identity missing or escaped")
        private[name] = digest(path)
    return dict(root_relative_path=ROOT_RELATIVE_PATH, directories=sorted(directories),
                files=files, private_identity_sha256=private)


def inventory_summary(value):
    return dict(sha256=sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()),
                files=len(value["files"]), bytes=sum(item["bytes"] for item in value["files"].values()))


def verify_install_continuity(before, container, prior, record):
    after = account_storage_inventory(container)
    record.update(before=inventory_summary(before), after=inventory_summary(after))
    require(before == after, "App install changed or removed original native account data")
    require(after["private_identity_sha256"]["ledger.json"] == prior["nextLedgerSHA256"],
            "App install changed or removed the preceding account ledger")
    record["status"] = "PASS_ALL_NATIVE_FILES_AND_PRIVATE_IDENTITY_UNCHANGED"


def verify_current_root(report, container):
    actual = (container / ROOT_RELATIVE_PATH).resolve(strict=True)
    require(actual.is_dir() and actual.is_relative_to(container.resolve(strict=True)),
            "Actual native account root missing or escaped")
    require(report.get("currentRootPathSHA256") == sha_bytes(str(actual).encode()),
            "Native receipt differs from the actual current account root")


def preserve_private_credential_inventory(container, work, token):
    source = container / PAIR_RELATIVE_PATH / "secrets.json"
    require(not source.is_symlink() and source.resolve(strict=True).is_relative_to(container.resolve(strict=True)),
            "Disposable credential inventory escaped its owned container")
    raw = source.read_bytes()
    value = json.loads(raw)
    require(value.get("token") == token and all(isinstance(value.get(key), str) and value[key]
            for key in ["mnemonic", "accountKey"]), "Disposable secret guard is incomplete")
    destination = work / "credential-inventory.json"
    # Preserve the original values before any update can move or lose the data
    # container. Never substitute later credentials for the original inventory.
    if destination.exists():
        require(destination.read_bytes() == raw, "Original disposable credential inventory changed")
    else:
        with destination.open("xb") as stream:
            stream.write(raw)
        destination.chmod(0o600)
    return destination


def contains_secret(path, needles):
    overlap = max(map(len, needles), default=1) - 1
    previous = b""
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(128 * 1024), b""):
            combined = previous + data
            if any(needle in combined for needle in needles):
                return True
            previous = combined[-overlap:] if overlap else b""
    return False


def preserve_native_evidence(work, proof, container, token, include_freshness=False, credential_inventory=None):
    destination = proof / "actual-phases"
    require(not destination.exists(), "Refuse stale public native evidence")
    candidates = []
    secrets_path = credential_inventory or (container / PAIR_RELATIVE_PATH / "secrets.json" if container else None)
    if not secrets_path or not secrets_path.is_file():
        write(proof / "native-evidence-policy.json", dict(status="WITHHELD_NO_SECRET_INVENTORY",
              raw_xcresult_uploaded=False, account_data_uploaded=False))
        return False
    secret_record = json.loads(secrets_path.read_text(encoding="utf8"))
    require(secret_record.get("token") == token and all(isinstance(secret_record.get(key), str) and secret_record[key]
            for key in ["mnemonic", "accountKey"]), "Disposable secret guard is incomplete")
    values = [secret_record[key] for key in ["mnemonic", "accountKey"]]
    needles = [value.encode(encoding) for value in values for encoding in ["utf8", "utf-16-le", "utf-16-be"]]
    allowed = ["test.log", "test.command.json", "summary.json", "tests.json", "receipt.json",
               "result.json", "selection.json", "install.log", "install.command.json",
                "terminate.log", "terminate.command.json", "export-summary.command.json", "export-tests.command.json",
                "install-continuity.json"]
    for phase, _ in phases(include_freshness):
        directory = work / "phases" / phase
        for filename in allowed:
            path = directory / filename
            if path.is_file():
                require(not path.is_symlink() and path.resolve().is_relative_to(work.resolve()), "Native evidence escaped owned work")
                require(not contains_secret(path, needles), "Disposable credential found; all native evidence withheld")
                candidates.append((path, destination / phase / filename))
    for source, target in candidates:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    write(proof / "native-evidence-policy.json", dict(status="PASS", copied_files=[
          str(target.relative_to(proof)) for _, target in candidates], raw_xcresult_uploaded=False,
          account_data_uploaded=False, secrets_uploaded=False, scanned_complete_credential_encodings=3))
    return True


def run_phase(phase, role, build, app, work, udid, source, token, nonce, container, prior, ui, method_results):
    directory = work / "phases" / phase
    directory.mkdir(parents=True)
    record = dict(status="RUNNING", phase=phase, role=role, actual_test_counts=None)
    write(directory / "result.json", record)
    try:
        run_logged(["xcrun", "simctl", "terminate", udid, BUNDLE], app, directory, "terminate", 30, check=False)
        before = account_storage_inventory(container) if prior else None
        run_logged(["xcrun", "simctl", "install", udid, build["app"]], app, directory, "install", 120)
        actual_container = app_container(udid, "data")
        if prior:
            continuity = dict(status="FAIL", original_container_path_sha256=sha_bytes(str(container).encode()),
                              installed_container_path_sha256=sha_bytes(str(actual_container).encode()),
                              container_relocated=actual_container != container)
            try:
                verify_install_continuity(before, actual_container, prior, continuity)
            finally:
                write(directory / "install-continuity.json", continuity)
        with Path(build["configuration"]).open("rb") as stream:
            configuration = plistlib.load(stream)
        environment = {
            "PINKHA_T5_APPLE_PAIR": "1", "PINKHA_T5_PAIR_PHASE": phase, "PINKHA_T5_PAIR_TOKEN": token,
            "PINKHA_T5_PAIR_NONCE": nonce, "PINKHA_T5_PAIR_APP_SHA": source,
        }
        ui.inject(configuration, "AnytypeTests", environment)
        selected = Path(build["configuration"]).with_name("UI27-t5-pair-" + phase + ".xctestrun")
        require(not selected.exists(), "Refuse stale XCTest selection")
        selected.write_bytes(plistlib.dumps(configuration))
        write(directory / "selection.json", dict(method=METHOD, environment=environment,
              device_udid=udid, xctestrun_sha256=digest(selected), packaged_code_sha256=build["code_sha256"]))
        bundle = directory / "original.xcresult"
        command = ["xcodebuild", "test-without-building", "-xctestrun", str(selected),
                   "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                   "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "300",
                   "-maximum-test-execution-time-allowance", "300",
                   "-only-testing:AnytypeTests/TorahT5RuntimePairTests", "-resultBundlePath", str(bundle)]
        outcome, _ = run_logged(command, app, directory, "test", 600, check=False)
        record.update(command_exit_code=outcome["return_code"], timed_out=outcome.get("timed_out", False))
        if bundle.exists():
            for mode in ["summary", "tests"]:
                run_logged(["xcrun", "xcresulttool", "get", "test-results", mode, "--path", str(bundle), "--format", "json"],
                           app, directory, "export-" + mode, 120, check=False, output=directory / (mode + ".json"))
        actual_container = app_container(udid, "data")
        installed = app_container(udid, "app")
        require(ui.code_carriers(installed)["sha256"] == build["code_sha256"],
                "Actual installed executable bytes differ from the selected packaged runtime")
        summary = json.loads((directory / "summary.json").read_text(encoding="utf8"))
        methods = method_results(json.loads((directory / "tests.json").read_text(encoding="utf8")))
        record["actual_test_counts"] = {key: summary.get(key) for key in ["passedTests", "failedTests", "skippedTests"]}
        require(outcome["return_code"] == 0 and not outcome.get("timed_out"), "Actual selected Swift test process failed")
        validate_xcresult(summary, methods, udid)
        fixture_directory = actual_container / "Library/Application Support/pinkha-t5-runtime-pair"
        receipt_path = fixture_directory / ("result-" + phase + ".json")
        ledger_path = fixture_directory / "ledger.json"
        report = json.loads(receipt_path.read_text(encoding="utf8"))
        ledger = json.loads(ledger_path.read_text(encoding="utf8"))
        shutil.copyfile(receipt_path, directory / "receipt.json")
        verify_current_root(report, actual_container)
        validate_phase(report, phase, role, token, nonce, source, ledger, digest(ledger_path), prior)
        record.update(status="PASS", actual_host_process_id=report["processID"],
                      original_account_root_path_sha256=report["rootPathSHA256"],
                      current_account_root_path_sha256=report["currentRootPathSHA256"],
                      container_path_sha256=sha_bytes(str(actual_container).encode()),
                      installed_code_sha256=build["code_sha256"], actual_methods=methods)
        return report, actual_container
    finally:
        if record["status"] != "PASS":
            record["status"] = "FAIL"
        write(directory / "result.json", record)


def shutdown_owned_simulator(udid, app, proof, result, primary_error):
    """Shut down only the validated job-owned device without masking a primary failure."""
    record = dict(status="RUNNING", action="shutdown", device_udid=udid,
                  primary_error_type=type(primary_error).__name__ if primary_error is not None else None,
                  started_at=datetime.now(timezone.utc).isoformat())
    result["simulator_cleanup"] = record
    cleanup_error = None
    try:
        metadata, _ = run_logged(["xcrun", "simctl", "shutdown", udid], app,
                                 proof / "simulator", "shutdown", 120, check=False)
        record["return_code"] = metadata["return_code"]
        require(metadata["return_code"] == 0, "Job-owned simulator shutdown failed; original command output retained")
        record["status"] = "PASS"
    except BaseException as error:
        record.update(status="FAIL", error_type=type(error).__name__)
        cleanup_error = error
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    try:
        write(proof / "simulator/cleanup.json", record)
    except BaseException as error:
        record.update(status="FAIL", receipt_error_type=type(error).__name__)
        if cleanup_error is None:
            cleanup_error = error
    if cleanup_error is not None and primary_error is None:
        raise cleanup_error


def execute(args, result):
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon Mac required")
    require(sys.version_info >= (3, 12), "Python3.12 required for safe original archive extraction")
    app, native_source, work, proof, derived = [path.resolve() for path in
                                             [args.app, args.native_source, args.work, args.evidence, args.derived]]
    require(len({app, native_source, work, proof, derived}) == 5, "Separate source/work/proof/derived paths required")
    require(not work.exists(), "Fresh controller-owned private work directory required")
    work.mkdir(parents=True, mode=0o700)
    source = verify_published_source(app, proof)
    require(git(native_source, "rev-parse", "HEAD") == NATIVE_SOURCE
            and not git(native_source, "status", "--porcelain"), "Exact immutable native inventory checkout required")
    preflight = json.loads((proof / "preflight/preflight.json").read_text(encoding="utf8"))
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
            and preflight.get("source_sha") == source, "Actual source-bound Xcode27 preflight required")
    selection = preflight["selected"]["ipad"]
    udid = selection["udid"]
    require(selection["name"] == "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-ipad",
            "Fresh job-owned simulator identity differs")
    require(shutil.disk_usage(work).free >= 8 * 1024**3, "Free disk reserve below8GiB")
    helper_path = app / "Tools/PinkhaNativeDerived"
    require(digest(helper_path / "build_custom_heart.py", True) == BUILDER_SHA, "Reviewed runtime helper source changed")
    sys.path.insert(0, str(helper_path))
    sys.path.insert(0, str(app / "Tools/PinkhaSimulatorGate"))
    import build_custom_heart as heart_helper
    import build_native_ipa as native_helper
    import run_ui27 as ui
    from validate_release import method_results
    result.update(app_source_sha=source, run_id=os.environ["GITHUB_RUN_ID"], device_udid=udid,
                  app_flags=FLAGS, expected_runtime_versions={role: runtime_version(role) for role in ["old", "new"]})
    write(proof / "result.json", result)
    try:
        run_logged(["xcrun", "simctl", "boot", udid], app, proof / "simulator", "boot", 120)
        run_logged(["xcrun", "simctl", "bootstatus", udid, "-b"], app, proof / "simulator", "boot-status", 180)
        require(app_container(udid, "data", required=False) is None, "Fresh simulator unexpectedly contains an app account")
        builds = {}
        for role, run_id in [("old", args.heart_r14_run_id), ("new", args.heart_r15_run_id)]:
            runtime_proof = proof / ("runtime-" + role)
            archive, source_run = download_runtime(role, run_id, work, runtime_proof, os.environ["GITHUB_REPOSITORY"])
            installed = install_runtime(role, archive, source_run, app, native_source, work, runtime_proof, heart_helper)
            builds[role] = build_app(role, app, derived, work, proof / ("build-" + role), udid, source, (ui, native_helper))
            shutil.move(str(installed), work / ("installed-framework-" + role))
            result["completed_builds"] = list(builds)
            write(proof / "result.json", result)
        token, reports, container, credential_inventory = uuid4().hex, [], None, None
        result["phase"] = "ACTUAL_NATIVE_EXECUTION"
        write(proof / "result.json", result)
        try:
            for phase, role in phases(args.include_freshness):
                result["active_phase"] = phase
                write(proof / "result.json", result)
                report, container = run_phase(phase, role, builds[role], app, work, udid, source,
                                             token, uuid4().hex, container, reports[-1] if reports else None, ui, method_results)
                credential_inventory = preserve_private_credential_inventory(container, work, token)
                reports.append(report)
                result["completed_phases"] = [item["phase"] for item in reports]
                write(proof / "result.json", result)
            result["actual_counts"] = validate_sequence(reports, builds, args.include_freshness)
            require(git(app, "rev-parse", "HEAD") == source and not git(app, "status", "--porcelain"),
                    "Application source changed during the actual native sequence")
        finally:
            container = app_container(udid, "data", required=False)
            secret_scan_passed = preserve_native_evidence(work, proof, container, token, args.include_freshness,
                                                         credential_inventory=credential_inventory)
    finally:
        shutdown_owned_simulator(udid, app, proof, result, primary_error=sys.exc_info()[1])
    require(secret_scan_passed, "Complete private credential inventory required before public acceptance")
    result.update(status="APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS", phase_reports=reports[:len(PHASES)],
                  freshness_report=reports[-1] if args.include_freshness else None,
                  host_freshness_status=FRESHNESS_STATUS if args.include_freshness else "NOT_REQUESTED",
                  exact_same_app_source=True, full_F10="NOT_PROVEN", product_lookup_flag="OFF")
    if args.include_native_ui:
        from run_t5_native_ui import continue_with_native_ui
        continue_with_native_ui(app=app, work=work, proof=proof, result=result, build=builds["new"],
                                pair_container=container, selection=selection, pair=sys.modules[__name__],
                                ui=ui, method_results=method_results)


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["app", "native-source", "work", "evidence", "derived"]:
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ["heart-r14-run-id", "heart-r15-run-id"]:
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--include-freshness", action="store_true")
    parser.add_argument("--include-native-ui", action="store_true")
    args = parser.parse_args(argv)
    if args.include_native_ui and not args.include_freshness:
        parser.error("--include-native-ui requires the actual optional fifth freshness phase")
    args.evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status="RUNNING", phase="PREFLIGHT", started_at=datetime.now(timezone.utc).isoformat(),
                  completed_builds=[], completed_phases=[], actual_counts=None, include_freshness=args.include_freshness,
                  include_native_ui=args.include_native_ui, native_ui_status="NOT_RUN" if args.include_native_ui else "NOT_REQUESTED",
                  product_lookup_flag="OFF", test_only_lookup_flag="IDENTICAL_BOTH_APP_BUILDS",
                  full_F10="NOT_PROVEN", release_accepted=False, full_matrix_accepted=False,
                  scope="same exact app source; two original Apple runtimes; four compatibility processes on one fresh OS27 iPad account"
                        + ("; optional fifth process proves bounded host freshness after intentional disposable mutations" if args.include_freshness else ""),
                  limitations=["Actual Linux account/export proof is separate", "Space-wide index freshness remains unproven",
                               "No visual UI, physical-device, TestFlight or release acceptance from this route"])
    write(args.evidence / "result.json", result)
    try:
        execute(args, result)
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    write(args.evidence / "result.json", result)
    print(json.dumps({key: result[key] for key in ["status", "completed_builds", "completed_phases", "actual_counts",
                                                    "product_lookup_flag", "full_F10"]}))
    return 0 if result["status"] in {"APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS",
                                    "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_AND_UI_PASS_VISUAL_REVIEW_PENDING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
