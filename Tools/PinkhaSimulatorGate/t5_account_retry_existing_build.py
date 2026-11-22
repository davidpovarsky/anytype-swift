"""Run only the nine pending R07 service queries on the current T5 App build.

The independent disposable simulator/account shares compiled products only.
The existing native method, exact receipt validator, and complete credential
scan are unchanged. Historical36 is retained evidence, never replayed here.
"""
from datetime import datetime, timezone
from pathlib import Path
import re
from uuid import uuid4

import owned_simulator_readiness as simulator
import run_t5_native_pagination as native
import run_t5_native_ui as native_ui
from t5_host_actions import host

PASS = "T5_PENDING_NINE_EXISTING_BUILD_PASS"


def validate_counts(counts, pair):
    exact = dict(selected_test_methods=1, baseline_body_invocations=0, baseline_observations=0,
                 baseline_search_calls=0, retry_observations=3, retry_successful_search_calls=8,
                 retry_failed_search_attempts=1, total_search_calls_in_wrapper=9,
                 tail_existing_account_restores=2, tail_account_stops=2)
    pair.require(all(type(counts.get(key)) is int and counts[key] == value for key, value in exact.items())
                 and counts.get("pending_only") is True and counts.get("fixture_setup_only") is True
                 and counts.get("baseline_acceptance_rerun") == "NOT_RUN",
                 "Exact pending nine-query scope is incomplete or replayed prior acceptance")


def run_after_corrected_build(*, app, work, proof, build, selection, pair, ui, method_results, source, run_id):
    profile = native_ui.validate_corrected_build(build, source, pair, ui)
    pair.require(profile.name == native.pending_evidence.RUNTIME_PROFILE
                 and build["runtime_binding"]["heart_source_run_id"] == native.pending_evidence.RUNTIME_RUN
                 and type(build.get("app_builds")) is int and build["app_builds"] == 1,
                 "Pending nine must reuse the one current corrected-r15 App build")
    return _run_after_build(app=app, work=work, proof=proof, build=build, selection=selection,
        pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id, profile=profile)


def run_after_coherent_build(*, app, work, proof, build, selection, pair, ui, method_results,
                             source, run_id, build_context, owned_device):
    import coherent_heart_release as coherent
    profile = coherent.validate_build(build, source, pair, ui, build_context)
    pair.require(owned_device is not None and owned_device.key == "t5-pending-nine",
                 "Pending nine requires its original planned disposable simulator")
    return _run_after_build(app=app, work=work, proof=proof, build=build, selection=selection,
        pair=pair, ui=ui, method_results=method_results, source=source, run_id=run_id,
        profile=profile, build_context=build_context, owned_device=owned_device)


def _run_after_build(*, app, work, proof, build, selection, pair, ui, method_results, source, run_id,
                     profile, build_context=None, owned_device=None):
    private, public = work / "account-retry-pending", proof / "account-retry-pending"
    pair.require(not private.exists() and not public.exists(), "Fresh pending-nine work/evidence required")
    private.mkdir(mode=0o700)
    public.mkdir(parents=True)
    token = uuid4().hex
    receipt = dict(status="RUNNING", phase="EXISTING_BUILD_ADMISSION", app_source_sha=source, run_id=run_id,
                   method=native.pending_evidence.METHOD, runtime_profile=profile.name,
                   runtime_binding=build["runtime_binding"], additional_app_builds=0,
                   baseline_body_invocations=0, baseline_acceptance_rerun="NOT_RUN",
                   physical_device_accepted=False, full_matrix_accepted=False,
                   product_lookup_flag="OFF", whole_index_completeness="NOT_PROVEN", acl_revocation="NOT_PROVEN",
                   started_at=datetime.now(timezone.utc).isoformat())
    destination = None
    native_started = False
    published = False
    failure = None
    try:
        pair.write(public / "retained-pagination.json", native.pending_evidence.validate_retained_source(
            app, runtime_binding=build["runtime_binding"] if build_context is not None else None))
        configuration = Path(build["configuration"])
        built, app_executable, _, test_executable = host.xctest_products(configuration)
        pair.require(built.resolve() == Path(build["app"]).resolve(), "Pending-nine App identity differs")
        if build_context is None:
            pair.require(built.resolve().is_relative_to((work / "new").resolve())
                         and configuration.resolve().is_relative_to((work / "new").resolve()),
                         "Pending-nine products are outside the current job's one App build")
        else:
            pair.require(built.resolve() == build_context.built.resolve()
                         and configuration == build_context.native_configuration,
                         "Pending-nine products differ from the frozen coherent build")
        binding = dict(app_executable_sha256=pair.digest(app_executable),
                       test_executable_sha256=pair.digest(test_executable),
                       original_xctestrun_sha256=pair.digest(configuration),
                       packaged_code_sha256=build["code_sha256"])
        receipt["built_products"] = binding

        def verify_binding():
            if build_context is not None:
                build_context.verify_current()
            pair.require(pair.git(app, "rev-parse", "HEAD") == source
                         and not pair.git(app, "status", "--porcelain", "--untracked-files=no"),
                         "Pending-nine published source changed")
            pair.require(pair.digest(app_executable) == binding["app_executable_sha256"]
                         and pair.digest(test_executable) == binding["test_executable_sha256"]
                         and pair.digest(configuration) == binding["original_xctestrun_sha256"]
                         and ui.code_carriers(built)["sha256"] == binding["packaged_code_sha256"],
                         "Pending-nine App, XCTest or original configuration changed")

        verify_binding()
        name = "Pinkha-T5R07-" + run_id + "-" + token[:12] if owned_device is None else owned_device.prepare()
        created_result, created = pair.run_logged(["xcrun", "simctl", "create", name, selection["device"]["identifier"],
                                      selection["runtime"]["identifier"]], app, public / "simulator", "create", 120)
        udid = created.read_text(encoding="utf-8").strip()
        pair.require(created_result.get("return_code") == 0 and not created_result.get("timed_out")
                     and re.fullmatch(native_ui.evidence.UUID, udid)
                     and udid.lower() != selection["udid"].lower(),
                     "Actual fresh pending-nine creation must return a distinct simulator UUID")
        destination = dict(selection, udid=udid, name=name)
        if owned_device is not None:
            owned_device.record_created(udid)
        receipt.update(phase="SIMULATOR_READINESS", device_udid=udid, device_name=name,
                       creation=dict(command_return_code=created_result["return_code"], log_sha256=pair.digest(created),
                                     nonce=token, source_sha=source, run_id=run_id,
                                     freshness_basis="ACTUAL_UNIQUE_OWNED_CREATE_COMMAND_AND_PREBOOT_SHUTDOWN_IDENTITY"))
        pair.write(public / "result.json", receipt)
        receipt["simulator_readiness"] = simulator.ensure_ready(app=app, evidence=public / "readiness",
            selection=destination, expected_name=name, pair=pair, require_initial_shutdown=True)
        pair.require(pair.app_container(udid, "data", required=False) is None,
                     "Fresh pending-nine simulator already contains an App account")
        receipt["phase"] = "ACTUAL_PENDING_NINE"
        pair.write(public / "result.json", receipt)
        native_started = True
        counts = native.execute_phase(app=app, work=private, build=build, udid=udid, source=source,
            run_id=run_id, token=token, ui=ui, method_results=method_results, pending_only=True,
            runtime_profile=profile.name if build_context is not None else None)
        validate_counts(counts, pair)
        verify_binding()
        receipt.update(actual_counts=counts, raw_result_sha256=pair.digest(private / "phase/result.json"),
                       phase="SECRET_SCAN_AND_SHUTDOWN")
    except BaseException as error:
        failure = error
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
        raise
    finally:
        cleanup_failure = None
        try:
            container = pair.app_container(destination["udid"], "data", required=False) if native_started else None
            published = native.publish_native_evidence(private, public, container, token)
            receipt["credential_scanned_evidence_published"] = published
        except BaseException as error:
            cleanup_failure = error
            receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                           publication_error_type=type(error).__name__, publication_error=str(error))
        try:
            if destination is not None:
                receipt["simulator_shutdown"] = simulator.shutdown_owned(app=app, evidence=public / "shutdown",
                    selection=destination, expected_name=destination["name"], pair=pair,
                    readiness_receipt_path=public / "readiness/readiness.json")
        except BaseException as error:
            cleanup_failure = cleanup_failure or error
            receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                           shutdown_error_type=type(error).__name__, shutdown_error=str(error))
        finally:
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            pair.write(public / "result.json", receipt)
        if failure is None and cleanup_failure is not None:
            raise cleanup_failure
    try:
        pair.require(published and receipt.get("simulator_shutdown", {}).get("status") == "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED",
                     "Complete secret-scanned pending-nine evidence and owned shutdown required")
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        pair.write(public / "result.json", receipt)
        raise
    receipt.update(status=PASS, phase="COMPLETE")
    pair.write(public / "result.json", receipt)
    return receipt
