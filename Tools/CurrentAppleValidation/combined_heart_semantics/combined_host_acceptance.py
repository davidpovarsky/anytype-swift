#!/usr/bin/env python3
"""Original F/T5 methods on source-bound combined Debug Products, without a build.

Each selected fixture owns a new simulator. Exact original declarations,
enumeration, XCTest results and native/UI receipts remain the authorities.
This consumer never labels Debug functional results Release acceptance.
"""
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
import shutil
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
import combined_heart_semantics as shared

require, raw, decode = shared.require, shared.raw, shared.decode
write, write_bytes, sha, digest = shared.write, shared.write_bytes, shared.sha, shared.digest
PROFILE = "dual-engine-runtime-v1"
NATIVE = "AnytypeTests"
UI = "PinkhaStage1AcceptanceUITests"
RETURN = ["BlockActionServiceReturnFocusTests/" + name for name in (
    "renderedSubscriberKeepsSplitRequest", "laterRenderedRowConsumesSplitRequest",
    "laterRequestStillSupersedesSplitFocus")]
SWITCH = "PinkhaStage1AcceptanceUITests/testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen"
PLANS = {
    "first-editor": ("editor",),
    "coherent-functional": ("editor", "return-controls", "quote-drop", "properties-set",
                            "t5-host-actions", "t5-pending-nine", "t5-remaining-freshness", "t5-native-ui"),
    "t5-only": ("t5-host-actions", "t5-pending-nine", "t5-remaining-freshness", "t5-native-ui"),
    "remaining-editor-journeys": ("quote-drop", "properties-set"),
    "return-controls-only": ("return-controls",),
}
ORIGINAL_SERIES = ("return-controls", "rtl-preparation", "editor", "quote-drop", "properties-set",
                   "t5-host-actions", "t5-pending-nine", "t5-remaining-freshness", "t5-native-ui")
EXPECTED_TEST_PROFILES = {
    "AnyTypeTests/Pinkha/TorahT5UIAcceptancePreparationTests.swift": "22024c677aeb0f5fbe0155cec4a5cd7ab42884d7abdfc6fca00ed46be3124363",
    "AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift": "e3b614136296081479f407c150282e70c7ede0e330bcbcd803654aadc8004650",
    "AnyTypeTests/Pinkha/TorahT5RuntimePairTests.swift": "04a559bdba3cfd5427870780ce18b91540be68fa444fda94554f6c88f2534f31",
}
HELPER_DIRS = ("Tools/PinkhaSimulatorGate", "Tools/PinkhaNativeDerived", "Tools/Hanlin",
               "Tools/AnyEnginePort", "Tools/CurrentAppleValidation")
SUPPORT = Path("Library/Application Support")


def freeze_helpers(source, commit, destination, pins_path):
    pins = decode(raw(pins_path))
    require(pins.get("schema") == "pinkha-combined-host-helper-closure-v1"
            and isinstance(pins.get("files"), dict) and len(pins["files"]) >= 15,
            "Original reviewed helper closure required")
    for name, row in pins["files"].items():
        path = source / name
        require(path.resolve().is_relative_to(source), "Helper source escaped admitted source")
        value = raw(path)
        require(len(value) == row["bytes"] and sha(value) == row["sha256"], "Reviewed original helper changed: " + name)
        tracked = subprocess.check_output(["git", "-C", str(source), "show", commit + ":" + name], timeout=30)
        require(value == tracked, "Helper differs from exact compiled source commit")
        target = destination / name
        if target.exists():
            require(raw(target) == value, "Previously frozen helper disagrees")
        else:
            write_bytes(target, value)
    for name, expected in EXPECTED_TEST_PROFILES.items():
        require(digest(source / name) == expected, "Exact additive compiled T5 profile admission changed: " + name)
    return {"helperFiles": len(pins["files"]), "pinsSHA256": digest(pins_path),
            "compiledT5ProfileFiles": EXPECTED_TEST_PROFILES}


def load_helpers(root):
    for name in HELPER_DIRS:
        sys.path.insert(0, str(root / name))
    shared.common = importlib.import_module("contracts")
    modules = {name: importlib.import_module(name) for name in (
        "run_ui27", "run_wave15_acceptance", "t5_host_actions", "t5_native_ui_evidence",
        "t5_native_ui_mutations", "t5_native_ui_r08", "run_t5_native_ui",
        "t5_native_account_retry_pending_evidence", "run_t5_native_pagination",
        "t5_remaining_freshness", "type_preservation")}
    for name, module in modules.items():
        require(Path(module.__file__).resolve().is_relative_to(root), "Foreign helper module: " + name)
    return modules


def scoped_descriptor(built, app, selectors, environment):
    require(isinstance(selectors, list) and selectors and len(selectors) == len(set(selectors))
            and len({s.split("/")[0] for s in selectors}) == 1, "Exact distinct one-target method list required")
    data, proof = shared.bind_descriptor(built, app, selectors[0], environment)
    value = plistlib.loads(data)
    before = copy.deepcopy(value)
    target = (value["TestConfigurations"][0]["TestTargets"][0]
              if selectors[0].startswith(NATIVE + "/") else value[UI])
    original_only = target["OnlyTestIdentifiers"]
    target["OnlyTestIdentifiers"] = [s.split("/", 1)[1] for s in selectors]
    inverse = copy.deepcopy(value)
    inverse_target = (inverse["TestConfigurations"][0]["TestTargets"][0]
                      if selectors[0].startswith(NATIVE + "/") else inverse[UI])
    inverse_target["OnlyTestIdentifiers"] = original_only
    require(inverse == before, "Additional selector scope changed nonselection configuration")
    proof.update(selectors=selectors, exactMultiMethodInverse=True)
    return plistlib.dumps(value, sort_keys=False), proof


def exact_enumeration(value, selectors):
    require(isinstance(value, dict) and value.get("errors") == [], "Original compiled enumeration failed")
    configurations = value.get("values")
    require(isinstance(configurations, list) and len(configurations) == 1, "One compiled test configuration required")
    config = configurations[0]
    names = {}
    for key in ("enabledTests", "disabledTests"):
        rows = config.get(key)
        require(isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("identifier"), str) for r in rows),
                "Compiled enumeration schema differs")
        names[key] = [r["identifier"] for r in rows]
        require(len(names[key]) == len(set(names[key])), "Duplicate compiled test identifier")
    target = selectors[0].split("/", 1)[0]
    normalize = lambda s: s.removeprefix(target + "/")
    require(sorted(map(normalize, names["enabledTests"])) == sorted(map(normalize, selectors))
            and not set(names["enabledTests"]).intersection(names["disabledTests"]),
            "Enumeration must contain every exact original selected method and no extra method")
    if target == NATIVE:
        require(config.get("testPlan") == NATIVE, "Original native test plan changed")
    return {"testPlan": config.get("testPlan"), **names}


def result_selection(summary, tree, selectors, udid, helpers):
    methods = [s.split("/", 1)[1].removesuffix("()") for s in selectors]
    actual = helpers["run_ui27"].method_results(tree)
    counts = helpers["t5_native_ui_evidence"].validate_selection(summary, actual, methods, udid)
    devices = [r["device"] for r in summary.get("devicesAndConfigurations", [])]
    require(len(devices) == 1 and devices[0].get("osVersion") == shared.OS_VERSION
            and devices[0].get("osBuildNumber") == shared.OS_BUILD
            and devices[0].get("platform") == "iOS Simulator", "Exact original installed runtime required")
    return {"status": "PASS", "selected": methods, "command_exit_code": 0,
            "passed": len(methods), "failed": 0, "skipped": 0, "actual_methods": actual,
            "actual_devices": devices, "originalValidatorCounts": counts}


class Consumer:
    def __init__(self, root, admission, commands, built, app, helpers, binding):
        self.root, self.admission, self.commands = root, admission, commands
        self.built, self.app, self.helpers, self.binding = built, app, helpers, binding
        self.source = Path(admission["sourceRoot"])
        self.carriers = helpers["run_ui27"].code_carriers(app)
        self.devices, self.current = [], None
        write(root / "evidence/built-code-carriers.json", self.carriers)

    def command(self, argv, label, timeout=120, **kw):
        return self.commands.run(argv, label, timeout, **kw)

    def container(self, udid, kind, label, *, required=True):
        log, result = self.command(["xcrun", "simctl", "get_app_container", udid, shared.BUNDLE, kind], label,
                                   30, checked=False, capacity=False)
        if result["exitCode"] != 0:
            require(not required, "Expected actual owned application container")
            return None
        path = Path(raw(log, 4096).decode().strip())
        owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
        require(path.is_absolute() and path.resolve() == path and path.is_dir() and path.is_relative_to(owner),
                "Application container escaped its new owned simulator")
        return path

    def installed(self, udid, label):
        path = self.container(udid, "app", label + "-app-container")
        actual = self.helpers["run_ui27"].code_carriers(path)
        require(actual["sha256"] == self.carriers["sha256"], "Installed executable code differs from original producer")
        return {"codeCarriersSHA256": actual["sha256"], "installedApp": str(path)}

    def create(self, lane, directory, *, editor=False):
        name = "F-Combined-" + self.binding["nonce"] + "-" + lane
        log, _ = self.command(["xcrun", "simctl", "create", name, self.admission["deviceType"], shared.RUNTIME], lane + "-create", 60)
        udid = raw(log, 4096).decode().strip()
        require(re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", udid), "New owned simulator UUID missing")
        require(udid.lower() not in {d.lower() for d in self.devices}, "Simulator reused by another fixture")
        self.devices.append(udid); self.current = udid
        write(directory / "owned-simulator.json", {"udid": udid, "name": name, "deviceType": self.admission["deviceType"],
              "deviceFamily": self.admission["deviceFamily"], "runtime": shared.RUNTIME})
        self.command(["xcrun", "simctl", "boot", udid], lane + "-boot", 60)
        self.command(["xcrun", "simctl", "bootstatus", udid, "-b"], lane + "-boot-ready", 180)
        require(self.container(udid, "data", lane + "-assert-empty", required=False) is None, "Fresh simulator already has app data")
        observation = None
        if editor:
            language = "en" if self.admission["appLanguage"] == "he" else "he"
            locale = "en_US" if language == "en" else "he_IL"
            commands = [["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLanguages", "-array", language],
                        ["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLocale", "-string", locale],
                        ["xcrun", "simctl", "shutdown", udid], ["xcrun", "simctl", "boot", udid],
                        ["xcrun", "simctl", "bootstatus", udid, "-b"]]
            for index, argv in enumerate(commands):
                self.command(argv, lane + "-language-" + str(index), 180)
            log, _ = self.command(["xcrun", "simctl", "spawn", udid, "defaults", "export", "NSGlobalDomain", "-"], lane + "-language-readback", 120)
            observation = self.helpers["run_wave15_acceptance"].validate_device_language(raw(log, 1024**2), self.admission["appLanguage"])
            write(directory / "device-language-observation.json", observation)
        self.command(["xcrun", "simctl", "install", udid, str(self.app)], lane + "-install-original", 180)
        self.installed(udid, lane + "-installed-original")
        self.appearance(udid, lane, self.admission["appearance"], "large")
        return udid, observation

    def appearance(self, udid, prefix, appearance, size):
        require(appearance in ("light", "dark") and size == "large", "Explicit original presentation scope required")
        for key, value in (("appearance", appearance), ("content_size", size)):
            self.command(["xcrun", "simctl", "ui", udid, key, value], prefix + "-set-" + key.replace("_", "-"), 30)
            log, _ = self.command(["xcrun", "simctl", "ui", udid, key], prefix + "-read-" + key.replace("_", "-"), 30)
            self.helpers["t5_native_ui_r08"].actual_setting(raw(log).decode(), value, key)

    def read_private(self, udid, relative, directory, label, maximum=4 * 1024**2):
        container = self.container(udid, "data", label + "-container")
        path = container / relative
        require(path.resolve().is_relative_to(container) and not path.is_symlink(), "Private receipt escaped owned app")
        value = raw(path, maximum)
        write_bytes(directory / Path(relative).name, value)
        require(digest(path) == sha(value), "Original receipt changed during preservation")
        return value, container

    def stage(self, directory, name, udid, methods, environment, *, target=NATIVE, allowance=300, host_contract=None):
        selectors = [target + "/" + n for n in methods]
        kind = "app" if target == NATIVE else "ui"
        built = self.built[kind]
        path = directory / name; path.mkdir(mode=0o700)
        prefix = directory.name + "-" + name
        outcome = {"status": "FAIL", "selected": [s.removesuffix("()") for s in methods], "testInvoked": False, "errors": []}
        first = None
        try:
            shared.product_integrity(built)
            data, proof = scoped_descriptor(built, self.app, selectors, environment)
            config = built["products"] / ("F-Combined-" + prefix + ".xctestrun")
            write_bytes(config, data)
            built["copies"][config.name] = {"kind": "file", "bytes": len(data), "mode": 0o600, "sha256": sha(data)}
            write(path / "descriptor-binding.json", proof)
            write_bytes(path / "bound.xctestrun", data)
            base = ["xcodebuild", "test-without-building", "-xctestrun", str(config), "-destination",
                    "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                    *["-only-testing:" + s for s in selectors]]
            listing = path / "enumeration.json"
            self.command(base + ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                                "-test-enumeration-output-path", str(listing)], prefix + "-enumerate", 180)
            outcome["enumeration"] = exact_enumeration(decode(raw(listing)), selectors)
            if host_contract is not None:
                outcome["originalHostEnumeration"] = self.helpers["t5_host_actions"].validate_enumeration(decode(raw(listing)), host_contract)
            require(digest(config) == sha(data), "Enumerated descriptor changed")
            shared.product_integrity(built)
            if target == UI:
                budget = self.helpers["run_ui27"].selection_time_budget(target, methods)
                default, maximum, timeout = budget["default_seconds"], budget["maximum_seconds"], budget["total_method_seconds"] + 300
                outcome["originalTimeBudget"] = budget
            else:
                default = maximum = allowance; timeout = len(methods) * allowance + 300
                if host_contract is not None:
                    timeout = 600  # Preserve the original entire host-suite allowance.
            argv = base + ["-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", str(default),
                           "-maximum-test-execution-time-allowance", str(maximum), "-resultBundlePath", str(path / "original.xcresult"),
                           "-collect-test-diagnostics", "never"]
            write(path / "invocation.json", {"argv": argv, "environmentKeys": sorted(environment),
                  "descriptorSHA256": sha(data), "enumerationSHA256": digest(listing), "binding": self.binding})
            outcome["testInvoked"] = True
            log, actual = self.command(argv, prefix + "-test", timeout, checked=False)
            outcome["command"] = actual
            outcome["command_exit_code"] = actual["exitCode"]
            require(actual["status"] == "PASS_COMMAND", "Original selected test command failed")
            require(b"** TEST EXECUTE SUCCEEDED **" in raw(log), "Original successful terminal stdout missing")
        except BaseException as exc:
            first = exc; outcome["firstFailure"] = shared.error(exc)
        bundle = path / "original.xcresult"
        if bundle.is_dir():
            for key in ("summary", "tests"):
                try:
                    output, _ = self.command(["xcrun", "xcresulttool", "get", "test-results", key, "--path", str(bundle), "--format", "json"],
                                             prefix + "-" + key, 120, capacity=False)
                    value = raw(output); decode(value); write_bytes(path / (key + ".json"), value)
                except BaseException as exc: outcome["errors"].append({"phase": key, **shared.error(exc)})
            try:
                self.command(["xcrun", "xcresulttool", "export", "attachments", "--path", str(bundle), "--output-path", str(path / "private-attachments")],
                             prefix + "-attachments", 180, capacity=False)
            except BaseException as exc: outcome["errors"].append({"phase": "attachments", **shared.error(exc)})
        try:
            shared.product_integrity(built)
            if first is None and not outcome["errors"]:
                summary, tree = decode(raw(path / "summary.json")), decode(raw(path / "tests.json"))
                destinations = summary.get("devicesAndConfigurations", [])
                require(len(destinations) == 1 and destinations[0].get("device", {}).get("deviceId", "").lower() == udid.lower()
                        and destinations[0]["device"].get("architecture") == "arm64"
                        and destinations[0]["device"].get("platform") == "iOS Simulator"
                        and destinations[0]["device"].get("osVersion") == shared.OS_VERSION
                        and destinations[0]["device"].get("osBuildNumber") == shared.OS_BUILD,
                        "Original result uses a different owned runtime/device")
                if host_contract is None:
                    outcome.update(result_selection(summary, tree, selectors, udid, self.helpers))
                else:
                    outcome["actualHostCases"] = self.helpers["t5_host_actions"].validate_results(summary, tree, udid)
                    outcome["status"] = "PASS"
                outcome["installedOriginalCode"] = self.installed(udid, prefix + "-post")
        except BaseException as exc:
            outcome["status"] = "FAIL"; outcome["errors"].append({"phase": "qualification", **shared.error(exc)})
        write(path / "result.json", outcome)
        require(outcome["status"] == "PASS", prefix + " actual original test/receipt failed")
        return outcome, path

    def preserve(self, udid, directory, lane):
        private = directory / "final-private-sandbox"; private.mkdir(mode=0o700)
        container = self.container(udid, "data", lane + "-final-container", required=False)
        if container is None:
            return {"status": "NO_APPLICATION_CONTAINER", "engineCalls": 0}
        support = container / SUPPORT
        files = {}
        if support.is_dir():
            candidates = []
            for path in support.iterdir():
                if not path.name.startswith("pinkha-"):
                    continue
                if path.is_dir() and not path.is_symlink():
                    candidates.extend(p for p in path.rglob("*") if p.is_file())
                elif path.is_file():
                    candidates.append(path)
            require(len(candidates) <= 200, "Bounded original witness inventory required")
            for path in sorted(candidates):
                require(path.resolve().is_relative_to(container) and not path.is_symlink(), "Original witness alias")
                value = raw(path, 16 * 1024**2)
                relative = path.relative_to(support)
                write_bytes(private / relative, value)
                require(digest(path) == sha(value), "Final witness changed during retention")
                files[relative.as_posix()] = {"bytes": len(value), "sha256": sha(value)}
        return {"status": "PRESERVED_ORIGINAL_PRIVATE_WITNESSES", "files": files, "engineCalls": 0,
                "rawPayloadsUploaded": False, "nativeAccountRetainedInOwnedShutdownSimulator": True}

    def wave(self, lane, directory, udid, language):
        original = self.helpers["run_wave15_acceptance"]
        spec = original.LANES[lane]
        env = original.preparation_environment(lane, self.binding["sourceSHA"], self.binding["runID"], self.binding["runAttempt"])
        preservation = self.helpers["type_preservation"]
        bound = None
        if lane == "properties-set":
            bound = preservation.binding(self.binding["sourceSHA"], self.binding["runID"], self.binding["runAttempt"])
            env.update(preservation.binding_environment(bound)); env["PINKHA_PREPARE_TYPE_PRESERVATION"] = "1"
        prep, _ = self.stage(directory, "preparation", udid, [spec["preparation"] + "()"], env)
        fixture_raw, container = self.read_private(udid, SUPPORT / spec["fixture"], directory / "private", lane + "-fixture")
        fixture = decode(fixture_raw)
        observed_language = language["device_language"] if language else None
        ui_env = original.fixture_environment(lane, fixture, self.admission["appLanguage"], observed_language)
        ui_env.update(PINKHA_UI27_APP_LANGUAGE=self.admission["appLanguage"], PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
        frozen = preservation.freeze(container, directory / "private", bound, fixture, udid) if bound else None
        methods = [spec["suite"] + "/" + name for name in spec["methods"]]
        if lane == "editor": methods.append(SWITCH)
        original.source_methods(self.source, methods)
        ui_result, ui_path = self.stage(directory, "ui", udid, methods, ui_env, target=UI)
        outcome = {"preparation": prep, "ui": ui_result, "fixtureSHA256": sha(fixture_raw),
                   "appLanguage": self.admission["appLanguage"], "appearance": self.admission["appearance"],
                   "deviceLanguage": language, "physicalDeviceAccepted": False, "visualReview": "PENDING"}
        if lane == "properties-set":
            preservation.require_ui_passed(ui_result, methods)
            current = self.container(udid, "data", lane + "-postflight-container")
            preservation.verify_frozen(frozen, current)
            self.installed(udid, lane + "-pre-postflight")
            # The original bounded same-build install preserves all source-store
            # bytes and proves stopped-process identities before native reopening.
            installation = preservation.install_for_postflight(frozen, self.app, self.carriers["sha256"], directory / "private",
                                                               self.helpers["run_ui27"].code_carriers)
            post_env = preservation.environment(frozen, installation)
            post, _ = self.stage(directory, "postflight", udid, [preservation.METHOD + "()"], post_env)
            native, current = self.read_private(udid, SUPPORT / ("pinkha-type-preservation-result-" + bound["nonce"] + ".json"),
                                                 directory / "postflight/private", lane + "-native-readback")
            outcome["postflight"] = post
            outcome["nativePreservation"] = preservation.validate_result(frozen, installation, preservation.decode(native), post, current)
        return outcome

    def pending(self, directory, udid):
        import combined_t5_retry as combined
        original = self.helpers["t5_native_account_retry_pending_evidence"]
        retained = original.validate_retained_source(self.source)
        token = uuid.uuid4().hex
        env = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_T5_ACCOUNT_RETRY_PENDING": "1",
               "PINKHA_T5_PAGINATION_TOKEN": token, "PINKHA_T5_PAGINATION_APP_SHA": self.binding["sourceSHA"],
               "PINKHA_T5_PAGINATION_RUN_ID": self.binding["runID"], "PINKHA_T5_ACCOUNT_RETRY_RUN_ATTEMPT": self.binding["runAttempt"],
               "PINKHA_T5_ACCOUNT_RETRY_RUNTIME_PROFILE": PROFILE, "PINKHA_T5_ACCOUNT_RETRY_RUNTIME_VERSION": shared.VERSION}
        result, path = self.stage(directory, "native", udid, [original.METHOD + "()"], env, allowance=900)
        relative = Path("Library/Application Support/pinkha-t5-native-pagination")
        fixture_raw, container = self.read_private(udid, relative / "account-retry-fixture.json", directory / "private", "pending-fixture")
        native_raw, current = self.read_private(udid, relative / "account-retry-receipt.json", directory / "private", "pending-native")
        credentials, current = self.read_private(udid, relative / "secrets.json", directory / "private", "pending-credentials")
        require(current == container and not (container / relative / "receipt.json").exists(),
                "Original pagination body must not be replayed or replaced")
        fixture = decode(fixture_raw); native = decode(native_raw)
        account = fixture["state"]["accountID"]
        require(isinstance(account, str) and account not in ("", ".", "..") and "/" not in account and "\\" not in account, "Actual account directory name invalid")
        helper = self.helpers["run_t5_native_pagination"]
        root = container / helper.pair.ROOT_RELATIVE_PATH
        directories = {"root": helper.existing_directory_identity(root), "account": helper.existing_directory_identity(root / account)}
        summary = decode(raw(path / "summary.json"))
        counts = combined.validate_combined_receipt(native, fixture, fixture_raw, source=self.binding["sourceSHA"],
            run_id=self.binding["runID"], run_attempt=self.binding["runAttempt"], token=token,
            root_sha=directories["root"]["pathSHA256"], credential_sha=sha(credentials), current_directories=directories,
            execution_window=[summary.get("startTime"), summary.get("finishTime")], pending_only=True, runtime_profile=PROFILE)
        return {"native": result, "actualCounts": counts, "retainedHistoricalPagination": retained,
                "actualCombinedRuntime": shared.VERSION, "credentialSHA256": sha(credentials), "controllerDirectories": directories}

    def freshness(self, directory, udid):
        import combined_t5_freshness as combined
        original = self.helpers["t5_remaining_freshness"]
        contract = original.source_contract(self.source); token = uuid.uuid4().hex
        env = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_T5_REMAINING_FRESHNESS": "1",
               "PINKHA_T5_FRESHNESS_TOKEN": token, "PINKHA_T5_FRESHNESS_APP_SHA": self.binding["sourceSHA"],
               "PINKHA_T5_FRESHNESS_RUN_ID": self.binding["runID"], "PINKHA_T5_FRESHNESS_RUN_ATTEMPT": self.binding["runAttempt"],
               "PINKHA_T5_FRESHNESS_RUNTIME_PROFILE": PROFILE}
        result, _ = self.stage(directory, "native", udid, [original.METHOD + "()"], env)
        value, container = self.read_private(udid, Path(original.PRIVATE) / "receipt.json", directory / "private", "freshness-native")
        _, root_sha = original.native_paths(container)
        counts = combined.validate_combined_receipt(decode(value), source=self.binding["sourceSHA"], run_id=self.binding["runID"],
            run_attempt=self.binding["runAttempt"], token=token, root_sha=root_sha, runtime=shared.VERSION)
        return {"native": result, "sourceContract": contract, "actualCounts": counts, "nativeReceiptSHA256": sha(value)}

    def native_ui(self, directory, udid):
        evidence = self.helpers["t5_native_ui_evidence"]
        original = self.helpers["run_t5_native_ui"]
        mutations = self.helpers["t5_native_ui_mutations"]
        r08 = self.helpers["t5_native_ui_r08"]
        token = uuid.uuid4().hex
        env = {"PINKHA_T5_UI_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_T5_UI_TOKEN": token,
               "PINKHA_T5_UI_APP_SHA": self.binding["sourceSHA"], "PINKHA_T5_UI_RUN_ID": self.binding["runID"],
               "PINKHA_T5_UI_RUNTIME_PROFILE": PROFILE}
        prep, _ = self.stage(directory, "preparation", udid, [evidence.PREPARATION + "()"], env)
        fixture_raw, container = self.read_private(udid, original.UI_FIXTURE, directory / "private", "t5-ui-fixture", 65536)
        fixture = decode(fixture_raw)
        evidence.validate_standalone_fixture(fixture, source=self.binding["sourceSHA"], run_id=self.binding["runID"], token=token, runtime=shared.VERSION)
        identity, _ = original.native_ui_identity(container)
        mutation_raw, container2 = self.read_private(udid, mutations.RELATIVE, directory / "private", "t5-ui-mutations", 65536)
        require(container2 == container, "Native fixture moved before UI")
        native_mutations = mutations.validate(decode(mutation_raw), fixture)
        ui_env = {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_T5_NATIVE_UI_FIXTURE_JSON": fixture_raw.decode(),
                  "PINKHA_T5_UI_TOKEN": token, "PINKHA_T5_UI_APP_SHA": self.binding["sourceSHA"],
                  "PINKHA_T5_UI_RUN_ID": self.binding["runID"], "PINKHA_UI27_APP_LANGUAGE": "en",
                  "PINKHA_UI27_SELECTION_SCOPE": "WAVE15_ACCEPTANCE"}
        ui, path = self.stage(directory, "core-ui", udid, list(evidence.METHODS.values()), ui_env, target=UI)
        observed, files = evidence.read_ui_receipts(path / "private-attachments", fixture)
        current = self.container(udid, "data", "t5-ui-core-identity")
        require(original.native_ui_identity(current)[0] == identity, "UI replaced original native credentials/fixture")
        note = observed["receipts"]["note-lifecycle"]["observations"][-1]
        retained = {k: note[k] for k in ("objectID", "blockID", "actualText")}
        used = {fixture["preparationProcessID"], *observed["actual_processes"]}
        reports = {}
        for appearance in r08.APPEARANCES:
            name = "r08-he-" + appearance
            self.appearance(udid, "t5-" + name, appearance, "large")
            env = dict(ui_env, PINKHA_UI27_APP_LANGUAGE="he", PINKHA_T5_UI_PRESENTATION_MODE="R08",
                       PINKHA_T5_UI_APPEARANCE=appearance, PINKHA_T5_R08_RETAINED_NOTE_JSON=json.dumps(retained))
            selected, stage_path = self.stage(directory, name, udid, [r08.METHOD], env, target=UI)
            report, _ = r08.read_receipt(stage_path / "private-attachments", appearance, fixture, retained, used)
            used.add(report["process_id"])
            current = self.container(udid, "data", "t5-" + name + "-identity")
            require(original.native_ui_identity(current)[0] == identity, "R08 changed original fixture/credentials")
            for key, expected in (("appearance", appearance), ("content_size", "large")):
                log, _ = self.command(["xcrun", "simctl", "ui", udid, key], "t5-" + name + "-after-" + key.replace("_", "-"), 30)
                r08.actual_setting(raw(log).decode(), expected, key)
            reports[appearance] = {"selected": selected, "originalObservations": report}
        return {"preparation": prep, "nativeMutations": native_mutations, "coreUI": ui, "originalCoreReceipts": observed,
                "r08": reports, "fixtureIdentity": identity, "visualReview": "PENDING", "voiceOver": "NOT_RUN",
                "dynamicTypeScope": "fixed-large-only", "physicalDevice": "NOT_RUN"}

    def execute_lane(self, lane):
        directory = self.root / "evidence/lanes" / lane; directory.mkdir(parents=True, mode=0o700)
        result = {"status": "FAIL", "lane": lane, "buildConfiguration": "Debug-Anytype",
                  "releaseAccepted": False, "fullMatrixAccepted": False, "sourceCommit": self.binding["sourceSHA"], "errors": []}
        udid = None
        try:
            udid, language = self.create(lane, directory, editor=lane == "editor")
            if lane in ("editor", "quote-drop", "properties-set"):
                result["actual"] = self.wave(lane, directory, udid, language)
            elif lane == "return-controls":
                require(isinstance(self.admission.get("returnControlRerunReason"), str)
                        and len(self.admission["returnControlRerunReason"].strip()) > 30,
                        "Concrete affected-path reason required to repeat accepted Return controls")
                result["actual"], _ = self.stage(directory, "native", udid, [n + "()" for n in RETURN], {}, allowance=360)
                result["affectedPathReason"] = self.admission["returnControlRerunReason"]
            elif lane == "t5-host-actions":
                contract = self.helpers["t5_host_actions"].source_contract(self.source)
                methods = [n.removeprefix(NATIVE + "/") for n in contract["compiled_identifiers"]]
                result["actual"], _ = self.stage(directory, "native", udid, methods, {}, allowance=600, host_contract=contract)
                result["actualNativeACLAccepted"] = result["actualNativePersistenceAccepted"] = False
            elif lane == "t5-pending-nine": result["actual"] = self.pending(directory, udid)
            elif lane == "t5-remaining-freshness": result["actual"] = self.freshness(directory, udid)
            elif lane == "t5-native-ui": result["actual"] = self.native_ui(directory, udid)
            else: raise ValueError("Unreviewed original lane")
            result["status"] = "PASS_ORIGINAL_METHODS_FUNCTIONAL_SCOPE"
        except BaseException as exc:
            result["firstFailure"] = shared.error(exc)
        finally:
            if udid:
                try: result["privateEvidence"] = self.preserve(udid, directory, lane)
                except BaseException as exc: result["errors"].append({"phase": "private-retention", **shared.error(exc)})
                try:
                    self.command(["xcrun", "simctl", "shutdown", udid], lane + "-shutdown", 60, capacity=False)
                    result["ownedSimulator"] = {"udid": udid, "status": "SHUTDOWN_ACCOUNT_RETAINED", "deleted": False}
                except BaseException as exc: result["errors"].append({"phase": "owned-shutdown", **shared.error(exc)})
            try:
                result["productsUnchanged"] = {k: shared.product_integrity(v) for k, v in self.built.items()}
            except BaseException as exc: result["errors"].append({"phase": "products", **shared.error(exc)})
            if result["errors"]: result["status"] = "FAIL"
            result["finishedAt"] = time.time()
            write(directory / "execution.json", result)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon Mac required")
    admission_raw = raw(args.admission)
    require(sha(admission_raw) == args.admission_sha256, "Reviewed original admission bytes differ")
    admission = decode(admission_raw)
    require(admission.get("schema") == "pinkha-combined-host-acceptance-admission-v1"
            and admission.get("executionEnvironment") == "SentinelX-owned-Mac"
            and admission.get("nativeManifestSHA256") == shared.MANIFEST and admission.get("heartOverlaySHA256") == shared.OVERLAY
            and admission.get("plan") in PLANS and admission.get("buildConfiguration") == "Debug-Anytype"
            and admission.get("appLanguage") in ("en", "he") and admission.get("appearance") in ("light", "dark")
            and admission.get("deviceFamily") in ("iphone", "ipad"), "Explicit exact combined functional admission required")
    parent = Path(__file__).resolve().parent
    required_files = {"combined_host_acceptance.py", "combined_heart_semantics.py", "combined_heart_observations.py",
                      "combined_host_helper_pins.json", "combined_t5_pending.py", "combined_t5_retry.py", "combined_t5_freshness.py"}
    require(set(admission.get("controlFiles", {})) == required_files, "Complete reviewed controller closure required")
    for name, expected in admission["controlFiles"].items():
        require(digest(parent / name) == expected, "Reviewed control source changed: " + name)
    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")
    args.root.mkdir(mode=0o700)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    write_bytes(evidence / "admission.json", admission_raw)
    commands = shared.Commands(args.root / "commands", args.root)
    binding = {"sourceSHA": admission["sourceCommit"], "runID": str(time.time_ns() // 1000), "runAttempt": "1", "nonce": uuid.uuid4().hex}
    result = {"status": "FAIL", "sourceCommit": admission["sourceCommit"], "binding": binding,
              "bindingIdentityKind": "unique local receipt identity, not a GitHub Actions run ID", "plan": admission["plan"],
              "configuration": "Debug-Anytype", "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0,
              "releaseAccepted": False, "fullFAcceptance": False, "fullT5Acceptance": False, "physicalDevice": "NOT_RUN",
              "series": {name: {"status": "NOT_RUN"} for name in ORIGINAL_SERIES},
              "requiredCoverageMatrix": {"UI" + str(i).zfill(2): "NOT_PROVEN_BY_NAMED_LANE_RESULT" for i in range(1, 13)}}
    built = {}
    try:
        source_proof, built, app = shared.admit_and_clone_products(admission, args.root, evidence, commands)
        result["sourceAdmission"] = source_proof
        result["originalHelpers"] = freeze_helpers(Path(admission["sourceRoot"]), admission["sourceCommit"], args.root / "helpers",
                                                    parent / "combined_host_helper_pins.json")
        helpers = load_helpers(args.root / "helpers")
        log, _ = commands.run(["xcodebuild", "-help"], "xcode-help", 30)
        require("-collect-test-diagnostics" in raw(log).decode() and "never" in raw(log).decode(), "Documented diagnostic option unavailable")
        log, _ = commands.run(["xcrun", "simctl", "list", "--json"], "simulator-inventory", 60)
        inventory = decode(raw(log))
        runtime = [r for r in inventory["runtimes"] if r.get("identifier") == shared.RUNTIME]
        device = [d for d in inventory["devicetypes"] if d.get("identifier") == admission["deviceType"]]
        require(len(runtime) == len(device) == 1 and runtime[0].get("isAvailable") is True
                and runtime[0].get("version") == shared.OS_VERSION and runtime[0].get("buildversion") == shared.OS_BUILD,
                "Actual exact installed runtime/device required")
        family = "iphone" if device[0].get("name", "").startswith("iPhone") else "ipad" if device[0].get("name", "").startswith("iPad") else None
        require(family == admission["deviceFamily"], "Actual device family differs from the declared coverage")
        supported = {d["identifier"] if isinstance(d, dict) else d for d in runtime[0].get("supportedDeviceTypes", [])}
        require(not supported or admission["deviceType"] in supported, "Requested actual device unsupported by installed runtime")
        result["actualConfiguration"] = {"runtime": runtime[0], "device": device[0], "family": family,
                                       "language": admission["appLanguage"], "appearance": admission["appearance"]}
        consumer = Consumer(args.root, admission, commands, built, app, helpers, binding)
        for lane in PLANS[admission["plan"]]:
            actual = consumer.execute_lane(lane)
            result["series"][lane] = {"status": actual["status"], "receipt": "lanes/" + lane + "/execution.json",
                                      "sha256": digest(evidence / "lanes" / lane / "execution.json")}
            if lane == "editor":
                prep = evidence / "lanes/editor/preparation/result.json"
                result["series"]["rtl-preparation"] = {"status": decode(raw(prep)).get("status") if prep.is_file() else "NOT_RUN",
                    "receipt": "lanes/editor/preparation/result.json" if prep.is_file() else None}
            write(evidence / ("checkpoint-" + lane + ".json"), result)
        selected = [result["series"][lane]["status"] for lane in PLANS[admission["plan"]]]
        if selected and all(status == "PASS_ORIGINAL_METHODS_FUNCTIONAL_SCOPE" for status in selected):
            result["status"] = "PASS_SELECTED_COMBINED_DEBUG_FUNCTIONAL_METHODS"
    except BaseException as exc:
        result["firstFailure"] = shared.error(exc)
    finally:
        cleanup = {"status": "PASS", "errors": []}
        for group in commands.groups:
            if group not in commands.absent_groups and commands.present(group):
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"ownedGroupStillPresent": group})
        try:
            result["finalProducts"] = {k: shared.product_integrity(v) for k, v in built.items()}
        except BaseException as exc: cleanup["status"] = "FAIL"; cleanup["errors"].append(shared.error(exc))
        result["cleanup"] = cleanup
        if cleanup["status"] != "PASS": result["status"] = "FAIL"
        write(evidence / "execution.json", result)
    print(json.dumps({"status": result["status"], "receipt": str(evidence / "execution.json"),
                      "series": {k: v["status"] for k, v in result["series"].items()}, "firstFailure": result.get("firstFailure")}, sort_keys=True))
    return 0 if result["status"] == "PASS_SELECTED_COMBINED_DEBUG_FUNCTIONAL_METHODS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
