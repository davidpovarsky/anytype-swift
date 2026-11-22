"""Immutable candidate, selected XCTest and source/provenance boundaries."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = "davidpovarsky/anytype-swift"
VERSION = "v0.5.0-pinkha.prepared.1"
MANIFEST = "Tools/AnyEngineValidation/evidence/native-prepared-migration-v11-candidate-source.json"
MANIFEST_SHA = "bff726fc54530af8f3cc0361b5a041d1c46019a5584e877303ef88aaf60c9c44"
HELPER = "Tools/AnyEnginePort/prepare_native_runtime.py"
WORKFLOW = ".github/workflows/pinkha-prepared-migration-apple.yml"
HERE = "Tools/AnyEngineValidation/prepared_migration_apple"
PACKAGE = "PinkhaAnyRuntime"
TARGET = "PinkhaAnyRuntimeTests"
METHOD = "AnyPreparedMigrationRuntimeTests/testManagedPreparedObjectAndBlockSurviveOrderlyReopenAndRejectRevokedOwner"
SELECTOR = TARGET + "/" + METHOD
TEST_SOURCE = "Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyPreparedMigrationRuntimeTests.swift"
TEST_SHA = "ba446f2a78f475517439111169cd6d4c33541bff470d848e63b7bf6207d0818f"
PASS = "PASS_ACTUAL_PREPARED_MIGRATION_APPLE"
BUILD_PASS = "BUILT_SOURCE_VERIFIED_PREPARED_MIGRATION_APPLE_NOT_EXECUTED"
PRODUCER_JOB = "Build prepared migration native runtime"
MODULES = ("PinkhaAnyRuntime", "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit")
PINS = {
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "torahinspectorkit": "511454e49450cb2581ddf77f644146ff3e30dbef",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular evidence/source file")
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=60).strip()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_native(control):
    return load_module(control / HELPER, "prepared_candidate_native_helper")


def candidate(control):
    path = control / MANIFEST
    require(digest(path) == MANIFEST_SHA, "Frozen prepared native manifest changed")
    native = load_native(control)
    value = native.read_manifest(path)
    require(native.native_version(value) == VERSION and value.get("qualificationCandidate") is True,
            "Explicit prepared candidate version required")
    require(value["wireCompatibility"]["migrationFileCapability"] == 0
            and value["wireCompatibility"]["migrationNetworkVerified"] is False,
            "Candidate does not authorize file or network acceptance")
    for name in ("any", "sdk"):
        require(digest(path.parent / native.safe_relative(value[name]["patch"])) == value[name]["patchSHA256"],
                "Candidate full patch changed")
    return native, value


def selected_source(control):
    require(digest(control / TEST_SOURCE) == TEST_SHA, "Frozen actual XCTest source changed")
    source = (control / TEST_SOURCE).read_text(encoding="utf-8")
    require(re.findall(r"^    func (test\w+)\(", source, re.M) == [METHOD.split("/")[1]],
            "Exactly the new selected XCTest must be declared")
    return {TEST_SOURCE: TEST_SHA}


def clean_source(control, expected):
    require(re.fullmatch(r"[0-9a-f]{40}", expected or ""), "Exact source commit required")
    require(git(control, "rev-parse", "HEAD") == expected
            and not git(control, "status", "--porcelain"), "Fresh exact clean control checkout required")
    candidate(control)


def snapshot(control):
    paths = [HERE, HELPER, MANIFEST, WORKFLOW, "Tools/AnyEnginePort/verify_native_test_execution.py",
             "Tools/PinkhaSimulatorGate/simulator_selection.py", "Tools/TorahNativeOperations",
             *("Modules/" + name for name in MODULES)]
    value = json.loads((control / MANIFEST).read_bytes())
    paths += [str(Path(MANIFEST).parent / value[name]["patch"]) for name in ("any", "sdk")]
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--", *paths], timeout=60).decode().split("\0")
    result = {name: digest(control / name) for name in sorted(filter(None, names))}
    require(set([HERE + "/run_host.py", HELPER, MANIFEST, WORKFLOW, TEST_SOURCE]) <= set(result),
            "Required tracked source is missing")
    # Xcode writes its own metadata outside these product source roots. A
    # newly injected untracked Swift/resource file must not escape the census.
    for module in MODULES:
        for kind in ("Sources", "Tests"):
            directory = control / "Modules" / module / kind
            for path in directory.rglob("*"):
                require(not path.is_symlink(), "Symlink in product source closure")
                if path.is_file():
                    require(path.relative_to(control).as_posix() in result, "Untracked file entered product source closure")
    return result


def source_after(control, before, evidence, receipt, primary):
    try:
        after = snapshot(control)
        save(evidence / "control-source-after.json", after)
        require(after == before, "Tracked consumer/producer source changed during execution")
        receipt["source_unchanged"] = True
    except BaseException as error:
        receipt["source_verification_failure"] = {"error_type": type(error).__name__, "error": str(error)}
        if primary is None:
            raise


def artifact_name(run_id, attempt, commit):
    require(re.fullmatch(r"[1-9][0-9]*", str(run_id or ""))
            and re.fullmatch(r"[1-9][0-9]*", str(attempt or ""))
            and re.fullmatch(r"[0-9a-f]{40}", commit or ""), "Exact producer run, attempt and commit required")
    return "Any-Prepared-Migration-Native-" + str(run_id) + "-" + str(attempt) + "-" + commit


def reuse_inputs(run_id, attempt, commit):
    values = (run_id or "", attempt or "", commit or "")
    if not any(values):
        return False
    require(all(values), "Reuse requires all three producer inputs")
    artifact_name(*values)
    return True


def resolved_pins(package):
    paths = sorted(package.rglob("Package.resolved"))
    require(paths, "Actual Xcode Package.resolved receipt required")
    result = {}
    for path in paths:
        value = json.loads(path.read_bytes())
        pins = value.get("pins")
        require(isinstance(pins, list), "Missing actual Swift package pins")
        actual = {row.get("identity"): row.get("state", {}).get("revision") for row in pins}
        require(len(actual) == len(pins) and actual == PINS, "Resolved Swift dependencies differ from retained exact revisions")
        result[str(path.relative_to(package))] = digest(path)
    return result


def dependency_checkouts(work):
    directory = work / "SourcePackages/checkouts"
    require(directory.is_dir(), "Actual resolved dependency checkouts required")
    actual = {path.name.lower(): path for path in directory.iterdir() if path.is_dir()}
    require(set(actual) == set(PINS), "Unexpected dependency checkout set")
    result = {}
    for identity, path in actual.items():
        require(not path.is_symlink() and git(path, "rev-parse", "HEAD") == PINS[identity]
                and not git(path, "status", "--porcelain", "--untracked-files=no"),
                "Actual dependency source changed from its resolved revision")
        result[identity] = {"revision": PINS[identity], "tree": git(path, "rev-parse", "HEAD^{tree}")}
    return result
