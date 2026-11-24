"""Original Return3 and RTL1 on the one fresh coherent Release build.

Only the frozen nine-suite native union is accepted. These four original
methods use new owned devices and selection-only descriptor copies.
"""
from dataclasses import replace
import copy
import importlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import time

import wave15_batch as batch

CURRENT = Path(__file__).resolve().parents[1] / "CurrentAppleValidation"
PORT = Path(__file__).resolve().parents[1] / "AnyEnginePort"
for directory in (CURRENT, PORT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import contracts as c
import current_execution as current
import native_ui_transition_contract as transition
import verify_native_test_execution as execution

for module, directory in ((c, CURRENT), (current, CURRENT),
                          (transition, PORT), (execution, PORT)):
    batch.require(Path(module.__file__).resolve().parent == directory,
                  "Foreign current Release validation module")

PROFILE = "release-return-rtl"
PASS = "COHERENT_ORIGINAL_RETURN3_RTL1_PASS"
KEYS = ("release-return-controls", "release-rtl-preparation")
STAGES = ("return-controls", "preparation")
RETURN_SUITE = "BlockActionServiceReturnFocusTests"
UNION = frozenset((
    RETURN_SUITE,
    "PinkhaStage1AcceptancePreparationTests",
    "SimulatorAcceptancePreparationTests",
    "TorahNativeDerivedProductIntegrationTests",
    "TorahStage2TypePreservationTests",
    "TorahT5UIAcceptancePreparationTests",
    "TorahRelatedDocumentActionTests",
    "TorahT5NativeAccountRetryPendingTests",
    "TorahT5RemainingFreshnessTests",
))


def planned_devices(inventory, token, run_id):
    spec = c.PROFILES[PROFILE]
    batch.require(re.fullmatch(r"[0-9a-f]{32}", token) and run_id.isdigit(),
                  "Focus device ownership requires this run identity")
    runtime = [r for r in inventory["runtimes"] if r.get("identifier") == spec["runtime"]
               and r.get("isAvailable") and r.get("version") == spec["version"]
               and r.get("buildversion") == spec["build"]]
    device = [d for d in inventory["devicetypes"] if d.get("identifier") == spec["device"]]
    batch.require(len(runtime) == len(device) == 1, "Original F runtime/device pair unavailable")
    supported = {d["identifier"] if isinstance(d, dict) else d
                 for d in runtime[0].get("supportedDeviceTypes", [])}
    batch.require(not supported or spec["device"] in supported, "F device unsupported by original runtime")
    return [dict(lane=key, name="Pinkha-UI27-" + run_id + "-batch-" + token + "-" + key,
                 device=device[0], runtime=runtime[0]) for key in KEYS]


def target(value):
    c.require(value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2,
              "focus_requires_original_format2")
    configurations = value.get("TestConfigurations")
    c.require(isinstance(configurations, list) and len(configurations) == 1
              and configurations[0].get("IsEnabled", True) is True, "focus_single_configuration")
    targets = configurations[0].get("TestTargets")
    c.require(isinstance(targets, list) and len(targets) == 1
              and targets[0].get("BlueprintName") == "AnytypeTests"
              and targets[0].get("IsEnabled", True) is True, "focus_exact_native_target")
    return targets[0]


def scope_descriptor(raw, stage, products):
    """Admit the exact coherent union, then reuse the unchanged F path checks."""
    original = plistlib.loads(raw)
    original_target = target(original)
    selected = original_target.get("OnlyTestIdentifiers")
    c.require(isinstance(selected, list) and len(selected) == len(UNION)
              and set(selected) == UNION and not original_target.get("SkipTestIdentifiers", []),
              "focus_original_union_not_exact")
    normalized = copy.deepcopy(original)
    target(normalized)["OnlyTestIdentifiers"] = c.selected_identifiers(PROFILE)
    raw_scoped, proof = c.scope_descriptor(plistlib.dumps(normalized, sort_keys=False),
                                          PROFILE, stage, products)
    scoped = plistlib.loads(raw_scoped)
    inverse = copy.deepcopy(scoped)
    target(inverse)["OnlyTestIdentifiers"] = list(selected)
    c.require(inverse == original, "focus_nonselection_descriptor_delta")
    proof.update(originalSHA256=c.sha(raw), originalCoherentUnion=sorted(UNION),
                 originalUnionCount=len(UNION), exactInverse=True)
    return raw_scoped, proof


class Commands:
    def __init__(self, context, pair, directory):
        self.context, self.pair, self.directory = context, pair, directory

    def run(self, argv, name, timeout):
        _, log = self.pair.run_logged(argv, self.context.app, self.directory, name, timeout,
                                     cleanup_profile=batch.COHERENT_HEART_PROFILE)
        return log


def read(path):
    return json.loads(Path(path).read_bytes())


def run_stage(args, frozen, ownership, intent, stage, receipt):
    import run_t5_apple_pair as pair
    key = ownership["lane"]
    directory = args.evidence.resolve() / "lanes" / key
    directory.mkdir(parents=True, exist_ok=False)
    result = dict(status="FAIL", stage=stage, source_sha=intent["source_sha"],
                  run_id=intent["run_id"], run_attempt=intent["run_attempt"],
                  selected=c.selected_identifiers(PROFILE, stage), testCommandInvoked=False,
                  additional_app_builds=0, additional_ui_runner_builds=0,
                  same_job_build_receipt_sha256=receipt["build_receipt_sha256"])
    batch.write(directory / "execution.json", result)
    commands = Commands(frozen, pair, directory / "commands")
    device = None
    ready = False
    try:
        frozen.verify_current()
        before = batch.scoped_device_inventory(ownership, timeout=30)
        batch.require(not any(before["devices"].values()), "Focus simulator name already exists")
        log = commands.run(["xcrun", "simctl", "create", ownership["name"],
                            ownership["device"]["identifier"], ownership["runtime"]["identifier"]],
                           "create-owned-device", 30)
        udid = log.read_text().strip()
        batch.require(batch.valid_udid(udid)
                      and udid.lower() not in {v.lower() for v in intent["baseline_udids"]},
                      "Focus destination is not a new owned device")
        device = dict(ownership, udid=udid)
        batch.write(directory / "owned-simulator.json", device)
        context = replace(frozen, device=device)
        context.prepare_fresh_device(udid, directory)
        ready = True
        context.confirm_empty_container(udid, directory)
        products = frozen.derived / "Build/Products"
        raw, binding = scope_descriptor(frozen.native_configuration.read_bytes(), stage, products)
        selected = products / ("UI27-Coherent-F4-" + key + ".xctestrun")
        batch.require(not selected.exists(), "Focus descriptor replay forbidden")
        with selected.open("xb") as stream:
            stream.write(raw)
        binding.update(copiedPath=str(selected), copiedSHA256=batch.digest(selected),
                       originalPath=str(frozen.native_configuration))
        batch.write(directory / "descriptor-binding.json", binding)
        bundle = directory / "original.xcresult"
        command = c.test_command(PROFILE, stage, selected, udid, bundle)
        command += ["-collect-test-diagnostics", "never"]
        enumeration = c.enumeration_command(command, directory / "enumeration.json")
        batch.write(directory / "plan.json", dict(command=command, enumeration=enumeration,
                    diagnosticsPolicy="never", unchangedAssertions=True))
        commands.run(enumeration, "enumerate", 180)
        result["enumeration"] = c.validate_enumeration(read(directory / "enumeration.json"),
            PROFILE, stage, transition.enumerated_identifiers)
        frozen.verify_current()
        batch.require(batch.digest(selected) == binding["copiedSHA256"],
                      "Focus descriptor changed during enumeration")
        names, allowance = c.PROFILES[PROFILE]["stages"][stage]
        timeout = len(names) * allowance + 300
        batch.require(args.deadline - time.monotonic() > timeout,
                      "Original focus execution allowance exceeds remaining bounded batch")
        result["testCommandInvoked"] = True
        batch.write(directory / "execution.json", result)
        outcome, log = pair.run_logged(command, frozen.app, directory / "commands",
            "test", timeout, check=False, cleanup_profile=batch.COHERENT_HEART_PROFILE)
        result["commandExitCode"] = outcome.get("return_code")
        for kind in ("summary", "tests"):
            pair.run_logged(["xcrun", "xcresulttool", "get", "test-results", kind,
                             "--path", str(bundle), "--format", "json"],
                frozen.app, directory / "commands", "export-" + kind, 120,
                output=directory / (kind + ".json"), cleanup_profile=batch.COHERENT_HEART_PROFILE)
        commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(bundle),
                      "--output-path", str(directory / "private-attachments")], "attachments", 120)
        summary, tests = read(directory / "summary.json"), read(directory / "tests.json")
        result["partialNamed"] = execution.test_cases(tests)
        if outcome.get("return_code") == 0:
            result["actual"] = c.validate_results(summary, tests, PROFILE, stage, udid, execution.test_cases)
            result["rawNamed"] = current.raw_terminal(log.read_bytes(), PROFILE, stage,
                                                       result["actual"]["actualCases"], {})
            result["installedCurrentApplication"] = current.installed_app(
                commands, device, frozen.built, batch.BUNDLE, stage)
            result["status"] = "PASS"
        else:
            observed = batch.validate_observed_result(summary, frozen.shared.method_results(tests),
                                                       names, udid, passing=False)
            batch.require(all(d.get("osVersion") == c.PROFILES[PROFILE]["version"]
                              and d.get("osBuildNumber") == c.PROFILES[PROFILE]["build"]
                              for d in observed["actual_devices"]), "Failed focus result runtime differs")
            result.update(status="FAILED_OBSERVED_TEST", originalFailure=observed)
        frozen.verify_current()
        batch.require(batch.digest(selected) == binding["copiedSHA256"],
                      "Focus copied descriptor changed during execution")
    except BaseException as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL_SETUP_OR_IDENTITY",
                      error_type=type(error).__name__, error=str(error))
        raise
    finally:
        try:
            frozen.verify_current()
            result["originalFrozenProductsUnchanged"] = True
            if ready:
                commands.run(["xcrun", "simctl", "shutdown", device["udid"]], "shutdown-owned-device", 30)
                result["ownedDeviceShutdown"] = True
        finally:
            result["finished_at"] = batch.now()
            batch.write(directory / "execution.json", result)
    return result


def execute(args, frozen, receipt, intent):
    worker_class = getattr(sys.modules.get("__main__"), "FrozenBuild", batch.FrozenBuild)
    batch.require(frozen.profile == batch.COHERENT_HEART_PROFILE
                  and isinstance(frozen, (batch.FrozenBuild, worker_class)),
                  "F4 requires the fresh same-job coherent frozen build")
    planned = intent.get("focus_devices", [])
    batch.require([d.get("lane") for d in planned] == list(KEYS), "Exact F4 ownership intent missing")
    build = read(args.evidence.resolve() / "batch-build/same-job-build.json")
    batch.require(set(build["native_preparation_suites_built"] + build["native_postflight_suites_built"]) == UNION
                  and len(build["native_preparation_suites_built"]) + len(build["native_postflight_suites_built"]) == len(UNION)
                  and build["build_flags"] == batch.profile_flags(batch.COHERENT_HEART_PROFILE)
                  and build["app_builds"] == build["ui_runner_builds"] == 1,
                  "Coherent original build selection or flags differ")
    proof = args.evidence.resolve() / "coherent-focus"
    proof.mkdir(exist_ok=False)
    result = dict(status="RUNNING", source_sha=intent["source_sha"], run_id=intent["run_id"],
                  run_attempt=intent["run_attempt"], same_job_build_receipt_sha256=receipt["build_receipt_sha256"],
                  stages={}, additional_app_builds=0, additional_ui_runner_builds=0,
                  release_accepted=False, physical_device_accepted=False)
    batch.write(proof / "result.json", result)
    try:
        for stage, ownership in zip(STAGES, planned, strict=True):
            actual = run_stage(args, frozen, ownership, intent, stage, receipt)
            result["stages"][stage] = dict(status=actual["status"], path="lanes/" + ownership["lane"] + "/execution.json",
                sha256=batch.digest(args.evidence.resolve() / "lanes" / ownership["lane"] / "execution.json"))
            batch.write(proof / "result.json", result)
        result["status"] = PASS if all(v["status"] == "PASS" for v in result["stages"].values()) else "FAILED_OBSERVED_TESTS"
    finally:
        result["finished_at"] = batch.now()
        batch.write(proof / "result.json", result)
    return result


def validate_saved(evidence, intent, worker):
    result = read(evidence / "coherent-focus/result.json")
    batch.require(worker.get("coherent_focus") == result
                  and worker.get("coherent_focus_receipt") == {"path": "coherent-focus/result.json",
                      "sha256": batch.digest(evidence / "coherent-focus/result.json")},
                  "Original F4 worker reference changed")
    batch.require(result.get("status") == PASS
                  and all(result.get(k) == intent[k] for k in ("source_sha", "run_id", "run_attempt"))
                  and result.get("same_job_build_receipt_sha256") == worker["build_receipt_sha256"]
                  and result.get("additional_app_builds") == result.get("additional_ui_runner_builds") == 0,
                  "Passing batch lacks exact current F4 proof")
    observed = set()
    for stage, key in zip(STAGES, KEYS, strict=True):
        directory = evidence / "lanes" / key
        record = result["stages"][stage]
        batch.require(record == dict(status="PASS", path="lanes/" + key + "/execution.json",
                                     sha256=batch.digest(directory / "execution.json")),
                      "Original F4 stage receipt changed")
        original, device = read(directory / "execution.json"), read(directory / "owned-simulator.json")
        planned = next(d for d in intent["focus_devices"] if d["lane"] == key)
        batch.require(device == dict(planned, udid=device["udid"])
                      and device["udid"].lower() not in observed
                      and device["udid"].lower() not in {x.lower() for x in intent["baseline_udids"]},
                      "Original F4 device identity was reused or changed")
        observed.add(device["udid"].lower())
        batch.require(original.get("status") == "PASS" and original.get("testCommandInvoked") is True
                      and original.get("commandExitCode") == 0
                      and original.get("originalFrozenProductsUnchanged") is True,
                      "Original F4 invocation was incomplete")
        c.validate_results(read(directory / "summary.json"), read(directory / "tests.json"),
                           PROFILE, stage, device["udid"], execution.test_cases)
        current.raw_terminal((directory / "commands/test.log").read_bytes(), PROFILE, stage, {}, {})
    return dict(status=PASS, return_methods=3, preparation_methods=1, failed=0, skipped=0)
