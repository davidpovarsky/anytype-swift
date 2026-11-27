#!/usr/bin/env python3
"""Source-bound hosted App + complete UI build using the original App16 producer.

No command here executes UI tests, creates an account or performs distribution.
The two manual routes are explicitly different: original native input export on
the retained owner Mac, and a fresh hosted build that consumes that exact export.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import traceback
import zipfile

sys.dont_write_bytecode = True
import native_inputs as native


REPOSITORY = "davidpovarsky/anytype-swift"
DEVELOPER = "/Applications/Xcode_27.0.0.app/Contents/Developer"
ORIGINAL_SHA = "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
ORIGINAL_COMMIT = "204f8fbb25c3b21f419fc1a8818eb46ed492e561"
ADAPTER_SHA = "47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd"
LIFECYCLE_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
LIFECYCLE_PATH = "Tools/CurrentAppleValidation/combined_heart_semantics/build14/combined_heart_semantics_owned_outcomes.py"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
BRIDGE = "Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift"
NATIVE_MANIFEST = "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json"
RUNTIME = "Tools/PinkhaDualEngineRuntime/runtime_identity.py"
SDK_MARKER = "Dependencies/Hanlin/.pinkha-source.json"
GIB = 1024 ** 3
FLOOR = 2 * GIB
PHASE_GROWTH = {"app": 16 * GIB, "ui": 2 * GIB}
CONCURRENT = 512 * 1024 ** 2
PACK_GROWTH = 8 * GIB
EXTERNAL_HOSTED_TESTS = (
    "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeDocumentPublicationTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextBlockCreationTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextTypographyTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentIntentStoreTests.swift",
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentMetadataTests.swift",
)
# Exact reviewed composition: published50 synchronized + UIKit2 + mounted1 + published9 external.
# This is source membership, never runtime or final native acceptance.
COMPOSED_NATIVE_SOURCE_PATHS = frozenset(('AnyTypeTests/Pinkha/AnyHanlinAtomicSaveBodyTests.swift', 'AnyTypeTests/Pinkha/AnyHanlinWriteApprovalTests.swift', 'AnyTypeTests/Pinkha/AnyNativeAttachmentMountedRecoveryTests.swift', 'AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift', 'AnyTypeTests/Pinkha/ChatAutoFollowTests.swift', 'AnyTypeTests/Pinkha/ChatScrollViewHandleTests.swift', 'AnyTypeTests/Pinkha/HanlinHostAdapterTests.swift', 'AnyTypeTests/Pinkha/HanlinHostCancellationTests.swift', 'AnyTypeTests/Pinkha/HanlinHostReadWriteTests.swift', 'AnyTypeTests/Pinkha/HanlinHostWriteTests.swift', 'AnyTypeTests/Pinkha/HanlinMessageSaveIntentTests.swift', 'AnyTypeTests/Pinkha/HanlinNativeAcceptancePreparationTests.swift', 'AnyTypeTests/Pinkha/HanlinOriginalMessageProjectionTests.swift', 'AnyTypeTests/Pinkha/HanlinSDKConsumerTests.swift', 'AnyTypeTests/Pinkha/HanlinSaveMessageConsentLayoutTests.swift', 'AnyTypeTests/Pinkha/HanlinSaveMessageJournalTests.swift', 'AnyTypeTests/Pinkha/HanlinSaveMessageRouterTests.swift', 'AnyTypeTests/Pinkha/HanlinSaveMessageWorkerTests.swift', 'AnyTypeTests/Pinkha/HanlinSelectionAcceptancePreparationTests.swift', 'AnyTypeTests/Pinkha/PinkhaBootstrapStateManagerTests.swift', 'AnyTypeTests/Pinkha/PinkhaHanlinHeartSaveBodyTests.swift', 'AnyTypeTests/Pinkha/PinkhaHanlinSaveMessageConversionTests.swift', 'AnyTypeTests/Pinkha/PinkhaHanlinSaveMessageStateTests.swift', 'AnyTypeTests/Pinkha/PinkhaMiniAppsNativePreparationTests.swift', 'AnyTypeTests/Pinkha/PinkhaNativeTextAcknowledgementTests.swift', 'AnyTypeTests/Pinkha/PinkhaNavigationGestureBridgeTests.swift', 'AnyTypeTests/Pinkha/PinkhaStage1AcceptancePreparationTests.swift', 'AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerAdapterTests.swift', 'AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerTests.swift', 'AnyTypeTests/Pinkha/PinkhaTextDirectionPersistenceTests.swift', 'AnyTypeTests/Pinkha/PinkhaTextDirectionUIKitAdapterTests.swift', 'AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift', 'AnyTypeTests/Pinkha/PropertyCreationSelectionTests.swift', 'AnyTypeTests/Pinkha/SDK06PendingSelectionTag.swift', 'AnyTypeTests/Pinkha/SemanticAnchorPage154MountedPreparationTests.swift', 'AnyTypeTests/Pinkha/SemanticAnchorPage154NativeAcceptanceTests.swift', 'AnyTypeTests/Pinkha/SimpleTableTextPersistenceTests.swift', 'AnyTypeTests/Pinkha/SimulatorAcceptancePreparationTests.swift', 'AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift', 'AnyTypeTests/Pinkha/TextViewLinkGestureArbitrationTests.swift', 'AnyTypeTests/Pinkha/TorahAssociationNativeMiddlewareProbeTests.swift', 'AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift', 'AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift', 'AnyTypeTests/Pinkha/TorahNativeUIParityTests.swift', 'AnyTypeTests/Pinkha/TorahQuoteInsertionTests.swift', 'AnyTypeTests/Pinkha/TorahRelatedDocumentActionTests.swift', 'AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift', 'AnyTypeTests/Pinkha/TorahSearchLayoutTests.swift', 'AnyTypeTests/Pinkha/TorahSearchResolutionPublicationTests.swift', 'AnyTypeTests/Pinkha/TorahT5NativePaginationTests.swift', 'AnyTypeTests/Pinkha/TorahT5RuntimePairTests.swift', 'AnyTypeTests/Pinkha/TorahT5UIAcceptancePreparationTests.swift', 'AnyTypeTests/Pinkha/TorahWave1IntegrationTests.swift', 'Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeDocumentPublicationTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentIntentStoreTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentMetadataTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextBlockCreationTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextTypographyTests.swift', 'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift'))
COMPOSED_STAGE1_SOURCE_PATHS = frozenset(('PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/HanlinNativeAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/HanlinSaveMessageAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/HanlinSelectionAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/PinkhaTorahQuoteAcceptanceUITests.swift', 'PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift'))
ORIGINAL_UIKIT23_PROJECTED_SOURCES = {'AnyTypeTests/Pinkha/ChatScrollViewHandleTests.swift': {'bytes': 36674, 'sha256': 'c2530c97736ef2dbc0dacae33bd60d04737083d14272cc5338f56298cd3a5311'}, 'AnyTypeTests/Pinkha/ChatAutoFollowTests.swift': {'bytes': 17723, 'sha256': '89e2be629ab5a50addc1bdc81668e5bd971f13d2c74e54222baaa8bc80f4c12e'}}

NATIVE_PINS = {
    "runtimeIdentityHelperSHA256": native.RUNTIME_SHA,
    "nativeSourceManifestSHA256": native.MANIFEST_SHA,
    "nativeAssemblyReceiptSHA256": native.ASSEMBLY_SHA,
    "nativeFrameworkInventorySHA256": native.FRAMEWORK_SHA,
    "simulatorReceiptSHA256": native.SLICE_PINS["simulator"][0],
    "simulatorCommandSHA256": native.SLICE_PINS["simulator"][1],
    "deviceReceiptSHA256": native.SLICE_PINS["device"][0],
    "deviceCommandSHA256": native.SLICE_PINS["device"][1],
    "nativeSimulatorBinarySHA256": native.SLICE_PINS["simulator"][2],
}

require, sha = native.require, native.sha


def write(path, value):
    path = Path(path)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def ref(path):
    return {"path": str(Path(path)), "sha256": sha(path)}


def exact(value, size, label):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(size) + "}", value),
            "Exact immutable " + label + " required")
    return value


def command(argv, *, cwd=None, env=None, timeout=120):
    return subprocess.run(argv, cwd=cwd, env=env, timeout=timeout, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def git(source, *args):
    return command(["git", "--no-replace-objects", "-C", str(source), *args]).decode()


def source_identity(source, expected_commit, expected_tree):
    source = Path(source)
    require(source.is_dir() and source.resolve() == source, "Physical source checkout required")
    state = {"commit": git(source, "rev-parse", "HEAD").strip(),
             "tree": git(source, "rev-parse", "HEAD^{tree}").strip(),
             "status": git(source, "status", "--porcelain", "--untracked-files=all"),
             "root": git(source, "rev-parse", "--show-toplevel").strip()}
    require(state == {"commit": expected_commit, "tree": expected_tree, "status": "", "root": str(source)},
            "Exact clean compiled source identity differs")
    return state


def control_identity(control, commit):
    require(git(control, "rev-parse", "HEAD").strip() == commit
            and git(control, "status", "--porcelain", "--untracked-files=all") == "",
            "Executed control checkout is not the exact clean immutable commit")
    prefix = "Tools/PinkhaDualEngineRuntime/hosted_shared_build/"
    paths = [p for p in git(control, "ls-files", "-z", prefix).split("\0") if p.endswith(".py")]
    require({prefix + name for name in ("run.py", "native_inputs.py", "retain.py")}.issubset(paths),
            "Complete executed hosted control files required")
    rows = {}
    for name in paths:
        data = command(["git", "--no-replace-objects", "-C", str(control), "show", commit + ":" + name])
        row = native.regular(control / name)
        require(row["sha256"] == hashlib.sha256(data).hexdigest() and row["bytes"] == len(data),
                "Executed controller bytes differ from immutable Git source")
        rows[name] = {k: row[k] for k in ("bytes", "sha256")}
    return {"commit": commit, "tree": git(control, "rev-parse", "HEAD^{tree}").strip(), "files": rows}


def validate_compiler_inputs(inputs):
    """File-only finite source admission; no count-only widening or subprocess."""
    require(type(inputs) is dict and set(inputs) == {"native", "ui"},
            "Only the complete original native and Stage1 compiler inputs are admitted")
    for kind, expected in (("native", COMPOSED_NATIVE_SOURCE_PATHS), ("ui", COMPOSED_STAGE1_SOURCE_PATHS)):
        rows = inputs[kind]
        require(type(rows) is dict and set(rows) == expected,
                "The exact reviewed compiler source membership differs: " + kind)
        for path, row in rows.items():
            native.safe_relative(path)
            require(type(row) is dict and set(row) == {"bytes", "sha256"}
                    and type(row["bytes"]) is int and row["bytes"] > 0,
                    "Exact original source byte/hash record required")
            exact(row["sha256"], 64, "selected source hash")
    require(all(inputs["native"][path] == pin for path, pin in ORIGINAL_UIKIT23_PROJECTED_SOURCES.items()),
            "The two canonical UIKit test files must retain the exact reviewed import-only projection")
    return {"native": len(inputs["native"]), "stage1UI": len(inputs["ui"]), "native23UI": 2}


def selected_sources(source):
    all_paths = git(source, "ls-files", "-z").split("\0")
    native_paths = sorted(p for p in all_paths if p.startswith("AnyTypeTests/Pinkha/") and p.endswith(".swift"))
    native_paths += list(EXTERNAL_HOSTED_TESTS)
    ui_paths = sorted(p for p in all_paths if p.startswith("PinkhaStage1Acceptance/") and p.endswith(".swift"))
    require(native_paths and ui_paths and set(EXTERNAL_HOSTED_TESTS).issubset(all_paths), "Original hosted test sources missing")
    require(len(native_paths) == len(set(native_paths)) and set(native_paths) == COMPOSED_NATIVE_SOURCE_PATHS
            and len(ui_paths) == len(set(ui_paths)) and set(ui_paths) == COMPOSED_STAGE1_SOURCE_PATHS,
            "Actual tracked source names differ from the exact reviewed62/10 composition")
    return {"native": {p: {k: native.regular(Path(source) / p)[k] for k in ("bytes", "sha256")} for p in native_paths},
            "ui": {p: {k: native.regular(Path(source) / p)[k] for k in ("bytes", "sha256")} for p in ui_paths}}


def validate_plan(plan, control_commit, *, export=False):
    require(plan["schema"] == "pinkha-hosted-original-shared-build-plan-v1", "Unsupported hosted plan")
    require(plan["readyForExport" if export else "readyForBuild"] is True, "Root must finalize the exact plan")
    require(plan["controlCommit"] == exact(control_commit, 40, "control commit"), "Executed controls differ from root plan")
    exact(plan["appSourceSHA"], 40, "App source")
    exact(plan["appSourceTree"], 40, "App tree")
    exact(plan["hanlinRevision"], 40, "canonical SDK source")
    require(plan["repository"] == REPOSITORY and plan["nativeBuildDate"] == "2026-11-26", "Wrong original source scope")
    for key, value in NATIVE_PINS.items():
        require(plan["pins"][key] == value, "This route only admits original native8ac: " + key)
    require(plan["originalProducerCommit"] == ORIGINAL_COMMIT and plan["originalProducerSHA256"] == ORIGINAL_SHA
            and plan["compilerProofAdapterSHA256"] == ADAPTER_SHA, "Original producer lineage differs")
    for key, value in plan["pins"].items():
        exact(value, 64, key)
    require(plan["toolchain"] == {"developerDir": DEVELOPER, "xcodeVersion": "Xcode 27.0\nBuild version 27A266a",
                                "simulatorSDKBuild": "24A430", "swiftIdentity": "swiftlang-6.4.0.34.1 clang-2100.3.34.1"},
            "Exact original Xcode/Swift/SDK identity required")
    require(plan["resourcePolicy"] == {"phaseGrowthAllowanceBytes": PHASE_GROWTH, "emergencyFloorBytes": FLOOR,
                                      "concurrentGrowthAllowanceBytes": CONCURRENT, "jobs": 4,
                                      "phaseTimeoutSeconds": 7200, "resultArchiveAllowanceBytes": PACK_GROWTH},
            "Reviewed cold hosted resource policy differs")
    for kind in ("native", "ui"):
        rows = plan["compilerInputs"][kind]
        require(rows and len(rows) <= 500, "Complete bounded compiler selection required")
        for path, row in rows.items():
            native.safe_relative(path)
            require(path.endswith(".swift") and isinstance(row["bytes"], int) and row["bytes"] > 0, "Invalid selected source")
            exact(row["sha256"], 64, "selected source hash")
    if export:
        exact(plan["exportAppSourceSHA"], 40, "retained export App source")
        exact(plan["exportAppSourceTree"], 40, "retained export App tree")
        require(set(plan["exportInputs"]) == {"appSource", "materialization", "framework", "nativeSource"},
                "Exact original native export input roles required")
        for value in plan["exportInputs"].values():
            require(isinstance(value, str) and Path(value).is_absolute() and ".." not in Path(value).parts,
                    "Absolute original export input path required")
    else:
        require(validate_compiler_inputs(plan["compilerInputs"])
                == {"native": 62, "stage1UI": 10, "native23UI": 2},
                "Complete reviewed compiler composition required before build admission")
        item = plan["nativeArtifact"]
        for key in ("id", "runID", "runAttempt", "zipBytes", "payloadBytes"):
            require(type(item[key]) is int and item[key] > 0, "Concrete native artifact field required: " + key)
        require(item["zipBytes"] <= 4 * GIB and item["payloadBytes"] <= 4 * GIB, "Native archive transport bound exceeded")
        for key in ("zipSHA256", "payloadSHA256", "payloadManifestSHA256"):
            exact(item[key], 64, key)
        exact(item["producerCommit"], 40, "native export control commit")
        require(re.fullmatch(r"Pinkha-Native8ac-Inputs-[0-9]+-[0-9]+", item["name"]), "Exact native artifact name required")
    return plan


def read_plan(path, expected_sha, control, *, export=False):
    exact(expected_sha, 64, "root plan hash")
    require(sha(path) == expected_sha, "Root plan bytes differ")
    data = json.loads(Path(path).read_bytes())
    control_identity(control, os.environ["GITHUB_SHA"])
    return validate_plan(data, os.environ["GITHUB_SHA"], export=export)


def load_adapter(control):
    path = Path(control) / "Tools/PinkhaDualEngineRuntime/wave3_shared_build.py"
    require(sha(path) == ADAPTER_SHA, "Original compiler-proof adapter differs")
    spec = importlib.util.spec_from_file_location("hosted_original_wave3", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hosted_cold_qualification():
    # This function is copied into the expanded original producer. It has no
    # dependency on this controller's mutable Python module or global state.
    w3_require(WAVE3_ADMISSION["hostedColdBuild"] is True, "Fresh hosted intake required")
    stage_path = pathlib.Path(WAVE3_ADMISSION["sourceStaging"]["path"])
    cache_path = pathlib.Path(WAVE3_ADMISSION["cacheQualification"]["path"])
    for path, key in ((stage_path, "sourceStaging"), (cache_path, "cacheQualification")):
        w3_require(sha(path) == WAVE3_ADMISSION[key]["sha256"], "Hosted intake receipt changed")
    stage, cache = json.loads(stage_path.read_bytes()), json.loads(cache_path.read_bytes())
    w3_require(stage["status"] == "PASS_FRESH_HOSTED_SOURCE_NATIVE_AND_SDK_NOT_BUILT"
               and stage["sourceCommit"] == EXPECTED and stage["sourceRoot"] == str(SOURCE)
               and stage["appDerived"] == str(APP_DERIVED), "Hosted staging identity differs")
    w3_require(cache["status"] == "PASS_EMPTY_HOSTED_COMPILER_PATHS_NOT_BUILT"
               and cache["sourceCommit"] == EXPECTED and cache["stageReceiptSHA256"] == sha(stage_path)
               and cache["phaseGrowthAllowanceBytes"] == PHASE_GROWTH
               and cache["emergencyFloorBytes"] == FLOOR
               and cache["concurrentGrowthAllowanceBytes"] == CONCURRENT_GROWTH
               and cache["applicationBuilds"] == 0 and cache["testsExecuted"] == 0,
               "Cold hosted resource qualification differs")
    for name, path in (("appDerived", APP_DERIVED), ("uiDerived", ROOT / "ui-derived")):
        w3_require(cache["observedPaths"][name] == {"path": str(path), "exists": False, "symlink": False}
                   and not path.exists() and not path.is_symlink(), "Hosted compiler path is not fresh")
    w3_require(shutil.disk_usage(ROOT).free >= FLOOR + PHASE_GROWTH["app"] + CONCURRENT_GROWTH,
               "Cold App estimate, concurrent allowance and live emergency floor are unavailable")
    write(EVIDENCE / "cache-requalification.json", dict(cache, receiptSHA256=sha(cache_path),
                                                       freshFreeBytes=shutil.disk_usage(ROOT).free))


def hosted_baseline(lock, sdk, native_binary):
    return {"freeBytes": shutil.disk_usage(ROOT).free,
            "memsize": subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True).stdout.strip(),
            "cpus": subprocess.run(["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, check=True).stdout.strip(),
            "vmStat": subprocess.run(["vm_stat"], capture_output=True, text=True, check=True).stdout,
            "reasonForJobs4": "Original bounded four-job producer on the separately observed hosted ARM64 runner; no Mac warm-cache claim.",
            "phaseGrowthAllowanceBytes": PHASE_GROWTH, "concurrentGrowthAllowanceBytes": CONCURRENT_GROWTH,
            "phaseBudgetEvidence": WAVE3_ADMISSION["hostedResourceRationale"],
            "lockSHA256": sha(lock), "sdkReceiptSHA256": sha(sdk), "nativeSHA256": sha(native_binary),
            "nativeSourceManifestSHA256": WAVE3_ADMISSION["pins"]["nativeSourceManifestSHA256"],
            "stagingReceiptSHA256": WAVE3_ADMISSION["sourceStaging"]["sha256"],
            "cacheRequalificationReceiptSHA256": WAVE3_ADMISSION["cacheQualification"]["sha256"],
            "originalIntermediatesAndPackagePathsReused": False, "hostedColdBuild": True,
            "sourceRoot": str(SOURCE), "appDerived": str(APP_DERIVED)}


def hosted_package_closure(stage):
    lock = SOURCE / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    pins = json.loads(lock.read_bytes())["pins"]
    expected = {row["identity"].casefold(): row["state"]["revision"] for row in pins}
    w3_require(len(expected) == len(pins), "Duplicate original package pin identity")
    checkouts = APP_DERIVED / "SourcePackages/checkouts"
    w3_require(checkouts.is_dir() and not checkouts.is_symlink(), "Actual resolved package checkouts required")
    observed = {}
    for path in sorted(checkouts.iterdir()):
        w3_require(path.is_dir() and not path.is_symlink(), "Unexpected package checkout")
        identity = path.name.casefold()
        head = subprocess.run(["git", "--no-replace-objects", "-C", str(path), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "--no-replace-objects", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
                                capture_output=True, text=True, check=True).stdout
        w3_require(identity in expected and head == expected[identity] and status == "",
                   "Actual package revision or untracked source differs: " + identity)
        observed[identity] = {"path": str(path), "commit": head, "status": status}
    w3_require(set(observed) == set(expected), "Complete locked package source closure required")
    write(EVIDENCE / ("package-checkouts-" + stage + ".json"),
          {"status": "PASS_EXACT_LOCKED_CLEAN_PACKAGE_CHECKOUTS_NOT_TEST_EXECUTION", "lockSHA256": sha(lock),
           "checkouts": observed, "testsExecuted": 0})


def expand(base, adapter, admission, admission_path, adapter_sha):
    original, previous = adapter.expand_controller(base, admission, admission_path, sha(admission_path), adapter_sha)
    candidate, changes = original, []

    def replace(old, new, count=1):
        nonlocal candidate
        require(candidate.count(old) == count and old != new, "Original producer shape changed")
        candidate = candidate.replace(old, new)
        changes.append({"old": old, "new": new, "count": count})

    replace('SOURCE=ROOT.parent/"main14/source"', "SOURCE=pathlib.Path(" + repr(admission["sourceRoot"]) + ")")
    replace('APP_DERIVED=ROOT.parent/"main14/app-derived"', "APP_DERIVED=pathlib.Path(" + repr(admission["appDerived"]) + ")")
    replace('DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"', "DEVELOPER_DIR=" + repr(DEVELOPER))
    replace('PHASE_GROWTH={"app":int(6*1024**3),"ui":int(1*1024**3)}', "PHASE_GROWTH=" + repr(PHASE_GROWTH))
    first = ' assert sha(pathlib.Path(' + repr(admission["sourceStaging"]["path"]) + '))=='
    start = candidate.index(first)
    end = candidate.index(' before=source_state()\n', start)
    replace(candidate[start:end], " hosted_cold_qualification()\n")
    start = candidate.index(' baseline={"freeBytes":')
    end = candidate.index('\n write(EVIDENCE/"input-and-resource-admission.json",baseline)', start)
    replace(candidate[start:end], " baseline=hosted_baseline(lock,sdk,native)")
    replace(' verify_dependencies("after-app")\n', ' verify_dependencies("after-app")\n hosted_package_closure("after-app")\n')
    replace(' verify_dependencies("after-ui")\n', ' verify_dependencies("after-ui")\n hosted_package_closure("after-ui")\n')
    helper_source = Path(__file__).read_text()
    functions = [ast.get_source_segment(helper_source, node) for node in ast.parse(helper_source).body
                 if isinstance(node, ast.FunctionDef) and node.name in ("hosted_cold_qualification", "hosted_baseline", "hosted_package_closure")]
    require(len(functions) == 3, "Hosted intake helpers missing")
    marker = "try:\n w3_control_admission()\n"
    replace(marker, "\n\n".join(functions) + "\n\n" + marker)
    inverse = candidate
    for row in reversed(changes):
        require(inverse.count(row["new"]) == row["count"], "Ambiguous hosted byte inverse")
        inverse = inverse.replace(row["new"], row["old"])
    require(inverse == original, "Hosted delta does not restore Wave3 expansion")
    for row in reversed(previous["changes"]):
        require(inverse.count(row["new"]) == row["count"], "Ambiguous original byte inverse")
        inverse = inverse.replace(row["new"], row["old"])
    require(inverse == base and hashlib.sha256(inverse.encode()).hexdigest() == ORIGINAL_SHA,
            "Hosted inverse does not restore every original producer byte")
    identical = [node.name for node in ast.parse(base).body if isinstance(node, ast.FunctionDef)]
    for name in identical:
        # Runtime/dependency pin and path substitutions are explicit in the
        # Wave3 delta. Scheduling, source snapshot and original compiler check
        # functions remain byte-identical to the unexpanded original.
        if name in ("run_phase", "source_state", "verify_new_test_compiler_inputs"):
            require(adapter.function_source(candidate, name) == adapter.function_source(base, name),
                    "Original function changed: " + name)
    compile(candidate, "<hosted-original-producer>", "exec")
    return candidate, {"schema": "pinkha-hosted-producer-full-byte-inverse-v1", "originalCommit": ORIGINAL_COMMIT,
                       "originalSHA256": ORIGINAL_SHA, "wave3Inverse": previous, "hostedChanges": changes,
                       "expandedSHA256": hashlib.sha256(candidate.encode()).hexdigest(),
                       "inverseRestoresEveryOriginalByte": True,
                       "byteIdenticalOriginalFunctions": ["run_phase", "source_state", "verify_new_test_compiler_inputs"],
                       "builds": 0, "tests": 0}


def record_toolchain(root, plan):
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Native hosted ARM64 Mac required")
    require(os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted", "A GitHub-hosted runner is required")
    require(os.environ.get("DEVELOPER_DIR") == DEVELOPER, "Exact selected Xcode environment required")
    out = root / "toolchain"
    out.mkdir()
    rows = []
    observations = (("xcode-version", ["xcodebuild", "-version"]),
                    ("swift-version", ["xcrun", "swift", "--version"]),
                    ("simulator-sdk-build", ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version"]))
    values = {}
    for name, argv in observations:
        data = command(argv, timeout=60)
        path = out / (name + ".txt")
        path.write_bytes(data)
        values[name] = data.decode().strip()
        rows.append({"name": name, "argv": argv, "exitCode": 0, **ref(path)})
    require(values["xcode-version"] == plan["toolchain"]["xcodeVersion"]
            and values["simulator-sdk-build"] == plan["toolchain"]["simulatorSDKBuild"]
            and plan["toolchain"]["swiftIdentity"] in values["swift-version"], "Actual hosted toolchain differs")
    result = {"status": "PASS_EXACT_ORIGINAL_TOOLCHAIN_NOT_BUILD_ACCEPTANCE", "observations": rows,
              "developerDir": DEVELOPER, "machine": platform.machine(), "system": platform.platform(),
              "runner": {key: os.environ.get(key) for key in ("RUNNER_ENVIRONMENT", "RUNNER_NAME", "RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion")}}
    write(out / "receipt.json", result)
    return ref(out / "receipt.json")


def gh_json(endpoint, destination):
    raw = command(["gh", "api", "--method", "GET", endpoint], timeout=60)
    require(len(raw) <= 2 * 1024 ** 2, "GitHub metadata response bound exceeded")
    destination.write_bytes(raw)
    return json.loads(raw)


def download_native(root, item):
    folder = root / "native-download"
    folder.mkdir()
    run = gh_json(f"repos/{REPOSITORY}/actions/runs/{item['runID']}/attempts/{item['runAttempt']}", folder / "run.original.json")
    artifact = gh_json(f"repos/{REPOSITORY}/actions/artifacts/{item['id']}", folder / "artifact.original.json")
    require(run["id"] == item["runID"] and run["run_attempt"] == item["runAttempt"]
            and run["head_sha"] == item["producerCommit"] and run["status"] == "completed"
            and run["conclusion"] == "success" and run["repository"]["full_name"] == REPOSITORY,
            "Original native export workflow is not the admitted successful attempt")
    require(artifact["id"] == item["id"] and artifact["name"] == item["name"]
            and artifact["workflow_run"]["id"] == item["runID"]
            and artifact["workflow_run"]["head_sha"] == item["producerCommit"]
            and artifact["expired"] is False and artifact["size_in_bytes"] == item["zipBytes"]
            and artifact["digest"] == "sha256:" + item["zipSHA256"], "Exact native artifact metadata differs")
    zipped = folder / "artifact.zip"
    with zipped.open("xb") as output:
        p = subprocess.run(["gh", "api", "--method", "GET", f"repos/{REPOSITORY}/actions/artifacts/{item['id']}/zip"],
                           stdout=output, stderr=subprocess.PIPE, timeout=600)
    require(p.returncode == 0, "Original native artifact download failed")
    require(zipped.stat().st_size == item["zipBytes"] and sha(zipped) == item["zipSHA256"], "Downloaded artifact bytes differ")
    payload = folder / native.PAYLOAD_NAME
    with zipfile.ZipFile(zipped) as archive:
        members = archive.infolist()
        require(len(members) == 1 and members[0].filename == native.PAYLOAD_NAME
                and members[0].file_size == item["payloadBytes"] and not members[0].is_dir()
                and stat.S_IFMT(members[0].external_attr >> 16) in (0, stat.S_IFREG), "Unexpected native transport ZIP member")
        with archive.open(members[0]) as source, payload.open("xb") as target:
            shutil.copyfileobj(source, target, 1024 ** 2)
    require(payload.stat().st_size == item["payloadBytes"] and sha(payload) == item["payloadSHA256"], "Native payload differs")
    destination = root / "original-native-inputs"
    result = native.read_payload(payload, expected_manifest=item["payloadManifestSHA256"], destination=destination)
    proof = {"status": "PASS_EXACT_ORIGINAL_NATIVE8AC_ARTIFACT_TRANSPORT_NOT_APP_ACCEPTANCE", "artifact": item,
             "run": ref(folder / "run.original.json"), "metadata": ref(folder / "artifact.original.json"),
             "archive": ref(zipped), "payload": ref(payload), "payloadClosure": result,
             "destination": str(destination), "nativeBuildsNow": 0, "testsExecuted": 0}
    write(root / "native-transport-receipt.json", proof)
    return destination


def native23_module():
    path = Path(__file__).with_name("native23_build.py")
    require(sha(path) == "9d6d8410507955d340ffc7c6fceb52477965ec8ec380255dce7d936b30fb643d",
            "Exact separately reviewed Native23 compiler helper required")
    name = "pinkha_hosted_native23_compiler"
    require(name not in sys.modules, "Native23 compiler module name is already occupied")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def stage_and_build(args, root, plan, control, source, hanlin):
    controls = control_identity(control, plan["controlCommit"])
    write(root / "controls-before.json", controls)
    native23 = native23_module()
    native23_intake = native23.preflight(sys.modules[__name__], args, root, plan, control, source)
    toolchain = record_toolchain(root, plan)
    before = source_identity(source, plan["appSourceSHA"], plan["appSourceTree"])
    require(selected_sources(source) == plan["compilerInputs"], "Complete current native/UI source enumeration differs")
    require(sha(source / LOCK) == plan["pins"]["packageResolvedSHA256"], "Original full App lock differs")
    sdk_pin = json.loads((source / "Tools/Hanlin/source.json").read_bytes())
    require(sha(source / "Tools/Hanlin/source.json") == plan["pins"]["sdkSourcePinSHA256"]
            and sdk_pin["revision"] == plan["hanlinRevision"]
            and sdk_pin["repository"] == "https://github.com/davidpovarsky/hanlin-ai.git",
            "Canonical source pin differs")
    require(git(hanlin, "rev-parse", "HEAD").strip() == plan["hanlinRevision"]
            and git(hanlin, "status", "--porcelain", "--untracked-files=all") == "", "Canonical checkout differs")
    require(shutil.disk_usage(root).free >= FLOOR + PHASE_GROWTH["app"] + CONCURRENT
            + 2 * plan["nativeArtifact"]["zipBytes"] + native.MAX_UNPACKED_BYTES,
            "Cold compiler estimate plus bounded native intake cannot fit")
    native_root = download_native(root, plan["nativeArtifact"])
    qualification = native.qualify(native_root / "native", native_root / "Lib.xcframework", source / NATIVE_MANIFEST,
                                   source / RUNTIME, source / BRIDGE)
    original_manifest = json.loads((source / NATIVE_MANIFEST).read_bytes())
    require(native.file_inventory(native_root / "native-source") == original_manifest["files"], "Complete original native source closure differs")
    framework = source / "Dependencies/Middleware/Lib.xcframework"
    require(not framework.exists() and not framework.is_symlink(), "Fresh native framework destination required")
    framework.parent.mkdir(parents=True, exist_ok=True)
    # A fresh checkout has no native binary. Copy only the completely admitted
    # original framework, then rehash it before the producer can compile.
    shutil.copytree(native_root / "Lib.xcframework", framework, copy_function=shutil.copy2)
    require(native.file_inventory(framework) == json.loads((native_root / "native/framework-files.json").read_bytes()),
            "Installed native framework changed")
    materializer = source / "Tools/Hanlin/prepare_sdk.py"
    require(sha(materializer) == plan["pins"]["sdkMaterializerSHA256"], "Original SDK materializer differs")
    sdk_log = root / "sdk-materialization.log"
    compiler_env = dict(os.environ)
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        compiler_env.pop(key, None)
    with sdk_log.open("xb") as log:
        result = subprocess.run([sys.executable, "-B", str(materializer), "--source", str(hanlin)],
                                cwd=source, env=compiler_env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    require(result.returncode == 0 and sha(source / SDK_MARKER) == plan["pins"]["sdkMaterializationReceiptSHA256"],
            "Exact original SDK materialization failed")
    require(source_identity(source, plan["appSourceSHA"], plan["appSourceTree"]) == before, "Source changed during intake")
    source_inputs = root / "source-inputs"
    source_inputs.mkdir()
    lifecycle = control / LIFECYCLE_PATH
    require(sha(lifecycle) == LIFECYCLE_SHA, "Original owned process lifecycle helper differs")
    shutil.copy2(lifecycle, source_inputs / lifecycle.name)
    derived = root / "app-derived"
    stage_path, cache_path = root / "source-staging.json", root / "cold-cache-qualification.json"
    write(stage_path, {"status": "PASS_FRESH_HOSTED_SOURCE_NATIVE_AND_SDK_NOT_BUILT", "sourceCommit": plan["appSourceSHA"],
                       "sourceTree": plan["appSourceTree"], "sourceRoot": str(source), "appDerived": str(derived),
                       "compilerInputs": plan["compilerInputs"], "nativeArtifactTransport": ref(root / "native-transport-receipt.json"),
                       "nativeQualification": qualification, "sdkReceiptSHA256": sha(source / SDK_MARKER),
                       "toolchain": toolchain, "rootPlan": ref(args.plan), "applicationBuilds": 0, "testsExecuted": 0})
    observed = {name: {"path": str(path), "exists": path.exists(), "symlink": path.is_symlink()}
                for name, path in (("appDerived", derived), ("uiDerived", root / "ui-derived"))}
    require(all(not row["exists"] and not row["symlink"] for row in observed.values()), "Fresh compiler paths required")
    write(cache_path, {"status": "PASS_EMPTY_HOSTED_COMPILER_PATHS_NOT_BUILT", "sourceCommit": plan["appSourceSHA"],
                       "stageReceiptSHA256": sha(stage_path), "observedPaths": observed,
                       "phaseGrowthAllowanceBytes": PHASE_GROWTH, "emergencyFloorBytes": FLOOR,
                       "concurrentGrowthAllowanceBytes": CONCURRENT, "freeBytes": shutil.disk_usage(root).free,
                       "applicationBuilds": 0, "testsExecuted": 0})
    admission = {"schema": "pinkha-root-frozen-build-admission-v1", "readyForBuild": True,
                 "appSourceSHA": plan["appSourceSHA"], "sourceRoot": str(source), "appDerived": str(derived),
                 "buildRoot": str(root), "nativeMaterializationRoot": str(native_root / "native"),
                 "nativeBuildDate": plan["nativeBuildDate"], "pins": plan["pins"],
                 "selectedNativeTestSources": list(plan["compilerInputs"]["native"]),
                 "selectedUITestSources": list(plan["compilerInputs"]["ui"]),
                 "sourceStaging": ref(stage_path), "cacheQualification": ref(cache_path),
                 "originalRetention": ref(root / "native-transport-receipt.json"), "toolchainIntake": toolchain,
                 "rootPlan": ref(args.plan), "hostedColdBuild": True,
                 "hostedResourceRationale": plan["resourceRationale"]}
    admission_path = root / "root-derived-build-admission.json"
    write(admission_path, admission)
    adapter = load_adapter(control)
    original = control / "Tools/PinkhaDualEngineRuntime/build_wave2_app16_compiler_qualified.py"
    require(sha(original) == ORIGINAL_SHA, "Original App16 producer differs")
    candidate, inverse = expand(original.read_text(), adapter, admission, admission_path, sha(Path(__file__)))
    producer = root / "hosted-original-producer.py"
    producer.write_text(candidate)
    write(root / "producer-full-byte-inverse.json", inverse)
    # No retry and no detached queue. Original run_phase owns each compiler's
    # process group and keeps its 7200-second deadline and live disk floor.
    with (root / "producer.stdout.log").open("xb") as log:
        process = subprocess.run([sys.executable, "-B", str(producer), plan["appSourceSHA"]],
                                 env=compiler_env, stdout=log, stderr=subprocess.STDOUT, check=False)
    write(root / "producer-exit.json", {"exitCode": process.returncode, "producer": ref(producer),
                                       "sourceCommit": plan["appSourceSHA"], "testsExecuted": 0})
    require(process.returncode == 0, "Original App/UI producer failed; preserve its original result")
    after_controls = control_identity(control, plan["controlCommit"])
    write(root / "controls-after.json", after_controls)
    require(after_controls == controls, "Executed control bytes changed during compilation")
    receipt = json.loads((root / "build16/receipt.json").read_bytes())
    require(receipt["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and receipt["sourceCommit"] == plan["appSourceSHA"] and receipt["testsExecuted"] == 0,
            "Original terminal compilation receipt missing")
    write(root / "hosted-receipt.json", {"status": "PASS_HOSTED_ORIGINAL_APP_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE",
                                        "originalBuildReceipt": ref(root / "build16/receipt.json"), "toolchain": toolchain,
                                        "rootPlan": ref(args.plan), "controlCommit": plan["controlCommit"],
                                        "appSourceSHA": plan["appSourceSHA"], "testsExecuted": 0,
                                        "releaseArchive": False, "testFlightUploaded": False})
    native23.build(sys.modules[__name__], args, root, plan, control, source, compiler_env, native23_intake)


def execute(args):
    control, source, hanlin, root = (Path(value).resolve() for value in (args.control, args.source, args.hanlin, args.output))
    plan = read_plan(args.plan, args.plan_sha256, control)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Original repository runner context required")
    require(root.parent == Path(os.environ["RUNNER_TEMP"]).resolve()
            and root.name == "pinkha-hosted-shared-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"],
            "Fresh run-owned hosted output required")
    root.mkdir(mode=0o700, exist_ok=False)
    try:
        stage_and_build(args, root, plan, control, source, hanlin)
    except BaseException as error:
        try:
            write(root / "hosted-failure.json", {"status": "FAIL_OR_NOT_RUN", "type": type(error).__name__,
                                                "reason": str(error), "traceback": traceback.format_exc(),
                                                "time": time.time(), "appSourceSHA": plan["appSourceSHA"],
                                                "testsExecuted": 0, "releaseArchive": False, "testFlightUploaded": False})
        except BaseException as receipt_error:
            error.add_note("Original hosted failure receipt also failed: " + repr(receipt_error))
        raise


def export_native(args):
    control, root = Path(args.control).resolve(), Path(args.output).resolve()
    plan = read_plan(args.plan, args.plan_sha256, control, export=True)
    require(os.environ.get("RUNNER_ENVIRONMENT") == "self-hosted"
            and os.environ.get("RUNNER_NAME") == "pinkha-scaleway-mac", "Existing owner Mac export route required")
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
            and root.parent == Path(os.environ["RUNNER_TEMP"]).resolve()
            and root.name == "pinkha-native8ac-export-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"],
            "Fresh run-owned original export output required")
    require(not root.exists(), "Fresh original export directory required")
    paths = {k: Path(v) for k, v in plan["exportInputs"].items()}
    source_identity(paths["appSource"], plan["exportAppSourceSHA"], plan["exportAppSourceTree"])
    qualification = native.qualify(paths["materialization"], paths["framework"], paths["appSource"] / NATIVE_MANIFEST,
                                   paths["appSource"] / RUNTIME, paths["appSource"] / BRIDGE)
    files = native.payload_sources(paths["materialization"], paths["framework"], paths["nativeSource"], paths["appSource"] / NATIVE_MANIFEST)
    needed = sum(p.stat().st_size for p in files.values()) + FLOOR
    require(shutil.disk_usage(root.parent).free >= needed, "A single bounded original input archive plus live floor cannot fit")
    root.mkdir(mode=0o700)
    write(root / "source-paths-before.json", {name: {"originalPath": str(path), **native.regular(path)} for name, path in files.items()})
    receipt = native.pack(files, root / native.PAYLOAD_NAME, qualification)
    source_identity(paths["appSource"], plan["exportAppSourceSHA"], plan["exportAppSourceTree"])
    write(root / "receipt.json", dict(receipt, rootPlan=ref(args.plan), controlCommit=plan["controlCommit"]))


def inspect_plan(args):
    raw = os.environ["PINKHA_HOSTED_PLAN"].encode()
    require(len(raw) <= 60000 and hashlib.sha256(raw).hexdigest() == args.plan_sha256, "Exact bounded root plan input required")
    path = Path(args.plan)
    with path.open("xb") as stream:
        stream.write(raw)
    plan = read_plan(path, args.plan_sha256, Path(args.control).resolve(), export=args.export)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write("source_sha=" + plan["appSourceSHA"] + "\n")
        stream.write("hanlin_sha=" + plan["hanlinRevision"] + "\n")


def make_draft(args):
    """Portable source-only plan; false-ready until actual export is admitted."""
    source, sdk = Path(args.source).resolve(), Path(args.hanlin).resolve()
    commit = exact(args.source_commit, 40, "draft compiled source")
    require(git(source, "rev-parse", commit + "^{commit}").strip() == commit, "Original App commit objects missing")
    tree = git(source, "rev-parse", commit + "^{tree}").strip()
    def blob(path):
        return command(["git", "--no-replace-objects", "-C", str(source), "show", commit + ":" + path])
    def blob_sha(path):
        return hashlib.sha256(blob(path)).hexdigest()
    paths = git(source, "ls-tree", "-r", "--name-only", "-z", commit).split("\0")
    native_paths = sorted(p for p in paths if p.startswith("AnyTypeTests/Pinkha/") and p.endswith(".swift")) + list(EXTERNAL_HOSTED_TESTS)
    ui_paths = sorted(p for p in paths if p.startswith("PinkhaStage1Acceptance/") and p.endswith(".swift"))
    compiler_inputs = {}
    for kind, selected in (("native", native_paths), ("ui", ui_paths)):
        compiler_inputs[kind] = {}
        for path in selected:
            data = blob(path)
            compiler_inputs[kind][path] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    validate_compiler_inputs(compiler_inputs)
    pins = json.loads(blob("Tools/Hanlin/source.json"))
    require(git(sdk, "rev-parse", pins["revision"] + "^{commit}").strip() == pins["revision"], "Exact original SDK objects required")
    archive = command(["git", "--no-replace-objects", "-C", str(sdk), "archive", "--format=tar", pins["revision"], *pins["packages"]])
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for member in bundle:
            native.safe_relative(member.name.rstrip("/"))
            require(member.isfile() or member.isdir(), "Unexpected canonical package node")
            if member.isfile():
                data = bundle.extractfile(member).read()
                require(not data.startswith(b"version https://git-lfs.github.com/spec/v1"), "SDK source needs LFS materialization")
                files[member.name] = hashlib.sha256(data).hexdigest()
    # Match prepare_sdk.hashes() exactly: pathlib sorts path components, which
    # differs from sorting raw strings when a directory and file share a prefix.
    ordered = {name: files[name] for name in sorted(files, key=Path)}
    marker = (json.dumps({"revision": pins["revision"], "files": ordered}, indent=2) + "\n").encode()
    actual_pins = dict(NATIVE_PINS, packageResolvedSHA256=blob_sha(LOCK),
                       sdkSourcePinSHA256=blob_sha("Tools/Hanlin/source.json"),
                       sdkMaterializerSHA256=blob_sha("Tools/Hanlin/prepare_sdk.py"),
                       sdkMaterializationReceiptSHA256=hashlib.sha256(marker).hexdigest(),
                       uiGeneratorSHA256=blob_sha("Tools/PinkhaNativeDerived/rerun_original_ui.py"),
                       page154UITestSHA256=blob_sha("PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"))
    plan = {"schema": "pinkha-hosted-original-shared-build-plan-v1", "repository": REPOSITORY,
            "readyForBuild": False, "readyForExport": False, "controlCommit": args.control_commit,
            "appSourceSHA": commit, "appSourceTree": tree, "hanlinRevision": pins["revision"],
            "nativeBuildDate": "2026-11-26", "originalProducerCommit": ORIGINAL_COMMIT,
            "originalProducerSHA256": ORIGINAL_SHA, "compilerProofAdapterSHA256": ADAPTER_SHA,
            "pins": actual_pins, "compilerInputs": compiler_inputs,
            "toolchain": {"developerDir": DEVELOPER, "xcodeVersion": "Xcode 27.0\nBuild version 27A266a",
                          "simulatorSDKBuild": "24A430", "swiftIdentity": "swiftlang-6.4.0.34.1 clang-2100.3.34.1"},
            "resourcePolicy": {"phaseGrowthAllowanceBytes": PHASE_GROWTH, "emergencyFloorBytes": FLOOR,
                               "concurrentGrowthAllowanceBytes": CONCURRENT, "jobs": 4,
                               "phaseTimeoutSeconds": 7200, "resultArchiveAllowanceBytes": PACK_GROWTH},
            "resourceRationale": {"kind": "CONSERVATIVE_COLD_ESTIMATE_NOT_MEASURED_HOSTED_PEAK",
                                  "retainedMacAllocatedBytes": {"intermediates": 3670495232, "products": 2973990912,
                                                               "sdkModules": 1403154432, "sourcePackages": 5391351808},
                                  "appAllowanceBytes": PHASE_GROWTH["app"], "uiAllowanceBytes": PHASE_GROWTH["ui"],
                                  "note": "Fresh hosted checkout and all compiler/package paths. Prior retained allocations inform the estimate only. No old warm peak or old build success is transferred."},
            "nativeArtifact": None, "exportInputs": None,
            "remainingPrerequisites": ["Root final compiled source and control commit selection", "One verified original native8ac export artifact and exact transport metadata", "Fresh hosted toolchain and resource admission"]}
    plan["native23Compiler"] = native23_module().declared_plan()
    write(args.output, plan)


def dispatch_body(raw, reference, route):
    """Prepare JSON only; preserve the exact plan newline without shell expansion."""
    require(route in ("wave3-native8ac-export", "wave3-hosted-shared-build"), "Closed original route required")
    require(re.fullmatch(r"[A-Za-z0-9_./-]+", reference) and ".." not in reference and "//" not in reference,
            "Explicit existing GitHub branch or tag required")
    plan = json.loads(raw)
    validate_plan(plan, plan["controlCommit"], export=route == "wave3-native8ac-export")
    return {"ref": reference, "inputs": {"route": route, "shared_build_plan_json": raw.decode("utf-8"),
                                         "shared_build_plan_sha256": hashlib.sha256(raw).hexdigest()}}


def dispatch_request(args):
    require(sha(args.plan) == args.plan_sha256, "Reviewed dispatch plan bytes differ")
    write(args.output, dispatch_body(args.plan.read_bytes(), args.ref, args.route))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("inspect", "execute", "export"):
        p = sub.add_parser(action)
        p.add_argument("--control", required=True)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--plan-sha256", required=True)
        if action == "inspect":
            p.add_argument("--export", action="store_true")
        else:
            p.add_argument("--output", required=True)
        if action == "execute":
            p.add_argument("--source", required=True)
            p.add_argument("--hanlin", required=True)
    p = sub.add_parser("draft")
    p.add_argument("--source", required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--hanlin", required=True)
    p.add_argument("--control-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("dispatch-request")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--plan-sha256", required=True)
    p.add_argument("--ref", required=True)
    p.add_argument("--route", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"inspect": inspect_plan, "execute": execute, "export": export_native, "draft": make_draft,
     "dispatch-request": dispatch_request}[args.action](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
