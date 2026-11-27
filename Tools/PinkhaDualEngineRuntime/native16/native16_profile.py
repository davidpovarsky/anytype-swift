"""NativeUI continuation through the separately reviewed shared app admission.

The source/SDK pins come only from that exact common qualifier and admission.
Stable NativeUI bytes, the original title correction, project projection and
all original test assertions remain independently fixed here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

NATIVE = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
OWNED_OUTCOMES_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
SOURCE_FILES = {
    "NativeApp/UITests/NativeLaunchTests.swift": "e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375",
    "NativeApp/UITests/NativeHistoryTests.swift": "2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca",
    "NativeApp/AnyNative.xcodeproj/project.pbxproj": "7282befe3104df28a3e0f5feef05a018bc515c68cf443307de65dbe977e33532",
    "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme": "f208c605b78e849e18defc7c759f3588dc9ab9b3f3bdd7502257c605da9db308",
    "Tools/AnyEnginePort/native_ui_transition_project.py": "3c666726a42f9e42b481f82e45d90362079c0c0ff062192e4b5c3461ea1f02ec",
    "Tools/AnyEnginePort/native_ui_transition_contract.py": "42d56e2193643fde5ae6f329b63a123fee89a2ef22d858e3bea8aeb94cd0d3d5",
    "Tools/AnyEnginePort/verify_native_test_execution.py": "af126a59d47fec07b0d465c0077c812fb5f52cfcadf71a2da22cebb969e21b91",
    "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py": "f99b1c04efeee2be45459b49d8c71fd8207039c97be4578cd6f2dfc8d29bb283",
    "Tools/PinkhaSimulatorGate/t5_native_ui_r08.py": "f726c600bd04f77b2ca8e8b42610b6c66dfbdaf96d86cc6535eaed0218fae4ea",
    "Tools/PinkhaSimulatorGate/run_ui27.py": "87e0972ee6852d1fdb34d82afa5dde346baf836afaa8419203b647e7d3e21ca7",
    "docs/validation/20261127-wave2-native-rtl/source-proof.json": "699e0ccdb963cfd9a630b65ffce9973a5c63d440b62db7fa3aacdb34907240d5",
}
TITLE_PROOF = "docs/validation/20261126-native-sharing-rendered-title/source-proof.json"
TITLE_PROOF_SHA = "3d7bb101ac6062e486acfc1250c06498c127ef9018b528663bf18b4eb8116b19"
TITLE_ORIGINAL = "Tools/PinkhaDualEngineRuntime/native-sharing-dec2-source/NativeLaunchTests.swift"
TITLE_ORIGINAL_SHA = "0b4cbd0663162801ed09f146fd531cc225539c7a6886317f4d9021fbff345b00"
TITLE_BEFORE = '''            waitUntilEnabled(app.navigationBars.matching(labels([
                "חברים והזמנות", "Members and invitations"
            ])).firstMatch, timeout: 30)
'''.encode()
TITLE_AFTER = '''            // SwiftUI renders the navigation title as a static-text descendant;
            // the enclosing navigation bar need not carry that title as its label.
            let titles = app.navigationBars.staticTexts.matching(labels([
                "חברים והזמנות", "Members and invitations"
            ]))
            waitFor(NSPredicate { _, _ in
                let visible = titles.allElementsBoundByIndex.filter {
                    $0.exists && $0.isEnabled && $0.isHittable
                }
                return visible.count == 1
            }, object: app, timeout: 30)
            XCTAssertEqual(titles.allElementsBoundByIndex.filter {
                $0.exists && $0.isEnabled && $0.isHittable
            }.count, 1, "One visible localized members-and-invitations title is required.")
'''.encode()
OVERLAY_ARGUMENTS = (
    "runner_source_commit", "native_sharing_source_commit", "history_source_commit",
    "archive_source_commit", "miniapps_source_commit", "bin_source_commit",
    "miniapps_menu_source_commit", "bin_confirmation_source_commit", "frozen_inputs", "companion_manifest",
)
ALTERNATIVE_BINDINGS = (
    "archiveGrabberPreparation", "miniAppsCrossAppFixture", "integratedMiniAppsFixture",
    "binContextPreparation", "currentMiniAppsMenuFixture", "current410bFixture",
    "current410bBinConfirmationFixture", "current11619Fixture",
)
SOURCE = None
PROFILE = {}
FIXTURE = {}
INTEGRATED_HISTORY = {}
ORIGINAL_EVIDENCE = None
_state = None


def rtl_module():
    path = Path(__file__).with_name("native_rtl_matrix.py")
    require(path.resolve() == path and not path.is_symlink(), "Canonical reviewed RTL matrix helper required")
    raw = path.read_bytes()
    require(sha(raw) == "58c240a703a757291822073f82d84627ac5e3fedd9a0a8daf60c961a33c384ae", "Exact reviewed RTL matrix helper required")
    module = type(sys)("nativeui_verified_rtl_matrix")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def configure(args):
    global _state, SOURCE, ORIGINAL_EVIDENCE
    require(_state is None, "NativeUI context may be configured only once")
    require(all(getattr(args, name, None) is None for name in OVERLAY_ARGUMENTS),
            "Only the already integrated NativeUI source is admitted; overlays are forbidden")
    if hasattr(args, "stage"):
        require(args.stage in ("sharing-owner", "archive", "rtl") and args.retain_owned_simulator,
                "This continuation selects only missing sharing/Archive/RTL and retains its owned account")
    require(re.fullmatch(r"[0-9a-f]{64}", args.shared_controller_sha256)
            and re.fullmatch(r"[0-9a-f]{64}", args.shared_admission_sha256), "Exact shared input pins required")
    path = Path(__file__).with_name("combined_heart_semantics_current.py")
    require(path.resolve() == path and not path.is_symlink(), "Canonical shared controller required")
    raw = path.read_bytes()
    require(sha(raw) == args.shared_controller_sha256, "Reviewed shared controller changed")
    sys.dont_write_bytecode = True
    module = type(sys)("nativeui_verified_shared_controller")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    require(all(callable(getattr(module, name, None)) for name in
                ("admit_and_clone_products", "qualify_app16_producer", "qualify_app16_runtime",
                 "product_integrity", "source_admission")), "Reviewed shared admission API required")
    pin = {"path": str(args.shared_admission), "sha256": args.shared_admission_sha256,
           "bytes": args.shared_admission.stat().st_size}
    admission = module.decode(module.pinned(pin))
    require(admission.get("controllerSHA256") == args.shared_controller_sha256
            and admission.get("sourceCommit") == module.APP16_SOURCE
            and re.fullmatch(r"[0-9a-f]{40}", module.APP16_SOURCE)
            and admission.get("nativeManifestSHA256") == module.MANIFEST == NATIVE
            and "app16Producer" in admission and "sharedAdmission" not in admission,
            "Only the exact source admitted by the reviewed common qualifier is supported")
    require(args.source_root == Path(admission["sourceRoot"])
            and args.main_evidence / "receipt.json" == Path(admission["producerReceipt"]["path"]),
            "NativeUI paths must be the actual shared producer source and receipt")
    require(args.output.is_absolute() and args.output.parent.resolve() == args.output.parent
            and args.main_root in args.output.parents, "Canonical owned NativeUI output required")
    matrix = rtl_module()
    rtl_cell = getattr(args, "rtl_cell", None)
    rtl_cell_sha = getattr(args, "rtl_cell_sha256", None)
    if getattr(args, "stage", None) == "rtl":
        configuration = matrix.cell(module, rtl_cell, rtl_cell_sha)
    else:
        require(rtl_cell is None and rtl_cell_sha is None, "RTL configuration is only valid for its exact original method")
        configuration = None
    SOURCE = admission["sourceCommit"]
    ORIGINAL_EVIDENCE = args.main_evidence
    for value in (module.NATIVE_BINARY, module.SDK_RECEIPT, module.LOCK):
        require(re.fullmatch(r"[0-9a-f]{64}", value), "Exact shared dependency SHA required")
    PROFILE.update(name="qualified-shared-app-native8ac-current-sdk",
                   nativeSHA256=module.NATIVE_BINARY, sdkReceiptSHA256=module.SDK_RECEIPT,
                   lockSHA256=module.LOCK)
    FIXTURE.update(sourceCommit=SOURCE, runnerSourceCommit=SOURCE,
                   originalSHA256=SOURCE_FILES["NativeApp/UITests/NativeLaunchTests.swift"],
                   compiledSHA256=SOURCE_FILES["NativeApp/UITests/NativeLaunchTests.swift"],
                   historySHA256=SOURCE_FILES["NativeApp/UITests/NativeHistoryTests.swift"],
                   sourceAlreadyIntegrated=True, allOriginalMethodsOutsideRTLByteIdentical=True,
                   rtlOriginalHebrewAssertionsRestoreExactly=True,
                   nativeSourceManifestSHA256=NATIVE, sharingTitlePreparationSHA256=TITLE_PROOF_SHA,
                   rtlLocalizationPreparationSHA256=matrix.SOURCE_PROOF_SHA,
                   rtlLocalizationSourceChanged=True, testCompilerAppliesNoSourceOverlay=True,
                   originalSharingAttemptReceiptSHA256="df8ad97c2a146765a7ea065df49ab86a2abe55bba34897d9172d5ecff31c421f",
                   testStorageOverrides=False, originalNativeUIIsolatedAccountScope=True)
    INTEGRATED_HISTORY.update(sourceCommit=SOURCE,
        reviewedPreparationCommit="6c398307682073f31f9fb59af59f34c96003d542",
        originalSHA256="6c4064014253837e4738b1c143f45f9af91746c53b3b665439e65f55bc837a77",
        compiledSHA256=SOURCE_FILES["NativeApp/UITests/NativeHistoryTests.swift"],
        reviewSHA256="27925f01b2a7817435637517793c19d49db9a6814caef6e33b88dafb6beb2117",
        inputRoute="real-keyboard-with-original-native-UIKit-range-witness",
        longPressMenuAccepted=False, allOriginalHistoryAssertionsUnchanged=True, sourceAlreadyIntegrated=True)
    _state = dict(args=args, shared=module, admission=admission, admissionPin=pin,
                  sharedSHA=args.shared_controller_sha256, proof=None, products=None,
                  rtl=matrix, rtlCell=configuration, rtlCellSHA256=rtl_cell_sha,
                  rtlHelpers=None, rtlHelperClosure=None)


def qualify_main(record):
    require(_state is not None, "Explicit shared NativeUI context required")
    c, admission = _state["shared"], _state["admission"]
    require(c.decode(c.pinned(_state["admissionPin"])) == admission
            and c.decode(c.pinned(admission["producerReceipt"])) == record,
            "Exact immutable shared admission and actual producer receipt required")
    require(record.get("sourceCommit") == SOURCE and record.get("sourceUnchanged") is True
            and record.get("testsExecuted") == 0
            and record.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and record.get("inputs", {}).get("nativeSourceManifestSHA256") == NATIVE,
            "Current completed shared App and full UI producer required")
    for name in ("nativeSHA256", "sdkReceiptSHA256", "lockSHA256"):
        require(record["inputs"].get(name) == PROFILE[name], "Shared producer dependency differs: " + name)
    for phase in ("app", "ui"):
        require(record[phase].get("status") == "PASS_BUILD_EXIT_0" and record[phase].get("exitCode") == 0,
                "Both actual shared build phases must succeed")


def check_source(source):
    c = _state["shared"]
    for name, expected in SOURCE_FILES.items():
        path = source / name
        require(path.resolve() == path and not path.is_symlink() and c.digest(path) == expected,
                "Stable original NativeUI source changed: " + name)
    old = c.raw(source / TITLE_ORIGINAL)
    current = c.raw(source / "NativeApp/UITests/NativeLaunchTests.swift")
    matrix = _state["rtl"]
    current = matrix.qualify_source(c, current, c.raw(source / matrix.SOURCE_PROOF))
    for row in matrix.HELPERS.values():
        path = source / row["path"]
        require(path.resolve() == path and not path.is_symlink() and c.digest(path) == row["sha256"],
                "Stable original RTL validator source changed: " + row["path"])
    proof_raw = c.raw(source / TITLE_PROOF)
    proof = c.decode(proof_raw)
    require(sha(old) == TITLE_ORIGINAL_SHA and sha(proof_raw) == TITLE_PROOF_SHA
            and proof["sourceBeforeSHA256"] == sha(old) and proof["sourceAfterSHA256"] == sha(current)
            and proof["replacementBeforeSHA256"] == sha(TITLE_BEFORE)
            and proof["replacementAfterSHA256"] == sha(TITLE_AFTER)
            and old.count(TITLE_BEFORE) == current.count(TITLE_AFTER) == 1
            and current.replace(TITLE_AFTER, TITLE_BEFORE) == old,
            "The rendered-title correction must restore every original NativeUI byte")


def qualify_runtime_inputs(source, evidence, record):
    qualify_main(record)
    c, admission, args = _state["shared"], _state["admission"], _state["args"]
    require(source == args.source_root and evidence == args.main_evidence,
            "Shared producer paths differ")
    require(c.digest(Path(c.__file__)) == _state["sharedSHA"], "Reviewed common qualifier changed")
    if _state["proof"] is None:
        root = args.output.with_name(args.output.name + "-app16-intake")
        require(not root.exists() and not root.is_symlink(), "Fresh separate shared intake root required")
        root.mkdir(mode=0o700)
        ev = root / "evidence"
        ev.mkdir(mode=0o700)
        commands = c.Commands(root / "commands", root)
        proof, products, app = c.admit_and_clone_products(admission, root, ev, commands)
        c.write(ev / "shared-source-proof.json", proof)
        _state.update(proof=proof, products=products, app=app, root=root)
    require(c.qualify_app16_runtime(admission, source) == _state["proof"]["runtimeIdentity"],
            "Original current native runtime and shared boundary receipts changed")
    for kind, value in _state["products"].items():
        c.product_integrity(value)
        row = admission["products"][kind]
        require(c.inventory(Path(row["root"])) == c.decode(c.pinned(row["manifest"])),
                "Original shared producer products changed")
    before = c.decode(c.pinned(admission["sourceBefore"]))
    require(subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], timeout=60).decode().strip() == SOURCE
            and not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], timeout=60).strip(),
            "Current source must remain exact and clean")
    for name, row in before["files"].items():
        path = source / name
        require(path.resolve().is_relative_to(source) and not path.is_symlink()
                and path.stat().st_size == row["bytes"] and c.digest(path) == row["sha256"],
                "Shared source changed during NativeUI: " + name)
    check_source(source)
    return {"sourceCommit": SOURCE, "nativeSourceManifestSHA256": NATIVE,
            "sharedControllerSHA256": _state["sharedSHA"],
            "sharedAdmissionSHA256": _state["admissionPin"]["sha256"],
            "sharedSourceProof": _state["proof"], "nativeCalls": 0}


def compile_sharing_source(source, arguments):
    require(all(arguments.get(name) is None for name in OVERLAY_ARGUMENTS), "NativeUI overlays are forbidden")
    check_source(source)
    return SOURCE, (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()


def bind_source(source, record, runner_origin, launch, history, arguments):
    qualify_main(record)
    expected_origin, expected = compile_sharing_source(source, arguments)
    require(runner_origin == expected_origin and launch == expected
            and history == (source / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
            "Complete same-source original NativeUI bytes required")
    return dict(FIXTURE)


def projected_files(source):
    check_source(source)
    path = source / "Tools/AnyEnginePort/native_ui_transition_project.py"
    spec = importlib.util.spec_from_file_location("current_nativeui_original_projection", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project, transform = module.project_bytes((source / "NativeApp/AnyNative.xcodeproj/project.pbxproj").read_bytes())
    scheme = module.scheme_bytes((source / "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme").read_bytes())
    return {
        "source/" + module.PROJECT_NAME + "/project.pbxproj": project,
        "source/" + module.PROJECT_NAME + "/xcshareddata/xcschemes/" + module.SCHEME_NAME + ".xcscheme": scheme,
        "source/UITests/NativeLaunchTests.swift": (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes(),
        "source/UITests/NativeHistoryTests.swift": (source / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
    }, transform


def reviewed_builder(c):
    root = Path(__file__).parent
    path = root / "nativeui16-materialization.json"
    raw = c.raw(path)
    materialized = c.decode(raw)
    name = "build_prebuilt_native_ui16.py"
    row = materialized["controllers"][name]
    require(materialized["status"] == "PREPARED_NATIVEUI_CONTROLLERS_NOT_APP_OR_UI_ACCEPTANCE"
            and materialized["nativeUIProfileSHA256"] == c.digest(Path(__file__))
            and row["originalSHA256"] == "e6c4c506cf893b2dc495fdc4b76c686f09a108c9980e05d19590d92acab804f9"
            and row["inverseRestoresEveryOriginalByte"] is True
            and row["candidateSHA256"] == materialized["files"][name]["sha256"] == c.digest(root / name),
            "Reviewed materialized NativeUI builder and profile must agree")
    return {"builderControllerSHA256": row["candidateSHA256"], "builderMaterializationSHA256": sha(raw)}


def seal_ui_build(output, record, controller):
    """Retain actual compiler input lists and product modes after the original build."""
    c, args = _state["shared"], _state["args"]
    require(output == args.output and record["status"] == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE",
            "The original UI-only build must have succeeded")
    builder = reviewed_builder(c)
    require(controller == Path(__file__).with_name("build_prebuilt_native_ui16.py")
            and c.digest(controller) == builder["builderControllerSHA256"],
            "Actual builder is not the reviewed materialized controller")
    required = {str(output / "source/UITests" / name) for name in ("NativeLaunchTests.swift", "NativeHistoryTests.swift")}
    lists = []
    for path in sorted((output / "derived").rglob("*.SwiftFileList")):
        value = c.raw(path)
        lines = [line.strip('"') for line in value.decode().splitlines() if line]
        if not any(name in lines for name in required):
            continue
        require(set(lines) == required and len(lines) == len(required), "Exact two original NativeUI compiler inputs required")
        retained = output / "original-compiler-file-lists" / (str(len(lists)) + ".SwiftFileList")
        c.write_bytes(retained, value)
        lists.append({"path": str(path), "retained": str(retained), "bytes": len(value), "sha256": sha(value)})
    require(lists, "Actual NativeUI SwiftFileList evidence required")
    products = c.inventory(output / "derived/Build/Products")
    inventory_path = output / "native16-products-with-modes.json"
    c.write(inventory_path, products)
    c.write(output / "native16-qualified.json", {
        "status": "PASS_NATIVEUI_COMPILER_INPUTS_AND_PRODUCTS_NOT_ACCEPTANCE",
        "sourceCommit": SOURCE, "sharedControllerSHA256": _state["sharedSHA"],
        "sharedAdmissionSHA256": _state["admissionPin"]["sha256"],
        **builder, "builderReceiptSHA256": c.digest(output / "receipt.json"),
        "nativeUIProfileSHA256": c.digest(Path(__file__)), "compiledSourceFiles": SOURCE_FILES,
        "actualCompilerFileLists": lists, "productsWithModesSHA256": c.digest(inventory_path),
        "testsExecuted": 0, "applicationBuildTargets": 0, "nativeLibraryBuilds": 0})


def admit(source, main_record, ui_build, ui_record):
    qualify_main(main_record)
    c = _state["shared"]
    require(ui_record.get("sourceCommit") == ui_record.get("runnerSourceCommit") == SOURCE
            and ui_record.get("status") == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
            and ui_record.get("testsExecuted") == ui_record.get("applicationBuildTargets") == 0
            and ui_record.get("exitCode") == 0 and ui_record.get("ownedProcessGroup") == "ABSENT_ESRCH"
            and ui_record.get("cleanupErrors") == ui_record.get("termination") == []
            and ui_record.get("reviewedInputProfile") == PROFILE, "Exact completed current UI-only build required")
    projection = c.decode(c.raw(ui_build / "projection.json"))
    require(ui_record.get("current8acFixture") == projection.get("current8acFixture") == FIXTURE
            and projection.get("mainSourceCommit") == projection.get("runnerSourceCommit") == SOURCE
            and projection.get("reviewedInputProfile") == PROFILE
            and projection.get("changedOriginalMethodAssertions") == 0
            and projection.get("applicationBuildTargets") == projection.get("nativeLibraryBuilds") == 0
            and projection.get("allOriginalNativeUITestMethodsCompiled") is True
            and ui_record.get("historyKeyboardPreparation") == projection.get("historyKeyboardPreparation") == INTEGRATED_HISTORY
            and all(ui_record.get(key) is None and projection.get(key) is None for key in ALTERNATIVE_BINDINGS),
            "Exact complete NativeUI projection without overlays required")
    files, transform = projected_files(source)
    require(projection.get("sourceFiles") == {name: {"bytes": len(value), "sha256": sha(value)} for name, value in files.items()}
            and projection.get("exactOriginalProjectAndScheme") == transform,
            "Original project transformation and all compiled test bytes required")
    for name, value in files.items():
        require(c.raw(ui_build / name) == value, "Compiled NativeUI source changed: " + name)
    qualified_path = ui_build / "native16-qualified.json"
    qualified_raw = c.raw(qualified_path)
    require(sha(qualified_raw) == _state["args"].native_ui_proof_sha256,
            "Exact independently retained NativeUI compiler/product proof required")
    qualified = c.decode(qualified_raw)
    builder = reviewed_builder(c)
    require(qualified["status"] == "PASS_NATIVEUI_COMPILER_INPUTS_AND_PRODUCTS_NOT_ACCEPTANCE"
            and qualified["sourceCommit"] == SOURCE and qualified["sharedControllerSHA256"] == _state["sharedSHA"]
            and qualified["sharedAdmissionSHA256"] == _state["admissionPin"]["sha256"]
            and qualified["builderReceiptSHA256"] == c.digest(ui_build / "receipt.json")
            and all(qualified.get(name) == value for name, value in builder.items())
            and qualified["nativeUIProfileSHA256"] == c.digest(Path(__file__))
            and qualified["compiledSourceFiles"] == SOURCE_FILES and qualified["actualCompilerFileLists"]
            and qualified["testsExecuted"] == qualified["applicationBuildTargets"] == qualified["nativeLibraryBuilds"] == 0,
            "Actual NativeUI qualification identity differs")
    for row in qualified["actualCompilerFileLists"]:
        require(c.digest(Path(row["retained"])) == row["sha256"]
                and Path(row["retained"]).stat().st_size == row["bytes"], "Retained actual compiler input list changed")
    inventory_path = ui_build / "native16-products-with-modes.json"
    require(c.digest(inventory_path) == qualified["productsWithModesSHA256"]
            and c.inventory(ui_build / "derived/Build/Products") == c.decode(c.raw(inventory_path)),
            "Original NativeUI products, file modes or links changed")
    require(c.digest(ui_build / "original-build.log") == ui_record["logSHA256"]
            and b"** TEST BUILD SUCCEEDED **" in c.raw(ui_build / "original-build.log")
            and c.digest(ui_build / "process-exit.json") == ui_record["processExitReceiptSHA256"],
            "Original successful NativeUI stdout and process exit required")
    return dict(FIXTURE)


def rtl_device(runtimes_raw, types_raw):
    require(_state["rtlCell"] is not None, "Explicit native RTL cell required")
    return _state["rtl"].device(_state["shared"], runtimes_raw, types_raw, _state["rtlCell"])


def rtl_prepare(run, out, udid):
    c, matrix, configuration = _state["shared"], _state["rtl"], _state["rtlCell"]
    require(configuration is not None, "Explicit native RTL cell required")
    require(matrix.cell(c, _state["args"].rtl_cell, _state["rtlCellSHA256"]) == configuration,
            "Native RTL cell changed before owned simulator configuration")
    helpers, closure = matrix.original_helpers(c, Path(_state["admission"]["sourceRoot"]))
    _state.update(rtlHelpers=helpers, rtlHelperClosure=closure)
    result = {"configuration": configuration, "configurationSHA256": _state["rtlCellSHA256"],
              "helperClosure": closure, "sourceLocalizationProofSHA256": matrix.SOURCE_PROOF_SHA,
              "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}
    c.write(out / "rtl-configuration.json", result)
    result["before"] = matrix.prepare(c, helpers, configuration, run, out, udid)
    return result


def rtl_installed(run, out, udid, app, phase):
    return _state["rtl"].installed(_state["shared"], _state["rtlHelpers"], run, out, udid, app, phase)


def rtl_bind(configured):
    return _state["rtl"].bind(_state["shared"], configured, _state["rtlCell"])


def rtl_environment():
    require(_state["rtlCell"] is not None, "Explicit native RTL cell required")
    return {"TEST_RUNNER_" + _state["rtl"].ENVIRONMENT: _state["rtlCell"]["appLanguage"]}


def rtl_after(run, out, udid, app):
    matrix, c = _state["rtl"], _state["shared"]
    require(matrix.cell(c, _state["args"].rtl_cell, _state["rtlCellSHA256"]) == _state["rtlCell"],
            "Native RTL cell changed during the original method")
    return {"environment": matrix.observe(c, _state["rtlHelpers"], _state["rtlCell"], run, out, udid, "after"),
            "installedCode": rtl_installed(run, out, udid, app, "after")}


def rtl_attachments(run, out, udid):
    directory = out / "private-original-rtl-attachments"
    require(not directory.exists() and not directory.is_symlink(), "Fresh original RTL attachment export required")
    run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(out / "Original.xcresult"),
         "--output-path", str(directory)], out, "rtl-original-attachments", timeout=180, cleanup=True)
    directory.chmod(0o700)
    result = _state["rtl"].screenshots(_state["shared"], directory, udid, _state["rtlCell"])
    _state["shared"].write(out / "rtl-original-screenshots.json", result)
    return result


def owned_lifecycle(source, root, directory):
    path = source / ("Tools/CurrentAppleValidation/combined_heart_semantics/build14/"
                     "combined_heart_semantics_owned_outcomes.py")
    original = path.read_bytes()
    require(sha(original) == OWNED_OUTCOMES_SHA, "exact_owned_outcomes_73bb_required")
    module = type(sys)("App15_NativeUI_owned_outcomes")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    return module.Commands(directory, root)
