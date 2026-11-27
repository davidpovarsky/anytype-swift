#!/usr/bin/env python3
"""Execute the five original App15 UIKit gesture ownership controls, without builds."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
import combined_heart_semantics_current as c

COMMON_SHA = "1dcd02a4413b26c201e8a38772484eff48e448ae4398af2fd4ee1fc6a5675736"
ADMISSION_SHA = "87c47c356e591ee7f51e6c3fa21a4fe0cd903821cceec357ed11cfbfc582a366"
RETENTION_SHA = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
COMMIT = "379ca3568f247d2fc218ed63df24796d461713c0"
SOURCE = "AnyTypeTests/Pinkha/TextViewLinkGestureArbitrationTests.swift"
SOURCE_SHA = "75a75277870bedb564a5015e1c1f33b17369f179db1802620016b63c563dd1fd"
SUITE = "TextViewLinkGestureArbitrationTests"
METHODS = (
    "sameInputSingleTapDefersToLinkSelection",
    "foreignAndUnrelatedGesturesRemainIndependent",
    "nativeTextInteractionUsesPublicOwnership",
    "removalAndReattachmentRetirePriorRecognizer",
    "singleTapAttributeHandlersRemainIndependent",
)
HELPERS = {
    "Tools/Hanlin/run_host_tests.py": "106d40df8594c067fdcc389d0ac93e3055a01247d431b13563f9d6e0d1c3403d",
    "Tools/Hanlin/host_command.py": "5f09813c5719f5ea3920c003e58ac6b2b5633f276686bf6c5ef8bc6f9f39a807",
    "Tools/Hanlin/wave15_core_profile.py": "f544619607be0d25e74cff541ac66418b76df11abcd9c15c0ca774d6cbd5d96a",
    "Tools/Hanlin/shared_editor_profile.py": "77d27d083f8073ad027cd28e98f2e2986aaee1cb2e31d2931287e33a4f8497c8",
}


def specification():
    return {name: {"parameters": [], "argument_collections": [], "case_count": 1} for name in METHODS}


def load_original_validators(source, root):
    for name, digest in HELPERS.items():
        value = c.raw(source / name)
        c.require(c.sha(value) == digest, "Exact compiled-source result helper differs: " + name)
        original = subprocess.check_output(["git", "-C", str(source), "show", COMMIT + ":" + name], timeout=30)
        c.require(value == original, "Result helper differs from compiled Git source")
        c.write_bytes(root / "helpers" / name, value)
    for name in ("Tools/Hanlin", "Tools/CurrentAppleValidation"):
        sys.path.insert(0, str(root / "helpers" / name))
    host = importlib.import_module("run_host_tests")
    core = importlib.import_module("wave15_core_profile")
    c.common = importlib.import_module("contracts")
    c.boundary = importlib.import_module("page154_boundary")
    for module in (host, core, c.common, c.boundary):
        c.require(Path(module.__file__).resolve().is_relative_to(root / "helpers"), "Foreign original validator")
    value = c.raw(source / SOURCE)
    c.require(c.sha(value) == SOURCE_SHA, "Exact five-control UIKit source required")
    original = subprocess.check_output(["git", "-C", str(source), "show", COMMIT + ":" + SOURCE], timeout=30)
    c.require(value == original and core.inspect_declarations(value.decode()) == specification(),
              "Actual source declarations differ from the original five methods")
    return host, core


def descriptor(built, app):
    first = "AnytypeTests/" + SUITE + "/" + METHODS[0] + "()"
    data, proof = c.bind_descriptor(built, app, first, {})
    value = plistlib.loads(data)
    before = copy.deepcopy(value)
    target = value["TestConfigurations"][0]["TestTargets"][0]
    target["OnlyTestIdentifiers"] = [SUITE]
    inverse = copy.deepcopy(value)
    inverse["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"] = (
        before["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"])
    c.require(inverse == before, "Gesture suite scope changed nonselection configuration")
    proof.update(originalFiveMethods=list(METHODS), suiteFilter=SUITE, exactSuiteSelectionInverse=True)
    return plistlib.dumps(value, sort_keys=False), proof


def qualify_enumeration(value):
    c.require(isinstance(value, dict) and value.get("errors") == [], "Original enumeration errors")
    configs = value.get("values")
    c.require(isinstance(configs, list) and len(configs) == 1 and configs[0].get("testPlan") == "AnytypeTests",
              "Exact original native test plan required")
    actual = {}
    for key in ("enabledTests", "disabledTests"):
        rows = configs[0].get(key)
        c.require(isinstance(rows, list) and all(isinstance(row, dict) and isinstance(row.get("identifier"), str)
                                               for row in rows), "Original enumeration schema differs")
        values = [row["identifier"] for row in rows]
        c.require(len(values) == len(set(values)), "Duplicate enumeration method")
        normalized = []
        for value in values:
            parts = value.split("/")
            if len(parts) == 3:
                c.require(parts[0] == "AnytypeTests", "Foreign compiled test target")
                parts = parts[1:]
            c.require(len(parts) == 2 and all(parts), "Exact compiled suite/method identity required")
            normalized.append("/".join(parts))
        c.require(len(normalized) == len(set(normalized)), "Duplicate canonical compiled method")
        actual[key] = normalized
    expected = {SUITE + "/" + name + "()" for name in METHODS}
    c.require(set(actual["enabledTests"]) == expected
              and not expected.intersection(actual["disabledTests"]), "Every exact five compiled methods required")
    return {"status": "PASS_EXACT_FIVE_COMPILED_METHODS", **actual}


def qualify_results(summary, tree, udid, host, core):
    expected = {SUITE + "/" + name for name in METHODS}
    result = host.validate_results(summary, tree, expected, udid)
    c.require(result["counts"] == {"totalTestCount": 5, "passedTests": 5, "failedTests": 0, "skippedTests": 0},
              "Five actual passing methods without failures/skips required")
    device = result["device"]
    c.require(device.get("platform") == "iOS Simulator" and device.get("osVersion") == c.OS_VERSION
              and device.get("osBuildNumber") == c.OS_BUILD, "Exact owned original iOS runtime required")
    cases = core.validate_arguments(tree, expected, {SUITE: {"methods": specification()}})
    c.require(cases["actual_method_count"] == cases["declared_case_count"] == 5, "Five original named cases required")
    return dict(result, **cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    own = Path(__file__).resolve().parent
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Original Apple Silicon execution")
    c.require(Path(c.__file__).resolve() == own / "combined_heart_semantics_current.py"
              and c.digest(Path(c.__file__)) == COMMON_SHA, "Exact canonical common required")
    c.require(c.digest(Path(__file__)) == args.controller_sha256
              and c.digest(own / "retain_owned_heart_account.py") == RETENTION_SHA, "Exact reviewed controls required")
    admission_raw = c.raw(args.admission)
    c.require(c.sha(admission_raw) == ADMISSION_SHA, "Exact canonical App15 admission required")
    admission = c.decode(admission_raw)
    c.require(admission["sourceCommit"] == COMMIT, "Original App15 source required")
    root = args.root
    c.require(root.is_absolute() and root.parent.resolve() == root.parent and not root.exists(),
              "Fresh canonical private execution root required")
    root.mkdir(mode=0o700)
    evidence, private = root / "evidence", root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", admission_raw)
    commands = c.Commands(root / "commands", root)
    binding = {"sourceSHA": COMMIT, "runID": str(time.time_ns() // 1000), "runAttempt": "1", "nonce": uuid.uuid4().hex}
    result = {"status": "FAIL", "scope": "five original UIKit gesture controls; no full E/native ACL/Release claim",
              "binding": binding, "sourceCommit": COMMIT, "controllerSHA256": args.controller_sha256,
              "commonSHA256": COMMON_SHA, "nativeManifestSHA256": c.MANIFEST, "stages": {},
              "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "fullEAcceptance": False}
    built = {}; device = None; test_invoked = False
    try:
        mask = os.umask(0)
        try:
            proof, built, app = c.admit_and_clone_products(admission, root, evidence, commands)
        finally:
            os.umask(mask)
        result["sourceAdmission"] = proof
        host, core = load_original_validators(Path(admission["sourceRoot"]), root)
        result["sourceContract"] = {"path": SOURCE, "sha256": SOURCE_SHA, "methods": list(METHODS), "caseCount": 5}
        log, _ = commands.run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtime-inventory", 30)
        rows = [row for row in c.decode(c.raw(log))["runtimes"] if row.get("identifier") == c.RUNTIME]
        c.require(len(rows) == 1 and rows[0].get("isAvailable") is True and rows[0].get("version") == c.OS_VERSION
                  and rows[0].get("buildversion") == c.OS_BUILD, "Exact actual runtime required")
        log, _ = commands.run(["xcrun", "simctl", "create", "E-Combined-Heart-" + binding["nonce"],
                               c.DEVICE, c.RUNTIME], "create-owned-simulator", 60)
        device = c.raw(log, 4096).decode().strip()
        c.require(re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", device),
                  "Actual owned device identity required")
        result["ownedSimulator"] = device
        c.write(evidence / "owned-simulator.json", {"udid": device, "runtime": rows[0], "deviceType": c.DEVICE})
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator", 60)
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-owned-boot", 180)
        commands.run(["xcrun", "simctl", "install", device, str(app)], "install-original-before-controls", 120)
        native = built["app"]; c.product_integrity(native)
        data, proof = descriptor(native, app)
        selected = native["products"] / "E-Gesture-Arbitration.xctestrun"
        c.write_bytes(selected, data)
        native["copies"][selected.name] = {"kind": "file", "bytes": len(data), "mode": 0o600, "sha256": c.sha(data)}
        stage = evidence / "gesture-controls"; stage.mkdir(mode=0o700)
        c.write(stage / "descriptor-binding.json", proof); c.write_bytes(stage / "bound.xctestrun", data)
        base = ["xcodebuild", "test-without-building", "-xctestrun", str(selected),
                "-destination", "platform=iOS Simulator,id=" + device, "-parallel-testing-enabled", "NO",
                "-only-testing:AnytypeTests/" + SUITE]
        listing = stage / "enumeration.json"
        commands.run(base + ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                            "-test-enumeration-output-path", str(listing)], "gesture-enumerate", 180)
        result["enumeration"] = qualify_enumeration(c.decode(c.raw(listing)))
        c.product_integrity(native); c.require(c.digest(selected) == c.sha(data), "Enumerated descriptor changed")
        argv = base + ["-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "300",
                       "-maximum-test-execution-time-allowance", "300", "-resultBundlePath", str(stage / "original.xcresult"),
                       "-collect-test-diagnostics", "never"]
        c.write(stage / "invocation.json", {"argv": argv, "binding": binding, "enumerationSHA256": c.digest(listing)})
        test_log, outcome = commands.run(argv, "gesture-test", 600, checked=False)
        result["originalCommand"] = outcome
        c.require(outcome["status"] == "PASS_COMMAND" and b"** TEST EXECUTE SUCCEEDED **" in c.raw(test_log),
                  "Original successful XCTest command required")
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
    finally:
        test_invoked = (root / "commands/gesture-test/started.json").is_file()
        stage = evidence / "gesture-controls"; bundle = stage / "original.xcresult"
        extraction_errors = []
        if bundle.is_dir():
            for kind in ("summary", "tests"):
                try:
                    log, _ = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                        "--path", str(bundle), "--format", "json"], "gesture-" + kind, 120, capacity=False)
                    c.decode(c.raw(log)); c.write_bytes(stage / (kind + ".json"), c.raw(log))
                except BaseException as exc:
                    extraction_errors.append({"phase": kind, **c.error(exc)})
            try:
                commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(bundle),
                    "--output-path", str(stage / "private-attachments")], "gesture-attachments", 180, capacity=False)
            except BaseException as exc:
                extraction_errors.append({"phase": "attachments", **c.error(exc)})
        if test_invoked and "firstFailure" not in result and not extraction_errors:
            try:
                result["actualFiveControls"] = qualify_results(c.decode(c.raw(stage / "summary.json")),
                    c.decode(c.raw(stage / "tests.json")), device, host, core)
                result["status"] = "PASS_FIVE_ORIGINAL_UIKIT_GESTURE_CONTROLS"
            except BaseException as exc:
                result["firstFailure"] = c.error(exc)
        result["extractionErrors"] = extraction_errors
        result["stages"]["gesture-controls"] = {"status": "PASS" if result["status"].startswith("PASS_") else "FAIL",
            "testInvoked": test_invoked or (root / "commands/gesture-test/started.json").exists()}
        cleanup = {"status": "PASS", "groups": [], "ownedSimulatorDeleted": False,
                   "ownedSimulatorRetainedForRecovery": device, "errors": []}
        if device:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, device,
                    private / "final-sandbox-originals", application_invoked=(test_invoked
                        or (args.root / "commands/gesture-enumerate/started.json").is_file()))
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "retention", **c.error(exc)})
            try:
                commands.run(["xcrun", "simctl", "shutdown", device], "cleanup-shutdown", 60, capacity=False)
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "shutdown", **c.error(exc)})
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
                continue
            try:
                present = c.Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                c.require(present is False, "Owned group still present")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "owned-group", "pgid": group, **c.error(exc)})
        try:
            result["finalProducts"] = {kind: c.product_integrity(value) for kind, value in built.items()}
            c.require(c.digest(Path(c.__file__)) == COMMON_SHA and c.digest(Path(__file__)) == args.controller_sha256,
                      "Exact controls changed")
            for name, digest in HELPERS.items():
                c.require(c.digest(root / "helpers" / name) == digest, "Frozen original validator changed")
        except BaseException as exc:
            cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "final-inputs", **c.error(exc)})
        if cleanup["status"] != "PASS":
            result["status"] = "FAIL"
        result["cleanup"] = cleanup
        c.write(evidence / "cleanup.json", cleanup); c.write(evidence / "execution.json", result)
    retention = {"status": "FAIL"}
    try:
        import retain_owned_heart_account as account
        c.require(Path(account.__file__).resolve() == own / "retain_owned_heart_account.py"
                  and c.digest(Path(account.__file__)) == RETENTION_SHA, "Foreign retention helper")
        retention = account.retain(root, c.digest(evidence / "execution.json"))
    except BaseException as exc:
        retention["failure"] = c.error(exc)
    c.write(evidence / "account-retention-result.json", retention)
    passed = (result["status"] == "PASS_FIVE_ORIGINAL_UIKIT_GESTURE_CONTROLS"
              and retention.get("status") == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE")
    c.write(root / "final-outcome.json", {"status": "PASS" if passed else "FAIL", "componentStatus": result["status"],
        "accountRetentionStatus": retention.get("status"), "executionSHA256": c.digest(evidence / "execution.json"),
        "wholeEAcceptance": False, "sourceCommit": COMMIT, "expectedMethodCount": 5})
    print(json.dumps({"status": "PASS" if passed else "FAIL", "componentStatus": result["status"],
                      "firstFailure": result.get("firstFailure"), "ownedSimulator": device}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
