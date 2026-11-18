#!/usr/bin/env python3
"""Run source-bound T2 native transport or private registry adapter acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

HEART_SHA = "d98420b1113536afd08cde6de9a5816f6d27ffff"
GO_VERSION = "go1.26.5"
PACKAGES = {
    "component": ["./core/block/editor/torahops"],
    "registration": ["./pkg/lib/pinkha/torahopscontract", "./pkg/lib/core/smartblock",
                     "./core/domain", "./space/spacecore/typeprovider", "./core/block/restriction",
                     "./core/block/object/objectcache", "./core/block/object/treemanager",
                     "./core/block/source/sourceimpl", "./core/block/editor", "./core"],
}
REQUIRED = {
    "component": {"TestNativeTwoProcessTreeSync", "TestNativeHostRejectsUnboundAuthorityAndInvalidHistory",
                  "TestNativeCurrentReadAuthority", "TestNativeCurrentWriteAuthority",
                  "TestNativeAccountBoundaryACLUsesCurrentSignedMembership",
                  "TestNativeLockedConstructorRecoversWhileCallerOwnsTree",
                  "TestNativeReceivingValidatorPreservesSignedHistory"},
    "registration": {"TestPrivateRootIdentityAndSpaceBinding", "TestPrivateRootRejectsNoncanonicalEnvelope",
                     "TestPinkhaPrivateTypeAllocationAndIndexPolicy", "TestPinkhaTorahOperationsUniqueKeyIsDedicated",
                     "TestPinkhaPrivateRegistryRequiresCanonicalSpaceRoot", "TestPinkhaPrivateRegistryRejectsGenericEnumForgery",
                     "TestPinkhaPrivateCachedTypeStillRequiresReceivingSpace", "TestPinkhaPrivateHostDeniesGenericObjectMutations",
                     "TestPinkhaPrivateCreationIsCanonicalAndLazy", "TestPinkhaPrivateCreationRefusesForeignOrPopulatedPayload",
                     "TestPinkhaPrivateSourceOwnsNoGenericBlockOrStorePath", "TestPinkhaPrivateSourceRejectsForeignReceivingSpace",
                     "TestPinkhaPrivateTreeManagerRejectsGenericImportBeforeStorage",
                     "TestPinkhaPrivateTreeManagerPreservesLegacyPutTreeBoundary",
                     "TestPinkhaPrivateFactoryNativeStorageAndTargetLifecycle",
                     "TestPinkhaNativeHandlerRejectsVersionBeforeAccountAccess",
                     "TestPinkhaNativeHandlerRequiresRunningAccount",
                     "TestPinkhaNativeReadShapeAndCancellationBeforeAccountAccess"},
}
MODULE = "github.com/anyproto/anytype-heart"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(value: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in value or ":" in value:
        raise ValueError("unsafe source inventory path")
    return Path(*path.parts)


def apply_sources(heart: Path, receipt: dict) -> list[Path]:
    control = Path(__file__).resolve().parent
    inventory_path = control / "heart-registration.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    patch = control / "heart-registration.patch"
    if inventory.get("heart_sha") != HEART_SHA or digest(patch) != inventory.get("patch_sha256"):
        raise ValueError("private registry patch identity mismatch")
    overlay = control / "overlay"
    actual = {p.relative_to(overlay).as_posix(): p for p in overlay.rglob("*.go")}
    if set(actual) != set(inventory["overlay"]):
        raise ValueError("unexpected or missing native source overlay")
    aggregate = hashlib.sha256()
    for name, expected in sorted(inventory["overlay"].items()):
        relative = safe_relative(name)
        file = actual[name]
        if file.is_symlink() or digest(file) != expected:
            raise ValueError("native overlay content differs: " + name)
        aggregate.update(name.encode() + b"\0" + file.read_bytes())
        target = heart / relative
        if target.exists() and (target.is_symlink() or digest(target) != expected):
            raise ValueError("refusing to replace existing native source: " + name)
    for name, hashes in inventory["tracked"].items():
        target = heart / safe_relative(name)
        if not target.is_file() or digest(target) != hashes["before_sha256"]:
            raise ValueError("native base source differs: " + name)
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=heart, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=heart, check=True)
    for name, file in actual.items():
        target = heart / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(file, target)
    receipt["inventory_sha256"] = digest(inventory_path)
    receipt["patch_sha256"] = digest(patch)
    receipt["overlay_sha256"] = aggregate.hexdigest()
    expected_hashes = dict(inventory["overlay"])
    expected_hashes.update({name: hashes["after_sha256"] for name, hashes in inventory["tracked"].items()})
    actual_hashes = {name: digest(heart / name) for name in expected_hashes}
    if actual_hashes != expected_hashes:
        raise ValueError("applied native source differs from inventory")
    changed = set(output(["git", "diff", "HEAD", "--name-only"], heart).splitlines())
    if changed != set(inventory["tracked"]):
        raise ValueError("unexpected tracked Heart changes after patch")
    receipt["source_sha256"] = actual_hashes
    return [heart / name for name in sorted(expected_hashes)]


def passes_suite(events: list[dict], suite: str, returncode: int) -> bool:
    passed = {e.get("Test") for e in events if e.get("Action") == "pass" and e.get("Test")}
    package_pass = {e.get("Package") for e in events if e.get("Action") == "pass" and not e.get("Test")}
    expected_packages = {MODULE + p[1:] for p in PACKAGES[suite]}
    failed = any(e.get("Action") == "fail" for e in events)
    skipped_registry = suite == "registration" and any(e.get("Action") == "skip" for e in events)
    return returncode == 0 and not failed and not skipped_registry and expected_packages <= package_pass and REQUIRED[suite] <= passed


def output(command: list[str], cwd: Path, env: dict | None = None) -> str:
    return subprocess.check_output(command, cwd=cwd, env=env, text=True, encoding="utf-8").strip()


def run_bounded(command: list[str], cwd: Path, env: dict, log, seconds: int) -> int:
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=os.name != "nt")
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=log, stderr=subprocess.STDOUT, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heart-source", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--suite", choices=sorted(PACKAGES), default="component")
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[2]
    heart, evidence = args.heart_source.resolve(), args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 3,
        "status": "NOT_RUN",
        "heart_sha_expected": HEART_SHA,
        "app_sha_expected": args.expected_app_sha,
        "platform": platform.platform(),
        "suite": args.suite,
        "private_registry_adapter": "NOT_RUN",
        "unknown_client_preservation": "NOT_RUN",
        "target_lifecycle_scope": "NON_ATOMIC_NATIVE_ADAPTER_ONLY",
        "evidence_scope": ("native StoreState / any-store component and two-process signed AnySync loopback transport"
                           if args.suite == "component" else "private native registry/source/factory adapter; controlled target State boundary"),
        "middleware_acceptance": "NOT_RUN",
        "two_client_transport_acceptance": "NOT_RUN",
        "full_t2_acceptance": "NOT_RUN",
        "ios_acceptance": "NOT_RUN",
        "native_host_rpc_acl_hidden_lifecycle": "NOT_BOUND_TO_APP",
        "native_signed_tree_contract": "NOT_RUN",
        "current_local_read_authority": "NOT_RUN",
        "current_local_write_authority": "NOT_RUN",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
    }
    started = time.time()
    code = 1
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha):
            raise ValueError("expected app SHA must be a full immutable commit")
        receipt["app_sha_actual"] = output(["git", "rev-parse", "HEAD"], app)
        receipt["heart_sha_actual"] = output(["git", "rev-parse", "HEAD"], heart)
        if receipt["app_sha_actual"] != args.expected_app_sha or receipt["heart_sha_actual"] != HEART_SHA:
            raise ValueError("source SHA mismatch")
        for source in (app, heart):
            if output(["git", "diff", "HEAD", "--name-only"], source):
                raise ValueError(f"tracked source modifications in {source}")
        receipt["go_mod_sha256"] = digest(heart / "go.mod")
        receipt["go_sum_sha256"] = digest(heart / "go.sum")
        applied = apply_sources(heart, receipt)
        go = shutil.which("go")
        if not go:
            raise ValueError("Go executable unavailable")
        env = os.environ.copy()
        env.update(GOMAXPROCS="2", GOMEMLIMIT="2048MiB", GOTOOLCHAIN="local", GOFLAGS="-mod=readonly")
        receipt["go_version"] = output([go, "version"], heart, env)
        if receipt["go_version"].split()[2] != GO_VERSION:
            raise ValueError("unexpected Go toolchain")
        gofmt = Path(output([go, "env", "GOROOT"], heart, env)) / "bin" / ("gofmt.exe" if os.name == "nt" else "gofmt")
        unformatted = output([str(gofmt), "-l", *map(str, applied)], heart, env)
        if unformatted:
            raise ValueError("native overlay formatting differs: " + unformatted)
        command = [go, "test", "-p", "1", "-count=1", "-timeout=240s", "-json"]
        if args.suite == "registration":
            command += ["-run", "^(TestPinkha|TestPrivate)", "-ldflags=-extldflags=-static"]
        command += PACKAGES[args.suite]
        receipt["command"] = command
        receipt["status"] = "RUNNING"
        with (evidence / "go-test.jsonl").open("w", encoding="utf-8", newline="") as log:
            code = run_bounded(command, heart, env, log, seconds=2100 if args.suite == "registration" else 900)
        events = []
        for line in (evidence / "go-test.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # compiler/download messages remain verbatim in the log
        receipt["passed_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "pass" and e.get("Test"))
        receipt["failed_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "fail" and e.get("Test"))
        receipt["skipped_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "skip" and e.get("Test"))
        receipt["passed_test_ids"] = sorted(e["Package"] + "::" + e["Test"] for e in events if e.get("Action") == "pass" and e.get("Test"))
        receipt["package_passes"] = sorted(e["Package"] for e in events if e.get("Action") == "pass" and not e.get("Test"))
        if passes_suite(events, args.suite, code):
            if args.suite == "component":
                receipt["status"] = "PASS_NATIVE_COMPONENT_AND_LOOPBACK_TRANSPORT"
                receipt["two_client_transport_acceptance"] = "PASS_ISOLATED_LOOPBACK_PROTOCOL_ONLY"
                receipt["native_signed_tree_contract"] = "PASS_ISOLATED_NATIVE_HOST"
                receipt["current_local_read_authority"] = "PASS_CURRENT_LOCALLY_VERIFIED_ACL"
                receipt["current_local_write_authority"] = "PASS_CURRENT_ACL_AT_NATIVE_PREPARATION"
            else:
                receipt["status"] = "PASS_PRIVATE_NATIVE_REGISTRY_ADAPTER"
                receipt["private_registry_adapter"] = "PASS_FACTORY_SOURCE_STORAGE_BOUNDARIES"
        else:
            receipt["status"] = "FAIL"
            code = code or 1
        for name, expected in receipt["source_sha256"].items():
            if digest(heart / name) != expected:
                raise ValueError("compiled source mutated during tests: " + name)
        if digest(heart / "go.mod") != receipt["go_mod_sha256"] or digest(heart / "go.sum") != receipt["go_sum_sha256"]:
            raise ValueError("pinned modules mutated during tests")
        receipt["returncode"] = code
    except Exception as exc:
        code = 1
        receipt["status"] = "FAIL" if receipt.get("command") else "NOT_RUN_PREFLIGHT_FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["returncode"] = 1
        print(receipt["error"], file=sys.stderr)
    finally:
        receipt["elapsed_seconds"] = round(time.time() - started, 3)
        receipt["evidence_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(evidence.glob("*.jsonl"))
        }
        (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
