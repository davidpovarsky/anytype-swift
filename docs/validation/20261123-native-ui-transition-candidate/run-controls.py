#!/usr/bin/env python3
"""Execute exactly the three frozen new host controls after explicit review."""
from __future__ import annotations
import argparse
import contextlib
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
import traceback
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SOURCE = "1a710285102077f8be7b3180a6685fbed1dc7cd9"
MANIFEST = Path(__file__).with_name("control-inputs.json")
MANIFEST_SHA = "c4a4de9506103ea52e201f66556ff80729f0e2784b44a6479f83cfdbfc25fe4f"
OUTPUT = Path("/mnt/development/projects/diagnostics/native-ui-transition-controls-20261123/attempt1")
MIN_FREE = 2_500_000_000
CASES = (
    "NativeUITransitionCandidateControls.test_project_projection_builds_only_ui_sources",
    "NativeUITransitionCandidateControls.test_descriptor_and_enumeration_bind_original_app_and_five_only",
    "NativeUITransitionCandidateControls.test_first_failure_preserves_named_partial_results_and_never_validates",
)
MODULE = "test_native_ui_transition_candidate"


def require(value, code):
    if not value:
        raise RuntimeError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def free():
    value = os.statvfs("/mnt/development")
    return value.f_bavail * value.f_frsize


def guard(extra=0):
    value = free()
    require(value >= MIN_FREE + extra, "unchanged_2_5GB_capacity_guard")
    return value


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT), *args], timeout=30)


def regular(path):
    value = path.lstat()
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1
            and value.st_size <= 4 * 1024**2, "bounded_single_link_input_required")
    return path.read_bytes()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def observe(manifest, head):
    require(git("rev-parse", "HEAD").decode().strip() == head
            and not git("status", "--porcelain=v1"), "frozen_controller_tree_required")
    rows = []
    for row in manifest["files"]:
        path = ROOT / row["path"]
        require(path.resolve() == path, "source_path_alias_forbidden")
        raw = regular(path)
        current = git("show", head + ":" + row["path"])
        original = git("cat-file", "blob", row["git_blob"])
        require(raw == current == original
                and sha(raw) == row["sha256"] and len(raw) == row["bytes"]
                and stat.S_IMODE(path.lstat().st_mode) == row["physical_mode"],
                "frozen_source_input_changed:" + row["path"])
        entry = git("ls-tree", SOURCE, "--", row["path"]).decode().strip()
        require(entry == row["git_mode"] + " blob " + row["git_blob"] + "\t" + row["path"],
                "frozen_source_git_identity_changed")
        rows.append(row)
    return rows


def loaded(manifest):
    expected = set(manifest["loaded_python"])
    actual = {}
    for name in (MODULE, "native_ui_transition_project", "native_ui_transition_contract"):
        module = sys.modules[name]
        path = Path(module.__file__).absolute()
        relative = path.relative_to(ROOT).as_posix()
        require(relative in expected and path.resolve() == path, "loaded_control_origin_changed")
        actual[relative] = sha(regular(path))
    require(set(actual) == expected, "complete_three_module_closure_required")
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).absolute()
        if path.is_relative_to(ROOT):
            require(path == Path(__file__).resolve() or path.relative_to(ROOT).as_posix() in expected,
                    "unadmitted_repo_import_in_new_controls")
    lookup = {row["path"]: row["sha256"] for row in manifest["files"]}
    require(all(lookup[name] == digest for name, digest in actual.items()), "loaded_control_bytes_changed")
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{40}", args.expected_head), "exact_reviewed_controller_head_required")
    initial_free = guard(16 * 1024**2)
    raw = regular(MANIFEST)
    require(sha(raw) == MANIFEST_SHA, "fixed_control_manifest_changed")
    manifest = json.loads(raw)
    require(manifest["source_commit"] == SOURCE and tuple(manifest["case_ids"]) == CASES
            and len(manifest["files"]) == 13 and len({x["path"] for x in manifest["files"]}) == 13,
            "fixed_source_or_three_control_selection_changed")
    for path in (MANIFEST, Path(__file__).resolve()):
        name = path.relative_to(ROOT).as_posix()
        require(regular(path) == git("show", args.expected_head + ":" + name),
                "controller_metadata_differs_from_reviewed_git")
    before = observe(manifest, args.expected_head)
    require(OUTPUT.is_absolute() and OUTPUT.resolve() == OUTPUT and not OUTPUT.exists(),
            "fresh_owned_attempt1_required")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(mode=0o700)
    temporary = OUTPUT / "tmp"
    temporary.mkdir(mode=0o700)
    os.environ["TMPDIR"] = str(temporary)
    write(OUTPUT / "source-before.json", before)
    write(OUTPUT / "invocation.json", {"argv": sys.argv, "sourceCommit": SOURCE,
          "controllerHead": args.expected_head, "manifestSHA256": MANIFEST_SHA,
          "wrapperSHA256": sha(regular(Path(__file__).resolve())),
          "startedAt": now(), "initialFreeBytes": initial_free,
          "python": sys.version, "platform": platform.platform(),
          "exactMethods": list(CASES), "oldSuitesReplayed": 0, "productMethodsExecuted": 0})
    events = (OUTPUT / "original-events.jsonl").open("x", encoding="utf-8")
    outcomes = {}
    subcases = []
    started = []
    first = None
    result = None
    closures = {}
    def event(kind, test, **values):
        row = {"time": now(), "monotonic": time.monotonic(), "action": kind,
               "test": test, **values}
        events.write(json.dumps(row, sort_keys=True) + "\n")
        events.flush()
        os.fsync(events.fileno())
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            guard()
            require(test.id() in {MODULE + "." + name for name in CASES},
                    "unexpected_control_method")
            started.append(test.id())
            event("START", test.id())
            super().startTest(test)
        def addSuccess(self, test):
            outcomes[test.id()] = "PASS"
            event("PASS", test.id())
            super().addSuccess(test)
        def addFailure(self, test, err):
            outcomes[test.id()] = "FAIL"
            event("FAIL", test.id(), error_type=err[0].__name__)
            super().addFailure(test, err)
        def addError(self, test, err):
            outcomes[test.id()] = "ERROR"
            event("ERROR", test.id(), error_type=err[0].__name__)
            super().addError(test, err)
        def addSkip(self, test, reason):
            outcomes[test.id()] = "SKIP"
            event("SKIP", test.id(), reason=reason)
            super().addSkip(test, reason)
        def addSubTest(self, test, subtest, err):
            status = "PASS" if err is None else "FAIL"
            subcases.append({"test": test.id(), "subtest": str(subtest), "status": status})
            event("SUBCASE_" + status, test.id(), subtest=str(subtest))
            if err is not None:
                outcomes[test.id()] = "FAIL"
            super().addSubTest(test, subtest, err)
    with (OUTPUT / "original.stdout").open("x", encoding="utf-8") as stdout, \
         (OUTPUT / "original.stderr").open("x", encoding="utf-8") as stderr:
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                guard()
                sys.path.insert(0, str(ROOT / "Tools/AnyEnginePort"))
                module = importlib.import_module(MODULE)
                closures["before"] = loaded(manifest)
                suite = unittest.TestSuite()
                for name in CASES:
                    selected = unittest.defaultTestLoader.loadTestsFromName(name, module)
                    require(selected.countTestCases() == 1, "one_exact_method_required")
                    suite.addTests(selected)
                require(suite.countTestCases() == 3, "exactly_three_new_controls_required")
                result = unittest.TextTestRunner(stream=stderr, verbosity=2, resultclass=Result).run(suite)
                closures["after"] = loaded(manifest)
                require(closures["before"] == closures["after"], "loaded_control_closure_changed")
                require(len(started) == len(set(started)) == 3 and result.testsRun == 3
                        and result.wasSuccessful() and not result.skipped
                        and set(outcomes.values()) == {"PASS"}, "new_control_scope_failed")
        except BaseException as error:
            first = error
            traceback.print_exc(file=stderr)
        finally:
            stdout.flush(); os.fsync(stdout.fileno())
            stderr.flush(); os.fsync(stderr.fileno())
    try:
        after = observe(manifest, args.expected_head)
        require(after == before, "source_changed_during_new_control_execution")
        write(OUTPUT / "source-after.json", after)
    except BaseException as error:
        event("SOURCE_AFTER_ERROR", "controller", error_type=type(error).__name__, message=str(error))
        if first is None:
            first = error
    events.close()
    # Seal small original outcomes even if a later per-method guard refused work.
    # No later test starts and no passing method is replayed.
    receipt = {"status": "PASS" if first is None else "FAIL",
               "sourceCommit": SOURCE, "controllerHead": args.expected_head,
               "manifestSHA256": MANIFEST_SHA, "finishedAt": now(), "freeBytesAfter": free(),
               "actualStarts": started, "actualNamedOutcomes": outcomes,
               "subcases": subcases, "loadedSources": closures,
               "testsRun": None if result is None else result.testsRun,
               "oldSuitesReplayed": 0, "productMethodsExecuted": 0, "appleCompilation": "NOT_RUN",
               "firstFailure": None if first is None else {"type": type(first).__name__, "message": str(first)}}
    write(OUTPUT / "execution.json", receipt)
    print(json.dumps({"status": receipt["status"], "actualNamedOutcomes": outcomes,
                      "executionSHA256": sha(regular(OUTPUT / "execution.json")),
                      "directory": str(OUTPUT)}, sort_keys=True))
    return 0 if first is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
