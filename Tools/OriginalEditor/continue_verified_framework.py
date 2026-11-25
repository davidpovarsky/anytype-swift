#!/usr/bin/env python3
"""Continue the unchanged native gates after an authenticated completed framework build.

The compiled SDK checkout remains frozen. This separately committed control
executes the exact post-build AST from that checkout's original driver; it never
substitutes a compiler result, filters a gate or changes the original failure.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

SOURCE = "e79192e5ad2b879ca4a45e46a3f6b504a1094155"
CONTROL_PATH = "Tools/OriginalEditor/continue_verified_framework.py"
ALLOWED_CONTROL_DELTA = {
    CONTROL_PATH,
    "docs/validation/20261125-miniapps-original-editor/VERIFIED_FRAMEWORK_CONTINUATION.md",
}

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("root", "prior-evidence", "prior-work", "evidence", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-commit", required=True)
    parser.add_argument("--incremental-budget-bytes", type=int, required=True)
    parser.add_argument("--concurrent-budget-bytes", type=int, required=True)
    args = parser.parse_args()
    root, prior, prior_work, evidence, work = map(
        lambda p: p.resolve(),
        (args.root, args.prior_evidence, args.prior_work, args.evidence, args.work))
    require(git(root, "rev-parse", "HEAD").decode().strip() == SOURCE,
            "The actual compiled source checkout must remain frozen")
    require(not git(root, "diff", "--name-only", "HEAD").strip(), "Tracked source changed")
    delta = set(git(root, "diff", "--name-only", SOURCE, args.control_commit).decode().splitlines())
    require(CONTROL_PATH in delta and delta <= ALLOWED_CONTROL_DELTA,
            "Continuation control changes a compiled input or unrelated gate")
    require(git(root, "show", args.control_commit + ":" + CONTROL_PATH) == Path(__file__).read_bytes(),
            "Continuation executable differs from its committed control")
    require(all(p.is_relative_to(root / "build") for p in (prior, prior_work, evidence, work))
            and len({prior, prior_work, evidence, work}) == 4
            and not evidence.exists() and not work.exists(),
            "Fresh disjoint owned continuation paths required")
    identity_path = prior / "local-execution.json"
    identity = json.loads(identity_path.read_bytes())
    require(identity["source_sha"] == SOURCE
            and Path(os.environ.get("OTZARIA_LOCAL_EXECUTION", "")) == identity_path
            and os.environ.get("OTZARIA_LOCAL_EXECUTION_SHA256") == sha(identity_path),
            "Use the genuine original local execution identity")
    driver_path = root / "Tools/OriginalEditor/run_framework_acceptance.py"
    require(sha(driver_path) == identity["runner_sha256"]
            and git(root, "show", SOURCE + ":Tools/OriginalEditor/run_framework_acceptance.py") == driver_path.read_bytes(),
            "Original acceptance driver changed")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(driver_path.parent))
    spec = importlib.util.spec_from_file_location("frozen_original_framework_driver", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    before = json.loads((prior / "source-before.json").read_bytes())
    require(before == json.loads((prior / "source-after.json").read_bytes())
            == driver.source_observation(root), "Original compiled source closure changed")
    original = json.loads((prior / "execution.json").read_bytes())
    require(original["source_sha"] == SOURCE and original["status"] == "FAIL"
            and original["phase"] == "ORIGINAL_FRAMEWORK_BUILD"
            and original["original_framework_build"] == "PASS"
            and original["external_consumer_build"] == "NOT_RUN"
            and original["strict_dependency_resolution"] == "PASS_EXACT_COMMITTED_LOCK_UNCHANGED"
            and "SourcePackages/checkouts/abseil-cpp-binary" in original.get("error", "")
            and "actual_source_closure" in original, "Unreviewed original failure boundary")
    record = json.loads((prior / "framework-build.command.json").read_bytes())
    require(record["returncode"] == 0 and not record["timed_out"]
            and record["cwd"] == str(root), "Original framework command did not pass")
    for stream in ("stdout", "stderr"):
        require(sha(prior / ("framework-build." + stream + ".log")) == record[stream + "_sha256"],
                "Original successful build output changed")
    require("** BUILD SUCCEEDED **" in (prior / "framework-build.stdout.log").read_text(),
            "Missing actual successful compiler result")
    derived = prior_work / "producer-derived"
    require(record["command"][record["command"].index("-derivedDataPath") + 1] == str(derived)
            and derived.is_dir() and not derived.is_symlink(), "Original build directory differs")
    processes = subprocess.check_output(["ps", "axo", "command"], text=True)
    require(not any(str(derived) in row and ("xcodebuild " in row or "swift-frontend " in row)
                    for row in processes.splitlines()), "Original compiler still owns products")
    repair_path = prior / "git-metadata-repair/RESULT.json"
    repair = json.loads(repair_path.read_bytes())
    require(repair["status"] == "ALL_56_CHECKOUT_HEADS_AND_TRACKED_DIFFS_VERIFIED"
            and len(repair["checkouts"]) == 56 and not repair["compiled_swift_source_changed"]
            and not repair["build_products_changed"] and not repair["donor_changed"],
            "Private Git metadata repair is not complete")
    capacity = {"free_bytes": shutil.disk_usage(root).free,
                "incremental_budget_bytes": args.incremental_budget_bytes,
                "concurrent_budget_bytes": args.concurrent_budget_bytes,
                "os_margin_bytes": 268435456}
    require(args.incremental_budget_bytes > 0 and args.concurrent_budget_bytes >= 0
            and capacity["free_bytes"] >
            args.incremental_budget_bytes + args.concurrent_budget_bytes + capacity["os_margin_bytes"],
            "Current remaining continuation phase does not fit")
    evidence.mkdir()
    work.mkdir()
    write(evidence / "phase-capacity-estimate.json", capacity)
    for name in ("framework-build.command.json", "framework-build.stdout.log", "framework-build.stderr.log",
                 "source-before.json", "source-after.json", "original-hanlin-snapshot.json", "import-abi-before.json"):
        shutil.copy2(prior / name, evidence / name)
    shutil.copy2(prior / "execution.json", evidence / "original-failed-execution.json")
    shutil.copy2(repair_path, evidence / "verified-git-metadata-repair.json")
    product_files = driver.inventory(derived / "Build/Products/Debug-Anytype-iphonesimulator")
    write(evidence / "retained-original-products.json", product_files)
    receipt = dict(original)
    receipt.pop("error", None)
    receipt.pop("error_type", None)
    receipt.pop("finished_at", None)
    receipt["continuation"] = {
        "control_commit": args.control_commit, "control_sha256": sha(Path(__file__)),
        "compiled_source_sha": SOURCE, "original_evidence": str(prior),
        "original_failed_execution_sha256": sha(prior / "execution.json"),
        "successful_build_command_sha256": sha(prior / "framework-build.command.json"),
        "original_product_inventory_sha256": sha(evidence / "retained-original-products.json"),
        "original_driver_sha256": sha(driver_path),
        "git_metadata_repair_sha256": sha(repair_path),
        "framework_build_reexecuted": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    write(evidence / "execution.json", receipt)
    preflight = None
    try:
        require(subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
                == "Xcode 27.0\nBuild version 27A266a", "Current Xcode differs")
        sys.path.insert(0, str(root / "Tools/PinkhaSimulatorGate"))
        from preflight import select_pairs
        state = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "--json"]))
        runtime, devices = select_pairs(state)
        pf = evidence / "preflight"
        pf.mkdir()
        write(pf / "simulator-inventory.json", state)
        name = "Pinkha-UI27-" + before["run_id"] + "-ipad"
        udid = subprocess.check_output(
            ["xcrun", "simctl", "create", name, devices["ipad"]["identifier"], runtime["identifier"]],
            text=True).strip()
        preflight = dict(original["preflight"])
        preflight.update(selected={"ipad": {"udid": udid, "device": devices["ipad"],
                                            "runtime": runtime, "name": name}},
                         status="PREFLIGHT_PASS_UI_NOT_RUN",
                         continuation_control_commit=args.control_commit,
                         started_at=receipt["continuation"]["started_at"],
                         finished_at=datetime.now(timezone.utc).isoformat())
        write(pf / "preflight.json", preflight)
        receipt["preflight"] = preflight
        receipt["continued_owned_preflight"] = preflight
        profile = driver.read_manifest()
        from import_abi_input import verify as verify_import_abi
        launch = json.loads((prior / "controller-launch.json").read_bytes())["arguments"]
        abi = Path(launch[launch.index("--import-abi-receipt") + 1])
        abi_sha = launch[launch.index("--import-abi-sha256") + 1]
        installation = verify_import_abi(root, abi, abi_sha, before)
        require(installation == json.loads((prior / "import-abi-before.json").read_bytes()),
                "Original ABI identity changed")
        sys.path.insert(0, str(root / "Tools/Hanlin"))
        from prepare_sdk import verify as verify_hanlin
        hanlin_before = verify_hanlin(root / "Dependencies/Hanlin")
        require(hanlin_before == json.loads((prior / "original-hanlin-snapshot.json").read_bytes()),
                "Original shared package input changed")
        tree = ast.parse(driver_path.read_text(), filename=str(driver_path))
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute"]
        require(len(functions) == 1, "Original gate function is ambiguous")
        body = functions[0].body
        markers = [i for i, node in enumerate(body)
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and ast.unparse(node.targets[0]) == "receipt['original_framework_build']"
                   and isinstance(node.value, ast.Constant) and node.value.value == "PASS"]
        require(len(markers) == 1, "Original successful framework boundary is ambiguous")
        remainder = body[markers[0] + 1:]
        require(remainder and ast.unparse(remainder[0]).startswith(
            "receipt['actual_source_closure'] = source_file_proof("),
            "Original full post-build gate sequence changed")
        suffix = ast.Module(body=remainder, type_ignores=[])
        suffix_hash = hashlib.sha256(ast.dump(suffix, include_attributes=False).encode()).hexdigest()
        receipt["continuation"]["original_postbuild_ast_sha256"] = suffix_hash
        write(evidence / "execution.json", receipt)
        context = dict(vars(driver))
        context.update(args=SimpleNamespace(import_abi_receipt=abi, import_abi_sha256=abi_sha),
                       root=root, evidence=evidence, work=work, receipt=receipt, before=before,
                       profile=profile, derived=derived, installation=installation,
                       hanlin_before=hanlin_before, verify_hanlin=verify_hanlin,
                       verify_import_abi=verify_import_abi, preflight=preflight, udid=udid,
                       destination="platform=iOS Simulator,id=" + udid)
        exec(compile(suffix, str(driver_path), "exec"), context, context)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        receipt["continuation"]["finished_at"] = datetime.now(timezone.utc).isoformat()
        if preflight is not None:
            cleanup = []
            for selected in preflight["selected"].values():
                row = {"udid": selected["udid"], "name": selected["name"]}
                for operation in ("shutdown", "delete"):
                    result = subprocess.run(["xcrun", "simctl", operation, selected["udid"]],
                                            capture_output=True, text=True)
                    row[operation] = {"returncode": result.returncode, "stderr": result.stderr}
                cleanup.append(row)
            write(evidence / "owned-simulator-cleanup.json", cleanup)
        require(driver.source_observation(root) == before,
                "Frozen original source changed during continuation")
        write(evidence / "source-after.json", driver.source_observation(root))
        write(evidence / "execution.json", receipt)
    print(json.dumps({k: receipt.get(k) for k in
                      ("status", "phase", "error", "source_sha", "original_framework_build",
                       "external_consumer_build", "actual_public_surface")}))
    return 0 if receipt["status"] == "ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
