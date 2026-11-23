#!/usr/bin/env python3
"""Run exactly one frozen Page warning host control; never invoke Mac/native/UI."""
from __future__ import annotations
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = "e6578312b3939cf4880ca8a70c3283f3041f3e39"
MANIFEST_SHA = "2dfcde2a8a69b27f199c88715467cd10f5b9ad48d87d76ab3194941d1b470592"
METHOD = "test_warning_profile.PageStartupWarningControls.testWarningUiOnlyCompositionPreservesNativeOriginAndSetupAccounting"
OUTPUT = Path("/mnt/development/projects/diagnostics/semantic-page-warning-controls-20261123/attempt1")
START_FREE = 2_517_825_792
MINIMUM_FREE = 2_500_000_000


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def git(*args):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), *args],
                            capture_output=True, check=True)
    return result.stdout


def guard(minimum=MINIMUM_FREE):
    free = shutil.disk_usage(ROOT).free
    require(free >= minimum, "capacity_reserve_not_met:" + str(free))
    return free


def sources(manifest, head):
    rows = {}
    names = set(manifest["inputs"]) | {
        (HERE / "control-inputs.json").relative_to(ROOT).as_posix(),
        Path(__file__).relative_to(ROOT).as_posix()}
    for name in sorted(names):
        path = ROOT / name
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "source_must_be_single_regular:" + name)
        raw = path.read_bytes()
        entry = git("ls-tree", head, "--", name).decode().strip()
        mode, kind, tail = entry.split(" ", 2)
        blob, actual = tail.split("\t")
        require(kind == "blob" and actual == name and raw == git("cat-file", "blob", blob),
                "current_git_physical_source_differs:" + name)
        row = dict(bytes=len(raw), sha256=digest(raw), git_blob=blob, git_mode=mode,
                   mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, inode=info.st_ino,
                   device=info.st_dev, mtime_ns=info.st_mtime_ns)
        if name in manifest["inputs"]:
            expected = manifest["inputs"][name]
            require(all(row[k] == value for k, value in expected.items()), "frozen_source_differs:" + name)
            require(git("rev-parse", SOURCE + ":" + name).decode().strip() == blob,
                    "source_checkpoint_blob_differs:" + name)
        rows[name] = row
    return rows


def loaded(manifest, source_rows):
    rows, failures = {}, []
    for name, module in list(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if not value:
            continue
        path = Path(value).resolve()
        if path.is_relative_to(ROOT):
            relative = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            rows[name] = dict(path=relative, sha256=digest(raw), bytes=len(raw))
            if manifest["loaded_modules"].get(name) != relative or relative not in source_rows:
                failures.append("undeclared_local_module:" + name)
            elif rows[name]["sha256"] != source_rows[relative]["sha256"]:
                failures.append("loaded_module_bytes_differ:" + name)
    for name, relative in manifest["loaded_modules"].items():
        module = sys.modules.get(name)
        if module is None or Path(getattr(module, "__file__", "")).resolve() != ROOT / relative:
            failures.append("required_module_origin_differs:" + name)
    return {"modules": rows, "failures": failures}


class Events(unittest.TextTestResult):
    def __init__(self, *args, event_stream, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_stream = event_stream
        self.rows = []
        self.terminals = set()

    def event(self, action, test, **more):
        value = dict(time=datetime.now(timezone.utc).isoformat(), action=action, test=test.id(), **more)
        self.rows.append(value)
        self.event_stream.write(json.dumps(value, sort_keys=True) + "\n")
        self.event_stream.flush(); os.fsync(self.event_stream.fileno())

    def startTest(self, test):
        guard()
        require(test.id() == METHOD, "unexpected_control_method")
        self.event("START", test)
        super().startTest(test)

    def addSuccess(self, test):
        self.event("PASS", test); self.terminals.add(test.id())
        super().addSuccess(test)

    def addError(self, test, error):
        self.event("ERROR", test, error_type=error[0].__name__); self.terminals.add(test.id())
        super().addError(test, error)

    def addFailure(self, test, error):
        self.event("FAIL", test, error_type=error[0].__name__); self.terminals.add(test.id())
        super().addFailure(test, error)

    def addSubTest(self, test, subtest, error):
        self.event("SUBCASE_PASS" if error is None else "SUBCASE_FAIL", test,
                   label=str(subtest), error_type=error[0].__name__ if error else None)
        super().addSubTest(test, subtest, error)

    def stopTest(self, test):
        if test.id() not in self.terminals:
            self.event("FAIL", test, reason="subcase_failure"); self.terminals.add(test.id())
        self.event("STOP", test)
        super().stopTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    head = git("rev-parse", "HEAD").decode().strip()
    require(head == args.expected_head, "exact_current_control_head_required")
    require(not git("status", "--porcelain", "--untracked-files=all"), "clean_control_writer_required")
    manifest_raw = (HERE / "control-inputs.json").read_bytes()
    require(digest(manifest_raw) == MANIFEST_SHA, "fixed_control_manifest_required")
    manifest = json.loads(manifest_raw)
    require(manifest["source_sha"] == SOURCE and manifest["method"] == METHOD
            and manifest["methods"] == 1 and manifest["named_subcases"] == 7,
            "one_fixed_control_scope_required")
    metadata = {(HERE / "control-inputs.json").relative_to(ROOT).as_posix(),
                Path(__file__).relative_to(ROOT).as_posix()}
    changed = set(git("diff", "--name-only", SOURCE, head).decode().splitlines())
    require(changed == metadata, "source_to_wrapper_freeze_may_only_add_two_metadata_files")
    free_before = guard(START_FREE)
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), "fresh_attempt1_required")
    OUTPUT.mkdir(parents=True, mode=0o700)
    temporary = OUTPUT / "private-work"; temporary.mkdir(mode=0o700)
    os.environ["TMPDIR"] = str(temporary)
    receipt = dict(protocol="page154-warning-control-execution-v1", status="RUNNING",
                   source_sha=SOURCE, head=head, manifest_sha256=MANIFEST_SHA,
                   scope=manifest["scope"], expected_method=METHOD, expected_subcases=7,
                   started_at=datetime.now(timezone.utc).isoformat(), free_before=free_before,
                   native_calls=0, simulator_calls=0, builds=0, old_control_replays=0)
    result = None
    started = time.monotonic()
    with (OUTPUT / "original.stdout").open("x") as stdout, (OUTPUT / "original.stderr").open("x") as stderr, (
            OUTPUT / "events.jsonl").open("x") as events:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                before = sources(manifest, head); save(OUTPUT / "source-before.json", before)
                module_root = ROOT / "Tools/PinkhaSemanticAnchorWire/apple_mounted"
                sys.path.insert(0, str(module_root))
                for name, relative in manifest["loaded_modules"].items():
                    found = importlib.util.find_spec(name)
                    require(found is not None and Path(found.origin).resolve() == ROOT / relative,
                            "initial_module_origin_differs:" + name)
                for name in manifest["loaded_modules"]:
                    importlib.import_module(name)
                initial = loaded(manifest, before); save(OUTPUT / "loaded-before.json", initial)
                require(not initial["failures"], "initial_loaded_admission_failed")
                suite = unittest.defaultTestLoader.loadTestsFromName(METHOD)
                require(suite.countTestCases() == 1, "one_new_control_case_required")
                runner = unittest.TextTestRunner(stream=stdout, verbosity=2,
                    resultclass=lambda *a, **k: Events(*a, event_stream=events, **k))
                result = runner.run(suite)
                # Record the actual outcome before any later admission can fail.
                receipt["actual_tests_run"] = result.testsRun
                receipt["actual_method_passes"] = sum(row["action"] == "PASS" for row in result.rows)
                receipt["actual_subcase_passes"] = sum(row["action"] == "SUBCASE_PASS" for row in result.rows)
                receipt["actual_subcase_failures"] = sum(row["action"] == "SUBCASE_FAIL" for row in result.rows)
                receipt["actual_errors"] = len(result.errors)
                receipt["actual_failures"] = len(result.failures)
                receipt["actual_skips"] = len(result.skipped)
                save(OUTPUT / "named-outcomes.json", dict(
                    method=METHOD, events=result.rows, unittest_was_successful=result.wasSuccessful()))
                guard()
                after = sources(manifest, head); save(OUTPUT / "source-after.json", after)
                final = loaded(manifest, after); save(OUTPUT / "loaded-after.json", final)
                require(before == after and initial == final and not final["failures"],
                        "source_or_loaded_closure_changed")
                require(result.wasSuccessful() and result.testsRun == 1
                        and receipt["actual_method_passes"] == 1
                        and receipt["actual_subcase_passes"] == 7 and receipt["actual_subcase_failures"] == 0
                        and not result.skipped, "new_control_did_not_pass_exact_scope")
                receipt.update(status="PASS", input_count=len(before), loaded_modules=len(final["modules"]),
                               source_before_after_equal=True, loaded_before_after_equal=True)
            except BaseException as error:
                import traceback
                receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
                traceback.print_exc(file=stderr)
            finally:
                receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
                receipt["elapsed_seconds"] = time.monotonic() - started
                receipt["free_after"] = shutil.disk_usage(ROOT).free
                stdout.flush(); stderr.flush(); events.flush()
                for stream in (stdout, stderr, events):
                    os.fsync(stream.fileno())
    receipt["original_files"] = {path.name: dict(bytes=path.stat().st_size, sha256=digest(path.read_bytes()))
        for path in sorted(OUTPUT.iterdir()) if path.is_file()}
    save(OUTPUT / "execution.json", receipt)
    print(json.dumps({"status": receipt["status"], "output": str(OUTPUT),
                      "actual_method_passes": receipt.get("actual_method_passes", 0),
                      "actual_subcase_passes": receipt.get("actual_subcase_passes", 0),
                      "execution_sha256": digest((OUTPUT / "execution.json").read_bytes())}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
