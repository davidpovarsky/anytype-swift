"""Resume only the observed failed own-cache interval after three reviewed source fixes.

The historical 9225 complete product archive and af229 exit-65 remain evidence.
Every current build, native source gate, entitlement gate and app test runs anew.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import local_cache_input as completed
from local_execution import PRIVATE_ROOT, digest, write, require

APP, DERIVED = completed.APP, completed.DERIVED
FAILED_SOURCE = "af229032a76b908ad24f063c37f6a2e1fdd8eca3"
REVIEWED_SOURCE = "001ed8aa7940d90b8da77e9f96745aab38420d45"
FAILED = PRIVATE_ROOT / "evidence/acceptance-af229032-01"
FAILED_RECEIPTS = {
    "local-execution.json": "5d44010ec464198bd4ee8b2442334d6bd16c43cf4eb979b3391de5e39731b22d",
    "local-execution-result.json": "d5d2717ff839095d38403ca4cf729aa8e02b07a58b5db2e9f51cae3a59522f11",
    "miniapps-build.json": "5f6042152c29235af7ec91dd92aa286b2987caa490b4f3b8c5ba65ceae38cf8d",
    "build-native.command.json": "14e394827cf0e3433bed783402f7397a732c7f6ad35738d5e9ca940d3ab59d61",
    "resolve-native-packages.command.json": "56a232a8479b349087054be48a3755831063541170d62f3843b56bb3af2be1ca",
    "owned-compiler-cache-admission.json": "c4ac99f610fea56b7058e6554af6f75754389f40e6bb69ad0425df1b2a889e16",
}
REVIEWED_CHANGES = {
    "Anytype.xcodeproj/project.pbxproj": (
        "100644 blob de4ddd63e1792e3c3628c8cb7060fbafe4f6bbee",
        "100644 blob 2b2383eadfc4f8d51c607fad3b93b907271b9c41"),
    "Anytype/Sources/PresentationLayer/Common/UIKit/TextView/Views/TextViewWithPlaceholder.swift": (
        "100644 blob d3ae3d24743f81821b2bb9f47c463e92f733ce32",
        "100644 blob 62aaf86510a3543eaac438aa6d647ec7e7dc25c6"),
    "Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController.swift": (
        "100644 blob 2c7bbb3473a02a63cef2f7be725ca19e6fd39577",
        "100644 blob 613d5df610f4e5fc10ba8dbb3378cebb1417e172"),
}
CONTROL_ONLY_PATHS = completed.CONTROL_ONLY_PATHS | {
    "Tools/MiniApps/local_failed_cache_input.py",
    "Tools/MiniApps/test_local_failed_cache_input.py",
    "Tools/MiniApps/producer-preparation-86a6dde3.json",
    "docs/miniapps-cross-app/evidence/20261125-native-core-link/APPLE_PROJECT_GRAPH.json",
    "docs/miniapps-cross-app/evidence/20261125-native-core-link/PROJECT_REVIEW.json",
    "docs/miniapps-cross-app/evidence/20261125-failed-cache-continuation/CONTRACT.json",
}


def source_tree(app, revision):
    raw = subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(app),
                                   "ls-tree", "-rz", revision])
    result = {}
    for row in raw.split(b"\0"):
        if row:
            meta, name = row.split(b"\t", 1)
            name = name.decode()
            if name not in CONTROL_ONLY_PATHS:
                result[name] = meta.decode()
    require(result, "Empty original compiler source tree")
    return result


def check_source_contract(before, reviewed, current):
    changes = {name: (before.get(name), reviewed.get(name))
               for name in before.keys() | reviewed.keys()
               if before.get(name) != reviewed.get(name)}
    require(changes == REVIEWED_CHANGES,
            "Reviewed repair is not exactly the three original project/edit-menu files")
    require(current == reviewed,
            "Current app, tests, capabilities, resource or dependency source differs from the reviewed repair")
    return current


def require_group_absent(group):
    require(isinstance(group, int) and group > 1, "Invalid original owned process group")
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return
    raise RuntimeError("An original owned process group is still present; no cache snapshot admitted")


def validate_failure(descriptor, terminal, build, command):
    require(descriptor["source_sha"] == FAILED_SOURCE
            and descriptor["source_root"] == str(APP)
            and descriptor["derived"] == str(DERIVED)
            and descriptor["configuration"] == "Debug-MiniAppsOwner"
            and descriptor["execution_origin"] == "local-mac"
            and descriptor["github_run_id"] is None,
            "Failed cache belongs to another source, owner, configuration or execution")
    require(terminal["status"] == "FAIL" and terminal["actual_test_methods"] == 0
            and terminal["error"] == "build-native returned 65; see the original log"
            and terminal["source_sha"] == build["source_sha"] == FAILED_SOURCE
            and terminal["run_id"] == build["run_id"] == descriptor["run_id"]
            and terminal["local_execution_sha256"] == FAILED_RECEIPTS["local-execution.json"]
            and build["status"] == "BUILDING" and build["phase"] == "build-native-finished",
            "The original failed build or its zero-test status was relabelled")
    require(command["returncode"] == 65 and command["timed_out"] is False
            and command["owned_group_drained"] is True
            and command["cwd"] == str(APP)
            and command["arguments"] == build["completed_build_commands"]["build-native"]["arguments"]
            and command["log_sha256"] == build["completed_build_commands"]["build-native"]["log_sha256"],
            "The original failed command, complete log or owned-group drain differs")


def previous_failure():
    completed.previous_build()  # Retain the complete immutable 9225 products and proof.
    rows = {name: completed.exact_json(FAILED / name, sha)
            for name, sha in FAILED_RECEIPTS.items()}
    descriptor, terminal, build, command = [rows[name] for name in (
        "local-execution.json", "local-execution-result.json",
        "miniapps-build.json", "build-native.command.json")]
    validate_failure(descriptor, terminal, build, command)
    for name, expected_exit in (("resolve-native-packages", 0), ("build-native", 65)):
        row = rows[name + ".command.json"]
        require(row["returncode"] == expected_exit and row["timed_out"] is False
                and row["owned_group_drained"] is True and row["cwd"] == str(APP)
                and digest(FAILED / (name + ".log")) == row["log_sha256"]
                and row["arguments"] == build["completed_build_commands"][name]["arguments"],
                "Original failed interval resolver/build proof changed: " + name)
        require_group_absent(row["process_group_id"])
    admission = rows["owned-compiler-cache-admission.json"]
    require(admission["status"] == "ADMITTED_SAME_PATH_SOURCE_IDENTICAL_OWNED_COMPILER_CACHE"
            and admission["current_source_sha"] == FAILED_SOURCE
            and admission["prior_source_sha"] == completed.SOURCE
            and admission["old_products_remain_in_immutable_archive"] == completed.ARCHIVE_SHA256,
            "The failed interval did not use the proven original owned cache")
    return descriptor, admission


def shared_file_digest(shared):
    return hashlib.sha256(json.dumps(
        shared["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def seal(app, derived, output):
    require(app == APP and derived == DERIVED and app.resolve() == app
            and derived.resolve() == derived and not output.exists()
            and output.is_relative_to(PRIVATE_ROOT / "evidence") and output.resolve() == output,
            "Only the existing owned cache may be sealed into fresh evidence")
    require(completed.git(app, "rev-parse", "HEAD") == FAILED_SOURCE
            and not completed.git(app, "diff", "--name-only", "HEAD"),
            "Seal must precede the reviewed source update")
    descriptor, admission = previous_failure()
    shared = completed.qualified_hanlin(app)
    require(shared_file_digest(shared) == admission["complete_hanlin_file_set_sha256"],
            "Shared source changed during the failed compiler interval")
    before = source_tree(app, FAILED_SOURCE)
    value = dict(schema="miniapps.failed-owned-compiler-cache/1",
        status="SEALED_ACTUAL_FAILED_INTERVAL_NOT_BUILD_OR_ACCEPTANCE",
        source_sha=FAILED_SOURCE, source_root=str(app), derived=str(derived),
        prior_run_id=descriptor["run_id"], prior_receipts=FAILED_RECEIPTS,
        previous_complete_archive_sha256=completed.ARCHIVE_SHA256,
        reviewed_source_sha=REVIEWED_SOURCE, reviewed_changes=REVIEWED_CHANGES,
        compiler_source_tree=before, hanlin_snapshot=shared,
        cache=completed.cache_inventory(derived), native_or_ui_credit=0)
    previous_failure()
    require(completed.git(app, "rev-parse", "HEAD") == FAILED_SOURCE
            and not completed.git(app, "diff", "--name-only", "HEAD"),
            "Original source changed during the failed-cache observation")
    write(output, value)
    return dict(path=str(output), sha256=digest(output),
                cache_members=len(value["cache"]), source_members=len(before),
                status=value["status"], native_or_ui_credit=0)


def admit(app, derived, evidence, snapshot, expected_sha256):
    require(app == APP and derived == DERIVED and app.resolve() == app
            and derived.resolve() == derived and snapshot is not None and expected_sha256,
            "Failed-cache continuation requires the exact owned paths and snapshot")
    path = Path(snapshot)
    require(path.resolve() == path and path.is_relative_to(PRIVATE_ROOT / "evidence"),
            "Failed-cache snapshot is unowned or aliased")
    value = completed.exact_json(path, expected_sha256)
    descriptor, admission = previous_failure()
    require(value.get("schema") == "miniapps.failed-owned-compiler-cache/1"
            and value.get("status") == "SEALED_ACTUAL_FAILED_INTERVAL_NOT_BUILD_OR_ACCEPTANCE"
            and value.get("source_sha") == FAILED_SOURCE and value.get("source_root") == str(app)
            and value.get("derived") == str(derived) and value.get("prior_run_id") == descriptor["run_id"]
            and value.get("prior_receipts") == FAILED_RECEIPTS
            and value.get("previous_complete_archive_sha256") == completed.ARCHIVE_SHA256
            and value.get("reviewed_source_sha") == REVIEWED_SOURCE
            and value.get("reviewed_changes") == {k: list(v) for k, v in REVIEWED_CHANGES.items()}
            and value.get("native_or_ui_credit") == 0,
            "Unknown, foreign or relabelled failed-cache observation")
    require(subprocess.run(["git", "-c", "gc.auto=0", "-C", str(app),
                            "merge-base", "--is-ancestor", REVIEWED_SOURCE, "HEAD"]).returncode == 0,
            "Current source does not contain the reviewed original repair")
    before = source_tree(app, FAILED_SOURCE)
    current = check_source_contract(before, source_tree(app, REVIEWED_SOURCE), source_tree(app, "HEAD"))
    require(before == value["compiler_source_tree"],
            "The failed interval source tree changed")
    shared = completed.qualified_hanlin(app)
    require(shared["files"] == value["hanlin_snapshot"]["files"]
            and shared_file_digest(shared) == admission["complete_hanlin_file_set_sha256"],
            "The shared source/ABI closure changed; this narrow continuation cannot admit it")
    require(completed.cache_inventory(derived) == value["cache"],
            "Owned compiler/module/product bytes changed after the failed-cache snapshot")
    result = dict(status="ADMITTED_FAILED_OWN_CACHE_FOR_ACTUAL_REBUILD_ONLY",
        snapshot_path=str(path), snapshot_sha256=expected_sha256,
        prior_failed_source_sha=FAILED_SOURCE, current_source_sha=completed.git(app, "rev-parse", "HEAD"),
        prior_run_id=descriptor["run_id"], reviewed_source_sha=REVIEWED_SOURCE,
        reviewed_production_changes=REVIEWED_CHANGES,
        module_cache=str(derived / "MiniAppsCurrentModuleCache.noindex"),
        source_members=len(current), cache_members=len(value["cache"]),
        prior_hanlin_source_sha=value["hanlin_snapshot"]["revision"],
        current_hanlin_source_sha=shared["revision"],
        complete_hanlin_file_set_sha256=shared_file_digest(shared),
        old_products_remain_in_immutable_archive=completed.ARCHIVE_SHA256,
        new_native_or_ui_credit=0, both_actual_compiler_commands_and_postgates_required=True)
    write(evidence / "failed-owned-compiler-cache-admission.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--seal", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(seal(APP, DERIVED, args.seal)))
