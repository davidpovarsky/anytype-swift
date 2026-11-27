#!/usr/bin/env python3
"""Read and export one original Apple dependency archive without copying it.

The pinned artifact action reads the existing compressed file directly. A
finalized artifact is only transport evidence: before/after source custody and
independent downloaded a20 bytes are both required before a later native build.
This controller spawns no child process, creates no FIFO and never signals a PID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tarfile
import time

SCHEMA = "pinkha-original-native-dependency-ingress-v1"
SOURCE = Path("/Users/m1/development/anytype-d-active-20261125/native-immutable/inputs-11619a9928d6-8393d79/native-dependencies.tar.gz")
ARCHIVE_BYTES = 55038316
ARCHIVE_SHA = "a20d84bcffa31bab35909ad0555142ec5b1f54f07c1482fb023675ad81309159"
MANIFEST_SHA = "8c63151616ed8fdd4f5c2bb7b4418d9f134fe4574e52a23d8ac049d68aef385b"
CONTROLLER = "Tools/PinkhaDualEngineRuntime/native_dependency_ingress/ingress.py"
WORKFLOW = ".github/workflows/torah-inspector-ipados27.yml"
EXPECTED = {
    "dependency-manifest.json": (1130, MANIFEST_SHA),
    "ios-arm64/libtantivy_go.a": (37144736, "598f4d40afa384f5364a234bffd07133a31f80c2bb4228491382fd95ff6e3e0e"),
    "ios-arm64/original-release.tar.gz": (15639239, "c949c72ac58601ef02f5b5e11569fbf21970a6afcd05d1ac645e78174398ccde"),
    "ios-arm64/transform.json": (1350, "29ee6188b9bd77ec3129fbd0fedc0a6ce14ba93b2148e94e0a958ba46330c455"),
    "ios-arm64-sim/libtantivy_go.a": (37079896, "aafce3613a1ec63a0cca3fa2acf08cf56cb5ebefe6dc03a88f5702cdc4981652"),
    "ios-arm64-sim/original-release.tar.gz": (15625269, "8902d1608a2263597f8f9fa9d7d4155e8ec5efe4701cc0db03905c170c25899a"),
    "ios-arm64-sim/transform.json": (1358, "4368030a405c9cb083af018df47300cd978c0109c445c3b839a2b45d18bef797"),
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata(value):
    # Reads may update atime; identity and all mutation-sensitive fields remain.
    return {name: getattr(value, name) for name in (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns")}


def read_small(path, maximum):
    require(path.resolve(strict=True) == path, "canonical_original_input_required")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as incoming:
        before = os.fstat(incoming.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
                "bounded_regular_input_required")
        raw = incoming.read(maximum + 1)
        require(len(raw) == before.st_size and metadata(before) == metadata(os.fstat(incoming.fileno()))
                == metadata(path.lstat()), "original_input_changed_during_read")
    return raw


def write_new(path, value):
    raw = value if isinstance(value, bytes) else encoded(value)
    with path.open("xb") as outgoing:
        outgoing.write(raw)
        outgoing.flush()
        os.fsync(outgoing.fileno())


def qualified_archive():
    require(SOURCE.resolve(strict=True) == SOURCE, "canonical_exact_original_archive_required")
    started = time.monotonic()
    with os.fdopen(os.open(SOURCE, os.O_RDONLY | os.O_NOFOLLOW), "rb") as incoming:
        before = os.fstat(incoming.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == ARCHIVE_BYTES,
                "exact_original_archive_size_required")
        h = hashlib.sha256()
        for chunk in iter(lambda: incoming.read(1024**2), b""):
            h.update(chunk)
            require(time.monotonic() - started < 120, "original_archive_read_deadline")
        require(h.hexdigest() == ARCHIVE_SHA, "original_archive_bytes_changed")
        incoming.seek(0)
        rows, small = {}, {}
        with tarfile.open(fileobj=incoming, mode="r:gz") as archive:
            for member in archive:
                require(member.name in EXPECTED and member.name not in rows and member.isfile()
                        and member.size == EXPECTED[member.name][0]
                        and member.mode == 0o644, "closed_original_seven_member_inventory_required")
                member_hash, count, retained = hashlib.sha256(), 0, []
                with archive.extractfile(member) as data:
                    for chunk in iter(lambda: data.read(1024**2), b""):
                        member_hash.update(chunk)
                        count += len(chunk)
                        require(count <= member.size and time.monotonic() - started < 120,
                                "original_member_read_bound")
                        if member.size < 65536:
                            retained.append(chunk)
                require((count, member_hash.hexdigest()) == EXPECTED[member.name],
                        "original_dependency_member_changed:" + member.name)
                rows[member.name] = {"bytes": count, "sha256": member_hash.hexdigest(), "mode": member.mode}
                if retained:
                    small[member.name] = json.loads(b"".join(retained))
        require(set(rows) == set(EXPECTED), "original_dependency_archive_incomplete")
        manifest = small["dependency-manifest.json"]
        require(manifest["contract"] == "pinkha-dual-native-dependencies-v1"
                and manifest["version"] == "v1.0.6"
                and manifest["files"] == {name: {"bytes": row["bytes"], "sha256": row["sha256"]}
                                          for name, row in rows.items() if name != "dependency-manifest.json"},
                "original_dependency_manifest_changed")
        for target in ("ios-arm64", "ios-arm64-sim"):
            proof = small[target + "/transform.json"]
            require(proof["contract"] == "pinkha-native-embedded-llvm-removal-v2"
                    and proof["verified"] is True
                    and proof["nativeSHA256"] == EXPECTED[target + "/libtantivy_go.a"][1]
                    and proof["nativeCodeDataSymbolsRelocationTargetsUnchanged"] is True
                    and proof["goLTOGuardDisabled"] is False
                    and proof["removedLegacyLLVMSections"] == 474
                    and proof["originalPinnedReleaseRetained"] is True,
                    "original_apple_transformation_proof_changed")
        after = os.fstat(incoming.fileno())
        require(metadata(before) == metadata(after) == metadata(SOURCE.lstat()),
                "original_archive_identity_changed_during_read")
    return {"path": str(SOURCE), "bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA,
            "metadata": metadata(before), "members": rows,
            "dependencyManifestSHA256": MANIFEST_SHA}


def validate_plan(raw, expected_sha, control):
    require(len(raw) < 32768 and re.fullmatch(r"[0-9a-f]{64}", expected_sha)
            and digest(raw) == expected_sha, "exact_root_plan_bytes_required")
    plan = json.loads(raw)
    require(set(plan) == {"schema", "readyForExport", "control", "archive", "dependencyManifestSHA256",
                          "nativeAcceptanceClaimed"}
            and plan["schema"] == SCHEMA and plan["readyForExport"] is True
            and plan["nativeAcceptanceClaimed"] is False, "closed_root_export_plan_required")
    require(plan["archive"] == {"path": str(SOURCE), "bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA}
            and plan["dependencyManifestSHA256"] == MANIFEST_SHA,
            "only_original_a20_archive_may_be_exported")
    owner = plan["control"]
    require(set(owner) == {"commit", "files"} and re.fullmatch(r"[0-9a-f]{40}", owner["commit"])
            and owner["commit"] == os.environ["GITHUB_SHA"]
            and os.environ["GITHUB_REPOSITORY"] == "davidpovarsky/anytype-swift"
            and set(owner["files"]) == {CONTROLLER, WORKFLOW}, "exact_registered_control_commit_required")
    require(control.is_absolute() and control.resolve(strict=True) == control
            and Path(__file__).resolve(strict=True) == control / CONTROLLER,
            "exact_executed_control_path_required")
    for name, sha in owner["files"].items():
        require(re.fullmatch(r"[0-9a-f]{64}", sha)
                and digest(read_small(control / name, 128 * 1024)) == sha,
                "root_reviewed_control_file_changed:" + name)
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(platform.system() == "Darwin" and platform.machine() == "arm64"
            and sys.version_info[:2] == (3, 12), "original_mac_python_runtime_required")
    run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    require(run.isdecimal() and int(run) > 0 and attempt.isdecimal() and int(attempt) > 0,
            "actual_actions_run_identity_required")
    temporary = Path(os.environ["RUNNER_TEMP"])
    require(temporary.resolve(strict=True) == temporary
            and args.output == temporary / ("pinkha-original-native-dependencies-" + run + "-" + attempt)
            and args.plan == temporary / ("pinkha-native-dependencies-plan-" + run + "-" + attempt + ".json"),
            "run_owned_output_paths_required")
    raw = (os.environ["PINKHA_HOSTED_PLAN"].encode() if args.phase == "before"
           else read_small(args.plan, 32768))
    plan = validate_plan(raw, args.plan_sha256, args.control)
    os.umask(0o077)
    if args.phase == "before":
        require(not args.output.exists() and not args.output.is_symlink()
                and not args.plan.exists() and not args.plan.is_symlink(), "fresh_ingress_claim_required")
        args.output.mkdir(mode=0o700)
        write_new(args.plan, raw)
    else:
        require(args.output.resolve(strict=True) == args.output
                and args.output.is_dir() and not (args.output / "receipt.json").exists(),
                "one_original_export_finalization_required")
    result = {"schema": SCHEMA, "phase": args.phase, "status": "FAIL_ORIGINAL_DEPENDENCY_INGRESS",
              "runID": int(run), "runAttempt": int(attempt), "controlCommit": plan["control"]["commit"],
              "controllerSHA256": plan["control"]["files"][CONTROLLER],
              "planSHA256": args.plan_sha256, "startedAt": time.time(),
              "nativeBuilds": 0, "applicationBuilds": 0, "testsExecuted": 0,
              "sourceArchiveCreated": False, "nativeAcceptanceClaimed": False,
              "ownedProducerProcessesCreated": 0, "FIFOObjectsCreated": 0,
              "independentDownloadedArchiveReadbackRequired": True}
    first = None
    try:
        result["archive"] = qualified_archive()
        if args.phase == "before":
            result["status"] = "PASS_ORIGINAL_ARCHIVE_BEFORE_UPLOAD_NOT_EXPORTED"
        else:
            before_raw = read_small(args.output / "before.json", 32768)
            before = json.loads(before_raw)
            require(before["status"] == "PASS_ORIGINAL_ARCHIVE_BEFORE_UPLOAD_NOT_EXPORTED"
                    and before["runID"] == int(run) and before["runAttempt"] == int(attempt)
                    and before["controlCommit"] == result["controlCommit"]
                    and before["controllerSHA256"] == result["controllerSHA256"]
                    and before["planSHA256"] == args.plan_sha256
                    and before["archive"] == result["archive"], "original_source_changed_across_upload")
            artifact_id, artifact_sha = os.environ["ARTIFACT_ID"], os.environ["ARTIFACT_DIGEST"]
            require(artifact_id.isdecimal() and int(artifact_id) > 0
                    and re.fullmatch(r"[0-9a-f]{64}", artifact_sha), "actual_artifact_identity_required")
            result.update(status="PASS_EXPORTED_ORIGINAL_DEPENDENCIES_NOT_NATIVE_ACCEPTANCE",
                          beforeReceiptSHA256=digest(before_raw),
                          artifactID=int(artifact_id), artifactZIPDigest=artifact_sha,
                          allOriginalSourceMetadataAndBytesUnchanged=True)
    except BaseException as error:
        first = error
        result["firstFailure"] = {"type": type(error).__name__, "message": str(error)}
    result["finishedAt"] = time.time()
    terminal = args.output / ("before.json" if args.phase == "before" else "receipt.json")
    try:
        write_new(terminal, result)
    except BaseException as receipt_error:
        result["receiptWriteFailure"] = {"type": type(receipt_error).__name__, "message": str(receipt_error)}
        if first is None:
            first = receipt_error
    try:
        print(json.dumps(result, sort_keys=True), flush=True)
    except BaseException:
        if first is None:
            raise
    if first is not None:
        raise first


if __name__ == "__main__":
    main()
