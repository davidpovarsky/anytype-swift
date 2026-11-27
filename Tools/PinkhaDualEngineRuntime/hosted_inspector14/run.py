#!/usr/bin/env python3
"""Closed original Inspector queued requests2/14 in the same successful producer's GitHub job.

No build, account preparation, cross-host relocation, source override or old
Mac entry point is used. Runtime evidence is recorded separately from producer
evidence; an admitted build is never called a passing test run.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time
import uuid

sys.dont_write_bytecode = True

import admission
from originals import Originals, require
import profile_binding
from native23_receipts import Native23Receipts

LANES = profile_binding.LANES
LANE_SCOPE = profile_binding.LANE_SCOPE
DEVICE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"


class CommandAdmission:
    """Latch unresolved original ownership before any subsequent command.

    The original Commands implementation still owns spawn/wait/terminate/reap.
    This adapter only closes admission; it never signals a group, clears an
    original observation or resumes after a later read-only absence proof.
    """
    def __init__(self, original, error_formatter):
        self.original, self.error = original, error_formatter
        self.root, self.cwd = original.root, original.cwd
        self.environment = original.environment
        self.groups, self.absent_groups = original.groups, original.absent_groups
        self.blocked = None
        self.first_exception = None

    def _latch(self, label, error=None):
        unresolved = sorted(set(self.groups).difference(self.absent_groups))
        if unresolved and self.blocked is None:
            self.blocked = {"status": "CLOSED_UNRESOLVED_ORIGINAL_OWNED_GROUP", "label": label,
                            "groupsAtClosure": unresolved, "at": time.time()}
            if error is not None:
                self.blocked["firstFailure"] = self.error(error)

    @property
    def is_open(self):
        self._latch("before-next-operation")
        return self.blocked is None

    def run(self, argv, label, timeout=120, **kwargs):
        require(self.is_open, "Original owned group is unresolved; subsequent command admission is closed")
        try:
            return self.original.run(argv, label, timeout, **kwargs)
        except BaseException as error:
            if self.first_exception is None:
                self.first_exception = self.error(error)
            self._latch(label, error)
            raise
        finally:
            self._latch(label)

    def present(self, group):
        # Only the unchanged final observer uses this read-only operation.
        return self.original.present(group)


def retain_receipt(shared, path, value, phase):
    """Keep the first failure in memory even when exclusive receipt IO fails."""
    try:
        shared.write(path, value)
        return True
    except BaseException as error:
        observation = {"phase": phase, "path": str(path), **shared.error(error)}
        value.setdefault("firstFailure", observation)
        value.setdefault("receiptFailures", []).append(observation)
        value["status"] = "FAIL"
        return False


def select_runtime(inventory):
    """Select only an observed, unambiguous available OS27 runtime and original iPad type."""
    require(isinstance(inventory, dict) and isinstance(inventory.get("runtimes"), list)
            and isinstance(inventory.get("devicetypes"), list), "Original simctl runtime inventory missing")
    candidates = [row for row in inventory["runtimes"] if isinstance(row, dict)
                  and row.get("isAvailable") is True and isinstance(row.get("version"), str)
                  and row["version"].split(".")[0] == "27"
                  and str(row.get("identifier", "")).startswith("com.apple.CoreSimulator.SimRuntime.iOS-")]
    require(len(candidates) == 1, "One actual available OS27 iOS runtime is required; ambiguity needs review")
    runtime = candidates[0]
    require(isinstance(runtime.get("buildversion"), str) and runtime["buildversion"],
            "Actual runtime build identity missing")
    devices = [row for row in inventory["devicetypes"] if isinstance(row, dict)
               and row.get("identifier") == DEVICE_TYPE and str(row.get("name", "")).startswith("iPad")]
    require(len(devices) == 1, "The original OS27 iPad device type is not actually installed")
    supported = runtime.get("supportedDeviceTypes", [])
    require(isinstance(supported, list), "Unknown installed runtime support inventory")
    identities = {row.get("identifier") if isinstance(row, dict) else row for row in supported}
    require(not supported or DEVICE_TYPE in identities, "Observed runtime does not support the original iPad type")
    return runtime, devices[0]


def fresh_toolchain(commands, originals, context):
    observations = context["toolchain"]["observations"]
    expected = {tuple(row["argv"]): row for row in observations}
    required = {("xcodebuild", "-version"), ("xcrun", "swift", "--version"),
                ("xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version")}
    require(len(observations) == 3 and set(expected) == required,
            "Exactly three original producer toolchain observations are required")
    results = []
    for index, argv in enumerate(sorted(required)):
        row = expected[argv]
        reference = {"path": row["path"], "sha256": row["sha256"]}
        old = originals.gate.read_ref(reference)
        require(row["exitCode"] == 0, "Original toolchain command failed")
        log, outcome = commands.run(list(argv), "runtime-toolchain-" + str(index), 60)
        actual = originals.shared.raw(log)
        require(actual.strip() == old.strip(), "Actual same-job Apple toolchain changed after compilation")
        results.append({"argv": list(argv), "producerObservation": reference,
                        "runtimeObservation": admission.ref(log), "commandStatus": outcome["status"]})
    return results


def clone_products(contract, products, root, originals, commands, built, clone_progress):
    """Same-host APFS clones, preserving original descriptor and complete mode inventory."""
    shared = originals.shared
    for label in ("app", "ui"):
        slot = label + "-derived"
        original = originals.gate.canonical(products[slot]["base"], directory=True)
        originals.gate.verify_inventory(original, products[slot]["entries"])
        observed = shared.inventory(original)
        destination = root / (label + "-products")
        require(not destination.exists() and not destination.is_symlink(), "Fresh owned product clone required")
        clone_progress[label] = {"status": "STARTED", "source": str(original), "destination": str(destination)}
        previous = os.umask(0)
        try:
            commands.run(["cp", "-cR", str(original), str(destination)], "clone-" + label + "-products", 180)
        finally:
            os.umask(previous)
        require(shared.inventory(destination) == observed, "Cloned original product bytes/modes/links differ")
        descriptor = destination / contract["descriptors"][label]["path"]
        target = "AnytypeTests" if label == "app" else "PinkhaStage1AcceptanceUITests"
        _, _, entry = originals.products.entries(descriptor, target)
        original_descriptor = original / contract["descriptors"][label]["path"]
        require(descriptor.parent == destination and descriptor.suffix == ".xctestrun"
                and shared.raw(descriptor) == shared.raw(original_descriptor), "Original compiled descriptor changed")
        selection = entry.get("OnlyTestIdentifiers", [])
        require(isinstance(selection, list) and all(isinstance(value, str) for value in selection),
                "Unknown original compiled descriptor selection")
        built[label] = {"products": destination, "inventory": observed, "copies": {},
                        "descriptor": descriptor, "originalSelection": selection}
        shared.write(root / "evidence" / (label + "-original-products.json"), observed)
        clone_progress[label]["status"] = "VERIFIED_ORIGINAL_BYTES_MODES_AND_LINKS"
    _, _, entry = originals.products.entries(built["app"]["descriptor"], "AnytypeTests")
    app = originals.paths.product_path(entry["TestHostPath"], built["app"]["products"])
    info, executable = originals.products.bundle_executable(app)
    require(info.get("CFBundleExecutable") == "Anytype" and isinstance(info.get("CFBundleIdentifier"), str)
            and info["CFBundleIdentifier"] and executable.is_file(), "Original native App host identity is incomplete")
    return app, info["CFBundleIdentifier"]


def verify_created_device(consumer, lane, udid, runtime, device_type, *, state="Booted"):
    suffix = "-owned-device-readback" if state == "Booted" else "-owned-shutdown-readback"
    log, _ = consumer.command(["xcrun", "simctl", "list", "devices", "--json"], lane + suffix, 60,
                              capacity=state == "Booted")
    value = consumer.shared_module.decode(consumer.shared_module.raw(log))
    require(isinstance(value.get("devices"), dict), "Actual owned device inventory missing")
    matches = [(key, row) for key, rows in value["devices"].items() for row in rows
               if isinstance(row, dict) and str(row.get("udid", "")).lower() == udid.lower()]
    require(len(matches) == 1, "Created original simulator is absent or duplicated")
    key, row = matches[0]
    require(key == runtime["identifier"] and row.get("state") == state and row.get("isAvailable") is True
            and row.get("deviceTypeIdentifier") == device_type["identifier"]
            and row.get("name") == "F-Combined-" + consumer.binding["nonce"] + "-" + lane,
            "Actual new device differs from its original create command")
    return {"runtime": key, "device": row, "originalInventory": admission.ref(log)}


def source_contract_for_lane(consumer, lane, originals, producer_pin):
    """Delegate to one original component lane instance under the original command barrier."""
    require(lane in LANES and consumer.profile_bindings.originals is originals,
            "Only the one fixed lanes and actual original Core22 loader are permitted")
    return consumer.profile_bindings.source_contract(lane,
        source_commit=consumer.binding["sourceSHA"], native_compilation_proof=producer_pin)


def execute_lane(consumer, lane, originals, context, runtime, device_type):
    require(lane in LANES, "Only the one fixed original component lanes are permitted")
    shared = originals.shared
    directory = consumer.root / "evidence/lanes" / lane
    directory.mkdir(parents=True, mode=0o700)
    result = {"status": "FAIL", "lane": lane, "sourceCommit": consumer.binding["sourceSHA"],
              "originalTarget": None, "executedTarget": "AnytypeTests",
              "errors": [], "actualNativeACLAccepted": False, "actualNativePersistenceAccepted": False,
              "applicationUIAccepted": False, "physicalDeviceAccepted": False, "releaseAccepted": False}
    udid, devices_before = None, set(consumer.devices)
    producer_pin = context["build"]["nativeCompilationProof"]
    def source_contract():
        return source_contract_for_lane(consumer, lane, originals, producer_pin)
    try:
        before = source_contract()
        require((before["expected_methods"], before["declared_cases"]) == LANE_SCOPE[lane],
                "Original exact Inspector queued requests2/14 method and argument scope differs")
        require(before["original_target"] == profile_binding.ORIGINAL_TARGETS[lane]
                and before["selected_target"] == "AnytypeTests", "Original source target identity differs")
        result["originalTarget"] = before["original_target"]
        result["sourceContract"] = before
        udid, _ = consumer.create(lane, directory, editor=False)
        result["actualDevice"] = verify_created_device(consumer, lane, udid, runtime, device_type)
        methods = [name.removeprefix("AnytypeTests/") for name in before["expected_compiled_identifiers"]]
        actual, _ = consumer.stage(directory, "native", udid, methods, {}, allowance=300, host_contract=before)
        require(source_contract() == before, "Original source/compiler witness changed during runtime")
        originals.unchanged()
        result.update(status="PASS_ORIGINAL_HOSTED_INSPECTOR_SUITE", actual=actual)
    except BaseException as error:
        result["firstFailure"] = consumer.commands.first_exception or shared.error(error)
        if result["firstFailure"] != shared.error(error):
            result["laterFailure"] = shared.error(error)
    finally:
        created = [value for value in consumer.devices if value not in devices_before]
        if udid is None and len(created) == 1:
            udid = created[0]
        if len(created) > 1:
            result["errors"].append({"phase": "owned-create", "error": "Unexpected multiple owned devices"})
        if udid is None and (consumer.commands.root / (lane + "-create") / "original.log").exists():
            # The original create call may have exited before its group proof
            # failed. No broad lookup or another owner's shutdown is permitted.
            result["errors"].append({"phase": "owned-create", "error": "Create command began without admitted owned UUID"})
        if udid:
            if consumer.commands.is_open:
                try:
                    result["privateEvidence"] = consumer.preserve(udid, directory, lane)
                except BaseException as error:
                    result["errors"].append({"phase": "private-retention", **shared.error(error)})
            if consumer.commands.is_open:
                try:
                    consumer.command(["xcrun", "simctl", "shutdown", udid], lane + "-shutdown", 60, capacity=False)
                    observed = verify_created_device(consumer, lane, udid, runtime, device_type, state="Shutdown")
                    result["ownedSimulator"] = {"udid": udid, "status": "SHUTDOWN_RETAINED_UNTIL_JOB_TEARDOWN",
                                                 "deleted": False, "originalObservation": observed}
                except BaseException as error:
                    result["errors"].append({"phase": "owned-shutdown", **shared.error(error)})
            if not consumer.commands.is_open:
                result["ownedSimulator"] = {"udid": udid, "status": "UNRESOLVED_NO_FURTHER_DEVICE_OPERATION",
                                             "deleted": False}
                result["errors"].append({"phase": "owned-command-admission", **consumer.commands.blocked})
        try:
            result["productsUnchanged"] = {key: shared.product_integrity(value) for key, value in consumer.built.items()}
        except BaseException as error:
            result["errors"].append({"phase": "products", **shared.error(error)})
        if result["errors"]:
            result["status"] = "FAIL"
            result.setdefault("firstFailure", result["errors"][0])
        result["testInvoked"] = udid in consumer.invoked_devices if udid else False
        result["finishedAt"] = time.time()
        retain_receipt(shared, directory / "execution.json", result, "lane-terminal-receipt")
    return result


def lane_summary(directory, originals, *, execution=None):
    """Retain failed original runtime evidence without relabeling it NOT_RUN."""
    shared = originals.shared
    execution_path, native = directory / "execution.json", directory / "native/result.json"
    row = {"status": "FAIL_NO_TERMINAL_LANE_RECEIPT", "testInvoked": bool(execution and execution.get("testInvoked")),
           "qualifiedMethods": 0, "qualifiedCases": 0}
    if execution is not None:
        for key in ("firstFailure", "receiptFailures", "ownedSimulator"):
            if key in execution:
                row[key] = execution[key]
        row["cleanupErrors"] = execution["errors"]
    if execution_path.is_file():
        try:
            value = shared.decode(shared.raw(execution_path))
            require(execution is None or value == execution, "Original terminal lane receipt is incomplete or changed")
            row.update(status=value["status"], receipt=admission.ref(execution_path), cleanupErrors=value["errors"])
            if "ownedSimulator" in value:
                row["ownedSimulator"] = value["ownedSimulator"]
        except BaseException as error:
            row["terminalReceiptError"] = shared.error(error)
    if native.is_file():
        try:
            value = shared.decode(shared.raw(native))
            require(type(value["testInvoked"]) is bool, "Original native invocation observation is missing")
            require(execution is None or "actual" not in execution or value == execution["actual"],
                    "Original native result differs from the observed suite outcome")
            row.update(nativeResult=admission.ref(native), nativeStatus=value["status"], testInvoked=value["testInvoked"])
            if "firstFailure" in value:
                row["originalNativeFirstFailure"] = value["firstFailure"]
            if value["status"] == "PASS":
                observed = value["actualHostCases"]
                row["originalValidatorCounts"] = {"methods": observed["actual_method_count"],
                                                   "cases": observed["declared_case_count"]}
                if row["status"] == "PASS_ORIGINAL_HOSTED_INSPECTOR_SUITE":
                    row.update(qualifiedMethods=observed["actual_method_count"],
                               qualifiedCases=observed["declared_case_count"])
        except BaseException as error:
            row.update(status="FAIL", nativeReceiptError=shared.error(error))
    return row


def include_lane_cleanup(cleanup, series):
    """A terminal process proof cannot hide failed private retention/shutdown."""
    for lane, row in series.items():
        for error in row.get("cleanupErrors", []):
            cleanup["status"] = "FAIL"
            cleanup["errors"].append({"lane": lane, **error})
        if row["status"] in ("STARTED", "FAIL_NO_TERMINAL_LANE_RECEIPT"):
            cleanup["status"] = "FAIL"
            cleanup["errors"].append({"lane": lane, "phase": "lane-receipt", "error": "Owned cleanup is not recorded"})
    return cleanup


def run(args, originals):
    profile_binding.require_runtime_ready()
    shared = originals.shared
    plan = shared.decode(shared.raw(args.plan))
    job = admission.bind_job(args, plan)
    control_before = admission.control_identity(args.control, plan["controlCommit"])
    require(Path(__file__).resolve() == args.control / admission.CONTROL_PREFIX / "run.py",
            "Runtime entry point must be the original admitted control file")
    source_before = admission.identity(args.source, plan["appSourceSHA"], plan["appSourceTree"])
    owner = admission.load_hosted_owner(args.control)
    context = admission.producer_context(args, plan, originals, owner)
    native23_reader = Native23Receipts(args.control, args.source, context, plan, owner, originals)
    output = args.output
    require(output.is_absolute() and output.parent.resolve() == output.parent and not output.exists()
            and not output.is_symlink(), "Fresh exclusive same-job execution output required")
    output.mkdir(mode=0o700)
    (output / "evidence").mkdir(mode=0o700)
    commands = CommandAdmission(shared.Commands(output / "commands", output), shared.error)
    # The original lifecycle and all command bodies remain unchanged. Bind its
    # environment to the original producer's actually observed selected Xcode.
    commands.environment["DEVELOPER_DIR"] = job["developerDir"]
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        commands.environment.pop(name, None)
    result = {"schema": "pinkha-hosted-inspector14-runtime-v1", "status": "FAIL", "startedAt": time.time(),
              "job": job, "sourceIdentity": source_before, "controlIdentity": control_before,
              "rootPlan": context["planRef"], "originalBuildReceipt": context["buildRef"],
              "native23CompilerAdmission": native23_reader.proof(),
              "expectedMethods": 2, "expectedCases": 14, "series": {lane: {"status": "NOT_RUN"} for lane in LANES},
              "qualifiedMethodsPassed": 0, "qualifiedCasesPassed": 0, "testCommandsInvoked": 0,
              "appBuilds": 0, "nativeBuilds": 0, "uiTestMethodsInvoked": 0,
              "nativePersistenceAccepted": False, "nativeACLAccepted": False, "appUIAccepted": False,
              "releaseAccepted": False, "testFlightAccepted": False, "physicalDevice": "NOT_RUN"}
    built, contract, consumer, clone_progress = {}, None, None, {}
    profile_bindings = None
    with originals.signals.cancellation_signals():
        try:
            shared.write(output / "evidence/job-admission.json", result)
            result["runtimeToolchain"] = fresh_toolchain(commands, originals, context)
            log, _ = commands.run(["xcodebuild", "-help"], "xcode-help", 30)
            help_text = shared.raw(log).decode()
            require("-collect-test-diagnostics" in help_text and "never" in help_text,
                    "Original documented bounded diagnostic option unavailable")
            log, _ = commands.run(["xcrun", "simctl", "list", "--json"], "original-simulator-inventory", 60)
            runtime, device_type = select_runtime(shared.decode(shared.raw(log)))
            result["runtimeDiscovery"] = {"originalInventory": admission.ref(log), "runtime": runtime, "deviceType": device_type}
            contract, proof, products, contract_ref = admission.receipt_contract(context, output, originals, runtime, device_type)
            result.update(receiptContract=contract_ref, commonBuildAdmission=proof)
            profile_bindings = profile_binding.RuntimeBindings(originals, commands, args.control)
            result["originalComponentProfileBinding"] = profile_bindings.proof
            app, bundle_id = clone_products(contract, products, output, originals, commands, built, clone_progress)
            originals.configure_runtime(runtime=runtime, bundle_id=bundle_id)
            shared.write(output / "evidence/original-controller-declarations.json", originals.proof)
            binding = {"sourceSHA": plan["appSourceSHA"], "runID": job["runID"],
                       "runAttempt": job["runAttempt"], "nonce": uuid.uuid4().hex}
            settings = {"sourceRoot": str(args.source), "deviceType": device_type["identifier"],
                        "deviceFamily": "ipad", "appLanguage": "en", "appearance": "light"}
            consumer = profile_bindings.host.Consumer(output, settings, commands, built, app, originals.helpers, binding)
            consumer.profile_bindings = profile_bindings
            consumer.source_admission = source_before
            for lane in LANES:
                result["series"][lane] = {"status": "STARTED"}
                execution = None
                try:
                    execution = execute_lane(consumer, lane, originals, context, runtime, device_type)
                except BaseException as error:
                    result.setdefault("firstFailure", commands.first_exception or shared.error(error))
                    raise
                finally:
                    if execution is not None and "firstFailure" in execution:
                        result.setdefault("firstFailure", {"lane": lane, **execution["firstFailure"]})
                    result["series"][lane] = lane_summary(output / "evidence/lanes" / lane, originals, execution=execution)
                    result["qualifiedMethodsPassed"] = sum(row.get("qualifiedMethods", 0) for row in result["series"].values())
                    result["qualifiedCasesPassed"] = sum(row.get("qualifiedCases", 0) for row in result["series"].values())
                    result["testCommandsInvoked"] = sum(row.get("testInvoked", False) for row in result["series"].values())
                    retained = retain_receipt(shared, output / "evidence" / (lane + "-checkpoint.json"),
                                              result, "lane-checkpoint-receipt")
                require(retained, "Inspector queued requests2/14 checkpoint retention failed; no later suite may start")
                require(result["series"][lane]["status"] == "PASS_ORIGINAL_HOSTED_INSPECTOR_SUITE",
                        "Original Inspector queued requests2/14 suite failed: " + lane)
            require(all(row["status"] == "PASS_ORIGINAL_HOSTED_INSPECTOR_SUITE" for row in result["series"].values())
                    and result["qualifiedMethodsPassed"] == 2 and result["qualifiedCasesPassed"] == 14,
                    "Every original Inspector queued requests2/14 method/argument case must actually pass")
            result.update(status="PASS_ORIGINAL_HOSTED_INSPECTOR_METHODS_2_CASES_14", actualMethodsPassed=2, actualCasesPassed=14)
        except BaseException as error:
            result.setdefault("firstFailure", commands.first_exception or shared.error(error))
        finally:
            cleanup = include_lane_cleanup(originals.host_functions.observe_owned_groups(commands), result["series"])
            if commands.blocked is not None:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"phase": "owned-command-admission", **commands.blocked})
            try:
                result["productCloneProgress"] = clone_progress
                result["finalProducts"] = {name: shared.product_integrity(value) for name, value in built.items()}
                originals.unchanged()
                if profile_bindings is not None:
                    profile_bindings.unchanged()  # File-only after any owned-command closure.
                result["native23CompilerFinal"] = native23_reader.recheck()
                # File-only third-compiler/product/source readback remains safe
                # after a blocked original command. Do not start unmanaged Git
                # or admission subprocesses while owned custody is unresolved.
                if commands.is_open:
                    require(admission.identity(args.source, plan["appSourceSHA"], plan["appSourceTree"]) == source_before,
                            "Original compiled source identity changed during tests")
                    require(admission.control_identity(args.control, plan["controlCommit"]) == control_before,
                            "Original runtime controller identity changed during tests")
                    if contract is not None:
                        originals.gate.verify_source(contract["source"])
                        originals.gate.verify_controls(contract["controls"])
                else:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append({"phase": "subprocess-postflight-withheld",
                        "reason": "Unresolved original ownership forbids new Git/admission commands"})
                if contract is not None:
                    for slot, record in products.items():
                        originals.gate.verify_inventory(record["base"], record["entries"])
            except BaseException as error:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"phase": "original-custody-final-readback", **shared.error(error)})
            result["cleanup"] = cleanup
            if cleanup["status"] != "PASS":
                result["status"] = "FAIL"
                if cleanup["errors"]:
                    result.setdefault("firstFailure", cleanup["errors"][0])
            result["finishedAt"] = time.time()
            receipt_retained = retain_receipt(shared, output / "receipt.json", result, "final-runtime-receipt")
    summary = {"status": result["status"], "receipt": str(output / "receipt.json"),
               "receiptRetained": receipt_retained, "series": result["series"]}
    if receipt_retained:
        try:
            summary["sha256"] = admission.sha(output / "receipt.json")
        except BaseException as error:
            result["status"] = summary["status"] = "FAIL"
            result.setdefault("firstFailure", shared.error(error))
            summary.update(firstFailure=result["firstFailure"], terminalReadbackError=shared.error(error))
    else:
        # The workflow retains original stdout even if the filesystem cannot
        # retain a complete terminal receipt. Never overwrite a partial file.
        summary.update(firstFailure=result.get("firstFailure"), receiptFailures=result["receiptFailures"])
    print(json.dumps(summary, sort_keys=True))
    return 0 if result["status"] == "PASS_ORIGINAL_HOSTED_INSPECTOR_METHODS_2_CASES_14" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "source", "build-root", "plan", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    profile_binding.require_runtime_ready()
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "Actual hosted Apple Silicon runtime is required")
    require(admission.sha(admission.canonical(args.plan)) == args.plan_sha256,
            "Root-reviewed original plan bytes changed")
    # Decode through the unchanged original duplicate-key/nonfinite JSON guard.
    originals = Originals(admission.canonical(args.source, directory=True))
    try:
        originals.install()
        return run(args, originals)
    finally:
        originals.close()


if __name__ == "__main__":
    raise SystemExit(main())
