"""Closed NativeUI source/product profile for the original App15 build.

This validates the original complete NativeUI source and reversible project.
It performs no compilation, simulator operation, application change, or test.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = "379ca3568f247d2fc218ed63df24796d461713c0"
NATIVE = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
ASSEMBLY = "c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231"
PROFILE = {
    "name": "qualified-mobile8ac-sdk9565-torah9058",
    "nativeSHA256": "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763",
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
INTEGRATED_HISTORY = {'allOriginalHistoryAssertionsUnchanged': True, 'compiledSHA256': '2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca', 'inputRoute': 'real-keyboard-with-original-native-UIKit-range-witness', 'longPressMenuAccepted': False, 'originalSHA256': '6c4064014253837e4738b1c143f45f9af91746c53b3b665439e65f55bc837a77', 'reviewSHA256': '27925f01b2a7817435637517793c19d49db9a6814caef6e33b88dafb6beb2117', 'reviewedPreparationCommit': '6c398307682073f31f9fb59af59f34c96003d542', 'sourceAlreadyIntegrated': True, 'sourceCommit': '379ca3568f247d2fc218ed63df24796d461713c0'}
ALTERNATIVE_BINDINGS = (
    "archiveGrabberPreparation",
    "miniAppsCrossAppFixture", "integratedMiniAppsFixture",
    "binContextPreparation", "currentMiniAppsMenuFixture",
    "current410bFixture", "current410bBinConfirmationFixture", "current11619Fixture",
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
            "original_App15_complete_build_required")
    require(record.get("sourceCommit") == SOURCE
            and record.get("assemblyReceiptSHA256") == ASSEMBLY
            and record.get("inputs", {}).get("nativeSourceManifestSHA256") == NATIVE,
            "exact_App15_source_and_native_assembly_required")
    require(record.get("controllerSHA256") == PRODUCER_SHA
            and record.get("inputs", {}).get("stagingReceiptSHA256") == STAGING_SHA,
            "exact_App15_original_producer_and_staging_required")
    for key, value in PROFILE.items():
        if key != "name":
            require(record["inputs"].get(key) == value, "App15_dependency_changed:" + key)
    for phase in ("app", "ui"):
        require(record.get(phase, {}).get("exitCode") == 0
                and record[phase].get("status") == "PASS_BUILD_EXIT_0",
                "both_original_App15_build_phases_required")


def check_source(source):
    for name, expected in SOURCE_FILES.items():
        path = source / name
        require(path.is_file() and not path.is_symlink()
                and source in path.resolve().parents and sha(path.read_bytes()) == expected,
                "exact_original_App15_NativeUI_input_required:" + name)


def bind_source(source, record, runner_origin, launch, history, arguments):
    qualify_main(record)
    require(runner_origin == SOURCE
            and all(arguments.get(key) is None for key in OVERLAY_ARGUMENTS),
            "App15_requires_complete_same_source_NativeUI_without_overlays")
    check_source(source)
    require(launch == (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
            and history == (source / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
            "App15_all_original_NativeUI_bytes_required")
    require(launch.count(MARKER) == 1
            and sha(launch.split(MARKER)[1]) == FIXTURE["miniAppsMethodSectionSHA256"],
            "App15_original_MiniApps_assertions_required")
    return dict(FIXTURE)


def admit(source, main_record, ui_build, ui_record):
    qualify_main(main_record)
    require(ui_record.get("sourceCommit") == ui_record.get("runnerSourceCommit") == SOURCE
            and ui_record.get("status") == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
            and ui_record.get("testsExecuted") == 0
            and ui_record.get("reviewedInputProfile") == PROFILE,
            "exact_App15_NativeUI_build_required")
    check_source(source)
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("current8acFixture") ==
            projection.get("current8acFixture") == FIXTURE
            and projection.get("mainSourceCommit") == projection.get("runnerSourceCommit") == SOURCE
            and projection.get("reviewedInputProfile") == PROFILE
            and projection.get("changedOriginalMethodAssertions") == 0
            and projection.get("applicationBuildTargets") == projection.get("nativeLibraryBuilds") == 0
            and projection.get("allOriginalNativeUITestMethodsCompiled") is True,
            "complete_same_source_App15_NativeUI_projection_required")
    require(ui_record.get("historyKeyboardPreparation") ==
            projection.get("historyKeyboardPreparation") == INTEGRATED_HISTORY,
            "App15_exact_already_integrated_History_binding_required")
    require(all(ui_record.get(key) is None and projection.get(key) is None
                for key in ALTERNATIVE_BINDINGS),
            "App15_disallows_other_source_derivatives")
    helper = source / "Tools/AnyEnginePort/native_ui_transition_project.py"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("original_App15_NativeUI_projection", helper)
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
            "exact_original_App15_complete_project_and_sources_required")
    for name, raw in raw_files.items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink()
                and ui_build in path.resolve().parents and path.read_bytes() == raw,
                "compiled_App15_NativeUI_source_changed:" + name)
    return dict(FIXTURE)

# The original producer deliberately reused the unchanged physical compiler path.
# This closed resolver admits that exact recorded layout; it is not a path alias.
WORKSPACE = Path("/Users/m1/development/anytype-d-active-20261125")
WARM_SOURCE = WORKSPACE / "main14/source"
MAIN_EVIDENCE = WORKSPACE / "main15/build15"
PRODUCER_SHA = "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68"
STAGING_SHA = "dc0617be03813129b76a09a347c15f835611e6520f4f261825abacab16a71781"
RUNTIME_HELPER_SHA = "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0"
OWNED_OUTCOMES_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"


def file_sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(raw)
    return result.hexdigest()


def qualify_runtime_inputs(source, evidence, record):
    """Independently requalify the original producer's inputs; zero engine calls."""
    qualify_main(record)
    require(source == WARM_SOURCE and evidence == MAIN_EVIDENCE
            and source.is_absolute() and source.resolve() == source
            and evidence.resolve() == evidence
            and record["inputs"].get("sourceRoot") == str(source)
            and record["inputs"].get("appDerived") ==
                str(WORKSPACE / "main14/app-derived"),
            "exact_recorded_App15_warm_source_and_evidence_required")
    stage_path = evidence.parent / "source-staging1/receipt.json"
    stage_raw = stage_path.read_bytes()
    require(sha(stage_raw) == STAGING_SHA, "original_App15_staging_receipt_changed")
    stage = json.loads(stage_raw)
    require(stage.get("status") ==
                "PASS_EXACT_APP15_SOURCE_AND_NATIVE_MATERIALIZED_ORIGINALS_RETAINED"
            and stage.get("sourceCommit") == SOURCE
            and stage.get("sourceRoot") == str(source)
            and stage.get("appDerived") == record["inputs"]["appDerived"],
            "exact_original_App15_staging_identity_required")
    helper = source / "Tools/PinkhaDualEngineRuntime/runtime_identity.py"
    helper_raw = helper.read_bytes()
    require(sha(helper_raw) == RUNTIME_HELPER_SHA, "original_runtime_identity_helper_changed")
    module = type(sys)("App15_NativeUI_runtime_identity")
    module.__file__ = str(helper)
    exec(compile(helper_raw, str(helper), "exec"), module.__dict__)
    manifest = (source / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json").read_bytes()
    require(sha(manifest) == NATIVE, "actual_permission_manifest_changed")
    retained = evidence.parent / "native-materialization-8ac"
    pins = {
        "simulator": ("946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b",
                      "efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903"),
        "device": ("c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208",
                   "fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546"),
    }
    inputs = {}
    for kind, (receipt_sha, command_sha) in pins.items():
        values = {key: (retained / kind / name).read_bytes()
                  for key, name in (("receipt", "receipt.json"),
                                    ("command", "combined-gomobile-bind.command.json"),
                                    ("log", "combined-gomobile-bind.log"))}
        receipt = json.loads(values["receipt"])
        command = json.loads(values["command"])
        require([row for row in receipt["commands"]
                 if row["name"] == "combined-gomobile-bind"] == [command],
                "original_unique_native_bind_command_required:" + kind)
        inputs[kind] = dict(values, expectedReceiptSHA256=receipt_sha,
                           expectedCommandSHA256=command_sha)
    result = module.qualify_application(
        manifest, "2026-11-26",
        (source / "Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift").read_bytes(),
        inputs)
    assembly_raw = (retained / "receipt.json").read_bytes()
    require(sha(assembly_raw) == ASSEMBLY, "actual_8ac_assembly_changed")
    assembly = json.loads(assembly_raw)
    require(assembly["status"] == "PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
            and result["identity"] == assembly["runtimeIdentity"],
            "actual_native_and_consumer_identity_must_agree")
    for kind, identifier in (("simulator", "ios-arm64-simulator"), ("device", "ios-arm64")):
        binary = source / "Dependencies/Middleware/Lib.xcframework" / identifier / "Lib.framework/Lib"
        require(file_sha(binary) == result["slices"][kind]["binarySHA256"] ==
                    assembly["inputs"][kind]["binarySHA256"]
                and binary.stat().st_size == result["slices"][kind]["binaryBytes"] ==
                    assembly["inputs"][kind]["binaryBytes"],
                "actual_original_native_framework_changed:" + kind)
    proofs = {}
    for stage in ("before", "after-app", "after-ui"):
        raw = (evidence / ("runtime-identity-" + stage + ".json")).read_bytes()
        require(json.loads(raw) == result, "original_runtime_proof_differs:" + stage)
        proofs[stage] = {"bytes": len(raw), "sha256": sha(raw)}
    return {"nativeSourceManifestSHA256": NATIVE, "assemblyReceiptSHA256": ASSEMBLY,
            "stagingReceiptSHA256": STAGING_SHA, "producerSHA256": PRODUCER_SHA,
            "runtimeHelperSHA256": RUNTIME_HELPER_SHA,
            "runtimeIdentity": result["identity"], "originalRuntimeProofs": proofs}


def owned_lifecycle(source, root, directory):
    path = source / ("Tools/CurrentAppleValidation/combined_heart_semantics/build14/"
                     "combined_heart_semantics_owned_outcomes.py")
    original = path.read_bytes()
    require(sha(original) == OWNED_OUTCOMES_SHA, "exact_owned_outcomes_73bb_required")
    module = type(sys)("App15_NativeUI_owned_outcomes")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    return module.Commands(directory, root)
