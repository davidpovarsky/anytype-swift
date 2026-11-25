#!/usr/bin/env python3
"""Continue four original source methods from one retained zero-write UI failure.

No preparation, account creation, semantic capture, app build or native build is
performed. The separately hashed admission names the exact original failed run;
its two successful setup methods and all original private witnesses are verified
before reuse. A changed, foreign, expired or missing account fails admission.
"""
import argparse
import importlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import combined_heart_semantics as c
import semantic_source_menu_override as menu

PRIOR_EXECUTION = "21ecaa2c4f2d83e70212773e8c28c07acb691fdfba730cb5072e85bc00c12bbc"
PRIOR_CORE = "2421f03c34831265659c79ed36160072c135a1ff8ba48a5e5e27000ac8a1011e"
PRIOR_UI = "f022a51c37bcada450a3208e87a5bea706b64b76"
PROFILE = "heart6db-retained-source-menu-zero-write-21ec-v1"
PASS = "PASS_FOUR_ACTUAL_HEART_SOURCE_METHODS_WITH_QUALIFIED_ORIGINAL_SETUP"


def qualify_prior_header(prior, admission):
    c.require(prior.get("status") == "FAIL" and prior.get("sourceCommit") == admission["sourceCommit"] == menu.BASE
              and prior.get("controllerSHA256") == PRIOR_CORE and prior.get("nativeManifestSHA256") == c.MANIFEST
              and prior.get("heartOverlaySHA256") == c.OVERLAY
              and prior.get("firstFailure") == {"type": "ValueError", "message": "linked-ui actual method failed"},
              "Exact original source-menu failure required")
    c.require(set(prior.get("stages", {})) == {"preparation", "mounted", "linked-ui"}
              and all(prior["stages"][name].get("status") == "PASS" for name in ("preparation", "mounted"))
              and prior["stages"]["linked-ui"].get("status") == "FAIL"
              and all(prior["stages"][name].get("testInvoked") is True for name in prior["stages"]),
              "Two actual setup passes and one actual source-menu failure required")
    cleanup = prior.get("cleanup", {})
    device = prior.get("ownedSimulator")
    c.require(isinstance(device, str) and re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", device)
              and cleanup.get("status") == "PASS" and cleanup.get("ownedSimulatorDeleted") is False
              and cleanup.get("ownedSimulatorRetainedForRecovery") == device and cleanup.get("errors") == []
              and cleanup.get("groups")
              and all(row.get("absentAtOriginalExit") is True and row.get("historicalGroupReprobed") is False
                      for row in cleanup["groups"]), "Original owned simulator and completed cleanup required")
    override = prior.get("sourceAdmission", {}).get("uiTestOverride", {})
    c.require(override.get("status") == "PASS_EXACT_UI_ONLY_MENU_OVERRIDE_SOURCE_AND_PRODUCTS"
              and override.get("appSourceCommit") == menu.BASE and override.get("uiTestChangeCommit") == PRIOR_UI,
              "Original helper-only UI provenance required")
    return device


def qualify_original_setup(prior, prior_root, device, binding):
    rows = {}
    for name in ("preparation", "mounted"):
        folder = prior_root / "evidence" / name
        log = prior_root / "commands" / (name + "-test") / "original.log"
        actual = c.qualify_execution(c.decode(c.raw(folder / "summary.json")), c.decode(c.raw(folder / "tests.json")),
                                     c.STAGES[name], device, log)
        actual = c.decode(json.dumps(actual).encode())
        recorded = prior["stages"][name]
        c.require(recorded["actual"] == actual and recorded["command"]["logSHA256"] == c.digest(log)
                  and recorded["command"]["logBytes"] == log.stat().st_size
                  and recorded["command"]["exitCode"] == 0,
                  "Original setup xcresult exports or named stdout differ")
        rows[name] = actual
    folder = prior_root / "evidence/linked-ui"
    summary = c.decode(c.raw(folder / "summary.json"))
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    c.require(all(type(v) is int for v in counts.values()) and counts ==
              {"totalTestCount": 1, "passedTests": 0, "failedTests": 1, "skippedTests": 0},
              "One actual original source UI failure required")
    c.qualify_enumeration(c.decode(c.raw(folder / "enumeration.json")), c.STAGES["linked-ui"])
    log = prior_root / "commands/linked-ui-test/original.log"
    text = c.raw(log).decode("utf-8", "replace")
    c.require(c.digest(log) == prior["stages"]["linked-ui"]["command"]["logSHA256"]
              and "source-action-not-found-in-menu" in text and "** TEST EXECUTE FAILED **" in text,
              "Original pre-source-action failure stdout differs")
    trace_raw, origin = c.policy.attachment(folder / "private-attachments", "semantic-source-menu-navigation",
                                           c.STAGES["linked-ui"], device, maximum=65536)
    trace = c.decode(trace_raw)
    c.require(trace.get("protocol") == "pinkha-semantic-source-menu-v1" and trace.get("status") == "FAIL"
              and all(trace.get(key) == value for key, value in binding.items())
              and type(trace.get("sourceActionTaps")) is int and trace["sourceActionTaps"] == 0
              and trace.get("nextPageTaps") == 3 and trace.get("budgetSeconds") == 20
              and trace.get("firstError") == 'admission("source-action-not-found-in-menu")',
              "Original failed helper must prove zero source action before continuation")
    return {"status": "PASS_ORIGINAL_SETUP_AND_ZERO_SOURCE_ACTION_FAILURE_REQUALIFIED",
            "priorReceiptSHA256": PRIOR_EXECUTION, "setupMethods": rows,
            "failureTraceSHA256": c.sha(trace_raw), "sourceActionTaps": 0,
            "setupMethodsReexecuted": 0, "originalFixtureDeadlineChanged": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    raw_admission = c.raw(args.admission)
    c.require(c.sha(raw_admission) == args.admission_sha256, "Reviewed continuation admission differs")
    admission = c.decode(raw_admission)
    row = admission["semanticContinuation"]
    c.require(admission["schema"] == "pinkha-combined-heart-semantics-admission-v1"
              and admission["executionEnvironment"] == "SentinelX-owned-Mac"
              and admission["nativeManifestSHA256"] == c.MANIFEST and admission["heartOverlaySHA256"] == c.OVERLAY
              and admission["controllerSHA256"] == c.digest(Path(c.__file__))
              and row["profile"] == PROFILE and row["controllerSHA256"] == c.digest(Path(__file__))
              and c.digest(Path(c.__file__).with_name("combined_heart_observations.py")) == c.OBSERVATION_HELPER,
              "Exact reviewed combined continuation source required")
    prior_raw = c.pinned(row["priorReceipt"])
    c.require(c.sha(prior_raw) == PRIOR_EXECUTION, "Only the exact retained original failure may resume")
    prior = c.decode(prior_raw); device = qualify_prior_header(prior, admission)
    prior_root = Path(row["priorRoot"])
    c.require(prior_root.resolve() == prior_root and Path(row["priorReceipt"]["path"]) == prior_root / "evidence/execution.json",
              "Exact original retained root required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh owned continuation root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", raw_admission)
    c.write_bytes(evidence / "prior-execution.json", prior_raw)
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; owned_boot = False
    result = {"status": "FAIL", "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": admission["sourceCommit"],
              "uiTestChangeCommit": menu.CHANGE, "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
              "binding": prior["binding"], "bindingIdentityKind": "original owned local microsecond receipt identity, not a GitHub Actions run",
              "priorReceiptSHA256": PRIOR_EXECUTION, "controllerSHA256": c.digest(Path(__file__)),
              "startedAt": time.time(), "ownedSimulator": device, "stages": {},
              "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "factoryMethodsExecuted": 0,
              "setupMethodsReexecuted": 0, "physicalDevice": "NOT_RUN", "fullEAcceptance": False}
    binding = prior["binding"]
    try:
        proof, built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        result["sourceAdmission"] = proof
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts")
        c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract")
        c.boundary = importlib.import_module("page154_boundary")
        c.policy = importlib.import_module("page154_contract")
        specialized = importlib.import_module("combined_heart_observations")
        c.native.binding(binding)
        result["originalSetupAdmission"] = qualify_original_setup(prior, prior_root, device, binding)
        log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "original-owned-device", 30)
        devices = c.decode(c.raw(log))["devices"].get(c.RUNTIME, [])
        matched = [value for value in devices if value.get("udid") == device]
        c.require(len(matched) == 1 and matched[0].get("state") == "Shutdown" and matched[0].get("isAvailable") is True
                  and matched[0].get("deviceTypeIdentifier") == c.DEVICE
                  and matched[0].get("name") == "E-Combined-Heart-" + binding["nonce"], "Original owned shutdown simulator differs")
        c.mounted.fixture(c.decode(c.raw(prior_root / "private/final-sandbox-originals" / c.FIXTURE)), binding)
        # CoreSimulator refuses get_app_container for a shutdown device (405).
        # Boot only the already admitted owned device before reading its live
        # container; no application or engine call is issued by this step.
        commands.run(["xcrun", "simctl", "boot", device], "boot-original-owned-simulator", 60)
        owned_boot = True
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-original-owned-boot", 180)
        retained = prior["finalPrivateSandbox"]
        c.require(retained["status"] == "PRESERVED_ORIGINAL_PRIVATE_FILES" and retained["engineCalls"] == 0
                  and retained["rawPayloadsUploaded"] is False, "Original private retention required")
        base_files = [c.FIXTURE, c.CAPTURE, c.REOPEN, *c.boundary.FILES.values()]
        baseline = private / "baseline"; baseline.mkdir(mode=0o700)
        actual = {}
        for index, filename in enumerate(base_files):
            expected = retained["files"][filename]
            original = c.raw(prior_root / "private/final-sandbox-originals" / filename)
            c.require(expected["status"] == "COPIED_ORIGINAL" and expected["bytes"] == len(original)
                      and expected["sha256"] == c.sha(original), "Original retained witness differs")
            actual[filename] = c.app_file(commands, device, baseline, filename, "original-witness-" + str(index))
            c.require(actual[filename] == original, "Live retained account witness differs from original failed run")
        for phase in ("linked", "unlinked"):
            c.require(retained["files"]["pinkha-semantic-source-" + phase + "-native-readback.json"] == {"status": "NOT_PRESENT"},
                      "Source continuation was already performed")
        container = Path(c.raw(commands.root / ("original-witness-" + str(len(base_files) - 1) + "-container/original.log")).decode().strip())
        for phase in ("linked", "unlinked"):
            path = container / "Library/Application Support" / ("pinkha-semantic-source-" + phase + "-native-readback.json")
            c.require(not path.exists() and not path.is_symlink(), "Retained account acquired a later continuation witness")
        fixture_raw, capture_raw, reopen_raw = (actual[n] for n in (c.FIXTURE, c.CAPTURE, c.REOPEN))
        fixture, capture, reopen = map(c.decode, (fixture_raw, capture_raw, reopen_raw))
        c.mounted.fixture(fixture, binding)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        c.require(result["mountedProof"] == prior["mountedProof"], "Original mounted proof changed")
        result["nativeBoundaryComparison"] = c.boundary.verify({role: actual[filename] for role, filename in c.boundary.FILES.items()},
                                                               fixture, capture, c.native, c.mounted)
        c.require(result["nativeBoundaryComparison"] == prior["nativeBoundaryComparison"]
                  and result["nativeBoundaryComparison"]["projectionFieldCount"] == 9, "Original full native boundary differs")
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": c.sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = c.sha(payload)
        def run(name, additions):
            kind = "app" if c.STAGES[name].startswith("AnytypeTests/") else "ui"
            value = c.stage(commands, evidence, name, built[kind], app, binding, device, dict(base, **additions))
            result["stages"][name] = value
            c.require(value["status"] == "PASS", name + " actual method failed")
        previous, previous_raw = None, None
        for phase in ("linked", "unlinked"):
            if previous_raw is not None:
                source_env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"] = c.sha(previous_raw)
            run(phase + "-ui", dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE=phase))
            ui_raw, _ = c.policy.attachment(evidence / (phase + "-ui/private-attachments"), "heart-semantic-source-ui-" + phase,
                                           c.STAGES[phase + "-ui"], device, maximum=65536)
            result[phase + "UIProof"] = c.continuation_ui(c.decode(ui_raw), phase, fixture, capture, capture_raw, reopen_raw)
            native_env = dict(source_env, PINKHA_SEMANTIC_SOURCE_READBACK_PHASE=phase,
                              PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_JSON=ui_raw.decode(), PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_SHA256=c.sha(ui_raw))
            run(phase + "-native", native_env)
            native_raw = c.app_file(commands, device, private, "pinkha-semantic-source-" + phase + "-native-readback.json", "preserve-" + phase + "-readback")
            attached, _ = c.policy.attachment(evidence / (phase + "-native/private-attachments"), "heart-semantic-source-native-" + phase,
                                             c.STAGES[phase + "-native"], device, maximum=65536)
            value = c.decode(native_raw)
            proof = c.continuation_native(value, c.decode(attached), native_raw, phase, fixture, capture,
                                          fixture_raw, capture_raw, reopen_raw, ui_raw, previous)
            result[phase + "NativeProof"] = proof
            c.write(evidence / (phase + "-independent-native-qualified.json"), proof)
            previous, previous_raw = value, native_raw
        result["status"] = PASS
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        cleanup = {"status": "PASS", "groups": [], "device": device, "errors": []}
        if owned_boot:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, device, private / "final-sandbox-originals",
                    application_invoked=any(v.get("testInvoked") is True for v in result["stages"].values()))
            except BaseException as exc:
                cleanup["errors"].append({"phase": "private-evidence-retention", **c.error(exc)})
            try:
                _, status = commands.run(["xcrun", "simctl", "shutdown", device], "cleanup-shutdown", 60, checked=False, capacity=False)
                c.require(status["exitCode"] == 0, "Owned simulator shutdown failed")
            except BaseException as exc:
                cleanup["errors"].append(c.error(exc))
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
            else:
                present = c.Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present: cleanup["errors"].append({"ownedGroupStillPresent": group})
        try:
            result["finalProducts"] = {kind: c.product_integrity(value) for kind, value in built.items()}
            for name, expected in c.HELPERS.items():
                c.require(c.digest(args.root / "helpers" / name) == expected, "Frozen helper changed")
            result["finalHelperIntegrity"] = "PASS"
        except BaseException as exc:
            cleanup["errors"].append(c.error(exc))
        # The retained account remains owned by E. Keep it even after success
        # until the final delivery checkpoint decides its bounded retirement.
        cleanup["ownedSimulatorDeleted"] = False
        cleanup["ownedSimulatorRetainedForRecovery"] = device
        if result["status"] == PASS:
            retained = result.get("finalPrivateSandbox", {})
            complete = (retained.get("status") == "PRESERVED_ORIGINAL_PRIVATE_FILES"
                        and retained.get("files")
                        and all(value.get("status") == "COPIED_ORIGINAL" for value in retained["files"].values()))
            if not complete:
                cleanup["errors"].append({"phase": "private-evidence-retention", "message": "Complete final original witnesses required"})
        if cleanup["errors"]:
            cleanup["status"] = "FAIL"; result["status"] = "FAIL"
        result["cleanup"] = cleanup
        c.write(evidence / "cleanup.json", cleanup)
        c.write(evidence / "execution.json", result)
    print(json.dumps({"status": result["status"], "stages": {k: v["status"] for k, v in result["stages"].items()},
                      "receipt": str(evidence / "execution.json"), "firstFailure": result.get("firstFailure")}))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
