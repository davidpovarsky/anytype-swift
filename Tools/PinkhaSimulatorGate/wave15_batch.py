"""Fixed same-job Release/r14 profiles over existing Wave15 UI lanes.

The existing lane executor remains the authority for native preparation, live
runtime mapping, UI selection, language observations, and installed code bytes.
This module owns a bounded worker and newly created disposable simulators. It
does not accept a previous build artifact or a serialized prebuilt descriptor.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import subprocess
import sys
import time
from uuid import uuid4
import wave15_diagnostics as diagnostics
import type_preservation as preservation


PROFILE = "remaining-release"
RETAINED_HEART_PROFILE = "retained-heart-release"
PROTOCOL = "pinkha-wave15-same-job-batch-v1"
LANES = ("inspector", "inspector-search", "properties", "properties-set", "canonical-properties", "editor")
COUNTS = (5, 1, 3, 2, 1, 3)
UI_COUNT = 15
PREPARATION_COUNT = 6
POSTFLIGHT_COUNT = 1
PREPARATIONS = (
    "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
    "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
    "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
    "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
    "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
    "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
)


@dataclass(frozen=True)
class BatchProfile:
    name: str
    lanes: tuple
    counts: tuple
    preparations: tuple

    @property
    def ui_count(self):
        return sum(self.counts)

    @property
    def preparation_count(self):
        return len(self.lanes)

    @property
    def postflight_count(self):
        return self.lanes.count("properties-set")


# Reviewed presets only. Callers select a name, never a method list, an
# arbitrary lane subset, a previous build, or a previously populated simulator.
PROFILES = {
    PROFILE: BatchProfile(PROFILE, LANES, COUNTS, PREPARATIONS),
    RETAINED_HEART_PROFILE: BatchProfile(RETAINED_HEART_PROFILE,
        ("editor", "quote-drop", "properties-set"), (3, 1, 2),
        (PREPARATIONS[5], PREPARATIONS[0], PREPARATIONS[3])),
}


def profile_spec(name=PROFILE):
    require(isinstance(name, str) and name in PROFILES, "Unknown reviewed batch profile")
    return PROFILES[name]


CONFIGURATION = "Release-Anytype"
FLAGS = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED", "ENABLE_TESTABILITY=YES",
         "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
         "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
# The existing workflow has a 120-minute execution step and a 150-minute job.
# Leave 12 minutes outside the worker for owned cleanup and final publication.
WORKER_SECONDS = 105 * 60
CLEANUP_SECONDS = 3 * 60
STEP_SECONDS = 120 * 60
SCOPED_DEVICE_QUERY_SECONDS = 120
BUNDLE = "io.anytype.app"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf8")
    temporary.replace(path)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plan(lane, profile=PROFILE):
    spec = profile_spec(profile)
    result = []
    for name, count, preparation in zip(spec.lanes, spec.counts, spec.preparations, strict=True):
        item = lane.plan(name, "ipad", "en")
        require(item["build_configuration"] == CONFIGURATION
                and item["expected_ui_executions"] == count
                and item["expected_preparation_executions"] == 1
                and item["preparation"] == preparation
                and item.get("expected_postflight_executions") == (1 if name == "properties-set" else 0)
                and item.get("postflight") == (preservation.METHOD if name == "properties-set" else None),
                "An existing lane changed; review the bounded batch profile")
        result.append(item)
    methods = [method for item in result for method in item["methods"]]
    require(len(methods) == spec.ui_count and len(set(methods)) == spec.ui_count,
            "Exactly the reviewed profile's existing UI methods are required")
    require(len({item["preparation"].split("/")[0] for item in result}) == 3,
            "Exactly three separately executed preparation suites required")
    return result


def minimum_lane_budget(selection):
    from run_ui27 import selection_time_budget
    require(len(selection["methods"]) == selection["expected_ui_executions"],
            "Lane budget requires its exact declared UI method selection")
    budget = selection_time_budget("PinkhaStage1AcceptanceUITests", selection["methods"])
    # Native preparation retains 300s. UI ceilings come from the same whitelist
    # used by the executor; two long Properties methods require 900s each.
    postflight = selection.get("postflight")
    expected = 1 if selection["lane"] == "properties-set" else 0
    require(selection.get("expected_postflight_executions") == expected
            and postflight == (preservation.METHOD if expected else None), "Lane postflight budget contract differs")
    return 300 + budget["total_method_seconds"] + (preservation.SECONDS + preservation.INSTALLATION_SECONDS) * expected + 180


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def bundle_manifest(root):
    """Freeze selected bundles, including resources and internal symlinks."""
    require(root.is_dir() and not root.is_symlink(), "Selected build bundle is missing or is a symlink")
    root = root.resolve()
    entries = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        require(path.resolve().is_relative_to(root), "Selected build bundle has an external dependency")
        if path.is_symlink():
            require(path.exists(), "Selected build bundle has a dangling symlink")
            entries[relative] = {"symlink": os.readlink(path)}
        elif path.is_file():
            entries[relative] = {"sha256": digest(path), "bytes": path.stat().st_size}
    require(entries, "Selected build bundle is empty")
    return {"sha256": canonical_hash(entries), "entries": entries}


class TrackedSourceChanged(RuntimeError):
    def __init__(self, observation):
        super().__init__("Tracked source changed during the same-job build")
        self.observation = observation


def tracked_source_change(app, shared, status, stage):
    """Record names/modes/hashes only; never accept or reset a changed source."""
    observation = {"stage": stage, "porcelain_observation": status, "changes": []}
    try:
        observation["source_sha"] = shared.git(app, "rev-parse", "HEAD")
        paths = sorted(filter(None, shared.git(app, "diff", "--name-only", "--no-renames", "-z",
                                               "HEAD", "--").split("\0")))
        observation.update(changed_path_count=len(paths), changed_paths_sha256=canonical_hash(paths),
                           omitted_path_count=max(0, len(paths) - 64))
        for name in paths[:64]:
            entry = {"path": name}
            observation["changes"].append(entry)
            original = shared.git(app, "ls-tree", "-z", "HEAD", "--", name)
            entry["head_tree_entry"] = original
            if original:
                metadata, original_name = original.rstrip("\0").split("\t", 1)
                mode, kind, blob = metadata.split()
                require(original_name == name, "Changed source tree entry is ambiguous")
                entry.update(head_mode=mode, head_kind=kind, head_blob=blob)
                if kind == "blob":
                    content = subprocess.check_output(["git", "-C", str(app), "cat-file", "blob", blob], timeout=30)
                    entry.update(head_sha256=hashlib.sha256(content).hexdigest(), head_bytes=len(content))
            path = app / name
            if path.is_symlink():
                content = os.readlink(path).encode("utf8", errors="surrogateescape")
                entry.update(worktree_kind="symlink", worktree_sha256=hashlib.sha256(content).hexdigest(),
                             worktree_bytes=len(content))
            elif not path.resolve().is_relative_to(app.resolve()):
                entry["worktree_kind"] = "OUTSIDE_CHECKOUT_NOT_READ"
            elif path.is_file():
                entry.update(worktree_kind="file", worktree_sha256=digest(path),
                             worktree_bytes=path.stat().st_size, worktree_mode=oct(path.stat().st_mode & 0o7777))
            else:
                entry["worktree_kind"] = "directory" if path.exists() else "missing"
    except Exception as error:
        # A diagnostic failure cannot make dirty source acceptable or replace
        # the original identity failure. Cancellation remains interruptible.
        observation["diagnostic_error_type"] = type(error).__name__
    return observation


def source_snapshot(app, shared, *, stage="SHARED_INPUTS_BETWEEN_PHASES"):
    status = shared.git(app, "status", "--porcelain", "--untracked-files=no")
    if status:
        raise TrackedSourceChanged(tracked_source_change(app, shared, status, stage))
    tracked = shared.git(app, "ls-files").splitlines()
    locks = {name: digest(app / name) for name in tracked if name.endswith("Package.resolved")}
    require(locks, "Tracked package locks are missing")
    return {"source_sha": shared.git(app, "rev-parse", "HEAD"),
            "source_tree_sha": shared.git(app, "rev-parse", "HEAD^{tree}"),
            "branch": shared.git(app, "branch", "--show-current"),
            "package_locks": locks,
            "hanlin_snapshot_sha256": digest(app / "Dependencies/Hanlin/.pinkha-source.json")}


def explicit_selection(configuration, blueprint, selections, environment, shared, app_path=None):
    """Use the reviewed T5 selection contract without inheriting T5 build flags."""
    original = configuration.read_bytes()
    data = plistlib.loads(original)
    shared.inject(data, blueprint, environment, app_path)
    targets = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("BlueprintName") == blueprint or value.get("TestBundlePath", "").endswith(blueprint + ".xctest"):
                targets.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(data)
    require(len(targets) == 1, "One original XCTest target required")
    filters = sorted({name.split("/")[0] for name in selections}) if blueprint == "AnytypeTests" else list(selections)
    require(filters and len(filters) == len(set(filters)), "Nonempty unique XCTest selection required")
    targets[0]["OnlyTestIdentifiers"] = filters
    targets[0]["SkipTestIdentifiers"] = []
    if selections == [preservation.METHOD]:
        require(blueprint == "AnytypeTests", "Postflight must select the actual native target")
        preservation.configure_target(targets[0], environment)
    selected = configuration.with_name("UI27-Batch-" + uuid4().hex + ".xctestrun")
    with selected.open("xb") as stream:
        plistlib.dump(data, stream)
    require(configuration.read_bytes() == original, "Original XCTest configuration changed")
    return selected


def validate_observed_result(summary, methods, expected, udid, *, passing):
    """Qualify original xcresult data, including a failed lane that may continue."""
    devices = [row.get("device", {}) for row in summary.get("devicesAndConfigurations", [])]
    require(devices and all(device.get("osVersion", "").split(".")[0] == "27"
            and device.get("deviceId", "").lower() == udid.lower()
            and device.get("architecture") == "arm64" for device in devices),
            "Original xcresult has another device, architecture or runtime")
    expected = {name.removesuffix("()") for name in expected}
    actual = {name.removesuffix("()"): value for name, value in methods.items()}
    require(actual and len(actual) == len(methods) and set(actual).issubset(expected),
            "Original xcresult has empty, duplicate or foreign methods")
    require(all(value in {"Passed", "Failed"} for value in actual.values()),
            "Skipped or unknown method results cannot qualify a batch lane")
    observed = {"totalTestCount": len(actual),
                "passedTests": sum(value == "Passed" for value in actual.values()),
                "failedTests": sum(value == "Failed" for value in actual.values()), "skippedTests": 0}
    require(all(type(summary.get(key)) is int and summary[key] == value for key, value in observed.items()),
            "Original xcresult counts do not match its named cases")
    if passing:
        require(set(actual) == expected and observed["failedTests"] == 0,
                "Passing lane did not execute every exact selected method")
    else:
        require(observed["failedTests"] > 0, "Failure is not an observed test failure; abort shared setup")
    return {"original_counts": observed, "actual_methods": methods, "actual_devices": devices}


@dataclass(frozen=True)
class FrozenBuild:
    app: Path
    derived: Path
    ui_derived: Path
    built: Path
    native_configuration: Path
    ui_configuration: Path
    shared: object
    source: dict
    candidate_hashes: dict
    artifacts: dict
    native_bundles: tuple
    runtime_receipt_path: Path
    runtime_receipt_sha256: str
    fixtures: dict
    device: dict | None = None

    def observed_artifacts(self):
        runner = self.ui_derived / "Build/Products" / (CONFIGURATION + "-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app")
        return {"app": bundle_manifest(self.built), "ui_runner": bundle_manifest(runner),
                "native_test_bundles": {str(path): bundle_manifest(path) for path in self.native_bundles},
                "native_xctestrun_sha256": digest(self.native_configuration),
                "ui_xctestrun_sha256": digest(self.ui_configuration)}

    def verify(self, app, head, identity, flags, configuration):
        require(app == self.app and head == self.source["source_sha"]
                and flags == FLAGS and configuration == CONFIGURATION,
                "Same-job source/configuration/flags differ")
        require(source_snapshot(app, self.shared) == self.source,
                "Shared source, package locks or Hanlin snapshot changed")
        require(identity["hashes"] == self.candidate_hashes, "Shared candidate inputs changed")
        require(digest(self.runtime_receipt_path) == self.runtime_receipt_sha256,
                "Verified r14 installation receipt changed")
        require(self.observed_artifacts() == self.artifacts,
                "Selected built App, native test bundle, UI runner or original xctestrun changed")

    def verify_current(self):
        matrix = json.loads((self.app / "Tools/PinkhaSimulatorGate/required-coverage.json").read_text())
        self.verify(self.app, self.shared.git(self.app, "rev-parse", "HEAD"),
                    self.shared.candidate_identity(self.app, matrix), FLAGS, CONFIGURATION)

    def confirm_empty_container(self, udid, evidence):
        require(self.device is not None and self.device["udid"] == udid, "Unowned fixture destination")
        observation = {}
        try:
            inventory = scoped_device_inventory(self.device, timeout=SCOPED_DEVICE_QUERY_SECONDS,
                                                observation=observation)
        finally:
            write(evidence / "fresh-device-query.json", observation)
        observed = validate_owned_device(inventory, self.device, expected_state="Booted")
        query = subprocess.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"],
                               capture_output=True, timeout=30)
        negative_unclassified = query.returncode != 0 and not query.stdout
        stderr_path = evidence / "container-lookup.stderr"
        with stderr_path.open("xb") as stream:
            stream.write(query.stderr)
        receipt = {"simulator_udid": udid, "owned_created_device": observed,
                   "freshness_basis": "NEW_OWNED_DEVICE_BEFORE_FIRST_APP_INSTALL",
                   "container_lookup_exit_code": query.returncode,
                   "container_lookup_stdout_sha256": hashlib.sha256(query.stdout).hexdigest(),
                   "container_lookup_classification": "NEGATIVE_UNCLASSIFIED" if negative_unclassified else "UNEXPECTED_SUCCESS_OR_STDOUT",
                   "container_lookup_stderr_path": stderr_path.name,
                   "container_lookup_stderr_sha256": hashlib.sha256(query.stderr).hexdigest(),
                   "container_lookup_stderr_bytes": len(query.stderr),
                   "status": "FRESH_CREATED_DEVICE_BEFORE_NATIVE_PREPARATION" if negative_unclassified else "FAIL"}
        write(evidence / "fresh-container.json", receipt)
        require(receipt["status"] != "FAIL", "Unexpected successful or nonempty container lookup before preparation")

    def run_selection(self, app, configuration, blueprint, udid, selections, environment, evidence, prefix, app_path=None):
        require(self.device is not None and udid == self.device["udid"], "Selection is not on its newly created simulator")
        original = self.native_configuration if blueprint == "AnytypeTests" else self.ui_configuration
        require(configuration == original, "Selection is not from this job's original build")
        selected = explicit_selection(configuration, blueprint, selections, environment, self.shared, app_path)
        result = self.shared.run_selection(app, selected, blueprint, udid, selections, environment, evidence, prefix, app_path)
        if result["status"] == "PASS":
            summary = json.loads((evidence / (prefix + "-summary.json")).read_text())
            methods = self.shared.method_results(json.loads((evidence / (prefix + "-tests.json")).read_text()))
            result["batch_exact_observation"] = validate_observed_result(summary, methods, selections, udid, passing=True)
            write(evidence / "batch-validation.json", result["batch_exact_observation"])
        return result

    def observe_fixture(self, fixture, container, evidence):
        require(self.device is not None, "Fixture has no owned simulator")
        space = fixture.get("spaceId")
        require(isinstance(space, str) and space, "Prepared fixture Space is missing")
        container = container.resolve()
        require(self.device["udid"].lower() in {part.lower() for part in container.parts},
                "Prepared fixture container is outside its owned simulator")
        require(not any(item["space_id"] == space or item["container"] == str(container)
                        for item in self.fixtures.values()), "Batch lanes reused a Space or App data container")
        name = self.device["lane"]
        require(name not in self.fixtures, "A batch lane prepared its fixture more than once")
        record = {"space_id": space, "container": str(container), "simulator_udid": self.device["udid"],
                  "status": "SEPARATE_NATIVE_FIXTURE_OBSERVED_BEFORE_UI"}
        self.fixtures[name] = record
        write(evidence / "fixture-isolation.json", record)


def valid_udid(value):
    return isinstance(value, str) and re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value) is not None


def scoped_device_inventory(ownership, *, timeout, observation=None):
    """Query only an owned UDID, or the exact planned nonce name before its receipt.

    simctl's search string is only a transport filter. Every returned identity
    is checked here and all existing ownership/runtime/state checks still apply.
    An empty filtered result is not a freshness or Native acceptance claim.
    """
    udid = ownership.get("udid")
    has_udid = "udid" in ownership
    if has_udid:
        require(valid_udid(udid), "Refuse a non-UUID simulator selector")
        selector = udid
    else:
        selector = ownership.get("name")
        require(isinstance(selector, str) and selector and "\0" not in selector,
                "Missing exact planned simulator name")
    require(0 < timeout <= SCOPED_DEVICE_QUERY_SECONDS, "Invalid bounded simulator query timeout")
    observation = {} if observation is None else observation
    observation.update(status="QUERY_STARTED", selector=selector,
                       selector_kind="OWNED_UDID" if has_udid else "EXACT_PLANNED_NAME",
                       timeout_seconds=timeout)
    started = time.monotonic()
    try:
        value = json.loads(subprocess.check_output(
            ["xcrun", "simctl", "list", "devices", selector, "--json"], timeout=timeout))
        require(isinstance(value, dict) and isinstance(value.get("devices"), dict),
                "Invalid scoped simulator inventory")
        for items in value["devices"].values():
            require(isinstance(items, list), "Invalid scoped simulator device list")
            for item in items:
                require(isinstance(item, dict) and valid_udid(item.get("udid")),
                        "Invalid scoped simulator UDID")
                require(item["udid"].lower() == udid.lower() if has_udid else item.get("name") == selector,
                        "Scoped simulator query returned another identity")
        observation["status"] = "RETURNED_VALID_SCOPED_INVENTORY"
        return value
    except BaseException as error:
        observation.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                           "TIMED_OUT" if isinstance(error, subprocess.TimeoutExpired) else "FAIL",
                           error_type=type(error).__name__)
        raise
    finally:
        observation["elapsed_seconds"] = round(max(0, time.monotonic() - started), 6)


def validate_owned_device(inventory, device, *, expected_state=None):
    found = [(runtime, item) for runtime, items in inventory.get("devices", {}).items()
             for item in items if item.get("udid", "").lower() == device["udid"].lower()]
    require(len(found) == 1, "Owned simulator is missing or duplicated")
    runtime, item = found[0]
    require(runtime == device["runtime"]["identifier"]
            and item.get("deviceTypeIdentifier") == device["device"]["identifier"]
            and item.get("name") == device["name"] and item.get("isAvailable") is True,
            "Owned simulator type/runtime/name differs")
    if expected_state is not None:
        require(item.get("state") == expected_state, "Owned simulator has an unexpected state")
    return item


def validate_fresh_device_receipt(fresh, directory, udid):
    require(fresh.get("status") == "FRESH_CREATED_DEVICE_BEFORE_NATIVE_PREPARATION"
            and fresh.get("freshness_basis") == "NEW_OWNED_DEVICE_BEFORE_FIRST_APP_INSTALL"
            and fresh.get("simulator_udid") == udid
            and fresh.get("container_lookup_classification") == "NEGATIVE_UNCLASSIFIED"
            and type(fresh.get("container_lookup_exit_code")) is int and fresh["container_lookup_exit_code"] != 0
            and fresh.get("container_lookup_stdout_sha256") == hashlib.sha256(b"").hexdigest(),
            "Passing lane lacks the fresh-device construction and unclassified lookup receipt")
    require(fresh.get("container_lookup_stderr_path") == "container-lookup.stderr", "Original lookup stderr path differs")
    original = directory / "container-lookup.stderr"
    require(original.is_file() and not original.is_symlink()
            and type(fresh.get("container_lookup_stderr_bytes")) is int
            and original.stat().st_size == fresh["container_lookup_stderr_bytes"]
            and digest(original) == fresh.get("container_lookup_stderr_sha256"),
            "Original unclassified lookup stderr differs")


def build_once(args, lane, selections, receipt):
    shared = lane.shared
    app, evidence, derived = args.app.resolve(), args.evidence.resolve(), args.derived.resolve()
    require(derived.is_relative_to(app / "build") and evidence.is_relative_to(app / "build"),
            "Batch requires this checkout's job-owned build/evidence paths")
    head = shared.git(app, "rev-parse", "HEAD")
    lane.require_source_identity(head, os.environ.get("GITHUB_SHA"),
        shared.git(app, "branch", "--show-current"), os.environ.get("GITHUB_REF"))
    preflight_path = evidence / "preflight/preflight.json"
    preflight = json.loads(preflight_path.read_text())
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight.get("source_sha") == head
            and preflight.get("run_id") == os.environ.get("GITHUB_RUN_ID"), "Original OS27 preflight identity differs")
    runtime_path = evidence / "heart/heart-installation.json"
    runtime = json.loads(runtime_path.read_text())
    require(runtime.get("status") == "PASS" and runtime.get("app_source_sha") == head
            and runtime.get("marker") == shared.MARKER, "Exact r14 runtime installation is required")
    source = source_snapshot(app, shared, stage="BEFORE_BUILD")
    matrix = json.loads((app / "Tools/PinkhaSimulatorGate/required-coverage.json").read_text())
    identity = shared.candidate_identity(app, matrix)
    methods = [method for selection in selections for method in selection["methods"]]
    lane.source_methods(app, methods)
    common = evidence / "batch-build"
    common.mkdir(parents=True, exist_ok=False)
    receipt.update(source=source, candidate_input_hashes=identity["hashes"],
                   preflight_sha256=digest(preflight_path), runtime_installation=runtime, phase="BUILD")
    write(evidence / "batch-worker.json", receipt)
    udid = preflight["selected"]["ipad"]["udid"]
    shared.command(["xcrun", "simctl", "boot", udid], app, common)
    shared.command(["xcrun", "simctl", "bootstatus", udid, "-b"], app, common)
    shared.prepare_source_cache(app, derived)
    require(source_snapshot(app, shared, stage="AFTER_SOURCE_CACHE") == source,
            "Source or package inputs changed during cache preparation")
    base = ["xcodebuild", "build-for-testing", "-configuration", CONFIGURATION,
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO"]
    native_suites = sorted({selection["preparation"].split("/")[0] for selection in selections})
    postflight_suites = sorted({selection["postflight"].split("/")[0] for selection in selections if selection["postflight"]})
    require(postflight_suites == [preservation.SUITE], "Exactly one isolated postflight suite required")
    shared.command([*base, "-project", "Anytype.xcodeproj", "-scheme", "Anytype", "-derivedDataPath", str(derived),
                    *["-only-testing:AnytypeTests/" + name for name in native_suites + postflight_suites], *FLAGS], app, common)
    require(source_snapshot(app, shared, stage="AFTER_APP_AND_NATIVE_TEST_BUILD") == source,
            "Source or package inputs changed during App/native test build")
    built = derived / "Build/Products" / (CONFIGURATION + "-iphonesimulator/Anytype.app")
    shared.verify_signed_simulator(built, common)
    shared.verify_runtime_copies(built, shared.MARKER.encode(), common)
    native_configuration = shared.test_configuration(derived / "Build/Products", "AnytypeTests")
    project = shared.ui_only_project(app)
    require(source_snapshot(app, shared, stage="AFTER_UI_PROJECT_GENERATION") == source,
            "Source or package inputs changed during UI-only project generation")
    ui_derived = derived.with_name(derived.name + "-ui")
    shared.command([*base, "-project", str(project), "-scheme", "PinkhaPrebuiltUI", "-derivedDataPath", str(ui_derived),
                    *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in methods], *FLAGS], app, common)
    ui_configuration = shared.test_configuration(ui_derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    shared.command(["xcrun", "simctl", "shutdown", udid], app, common)
    native_bundles = tuple(sorted((derived / "Build/Products").rglob("AnytypeTests.xctest")))
    require(native_bundles, "Built native XCTest bundle is missing")
    require(source_snapshot(app, shared, stage="AFTER_UI_RUNNER_BUILD") == source,
            "Source or package inputs changed during UI runner build")
    frozen = FrozenBuild(app, derived, ui_derived, built, native_configuration, ui_configuration, shared,
                         source, identity["hashes"], {}, native_bundles, runtime_path, digest(runtime_path), {})
    frozen = replace(frozen, artifacts=frozen.observed_artifacts())
    build_record = {"status": "SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS", "source": source,
                    "build_flags": FLAGS, "configuration": CONFIGURATION,
                    "native_preparation_suites_built": native_suites, "native_postflight_suites_built": postflight_suites,
                    "ui_methods_built": methods,
                    "artifacts": frozen.artifacts, "runtime_receipt_sha256": frozen.runtime_receipt_sha256,
                    "native_acceptance_reused": False, "ui_acceptance_reused": False,
                    "previous_artifact_reuse": False}
    write(common / "same-job-build.json", build_record)
    receipt["build_receipt_sha256"] = digest(common / "same-job-build.json")
    return frozen, preflight


def qualify_functional_failure(lane_receipt, directory, selection, device, shared):
    phase = lane_receipt.get("phase")
    require(phase in {"PREPARATION", "UI", "POSTFLIGHT"}, "Failure is outside a named XCTest phase")
    native = phase == "PREPARATION"
    prefix = "prepare" if native else "wave15-" + selection["lane"]
    evidence = directory / ("preparation" if native else "ui")
    expected = [selection["preparation"]] if native else selection["methods"]
    if phase == "POSTFLIGHT":
        require(selection.get("postflight") == preservation.METHOD, "Unexpected postflight failure lane")
        prefix, evidence, expected = preservation.PREFIX, directory / "postflight", [preservation.METHOD]
    summary = json.loads((evidence / (prefix + "-summary.json")).read_text())
    methods = shared.method_results(json.loads((evidence / (prefix + "-tests.json")).read_text()))
    return validate_observed_result(summary, methods, expected, device["udid"], passing=False)


def validate_lane_pass(receipt, directory, selection, context):
    require(receipt.get("status") == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING"
            and receipt.get("source_sha") == context.source["source_sha"]
            and receipt.get("run_id") == os.environ.get("GITHUB_RUN_ID")
            and receipt.get("run_attempt") == os.environ.get("GITHUB_RUN_ATTEMPT"),
            "Passing lane receipt has another source/run identity")
    require(receipt.get("native_build_flags") == FLAGS
            and receipt.get("selection", {}).get("methods") == selection["methods"]
            and receipt["selection"].get("build_configuration") == CONFIGURATION,
            "Passing lane source selection/configuration differs")
    observations = {}
    phases = [("preparation", "prepare", [selection["preparation"]]),
              ("ui", "wave15-" + selection["lane"], selection["methods"])]
    if selection["postflight"]:
        phases.append(("postflight", preservation.PREFIX, [preservation.METHOD]))
        preservation.validate_saved(directory, receipt, context.device["udid"])
    for phase, prefix, expected in phases:
        require(receipt.get(phase, {}).get("status") == "PASS", "Passing lane has no passing actual phase")
        original = directory / phase
        summary_path, tests_path = original / (prefix + "-summary.json"), original / (prefix + "-tests.json")
        summary = json.loads(summary_path.read_text())
        methods = context.shared.method_results(json.loads(tests_path.read_text()))
        observations[phase] = {**validate_observed_result(summary, methods, expected, context.device["udid"], passing=True),
                               "summary_sha256": digest(summary_path), "tests_sha256": digest(tests_path)}
    fresh = json.loads((directory / "fresh-container.json").read_text())
    validate_fresh_device_receipt(fresh, directory, context.device["udid"])
    fixture = json.loads((directory / "fixture-isolation.json").read_text())
    require(fixture == context.fixtures.get(selection["lane"]), "Passing lane fixture identity differs")
    write(directory / "batch-original-results-validation.json", observations)
    return observations


def worker(args, lane, intent):
    require(os.getppid() == intent["parent_pid"], "Batch worker has another parent")
    require(0 < args.deadline - time.monotonic() <= WORKER_SECONDS, "Invalid bounded worker deadline")
    spec = profile_spec(intent.get("profile", PROFILE))
    selections = plan(lane, spec.name)
    receipt = {"protocol": PROTOCOL, "status": "FAIL", "phase": "SETUP", "started_at": now(),
               "profile": spec.name, "planned_ui_methods": spec.ui_count,
               "planned_native_preparations": spec.preparation_count,
               "planned_native_postflights": spec.postflight_count,
               "lane_statuses": {name: "NOT_RUN_SETUP" for name in spec.lanes},
               "lane_receipts": {}, "device_queries": [], "full_matrix_accepted": False, "release_accepted": False}
    evidence = args.evidence.resolve()
    write(evidence / "batch-worker.json", receipt)
    try:
        frozen, preflight = build_once(args, lane, selections, receipt)
        for selection, ownership in zip(selections, intent["lane_devices"], strict=True):
            name = selection["lane"]
            receipt.update(phase="SHARED_INPUTS_BEFORE_LANE", current_lane=name)
            write(evidence / "batch-worker.json", receipt)
            frozen.verify_current()
            if args.deadline - time.monotonic() < minimum_lane_budget(selection):
                receipt["lane_statuses"].update({item["lane"]: "NOT_RUN_BUDGET"
                    for item in selections if receipt["lane_statuses"][item["lane"]] == "NOT_RUN_SETUP"})
                receipt.update(status="BATCH_BUDGET_EXHAUSTED", phase="BUDGET_LIMIT")
                break
            directory = evidence / "lanes" / name
            directory.mkdir(parents=True, exist_ok=False)
            receipt.update(phase="LANE", current_lane=name)
            receipt["lane_statuses"][name] = "IN_PROGRESS"
            write(evidence / "batch-worker.json", receipt)
            observation = {"lane": name, "phase": "BEFORE_CREATE"}
            receipt["device_queries"].append(observation)
            inventory = scoped_device_inventory(ownership, timeout=SCOPED_DEVICE_QUERY_SECONDS,
                                                observation=observation)
            require(not any(item.get("name") == ownership["name"] for items in inventory["devices"].values() for item in items),
                    "Refuse an existing batch simulator name")
            udid = subprocess.check_output(["xcrun", "simctl", "create", ownership["name"],
                ownership["device"]["identifier"], ownership["runtime"]["identifier"]], text=True, timeout=30).strip()
            device = {**ownership, "udid": udid}
            require(udid.lower() not in {item.lower() for item in intent["baseline_udids"]},
                    "Created batch simulator reused a baseline identity")
            write(directory / "owned-simulator.json", device)
            observation = {"lane": name, "phase": "AFTER_CREATE"}
            receipt["device_queries"].append(observation)
            inventory = scoped_device_inventory(device, timeout=SCOPED_DEVICE_QUERY_SECONDS,
                                                observation=observation)
            validate_owned_device(inventory, device, expected_state="Shutdown")
            local_preflight = {**preflight, "selected": {"ipad": device}}
            write(directory / "preflight/preflight.json", local_preflight)
            (directory / "heart").mkdir()
            (directory / "heart/heart-installation.json").write_bytes(frozen.runtime_receipt_path.read_bytes())
            local = type(args)(app=args.app, evidence=directory, derived=args.derived,
                               lane=name, device="ipad", language="en")
            lane_receipt = {"status": "FAIL", "phase": "PREFLIGHT", "started_at": now(),
                            "same_job_build_receipt_sha256": receipt["build_receipt_sha256"],
                            "full_matrix_accepted": False, "release_accepted": False}
            try:
                context = replace(frozen, device=device)
                try:
                    lane.execute(local, lane_receipt, build_context=context)
                except lane.SelectionFailure as error:
                    observation = qualify_functional_failure(lane_receipt, directory, selection, device, lane.shared)
                    lane_receipt.update(status="LANE_FAILED_OBSERVED_TEST", error_type=type(error).__name__,
                                        error=str(error), observed_failure=observation)
                frozen.verify_current()
                if lane_receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING":
                    lane_receipt["batch_original_results"] = validate_lane_pass(lane_receipt, directory, selection, context)
            except BaseException as error:
                lane_receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "LANE_ABORTED_SETUP_OR_IDENTITY",
                                    error_type=type(error).__name__, error=str(error))
                raise
            finally:
                lane_receipt["finished_at"] = now()
                write(directory / "execution.json", lane_receipt)
                receipt["lane_receipts"][name] = {"path": str((directory / "execution.json").relative_to(evidence)),
                                                 "sha256": digest(directory / "execution.json")}
                receipt["lane_statuses"][name] = lane_receipt["status"]
                write(evidence / "batch-worker.json", receipt)
            shutdown = subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True, timeout=30)
            require(shutdown.returncode == 0, "Could not shut down the lane's owned simulator")
        else:
            receipt.update(status="BATCH_PASS_ACCEPTANCE_REVIEW_PENDING" if all(
                status == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" for status in receipt["lane_statuses"].values())
                else "BATCH_FAILED_OBSERVED_TESTS", phase="COMPLETE")
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "BATCH_ABORTED_SETUP_OR_IDENTITY",
                       error_type=type(error).__name__, error=str(error))
        if isinstance(error, TrackedSourceChanged):
            receipt["tracked_source_change"] = error.observation
        if receipt.get("current_lane") and receipt["lane_statuses"][receipt["current_lane"]] == "IN_PROGRESS":
            receipt["lane_statuses"][receipt["current_lane"]] = "NOT_COMPLETED_SETUP_OR_IDENTITY"
        if isinstance(error, KeyboardInterrupt):
            raise
    finally:
        receipt["finished_at"] = now()
        write(evidence / "batch-worker.json", receipt)
    return 0 if receipt["status"] == "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


def terminate_owned(process):
    require(process.pid != os.getpgrp(), "Refuse the controller's own process group")
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # An exited parent can leave TERM-ignoring owned descendants.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run_worker_command(command, cwd, log, timeout):
    record = {"status": "FAIL", "started_at": now(), "timeout_seconds": timeout, "argv": command}
    process = None
    try:
        with log.open("xb") as stream:
            try:
                process = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                record["worker_pid"] = process.pid
                record["return_code"] = process.wait(timeout=timeout)
                record["status"] = "COMPLETE" if process.returncode == 0 else "WORKER_FAILED"
                terminate_owned(process)
                record["owned_group_cleanup"] = "TERM_THEN_KILL"
            except BaseException as error:
                record.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                              "TIMED_OUT" if isinstance(error, subprocess.TimeoutExpired) else "FAIL",
                              error_type=type(error).__name__)
                if process is not None:
                    try:
                        terminate_owned(process)
                    except BaseException as cleanup_error:
                        record["cleanup_error_type"] = type(cleanup_error).__name__
                raise
            finally:
                stream.flush()
                os.fsync(stream.fileno())
    finally:
        if process is not None:
            record["return_code"] = process.returncode
        record["finished_at"] = now()
        write(log.with_suffix(".command.json"), record)
    return record


def resolve_cleanup_device(inventory, ownership, baseline_udids, created_receipt=None):
    if "udid" in ownership:
        if not any(item.get("udid", "").lower() == ownership["udid"].lower()
                   for items in inventory.get("devices", {}).values() for item in items):
            return None
        validate_owned_device(inventory, ownership)
        return ownership
    matches = [item for items in inventory.get("devices", {}).values()
               for item in items if item.get("name") == ownership["name"]]
    if not matches:
        return None
    require(len(matches) == 1, "Ambiguous cleanup identity; no device was signalled")
    device = {**ownership, "udid": matches[0]["udid"]}
    require(valid_udid(device["udid"]), "Refuse cleanup without a valid created simulator UDID")
    require(device["udid"].lower() not in {item.lower() for item in baseline_udids},
            "Refuse cleanup of a pre-existing simulator matched by name")
    if created_receipt is not None:
        require(created_receipt == device, "Created simulator receipt no longer matches inventory")
    validate_owned_device(inventory, device)
    return device


def cleanup_owned(intent, evidence):
    deadline = time.monotonic() + CLEANUP_SECONDS
    report = {"status": "PASS", "devices": [], "inventory_queries": [], "started_at": now()}
    try:
        for ownership in [*intent["preflight_devices"], *intent["lane_devices"]]:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "Owned cleanup budget exhausted")
            directory = evidence / "lanes" / ownership.get("lane", "preflight")
            created_path = directory / "owned-simulator.json"
            created = None
            query_identity = ownership
            if "udid" not in ownership:
                if not directory.exists():
                    report["devices"].append({"name": ownership["name"], "status": "NOT_STARTED"})
                    continue
                if created_path.exists():
                    created = json.loads(created_path.read_text())
                    require(isinstance(created, dict) and valid_udid(created.get("udid"))
                            and created == {**ownership, "udid": created["udid"]},
                            "Created simulator receipt differs from planned ownership")
                    require(created["udid"].lower() not in {item.lower() for item in intent["baseline_udids"]},
                            "Refuse cleanup of a baseline simulator in a created receipt")
                    query_identity = created
            observation = {}
            report["inventory_queries"].append(observation)
            inventory = scoped_device_inventory(query_identity, timeout=min(SCOPED_DEVICE_QUERY_SECONDS, remaining),
                                                observation=observation)
            device = resolve_cleanup_device(inventory, ownership, intent["baseline_udids"],
                                            created)
            if device is None:
                report["devices"].append({"name": ownership["name"], "status": "NOT_PRESENT"})
                continue
            item = validate_owned_device(inventory, device)
            entry = {"name": device["name"], "udid": device["udid"], "status": "CLEANUP_STARTED"}
            report["devices"].append(entry)
            for action in (["shutdown"] if item["state"] != "Shutdown" else []) + ["delete"]:
                remaining = deadline - time.monotonic()
                require(remaining > 0, "Owned cleanup budget exhausted")
                result = subprocess.run(["xcrun", "simctl", action, device["udid"]], capture_output=True,
                                        timeout=min(20, remaining))
                entry[action + "_exit_code"] = result.returncode
                require(result.returncode == 0, "Owned simulator cleanup failed")
            entry["status"] = "DELETED_OWNED_SIMULATOR"
    except BaseException as error:
        report.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                      error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["finished_at"] = now()
        write(evidence / "batch-cleanup.json", report)
    return report


def validate_worker_conclusion(receipt, intent, evidence, lane):
    spec = profile_spec(intent.get("profile", PROFILE))
    require(receipt.get("protocol") == PROTOCOL and receipt.get("profile") == spec.name
            and receipt.get("planned_ui_methods") == spec.ui_count
            and receipt.get("planned_native_preparations") == spec.preparation_count
            and receipt.get("planned_native_postflights") == spec.postflight_count
            and set(receipt.get("lane_statuses", {})) == set(spec.lanes), "Worker receipt profile differs")
    if receipt.get("status") != "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING":
        require(receipt.get("status") in {"BATCH_FAILED_OBSERVED_TESTS", "BATCH_BUDGET_EXHAUSTED",
                "BATCH_ABORTED_SETUP_OR_IDENTITY", "CANCELLED"}, "Unknown terminal worker status")
        return
    require(all(value == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" for value in receipt["lane_statuses"].values())
            and set(receipt.get("lane_receipts", {})) == set(spec.lanes), "Passing batch lacks every reviewed lane receipt")
    require(receipt.get("source", {}).get("source_sha") == intent["source_sha"], "Passing worker source differs")
    build_path = evidence / "batch-build/same-job-build.json"
    require(digest(build_path) == receipt["build_receipt_sha256"], "Same-job successful build receipt changed")
    build = json.loads(build_path.read_text())
    require(build.get("status") == "SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS"
            and build.get("source") == receipt["source"] and build.get("build_flags") == FLAGS
            and build.get("configuration") == CONFIGURATION and build.get("previous_artifact_reuse") is False,
            "Passing worker has no exact successful same-job build")
    observed_udids, observed_spaces, observed_containers = set(), set(), set()
    totals = {"native_preparations": 0, "ui_methods": 0, "native_postflights": 0}
    for selection in plan(lane, spec.name):
        name = selection["lane"]
        reference = receipt["lane_receipts"][name]
        require(reference.get("path") == "lanes/" + name + "/execution.json", "Lane receipt path differs")
        path = evidence / reference["path"]
        require(digest(path) == reference["sha256"], "Completed lane receipt changed")
        original = json.loads(path.read_text())
        require(original.get("status") == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING"
                and original.get("source_sha") == intent["source_sha"]
                and original.get("run_id") == intent["run_id"] and original.get("run_attempt") == intent["run_attempt"]
                and original.get("same_job_build_receipt_sha256") == receipt["build_receipt_sha256"],
                "Passing lane identity/build binding differs")
        device = json.loads((path.parent / "owned-simulator.json").read_text())
        planned = next(item for item in intent["lane_devices"] if item["lane"] == name)
        require({key: value for key, value in device.items() if key != "udid"} == planned
                and device["udid"].lower() not in {value.lower() for value in intent["baseline_udids"]}
                and device["udid"].lower() not in observed_udids, "Passing lanes reused or changed their owned devices")
        observed_udids.add(device["udid"].lower())
        fresh = json.loads((path.parent / "fresh-container.json").read_text())
        fixture = json.loads((path.parent / "fixture-isolation.json").read_text())
        validate_fresh_device_receipt(fresh, path.parent, device["udid"])
        require(fixture.get("simulator_udid") == device["udid"]
                and fixture.get("space_id") and fixture["space_id"] not in observed_spaces
                and fixture.get("container") and fixture["container"] not in observed_containers,
                "Passing lanes do not retain independent fresh fixture evidence")
        observed_spaces.add(fixture["space_id"])
        observed_containers.add(fixture["container"])
        phases = [("preparation", "prepare", [selection["preparation"]], "native_preparations"),
                  ("ui", "wave15-" + name, selection["methods"], "ui_methods")]
        if selection["postflight"]:
            phases.append(("postflight", preservation.PREFIX, [preservation.METHOD], "native_postflights"))
            preservation.validate_saved(path.parent, original, device["udid"])
        for phase, prefix, expected, total_key in phases:
            summary_path = path.parent / phase / (prefix + "-summary.json")
            tests_path = path.parent / phase / (prefix + "-tests.json")
            observed = validate_observed_result(json.loads(summary_path.read_text()),
                lane.shared.method_results(json.loads(tests_path.read_text())), expected, device["udid"], passing=True)
            totals[total_key] += observed["original_counts"]["passedTests"]
    require(totals == {"native_preparations": spec.preparation_count, "ui_methods": spec.ui_count,
                      "native_postflights": spec.postflight_count}, "Original batch execution counts differ")


def publish_batch_observations(evidence, result):
    """Project only this fresh execution's fixed receipt paths to annotations.

    Worker stdout is retained in its private log. The parent publishes the
    same bounded schema without forwarding that log or reading old artifacts.
    Diagnostic faults never change the original controller result.
    """
    spec = profile_spec(result.get("profile", PROFILE))
    diagnostics.emit_execution(result, spec.name)
    root = evidence.resolve()

    def read_receipt(path, expected_sha):
        if (path.is_symlink() or not path.resolve().is_relative_to(root)
                or not path.is_file()):
            raise ValueError("Diagnostic receipt is unavailable")
        with path.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("Diagnostic receipt identity differs")
        value = json.loads(raw)
        if type(value) is not dict:
            raise ValueError("Diagnostic receipt is not a record")
        return value

    worker_path = root / "batch-worker.json"
    if not worker_path.exists():
        return
    try:
        retained = result.get("retained_worker_receipt", {})
        worker = read_receipt(worker_path, retained.get("sha256"))
        if worker.get("protocol") != PROTOCOL or worker.get("profile") != spec.name:
            raise ValueError("Diagnostic worker profile differs")
        diagnostics.emit_execution(worker, spec.name)
        references = worker.get("lane_receipts", {})
        if type(references) is not dict:
            raise ValueError("Diagnostic worker lane references differ")
    except Exception:
        diagnostics.emit_execution({"status": "DIAGNOSTIC_READ_FAILED"}, spec.name)
        return
    for name in spec.lanes:
        if name not in references:
            continue
        try:
            reference = references[name]
            relative = "lanes/" + name + "/execution.json"
            if type(reference) is not dict or reference.get("path") != relative:
                raise ValueError("Diagnostic lane reference differs")
            value = read_receipt(root / relative, reference.get("sha256"))
            if any(key not in result or value.get(key) != result[key]
                   for key in ("source_sha", "run_id", "run_attempt")):
                raise ValueError("Diagnostic lane source/run identity differs")
            diagnostics.emit_execution(value, name)
        except Exception:
            diagnostics.emit_execution({"status": "DIAGNOSTIC_READ_FAILED"}, name)


def run(args, lane):
    require(sys.platform == "darwin", "Actual Apple host required")
    require(args.device == "ipad" and args.language == "en", "Batch is only the existing iPad English Release lanes")
    require(WORKER_SECONDS + CLEANUP_SECONDS < STEP_SECONDS, "Batch exceeds the existing execution cap")
    evidence = args.evidence.resolve()
    require(not any(path.exists() or path.is_symlink() for path in
                    (evidence / name for name in ("execution.json", "batch-intent.json", "batch-worker.json", "lanes"))),
            "Refuse stale batch evidence")
    spec = profile_spec(getattr(args, "lane", PROFILE))
    plan(lane, spec.name)
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight.get("source_sha") == os.environ.get("GITHUB_SHA")
            and preflight.get("run_id") == os.environ.get("GITHUB_RUN_ID")
            and preflight.get("run_attempt") == os.environ.get("GITHUB_RUN_ATTEMPT")
            and preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN", "Original preflight identity differs")
    token = uuid4().hex
    template = preflight["selected"]["ipad"]
    baseline_raw = subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30)
    baseline = json.loads(baseline_raw)
    for kind, device in preflight["selected"].items():
        require(kind in {"ipad", "iphone"} and device["name"] == "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-" + kind,
                "Original preflight device is not owned by this run")
        validate_owned_device(baseline, device, expected_state="Shutdown")
    intent = {"protocol": PROTOCOL, "profile": spec.name, "token": token, "parent_pid": os.getpid(),
              "source_sha": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
              "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "baseline_udids": sorted(item["udid"] for items in baseline["devices"].values() for item in items),
              "baseline_inventory_sha256": hashlib.sha256(baseline_raw).hexdigest(),
              "preflight_devices": list(preflight["selected"].values()),
              "lane_devices": [{"lane": name, "name": "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-batch-" + token + "-" + name,
                                "device": template["device"], "runtime": template["runtime"]} for name in spec.lanes]}
    require(not any(item.get("name") in {device["name"] for device in intent["lane_devices"]}
                    for items in baseline["devices"].values() for item in items), "Planned simulator name already exists")
    (evidence / "batch-simulator-baseline.json").write_bytes(baseline_raw)
    write(evidence / "batch-intent.json", intent)
    result = {"protocol": PROTOCOL, "profile": spec.name, "status": "FAIL", "started_at": now(),
              "source_sha": intent["source_sha"], "run_id": intent["run_id"], "run_attempt": intent["run_attempt"],
              "planned_ui_methods": spec.ui_count, "planned_native_preparations": spec.preparation_count,
              "planned_native_postflights": spec.postflight_count,
              "full_matrix_accepted": False, "release_accepted": False, "visual_review": "PENDING"}
    write(evidence / "execution.json", result)
    cancellation = None
    previous_handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancellation_latched = False
    finalizing = False

    def cancel_on_signal(signum, frame):
        nonlocal cancellation, cancellation_latched
        if cancellation_latched:
            return
        cancellation_latched = True
        cancellation = cancellation or KeyboardInterrupt("Batch cancellation signal")
        result["status"] = "CANCELLED"
        # The first signal interrupts the worker wait. Finalization remains
        # bounded and must finish its owned cleanup even if more signals arrive.
        if not finalizing:
            raise cancellation

    for number in previous_handlers:
        signal.signal(number, cancel_on_signal)
    try:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--app", str(args.app.resolve()),
                   "--evidence", str(evidence), "--derived", str(args.derived.resolve()),
                   "--deadline", str(time.monotonic() + WORKER_SECONDS)]
        outcome = run_worker_command(command, args.app.resolve(), evidence / "batch-worker.log", WORKER_SECONDS)
        worker_receipt = json.loads((evidence / "batch-worker.json").read_text())
        validate_worker_conclusion(worker_receipt, intent, evidence, lane)
        result.update(worker=worker_receipt, worker_receipt_sha256=digest(evidence / "batch-worker.json"),
                      worker_command=outcome, status=worker_receipt["status"])
        require(outcome["return_code"] == 0 or result["status"] != "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING",
                "Failed worker cannot qualify a passing batch")
    except BaseException as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                      "BATCH_BUDGET_EXHAUSTED" if isinstance(error, subprocess.TimeoutExpired) else "BATCH_ABORTED_SETUP_OR_IDENTITY",
                      error_type=type(error).__name__, error=str(error))
        if isinstance(error, KeyboardInterrupt):
            cancellation, cancellation_latched = cancellation or error, True
    finally:
        finalizing = True
        try:
            result["cleanup"] = cleanup_owned(intent, evidence)
        except BaseException as error:
            result["cleanup_error_type"] = type(error).__name__
            if isinstance(error, KeyboardInterrupt):
                result["status"], cancellation = "CANCELLED", cancellation or error
                cancellation_latched = True
            elif result["status"] == "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING":
                result["status"] = "BATCH_FAILED_CLEANUP"
        try:
            if cancellation is not None:
                result["status"] = "CANCELLED"
            partial = evidence / "batch-worker.json"
            if partial.exists():
                result["retained_worker_receipt"] = {"path": partial.name, "sha256": digest(partial)}
            result["finished_at"] = now()
            write(evidence / "execution.json", result)
            if cancellation is not None:
                # The first signal can arrive while the prior JSON is being
                # serialized; publish the latched status after that write too.
                result["status"] = "CANCELLED"
                write(evidence / "execution.json", result)
        except KeyboardInterrupt as error:
            result["status"], cancellation = "CANCELLED", cancellation or error
            cancellation_latched = True
            result["finished_at"] = now()
            write(evidence / "execution.json", result)
        finally:
            for number, previous in previous_handlers.items():
                signal.signal(number, previous)
    try:
        publish_batch_observations(evidence, result)
    except KeyboardInterrupt as error:
        result["status"], cancellation = "CANCELLED", cancellation or error
        write(evidence / "execution.json", result)
    except Exception:
        diagnostics.emit_execution({"status": "DIAGNOSTIC_READ_FAILED"}, spec.name)
    if cancellation is not None:
        raise cancellation
    print(json.dumps(result))
    return 0 if result["status"] == "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


if __name__ == "__main__":
    import argparse
    import run_wave15_acceptance as lane
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--deadline", type=float, required=True)
    arguments = parser.parse_args()
    sys.exit(worker(arguments, lane, json.loads((arguments.evidence / "batch-intent.json").read_text())))
