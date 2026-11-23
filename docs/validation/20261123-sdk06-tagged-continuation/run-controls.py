#!/usr/bin/env python3
"""Run only the four new tagged-route controls after frozen Git/source admission."""
import argparse
import datetime
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
INPUTS = "docs/validation/20261123-sdk06-tagged-continuation/control-inputs.json"
TEST = "test_sdk06_tagged_continuation"
METHODS = (
    "test_pending_tag_preserves_all_bodies_arguments_exclusions_and_target_membership",
    "test_historical_view_retains_only_its_original_scope_and_rejects_dependency_or_member_drift",
    "test_actual_current_tag_enumeration_binds_exact23_and_one_use_execution_argv",
    "test_one_current_build_archives_then_refuses_all_product_phases_on_wrong_tag_enumeration",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def frozen_files():
    raw = (ROOT / INPUTS).read_bytes()
    manifest = json.loads(raw)
    rows = manifest["files"]
    assert manifest["schema"] == "sdk06-tagged-controls-inputs-v1"
    assert len(rows) == len({row["path"] for row in rows})
    expected = {row["path"]: row for row in rows}
    assert INPUTS not in expected
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, timeout=30).strip()
    request = "".join(head + ":" + path + "\n" for path in [INPUTS, *sorted(expected)]).encode()
    result = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch"],
        input=request, capture_output=True, check=True, timeout=45)
    stream = io.BytesIO(result.stdout)
    tree_raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-rz", head,
        "--", INPUTS, *sorted(expected)], timeout=30)
    tree = {}
    for row in tree_raw.split(b"\0"):
        if not row: continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        assert kind == "blob" and mode in {"100644", "100755"}
        tree[name.decode()] = (mode, object_id)
    assert set(tree) == set(expected) | {INPUTS}
    observed = {}
    for path in [INPUTS, *sorted(expected)]:
        header = stream.readline().decode().strip().split()
        assert len(header) == 3 and header[1] == "blob" and header[2].isdigit(), path
        size = int(header[2]); assert 0 <= size <= 4 * 1024**2
        blob = stream.read(size); assert len(blob) == size and stream.read(1) == b"\n"
        physical = ROOT / path
        assert not physical.is_symlink() and stat.S_ISREG(physical.stat().st_mode), path
        actual = physical.read_bytes()
        assert actual == blob, "Physical/frozen Git bytes differ: " + path
        mode = "100755" if physical.stat().st_mode & 0o111 else "100644"
        assert tree[path] == (mode, header[0]), "Frozen Git mode/object differs: " + path
        if path != INPUTS:
            assert sha(actual) == expected[path]["sha256"] and mode == expected[path]["git_mode"], path
        observed[path] = dict(sha256=sha(actual), bytes=len(actual), git_object=header[0], git_mode=mode)
    assert stream.read() == b""
    return dict(source_sha=head, manifest_sha256=sha(raw), files=observed)


def loaded_sources(inventory):
    result = {}
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if not raw: continue
        path = Path(raw).resolve()
        if path.suffix != ".py" or not path.is_relative_to(ROOT / "Tools"): continue
        relative = path.relative_to(ROOT).as_posix()
        assert relative in inventory["files"], "Unfrozen imported dependency: " + relative
        assert not path.name.startswith("test_") or path.name == TEST + ".py", "Old control module imported"
        actual = sha(path.read_bytes())
        assert actual == inventory["files"][relative]["sha256"], relative
        result[relative] = actual
    assert "Tools/PinkhaSimulatorGate/" + TEST + ".py" in result
    return dict(sorted(result.items()))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    destination = args.evidence.resolve()
    assert not destination.exists() and not destination.is_symlink()
    destination.mkdir(parents=True)
    receipt = dict(status="PRECHECK", started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        requested_methods=[TEST + ".TaggedSDK06Controls." + name for name in METHODS],
        old_controller_methods_executed=0, apple_builds=0, product_tests=0,
        actual_compiled_tag_enumeration="NOT_RUN", original_products_relabelled=False)
    save(destination / "receipt.json", receipt)
    events = []
    started = time.monotonic()
    try:
        before = frozen_files()
        save(destination / "source-before.json", before)
        sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
        module = importlib.import_module(TEST)
        # The second new control calls this unchanged production verifier.
        # Preload its definitions before measuring the frozen loaded closure;
        # this does not call the verifier or import/execute any old test.
        importlib.import_module("sdk06_retained_controls")
        loaded_before = loaded_sources(before)
        save(destination / "loaded-before.json", loaded_before)
        assert {name for name in vars(module.TaggedSDK06Controls) if name.startswith("test_")} == set(METHODS)
        class Result(unittest.TextTestResult):
            def startTest(self, test):
                events.append(dict(event="start", method=test.id()))
                super().startTest(test)
            def addSuccess(self, test):
                events.append(dict(event="PASS", method=test.id()))
                super().addSuccess(test)
            def addError(self, test, error):
                events.append(dict(event="ERROR", method=test.id(), error_type=error[0].__name__))
                super().addError(test, error)
            def addFailure(self, test, error):
                events.append(dict(event="FAIL", method=test.id(), error_type=error[0].__name__))
                super().addFailure(test, error)
            def addSkip(self, test, reason):
                events.append(dict(event="SKIP", method=test.id(), reason=reason))
                super().addSkip(test, reason)
            def addSubTest(self, test, subtest, error):
                events.append(dict(event="subcase", method=test.id(), subcase=str(subtest),
                                   result="PASS" if error is None else "FAIL"))
                super().addSubTest(test, subtest, error)
        suite = unittest.TestSuite(module.TaggedSDK06Controls(name) for name in METHODS)
        with (destination / "tests.log").open("x") as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(suite)
        after = frozen_files()
        loaded_after = loaded_sources(after)
        save(destination / "source-after.json", after)
        save(destination / "loaded-after.json", loaded_after)
        assert before == after, "Frozen source/dependency bytes changed during the controls"
        assert loaded_before == loaded_after, "Loaded controller closure changed during controls"
        receipt.update(status="PASS" if result.wasSuccessful() and result.testsRun == 4 and not result.skipped else "FAIL",
            tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
            skipped=len(result.skipped), source_sha=before["source_sha"],
            input_count=len(before["files"]), loaded_count=len(loaded_before),
            sources_unchanged=True, loaded_sources_unchanged=True,
            source_before_sha256=sha((destination / "source-before.json").read_bytes()),
            source_after_sha256=sha((destination / "source-after.json").read_bytes()),
            log_sha256=sha((destination / "tests.log").read_bytes()))
    except BaseException as error:
        receipt.update(status="PRECHECK_OR_POSTCHECK_ERROR", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save(destination / "events.json", events)
        receipt.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       duration_seconds=time.monotonic()-started,
                       events_sha256=sha((destination / "events.json").read_bytes()))
        save(destination / "receipt.json", receipt)
        print(json.dumps({key: receipt.get(key) for key in ("status", "tests_run", "input_count", "loaded_count", "duration_seconds")}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
