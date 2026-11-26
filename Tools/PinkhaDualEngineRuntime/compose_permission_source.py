#!/usr/bin/env python3
"""Compose the exact qualified T2 HTTP error delta onto retained native11619.

Source composition and the existing Oracle unit result are recorded separately
from the pending real mixed-peer, Apple slice and application qualifications.
"""
from __future__ import annotations
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

REPO = Path("/mnt/development/projects/worktrees/anytype-native-d-completion-20261125")
HERE = REPO / "Tools/PinkhaDualEngineRuntime"
ANY = Path("/mnt/development/projects/worktrees/any-t2-permission-boundary-20261126")
SDK = Path("/mnt/development/projects/worktrees/any-sync-sdk-prepared-collection-owner-20261124")
BASE = "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
OLD_ANY = "41c07bd32e95a54824a3d3c5d592accf5074ab68"
NEW_ANY = "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81"
SDK_COMMIT = "c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"
OLD_ARCHIVE = Path("/mnt/development/projects/evidence/native-d-final-20261125/native-immutable-20261126/native-source-11619a9928d6.tar.gz")
OLD_ARCHIVE_SHA = "4e7a090e17b489536c7f7f72633010d8131b0f185d069b5ed3d05520eb13bb13"
EXPORT = Path("/mnt/development/projects/evidence/t2-native-permission-boundary-20261126/source-exports/current-source-manifest.json")
EXPORT_SHA = "12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"
EXPORT_ARCHIVE = EXPORT.with_name("current-source.tar.gz")
EXPORT_ARCHIVE_SHA = "90f08ed6d334df44c975082731e8e9e377e5e13dc4374fb50abca711553ddd67"
UNIT_PATH = "docs/validation/20261126-native-acl-boundary/unit-result.json"
UNIT_SHA = "4ec74e54823d308c227ddc9288fac53281ad8e7535abf31489294b808abf0cba"
CHANGES = [
    ("A", "docs/validation/20261126-native-acl-boundary/README.md"),
    ("A", "docs/validation/20261126-native-acl-boundary/run_unit1.py"),
    ("A", "docs/validation/20261126-native-acl-boundary/source-admission.json"),
    ("A", "docs/validation/20261126-native-acl-boundary/unit-original.jsonl"),
    ("A", UNIT_PATH),
    ("M", "internal/server/handlers_common.go"),
    ("A", "internal/server/handlers_native_acl_error_test.go"),
]
OUT = Path("/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126")
DOCS = REPO / "docs/validation/20261126-native-permission-composition"


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def git(root, *args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + str(root), "-C", str(root), *args], timeout=60)


def put(path, data, public=False):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755 if public else 0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o644 if public else 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if public:
        owner = REPO.stat()
        os.chown(path, owner.st_uid, owner.st_gid)


def main():
    old_bytes = (HERE / "source-immutable-manifest.json").read_bytes()
    require(sha(old_bytes) == BASE, "original_11619_manifest_changed")
    old = json.loads(old_bytes)
    require(old["sourcePins"]["any"] == OLD_ANY and old["sourcePins"]["sdk"] == SDK_COMMIT
            and len(old["files"]) == 4862, "original_native_closure_changed")
    require(shutil.disk_usage(OUT.parent).free > 128 * 1024**2, "source_archive_incremental_headroom_unavailable")
    require(sha(OLD_ARCHIVE.read_bytes()) == OLD_ARCHIVE_SHA, "retained_11619_archive_changed")
    export_bytes = EXPORT.read_bytes()
    require(sha(export_bytes) == EXPORT_SHA and sha(EXPORT_ARCHIVE.read_bytes()) == EXPORT_ARCHIVE_SHA,
            "root_original_source_export_changed")
    export = json.loads(export_bytes)
    require(export["commits"] == {"any": NEW_ANY, "sdk": SDK_COMMIT}
            and len(export["files"]) == 1594, "exact_new_native_export_required")
    actual_delta = git(ANY, "diff", "--name-status", OLD_ANY, NEW_ANY).decode().splitlines()
    require(actual_delta == [kind + "\t" + path for kind, path in CHANGES], "closed_8fbd_delta_changed")
    unit_bytes = git(ANY, "show", NEW_ANY + ":" + UNIT_PATH)
    require(sha(unit_bytes) == UNIT_SHA, "original_native_unit_receipt_changed")
    unit = json.loads(unit_bytes)
    require(unit["status"] == "PASS" and unit["exitCode"] == 0 and unit["packagePass"] is True
            and unit["fail"] == [] and unit["skip"] == [] and unit["sourceBefore"] == unit["sourceAfter"],
            "actual_unchanged_native_unit_result_required")

    contents, modes = {}, {}
    with tarfile.open(OLD_ARCHIVE, "r:gz") as archive:
        for entry in archive:
            require(entry.isfile() and entry.name not in contents and not entry.name.startswith("/")
                    and all(part not in ("", ".", "..") for part in entry.name.split("/")),
                    "closed_original_source_members_required")
            contents[entry.name] = archive.extractfile(entry).read()
            modes[entry.name] = entry.mode & 0o777
    require(set(contents) == set(old["files"]) | {"source-manifest.json"}
            and contents.pop("source-manifest.json") == old_bytes, "original_archive_manifest_differs")
    modes.pop("source-manifest.json")
    for name, row in old["files"].items():
        require({"bytes": len(contents[name]), "sha256": sha(contents[name])} == row,
                "original_source_blob_changed:" + name)

    new = copy.deepcopy(old)
    delta = []
    for kind, path in CHANGES:
        name = "any/" + path
        before = old["files"].get(name)
        if kind == "A":
            require(name not in contents, "new_native_path_already_exists")
        else:
            require(name in contents and git(ANY, "show", OLD_ANY + ":" + path) == contents[name],
                    "old_unified_blob_does_not_match_actual_parent")
        data = git(ANY, "show", NEW_ANY + ":" + path)
        row = {"bytes": len(data), "sha256": sha(data)}
        contents[name], new["files"][name] = data, row
        modes.setdefault(name, 0o644)
        delta.append({"status": kind, "path": name, "before": before, "after": row})
    require(len(contents) == 4868, "new_native_source_count_differs")
    # Both complete Git trees and the separately retained root export must match.
    git_entries = {}
    for root, commit, prefix in ((ANY, NEW_ANY, "any/"),
                                  (SDK, SDK_COMMIT, "any/.runtime-artifacts/sdk-source/")):
        paths = git(root, "ls-tree", "-r", "--name-only", commit).decode().splitlines()
        for line in git(root, "ls-tree", "-r", commit).decode().splitlines():
            metadata, name = line.split("\t", 1)
            mode, kind, blob = metadata.split()
            require(kind == "blob" and mode in ("100644", "100755"), "closed_native_git_mode_required")
            git_entries[(prefix + name)[4:]] = {"gitMode": mode, "gitBlob": blob, "source": "any" if prefix == "any/" else "sdk", "sourceCommit": commit}
        actual = {name[len(prefix):] for name in contents if name.startswith(prefix)
                  and not (prefix == "any/" and name.startswith("any/.runtime-artifacts/sdk-source/"))}
        require(actual == set(paths), "whole_native_git_tree_paths_differ")
        with tarfile.open(fileobj=io.BytesIO(git(root, "archive", "--format=tar", commit)), mode="r:") as archive:
            seen = set()
            for entry in archive:
                if entry.isdir():
                    continue
                require(entry.isfile() and entry.name in actual, "unexpected_native_git_member")
                require(archive.extractfile(entry).read() == contents[prefix + entry.name],
                        "whole_native_git_tree_bytes_differ")
                seen.add(entry.name)
            require(seen == actual, "native_git_tree_incomplete")
    native_rows = {name[4:]: row for name, row in new["files"].items() if name.startswith("any/")}
    require(set(native_rows) == set(export["files"]) == set(git_entries),
            "original_root_source_export_path_inventory_differs")
    root_export_mode_differences = []
    for name, row in export["files"].items():
        require(set(row) == {"bytes", "sha256", "gitBlob", "gitMode", "kind", "mode", "source", "sourceCommit"}
                and row["kind"] == "file" and type(row["mode"]) is int and 0 <= row["mode"] <= 0o777,
                "closed_original_root_export_schema_required")
        require({key: row[key] for key in ("bytes", "sha256")} == native_rows[name]
                and all(row[key] == value for key, value in git_entries[name].items()),
                "original_root_source_export_content_or_git_provenance_differs:" + name)
        # Preserve previously qualified unified source modes. The root export
        # records its own checkout modes; no mode equality is implied here.
        if row["mode"] != modes["any/" + name]:
            root_export_mode_differences.append({"path": "any/" + name,
                "rootExportMode": row["mode"], "unifiedArchiveMode": modes["any/" + name],
                "gitMode": row["gitMode"]})
    unchanged = set(old["files"]) - {row["path"] for row in delta}
    require(all(new["files"][name] == old["files"][name] for name in unchanged),
            "unrelated_unified_source_changed")
    require(sum(name.startswith("heart/") for name in contents) == 2692
            and sum(name.startswith("sync/") for name in contents) == 580
            and {name for name in contents if "/" not in name} == {"go.work", "go.work.sum"},
            "heart_sync_workspace_closure_changed")
    new["sourcePins"]["any"] = NEW_ANY
    new["predecessorSourceManifestSHA256"] = BASE
    new["runtimeBuildDate"] = "2026-11-26"
    new["nativeACLHTTPBoundary"] = {
        "anyCommit": NEW_ANY, "originalAnyCommit": OLD_ANY, "sdkCommitUnchanged": SDK_COMMIT,
        "sourceExportManifestSHA256": EXPORT_SHA, "sourceExportArchiveSHA256": EXPORT_ARCHIVE_SHA,
        "actualOracleUnitReceiptSHA256": UNIT_SHA,
        "actualOracleMethods": 4, "actualOracleLeafCases": 9,
        "qualifiedScope": "ACTUAL_ORACLE_NATIVE_HTTP_UNIT_ONLY_AT_SOURCE_COMPOSITION",
        "mixedPeerQualification": "SEPARATE_ORIGINAL_RECEIPT_REQUIRED_BEFORE_APPLE_PRODUCER",
        "productionChangedPaths": ["any/internal/server/handlers_common.go"],
        "nativeACLBehaviorChanged": False, "applicationAcceptanceClaimed": False,
    }
    manifest_bytes = encoded(new)
    manifest_sha = sha(manifest_bytes)
    OUT.mkdir(mode=0o700, exist_ok=True)
    archive_path = OUT / ("native-source-" + manifest_sha[:12] + ".tar.gz")
    with archive_path.open("xb") as raw:
        os.chmod(archive_path, 0o600)
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name in sorted(contents):
                    entry = tarfile.TarInfo(name)
                    entry.size, entry.mode, entry.mtime = len(contents[name]), modes[name], 0
                    archive.addfile(entry, io.BytesIO(contents[name]))
                entry = tarfile.TarInfo("source-manifest.json")
                entry.size, entry.mode, entry.mtime = len(manifest_bytes), 0o644, 0
                archive.addfile(entry, io.BytesIO(manifest_bytes))
        raw.flush()
        os.fsync(raw.fileno())
    with tarfile.open(archive_path, "r:gz") as archive:
        observed = {}
        for entry in archive:
            require(entry.isfile() and entry.name not in observed, "composed_member_invalid")
            data = archive.extractfile(entry).read()
            observed[entry.name] = {"bytes": len(data), "sha256": sha(data)}
    require(observed.pop("source-manifest.json") == {"bytes": len(manifest_bytes), "sha256": manifest_sha}
            and observed == new["files"], "composed_archive_exact_readback_failed")
    info = {
        "archive": str(archive_path), "bytes": archive_path.stat().st_size,
        "sha256": sha(archive_path.read_bytes()), "manifestSHA256": manifest_sha,
        "sourceFiles": len(contents), "buildDate": new["runtimeBuildDate"],
        "heartVersion": "pinkha-dual-runtime-v1-" + manifest_sha,
        "anyVersion": "v0.5.0-pinkha.dual.1-" + manifest_sha,
        "anyRuntimeVersion": "any v0.5.0-pinkha.dual.1-" + manifest_sha
                             + " (commit " + NEW_ANY + ", built 2026-11-26)",
        "qualification": "SOURCE_COMPOSITION_ONLY_MIXED_PEER_AND_APPLE_GATES_PENDING",
    }
    receipt = {
        "protocol": "pinkha-unified-permission-native-source-composition-v1",
        "status": "PASS_SOURCE_COMPOSITION_ONLY",
        "originalManifestSHA256": BASE, "originalArchiveSHA256": OLD_ARCHIVE_SHA,
        "nativeSourceExportManifestSHA256": EXPORT_SHA, "actualOracleUnitReceiptSHA256": UNIT_SHA,
        "newManifestSHA256": manifest_sha, "newSourceFiles": len(contents), "archive": info,
        "changes": delta, "unchangedOriginalFiles": len(unchanged),
        "heartFilesUnchanged": 2692, "syncFilesUnchanged": 580, "workspaceFilesUnchanged": 2,
        "fullAnySDKGitTreesVerified": True, "compilations": 0, "testsExecuted": 0,
        "rootExportFilesystemModeEqualityClaimed": False,
        "rootExportModeDifferences": root_export_mode_differences,
        "applicationAcceptanceClaimed": False,
    }
    for path, data, public in [
        (HERE / "source-permission-manifest.json", manifest_bytes, True),
        (HERE / "source-permission-archive.json", encoded(info), True),
        (OUT / "source-manifest.json", manifest_bytes, False),
        (OUT / "composition.json", encoded(receipt), False),
        (DOCS / "composition.json", encoded(receipt), True),
    ]:
        put(path, data, public)
    print(json.dumps({"status": receipt["status"], "manifestSHA256": manifest_sha,
                      "sourceFiles": len(contents), "archive": info,
                      "receiptSHA256": sha(encoded(receipt))}, sort_keys=True))


if __name__ == "__main__":
    main()
