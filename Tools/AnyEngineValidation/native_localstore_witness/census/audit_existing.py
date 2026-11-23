#!/usr/bin/env python3
"""Audit only the six original pairs. Never build, execute tests, chmod or rewrite originals."""
import collections
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

import audit_private as audit

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parent
NATIVE = Path("/mnt/development/projects/worktrees/anytype-heart-local-tree-census-20261123")
ORIGINAL = Path("/mnt/development/projects/evidence/local-tree-census-20261123/attempt1")
OUTPUT = ORIGINAL.parent / "audit-only-attempt1"
OLD_SOURCE = "5d6ec4b42db00ec01737ea150b4e288be9ab3743"
NATIVE_SOURCE = "35c169e7a39e3dafc0a1281f56a1fe37fce57533"
OLD_AUDITOR = "915973cfad4f0587a8ddd8fd8d975160a300e41592cb2205fd40bcf2eea2855c"
OLD_MANIFEST = "fdc88476018f7e32cdb6be9ceb03db47957b5cc6fd6430285992704fad77608c"
OLD_MODE = 'require(stat.S_IMODE(census.parent.stat().st_mode) == 0o700, "private_pair_directory_mode")'
NEW_MODE = 'require(stat.S_IMODE(census.parent.stat().st_mode) in {0o700, 0o2700}, "private_pair_directory_mode")'
PACKAGE = "github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
require = audit.require

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=30).decode().strip()

def blob(root, revision, name):
    return subprocess.check_output(["git", "-C", str(root), "show", revision + ":" + name], timeout=30)

def current_sources():
    require(not git(ROOT, "status", "--porcelain") and
            git(NATIVE, "rev-parse", "HEAD") == NATIVE_SOURCE and not git(NATIVE, "status", "--porcelain"),
            "audit_sources_must_be_frozen_and_clean")
    manifest = read(SOURCE / "source.json")
    require(manifest["native_source_sha"] == NATIVE_SOURCE and
            manifest["audit_followup"]["original_source_sha"] == OLD_SOURCE,
            "audit_source_origin_changed")
    require(Path(audit.__file__).resolve() == SOURCE / "audit_private.py", "audit_module_origin")
    files = {}
    for path in sorted(SOURCE.rglob("*")):
        require(not path.is_symlink(), "audit_source_link")
        if path.is_file():
            relative = path.relative_to(ROOT).as_posix()
            raw = blob(ROOT, "HEAD", relative)
            require(hashlib.sha256(raw).hexdigest() == sha(path), "audit_source_git_bytes")
            files[relative] = sha(path)
    require(sha(SOURCE / "audit_private.py") == manifest["private_auditor_sha256"] and
            sha(__file__) == manifest["audit_continuation_sha256"], "frozen_audit_source_changed")
    old = blob(ROOT, OLD_SOURCE, "Tools/AnyEngineValidation/native_localstore_witness/census/audit_private.py")
    require(hashlib.sha256(old).hexdigest() == OLD_AUDITOR, "original_auditor_git_identity")
    current = (SOURCE / "audit_private.py").read_text()
    require(current.count(NEW_MODE) == 1 and current.replace(NEW_MODE, OLD_MODE, 1).encode() == old,
            "only_exact_setgid_directory_admission_may_change")
    require(hashlib.sha256(blob(ROOT, OLD_SOURCE,
            "Tools/AnyEngineValidation/native_localstore_witness/census/source.json")).hexdigest() == OLD_MANIFEST,
            "original_manifest_git_identity")
    return {"source_sha": git(ROOT, "rev-parse", "HEAD"), "files": files,
            "loaded_auditor_sha256": sha(audit.__file__), "native_source_sha": NATIVE_SOURCE}

def original_artifacts(manifest):
    expected = manifest["audit_followup"]["original_artifacts"]
    observed = {}
    for name, row in expected.items():
        path = ORIGINAL / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == row["bytes"]
                and sha(path) == row["sha256"], "original_artifact_changed")
        observed[name] = dict(row)
    return observed

def original_native_passes():
    build, execution = read(ORIGINAL / "build.json"), read(ORIGINAL / "execute.json")
    require(build["status"] == "BUILD_PASS_EXECUTION_NOT_RUN" and
            execution["status"] == "FAILED" and execution["error"] ==
            {"message": "private_pair_directory_mode", "type": "RuntimeError"},
            "original_failure_must_remain_original")
    for value in (build, execution):
        require(value["controller_source_sha"] == OLD_SOURCE and value["native_source_sha"] == NATIVE_SOURCE and
                value["command"]["returncode"] == 0 and value["command"]["owned_process_group_absent"] is True and
                value["command"]["interruption"] is None, "original_native_command_not_qualified")
    binary = ORIGINAL / "products/local-tree-census.test"
    require(sha(binary) == build["binary_sha256"] ==
            "4721b54afc0052d28de4e20043287d0da245dbd92818f611ce82fac59d0bba2c", "original_binary_changed")
    events = [json.loads(line) for line in (ORIGINAL / "private/execution-original.jsonl").read_text().splitlines()]
    safe, streams = [], {}
    for event in events:
        require(event.get("Package") == PACKAGE, "original_wrong_package")
        safe.append({k: event[k] for k in ("Time", "Action", "Package", "Test", "Elapsed") if k in event})
        if "Output" in event:
            name = event.get("Test", "")
            streams[name] = streams.get(name, "") + event["Output"]
    require(safe == read(ORIGINAL / "safe-events.json"), "original_safe_event_projection")
    methods = set(audit.LABELS.values())
    starts = collections.Counter(v["Test"] for v in safe if v.get("Action") == "run" and "Test" in v)
    passes = collections.Counter(v["Test"] for v in safe if v.get("Action") == "pass" and "Test" in v)
    require(starts == passes == collections.Counter({name: 1 for name in methods}) and
            not any(v.get("Action") in ("fail", "skip") for v in safe), "original_exact_five_not_passed")
    receipts = {}
    for method, stream in streams.items():
        for line in stream.splitlines():
            if line.startswith("LOCAL_TREE_CENSUS_RECEIPT "):
                _, label, raw = line.split(" ", 2)
                require(label in audit.LABELS and audit.LABELS[label] == method and label not in receipts,
                        "original_receipt_label")
                receipts[label] = audit.safe_receipt(json.loads(raw))
    require(set(receipts) == set(audit.LABELS) and receipts == read(ORIGINAL / "safe-native-receipts.json"),
            "original_safe_receipt_projection")
    source = read(ORIGINAL / "build-source-before.json")
    for name in ("build-source-after.json", "build-source-final.json",
                 "execute-source-before.json", "execute-source-final.json"):
        require(read(ORIGINAL / name) == source, "original_source_snapshot_changed")
    require(sum(len(v) for v in source.values()) == 42, "original_source_input_count")
    for relative, expected in source["native"].items():
        require(sha(NATIVE / relative) == expected, "retained_native_source_changed")
    for relative, expected in source["controller"].items():
        require(hashlib.sha256(blob(ROOT, OLD_SOURCE, relative)).hexdigest() == expected,
                "original_controller_git_binding")
    for path, expected in source["native_schema_dependencies"].items():
        require(sha(path) == expected, "native_schema_source_changed")
    deps = read(ORIGINAL / "dependency-inputs-before.json")
    for name in ("dependency-inputs-after-build.json", "build-dependency-inputs-final.json",
                 "execute-dependency-inputs-final.json"):
        require(read(ORIGINAL / name) == deps, "original_dependency_snapshot_changed")
    require(len(deps) == 4045 and all(sha(path) == expected for path, expected in deps.items()),
            "retained_native_dependencies_changed")
    return receipts, {"original_execute_status": execution["status"],
        "retained_native_starts": sorted(starts), "retained_native_passes": sorted(passes),
        "new_native_methods_executed": 0, "new_builds": 0, "original_source_inputs": 42,
        "original_dependency_inputs": 4045, "binary_sha256": build["binary_sha256"]}

def pair_metadata():
    root = ORIGINAL / "private/fixtures"
    result = {}
    for label in audit.LABELS:
        matches = list(root.glob("*/" + label + ".census.bin"))
        require(len(matches) == 1, "original_private_pair_membership")
        census = matches[0]
        witness = census.with_name(label + ".witness.bin")
        record = {"files": {}, "ancestors": []}
        for kind, path in (("census", census), ("witness", witness)):
            item = path.lstat()
            require(stat.S_ISREG(item.st_mode) and stat.S_IMODE(item.st_mode) == 0o600 and
                    item.st_uid == os.geteuid(), "original_private_file_mode_owner")
            record["files"][kind] = {"sha256": sha(path), "bytes": item.st_size,
                                    "inode": item.st_ino, "device": item.st_dev,
                                    "mode": stat.S_IMODE(item.st_mode), "uid": item.st_uid, "gid": item.st_gid}
        for path in (census.parent, root, root.parent):
            item = path.lstat()
            require(stat.S_ISDIR(item.st_mode) and stat.S_IMODE(item.st_mode) in {0o700, 0o2700}
                    and item.st_uid == os.geteuid(), "original_private_ancestor_boundary")
            record["ancestors"].append({"inode": item.st_ino, "device": item.st_dev,
                "mode": stat.S_IMODE(item.st_mode), "uid": item.st_uid, "gid": item.st_gid})
        result[label] = record
    return result

def main():
    require(shutil.disk_usage("/mnt/development").free >= 2500000000, "audit_capacity_reserve")
    require(not OUTPUT.exists(), "fresh_audit_only_output_required")
    OUTPUT.mkdir()
    result = {"status": "FAIL_AUDIT_ONLY", "started_at": datetime.now(timezone.utc).isoformat(),
              "native_source_sha": NATIVE_SOURCE, "original_controller_source_sha": OLD_SOURCE,
              "new_builds": 0, "new_native_methods_executed": 0, "chmod_performed": False,
              "hasNativeSourceAdmission": False, "permitsDestinationWrites": False,
              "semanticIdentityCensusComplete": False}
    try:
        before = current_sources()
        save(OUTPUT / "source-before.json", before)
        manifest = read(SOURCE / "source.json")
        originals = original_artifacts(manifest)
        save(OUTPUT / "original-artifacts-before.json", originals)
        receipts, native = original_native_passes()
        metadata = pair_metadata()
        save(OUTPUT / "private-metadata-before.json", metadata)
        audited = audit.audit_private_pairs(ORIGINAL / "private/fixtures", receipts)
        save(OUTPUT / "private-pairs-audit.json", audited)
        after_metadata = pair_metadata()
        after = current_sources()
        save(OUTPUT / "private-metadata-after.json", after_metadata)
        save(OUTPUT / "source-after.json", after)
        require(metadata == after_metadata and before == after and
                original_artifacts(manifest) == originals, "audit_changed_source_or_originals")
        # Rehash the same declared native dependency bytes after the read-only audit.
        deps = read(ORIGINAL / "dependency-inputs-before.json")
        require(all(sha(path) == expected for path, expected in deps.items()), "post_audit_dependency_change")
        result.update(status="PASS_AUDIT_ONLY_RETAINED_NATIVE_FIVE", retained_native=native,
            original_execute_remains="FAILED", independently_audited_original_pairs=len(audited),
            current_audit_source_sha=before["source_sha"], sources_and_original_bytes_unchanged=True,
            private_modes_inodes_and_ownership_unchanged=True)
    except BaseException as error:
        result.update(error={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["free_bytes_final"] = shutil.disk_usage("/mnt/development").free
        save(OUTPUT / "receipt.json", result)
        print(json.dumps({"status": result["status"], "receipt_sha256": sha(OUTPUT / "receipt.json"),
                          "new_builds": 0, "new_native_methods_executed": 0}))

if __name__ == "__main__":
    main()
