#!/usr/bin/env python3
"""Continue only never-executed native UI scopes from admitted original Products."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import uuid
import native_ui_original_products_contract as c

def provider():
    module = importlib.import_module("hanlin_fixture_ci")
    c.require(Path(module.__file__).resolve() == c.ROOT / "Tools/AnyEnginePort/hanlin_fixture_ci.py",
              "current_qualified_provider_controller_required")
    return module

def environment(values):
    destination = Path(os.environ.get("GITHUB_ENV", ""))
    c.require(os.environ.get("GITHUB_ENV") and destination.is_file(), "actual_github_environment_file_required")
    with destination.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            c.require("\n" not in str(value) and "\r" not in str(value), "single_line_environment_required")
            stream.write(key + "=" + str(value) + "\n")

def base():
    fixed = c.contract()
    ctx = c.control_context(fixed)
    provider().github_context()
    locations = c.paths(ctx)
    c.validate_paths(locations)
    return fixed, ctx, locations

def create_simulator():
    fixed, ctx, locations = base()
    evidence = locations["evidence"]
    evidence.mkdir(parents=True, exist_ok=True)
    c.require(not (evidence / "simulator.json").exists(), "fresh_owned_simulator_receipt_required")
    commands = evidence / "native-ui-original-commands/create"
    xcode = c.public_command(["xcodebuild", "-version"], commands, "xcode-version")
    c.require(xcode.decode("utf-8") == fixed["originalXcodeText"], "original_xcode_version_changed")
    with (evidence / "xcode-version.txt").open("xb") as stream:
        stream.write(xcode)
    runtimes = c.strict_json(c.public_command(["xcrun", "simctl", "list", "runtimes", "--json"],
                                              commands, "runtimes"))
    devices = c.strict_json(c.public_command(["xcrun", "simctl", "list", "devicetypes", "--json"],
                                             commands, "device-types"))
    pair = c.runtime_pair(runtimes, devices, fixed)
    before = c.strict_json(c.public_command(["xcrun", "simctl", "list", "devices", "--json"],
                                            commands, "devices-before"))
    name = "AnyNativePort-" + ctx["currentRunID"]
    old_ids = set()
    for values in before.get("devices", {}).values():
        for device in values:
            c.require(device.get("name") != name, "current_run_simulator_already_exists")
            old_ids.add(str(device.get("udid", "")).upper())
    raw = c.public_command(["xcrun", "simctl", "create", name,
                            fixed["runtime"]["deviceType"], fixed["runtime"]["identifier"]],
                           commands, "create", timeout=30).decode("ascii").strip()
    udid = str(uuid.UUID(raw)).upper()
    c.require(raw == udid and udid not in old_ids and udid != fixed["originalSimulatorUDID"],
              "new_owned_simulator_required")
    # Publish the exact returned ownership immediately so later failures retain cleanup access.
    c.dump(evidence / "simulator.json", {"ownedUDID": udid, "runtime": fixed["runtime"]["identifier"],
                                       "deviceType": fixed["runtime"]["deviceType"]})
    environment({"ANY_NATIVE_SIMULATOR_UDID": udid})
    os.environ["ANY_NATIVE_SIMULATOR_UDID"] = udid
    verified, receipt, state = provider().verify_simulator(evidence / "simulator.json", ctx["currentRunID"])
    c.require(verified == udid and state == "Shutdown", "new_simulator_must_start_shutdown")
    c.dump(evidence / "native-ui-original-runtime.json",
           {"schemaVersion": 1, "status": "EXACT_INSTALLED_ORIGINAL_RUNTIME_PAIR",
            **ctx, "selection": pair["selection"], "runtime": pair["runtime"], "device": pair["device"],
            "ownedSimulatorUDID": udid, "originalSimulatorReused": False,
            "readiness": "NOT_RUN", "testsExecuted": 0})
    return {"status": "CREATED_FRESH_ORIGINAL_COMPATIBLE_SIMULATOR", "ownedSimulatorUDID": udid}

def fetch_original(fixed, locations):
    download = locations["download"]
    c.require(not download.exists(), "one_fresh_original_download_required")
    download.mkdir(parents=True)
    prefix = "repos/" + fixed["repository"] + "/actions/"
    routes = {"run": "runs/" + fixed["origin"]["runID"] + "/attempts/1",
              "artifact": "artifacts/" + str(fixed["artifact"]["id"]),
              "jobs": "runs/" + fixed["origin"]["runID"] + "/attempts/1/jobs?per_page=100"}
    records = {}
    for key, route in routes.items():
        raw = c.public_command(["gh", "api", prefix + route], download, "original-" + key, timeout=60)
        records[key] = c.strict_json(raw)
    api = c.validate_original_api(records["run"], records["artifact"], records["jobs"], fixed)
    c.public_command(["gh", "api", prefix + "artifacts/" + str(fixed["artifact"]["id"]) + "/zip"],
                     download, "original-carrier", timeout=180)
    carrier = download / "original-carrier.stdout"
    tar = download / "native-ui-products.tar.gz"
    c.extract_originals(carrier, locations["originals"], tar, fixed)
    api_dir = locations["evidence"] / "original-451082-api"
    api_dir.mkdir()
    for key in routes:
        shutil.copyfile(download / ("original-" + key + ".stdout"), api_dir / (key + ".json"))
    return tar, api

def copy_metadata(originals, app):
    vendor = app / "Modules/PinkhaAnyRuntime/Vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    for source, name in (("native-reuse.json", "consumer-binding.json"),
                         ("original-native-artifact.json", "native-artifact.json")):
        destination = vendor / name
        c.require(not destination.exists(), "original_generated_metadata_destination_must_be_fresh")
        with destination.open("xb") as stream:
            stream.write(c.regular(originals / source))

def validate_runtime_record(fixed, ctx, locations):
    evidence = locations["evidence"]
    record = c.data(evidence / "native-ui-original-runtime.json")
    c.require(all(record.get(k) == v for k, v in ctx.items()) and
              record.get("status") == "EXACT_INSTALLED_ORIGINAL_RUNTIME_PAIR", "current_runtime_origin_changed")
    pair = c.runtime_pair({"runtimes": [record["runtime"]]}, {"devicetypes": [record["device"]]}, fixed)
    c.require(record["selection"] == pair["selection"]
              and c.regular(evidence / "xcode-version.txt").decode() == fixed["originalXcodeText"],
              "runtime_or_xcode_binding_changed")
    simulator = c.data(evidence / "simulator.json")
    c.require(simulator == {"ownedUDID": record["ownedSimulatorUDID"],
                            "runtime": fixed["runtime"]["identifier"], "deviceType": fixed["runtime"]["deviceType"]}
              and simulator["ownedUDID"] != fixed["originalSimulatorUDID"],
              "current_owned_simulator_receipt_changed")
    return record

def admit():
    fixed, ctx, locations = base()
    runtime = validate_runtime_record(fixed, ctx, locations)
    c.require(not c.ADMISSION.exists() and not locations["app"].exists() and not locations["products"].exists(),
              "fresh_original_products_admission_required")
    locations["work"].mkdir(parents=True, exist_ok=True)
    c.public_command(["git", "worktree", "add", "--detach", str(locations["app"]), fixed["origin"]["commit"]],
                     locations["evidence"] / "native-ui-original-commands/admit", "original-app-checkout", timeout=180)
    modules = c.legacy_modules(locations["app"])
    source = c.application_source(locations["app"], fixed, modules)
    tar, api = fetch_original(fixed, locations)
    c.require(b"** TEST BUILD SUCCEEDED **" in c.regular(locations["originals"] / "native-ui-build.log"),
              "original_build_completion_marker_missing")
    frozen = c.data(locations["originals"] / "native-shared-products.json")
    c.require(frozen == fixed["frozenBuild"] and frozen["commit"] == fixed["origin"]["commit"]
              and frozen["githubRunID"] == fixed["origin"]["runID"]
              and frozen["scope"] == "same_job_native_ui_product_identity",
              "original_frozen_same_job_receipt_must_remain_original")
    c.restore_tar(tar, locations["products"], fixed["productEntries"])
    copy_metadata(locations["originals"], locations["app"])
    files = c.verify_entries(locations["products"], fixed["productEntries"])
    actual_product = modules["verify_custom_type"].product_identity(locations["derived"], root=locations["app"])
    c.require(actual_product == frozen["products"], "original_native_and_compiled_product_bindings_changed")
    retained = c.retained_proof(locations["originals"], locations["app"], fixed, modules)
    original_name = fixed["productArchive"]["xctestrun"][0]["path"]
    descriptor = c.copied_descriptor(locations["products"] / original_name,
                                    locations["products"] / c.COPY_NAME, runtime["runtime"], fixed)
    commands = locations["evidence"] / "native-ui-original-commands/admit"
    for key, bundle in (("application", "PinkhaAnyNative.app"),
                        ("ui-runner", "PinkhaAnyNativeUITests-Runner.app")):
        c.public_command(["codesign", "--verify", "--deep", "--strict",
                          str(locations["products"] / "Debug-iphonesimulator" / bundle)],
                         commands, "signature-" + key)
    carriers = []
    for entry in fixed["productEntries"]:
        if entry["kind"] != "file" or not entry["mode"] & 0o111:
            continue
        candidate = locations["products"] / entry["name"]
        with candidate.open("rb") as stream:
            magic = stream.read(4)
        if magic not in modules["verify_custom_type"].MACHO:
            continue
        architectures = c.public_command(["lipo", "-archs", str(candidate)], commands,
                                         "carrier-" + str(len(carriers))).decode().split()
        c.require("arm64" in architectures, "original_code_carrier_is_not_arm64")
        carriers.append({"path": entry["name"], "sha256": entry["sha256"],
                         "architectures": architectures, "mode": entry["mode"]})
    c.require(len(carriers) == 5, "five_original_executable_carriers_required")
    selection = {name: list(value[2]) for name, value in c.STAGES.items()}
    c.validate_selection(selection, fixed)
    original_hashes = {name: c.sha(c.regular(locations["originals"] / name))
                       for name in fixed["metadataSHA256"]}
    record = {"schemaVersion": 1, "status": "ADMITTED_ORIGINAL_NATIVE_UI_PRODUCTS",
              "contract": c.PROFILE, "contractSHA256": c.CONTRACT_SHA, **ctx,
              "applicationCommit": fixed["origin"]["commit"], "applicationCheckout": str(locations["app"]),
              "productsDirectory": str(locations["products"]), "originalProductOrigin": api,
              "originalArtifact": fixed["artifact"], "originalMetadataSHA256": original_hashes,
              "sourceProof": source, "retainedProof": retained, "restoredProducts": files,
              "originalFrozenBuildSHA256": fixed["metadataSHA256"]["native-shared-products.json"],
              "originalNativeBinding": {k: actual_product[k] for k in actual_product if k.startswith("native")},
              "executableCarriers": carriers, "copiedDescriptor": descriptor,
              "runtimeReceiptSHA256": c.sha(c.regular(locations["evidence"] / "native-ui-original-runtime.json")),
              "simulatorReceiptSHA256": c.sha(c.regular(locations["evidence"] / "simulator.json")),
              "ownedSimulatorUDID": runtime["ownedSimulatorUDID"],
              "selection": selection, "currentApplicationBuilds": 0, "currentUIRunnerBuilds": 0,
              "currentNativeLibraryBuilds": 0, "currentMethodsExecutedAtAdmission": 0,
              "fullAcceptance": False,
              "claimBoundary": "Original application4b and original compiled Products; current control/provider only. No current shared App, Page154, inline candidate or physical-device acceptance."}
    c.dump(c.ADMISSION, record)
    for stage in c.STAGES:
        c.dump(locations["evidence"] / (stage + "-original-products-plan.json"),
               c.plan(stage, Path(descriptor["path"]), runtime["ownedSimulatorUDID"],
                      locations["evidence"] / (stage + ".xcresult")))
    environment({"ANY_NATIVE_XCTESTRUN": descriptor["path"], "ANY_NATIVE_ORIGINAL_APP_ROOT": str(locations["app"])})
    return {"status": record["status"], "admissionSHA256": c.sha(c.regular(c.ADMISSION)),
            "originalFiles": files["originalRegularFiles"], "retainedMethods": 22, "newBuilds": 0, "newTests": 0}

def current():
    fixed, ctx, locations = base()
    record = c.data(c.ADMISSION)
    c.validate_admission_origin(record, fixed, ctx, locations)
    runtime = validate_runtime_record(fixed, ctx, locations)
    c.require(c.sha(c.regular(locations["evidence"] / "native-ui-original-runtime.json")) == record["runtimeReceiptSHA256"]
              and c.sha(c.regular(locations["evidence"] / "simulator.json")) == record["simulatorReceiptSHA256"]
              and record["ownedSimulatorUDID"] == runtime["ownedSimulatorUDID"], "current_runtime_binding_changed")
    c.validate_selection(record["selection"], fixed)
    modules = c.legacy_modules(locations["app"])
    c.require(c.application_source(locations["app"], fixed, modules) == record["sourceProof"],
              "current_original_application_source_changed")
    files = c.verify_entries(locations["products"], fixed["productEntries"], record["copiedDescriptor"]["sha256"])
    c.require(files == record["restoredProducts"], "original_product_inventory_changed")
    original_product = modules["verify_custom_type"].product_identity(locations["derived"], root=locations["app"])
    c.require(original_product == fixed["frozenBuild"]["products"], "original_product_or_native_binding_changed")
    for name, expected in record["originalMetadataSHA256"].items():
        c.require(expected == fixed["metadataSHA256"][name] and
                  c.sha(c.regular(locations["originals"] / name)) == expected, "original_metadata_binding_changed")
    copied = record["copiedDescriptor"]
    c.require(copied["path"] == str(locations["products"] / c.COPY_NAME)
              and copied["originalSHA256"] == fixed["productArchive"]["xctestrun"][0]["sha256"],
              "copied_descriptor_path_or_original_changed")
    library = Path(copied["normalization"]["replacement_token"])
    c.require(c.file_sha(library) == copied["normalization"]["library_sha256"]
              and library.stat().st_size == copied["normalization"]["library_bytes"],
              "actual_runtime_injection_library_changed")
    original = plistlib.loads(c.regular(locations["products"] / fixed["productArchive"]["xctestrun"][0]["path"]))
    configured = plistlib.loads(c.regular(Path(copied["path"])))
    c.require(configured["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"]
              == copied["normalization"]["replacement_token"], "copied_runtime_token_changed")
    configured["PinkhaAnyNativeUITests"]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = (
        fixed["runtime"]["originalMainThreadChecker"])
    c.require(configured == original, "copied_descriptor_contains_unadmitted_change")
    c.require(record["retainedProof"]["retainedMethodsWithOrigins"] == fixed["retainedMethods"]
              and record["retainedProof"]["retainedMethodCount"] == 22
              and record["retainedProof"]["retainedMethodsExecutedThisRun"] == 0,
              "original_retained_scope_changed")
    return fixed, ctx, locations, record, modules

def check(label):
    c.require(label in {*c.STAGES, "final"}, "fixed_integrity_phase_required")
    fixed, ctx, locations, admission, modules = current()
    if label != "final":
        provider().verify_simulator(locations["evidence"] / "simulator.json", ctx["currentRunID"])
    return {"schemaVersion": 1, "status": "UNCHANGED_ORIGINAL_PRODUCTS_CONTROL_AND_APP",
            **receipt_context(admission), "phase": label, "originalFiles": 216,
            "currentBuilds": 0, "methodsExecutedByThisCheck": 0}

def receipt_context(admission):
    return {key: admission[key] for key in
            ("controlCommit", "currentRunID", "currentRunAttempt", "applicationCommit", "ownedSimulatorUDID")} | {
                "contract": c.PROFILE, "admissionSHA256": c.sha(c.regular(c.ADMISSION)),
                "originalProductRunID": admission["originalProductOrigin"]["origin"]["runID"],
                "originalProductRunAttempt": admission["originalProductOrigin"]["origin"]["runAttempt"],
                "originalFrozenBuildSHA256": admission["originalFrozenBuildSHA256"],
                "copiedDescriptorSHA256": admission["copiedDescriptor"]["sha256"]}

def cleanup_simulator():
    fixed, ctx, locations = base()
    path = locations["evidence"] / "simulator.json"
    if not path.exists():
        return {"schemaVersion": 1, "status": "NO_SIMULATOR_WAS_CREATED", **ctx,
                "ownedSimulatorRemoved": False, "absenceProof": False}
    udid, receipt, state = provider().verify_simulator(path, ctx["currentRunID"])
    commands = locations["evidence"] / "native-ui-original-commands/cleanup"
    errors = []
    for label, command in (("shutdown", ["xcrun", "simctl", "shutdown", udid]),
                           ("delete", ["xcrun", "simctl", "delete", udid])):
        try:
            c.public_command(command, commands, label, timeout=30)
        except (ValueError, subprocess.TimeoutExpired, OSError) as error:
            errors.append({"command": label, "kind": type(error).__name__})
    # An explicit post-delete inventory is required; timeout never proves absence.
    after = c.strict_json(c.public_command(["xcrun", "simctl", "list", "devices", "--json"],
                                           commands, "devices-after", timeout=30))
    present = [d for rows in after.get("devices", {}).values() for d in rows
               if str(d.get("udid", "")).upper() == udid]
    c.require(not present and not any(e["command"] == "delete" for e in errors),
              "owned_simulator_deletion_not_proven")
    return {"schemaVersion": 1, "status": "OWNED_SIMULATOR_REMOVAL_OBSERVED", **ctx,
            "ownedSimulatorUDID": udid, "ownedSimulatorRemoved": True, "absenceProof": True,
            "originalShutdownObservations": errors, "foreignSimulatorsTouched": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create-simulator", "admit", "check", "named", "files", "type",
                                          "aggregate", "cleanup-simulator"))
    parser.add_argument("--stage", choices=(*c.STAGES, "final"))
    parser.add_argument("--test-exit", type=int)
    parser.add_argument("--attachments", type=Path)
    args = parser.parse_args()
    destinations = {"create-simulator": "native-ui-original-simulator-create.json",
                    "admit": "native-ui-original-products-restore.json",
                    "files": "archive-roundtrip/postflight.json", "type": "custom-type/postflight.json",
                    "aggregate": "native-ui-original-products-aggregate.json",
                    "cleanup-simulator": "native-ui-original-simulator-cleanup.json"}
    if args.action in {"named", "check"}:
        c.require(args.stage is not None, "fixed_stage_required")
        name = args.stage + ("-named-execution.json" if args.action == "named" else "-products-check.json")
    else:
        name = destinations[args.action]
    output = c.EVIDENCE / name
    c.require(not output.exists(), "original_action_receipt_already_exists")
    result = {"schemaVersion": 1, "status": "FAIL", "action": args.action,
              "contract": c.PROFILE, "fullAcceptance": False}
    try:
        if args.action == "create-simulator":
            result.update(create_simulator())
        elif args.action == "admit":
            result.update(admit())
        elif args.action == "check":
            result.update(check(args.stage))
        elif args.action == "cleanup-simulator":
            result.update(cleanup_simulator())
        else:
            import native_ui_original_products_results as results
            fixed, ctx, locations, admission, modules = current()
            if args.action == "named":
                result.update(results.named(args.stage, args.test_exit, locations, admission, modules))
            elif args.action == "files":
                result.update(results.files(args.attachments, locations, admission, modules))
            elif args.action == "type":
                result.update(results.custom_type(args.attachments, locations, admission, modules))
            else:
                result.update(results.aggregate(locations, admission, modules))
    except Exception as error:
        result["failure"] = {"kind": type(error).__name__, "reason": str(error)[:1200]}
    c.dump(output, result)
    print(json.dumps({"action": args.action, "status": result["status"], "receipt": str(output),
                      "failure": result.get("failure")}, sort_keys=True))
    return 1 if result["status"] == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
