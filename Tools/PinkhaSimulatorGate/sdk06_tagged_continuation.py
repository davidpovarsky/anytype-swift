#!/usr/bin/env python3
"""Build current SDK06 once, then admit only its actual pending-tag enumeration.

The original 7293 Products are retained historical failures. A historical source
view reuses only fixed original controller evidence. It is never an App source,
selector qualification or product acceptance. The current build must pass
exact23 enumeration, exact32 argument cases, ack7, native1/UI1 and live mapping.
"""
import argparse
import json
from pathlib import Path
import signal
import sys

import sdk06_qualified_continuation as original
import sdk06_tagged_selector as tagged

PROTOCOL = tagged.PROTOCOL
require = tagged.require
save = original.save
lane = original.lane
lifecycle = original.lifecycle
supervisor = original.supervisor
owned = original.owned
PROFILE = original.PROFILE


def retained(app, work):
    return tagged.historical_retained_view(app, work / "historical-control-view")


def existing_plan(app, work, evidence):
    binding = original.current_identity(app)
    plan = tagged.load_plan(app, binding)
    admitted = tagged.original.read(evidence / "tagged-source/admission.json")
    require(admitted.get("protocol") == PROTOCOL
            and admitted.get("status") == "SOURCE_METADATA_ADMITTED_SELECTOR_NOT_RUN"
            and all(admitted.get(name) == value for name, value in binding.items())
            and admitted.get("source_admission") == json.loads(plan.source_json)
            and admitted.get("historical_view_root") == str((work / "historical-control-view").resolve())
            and admitted.get("selector_qualified") is False,
            "Current tag admission must belong to this exact source/run/attempt; it is not selector proof")
    return plan


def loaded_sources(app):
    result = original.loaded_sources(app)
    require(all(name in result for name in tagged.CONTROL_PATHS if name.endswith(".py")),
            "Tagged current controller source closure is incomplete")
    return result


def admit(app, work, evidence):
    binding = original.current_identity(app)
    require(not work.exists() and not work.is_symlink(), "Fresh owned tag continuation directory required")
    work.mkdir(parents=True)
    directory = evidence / "tagged-source"
    directory.mkdir(parents=True, exist_ok=False)
    receipt = dict(protocol=PROTOCOL, status="FAIL", phase="SOURCE_METADATA_ADMISSION", **binding,
        selector_qualified=False, app_builds=0, product_tests_executed=0,
        original_7293_products_relabelled=False, full_matrix_accepted=False, sdk06_accepted=False)
    save(directory / "admission.json", receipt)
    try:
        plan = tagged.load_plan(app, binding)
        tagged.validate_build_membership(app)
        receipt["source_admission"] = json.loads(plan.source_json)
        receipt["retained_controls"] = retained(app, work)
        receipt["historical_view_root"] = receipt["retained_controls"]["historical_view_root"]
        receipt["compilation_cache"] = original.cache_binding(app)
        receipt["current_controller_sources"] = loaded_sources(app)
        receipt["status"] = "SOURCE_METADATA_ADMITTED_SELECTOR_NOT_RUN"
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt["finished_at"] = owned.now()
        save(directory / "admission.json", receipt)
    return receipt


def prepare(app, work, evidence):
    plan = existing_plan(app, work, evidence)
    plan.verify()
    tagged.validate_build_membership(app)
    retained(app, work)
    return lifecycle.prepare(app, evidence, original.current_identity(app), profile=PROFILE)


def worker(app, work, evidence, derived):
    binding = original.current_identity(app)
    require(not (evidence / "execution.json").exists(), "Refuse stale current tag worker evidence")
    receipt = dict(protocol=PROTOCOL, status="FAIL", phase="PREFLIGHT", **binding,
        started_at=owned.now(), selector_qualified_before_build=False,
        full_matrix_accepted=False, release_accepted=False,
        original_7293_products_relabelled=False, historical_view_is_app_build_source=False)
    save(evidence / "execution.json", receipt)
    sources = None
    try:
        plan = existing_plan(app, work, evidence)
        tagged.validate_build_membership(app)
        receipt["source_admission"] = json.loads(plan.source_json)
        receipt["retained_controls"] = retained(app, work)
        sources = loaded_sources(app)
        receipt["current_controller_sources"] = sources
        args = argparse.Namespace(app=app, evidence=evidence, derived=derived,
            lane="hanlin-native", device="ipad", language="en",
            runtime_profile=original.RUNTIME_PROFILE, heart_source_run_id=original.PRODUCER_RUN,
            include_text_native_ack=True, include_shared_editor=True,
            sdk06_tagged_selection_plan=plan)
        # This is the real current checkout, never the historical control view.
        require(args.app.resolve() == Path(__file__).resolve().parents[2]
                and args.app.resolve() != (work / "historical-control-view").resolve(),
                "Historical source view cannot be built or tested as the App")
        lane.execute(args, receipt)
        plan.verify()
        require(retained(app, work) == receipt["retained_controls"], "Historical/current source bindings changed")
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        if receipt.get("native_build_succeeded"):
            try:
                receipt["compiled_products"] = lane.shared.capture_products(
                    derived, evidence, receipt["source_sha"], receipt["native_build_flags"])
            except BaseException as error:
                receipt["compiled_products"] = dict(status="CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED", error=str(error))
        try:
            require(sources is not None and loaded_sources(app) == sources, "Loaded tagged controller sources changed")
            receipt["current_controller_sources_unchanged"] = True
        except BaseException as error:
            receipt["final_source_integrity_failure"] = dict(error_type=type(error).__name__, error=str(error))
            receipt["status"] = "FAIL"
        receipt["finished_at"] = owned.now()
        save(evidence / "execution.json", receipt)
        lane.diagnostics.emit_execution(receipt, "hanlin-native-shared-editor")
    return 0 if receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


def execute(app, work, evidence, derived):
    plan = existing_plan(app, work, evidence)
    plan.verify()
    retained(app, work)
    binding = original.current_identity(app)
    supervisor.preflight_intent(evidence, binding)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "worker",
        "--app", str(app), "--work", str(work), "--evidence", str(evidence), "--derived", str(derived)]
    def cleanup():
        result = original.cleanup(app, evidence)
        require(result.get("status") == "PASS", "Current SDK owned simulator cleanup did not pass")
        return result
    return supervisor.supervise(command, app, evidence, context=binding,
                                cleanup=cleanup, cleanup_profile=PROFILE)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=("admit", "prepare", "execute", "worker", "cleanup"))
    for name in ("app", "work", "evidence", "derived"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    app, work, evidence, derived = (getattr(args, name).resolve() for name in ("app", "work", "evidence", "derived"))
    require(app == Path(__file__).resolve().parents[2]
            and all(path.is_relative_to(app / "build") and path != app / "build"
                    for path in (work, evidence, derived))
            and len({work, evidence, derived}) == 3
            and all(not first.is_relative_to(second) for first in (work, evidence, derived)
                    for second in (work, evidence, derived) if first != second),
            "Exact current controller-owned build paths are required")
    lifecycle.actual_host()
    evidence.mkdir(parents=True, exist_ok=True)
    previous = {}
    def cancel(signum, frame): raise KeyboardInterrupt("Current tagged SDK continuation cancelled")
    try:
        if args.action not in {"execute", "worker"}:
            for number in (signal.SIGTERM, signal.SIGINT):
                previous[number] = signal.getsignal(number)
                signal.signal(number, cancel)
        if args.action == "execute": return execute(app, work, evidence, derived)
        if args.action == "worker": return worker(app, work, evidence, derived)
        result = (admit(app, work, evidence) if args.action == "admit" else
                  prepare(app, work, evidence) if args.action == "prepare" else original.cleanup(app, evidence))
        print(json.dumps({name: result.get(name) for name in ("status", "source_sha", "run_id", "run_attempt")}))
        return 0 if result["status"] in {"SOURCE_METADATA_ADMITTED_SELECTOR_NOT_RUN",
            "PREFLIGHT_PASS_UI_NOT_RUN", "PASS", "NO_OWNED_CREATION"} else 1
    finally:
        for number, handler in previous.items(): signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())
