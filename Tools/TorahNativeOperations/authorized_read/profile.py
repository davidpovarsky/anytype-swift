"""Exact additive Heart authorized-read source and focused execution profile.

The retained registry/RPC sources and default runner profile are immutable inputs.
This module neither selects a default runtime nor advertises a capability.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

PROFILE = "authorized-operation-read-v1"
CONTRACT = "pinkha-authorized-operation-read-v1"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
PROTO = "pb/protos/pinkha_authorized_operation_read.proto"
GENERATED = "pb/pinkha_authorized_operation_read.pb.go"
PACKAGE_ROOT = "github.com/anyproto/anytype-heart/"

TOP_LEVEL = {
    "core/block/editor/torahops": {
        "TestNativeAuthorizedOperationReadCompleteExactConflictClosure",
        "TestNativeAuthorizedOperationReadRetainsNonLiveHistoryAndLocalAbsence",
        "TestNativeAuthorizedOperationReadCurrentACLAndLifetimeFences",
        "TestNativeAuthorizedOperationReadRejectsChangedCandidateClosure",
        "TestNativeAuthorizedOperationReadReopensExactSignedReceipts",
        "TestNativeAuthorizedOperationReadRejectsForgedProjectionProvenance",
        "TestNativeAuthorizedOperationReadBoundsNeverReturnPartialClosure",
        "TestNativeAuthorizedOperationReadInvalidShapeBeforeAuthority",
    },
    "core/block/editor/torahopsobject": {
        "TestPinkhaAuthorizedOperationTargetsAcquireOnceAndInStableOrder",
        "TestPinkhaAuthorizedOperationTargetsRejectChangedEligibility",
        "TestPinkhaAuthorizedOperationTargetsRejectMalformedRequestedGraph",
        "TestPinkhaAuthorizedOperationTargetsIgnoreUnrelatedOrphanHistory",
        "TestPinkhaAuthorizedOperationTargetsRetainGenesisDeletionAuthority",
        "TestPinkhaAuthorizedOperationTargetsCancellationAndLoadFailure",
        "TestPinkhaAuthorizedOperationReadUsesCurrentPrivateWrapper",
    },
    "core": {
        "TestPinkhaAuthorizedOperationReadRejectsVersionBeforeAccount",
        "TestPinkhaAuthorizedOperationReadShapeAndCancellationBeforeAccount",
        "TestPinkhaAuthorizedOperationReadRequiresRunningAccount",
        "TestPinkhaAuthorizedOperationRPCSchemaAndExactOpaqueRoundTrip",
        "TestPinkhaAuthorizedOperationRPCFailedFencesReleaseNoPayload",
        "TestPinkhaAuthorizedOperationRPCBoundsAndInvalidShape",
        "TestPinkhaAuthorizedOperationRPCRejectsBeforeAccount",
    },
    "clientlibrary/service": {
        "TestPinkhaAuthorizedOperationGeneratedByteBoundaryWithoutAccount",
    },
}
SUBCASES = {
    "TestNativeAuthorizedOperationReadCurrentACLAndLifetimeFences": [
        "foreign-reader-before-targets", "revoked-after-discovery", "cancelled-after-discovery",
        "closed-after-discovery", "target-unavailable", "foreign-acl-lease"],
    "TestNativeAuthorizedOperationReadBoundsNeverReturnPartialClosure": ["variant-count", "encoded-response"],
    "TestPinkhaAuthorizedOperationTargetsRejectChangedEligibility": [
        "replaced-cache", "deleted", "uninstalled", "foreign-space", "wrong-native-type"],
    "TestPinkhaAuthorizedOperationTargetsRejectMalformedRequestedGraph": [
        "cycle", "duplicate-parent", "missing-child", "wrong-row-id", "missing-root", "orphan-cycle", "orphan-links-live-graph"],
    "TestPinkhaAuthorizedOperationTargetsRetainGenesisDeletionAuthority": [
        "deleted-object-before-snapshot", "deleted-space-empty-closure"],
    "TestPinkhaAuthorizedOperationTargetsCancellationAndLoadFailure": [
        "cancelled-before-load", "cancelled-during-load", "native-load-error", "cancelled-waiting-settings"],
    "TestPinkhaAuthorizedOperationRPCFailedFencesReleaseNoPayload": [
        "account-changed", "denied", "missing-key", "no-account", "unsupported-version", "invalid",
        "target-unavailable", "history-unavailable", "snapshot-changed", "projection-behind", "read-limit", "cancelled", "deadline"],
    "TestPinkhaAuthorizedOperationRPCBoundsAndInvalidShape": [
        "variant-count", "encoded-response", "incomplete", "wrong-outcome", "wrong-reachability", "duplicate-claim"],
    "TestPinkhaAuthorizedOperationGeneratedByteBoundaryWithoutAccount": ["0", "1", "2"],
}
REQUIRED = {
    (method, PACKAGE_ROOT + package)
    for package, methods in TOP_LEVEL.items() for method in methods
}
REQUIRED |= {
    (method + "/" + case, PACKAGE_ROOT + package)
    for package, methods in TOP_LEVEL.items() for method in methods for case in SUBCASES.get(method, [])
}
PACKAGES = {PACKAGE_ROOT + package for package in TOP_LEVEL}
TEST_PATTERN = "^(TestPinkhaAuthorizedOperation|TestNativeAuthorizedOperationRead)"


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "Expected regular candidate source")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value: str) -> Path:
    path = PurePosixPath(value)
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and ":" not in value, "Unsafe candidate source path")
    return Path(*path.parts)


def read_sources(control: Path, retained_rpc: dict, registry: dict) -> dict:
    base = control / "Tools/TorahNativeOperations"
    root = base / "authorized_read"
    native_path = root / "native-read.json"
    manifest_path = root / "rpc/heart-authorized-read.json"
    native = json.loads(native_path.read_bytes())
    manifest = json.loads(manifest_path.read_bytes())
    for value in [native, manifest]:
        require(value["heart_sha"] == HEART and value["contract"] == CONTRACT
                and value["read_protocol_version"] == 1 and value["app_capability"] == "OFF",
                "Wrong additive read authority contract")
        require(value["maximum_variants"] == 256 and value["maximum_response_bytes"] == 4 * 1024 * 1024,
                "Candidate read bounds differ")
    require(native["registration_inventory_sha256"] == digest(base / "heart-registration.json")
            and native["registration_patch_sha256"] == digest(base / "heart-registration.patch"),
            "Retained private registry source differs")
    require(manifest["native_read_inventory_sha256"] == digest(native_path)
            and manifest["retained_rpc_inventory_sha256"] == digest(base / "rpc/heart-rpc.json")
            and manifest["retained_rpc_patch_sha256"] == digest(base / "rpc/heart-rpc.patch"),
            "Retained read/RPC input differs")
    require(manifest["patch_sha256"] == digest(root / "rpc/heart-authorized-read.patch"),
            "Additive read schema patch differs")
    require(set(manifest["tracked"]) == {"pb/protos/service/service.proto"}
            and manifest["tracked"]["pb/protos/service/service.proto"]["before_sha256"]
            == retained_rpc["tracked"]["pb/protos/service/service.proto"]["after_sha256"],
            "Candidate must extend the exact retained service schema")
    paths: dict[str, tuple[Path, str]] = {}
    for overlay, expected in [(root / "overlay", native["overlay"]), (root / "rpc/overlay", manifest["overlay"])]:
        actual = {p.relative_to(overlay).as_posix(): digest(p)
                  for p in overlay.rglob("*") if p.is_file() and p.suffix in {".go", ".proto"}}
        require(actual == expected, "Missing, additional or changed candidate overlay")
        for name, sha in actual.items():
            relative(name)
            require(name not in paths, "Candidate overlay path collision")
            paths[name] = (overlay / name, sha)
    retained_paths = (set(registry["tracked"]) | set(registry["overlay"]) | set(retained_rpc["tracked"])
                      | set(retained_rpc["overlay"]) | set(retained_rpc["generation"]["generated_paths"]))
    require(not set(paths).intersection(retained_paths) and GENERATED not in retained_paths | set(paths),
            "Candidate may not replace retained sources")
    require(PROTO in paths and manifest["generated_paths"] == [GENERATED], "Wrong additive generated message path")
    return {"root": root, "native": native, "manifest": manifest, "paths": paths,
            "native_inventory_sha256": digest(native_path), "manifest_sha256": digest(manifest_path)}


def apply_sources(source: dict, heart: Path, expected: dict, tracked: set[str], run) -> None:
    manifest = source["manifest"]
    for name, hashes in manifest["tracked"].items():
        require(digest(heart / name) == hashes["before_sha256"], "Retained service schema input differs")
    patch = source["root"] / "rpc/heart-authorized-read.patch"
    import os
    run(["git", "apply", "--check", str(patch)], "authorized-schema-check", heart, os.environ.copy())
    run(["git", "apply", str(patch)], "authorized-schema-apply", heart, os.environ.copy())
    for name, hashes in manifest["tracked"].items():
        require(digest(heart / name) == hashes["after_sha256"], "Candidate service schema output differs")
        expected[name] = hashes["after_sha256"]
        tracked.add(name)
    for name, (path, sha) in source["paths"].items():
        target = heart / relative(name)
        require(not target.exists(), "Candidate overlay would replace native source")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        require(digest(target) == sha, "Candidate source copy differs")
        expected[name] = sha


def validate_test_events(events: list[dict], success: bool) -> dict:
    terminal = [event for event in events if event.get("Test") and event.get("Action") in {"pass", "fail", "skip"}]
    actual = [(event["Test"], event.get("Package")) for event in terminal if event.get("Action") == "pass"]
    packages = {event.get("Package") for event in events if not event.get("Test") and event.get("Action") == "pass"}
    require(success and not any(event.get("Action") in {"fail", "skip"} for event in events),
            "Candidate native execution failed/skipped")
    require(set(actual) == REQUIRED and len(actual) == len(REQUIRED) and packages == PACKAGES,
            "Missing, repeated, unexpected or wrong-package candidate execution")
    return {"pass": len(actual), "top_level_pass": sum(len(values) for values in TOP_LEVEL.values()),
            "subcase_pass": sum(len(values) for values in SUBCASES.values()), "fail": 0, "skip": 0,
            "required_passed": sorted({name for name, _ in REQUIRED}),
            "unchanged_prior_tests_executed": 0}
