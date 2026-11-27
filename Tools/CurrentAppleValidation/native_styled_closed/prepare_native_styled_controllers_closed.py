#!/usr/bin/env python3
"""Materialize a CLOSED styled derivative of the original NativeUI controllers.

No compiler or simulator is invoked. A separately reviewed exact common app
qualifier and its real successful admission are mandatory at execution.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ORIGINALS = {
    "build_prebuilt_native_ui8ac.py": "e6c4c506cf893b2dc495fdc4b76c686f09a108c9980e05d19590d92acab804f9",
    "run_prebuilt_native_ui8ac.py": "18c7cc5722a856782d454a11db11ea172c9d718cecd17cd6dc54ffcc2a256d2b",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def functions(value):
    text = value.decode()
    return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def substitute(value, changes):
    text = value.decode()
    inverse = []
    for old, new in changes:
        require(text.count(old) == 1, "Exact original replacement must occur once")
        text = text.replace(old, new)
        positions = [m.start() for m in re.finditer(re.escape(new), text)]
        require(len(positions) == 1, "Exact replacement must have one reversible position")
        inverse.append({"old": old, "new": new, "position": positions[0]})
    restored = text
    for row in reversed(inverse):
        p = row["position"]
        require(restored[p:p + len(row["new"])] == row["new"], "Inverse position differs")
        restored = restored[:p] + row["old"] + restored[p + len(row["new"]):]
    require(restored.encode() == value, "All original controller bytes must be recoverable")
    ast.parse(text)
    return text.encode(), inverse


def rtl_runner_changes():
    original_devices = '''        _, raw = run(["xcrun", "simctl", "list", "runtimes", "--json"], out, "runtimes")
        runtimes = [x for x in json.loads(raw)["runtimes"] if
                    x.get("isAvailable") is True and x.get("version") == "27.0"
                    and "iOS" in x.get("name", "")]
        require(len(runtimes) == 1, "one_available_original_ios27_runtime_required")
        _, raw = run(["xcrun", "simctl", "list", "devicetypes", "--json"], out, "device-types")
        types = [x for x in json.loads(raw)["devicetypes"] if
                 x.get("identifier") == "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"]
        require(len(types) == 1, "one_available_ipad_pro_m5_device_type_required")
        runtime = runtimes[0]'''
    devices = '''        if args.stage == "rtl":
            _, runtimes_raw = run(["xcrun", "simctl", "list", "runtimes", "--json"], out, "runtimes")
            _, types_raw = run(["xcrun", "simctl", "list", "devicetypes", "--json"], out, "device-types")
            runtime, actual_type = current8ac.rtl_device(runtimes_raw, types_raw)
            types = [actual_type]
            receipt["rtlActualDevice"] = {"runtime": runtime, "deviceType": actual_type}
        else:
''' + "\n".join("    " + line for line in original_devices.splitlines())
    boot = '        run(["xcrun", "simctl", "bootstatus", udid, "-b"], out, "bootstatus", timeout=180)'
    install = '        run(["xcrun", "simctl", "install", udid, str(app)], out, "install-unified-app", timeout=120)'
    executed = '        require(record["status"] == "PASS", "actual_original_ui_execution_failed")'
    final_guard = '        if args.stage == "miniapps" and not first_error and not cleanup_errors:'
    return [
        ('STAGES = {', 'STAGES = {\n    "rtl": ("NativeLaunchTests/testExplicitHebrewDirectionAndAlignmentSurviveColdReopen", 360),'),
        (original_devices, devices),
        (boot, boot + '\n        if args.stage == "rtl":\n            receipt["nativeRTL"] = current8ac.rtl_prepare(run, out, udid)'),
        (install, install + '\n        if args.stage == "rtl":\n            receipt["nativeRTL"]["installedBefore"] = current8ac.rtl_installed(run, out, udid, app, "before")'),
        ('        fixture_environment = {}', '''        if args.stage == "rtl":
            configured, binding["nativeRTL"] = current8ac.rtl_bind(configured)
            fixture_environment = current8ac.rtl_environment()
        else:
            fixture_environment = {}'''),
        (executed, executed + '\n        if args.stage == "rtl":\n            receipt["nativeRTL"]["after"] = current8ac.rtl_after(run, out, udid, app)'),
        (final_guard, '''        if args.stage == "rtl" and not first_error and not cleanup_errors:
            try:
                receipt["nativeRTL"]["screenshots"] = current8ac.rtl_attachments(run, out, udid)
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-rtl-screenshots", "reason": str(exc)})
''' + final_guard),
        ('        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":',
         '''        if args.stage == "rtl" and receipt["status"] == "PASS":
            receipt["status"] = "PASS_NATIVE_RTL_METHOD_VISUAL_REVIEW_PENDING"
        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":'''),
        ('    expected_status = ("PASS_DIAGNOSTIC_ONLY_NOT_ARCHIVE_ACCEPTANCE"\n                       if args.stage == "archive-picker-observe" else "PASS")',
         '''    expected_status = ("PASS_NATIVE_RTL_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "rtl" else
                       "PASS_DIAGNOSTIC_ONLY_NOT_ARCHIVE_ACCEPTANCE"
                       if args.stage == "archive-picker-observe" else "PASS")'''),
    ]


def library_runner_changes():
    final_guard = '        if args.stage == "miniapps" and not first_error and not cleanup_errors:'
    return [
        ('STAGES = {', 'STAGES = {\n    "library-search": ("NativeLaunchTests/testLibrarySearchReplacementAndColdReopenUseCurrentQuery", 900),\n    "source-drag": ("NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens", 360),'),
        (final_guard, '''        if args.stage == "library-search" and not first_error and not cleanup_errors:
            try:
                receipt["nativeLibrarySearch"] = current8ac.library_attachments(run, out, udid)
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-library-observations", "reason": str(exc)})
        if args.stage == "source-drag" and not first_error and not cleanup_errors:
            try:
                receipt["nativeSourceDrag"] = current8ac.source_drag_attachments(run, out, udid)
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-source-drag-observations", "reason": str(exc)})
''' + final_guard),
        ('        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":',
         '''        if args.stage == "library-search" and receipt["status"] == "PASS":
            receipt["status"] = "PASS_NATIVE_LIBRARY_SEARCH_METHOD_VISUAL_REVIEW_PENDING"
        if args.stage == "source-drag" and receipt["status"] == "PASS":
            receipt["status"] = "PASS_NATIVE_SOURCE_DRAG_METHOD_VISUAL_REVIEW_PENDING"
        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":'''),
        ('    expected_status = ("PASS_NATIVE_RTL_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "rtl" else',
         '''    expected_status = ("PASS_NATIVE_LIBRARY_SEARCH_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "library-search" else
                       "PASS_NATIVE_SOURCE_DRAG_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "source-drag" else
                       "PASS_NATIVE_RTL_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "rtl" else'''),
    ]


def styled_runner_changes():
    stages = '("styled-blocks", "styled-live-type")'
    boot = '        run(["xcrun", "simctl", "bootstatus", udid, "-b"], out, "bootstatus", timeout=180)'
    install = '        run(["xcrun", "simctl", "install", udid, str(app)], out, "install-unified-app", timeout=120)'
    execute = '''        record, _ = run(plan + ["-resultBundlePath", str(out / "Original.xcresult")],
                        out, "execute", timeout=allowance + 300,
                        environment=fixture_environment, allow_failure=True)'''
    return [
        ('def main():\n    global LIFECYCLE', 'def main(run=run):\n    global LIFECYCLE'),
        ('            LIFECYCLE = current8ac.owned_lifecycle(source, out, out / "owned-command-lifecycle")',
         '''            LIFECYCLE = current8ac.owned_lifecycle(source, out, out / "owned-command-lifecycle")
            if args.stage in ''' + stages + ''':
                run = current8ac.styled_owned_commands(run, out)'''),
        ('STAGES = {', '''STAGES = {
    "styled-blocks": ("NativeLaunchTests/testTypedBlockMenusPersistAllNineKindsAndColdReopen", 1800),
    "styled-live-type": ("NativeLaunchTests/testNativeStyledTypographyRefreshesLiveAtAccessibilitySize", 900),'''),
        ('            receipt["rtlActualDevice"] = {"runtime": runtime, "deviceType": actual_type}\n        else:',
         '''            receipt["rtlActualDevice"] = {"runtime": runtime, "deviceType": actual_type}
        elif args.stage in ''' + stages + ''':
            _, runtimes_raw = run(["xcrun", "simctl", "list", "runtimes", "--json"], out, "runtimes")
            _, types_raw = run(["xcrun", "simctl", "list", "devicetypes", "--json"], out, "device-types")
            runtime, actual_type = current8ac.styled_device(runtimes_raw, types_raw)
            types = [actual_type]
            receipt["styledActualDevice"] = {"runtime": runtime, "deviceType": actual_type}
        else:'''),
        (boot, boot + '\n        if args.stage in ' + stages + ':\n            receipt["nativeStyled"] = current8ac.styled_prepare(run, out, udid)'),
        (install, install + '\n        if args.stage in ' + stages + ':\n            receipt["nativeStyled"]["installedBefore"] = current8ac.styled_installed(run, out, udid, app, "before")'),
        ('            fixture_environment = current8ac.rtl_environment()\n        else:',
         '''            fixture_environment = current8ac.rtl_environment()
        elif args.stage in ''' + stages + ''':
            configured, binding["nativeStyled"] = current8ac.styled_bind(configured, out, products)
            fixture_environment = current8ac.styled_environment()
        else:'''),
        (execute, '''        if args.stage in ''' + stages + ''':
            record, _ = current8ac.styled_execute(run, out, udid,
                plan + ["-resultBundlePath", str(out / "Original.xcresult")],
                allowance + 300, fixture_environment)
        else:
''' + '\n'.join('    ' + line for line in execute.splitlines())),
        ('    finally:\n        # Only the original xcresult may establish completed test counts.',
         '''    finally:
        if args.stage in ''' + stages + ''':
            try:
                receipt["styledFinalization"] = native8ac_module().styled_finalize(run, out, udid, app)
            except BaseException as exc:
                cleanup_errors.append({"phase": "styled-restoration-and-final-readback", "reason": str(exc)})
        # Only the original xcresult may establish completed test counts.'''),
        ('        if udid is not None:\n            sandbox = None',
         '''        if args.stage in ''' + stages + ''' and not native8ac_module().styled_process_closed():
            cleanup_errors.append({"phase": "owned-device-custody", "reason": "Unresolved captured process/group; settings, sandbox and shutdown operations withheld"})
        if udid is not None and (args.stage not in ''' + stages + ''' or native8ac_module().styled_process_closed()):
            sandbox = None'''),
        ('                       ownedSimulatorRetention=("Shutdown" if args.retain_owned_simulator\n                                                else "Deleted"),',
         '''                       ownedSimulatorRetention=("RetainedUnresolvedOwnedCommands" if
                           args.stage in ''' + stages + ''' and not native8ac_module().styled_process_closed()
                           else "Shutdown" if args.retain_owned_simulator else "Deleted"),'''),
        ('        receipt.update(firstFailure=first_error, diagnosticFailures=cleanup_errors,',
         '''        if args.stage in ''' + stages + ''':
            try:
                receipt["styledOwnedCommands"] = native8ac_module().styled_owned_final_receipt()
            except BaseException as exc:
                cleanup_errors.append({"phase": "final-owned-command-custody", "reason": str(exc)})
        receipt.update(firstFailure=first_error, diagnosticFailures=cleanup_errors,'''),
        ('        if args.stage == "miniapps" and not first_error and not cleanup_errors:',
         '''        if args.stage in ''' + stages + ''' and not first_error and not cleanup_errors:
            try:
                receipt["nativeStyled"]["observations"] = current8ac.styled_attachments(run, out, udid)
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-styled-observations", "reason": str(exc)})
        if args.stage == "miniapps" and not first_error and not cleanup_errors:'''),
        ('        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":',
         '''        if args.stage in ''' + stages + ''' and receipt["status"] == "PASS":
            receipt["status"] = "PASS_NATIVE_STYLED_METHOD_VISUAL_REVIEW_PENDING"
        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":'''),
        ('    expected_status = ("PASS_NATIVE_LIBRARY_SEARCH_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "library-search" else',
         '''    expected_status = ("PASS_NATIVE_STYLED_METHOD_VISUAL_REVIEW_PENDING" if args.stage in ''' + stages + ''' else
                       "PASS_NATIVE_LIBRARY_SEARCH_METHOD_VISUAL_REVIEW_PENDING" if args.stage == "library-search" else'''),
    ]


def prepare(original_root, profile_path, output):
    original_root, profile_path, output = map(Path, (original_root, profile_path, output))
    require(original_root.is_absolute() and original_root.resolve() == original_root
            and profile_path.is_absolute() and profile_path.resolve() == profile_path
            and not profile_path.is_symlink(), "Canonical original inputs required")
    require(output.is_absolute() and output.parent.resolve() == output.parent
            and output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            "Fresh canonical controller output required")
    profile = profile_path.read_bytes()
    require(len(profile) < 128 * 1024, "Bounded NativeUI profile required")
    ast.parse(profile)
    profile_sha = sha(profile)
    matrix_path = profile_path.with_name("native_rtl_matrix.py")
    require(matrix_path.resolve() == matrix_path and not matrix_path.is_symlink(), "Canonical RTL helper required")
    matrix = matrix_path.read_bytes()
    require(len(matrix) < 128 * 1024, "Bounded NativeUI RTL helper required")
    ast.parse(matrix)
    require(('sha(raw) == "' + sha(matrix) + '"').encode() in profile,
            "NativeUI profile must pin the exact reviewed RTL helper")
    library_path = profile_path.with_name("native_library_search.py")
    require(library_path.resolve() == library_path and not library_path.is_symlink(), "Canonical Library helper required")
    library = library_path.read_bytes()
    require(len(library) < 128 * 1024, "Bounded NativeUI Library helper required")
    ast.parse(library)
    require(('sha(raw) == "' + sha(library) + '"').encode() in profile,
            "NativeUI profile must pin the exact reviewed Library helper")
    styled_files = {}
    for name in ("native_styled_runtime.py", "native_styled_observations.py"):
        path = profile_path.with_name(name)
        require(path.resolve() == path and not path.is_symlink(), "Canonical styled helper required")
        raw = path.read_bytes()
        require(len(raw) < 128 * 1024, "Bounded exact styled helper required")
        ast.parse(raw)
        require(('sha(raw) == "' + sha(raw) + '"').encode() in profile,
                "Closed profile must pin the exact styled helper: " + name)
        styled_files[name] = raw
    namespace = {"__file__": str(profile_path)}
    exec(compile(profile, str(profile_path), "exec"), namespace)
    require(namespace["READY_FOR_EXECUTION"] is False
            and all(namespace[key] is None for key in ("FUTURE_SOURCE_COMMIT", "FUTURE_SHARED_CONTROLLER_SHA256",
                                                       "FUTURE_CANONICAL_ADMISSION_SHA256")),
            "This source preparation must remain closed without actual future producer pins")
    loader = '''def native8ac_module():
    path = Path(__file__).resolve().with_name("native16_profile.py")
    sys.dont_write_bytecode = True
    original = path.read_bytes()
    require(hashlib.sha256(original).hexdigest() == "PROFILE_SHA",
            "exact_reviewed_shared_app_NativeUI_profile_required")
    cached = getattr(native8ac_module, "qualified", None)
    if cached is not None:
        return cached
    module = type(sys)("qualified_native16")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    native8ac_module.qualified = module
    return module'''.replace("PROFILE_SHA", profile_sha)
    files = {"native16_profile.py": profile, "native_rtl_matrix.py": matrix, "native_library_search.py": library,
             **styled_files}
    receipts = {}
    for name, expected in ORIGINALS.items():
        path = original_root / name
        require(path.resolve() == path and not path.is_symlink(), "Canonical original controller required")
        original = path.read_bytes()
        require(sha(original) == expected, "Original controller bytes changed: " + name)
        original_defs = functions(original)
        arguments = ('    parser.add_argument("--shared-admission", type=Path, required=True)\n'
                     '    parser.add_argument("--shared-admission-sha256", required=True)\n'
                     '    parser.add_argument("--shared-controller-sha256", required=True)\n')
        if name.startswith("run_"):
            arguments += '    parser.add_argument("--native-ui-proof-sha256", required=True)\n'
            arguments += ('    parser.add_argument("--rtl-cell", type=Path)\n'
                          '    parser.add_argument("--rtl-cell-sha256")\n')
            arguments += ('    parser.add_argument("--styled-cell", type=Path)\n'
                          '    parser.add_argument("--styled-cell-sha256")\n')
        arguments += '    args = parser.parse_args()\n    native8ac_module().configure(args)'
        changes = [(original_defs["native8ac_module"], loader),
                   ("    args = parser.parse_args()", arguments)]
        if name.startswith("build_"):
            old = '    require(code == 0 and stopped is None, "original_native_ui_runner_build_failed")'
            changes.append((old, old + '\n    current8ac.seal_ui_build(output, record, Path(__file__).resolve())'))
        else:
            changes += rtl_runner_changes()
            changes += library_runner_changes()
            changes += styled_runner_changes()
        candidate, inverse = substitute(original, changes)
        after_defs = functions(candidate)
        preserved = sorted(set(original_defs) - {"native8ac_module", "main"})
        require(set(original_defs) == set(after_defs)
                and all(original_defs[key] == after_defs[key] for key in preserved),
                "Original command/descriptor/result functions changed")
        output_name = name.replace("ui8ac.py", "ui16.py")
        files[output_name] = candidate
        receipts[output_name] = {"originalSHA256": expected, "candidateSHA256": sha(candidate),
                                "changes": inverse, "unchangedDefinitions": preserved,
                                "inverseRestoresEveryOriginalByte": True}
    receipt = {
        "schema": "pinkha-nativeui-shared-app-controller-preparation-v1",
        "status": "PREPARED_NATIVEUI_CONTROLLERS_NOT_APP_OR_UI_ACCEPTANCE",
        "nativeUIProfileSHA256": profile_sha, "controllers": receipts,
        "allowedExecutionStages": ["styled-blocks", "styled-live-type"],
        "executionReadiness": "CLOSED_NO_FUTURE_SOURCE_COMMON_OR_ACTUAL_ADMISSION",
        "futureSourceCommit": None, "futureSharedControllerSHA256": None, "futureCanonicalAdmissionSHA256": None,
        "styledHelpers": {name: sha(raw) for name, raw in styled_files.items()},
        "styledMethods": {
            "styled-blocks": {"selector": "PinkhaAnyNativeUITests/NativeLaunchTests/testTypedBlockMenusPersistAllNineKindsAndColdReopen", "allowanceSeconds": 1800},
            "styled-live-type": {"selector": "PinkhaAnyNativeUITests/NativeLaunchTests/testNativeStyledTypographyRefreshesLiveAtAccessibilitySize", "allowanceSeconds": 900}},
        "originalRunAndBindFunctionsUnchanged": True,
        "originalXCTestResultAuthorityUnchanged": True,
        "liveSettingScope": "exact fresh owned simulator content_size; two source-bound runner requests plus unconditional final restore after any attempted write",
        "nativeRTLHelperSHA256": sha(matrix),
        "nativeRTLMethod": "PinkhaAnyNativeUITests/NativeLaunchTests/testExplicitHebrewDirectionAndAlignmentSurviveColdReopen",
        "nativeRTLMatrix": {"appLanguages": ["he", "en"], "oppositeOSLanguageRequired": True,
                            "deviceFamilies": ["iphone", "ipad"], "appearances": ["light", "dark"],
                            "contentSize": "large", "cellsExecuted": 0},
        "nativeLibraryHelperSHA256": sha(library),
        "nativeLibraryMethod": "PinkhaAnyNativeUITests/NativeLaunchTests/testLibrarySearchReplacementAndColdReopenUseCurrentQuery",
        "nativeLibrarySourceRequirement": "Fixed reviewed31c644 insertion must already be integrated in the exact shared App source",
        "nativeLibraryObservations": {"typedPhaseGroupsRequired": 7, "visualReview": "PENDING", "actualMethodsExecuted": 0},
        "actualNativeCompilerInvocationRequired": True,
        "nativeSourceDragMethod": "PinkhaAnyNativeUITests/NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
        "nativeSourceDragAllowanceSeconds": 360,
        "nativeSourceDragMethodChanged": False,
        "passedHierarchyDragSelected": False,
        "sourcePinAuthority": "Exact reviewed shared controller APP16_SOURCE plus its immutable successful producer admission",
        "sharedProducerAdmitted": False, "builds": 0, "tests": 0, "nativeCalls": 0,
        "originalProfilesModified": False,
        "nextIntegratedSource": "BLOCKED_UNTIL_SEPARATELY_REVIEWED_COMMON_QUALIFIER_AND_ACTUAL_BUILD_RECEIPT",
        "files": {name: {"bytes": len(value), "sha256": sha(value)} for name, value in files.items()},
    }
    files["nativeui16-materialization.json"] = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    output.mkdir(mode=0o700)
    for name, value in files.items():
        with (output / name).open("xb") as stream:
            stream.write(value)
        (output / name).chmod(0o600)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-controller-root", type=Path, required=True)
    parser.add_argument("--native-ui-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.original_controller_root, args.native_ui_profile, args.output)
    print(json.dumps({name: result[name] for name in ("status", "nativeUIProfileSHA256", "builds", "tests")}, sort_keys=True))


if __name__ == "__main__":
    main()
