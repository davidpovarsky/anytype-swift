#!/usr/bin/env python3
"""Execute the corrected original import/reentry case and reuse the authentic prior prestart PASS."""
import argparse
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
import time

PACKET = "docs/pinkha/torah-integration/native-heart-lifetime-repair-20261123"
BASE_PACKET = "docs/pinkha/torah-integration/native-heart-rpc-runtime-20261123"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
SUPPORT_SHA256 = "017778c096eca985774bd1a4f1e1e117ac3dee6ac08082c2a9793273826aa196"

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)

def safe(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe retained path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "Aliased retained path")
    return path

def read_sources(control, manifest, destination=None):
    inventory = []
    destinations = set()
    for entry in manifest["source_inputs"]:
        require(entry["destination"] not in destinations, "Duplicate materialized source")
        destinations.add(entry["destination"])
        retained = BASE_PACKET + "/retained-inputs/" + entry["destination"]
        raw = safe(control, retained).read_bytes()
        require(raw == git(control, "show", "HEAD:" + retained), "Dirty retained original source input")
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
                and blob == entry["git_blob"], "Immutable source input differs")
        if destination:
            target = safe(destination, entry["destination"])
            require(not target.exists(), "Preserve a pre-existing source output")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        inventory.append({k: entry[k] for k in ("revision", "source_path", "destination", "bytes", "sha256", "git_blob")})
    return inventory

def control_inputs(control, packet, manifest):
    raw = (packet / "EXECUTION_INPUTS.json").read_bytes()
    require(raw == git(control, "show", "HEAD:" + PACKET + "/EXECUTION_INPUTS.json"), "Dirty native execution contract")
    require(manifest["heart_base"] == HEART and manifest["historical_controls_replayed"] is False,
            "Unexpected original native scope")
    result = []
    for entry in manifest["control_inputs"]:
        path = safe(packet, entry["path"])
        data = path.read_bytes()
        require(sha(data) == entry["sha256"] and len(data) == entry["bytes"], "Native control input changed")
        require(data == git(control, "show", "HEAD:" + PACKET + "/" + entry["path"]), "Dirty native control input")
        result.append(entry)
    return result

def materialize_and_load_support(control, packet, manifest, work):
    inputs = work / "inputs"
    inputs.mkdir()
    inventory = read_sources(control, manifest, inputs)
    source = inputs / "support/run_original_application_compile.py"
    require(sha(source.read_bytes()) == SUPPORT_SHA256, "Original bounded process owner differs")
    spec = importlib.util.spec_from_file_location("original_native_process_owner", source)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    return support, inputs, inventory

def verify_reused_prestart(control, packet, manifest):
    # This authored helper is hashed and Git-bound by control_inputs first.
    path = packet / "verify_reused_prestart.py"
    namespace = {}
    exec(compile(path.read_bytes(), str(path), "exec"), namespace)
    return namespace["verify"](control, packet, manifest)

def install_native(support, commands, inputs, heart, packet, manifest, evidence):
    require(git(heart, "rev-parse", "HEAD").decode().strip() == HEART, "Original Heart checkout differs")
    require(not git(heart, "status", "--porcelain", "--untracked-files=all").strip(), "Original Heart checkout is not fresh")
    for name, digest in manifest["original_module_hashes"].items():
        require(support.digest(heart / name) == digest, "Original module/native checksum differs")
    original = json.loads((inputs / "support/ORIGINAL_COMPILE_INPUTS.json").read_bytes())
    require(original["final_product_hashes"] == manifest["baseline_product_hashes"],
            "The previously compiled 28-file lifetime closure changed")
    patch = inputs / "r14/native-heart-integration.patch"
    inventory = json.loads((inputs / "r14/native-heart-integration.json").read_bytes())
    require(inventory["heart_sha"] == HEART and inventory["patch_sha256"] == support.digest(patch), "Original r14 binding differs")
    commands.require("r14-check", ["git", "apply", "--check", str(patch)], heart, 30)
    commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
    for entry in inventory["files"]:
        require(support.digest(heart / entry["path"]) == entry["after_sha256"], "r14 afterimage differs")
    for role, program in (("origin", "install_native_sources.py"), ("owned", "install_owned_sources.py")):
        commands.require("install-" + role, [
            sys.executable, "-I", str(inputs / role / program),
            "--source-root", str(heart), "--receipt", str(evidence / (role.upper() + "_OVERLAY.json")),
        ], heart, 30)
    commands.require("install-lifetime", [
        sys.executable, "-I", str(inputs / "lifetime/install_lifetime_sources.py"),
        "--root", str(heart), "--packet", str(inputs / "lifetime"),
        "--output", str(evidence / "LIFETIME_OVERLAY.json"),
    ], heart, 30)
    required = dict(manifest["baseline_product_hashes"])
    for name, digest in required.items():
        require(support.digest(heart / name) == digest, "Previously compiled product source changed: " + name)
    repairs = []
    for repair in manifest["product_repairs"]:
        name = repair["native_path"]
        require(name in required and required[name] == repair["before_sha256"],
                "Correction is not based on the actual previously compiled source")
        target = safe(heart, name)
        require(support.digest(target) == repair["before_sha256"], "Original correction beforeimage differs")
        data = safe(packet, repair["path"]).read_bytes()
        require(sha(data) == repair["after_sha256"], "Reviewed correction afterimage differs")
        target.write_bytes(data)
        required[name] = support.digest(target)
        repairs.append({"path": name, "before_sha256": repair["before_sha256"],
                        "after_sha256": required[name], "scope": "No-progress mapping observation only"})
    require(len(repairs) == 1 and repairs[0]["path"] == "core/block/import/mapping_observation.go",
            "Unexpected product correction scope")
    require(support.digest(heart / "core/block/process/noop.go") == manifest["original_noop_sha256"],
            "Original no-progress implementation changed")
    support.write_json(evidence / "MAPPING_NO_PROGRESS_CORRECTION.json", {
        "product_repairs": repairs, "whole_product_tree_unchanged": False,
        "original_noop_unchanged": True, "synthetic_process_id_created": False,
    })
    name = manifest["test_file"].removeprefix("native/")
    target = safe(heart, name)
    require(not target.exists(), "Native test path already exists")
    target.write_bytes((packet / manifest["test_file"]).read_bytes())
    required[name] = support.digest(target)
    composed = {entry["path"]: entry["after_sha256"] for entry in inventory["files"]}
    composed.update(required)
    status = git(heart, "status", "--porcelain", "--untracked-files=all").decode().splitlines()
    require(all(row[:2] in (" M", "??") and row[3:] in composed for row in status), "Unexpected native source mutation")
    for name, digest in composed.items():
        require(support.digest(heart / name) == digest, "Composed original source differs")
    return required, composed

def verify_native_results(path, expected):
    events = []
    for line in path.read_text().splitlines():
        events.append(json.loads(line))
    runs, passes, failures, skips = {}, {}, [], []
    for event in events:
        name, action = event.get("Test"), event.get("Action")
        if name and action == "run":
            runs[name] = runs.get(name, 0) + 1
        if name and action == "pass":
            passes[name] = passes.get(name, 0) + 1
        if action == "fail":
            failures.append(name or "<package>")
        if action == "skip":
            skips.append(name or "<package>")
    selected = set(expected) | {"TestOtzariaOwnedImportNativeLifetime"}
    require(set(runs) == selected and all(n == 1 for n in runs.values()), "Unexpected/missing/replayed native case")
    require(set(passes) == selected and all(n == 1 for n in passes.values()) and not failures and not skips,
            "Actual native cases did not all pass once")
    require(any(e.get("Action") == "pass" and not e.get("Test") for e in events), "Native package completion absent")
    return {"leaf_cases": sorted(expected), "leaf_pass": len(expected), "fail": 0, "skip": 0,
            "original_prior_cases_replayed": 0, "json_events": len(events)}

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--heart", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    control = args.control_root.resolve()
    packet = control / PACKET
    manifest_raw = (packet / "EXECUTION_INPUTS.json").read_bytes()
    require(sha(manifest_raw) == args.execution_manifest_sha256, "Workflow manifest binding differs")
    manifest = json.loads(manifest_raw)
    require(git(control, "rev-parse", "HEAD").decode().strip() == args.control_head, "Workflow source differs")
    controls = control_inputs(control, packet, manifest)
    reused_prestart = verify_reused_prestart(control, packet, manifest)
    if args.source_only:
        rows = read_sources(control, manifest)
        print(json.dumps({"status": "SOURCE_ONLY_PASS", "checkout_sha": args.control_head,
                          "immutable_source_rows": len(rows), "controls": controls,
                          "reused_prestart": reused_prestart,
                          "native_execution": False, "provider_called": False}, indent=2))
        return 0
    heart, work, evidence = (p.resolve() for p in (args.heart, args.work, args.evidence))
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Darwin ARM64 native route required")
    require(not work.exists() and not evidence.exists(), "Fresh owned native work/evidence paths required")
    for path in (heart, work, evidence):
        require(path.is_relative_to(control) and path != control, "Execution path escapes owned checkout")
    roots = (packet, heart, work, evidence)
    require(not any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
                    for i, a in enumerate(roots) for b in roots[i+1:]), "Execution roots overlap")
    require(time.time() < args.job_deadline_unix <= time.time() + 7100, "Invalid native execution deadline")
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    support, inputs, source_rows = materialize_and_load_support(control, packet, manifest, work)
    temporary = work / "native-temporary"
    temporary.mkdir()
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(TMPDIR=str(temporary), CGO_ENABLED="1", GOMAXPROCS="2",
               GOTOOLCHAIN="local", GOWORK="off", GOENV="off", GOFLAGS="-mod=readonly",
               OTZARIA_NATIVE_RUNTIME_EVIDENCE=str(evidence))
    commands = support.Commands(evidence, env, args.job_deadline_unix - 180)
    result = {"status": "STARTED_NOT_ACCEPTED", "control_head": args.control_head,
              "heart_base": HEART, "execution_manifest_sha256": sha(manifest_raw),
              "historical_controls_replayed": False, "native_result": "NOT_RUN",
              "scope": manifest["scope"], "source_inputs": source_rows, "control_inputs": controls,
              "product_repairs": manifest["product_repairs"], "reused_prestart": reused_prestart}
    support.write_json(evidence / "RESULT.json", result)
    support.write_json(evidence / "REUSED_PRESTART_PROOF.json", reused_prestart)
    success = False
    try:
        required, composed = install_native(support, commands, inputs, heart, packet, manifest, evidence)
        go = shutil.which("go")
        require(go, "Native Go toolchain absent")
        go = str(Path(go).resolve())
        version = commands.require("go-version", [go, "version"], heart, 30).read_text().strip()
        require(version == "go version go1.26.5 darwin/arm64", "Original Go toolchain differs")
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], heart, 30).read_text()
        require(xcode.startswith("Xcode 27"), "Original Apple compiler route differs")
        commands.require("clang-version", ["xcrun", "--sdk", "macosx", "clang", "--version"], heart, 30)
        result["go"] = {"version": version, "path": go, "sha256": support.digest(go)}
        formatting = commands.require("native-source-format", [
            str(Path(go).with_name("gofmt")), "-l", *[str(heart / name) for name in required]
        ], heart, 30)
        require(not formatting.read_text().strip(), "Native input differs from exact gofmt; no automatic rewrite")
        commands.require("original-tantivy", [
            sys.executable, "-I", str(inputs / "support/bootstrap/prepare_original_tantivy.py"),
            "--heart", str(heart), "--helper", str(inputs / "support/bootstrap/build_custom_heart.py"),
            "--helper-sha256", "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
            "--receipt", str(evidence / "TANTIVY_SETUP.json"),
        ], heart, 600)
        native = support.native_library_inputs(heart)
        require(native == manifest["expected_tantivy_inputs"], "Original native Tantivy bytes differ")
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        listing = commands.require("declared-native-inputs", [go, "list", "-deps", "-test", "-json", "./core/application"], heart, 1200)
        coverage = [{"path": name, "sha256": digest} for name, digest in sorted(required.items())]
        closure = support.dependency_inputs(listing, heart, coverage)
        support.write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        require(len(closure["required_product_test_coverage"]) == 29, "Native compiled source closure is incomplete")
        binary = work / "original-application-native.test"
        commands.require("compile-new-native-cases", [go, "test", "-c", "-p", "2", "-o", str(binary), "./core/application"], heart, 3600)
        require(binary.is_file() and binary.stat().st_size > 0, "Native compiler produced no test executable")
        result["native_binary"] = {"sha256": support.digest(binary), "bytes": binary.stat().st_size}
        commands.require("native-binary-buildinfo", [go, "version", "-m", str(binary)], heart, 30)
        result["native_result"] = "EXECUTION_REQUESTED"
        support.write_json(evidence / "RESULT.json", result)
        output = commands.require("execute-new-native-cases", [
            go, "tool", "test2json", "-t", "-p", "github.com/anyproto/anytype-heart/core/application",
            str(binary), "-test.v=test2json", "-test.run=" + manifest["selector"],
            "-test.count=1", "-test.timeout=26m",
        ], heart, 1650)
        result["native_cases"] = verify_native_results(output, manifest["expected_cases"])
        for name in ("original-import-reentrant-retirement.json",):
            require((evidence / name).is_file(), "Actual native phase receipt absent")
            result.setdefault("native_receipts", []).append({"path": name, "sha256": support.digest(evidence / name)})
        for entry in closure["files"]:
            require(support.digest(entry["path"]) == entry["sha256"], "Declared native input changed during runtime")
        for name, digest in composed.items():
            require(support.digest(heart / name) == digest, "Product or test source changed during runtime")
        require(support.native_library_inputs(heart) == native, "Native link inputs changed")
        require(support.digest(binary) == result["native_binary"]["sha256"], "Executed native binary changed")
        control_inputs(control, packet, manifest)
        read_sources(control, manifest)
        result["native_result"] = "ONE_ACTUAL_NATIVE_REENTRANT_CASE_PASSED"
        result["prior_prestart_pass_reused_without_reexecution"] = True
        result["status"], success = "PASS_NATIVE_REENTRANT_WITH_REUSED_PRESTART", True
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        try:
            require(commands.owned_groups_drained, "Preserve native temporary state: owned process group not drained")
            shutil.rmtree(temporary)
            result["owned_native_temporary_removed"] = True
        except Exception as error:
            result.update(status="FAIL", owned_native_temporary_removed=False,
                          cleanup_error_type=type(error).__name__)
            success = False
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        support.write_json(evidence / "RESULT.json", result)
        support.write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Exact source, compiler, native-case and lifetime receipts. No wallet, account database or credential file.",
            "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": support.digest(path)}
                      for path in sorted(evidence.iterdir()) if path.is_file() and path.name != "EVIDENCE_INDEX.json"],
        })
    return 0 if success else 1

if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Native workflow interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
