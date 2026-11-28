"""Closed current-product admission for the original warm focus/editor lanes.

This is a same-host consumer of an actually completed phase-bound forward warm build. It does
not stage, resolve, compile, revive App15, or require the separate Native UI
target. The complete original common validator still admits App62/Stage1UI10.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

from originals import require

CONTROL_PREFIX = "Tools/PinkhaDualEngineRuntime/warm_focus_editor/"
SOURCE_ROOT = Path("/Users/m1/development/anytype-d-active-20261125/main14/source")
APP_DERIVED = SOURCE_ROOT.parent / "app-derived"
LOCK = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
SDK_MARKER = "Dependencies/Hanlin/.pinkha-source.json"
NATIVE_MANIFEST = "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json"
NATIVE_BINARY = "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
UI_GENERATOR = "Tools/PinkhaNativeDerived/rerun_original_ui.py"
WARM_ADAPTER_SHA256 = "181b5f3ca42943e1dc8179d16a98d63998f966212920e63c3c8a5317e98b4d75"
STAGER_SHA256 = "38644915911ae3df8fa9d7d446a7ca1e9d1bc57fd95d5f0542dd35fd3413083a"
ORIGINAL_ADAPTER_SHA256 = "47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd"
ORIGINAL_PRODUCER_SHA256 = "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c"
ORIGINAL_SUPERVISOR_SHA256 = "bd0ee535786b2a7c95b4da1b6dfdbd1b1f409438a6214cb4252d0c386cebf42e"
FOREGROUND_SHA256 = "f215726b8de42b6fa1934038ea26a8c46a27dde1d64e39afca8ac22db2dadaf4"
FOREGROUND_CUSTODY_SHA256 = "e7e630f78b3abdd1a86b7c5376c39351fa4fd01d48ecb2380137aac20cecfd6d"
ORIGINAL_NATIVE_PINS = {
    "nativeSourceManifestSHA256": "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
    "runtimeIdentityHelperSHA256": "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0",
    "simulatorReceiptSHA256": "946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b",
    "simulatorCommandSHA256": "efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903",
    "deviceReceiptSHA256": "c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208",
    "deviceCommandSHA256": "fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546",
    "nativeAssemblyReceiptSHA256": "c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231",
    "nativeFrameworkInventorySHA256": "fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf",
    "nativeSimulatorBinarySHA256": "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763",
}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(path, *, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
            "Original physical same-host path required: " + str(path))
    require(path.is_dir() if directory else path.is_file(), "Wrong original input kind")
    return path


def ref(path):
    path = canonical(path)
    return {"path": str(path), "sha256": sha(path)}


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "--no-replace-objects",
                                    "-C", str(root), *args], timeout=60).decode()


def identity(root, commit, tree=None):
    root = canonical(root, directory=True)
    value = {"root": git(root, "rev-parse", "--show-toplevel").strip(),
             "commit": git(root, "rev-parse", "HEAD").strip(),
             "tree": git(root, "rev-parse", "HEAD^{tree}").strip(),
             "status": git(root, "status", "--porcelain", "--untracked-files=all")}
    require(value["root"] == str(root) and value["commit"] == commit and value["status"] == ""
            and (tree is None or value["tree"] == tree), "Immutable clean original checkout differs")
    return value


def bind_job(args, plan):
    """A separately root-admitted SentinelX window, never a fabricated CI job."""
    require(plan["schema"] == "pinkha-forward-warm-focus-editor-runtime-plan-v1"
            and plan["readyForRuntime"] is True and plan["executionEnvironment"] == "SentinelX-owned-Mac",
            "Actual separately approved current-product runtime plan required")
    require(Path(args.source) == SOURCE_ROOT == Path(plan["sourceRoot"])
            and Path(args.control) == canonical(plan["controlRoot"], directory=True)
            and Path(args.build_root) == canonical(plan["buildRoot"], directory=True),
            "Original live source/control/build paths differ")
    root = Path(args.build_root)
    require(root.parent == SOURCE_ROOT.parent.parent and root.name.startswith("main16-wave3-forward-")
            and Path(args.output) == root / "focus-editor-runtime1"
            and Path(args.plan) == root / "focus-editor-runtime.approved.json",
            "One fresh finite current-product output/plan namespace required")
    require(plan["developerDir"] == "/Applications/Xcode.app/Contents/Developer"
            and os.environ.get("DEVELOPER_DIR") == plan["developerDir"],
            "Use the unchanged warm producer's actually observed Xcode path")
    require(plan["plans"] == ["focus-lifecycle-only", "first-editor"]
            and re.fullmatch(r"[1-9][0-9]*", plan["runtimeRunID"] or "")
            and re.fullmatch(r"[1-9][0-9]*", plan["runtimeRunAttempt"] or "")
            and plan["rootWindow"]["status"] == "ROOT_REVIEWED_FINITE_OWNER_WINDOW",
            "Explicit original plans/run identity and root-owned window required")
    require(ref(plan["rootWindow"]["evidence"]["path"]) == plan["rootWindow"]["evidence"],
            "Original current root coordination bytes changed")
    require(plan["configuration"]["deviceFamily"] == "ipad"
            and plan["configuration"]["appLanguage"] in ("en", "he")
            and plan["configuration"]["appearance"] in ("light", "dark"),
            "One explicit actual original iPad configuration required")
    return {"executionEnvironment": "SentinelX-owned-Mac", "runID": plan["runtimeRunID"],
            "runAttempt": plan["runtimeRunAttempt"], "controlCommit": plan["controlCommit"],
            "sourceRoot": str(args.source), "buildRoot": str(root),
            "developerDir": plan["developerDir"], "rootWindow": plan["rootWindow"],
            "windowIsAtomicGlobalLock": False}


def control_identity(control, commit):
    result = identity(control, commit)
    paths = [path for path in git(control, "ls-files", "-z", CONTROL_PREFIX).split("\0") if path]
    required = {CONTROL_PREFIX + name for name in ("run.py", "admission.py", "originals.py",
        "original_sources.json", "profile_binding.py", "activation.json", "source-membership.json",
        "priority-runtime-selection.closed.json")}
    require(required.issubset(paths) and all(path.startswith(CONTROL_PREFIX) for path in paths),
            "Complete reviewed finite runtime controller closure required")
    result["files"] = {}
    for path in paths:
        original = subprocess.check_output(["git", "--no-replace-objects", "-C", str(control),
                                            "show", commit + ":" + path], timeout=60)
        file = canonical(Path(control) / path)
        require(file.read_bytes() == original, "Executed runtime control differs from its immutable Git blob")
        result["files"][path] = {"bytes": len(original), "sha256": hashlib.sha256(original).hexdigest()}
    require(Path(__file__).resolve() == Path(control) / CONTROL_PREFIX / "admission.py",
            "The actual runtime adapter is outside the admitted control checkout")
    return result


def pinned(reference, expected=None):
    require(set(reference) == {"path", "sha256"} and ref(reference["path"]) == reference,
            "Exact original file reference differs")
    require(expected is None or reference["sha256"] == expected, "Reviewed original source pin differs")
    return canonical(reference["path"])


def load_warm_owner(plan, originals):
    modules = {}
    for role, expected in (("originalAdapter", ORIGINAL_ADAPTER_SHA256), ("warmAdapter", WARM_ADAPTER_SHA256),
                           ("foreground", FOREGROUND_SHA256)):
        path = pinned(plan["producerControls"][role], expected)
        name = "warm_focus_original_" + role
        require(name not in sys.modules, "A foreign module owns the exact original producer name")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        originals.modules[name] = module
        spec.loader.exec_module(module)
        modules[role] = module
    for role, expected in (("originalProducer", ORIGINAL_PRODUCER_SHA256),
                           ("stager", STAGER_SHA256), ("foregroundCustody", FOREGROUND_CUSTODY_SHA256)):
        pinned(plan["producerControls"][role], expected)
    return modules


def selected_sources(source, root_admission, stage_plan, gate):
    import profile_binding
    membership = profile_binding.source_membership()
    paths = [p for p in git(source, "ls-files", "-z").split("\0") if p]
    native = {p for p in paths if p.startswith("AnyTypeTests/Pinkha/") and p.endswith(".swift")}
    native.update(membership["externalPackageSources"])
    ui = {p for p in paths if p.startswith("PinkhaStage1Acceptance/") and p.endswith(".swift")}
    require(native == set(membership["native"]) and ui == set(membership["ui"])
            and len(native) == 62 and len(ui) == 10
            and set(membership["externalPackageSources"]).issubset(paths),
            "Actual original62/10 tracked source membership differs")
    inventory_ref = stage_plan["compilerInputInventory"]
    inventory = gate.json_ref(inventory_ref)
    require(set(inventory["selectedNativeTestSources"]) == native
            and set(inventory["selectedUITestSources"]) == ui
            and inventory["selectedNativeTestSources"] == root_admission["selectedNativeTestSources"]
            and inventory["selectedUITestSources"] == root_admission["selectedUITestSources"],
            "Root's actual compiler inventory must select every62/10 input")
    rows = {row["path"]: row for row in inventory["sources"]}
    require(len(rows) == len(inventory["sources"]) == 72 and set(rows) == native | ui,
            "Complete unique original compiler source rows required")
    for relative, row in rows.items():
        path = canonical(source / relative)
        require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                "Actual selected compiler source bytes differ: " + relative)
    proof = root_admission["compilerInputEnumeration"]
    require(proof["sourceCommit"] == root_admission["appSourceSHA"]
            and proof["sourceTree"] == stage_plan["appSourceTree"]
            and proof["sha256"] == inventory_ref["sha256"]
            and (proof["nativeCount"], proof["uiSwiftCount"]) == (62, 10),
            "Exact original compiler inventory identity differs")
    return {"inventory": inventory_ref, "native": 62, "stage1UI": 10,
            "native26UIRequired": False, "sourceRows": rows}


def foreground_context(plan, root_admission, owner, gate, root, build, build_ref):
    """Join the actual foreground producer and both full inverses; no process probe."""
    launch_ref = plan["foregroundLaunch"]
    launch = gate.json_ref(launch_ref)
    exit_ref = plan["producerExit"]
    exit_record = gate.json_ref(exit_ref)
    output = canonical(exit_record["outputRoot"], directory=True)
    normalized = lambda value: {key: value[key] for key in ("path", "sha256")}
    require(exit_record["schema"] == "pinkha-original-warm-build-whole-budget-receipt-v1"
            and exit_record["status"] == "PASS_ORIGINAL_APP_AND_STAGE1_BUILD_WITHIN_WHOLE_BUDGET_NOT_ACCEPTANCE"
            and exit_record["sourceCommit"] == plan["appSourceSHA"]
            and exit_record["buildRoot"] == str(root)
            and normalized(exit_record["plan"]) == launch_ref
            and normalized(exit_record["controller"]) == plan["producerControls"]["foreground"]
            and normalized(exit_record["custodyHelper"]) == plan["producerControls"]["foregroundCustody"]
            and normalized(exit_record["buildAdmission"]) == plan["buildAdmission"]
            and exit_record["originalExitCode"] == 0 and exit_record["producerInvocationCount"] == 1
            and exit_record["firstFailure"] is None and exit_record["secondaryErrors"] == []
            and exit_record["allKnownGroupsClosed"] is True
            and exit_record["allDirectProducerGroupsClosed"] is True
            and exit_record["commandCustodyBlocked"] is False
            and exit_record["workAdmissionClosed"] is True
            and exit_record["withinWholeOperationBudget"] is True and exit_record["alarmFired"] is False
            and exit_record["compilerPhasesStarted"] == ["app", "ui"]
            and exit_record["nativeBuilds"] == exit_record["testsExecuted"] == 0
            and exit_record["runtimeActivation"] is False and exit_record["readyForRuntime"] is False
            and exit_record["historicalProcessProbes"] == 0
            and (exit_record["activeWorkBudgetSeconds"], exit_record["foregroundOperationBudgetSeconds"],
                 exit_record["outerLauncherMaximumSeconds"]) == (3000, 3300, 3600)
            and exit_record["requiredAppAdmissionBytes"] == 9126805504 and exit_record["jobs"] == 4,
            "Actual foreground App/Stage1 terminal success and original custody are required")
    require(launch["schema"] == "pinkha-original-warm-build-whole-budget-launch-v1"
            and launch["readyForBuild"] is True and launch["runtimeActivation"] is False
            and launch["readyForRuntime"] is False and launch["sourceCommit"] == plan["appSourceSHA"]
            and launch["outputRoot"] == str(output) and Path(exit_ref["path"]) == output / "receipt.json"
            and output.parent == owner["foreground"].CONTROL_ROOT
            and re.fullmatch("whole-app-build-[a-z0-9-]+", output.name)
            and launch["maximumInvocations"] == 1
            and launch["requiredAppAdmissionBytes"] == 9126805504
            and (launch["selectedNativeSourceCount"], launch["selectedUISourceCount"]) == (62, 10)
            and normalized(launch["buildAdmission"]) == plan["buildAdmission"]
            and launch["originalControls"] == exit_record["originalControls"]
            and launch["rootWindow"] == exit_record["rootWindow"],
            "Exact current foreground launch contract differs")
    window = gate.json_ref(normalized(launch["rootWindow"]))
    require(window["schema"] == "pinkha-root-warm-app-build-window-v1"
            and window["sourceCommit"] == plan["appSourceSHA"] and window["readyForBuild"] is True
            and window["runtimeActivation"] is False and window["maximumInvocations"] == 1
            and (window["activeWorkBudgetSeconds"], window["foregroundOperationBudgetSeconds"],
                 window["outerLauncherMaximumSeconds"]) == (3000, 3300, 3600),
            "Actual finite foreground build window differs")
    for role, key in (("warmAdapter", "warm"), ("originalAdapter", "adapter"), ("originalProducer", "producer")):
        require(normalized(launch["originalControls"][key]) == plan["producerControls"][role],
                "Foreground control ancestry differs: " + role)
    for reference in launch["originalControls"].values():
        pinned(normalized(reference))
    original = pinned(plan["producerControls"]["originalProducer"], ORIGINAL_PRODUCER_SHA256)
    expanded, inverse = owner["warmAdapter"].expand(original.read_text(), root_admission,
        Path(plan["buildAdmission"]["path"]), plan["buildAdmission"]["sha256"],
        owner["originalAdapter"], WARM_ADAPTER_SHA256)
    derived, foreground_inverse = owner["foreground"].project_producer(expanded, original.read_text())
    producer = pinned(plan["executedProducer"])
    require(producer == output / "foreground-original-producer.py"
            and producer.read_text() == derived and sha(producer) == build["controllerSHA256"]
            and normalized(exit_record["foregroundProducer"]) == plan["executedProducer"]
            and normalized(exit_record["originalProducerInverse"]) == plan["producerInverse"]
            and normalized(exit_record["foregroundInverse"]) == plan["foregroundInverse"]
            and gate.json_ref(plan["producerInverse"]) == inverse
            and gate.json_ref(plan["foregroundInverse"]) == foreground_inverse,
            "Actual foreground producer or either complete original inverse differs")
    expanded_ref = normalized(exit_record["originalExpandedProducer"])
    require(Path(expanded_ref["path"]) == output / "root-approved-original-producer.py"
            and pinned(expanded_ref).read_text() == expanded,
            "The complete original warm expansion differs")
    terminal = exit_record["originalTerminalEvidence"]
    require(normalized(terminal["producer"]) == build_ref
            and [Path(row["path"]) for row in terminal["phases"]]
                == [root / "build16" / role / "result.json" for role in ("app", "ui")]
            and [normalized(row) for row in terminal["compilerProofs"]]
                == [normalized(build[key]) for key in ("nativeCompilationProof", "uiCompilationProof")]
            and normalized(terminal["completeProducts"]) == normalized(build["completeProductsInventory"]),
            "Actual foreground source/compiler/product evidence differs")
    for role, reference in zip(("app", "ui"), terminal["phases"], strict=True):
        require(gate.json_ref(normalized(reference)) == build[role],
                "Actual foreground phase receipt differs from original producer")
    for reference in terminal["compilerProofs"] + [terminal["completeProducts"]]:
        gate.read_ref(normalized(reference))
    before, after = terminal["sourceBefore"], terminal["sourceAfter"]
    require(Path(before["path"]) == root / "build16/source-before.json"
            and Path(after["path"]) == root / "build16/source-after.json"
            and before["sha256"] == build["sourceBeforeSHA256"]
            and after["sha256"] == build["sourceAfterSHA256"]
            and gate.read_ref(normalized(before)) == gate.read_ref(normalized(after)),
            "Actual foreground source before/after custody differs")
    observations = terminal["originalPhaseObservations"]
    require(len(observations) == 2, "Both actual original phase observations are required")
    phases = set()
    for reference in observations:
        value = gate.json_ref(normalized(reference))
        require(value["status"] == "PASS_COMPLETE_OBSERVATION_AND_PHASE_PREDICATES"
                and value["allKnownGroupsClosed"] is True and value["firstFailure"] is None
                and value["secondaryErrors"] == [], "A foreground phase observation is not positively closed")
        phases.add(value["phase"])
    require(phases == {"build-cache-writer", "build-resource"}, "Original phase-observation scope differs")
    index_ref = normalized(exit_record["ownedCommandIndex"])
    require(Path(index_ref["path"]) == output / "owned-producer-command-index.json",
            "Actual owned command index must belong to the foreground invocation")
    index = gate.json_ref(index_ref)
    require(index["schema"] == "pinkha-warm-build-owned-command-index-v1"
            and index["allDirectProducerGroupsClosed"] is True and index["firstFailure"] is None
            and index["historicalProcessProbes"] == 0 and index["commands"],
            "Actual foreground direct command closure is incomplete")
    for row in index["commands"]:
        require(type(row["pid"]) is int and row["pid"] > 1 and row["exitCode"] == 0
                and row["ownedGroup"] == "ABSENT_ESRCH"
                and row["status"] in ("PASS_COMMAND", "PASS_BUILD_EXIT_0"),
                "An actual foreground command is not positively closed")
        value = gate.json_ref(normalized(row["result"]))
        gate.read_ref(normalized(row["processExit"]))
        require(value["pid"] == row["pid"] == value["pgid"] and value["exitCode"] == 0
                and value["status"] == row["status"] and value["ownedProcessGroup"] == "ABSENT_ESRCH"
                and value["cleanupErrors"] == value["termination"] == []
                and value["firstFailure"] is None
                and value["processExitReceiptSHA256"] == row["processExit"]["sha256"],
                "Original foreground command result/exit evidence differs")
    return {"producer": producer, "foregroundReceipt": exit_ref,
            "foregroundLaunch": launch_ref, "ownedCommandIndex": index_ref,
            "historicalGroupsReprobed": False}


def producer_context(args, plan, originals, owner):
    gate = originals.gate
    root, source = canonical(args.build_root, directory=True), canonical(args.source, directory=True)
    runtime_plan = ref(args.plan)
    require(runtime_plan["sha256"] == args.plan_sha256, "Runtime plan bytes changed")
    stage_plan_ref = plan["sourceStagingPlan"]
    stage_plan = gate.json_ref(stage_plan_ref)
    root_ref = plan["buildAdmission"]
    root_admission = owner["originalAdapter"].load_admission(
        pinned(root_ref), root_ref["sha256"], plan["appSourceSHA"])
    owner["warmAdapter"].validate_retry(root_admission)
    require(stage_plan["schema"] == "pinkha-root-forward-warm-staging-plan-v1"
            and stage_plan["readyForStaging"] is True and stage_plan["appSourceSHA"] == plan["appSourceSHA"]
            and stage_plan["appSourceTree"] == plan["appSourceTree"]
            and stage_plan["sourceRoot"] == str(source) and stage_plan["buildRoot"] == str(root)
            and stage_plan["appDerived"] == root_admission["appDerived"] == str(APP_DERIVED)
            and stage_plan["pins"] == root_admission["pins"]
            and root_admission["buildRoot"] == str(root), "Actual a72-forward source/admission lineage differs")
    for role in ("originalAdapter", "warmAdapter"):
        require({key: stage_plan["controls"][role][key] for key in ("path", "sha256")}
                == plan["producerControls"][role], "Actual staged producer control reference differs")
    for key, expected in ORIGINAL_NATIVE_PINS.items():
        require(root_admission["pins"][key] == expected, "Only the exact original8ac assembly is admitted: " + key)
    require(root_admission["nativeBuildDate"] == "2026-11-26"
            and stage_plan["nativeMode"] == "reuse-exact-installed-qualified-input"
            and stage_plan["nativeMaterializationRoot"] == root_admission["nativeMaterializationRoot"],
            "This intermediate route cannot replace or relabel the original native input")
    source_identity = identity(source, plan["appSourceSHA"], plan["appSourceTree"])
    sdk = gate.json_ref(ref(source / "Tools/Hanlin/source.json"))
    pins = root_admission["pins"]
    require(sdk["revision"] == plan["sdkRevision"] == stage_plan["sdkRevision"]
            == root_admission["forwardWarm"]["targetSDKRevision"]
            and sdk["repository"] == "https://github.com/davidpovarsky/hanlin-ai.git"
            and sha(source / "Tools/Hanlin/source.json") == pins["hanlinSourcePinSHA256"]
            and sha(source / "Tools/Hanlin/prepare_sdk.py") == pins["sdkMaterializerSHA256"]
            and sha(source / SDK_MARKER) == pins["sdkMaterializationReceiptSHA256"]
            and sha(source / LOCK) == pins["packageResolvedSHA256"],
            "Current compiled SDK/materializer/marker/lock tuple differs")
    selected = selected_sources(source, root_admission, stage_plan, gate)
    stage_ref, cache_ref = root_admission["sourceStaging"], root_admission["cacheQualification"]
    require(Path(stage_ref["path"]) == root / "source-staging1/receipt.json"
            and Path(cache_ref["path"]) == root / "cache-requalification1/receipt.json",
            "Current forward evidence must belong to the actual build root")
    stage, cache = gate.json_ref(stage_ref), gate.json_ref(cache_ref)
    require(stage["status"] == "PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED"
            and stage["controllerSHA256"] == STAGER_SHA256 and stage["planSHA256"] == stage_plan_ref["sha256"]
            and stage["sourceCommit"] == plan["appSourceSHA"] and stage["tree"] == plan["appSourceTree"]
            and stage["priorSource"] == root_admission["forwardWarm"]["baselineSourceSHA"]
            and cache["protocol"] == "pinkha-forward-warm-cache-qualification-v1"
            and cache["stageReceiptSHA256"] == stage_ref["sha256"]
            and cache["sourceCommit"] == plan["appSourceSHA"]
            and (cache["estimateNewAppPhaseBytes"], cache["emergencyFloorBytes"],
                 cache["concurrentGrowthAllowanceBytes"]) == (6 * 1024**3, 2 * 1024**3, 512 * 1024**2)
            and cache["applicationBuilds"] == cache["testsExecuted"] == 0,
            "Original forward staging/cache evidence differs; old pre-build evidence is not current")
    require(stage["priorForwardStage"] == cache["priorForwardStage"]
            == root_admission["forwardWarm"]["priorForwardStage"], "Exact prior a72 stage chain differs")
    owner["warmAdapter"].wr_prior_forward(root_admission["forwardWarm"]["priorForwardStage"])
    baseline_ref = root_admission["forwardWarm"]["currentBaselinePreservation"]
    require(stage["currentBaselinePreservation"] == baseline_ref
            and cache["baselinePreservationSHA256"] == baseline_ref["sha256"], "Actual a72 baseline retention chain differs")
    baseline = gate.json_ref(baseline_ref)
    require(baseline["status"] == "PASS_FORWARD_BASELINE_SOURCE_PRODUCTS_AND_KIT_RETAINED"
            and baseline["sourceCommit"] == "a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd"
            and baseline["sourceMutated"] is False, "The actual a72 staged checkpoint was not retained")
    for row in baseline["trees"].values():
        canonical(row["retained"], directory=True)
        for key in ("before", "retainedManifest", "after"):
            gate.read_ref(row[key])
    gate.read_ref(root_admission["originalRetention"])
    failure = gate.json_ref(root_admission["warmRetry"]["failedPreservation"])
    require(failure["originalFailure"] == {"exitCode": 65, "uiPhaseRun": False, "applicationAccepted": False},
            "Historical6aab failure must stay separate and failed")
    build_ref = ref(root / "build16/receipt.json")
    build = gate.json_ref(build_ref)
    require(build["status"] == gate.BUILD_STATUS and build["testsExecuted"] == 0
            and build["sourceCommit"] == plan["appSourceSHA"] and build["sourceUnchanged"] is True
            and build["controlAdmission"]["admission"] == root_ref
            and build["controlAdmission"]["adapterSHA256"] == WARM_ADAPTER_SHA256,
            "Actual new App/complete-Stage1 producer PASS is required")
    for label in ("app", "ui"):
        step = build[label]
        require(step["exitCode"] == 0 and step["status"] == "PASS_BUILD_EXIT_0"
                and step["ownedProcessGroup"] == "ABSENT_ESRCH" and not step["cleanupErrors"]
                and step["sourceCommit"] == plan["appSourceSHA"]
                and step["environment"]["DEVELOPER_DIR"] == plan["developerDir"]
                and step["timeoutSeconds"] == 7200 and step["jobs"] == 4
                and sha(root / "build16" / label / "process-exit.json") == step["processExitReceiptSHA256"],
                "Original compiler outcome/custody/toolchain/budget differs")
    foreground = foreground_context(plan, root_admission, owner, gate, root, build, build_ref)
    producer = foreground["producer"]
    # Positive compiler group absence above is historical evidence: never probe
    # those PIDs again or imply that this supervisor receipt proves a lease.
    toolchain_ref = stage["toolchainIntake"]
    toolchain_original = gate.json_ref(toolchain_ref)
    require(toolchain_original["status"] == "PASS_ORIGINAL_SAME_ENVIRONMENT_TOOLCHAIN_OUTPUTS"
            and toolchain_original["developerDir"] == plan["developerDir"], "Original toolchain intake differs")
    observations = []
    for row in toolchain_original["observations"]:
        outcome = row["originalCommand"]
        log = Path(outcome["processExitReceipt"]["path"]).parent / "original.log"
        require(outcome["status"] == "PASS_COMMAND" and outcome["exitCode"] == 0
                and outcome["argv"] == row["argv"]
                and outcome["ownedGroupObservationStatus"] == "ABSENT_ESRCH"
                and not outcome["cleanupErrors"] and sha(log) == row["sha256"] == outcome["logSHA256"]
                and log.stat().st_size == row["bytes"], "Original bounded toolchain output differs")
        gate.read_ref({key: outcome["processExitReceipt"][key] for key in ("path", "sha256")})
        observations.append({"argv": row["argv"], **ref(log), "exitCode": 0})
    native_root = canonical(root_admission["nativeMaterializationRoot"], directory=True)
    require(sha(native_root / "receipt.json") == ORIGINAL_NATIVE_PINS["nativeAssemblyReceiptSHA256"]
            and sha(source / NATIVE_MANIFEST) == ORIGINAL_NATIVE_PINS["nativeSourceManifestSHA256"]
            and sha(source / NATIVE_BINARY) == ORIGINAL_NATIVE_PINS["nativeSimulatorBinarySHA256"],
            "Original8ac exact assembly/source/simulator input differs")
    return {"root": root, "source": source, "sourceIdentity": source_identity, "build": build,
            "buildRef": build_ref, "rootAdmission": root_admission, "rootAdmissionRef": root_ref,
            "producer": producer, "nativeRoot": native_root, "toolchainRef": toolchain_ref,
            "toolchain": {"observations": observations}, "planRef": runtime_plan,
            "stage": stage, "stagePlan": stage_plan, "selectedSourceProof": selected,
            "originalPackageState": cache["packageState"], "foregroundBuild": foreground}


def receipt_contract(context, output, originals, runtime, device_type):
    gate = originals.gate
    root, source, build = context["root"], context["source"], context["build"]
    base = root / "build16"
    manifest = output / "evidence/original-tools-source-manifest.json"
    originals.preparation.control_manifest(SimpleNamespace(repository=source,
        commit=context["sourceIdentity"]["commit"], output=manifest))
    product_ref = ref(base / "products-all.json")
    products = gate.json_ref(product_ref)
    descriptors = {}
    for label, target in (("app", "AnytypeTests"), ("ui", "PinkhaStage1AcceptanceUITests")):
        slot = label + "-derived"
        expected_root = (APP_DERIVED if label == "app" else root / slot) / "Build/Products"
        require(products[slot]["base"] == str(expected_root), "Actual Products do not belong to this warm producer")
        candidates = []
        for row in products[slot]["entries"]:
            if row["kind"] != "file" or not row["path"].endswith(".xctestrun"):
                continue
            try:
                originals.products.entries(expected_root / row["path"], target)
                candidates.append(row["path"])
            except (ValueError, KeyError, TypeError):
                continue
        require(len(candidates) == 1, "One actual original compiled descriptor required for " + target)
        descriptors[label] = {"slot": slot, "path": candidates[0]}
    input_paths = {
        "nativeSourceManifestSHA256": source / NATIVE_MANIFEST,
        "nativeSHA256": source / NATIVE_BINARY,
        "lockSHA256": source / LOCK,
        "sdkReceiptSHA256": source / SDK_MARKER,
        "stagingReceiptSHA256": Path(context["rootAdmission"]["sourceStaging"]["path"]),
        "cacheRequalificationReceiptSHA256": Path(context["rootAdmission"]["cacheQualification"]["path"]),
    }
    require({key for key in build["inputs"] if key.endswith("SHA256")} == set(input_paths),
            "Every original input digest must have its exact live file; unknown input needs review")
    before = gate.json_ref(ref(base / "source-before.json"))
    assembly = ref(context["nativeRoot"] / "receipt.json")
    manifest_ref, lock_ref = ref(source / NATIVE_MANIFEST), ref(source / LOCK)
    contract = {
        "schema": gate.SCHEMA,
        "source": {"root": str(source), "commit": before["commit"], "tree": before["tree"],
                   "before": ref(base / "source-before.json"), "after": ref(base / "source-after.json")},
        "controls": {"root": str(source), "commit": before["commit"], "manifest": ref(manifest)},
        "build": {"receipt": context["buildRef"], "producer": ref(context["producer"]),
                  "assembly": assembly, "uiGenerator": ref(source / UI_GENERATOR),
                  "originalUICopy": ref(base / "original-ui-copy.json"),
                  "uiCompilationProof": build["uiCompilationProof"],
                  "nativeCompilationProof": build["nativeCompilationProof"],
                  "products": product_ref, "inputs": {key: ref(path) for key, path in input_paths.items()},
                  "logs": {key: ref(base / key / "original.log") for key in ("app", "ui")}},
        "descriptors": descriptors,
        "dependencyEvidence": {
            "Hanlin": [ref(source / "Tools/Hanlin/source.json"), ref(source / SDK_MARKER), ref(base / "sdk-after-ui.log")],
            "Any": [manifest_ref, assembly, ref(base / "runtime-identity-after-ui.json")],
            "Heart": [manifest_ref, assembly, ref(base / "runtime-identity-after-ui.json")],
            "TorahInspectorKit": [lock_ref, context["rootAdmission"]["cacheQualification"],
                                  ref(output / "evidence/runtime-package-state.json")],
        },
        "runtime": {"identifier": runtime["identifier"], "version": runtime["version"],
                    "build": runtime["buildversion"], "architecture": "arm64", "family": "ipad",
                    "deviceType": device_type["identifier"]},
        "toolchain": [{"argv": row["argv"], "original": {"path": row["path"], "sha256": row["sha256"]}}
                      for row in context["toolchain"]["observations"]],
    }
    require(all(row["exitCode"] == 0 for row in context["toolchain"]["observations"]),
            "Original Apple toolchain outcome missing")
    path = output / "evidence/receipt-input.json"
    originals.shared.write(path, contract)
    admitted, proof, actual_products = gate.admit(path, sha(path))
    originals.shared.write(output / "evidence/common-original-admission.json", proof)
    return admitted, proof, actual_products, ref(path)
