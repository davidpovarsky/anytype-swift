#!/usr/bin/env python3
"""Closed same-job original fresh T5 core2/R08 and quote-freshness continuation.

No build, old account admission, old Mac ready flag, source alias, or runtime
identity override is supported. The public output and encrypted private output
are separate; the workflow must never upload this entire working directory.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
import uuid

sys.dont_write_bytecode = True

import profile
import publication
import t5_originals
from profile import require


class FirstFailure:
    """Capture the original stage failure before its final receipt can fail."""
    def __init__(self, shared):
        self.shared, self.first, self.receipt_failures = shared, None, []

    def observe(self, value, phase):
        if self.first is None:
            self.first = {"phase": phase, **value}

    def failure(self, error, phase):
        self.observe(self.shared.error(error), phase)

    def write(self, path, value):
        # The complete original Consumer.stage body is unchanged. Its injected
        # writer observes the real outcome before touching the filesystem.
        if isinstance(value, dict):
            if isinstance(value.get("firstFailure"), dict):
                self.observe(value["firstFailure"], "original-stage")
            elif value.get("status") == "FAIL" and isinstance(value.get("errors"), list) and value["errors"]:
                self.observe(value["errors"][0], "original-stage-qualification")
        try:
            return self.shared.write(path, value)
        except BaseException as error:
            self.failure(error, "original-receipt-write")
            self.receipt_failures.append({"path": str(path), **self.shared.error(error)})
            raise

    def retain(self, path, value, phase):
        try:
            self.write(path, value)
            return True
        except BaseException as error:
            self.failure(error, phase)
            value["status"] = "FAIL"
            if value.get("firstFailure") is None:
                value["firstFailure"] = self.first
            value["receiptFailures"] = list(self.receipt_failures)
            return False


def load_dependencies(control):
    modules = {}
    try:
        for name in ("originals", "admission", "hosted_t5_core_lifetime", "hosted_t5_native23_receipts"):
            relative, expected = profile.DEPENDENCIES[name]
            path = control / relative
            require(path.is_file() and path.resolve() == path and not path.is_symlink()
                    and profile.digest(path) == expected and name not in sys.modules,
                    "Exact existing reviewed dependency required: " + relative)
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module; modules[name] = module
            spec.loader.exec_module(module)
        return modules
    except BaseException:
        close_modules(modules)
        raise


def close_modules(modules):
    for name, module in reversed(list(modules.items())):
        if sys.modules.get(name) is module:
            del sys.modules[name]


def control_identity(control, commit, admission):
    identity = admission.identity(control, commit)
    files = [path for path in admission.git(control, "ls-files", "-z", profile.PREFIX).split("\0") if path]
    required = {profile.PREFIX + name for name in ("run.py", "profile.py", "job_binding.py", "t5_originals.py",
                "publication.py", "custody_crypto.mjs", "recipient-public.pem", "activation.json", "original_sources.json")}
    require(required.issubset(files), "Complete actual T5 control source closure required")
    observed = {}
    for relative in files:
        path = admission.canonical(control / relative)
        original = admission.git(control, "rev-parse", commit + ":" + relative).strip()
        raw = path.read_bytes()
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == original,
                "Actual T5 control differs from its immutable Git blob")
        observed[relative] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    require(Path(__file__).resolve() == control / profile.PREFIX / "run.py", "Actual T5 entrypoint is not the admitted file")
    return {**identity, "files": observed}


def file_only_controls(control, before):
    for relative, pin in before["files"].items():
        path = control / relative
        require(path.resolve() == path and not path.is_symlink() and path.is_file()
                and path.stat().st_size == pin["bytes"] and profile.digest(path) == pin["sha256"], "T5 control changed")
    for relative, expected in profile.DEPENDENCIES.values():
        path = control / relative
        require(path.resolve() == path and not path.is_symlink() and profile.digest(path) == expected, "Shared dependency changed")


def file_only_source(source, context, originals):
    reference = context["root"] / "build16/source-before.json"
    before = originals.shared.decode(originals.shared.raw(reference))
    require(before == originals.shared.decode(originals.shared.raw(context["root"] / "build16/source-after.json")),
            "Original producer source observations changed")
    for relative, pin in before["files"].items():
        path = source / originals.gate.relative(relative)
        require(path.resolve() == path and not path.is_symlink() and path.is_relative_to(source)
                and path.is_file() and path.stat().st_size == pin["bytes"] and profile.digest(path) == pin["sha256"],
                "Original compiled source bytes changed")


def execute_lane(consumer, lane, action, t5, lifetime, runtime, device_type, writer):
    require((lane, action) in {(row[1], row[2]) for row in profile.PLANS}, "Only the original two fresh T5 plans are selected")
    shared, commands = consumer.shared_module, consumer.commands
    directory = consumer.root / "evidence/lanes" / lane
    directory.mkdir(mode=0o700, parents=True)
    result = {"status": "FAIL", "lane": lane, "sourceCommit": consumer.binding["sourceSHA"],
              "errors": [], "nativeAccountReused": False, "startupSeconds": 120,
              "physicalDevice": "NOT_RUN", "voiceOver": "NOT_RUN", "dynamicTypeScope": "fixed-large-only"}
    previous = set(consumer.devices); udid = None; scope = None
    try:
        udid, _ = consumer.create(lane, directory, editor=False)
        result["actualDevice"] = lifetime.verify_created_device(consumer, lane, udid, runtime, device_type)
        actual = getattr(consumer, action)(directory, udid)
        result.update(status="PASS_ORIGINAL_FRESH_T5_PLAN", originalResult=actual)
    except BaseException as error:
        if commands.first_exception is not None:
            writer.observe(commands.first_exception, "original-command")
        writer.failure(error, lane)
        result["firstFailure"] = writer.first
    finally:
        created = [value for value in consumer.devices if value not in previous]
        if udid is None and len(created) == 1:
            udid = created[0]
        if len(created) > 1:
            result["errors"].append({"phase": "create", "error": "Unexpected multiple owned devices"})
        if udid:
            if commands.is_open:
                try:
                    container = consumer.container(udid, "data", lane + "-capture-owned-container", required=udid in consumer.invoked_devices)
                    if container is not None:
                        require(container.resolve() == container and not container.is_symlink(), "Physical original App container required")
                        consumer.t5_containers[udid] = container
                    result["privateWitnesses"] = consumer.preserve(udid, directory, lane)
                except BaseException as error:
                    writer.failure(error, lane + "-private-preservation")
                    result["errors"].append({"phase": "private-preservation", **shared.error(error)})
            if commands.is_open:
                try:
                    consumer.command(["xcrun", "simctl", "shutdown", udid], lane + "-shutdown", 60, capacity=False)
                    shutdown = lifetime.verify_created_device(consumer, lane, udid, runtime, device_type, state="Shutdown")
                    consumer.t5_shutdown[udid] = shutdown
                    scope = publication.account_scope(consumer, lane, directory, udid, shutdown, shared)
                    result["ownedSimulator"] = {"udid": udid, "status": "ACTUAL_SHUTDOWN_PENDING_PRIVATE_CIPHERTEXT",
                                                "observation": shutdown, "deleted": False}
                except BaseException as error:
                    writer.failure(error, lane + "-shutdown")
                    result["errors"].append({"phase": "owned-shutdown", **shared.error(error)})
            if not commands.is_open:
                result["errors"].append({"phase": "owned-command-admission", **commands.blocked})
                result["ownedSimulator"] = {"udid": udid, "status": "UNRESOLVED_NO_FURTHER_DEVICE_OPERATION", "deleted": False}
        try:
            result["productsUnchanged"] = {key: shared.product_integrity(value) for key, value in consumer.built.items()}
        except BaseException as error:
            writer.failure(error, lane + "-product-readback")
            result["errors"].append({"phase": "product-readback", **shared.error(error)})
        if result["errors"]:
            result["status"] = "FAIL"
            writer.observe(result["errors"][0], lane)
        result["testInvoked"] = bool(udid and udid in consumer.invoked_devices)
        if writer.first is not None:
            result.setdefault("firstFailure", writer.first)
        result["finishedAt"] = time.time()
        retained = writer.retain(directory / "execution.json", result, lane + "-terminal-receipt")
        if not retained:
            result["status"] = "FAIL"
    return result, scope


def final_inputs(args, plan, context, originals, controls_before, source_before, native23, contract, products, commands, admission):
    """Every final operation after an unresolved group is a file read only."""
    originals.unchanged(); file_only_controls(args.control, controls_before)
    file_only_source(args.source, context, originals)
    native23.recheck()
    if contract is not None:
        originals.gate.verify_controls(contract["controls"])
        for slot, record in products.items():
            originals.gate.verify_inventory(record["base"], record["entries"])
    if not commands.is_open:
        return {"status": "FILE_READS_ONLY_GIT_NOT_RUN_UNRESOLVED_CUSTODY", "subprocessesStarted": 0}
    require(admission.identity(args.source, plan["appSourceSHA"], plan["appSourceTree"]) == source_before,
            "Original source checkout identity changed")
    require(control_identity(args.control, plan["controlCommit"], admission) == controls_before,
            "Original T5 control checkout identity changed")
    return {"status": "PASS_ORIGINAL_PHYSICAL_SOURCE_PRODUCTS_AND_GIT", "originalPathsRewritten": False}


def run(args, modules, activation):
    admission = modules["admission"]; lifetime = modules["hosted_t5_core_lifetime"]
    import job_binding
    originals = modules["originals"].Originals(admission.canonical(args.source, directory=True))
    owner_module_names = set(sys.modules)
    try:
        originals.install()
        shared = originals.shared
        plan = shared.decode(shared.raw(args.plan))
        job = job_binding.bind_job(args, plan)
        source_before = admission.identity(args.source, plan["appSourceSHA"], plan["appSourceTree"])
        controls_before = control_identity(args.control, plan["controlCommit"], admission)
        admission.control_identity(args.control, plan["controlCommit"])
        owner = admission.load_hosted_owner(args.control)
        context = admission.producer_context(args, plan, originals, owner)
        writer = FirstFailure(shared)
        t5 = t5_originals.install(originals, args.control, writer)
        final_proof = profile.qualify_final(activation, plan, context, originals)
        native23 = modules["hosted_t5_native23_receipts"].Native23Receipts(args.control, args.source, context, plan, owner, originals)
        output = args.output
        require(output.is_absolute() and output.parent.resolve() == output.parent and not output.exists()
                and not output.is_symlink(), "Exclusive fresh T5 output required")
        output.mkdir(mode=0o700)
        for directory in ("evidence", "private-control", "ciphertext"):
            (output / directory).mkdir(mode=0o700)
        commands = lifetime.CommandAdmission(shared.Commands(output / "commands", output), shared.error)
        commands.environment["DEVELOPER_DIR"] = job["developerDir"]
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
                     "NODE_OPTIONS", "NODE_PATH", "NODE_V8_COVERAGE", "OPENSSL_CONF", "OPENSSL_MODULES"):
            commands.environment.pop(name, None)
        result = {"schema": "pinkha-hosted-original-fresh-t5-runtime-v1", "status": "FAIL", "startedAt": time.time(),
            "sourceIdentity": source_before, "controlIdentity": controls_before, "job": job,
            "rootPlan": context["planRef"], "originalAppBuild": context["buildRef"], "native23Compiler": native23.proof(),
            "finalProductAdmission": final_proof, "plans": {row[0]: {"status": "NOT_RUN"} for row in profile.PLANS},
            "uniqueMethods": 5, "executionInstances": 6, "historical36Replayed": False, "pending9Replayed": False,
            "appBuilds": 0, "nativeBuilds": 0, "testFlightAccepted": False, "releaseAccepted": False,
            "physicalDevice": "NOT_RUN", "voiceOver": "NOT_RUN", "fullSpaceReaderAccepted": False,
            "coverage": "indexedTargetsOnly", "limitation": "indexFreshnessUnverified"}
        built, clone_progress, products, contract = {}, {}, {}, None
        consumer = None; account_scopes = []; receipt_retained = False
        public_binding = {"repository": job["repository"], "runID": job["runID"], "runAttempt": job["runAttempt"], "job": job["job"],
            "sourceCommit": plan["appSourceSHA"], "nativeManifestSHA256": activation["finalProducerTuple"]["nativeSourceManifestSHA256"],
            "runtimeVersion": activation["finalProducerTuple"]["nativeRuntimeVersion"], "rootPlanSHA256": context["planRef"]["sha256"],
            "appBuildReceiptSHA256": context["buildRef"]["sha256"],
            "native23CompilerReceiptSHA256": native23.proof()["actualCompiler"]["actualCompilerReceipt"]["sha256"]}
        with originals.signals.cancellation_signals():
            try:
                writer.write(output / "evidence/job-admission.json", result)
                result["cryptoPreflight"] = publication.preflight(args.control, output, commands, shared, activation, public_binding)
                result["runtimeToolchain"] = lifetime.fresh_toolchain(commands, originals, context)
                log, _ = commands.run(["xcodebuild", "-help"], "xcode-help", 30)
                require("-collect-test-diagnostics" in shared.raw(log).decode() and "never" in shared.raw(log).decode(),
                        "Original bounded diagnostics option is unavailable")
                log, _ = commands.run(["xcrun", "simctl", "list", "--json"], "original-simulator-inventory", 60)
                runtime, device_type = lifetime.select_runtime(shared.decode(shared.raw(log)))
                result["runtimeDiscovery"] = {"originalInventory": admission.ref(log), "runtime": runtime, "deviceType": device_type}
                contract, proof, products, contract_ref = admission.receipt_contract(context, output, originals, runtime, device_type)
                result.update(receiptContract=contract_ref, commonBuildAdmission=proof)
                app, bundle_id = lifetime.clone_products(contract, products, output, originals, commands, built, clone_progress)
                t5_originals.bind_runtime(originals, t5, runtime, bundle_id, activation["finalProducerTuple"]["nativeRuntimeVersion"])
                writer.write(output / "evidence/original-t5-controller-declarations.json", originals.proof)
                binding = {"sourceSHA": plan["appSourceSHA"], "runID": job["runID"], "runAttempt": job["runAttempt"], "nonce": uuid.uuid4().hex}
                settings = {"sourceRoot": str(args.source), "deviceType": device_type["identifier"], "deviceFamily": "ipad", "appLanguage": "en", "appearance": "light"}
                consumer = t5["host"].Consumer(output, settings, commands, built, app, t5["helpers"], binding)
                consumer.shared_module = shared
                consumer.t5_containers, consumer.t5_shutdown = {}, {}
                for plan_name, lane, action in profile.PLANS:
                    execution, scope = execute_lane(consumer, lane, action, t5, lifetime, runtime, device_type, writer)
                    result["plans"][plan_name] = execution
                    if scope is not None:
                        account_scopes.append(scope)
                    require(writer.retain(output / "evidence" / (lane + "-checkpoint.json"), result, "plan-checkpoint"),
                            "Original first failure/receipt custody was not retained; no next fixture may start")
                    require(execution["status"] == "PASS_ORIGINAL_FRESH_T5_PLAN", "Original fresh T5 plan failed")
                require(all(value["status"] == "PASS_ORIGINAL_FRESH_T5_PLAN" for value in result["plans"].values()),
                        "Both original fresh T5 plans must actually pass")
                result["status"] = "PASS_ORIGINAL_FRESH_T5_RUNTIME_PENDING_CUSTODY"
            except BaseException as error:
                if commands.first_exception is not None:
                    writer.observe(commands.first_exception, "original-command")
                writer.failure(error, "runtime")
            finally:
                result["firstFailure"] = writer.first
                result["productCloneProgress"] = clone_progress
                cleanup = t5["functions"].observe_owned_groups(commands)
                result["ownedProcessClosure"] = cleanup
                if commands.blocked is not None or cleanup["status"] != "PASS":
                    result["status"] = "FAIL"
                    writer.observe(commands.blocked or cleanup, "original-owned-custody")
                try:
                    result["finalProducts"] = {name: shared.product_integrity(value) for name, value in built.items()}
                    result["finalInputBoundary"] = final_inputs(args, plan, context, originals, controls_before, source_before,
                        native23, contract, products, commands, admission)
                except BaseException as error:
                    writer.failure(error, "final-original-inputs")
                    result["status"] = "FAIL"
                if writer.first is not None:
                    result["status"] = "FAIL"
                result["firstFailure"] = writer.first
                result["finishedNativeAt"] = time.time()
                writer.retain(output / "evidence/runtime-before-private-custody.json", result, "original-pre-custody-receipt")
                try:
                    require(commands.is_open and cleanup["status"] == "PASS", "Unresolved owned custody forbids encryption or any new process")
                    require(consumer is None or consumer.invoked_devices.issubset(consumer.t5_shutdown),
                            "Every actual invoked owned simulator must be observed shut down before private custody")
                    result["privateCiphertext"] = publication.encrypt_private(args.control, output, commands, shared, activation, public_binding, account_scopes)
                    if result["status"] == "PASS_ORIGINAL_FRESH_T5_RUNTIME_PENDING_CUSTODY" and writer.first is None:
                        result["status"] = "PASS_ORIGINAL_FRESH_T5_WITH_ENCRYPTED_CUSTODY_RESTORE_PENDING"
                except BaseException as error:
                    writer.failure(error, "private-custody")
                    result["status"] = "FAIL"
                # Only this read-only observer may inspect a newly unresolved
                # encryptor group. It never re-probes old latched absences.
                result["finalOwnedProcessClosure"] = t5["functions"].observe_owned_groups(commands)
                if not commands.is_open or result["finalOwnedProcessClosure"]["status"] != "PASS":
                    writer.observe(commands.blocked or result["finalOwnedProcessClosure"], "private-custody-process")
                    result["status"] = "FAIL"
                result["firstFailure"] = writer.first
                result["receiptFailures"] = writer.receipt_failures
                result["finishedAt"] = time.time()
                receipt_retained = writer.retain(output / "receipt.json", result, "terminal-runtime-receipt")
        public_status = {"schema": result["schema"], "status": result["status"], "sourceCommit": plan["appSourceSHA"],
                        "privateCiphertextAvailable": "privateCiphertext" in result, "privateRestoreVerified": False,
                        "originalDataDeleted": False, "receiptRetained": receipt_retained,
                        "originalHistoriesReplayed": False, "releaseAccepted": False, "testFlightAccepted": False}
        if consumer is not None:
            try:
                publication.publish(output, consumer, t5, public_status)
            except BaseException:
                # Raw errors and paths are already private. No guessed or
                # partially inventoried credentials authorize public raw files.
                public_status["publicOriginalEvidence"] = "WITHHELD_INCOMPLETE_OR_UNSAFE_CREDENTIAL_INVENTORY"
        print(json.dumps(public_status, sort_keys=True))
        return 0 if result["status"] == "PASS_ORIGINAL_FRESH_T5_WITH_ENCRYPTED_CUSTODY_RESTORE_PENDING" and receipt_retained else 1
    finally:
        originals.close()
        for name in set(sys.modules).difference(owner_module_names):
            module = sys.modules[name]
            location = getattr(module, "__file__", None)
            if location and Path(location).is_relative_to(args.control):
                del sys.modules[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "source", "build-root", "plan", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    modules = {}
    try:
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual original hosted Apple Silicon job required")
        # Source-pinned closed readiness is checked before importing other
        # runtimes, creating output, launching commands or touching an account.
        selected = profile.activation(args.control)
        require(profile.digest(args.plan) == args.plan_sha256, "Original root plan changed")
        modules = load_dependencies(args.control)
        return run(args, modules, selected)
    except BaseException:
        # Detailed native evidence, if any, belongs to private custody. This
        # entry failure cannot leak a JSON fixture, environment or credentials.
        print(json.dumps({"status": "CLOSED_OR_FAILED_HOSTED_T5", "runtimeAcceptanceClaimed": False, "privateDataUploaded": False}))
        return 1
    finally:
        close_modules(modules)


if __name__ == "__main__":
    raise SystemExit(main())
