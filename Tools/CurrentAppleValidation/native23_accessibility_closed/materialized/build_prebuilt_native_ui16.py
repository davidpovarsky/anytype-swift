#!/usr/bin/env python3
"""Compile original Native UI tests against an already-built unified host.

This creates one UI-runner-only project from the existing exact reversible
projection. It never compiles, alters, signs or replaces the application.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

LIFECYCLE = None


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def native8ac_module():
    path = Path(__file__).resolve().with_name("native16_profile.py")
    sys.dont_write_bytecode = True
    original = path.read_bytes()
    require(hashlib.sha256(original).hexdigest() == "3fd3049737f4be72f4257a04e5ca94085e6d9e11cd3916257ced4bf2e8943aa6",
            "exact_reviewed_shared_app_NativeUI_profile_required")
    cached = getattr(native8ac_module, "qualified", None)
    if cached is not None:
        return cached
    module = type(sys)("qualified_native16")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    native8ac_module.qualified = module
    return module


def native11619_module():
    path = Path(__file__).resolve().with_name("native11619_profile.py")
    require(digest(path) == "58643d32057cf6f692b39e15eb53d50925170d26ccbe12304c55a62f73fa5e41", "exact_App14_NativeUI_profile_required")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_native11619", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bin_confirmation_module():
    path = Path(__file__).resolve().with_name("bin_confirmation_preparation.py")
    require(digest(path) == "6f30156103912fdebe67bedc530e57f159ece79d640cde38b1c05b51e67341a4", "exact_Bin_confirmation_source_validator_required")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_bin_confirmation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    global LIFECYCLE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner-source-commit")
    parser.add_argument("--native-sharing-source-commit", choices=["dec2ecbb19ff6dab720866ef5a973058c47c7e91"])
    parser.add_argument("--history-source-commit", choices=["6c398307682073f31f9fb59af59f34c96003d542"])
    parser.add_argument("--archive-source-commit", choices=["658f4af4380dffc55c65559ca9e0cc6d5ed9c931"])
    parser.add_argument("--miniapps-source-commit", choices=["53eec4a2289f969979bc301760ce152088ebc2f7"])
    parser.add_argument("--bin-source-commit", choices=["36401a8e49189465ad89e395d962695e3a76e67a", "06a3d5b83caf656f2b9a28618cd186c6794ab27e"])
    parser.add_argument("--miniapps-menu-source-commit", choices=["9b7f0df07ad4b9f81829ee834ac30c5c4c8588fd"])
    parser.add_argument("--bin-confirmation-source-commit", choices=["d9acff333db5a2df0cfa373524a9c17e53410ffe"])
    parser.add_argument("--shared-admission", type=Path, required=True)
    parser.add_argument("--shared-admission-sha256", required=True)
    parser.add_argument("--shared-controller-sha256", required=True)
    args = parser.parse_args()
    native8ac_module().configure(args)
    root, evidence, output = args.main_root, args.main_evidence, args.output
    for path in (root, evidence, output):
        require(path.is_absolute() and path.resolve() == path, "canonical_absolute_path_required")
    require(root in evidence.parents and root in output.parents, "one_owned_main_workspace_required")
    require(not output.exists(), "refuse_existing_native_ui_output")
    source = args.source_root or root / "source"
    original = json.loads((evidence / "receipt.json").read_bytes())
    require((original.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
             or (original.get("sourceCommit") == "379ca3568f247d2fc218ed63df24796d461713c0"
                 and original.get("status") == "PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                 and original.get("protocol") == "pinkha-app15-original-app-ui-continuation-v1"))
            and original.get("testsExecuted") == 0 and original.get("sourceUnchanged") is True,
            "completed_original_main_build_required")
    origin = original["sourceCommit"]
    before = json.loads((evidence / "source-before.json").read_bytes())
    after = json.loads((evidence / "source-after.json").read_bytes())
    require(before == after and before["commit"] == origin and before["status"] == "",
            "unchanged_original_source_required")
    current = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                             check=True, capture_output=True, text=True).stdout.strip()
    clean = subprocess.run(["git", "-C", str(source), "status", "--porcelain"],
                           check=True, capture_output=True, text=True).stdout
    require(current == origin and clean == "", "frozen_main_checkout_required")
    profiles = {
        "70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683": {
            "name": "original-unified70fb-sdk44",
            "nativeSHA256": "08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc",
            "sdkReceiptSHA256": "67edd8f955524044428bf583b51f2357ca290e5ded0aacd8def0dff92f6b1521",
            "lockSHA256": "bb5582d3f0b9bc17b909ade4751904fd7b2fee2d066fea50b7a1ef913a8fe513",
        },
        "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72": {
            "name": "qualified-mobile70f0-sdk30e",
            "nativeSHA256": "c3374a58dffb64658fe6840ee9bd2711a4b1bf8c449c32da5bd51ede4901cece",
            "sdkReceiptSHA256": "0ae5a1476c899b1790f01a2a3b4118034e848d8ad8dcf2d97f12104f7387f798",
            "lockSHA256": "ffc47556534ee279d01bb771c6d49637766e8828bd872cce739e541d8ce4f124",
        },
    }
    profiles["410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9"] = {
        "name": "qualified-mobile410b-sdk86-torah9058",
        "nativeSHA256": "48905b7312d7228fe88a60517ec90c1c23d73f2ada762877c05ace9752103342",
        "sdkReceiptSHA256": "bad0afa285da6bd023235b15f82329f9d7b32ec50bf9194d63b9ee96730324a5",
        "lockSHA256": "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd",
    }
    if original["inputs"]["nativeSourceManifestSHA256"] == "410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9":
        require(origin == "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f"
                and original.get("assemblyReceiptSHA256") ==
                    "8556b47a6a7e523bd5ad4c58ae292501acda1038b0d1f827e268cef15a542797",
                "exact_reviewed_build13_source_and_original_assembly_required")
    current11619 = None
    if (origin == "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
            or original["inputs"]["nativeSourceManifestSHA256"] ==
                "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"):
        current11619 = native11619_module()
        current11619.qualify_main(original)
        profiles[current11619.NATIVE] = dict(current11619.PROFILE)
    current8ac = None
    runtime_binding = None
    if (origin == "379ca3568f247d2fc218ed63df24796d461713c0"
            or original["inputs"]["nativeSourceManifestSHA256"] ==
                "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"):
        current8ac = native8ac_module()
        current8ac.qualify_main(original)
        runtime_binding = current8ac.qualify_runtime_inputs(source, evidence, original)
        profiles[current8ac.NATIVE] = dict(current8ac.PROFILE)
    require(args.source_root is None or current8ac is not None,
            "explicit_source_root_is_only_for_closed_App15_warm_layout")
    require(args.native_sharing_source_commit is None or current8ac is not None,
            "sharing_donor_is_only_for_exact_App15")
    profile = profiles.get(original["inputs"]["nativeSourceManifestSHA256"])
    require(profile is not None, "explicit_reviewed_unified_profile_required")
    if origin in {"5c05a612e4054a4adfa7f812343be6a15871cc89",
                  "5ffff121e696044b0d1955524b7a69baf453b4b1",
                  "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78"}:
        require(original["inputs"]["nativeSourceManifestSHA256"] ==
                "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72",
                "reviewed5c_native_runtime_required")
        profile = dict(profile, name="qualified-mobile70f0-sdk30e-torah9058",
            lockSHA256="4453726b6b4bbd52dc3c5caa5a315a51e718139c4f96182b7a6851a0b8c82d04")
    for key in ("nativeSHA256", "sdkReceiptSHA256", "lockSHA256"):
        require(original["inputs"].get(key) == profile[key],
                "reviewed_unified_input_changed:" + key)
    require(digest(source / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")
            == profile["lockSHA256"], "reviewed_package_lock_changed")
    for phase in ("app", "ui"):
        require(original[phase]["exitCode"] == 0
                and original[phase]["status"] == "PASS_BUILD_EXIT_0",
                "both_original_build_phases_must_have_completed")
        phase_evidence = (current8ac.ORIGINAL_EVIDENCE
                          if current8ac is not None and phase == "app" else evidence)
        require(digest(phase_evidence / phase / "original.log") == original[phase]["logSHA256"],
                "original_build_log_changed:" + phase)
    native = source / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
    require(digest(native) == original["inputs"]["nativeSHA256"], "native_input_changed")
    require(digest(source / "Dependencies/Hanlin/.pinkha-source.json") ==
            original["inputs"]["sdkReceiptSHA256"], "canonical_sdk_changed")
    inputs = [
        "NativeApp/AnyNative.xcodeproj/project.pbxproj",
        "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme",
        "NativeApp/UITests/NativeLaunchTests.swift",
        "NativeApp/UITests/NativeHistoryTests.swift",
    ]
    for relative in inputs:
        require(digest(source / relative) == before["files"][relative]["sha256"],
                "original_native_ui_source_changed:" + relative)
    runner_origin = args.runner_source_commit or origin
    require(len(runner_origin) == 40 and all(x in "0123456789abcdef" for x in runner_origin),
            "explicit_runner_source_commit_required")
    runner_launch = (source / inputs[2]).read_bytes()
    if current8ac is not None:
        runner_origin, runner_launch = current8ac.compile_sharing_source(source, vars(args))
    elif runner_origin != origin:
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, runner_origin], check=True, capture_output=True)
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only",
            origin, runner_origin], check=True, capture_output=True, text=True).stdout.splitlines()
        require(all(name == inputs[2] or name.startswith(("Tools/", "docs/validation/"))
                    for name in changed), "runner_overlay_must_not_change_application_source")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            runner_origin + ":" + inputs[2]], check=True, capture_output=True).stdout
        start = b"/// The existing native flows may run against the standalone acceptance app or\n"
        end = b"// Test-runner-only fixture protocol. These types never enter the app target.\n"
        require(runner_launch.count(start) == candidate.count(start) == 1
                and runner_launch.count(end) == candidate.count(end) == 1,
                "one_explicit_unified_launch_adapter_required")
        require(runner_launch.split(start)[0] == candidate.split(start)[0]
                and runner_launch.split(end)[1] == candidate.split(end)[1],
                "all_original_test_methods_and_fixture_contract_must_remain_byte_identical")
        runner_launch = candidate
    archive_binding = None
    if args.archive_source_commit is not None:
        require(origin == "6f1194f9b8c9540dea1187826dda6a256777dbbf"
                and runner_origin == origin, "one_exact_archive_preparation_on_original6f_required")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            args.archive_source_commit + ":" + inputs[2]], check=True, capture_output=True).stdout
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, args.archive_source_commit], check=True, capture_output=True)
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only",
            origin, args.archive_source_commit], check=True, capture_output=True, text=True).stdout.splitlines()
        require(all(name == inputs[2] or name.startswith(("Tools/", "docs/validation/"))
                    for name in changed), "archive_preparation_must_not_change_application_source")
        review_root = ":docs/validation/20261125-archive-native-grabber-preparation/"
        def reviewed_file(name):
            return subprocess.run(["git", "-C", str(source), "show",
                args.archive_source_commit + review_root + name],
                check=True, capture_output=True).stdout
        review_bytes = reviewed_file("source-review.json")
        review = json.loads(review_bytes)
        previous, replacement = reviewed_file("before.txt"), reviewed_file("after.txt")
        require(digest(source / inputs[2]) == review["beforeSHA256"] ==
                    "79a8192207b1cfa236c4ec0cdef71d3c99a81b1908aecd4bf79c7b1152080868"
                and hashlib.sha256(candidate).hexdigest() == review["afterSHA256"] ==
                    "cdb63944d9a7d4af1f3581415594ccf916ba6bf250698ad90bd6037ddbcb54aa",
                "exact_reviewed_archive_preparation_required")
        require(runner_launch.count(previous) == candidate.count(replacement) == 1
                and candidate.replace(replacement, previous) == runner_launch
                and review["inverseDeltaRestoresCompleteOriginalFile"] is True
                and review["allOriginalArchiveOutcomeAssertionsUnchanged"] is True
                and review["peekContentSwipeAccepted"] is False,
                "all_original_archive_outcomes_and_other_methods_must_remain_byte_identical")
        archive_binding = {"sourceCommit": args.archive_source_commit,
            "originalSHA256": review["beforeSHA256"], "compiledSHA256": review["afterSHA256"],
            "reviewSHA256": hashlib.sha256(review_bytes).hexdigest(),
            "allOriginalArchiveOutcomeAssertionsUnchanged": True,
            "peekContentSwipeAccepted": False, "inputRoute": review["inputRoute"]}
        runner_origin, runner_launch = args.archive_source_commit, candidate
    runner_history = (source / inputs[3]).read_bytes()
    history_binding = None
    if args.history_source_commit is not None:
        # This is one reviewed preparation correction, not an arbitrary test
        # overlay. The original history/result assertions are restored exactly
        # by removing its explicit keyboard preparation and read-only witness.
        require(hashlib.sha256(runner_history).hexdigest() ==
                "6c4064014253837e4738b1c143f45f9af91746c53b3b665439e65f55bc837a77",
                "exact_original_history_fixture_required")
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, args.history_source_commit], check=True, capture_output=True)
        candidate = subprocess.run(["git", "-C", str(source), "show",
            args.history_source_commit + ":" + inputs[3]], check=True, capture_output=True).stdout
        require(hashlib.sha256(candidate).hexdigest() ==
                "2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca",
                "reviewed_keyboard_history_fixture_required")
        review = subprocess.run(["git", "-C", str(source), "show", args.history_source_commit +
            ":docs/validation/20261125-native-history-keyboard-preparation/source-review.json"],
            check=True, capture_output=True).stdout
        reviewed = json.loads(review)
        require(reviewed["beforeSHA256"] == hashlib.sha256(runner_history).hexdigest()
                and reviewed["afterSHA256"] == hashlib.sha256(candidate).hexdigest()
                and reviewed["inverseDeltaRestoresCompleteOriginalFile"] is True
                and reviewed["allHistoryVersionBodyIdentityColdReopenAssertionsUnchanged"] is True
                and reviewed["longPressMenuAccepted"] is False,
                "explicit_history_preparation_review_required")
        history_binding = {"sourceCommit": args.history_source_commit,
            "originalSHA256": hashlib.sha256(runner_history).hexdigest(),
            "compiledSHA256": hashlib.sha256(candidate).hexdigest(),
            "reviewSHA256": hashlib.sha256(review).hexdigest(),
            "inputRoute": "real-keyboard-with-original-native-UIKit-range-witness",
            "longPressMenuAccepted": False, "allOriginalHistoryAssertionsUnchanged": True}
        runner_history = candidate
    elif hashlib.sha256(runner_history).hexdigest() == (
            "2772d790979de88a3b622f17453a91ca792114292016f01e31386de7f4f614ca"):
        # The same reviewed preparation may already be integrated into the App
        # source revision. Record that exact route without applying an overlay
        # or pretending that the former long-press interaction was accepted.
        reviewed_commit = "6c398307682073f31f9fb59af59f34c96003d542"
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        reviewed_commit, origin], check=True, capture_output=True)
        review = (source / "docs/validation/20261125-native-history-keyboard-preparation/source-review.json").read_bytes()
        require(hashlib.sha256(review).hexdigest() ==
                "27925f01b2a7817435637517793c19d49db9a6814caef6e33b88dafb6beb2117",
                "integrated_exact_history_preparation_review_required")
        reviewed = json.loads(review)
        require(reviewed["afterSHA256"] == hashlib.sha256(runner_history).hexdigest()
                and reviewed["inverseDeltaRestoresCompleteOriginalFile"] is True
                and reviewed["allHistoryVersionBodyIdentityColdReopenAssertionsUnchanged"] is True
                and reviewed["longPressMenuAccepted"] is False,
                "integrated_history_outcome_assertions_must_remain_original")
        history_binding = {"sourceCommit": origin, "reviewedPreparationCommit": reviewed_commit,
            "originalSHA256": reviewed["beforeSHA256"],
            "compiledSHA256": hashlib.sha256(runner_history).hexdigest(),
            "reviewSHA256": hashlib.sha256(review).hexdigest(),
            "inputRoute": "real-keyboard-with-original-native-UIKit-range-witness",
            "longPressMenuAccepted": False, "allOriginalHistoryAssertionsUnchanged": True,
            "sourceAlreadyIntegrated": True}

    miniapps_binding = None
    if args.miniapps_source_commit is not None:
        require(origin == "5c05a612e4054a4adfa7f812343be6a15871cc89"
                and runner_origin == origin and args.archive_source_commit is None
                and args.history_source_commit is None,
                "one_exact_additive_miniapps_method_on_original5c_required")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            args.miniapps_source_commit + ":" + inputs[2]],
            check=True, capture_output=True).stdout
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, args.miniapps_source_commit], check=True, capture_output=True)
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only",
            origin, args.miniapps_source_commit], check=True, capture_output=True, text=True).stdout.splitlines()
        require(all(name == inputs[2] or name.startswith(("Tools/", "docs/validation/"))
                    for name in changed), "miniapps_runner_must_not_change_application_source")
        marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
        require(runner_launch.count(marker) == 0 and candidate.count(marker) == 1
                and candidate.split(marker)[0].rstrip() == runner_launch.rstrip()
                and candidate.count(b"func testAnyMiniAppsTextStudioWarmAndColdReturnPersistInNativeDocument()") == 1,
                "every_existing_method_and_helper_must_remain_byte_identical")
        require(hashlib.sha256(runner_launch).hexdigest() ==
                    "2727945d9a6745c8f11d64841649c7a5117d79b85818f9406e7ed0e35ec346be"
                and hashlib.sha256(candidate).hexdigest() ==
                    "cc3f0e17c1c228b01a36c9e3307bcbae7a2f444f5c850614e7d843fd1e29dfc7",
                "exact_reviewed_new_miniapps_UI_source_required")
        miniapps_binding = {
            "sourceCommit": args.miniapps_source_commit,
            "originalSHA256": hashlib.sha256(runner_launch).hexdigest(),
            "compiledSHA256": hashlib.sha256(candidate).hexdigest(),
            "allOriginalMethodsByteIdentical": True,
            "newMethods": ["NativeLaunchTests/testAnyMiniAppsTextStudioWarmAndColdReturnPersistInNativeDocument"],
            "testStorageOverrides": False,
            "actualCompanionRequired": True,
            "ordinaryAccountSelectionAfterColdCallback": True,
        }
        runner_origin, runner_launch = args.miniapps_source_commit, candidate
    integrated_miniapps_binding = None
    bin_binding = None
    bin_review = None
    if origin == "5ffff121e696044b0d1955524b7a69baf453b4b1":
        require(runner_origin == origin and args.miniapps_source_commit is None
                and args.archive_source_commit is None and args.history_source_commit is None,
                "current_integrated_UI_requires_its_original_source")
        marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
        require(hashlib.sha256(runner_launch).hexdigest() ==
                    "61a981863f52c18f5b2f73125209b39df8e6b7b5e9aabf6bb4cc09cfb703e687"
                and runner_launch.count(marker) == 1
                and hashlib.sha256(runner_launch.split(marker)[1]).hexdigest() ==
                    "3a4b0995b8a37f10521a4c6355c3830a2c152ea44f56d77a787c27b534b98465",
                "exact_normal_storage_observer_fixture_required")
        integrated_miniapps_binding = {
            "sourceCommit": origin,
            "originalSHA256": hashlib.sha256(runner_launch).hexdigest(),
            "methodSectionSHA256": "3a4b0995b8a37f10521a4c6355c3830a2c152ea44f56d77a787c27b534b98465",
            "sourceAlreadyIntegrated": True,
            "allMiniAppsMethodBytesUnchanged": True,
            "testStorageOverrides": False,
            "disposableSimulatorObserverOptIn": True,
            "actualCompanionRequired": True,
            "ordinaryAccountSelectionAfterColdCallback": True,
        }
    if args.bin_source_commit is not None:
        require(integrated_miniapps_binding is not None and runner_origin == origin,
                "reviewed_Bin_preparation_requires_current_original_App")
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, args.bin_source_commit], check=True, capture_output=True)
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only",
            origin, args.bin_source_commit], check=True, capture_output=True, text=True).stdout.splitlines()
        require(all(name == inputs[2] or name.startswith(("Tools/", "docs/validation/"))
                    for name in changed), "Bin_preparation_must_not_change_application_source")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            args.bin_source_commit + ":" + inputs[2]], check=True, capture_output=True).stdout
        observed_creation = args.bin_source_commit == "06a3d5b83caf656f2b9a28618cd186c6794ab27e"
        review_directory = "20261125-native-bin-observed-create" if observed_creation else "20261125-native-bin-row-readiness"
        expected_review = "7619c15a8557736acdeb712b957d8405dd14fd4c0abb03f2297f3d6bdfd8babe" if observed_creation else "31b047c1fa07be8a86fbb078d1b6ae73dbcb8c7b48bb7d9457fdeee05a1606dc"
        expected_compiled = "989af328bd04926cbef2f7e3fc529e13012b784d1c72fd90ac47a37c444254b3" if observed_creation else "0b01a8f35eea248f2bbd7727e60c6a2bf95fdcd9af74674b58437d75d0b62eae"
        bin_review = subprocess.run(["git", "-C", str(source), "show", args.bin_source_commit +
            ":docs/validation/" + review_directory + "/source-review.json"],
            check=True, capture_output=True).stdout
        require(hashlib.sha256(bin_review).hexdigest() == expected_review
                and hashlib.sha256(candidate).hexdigest() == expected_compiled,
                "exact_reviewed_Bin_context_preparation_required")
        method = b"    func testNativeBinRestoreKeepsIdentityAndBodyAcrossColdReopen()"
        start = b"        let row = app.buttons[title].firstMatch\n"
        end = b"        let rowID = row.identifier\n"
        a = runner_launch.index(start, runner_launch.index(method))
        b = runner_launch.index(end, a)
        c = candidate.index(start, candidate.index(method))
        d = candidate.index(end, c)
        restored = candidate[:c] + runner_launch[a:b] + candidate[d:]
        if observed_creation:
            m = restored.index(method); n = restored.index(b"    private func makeApplication(", m)
            section = restored[m:n]
            section = section.replace(method + b" throws {", method + b" {", 1)
            section = section.replace(b'        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: title)',
                                      b'        createNamedItem(app, action: "any-native-new-document", title: title)', 1)
            restored = restored[:m] + section + restored[n:]
        require(restored == runner_launch, "Bin_inverse_must_restore_complete_original_UI_file")
        require(candidate.split(marker)[1] == runner_launch.split(marker)[1],
                "MiniApps_method_must_be_byte_identical_after_Bin_preparation")
        reviewed = json.loads(bin_review)
        require(reviewed["inverseDeltaRestoresCompleteOriginalFile"] is True
                and reviewed["allOriginalIdentityBodyBinRestoreColdReopenAssertionsUnchanged"] is True
                and reviewed["timeoutSeconds"] == 60 and reviewed["gestureDurationSeconds"] == 1.1
                and reviewed["establishedProductRootCause"] is False,
                "Bin_preparation_must_not_claim_unproven_product_acceptance")
        bin_binding = {"sourceCommit": args.bin_source_commit,
            "originalSHA256": hashlib.sha256(runner_launch).hexdigest(),
            "compiledSHA256": hashlib.sha256(candidate).hexdigest(),
            "reviewSHA256": hashlib.sha256(bin_review).hexdigest(),
            "inverseDeltaRestoresCompleteOriginalFile": True,
            "allOriginalIdentityBodyBinRestoreColdReopenAssertionsUnchanged": True,
            "timeoutSeconds": 60, "gestureDurationSeconds": 1.1}
        if observed_creation:
            require(reviewed["creationPreparation"] == "existing-createNamedItemWithObservedTransition"
                    and reviewed["creationNativeCallsAdded"] == 0
                    and reviewed["originalCreateFieldBudgetSeconds"] == reviewed["newCreateFieldBudgetSeconds"] == 30,
                    "existing_typed_field_preparation_must_retain_original_UI_budget")
            bin_binding["creationPreparation"] = "existing-createNamedItemWithObservedTransition"
        runner_origin, runner_launch = args.bin_source_commit, candidate
    current_menu_binding = None
    current_menu_review = None
    if args.miniapps_menu_source_commit is not None:
        require(origin == "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78"
                and runner_origin == origin and args.archive_source_commit is None
                and args.history_source_commit is None and args.miniapps_source_commit is None
                and args.bin_source_commit is None,
                "one_exact_menu_preparation_on_original_build12_required")
        expected = {'mainSourceCommit': '0c5ffc51cdeb480194fdd4d5e396a602d04d5d78', 'sourceCommit': '9b7f0df07ad4b9f81829ee834ac30c5c4c8588fd', 'originalSHA256': '989af328bd04926cbef2f7e3fc529e13012b784d1c72fd90ac47a37c444254b3', 'compiledSHA256': 'de36d8508963db5e31554e88078a60cbf2273ba8ae67a8d53c597647f97a4b97', 'originalMethodSectionSHA256': '3a4b0995b8a37f10521a4c6355c3830a2c152ea44f56d77a787c27b534b98465', 'compiledMethodSectionSHA256': 'cef7734232b8f12ff432a97b435a5c6e0801d2cd77a30ce097e83f5e1cf40a63', 'reviewSHA256': 'f5811451e908f601be5ea6005912b13b759e9e288afdd4231e478c8d51ed062f', 'inverseDeltaRestoresCompleteOriginalFile': True, 'allOriginalCrossAppNativeColdAssertionsUnchanged': True, 'testStorageOverrides': False, 'actualCompanionRequired': True, 'ordinaryAccountSelectionAfterColdCallback': True, 'nativeCallsAdded': 0, 'timeoutsChanged': 0, 'productChanges': 0}
        parents = subprocess.run(["git", "-C", str(source), "rev-list", "--parents", "-n", "1",
            args.miniapps_menu_source_commit], check=True, capture_output=True, text=True).stdout.split()
        require(parents == [expected["sourceCommit"], origin], "exact_UI_only_parent_required")
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only", origin,
            args.miniapps_menu_source_commit], check=True, capture_output=True, text=True).stdout.splitlines()
        require(inputs[2] in changed and all(name == inputs[2] or
            name.startswith("docs/validation/20261125-miniapps-document-menu-preparation/")
            for name in changed), "menu_preparation_must_not_change_App_or_other_tests")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            args.miniapps_menu_source_commit + ":" + inputs[2]], check=True, capture_output=True).stdout
        current_menu_review = subprocess.run(["git", "-C", str(source), "show",
            args.miniapps_menu_source_commit +
            ":docs/validation/20261125-miniapps-document-menu-preparation/source-review.json"],
            check=True, capture_output=True).stdout
        previous = b'        func roundTrip(_ text: String, cold: Bool) {\n            tapReady(app.buttons["any-native-miniapps"])'
        replacement = b'        func roundTrip(_ text: String, cold: Bool) {\n            tapReady(app.buttons["any-native-document-options"])\n            tapReady(app.buttons["any-native-miniapps"])'
        require(hashlib.sha256(runner_launch).hexdigest() == expected["originalSHA256"]
                and hashlib.sha256(candidate).hexdigest() == expected["compiledSHA256"]
                and hashlib.sha256(current_menu_review).hexdigest() == expected["reviewSHA256"]
                and runner_launch.count(previous) == candidate.count(replacement) == 1
                and candidate.replace(replacement, previous) == runner_launch,
                "one_real_menu_tap_must_restore_complete_original_UI_file")
        marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
        require(hashlib.sha256(runner_launch.split(marker)[1]).hexdigest() ==
                    expected["originalMethodSectionSHA256"]
                and hashlib.sha256(candidate.split(marker)[1]).hexdigest() ==
                    expected["compiledMethodSectionSHA256"], "original_cross_app_assertions_required")
        current_menu_binding = expected
        runner_origin, runner_launch = args.miniapps_menu_source_commit, candidate
    current410b_binding = None
    if origin == "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f":
        require(runner_origin == origin and args.history_source_commit is None
                and args.archive_source_commit is None and args.miniapps_source_commit is None
                and args.bin_source_commit is None and args.miniapps_menu_source_commit is None,
                "complete_same_source_build13_native_UI_required")
        current410b_binding = {'sourceCommit': 'e540cd7e01b497f1b3173ae2e68b43ade0b00b6f', 'originalSHA256': '6fbcd0173351597af99dd6d79e7869ac72077c0b9ad2ff464d9c02e60d096d02', 'compiledSHA256': '6fbcd0173351597af99dd6d79e7869ac72077c0b9ad2ff464d9c02e60d096d02', 'miniAppsMethodSectionSHA256': 'cef7734232b8f12ff432a97b435a5c6e0801d2cd77a30ce097e83f5e1cf40a63', 'sourceAlreadyIntegrated': True, 'allOriginalMethodAssertionsUnchanged': True, 'testStorageOverrides': False, 'actualCompanionRequired': True, 'ordinaryAccountSelectionAfterColdCallback': True, 'binPreparation': 'real-accessible-native-row-menu', 'nativeSourceManifestSHA256': '410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9'}
        marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
        require(hashlib.sha256(runner_launch).hexdigest() == current410b_binding["originalSHA256"]
                and runner_launch.count(marker) == 1
                and hashlib.sha256(runner_launch.split(marker)[1]).hexdigest() ==
                    current410b_binding["miniAppsMethodSectionSHA256"],
                "exact_integrated_document_menu_Bin_and_original_assertions_required")
    current11619_binding = None
    if current11619 is not None:
        current11619_binding = current11619.bind_source(
            source, original, runner_origin, runner_launch, runner_history, vars(args))
    current8ac_binding = None
    if current8ac is not None:
        current8ac_binding = current8ac.bind_source(
            source, original, runner_origin, runner_launch, runner_history, vars(args))
    bin_confirmation_binding = None
    bin_confirmation_review = None
    if args.bin_confirmation_source_commit is not None:
        validator = bin_confirmation_module()
        require(origin == validator.MAIN and runner_origin == origin and current410b_binding is not None,
                "one_Bin_confirmation_derivative_on_exact_App13_required")
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only", origin,
            validator.SOURCE], check=True, capture_output=True, text=True).stdout.splitlines()
        require(inputs[2] in changed and all(name == inputs[2] or
                name.startswith(("Tools/", "docs/validation/")) for name in changed),
                "Bin_confirmation_candidate_must_not_change_App_or_other_UI_files")
        candidate = subprocess.run(["git", "-C", str(source), "show", validator.SOURCE + ":" + inputs[2]],
                                   check=True, capture_output=True).stdout
        bin_confirmation_review = subprocess.run(["git", "-C", str(source), "show",
            validator.SOURCE + ":" + validator.REVIEW_PATH], check=True, capture_output=True).stdout
        bin_confirmation_binding = validator.qualify_source(runner_launch, candidate, bin_confirmation_review)
        current410b_binding = None  # This is explicitly a separately sourced UI derivative.
        runner_origin, runner_launch = validator.SOURCE, candidate
    helper = source / "Tools/AnyEnginePort/native_ui_transition_project.py"
    original_helper = subprocess.run(["git", "-C", str(source), "show",
        origin + ":Tools/AnyEnginePort/native_ui_transition_project.py"],
        check=True, capture_output=True).stdout
    require(helper.read_bytes() == original_helper, "original_ui_projection_changed")
    # Loading the original helper must not write bytecode into frozen source.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_native_ui_projection", helper)
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    project_bytes, transformation = projection.project_bytes((source / inputs[0]).read_bytes())
    scheme_bytes = projection.scheme_bytes((source / inputs[1]).read_bytes())

    output.mkdir(mode=0o700)
    if current8ac is not None:
        LIFECYCLE = current8ac.owned_lifecycle(source, source, output / "owned-builder-lifecycle")
    project = output / "source" / projection.PROJECT_NAME
    files = {
        "source/" + projection.PROJECT_NAME + "/project.pbxproj": project_bytes,
        "source/" + projection.PROJECT_NAME + "/xcshareddata/xcschemes/"
        + projection.SCHEME_NAME + ".xcscheme": scheme_bytes,
        "source/UITests/NativeLaunchTests.swift": runner_launch,
        "source/UITests/NativeHistoryTests.swift": runner_history,
    }
    if bin_confirmation_review is not None:
        files["bin-confirmation-source-review.json"] = bin_confirmation_review
    if current_menu_review is not None:
        files["miniapps-menu-source-review.json"] = current_menu_review
    if bin_review is not None:
        files["bin-preparation-source-review.json"] = bin_review
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    sources = {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
               for name, raw in files.items()}
    write(output / "projection.json", {
        "mainSourceCommit": origin, "runnerSourceCommit": runner_origin,
        "historyKeyboardPreparation": history_binding,
        "archiveGrabberPreparation": archive_binding,
        "miniAppsCrossAppFixture": miniapps_binding,
        "integratedMiniAppsFixture": integrated_miniapps_binding,
        "binContextPreparation": bin_binding,
        "currentMiniAppsMenuFixture": current_menu_binding,
        "current410bFixture": current410b_binding,
        "current11619Fixture": current11619_binding,
        "current8acFixture": current8ac_binding,
        "current8acRuntimeIdentity": runtime_binding,
        "current410bBinConfirmationFixture": bin_confirmation_binding,
        "mainReceiptSHA256": digest(evidence / "receipt.json"),
        "reviewedInputProfile": profile,
        "exactOriginalProjectAndScheme": transformation, "sourceFiles": sources,
        "applicationBuildTargets": 0, "nativeLibraryBuilds": 0,
        "allOriginalNativeUITestMethodsCompiled": True,
        "changedOriginalMethodAssertions": 0,
    })
    argv = [
        "xcodebuild", "build-for-testing", "-project", str(project),
        "-scheme", projection.SCHEME_NAME, "-configuration", "Debug",
        "-destination", "generic/platform=iOS Simulator",
        "-derivedDataPath", str(output / "derived"),
        "-resultBundlePath", str(output / "Build.xcresult"), "-jobs", "4",
        "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "ENABLE_TESTABILITY=YES",
        "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
        "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
        "PROVISIONING_PROFILE_SPECIFIER=",
    ]
    free = shutil.disk_usage(root).free
    floor = 2 * 1024**3
    require(free >= floor, "owned_process_disk_floor")
    if current8ac is not None:
        require(free >= floor + 512 * 1024**2 + 512 * 1024**2,
                "NativeUI_phase_allowance_and_concurrent_growth_unavailable")
    log = output / "original-build.log"
    started = time.time()
    environment = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with log.open("wb") as stream:
        process = subprocess.Popen(argv, cwd=source, env=environment, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record = {"sourceCommit": origin, "runnerSourceCommit": runner_origin,
                  "historyKeyboardPreparation": history_binding,
                  "archiveGrabberPreparation": archive_binding,
        "miniAppsCrossAppFixture": miniapps_binding,
        "integratedMiniAppsFixture": integrated_miniapps_binding,
        "binContextPreparation": bin_binding,
        "currentMiniAppsMenuFixture": current_menu_binding,
        "current410bFixture": current410b_binding,
        "current11619Fixture": current11619_binding,
        "current8acFixture": current8ac_binding,
        "current8acRuntimeIdentity": runtime_binding,
        "current410bBinConfirmationFixture": bin_confirmation_binding,
                  "mainReceiptSHA256": digest(evidence / "receipt.json"),
                  "reviewedInputProfile": profile,
                  "argv": argv, "pid": process.pid,
                  "pgid": process.pid, "started": started, "freeBytesBefore": free}
        if LIFECYCLE is not None:
            record.update(cleanupErrors=[], termination=[], lifecycleSHA256=current8ac.OWNED_OUTCOMES_SHA,
                          phaseGrowthAllowanceBytes=512 * 1024**2,
                          concurrentGrowthAllowanceBytes=512 * 1024**2)
        write(output / "launch.json", record)
        stopped = None
        minimum = free
        while process.poll() is None:
            free = shutil.disk_usage(root).free
            minimum = min(minimum, free)
            if free < floor:
                stopped = "RESOURCE_DISK_FLOOR"
            elif time.time() - started > 1200:
                stopped = "TIMEOUT"
            if stopped:
                if LIFECYCLE is not None:
                    LIFECYCLE._terminate_owned_process(process, record)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                break
            write(output / "monitor.json", {"freeBytes": free, "minimumFreeBytes": minimum,
                                            "elapsedSeconds": time.time() - started})
            time.sleep(2)
        if LIFECYCLE is not None:
            try:
                code = process.wait(timeout=1)
            except BaseException as exc:
                code = None
                record["cleanupErrors"].append({"phase": "final-owned-wait",
                    "type": type(exc).__name__, "reason": str(exc)})
        else:
            code = process.wait()
    if LIFECYCLE is not None:
        record.update(exitCode=code, stopped=stopped, elapsedSeconds=time.time() - started,
                      minimumFreeBytes=minimum, logSHA256=digest(log),
                      status="EXIT_RECORDED_PENDING_GROUP_OBSERVATION")
        write(output / "process-exit.json", record)
        observation = LIFECYCLE._observe_exited_group(process.pid)
        record["ownedProcessGroup"] = observation["status"]
        record["ownedGroupObservations"] = observation["observations"]
        record["processExitReceiptSHA256"] = digest(output / "process-exit.json")
        if observation["status"] != "ABSENT_ESRCH" or record["cleanupErrors"]:
            stopped = stopped or "OWNED_PROCESS_LIFECYCLE_UNRESOLVED"
        write(output / "owned-process-outcome.json", record)
    require(all(digest(output / name) == row["sha256"] for name, row in sources.items()),
            "native_ui_source_mutated_during_build")
    if current8ac is not None:
        require(current8ac.qualify_runtime_inputs(source, evidence, original) == runtime_binding,
                "App15_original_runtime_inputs_changed_during_NativeUI_build")
    products = output / "derived/Build/Products"
    rows = []
    for path in sorted(products.rglob("*")):
        if path.is_symlink():
            rows.append({"path": str(path.relative_to(products)), "kind": "symlink",
                         "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": str(path.relative_to(products)), "kind": "file",
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    write(output / "products-all.json", rows)
    record["completeProductsInventory"] = {
        "path": str(output / "products-all.json"),
        "sha256": digest(output / "products-all.json"), "entries": len(rows)}
    record.update(exitCode=code, elapsedSeconds=time.time() - started,
                  minimumFreeBytes=minimum, logSHA256=digest(log),
                  status=stopped or ("PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE" if code == 0 else "FAIL_BUILD"),
                  testsExecuted=0, applicationBuildTargets=0, sourceUnchanged=True)
    write(output / "receipt.json", record)
    require(code == 0 and stopped is None, "original_native_ui_runner_build_failed")
    current8ac.seal_ui_build(output, record, Path(__file__).resolve())


if __name__ == "__main__":
    main()
