#!/usr/bin/env python3
"""Generate pinned ClientCommands RPCs, then prove their native byte boundary.

Generation runs on the Ubuntu host because the official pinned protoc is glibc.
Native tests run separately in the existing pinned musl/Go/Tantivy container.
No App binding, account mutation, generated Swift, release or source upload.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import signal
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import run_account_lifecycle as process_control
import run_native_operations as registry
import run_native_registration as closure
from authorized_read import profile as authorized
from authorized_read import account as authorized_account

HEART = registry.HEART_SHA
VERSION = "go version go1.26.5 linux/amd64"
REQUIRED = {
    "TestPinkhaTorahRPCSchemaAndOpaqueRequestRoundTrip",
    "TestPinkhaTorahRPCRejectsUnknownContractBeforeNativeAuthority",
    "TestPinkhaTorahRPCPreservesCommittedReceiptAndJoinedIssues",
    "TestPinkhaTorahRPCSeparatesRetryCollisionAndRemoteVariants",
    "TestPinkhaTorahRPCBoundsNeverTruncateSuccessfulHistory",
    "TestPinkhaTorahRPCDoesNotExpandExternalScope",
    "TestPinkhaTorahGeneratedByteBoundaryRejectsWithoutAccount",
}
PACKAGES = {"github.com/anyproto/anytype-heart/core", "github.com/anyproto/anytype-heart/clientlibrary/service"}
REQUIRED_PAIRS = {(name, "github.com/anyproto/anytype-heart/" +
                   ("clientlibrary/service" if name == "TestPinkhaTorahGeneratedByteBoundaryRejectsWithoutAccount" else "core"))
                  for name in REQUIRED}
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
PROTO_MAP = ",".join([
    "Mgoogle/protobuf/timestamp.proto=github.com/gogo/protobuf/types",
    "Mgoogle/protobuf/struct.proto=github.com/gogo/protobuf/types",
    "Mgoogle/protobuf/descriptor.proto=github.com/gogo/protobuf/protoc-gen-gogo/descriptor",
    "Mpkg/lib/pb/model/protos/models.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
    "Mpkg/lib/pb/model/protos/export_report.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
    "Mpkg/lib/pb/model/protos/localstore.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
    "Mpb/protos/commands.proto=github.com/anyproto/anytype-heart/pb",
    "Mpb/protos/events.proto=github.com/anyproto/anytype-heart/pb",
])


def require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "Expected regular nonsymlink source")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def relative(value: str) -> Path:
    path = PurePosixPath(value)
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and ":" not in value, "Unsafe inventory path")
    return Path(*path.parts)


def source_inputs(control: Path, rpc: Path) -> tuple[dict, dict]:
    manifest = json.loads((rpc / "heart-rpc.json").read_text())
    require(manifest["heart_sha"] == HEART and manifest["protocol_version"] == 1, "Wrong native RPC contract")
    require(digest(rpc / "heart-rpc.patch") == manifest["patch_sha256"], "RPC schema patch differs")
    base = control / "Tools/TorahNativeOperations"
    require(digest(base / "heart-registration.json") == manifest["registration_inventory_sha256"]
            and digest(base / "heart-registration.patch") == manifest["registration_patch_sha256"], "Private registry source differs")
    inventory = json.loads((base / "heart-registration.json").read_text())
    actual = {p.relative_to(rpc / "overlay").as_posix(): digest(p) for p in (rpc / "overlay").rglob("*.go")}
    require(actual == manifest["overlay"], "RPC native overlay differs from exact manifest")
    private = set(inventory["tracked"]) | set(inventory["overlay"])
    rpc_paths = set(manifest["tracked"]) | set(actual) | set(manifest["generation"]["generated_paths"])
    require(not private.intersection(rpc_paths), "RPC/native registry path collision")
    for path in rpc_paths:
        relative(path)
    return manifest, inventory


def validate_test_events(events: list[dict], success: bool) -> dict:
    tests = [event for event in events if event.get("Test") and event.get("Action") in {"pass", "fail", "skip"}]
    passed = {(event["Test"], event.get("Package")) for event in tests if event["Action"] == "pass"}
    packages = {event.get("Package") for event in events if not event.get("Test") and event.get("Action") == "pass"}
    require(success and not any(event.get("Action") in {"fail", "skip"} for event in events), "Native RPC execution failed/skipped")
    require(REQUIRED_PAIRS <= passed and PACKAGES <= packages, "Missing actual generated RPC acceptance")
    return {"pass": len(tests), "top_level_pass": sum("/" not in event["Test"] for event in tests),
            "subcase_pass": sum("/" in event["Test"] for event in tests), "fail": 0, "skip": 0,
            "required_passed": sorted(REQUIRED)}


def proto_closure(heart: Path, include: Path) -> dict[str, str]:
    pending = ["pb/protos/commands.proto", "pb/protos/service/service.proto"]
    inputs = {}
    while pending:
        name = pending.pop()
        if name in inputs:
            continue
        path = (include if name.startswith("google/protobuf/") else heart) / relative(name)
        inputs[name] = digest(path)
        pending.extend(re.findall(r'^\s*import\s+(?:public\s+|weak\s+)?"([^"\n]+)"\s*;', path.read_text(), re.M))
    return inputs


def verify_composed_source(heart: Path, expected: dict, tracked: set[str], modules: dict) -> None:
    require(git(heart, "rev-parse", "HEAD") == HEART, "Heart revision changed")
    require({name: digest(heart / relative(name)) for name in expected} == expected, "Native source changed")
    require(set(git(heart, "diff", "--name-only", "HEAD").splitlines()) == tracked, "Unexpected native tracked mutation")
    require(set(git(heart, "ls-files", "--others", "--exclude-standard").splitlines()) <= set(expected) - tracked,
            "Unexpected native source file")
    require({name: digest(heart / name) for name in modules} == modules, "Go module pin changed")


def generate(args, receipt, run, *, protoc_profile="linux-amd64") -> None:
    control, heart, work, evidence = args.control, args.heart_source, args.work, args.evidence
    rpc = control / "Tools/TorahNativeOperations/rpc"
    manifest, inventory = source_inputs(control, rpc)
    extension = (authorized.read_sources(control, manifest, inventory)
                 if getattr(args, "rpc_profile", "retained-v1") == authorized.PROFILE else None)
    compiler = manifest["generation"]["protoc"]
    if protoc_profile == "darwin-universal":
        from authorized_read.apple_toolchain import PROTOC
        require(extension is not None, "Apple generator is an explicit authorized-read candidate only")
        compiler = PROTOC
    else:
        require(protoc_profile == "linux-amd64", "Unknown pinned protobuf compiler profile")
    require(not git(heart, "status", "--porcelain"), "Fresh clean pinned Heart checkout required")
    work.mkdir(parents=True, exist_ok=False)
    modules = {name: digest(heart / name) for name in ["go.mod", "go.sum"]}
    base = {}
    registry.apply_sources(heart, base)
    expected = dict(base["source_sha256"])
    tracked = set(inventory["tracked"]) | set(manifest["tracked"]) | set(manifest["generation"]["generated_paths"])
    for name, hashes in manifest["tracked"].items():
        require(digest(heart / name) == hashes["before_sha256"], "RPC schema input changed")
    run(["git", "apply", "--check", str(rpc / "heart-rpc.patch")], "schema-check", heart, os.environ.copy())
    run(["git", "apply", str(rpc / "heart-rpc.patch")], "schema-apply", heart, os.environ.copy())
    for name, hashes in manifest["tracked"].items():
        require(digest(heart / name) == hashes["after_sha256"], "RPC schema output differs")
        expected[name] = hashes["after_sha256"]
    for name, sha in manifest["overlay"].items():
        target = heart / relative(name)
        require(not target.exists(), "RPC overlay would replace existing native source")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rpc / "overlay" / name, target)
        require(digest(target) == sha, "RPC overlay copy differs")
        expected[name] = sha
    if extension:
        authorized.apply_sources(extension, heart, expected, tracked, run)
    archive = work / "protoc.zip"
    with urllib.request.urlopen(compiler["url"], timeout=60) as response:
        data = response.read(5 * 1024 * 1024)
    require(hashlib.sha256(data).hexdigest() == compiler["zip_sha256"], "Official protoc archive differs")
    archive.write_bytes(data)
    tool = work / "protoc"
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            path = relative(entry.filename)
            require(entry.filename == "bin/protoc" or entry.filename.startswith("include/") or entry.filename == "readme.txt",
                    "Unexpected protoc archive member")
            require((entry.external_attr >> 16) & 0o170000 != 0o120000, "Symlink in protoc archive")
            target = tool / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(entry))
    protoc = tool / "bin/protoc"
    protoc.chmod(0o755)
    require(digest(protoc) == compiler["binary_sha256"], "Pinned protoc executable differs")
    require(subprocess.check_output([str(protoc), "--version"], text=True).strip() == compiler["version"], "Wrong protoc version")
    bin_dir = work / "bin"
    bin_dir.mkdir()
    env = dict(os.environ, GOTOOLCHAIN="local", GOWORK="off", CGO_ENABLED="0", GOMAXPROCS="2", GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly")
    run(["go", "mod", "download", "github.com/gogo/protobuf"], "gogo-download", heart, env)
    run(["go", "list", "-m", "-json", "github.com/gogo/protobuf"], "gogo-selection", heart, env)
    selected = json.loads((evidence / "gogo-selection.log").read_text())
    effective = selected.get("Replace", {})
    gogo = manifest["generation"]["gogo"]
    require(selected.get("Path") == gogo["module"] and effective.get("Path") == gogo["replace_module"]
            and effective.get("Version") == gogo["version"] and effective.get("Sum") == gogo["sum"]
            and effective.get("GoModSum") == gogo["go_mod_sum"], "Gogo generator module differs from pinned Heart")
    run(["go", "build", "-p", "1", "-o", str(bin_dir / "protoc-gen-gogofaster"), "github.com/gogo/protobuf/protoc-gen-gogofaster"],
        "build-gogo", heart, env)
    env.update(manifest["generation"]["environment"])
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    inputs = proto_closure(heart, tool / "include")
    generated = {}
    generation_jobs = [
        ("messages", "pb/protos/commands.proto", "", {}, "pb/commands.pb.go"),
        ("grpc", "pb/protos/service/service.proto", ",plugins=grpc", {"GOGO_GRPC_SERVER_METHOD_NO_ERROR": "1"}, "pb/service/service.pb.go"),
        ("gomobile", "pb/protos/service/service.proto", ",plugins=gomobile", {"GOGO_GOMOBILE_WITH_CONTEXT": "1"}, "clientlibrary/service/service.pb.go"),
    ]
    proto_map = PROTO_MAP
    if extension:
        generation_jobs.insert(1, ("authorized-operation-read", authorized.PROTO, "", {}, authorized.GENERATED))
        proto_map += ",M" + authorized.PROTO + "=github.com/anyproto/anytype-heart/pb"
    for name, source, plugins, flags, target in generation_jobs:
        destination = work / ("generated-" + name)
        destination.mkdir()
        run([str(protoc), "-I", str(heart), "-I", str(tool / "include"),
             "--gogofaster_out=" + proto_map + plugins + ":" + str(destination), source], "generate-" + name, heart, dict(env, **flags))
        files = list(destination.rglob("*.pb.go"))
        require(len(files) == 1 and files[0].name == Path(target).name, "Unexpected generated output set")
        generated[target] = digest(files[0])
        shutil.copyfile(files[0], heart / target)
        expected[target] = generated[target]
    require(inputs == proto_closure(heart, tool / "include"), "Protobuf inputs changed during generation")
    verify_composed_source(heart, expected, tracked, modules)
    receipt.update(status="PASS_PINNED_RPC_GENERATION", rpc_manifest_sha256=digest(rpc / "heart-rpc.json"),
                   schema_patch_sha256=manifest["patch_sha256"], registry=base,
                   compiler={"protoc": compiler, "generator_module": gogo,
                             "generator_binary_sha256": digest(bin_dir / "protoc-gen-gogofaster")},
                   protobuf_inputs_sha256=inputs, generated_sha256=generated, source_sha256=expected,
                   tracked_paths=sorted(tracked), module_sha256=modules)
    if extension:
        receipt.update(authorized_read_manifest_sha256=extension["manifest_sha256"],
                       native_read_inventory_sha256=extension["native_inventory_sha256"],
                       authorized_schema_patch_sha256=extension["manifest"]["patch_sha256"])


def native_tests(args, receipt, run) -> None:
    control, heart, work, evidence = args.control, args.heart_source, args.work, args.evidence
    rpc = control / "Tools/TorahNativeOperations/rpc"
    manifest, inventory = source_inputs(control, rpc)
    extension = (authorized.read_sources(control, manifest, inventory)
                 if getattr(args, "rpc_profile", "retained-v1") == authorized.PROFILE else None)
    previous = json.loads((evidence / "generation-receipt.json").read_text())
    require(previous["status"] == "PASS_PINNED_RPC_GENERATION" and previous["app_sha"] == args.expected_app_sha
            and previous["run_id"] == receipt["run_id"] and previous["run_attempt"] == receipt["run_attempt"]
            and previous["rpc_manifest_sha256"] == digest(rpc / "heart-rpc.json"), "Generation evidence does not match this run/source")
    if extension:
        require(previous.get("authorized_read_manifest_sha256") == extension["manifest_sha256"]
                and previous.get("native_read_inventory_sha256") == extension["native_inventory_sha256"],
                "Authorized read generation source differs")
    else:
        require(not previous.get("authorized_read_manifest_sha256"), "Candidate generation cannot qualify retained RPC")
    verify_composed_source(heart, previous["source_sha256"], set(previous["tracked_paths"]), previous["module_sha256"])
    helper = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    spec = importlib.util.spec_from_file_location("t2_rpc_tantivy_helper", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = module.fetch_tantivy(heart, "linux-amd64-musl")
    require(native["archive_sha256"] == closure.TANTIVY_SHA, "Wrong pinned Tantivy")
    gowork = work / "native.go.work"
    require(not gowork.exists(), "Fresh native-stage work required")
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + closure.GENPROTO_PATH + " => "
                      + closure.GENPROTO_PATH + " " + closure.GENPROTO_VERSION + "\n")
    env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2",
               GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly", CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
    run(["go", "mod", "download"], "native-module-download", heart, env)
    env["GOPROXY"] = "off"
    run(["go", "list", "-m", "-json", closure.GENPROTO_PATH], "native-genproto-selection", heart, env)
    selected = json.loads((evidence / "native-genproto-selection.log").read_text())
    effective = selected.get("Replace", selected)
    require(effective.get("Path") == closure.GENPROTO_PATH and effective.get("Version") == closure.GENPROTO_VERSION
            and effective.get("Sum") == closure.GENPROTO_SUM and effective.get("GoModSum") == closure.GENPROTO_MOD_SUM,
            "Wrong pinned native genproto closure")
    new_go = [str(heart / name) for name in manifest["overlay"]]
    if extension:
        new_go += [str(heart / name) for name in extension["paths"] if name.endswith(".go")]
    require(not subprocess.check_output(["gofmt", "-l", *new_go], text=True).strip(), "RPC source is not formatted")
    receipt.update(generation_receipt_sha256=digest(evidence / "generation-receipt.json"),
                   rpc_manifest_sha256=digest(rpc / "heart-rpc.json"), generated_sha256=previous["generated_sha256"],
                   native_source_sha256=previous["source_sha256"], tantivy=native,
                   genproto={"Path": effective["Path"], "Version": effective["Version"], "Sum": effective["Sum"], "GoModSum": effective["GoModSum"]},
                   grpc_registration_package="NOT_RUN_IN_THIS_STAGE")
    if args.stage == "account":
        require(extension is not None, "Account read proof requires explicit candidate profile")
        authorized_account.execute(args, receipt, run, previous, env, lambda: verify_composed_source(
            heart, previous["source_sha256"], set(previous["tracked_paths"]), previous["module_sha256"]))
        return
    run(["go", "test", "-p", "1", "-count=1", "-run", "^$", "./pb/service"], "generated-grpc-compile", heart, env)
    receipt["grpc_registration_package"] = "COMPILED_NO_TESTS_CLAIMED"
    pattern = authorized.TEST_PATTERN if extension else "^TestPinkhaTorah(RPC|GeneratedByte)"
    packages = (["./" + name for name in authorized.TOP_LEVEL] if extension else ["./core", "./clientlibrary/service"])
    command = ["go", "test", "-p", "1", "-parallel", "1", "-count=1", "-timeout=240s", "-json", "-tags", TAGS,
               "-ldflags=-extldflags=-static", "-run", pattern, *packages]
    run(command, "native-rpc-tests", heart, env, 1800)
    lines = (evidence / "native-rpc-tests.log").read_text().splitlines()
    events = []
    for line in lines:
        if line.startswith("{"):
            events.append(json.loads(line))
        else:
            require(not line.strip() or line.startswith("go: downloading "), "Unexpected non-JSON test output")
    counts = (authorized.validate_test_events if extension else validate_test_events)(events, True)
    verify_composed_source(heart, previous["source_sha256"], set(previous["tracked_paths"]), previous["module_sha256"])
    receipt.update(status="PASS_AUTHORIZED_OPERATION_READ_NATIVE_BOUNDARY" if extension else "PASS_GENERATED_NATIVE_RPC_BOUNDARY", actual_counts=counts,
                   native_test_log_sha256=digest(evidence / "native-rpc-tests.log"))
    if extension:
        receipt.update(authorized_read_manifest_sha256=extension["manifest_sha256"],
                       native_read_inventory_sha256=extension["native_inventory_sha256"],
                       unchanged_prior_tests_executed=0)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["generate", "test", "account"])
    for name in ["control", "heart-source", "work", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--rpc-profile", choices=["retained-v1", authorized.PROFILE], default="retained-v1")
    args = parser.parse_args(argv)
    for name in ["control", "heart_source", "work", "evidence"]:
        setattr(args, name, getattr(args, name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt_path = args.evidence / ("generation-receipt.json" if args.stage == "generate" else "receipt.json")
    require(not receipt_path.exists(), "Fresh source-bound receipt required")
    receipt = {"status": "NOT_RUN_PREFLIGHT", "stage": args.stage, "rpc_profile": args.rpc_profile, "app_sha": args.expected_app_sha, "heart_sha": HEART,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"), "commands": [], "started_at": datetime.now(timezone.utc).isoformat(),
               "scope": "generated protocol/mapping and native no-account byte boundary; not account wire or two App clients",
               "account_wire_acceptance": "NOT_RUN", "app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN"}
    previous_handlers = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}
    cancellation_requested = False
    def cancel(number, frame):
        nonlocal cancellation_requested
        # Repeated cancellation must not interrupt owned-group cleanup or the
        # final durable receipt after the first signal entered that path.
        if not cancellation_requested:
            cancellation_requested = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous_handlers:
        signal.signal(number, cancel)
    result = 1
    def run(command, name, cwd, env, timeout=900):
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}
        receipt["commands"].append(entry)
        process_control.write_json(receipt_path, receipt)
        try:
            entry["pid"] = process_control.run_process(list(map(str, command)), cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as exc:
            entry["status"] = "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            process_control.write_json(receipt_path, receipt)
    try:
        require(args.stage != "account" or args.rpc_profile == authorized.PROFILE, "Account proof requires explicit authorized-read profile")
        require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux amd64 runner required")
        require(len({args.control, args.heart_source, args.work, args.evidence}) == 4, "Separate source/work/evidence paths required")
        require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha) is not None, "Exact source SHA required")
        require(git(args.control, "rev-parse", "HEAD") == args.expected_app_sha and not git(args.control, "status", "--porcelain"), "Control source changed")
        require(git(args.heart_source, "rev-parse", "HEAD") == HEART, "Wrong Heart checkout")
        require(shutil.disk_usage(args.work.parent).free >= 8 * 1024**3, "Disk reserve below 8 GiB")
        require(subprocess.check_output(["go", "version"], text=True).strip() == VERSION, "Pinned Go 1.26.5 required")
        (generate if args.stage == "generate" else native_tests)(args, receipt, run)
        require(git(args.control, "rev-parse", "HEAD") == args.expected_app_sha and not git(args.control, "status", "--porcelain"), "Control changed during execution")
        result = 0
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error=type(exc).__name__)
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    finally:
        def finish():
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            process_control.write_json(receipt_path, receipt)
        try:
            try:
                finish()
            except KeyboardInterrupt:
                # Cancellation can arrive after all commands finished, including
                # after an initial receipt write. Preserve command outcomes but
                # durably replace the overall status before returning failure.
                result = 1
                receipt.update(status="CANCELLED", error="KeyboardInterrupt")
                finish()
        finally:
            for number, previous in previous_handlers.items():
                signal.signal(number, previous)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
