"""Opt-in, same-job Release/r14 build for six existing Wave15 UI lanes.

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
import signal
import subprocess
import sys
import time
from uuid import uuid4


PROFILE = "remaining-release"
PROTOCOL = "pinkha-wave15-same-job-batch-v1"
LANES = ("inspector", "inspector-search", "properties", "properties-set", "canonical-properties", "editor")
COUNTS = (5, 1, 3, 2, 1, 3)
UI_COUNT = 15
PREPARATION_COUNT = 6
PREPARATIONS = (
    "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
    "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
    "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
    "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
    "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
    "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
)
CONFIGURATION = "Release-Anytype"
FLAGS = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED", "ENABLE_TESTABILITY=YES",
         "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
         "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
# The existing workflow has a 120-minute execution step and a 150-minute job.
# Leave 12 minutes outside the worker for owned cleanup and final publication.
WORKER_SECONDS = 105 * 60
CLEANUP_SECONDS = 3 * 60
STEP_SECONDS = 120 * 60
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


def plan(lane):
    result = []
    for name, count, preparation in zip(LANES, COUNTS, PREPARATIONS, strict=True):
        item = lane.plan(name, "ipad", "en")
        require(item["build_configuration"] == CONFIGURATION
                and item["expected_ui_executions"] == count
                and item["expected_preparation_executions"] == 1
                and item["preparation"] == preparation,
                "An existing lane changed; review the bounded batch profile")
        result.append(item)
    methods = [method for item in result for method in item["methods"]]
    require(len(methods) == UI_COUNT and len(set(methods)) == UI_COUNT, "Exactly 15 existing UI methods required")
    require(len({item["preparation"].split("/")[0] for item in result}) == 3,
            "Exactly three separately executed preparation suites required")
    return result


def minimum_lane_budget(selection):
    # Every native preparation and UI method retains the existing 300s XCTest
    # ceiling; allow a further 180s for simulator launch, evidence and cleanup.
    return 300 * (1 + selection["expected_ui_executions"]) + 180


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


def source_snapshot(app, shared):
    require(not shared.git(app, "status", "--porcelain", "--untracked-files=no"),
            "Tracked source changed during the same-job build")
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
        inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
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
    require(head == os.environ.get("GITHUB_SHA") and shared.git(app, "branch", "--show-current") == lane.BRANCH,
            "Actual integration source identity differs")
    preflight_path = evidence / "preflight/preflight.json"
    preflight = json.loads(preflight_path.read_text())
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight.get("source_sha") == head
            and preflight.get("run_id") == os.environ.get("GITHUB_RUN_ID"), "Original OS27 preflight identity differs")
    runtime_path = evidence / "heart/heart-installation.json"
    runtime = json.loads(runtime_path.read_text())
    require(runtime.get("status") == "PASS" and runtime.get("app_source_sha") == head
            and runtime.get("marker") == shared.MARKER, "Exact r14 runtime installation is required")
    source = source_snapshot(app, shared)
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
    base = ["xcodebuild", "build-for-testing", "-configuration", CONFIGURATION,
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO"]
    native_suites = sorted({selection["preparation"].split("/")[0] for selection in selections})
    shared.command([*base, "-project", "Anytype.xcodeproj", "-scheme", "Anytype", "-derivedDataPath", str(derived),
                    *["-only-testing:AnytypeTests/" + name for name in native_suites], *FLAGS], app, common)
    built = derived / "Build/Products" / (CONFIGURATION + "-iphonesimulator/Anytype.app")
    shared.verify_signed_simulator(built, common)
    shared.verify_runtime_copies(built, shared.MARKER.encode(), common)
    native_configuration = shared.test_configuration(derived / "Build/Products", "AnytypeTests")
    project = shared.ui_only_project(app)
    ui_derived = derived.with_name(derived.name + "-ui")
    shared.command([*base, "-project", str(project), "-scheme", "PinkhaPrebuiltUI", "-derivedDataPath", str(ui_derived),
                    *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in methods], *FLAGS], app, common)
    ui_configuration = shared.test_configuration(ui_derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    shared.command(["xcrun", "simctl", "shutdown", udid], app, common)
    native_bundles = tuple(sorted((derived / "Build/Products").rglob("AnytypeTests.xctest")))
    require(native_bundles, "Built native XCTest bundle is missing")
    require(source_snapshot(app, shared) == source, "Source or package inputs changed during build")
    frozen = FrozenBuild(app, derived, ui_derived, built, native_configuration, ui_configuration, shared,
                         source, identity["hashes"], {}, native_bundles, runtime_path, digest(runtime_path), {})
    frozen = replace(frozen, artifacts=frozen.observed_artifacts())
    build_record = {"status": "SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS", "source": source,
                    "build_flags": FLAGS, "configuration": CONFIGURATION,
                    "native_preparation_suites_built": native_suites, "ui_methods_built": methods,
                    "artifacts": frozen.artifacts, "runtime_receipt_sha256": frozen.runtime_receipt_sha256,
                    "native_acceptance_reused": False, "ui_acceptance_reused": False,
                    "previous_artifact_reuse": False}
    write(common / "same-job-build.json", build_record)
    receipt["build_receipt_sha256"] = digest(common / "same-job-build.json")
    return frozen, preflight


def qualify_functional_failure(lane_receipt, directory, selection, device, shared):
    phase = lane_receipt.get("phase")
    require(phase in {"PREPARATION", "UI"}, "Failure is outside a named XCTest phase")
    native = phase == "PREPARATION"
    prefix = "prepare" if native else "wave15-" + selection["lane"]
    evidence = directory / ("preparation" if native else "ui")
    expected = [selection["preparation"]] if native else selection["methods"]
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
    for phase, prefix, expected in [("preparation", "prepare", [selection["preparation"]]),
                                    ("ui", "wave15-" + selection["lane"], selection["methods"])]:
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
    selections = plan(lane)
    receipt = {"protocol": PROTOCOL, "status": "FAIL", "phase": "SETUP", "started_at": now(),
               "profile": PROFILE, "planned_ui_methods": UI_COUNT, "planned_native_preparations": PREPARATION_COUNT,
               "lane_statuses": {name: "NOT_RUN_SETUP" for name in LANES},
               "lane_receipts": {}, "full_matrix_accepted": False, "release_accepted": False}
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
            inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
            require(not any(item.get("name") == ownership["name"] for items in inventory["devices"].values() for item in items),
                    "Refuse an existing batch simulator name")
            udid = subprocess.check_output(["xcrun", "simctl", "create", ownership["name"],
                ownership["device"]["identifier"], ownership["runtime"]["identifier"]], text=True, timeout=30).strip()
            device = {**ownership, "udid": udid}
            require(udid.lower() not in {item.lower() for item in intent["baseline_udids"]},
                    "Created batch simulator reused a baseline identity")
            write(directory / "owned-simulator.json", device)
            inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
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
    require(device["udid"].lower() not in {item.lower() for item in baseline_udids},
            "Refuse cleanup of a pre-existing simulator matched by name")
    if created_receipt is not None:
        require(created_receipt == device, "Created simulator receipt no longer matches inventory")
    validate_owned_device(inventory, device)
    return device


def cleanup_owned(intent, evidence):
    deadline = time.monotonic() + CLEANUP_SECONDS
    report = {"status": "PASS", "devices": [], "started_at": now()}
    try:
        for ownership in [*intent["preflight_devices"], *intent["lane_devices"]]:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "Owned cleanup budget exhausted")
            inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"],
                                                          timeout=min(20, remaining)))
            created = evidence / "lanes" / ownership.get("lane", "preflight") / "owned-simulator.json"
            device = resolve_cleanup_device(inventory, ownership, intent["baseline_udids"],
                                            json.loads(created.read_text()) if created.exists() else None)
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
    require(receipt.get("protocol") == PROTOCOL and receipt.get("profile") == PROFILE
            and receipt.get("planned_ui_methods") == UI_COUNT and receipt.get("planned_native_preparations") == PREPARATION_COUNT
            and set(receipt.get("lane_statuses", {})) == set(LANES), "Worker receipt profile differs")
    if receipt.get("status") != "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING":
        require(receipt.get("status") in {"BATCH_FAILED_OBSERVED_TESTS", "BATCH_BUDGET_EXHAUSTED",
                "BATCH_ABORTED_SETUP_OR_IDENTITY", "CANCELLED"}, "Unknown terminal worker status")
        return
    require(all(value == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" for value in receipt["lane_statuses"].values())
            and set(receipt.get("lane_receipts", {})) == set(LANES), "Passing batch lacks six passing lane receipts")
    require(receipt.get("source", {}).get("source_sha") == intent["source_sha"], "Passing worker source differs")
    build_path = evidence / "batch-build/same-job-build.json"
    require(digest(build_path) == receipt["build_receipt_sha256"], "Same-job successful build receipt changed")
    build = json.loads(build_path.read_text())
    require(build.get("status") == "SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS"
            and build.get("source") == receipt["source"] and build.get("build_flags") == FLAGS
            and build.get("configuration") == CONFIGURATION and build.get("previous_artifact_reuse") is False,
            "Passing worker has no exact successful same-job build")
    observed_udids, observed_spaces, observed_containers = set(), set(), set()
    totals = {"native_preparations": 0, "ui_methods": 0}
    for selection in plan(lane):
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
        for phase, prefix, expected, total_key in [
            ("preparation", "prepare", [selection["preparation"]], "native_preparations"),
            ("ui", "wave15-" + name, selection["methods"], "ui_methods")]:
            summary_path = path.parent / phase / (prefix + "-summary.json")
            tests_path = path.parent / phase / (prefix + "-tests.json")
            observed = validate_observed_result(json.loads(summary_path.read_text()),
                lane.shared.method_results(json.loads(tests_path.read_text())), expected, device["udid"], passing=True)
            totals[total_key] += observed["original_counts"]["passedTests"]
    require(totals == {"native_preparations": PREPARATION_COUNT, "ui_methods": UI_COUNT}, "Original batch execution counts differ")


def run(args, lane):
    require(sys.platform == "darwin", "Actual Apple host required")
    require(args.device == "ipad" and args.language == "en", "Batch is only the existing iPad English Release lanes")
    require(WORKER_SECONDS + CLEANUP_SECONDS < STEP_SECONDS, "Batch exceeds the existing execution cap")
    evidence = args.evidence.resolve()
    require(not (evidence / "execution.json").exists() and not (evidence / "batch-intent.json").exists(),
            "Refuse stale batch evidence")
    plan(lane)
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
    intent = {"protocol": PROTOCOL, "token": token, "parent_pid": os.getpid(),
              "source_sha": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
              "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "baseline_udids": sorted(item["udid"] for items in baseline["devices"].values() for item in items),
              "baseline_inventory_sha256": hashlib.sha256(baseline_raw).hexdigest(),
              "preflight_devices": list(preflight["selected"].values()),
              "lane_devices": [{"lane": name, "name": "Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-batch-" + token + "-" + name,
                                "device": template["device"], "runtime": template["runtime"]} for name in LANES]}
    require(not any(item.get("name") in {device["name"] for device in intent["lane_devices"]}
                    for items in baseline["devices"].values() for item in items), "Planned simulator name already exists")
    (evidence / "batch-simulator-baseline.json").write_bytes(baseline_raw)
    write(evidence / "batch-intent.json", intent)
    result = {"protocol": PROTOCOL, "profile": PROFILE, "status": "FAIL", "started_at": now(),
              "source_sha": intent["source_sha"], "run_id": intent["run_id"], "run_attempt": intent["run_attempt"],
              "planned_ui_methods": UI_COUNT, "planned_native_preparations": PREPARATION_COUNT,
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
