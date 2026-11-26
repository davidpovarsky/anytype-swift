#!/usr/bin/env python3
"""Compose only the qualified immutable-record delta onto the original unified source."""
from __future__ import annotations
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

REPO = Path("/mnt/development/projects/worktrees/anytype-native-d-completion-20261125")
HERE = REPO / "Tools/PinkhaDualEngineRuntime"
OLD_MANIFEST = "410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9"
OLD_ARCHIVE = Path("/mnt/development/projects/evidence/native-d-final-20261125/native410b-inputs/native-source-410b441e5726.tar.gz")
OLD_ARCHIVE_SHA = "eba6a0354006c9cfc363c4769bd08951d3b4be4ef3fa8a65eb0cde9b6376e008"
DELTA_PATH = Path("/mnt/development/projects/evidence/migration-final-20261125/immutable-native/native-source-export-inventory/manifest.json")
DELTA_SHA = "4fc0cefbe9b80498a37f282eade66c6fa65441af929fb8c7117a2432ef9a166c"
C_PROOF = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125/docs/validation/20261125-native-immutable-record/actual-native-roundtrip/result.json")
C_PROOF_SHA = "ab3fff47239257d992ac9170a1ec89f521c76a28007286507951bcadce488cdb"
OUT = Path("/mnt/development/projects/evidence/native-d-final-20261125/native-immutable-20261126")
DOCS = REPO / "docs/validation/20261126-native-immutable-composition"

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(value):
    return hashlib.sha256(value).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()

def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())

def git(repo, *args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + str(repo), "-C", str(repo), *args], timeout=60)

def main():
    old_bytes = (HERE / "source-manifest.json").read_bytes()
    require(sha(old_bytes) == OLD_MANIFEST, "original_manifest_changed")
    old = json.loads(old_bytes)
    require(len(old["files"]) == 4855 and sha(OLD_ARCHIVE.read_bytes()) == OLD_ARCHIVE_SHA, "original_archive_changed")
    delta_bytes, proof_bytes = DELTA_PATH.read_bytes(), C_PROOF.read_bytes()
    require(sha(delta_bytes) == DELTA_SHA and sha(proof_bytes) == C_PROOF_SHA, "qualified_native_inputs_changed")
    delta, proof = json.loads(delta_bytes), json.loads(proof_bytes)
    require(proof["result"] == "PASS" and proof["sourceAdmissionPromoted"] is False and proof["wholeSpaceMigration"] is False, "scoped_original_native_pass_required")
    require([(row["phase"], row["result"], row["exitCode"]) for row in proof["phases"]] ==
            [("execute", "PASS", 0), ("reopen", "PASS", 0)], "both_original_native_phases_required")
    contents, modes = {}, {}
    with tarfile.open(OLD_ARCHIVE, "r:gz") as archive:
        for member in archive:
            name = member.name
            require(name not in contents and member.isfile() and not name.startswith("/") and
                    all(part not in ("", ".", "..") for part in name.split("/")), "closed_original_archive_required")
            contents[name] = archive.extractfile(member).read()
            modes[name] = member.mode & 0o777
    require(set(contents) == set(old["files"]) | {"source-manifest.json"}, "original_archive_inventory_changed")
    require(contents.pop("source-manifest.json") == old_bytes, "original_embedded_manifest_changed")
    modes.pop("source-manifest.json")
    for name, item in old["files"].items():
        require(len(contents[name]) == item["bytes"] and sha(contents[name]) == item["sha256"], "original_source_changed:" + name)

    new = copy.deepcopy(old)
    changes = []
    for key, prefix, expected_count in [("any", "any/", 4), ("sdk", "any/.runtime-artifacts/sdk-source/", 5)]:
        spec = delta[key]
        require(spec["before"] == old["sourcePins"][key] and len(spec["changedPaths"]) == expected_count, "qualified_delta_base_changed")
        repo = Path(spec["gitRepository"])
        require(git(repo, "rev-parse", spec["after"]).decode().strip() == spec["after"], "exact_native_git_commit_missing")
        actual = git(repo, "diff", "--name-status", spec["before"], spec["after"]).decode().splitlines()
        expected = [row["status"] + "\t" + row["path"] for row in spec["changedPaths"]]
        require(actual == expected, "native_delta_path_inventory_changed")
        for row in spec["changedPaths"]:
            name = prefix + row["path"]
            require(row["status"] in ("A", "M"), "unreviewed_delete_or_rename")
            if row["status"] == "A":
                require(name not in contents and "before" not in row, "new_native_path_already_exists")
            else:
                require(old["files"].get(name) == row["before"], "old_unified_blob_does_not_match_native_base")
            data = git(repo, "show", spec["after"] + ":" + row["path"])
            require({"bytes": len(data), "sha256": sha(data)} == row["after"], "new_native_blob_changed")
            contents[name] = data
            modes.setdefault(name, 0o644)
            new["files"][name] = row["after"]
            changes.append({"path": name, "status": row["status"], "before": row.get("before"), "after": row["after"]})
        new["sourcePins"][key] = spec["after"]

    require(len(contents) == 4862 and len(changes) == 9, "new_source_count_changed")
    # Whole native Any/SDK tree closure, not merely the nine changed blobs.
    for key, prefix in [("any", "any/"), ("sdk", "any/.runtime-artifacts/sdk-source/")]:
        spec = delta[key]
        repo = Path(spec["gitRepository"])
        tracked = git(repo, "ls-tree", "-r", "--name-only", spec["after"]).decode().splitlines()
        actual = {name[len(prefix):] for name in contents if name.startswith(prefix)
                  and not (key == "any" and name.startswith("any/.runtime-artifacts/sdk-source/"))}
        require(actual == set(tracked), "whole_native_git_tree_paths_changed:" + key)
        with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", spec["after"])), mode="r:") as archive:
            observed = set()
            for member in archive:
                if member.isdir():
                    continue
                require(member.isfile() and member.name in actual, "unexpected_native_git_member")
                name = prefix + member.name
                data = archive.extractfile(member).read()
                require(data == contents[name], "whole_native_git_tree_bytes_changed:" + name)
                observed.add(member.name)
            require(observed == actual, "whole_native_git_tree_incomplete")

    changed_names = {row["path"] for row in changes}
    unchanged = set(old["files"]) - changed_names
    require(all(new["files"][name] == old["files"][name] for name in unchanged), "unrelated_native_source_changed")
    require(sum(name.startswith("heart/") for name in contents) == 2692 and
            sum(name.startswith("sync/") for name in contents) == 580 and
            {name for name in contents if "/" not in name} == {"go.work", "go.work.sum"}, "heart_sync_workspace_closure_changed")
    new["predecessorSourceManifestSHA256"] = OLD_MANIFEST
    new["nativeImmutableRecords"] = {
        "anyCommit": delta["any"]["after"], "sdkCommit": delta["sdk"]["after"],
        "sourceDeltaManifestSHA256": DELTA_SHA,
        "qualifiedStandaloneSourceManifestSHA256": "39f4ee580af8f2897b2f794f872327b7391828a3a57355cf0235dae7d1626e72",
        "actualNativeRoundtripReceiptSHA256": C_PROOF_SHA,
        "actualNativePhases": ["execute", "reopen"],
        "actualPassedMethods": 2, "actualFailedMethods": 0, "actualSkippedMethods": 0,
        "actualPreparedOperations": 4, "actualLostReplyAndNewProcessOffline": True,
        "sharedSwiftVerifierCommit": "12cafb7b76849b3932b45345dc6538cce07d41bc",
        "qualificationScope": "STANDALONE_NATIVE_HTTP_AND_SHARED_SWIFT_NOT_COMBINED_APPLE",
        "combinedAppleQualified": False, "applicationAcceptanceClaimed": False,
        "wholeSpaceMigrationAccepted": False,
        "heartSyncAndWorkspaceBytesUnchanged": True,
        "changedPaths": sorted(changed_names),
    }
    manifest_bytes = encoded(new)
    manifest_sha = sha(manifest_bytes)
    OUT.mkdir(mode=0o700, parents=True, exist_ok=True)
    archive_path = OUT / ("native-source-" + manifest_sha[:12] + ".tar.gz")
    with archive_path.open("xb") as raw:
        os.chmod(archive_path, 0o600)
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name in sorted(contents):
                    data = contents[name]
                    member = tarfile.TarInfo(name)
                    member.size, member.mode, member.mtime = len(data), modes[name], 0
                    archive.addfile(member, io.BytesIO(data))
                member = tarfile.TarInfo("source-manifest.json")
                member.size, member.mode, member.mtime = len(manifest_bytes), 0o644, 0
                archive.addfile(member, io.BytesIO(manifest_bytes))
        raw.flush()
        os.fsync(raw.fileno())
    with tarfile.open(archive_path, "r:gz") as archive:
        inventory = {}
        for member in archive:
            require(member.isfile() and member.name not in inventory, "composed_archive_member_invalid")
            data = archive.extractfile(member).read()
            inventory[member.name] = {"bytes": len(data), "sha256": sha(data)}
    require(inventory.pop("source-manifest.json") == {"bytes": len(manifest_bytes), "sha256": manifest_sha}
            and inventory == new["files"], "composed_archive_exact_readback_failed")
    archive_info = {
        "archive": str(archive_path), "bytes": archive_path.stat().st_size, "sha256": sha(archive_path.read_bytes()),
        "manifestSHA256": manifest_sha, "sourceFiles": len(contents),
        "heartVersion": "pinkha-dual-runtime-v1-" + manifest_sha,
        "anyVersion": "v0.5.0-pinkha.dual.1-" + manifest_sha,
        "nativeDependencyArchive": "/mnt/development/projects/evidence/native-d-final-20261125/native410b-inputs/native-dependencies.tar.gz",
        "nativeDependencyArchiveSHA256": "a20d84bcffa31bab35909ad0555142ec5b1f54f07c1482fb023675ad81309159",
        "qualification": "ACTUAL_STANDALONE_IMMUTABLE_RECORD_WARM_AND_COLD_PASS_COMBINED_APPLE_PENDING",
    }
    receipt = {
        "protocol": "pinkha-unified-immutable-native-source-composition-v1", "result": "PASS_SOURCE_COMPOSITION_ONLY",
        "originalManifestSHA256": OLD_MANIFEST, "originalArchiveSHA256": OLD_ARCHIVE_SHA,
        "nativeChangedPathInventorySHA256": DELTA_SHA, "actualNativeRoundtripReceiptSHA256": C_PROOF_SHA,
        "newManifestSHA256": manifest_sha, "newSourceFileCount": len(contents),
        "newArchive": archive_info, "changes": changes,
        "unchangedOriginalFiles": len(unchanged), "heartFilesUnchanged": 2692, "syncFilesUnchanged": 580,
        "workspaceFilesUnchanged": 2, "fullAnySDKGitTreeVerified": True,
        "noCompilationOrTestsInvoked": True, "applicationAcceptanceClaimed": False,
    }
    put(HERE / "source-immutable-manifest.json", manifest_bytes)
    put(HERE / "source-immutable-archive.json", encoded(archive_info))
    put(OUT / "source-manifest.json", manifest_bytes)
    put(OUT / "composition.json", encoded(receipt))
    put(DOCS / "composition.json", encoded(receipt))
    put(DOCS / "native-source-export-manifest.json", delta_bytes)
    print(json.dumps({"result": receipt["result"], "manifest": manifest_sha, "sourceFiles": len(contents),
                      "archive": archive_info, "receiptSHA256": sha(encoded(receipt))}, sort_keys=True))

if __name__ == "__main__":
    main()
