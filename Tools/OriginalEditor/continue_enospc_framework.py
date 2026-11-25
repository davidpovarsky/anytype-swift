#!/usr/bin/env python3
"""Continue one authenticated ENOSPC build without changing compiled source or gates.

The producer remains at SOURCE. This separately committed controller runs the
original build expression or its complete post-build AST, with separate phase
admission and receipts. No partial object or historical qualification is a pass.
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
import platform
import shutil
import signal
import subprocess
import sys
from types import SimpleNamespace

SOURCE = "bc35bb619f530b98d7026b355c24c479dee704a8"
DRIVER_SHA256 = "51944452de1d5fa6ca6d6fc9a9f89097ab7c15445763d2b2d7251a198d21b8b4"
CONTROL = "Tools/OriginalEditor/continue_enospc_framework.py"
FAILURE_SHA256 = "01223a1a5bbd78fd42bc9a38431374388888078836683e67d2af754f7ddb82c2"
FAILURE_LOG_SHA256 = "83635b1f4117c305cb8ff08da1c4b9dc204d7aa2fb6172c6a56979819ded1bae"

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

def git(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments])

def subset(tree, start, stop):
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute").body
    selected = [n for n in body if start <= n.lineno and n.end_lineno <= stop]
    require(selected and selected[0].lineno == start and selected[-1].end_lineno == stop,
            "Frozen original driver phase boundary differs")
    return compile(ast.Module(body=selected, type_ignores=[]), "<frozen-original-driver>", "exec")

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("root", "prior-evidence", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-commit", required=True)
    parser.add_argument("--phase", choices=("build", "qualify"), required=True)
    parser.add_argument("--build-evidence", type=Path)
    parser.add_argument("--incremental-budget-bytes", type=int, required=True)
    parser.add_argument("--concurrent-budget-bytes", type=int, required=True)
    args = parser.parse_args()
    root, prior, work, evidence = [p.resolve() for p in
                                 (args.root, args.prior_evidence, args.work, args.evidence)]
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Native Apple silicon required")
    require(git(root, "rev-parse", "HEAD").decode().strip() == SOURCE
            and not git(root, "diff", "--name-only", "HEAD").strip(), "Frozen producer source changed")
    changed = set(git(root, "diff", "--name-only", SOURCE, args.control_commit).decode().splitlines())
    require(changed == {CONTROL}, "Recovery control changes compiled inputs or other gates")
    require(git(root, "show", args.control_commit + ":" + CONTROL) == Path(__file__).read_bytes(),
            "Recovery executable differs from its committed source")
    require(all(p.is_relative_to(root / "build") for p in (prior, work, evidence))
            and len({prior, work, evidence}) == 3 and not evidence.exists()
            and not prior.is_symlink() and not work.is_symlink(), "Fresh owned evidence required")
    require(sha(prior / "execution.json") == FAILURE_SHA256
            and sha(prior / "framework-build.stdout.log") == FAILURE_LOG_SHA256,
            "Original failed interval changed")
    original = json.loads((prior / "execution.json").read_bytes())
    require(original["status"] == "FAIL" and original["phase"] == "ORIGINAL_FRAMEWORK_BUILD"
            and original["source_sha"] == SOURCE and original["original_framework_build"] == "NOT_RUN"
            and original["external_consumer_build"] == "NOT_RUN" and "No space left on device" in original["error"]
            and original["strict_dependency_resolution"] == "PASS_EXACT_COMMITTED_LOCK_UNCHANGED",
            "Unreviewed failure boundary")
    descriptor = prior / "local-execution.json"
    require(os.environ.get("OTZARIA_LOCAL_EXECUTION") == str(descriptor)
            and os.environ.get("OTZARIA_LOCAL_EXECUTION_SHA256") == sha(descriptor)
            and not any(os.environ.get(k) for k in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")),
            "Use the actual original local execution identity")
    driver_path = root / "Tools/OriginalEditor/run_framework_acceptance.py"
    require(sha(driver_path) == DRIVER_SHA256
            and git(root, "show", SOURCE + ":Tools/OriginalEditor/run_framework_acceptance.py") == driver_path.read_bytes(),
            "Frozen original acceptance driver changed")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(driver_path.parent))
    spec = importlib.util.spec_from_file_location("frozen_framework_driver", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    before = json.loads((prior / "source-before.json").read_bytes())
    require(before == json.loads((prior / "source-after.json").read_bytes()) == driver.source_observation(root),
            "Source closure changed before recovery")
    derived = work / "producer-derived"
    require(derived.is_dir() and not derived.is_symlink(), "Original current-path compiler directory missing")
    processes = subprocess.check_output(["ps", "-axo", "pid,ppid,etime,command"], text=True)
    require(not any(str(derived) in line and any(x in line for x in
                    ("xcodebuild ", "swift-frontend ", "clang ")) for line in processes.splitlines()),
            "Owned compiler output still has an active writer")
    require(subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
            == original["preflight"]["xcode"], "Xcode toolchain changed")
    capacity = dict(free_bytes=shutil.disk_usage(root).free,
                    incremental_budget_bytes=args.incremental_budget_bytes,
                    concurrent_budget_bytes=args.concurrent_budget_bytes,
                    os_margin_bytes=536870912)
    require(args.incremental_budget_bytes > 0 and args.concurrent_budget_bytes >= 0
            and capacity["free_bytes"] > sum(capacity[k] for k in
                ("incremental_budget_bytes", "concurrent_budget_bytes", "os_margin_bytes")),
            "Current continuation phase does not fit")
    evidence.mkdir()
    write(evidence / "phase-capacity-estimate.json", capacity)
    (evidence / "processes-before.txt").write_text(processes)
    write(evidence / "source-before.json", before)
    receipt = {k: v for k, v in original.items() if k not in ("error", "error_type", "finished_at")}
    receipt.update(status="CONTINUATION_RUNNING", phase=args.phase.upper(),
                   continuation=dict(control_commit=args.control_commit, control_sha256=sha(__file__),
                        compiled_source_sha=SOURCE, original_failed_evidence=str(prior),
                        original_failed_execution_sha256=FAILURE_SHA256,
                        original_failed_stdout_sha256=FAILURE_LOG_SHA256,
                        original_driver_sha256=DRIVER_SHA256, same_derived_data=str(derived),
                        scheduler_jobs=2, started_at=datetime.now(timezone.utc).isoformat()))
    write(evidence / "execution.json", receipt)
    owned_udid = None
    def interrupt(signum, frame):
        raise InterruptedError("Owned continuation signal " + str(signum))
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    try:
        from import_abi_input import verify as verify_import_abi
        prepared = json.loads((prior / "PREPARED.json").read_bytes())
        args.import_abi_receipt = Path(prepared["abi"]["reference"])
        args.import_abi_sha256 = prepared["abi"]["reference_sha256"]
        installation = verify_import_abi(root, args.import_abi_receipt, args.import_abi_sha256, before)
        require(installation == json.loads((prior / "import-abi-before.json").read_bytes()), "Native ABI input changed")
        write(evidence / "import-abi-before.json", installation)
        sys.path.insert(0, str(root / "Tools/Hanlin"))
        from prepare_sdk import verify as verify_hanlin
        hanlin_before = verify_hanlin(root / "Dependencies/Hanlin")
        require(hanlin_before == json.loads((prior / "original-hanlin-snapshot.json").read_bytes()), "Shared source changed")
        write(evidence / "original-hanlin-snapshot.json", hanlin_before)
        tree = ast.parse(driver_path.read_text())
        profile = driver.read_manifest()
        if args.phase == "build":
            require(args.build_evidence is None and not (work / "distribution").exists(), "Build cannot reuse a qualified export")
            sys.path.insert(0, str(root / "Tools/PinkhaSimulatorGate"))
            from preflight import select_pairs
            state = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "--json"]))
            runtime, devices = select_pairs(state)
            selected = devices["ipad"]
            name = "Pinkha-UI27-" + before["run_id"] + "-ipad"
            owned_udid = subprocess.check_output(["xcrun", "simctl", "create", name, selected["identifier"],
                                                 runtime["identifier"]], text=True).strip()
            preflight = dict(original["preflight"])
            preflight.update(selected={"ipad": dict(udid=owned_udid, device=selected, runtime=runtime, name=name)},
                             continuation_control_commit=args.control_commit)
            write(evidence / "preflight/preflight.json", preflight)
            context = dict(driver.__dict__, root=root, evidence=evidence, work=work,
                           derived=derived, udid=owned_udid)
            exec(subset(tree, 347, 354), context)
            build = context["build"]
            # Scheduler-only override. All original compilation, signing,
            # resolution, architecture and graph flags remain exactly intact.
            build[2:2] = ["-jobs", "2"]
            write(evidence / "actual-build-invocation.json", {
                "command": build, "scheduler_only_change": ["-jobs", "2"],
                "original_semantic_flags": context["flags"],
                "original_derived_data": str(derived), "source_sha": SOURCE})
            driver.command(build, root, evidence, "framework-build", 6000)
            require("** BUILD SUCCEEDED **" in (evidence / "framework-build.stdout.log").read_text(),
                    "Actual compiler did not report success")
            receipt["original_framework_build"] = "PASS"
            receipt["preflight"] = preflight
            receipt["actual_source_closure"] = driver.source_file_proof(root, derived, before, evidence)
            receipt["dependencies"] = driver.dependency_proof(root, derived, profile, evidence)
            write(evidence / "products-after.json", driver.inventory(derived / "Build/Products/Debug-Anytype-iphonesimulator"))
            receipt.update(status="ACTUAL_INCREMENTAL_FRAMEWORK_BUILD_PASS_QUALIFICATION_NOT_RUN",
                           phase="FRAMEWORK_BUILD_COMPLETE")
        else:
            build_evidence = args.build_evidence.resolve(strict=True)
            require(build_evidence.is_relative_to(root / "build") and build_evidence not in (prior, work, evidence),
                    "Unowned build evidence")
            successful = json.loads((build_evidence / "execution.json").read_bytes())
            require(successful["status"] == "ACTUAL_INCREMENTAL_FRAMEWORK_BUILD_PASS_QUALIFICATION_NOT_RUN"
                    and successful["source_sha"] == SOURCE and successful["original_framework_build"] == "PASS"
                    and successful["continuation"]["control_commit"] == args.control_commit
                    and successful["continuation"]["same_derived_data"] == str(derived),
                    "No successful current-source framework build")
            require(before == json.loads((build_evidence / "source-before.json").read_bytes())
                    == json.loads((build_evidence / "source-after.json").read_bytes()), "Build source changed")
            command_receipt = json.loads((build_evidence / "framework-build.command.json").read_bytes())
            require(command_receipt["returncode"] == 0 and not command_receipt["timed_out"]
                    and command_receipt["cwd"] == str(root), "Native build command failed")
            for stream in ("stdout", "stderr"):
                name = "framework-build." + stream + ".log"
                require(sha(build_evidence / name) == command_receipt[stream + "_sha256"], "Native build log changed")
                shutil.copy2(build_evidence / name, evidence / name)
            shutil.copy2(build_evidence / "framework-build.command.json", evidence / "framework-build.command.json")
            require(driver.inventory(derived / "Build/Products/Debug-Anytype-iphonesimulator")
                    == json.loads((build_evidence / "products-after.json").read_bytes()), "Completed products changed")
            preflight = successful["preflight"]
            owned_udid = preflight["selected"]["ipad"]["udid"]
            write(evidence / "preflight/preflight.json", preflight)
            receipt.update(preflight=preflight, original_framework_build="PASS",
                           successful_build_evidence=str(build_evidence),
                           successful_build_execution_sha256=sha(build_evidence / "execution.json"))
            context = dict(driver.__dict__, args=args, root=root, evidence=evidence, work=work, before=before,
                           receipt=receipt, derived=derived, profile=profile, preflight=preflight,
                           udid=owned_udid, destination="platform=iOS Simulator,id=" + owned_udid,
                           installation=installation, verify_import_abi=verify_import_abi,
                           hanlin_before=hanlin_before, verify_hanlin=verify_hanlin)
            # Every original post-build source, dependency, binary, graph,
            # ownership, resource and actual external-consumer gate runs.
            exec(subset(tree, 370, 638), context)
        require(driver.source_observation(root) == before, "Current source closure changed")
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        try:
            after = driver.source_observation(root)
            write(evidence / "source-after.json", after)
            require(after == before, "Source closure changed at final observation")
        except BaseException as error:
            receipt.update(status="FAIL", source_after_error=str(error))
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        receipt["free_after"] = shutil.disk_usage(root).free
        write(evidence / "execution.json", receipt)
        if receipt.get("distribution"):
            write(Path(receipt["distribution"]) / "QUALIFICATION.json", receipt)
        # Preserve the owned simulator for the separately admitted consumer
        # phase and its diagnostics. No simulator or compiler cache is deleted.
        if owned_udid and args.phase == "qualify":
            result = subprocess.run(["xcrun", "simctl", "shutdown", owned_udid], capture_output=True, text=True)
            write(evidence / "owned-simulator-shutdown.json", dict(udid=owned_udid,
                  returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, deleted=False))
    print(json.dumps({k: receipt.get(k) for k in ("status", "phase", "error", "source_sha", "free_after")}))
    return 0 if receipt["status"] in ("ACTUAL_INCREMENTAL_FRAMEWORK_BUILD_PASS_QUALIFICATION_NOT_RUN",
        "ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS") else 1

if __name__ == "__main__":
    raise SystemExit(main())
