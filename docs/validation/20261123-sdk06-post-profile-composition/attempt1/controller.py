#!/usr/bin/env python3
"""Execute exactly two newly reviewed fixed-admission methods."""
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-qualified-continuation-20261123")
EVIDENCE = Path(__file__).resolve().parent
EXPECTED = "b7c74c8bac972dedf47f7382ffaeb6f66e424737"
METHODS = [
    "test_sdk06_retained_controls.RetainedControllerAdmissionTests.test_sdk_qualified_profile_addendum_preserves_history_and_rejects_scope_relabelling",
    "test_sdk06_dependency_composition.DependencyCompositionControls.test_exact_composed_dependencies_preserve_original_scopes_and_reject_unreviewed_source_or_events",
]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))

def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

assert git("rev-parse", "HEAD") == EXPECTED
assert not git("status", "--porcelain", "--untracked-files=no")
assert not (EVIDENCE / "intent.json").exists(), "Original attempt already exists"
manifest_path = "Tools/PinkhaSimulatorGate/sdk06-retained-controls.json"
contract = json.loads((ROOT / manifest_path).read_bytes())
paths = {manifest_path, "Tools/PinkhaSimulatorGate/sdk06_retained_controls.py",
         "Tools/PinkhaSimulatorGate/test_sdk06_retained_controls.py",
         "Tools/PinkhaSimulatorGate/test_sdk06_dependency_composition.py",
         "docs/validation/20261123-sdk06-post-profile-composition/source-review.json"}
paths.update(row["path"] for row in contract["source_inputs"])
paths.update(row["path"] for row in contract["proof_files"])
missing = sorted(path for path in paths if not (ROOT / path).is_file())
assert not missing, ("Missing exact declared inputs", missing)
raw_tree = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-rz", "HEAD", "--", *sorted(paths)])
blobs = {}
for row in raw_tree.split(b"\0"):
    if not row:
        continue
    meta, relative = row.split(b"\t", 1)
    mode, kind, oid = meta.decode().split()
    assert mode == "100644" and kind == "blob", (mode, kind, relative)
    blobs[relative.decode()] = oid
assert set(blobs) == paths

def snapshot():
    answer = {}
    for relative in sorted(paths):
        path = ROOT / relative
        assert not path.is_symlink(), relative
        raw = path.read_bytes()
        oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert oid == blobs[relative], ("Frozen Git input differs", relative)
        answer[relative] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), git_blob=oid)
    return answer

def loaded():
    answer = {}
    for value in tuple(sys.modules.values()):
        raw = getattr(value, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(ROOT):
            relative = path.relative_to(ROOT).as_posix()
            assert relative in paths, ("Uninventoried loaded source", relative)
            answer[relative] = dict(sha256=digest(path), bytes=path.stat().st_size)
    return dict(sorted(answer.items()))

before = snapshot()
write("intent.json", dict(source_sha=EXPECTED, method_ids=METHODS,
    controller_sha256=digest(Path(__file__)), new_admission_methods_requested=2,
    old_control_methods_requested=0, product_tests_requested=0, app_builds_requested=0,
    selector_admission_created=False, actual_selector_status="FAIL_26_ENABLED_23_REQUIRED",
    started_at=datetime.now(timezone.utc).isoformat()))
for name in ("test_sdk06_retained_controls", "test_sdk06_dependency_composition"):
    importlib.import_module(name)
write("source-before.json", dict(source_sha=EXPECTED, files=before, loaded_modules=loaded()))

events = []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        events.append(dict(event="START", test_id=test.id()))
        super().startTest(test)
    def addSuccess(self, test):
        events.append(dict(event="PASS", test_id=test.id()))
        super().addSuccess(test)
    def addFailure(self, test, error):
        events.append(dict(event="FAIL", test_id=test.id()))
        super().addFailure(test, error)
    def addError(self, test, error):
        events.append(dict(event="ERROR", test_id=test.id()))
        super().addError(test, error)
    def addSubTest(self, test, subtest, error):
        events.append(dict(event="SUBCASE_PASS" if error is None else "SUBCASE_FAILURE",
                           test_id=test.id(), subtest=str(subtest)))
        super().addSubTest(test, subtest, error)

suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in METHODS)
assert suite.countTestCases() == 2
log = io.StringIO()
started = time.monotonic()
result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(suite)
elapsed = time.monotonic() - started
(EVIDENCE / "controls.log").write_text(log.getvalue())
write("events.json", events)
after = snapshot()
write("source-after.json", dict(source_sha=EXPECTED, files=after, loaded_modules=loaded()))
unchanged = before == after and git("rev-parse", "HEAD") == EXPECTED and not git("status", "--porcelain", "--untracked-files=no")
outcome = dict(status="PASS" if result.wasSuccessful() and unchanged else "FAIL",
    source_sha=EXPECTED, tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    method_ids=[event["test_id"] for event in events if event["event"] == "START"],
    new_admission_methods_executed=2, old_control_methods_executed=0, product_tests_executed=0,
    app_builds=0, source_unchanged=bool(unchanged), source_input_count=len(before),
    original_manifest_source_rows=len(contract["source_inputs"]),
    original_manifest_proof_rows=len(contract["proof_files"]),
    loaded_source_count=len(loaded()), elapsed_seconds=elapsed,
    finished_at=datetime.now(timezone.utc).isoformat(),
    selector_admission_created=False, actual_selector_status="FAIL_26_ENABLED_23_REQUIRED",
    artifacts={name:dict(sha256=digest(EVIDENCE/name), bytes=(EVIDENCE/name).stat().st_size)
        for name in ("controller.py", "intent.json", "controls.log", "events.json",
                     "source-before.json", "source-after.json")})
write("result.json", outcome)
print(log.getvalue())
print(json.dumps(outcome, indent=2, sort_keys=True))
raise SystemExit(0 if outcome["status"] == "PASS" else 1)
