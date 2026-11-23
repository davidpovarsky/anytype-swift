#!/usr/bin/env python3
"""Build the exact additive Page candidate and run only its two new account phases."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CONTROL = HERE.parents[1]
HEART_SHA = "d98420b1113536afd08cde6de9a5816f6d27ffff"
PACKAGE = "github.com/anyproto/anytype-heart/clientlibrary/service"
PROTOCOL = "pinkha-semantic-anchor-native-page-v1"
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
GENPROTO = "google.golang.org/genproto"
GENPROTO_VERSION = "v0.0.0-20241021214115-324edc3d5d38"
GENPROTO_SUM = "h1:Q3nlH8iSQSRUwOskjbcSMcF2jiYMNiQYZ0c2KEJLKKU="
GENPROTO_MOD_SUM = "h1:xBI+tzfqGGN2JBeSebfKXFSdBpWVQ7sLW40PTupVRm4="
PROFILES = {
    "oracle-arm64": {"machine": "aarch64", "go": "go version go1.27.4 linux/arm64", "workspace_go": "1.27.4",
        "image": "sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d",
        "tantivy_arch": "linux-arm64-musl", "tantivy_sha256": "0a4a9143388977df41a174075ce05cd6aee2821da6425b5b9f9d591fe35d3756"},
    "oracle-arm64-go1265": {"machine": "aarch64", "go": "go version go1.26.5 linux/arm64", "workspace_go": "1.26.5",
        "image": "sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d",
        "go_archive_sha256": "fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49",
        "go_binary_sha256": "22201b57b855105df064a291863c3fc04f22a7431187a9205122aff42a0c825b",
        "tantivy_arch": "linux-arm64-musl", "tantivy_sha256": "0a4a9143388977df41a174075ce05cd6aee2821da6425b5b9f9d591fe35d3756"},
    "ci-amd64": {"machine": "x86_64", "go": "go version go1.26.5 linux/amd64", "workspace_go": "1.26.5",
        "image": "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8",
        "tantivy_arch": "linux-amd64-musl", "tantivy_sha256": "88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc"},
}
PHASES = (("capture", "TestSemanticAnchorNativePageCaptureAndWire"),
          ("cold-reopen", "TestSemanticAnchorNativePageColdReopen"))

def require(condition, label):
    if not condition:
        raise ValueError(label)

def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected a regular nonsymlink file")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)

def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

def source(args):
    require(git(CONTROL, "rev-parse", "HEAD") == args.expected_app_sha and not git(CONTROL, "status", "--porcelain"),
            "Controller must be the clean reviewed source commit")
    require(git(args.heart, "rev-parse", "HEAD") == HEART_SHA, "Wrong Heart base")
    manifest = read(HERE / "page-source.json")
    files = manifest["files"]
    require(manifest["heart_sha"] == HEART_SHA and len(files) == manifest["candidate_path_count"] == 154,
            "Wrong candidate inventory")
    require(digest(CONTROL / manifest["qualified139_patch"]) == manifest["qualified139_patch_sha256"],
            "Qualified patch changed")
    require({name: digest(args.heart / name) for name in manifest["module_sha256"]} == manifest["module_sha256"],
            "Native module files changed")
    hashes = {name: digest(args.heart / name) for name in files}
    require(hashes == {name: row["after_sha256"] for name, row in files.items()}, "Candidate source hash mismatch")
    for name, row in files.items():
        if "control_source" in row:
            require(digest(CONTROL / row["control_source"]) == row["after_sha256"], "Additive source differs")
    tracked = {name for name, row in files.items() if row["before_sha256"] is not None}
    changed = set(git(args.heart, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(git(args.heart, "ls-files", "--others", "--exclude-standard").splitlines())
    require(changed == tracked and untracked == files.keys() - tracked, "Unexpected native source mutation")
    return hashes

def prepare(args):
    require(git(CONTROL, "rev-parse", "HEAD") == args.expected_app_sha and not git(CONTROL, "status", "--porcelain"),
            "Exact clean controller required")
    require(git(args.heart, "rev-parse", "HEAD") == HEART_SHA and not git(args.heart, "status", "--porcelain"),
            "Fresh clean pinned Heart checkout required")
    manifest = read(HERE / "page-source.json")
    patch = CONTROL / manifest["qualified139_patch"]
    require(digest(patch) == manifest["qualified139_patch_sha256"], "Qualified patch changed")
    require({name: digest(args.heart / name) for name in manifest["module_sha256"]} == manifest["module_sha256"],
            "Unreviewed native module files")
    subprocess.run(["git", "-C", str(args.heart), "apply", "--check", str(patch)], check=True)
    subprocess.run(["git", "-C", str(args.heart), "apply", str(patch)], check=True)
    for name, row in manifest["files"].items():
        if "control_source" in row:
            destination = args.heart / name
            require(not destination.exists(), "Additive candidate may not replace a native file")
            require(digest(CONTROL / row["control_source"]) == row["after_sha256"], "Additive source changed")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(CONTROL / row["control_source"], destination)
    hashes = source(args)
    save(args.run / "evidence/candidate-source-prepared.json", hashes)
    return hashes

def profile(args):
    value = PROFILES[args.profile]
    require(sys.platform == "linux" and platform.machine() == value["machine"], "Wrong execution architecture")
    require(subprocess.check_output(["go", "version"], text=True).strip() == value["go"], "Wrong Go compiler")
    require(os.environ.get("PINKHA_PAGE_IMAGE") == value["image"], "Wrong declared container image")
    require(Path("/etc/alpine-release").is_file(), "Musl Alpine runtime required")
    compiler = subprocess.check_output(["gcc", "-dumpmachine"], text=True).strip()
    require("musl" in compiler, "Musl C compiler required")
    go = Path(shutil.which("go")).resolve()
    if "go_archive_sha256" in value:
        archive = Path(os.environ.get("PINKHA_PAGE_GO_ARCHIVE", ""))
        require(digest(archive) == value["go_archive_sha256"] and digest(go) == value["go_binary_sha256"],
                "Unverified project Go archive or executable")
    return dict(value, profile=args.profile, alpine=Path("/etc/alpine-release").read_text().strip(),
        compiler_target=compiler, go_executable_sha256=digest(go),
        cache_root=str(cache_root(args)), cache_realpath=str(cache_root(args).resolve()))

def cache_root(args):
    # Keep the chosen absolute spelling stable across retries. Resolving a
    # symlink here would change Go module source filenames and invalidate the
    # already qualified dependency cache despite identical physical files.
    path = args.cache_root if args.cache_root is not None else args.run / "cache"
    require(path.is_absolute() and path.is_dir(), "Existing absolute task cache required")
    resolved = path.resolve()
    require(not resolved.is_relative_to(CONTROL) and not resolved.is_relative_to(args.heart),
            "Cache must be separate from source trees")
    return path

def environment(args, selected):
    work = args.run / "work"
    cache = cache_root(args)
    return dict(os.environ, GOMAXPROCS="2", GOMEMLIMIT="3072MiB", CGO_ENABLED="1", GOTOOLCHAIN="local",
        GOFLAGS="-mod=readonly", GOWORK=str(work / "go.work"), GOPATH=str(cache / "go-path"),
        GOMODCACHE=str(cache / "go-mod"),
        GOCACHE=str(cache / "go-build"), GOTMPDIR=str(cache / "tmp"),
        TMPDIR=str(cache / "tmp"), CGO_LDFLAGS="-L" + str(args.heart / "deps/libs" / selected["tantivy_arch"]),
        GIT_OPTIONAL_LOCKS="0", PYTHONDONTWRITEBYTECODE="1")

def run_command(argv, args, env, log, timeout):
    require(not log.exists(), "Refusing to overwrite an earlier command log")
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=args.heart, env=env, stdout=stream,
            stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
            raise
        stream.flush()
        os.fsync(stream.fileno())
    return {"argv": argv, "pid": process.pid, "exit_code": code, "log_sha256": digest(log)}

def builder():
    path = CONTROL / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    spec = importlib.util.spec_from_file_location("semantic_page_pinned_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def build(args, receipt):
    hashes = source(args)
    selected = profile(args)
    require(shutil.disk_usage(args.run).free >= 8 * 1024**3, "Eight GiB build reserve required")
    candidate_sha = digest(HERE / "page-source.json")
    save(args.run / "evidence/candidate-source-before-build.json", hashes)
    save(args.run / "evidence/toolchain.json", selected)
    env = environment(args, selected)
    work = args.run / "work"
    require(not (work / "go.work").exists(), "Fresh build workspace required")
    (work / "go.work").write_text("go " + selected["workspace_go"] + "\n\nuse " + str(args.heart)
        + "\n\nreplace " + GENPROTO + " => " + GENPROTO + " " + GENPROTO_VERSION + "\n")
    native = builder().fetch_tantivy(args.heart, selected["tantivy_arch"])
    require(native["archive_sha256"] == selected["tantivy_sha256"], "Wrong pinned Tantivy archive")
    save(args.run / "evidence/tantivy.json", native)
    receipt.update(status="BUILDING", profile=selected, candidate_sha256=candidate_sha,
        source_sha256=hashes, commands=[])
    for name, argv, timeout in [
        ("download-modules", ["go", "mod", "download"], 1200),
        ("genproto", ["go", "list", "-m", "-json", GENPROTO], 120),
    ]:
        save(args.run / "evidence/build.json", receipt)
        result = run_command(argv, args, env, args.run / "evidence" / (name + ".log"), timeout)
        receipt["commands"].append(result)
        require(result["exit_code"] == 0, "Dependency command failed: " + name)
    genproto = read(args.run / "evidence/genproto.log")
    effective = genproto.get("Replace", genproto)
    require(effective["Path"] == GENPROTO and effective["Version"] == GENPROTO_VERSION
        and effective["Sum"] == GENPROTO_SUM and effective["GoModSum"] == GENPROTO_MOD_SUM,
        "Unexpected genproto resolution")
    env["GOPROXY"] = "off"
    binary = work / "semantic-page.test"
    version = "pinkha-semantic-anchor-native-page-candidate-v1-" + candidate_sha
    flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + HEART_SHA
        + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + version
        + " -X " + PACKAGE + ".semanticPageSourceSHA=" + candidate_sha)
    receipt["status"] = "COMPILING_SERVICE"
    save(args.run / "evidence/build.json", receipt)
    command = ["go", "test", "-c", "-p", "2", "-tags", TAGS, "-ldflags", flags,
        "-o", str(binary), "./clientlibrary/service"]
    result = run_command(command, args, env, args.run / "evidence/compile-service.log", 2400)
    receipt["commands"].append(result)
    require(result["exit_code"] == 0, "Native service compile failed")
    require(all(builder().contains(binary, method.encode()) for _, method in PHASES), "Missing selected Page method")
    require(source(args) == hashes, "Source changed while compiling")
    save(args.run / "evidence/candidate-source-after-build.json", hashes)
    receipt.update(status="PASS_NATIVE_PAGE_CANDIDATE_COMPILE_ONLY", binary_sha256=digest(binary),
        runtime_version=version, actual_methods_executed=0)

def named_execution(path, method):
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
    require(all(row.get("Package") == PACKAGE for row in rows), "Unexpected test package")
    named = [r for r in rows if r.get("Test") and r["Action"] in ("run", "pass", "fail", "skip")]
    require(all(r["Test"] == method for r in named), "An unselected test executed")
    actions = [r["Action"] for r in named]
    require(actions.count("run") <= 1 and actions.count("pass") <= 1, "Repeated selected method")
    return {"method": method, "named_actions": actions, "actual_methods_executed": actions.count("run"),
        "actual_methods_passed": actions.count("pass"), "private_raw_log_sha256": digest(path)}

def named_result(path, method):
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
    require(all(row.get("Package") == PACKAGE for row in rows), "Unexpected test package")
    named = [r for r in rows if r.get("Test") and r["Action"] in ("run", "pass", "fail", "skip")]
    require({r["Test"] for r in named} == {method}, "An unselected test executed")
    require([r["Action"] for r in named] == ["run", "pass"], "Selected Page method did not pass")
    package = [r for r in rows if not r.get("Test") and r["Action"] in ("pass", "fail", "skip")]
    require(len(package) == 1 and package[0]["Action"] == "pass", "Package did not pass")
    return {"method": method, "status": "PASS", "terminal_count": 1,
        "package_elapsed": package[0].get("Elapsed"), "private_raw_log_sha256": digest(path)}

def export_safe(sequence, evidence):
    needles_file = sequence / "sensitive-needles.private"
    require(needles_file.is_file(), "No private-key redaction input")
    needles = [s.encode() for s in read(needles_file)]
    require(len(needles) == 2 and all(len(s) >= 16 for s in needles), "Incomplete private-key redaction input")
    out = evidence / "page-results"
    out.mkdir()
    rows = {}
    for path in sorted(sequence.iterdir()):
        if path.is_dir() or path.name.endswith(".private") or path.name.endswith(".jsonl"):
            continue
        require(not path.is_symlink() and path.suffix in (".json", ".pb", ".bin"), "Unreviewed account artifact")
        data = path.read_bytes()
        require(not any(n in data for n in needles), "Private key appears in an export candidate")
        shutil.copyfile(path, out / path.name)
        rows[path.name] = {"bytes": len(data), "sha256": digest(path)}
    return rows

def execute(args, receipt):
    hashes = source(args)
    selected = profile(args)
    built = read(args.run / "evidence/build.json")
    binary = args.run / "work/semantic-page.test"
    require(built["status"] == "PASS_NATIVE_PAGE_CANDIDATE_COMPILE_ONLY"
        and built["app_sha"] == args.expected_app_sha and built["profile"] == selected
        and built["source_sha256"] == hashes and built["binary_sha256"] == digest(binary)
        and built["candidate_sha256"] == digest(HERE / "page-source.json"), "Unqualified Page binary")
    # The launcher disconnects the disposable container before entering this mode.
    require(os.environ.get("PINKHA_PAGE_NETWORK_DISABLED") == "1"
        and {name for _, name in socket.if_nameindex()} == {"lo"}, "Isolated account must have only loopback networking")
    sequence = args.run / "private/account-sequence"
    sequence.mkdir(mode=0o700)
    root = sequence / "account-root"
    root.mkdir(mode=0o700)
    ownership = {"protocol": PROTOCOL, "nonce": secrets.token_hex(16), "synthetic_only": True}
    save(sequence / "ownership.json", ownership)
    token = (sequence / "ownership.json").read_text()
    env = environment(args, selected)
    env.update(PINKHA_SEMANTIC_PAGE_ROOT=str(root), PINKHA_SEMANTIC_PAGE_WORK=str(sequence),
        PINKHA_SEMANTIC_PAGE_OWNER_TOKEN=token, PINKHA_SEMANTIC_PAGE_SOURCE_SHA=built["candidate_sha256"], GOPROXY="off")
    receipt.update(status="RUNNING_NATIVE_PAGE_PHASES", binary_sha256=built["binary_sha256"],
        candidate_sha256=built["candidate_sha256"], profile=selected, phases=[], attempts=[], actual_methods_passed=0)
    reports = []
    for phase, method in PHASES:
        env["PINKHA_SEMANTIC_PAGE_PHASE"] = phase
        save(args.run / "evidence/page-acceptance.json", receipt)
        command = ["go", "tool", "test2json", "-t", "-p", PACKAGE, str(binary),
            "-test.v=test2json", "-test.run=^" + method + "$", "-test.timeout=240s", "-test.count=1"]
        log = sequence / (phase + ".jsonl")
        result = run_command(command, args, env, log, 300)
        observed = named_execution(log, method)
        receipt["attempts"].append(dict(observed, phase=phase, exit_code=result["exit_code"],
            test2json_pid=result["pid"]))
        receipt["actual_methods_executed"] += observed["actual_methods_executed"]
        receipt["actual_methods_passed"] += observed["actual_methods_passed"]
        save(args.run / "evidence/page-acceptance.json", receipt)
        require(result["exit_code"] == 0, "Selected native Page phase failed: " + phase)
        named = named_result(log, method)
        report = read(sequence / (phase + ".json"))
        require(report["protocol"] == PROTOCOL and report["phase"] == phase and report["nonce"] == ownership["nonce"]
            and report["source_manifest_sha256"] == built["candidate_sha256"]
            and report["runtime_version"] == built["runtime_version"] and report["heart_sha"] == HEART_SHA
            and report["test_passed"] and report["closed"] and report["account_stop_verified"],
            "Incomplete native phase report")
        require(source(args) == hashes and digest(binary) == built["binary_sha256"], "Source/binary changed during phase")
        receipt["phases"].append(dict(named, phase=phase, pid=report["pid"], phase_report_sha256=digest(sequence / (phase + ".json"))))
        reports.append(report)
        save(args.run / "evidence/page-acceptance.json", receipt)
    first, second = reports
    require(first["pid"] == first["create_pid"] == second["create_pid"] and first["pid"] != second["pid"],
        "Reopen did not execute in a different process")
    for field in ("account_id", "space_id", "object_id", "block_id", "anchor_id", "native_change_id",
                  "native_change_sha256", "source_manifest_sha256", "state_sha256"):
        require(first[field] == second[field], "Reopen identity or native stored payload differs")
    require(first["rpc_calls"]["PinkhaSemanticAnchorCapture"] == 4
        and second["rpc_calls"]["PinkhaSemanticAnchorCapture"] == 1, "Wrong selected native capture count")
    receipt.update(status="PASS_NATIVE_PAGE_CAPTURE_AND_COLD_REOPEN", actual_methods_executed=2, actual_methods_passed=2,
        distinct_native_pids=[first["pid"], second["pid"]], artifacts=export_safe(sequence, args.run / "evidence"),
        current_source_sha256=hashes, native_service_acceptance="PASS", native_page_apply="PASS",
        process_reopen="PASS", public_http="NOT_RUN", apple="NOT_RUN", mounted_editor="NOT_RUN")

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("mode", choices=("prepare", "verify-source", "build", "execute"))
    parser.add_argument("--heart", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--cache-root", type=Path, help="Stable absolute task cache; defaults to RUN/cache")
    args = parser.parse_args()
    os.umask(0o077)
    args.heart, args.run = args.heart.resolve(), args.run.resolve()
    require(re.fullmatch("[0-9a-f]{40}", args.expected_app_sha), "Exact app SHA required")
    require(len({CONTROL, args.heart, args.run}) == 3 and not args.run.is_relative_to(CONTROL)
        and not args.run.is_relative_to(args.heart), "Separate controller/native/work paths required")
    if args.mode in ("prepare", "verify-source"):
        hashes = prepare(args) if args.mode == "prepare" else source(args)
        print(json.dumps({"status": "PASS_EXACT_154_SOURCE", "count": len(hashes),
            "candidate_sha256": digest(HERE / "page-source.json"), "methods_executed": 0}))
        return 0
    target = args.run / "evidence" / ("build.json" if args.mode == "build" else "page-acceptance.json")
    require(not target.exists(), "Existing build/execution receipt must not be overwritten")
    receipt = {"status": "PROBE_UNKNOWN", "app_sha": args.expected_app_sha, "heart_sha": HEART_SHA,
        "app_capability": "OFF", "actual_methods_executed": 0, "previous_methods_rerun": 0,
        "started_at": datetime.now(timezone.utc).isoformat()}
    code = 1
    try:
        (build if args.mode == "build" else execute)(args, receipt)
        code = 0
    except BaseException as exc:
        receipt.update(status="FAIL_" + args.mode.upper(), error_type=type(exc).__name__, error=str(exc))
        # Native stdout stays in private logs; errors here are controller labels.
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(target, receipt)
    print(json.dumps({key: receipt.get(key) for key in ("status", "actual_methods_executed", "app_capability")}))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
