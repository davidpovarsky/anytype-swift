#!/usr/bin/env python3
"""Use actually qualified selector grammar in one current SDK06 Debug build.

Historical7293 Products prove selector grammar only. The current build uses the
separately qualified45091223011 runtime, re-enumerates exact23+7, and retains the
unchanged23-method/32-case, acknowledgement7, native1/UI1 and live-runtime gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import subprocess
import sys
import zipfile

import coherent_original_preflight as lifecycle
# This existing lane dependency must be loaded before freezing the worker closure.
import coherent_original_products
import early_build_products
import run_owned_single_lane as supervisor
import run_wave15_acceptance as lane
import sdk06_enumeration_probe as probe
import sdk06_qualified_selector as selector
import wave15_batch as owned

PROTOCOL = "sdk06-current-build-qualified-selector-v1"
PROFILE = "sdk06-qualified"
RUNTIME_PROFILE = "r15-attachment-authorized-current-read-v1"
PRODUCER_RUN = "45091223011"
ADMISSION = "Tools/PinkhaSimulatorGate/sdk06-selector-admission.json"
CACHE_SOURCE = "d254a4a1ccd9288f585ff9374088cbaf965b36b4"
CACHE_KEY = ("pinkha-ui27-compiled-v2-arm64-xcode27.0-Debug-Anytype-"
    "039ba744ad174afaafa75d5ab1365ef3bd59d490bbb0c9e0573c4e1c49f9799a-" + CACHE_SOURCE)
CACHE_INPUTS = (
    "Modules/PinkhaKit/Package.swift", "Anytype.xcodeproj/project.pbxproj",
    "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
    "Tools/Hanlin/source.json",
)
require = selector.require


def save(path, value):
    lifecycle.save(path, value)


def current_identity(app):
    binding = lifecycle.context()
    lifecycle.identity(binding)
    head = subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True, timeout=30).strip()
    branch = subprocess.check_output(["git", "-C", str(app), "branch", "--show-current"], text=True, timeout=30).strip()
    lane.require_source_identity(head, binding["source_sha"], branch, os.environ.get("GITHUB_REF"))
    return binding


def fixed_admission(app):
    path = app / ADMISSION
    value = selector.admission(selector.read(path))
    original = subprocess.check_output(["git", "-C", str(app), "show", "HEAD:" + ADMISSION], timeout=30)
    require(path.read_bytes() == original, "Selector admission must be the exact committed reviewed file")
    return path, value


def loaded_sources(app):
    result = {}
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw: continue
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(app / "Tools"):
            result[path.relative_to(app).as_posix()] = owned.digest(path)
    require("Tools/PinkhaSimulatorGate/sdk06_qualified_continuation.py" in result
            and "Tools/PinkhaSimulatorGate/sdk06_qualified_selector.py" in result,
            "Current continuation source closure is incomplete")
    return dict(sorted(result.items()))


def retained(app):
    from sdk06_retained_controls import verify_retained_controls
    return verify_retained_controls(app)


def cache_binding(app):
    current, original = {}, {}
    for name in CACHE_INPUTS:
        current[name] = owned.digest(app / name)
        raw = subprocess.check_output(["git", "-C", str(app), "show", CACHE_SOURCE + ":" + name], timeout=30)
        original[name] = hashlib.sha256(raw).hexdigest()
    require(current == original, "The exact original compilation-cache input contract changed")
    return dict(status="COMPATIBLE_COMPILATION_ACCELERATOR_ONLY", source_sha=CACHE_SOURCE,
                key=CACHE_KEY, inputs=current, accepted_current_binary_evidence=False,
                current_app_build_required=True)


def extract_probe_files(archive_path, destination, approved):
    require(not destination.exists() and not destination.is_symlink(), "Refuse stale qualified-probe files")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        require(len(infos) <= 20000 and len({row.filename for row in infos}) == len(infos),
                "Duplicate or unbounded probe artifact inventory")
        for info in infos:
            name = PurePosixPath(info.filename)
            require(not name.is_absolute() and "\\" not in info.filename
                    and all(p not in {"", ".", ".."} for p in name.parts)
                    and not stat.S_ISLNK(info.external_attr >> 16), "Unsafe probe artifact member")
        require(set(approved["files"]) <= {row.filename for row in infos}, "Pinned probe originals are missing")
        total = 0
        for name, checksum in approved["files"].items():
            info = archive.getinfo(name); total += info.file_size
            require(0 < info.file_size <= 4 * 1024**2 and total <= 24 * 1024**2,
                    "Unbounded exact selector original")
            raw = archive.read(info)
            require(hashlib.sha256(raw).hexdigest() == checksum, "Original selector file digest differs")
            path = destination / name; path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output: output.write(raw)


def existing_plan(app, evidence):
    admission_path, approved = fixed_admission(app)
    root = evidence / "qualified-selector"
    plan = selector.load_plan(admission_path, root / "originals",
        selector.read(root / "run-api.json"), selector.read(root / "artifact-api.json"),
        lane.shared_editor_existing_build.source_contract(app), control=app)
    require(approved["qualified_variant"] == json.loads(plan.variant_json)["name"], "Qualified selector differs")
    return plan


def admit(app, work, evidence):
    binding = current_identity(app)
    admission_path, approved = fixed_admission(app)
    require(not work.exists() and not work.is_symlink(), "Fresh selector download directory required")
    work.mkdir(parents=True)
    directory = evidence / "qualified-selector"; directory.mkdir(parents=True, exist_ok=False)
    receipt = dict(protocol=PROTOCOL, status="FAIL", phase="SELECTOR_ADMISSION", **binding,
                   app_builds=0, actual_product_tests_executed=0, original_7293_products_relabelled=False,
                   full_matrix_accepted=False, release_accepted=False, sdk06_accepted=False)
    save(directory / "admission.json", receipt)
    try:
        receipt["retained_controls"] = retained(app)
        receipt["compilation_cache"] = cache_binding(app)
        commands = directory / "commands"; commands.mkdir()
        runner = probe.Commands(app, commands, receipt)
        run = runner.json(["gh", "api", "repos/" + probe.REPOSITORY + "/actions/runs/" +
            approved["probe_run_id"] + "/attempts/" + approved["probe_run_attempt"]], "qualified-probe-run")
        artifact = runner.json(["gh", "api", "repos/" + probe.REPOSITORY + "/actions/artifacts/" +
            str(approved["artifact_id"])], "qualified-probe-artifact")
        selector.original_api(run, artifact, approved)
        save(directory / "run-api.json", run); save(directory / "artifact-api.json", artifact)
        archive = work / "qualified-probe-original.zip"
        runner.run(["gh", "api", "repos/" + probe.REPOSITORY + "/actions/artifacts/" +
            str(approved["artifact_id"]) + "/zip"], "download-qualified-probe", timeout=300, destination=archive)
        require(archive.stat().st_size == approved["artifact_bytes"]
                and owned.digest(archive) == approved["artifact_sha256"], "Original probe API artifact bytes differ")
        extract_probe_files(archive, directory / "originals", approved)
        plan = existing_plan(app, evidence)
        receipt.update(status="SELECTOR_GRAMMAR_ADMITTED_CURRENT_PRODUCTS_NOT_YET_BUILT",
            selector_admission_sha256=plan.admission_sha256,
            actual_original_probe=dict(run_id=approved["probe_run_id"], run_attempt=approved["probe_run_attempt"],
                source_sha=approved["probe_source_sha"], artifact_id=approved["artifact_id"],
                artifact_sha256=approved["artifact_sha256"], variant=approved["qualified_variant"]),
            current_test_selection=json.loads(plan.selection_json), current_controller_sources=loaded_sources(app))
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt["finished_at"] = owned.now(); save(directory / "admission.json", receipt)
    return receipt


def prepare(app, evidence):
    binding = current_identity(app)
    plan = existing_plan(app, evidence); plan.verify(); retained(app)
    return lifecycle.prepare(app, evidence, binding, profile=PROFILE)


def cleanup(app, evidence):
    binding = current_identity(app)
    destination = evidence / "preflight/lifecycle-cleanup.json"
    if destination.exists():
        original = selector.read(destination)
        require(original.get("protocol") == lifecycle.SDK_PROTOCOL and original.get("action") == "cleanup"
                and all(original.get(key) == value for key, value in binding.items())
                and original.get("finished_at"), "Existing SDK cleanup is not from this exact attempt")
        if original.get("status") == "PASS":
            intent = evidence / "preflight/lifecycle/intent.json"
            require(original.get("intent_sha256") == owned.digest(intent), "SDK cleanup journal changed")
            lifecycle.admitted_journal(evidence / "preflight", binding, profile=PROFILE)
            fallback = evidence / "preflight/lifecycle/batch-cleanup.json"
            require(original.get("fallback_cleanup_sha256") == owned.digest(fallback)
                    and original.get("fallback_cleanup") == selector.read(fallback)
                    and original["fallback_cleanup"].get("status") == "PASS",
                    "Existing SDK cleanup lacks its own actual bounded cleanup receipt")
        else:
            require(original.get("status") in {"FAIL", "NO_OWNED_CREATION"}, "Unknown original cleanup state")
            if original["status"] == "NO_OWNED_CREATION":
                journal = evidence / "preflight/lifecycle/intent.json"
                if journal.exists():
                    _, known, attempted = lifecycle.admitted_journal(
                        evidence / "preflight", binding, profile=PROFILE)
                    require(attempted == 0 and not known, "No-creation cleanup cannot hide later creation")
                else:
                    require(not (evidence / "preflight/lifecycle/lanes").exists(),
                            "No-creation cleanup cannot hide later creation")
        return original
    return lifecycle.cleanup(app, evidence, binding, profile=PROFILE)


def capture_later_ui(derived, evidence, *, source_sha, run_id, run_attempt, build_flags):
    """One exact separate UI archive; no build/acceptance-reuse authority."""
    prefix = "sdk06-ui"
    result = early_build_products.capture(derived, evidence / prefix, source_sha=source_sha,
        run_id=run_id, run_attempt=run_attempt, build_flags=build_flags, scope="sdk06")
    return {**result, "archive_path": prefix + "/" + result["archive_path"],
        "manifest_path": prefix + "/" + result["manifest_path"],
        "build_origin": "CURRENT_ATTEMPT_UI_BUILD_BEFORE_ADMISSION", "acceptance_reused": False}


def worker(app, evidence, derived):
    binding = current_identity(app)
    require(not (evidence / "execution.json").exists(), "Refuse stale current SDK worker evidence")
    receipt = dict(protocol=PROTOCOL, status="FAIL", phase="PREFLIGHT", **binding,
                   started_at=owned.now(), full_matrix_accepted=False, release_accepted=False,
                   original_7293_products_relabelled=False)
    save(evidence / "execution.json", receipt)
    sources = None
    try:
        plan = existing_plan(app, evidence)
        receipt["retained_controls"] = retained(app)
        sources = loaded_sources(app); receipt["current_controller_sources"] = sources
        receipt["qualified_selector_admission_sha256"] = plan.admission_sha256
        args = argparse.Namespace(app=app, evidence=evidence, derived=derived,
            lane="hanlin-native", device="ipad", language="en", runtime_profile=RUNTIME_PROFILE,
            heart_source_run_id=PRODUCER_RUN, include_text_native_ack=True, include_shared_editor=True,
            sdk06_qualified_selector_plan=plan)
        lane.execute(args, receipt)
        plan.verify()
        require(retained(app) == receipt["retained_controls"], "Retained original control admission changed")
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        if receipt.get("native_build_succeeded"):
            try:
                receipt["compiled_products"] = lane.shared.capture_products(derived, evidence,
                    receipt["source_sha"], receipt["native_build_flags"])
            except BaseException as error:
                receipt["compiled_products"] = dict(status="CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED", error=str(error))
        try:
            require(sources is not None and loaded_sources(app) == sources, "Loaded controller source closure changed")
            receipt["current_controller_sources_unchanged"] = True
        except BaseException as error:
            receipt["final_source_integrity_failure"] = dict(error_type=type(error).__name__, error=str(error))
            receipt["status"] = "FAIL"
        receipt["finished_at"] = owned.now(); save(evidence / "execution.json", receipt)
        lane.diagnostics.emit_execution(receipt, "hanlin-native-shared-editor")
    return 0 if receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


def execute(app, work, evidence, derived):
    binding = current_identity(app)
    plan = existing_plan(app, evidence); plan.verify(); retained(app)
    supervisor.preflight_intent(evidence, binding)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "worker",
               "--app", str(app), "--work", str(work), "--evidence", str(evidence), "--derived", str(derived)]
    def owned_cleanup():
        original = cleanup(app, evidence)
        require(original.get("status") == "PASS", "SDK owned simulator cleanup did not pass")
        return original
    return supervisor.supervise(command, app, evidence, context=binding, cleanup=owned_cleanup,
                                cleanup_profile=PROFILE)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=("admit", "prepare", "execute", "worker", "cleanup"))
    for name in ("app", "work", "evidence", "derived"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    app, work, evidence, derived = (getattr(args, key).resolve() for key in ("app", "work", "evidence", "derived"))
    require(app == Path(__file__).resolve().parents[2] and
            all(path.is_relative_to(app / "build") and path != app / "build" for path in (work, evidence, derived))
            and len({work, evidence, derived}) == 3 and
            all(not first.is_relative_to(second) for first in (work, evidence, derived)
                for second in (work, evidence, derived) if first != second),
            "Exact controller-owned current build paths required")
    lifecycle.actual_host(); evidence.mkdir(parents=True, exist_ok=True)
    previous = {}
    def cancel(signum, frame): raise KeyboardInterrupt("Qualified SDK continuation cancelled")
    try:
        if args.action not in {"execute", "worker"}:
            for number in (signal.SIGTERM, signal.SIGINT):
                previous[number] = signal.getsignal(number); signal.signal(number, cancel)
        if args.action == "execute": return execute(app, work, evidence, derived)
        if args.action == "worker": return worker(app, evidence, derived)
        result = (admit(app, work, evidence) if args.action == "admit" else
                  prepare(app, evidence) if args.action == "prepare" else cleanup(app, evidence))
        print(json.dumps({key: result.get(key) for key in ("status", "source_sha", "run_id", "run_attempt")}))
        return 0 if result["status"] in {"SELECTOR_GRAMMAR_ADMITTED_CURRENT_PRODUCTS_NOT_YET_BUILT",
            "PREFLIGHT_PASS_UI_NOT_RUN", "PASS", "NO_OWNED_CREATION"} else 1
    finally:
        for number, handler in previous.items(): signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())
