"""Execute exactly the three new SDK original-native offline controls once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import traceback
import unittest

DIRECTORY = "docs/validation/20261123-sdk06-original-native-continuation"
INPUTS = DIRECTORY + "/control-inputs.json"
INPUTS_SHA256 = "693ddd9f5a7044e0536611da2977c9579acb644a39b3a3e86eb59ad7afed9c2a"
ROOT_PATH = "/mnt/development/projects/worktrees/anytype-wave15-sdk06-original-native-20261123"
METHODS = (
    ("test_sdk06_original_tagged_selector", "OriginalTagSelectionControls",
     "test_original_descriptor_has_one_tag_only_selection_and_requires_actual23"),
    ("test_sdk06_original_native", "OriginalNativeContinuationControls",
     "test_fixed_original_origin_and_exact_restoration_refuse_source_or_entry_drift"),
    ("test_sdk06_original_native", "OriginalNativeContinuationControls",
     "test_actual_lane_stops_on_original30_and_ui_builder_cannot_rebuild_native"),
)
METADATA = (
    DIRECTORY + "/control-inputs.json",
    DIRECTORY + "/run-controls.py",
    DIRECTORY + "/source-review.json",
    DIRECTORY + "/source-plan.json",
    DIRECTORY + "/exact-source-inverses.json",
    DIRECTORY + "/selection-copy-inverse.json",
    DIRECTORY + "/current-static-closure.json",
)
RESERVE = 2_500_000_000
_CREATED_RESULTS = []


def require(value, message):
    if not value:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reserve(root, extra=0):
    free = shutil.disk_usage(root).free
    require(free - extra >= RESERVE, "Oracle 2.5 GB reserve would be crossed")
    return free


def write(path, value):
    require(not path.exists() and not path.is_symlink(), "Refuse to replace an original control artifact")
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    reserve(path.parent, len(raw) + 4096)
    with path.open("xb") as output:
        output.write(raw)
    return {"bytes": len(raw), "sha256": digest(raw)}


def git_blobs(root, source, names):
    raw = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-r", "-z", source, "--", *names],
                                  timeout=30)
    tree = {}
    for entry in raw.split(b"\0"):
        if entry:
            meta, name = entry.split(b"\t", 1)
            mode, kind, object_id = meta.decode().split()
            require(kind == "blob" and mode in {"100644", "100755"}, "Unsupported frozen Git mode")
            tree[name.decode()] = (mode, object_id)
    require(set(tree) == set(names), "A fixed source or metadata input is absent from frozen Git")
    order = sorted(names)
    raw = subprocess.check_output(["git", "-C", str(root), "cat-file", "--batch"],
        input=b"".join((tree[name][1] + "\n").encode() for name in order), timeout=30)
    offset, result = 0, {}
    for name in order:
        end = raw.index(b"\n", offset)
        oid, kind, size_raw = raw[offset:end].split()
        size = int(size_raw)
        start = end + 1
        data = raw[start:start + size]
        require(kind == b"blob" and oid.decode() == tree[name][1] and len(data) == size
                and raw[start + size:start + size + 1] == b"\n", "Malformed frozen Git response")
        offset = start + size + 1
        result[name] = (tree[name][0], tree[name][1], data)
    require(offset == len(raw), "Unexpected trailing Git source bytes")
    return result


def frozen_files(root, source):
    require(subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                   text=True, timeout=30).strip() == source,
            "Control source moved from its exact frozen commit")
    raw = (root / INPUTS).read_bytes()
    require(digest(raw) == INPUTS_SHA256, "The frozen control input map changed")
    manifest = json.loads(raw)
    require(manifest["protocol"] == "sdk06-original-native-three-controls-v1"
            and manifest["methods"] == ["/".join(item) for item in METHODS],
            "Only the three named new controls are admitted")
    names = set(manifest["inputs"]) | set(METADATA)
    require(0 < len(names) <= 180, "Unexpected fixed new-control input cardinality")
    blobs = git_blobs(root, source, sorted(names))
    result = {}
    for name in sorted(names):
        require(name and not name.startswith("/") and "\\" not in name
                and all(part not in {"", ".", ".."} for part in name.split("/")),
                "Control input is not an exact relative member")
        mode, oid, data = blobs[name]
        require(len(data) <= 8 * 1024**2, "Oversized fixed control input")
        path = root
        for part in name.split("/"):
            path = path / part
            require(not path.is_symlink(), "Fixed control input traverses a link")
        observed = path.lstat()
        require(stat.S_ISREG(observed.st_mode) and path.read_bytes() == data
                and bool(observed.st_mode & 0o111) == (mode == "100755"),
                "Physical frozen input differs from Git: " + name)
        value = {"sha256": digest(data), "bytes": len(data), "git_mode": mode, "git_blob": oid,
                 "physical_mode": stat.S_IMODE(observed.st_mode)}
        if name in manifest["inputs"]:
            require({key: value[key] for key in ("sha256", "bytes", "git_mode")} ==
                    manifest["inputs"][name], "A fixed source/dependency hash differs: " + name)
        result[name] = value
    return result, manifest


def loaded_sources(root, manifest):
    result = {}
    approved_tests = {item[0] for item in METHODS}
    for name, module in tuple(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if not path.is_relative_to(root) or path.suffix != ".py":
            continue
        relative = path.relative_to(root).as_posix()
        require(relative in manifest["inputs"], "An unbound repository module was loaded: " + relative)
        require(not path.stem.startswith("test_") or path.stem in approved_tests,
                "An old controller test module was imported")
        expected = manifest["inputs"][relative]
        actual = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
                  "git_mode": "100755" if path.stat().st_mode & 0o111 else "100644"}
        require(actual == expected, "A loaded repository module differs from frozen source")
        result[relative] = actual
    return dict(sorted(result.items()))


class NamedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []
        self.last_failure_reason = None
        _CREATED_RESULTS.append(self)

    def startTest(self, test):
        reserve(Path(ROOT_PATH), 4 * 1024**2)
        self.events.append({"event": "START", "method": test.id(), "at": now()})
        super().startTest(test)

    def addSuccess(self, test):
        self.events.append({"event": "PASS", "method": test.id(), "at": now()})
        super().addSuccess(test)

    def addFailure(self, test, error):
        self.events.append({"event": "FAIL", "method": test.id(), "at": now(),
                            "error_type": error[0].__name__, "error": str(error[1])})
        super().addFailure(test, error)

    def addError(self, test, error):
        self.events.append({"event": "ERROR", "method": test.id(), "at": now(),
                            "error_type": error[0].__name__, "error": str(error[1])})
        super().addError(test, error)

    def addSkip(self, test, reason):
        self.events.append({"event": "SKIP", "method": test.id(), "at": now(), "reason": reason})
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, error):
        self.events.append({"event": "SUBCASE_PASS" if error is None else "SUBCASE_FAIL",
                            "method": test.id(), "scope": str(subtest), "at": now(),
                            **({} if error is None else {
                                "error_type": error[0].__name__, "error": str(error[1])})})
        super().addSubTest(test, subtest, error)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    root, evidence = args.repository.resolve(strict=True), args.evidence.resolve()
    require(root == Path(ROOT_PATH) and len(args.source) == 40
            and all(c in "0123456789abcdef" for c in args.source), "Exact isolated source is required")
    executed_wrapper = Path(__file__).resolve(strict=True)
    require(not executed_wrapper.is_relative_to(root)
            and executed_wrapper.read_bytes() == (root / DIRECTORY / "run-controls.py").read_bytes(),
            "Execute only a byte-exact outside-repository copy of this frozen wrapper")
    require(not evidence.exists() and evidence.is_relative_to(Path("/mnt/development/projects/diagnostics"))
            and not evidence.is_relative_to(root), "Fresh separate diagnostic attempt directory required")
    reserve(root, 16 * 1024**2)
    evidence.mkdir(parents=True, exist_ok=False)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PINKHA_SDK06_NEW_CONTROL_ARTIFACTS"] = str(evidence / "artifacts")
    (evidence / "artifacts").mkdir()
    receipt = {"protocol": "sdk06-original-native-three-controls-v1", "status": "FAIL",
               "source_sha": args.source, "started_at": now(),
               "executed_wrapper_sha256": digest(executed_wrapper.read_bytes()),
               "planned_methods": ["/".join(item) for item in METHODS],
               "old_controller_methods_executed": 0, "product_tests_executed": 0,
               "Apple_builds": 0, "actual_selector_qualified": False,
               "actual_original_products_restoration": False}
    before = after = loaded_before = loaded_after = result = manifest = None
    error = None
    started = time.monotonic()
    try:
        before, manifest = frozen_files(root, args.source)
        write(evidence / "source-before.json", before)
        for directory in ("Tools/PinkhaNativeDerived", "Tools/Hanlin", "Tools/PinkhaSimulatorGate"):
            sys.path.insert(0, str(root / directory))
        modules = {}
        for name, _, _ in METHODS:
            if name not in modules:
                spec = importlib.util.find_spec(name)
                require(spec is not None and Path(spec.origin).resolve() ==
                        root / "Tools/PinkhaSimulatorGate" / (name + ".py"),
                        "New control import resolves outside the frozen writer")
                modules[name] = importlib.import_module(name)
        controller = importlib.import_module("sdk06_original_native_continuation")
        contract = json.loads((root / controller.SOURCE_CONTRACT).read_bytes())
        controller.preload_current_sources(root, contract)
        loaded_before = loaded_sources(root, manifest)
        write(evidence / "loaded-before.json", loaded_before)
        cases = []
        for module_name, class_name, method_name in METHODS:
            cls = getattr(modules[module_name], class_name)
            require(issubclass(cls, unittest.TestCase), "Named new control is not a TestCase")
            cases.append(cls(method_name))
        suite = unittest.TestSuite(cases)
        require(suite.countTestCases() == 3, "Only three new methods may execute")
        with (evidence / "tests.log").open("x", encoding="utf-8") as log:
            runner = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=NamedResult)
            result = runner.run(suite)
        receipt.update(tests_run=result.testsRun, failures=len(result.failures),
                       errors=len(result.errors), skipped=len(result.skipped),
                       named_passes=[row["method"] for row in result.events if row["event"] == "PASS"])
        expected_ids = [".".join(item) for item in METHODS]
        require(result.testsRun == 3 and result.wasSuccessful() and not result.skipped
                and receipt["named_passes"] == expected_ids
                and [row["method"] for row in result.events if row["event"] == "START"] == expected_ids,
                "One or more exact named new controls did not pass")
        receipt["status"] = "PASS"
    except BaseException as caught:
        error = caught
        receipt.update(status="FAIL", error_type=type(caught).__name__, error=str(caught))
        with (evidence / "wrapper-error.log").open("x", encoding="utf-8") as output:
            traceback.print_exc(file=output)
    finally:
        if result is None and len(_CREATED_RESULTS) == 1:
            result = _CREATED_RESULTS[0]
        if result is not None:
            write(evidence / "events.json", result.events)
            receipt["actual_named_starts"] = [row["method"] for row in result.events if row["event"] == "START"]
            receipt["actual_named_passes"] = [row["method"] for row in result.events if row["event"] == "PASS"]
            receipt["actual_subcase_passes"] = sum(row["event"] == "SUBCASE_PASS" for row in result.events)
        try:
            after, observed_manifest = frozen_files(root, args.source)
            write(evidence / "source-after.json", after)
            require(before is not None and before == after and manifest == observed_manifest,
                    "Frozen source/data/metadata changed during the new control attempt")
            loaded_after = loaded_sources(root, manifest)
            write(evidence / "loaded-after.json", loaded_after)
            require(loaded_before is not None and loaded_before == loaded_after,
                    "Loaded frozen repository closure changed during the new controls")
            receipt.update(source_inputs_unchanged=True, loaded_sources_unchanged=True,
                           source_input_count=len(after), loaded_repository_module_count=len(loaded_after))
        except BaseException as caught:
            receipt.update(status="FAIL", final_integrity_failure={
                "error_type": type(caught).__name__, "error": str(caught)})
        receipt.update(finished_at=now(), elapsed_seconds=time.monotonic() - started)
        write(evidence / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
