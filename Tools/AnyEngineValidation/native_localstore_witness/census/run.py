#!/usr/bin/env python3
"""Five new captured local-tree-storage census methods; no old native method reruns."""
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


from audit_private import LABELS, audit_private_pairs, safe_receipt

METHODS = [
    "TestLocalTreeCensusNativeStorageRelationships",
    "TestLocalTreeCensusUsesCapturedCheckpointWithoutLiveReads",
    "TestLocalTreeCensusRetainsUnknownRowsAndExactTypedIdentities",
    "TestLocalTreeCensusReportsMissingCrossTreeAndACLReferences",
    "TestLocalTreeCensusQualificationLimitsAndPrivateReceipt",
]
NATIVE_PARENT = "102f6243edb17068048869b85bc151f177897a68"
PREFIX = "core/pinkha/localstorewitness/"

def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)

def native_inputs(native, manifest):
    require(git(native, "rev-parse", "HEAD") == manifest["native_source_sha"], "native_source_commit_changed")
    require(not git(native, "status", "--porcelain"), "native_worktree_dirty")
    require(git(native, "merge-base", "HEAD", NATIVE_PARENT) == NATIVE_PARENT, "native_parent_changed")
    changed = git(native, "diff", "--name-only", NATIVE_PARENT, "HEAD").splitlines()
    require(changed == sorted(v["native_path"] for v in manifest["files"]), "only_four_new_native_files_permitted")
    paths = dict(manifest["retained_native_sha256"])
    paths.update({v["native_path"]: v["sha256"] for v in manifest["files"]})
    paths.update(manifest["module_sha256"])
    require(len(manifest["files"]) == 4 and len(manifest["retained_native_sha256"]) == 6, "native_source_shape")
    for rel, expected in paths.items():
        require((native / rel).is_file() and not (native / rel).is_symlink() and digest(native / rel) == expected,
                "native_source_bytes_changed")
    for rel, expected in manifest["retained_native_sha256"].items():
        original = subprocess.check_output(["git", "-C", str(native), "show", NATIVE_PARENT + ":" + rel])
        require(hashlib.sha256(original).hexdigest() == expected, "retained_native_original_changed")
    return paths

def schema_inputs(manifest):
    result = {}
    for row in manifest["read_dependency_sources"]:
        path = MODCACHE / row["module"] / row["path"]
        require(path.is_file() and not path.is_symlink() and digest(path) == row["sha256"] and
                path.stat().st_size == row["bytes"], "pinned_native_schema_dependency_changed")
        result[str(path)] = row["sha256"]
    return result

def controller_inputs(source, manifest):
    root = source.parents[3]
    require(not git(root, "status", "--porcelain"), "controller_source_worktree_dirty")
    result = {}
    paths = {"run.py": manifest["controller_sha256"], "audit_private.py": manifest["private_auditor_sha256"],
             "PROTOCOL.md": manifest["protocol_sha256"]}
    for name, expected in paths.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and digest(path) == expected,
                "controller_source_bytes_changed")
        result[str(path.relative_to(root))] = expected
    result[str((source / "source.json").relative_to(root))] = digest(source / "source.json")
    for row in manifest["files"]:
        path = root / row["copy_path"]
        require(path.is_file() and not path.is_symlink() and digest(path) == row["sha256"],
                "frozen_native_source_copy_changed")
        result[row["copy_path"]] = row["sha256"]
    for path, expected in result.items():
        raw = subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + path])
        require(hashlib.sha256(raw).hexdigest() == expected, "controller_physical_git_mismatch")
    return result

def inspect_events(log, safe_path):
    events, streams, receipts = [], {}, {}
    for line in log.read_text().splitlines():
        value = json.loads(line)
        require(value.get("Package") == PACKAGE, "unexpected_executed_native_package")
        events.append({key: value[key] for key in ["Time", "Action", "Package", "Test", "Elapsed"] if key in value})
        if "Output" in value:
            require(type(value["Output"]) is str, "invalid_native_output")
            key = value.get("Test", "")
            streams[key] = streams.get(key, "") + value["Output"]
    write(safe_path, events)
    starts = [v["Test"] for v in events if v.get("Action") == "run" and "Test" in v]
    passes = [v["Test"] for v in events if v.get("Action") == "pass" and "Test" in v]
    require(sorted(starts) == sorted(METHODS) and sorted(passes) == sorted(METHODS),
            "five_new_named_run_pass_scope_required")
    require(not any(v.get("Action") in ("fail", "skip") for v in events), "native_fail_or_skip_event")
    for method, stream in streams.items():
        for line in stream.splitlines():
            if not line.startswith("LOCAL_TREE_CENSUS_RECEIPT "):
                continue
            _, label, raw = line.split(" ", 2)
            require(label in LABELS and LABELS[label] == method and label not in receipts,
                    "unexpected_duplicate_or_wrong_method_census_receipt")
            receipts[label] = safe_receipt(json.loads(raw))
    require(set(receipts) == set(LABELS), "six_private_census_pair_receipts_required")
    return events, receipts

def source_snapshot(native, source, manifest):
    return {"native": native_inputs(native, manifest), "controller": controller_inputs(source, manifest),
            "native_schema_dependencies": schema_inputs(manifest)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build", "execute"])
    ap.add_argument("--native", type=pathlib.Path, required=True)
    ap.add_argument("--evidence", type=pathlib.Path, required=True)
    args = ap.parse_args()
    source = pathlib.Path(__file__).resolve().parent
    source_repo = source.parents[3]
    manifest = json.loads((source / "source.json").read_text())
    require(manifest["selected_top_level_methods"] == METHODS and manifest["expected_named_runs_and_passes"] == 5
            and manifest["native_parent_sha"] == NATIVE_PARENT and
            manifest["package"] == "./core/pinkha/localstorewitness" and
            manifest["old_methods_selected"] == 0 and manifest["production_capability_issuer"] is False,
            "five_new_census_method_contract_changed")
    native, evidence = args.native.resolve(), args.evidence.resolve()
    require(native.parent == pathlib.Path("/mnt/development/projects/worktrees") and
            native.name == "anytype-heart-local-tree-census-20261123" and
            evidence.parent == pathlib.Path("/mnt/development/projects/evidence/local-tree-census-20261123") and
            re.fullmatch(r"attempt[1-9][0-9]*", evidence.name), "fixed_owned_oracle_paths_required")
    require(shutil.disk_usage("/mnt/development").free >= (START_FREE if args.stage == "build" else STOP_FREE),
            "insufficient_reserved_capacity")
    if args.stage == "build":
        evidence.mkdir(parents=True, exist_ok=False)
        (evidence / "private").mkdir(mode=0o700)
        (evidence / "private/fixtures").mkdir(mode=0o700)
        (evidence / "tmp").mkdir(mode=0o700)
        (evidence / "products").mkdir()
    require(evidence.is_dir() and not evidence.is_symlink(), "owned_attempt_directory_missing")
    env = dict(os.environ, GOMAXPROCS="1", CGO_ENABLED="1", GOPROXY="off", GOSUMDB="off",
               GOTOOLCHAIN="local", GOPATH=str(GOPATH), GOMODCACHE=str(MODCACHE),
               GOCACHE=str(BUILDCACHE), TMPDIR=str(evidence / "tmp"), GOTMPDIR=str(evidence / "tmp"),
               PINKHA_LOCAL_WITNESS_PRIVATE_ROOT=str(evidence / "private/fixtures"))
    result = {"stage": args.stage, "status": "FAILED", "started": now(),
              "scope": "captured-local-tree-storage-census-only-v1",
              "old_methods_executed": 0, "new_methods_executed": 0,
              "actual_new_interleaving_proofs": 0, "production_capability_issuer": False,
              "hasNativeSourceAdmission": False, "permitsDestinationWrites": False,
              "semanticIdentityCensusComplete": False,
              "controller_sha256": digest(__file__), "manifest_sha256": digest(source / "source.json"),
              "private_auditor_sha256": digest(source / "audit_private.py"),
              "native_source_sha": manifest["native_source_sha"],
              "controller_source_sha": git(source_repo, "rev-parse", "HEAD"), "command": None}
    dependencies = None
    result_path = evidence / (args.stage + ".json")
    require(not result_path.exists(), "never_overwrite_original_stage_receipt")
    try:
        inputs = source_snapshot(native, source, manifest)
        write(evidence / (args.stage + "-source-before.json"), inputs)
        binary = evidence / "products/local-tree-census.test"
        if args.stage == "build":
            result["go_version"] = subprocess.check_output([str(GO), "version"], text=True).strip()
            result["go_binary_sha256"] = digest(GO)
            require(result["go_version"] == "go version go1.27.4 linux/arm64" and
                    result["go_binary_sha256"] == manifest["go_binary_sha256"], "frozen_go_toolchain_changed")
            result["environment"] = {key: env[key] for key in ["GOMAXPROCS", "CGO_ENABLED", "GOPROXY", "GOSUMDB",
                                      "GOTOOLCHAIN", "GOPATH", "GOMODCACHE", "GOCACHE", "TMPDIR", "GOTMPDIR"]}
            result["compiler_version"] = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
            require(result["compiler_version"] == manifest["compiler_version"], "native_c_compiler_identity_changed")
            dep_log = evidence / "private/dependencies-original.json"
            cmd = command([str(GO), "list", "-mod=readonly", "-deps", "-test", "-json",
                           "-tags=pinkha_localstore_witness", manifest["package"]], native, env, dep_log, 120)
            result["dependency_command"] = cmd
            require(cmd["returncode"] == 0, "dependency_resolution_failed_original_preserved")
            dependencies, modules = dependency_inputs(dep_log.read_text(), native)
            write(evidence / "dependency-inputs-before.json", dependencies)
            write(evidence / "resolved-modules.json", modules)
            module_versions = {key: value.get("Version") for key, value in modules.items() if not value.get("Main")}
            require(module_versions == manifest["retained_external_module_versions"], "unexpected_native_module_graph_change")
            for rel, expected in inputs["native"].items():
                if rel.endswith(".go"):
                    require(dependencies.get(str(native / rel)) == expected, "declared_native_file_missing_from_resolved_graph")
            result["command"] = command([str(GO), "test", "-mod=readonly", "-c", "-p=1",
                "-tags=pinkha_localstore_witness", "-o", str(binary), manifest["package"]],
                native, env, evidence / "private/build-original.log", 900)
            after = {path: digest(path) for path in dependencies}
            write(evidence / "dependency-inputs-after-build.json", after)
            require(dependencies == after, "dependency_inputs_changed_during_build")
            require(result["command"]["returncode"] == 0, "build_failed_original_preserved")
            result["binary_sha256"], result["binary_bytes"] = digest(binary), binary.stat().st_size
            buildinfo = subprocess.check_output([str(GO), "version", "-m", str(binary)], text=True)
            (evidence / "binary-buildinfo-original.txt").write_text(buildinfo)
            result["status"] = "BUILD_PASS_EXECUTION_NOT_RUN"
        else:
            build = json.loads((evidence / "build.json").read_text())
            require(build["status"] == "BUILD_PASS_EXECUTION_NOT_RUN" and build["binary_sha256"] == digest(binary),
                    "original_qualified_binary_missing_or_changed")
            for key in ("manifest_sha256", "controller_sha256", "private_auditor_sha256", "native_source_sha", "controller_source_sha"):
                require(build[key] == result[key], "build_execute_source_binding_changed")
            dependencies = json.loads((evidence / "dependency-inputs-before.json").read_text())
            require(all(digest(path) == expected for path, expected in dependencies.items()),
                    "dependency_inputs_changed_before_execution")
            selector = "^(" + "|".join(METHODS) + ")$"
            raw = evidence / "private/execution-original.jsonl"
            result["command"] = command([str(GO), "tool", "test2json", "-t", "-p", PACKAGE, str(binary),
                "-test.v=test2json", "-test.run=" + selector, "-test.timeout=90s", "-test.count=1"],
                native, env, raw, 120)
            events, receipts = inspect_events(raw, evidence / "safe-events.json")
            write(evidence / "safe-native-receipts.json", receipts)
            require(result["command"]["returncode"] == 0, "native_execution_failed_original_preserved")
            private_audit = audit_private_pairs(evidence / "private/fixtures", receipts)
            write(evidence / "private-source-accounting-audit.json", private_audit)
            after_dependencies = {path: digest(path) for path in dependencies}
            write(evidence / "dependency-inputs-after-execute.json", after_dependencies)
            require(after_dependencies == dependencies, "dependency_inputs_changed_during_execution")
            result["new_methods_executed"] = 5
            result["actual_named_starts_and_passes"] = 5
            result["private_pairs_independently_audited"] = len(private_audit)
            result["binary_sha256"] = digest(binary)
            result["status"] = "PASS_LOCAL_STRUCTURAL_CENSUS_ONLY"
        after = source_snapshot(native, source, manifest)
        write(evidence / (args.stage + "-source-after.json"), after)
        require(after == inputs, "source_inputs_changed")
        result["finished"] = now()
    except BaseException as error:
        result["status"] = "FAILED"
        result["finished"] = now()
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        if dependencies is not None:
            try:
                final_dependencies = {path: digest(path) for path in dependencies}
                write(evidence / (args.stage + "-dependency-inputs-final.json"), final_dependencies)
                require(final_dependencies == dependencies, "final_dependency_integrity_changed")
            except BaseException as dependency_error:
                result["status"] = "FAILED"
                result["dependency_final_error"] = {"type": type(dependency_error).__name__, "message": str(dependency_error)}
        try:
            write(evidence / (args.stage + "-source-final.json"), source_snapshot(native, source, manifest))
        except BaseException as final_error:
            result["status"] = "FAILED"
            result["source_final_error"] = {"type": type(final_error).__name__, "message": str(final_error)}
        result["free_bytes_final"] = shutil.disk_usage("/mnt/development").free
        write(result_path, result)
        print(json.dumps({"stage": args.stage, "status": result["status"], "receipt": str(result_path),
                          "receipt_sha256": digest(result_path), "free_bytes": result["free_bytes_final"]}))
    require(result["status"] != "FAILED", "final_integrity_failed_originals_preserved")

if __name__ == "__main__":
    main()
