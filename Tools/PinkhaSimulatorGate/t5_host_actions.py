"""Exact pending T5 host callbacks in the existing corrected-runtime App build.

The whole eleven-method suite is pending. Compile once with native preparation,
enumerate this one owned target, then execute the same configuration. This is
host lifetime/authority evidence, not signed native ACL or persistence proof.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

HANLIN_TOOLS = Path(__file__).resolve().parents[1] / "Hanlin"
if str(HANLIN_TOOLS) not in sys.path:
    sys.path.insert(0, str(HANLIN_TOOLS))
import run_host_tests as host
import wave15_core_profile as core
import shared_editor_existing_build as existing
import owned_simulator_readiness as simulator

SUITE = "TorahRelatedDocumentActionTests"
SOURCE_PATH = "AnyTypeTests/Pinkha/TorahRelatedDocumentActionTests.swift"
METHOD_COUNT = 11
CASE_COUNT = 12
PASS = "T5_HOST_ACTIONS_PASS"


def plain():
    return dict(parameters=[], argument_collections=[], case_count=1)


METHODS = {
    "relatedNavigationRequiresCurrentSpaceAndLifetime": plain(),
    "relatedNavigationPreservesBlockTarget": plain(),
    "changedRootSelectionRejectsCapturedCallbacks": plain(),
    "dismissedInspectorCallbacksAreRetired": plain(),
    "lateUnlinkFailureIsIgnoredAfterDocumentLifetimeEnds": dict(
        parameters=[dict(name="isNote", type="Bool")],
        argument_collections=[[False, True]], case_count=2),
    "unlinkRejectsDeniedAuthorityAtEntry": plain(),
    "unlinkRejectsForeignSpaceBeforeRead": plain(),
    "unlinkRechecksAuthorityAfterSuspendedRead": plain(),
    "cancelledUnlinkDoesNotMutateAfterRead": plain(),
    "unlinkRemovesOnlyTheSelectedCanonicalSource": plain(),
    "noteUnlinkStopsBeforeBothSourceAndOriginMutationWhenRevoked": plain(),
}


def validate_source(text):
    declarations = core.inspect_declarations(text)
    core.require(declarations == METHODS, "T5 host named declarations or exact literal cases changed")
    core.require(len(METHODS) == METHOD_COUNT
                 and sum(value["case_count"] for value in METHODS.values()) == CASE_COUNT,
                 "T5 host source method/case scope differs")
    return {SUITE + "/" + name for name in METHODS}


def source_contract(app):
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    candidates = [name for name in tracked if name.casefold() == SOURCE_PATH.casefold()]
    core.require(len(candidates) == 1, "Missing or case-colliding tracked T5 host source")
    actual, synced = app / candidates[0], app / SOURCE_PATH
    core.require(synced.is_file() and actual.samefile(synced), "T5 host source is outside the synchronized Xcode root")
    data = actual.read_bytes()
    methods = validate_source(data.decode("utf-8"))
    identifiers = ["AnytypeTests/" + SUITE + "/" + name + "("
                   + "".join(parameter["name"] + ":" for parameter in spec["parameters"]) + ")"
                   for name, spec in METHODS.items()]
    return dict(source_path=candidates[0], source_sha256=hashlib.sha256(data).hexdigest(),
                methods=sorted(methods), compiled_identifiers=sorted(identifiers),
                expected_methods=METHOD_COUNT, declared_cases=CASE_COUNT)


def validate_results(summary, tree, udid):
    expected = {SUITE + "/" + name for name in METHODS}
    actual = host.validate_results(summary, tree, expected, udid)
    cases = core.validate_arguments(tree, expected, {SUITE: {"methods": METHODS}})
    core.require(actual["counts"]["totalTestCount"] in {METHOD_COUNT, CASE_COUNT},
                 "T5 host summary differs from exact11 methods or12 literal cases")
    core.require(cases["actual_method_count"] == METHOD_COUNT and cases["declared_case_count"] == CASE_COUNT,
                 "T5 host actual named/argument execution is incomplete")
    return dict(actual, **cases)


def validate_enumeration(payload, contract):
    plan, enabled, disabled = existing.enumerated_identifiers(payload)
    core.require(enabled == set(contract["compiled_identifiers"]) and not enabled.intersection(disabled),
                 "Compiled pending T5 suite differs from exact11 declarations; no tests executed")
    return dict(test_plan=plan, identifiers=sorted(enabled), tests_executed=0)


def execute(*, app, build, selection, evidence, pair, ui, source, run_id):
    core.require(not evidence.exists(), "Refuse stale T5 host execution evidence")
    evidence.mkdir(parents=True)
    contract = source_contract(app)
    configuration = Path(build["configuration"])
    built, app_executable, _, test_executable = host.xctest_products(configuration)
    core.require(built.resolve() == Path(build["app"]).resolve()
                 and build.get("app_source_sha") == source,
                 "T5 host tests must reuse this same corrected application build")
    binding = {"app_executable_sha256": pair.digest(app_executable),
               "test_executable_sha256": pair.digest(test_executable),
               "original_xctestrun_sha256": pair.digest(configuration)}
    selected = configuration.with_name("UI27-T5-host-" + uuid4().hex + ".xctestrun")
    selected_binding = existing.scoped_configuration(
        configuration, selected, ["AnytypeTests/" + SUITE], pair)
    udid = selection["udid"]
    base = ["xcodebuild", "test-without-building", "-xctestrun", str(selected),
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
            "-only-testing:AnytypeTests/" + SUITE]
    receipt = dict(status="RUNNING", phase="SIMULATOR_READINESS", app_source_sha=source, run_id=run_id,
                   source=contract, built_products=binding, selected_configuration=selected_binding,
                   additional_app_builds=0, real_native_acl_accepted=False,
                   real_native_persistence_accepted=False)
    pair.write(evidence / "execution.json", receipt)

    def verify_binding():
        core.require(source_contract(app) == contract and pair.git(app, "rev-parse", "HEAD") == source,
                     "T5 host source changed during execution")
        core.require(pair.digest(app_executable) == binding["app_executable_sha256"]
                     and pair.digest(test_executable) == binding["test_executable_sha256"]
                     and pair.digest(configuration) == binding["original_xctestrun_sha256"]
                     and pair.digest(selected) == selected_binding["sha256"]
                     and ui.code_carriers(built)["sha256"] == build["code_sha256"],
                     "T5 host execution changed its original or selected App products")

    failure = None
    try:
        receipt["simulator_readiness"] = simulator.ensure_ready(app=app, evidence=evidence / "readiness",
            selection=selection, expected_name="Pinkha-UI27-" + run_id + "-ipad", pair=pair)
        receipt["phase"] = "COMPILED_SELECTION"
        pair.write(evidence / "execution.json", receipt)
        inventory = evidence / "compiled-enumeration.json"
        enumerate_command = [*base, "-enumerate-tests", "-test-enumeration-style", "flat",
                             "-test-enumeration-format", "json", "-test-enumeration-output-path", str(inventory)]
        pair.run_logged(enumerate_command, app, evidence, "enumerate", 180)
        receipt["enumeration"] = dict(validate_enumeration(
            json.loads(inventory.read_text(encoding="utf-8")), contract), source_sha256=pair.digest(inventory))
        verify_binding()
        bundle = evidence / "original.xcresult"
        command = [*base, "-test-timeouts-enabled", "YES",
                   "-default-test-execution-time-allowance", "300",
                   "-maximum-test-execution-time-allowance", "300", "-resultBundlePath", str(bundle)]
        receipt.update(phase="ACTUAL_HOST_TESTS", command=command)
        pair.write(evidence / "execution.json", receipt)
        outcome = None
        interrupted = False
        try:
            outcome, _ = pair.run_logged(command, app, evidence, "test", 600, check=False)
        except KeyboardInterrupt:
            interrupted = True
            raise
        finally:
            if bundle.exists() and not interrupted:
                for mode in ("summary", "tests"):
                    pair.run_logged(["xcrun", "xcresulttool", "get", "test-results", mode,
                                     "--path", str(bundle), "--format", "json"], app, evidence,
                                    "export-" + mode, 120, check=False, output=evidence / (mode + ".json"))
        core.require(outcome and outcome.get("return_code") == 0 and not outcome.get("timed_out"),
                     "Actual T5 host command failed")
        summary, tree = [json.loads((evidence / (mode + ".json")).read_text(encoding="utf-8"))
                         for mode in ("summary", "tests")]
        actual = validate_results(summary, tree, udid)
        verify_binding()
        receipt.update(status=PASS, phase="COMPLETE", actual=actual,
                       raw_summary_sha256=pair.digest(evidence / "summary.json"),
                       raw_tests_sha256=pair.digest(evidence / "tests.json"))
    except BaseException as error:
        failure = error
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
        raise
    finally:
        try:
            receipt["simulator_shutdown"] = simulator.shutdown_owned(app=app, evidence=evidence / "shutdown",
                selection=selection, expected_name="Pinkha-UI27-" + run_id + "-ipad", pair=pair,
                readiness_receipt_path=evidence / "readiness/readiness.json")
        except BaseException as cleanup_error:
            receipt.update(status="CANCELLED" if isinstance(cleanup_error, KeyboardInterrupt) else "FAIL",
                           cleanup_error_type=type(cleanup_error).__name__, cleanup_error=str(cleanup_error))
            if failure is None:
                raise
        finally:
            pair.write(evidence / "execution.json", receipt)
    return receipt
