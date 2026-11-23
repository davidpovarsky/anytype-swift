#!/usr/bin/env python3
"""Run only four new coherent continuation controls from a frozen exact closure."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESERVE = 2_500_000_000
MAXIMUM = 4 * 1024 * 1024
TEST_MODULE = "test_coherent_owned_continuation"
SOURCE = "3a6f932925a7cadd37490b91eed59c27f58da446"
TESTS = (
    "CoherentOwnedContinuationTests.test_construction_and_first_selection_bind_original_ownership_and_retained_outputs",
    "CoherentOwnedContinuationTests.test_new_create_callback_persists_uuid_before_later_owned_failure",
    "CoherentOwnedContinuationTests.test_outer_coherent_caller_forwards_profile_and_retains_original_failures",
    "CoherentOwnedContinuationTests.test_cleanup_snapshot_checks_live_bytes_closure_and_intent_without_git",
)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30)


def entries(commit, names):
    raw = git("ls-tree", "-r", "-z", commit, "--", *names)
    result = {}
    for row in raw.split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        key = name.decode("utf-8")
        require(kind == "blob" and key not in result, "Exact unique Git input blob required")
        result[key] = dict(mode=mode, blob=blob)
    require(set(result) == set(names), "Git input closure is incomplete")
    return result


def exact_file(relative):
    path = ROOT / relative
    require(path.resolve() == path and path.is_relative_to(ROOT) and path.is_file()
            and not path.is_symlink() and path.stat().st_size <= MAXIMUM,
            "Frozen input is missing, aliased or unbounded: " + relative)
    return path.read_bytes()


def observe_sources(plan, head):
    require(not git("status", "--porcelain=v1", "--untracked-files=no").strip(),
            "Tracked source is dirty")
    changed = git("diff", "--name-only", plan["source_commit"], head).decode().splitlines()
    prefix = HERE.relative_to(ROOT).as_posix() + "/"
    require(all(name.startswith(prefix) for name in changed),
            "Changes after the source freeze escape this evidence directory")
    frozen = plan["inputs"]
    fixed_tree = entries(plan["source_commit"], sorted(frozen))
    current_tree = entries(head, sorted(frozen))
    rows = {}
    for name, wanted in frozen.items():
        raw = exact_file(name)
        require(current_tree[name] == fixed_tree[name] == {"mode": wanted["mode"], "blob": wanted["blob"]},
                "Frozen input Git identity differs: " + name)
        require(len(raw) == wanted["bytes"] and digest(raw) == wanted["sha256"]
                and hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == wanted["blob"],
                "Frozen physical input differs: " + name)
        rows[name] = dict(wanted, physical_mode=oct(stat.S_IMODE((ROOT / name).stat().st_mode)))
    metadata = {**plan["metadata"], (HERE / "control-inputs.json").relative_to(ROOT).as_posix():
                {"sha256": digest((HERE / "control-inputs.json").read_bytes()),
                 "bytes": (HERE / "control-inputs.json").stat().st_size}}
    tree = entries(head, sorted(metadata))
    for name, wanted in metadata.items():
        raw = exact_file(name)
        require(len(raw) == wanted["bytes"] and digest(raw) == wanted["sha256"],
                "Frozen controller metadata differs: " + name)
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == tree[name]["blob"],
                "Controller metadata differs from its current Git object: " + name)
        rows[name] = dict(wanted, **tree[name], physical_mode=oct(stat.S_IMODE((ROOT / name).stat().st_mode)))
    return dict(source_commit=plan["source_commit"], controller_commit=head,
                input_count=len(rows), files=rows)


def observe_loaded(allowed):
    values = {}
    for name, module in tuple(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if not value:
            continue
        raw = Path(value).absolute()
        path = raw.resolve()
        if path.suffix != ".py" or not path.is_relative_to(ROOT):
            continue
        require(raw == path, "Loaded repository input uses an alias")
        relative = path.relative_to(ROOT).as_posix()
        require(relative in allowed, "Loaded repository input is outside the frozen closure: " + relative)
        data = exact_file(relative)
        require(digest(data) == allowed[relative]["sha256"], "Loaded source bytes changed")
        values[name] = dict(path=relative, sha256=digest(data), bytes=len(data))
    return values


class Events(unittest.TextTestResult):
    def __init__(self, *args, event_stream, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_stream = event_stream

    def event(self, action, test, **extra):
        self.event_stream.write(json.dumps(dict(time=stamp(), action=action, test=test.id(), **extra),
                                          sort_keys=True) + "\n")
        self.event_stream.flush()

    def startTest(self, test):
        require(shutil.disk_usage(ROOT).free >= RESERVE, "Capacity reserve unavailable before next method")
        self.event("start", test)
        super().startTest(test)

    def addSuccess(self, test):
        self.event("pass", test)
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.event("fail", test, error_type=err[0].__name__)
        super().addFailure(test, err)

    def addError(self, test, err):
        self.event("error", test, error_type=err[0].__name__)
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.event("skip", test, reason=reason)
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, err):
        self.event("subtest-pass" if err is None else "subtest-fail", test,
                   subtest=str(subtest), error_type=None if err is None else err[0].__name__)
        super().addSubTest(test, subtest, err)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    output = args.evidence.absolute()
    owned = Path("/mnt/development/projects/diagnostics/coherent-owned-continuation-controls-20261123")
    require(output.resolve() == output and output.parent == owned
            and not output.exists() and not output.is_symlink(),
            "Fresh exact owned attempt directory required")
    free = shutil.disk_usage(ROOT).free
    require(free >= RESERVE + 16 * 1024 * 1024, "2.5 GB reserve is not available")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    original_out = output / "original.stdout"
    original_err = output / "original.stderr"
    receipt = dict(protocol="pinkha-coherent-owned-continuation-controls-v1", started_at=stamp(),
        status="FAIL_BEFORE_CONTROLS", free_bytes_before=free, reserve_bytes=RESERVE,
        simulator_commands_executed=0, product_methods_executed=0, old_control_methods_executed=0,
        command=[sys.executable, "-B", str(Path(__file__).resolve()), "--evidence", str(output)],
        python=dict(executable=sys.executable, version=sys.version, platform=platform.platform()),
        limitations=["Four new controller/ownership controls only",
                     "Injected simulator command results are not native or UI acceptance",
                     "Original actual eleven kernel observations remain a separate retained scope"])
    before = None
    result = None
    try:
        with original_out.open("x", encoding="utf-8") as stdout, original_err.open("x", encoding="utf-8") as stderr, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            plan = json.loads((HERE / "control-inputs.json").read_bytes())
            require(plan["source_commit"] == SOURCE and plan["tests"] == list(TESTS),
                    "Exact frozen source and four named controls required")
            head = git("rev-parse", "HEAD").decode().strip()
            before = observe_sources(plan, head)
            write(output / "source-before.json", before)
            receipt.update(source_commit=plan["source_commit"], controller_commit=head, selected_tests=plan["tests"])
            sys.dont_write_bytecode = True
            sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
            module = importlib.import_module(TEST_MODULE)
            loaded = observe_loaded(before["files"])
            write(output / "loaded-before.json", loaded)
            suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, module)
                                       for name in plan["tests"])
            require(suite.countTestCases() == 4, "Selected method count differs")
            os.environ["COHERENT_OWNED_CONTROL_EVIDENCE"] = str(output / "control-produced-originals")
            receipt["status"] = "RUNNING_FOUR_NEW_CONTROLS"
            with (output / "events.jsonl").open("x", encoding="utf-8") as events:
                def factory(*args, **kwargs):
                    return Events(*args, event_stream=events, **kwargs)
                result = unittest.TextTestRunner(stream=stderr, verbosity=2, resultclass=factory).run(suite)
            loaded_after = observe_loaded(before["files"])
            write(output / "loaded-after.json", loaded_after)
            after = observe_sources(plan, head)
            write(output / "source-after.json", after)
            require(after == before, "Source closure changed during the new controls")
            actual = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
            expected = [TEST_MODULE + "." + value for value in plan["tests"]]
            starts = [row["test"] for row in actual if row["action"] == "start"]
            passes = [row["test"] for row in actual if row["action"] == "pass"]
            receipt.update(methods_started=starts, methods_passed=passes, methods_run=result.testsRun,
                failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                subtests_passed=sum(row["action"] == "subtest-pass" for row in actual),
                subtests_failed=sum(row["action"] == "subtest-fail" for row in actual),
                source_before_after_identical=True, loaded_before_count=len(loaded), loaded_after_count=len(loaded_after))
            require(starts == expected, "Actual named method starts differ")
            require(result.wasSuccessful() and passes == expected and result.testsRun == 4
                    and not result.skipped, "One or more new controls did not pass")
            receipt["status"] = "PASS_FOUR_NEW_CONTROLS"
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        with original_err.open("a", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
    finally:
        # Preserve actual starts/passes even if a later loaded/source guard fails.
        events_path = output / "events.jsonl"
        if events_path.exists():
            try:
                observed = [json.loads(line) for line in events_path.read_text().splitlines()]
                starts = [row["test"] for row in observed if row["action"] == "start"]
                passes = [row["test"] for row in observed if row["action"] == "pass"]
                receipt.update(methods_started=starts, methods_passed=passes, methods_run=len(starts),
                    subtests_passed=sum(row["action"] == "subtest-pass" for row in observed),
                    subtests_failed=sum(row["action"] == "subtest-fail" for row in observed))
            except BaseException as error:
                receipt.update(event_audit_error_type=type(error).__name__,
                               event_audit_error=str(error), status="FAIL")
        else:
            receipt.update(methods_started=[], methods_passed=[], methods_run=0)
        receipt.update(finished_at=stamp(), free_bytes_after=shutil.disk_usage(ROOT).free)
        if original_out.exists():
            receipt["stdout_sha256"] = digest(original_out.read_bytes())
        if original_err.exists():
            receipt["stderr_sha256"] = digest(original_err.read_bytes())
        receipt["original_artifacts"] = {p.relative_to(output).as_posix():
            dict(sha256=digest(p.read_bytes()), bytes=p.stat().st_size)
            for p in sorted(output.rglob("*")) if p.is_file() and not p.is_symlink()}
        write(output / "execution.json", receipt)
        print(json.dumps({"status": receipt["status"], "evidence": str(output),
                          "methods_run": receipt.get("methods_run", 0),
                          "execution_sha256": digest((output / "execution.json").read_bytes())}))
    return 0 if receipt["status"] == "PASS_FOUR_NEW_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
