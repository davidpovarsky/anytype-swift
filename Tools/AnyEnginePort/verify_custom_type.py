#!/usr/bin/env python3
"""Source-bound exact-one native custom Type UI proof, reusing one built app."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import uuid

import verify_native_test_execution as execution
from verify_archive_roundtrip import regular_bytes, strict_json, same_value

ROOT = Path(__file__).resolve().parents[2]
METHOD = "NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen"
ATTACHMENT = "native-custom-type-transition-receipt"
CONTRACT = "pinkha-native-custom-type-ui-v1"
PROFILE = "native-custom-type"
APP_ID = "io.pinkha.anynative.dev"
UI_TARGET = "PinkhaAnyNativeUITests"
UI_BUNDLE_ID = "io.pinkha.anynative.uitests"
ORIGINAL_TEST_SHA256 = "ffc938a140fbaa6bf3cc4ef30603f6d0fde08b30f82c08ae5f8e07859e917ec2"
SOURCES = (
    "NativeApp/Sources/AnyNativeApp.swift",
    "NativeApp/Sources/NativeCustomTypeFixture.swift",
    "NativeApp/UITests/NativeLaunchTests.swift",
    "NativeApp/AnyNative.xcodeproj/project.pbxproj",
    "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme",
    "Tools/AnyEnginePort/verify_custom_type.py",
    "Tools/AnyEnginePort/verify_native_test_execution.py",
    "Tools/AnyEnginePort/verify_archive_roundtrip.py",
    ".github/workflows/pinkha-any-engine-port.yml",
)
SEED_KEYS = {
    "contract", "scopeUUID", "attemptUUID", "accountID", "spaceID", "ownerGeneration", "engineStartedAt",
    "processID", "typeID", "typeName", "typeKey", "pageTypeName", "propertyID", "propertyName", "propertyKey",
    "canonicalEditorDataset", "eligible", "nativeWrites", "documentWrites", "bodyWrites", "membershipWrites",
}
OBSERVATION_KEYS = {"contract", "phase", "seed", "nativeWritesThisProcess", "ownerGeneration", "engineStartedAt", "processID"}
RECEIPT_KEYS = {
    "schemaVersion", "contract", "method", "scopeUUID", "documentName", "objectID",
    "initialTypeID", "initialTypeName", "selectedTypeID", "selectedTypeName", "coldTypeName",
    "propertyID", "propertyValue", "coldPropertyValue", "beforeType", "afterType", "afterEdit", "afterCold",
    "prepare", "audit", "coldProcessReopen", "creationFlagRemoved", "auditFlagPresent", "blockCountBefore", "blockCountAfter",
}
MACHO = {bytes.fromhex(value) for value in
         ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def identity(value):
    return isinstance(value, str) and 0 < len(value.encode()) <= 1024 and "\0" not in value and value not in {".", ".."}


def exact_uuid(value):
    require(isinstance(value, str) and str(uuid.UUID(value)).upper() == value, "canonical_uuid_required")


def validate_receipt(receipt):
    require(isinstance(receipt, dict) and set(receipt) == RECEIPT_KEYS, "exact_ui_receipt_shape")
    require(type(receipt["schemaVersion"]) is int and receipt["schemaVersion"] == 1 and
            receipt["contract"] == "pinkha-native-custom-type-ui-journey-v1" and receipt["method"] == METHOD,
            "ui_receipt_contract")
    scope = receipt["scopeUUID"]
    exact_uuid(scope)
    suffix, token = scope[:8], scope.lower().replace("-", "")
    prepare, audit = receipt["prepare"], receipt["audit"]
    for observation, phase, writes in ((prepare, "prepare", 3), (audit, "audit", 0)):
        require(isinstance(observation, dict) and set(observation) == OBSERVATION_KEYS and
                observation["contract"] == CONTRACT and observation["phase"] == phase, "fixture_observation_shape")
        require(type(observation["nativeWritesThisProcess"]) is int and
                observation["nativeWritesThisProcess"] == writes, "exact_fixture_write_count")
        require(type(observation["processID"]) is int and observation["processID"] > 0 and
                identity(observation["engineStartedAt"]), "actual_process_identity")
        exact_uuid(observation["ownerGeneration"])
    seed = prepare["seed"]
    require(isinstance(seed, dict) and set(seed) == SEED_KEYS and same_value(seed, audit["seed"]),
            "cold_process_must_reuse_exact_seed")
    require(seed["contract"] == CONTRACT and seed["scopeUUID"] == scope, "owned_fixture_scope")
    exact_uuid(seed["attemptUUID"])
    exact_uuid(seed["ownerGeneration"])
    require(all(identity(seed[key]) for key in ("accountID", "spaceID", "typeID", "propertyID", "engineStartedAt", "pageTypeName")),
            "native_definition_identity")
    require(seed["typeID"] != "page" and seed["typeName"] == "UI canonical Type " + suffix and
            seed["pageTypeName"] != seed["typeName"] and seed["typeKey"] == "ui_custom_type_" + token and
            seed["propertyName"] == "UI custom value " + suffix and seed["propertyKey"] == "ui_custom_value_" + token,
            "actual_distinct_custom_type")
    require(seed["eligible"] is True and seed["canonicalEditorDataset"] == "editor_blocks", "native_canonical_type_policy")
    for key, count in (("nativeWrites", 3), ("documentWrites", 0), ("bodyWrites", 0), ("membershipWrites", 0)):
        require(type(seed[key]) is int and seed[key] == count, "fixture_cannot_write_document_or_membership")
    require(type(seed["processID"]) is int and seed["processID"] == prepare["processID"] != audit["processID"] and
            seed["ownerGeneration"] == prepare["ownerGeneration"] != audit["ownerGeneration"] and
            seed["engineStartedAt"] == prepare["engineStartedAt"] != audit["engineStartedAt"], "fresh_process_and_native_owner")
    require(receipt["coldProcessReopen"] is True and receipt["creationFlagRemoved"] is True and
            receipt["auditFlagPresent"] is True, "cold_read_only_fixture_mode")
    require(receipt["initialTypeID"] == "page" and receipt["initialTypeName"] == seed["pageTypeName"] and
            receipt["selectedTypeID"] == seed["typeID"] and
            receipt["selectedTypeName"] == receipt["coldTypeName"] == seed["typeName"], "ui_native_type_readback")
    require(receipt["propertyID"] == seed["propertyID"] and
            receipt["propertyValue"] == receipt["coldPropertyValue"] == "ערך משותף " + suffix + " 864", "ui_property_readback")
    require(receipt["documentName"] == "Custom Type UI Document " + suffix and identity(receipt["objectID"]),
            "same_native_document")
    before = ("שלום סוג מסמך מותאם ABC 482 " + suffix).encode()
    after = before + " — נשמר בסוג החדש 739".encode()
    block_ids = []
    for key, expected in (("beforeType", before), ("afterType", before), ("afterEdit", after), ("afterCold", after)):
        value = receipt[key]
        require(isinstance(value, dict) and set(value) == {"nativeBlockID", "sha256", "utf8Count"} and
                identity(value["nativeBlockID"]) and value["sha256"] == sha(expected) and
                type(value["utf8Count"]) is int and value["utf8Count"] == len(expected), "exact_body_bytes_" + key)
        block_ids.append(value["nativeBlockID"])
    require(len(set(block_ids)) == 1 and all(type(receipt[key]) is int and receipt[key] == 1
            for key in ("blockCountBefore", "blockCountAfter")), "same_single_native_block")
    return {"nativeTypeID": seed["typeID"], "propertyID": seed["propertyID"], "objectID": receipt["objectID"],
            "nativeBlockID": block_ids[0], "initialBodySHA256": sha(before), "coldBodySHA256": sha(after),
            "fixtureNativeWrites": 3, "coldFixtureNativeWrites": 0,
            "nativeCanonicalTypeEligible": True, "freshIOSProcessReopen": True}


def original_receipt(directory):
    manifest = strict_json(regular_bytes(directory / "manifest.json", directory, 1024 * 1024))
    require(isinstance(manifest, list), "attachment_manifest_shape")
    cases = [case for case in manifest if isinstance(case, dict) and
             case.get("testIdentifier", "").removesuffix("()") == METHOD]
    require(len(cases) == 1, "exactly_one_original_ui_attachment_case")
    exported = re.compile(re.escape(ATTACHMENT) + r"_\d+_[0-9A-Fa-f-]{36}\.json")
    matches = [entry for entry in cases[0].get("attachments", []) if isinstance(entry, dict) and
               (entry.get("suggestedHumanReadableName") == ATTACHMENT or
                exported.fullmatch(entry.get("suggestedHumanReadableName", "")))]
    require(len(matches) == 1, "exactly_one_original_ui_receipt")
    name = matches[0].get("exportedFileName")
    require(isinstance(name, str) and Path(name).name == name and "/" not in name and "\\" not in name,
            "unsafe_attachment_basename")
    raw = regular_bytes(directory / name, directory, 64 * 1024)
    return strict_json(raw), raw


def validate_sources(root=ROOT):
    raw = (root / SOURCES[2]).read_bytes()
    require(b"\r" not in raw, "source_must_use_canonical_lf")
    begin, end = b"    // BEGIN_NATIVE_CUSTOM_TYPE_UI_V1\n", b"    // END_NATIVE_CUSTOM_TYPE_UI_V1\n\n"
    require(raw.count(begin) == raw.count(end) == 1, "one_additive_ui_section_required")
    prefix, section = raw.split(begin)
    method, suffix = section.split(end)
    require(sha(prefix + suffix) == ORIGINAL_TEST_SHA256, "existing_tests_or_helpers_changed")
    require(method.count(b"    func test") == 1 and
            ("func " + METHOD.split("/")[1] + "() throws").encode() in method,
            "one_new_actual_ui_method_required")
    fixture = (root / SOURCES[1]).read_text(encoding="utf-8")
    require(fixture.startswith("#if DEBUG\n") and fixture.rstrip().endswith("#endif"), "debug_only_fixture_required")
    audit = fixture.split("private nonisolated static func audit(", 1)[1].split(
        "private nonisolated static func validate(", 1)[0]
    require('method: "GET"' in audit and not re.search(r'method:\s*"(POST|PATCH|PUT|DELETE)"', audit),
            "cold_audit_must_be_read_only")
    require(fixture.count('method: "POST"') == fixture.count("counter.beforeNativeWrite()") == 3,
            "only_three_counted_definition_writes")
    return {name: sha((root / name).read_bytes()) for name in SOURCES}


def inventory(directory):
    require(directory.is_dir() and not directory.is_symlink(), "built_bundle_missing")
    root, entries, code = directory.resolve(), {}, {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        require(path.resolve().is_relative_to(root), "external_bundle_dependency")
        if path.is_symlink():
            require(path.exists(), "dangling_bundle_symlink")
            entries[relative] = {"symlink": os.readlink(path)}
        elif path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                first = stream.read(4); digest.update(first)
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            entry = {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}
            entries[relative] = entry
            if first in MACHO:
                code[relative] = entry
    require(entries and code, "actual_executable_carriers_required")
    return {"sha256": canonical(entries), "entries": entries, "codeCarriers": code}


class UniquePlistDictionary(dict):
    def __setitem__(self, key, value):
        require(key not in self, "duplicate_compiled_plist_key")
        super().__setitem__(key, value)


def compiled_plist(path, products):
    require(path.resolve().is_relative_to(products.resolve()), "compiled_plist_escaped_products")
    value = plistlib.loads(regular_bytes(path, path.parent, 8 * 1024 * 1024), dict_type=UniquePlistDictionary)
    require(isinstance(value, dict), "compiled_plist_dictionary_required")
    return value


def compiled_ui_target(configuration):
    """Read Apple's two xctestrun schemas without choosing among multiple targets.

    Schemes with Testables (our committed scheme) use format 1; Test Plans use
    format 2. See Apple's Xcode 11 release notes, Testing (46346053).
    The format 1 target name is the dictionary key, not a required BlueprintName.
    """
    require(isinstance(configuration, dict), "compiled_ui_configuration_shape")
    metadata = configuration.get("__xctestrun_metadata__")
    if metadata is None:
        require("__xctestrun_metadata__" not in configuration, "compiled_ui_metadata_shape")
        version = 1
    else:
        require(isinstance(metadata, dict), "compiled_ui_metadata_shape")
        version = metadata.get("FormatVersion")
    require(type(version) is int and version in (1, 2), "compiled_ui_format_version")
    metadata_keys = {"__xctestrun_metadata__", "CodeCoverageBuildableInfos"}
    if version == 1:
        require(set(configuration) - metadata_keys == {UI_TARGET}, "compiled_ui_target_identity")
        target = configuration[UI_TARGET]
        require(isinstance(target, dict) and target.get("BlueprintName", UI_TARGET) == UI_TARGET,
                "compiled_ui_target_identity")
    else:
        require(set(configuration) <= metadata_keys | {"TestPlan", "TestConfigurations"},
                "compiled_ui_mixed_formats")
        configs = configuration.get("TestConfigurations")
        require(isinstance(configs, list) and len(configs) == 1 and isinstance(configs[0], dict) and
                configs[0].get("IsEnabled", True) is True, "compiled_ui_configuration_identity")
        targets = configs[0].get("TestTargets")
        require(isinstance(targets, list) and len(targets) == 1 and isinstance(targets[0], dict),
                "compiled_ui_target_identity")
        target = targets[0]
        require(target.get("BlueprintName") == UI_TARGET, "compiled_ui_target_identity")
    require(target.get("IsUITestBundle", True) is True and target.get("IsEnabled", True) is True and
            target.get("BlueprintIsSkipped", False) is False and
            target.get("UseDestinationArtifacts", False) is False,
            "compiled_ui_local_enabled_test_bundle_required")
    require(target.get("ProductModuleName", UI_TARGET) == UI_TARGET, "compiled_ui_module_identity")
    return version, target


def compiled_product_path(value, *, products, host, expected):
    require(isinstance(value, str) and value and "\0" not in value and "\\" not in value,
            "compiled_ui_product_path_shape")
    expanded = value
    placeholders = [("__TESTROOT__", products)]
    if host is not None:
        placeholders.append(("__TESTHOST__", host))
    for placeholder, directory in placeholders:
        if value == placeholder or value.startswith(placeholder + "/"):
            expanded = str(directory) + value[len(placeholder):]
            break
    path = Path(expanded)
    require(path.is_absolute() and ".." not in path.parts and not re.search(r"__[A-Z][A-Z0-9_]*__", expanded) and
            path.is_dir() and path.resolve() == expected.resolve() and
            path.resolve().is_relative_to(products.resolve()), "compiled_ui_product_path_identity")


def product_identity(derived, *, root=ROOT):
    products = derived.resolve() / "Build/Products"
    app = products / "Debug-iphonesimulator/PinkhaAnyNative.app"
    runner = products / "Debug-iphonesimulator/PinkhaAnyNativeUITests-Runner.app"
    info = compiled_plist(app / "Info.plist", products)
    require(info.get("CFBundleIdentifier") == APP_ID and info.get("CFBundleExecutable") == "PinkhaAnyNative",
            "native_application_identity")
    bundle = runner / "PlugIns/PinkhaAnyNativeUITests.xctest"
    require(bundle.is_dir(), "actual_ui_test_bundle_missing")
    runner_info = compiled_plist(runner / "Info.plist", products)
    bundle_info = compiled_plist(bundle / "Info.plist", products)
    require(runner_info.get("CFBundleIdentifier") == UI_BUNDLE_ID + ".xctrunner" and
            runner_info.get("CFBundleExecutable") == UI_TARGET + "-Runner" and
            bundle_info.get("CFBundleIdentifier") == UI_BUNDLE_ID and
            bundle_info.get("CFBundleExecutable") == UI_TARGET, "compiled_ui_bundle_identity")
    candidates = sorted(products.glob("PinkhaAnyNativeApp_*.xctestrun"))
    require(len(candidates) == 1 and not candidates[0].is_symlink(), "one_compiled_native_test_configuration")
    configuration = compiled_plist(candidates[0], products)
    version, target = compiled_ui_target(configuration)
    for field, expected in (("TestHostPath", runner), ("TestBundlePath", bundle), ("UITargetAppPath", app)):
        compiled_product_path(target.get(field), products=products,
                              host=runner if field == "TestBundlePath" else None, expected=expected)
    require(target.get("TestHostBundleIdentifier", UI_BUNDLE_ID + ".xctrunner") == runner_info["CFBundleIdentifier"] and
            target.get("UITargetAppBundleIdentifier", APP_ID) == info["CFBundleIdentifier"],
            "compiled_ui_launch_bundle_identity")
    binding_path = root / "Modules/PinkhaAnyRuntime/Vendor/consumer-binding.json"
    artifact_path = root / "Modules/PinkhaAnyRuntime/Vendor/native-artifact.json"
    binding = strict_json(binding_path.read_bytes())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(binding.get("status") == "SOURCE_IDENTICAL_NATIVE_ARTIFACT" and
            binding.get("consumerCommit") == commit and binding.get("testResultsRelabeled") is False and
            binding.get("reused") is True and binding.get("artifactReceiptSHA256") == sha(artifact_path.read_bytes()),
            "source_identical_native_runtime_binding")
    return {"app": inventory(app), "uiRunner": inventory(runner),
            "xctestrun": {"name": candidates[0].name, "sha256": sha(candidates[0].read_bytes()),
                          "formatVersion": version, "target": UI_TARGET,
                          "testBundle": bundle.relative_to(products).as_posix(),
                          "testHost": runner.relative_to(products).as_posix(),
                          "uiTargetApp": app.relative_to(products).as_posix()},
            "nativeBindingSHA256": sha(binding_path.read_bytes()), "nativeArtifactSHA256": sha(artifact_path.read_bytes()),
            "nativeProducerCommit": binding.get("producerCommit"),
            "nativeSourceManifestSHA256": binding.get("sourceManifestSHA256")}


def current_context(simulator):
    from hanlin_fixture_ci import github_context, verify_simulator
    run_id, commit, _ = github_context()
    udid, _, _ = verify_simulator(simulator, run_id)
    subprocess.run(["git", "diff", "--exit-code", "--quiet", "HEAD", "--"], cwd=ROOT, check=True)
    return {"githubRunID": run_id, "commit": commit, "ownedSimulatorUDID": udid}


def capture(args):
    return {"schemaVersion": 1, "status": "FROZEN_BUILD_INPUTS", **current_context(args.simulator_receipt),
            "scope": "same_job_native_ui_product_identity", "sourceInputs": validate_sources(),
            "products": product_identity(args.derived)}


def validate_frozen(frozen, current):
    require(same_value(frozen, current), "source_runtime_or_compiled_products_changed")


def postflight(args):
    context = current_context(args.simulator_receipt)
    frozen = strict_json(args.frozen.read_bytes())
    validate_frozen(frozen, capture(args))
    summary = strict_json(args.summary.read_bytes())
    tests = strict_json(args.tests.read_bytes())
    executed = execution.validate(summary, tests, PROFILE, context["ownedSimulatorUDID"])
    receipt, raw = original_receipt(args.attachments)
    proof = validate_receipt(receipt)
    previous = {}
    for name, profile in (("native-ui", "native-ui-entry"), ("native-ui-followup", "native-ui-followup"),
                          ("archive-roundtrip", "archive-roundtrip")):
        path = args.previous / (name + "-named-execution.json")
        record = strict_json(path.read_bytes())
        require(record.get("status") == "PASS" and record.get("commit") == context["commit"] and
                record.get("profile") == profile and
                record.get("device", {}).get("deviceId", "").lower() == context["ownedSimulatorUDID"].lower(),
                "prior_same_products_stage_not_qualified_" + name)
        previous[profile] = sha(path.read_bytes())
    container = Path(subprocess.check_output(
        ["xcrun", "simctl", "get_app_container", context["ownedSimulatorUDID"], APP_ID, "app"],
        text=True, timeout=30).strip())
    installed = inventory(container)
    require(same_value(installed["codeCarriers"], frozen["products"]["app"]["codeCarriers"]),
            "installed_executable_bytes_differ_from_frozen_build")
    return {"schemaVersion": 1, "status": "PASS", **context, **proof, "profile": PROFILE,
            "scope": "actual_native_custom_type_ui_and_fresh_process_reopen", "fullAcceptance": False,
            "actualMethod": METHOD, "actualMethodCount": 1, "execution": executed,
            "fixtureBoundary": "Only three definition writes; document creation, Type membership, property value and body editing use the normal UI.",
            "claimBoundary": "One Page-to-custom eligible canonical Type journey; no claim for every possible Type schema or cross-device sync.",
            "uiReceiptSHA256": sha(raw), "summarySHA256": sha(args.summary.read_bytes()),
            "testTreeSHA256": sha(args.tests.read_bytes()), "frozenBuildSHA256": sha(args.frozen.read_bytes()),
            "priorStageReceipts": previous, "sameCompiledProducts": True,
            "installedCodeCarriersSHA256": canonical(installed["codeCarriers"]),
            "sourceInputs": frozen["sourceInputs"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "check", "postflight"))
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--simulator-receipt", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--attachments", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--tests", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "action": args.action,
              "scope": "native_custom_type_ui_admission", "fullAcceptance": False}
    try:
        if args.action == "capture":
            require(not args.output.exists(), "cannot_replace_original_frozen_build")
            record = capture(args)
        elif args.action == "check":
            validate_frozen(strict_json(args.frozen.read_bytes()), capture(args))
            record.update(status="UNCHANGED_BUILD_INPUTS", frozenBuildSHA256=sha(args.frozen.read_bytes()))
        else:
            record = postflight(args)
    except Exception as error:
        record["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Failure never overwrites an existing original capture.
    output = args.output if args.action != "capture" or not args.output.exists() else args.output.with_suffix(".rejected.json")
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: record[key] for key in ("status", "scope", "error") if key in record}, ensure_ascii=False))
    return 0 if record["status"] in {"PASS", "FROZEN_BUILD_INPUTS", "UNCHANGED_BUILD_INPUTS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

