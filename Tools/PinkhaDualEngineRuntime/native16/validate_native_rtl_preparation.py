#!/usr/bin/env python3
"""Portable controls for the added RTL configuration seam; zero Apple commands."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import plistlib
import tempfile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--original-helper-root", type=Path, required=True)
    parser.add_argument("--shared-controller", type=Path, required=True)
    parser.add_argument("--shared-controller-sha256", required=True)
    parser.add_argument("--native-launch", type=Path, required=True)
    parser.add_argument("--source-proof", type=Path, required=True)
    parser.add_argument("--only-control", help="Replay one named portable control without repeating passed controls")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sha = lambda value: hashlib.sha256(value).hexdigest()
    if sha(args.shared_controller.read_bytes()) != args.shared_controller_sha256:
        raise ValueError("Exact shared utility module required for portable controls")
    c = load(args.shared_controller, "rtl_control_shared")
    m = load(args.control_root / "native_rtl_matrix.py", "rtl_control_matrix")
    profile = load(args.control_root / "native16_profile.py", "rtl_control_profile")
    helpers, closure = m.original_helpers(c, args.original_helper_root)
    results = []

    def control(name, action):
        if args.only_control is not None and args.only_control != name:
            return
        try:
            detail = action()
            results.append({"name": name, "status": "PASS", "detail": detail})
        except BaseException as error:
            results.append({"name": name, "status": "FAIL", "error": str(error)})

    def rejected(action):
        try:
            action()
        except (RuntimeError, ValueError):
            return
        raise AssertionError("The invalid configuration was accepted")

    def inverse():
        prepared = args.native_launch.read_bytes()
        original = m.qualify_source(c, prepared, args.source_proof.read_bytes())
        assert sha(original) == m.SOURCE_BEFORE
        assert original.count(profile.TITLE_AFTER) == 1
        oldest = original.replace(profile.TITLE_AFTER, profile.TITLE_BEFORE)
        assert sha(oldest) == profile.TITLE_ORIGINAL_SHA
        changed_elsewhere = prepared.replace(b'let documentName = "Drag document "', b'let documentName = "Changed document "', 1)
        assert changed_elsewhere != prepared
        rejected(lambda: m.qualify_source(c, changed_elsewhere, args.source_proof.read_bytes()))
        return {"restoredFileSHA256": sha(original), "restoredTitleBaselineSHA256": sha(oldest),
                "mutationOutsideRTLRejected": True}

    control("single_method_inverse_then_original_title_inverse", inverse)
    with tempfile.TemporaryDirectory(prefix="native-rtl-portable-") as temporary:
        root = Path(temporary).resolve()
        device_id = "00000000-0000-4000-8000-000000000001"
        base = {"schema": "pinkha-native-rtl-cell-v1", "appLanguage": "he", "deviceFamily": "ipad",
                "deviceType": "com.apple.CoreSimulator.SimDeviceType.iPad-Synthetic-Control",
                "appearance": "light", "contentSize": "large"}

        def pinned(value):
            path = root / "cell.json"
            path.write_text(json.dumps(value, sort_keys=True) + "\n")
            return m.cell(c, path, sha(path.read_bytes()))

        def descriptor():
            return {m.TARGET: {"OnlyTestIdentifiers": [m.SELECTOR],
                              "EnvironmentVariables": {"PINKHA_NATIVE_UI_UNIFIED_HOST": "1",
                                                       "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
                              "SystemAttachmentLifetime": "keepAlways", "UserAttachmentLifetime": "keepAlways"},
                    "__xctestrun_metadata__": {"FormatVersion": 1}}

        def finite_matrix():
            cells = []
            for language, family, appearance in itertools.product(("he", "en"), ("iphone", "ipad"), ("light", "dark")):
                value = dict(base, appLanguage=language, deviceFamily=family, appearance=appearance,
                             deviceType="com.apple.CoreSimulator.SimDeviceType." + ("iPhone" if family == "iphone" else "iPad") + "-Synthetic-Control")
                selected = pinned(value)
                bound, binding = m.bind(c, descriptor(), selected)
                assert bound[m.TARGET]["EnvironmentVariables"][m.ENVIRONMENT] == language
                assert binding["inverseRestoresOriginalBoundDescriptor"] is True
                directory = root / (language + "-" + family + "-" + appearance)
                directory.mkdir()
                c.write(directory / "simulator.json", {"ownedUDID": device_id, "runtime": c.RUNTIME, "deviceType": selected["deviceType"]})
                calls = []
                opposite = "en" if language == "he" else "he"
                preferences = plistlib.dumps({"AppleLanguages": [opposite], "AppleLocale": "en_US" if opposite == "en" else "he_IL"})

                def fake_run(argv, out, label, **kwargs):
                    calls.append((argv, label))
                    assert out == directory
                    if "get_app_container" in argv:
                        return {"exitCode": 1, "stopped": None, "ownedProcessGroup": "ABSENT_ESRCH"}, b"synthetic absent app"
                    if "export" in argv:
                        return {"exitCode": 0}, preferences
                    if len(argv) == 6 and argv[:3] == ["xcrun", "simctl", "ui"]:
                        return {"exitCode": 0}, b""
                    if len(argv) == 5 and argv[:3] == ["xcrun", "simctl", "ui"]:
                        return {"exitCode": 0}, (appearance if argv[-1] == "appearance" else "large").encode()
                    return {"exitCode": 0}, b""

                observed = m.prepare(c, helpers, selected, fake_run, directory, device_id)
                assert observed["language"]["device_language"] == opposite
                assert observed["language"]["app_override_verified_by_this_observation"] is False
                assert observed["presentation"] == {"appearance": appearance, "content_size": "large"}
                commands = [argv for argv, _ in calls]
                assert commands.index(["xcrun", "simctl", "shutdown", device_id]) < commands.index(
                    ["xcrun", "simctl", "spawn", device_id, "defaults", "export", "NSGlobalDomain", "-"])
                assert len({label for _, label in calls}) == len(calls)
                cells.append({"appLanguage": language, "osLanguage": opposite, "deviceFamily": family, "appearance": appearance})
            return {"syntheticConfigurations": cells, "actualAppleCommands": 0, "actualMatrixCells": 0}

        control("eight_finite_configurations_use_original_readback_and_explicit_descriptor_binding", finite_matrix)

        def invalid_cell():
            for value in (dict(base, appLanguage="fr"), dict(base, appearance="automatic"),
                          dict(base, deviceFamily="mac"), dict(base, contentSize="accessibility-large"),
                          dict(base, sourceCommit="arbitrary-override")):
                rejected(lambda value=value: pinned(value))
            return {"unsupportedOrAdditionalConfigurationRejected": 5}

        control("unsupported_configuration_cannot_expand_scope", invalid_cell)

        def descriptor_conflict():
            original = descriptor()
            original[m.TARGET]["EnvironmentVariables"][m.ENVIRONMENT] = "en"
            rejected(lambda: m.bind(c, original, base))
            original = descriptor()
            original[m.TARGET]["OnlyTestIdentifiers"] = ["NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen"]
            rejected(lambda: m.bind(c, original, base))
            return {"conflictingLanguageAndUnselectedJourneyRejected": True}

        control("descriptor_conflict_or_other_journey_rejected", descriptor_conflict)

        def runtime_mismatch():
            runtime = {"identifier": c.RUNTIME, "version": c.OS_VERSION, "buildversion": c.OS_BUILD,
                       "isAvailable": True, "supportedDeviceTypes": [base["deviceType"]]}
            actual_type = {"identifier": base["deviceType"], "name": "iPad Synthetic Control"}
            encode = lambda value: json.dumps(value).encode()
            assert m.device(c, encode({"runtimes": [runtime]}), encode({"devicetypes": [actual_type]}), base) == (runtime, actual_type)
            rejected(lambda: m.device(c, encode({"runtimes": [dict(runtime, buildversion="unadmitted")]}), encode({"devicetypes": [actual_type]}), base))
            rejected(lambda: m.device(c, encode({"runtimes": [runtime]}), encode({"devicetypes": [dict(actual_type, name="iPhone Wrong Family")]}), base))
            return {"wrongRuntimeBuildAndMisreportedDeviceFamilyRejected": True}

        control("installed_runtime_and_device_family_cannot_be_relabelled", runtime_mismatch)

        def wrong_readbacks():
            same_language = plistlib.dumps({"AppleLanguages": ["he"], "AppleLocale": "he_IL"})
            rejected(lambda: helpers["validate_device_language"](same_language, "he"))
            rejected(lambda: helpers["actual_setting"]("light", "dark", "appearance"))
            return {"matchingOSLanguageAndWrongAppearanceRejectedByOriginalHelpers": True}

        control("original_validators_reject_wrong_actual_readbacks", wrong_readbacks)

        def images():
            directory = root / "synthetic-attachments"
            directory.mkdir()
            pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jO1sAAAAASUVORK5CYII=")
            attachments = []
            for phase in ("before_reopen", "after_reopen"):
                name = phase + ".png"
                (directory / name).write_bytes(pixel)
                attachments.append({"suggestedHumanReadableName": "NATIVE_RTL_he_center_" + phase + "_1_" + device_id + ".png",
                                    "exportedFileName": name, "deviceId": device_id, "isAssociatedWithFailure": False})
            manifest = [{"testIdentifier": m.TARGET + "/" + m.SELECTOR + "()", "attachments": attachments}]
            c.write(directory / "manifest.json", manifest)
            proof = m.screenshots(c, directory, device_id, base)
            assert set(proof["screenshots"]) == {"before_reopen", "after_reopen"} and proof["visualReview"] == "PENDING"
            bad = copy.deepcopy(manifest)
            bad[0]["attachments"][1]["deviceId"] = "00000000-0000-4000-8000-000000000002"
            (directory / "manifest.json").write_text(json.dumps(bad) + "\n")
            rejected(lambda: m.screenshots(c, directory, device_id, base))
            (directory / "manifest.json").write_text(json.dumps([
                {"testIdentifier": manifest[0]["testIdentifier"], "attachments": attachments[:1]}
            ]) + "\n")
            rejected(lambda: m.screenshots(c, directory, device_id, base))
            return {"syntheticPNGOnly": True, "wrongDeviceAndMissingImageRejected": True, "visualAcceptance": False}

        control("screenshots_require_both_original_phases_and_same_device", images)

    if not results:
        raise ValueError("No named portable control was selected")
    result = {"status": "PASS_PORTABLE_RTL_PREPARATION_NOT_APPLE_ACCEPTANCE" if all(row["status"] == "PASS" for row in results) else "FAIL",
              "controls": results, "passed": sum(row["status"] == "PASS" for row in results), "failed": sum(row["status"] == "FAIL" for row in results),
              "sharedUtilityControllerSHA256": args.shared_controller_sha256, "originalHelperClosure": closure,
              "nativeRTLHelperSHA256": sha((args.control_root / "native_rtl_matrix.py").read_bytes()),
              "nativeUIProfileSHA256": sha((args.control_root / "native16_profile.py").read_bytes()),
              "sourceProofSHA256": sha(args.source_proof.read_bytes()), "AppleCommands": 0,
              "validationScriptSHA256": sha(Path(__file__).read_bytes()), "onlyControl": args.only_control,
              "builds": 0, "XCTestMethodsExecuted": 0, "actualMatrixCellsExecuted": 0, "nativeCalls": 0,
              "physicalDevice": "NOT_RUN"}
    if args.output.exists():
        raise ValueError("Portable control output must be fresh")
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "passed", "failed", "AppleCommands", "actualMatrixCellsExecuted")}))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
