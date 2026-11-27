"""Finite NativeUI RTL configuration; never launches an application by itself.

The original NativeUI consumer owns every command, simulator and XCTest result.
The unchanged original language, appearance and code-carrier validators are
loaded from exact files in the separately admitted source tree.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re

TARGET = "PinkhaAnyNativeUITests"
SELECTOR = "NativeLaunchTests/testExplicitHebrewDirectionAndAlignmentSurviveColdReopen"
ENVIRONMENT = "PINKHA_NATIVE_RTL_APP_LANGUAGE"
ALLOWANCE = 360
PASS = "PASS_NATIVE_RTL_METHOD_VISUAL_REVIEW_PENDING"
SOURCE_BEFORE = "fdb706fc9d1c805ceb7220e4ae64a14244f7437525cf06d8d14e1b1f100de6da"
SOURCE_AFTER = "e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375"
SOURCE_PROOF = "docs/validation/20261127-wave2-native-rtl/source-proof.json"
SOURCE_PROOF_SHA = "699e0ccdb963cfd9a630b65ffce9973a5c63d440b62db7fa3aacdb34907240d5"
HELPERS = {
    "validate_device_language": {
        "path": "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py",
        "sha256": "f99b1c04efeee2be45459b49d8c71fd8207039c97be4578cd6f2dfc8d29bb283",
        "functionSHA256": "2b1bd87999afaad3bf56337a6168706e6540e798338971ac10f5c965b64cf813",
    },
    "actual_setting": {
        "path": "Tools/PinkhaSimulatorGate/t5_native_ui_r08.py",
        "sha256": "f726c600bd04f77b2ca8e8b42610b6c66dfbdaf96d86cc6535eaed0218fae4ea",
        "functionSHA256": "3c1bfb0e07e92b7938b55b5f6b7c8f1affe1a8914204b8ea341b245f5e185d02",
    },
    "code_carriers": {
        "path": "Tools/PinkhaSimulatorGate/run_ui27.py",
        "sha256": "87e0972ee6852d1fdb34d82afa5dde346baf836afaa8419203b647e7d3e21ca7",
        "functionSHA256": "9173ba8198b3ae2a47ecb8f9be33cc2d015f31fe0a5315fb7d88c0cdf1225fcb",
    },
}


def qualify_source(c, current, proof_raw):
    c.require(c.sha(proof_raw) == SOURCE_PROOF_SHA and c.sha(current) == SOURCE_AFTER,
              "Exact reviewed Native RTL source and inverse proof required")
    proof = c.decode(proof_raw)
    before, after = proof["methodBefore"].encode(), proof["methodAfter"].encode()
    c.require(proof["sourceBeforeSHA256"] == SOURCE_BEFORE
              and proof["sourceAfterSHA256"] == SOURCE_AFTER
              and proof["methodBeforeSHA256"] == c.sha(before)
              and proof["methodAfterSHA256"] == c.sha(after)
              and proof["allBytesOutsideRTLMethodUnchanged"] is True
              and proof["hebrewActionsAndAssertionsRestoreExactly"] is True
              and current.count(after) == 1,
              "Exact single-method RTL localization inverse required")
    restored = current.replace(after, before)
    c.require(c.sha(restored) == SOURCE_BEFORE,
              "RTL localization inverse must restore every original NativeLaunch byte")
    return restored


def cell(c, path, expected):
    c.require(path is not None and path.is_absolute() and path.resolve() == path
              and not path.is_symlink() and re.fullmatch(r"[0-9a-f]{64}", expected or ""),
              "Canonical explicitly pinned RTL cell required")
    raw = c.raw(path, 4096)
    c.require(c.sha(raw) == expected, "Pinned RTL cell changed")
    value = c.decode(raw)
    c.require(isinstance(value, dict) and set(value) == {
        "schema", "appLanguage", "deviceFamily", "deviceType", "appearance", "contentSize"
    } and value["schema"] == "pinkha-native-rtl-cell-v1"
        and value["appLanguage"] in ("he", "en")
        and value["deviceFamily"] in ("iphone", "ipad")
        and isinstance(value["deviceType"], str)
        and re.fullmatch(r"com\.apple\.CoreSimulator\.SimDeviceType\.[A-Za-z0-9-]+", value["deviceType"])
        and value["appearance"] in ("light", "dark") and value["contentSize"] == "large",
        "One explicit original-language/device/appearance RTL cell required")
    c.require(all(key not in os.environ for key in (ENVIRONMENT, "TEST_RUNNER_" + ENVIRONMENT)),
              "Ambient native RTL runner-language overrides are forbidden")
    return value


def original_helpers(c, source):
    functions, closure = {}, {}
    for name, row in HELPERS.items():
        path = source / row["path"]
        c.require(path.resolve() == path and not path.is_symlink(), "Canonical original RTL helper required")
        raw = c.raw(path, 128 * 1024)
        c.require(c.sha(raw) == row["sha256"], "Original RTL helper file changed: " + row["path"])
        text = raw.decode()
        nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == name]
        c.require(len(nodes) == 1 and c.sha(ast.get_source_segment(text, nodes[0]).encode()) == row["functionSHA256"],
                  "Exact original RTL helper declaration required: " + name)
        namespace = dict(require=c.require, core=c, digest=c.digest, Path=Path,
                         hashlib=hashlib, plistlib=plistlib, json=json)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        functions[name] = namespace[name]
        closure[name] = row
    return functions, closure


def device(c, runtimes_raw, types_raw, configuration):
    c.require(len(runtimes_raw) <= 1024**2 and len(types_raw) <= 1024**2,
              "Bounded actual simulator inventories required")
    runtimes = [row for row in c.decode(runtimes_raw)["runtimes"] if row.get("identifier") == c.RUNTIME]
    types = [row for row in c.decode(types_raw)["devicetypes"] if row.get("identifier") == configuration["deviceType"]]
    c.require(len(runtimes) == len(types) == 1 and runtimes[0].get("isAvailable") is True
              and runtimes[0].get("version") == c.OS_VERSION and runtimes[0].get("buildversion") == c.OS_BUILD,
              "Exact shared runtime and installed requested device required")
    runtime, actual = runtimes[0], types[0]
    name = actual.get("name", "")
    family = "iphone" if name.startswith("iPhone") else "ipad" if name.startswith("iPad") else None
    c.require(family == configuration["deviceFamily"], "Actual device family differs from RTL coverage")
    supported = {row["identifier"] if isinstance(row, dict) else row for row in runtime.get("supportedDeviceTypes", [])}
    c.require(not supported or actual["identifier"] in supported, "RTL device is unsupported by the exact shared runtime")
    return runtime, actual


def observe(c, helpers, configuration, run, out, udid, phase):
    _, raw = run(["xcrun", "simctl", "spawn", udid, "defaults", "export", "NSGlobalDomain", "-"],
                 out, "rtl-" + phase + "-language-readback", timeout=120)
    language = helpers["validate_device_language"](raw, configuration["appLanguage"])
    presentation = {}
    for key, expected in (("appearance", configuration["appearance"]), ("content_size", "large")):
        _, raw = run(["xcrun", "simctl", "ui", udid, key], out,
                     "rtl-" + phase + "-" + key.replace("_", "-") + "-readback", timeout=30)
        c.require(len(raw) <= 4096, "Bounded original appearance readback required")
        presentation[key] = helpers["actual_setting"](raw.decode(), expected, key)
    value = {"language": language, "presentation": presentation, "ownedUDID": udid,
             "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
    c.write(out / ("rtl-" + phase + "-environment.json"), value)
    return value


def prepare(c, helpers, configuration, run, out, udid):
    owned = c.decode(c.raw(out / "simulator.json", 4096))
    c.require(owned["ownedUDID"] == udid and owned["runtime"] == c.RUNTIME
              and owned["deviceType"] == configuration["deviceType"], "Original fresh owned RTL simulator required")
    empty, _ = run(["xcrun", "simctl", "get_app_container", udid, c.BUNDLE, "data"], out,
                   "rtl-assert-empty-account", timeout=30, allow_failure=True)
    c.require(empty["exitCode"] != 0 and empty.get("stopped") is None
              and empty.get("ownedProcessGroup") == "ABSENT_ESRCH", "Fresh RTL simulator must have no existing app account")
    language = "en" if configuration["appLanguage"] == "he" else "he"
    locale = "en_US" if language == "en" else "he_IL"
    commands = [
        ["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLanguages", "-array", language],
        ["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLocale", "-string", locale],
        ["xcrun", "simctl", "shutdown", udid], ["xcrun", "simctl", "boot", udid],
        ["xcrun", "simctl", "bootstatus", udid, "-b"],
    ]
    for index, argv in enumerate(commands):
        run(argv, out, "rtl-language-" + str(index), timeout=180)
    for key, value in (("appearance", configuration["appearance"]), ("content_size", "large")):
        run(["xcrun", "simctl", "ui", udid, key, value], out,
            "rtl-set-" + key.replace("_", "-"), timeout=30)
    return observe(c, helpers, configuration, run, out, udid, "before")


def installed(c, helpers, run, out, udid, app, phase):
    _, raw = run(["xcrun", "simctl", "get_app_container", udid, c.BUNDLE, "app"], out,
                 "rtl-" + phase + "-installed-app", timeout=30)
    c.require(len(raw) <= 4096, "Bounded original installed app path required")
    path = Path(raw.decode().strip())
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
    c.require(path.is_absolute() and path.resolve() == path and path.is_dir() and path.is_relative_to(owner),
              "Installed app escaped its actual owned RTL simulator")
    original, actual = helpers["code_carriers"](app), helpers["code_carriers"](path)
    c.require(actual["sha256"] == original["sha256"], "Installed RTL app code differs from the admitted producer")
    proof = {"installedApp": str(path), "producerCodeCarriersSHA256": original["sha256"],
             "installedCodeCarriersSHA256": actual["sha256"], "originalHelper": HELPERS["code_carriers"]}
    c.write(out / ("rtl-" + phase + "-installed-code.json"), proof)
    return proof


def bind(c, original, configuration):
    c.require(set(original) == {TARGET, "__xctestrun_metadata__"}, "Original single native target descriptor required")
    target = original[TARGET]
    c.require(target["OnlyTestIdentifiers"] == [SELECTOR]
              and target["EnvironmentVariables"].get("PINKHA_NATIVE_UI_UNIFIED_HOST") == "1"
              and target["EnvironmentVariables"].get("PINKHA_SIMULATOR_UI_DISPOSABLE") == "1"
              and all(ENVIRONMENT not in target.get(key, {}) and "TEST_RUNNER_" + ENVIRONMENT not in target.get(key, {})
                      for key in ("EnvironmentVariables", "TestingEnvironmentVariables", "UITargetAppEnvironmentVariables")),
              "Original native RTL selection and unambiguous runner environment required")
    value = copy.deepcopy(original)
    value[TARGET]["EnvironmentVariables"][ENVIRONMENT] = configuration["appLanguage"]
    inverse = copy.deepcopy(value)
    del inverse[TARGET]["EnvironmentVariables"][ENVIRONMENT]
    c.require(inverse == original, "Only the exact native RTL app-language variable may be added")
    return value, {"environmentKey": ENVIRONMENT, "appLanguage": configuration["appLanguage"],
                   "inverseRestoresOriginalBoundDescriptor": True, "selector": TARGET + "/" + SELECTOR,
                   "methodBudgetSeconds": ALLOWANCE}


def screenshots(c, directory, udid, configuration):
    manifest_raw = c.raw(directory / "manifest.json", 8 * 1024**2)
    manifest = c.decode(manifest_raw)
    c.require(isinstance(manifest, list), "Original RTL attachment manifest required")
    names = {"NATIVE_RTL_" + configuration["appLanguage"] + "_center_" + phase: phase
             for phase in ("before_reopen", "after_reopen")}
    found, paths = {}, set()
    for row in manifest:
        for item in row.get("attachments", []):
            human = str(item.get("suggestedHumanReadableName", ""))
            if not human.startswith("NATIVE_RTL_"):
                continue
            matches = [name for name in names if re.fullmatch(re.escape(name) + r"(?:_[A-Za-z0-9-]+)*\.png", human)]
            test = str(row.get("testIdentifier", "")).removeprefix(TARGET + "/").removesuffix("()")
            c.require(len(matches) == 1 and test == SELECTOR
                      and str(item.get("deviceId", "")).lower() == udid.lower()
                      and item.get("isAssociatedWithFailure") is False,
                      "RTL screenshot name/test/device or outcome differs")
            name = item.get("exportedFileName")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", "..")
                      and Path(name).suffix == ".png", "Original RTL screenshot path escaped")
            path = directory / name
            phase = names[matches[0]]
            c.require(path.resolve() == path and not path.is_symlink() and name not in paths and phase not in found,
                      "Duplicate or aliased original RTL screenshot")
            raw = c.raw(path, 20 * 1024**2)
            c.require(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[8:16] == b"\x00\x00\x00\rIHDR"
                      and 0 < int.from_bytes(raw[16:20], "big") <= 16384
                      and 0 < int.from_bytes(raw[20:24], "big") <= 16384, "Actual bounded RTL PNG required")
            found[phase] = {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw),
                            "width": int.from_bytes(raw[16:20], "big"), "height": int.from_bytes(raw[20:24], "big")}
            paths.add(name)
    c.require(set(found) == {"before_reopen", "after_reopen"}, "Both actual original RTL screenshots are required")
    return {"manifestSHA256": c.sha(manifest_raw), "screenshots": found, "visualReview": "PENDING"}
