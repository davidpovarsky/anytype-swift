#!/usr/bin/env python3
"""Current original-Products receipts; original semantic/result validators stay unchanged."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import uuid
import native_ui_original_products_contract as c

def driver():
    import native_ui_original_products as module
    return module

def context(admission):
    return driver().receipt_context(admission)

def fixed_stage(stage, modules):
    c.require(stage in c.STAGES, "one_fixed_unexecuted_stage_required")
    profile, _, methods = c.STAGES[stage]
    execution = modules["verify_native_test_execution"]
    c.require(execution.expected_methods(profile) == set(methods), "original_named_validator_selection_changed")
    return profile, methods

def validate_named_inputs(stage, locations, admission, modules):
    profile, methods = fixed_stage(stage, modules)
    evidence = locations["evidence"]
    summary = c.data(evidence / (stage + "-test-counts.json"))
    tree = c.data(evidence / (stage + "-test-methods.json"))
    execution = modules["verify_native_test_execution"].validate(summary, tree, profile,
                                                                  admission["ownedSimulatorUDID"])
    fixed = c.contract()
    device = execution["device"]
    c.require(device["osVersion"] == fixed["runtime"]["version"]
              and device["osBuildNumber"] == fixed["runtime"]["buildversion"]
              and device["architecture"] == fixed["runtime"]["architecture"],
              "actual_test_destination_differs_from_original_runtime_contract")
    modules["continue_native_acceptance"].verify_log(c.regular(evidence / (stage + ".log")),
                                                     execution["actualCases"])
    return execution

def installed_carriers(stage, locations, admission, modules):
    driver().provider().verify_simulator(locations["evidence"] / "simulator.json", admission["currentRunID"])
    path = c.public_command(["xcrun", "simctl", "get_app_container", admission["ownedSimulatorUDID"],
                             "io.pinkha.anynative.dev", "app"],
                            locations["evidence"] / "native-ui-original-commands" / stage,
                            "installed-application-path", timeout=30).decode("utf-8").strip()
    c.require(path.startswith("/") and "\n" not in path and "\r" not in path,
              "one_absolute_installed_application_path_required")
    installed = modules["verify_custom_type"].inventory(Path(path))
    expected = c.contract()["frozenBuild"]["products"]["app"]["codeCarriers"]
    c.require(modules["verify_archive_roundtrip"].same_value(installed["codeCarriers"], expected),
              "installed_application_code_carriers_differ_from_original_build")
    return {"codeCarriersSHA256": c.canonical(installed["codeCarriers"]),
            "source": "actual_owned_simulator_get_app_container_and_binary_hashes",
            "containerObservationCommand": str((locations["evidence"] / "native-ui-original-commands" /
                                               stage / "installed-application-path.json").relative_to(locations["evidence"]))}

def named(stage, test_exit, locations, admission, modules):
    profile, methods = fixed_stage(stage, modules)
    evidence = locations["evidence"]
    plan = c.plan(stage, Path(admission["copiedDescriptor"]["path"]), admission["ownedSimulatorUDID"],
                  evidence / (stage + ".xcresult"))
    c.require(c.data(evidence / (stage + "-original-products-plan.json")) == plan,
              "actual_fixed_test_plan_changed")
    raw_exit = c.data(evidence / (stage + "-command-exit.json"))
    c.require(test_exit is None or test_exit == raw_exit.get("testExit"), "requested_exit_differs_from_original")
    test_exit = raw_exit.get("testExit")
    c.require(type(test_exit) is int and -255 <= test_exit <= 255, "actual_xcodebuild_exit_required")
    c.require(raw_exit == {"testExit": test_exit, "stage": stage, "command": plan["command"]},
              "original_xcodebuild_command_exit_binding_changed")
    c.require(test_exit == 0, "original_xcodebuild_command_failed")
    actual = validate_named_inputs(stage, locations, admission, modules)
    carriers = installed_carriers(stage, locations, admission, modules)
    execution = modules["verify_native_test_execution"]
    return {"schemaVersion": 1, "status": "PASS", **context(admission), "profile": profile,
            "scope": "actual_named_execution_in_original_native_ui_products",
            "observationOnly": False, "fullAcceptance": False, "stage": stage,
            "testCommandExit": test_exit, "testCommandSHA256": c.canonical(plan),
            "originalValidatorSHA256": c.sha(c.regular(Path(execution.__file__))),
            "testSources": {p: c.sha(c.regular(locations["app"] / p)) for p in execution.SOURCE_PATHS[profile]},
            "summarySHA256": c.sha(c.regular(evidence / (stage + "-test-counts.json"))),
            "testTreeSHA256": c.sha(c.regular(evidence / (stage + "-test-methods.json"))),
            "logSHA256": c.sha(c.regular(evidence / (stage + ".log"))),
            "originalCommandExitSHA256": c.sha(c.regular(evidence / (stage + "-command-exit.json"))),
            "installedOriginalApplication": carriers, **actual}

def named_receipt(stage, locations, admission, modules):
    evidence = locations["evidence"]
    record = c.data(evidence / (stage + "-named-execution.json"))
    profile, methods = fixed_stage(stage, modules)
    actual = validate_named_inputs(stage, locations, admission, modules)
    expected_plan = c.plan(stage, Path(admission["copiedDescriptor"]["path"]),
                           admission["ownedSimulatorUDID"], evidence / (stage + ".xcresult"))
    c.require(c.data(evidence / (stage + "-original-products-plan.json")) == expected_plan
              and c.data(evidence / (stage + "-command-exit.json")) ==
                  {"testExit": 0, "stage": stage, "command": expected_plan["command"]}
              and record.get("testCommandSHA256") == c.canonical(expected_plan),
              "current_original_command_or_selection_changed")
    c.require(record.get("status") == "PASS" and record.get("scope") ==
              "actual_named_execution_in_original_native_ui_products"
              and record.get("profile") == profile and record.get("observationOnly") is False
              and record.get("testCommandExit") == 0
              and all(record.get(k) == v for k, v in context(admission).items())
              and all(record.get(k) == v for k, v in actual.items()), "current_named_receipt_origin_or_outcome_changed")
    execution = modules["verify_native_test_execution"]
    c.require(record["originalValidatorSHA256"] == c.sha(c.regular(Path(execution.__file__)))
              and record["testSources"] == {p: c.sha(c.regular(locations["app"] / p))
                                           for p in execution.SOURCE_PATHS[profile]},
              "current_named_original_application_source_changed")
    for key, suffix in (("summarySHA256", "-test-counts.json"), ("testTreeSHA256", "-test-methods.json"),
                        ("logSHA256", ".log"), ("originalCommandExitSHA256", "-command-exit.json")):
        c.require(record[key] == c.sha(c.regular(evidence / (stage + suffix))),
                  "current_named_original_output_digest_changed")
    expected_carriers = c.contract()["frozenBuild"]["products"]["app"]["codeCarriers"]
    c.require(record["installedOriginalApplication"]["codeCarriersSHA256"] == c.canonical(expected_carriers),
              "current_installed_original_carrier_proof_changed")
    return record

def attachment_directory(path, stage, admission):
    expected = Path(os.environ["RUNNER_TEMP"]).resolve() / (
        "native-ui-original-attachments-" + admission["currentRunID"] + "-" +
        str(admission["currentRunAttempt"])) / stage
    c.require(path is not None and path.resolve() == expected and path.is_dir() and not path.is_symlink()
              and not expected.is_relative_to(c.EVIDENCE.resolve())
              and not c.EVIDENCE.resolve().is_relative_to(expected),
              "exact_private_current_attachment_directory_required")
    return expected

def originals_directory(locations, stem):
    directory = locations["evidence"] / stem / "originals"
    c.require(not directory.exists(), "original_postflight_bytes_must_be_preserved_once")
    directory.mkdir(parents=True)
    return directory

def files(attachments, locations, admission, modules):
    stage = "archive-roundtrip"
    named = named_receipt(stage, locations, admission, modules)
    original = modules["verify_archive_roundtrip"]
    private = attachment_directory(attachments, stage, admission)
    receipt, raw = original.ui_receipt(private)
    driver().provider().verify_simulator(locations["evidence"] / "simulator.json", admission["currentRunID"])
    observed = c.public_command(["xcrun", "simctl", "get_app_container", admission["ownedSimulatorUDID"],
                                 "io.pinkha.anynative.dev", "data"],
                                locations["evidence"] / "native-ui-original-commands" / stage,
                                "original-exports-container", timeout=30).decode("utf-8").strip()
    c.require(observed.startswith("/") and "\n" not in observed and "\r" not in observed,
              "one_absolute_owned_exports_container_required")
    container = Path(observed).resolve()
    exports = container / "Documents/Exports"
    c.require(exports.is_dir() and not exports.is_symlink() and exports.resolve().is_relative_to(container),
              "owned_exports_directory_missing")
    scope = receipt.get("scopeUUID")
    c.require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope, "actual_ui_export_scope_required")
    names = ("canonical-source-" + scope + ".json", "canonical-destination-" + scope + ".json",
             "canonical-source-cold-" + scope + ".json")
    source, destination, cold = [original.regular_bytes(exports / name, exports, original.MAXIMUM_BYTES)
                                  for name in names]
    checked = original.validate_roundtrip(source, destination, receipt, source_cold_bytes=cold)
    saved = originals_directory(locations, stage)
    for name, value in zip(names, (source, destination, cold)):
        with (saved / name).open("xb") as stream:
            stream.write(value)
    with (saved / "ui-receipt.json").open("xb") as stream:
        stream.write(raw)
    return {"schemaVersion": 1, "status": "PASS", **context(admission), **checked,
            "scope": "actual_files_roundtrip_in_original_native_ui_products", "fullAcceptance": False,
            "uiMethodExecutions": 1, "actualMethod": original.METHOD, "readOnlyPostflight": True,
            "bodyProofBoundary": "Unchanged original UI assertions read both native bodies after cold reopen.",
            "namedReceiptSHA256": c.sha(c.regular(locations["evidence"] / (stage + "-named-execution.json"))),
            "originalValidatorSHA256": c.sha(c.regular(Path(original.__file__))),
            "uiReceiptSHA256": c.sha(raw),
            "originalFiles": {name: c.sha(value) for name, value in zip(names, (source, destination, cold))},
            "testSourceSHA256": c.sha(c.regular(locations["app"] / "NativeApp/UITests/NativeLaunchTests.swift")),
            "archiveSourceSHA256": c.sha(c.regular(locations["app"] /
                "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift"))}

def validate_files_postflight(locations, admission, modules):
    stage = "archive-roundtrip"
    named_receipt(stage, locations, admission, modules)
    record = c.data(locations["evidence"] / stage / "postflight.json")
    c.require(record.get("status") == "PASS" and record.get("uiMethodExecutions") == 1
              and all(record.get(k) == v for k, v in context(admission).items()), "current_files_postflight_changed")
    original = modules["verify_archive_roundtrip"]
    saved = locations["evidence"] / stage / "originals"
    receipt_raw = c.regular(saved / "ui-receipt.json", 64 * 1024)
    receipt = c.strict_json(receipt_raw)
    scope = receipt.get("scopeUUID")
    c.require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope, "saved_ui_export_scope_required")
    names = ("canonical-source-" + scope + ".json", "canonical-destination-" + scope + ".json",
             "canonical-source-cold-" + scope + ".json")
    source, destination, cold = [original.regular_bytes(saved / name, saved, original.MAXIMUM_BYTES) for name in names]
    checked = original.validate_roundtrip(source, destination, receipt, source_cold_bytes=cold)
    c.require(all(record.get(k) == v for k, v in checked.items())
              and record["originalFiles"] == {name: c.sha(raw) for name, raw in zip(names, (source, destination, cold))}
              and record["uiReceiptSHA256"] == c.sha(receipt_raw)
              and record["namedReceiptSHA256"] == c.sha(c.regular(locations["evidence"] / (stage + "-named-execution.json")))
              and record["originalValidatorSHA256"] == c.sha(c.regular(Path(original.__file__))),
              "saved_files_semantic_proof_or_original_bytes_changed")
    return record

def provider_complete(locations, admission):
    directory = locations["evidence"] / "hanlin-provider"
    record = c.data(directory / "verify.json")
    transcript = c.data(directory / "provider-contract.json")
    c.require(record.get("status") == "FINITE_PROVIDER_CONTRACT_VERIFIED"
              and record.get("sourceCommit") == admission["controlCommit"]
              and record.get("githubRunID") == admission["currentRunID"]
              and transcript.get("complete") is True and transcript.get("state") == "complete"
              and transcript.get("phase") == transcript.get("responsesDelivered") == 6,
              "current_qualified_provider_contract_incomplete")
    return {"verificationSHA256": c.sha(c.regular(directory / "verify.json")),
            "contractSHA256": c.sha(c.regular(directory / "provider-contract.json")),
            "providerControlCommit": admission["controlCommit"], "complete": True}

def custom_type(attachments, locations, admission, modules):
    named_receipt("native-ui-continuation", locations, admission, modules)
    validate_files_postflight(locations, admission, modules)
    provider_complete(locations, admission)
    named_receipt("custom-type", locations, admission, modules)
    original = modules["verify_custom_type"]
    private = attachment_directory(attachments, "custom-type", admission)
    receipt, raw = original.original_receipt(private)
    proof = original.validate_receipt(receipt)
    saved = originals_directory(locations, "custom-type")
    with (saved / "ui-receipt.json").open("xb") as stream:
        stream.write(raw)
    return {"schemaVersion": 1, "status": "PASS", **context(admission), **proof,
            "scope": "actual_custom_type_and_fresh_process_in_original_native_ui_products",
            "fullAcceptance": False, "actualMethodCount": 1, "actualMethod": original.METHOD,
            "uiReceiptSHA256": c.sha(raw),
            "originalValidatorSHA256": c.sha(c.regular(Path(original.__file__))),
            "namedReceiptSHA256": c.sha(c.regular(locations["evidence"] / "custom-type-named-execution.json")),
            "priorReceiptSHA256": {name: c.sha(c.regular(locations["evidence"] / name)) for name in
                ("native-ui-continuation-named-execution.json", "archive-roundtrip/postflight.json",
                 "hanlin-provider/verify.json")},
            "fixtureBoundary": "Original three definition writes only; normal UI owns document, membership, property and body changes."}

def validate_type_postflight(locations, admission, modules):
    record = c.data(locations["evidence"] / "custom-type/postflight.json")
    c.require(record.get("status") == "PASS" and record.get("actualMethodCount") == 1
              and all(record.get(k) == v for k, v in context(admission).items()), "current_type_postflight_changed")
    raw = c.regular(locations["evidence"] / "custom-type/originals/ui-receipt.json", 64 * 1024)
    original = modules["verify_custom_type"]
    proof = original.validate_receipt(c.strict_json(raw))
    c.require(all(record.get(k) == v for k, v in proof.items()) and record["uiReceiptSHA256"] == c.sha(raw)
              and record["originalValidatorSHA256"] == c.sha(c.regular(Path(original.__file__)))
              and record["namedReceiptSHA256"] == c.sha(c.regular(locations["evidence"] / "custom-type-named-execution.json"))
              and record["priorReceiptSHA256"] == {name: c.sha(c.regular(locations["evidence"] / name)) for name in
                   ("native-ui-continuation-named-execution.json", "archive-roundtrip/postflight.json",
                    "hanlin-provider/verify.json")}, "saved_type_semantic_proof_or_original_bytes_changed")
    return record

def aggregate(locations, admission, modules):
    named = {stage: named_receipt(stage, locations, admission, modules) for stage in c.STAGES}
    files = validate_files_postflight(locations, admission, modules)
    custom = validate_type_postflight(locations, admission, modules)
    provider = provider_complete(locations, admission)
    integrity = c.data(locations["evidence"] / "final-products-check.json")
    c.require(integrity.get("status") == "UNCHANGED_ORIGINAL_PRODUCTS_CONTROL_AND_APP"
              and all(integrity.get(k) == v for k, v in context(admission).items())
              and integrity.get("currentBuilds") == integrity.get("methodsExecutedByThisCheck") == 0,
              "current_final_integrity_not_proven")
    cleanup = c.data(locations["evidence"] / "hanlin-provider/cleanup.json")
    c.require(cleanup.get("status") == "OWNED_FIXTURE_STOPPED_AND_PRIVATE_MATERIAL_REMOVED"
              and cleanup.get("sourceCommit") == admission["controlCommit"]
              and cleanup.get("githubRunID") == admission["currentRunID"], "provider_cleanup_not_proven")
    simulator = c.data(locations["evidence"] / "native-ui-original-simulator-cleanup.json")
    c.require(simulator.get("status") == "OWNED_SIMULATOR_REMOVAL_OBSERVED"
              and simulator.get("ownedSimulatorUDID") == admission["ownedSimulatorUDID"]
              and simulator.get("currentRunID") == admission["currentRunID"]
              and simulator.get("controlCommit") == admission["controlCommit"]
              and simulator.get("currentRunAttempt") == admission["currentRunAttempt"]
              and simulator.get("ownedSimulatorRemoved") is True and simulator.get("absenceProof") is True,
              "current_owned_simulator_cleanup_not_proven")
    count = sum(len(value["actualCases"]) for value in named.values())
    c.require(count == 7, "exact_seven_current_original_products_methods_required")
    return {"schemaVersion": 1, "status": "PASS_ORIGINAL_PRODUCTS_CONTINUATION",
            **context(admission), "scope": "seven_named_native_ui_methods_in_original_4b_products",
            "currentExecutedMethodCount": count, "currentApplicationBuilds": 0, "currentUIRunnerBuilds": 0,
            "retainedMethodCount": 22, "retainedMethodsExecutedThisRun": 0,
            "retainedMethodsWithOrigins": admission["retainedProof"]["retainedMethodsWithOrigins"],
            "originalRunConclusion": "failure", "originalFailedBatchesRemainFailure": True,
            "fullAcceptance": False, "currentSharedAppAcceptance": False,
            "wholeAPP01": "OPEN", "physicalDeviceAcceptance": "NOT_RUN",
            "namedReceiptSHA256": {stage: c.sha(c.regular(locations["evidence"] /
                                                       (stage + "-named-execution.json"))) for stage in c.STAGES},
            "filesReceiptSHA256": c.sha(c.regular(locations["evidence"] / "archive-roundtrip/postflight.json")),
            "typeReceiptSHA256": c.sha(c.regular(locations["evidence"] / "custom-type/postflight.json")),
            "provider": provider, "finalIntegritySHA256": c.sha(c.regular(locations["evidence"] / "final-products-check.json")),
            "providerCleanupSHA256": c.sha(c.regular(locations["evidence"] / "hanlin-provider/cleanup.json")),
            "simulatorCleanupSHA256": c.sha(c.regular(locations["evidence"] / "native-ui-original-simulator-cleanup.json"))}
