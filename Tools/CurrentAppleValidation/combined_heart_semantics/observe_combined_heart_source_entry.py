"""One original UI method with observational exact-image breakpoints.

This diagnostic cannot produce acceptance. It reuses the original account and
deadline, and preserves the actual XCTest outcome independently of trace success.
"""
import argparse
import concurrent.futures
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import combined_heart_semantics as c
import resume_combined_heart_sources as previous

CONTINUATION = "0239d48478c5627f5c07c97619d81da05d3ed359a9132f14a694b217b6fa2642"
RESUME = "5a438b4be1144b3214ea0cd5b495b263a089a99962e1c370bad8c4862e51e40e"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    admission_raw = c.raw(args.admission)
    c.require(c.sha(admission_raw) == args.admission_sha256, "Frozen observation admission differs")
    admission = c.decode(admission_raw); observation = admission["sourceEntryObservation"]
    c.require(observation["profile"] == "original6db-source-entry-diagnostic-0239-v1"
              and observation["controllerSHA256"] == c.digest(Path(__file__))
              and admission["controllerSHA256"] == c.digest(Path(c.__file__))
              and c.digest(Path(previous.__file__)) == RESUME, "Exact reviewed diagnostic helpers required")
    continuation_raw = c.pinned(observation["continuationReceipt"])
    c.require(c.sha(continuation_raw) == CONTINUATION, "Only the actual observed source-sheet failure may be diagnosed")
    continuation = c.decode(continuation_raw)
    row = admission["semanticContinuation"]
    prior_raw = c.pinned(row["priorReceipt"]); prior = c.decode(prior_raw)
    c.require(c.sha(prior_raw) == previous.PRIOR_EXECUTION, "Exact original account receipt required")
    device = previous.qualify_prior_header(prior, admission)
    c.require(continuation["binding"] == prior["binding"] and continuation["ownedSimulator"] == device
              and continuation["sourceCommit"] == admission["sourceCommit"]
              and continuation["nativeManifestSHA256"] == c.MANIFEST
              and continuation["status"] == "FAIL" and set(continuation["stages"]) == {"linked-ui"}
              and continuation["stages"]["linked-ui"]["status"] == "FAIL"
              and continuation["stages"]["linked-ui"]["testInvoked"] is True
              and continuation["cleanup"]["status"] == "PASS"
              and continuation["cleanup"]["ownedSimulatorDeleted"] is False,
              "One actual failed original source UI method and retained device required")
    last_root = Path(observation["continuationReceipt"]["path"]).parents[1]
    log = c.raw(last_root / "commands/linked-ui-test/original.log")
    c.require(c.sha(log) == continuation["stages"]["linked-ui"]["command"]["logSHA256"]
              and b'Sources for anchored text' in log and b'torah-sources-search-field' in log
              and b'** TEST EXECUTE FAILED **' in log, "Actual source entry and absent search failure required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh owned diagnostic root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", admission_raw)
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; owned_boot = False; future = None; pool = None
    stop = private / "stop-observer"
    result = {"status": "DIAGNOSTIC_INCOMPLETE_NOT_ACCEPTANCE", "sourceCommit": admission["sourceCommit"],
              "nativeManifestSHA256": c.MANIFEST, "uiTestChangeCommit": previous.menu.CHANGE,
              "binding": prior["binding"], "ownedSimulator": device, "startedAt": time.time(),
              "controllerSHA256": c.digest(Path(__file__)), "setupMethodsReexecuted": 0,
              "appBuilds": 0, "nativeBuilds": 0, "uiBuilds": 0, "fullEAcceptance": False,
              "extraEngineCallsByObserver": 0, "originalFixtureDeadlineChanged": False}
    binding = prior["binding"]
    try:
        result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts"); c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract"); c.boundary = importlib.import_module("page154_boundary")
        c.policy = importlib.import_module("page154_contract")
        specialized = importlib.import_module("combined_heart_observations")
        prior_root = Path(row["priorRoot"])
        result["originalSetupAdmission"] = previous.qualify_original_setup(prior, prior_root, device, binding)
        listing, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "admit-owned-device", 30)
        matches = [v for v in c.decode(c.raw(listing))["devices"].get(c.RUNTIME, []) if v.get("udid") == device]
        c.require(len(matches) == 1 and matches[0].get("state") == "Shutdown" and matches[0].get("isAvailable") is True
                  and matches[0].get("deviceTypeIdentifier") == c.DEVICE
                  and matches[0].get("name") == "E-Combined-Heart-" + binding["nonce"], "Exact owned shutdown device required")
        c.mounted.fixture(c.decode(c.raw(prior_root / "private/final-sandbox-originals" / c.FIXTURE)), binding)
        # Set cleanup ownership before boot: post-command capacity failures must
        # not strand an otherwise successfully booted, exactly admitted device.
        owned_boot = True
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-owned-boot", 180)
        baseline = private / "baseline"; baseline.mkdir(mode=0o700)
        actual = {}
        for index, filename in enumerate((c.FIXTURE, c.CAPTURE, c.REOPEN, *c.boundary.FILES.values())):
            original = c.raw(prior_root / "private/final-sandbox-originals" / filename)
            retained = continuation["finalPrivateSandbox"]["files"][filename]
            c.require(retained == {"status": "COPIED_ORIGINAL", "bytes": len(original), "sha256": c.sha(original)},
                      "Previous actual observation changed the original native witness")
            actual[filename] = c.app_file(commands, device, baseline, filename, "baseline-" + str(index))
            c.require(actual[filename] == original, "Live original native witness changed")
        fixture_raw, capture_raw, reopen_raw = (actual[n] for n in (c.FIXTURE, c.CAPTURE, c.REOPEN))
        fixture, capture, reopen = map(c.decode, (fixture_raw, capture_raw, reopen_raw))
        c.mounted.fixture(fixture, binding)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        result["nativeBoundaryComparison"] = c.boundary.verify({role: actual[name] for role, name in c.boundary.FILES.items()},
                                                               fixture, capture, c.native, c.mounted)
        c.require(result["mountedProof"] == prior["mountedProof"]
                  and result["nativeBoundaryComparison"] == prior["nativeBoundaryComparison"], "Original acceptance proof differs")
        observer, watcher = Path(observation["observerSource"]["path"]), Path(observation["watcherSource"]["path"])
        c.pinned(observation["observerSource"]); c.pinned(observation["watcherSource"])
        watcher_module = importlib.import_module("source_entry_trace_watch")
        c.require(Path(watcher_module.__file__) == watcher, "Frozen owned-process helper differs")
        old = watcher_module.owned_app_pids(device)
        trace = private / "original-entry-observation.json"
        config = {"device": device, "binding": binding, "excludePIDs": old, "output": str(trace),
                  "stopFile": str(stop), "observer": str(observer), "observerSHA256": c.digest(observer)}
        config_path = private / "observer-config.json"; c.write(config_path, config)
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(commands.run, [sys.executable, str(watcher), str(config_path)], "entry-observer", 200,
                             checked=False, capacity=False)
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        base.update(PINKHA_SEMANTIC_MOUNTED_TESTING="1", PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON=fixture_raw.decode(),
                    PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256=c.sha(fixture_raw), PINKHA_SEMANTIC_SOURCE_UI_PHASE="linked")
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            base["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            base["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = c.sha(payload)
        result["actualUI"] = c.stage(commands, evidence, "linked-ui", built["ui"], app, binding, device, base)
        result["status"] = "ORIGINAL_UI_DIAGNOSTIC_FINISHED_NOT_ACCEPTANCE"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        errors = []
        stop.write_text("Stop observational debugger and detach; retain original app state.\n")
        if future:
            try:
                _, result["observerCommand"] = future.result(timeout=35)
            except BaseException as exc:
                errors.append({"phase": "observer-completion", **c.error(exc)})
        if pool:
            pool.shutdown(wait=True)
        if owned_boot:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, device, private / "final-sandbox-originals",
                    application_invoked=result.get("actualUI", {}).get("testInvoked") is True)
            except BaseException as exc:
                errors.append({"phase": "private-retention", **c.error(exc)})
            try:
                _, shutdown = commands.run(["xcrun", "simctl", "shutdown", device], "shutdown-owned-device", 60,
                                            checked=False, capacity=False)
                c.require(shutdown["exitCode"] == 0, "Owned shutdown failed")
            except BaseException as exc:
                errors.append({"phase": "owned-shutdown", **c.error(exc)})
        try:
            result["finalProducts"] = {name: c.product_integrity(value) for name, value in built.items()}
        except BaseException as exc:
            errors.append({"phase": "product-retention", **c.error(exc)})
        trace = private / "original-entry-observation.json"
        if trace.exists():
            result["observerOriginal"] = {"bytes": trace.stat().st_size, "sha256": c.digest(trace)}
        result["cleanup"] = {"errors": errors, "status": "PASS" if not errors else "FAIL",
                             "ownedSimulatorDeleted": False, "ownedSimulatorRetainedForRecovery": device,
                             "groups": [{"pgid": g, "absentAtOriginalExit": g in commands.absent_groups,
                                         "historicalGroupReprobed": False} for g in commands.groups]}
        result["finishedAt"] = time.time()
        c.write(evidence / "execution.json", result)
    print(json.dumps({"status": result["status"], "actualUIStatus": result.get("actualUI", {}).get("status"),
                      "firstFailure": result.get("firstFailure"), "receipt": str(evidence / "execution.json")}))
    return 0 if result["status"] == "ORIGINAL_UI_DIAGNOSTIC_FINISHED_NOT_ACCEPTANCE" and not result["cleanup"]["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
