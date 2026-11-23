#!/usr/bin/env python3
"""Qualify the actual original native endpoint using retained generated RPC bytes."""
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
import zipfile

PACKET = "docs/pinkha/torah-integration/native-schema-endpoint-runtime-20261123"
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
        retained = PACKET + "/retained-inputs/" + entry["destination"]
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


def generated_inputs(control, manifest, archive, generation_root=None):
    binding = manifest["generation"]
    require(binding["regeneration_requested"] is False, "Prior accepted generation must be reused")
    require(archive.is_file() and archive.stat().st_size == binding["artifact_zip_bytes"],
            "Original generated archive absent or changed")
    data = archive.read_bytes()
    require(sha(data) == binding["artifact_zip_sha256"], "Original generated archive hash differs")
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    require(blob == binding["git_evidence_blob"], "Original generated archive Git blob differs")
    if generation_root:
        require(git(generation_root, "rev-parse", "HEAD").decode().strip() == binding["git_evidence_commit"],
                "Generation evidence checkout is not the exact accepted revision")
        require(archive == safe(generation_root, binding["git_evidence_path"]).resolve(),
                "Generation archive does not belong to its immutable checkout")
        require(data == git(generation_root, "show", "HEAD:" + binding["git_evidence_path"]),
                "Generation evidence archive is dirty")
    rows = []
    with zipfile.ZipFile(archive) as zipped:
        require(len(zipped.namelist()) == len(set(zipped.namelist())), "Ambiguous generation archive member")
        original = json.loads(zipped.read("RESULT.json"))
        require(original["status"] == "GENERATED_AND_MESSAGE_COMPILE_VERIFIED"
                and original["control_head"] == binding["source_sha"]
                and original["owned_command_groups_drained"] is True,
                "Accepted generation result/source binding differs")
        for entry in binding["generated_native_inputs"]:
            raw = zipped.read(entry["archive_path"])
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            require(len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
                    and blob == entry["git_blob"], "Actual original generated candidate differs")
            rows.append(dict(entry))
    return rows

def install_native(support, commands, inputs, heart, packet, manifest, evidence, archive):
    require(git(heart, "rev-parse", "HEAD").decode().strip() == HEART, "Original Heart checkout differs")
    require(not git(heart, "status", "--porcelain", "--untracked-files=all").strip(), "Original Heart checkout is not fresh")
    for name, digest in manifest["original_module_hashes"].items():
        require(support.digest(heart / name) == digest, "Original module/native checksum differs")
    patch = inputs / "r14/native-heart-integration.patch"
    inventory = json.loads((inputs / "r14/native-heart-integration.json").read_bytes())
    require(inventory["heart_sha"] == HEART and inventory["patch_sha256"] == support.digest(patch), "Original r14 binding differs")
    commands.require("r14-check", ["git", "apply", "--check", str(patch)], heart, 30)
    commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
    composed = {}
    for entry in inventory["files"]:
        require(support.digest(heart / entry["path"]) == entry["after_sha256"], "r14 afterimage differs")
        composed[entry["path"]] = entry["after_sha256"]
    required = {}
    for entry in manifest["source_inputs"]:
        if entry["role"] not in ("native-product", "proto-source"):
            continue
        name = entry["heart_path"]
        target = safe(heart, name)
        before = entry["heart_preimage_sha256"]
        require((target.is_file() and support.digest(target) == before) if before is not None else not target.exists(),
                "Original native product/proto preimage differs: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(safe(inputs, entry["destination"]).read_bytes())
        require(support.digest(target) == entry["sha256"], "Accepted native product afterimage differs")
        composed[name] = entry["sha256"]
        if entry["role"] == "native-product":
            required[name] = entry["sha256"]
    with zipfile.ZipFile(archive) as zipped:
        for entry in manifest["generation"]["generated_native_inputs"]:
            name = entry["path"]
            target = safe(heart, name)
            require(target.is_file() and support.digest(target) == entry["heart_preimage_sha256"],
                    "Original generated Go preimage differs")
            target.write_bytes(zipped.read(entry["archive_path"]))
            require(support.digest(target) == entry["sha256"], "Actual generated Go afterimage differs")
            composed[name] = entry["sha256"]
            # The actual mobile service entrypoint transitively compiles core and
            # pb/commands. pb/service remains the same accepted generated package;
            # this gate does not replay its independent message-only compilation.
            if name != "pb/service/service.pb.go":
                required[name] = entry["sha256"]
    name = manifest["test_file"].removeprefix("native/")
    target = safe(heart, name)
    require(not target.exists(), "Native test path already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((packet / manifest["test_file"]).read_bytes())
    required[name] = support.digest(target)
    composed[name] = required[name]
    status = git(heart, "status", "--porcelain", "--untracked-files=all").decode().splitlines()
    require(all(row[:2] in (" M", "??") and row[3:] in composed for row in status), "Unexpected native source mutation")
    for name, digest in composed.items():
        require(support.digest(heart / name) == digest, "Composed original source differs")
    support.write_json(evidence / "COMPOSED_NATIVE_SOURCES.json", {
        "all_declared_afterimages": composed, "required_actual_compiler_coverage": required,
        "genuine_generated_bytes_reused": True, "old_native_selectors_replayed": False,
    })
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
    selected = set(expected) | {"TestOtzariaOriginalSchemaEndpoint"}
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
    parser.add_argument("--generation-archive", required=True, type=Path)
    parser.add_argument("--generation-root", type=Path)
    args = parser.parse_args()
    control = args.control_root.resolve()
    packet = control / PACKET
    manifest_raw = (packet / "EXECUTION_INPUTS.json").read_bytes()
    require(sha(manifest_raw) == args.execution_manifest_sha256, "Workflow manifest binding differs")
    manifest = json.loads(manifest_raw)
    require(git(control, "rev-parse", "HEAD").decode().strip() == args.control_head, "Workflow source differs")
    controls = control_inputs(control, packet, manifest)
    archive = args.generation_archive.resolve()
    generation_root = args.generation_root.resolve() if args.generation_root else None
    generated = generated_inputs(control, manifest, archive, generation_root)
    if args.source_only:
        rows = read_sources(control, manifest)
        print(json.dumps({"status": "SOURCE_ONLY_PASS", "checkout_sha": args.control_head,
                          "immutable_source_rows": len(rows), "controls": controls,
                          "genuine_generated_rows": generated, "generation_replayed": False,
                          "native_execution": False, "provider_called": False}, indent=2))
        return 0
    heart, work, evidence = (p.resolve() for p in (args.heart, args.work, args.evidence))
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Darwin ARM64 native route required")
    require(not work.exists() and not evidence.exists(), "Fresh owned native work/evidence paths required")
    for path in (heart, work, evidence):
        require(path.is_relative_to(control) and path != control, "Execution path escapes owned checkout")
    require(generation_root is not None and generation_root.is_relative_to(control), "Owned exact generation evidence checkout required")
    roots = (packet, heart, work, evidence, generation_root)
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
              "generation_evidence": manifest["generation"], "generated_inputs": generated}
    support.write_json(evidence / "RESULT.json", result)
    success = False
    try:
        required, composed = install_native(support, commands, inputs, heart, packet, manifest, evidence, archive)
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
            str(Path(go).with_name("gofmt")), "-l", str(heart / manifest["test_file"].removeprefix("native/"))
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
        listing = commands.require("declared-native-inputs", [go, "list", "-deps", "-test", "-json", "./clientlibrary/service"], heart, 1200)
        coverage = [{"path": name, "sha256": digest} for name, digest in sorted(required.items())]
        closure = support.dependency_inputs(listing, heart, coverage)
        support.write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        require(len(closure["required_product_test_coverage"]) == 16, "Native compiled source closure is incomplete")
        binary = work / "original-native-schema-endpoint.test"
        commands.require("compile-new-native-cases", [go, "test", "-c", "-p", "2", "-o", str(binary), "./clientlibrary/service"], heart, 3600)
        require(binary.is_file() and binary.stat().st_size > 0, "Native compiler produced no test executable")
        result["native_binary"] = {"sha256": support.digest(binary), "bytes": binary.stat().st_size}
        commands.require("native-binary-buildinfo", [go, "version", "-m", str(binary)], heart, 30)
        result["native_result"] = "EXECUTION_REQUESTED"
        support.write_json(evidence / "RESULT.json", result)
        output = commands.require("execute-new-native-cases", [
            go, "tool", "test2json", "-t", "-p", "github.com/anyproto/anytype-heart/clientlibrary/service",
            str(binary), "-test.v=test2json", "-test.run=" + manifest["selector"],
            "-test.count=1", "-test.timeout=26m",
        ], heart, 1650)
        result["native_cases"] = verify_native_results(output, manifest["expected_cases"])
        for name in manifest["expected_receipts"]:
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
        generated_inputs(control, manifest, archive, generation_root)
        result["native_result"] = "FIVE_ACTUAL_NATIVE_ENDPOINT_CASES_PASSED"
        result["status"], success = "PASS_NATIVE_ENDPOINT_ONLY", True
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
            "scope": "Exact source, compiler, actual native endpoint wire/phase receipts. No wallet, account database or credential file.",
            "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": support.digest(path)}
                      for path in sorted(evidence.iterdir()) if path.is_file() and path.name != "EVIDENCE_INDEX.json"],
        })
    return 0 if success else 1

if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Native workflow interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())