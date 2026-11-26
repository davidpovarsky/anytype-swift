"""Closed NativeUI source/product profile for the original App14 build.

This validates the original complete NativeUI source and reversible project.
It performs no compilation, simulator operation, application change, or test.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
NATIVE = "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
ASSEMBLY = "a27b5f2f955d85b31157d7aedf7733e7d32e0acdac59920c0bd142ed304484bd"
PROFILE = {
    "name": "qualified-mobile11619-sdk9565-torah9058",
    "nativeSHA256": "9f64b4469e221cd27b04c0f46b7479cf1fb079b36fce8a26c0fd8b0521ecaf5e",
    "sdkReceiptSHA256": "b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150",
    "lockSHA256": "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd",
}
SOURCE_FILES = {
    "NativeApp/UITests/NativeLaunchTests.swift":
        "f7056f6f64144dffb9bca8420f543cf7ec78b2cc1b502e40b6c56abdc9dc0e95",
    "NativeApp/UITests/NativeHistoryTests.swift":
        "2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca",
    "NativeApp/AnyNative.xcodeproj/project.pbxproj":
        "7282befe3104df28a3e0f5feef05a018bc515c68cf443307de65dbe977e33532",
    "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme":
        "f208c605b78e849e18defc7c759f3588dc9ab9b3f3bdd7502257c605da9db308",
    "Tools/AnyEnginePort/native_ui_transition_project.py":
        "3c666726a42f9e42b481f82e45d90362079c0c0ff062192e4b5c3461ea1f02ec",
}
FIXTURE = {
    "sourceCommit": SOURCE,
    "originalSHA256": SOURCE_FILES["NativeApp/UITests/NativeLaunchTests.swift"],
    "compiledSHA256": SOURCE_FILES["NativeApp/UITests/NativeLaunchTests.swift"],
    "historySHA256": SOURCE_FILES["NativeApp/UITests/NativeHistoryTests.swift"],
    "miniAppsMethodSectionSHA256":
        "cef7734232b8f12ff432a97b435a5c6e0801d2cd77a30ce097e83f5e1cf40a63",
    "sourceAlreadyIntegrated": True,
    "allOriginalMethodAssertionsUnchanged": True,
    "testStorageOverrides": False,
    "actualCompanionRequired": True,
    "ordinaryAccountSelectionAfterColdCallback": True,
    "binPreparation": "real-unique-confirmation-sheet-and-leaf-button",
    "nativeSourceManifestSHA256": NATIVE,
}
ALTERNATIVE_BINDINGS = (
    "historyKeyboardPreparation", "archiveGrabberPreparation",
    "miniAppsCrossAppFixture", "integratedMiniAppsFixture",
    "binContextPreparation", "currentMiniAppsMenuFixture",
    "current410bFixture", "current410bBinConfirmationFixture",
)
OVERLAY_ARGUMENTS = (
    "history_source_commit", "archive_source_commit", "miniapps_source_commit",
    "bin_source_commit", "miniapps_menu_source_commit",
    "bin_confirmation_source_commit",
)
MARKER = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def qualify_main(record):
    require(record.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and record.get("sourceUnchanged") is True and record.get("testsExecuted") == 0,
            "original_App14_complete_build_required")
    require(record.get("sourceCommit") == SOURCE
            and record.get("assemblyReceiptSHA256") == ASSEMBLY
            and record.get("inputs", {}).get("nativeSourceManifestSHA256") == NATIVE,
            "exact_App14_source_and_native_assembly_required")
    for key, value in PROFILE.items():
        if key != "name":
            require(record["inputs"].get(key) == value, "App14_dependency_changed:" + key)
    for phase in ("app", "ui"):
        require(record.get(phase, {}).get("exitCode") == 0
                and record[phase].get("status") == "PASS_BUILD_EXIT_0",
                "both_original_App14_build_phases_required")


def check_source(source):
    for name, expected in SOURCE_FILES.items():
        path = source / name
        require(path.is_file() and not path.is_symlink()
                and source in path.resolve().parents and sha(path.read_bytes()) == expected,
                "exact_original_App14_NativeUI_input_required:" + name)


def bind_source(source, record, runner_origin, launch, history, arguments):
    qualify_main(record)
    require(runner_origin == SOURCE
            and all(arguments.get(key) is None for key in OVERLAY_ARGUMENTS),
            "App14_requires_complete_same_source_NativeUI_without_overlays")
    check_source(source)
    require(launch == (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
            and history == (source / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
            "App14_all_original_NativeUI_bytes_required")
    require(launch.count(MARKER) == 1
            and sha(launch.split(MARKER)[1]) == FIXTURE["miniAppsMethodSectionSHA256"],
            "App14_original_MiniApps_assertions_required")
    return dict(FIXTURE)


def admit(source, main_record, ui_build, ui_record):
    qualify_main(main_record)
    require(ui_record.get("sourceCommit") == ui_record.get("runnerSourceCommit") == SOURCE
            and ui_record.get("status") == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
            and ui_record.get("testsExecuted") == 0
            and ui_record.get("reviewedInputProfile") == PROFILE,
            "exact_App14_NativeUI_build_required")
    check_source(source)
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("current11619Fixture") ==
            projection.get("current11619Fixture") == FIXTURE
            and projection.get("mainSourceCommit") == projection.get("runnerSourceCommit") == SOURCE
            and projection.get("reviewedInputProfile") == PROFILE
            and projection.get("changedOriginalMethodAssertions") == 0
            and projection.get("applicationBuildTargets") == projection.get("nativeLibraryBuilds") == 0
            and projection.get("allOriginalNativeUITestMethodsCompiled") is True,
            "complete_same_source_App14_NativeUI_projection_required")
    require(all(ui_record.get(key) is None and projection.get(key) is None
                for key in ALTERNATIVE_BINDINGS),
            "App14_disallows_other_source_derivatives")
    helper = source / "Tools/AnyEnginePort/native_ui_transition_project.py"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("original_App14_NativeUI_projection", helper)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    project, transformation = original.project_bytes(
        (source / "NativeApp/AnyNative.xcodeproj/project.pbxproj").read_bytes())
    scheme = original.scheme_bytes((source /
        "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme").read_bytes())
    raw_files = {
        "source/" + original.PROJECT_NAME + "/project.pbxproj": project,
        "source/" + original.PROJECT_NAME + "/xcshareddata/xcschemes/" +
            original.SCHEME_NAME + ".xcscheme": scheme,
        "source/UITests/NativeLaunchTests.swift":
            (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes(),
        "source/UITests/NativeHistoryTests.swift":
            (source / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
    }
    expected = {name: {"bytes": len(raw), "sha256": sha(raw)}
                for name, raw in raw_files.items()}
    require(projection.get("sourceFiles") == expected
            and projection.get("exactOriginalProjectAndScheme") == transformation,
            "exact_original_App14_complete_project_and_sources_required")
    for name, raw in raw_files.items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink()
                and ui_build in path.resolve().parents and path.read_bytes() == raw,
                "compiled_App14_NativeUI_source_changed:" + name)
    return dict(FIXTURE)
