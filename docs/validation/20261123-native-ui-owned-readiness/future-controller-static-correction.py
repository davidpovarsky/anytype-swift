#!/usr/bin/env python3
"""Original, main-thread runner for exactly two newly authorized UI adapter controls."""
import collections
import contextlib
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

ROOT = Path("/mnt/development/projects/worktrees/anytype-wave15-native-ui-readiness-20261123")
APP = Path("/mnt/development/projects/worktrees/anytype-wave15-ui-qualified-continuation-20261123")
HEAD = "c30e20e42ae6c52b7c4d251fc59630c2ff2f677c"
APP_HEAD = "4b09cc5478c60c1c6728a54f2a27a115637a835b"
INPUTS = ROOT / "docs/validation/20261123-native-ui-owned-readiness/control-inputs.json"
INPUTS_SHA = "1193dcef9d33e36d0b8eebd84149891cabd5948072dfdc88122a74a30cd8bf1f"
OUT = Path(__file__).resolve().parent
NAMES = (
 "test_owned_command_binds_actual_child_and_preserves_first_failure",
 "test_driver_binds_real_both_origin_imports_before_exact_readiness",
)
EVENTS = []


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def write(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=30).strip()


def snapshot():
    assert sha(INPUTS) == INPUTS_SHA
    assert git(ROOT, "rev-parse", "HEAD") == HEAD and not git(ROOT, "status", "--porcelain")
    assert git(APP, "rev-parse", "HEAD") == APP_HEAD and not git(APP, "status", "--porcelain")
    data = json.loads(INPUTS.read_bytes())
    assert len(data["inputs"]) == 70
    rows = {}
    for item in data["inputs"]:
        assert item["origin"] in ("current", "originalApp")
        root = ROOT if item["origin"] == "current" else APP
        path = root / item["path"]
        assert path.resolve() == path and path.is_file() and not path.is_symlink()
        info = path.lstat()
        assert info.st_size == item["bytes"] and sha(path) == item["sha256"]
        key = item["origin"] + ":" + item["path"]
        assert key not in rows
        rows[key] = {"sha256": item["sha256"], "bytes": info.st_size, "mode": stat.S_IMODE(info.st_mode),
                     "inode": info.st_ino, "device": info.st_dev, "mtime_ns": info.st_mtime_ns}
    return {"source_sha": HEAD, "original_app_sha": APP_HEAD, "input_manifest_sha256": INPUTS_SHA,
            "controller_sha256": sha(__file__), "inputs": rows}


def loaded_sources(declared):
    found = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        raw = Path(filename).absolute()
        path = raw.resolve()
        origin = "current" if path.is_relative_to(ROOT) else "originalApp" if path.is_relative_to(APP) else None
        if origin is None:
            continue
        root = ROOT if origin == "current" else APP
        assert path == raw and path.suffix == ".py" and not path.is_symlink()
        key = origin + ":" + path.relative_to(root).as_posix()
        assert key in declared and sha(path) == declared[key]["sha256"], key
        entry = found.setdefault(key, {"sha256": sha(path), "modules": []})
        entry["modules"].append(name)
    for row in found.values():
        row["modules"].sort()
    assert "current:Tools/AnyEnginePort/native_ui_original_products_readiness.py" in found
    assert "originalApp:Tools/AnyEnginePort/verify_custom_type.py" in found
    return found


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        EVENTS.append({"event": "START", "test": test.id(), "time": now()})
        super().startTest(test)

    def addSuccess(self, test):
        EVENTS.append({"event": "PASS", "test": test.id(), "time": now()})
        super().addSuccess(test)

    def addFailure(self, test, error):
        EVENTS.append({"event": "FAIL", "test": test.id(), "time": now()})
        super().addFailure(test, error)

    def addError(self, test, error):
        EVENTS.append({"event": "ERROR", "test": test.id(), "time": now()})
        super().addError(test, error)

    def addSkip(self, test, reason):
        EVENTS.append({"event": "SKIP", "test": test.id(), "reason": reason, "time": now()})
        super().addSkip(test, reason)

    def addSubTest(self, test, subtest, error):
        if error is not None:
            EVENTS.append({"event": "SUBTEST_FAIL", "test": test.id(), "subtest": str(subtest), "time": now()})
        super().addSubTest(test, subtest, error)


def main():
    os.umask(0o077)
    assert shutil.disk_usage("/mnt/development").free >= 2500000000
    assert OUT == Path("/mnt/development/projects/evidence/native-ui-owned-readiness-20261123/attempt1")
    assert not (OUT / "intent.json").exists() and not (OUT / "result.json").exists()
    originals = OUT / "originals"
    originals.mkdir(mode=0o700)
    os.environ["PINKHA_UI_READINESS_CONTROL_ORIGINALS"] = str(originals)
    os.environ["PINKHA_UI_READINESS_ORIGINAL_APP"] = str(APP)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    receipt = {"status": "SOURCE_PREFLIGHT_PENDING", "started_at": now(), "source_sha": HEAD, "original_app_sha": APP_HEAD,
               "selected_methods": list(NAMES), "new_builds": 0, "apple_commands_executed": 0,
               "product_methods_executed": 0, "old_test_methods_reexecuted": 0,
               "python": sys.version, "python_executable": sys.executable,
               "python_executable_sha256": sha(Path(sys.executable).resolve())}
    write("intent.json", receipt)
    initial = None
    result = None
    failure = None
    try:
        initial = snapshot()
        write("source-before.json", initial)
        sys.path.insert(0, str(ROOT / "Tools/AnyEnginePort"))
        module = importlib.import_module("test_native_ui_original_products_readiness")
        assert Path(module.__file__).resolve() == ROOT / "Tools/AnyEnginePort/test_native_ui_original_products_readiness.py"
        # Import the actual immutable validators before any test body, so missing or foreign eager
        # dependencies fail as preflight, not as a partially executed qualification.
        module.r.ui.provider()
        actual_legacy = module.r.c.legacy_modules(APP)
        module.r.bind_modules(APP, actual_legacy)
        loaded_before = loaded_sources(initial["inputs"])
        write("loaded-sources-before.json", loaded_before)
        suite = unittest.TestSuite([module.UIOriginalProductsReadinessTests(name) for name in NAMES])
        expected = [test.id() for test in suite]
        started = time.monotonic()
        with (OUT / "controls.log").open("x") as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult)
            result = runner.run(suite)
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt.update(tests_run=result.testsRun, failures=len(result.failures),
                       errors=len(result.errors), skipped=len(result.skipped))
        starts = collections.Counter(x["test"] for x in EVENTS if x["event"] == "START")
        passes = collections.Counter(x["test"] for x in EVENTS if x["event"] == "PASS")
        assert result.wasSuccessful() and not result.skipped and result.testsRun == 2
        assert starts == passes == collections.Counter({name: 1 for name in expected})
        loaded_after = loaded_sources(initial["inputs"])
        write("loaded-sources-after.json", loaded_after)
        assert loaded_before == loaded_after
        receipt["actual_loaded_python_inputs"] = len(loaded_after)
        receipts = sorted(originals.rglob("*.command.json"))
        assert len(receipts) == 8
        observed = []
        for path in receipts:
            record = json.loads(path.read_bytes())
            assert record["argv"][0] == sys.executable and record["argv"][1] == "-c"
            assert record["cwd"] == str(ROOT) and record["owned_group_cleanup"] == "TERM_THEN_KILL"
            assert type(record["worker_pid"]) is int and record["worker_pid"] > 1
            assert not record.get("cleanup_error_type")
            qp = path.with_name(path.name.removesuffix(".command.json") + ".ui-quiescence.json")
            query = json.loads(qp.read_bytes())
            absence = query.get("quiescence")
            if absence is None:
                assert path == originals / "owned-command/nonzero.command.json"
                absence = json.loads((originals / "owned-command/nonzero-actual-owned-group-absence.json").read_bytes())
            assert absence["status"] == "PASS" and absence["pgid"] == record["worker_pid"] and absence["liveMembers"] == 0
            assert absence["kernelObservation"]["outcome"] == "ABSENT_ESRCH"
            observed.append({"path": path.relative_to(originals).as_posix(), "sha256": sha(path),
                             "worker_pid": record["worker_pid"], "return_code": record["return_code"],
                             "quiescence_sha256": sha(qp), "actual_group_absent": True})
        assert len({row["worker_pid"] for row in observed}) == 8
        assert collections.Counter(row["return_code"] for row in observed) == collections.Counter({0: 6, 9: 1, 13: 1})
        write("actual-owned-children.json", observed)
        receipt.update(status="PASS_TWO_NEW_UI_CONTROLS_APPLE_NOT_RUN", named_passes=sorted(passes),
                       actual_owned_control_children=8, actual_owned_groups_absent=8)
    except BaseException as error:
        failure = error
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
        with (OUT / "runner-error.log").open("x") as stream:
            stream.write(traceback.format_exc())
    finally:
        try:
            final = snapshot()
            write("source-after.json", final)
            assert initial is not None and initial == final
            receipt["declared_inputs_unchanged"] = True
        except BaseException as error:
            receipt["final_source_error"] = {"type": type(error).__name__, "message": str(error)}
            if failure is None:
                failure = error
        if failure is not None:
            receipt["status"] = "FAIL"
        write("events.json", EVENTS)
        receipt["finished_at"] = now()
        receipt["free_bytes_final"] = shutil.disk_usage("/mnt/development").free
        receipt["originals"] = {p.relative_to(OUT).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size,
                                  "mode": stat.S_IMODE(p.stat().st_mode)}
                               for p in sorted(OUT.rglob("*")) if p.is_file() and ".git" not in p.parts
                               and p.name not in ("launch.stdout.log", "launch.stderr.log")}
        write("result.json", receipt)
        print(json.dumps({"status": receipt["status"], "tests_run": receipt.get("tests_run", 0),
                          "result_sha256": sha(OUT / "result.json"),
                          "new_builds": 0, "product_methods_executed": 0}))
    return 0 if receipt["status"] == "PASS_TWO_NEW_UI_CONTROLS_APPLE_NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
