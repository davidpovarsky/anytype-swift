"""One corrected-r15 App build and the existing actual T5 Inspector journeys.

No historical runtime pair is executed or certified. Native runtime admission,
UI observations and publication use the same strict existing validators.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import sys

import run_t5_apple_pair as pair
import run_t5_native_ui as native_ui
import t5_host_actions as host_actions
import t5_account_retry_existing_build as pending_retry
import run_ui27 as ui
from validate_release import method_results

PROFILE = "r15-attachment-v1"
PASS = "CORRECTED_R15_T5_UI_PASS_VISUAL_REVIEW_PENDING"
CONFIGURATION = "Release-Anytype"
PREPARATION = native_ui.evidence.PREPARATION


def build_once(app, derived, work, proof, selection, source, binding):
    product_root = work / "new/Products"
    proof.mkdir(parents=True)
    before_locks = pair.lock_hashes(app)
    hanlin = app / "Dependencies/Hanlin/.pinkha-source.json"
    pair.require(hanlin.is_file(), "Prepared canonical Hanlin SDK is missing")
    hanlin_sha = pair.digest(hanlin)
    ui.prepare_source_cache(app, derived)
    command = [
        "xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
        "-configuration", CONFIGURATION, "-destination", "platform=iOS Simulator,id=" + selection["udid"],
        "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO",
        "-only-testing:AnytypeTests/" + PREPARATION.split("/")[0], *pair.FLAGS,
        "-only-testing:AnytypeTests/" + host_actions.SUITE,
        "-only-testing:AnytypeTests/" + pending_retry.native.pending_evidence.METHOD.split("/")[0],
    ]
    _, log = pair.run_logged(command, app, proof, "build-corrected-r15", 5400)
    pair.require(pair.git(app, "rev-parse", "HEAD") == source and not pair.git(app, "status", "--porcelain"),
                 "Published application source changed during the build")
    pair.require(before_locks == pair.lock_hashes(app) and pair.digest(hanlin) == hanlin_sha,
                 "Build dependency inputs changed")
    products = derived / "Build/Products"
    source_configuration = ui.test_configuration(products, "AnytypeTests")
    pair.require(not product_root.exists(), "Refuse stale same-job App products")
    shutil.copytree(products, product_root, symlinks=True)
    configuration = product_root / source_configuration.name
    configuration.write_bytes(plistlib.dumps(pair.rewrite_product_paths(
        plistlib.loads(configuration.read_bytes()), products, product_root)))
    built = product_root / (CONFIGURATION + "-iphonesimulator/Anytype.app")
    ui.verify_signed_simulator(built, proof)
    ui.verify_runtime_copies(built, binding["native_marker"].encode(), proof)
    (proof / "native-source-marker").mkdir()
    ui.verify_runtime_copies(built, pair.HEART.encode(), proof / "native-source-marker")
    carriers = ui.code_carriers(built)
    lock = json.loads((app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    pins = [item["state"]["revision"] for item in lock["pins"] if item["identity"].lower() == "torahinspectorkit"]
    pair.require(pins == [ui.KIT], "One exact reviewed Kit revision required")
    checkouts = [path for path in (derived / "SourcePackages/checkouts").iterdir()
                 if path.name.lower() == "torahinspectorkit"]
    pair.require(len(checkouts) == 1 and pair.git(checkouts[0], "rev-parse", "HEAD") == ui.KIT,
                 "Resolved Kit differs from the reviewed App lock")
    receipt = dict(role="corrected-r15", app_source_sha=source, flags=pair.FLAGS,
        runtime_version=ui.heart_profiles.select(PROFILE).version, runtime_binding=binding,
        package_lock_hashes=before_locks, hanlin_snapshot_sha256=hanlin_sha, kit_sha=ui.KIT,
        code_sha256=carriers["sha256"], code_carriers=carriers, app=str(built),
        configuration=str(configuration), build_log_sha256=pair.digest(log), app_builds=1)
    pair.write(proof / "build.json", receipt)
    return receipt


def execute(args, result):
    pair.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                 "Actual Apple silicon Mac required")
    pair.require(sys.version_info >= (3, 12), "Python3.12 required")
    app, work, proof, derived = [p.resolve() for p in [args.app, args.work, args.evidence, args.derived]]
    pair.require(len({app, work, proof, derived}) == 4
        and all(p.is_relative_to(app / "build") for p in [work, proof, derived]),
        "Separate job-owned source/work/proof/derived paths required")
    pair.require(not work.exists(), "Fresh controller-owned private work directory required")
    work.mkdir(parents=True, mode=0o700)
    source = pair.verify_published_source(app, proof)
    host_actions.source_contract(app)  # Reject declaration drift before compilation.
    pair.write(proof / "retained-pagination.json", pending_retry.native.pending_evidence.validate_retained_source(app))
    pair.require(args.source_run_id == pending_retry.native.pending_evidence.RUNTIME_RUN,
                 "The combined pending-nine route requires the current corrected runtime producer")
    run_id = os.environ["GITHUB_RUN_ID"]
    preflight = json.loads((proof / "preflight/preflight.json").read_text(encoding="utf8"))
    pair.require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
        and preflight.get("source_sha") == source and preflight.get("run_id") == run_id,
        "Actual source/run-bound Xcode27 preflight required")
    selection = preflight["selected"]["ipad"]
    pair.require(selection["name"] == "Pinkha-UI27-" + run_id + "-ipad", "Job-owned simulator identity differs")
    pair.require(shutil.disk_usage(work).free >= 8 * 1024**3, "Free disk reserve below8GiB")
    installation = json.loads((proof / "heart/heart-installation.json").read_text(encoding="utf8"))
    binding = ui.heart_profiles.installed_binding(app, installation, source, PROFILE, args.source_run_id)
    result.update(app_source_sha=source, run_id=run_id, app_flags=pair.FLAGS,
        runtime_profile=PROFILE, runtime_binding=binding, phase="ONE_APP_BUILD")
    pair.write(proof / "result.json", result)
    # Compilation uses a newly owned destination. The shared UI controller then
    # creates and verifies a separate empty simulator for its actual account.
    build = build_once(app, derived, work, proof / "build", selection, source, binding)
    result.update(completed_app_builds=1, phase="ACTUAL_HOST_ACTIONS", host_actions_status="RUNNING")
    pair.write(proof / "result.json", result)
    host = host_actions.execute(app=app, build=build, selection=selection,
        evidence=proof / "host-actions", pair=pair, ui=ui, source=source, run_id=run_id)
    pair.require(host["status"] == host_actions.PASS, "Exact pending T5 host actions did not pass")
    result.update(host_actions_status=host["status"], host_actions_result="host-actions/execution.json",
                  phase="ACTUAL_PENDING_NINE", pending_retry_status="RUNNING")
    pair.write(proof / "result.json", result)
    pending = pending_retry.run_after_corrected_build(app=app, work=work, proof=proof, build=build,
        selection=selection, pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id)
    pair.require(pending["status"] == pending_retry.PASS, "The exact pending native nine-query scope did not pass")
    result.update(pending_retry_status=pending["status"], pending_retry_result="account-retry-pending/result.json",
                  pending_retry_actual_counts=pending["actual_counts"], phase="ACTUAL_NATIVE_UI")
    pair.write(proof / "result.json", result)
    outcome = native_ui.run_after_corrected_build(app=app, work=work, proof=proof, build=build,
        selection=selection, pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id)
    result.update(native_ui_status=outcome["status"], native_ui_result="native-ui/result.json",
        native_mutations=outcome.get("native_mutations", {"status": "NOT_RUN"}),
        core_ui_status=outcome.get("core_ui_status", "NOT_RUN"),
        r08_status=outcome.get("r08", {}).get("status", "NOT_RUN"))
    pair.require(outcome["status"] == native_ui.PASS, "Actual corrected-r15 native/UI acceptance failed")
    mutations = outcome.get("native_mutations", {})
    pair.require(mutations.get("status") == native_ui.native_mutations.PASS
        and mutations.get("actual_mutations") == 2 and mutations.get("actual_observations") == 3,
        "Actual type change and whole-object deletion evidence is missing")
    pair.require(outcome.get("prerequisite_scope") == "SINGLE_CORRECTED_RUNTIME"
        and outcome.get("mixed_version_accepted") is False and outcome.get("host_freshness_accepted") is False
        and outcome.get("ui_simulator_shutdown") is True, "Standalone scope or owned cleanup differs")
    result.update(status=PASS, phase="COMPLETE", actual_counts=dict(
        app_builds=1, host_action_methods=11, host_action_cases=12,
        pending_retry_methods=1, pending_retry_observations=3, pending_retry_service_queries=9,
        native_preparation_methods=1, native_mutations=2, native_mutation_observations=3, core_ui_methods=2,
        hebrew_readonly_ui_executions=2, ui_app_lifetimes=5, failed=0, skipped=0),
        actual_ui_observations=outcome.get("actual_observation_counts"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["app", "work", "evidence", "derived"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args(argv)
    result = dict(status="RUNNING", phase="PREFLIGHT", completed_app_builds=0, native_ui_status="NOT_RUN",
        host_actions_status="NOT_RUN", pending_retry_status="NOT_RUN",
        mixed_version_accepted=False, host_freshness_accepted=False, full_matrix_accepted=False,
        product_lookup_flag="OFF", voice_over_status="NOT_RUN", visual_review_status="PENDING",
        physical_device_accepted=False, started_at=datetime.now(timezone.utc).isoformat())
    try:
        execute(args, result)
    except BaseException as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                      error_type=type(error).__name__, error=str(error))
        if result["phase"] == "ACTUAL_HOST_ACTIONS":
            result["host_actions_status"] = result["status"]
        if result["phase"] == "ACTUAL_PENDING_NINE":
            result["pending_retry_status"] = result["status"]
        raise
    finally:
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        pair.write(args.evidence / "result.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
