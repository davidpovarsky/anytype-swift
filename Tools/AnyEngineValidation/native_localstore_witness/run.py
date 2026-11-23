#!/usr/bin/env python3
"""Owned Oracle controller. Raw runtime output and native witnesses remain private."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone

MIN_FREE = 2_500_000_000
STOP_FREE = 2_600_000_000
START_FREE = 2_950_000_000
GO = pathlib.Path("/mnt/development/toolchains/go1.27.4/go/bin/go")
MODCACHE = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache/go-mod")
BUILDCACHE = pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-build-glibc")
GOPATH = pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-path")
PACKAGE = "github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def now():
    return datetime.now(timezone.utc).isoformat()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def command(argv, cwd, env, log, timeout):
    record = {"argv": argv, "cwd": str(cwd), "started": now(), "timeout_seconds": timeout,
              "free_bytes_before": shutil.disk_usage("/mnt/development").free}
    if record["free_bytes_before"] < STOP_FREE:
        raise RuntimeError("insufficient reserved disk before command")
    started = time.monotonic()
    with open(log, "xb") as stream:
        os.chmod(log, 0o600)
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        record["owned_pid"] = child.pid
        record["owned_pgid"] = os.getpgid(child.pid)
        record["interruption"] = None
        while child.poll() is None:
            free = shutil.disk_usage("/mnt/development").free
            if free < STOP_FREE or time.monotonic() - started >= timeout:
                record["interruption"] = "disk-reserve" if free < STOP_FREE else "timeout"
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                break
            time.sleep(0.25)
        record["returncode"] = child.wait()
        deadline = time.monotonic() + 3
        while True:
            try:
                os.killpg(child.pid, 0)
                absent = False
            except ProcessLookupError:
                absent = True
            if absent or time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        record["owned_process_group_absent"] = absent
        stream.flush()
        os.fsync(stream.fileno())
    record.update(finished=now(), elapsed_seconds=time.monotonic()-started,
                  free_bytes_after=shutil.disk_usage("/mnt/development").free,
                  original_log_sha256=digest(log), original_log_bytes=log.stat().st_size)
    write(log.with_suffix(log.suffix + ".command.json"), record)
    if not record["owned_process_group_absent"]:
        raise RuntimeError("owned process group did not become quiescent")
    return record

def native_inputs(native, manifest):
    if git(native, "rev-parse", "HEAD") != manifest["native_source_sha"]:
        raise RuntimeError("native source commit changed")
    if git(native, "status", "--porcelain"):
        raise RuntimeError("native source worktree is not clean")
    paths = {row["native_path"]: row["sha256"] for row in manifest["files"]}
    paths.update(manifest["module_sha256"])
    for rel, expected in paths.items():
        if digest(native / rel) != expected:
            raise RuntimeError("native source bytes changed: " + rel)
    return paths

def json_sequence(raw):
    decoder = json.JSONDecoder()
    at = 0
    while at < len(raw):
        while at < len(raw) and raw[at].isspace():
            at += 1
        if at == len(raw):
            return
        value, at = decoder.raw_decode(raw, at)
        yield value

def dependency_inputs(raw, native):
    paths = set()
    modules = {}
    fields = ("GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles",
              "FFiles", "SFiles", "SysoFiles", "EmbedFiles", "TestGoFiles", "XTestGoFiles")
    for pkg in json_sequence(raw):
        if pkg.get("Error") or pkg.get("DepsErrors"):
            raise RuntimeError("native package/dependency resolution error")
        directory = pkg.get("Dir")
        if directory:
            for field in fields:
                for rel in pkg.get(field, []):
                    path = pathlib.Path(directory) / rel
                    if path.is_file():
                        paths.add(str(path.resolve()))
        module = pkg.get("Module")
        if module:
            modules[module["Path"]] = module
            for item in (module, module.get("Replace", {})):
                gomod = item.get("GoMod")
                if gomod and pathlib.Path(gomod).is_file():
                    paths.add(str(pathlib.Path(gomod).resolve()))
    result = {path: digest(path) for path in sorted(paths)}
    if not any(str(native / "core/pinkha/localstorewitness/capture.go") == path for path in result):
        raise RuntimeError("native package absent from resolved input closure")
    return result, modules

def expected_tests(methods):
    result = set(methods)
    groups = {
        "TestLocalStoreWitnessOwnershipAndCancellation":
            ["retired-before", "retired-after-inventory", "wrong-space", "unsupported-authority", "cancel-after-inventory", "lease-close"],
        "TestLocalStoreWitnessLimitsAndNativeBinding":
            ["collections", "rows", "row-bytes", "total-bytes", "wrong-native-state", "missing-native-header"],
        "TestLocalStoreWitnessIteratorAndTransactionFailures":
            ["iterator-terminal", "iterator-close", "transaction-close"],
    }
    for parent, children in groups.items():
        result.update(parent + "/" + name for name in children)
    return result

def safe_receipt(value):
    fixed = {
        "Version": "native-localstore-witness-v1",
        "Encoding": "anyenc-v1.0.3-decoded-value-roundtrip-v1",
        "Authority": "owned-fixture-only-v1",
        "InventoryScope": "registered-native-collections-only",
        "NativeBindingScope": "space-state-acl-settings-roots-only",
        "LocalDecodedRowsComplete": True,
        "NativeSnapshotProofRequired": True,
        "NativeIdentityCensusRequired": True,
        "HasNativeSourceAdmission": False,
        "PermitsDestinationWrites": False,
    }
    hashes = ["OwnerSHA256", "SpaceSHA256", "SpaceHeaderSHA256", "WitnessSHA256"]
    counts = ["Generation", "Collections", "Rows", "EncodedValueBytes"]
    if set(value) != set(fixed) | set(hashes) | set(counts) | {"CollectionCoverage"}:
        raise RuntimeError("unexpected safe receipt keys")
    if any(type(value[k]) is not type(v) or value[k] != v for k, v in fixed.items()):
        raise RuntimeError("safe receipt scope mismatch")
    for key in hashes:
        if not isinstance(value[key], str) or not re.fullmatch("[0-9a-f]{64}", value[key]):
            raise RuntimeError("unsafe digest field")
    for key in counts:
        if type(value[key]) is not int or value[key] < 1:
            raise RuntimeError("invalid safe receipt count")
    rows = value["CollectionCoverage"]
    if not isinstance(rows, list) or len(rows) != value["Collections"]:
        raise RuntimeError("invalid collection coverage")
    for row in rows:
        if set(row) != {"NameSHA256", "Rows", "EncodedValueBytes", "UnresolvedCollection"}:
            raise RuntimeError("unsafe collection receipt")
        if not re.fullmatch("[0-9a-f]{64}", row["NameSHA256"]):
            raise RuntimeError("unsafe collection identity")
        if type(row["UnresolvedCollection"]) is not bool:
            raise RuntimeError("invalid collection disposition")
        if any(type(row[k]) is not int or row[k] < 0 for k in ["Rows", "EncodedValueBytes"]):
            raise RuntimeError("invalid collection count")
    if sum(row["Rows"] for row in rows) != value["Rows"] or sum(row["EncodedValueBytes"] for row in rows) != value["EncodedValueBytes"]:
        raise RuntimeError("safe receipt coverage totals mismatch")
    if len({row["NameSHA256"] for row in rows}) != len(rows):
        raise RuntimeError("duplicate collection receipt")
    return value

def inspect_events(log, methods, safe_path):
    events, receipts = [], []
    streams = {}
    for line in log.read_text().splitlines():
        value = json.loads(line)
        if value.get("Package") != PACKAGE:
            raise RuntimeError("unexpected executed package")
        events.append({key: value[key] for key in ["Time", "Action", "Package", "Test", "Elapsed"] if key in value})
        if "Output" in value:
            key = value.get("Test", "")
            streams[key] = streams.get(key, "") + value["Output"]
    write(safe_path, events)
    expected = expected_tests(methods)
    starts = [v["Test"] for v in events if v.get("Action") == "run" and "Test" in v]
    passes = [v["Test"] for v in events if v.get("Action") == "pass" and "Test" in v]
    if len(starts) != len(expected) or set(starts) != expected or len(passes) != len(expected) or set(passes) != expected:
        raise RuntimeError("named native run/pass scope is incomplete or unexpected")
    if any(v.get("Action") in ("fail", "skip") for v in events):
        raise RuntimeError("native fail/skip event")
    main = streams.get("TestLocalStoreWitnessNativeConcurrentTransaction", "")
    for line in main.splitlines():
        marker = "WITNESS_SAFE_RECEIPT "
        if marker in line:
            receipts.append(safe_receipt(json.loads(line.split(marker, 1)[1])))
    if len(receipts) != 2:
        raise RuntimeError("exact two native transaction receipts required")
    if receipts[0]["OwnerSHA256"] != receipts[1]["OwnerSHA256"] or receipts[0]["SpaceSHA256"] != receipts[1]["SpaceSHA256"]:
        raise RuntimeError("native interleaving changed owner or Space")
    if receipts[0]["WitnessSHA256"] == receipts[1]["WitnessSHA256"]:
        raise RuntimeError("later native transaction did not change")
    proof = "NATIVE_INTERLEAVING one_read_transaction=1 exact_context=1 writer_committed_after_inventory=1 later_transaction_sees_commit=1 iterator_detachment=1"
    if main.count(proof) != 1:
        raise RuntimeError("native interleaving observation missing")
    return events, receipts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build", "execute"])
    ap.add_argument("--native", type=pathlib.Path, required=True)
    ap.add_argument("--evidence", type=pathlib.Path, required=True)
    args = ap.parse_args()
    source = pathlib.Path(__file__).resolve().parent
    manifest = json.loads((source / "source.json").read_text())
    if digest(__file__) != manifest["controller_sha256"] or digest(source / "PROTOCOL.md") != manifest["protocol_sha256"]:
        raise RuntimeError("frozen controller/protocol bytes changed")
    source_repo = source.parents[2]
    if git(source_repo, "status", "--porcelain"):
        raise RuntimeError("controller source worktree is not clean")
    for row in manifest["files"]:
        if digest(source_repo / row["copy_path"]) != row["sha256"]:
            raise RuntimeError("frozen source copy changed")
    native = args.native.resolve()
    evidence = args.evidence.resolve()
    if not str(native).startswith("/mnt/development/projects/worktrees/") or not str(evidence).startswith("/mnt/development/projects/evidence/localstore-witness-20261123/"):
        raise RuntimeError("owned Oracle paths required")
    if shutil.disk_usage("/mnt/development").free < (START_FREE if args.stage == "build" else STOP_FREE):
        raise RuntimeError("insufficient reserved capacity")
    if args.stage == "build":
        evidence.mkdir(parents=True, exist_ok=False)
        (evidence / "private").mkdir(mode=0o700)
        (evidence / "private/fixtures").mkdir(mode=0o700)
        (evidence / "tmp").mkdir(mode=0o700)
        (evidence / "products").mkdir()
    env = dict(os.environ, GOMAXPROCS="1", CGO_ENABLED="1", GOPROXY="off", GOSUMDB="off",
               GOTOOLCHAIN="local", GOPATH=str(GOPATH), GOMODCACHE=str(MODCACHE),
               GOCACHE=str(BUILDCACHE), TMPDIR=str(evidence / "tmp"), GOTMPDIR=str(evidence / "tmp"),
               PINKHA_LOCAL_WITNESS_PRIVATE_ROOT=str(evidence / "private/fixtures"))
    result = {"stage": args.stage, "status": "FAILED", "started": now(), "old_methods_run": 0,
              "controller_sha256": digest(__file__), "manifest_sha256": digest(source / "source.json"),
              "native_source_sha": manifest["native_source_sha"], "controller_source_sha": git(source_repo, "rev-parse", "HEAD"), "command": None}
    result_path = evidence / (args.stage + ".json")
    if result_path.exists():
        raise RuntimeError("owned stage receipt already exists; never overwrite an attempt")
    try:
        inputs = native_inputs(native, manifest)
        write(evidence / (args.stage + "-source-before.json"), inputs)
        binary = evidence / "products/localstore-witness.test"
        if args.stage == "build":
            result["go_version"] = subprocess.check_output([str(GO), "version"], text=True).strip()
            result["go_binary_sha256"] = digest(GO)
            if result["go_version"] != "go version go1.27.4 linux/arm64" or result["go_binary_sha256"] != manifest["go_binary_sha256"]:
                raise RuntimeError("frozen Go toolchain changed")
            result["environment"] = {key: env[key] for key in ["GOMAXPROCS", "CGO_ENABLED", "GOPROXY", "GOSUMDB", "GOTOOLCHAIN", "GOPATH", "GOMODCACHE", "GOCACHE", "TMPDIR", "GOTMPDIR"]}
            result["compiler_version"] = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
            dep_log = evidence / "private/dependencies-original.json"
            cmd = command([str(GO), "list", "-mod=readonly", "-deps", "-test", "-json", "-tags=pinkha_localstore_witness", manifest["package"]], native, env, dep_log, 120)
            if cmd["returncode"] != 0:
                raise RuntimeError("dependency resolution failed; original retained privately")
            dependencies, modules = dependency_inputs(dep_log.read_text(), native)
            write(evidence / "dependency-inputs-before.json", dependencies)
            write(evidence / "resolved-modules.json", modules)
            result["command"] = command([str(GO), "test", "-mod=readonly", "-c", "-p=1", "-tags=pinkha_localstore_witness", "-o", str(binary), manifest["package"]], native, env, evidence / "private/build-original.log", 900)
            after = {path: digest(path) for path in dependencies}
            write(evidence / "dependency-inputs-after-build.json", after)
            if dependencies != after:
                raise RuntimeError("dependency inputs changed during build")
            if result["command"]["returncode"] != 0:
                raise RuntimeError("build failed; original retained privately")
            result["binary_sha256"] = digest(binary)
            result["binary_bytes"] = binary.stat().st_size
            buildinfo = subprocess.check_output([str(GO), "version", "-m", str(binary)], text=True)
            (evidence / "binary-buildinfo-original.txt").write_text(buildinfo)
            result["actual_product_methods_executed"] = 0
            result["status"] = "BUILD_PASS_EXECUTION_NOT_RUN"
        else:
            build = json.loads((evidence / "build.json").read_text())
            if build["status"] != "BUILD_PASS_EXECUTION_NOT_RUN" or build["binary_sha256"] != digest(binary):
                raise RuntimeError("original qualified binary missing or changed")
            if build["manifest_sha256"] != result["manifest_sha256"] or build["controller_sha256"] != result["controller_sha256"]:
                raise RuntimeError("build/execute controller binding changed")
            dependencies = json.loads((evidence / "dependency-inputs-before.json").read_text())
            if any(digest(path) != expected for path, expected in dependencies.items()):
                raise RuntimeError("dependency inputs changed before execution")
            selector = "^(" + "|".join(manifest["selected_top_level_methods"]) + ")$"
            raw = evidence / "private/execution-original.jsonl"
            result["command"] = command([str(GO), "tool", "test2json", "-t", "-p", PACKAGE, str(binary), "-test.v=test2json", "-test.run=" + selector, "-test.timeout=90s", "-test.count=1"], native, env, raw, 120)
            events, receipts = inspect_events(raw, manifest["selected_top_level_methods"], evidence / "safe-events.json")
            write(evidence / "safe-events.json", events)
            write(evidence / "safe-native-receipts.json", receipts)
            if result["command"]["returncode"] != 0:
                raise RuntimeError("native execution failed; original retained privately")
            private_files = {}
            for path in sorted((evidence / "private/fixtures").rglob("*")):
                if path.is_symlink():
                    raise RuntimeError("unexpected private artifact symlink")
                if path.is_file():
                    private_files[str(path.relative_to(evidence / "private"))] = {"sha256": digest(path), "bytes": path.stat().st_size, "mode": oct(path.stat().st_mode & 0o777)}
            write(evidence / "private-artifacts-hashes.json", private_files)
            after_dependencies = {path: digest(path) for path in dependencies}
            write(evidence / "dependency-inputs-after-execute.json", after_dependencies)
            if after_dependencies != dependencies:
                raise RuntimeError("dependency inputs changed during execution")
            result["actual_product_methods_executed"] = len(manifest["selected_top_level_methods"])
            result["actual_named_starts_and_passes"] = len(expected_tests(manifest["selected_top_level_methods"]))
            result["actual_interleaving_proofs"] = 1
            result["binary_sha256"] = digest(binary)
            result["status"] = "PASS_NATIVE_LOCAL_STORAGE_SCOPE_ONLY"
        after = native_inputs(native, manifest)
        write(evidence / (args.stage + "-source-after.json"), after)
        if after != inputs:
            raise RuntimeError("native source changed")
        result["finished"] = now()
    except BaseException as error:
        result["status"] = "FAILED"
        result["finished"] = now()
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        try:
            write(evidence / (args.stage + "-source-final.json"), native_inputs(native, manifest))
        except BaseException as final_error:
            result["status"] = "FAILED"
            result["source_final_error"] = {"type": type(final_error).__name__, "message": str(final_error)}
        result["free_bytes_final"] = shutil.disk_usage("/mnt/development").free
        write(result_path, result)
        print(json.dumps({"stage": args.stage, "status": result["status"], "receipt": str(result_path),
                          "receipt_sha256": digest(result_path), "free_bytes": result["free_bytes_final"]}))

if __name__ == "__main__":
    main()
