"""Two new source-origin controls; no native, simulator, or older control executes."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = ROOT / "docs/validation/20261123-page-source-origins/control-inputs.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture_git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Source Origin Control",
         "-c", "user.email=source-origin-control@example.invalid", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    if result.returncode:
        raise AssertionError("Owned fixture Git failed: " + result.stderr.decode(errors="replace"))
    return result.stdout.decode().strip()


def create_commit(root):
    fixture_git(root, "init", "-q")
    fixture_git(root, "add", ".")
    fixture_git(root, "commit", "-q", "-m", "Synthetic source-origin control")
    return fixture_git(root, "rev-parse", "HEAD")


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def child(mode, output):
    """Real independent Git roots plus the actual complete current import closure."""
    manifest = json.loads(INPUTS.read_bytes())
    declared = [row for row in manifest["inputs"] if row["role"] == "current_eager_python"]
    assert len(declared) == 33
    before_sources = {}
    for row in manifest["inputs"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert digest(raw) == row["sha256"]
        before_sources[row["path"]] = row["sha256"]
    report = {
        "protocol": "page-source-origin-real-git-control-v1",
        "mode": mode,
        "synthetic_git_fixture": True,
        "actual_product_or_native_methods": 0,
        "actual_simulator_commands": 0,
        "actual_imports_from_current_frozen_source": True,
        "source_before": before_sources,
        "fixture_owner_pid": os.getpid(),
    }
    with tempfile.TemporaryDirectory(prefix="page-origin-", dir=output) as directory:
        base = Path(directory).resolve()
        controller = base / "controller"
        app = base / "app"
        controller.mkdir()
        app.mkdir()
        expected_current = {}
        for row in declared:
            target = controller / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / row["path"]).read_bytes()
            target.write_bytes(raw)
            target.chmod(int(row["physical_mode"], 8))
            expected_current[row["path"]] = digest(raw)
        current_values = {
            "Modules/Synthetic/Version.swift": b"let version = \"current-only-module\"\n",
            ".gitattributes": b"*.json text eol=lf\n",
        }
        app_values = {
            "Modules/Synthetic/Version.swift": b"let version = \"original-compiled-app\"\n",
            "AnyTypeTests/Synthetic.swift": b"// immutable original test source\n",
            "Tools/AppOnlyProbe.py": b"VALUE = 'must never become a controller dependency'\n",
        }
        for root, values in ((controller, current_values), (app, app_values)):
            for name, raw in values.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        expected_current.update({name: digest(raw) for name, raw in current_values.items()})
        expected_app = {name: digest(raw) for name, raw in app_values.items()}
        current_sha = create_commit(controller)
        app_sha = create_commit(app)
        assert current_sha != app_sha
        mounted = import_file("page_origin_actual_mounted_control",
                              controller / "Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py")
        origins = mounted.mounted_source_origins
        actual = origins.capture(controller, app, current_sha, app_sha, mounted.consumer)
        assert actual["controller_inputs"] == expected_current
        assert actual["app_inputs"] == expected_app
        assert mounted.product_inputs(expected_app) == mounted.product_inputs(actual["app_inputs"])
        assert mounted.product_inputs(expected_app) != mounted.product_inputs(actual["controller_inputs"])
        expected_imports = {
            "page154_original_consumer_helpers": "Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py",
            "mounted_source_origins": "Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_source_origins.py",
            "mounted_contract": "Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_contract.py",
            "run_owned_single_lane": "Tools/PinkhaSimulatorGate/run_owned_single_lane.py",
            "wave15_batch": "Tools/PinkhaSimulatorGate/wave15_batch.py",
        }
        for name, path in expected_imports.items():
            assert actual["loaded_controller_modules"][name] == {
                "path": path, "sha256": expected_current[path]}
        report["before"] = origins.receipt(actual)
        report["independent_expected_current_inputs"] = expected_current
        report["independent_expected_app_inputs"] = expected_app
        report["former_comparison_would_refuse"] = True
        refusals = []

        def refused(label, operation):
            try:
                operation()
            except ValueError as error:
                expected_reason = {
                    "same-root": "Controller and App roots must be disjoint",
                    "nested-root": "Controller and App roots must be disjoint",
                    "wrong-controller-head": "Exact clean published source checkout required",
                    "wrong-app-head": "Exact clean published source checkout required",
                    "foreign-consumer-helper": "Actual consumer helper must come from the current controller",
                    "loaded-app-module": "Compiled App source checkout must not supply controller modules: page_origin_foreign_app_probe",
                    "app-source-postflight-drift": "Exact clean published source checkout required",
                    "controller-source-postflight-drift": "Exact clean published source checkout required",
                }[label]
                assert str(error) == expected_reason, (label, str(error), expected_reason)
                refusals.append({"case": label, "type": type(error).__name__, "message": str(error)})
            else:
                raise AssertionError("Unexpected source-origin admission: " + label)

        if mode == "success":
            after = origins.verify_current(actual, mounted.consumer)
            assert after["controller_inputs"] == actual["controller_inputs"]
            assert after["app_inputs"] == actual["app_inputs"]
            assert after["loaded_controller_modules"] == actual["loaded_controller_modules"]
            report["after"] = origins.receipt(after)
            assert report["after"]["current_controller_is_compiled_app_source"] is False
            assert report["after"]["product_acceptance"] is False
        elif mode == "refusals":
            refused("same-root", lambda: origins.capture(controller, controller, current_sha,
                                                          app_sha, mounted.consumer))
            nested = controller / "nested-app"
            nested.mkdir()
            refused("nested-root", lambda: origins.capture(controller, nested, current_sha,
                                                            app_sha, mounted.consumer))
            refused("wrong-controller-head", lambda: origins.capture(controller, app, "f" * 40,
                                                                     app_sha, mounted.consumer))
            refused("wrong-app-head", lambda: origins.capture(controller, app, current_sha,
                                                              "f" * 40, mounted.consumer))
            foreign = import_file("page_origin_foreign_app_probe", app / "Tools/AppOnlyProbe.py")
            refused("foreign-consumer-helper", lambda: origins.capture(controller, app, current_sha,
                                                                       app_sha, foreign))
            refused("loaded-app-module", lambda: origins.capture(controller, app, current_sha,
                                                                 app_sha, mounted.consumer))
            del sys.modules["page_origin_foreign_app_probe"]
            for label, root, values in (
                    ("app-source-postflight-drift", app, app_values),
                    ("controller-source-postflight-drift", controller, current_values)):
                path = root / "Modules/Synthetic/Version.swift"
                original = values["Modules/Synthetic/Version.swift"]
                path.write_bytes(original + b"// deliberate synthetic drift\n")
                try:
                    refused(label, lambda: origins.verify_current(actual, mounted.consumer))
                finally:
                    path.write_bytes(original)
            after = origins.verify_current(actual, mounted.consumer)
            assert len(refusals) == 8
            report["after"] = origins.receipt(after)
            report["refusals"] = refusals
        else:
            raise AssertionError("Only the two new fixed control modes are allowed")
        report["source_after"] = {row["path"]: digest((ROOT / row["path"]).read_bytes())
                                  for row in manifest["inputs"]}
        assert report["source_after"] == before_sources
    report["owned_temporary_fixtures_removed"] = True
    report["status"] = "PASS_NEW_SOURCE_ORIGIN_CONTROL"
    print(json.dumps(report, sort_keys=True))


class PageSourceOriginControls(unittest.TestCase):
    def _run(self, mode):
        output = Path(os.environ["PINKHA_PAGE_ORIGIN_CONTROL_OUTPUT"]).resolve()
        self.assertTrue(output.is_dir())
        name = "real-origin-" + mode
        stdout = output / (name + ".stdout.json")
        stderr = output / (name + ".stderr")
        self.assertFalse(stdout.exists() or stderr.exists())
        command = [sys.executable, "-B", str(Path(__file__).resolve()),
                   "--source-origin-child", mode, str(output)]
        primary = None
        cleanup_error = None
        started = time.monotonic()
        with stdout.open("xb") as out, stderr.open("xb") as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True)
            try:
                process.wait(timeout=90)
            except BaseException as error:
                primary = error
            finally:
                try:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=5)
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        group_absent = True
                    else:
                        group_absent = False
                        os.killpg(process.pid, signal.SIGKILL)
                        raise AssertionError("Owned origin-control group still present")
                except BaseException as error:
                    cleanup_error = error
        receipt = {
            "command": command, "return_code": process.returncode,
            "owned_pid": process.pid, "owned_pgid": process.pid,
            "new_session": True, "seconds": time.monotonic() - started,
            "stdout_sha256": digest(stdout.read_bytes()),
            "stderr_sha256": digest(stderr.read_bytes()),
            "primary_error": None if primary is None else {
                "type": type(primary).__name__, "message": str(primary)},
            "separate_cleanup_error": None if cleanup_error is None else {
                "type": type(cleanup_error).__name__, "message": str(cleanup_error)},
            "owned_group_absent": cleanup_error is None and group_absent,
            "old_or_product_tests": 0,
        }
        with (output / (name + ".command.json")).open("x") as file:
            file.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        if primary is not None:
            raise primary
        if cleanup_error is not None:
            raise cleanup_error
        self.assertEqual(process.returncode, 0, stderr.read_text()[-3000:])
        value = json.loads(stdout.read_bytes())
        self.assertEqual(value["status"], "PASS_NEW_SOURCE_ORIGIN_CONTROL")
        self.assertEqual(value["mode"], mode)
        self.assertTrue(value["owned_temporary_fixtures_removed"])
        self.assertEqual(value["source_before"], value["source_after"])

    def test_real_current_controller_and_original_app_have_separate_complete_source_admission(self):
        self._run("success")

    def test_actual_origin_adapter_refuses_wrong_roots_heads_foreign_imports_and_postflight_drift(self):
        self._run("refusals")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--source-origin-child"]:
        child(sys.argv[2], Path(sys.argv[3]))
    else:
        raise SystemExit("Use the pinned two-method source wrapper; no default test discovery.")
