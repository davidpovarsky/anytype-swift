#!/usr/bin/env python3
"""Execute only two new frozen basename-consumer controls."""
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
EXPECTED = "51dd4936221bcbf802b0bf1bcd54853337e0df3b"
METHODS = [
    "test_sdk06_qualified_basename_selector.BasenameSelectorControls.test_basename_provider_and_exact_nine_source_inputs_are_bound_without_extending_legacy_paths",
    "test_sdk06_qualified_basename_selector.BasenameSelectorControls.test_basename_record_current_enumeration_and_execution_keep_exact23_and_identical_seven_skips",
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
write("intent.json", dict(source_sha=EXPECTED, method_ids=METHODS, controller_sha256=digest(Path(__file__)),
                          old_control_methods_requested=0, new_control_methods_requested=2,
                          actual_product_tests_requested=0, app_builds_requested=0,
                          fixture_scope="SYNTHETIC_OFFLINE_NO_ACCEPTANCE_OR_COMMITTED_ADMISSION",
                          started_at=datetime.now(timezone.utc).isoformat()))
module = importlib.import_module("test_sdk06_qualified_basename_selector")
candidate = module.selected
importlib.import_module("sdk06_basename_enumeration_probe")
def loaded():
    answer = {}
    for value in tuple(sys.modules.values()):
        raw = getattr(value, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(ROOT):
            answer[path.relative_to(ROOT).as_posix()] = dict(sha256=digest(path), bytes=path.stat().st_size)
    return dict(sorted(answer.items()))
def snapshot():
    paths = set(loaded()) | set(candidate.BASENAME_EXTRA_INPUTS) | set(candidate.probe.SOURCES) | {
        "Tools/PinkhaSimulatorGate/test_sdk06_qualified_basename_selector.py",
        "docs/validation/20261123-sdk06-qualified-basename-selector/source-review.json"}
    files = {}
    for relative in sorted(paths):
        path = ROOT / relative
        files[relative] = dict(sha256=digest(path), bytes=path.stat().st_size,
                               git_blob=git("rev-parse", "HEAD:" + relative))
    return files
before = snapshot()
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
outcome = dict(status="PASS" if result.wasSuccessful() and unchanged else "FAIL", source_sha=EXPECTED,
               tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
               method_ids=[event["test_id"] for event in events if event["event"] == "START"],
               new_control_methods_executed=2, old_control_methods_executed=0,
               actual_product_tests_executed=0, app_builds=0, source_unchanged=bool(unchanged),
               source_input_count=len(before), loaded_source_count=len(loaded()),
               elapsed_seconds=elapsed, finished_at=datetime.now(timezone.utc).isoformat(),
               selector_admission_created=False,
               artifacts={name:dict(sha256=digest(EVIDENCE/name),bytes=(EVIDENCE/name).stat().st_size)
                          for name in ("controller.py","intent.json","controls.log","events.json",
                                       "source-before.json","source-after.json")})
write("result.json", outcome)
print(log.getvalue())
print(json.dumps(outcome, indent=2, sort_keys=True))
raise SystemExit(0 if outcome["status"] == "PASS" else 1)
