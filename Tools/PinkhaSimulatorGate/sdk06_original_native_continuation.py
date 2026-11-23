"""One current-controller continuation over original451394 native Products.

Only the first UI-only runner build is permitted. The native App/source origin
stays75bd, independently of the current reviewed controller source/run identity.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONTRACT = "Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
for directory in ("Tools/PinkhaNativeDerived", "Tools/Hanlin", "Tools/PinkhaSimulatorGate"):
    value = str(ROOT / directory)
    if value not in sys.path:
        sys.path.insert(0, value)


def require(value, message):
    if not value:
        raise ValueError(message)


def _source_bytes(control):
    """Current Git/physical admission, including modules before their import."""
    raw = (control / SOURCE_CONTRACT).read_bytes()
    contract = json.loads(raw)
    require(contract.get("protocol") == "sdk06-original-native-controller-source-v1",
            "Unknown current-controller source contract")
    inputs = contract["inputs"]
    require(isinstance(inputs, dict) and 1 <= len(inputs) <= 120,
            "Unexpected current-controller source closure size")
    names = sorted(set(inputs) | {SOURCE_CONTRACT})
    require(all(name and not name.startswith("/") and "\\" not in name
                and all(part not in {"", ".", ".."} for part in name.split("/")) for name in names),
            "Controller source paths must be exact relative members")
    head = subprocess.check_output(["git", "-C", str(control), "rev-parse", "HEAD"],
                                   text=True, timeout=30).strip()
    tree_raw = subprocess.check_output(["git", "-C", str(control), "ls-tree", "-r", "-z",
                                       head, "--", *names], timeout=30)
    tree = {}
    for entry in tree_raw.split(b"\0"):
        if entry:
            meta, name = entry.split(b"\t", 1)
            mode, kind, object_id = meta.decode().split()
            require(kind == "blob" and mode in {"100644", "100755"}, "Unsupported controller source mode")
            tree[name.decode()] = (mode, object_id)
    require(set(tree) == set(names), "The complete current-controller closure must be tracked")
    requested = b"".join((tree[name][1] + "\n").encode() for name in names)
    data = subprocess.check_output(["git", "-C", str(control), "cat-file", "--batch"],
                                   input=requested, timeout=30)
    offset, result = 0, {}
    for name in names:
        end = data.index(b"\n", offset)
        object_id, kind, size_raw = data[offset:end].split()
        size = int(size_raw)
        start = end + 1
        blob = data[start:start + size]
        require(kind == b"blob" and object_id.decode() == tree[name][1]
                and len(blob) == size and data[start + size:start + size + 1] == b"\n",
                "Current Git source response differs")
        offset = start + size + 1
        path = control / name
        current = control
        for part in name.split("/"):
            current = current / part
            require(not current.is_symlink(), "Controller source traverses a link")
        observed = path.lstat()
        require(stat.S_ISREG(observed.st_mode) and path.read_bytes() == blob
                and bool(observed.st_mode & 0o111) == (tree[name][0] == "100755"),
                "Current controller physical/Git bytes or mode differ: " + name)
        digest = hashlib.sha256(blob).hexdigest()
        if name != SOURCE_CONTRACT:
            require(inputs[name] == {"sha256": digest, "git_mode": tree[name][0]},
                    "An unreviewed current-controller input changed: " + name)
        result[name] = {"sha256": digest, "git_mode": tree[name][0]}
    require(offset == len(data), "Extra current source response bytes")
    for name, relative in contract["modules"].items():
        require(relative in inputs and relative.endswith(".py"), "Unbound repository module")
        canonical = (control / relative).resolve()
        loaded = sys.modules.get(name)
        if loaded is not None:
            require(Path(getattr(loaded, "__file__", "")).resolve() == canonical,
                    "An already loaded repository module has a foreign origin: " + name)
        spec = importlib.util.find_spec(name)
        require(spec is not None and Path(spec.origin or "").resolve() == canonical,
                "A repository import resolves outside its current source closure: " + name)
    return head, result, contract


# This checks exact physical/Git bytes and canonical origins before repository
# helpers can execute top-level imports. It invokes no controller test method.
_INITIAL_SOURCE = _source_bytes(ROOT)

import coherent_original_preflight as lifecycle
import run_owned_single_lane as supervisor
import run_wave15_acceptance as lane
import sdk06_original_native as origin
import sdk06_original_tagged_selector as selection
import sdk06_qualified_continuation as qualified
import sdk06_tagged_selector as retained_tagged


def loaded_sources(control, contract):
    result = {}
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(control):
            relative = path.relative_to(control).as_posix()
            require(relative in contract["inputs"], "An unbound repository module was imported: " + relative)
            result[relative] = origin.sha(path)
    for name, relative in contract["modules"].items():
        loaded = sys.modules.get(name)
        if loaded is not None:
            require(Path(getattr(loaded, "__file__", "")).resolve() == control / relative,
                    "A current module origin changed after import")
    return dict(sorted(result.items()))


def preload_current_sources(control, contract):
    """Load only the declared production closure before a frozen loaded snapshot."""
    names = contract["preload_modules"]
    expected = sorted(name for name in contract["modules"]
                      if not name.startswith("test_") and name != Path(__file__).stem)
    require(names == expected, "Current production preloads must equal the fixed declared closure")
    if __name__ == "__main__":
        name = Path(__file__).stem
        current = sys.modules[__name__]
        existing = sys.modules.get(name)
        require(existing is None or existing is current, "Duplicate current entrypoint module identity")
        if existing is None:
            current.__spec__ = importlib.util.spec_from_file_location(name, Path(__file__))
            sys.modules[name] = current
    for name in names:
        module = importlib.import_module(name)
        require(Path(getattr(module, "__file__", "")).resolve() ==
                control / contract["modules"][name],
                "A declared production preload resolved to a foreign source: " + name)
    return loaded_sources(control, contract)


def verify_controller(control, binding=None):
    require(control.resolve() == ROOT, "The current controller belongs to another checkout")
    head, inputs, contract = _source_bytes(control)
    actual = qualified.current_identity(control)
    require(actual["source_sha"] == head and (binding is None or actual == binding),
            "Current controller/run/attempt identity changed")
    loaded = preload_current_sources(control, contract)
    return {"binding": actual, "actual_current_inputs": inputs, "loaded_repository_sources": loaded}


def paths(args):
    control = args.control.resolve(strict=True)
    app = args.original_app.resolve(strict=True)
    work, evidence, derived = (getattr(args, name).resolve() for name in ("work", "evidence", "derived"))
    require(control == ROOT and app == control / "build/sdk06-original-app"
            and app != control and (app / ".git").exists(), "The original App must be its exact separate checkout")
    owned = (work, evidence, derived)
    require(len(set(owned)) == 3 and all(path.is_relative_to(control / "build")
            and path != control / "build" and path != app and not path.is_relative_to(app)
            and not app.is_relative_to(path) for path in owned)
            and all(not a.is_relative_to(b) for a in owned for b in owned if a != b),
            "Distinct current-controller-owned evidence/work/Products paths are required")
    return control, app, work, evidence, derived


def admit(control, app, work, evidence, derived):
    current = verify_controller(control)
    binding = current["binding"]
    require(not derived.exists() and not derived.with_name(derived.name + "-ui").exists(),
            "Original native restoration and first UI build must start with fresh output roots")
    receipt = {"protocol": origin.PROTOCOL, "status": "FAIL", "phase": "ORIGINAL_NATIVE_ADMISSION",
               **binding, "app_source_sha": origin.SOURCE, "native_builds_this_run": 0,
               "product_tests_executed": 0, "selector_qualified": False,
               "ui_build_status": "NOT_RUN", "sdk06_accepted": False}
    evidence.mkdir(parents=True, exist_ok=True)
    destination = evidence / "original-native-admission.json"
    require(not destination.exists(), "A fixed original-native admission cannot be repeated")
    origin.save(destination, receipt, original=True)
    try:
        contract = origin.manifest(control)
        origin.download_original(control, work, evidence, contract)
        receipt["restoration"] = origin.restore_original(control, app, work, evidence, derived, contract)
        # Revalidate immutable original metadata. This does not rerun retained
        # controller tests and does not qualify a new tag selection.
        source = retained_tagged.source_admission(app)
        original = origin.read(evidence / "original-native/execution.json")["source_admission"]
        require(source["selection"] == original["selection"]
                and source["actual_current_inputs"] == original["actual_current_inputs"],
                "Restored original tag/declaration/controller-source metadata differs")
        receipt["original_source_metadata"] = source
        receipt["retained_control_origin"] = {
            "kind": "ORIGINAL_451394_RETAINED_SOURCE_EVIDENCE",
            "receipt_sha256": contract["metadata_members"]["tagged-source/admission.json"]["sha256"],
            "old_controller_tests_executed_now": 0,
            "new_controller_qualified_by_this_receipt": False,
        }
        receipt["current_controller_sources"] = verify_controller(control, binding)
        receipt.update(status="ORIGINAL_NATIVE_RESTORED_CURRENT_SELECTION_NOT_RUN", phase="ADMITTED")
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        origin.save(destination, receipt)
    return receipt


def existing_admission(control, app, evidence):
    current = verify_controller(control)
    receipt = origin.read(evidence / "original-native-admission.json")
    require(receipt.get("protocol") == origin.PROTOCOL
            and receipt.get("status") == "ORIGINAL_NATIVE_RESTORED_CURRENT_SELECTION_NOT_RUN"
            and all(receipt.get(key) == value for key, value in current["binding"].items())
            and receipt.get("app_source_sha") == origin.SOURCE
            and receipt.get("selector_qualified") is False
            and receipt.get("native_builds_this_run") == 0,
            "Original-native admission does not belong to this current controller attempt")
    require(origin.verify_app_source(app,
            origin.read(evidence / "original-native/compiled-products/source-inputs.json"),
            origin.manifest(control)) == receipt["restoration"]["source_fingerprints"],
            "Original App source changed after restoration")
    return current["binding"]


def prepare(control, app, work, evidence, derived):
    binding = existing_admission(control, app, evidence)
    return lifecycle.prepare(control, evidence, binding, profile=origin.PROFILE)


def worker(control, app, work, evidence, derived):
    binding = existing_admission(control, app, evidence)
    receipt = {"protocol": origin.PROTOCOL, "status": "FAIL", "phase": "PREFLIGHT", **binding,
               "app_source_sha": origin.SOURCE, "controller_source_sha": binding["source_sha"],
               "native_builds_this_run": 0, "ui_build_status": "NOT_RUN",
               "full_matrix_accepted": False, "release_accepted": False,
               "native_acceptance_reused": False, "ui_acceptance_reused": False}
    require(not (evidence / "execution.json").exists(), "Refuse stale original-native execution evidence")
    origin.save(evidence / "execution.json", receipt, original=True)
    context, before = None, None
    try:
        before = verify_controller(control, binding)
        context = origin.load_context(control, app, work, evidence, derived, binding)
        plan = selection.load_plan(context)
        args = argparse.Namespace(app=app, evidence=evidence, derived=derived,
            lane="hanlin-native", device="ipad", language="en",
            runtime_profile=origin.RUNTIME_PROFILE, heart_source_run_id=origin.PRODUCER_RUN,
            include_text_native_ack=True, include_shared_editor=True,
            sdk06_original_native_tagged_plan=plan)
        lane.execute(args, receipt, sdk06_original_native=context)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        try:
            if context is not None:
                context.verify_current(full=True)
                receipt["original_native_products_unchanged"] = True
            require(before is not None and verify_controller(control, binding) == before,
                    "Current controller/source closure changed")
            receipt["current_controller_sources_unchanged"] = True
        except BaseException as error:
            receipt.update(status="FAIL", final_source_integrity_failure={
                "error_type": type(error).__name__, "error": str(error)})
        receipt["finished_at"] = lifecycle.batch.now()
        origin.save(evidence / "execution.json", receipt)
        lane.diagnostics.emit_execution(receipt, "hanlin-native-shared-editor")
    return 0 if receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


def execute(control, app, work, evidence, derived):
    binding = existing_admission(control, app, evidence)
    supervisor.preflight_intent(evidence, binding)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "worker",
        "--control", str(control), "--original-app", str(app), "--work", str(work),
        "--evidence", str(evidence), "--derived", str(derived)]
    def cleanup():
        result = qualified.cleanup(control, evidence)
        require(result.get("status") == "PASS", "Current SDK owned simulator cleanup did not pass")
        return result
    return supervisor.supervise(command, control, evidence, context=binding,
                                cleanup=cleanup, cleanup_profile=origin.PROFILE)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=("admit", "prepare", "execute", "worker", "cleanup"))
    for name in ("control", "original-app", "work", "evidence", "derived"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    control, app, work, evidence, derived = paths(args)
    lifecycle.actual_host()
    evidence.mkdir(parents=True, exist_ok=True)
    previous = {}
    def cancel(signum, frame):
        raise KeyboardInterrupt("Original-native SDK continuation cancelled")
    try:
        if args.action not in {"execute", "worker"}:
            for number in (signal.SIGTERM, signal.SIGINT):
                previous[number] = signal.getsignal(number)
                signal.signal(number, cancel)
        if args.action == "execute":
            return execute(control, app, work, evidence, derived)
        if args.action == "worker":
            return worker(control, app, work, evidence, derived)
        result = (admit(control, app, work, evidence, derived) if args.action == "admit" else
                  prepare(control, app, work, evidence, derived) if args.action == "prepare" else
                  qualified.cleanup(control, evidence))
        print(json.dumps({key: result.get(key) for key in ("status", "source_sha", "run_id", "run_attempt")}))
        return 0 if result["status"] in {"ORIGINAL_NATIVE_RESTORED_CURRENT_SELECTION_NOT_RUN",
            "PREFLIGHT_PASS_UI_NOT_RUN", "PASS", "NO_OWNED_CREATION"} else 1
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())
