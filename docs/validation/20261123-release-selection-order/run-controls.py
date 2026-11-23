#!/usr/bin/env python3
"""Exactly one new source-bound host control; preserve every original outcome."""
import argparse
import contextlib
import hashlib
import importlib
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[3]
DOC = Path(__file__).resolve().parent
SOURCE = "c853f6b68860f037d014c17cb2d268b8e9c1631a"
MANIFEST_SHA = "6347947179d47ac30c8e2e9fcd4c1fd2b697da9da88f0d75381fc87f530241b4"
TEST = "test_coherent_selection_order.ReleaseSelectionOrderTests.test_final_editor_plan_precedes_owned_seal_and_native_admission"
OUT = Path("/mnt/development/projects/diagnostics/release-selection-order-controls-20261123/attempt1")
RESERVE = 2500000000
MARGIN = 16 * 1024 * 1024
META = ("control-inputs.json", "run-controls.py")


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def guard(margin=0):
    free = shutil.disk_usage(ROOT).free
    need(free >= RESERVE + margin, "Owned capacity guard failed: " + str(free))
    return free


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT), *args], timeout=30)


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o400)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def observe_sources(manifest):
    fixed = {row["path"]: row for row in manifest["inputs"]}
    metadata = [(DOC / name).relative_to(ROOT).as_posix() for name in META]
    paths = sorted([*fixed, *metadata])
    raw = git("ls-tree", "-rz", "HEAD", "--", *paths)
    tree = {}
    for line in raw.split(b"\0"):
        if line:
            header, name = line.split(b"\t", 1)
            mode, kind, blob = header.split()
            need(kind == b"blob", "Source is not a regular Git blob")
            tree[name.decode()] = {"git_mode": mode.decode(), "git_blob": blob.decode()}
    need(set(tree) == set(paths), "Git input inventory differs")
    # Each exact small Git blob is read independently; no shell command interpolation.
    result = []
    for name in paths:
        path = ROOT / name
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path,
             "Source path is not one regular current file: " + name)
        data = path.read_bytes()
        expected = git("cat-file", "blob", tree[name]["git_blob"])
        need(data == expected, "Physical/Git source differs: " + name)
        row = {"path": name, "bytes": len(data), "mode": stat.S_IMODE(info.st_mode),
               "sha256": digest(data), **tree[name],
               "inode": info.st_ino, "mtime_ns": info.st_mtime_ns, "uid": info.st_uid}
        if name in fixed:
            need(all(row[k] == v for k, v in fixed[name].items()), "Frozen input differs: " + name)
        result.append(row)
    return result


def check_inverse(manifest):
    inverse = json.loads((ROOT / manifest["inverse_metadata"]).read_bytes())
    current = (ROOT / inverse["path"]).read_bytes()
    baseline = (ROOT / manifest["baseline_caller"]).read_bytes()
    need(digest(current) == inverse["after_sha256"] and digest(baseline) == inverse["before_sha256"],
         "Exact caller inverse inputs differ")
    restored = current.decode()
    for hunk in inverse["two_exact_substitutions"]:
        need(restored.count(hunk["after"]) == 1, "Caller inverse is not unique")
        restored = restored.replace(hunk["after"], hunk["before"])
    need(restored.encode() == baseline, "Two caller substitutions do not reverse to qualified source")


def loaded(manifest):
    allowed = set(manifest["python_modules"].values())
    result = {}
    for name, module in sorted(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if value is None:
            continue
        path = Path(value).resolve()
        if name in manifest["python_modules"]:
            need(path == ROOT / manifest["python_modules"][name], "Required module is foreign: " + name)
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if path == Path(__file__).resolve():
            continue
        need(relative in allowed and path.suffix == ".py", "Unadmitted repository module: " + relative)
        result[name] = {"path": relative, "sha256": digest(path.read_bytes())}
    need("test_coherent_selection_order" in result
         and "test_coherent_owned_continuation" in result
         and "owned_simulator_readiness" in result, "Required real guard/fixture closure missing")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    need(len(args.expected_head) == 40, "Exact frozen HEAD required")
    head = git("rev-parse", "HEAD").decode().strip()
    need(head == args.expected_head, "Current HEAD is not the reviewed freeze")
    need(git("status", "--porcelain=v1", "--untracked-files=all") == b"", "Writer must remain clean")
    subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT),
                    "merge-base", "--is-ancestor", SOURCE, head], check=True, timeout=30)
    manifest_raw = (DOC / "control-inputs.json").read_bytes()
    need(digest(manifest_raw) == MANIFEST_SHA, "Fixed manifest changed")
    manifest = json.loads(manifest_raw)
    need(manifest["source_commit"] == SOURCE and manifest["test_names"] == [TEST]
         and manifest["expected_methods"] == 1 and manifest["expected_subcases"] == 3,
         "New one-method scope changed")
    start_free = guard(MARGIN)
    need(not OUT.exists(), "Refuse replay or existing original outputs")
    OUT.mkdir(parents=True, mode=0o700)
    temporary = OUT / "temporary"
    temporary.mkdir(mode=0o700)
    os.environ["TMPDIR"] = str(temporary)
    os.environ["COHERENT_OWNED_CONTROL_EVIDENCE"] = str(OUT / "controls")
    tempfile.tempdir = str(temporary)
    sys.dont_write_bytecode = True
    events = []
    result = None
    failure = None
    before = after = loaded_before = loaded_after = None
    started = time.time()
    with (OUT / "events.jsonl").open("x") as event_stream:
        def event(action, test=None, **extra):
            row = {"time_ns": time.time_ns(), "action": action,
                   "test": test.id() if test is not None else None, **extra}
            events.append(row)
            event_stream.write(json.dumps(row, sort_keys=True) + "\n")
            event_stream.flush()
            os.fsync(event_stream.fileno())

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                guard()
                event("START", test)
                super().startTest(test)

            def addSuccess(self, test):
                event("PASS", test)
                super().addSuccess(test)

            def addError(self, test, error):
                event("ERROR", test, error_type=error[0].__name__)
                super().addError(test, error)

            def addFailure(self, test, error):
                event("FAIL", test, error_type=error[0].__name__)
                super().addFailure(test, error)

            def addSkip(self, test, reason):
                event("SKIP", test, reason=reason)
                super().addSkip(test, reason)

            def addSubTest(self, test, subtest, error):
                event("SUBCASE_PASS" if error is None else "SUBCASE_FAIL",
                      test, subcase=str(subtest),
                      error_type=None if error is None else error[0].__name__)
                super().addSubTest(test, subtest, error)

        with (OUT / "original.stdout").open("x") as stdout, (OUT / "original.stderr").open("x") as stderr:
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    before = observe_sources(manifest)
                    save(OUT / "source-before.json", before)
                    check_inverse(manifest)
                    for relative in ("Tools/Hanlin", "Tools/PinkhaNativeDerived", "Tools/PinkhaSimulatorGate"):
                        sys.path.insert(0, str(ROOT / relative))
                    for name, relative in manifest["python_modules"].items():
                        spec = importlib.machinery.PathFinder.find_spec(name, sys.path)
                        need(spec is not None and Path(spec.origin).resolve() == ROOT / relative,
                             "Static import origin differs: " + name)
                    module = importlib.import_module("test_coherent_selection_order")
                    loaded_before = loaded(manifest)
                    save(OUT / "loaded-before.json", loaded_before)
                    suite = unittest.defaultTestLoader.loadTestsFromName(TEST)
                    need(suite.countTestCases() == 1, "Unexpected method inventory")
                    guard()
                    result = unittest.TextTestRunner(stream=stderr, verbosity=2, resultclass=Result).run(suite)
                    loaded_after = loaded(manifest)
                    need(loaded_after == loaded_before, "Actual local import closure changed")
                    save(OUT / "loaded-after.json", loaded_after)
                    after = observe_sources(manifest)
                    need(after == before, "Frozen physical/Git inputs changed")
                    save(OUT / "source-after.json", after)
                    guard()
                    need(result.testsRun == 1 and result.wasSuccessful(), "The new method did not pass")
                    need(sum(e["action"] == "START" for e in events) == 1
                         and sum(e["action"] == "PASS" for e in events) == 1
                         and sum(e["action"] == "SUBCASE_PASS" for e in events) == 3
                         and not any(e["action"] in {"ERROR", "FAIL", "SKIP", "SUBCASE_FAIL"} for e in events),
                         "Actual named event inventory differs")
            except BaseException as error:
                failure = {"type": type(error).__name__, "message": str(error)}
                traceback.print_exc(file=stderr)
            finally:
                stdout.flush()
                stderr.flush()
                os.fsync(stdout.fileno())
                os.fsync(stderr.fileno())
    outputs = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file():
            need(not path.is_symlink() and path.stat().st_nlink == 1, "Unexpected owned output identity")
            outputs[path.relative_to(OUT).as_posix()] = {
                "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
    receipt = {
        "protocol": "release-selection-order-single-control-v1",
        "status": "PASS" if failure is None else "FAIL",
        "source_commit": SOURCE, "checked_head": head, "manifest_sha256": MANIFEST_SHA,
        "runner_sha256": digest(Path(__file__).read_bytes()), "selected_tests": [TEST],
        "python_executable": sys.executable, "python_version": sys.version,
        "tests_run": None if result is None else result.testsRun,
        "named_passes": [e["test"] for e in events if e["action"] == "PASS"],
        "named_failures": [e for e in events if e["action"] in {"ERROR", "FAIL", "SUBCASE_FAIL"}],
        "subcase_passes": sum(e["action"] == "SUBCASE_PASS" for e in events),
        "failure": failure, "source_inputs": len(manifest["inputs"]),
        "metadata_inputs": len(META), "actual_local_modules": len(loaded_after or loaded_before or {}),
        "inputs_unchanged": before is not None and after == before,
        "loaded_unchanged": loaded_before is not None and loaded_after == loaded_before,
        "actual_simulator_commands": 0, "actual_native_or_product_methods": 0, "old_tests_run": 0,
        "start_free": start_free, "final_free": shutil.disk_usage(ROOT).free,
        "elapsed_seconds": time.time() - started, "original_outputs": outputs,
    }
    # Preserve the named original outcomes even if a later guard has failed.
    saved = save(OUT / "execution.json", receipt)
    for path in OUT.rglob("*"):
        if path.is_file():
            path.chmod(0o400)
    print(json.dumps({"status": receipt["status"], "receipt": saved,
                      "tests_run": receipt["tests_run"], "subcase_passes": receipt["subcase_passes"],
                      "loaded_modules": receipt["actual_local_modules"], "failure": failure}))
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
