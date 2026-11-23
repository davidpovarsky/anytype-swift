#!/usr/bin/env python3
"""Build only the failed-scope UI runner and compose it with the original 4b App.

Original-Products admission, owned command policy and legacy validators remain
unchanged. This adapter records the new runner origin separately at every step.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import sys
import tarfile
import uuid

import native_ui_original_products as ui
import native_ui_original_products_contract as original
import native_ui_original_products_readiness as owned
import native_ui_original_products_results as old_results
import native_ui_transition_contract as contract
import native_ui_transition_project as project

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "build/native-ui-transition-candidate"
EVIDENCE = original.EVIDENCE / "native-ui-transition-candidate"
GENERATED = WORK / "source"
DERIVED = WORK / "derived"
PRODUCTS = DERIVED / "Build/Products"
BUILD_RECEIPT = EVIDENCE / "build.json"
NEW_WORKFLOW = ".github/workflows/pinkha-any-native-ui-transition-candidate.yml"
DIRECT_INPUTS = (
    "NativeApp/UITests/NativeLaunchTests.swift",
    "NativeApp/UITests/NativeHistoryTests.swift",
    "NativeApp/AnyNative.xcodeproj/project.pbxproj",
    "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme",
    "Tools/AnyEnginePort/native_ui_transition.py",
    "Tools/AnyEnginePort/native_ui_transition_contract.py",
    "Tools/AnyEnginePort/native_ui_transition_project.py",
    "docs/validation/20261123-native-ui-transition-candidate/test-source-inverse.json",
    NEW_WORKFLOW,
    ".github/workflows/torah-inspector-ipados27.yml",
)


def dump(path, value):
    owned.write_new(path, value)


def setup():
    fixed, context, locations, admission, legacy = ui.current()
    contract.require(admission["applicationCommit"] == contract.APP_COMMIT,
                     "exact_original_application_required")
    helpers = owned.verify_helpers()
    origins = owned.bind_modules(locations["app"], legacy)
    modules = {__name__: Path(__file__).resolve(), "project": Path(project.__file__).resolve(),
               "contract": Path(contract.__file__).resolve(), "old_results": Path(old_results.__file__).resolve(),
               "owned": Path(owned.__file__).resolve()}
    expected = {"project": ROOT / "Tools/AnyEnginePort/native_ui_transition_project.py",
                "contract": ROOT / "Tools/AnyEnginePort/native_ui_transition_contract.py",
                "old_results": ROOT / "Tools/AnyEnginePort/native_ui_original_products_results.py",
                "owned": ROOT / "Tools/AnyEnginePort/native_ui_original_products_readiness.py",
                __name__: ROOT / "Tools/AnyEnginePort/native_ui_transition.py"}
    contract.require(modules == expected and original.ROOT == owned.ROOT == ROOT,
                     "current_candidate_module_origin_changed")
    contract.require(contract.sha(contract.regular(ROOT / DIRECT_INPUTS[0])) == contract.SWIFT_SHA
                     and contract.sha(contract.regular(ROOT / DIRECT_INPUTS[1])) == contract.HISTORY_SHA
                     and contract.sha(contract.regular(expected["project"])) == contract.PROJECT_HELPER_SHA,
                     "frozen_candidate_ui_source_changed")
    execution = legacy["verify_native_test_execution"]
    contract.require(contract.sha(contract.regular(Path(execution.__file__)))
                     == contract.ORIGINAL_EXECUTION_HELPER_SHA,
                     "immutable_four_profile_validator_required")
    contract.require(set(contract.ALL_METHODS).isdisjoint(fixed["retainedMethods"])
                     and len(contract.ALL_METHODS) == len(set(contract.ALL_METHODS)) == 5,
                     "retained_method_or_duplicate_selection")
    app = locations["products"] / "Debug-iphonesimulator/PinkhaAnyNative.app"
    contract.require(app.is_dir() and app.resolve() == app and not app.is_relative_to(WORK),
                     "original_app_outside_new_runner_required")
    return {"fixed": fixed, "context": context, "locations": locations, "admission": admission,
            "legacy": legacy, "helpers": helpers, "origins": origins, "application": app}


def context_record(state):
    value = state["admission"]
    return {key: value[key] for key in
            ("controlCommit", "currentRunID", "currentRunAttempt", "applicationCommit", "ownedSimulatorUDID")} | {
        "contract": contract.PROFILE, "originalAdmissionSHA256": original.sha(original.regular(original.ADMISSION)),
        "originalArtifact": state["fixed"]["artifact"],
        "originalApplicationCodeCarriersSHA256": original.canonical(
            state["fixed"]["frozenBuild"]["products"]["app"]["codeCarriers"]),
        "candidateSwiftSHA256": contract.SWIFT_SHA,
        "applicationBuildsThisRun": 0, "nativeLibraryBuildsThisRun": 0,
        "retainedMethodCount": 22, "retainedMethodsExecutedThisRun": 0,
        "fullAcceptance": False, "currentSharedAppAcceptance": False,
    }


def source_snapshot(state):
    current = state["context"]["controlCommit"]
    paths = {name: ROOT / name for name in DIRECT_INPUTS}
    return {"loaded": owned.verify_source_closures(state["locations"]["app"], current, contract.APP_COMMIT),
            "direct": owned.git_source_bytes(ROOT, current, paths),
            "qualifiedOwnedHelpers": state["helpers"], "moduleOrigins": state["origins"]}


def recheck_sources(state, before):
    observed = {name: owned.digest(ROOT / name) for name in DIRECT_INPUTS}
    contract.require(observed == before["direct"], "candidate_direct_source_changed")
    return {"loaded": owned.recheck_physical_sources(state["locations"]["app"], before["loaded"]),
            "direct": observed}


def verify_device(state):
    udid, _, status = ui.provider().verify_simulator(
        state["locations"]["evidence"] / "simulator.json", state["context"]["currentRunID"])
    contract.require(udid == state["admission"]["ownedSimulatorUDID"] and status == "Booted",
                     "current_owned_booted_simulator_required")


def inventory(root, *, excluded=()):
    root = Path(root)
    contract.require(root.is_dir() and root.resolve() == root, "regular_products_root_required")
    omitted = set(excluded)
    rows = {}
    total = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        value = path.lstat()
        contract.require(not path.is_symlink(), "unreviewed_new_product_link")
        if relative in omitted:
            contract.require(stat.S_ISREG(value.st_mode), "excluded_descriptor_not_regular")
            continue
        if stat.S_ISDIR(value.st_mode):
            rows[relative] = {"kind": "directory", "mode": stat.S_IMODE(value.st_mode)}
        else:
            contract.require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1,
                             "regular_single_link_product_required")
            total += value.st_size
            contract.require(total <= 512 * 1024**2, "new_runner_products_size_limit")
            rows[relative] = {"kind": "file", "mode": stat.S_IMODE(value.st_mode),
                              "bytes": value.st_size, "sha256": owned.digest(path)}
        contract.require(len(rows) <= 5000, "new_runner_product_count_limit")
        if path.name.endswith(".app"):
            contract.require(path.name == contract.TARGET + "-Runner.app",
                             "application_target_product_in_ui_only_build")
    return rows


def generated_unchanged(record):
    expected = record["generatedInputs"]
    observed = {}
    for relative in expected:
        path = GENERATED / relative
        raw = contract.regular(path, 4 * 1024**2)
        observed[relative] = {"sha256": contract.sha(raw), "bytes": len(raw),
                              "mode": stat.S_IMODE(path.lstat().st_mode)}
    contract.require(observed == expected, "generated_ui_source_changed")


def build():
    state = setup()
    verify_device(state)
    contract.require(not WORK.exists() and not EVIDENCE.exists(), "fresh_candidate_build_roots_required")
    WORK.mkdir(mode=0o700)
    EVIDENCE.mkdir(mode=0o700)
    sources = source_snapshot(state)
    dump(EVIDENCE / "build-source-before.json", sources)
    created = project.generate(
        GENERATED,
        original_project=contract.regular(ROOT / DIRECT_INPUTS[2]),
        original_scheme=contract.regular(ROOT / DIRECT_INPUTS[3]),
        launch_source=contract.regular(ROOT / DIRECT_INPUTS[0]),
        expected_launch_sha256=contract.SWIFT_SHA,
        history_source=contract.regular(ROOT / DIRECT_INPUTS[1]))
    dump(EVIDENCE / "generated-project.json", created)
    command = ["xcodebuild", "build-for-testing", "-project", created["project"],
               "-scheme", created["scheme"], "-configuration", "Debug",
               "-destination", "platform=iOS Simulator,id=" + state["admission"]["ownedSimulatorUDID"],
               "-derivedDataPath", str(DERIVED), "-resultBundlePath", str(EVIDENCE / "build.xcresult"),
               "-parallel-testing-enabled", "NO", "-disableAutomaticPackageResolution", "-skipPackageUpdates",
               "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
               "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-", "DEVELOPMENT_TEAM="]
    for method in contract.ALL_METHODS:
        command += ["-only-testing:" + contract.TARGET + "/" + method]
    record = {"schemaVersion": 1, "status": "FAIL", **context_record(state),
              "uiRunnerBuildInvocations": 1, "testsExecutedByBuild": 0, "command": command,
              "generatedProjectSHA256": owned.digest(EVIDENCE / "generated-project.json")}
    first = None
    try:
        observed, _ = owned.run_owned(command, EVIDENCE / "build.log", 600)
        record["ownedCommand"] = observed
        generated_unchanged(created)
        entries = inventory(PRODUCTS)
        descriptors = sorted(PRODUCTS.glob("*.xctestrun"))
        contract.require(len(descriptors) == 1, "one_actual_generated_descriptor_required")
        descriptor = descriptors[0]
        original_raw = contract.regular(descriptor)
        # Both prospective copies must be admitted before any product test.
        for stage in contract.STAGES:
            contract.descriptor_bytes(original_raw, products=PRODUCTS,
                                      original_app=state["application"], stage=stage)
        record["originalDescriptor"] = {"path": str(descriptor), "sha256": contract.sha(original_raw)}
        dump(EVIDENCE / "runner-products.json", entries)
        record["runnerProductsSHA256"] = owned.digest(EVIDENCE / "runner-products.json")
        archive = EVIDENCE / "UIRunnerProducts.tar.gz"
        with tarfile.open(archive, "x:gz") as tar:
            for relative, item in entries.items():
                tar.add(PRODUCTS / relative, arcname="Build/Products/" + relative, recursive=False)
            for relative in created["generatedInputs"]:
                tar.add(GENERATED / relative, arcname="Source/" + relative, recursive=False)
        record["preservedRunnerProducts"] = {"path": archive.name, "bytes": archive.stat().st_size,
                                             "sha256": owned.digest(archive),
                                             "phase": "AFTER_BUILD_BEFORE_PRODUCT_EXECUTION"}
        contract.require(inventory(PRODUCTS) == entries, "products_changed_during_preservation")
    except BaseException as error:
        first = error
        record["firstFailure"] = owned.error_record(error)
    try:
        record["sourceAfter"] = recheck_sources(state, sources)
        # No old zero-current-build receipt is emitted after the new runner build.
        ui.current()
        record["originalProductsUnchanged"] = True
    except BaseException as error:
        record["postflightFailure"] = owned.error_record(error)
        if first is None:
            first = error
    if first is None:
        record["status"] = "BUILT_UI_ONLY_RUNNER_ORIGINAL_APP_UNCHANGED"
    dump(BUILD_RECEIPT, record)
    if first is not None:
        raise first
    return record


def admitted_build(state, *, restored_runner=None):
    if restored_runner is not None:
        from native_ui_runner_reuse import require_reference
        return require_reference(restored_runner).verify(state)
    value = original.data(BUILD_RECEIPT)
    contract.require(value.get("status") == "BUILT_UI_ONLY_RUNNER_ORIGINAL_APP_UNCHANGED"
                     and all(value.get(k) == v for k, v in context_record(state).items())
                     and value.get("uiRunnerBuildInvocations") == 1
                     and value.get("testsExecutedByBuild") == 0, "current_candidate_build_origin_changed")
    created = original.data(EVIDENCE / "generated-project.json")
    contract.require(owned.digest(EVIDENCE / "generated-project.json") == value["generatedProjectSHA256"],
                     "generated_project_receipt_changed")
    generated_unchanged(created)
    entries = original.data(EVIDENCE / "runner-products.json")
    contract.require(owned.digest(EVIDENCE / "runner-products.json") == value["runnerProductsSHA256"]
                     and inventory(PRODUCTS, excluded=contract.COPY_NAMES.values()) == entries,
                     "new_runner_products_changed")
    descriptor = Path(value["originalDescriptor"]["path"])
    contract.require(descriptor.parent == PRODUCTS and descriptor.name.endswith(".xctestrun")
                     and owned.digest(descriptor) == value["originalDescriptor"]["sha256"],
                     "original_new_runner_descriptor_changed")
    archive = EVIDENCE / value["preservedRunnerProducts"]["path"]
    contract.require(archive.name == "UIRunnerProducts.tar.gz"
                     and archive.stat().st_size == value["preservedRunnerProducts"]["bytes"]
                     and owned.digest(archive) == value["preservedRunnerProducts"]["sha256"],
                     "preserved_runner_product_archive_changed")
    return value, descriptor


def command_output(command, directory, label, timeout):
    path = directory / (label + ".log")
    observed, _ = owned.run_owned(command, path, timeout)
    return contract.regular(path, 16 * 1024**2), observed


def container_path(state, directory, kind, label):
    verify_device(state)
    raw, command = command_output(
        ["xcrun", "simctl", "get_app_container", state["admission"]["ownedSimulatorUDID"],
         contract.APP_BUNDLE, kind], directory, label, 30)
    text = raw.decode("utf-8").strip()
    path = Path(text)
    contract.require(text.startswith("/") and "\n" not in text and "\r" not in text
                     and path.is_dir() and path.resolve() == path, "one_current_owned_container_path_required")
    return path, command


def installed_app(state, directory):
    path, command = container_path(state, directory, "app", "installed-app-path")
    actual = state["legacy"]["verify_custom_type"].inventory(path)
    expected = state["fixed"]["frozenBuild"]["products"]["app"]["codeCarriers"]
    contract.require(state["legacy"]["verify_archive_roundtrip"].same_value(actual["codeCarriers"], expected),
                     "installed_application_differs_from_retained_app")
    return {"codeCarriersSHA256": original.canonical(actual["codeCarriers"]), "ownedCommand": command}


def exports_metadata(state, directory):
    """Diagnostic only. Open no file contents and enumerate no directory."""
    record = {"diagnosticOnly": True, "acceptance": False, "readDirectoryEntries": False}
    try:
        path, command = container_path(state, directory, "data", "failed-archive-container")
        record["ownedContainerCommand"] = command
        parent = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in ("Documents", "Exports"):
                try:
                    value = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    record[name] = {"observed": True, "mode": stat.S_IMODE(value.st_mode),
                                    "type": stat.S_IFMT(value.st_mode), "inode": value.st_ino,
                                    "device": value.st_dev, "size": value.st_size,
                                    "mtime_ns": value.st_mtime_ns}
                    if not stat.S_ISDIR(value.st_mode):
                        record["nextComponent"] = "NOT_OBSERVED_NON_DIRECTORY_OR_LINK"
                        break
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent)
                    parent = child
                except OSError as error:
                    record[name] = {"observed": False, "errno": error.errno}
                    record["nextComponent"] = "NOT_OBSERVED"
                    break
        finally:
            os.close(parent)
    except BaseException as error:
        record["diagnosticFailure"] = owned.error_record(error)
    dump(directory / "exports-directory-metadata.json", record)
    return record


def archive_semantics(state, directory, attachments):
    validator = state["legacy"]["verify_archive_roundtrip"]
    receipt, raw = validator.ui_receipt(attachments)
    scope = receipt.get("scopeUUID")
    contract.require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope,
                     "actual_ui_export_uuid_required")
    container, command = container_path(state, directory, "data", "archive-container")
    exports = container / "Documents/Exports"
    contract.require(exports.is_dir() and not exports.is_symlink() and exports.resolve() == exports,
                     "actual_owned_exports_directory_required")
    names = ("canonical-source-" + scope + ".json", "canonical-destination-" + scope + ".json",
             "canonical-source-cold-" + scope + ".json")
    values = [validator.regular_bytes(exports / name, exports, validator.MAXIMUM_BYTES) for name in names]
    proof = validator.validate_roundtrip(values[0], values[1], receipt, source_cold_bytes=values[2])
    saved = directory / "private-export-originals"
    saved.mkdir(mode=0o700)
    for name, value in [*zip(names, values), ("ui-receipt.json", raw)]:
        with (saved / name).open("xb") as stream:
            stream.write(value)
        (saved / name).chmod(0o400)
    return {**proof, "readOnlyPostflight": True, "ownedContainerCommand": command,
            "uiReceiptSHA256": contract.sha(raw),
            "originalFiles": {name: contract.sha(value) for name, value in zip(names, values)},
            "validatorSHA256": owned.digest(Path(validator.__file__)),
            "bodyProofBoundary": "Retained UI body/cold assertions; candidate changes only Files navigation."}


def execute(stage, *, restored_runner=None):
    contract.require(stage in contract.STAGES, "only_five_failed_scopes_authorized")
    state = setup()
    verify_device(state)
    build_record, original_descriptor = admitted_build(state, restored_runner=restored_runner)
    directory = EVIDENCE / stage
    contract.require(not directory.exists(), "no_stage_replay_in_current_owned_run")
    directory.mkdir(mode=0o700)
    source_before = source_snapshot(state)
    dump(directory / "source-before.json", source_before)
    descriptor = PRODUCTS / contract.COPY_NAMES[stage]
    contract.require(not descriptor.exists(), "fresh_sibling_candidate_descriptor_required")
    if restored_runner is None:
        raw, binding = contract.descriptor_bytes(
            contract.regular(original_descriptor), products=PRODUCTS,
            original_app=state["application"], stage=stage)
    else:
        raw, binding = restored_runner.descriptor_bytes(
            contract.regular(original_descriptor), state, stage)
    with descriptor.open("xb") as stream:
        stream.write(raw)
        if restored_runner is not None:
            stream.flush()
            os.fsync(stream.fileno())
    if restored_runner is not None:
        descriptor.chmod(0o600)
    binding["copiedSHA256"] = contract.sha(raw)
    binding["copiedPath"] = str(descriptor)
    dump(directory / "descriptor-binding.json", binding)
    if restored_runner is not None:
        restored_runner.register_descriptor(stage, descriptor, directory / "descriptor-binding.json", state)
    plan = contract.command(stage, descriptor, state["admission"]["ownedSimulatorUDID"],
                            directory / "original.xcresult")
    if restored_runner is not None:
        plan.update(restored_runner.record_fields())
        plan["runnerOrigin"] = "RETAINED_ORIGINAL_UI_RUNNER"
    enumeration_file = directory / "enumeration.json"
    enumeration_command = contract.enumeration_command(plan, enumeration_file)
    dump(directory / "plan.json", {**plan, "enumerationCommand": enumeration_command})
    outcome = {"schemaVersion": 1, "status": "FAIL", **context_record(state), "stage": stage,
               "uiRunnerBuildInvocations": 1, "buildReceiptSHA256": owned.digest(
                   BUILD_RECEIPT if restored_runner is None else restored_runner.build_receipt_path()),
               "descriptorBindingSHA256": owned.digest(directory / "descriptor-binding.json"),
               "planSHA256": owned.digest(directory / "plan.json"), "testCommandInvoked": False,
               "completeStageAcceptance": False, "partialNamed": None}
    if restored_runner is not None:
        outcome.update(restored_runner.record_fields())
    first = None
    errors = []
    try:
        enum_result, _ = owned.run_owned(enumeration_command, directory / "enumeration.log", 120)
        enumeration = contract.exact_enumeration(original.data(enumeration_file), stage)
        outcome["enumeration"] = enumeration
        outcome["enumerationCommand"] = enum_result
        outcome["enumerationSHA256"] = owned.digest(enumeration_file)
        # Exact descriptor bytes and full CLI selectors bind enumeration to XCTest.
        contract.require(owned.digest(descriptor) == binding["copiedSHA256"],
                         "descriptor_changed_after_enumeration")
        admitted_build(state, restored_runner=restored_runner)
        outcome["testCommandInvoked"] = True
        timeout = len(contract.STAGES[stage][2]) * contract.STAGES[stage][1] + 300
        result, _ = owned.run_owned(plan["command"], directory / "test.log", timeout)
        outcome["testCommand"] = result
    except BaseException as error:
        first = error
        outcome["firstFailure"] = owned.error_record(error)
    result_path = directory / "original.xcresult"
    if result_path.is_dir():
        for kind, suffix in (("summary", "summary.json"), ("tests", "tests.json")):
            try:
                data, command = command_output(
                    ["xcrun", "xcresulttool", "get", "test-results", kind,
                     "--path", str(result_path), "--format", "json"],
                    directory, "xcresult-" + kind, 120)
                with (directory / suffix).open("xb") as stream:
                    stream.write(data)
                outcome[kind + "Command"] = command
                outcome[kind + "SHA256"] = contract.sha(data)
            except BaseException as error:
                errors.append({"phase": "xcresult-" + kind, **owned.error_record(error)})
        try:
            attachments = directory / "private-attachments"
            contract.require(not attachments.exists(), "fresh_private_attachments_required")
            owned.run_owned(["xcrun", "xcresulttool", "export", "attachments",
                             "--path", str(result_path), "--output-path", str(attachments)],
                            directory / "attachments.log", 120)
            attachments.chmod(0o700)
        except BaseException as error:
            errors.append({"phase": "attachments", **owned.error_record(error)})
    else:
        errors.append({"phase": "original-xcresult", "type": "MissingOriginalResult"})
    if (directory / "tests.json").is_file():
        try:
            outcome["partialNamed"] = contract.partial_named(
                original.data(directory / "tests.json"), state["legacy"]["verify_native_test_execution"].test_cases)
        except BaseException as error:
            errors.append({"phase": "partial-named", **owned.error_record(error)})
    if first is not None and stage == "archive-roundtrip":
        # Diagnostic errors are secondary; the original XCTest error stays first.
        try:
            outcome["exportsMetadata"] = exports_metadata(state, directory)
        except BaseException as error:
            outcome["exportsDiagnosticPreservationFailure"] = owned.error_record(error)
    try:
        outcome["sourceAfter"] = recheck_sources(state, source_before)
        ui.current()
        admitted_build(state, restored_runner=restored_runner)
        contract.require(owned.digest(descriptor) == binding["copiedSHA256"],
                         "copied_descriptor_changed_after_execution")
        outcome["originalProductsUnchanged"] = True
    except BaseException as error:
        errors.append({"phase": "source-products-postflight", **owned.error_record(error)})

    def validate():
        contract.require(outcome["testCommandInvoked"] is True and "testCommand" in outcome,
                         "actual_owned_test_command_required")
        execution = state["legacy"]["verify_native_test_execution"]
        proof = execution.validate(original.data(directory / "summary.json"),
                                   original.data(directory / "tests.json"),
                                   contract.STAGES[stage][0], state["admission"]["ownedSimulatorUDID"])
        device = proof["device"]
        fixed = state["fixed"]["runtime"]
        contract.require(device["osVersion"] == fixed["version"]
                         and device["osBuildNumber"] == fixed["buildversion"]
                         and device["architecture"] == fixed["architecture"], "exact_owned_runtime_result_required")
        state["legacy"]["continue_native_acceptance"].verify_log(
            contract.regular(directory / "test.log", 32 * 1024**2), proof["actualCases"])
        output = {"actual": proof, "validatorSHA256": owned.digest(Path(execution.__file__)),
                  "installedOriginalApplication": installed_app(state, directory),
                  "testLogSHA256": owned.digest(directory / "test.log"),
                  "mixedOrigin": ("ORIGINAL_APP_WITH_CURRENT_UI_ONLY_RUNNER" if restored_runner is None
                                  else "ORIGINAL_APP_WITH_RETAINED_ORIGINAL_UI_RUNNER")}
        if stage == "archive-roundtrip":
            output["archive"] = archive_semantics(state, directory, directory / "private-attachments")
        return output

    outcome, failure = contract.finish_outcome(first, errors, outcome, validate=validate)
    dump(directory / "result.json", outcome)
    if failure is not None:
        raise failure
    return outcome


def final(*, restored_runner=None):
    state = setup()
    result = {"schemaVersion": 1, **context_record(state), "status": "INCOMPLETE",
              "uiRunnerBuildInvocations": 1, "currentMethods": {},
              "originalFailedRun451483RemainsFailure": True,
              "customType": "NOT_RUN", "history": "NOT_RUN", "physicalDevice": "NOT_RUN"}
    if restored_runner is not None:
        result.update(restored_runner.record_fields())
    first = None
    try:
        admitted_build(state, restored_runner=restored_runner)
        result["originalProductsUnchanged"] = True
        for stage in contract.STAGES:
            path = EVIDENCE / stage / "result.json"
            if not path.is_file():
                continue
            value = original.data(path)
            contract.require(value.get("stage") == stage and all(value.get(k) == v for k, v in context_record(state).items()),
                             "stage_receipt_origin_changed")
            if restored_runner is not None:
                contract.require(all(value.get(k) == v for k, v in restored_runner.record_fields().items())
                                 and value["buildReceiptSHA256"] == owned.digest(restored_runner.build_receipt_path()),
                                 "retained_runner_stage_origin_changed")
            binding_path = EVIDENCE / stage / "descriptor-binding.json"
            binding = original.data(binding_path)
            contract.require(value["descriptorBindingSHA256"] == owned.digest(binding_path)
                             and binding["copiedPath"] == str(PRODUCTS / contract.COPY_NAMES[stage])
                             and binding["copiedSHA256"] == owned.digest(PRODUCTS / contract.COPY_NAMES[stage]),
                             "candidate_descriptor_receipt_changed")
            result["currentMethods"][stage] = {"status": value["status"],
                "partialNamed": value.get("partialNamed"), "resultSHA256": owned.digest(path)}
        contract.require(len(result["currentMethods"]) == 2
                         and all(x["status"] == "PASS" for x in result["currentMethods"].values()),
                         "candidate_method_acceptance_incomplete")
        result["provider"] = old_results.provider_complete(state["locations"], state["admission"])
        provider_cleanup = original.data(original.EVIDENCE / "hanlin-provider/cleanup.json")
        contract.require(provider_cleanup.get("status") == "OWNED_FIXTURE_STOPPED_AND_PRIVATE_MATERIAL_REMOVED"
                         and provider_cleanup.get("sourceCommit") == state["context"]["controlCommit"]
                         and provider_cleanup.get("githubRunID") == state["context"]["currentRunID"],
                         "current_owned_provider_cleanup_not_proven")
        simulator_cleanup = original.data(original.EVIDENCE / "native-ui-original-simulator-cleanup.json")
        contract.require(simulator_cleanup.get("status") == "OWNED_SIMULATOR_REMOVAL_OBSERVED"
                         and all(simulator_cleanup.get(k) == state["admission"][k] for k in
                                 ("ownedSimulatorUDID", "currentRunID", "controlCommit", "currentRunAttempt"))
                         and simulator_cleanup.get("ownedSimulatorRemoved") is True
                         and simulator_cleanup.get("absenceProof") is True,
                         "current_owned_simulator_cleanup_not_proven")
        result["cleanupOriginalSHA256"] = {
            "provider": owned.digest(original.EVIDENCE / "hanlin-provider/cleanup.json"),
            "simulator": owned.digest(original.EVIDENCE / "native-ui-original-simulator-cleanup.json")}
        result["status"] = ("FIVE_FAILED_SCOPES_PASSED_IN_ORIGINAL_APP_WITH_NEW_UI_RUNNER"
                            if restored_runner is None else
                            "FIVE_FAILED_SCOPES_PASSED_WITH_ORIGINAL_APP_AND_RETAINED_UI_RUNNER")
    except BaseException as error:
        first = error
        result["firstFailure"] = owned.error_record(error)
    dump(EVIDENCE / "final.json", result)
    if first is not None:
        raise first
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("build", "execute", "final"))
    parser.add_argument("--stage", choices=tuple(contract.STAGES))
    args = parser.parse_args()
    if args.operation == "execute":
        contract.require(args.stage is not None, "stage_required")
        result = execute(args.stage)
    else:
        contract.require(args.stage is None, "stage_only_for_execution")
        result = build() if args.operation == "build" else final()
    print(json.dumps({"status": result["status"], "contract": contract.PROFILE}, sort_keys=True))


if __name__ == "__main__":
    main()
