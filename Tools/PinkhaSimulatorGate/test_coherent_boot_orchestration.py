"""Only new cold-boot orchestration controls; Apple subprocesses are substituted."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/PinkhaNativeDerived"))
sys.path.insert(0, str(ROOT / "Tools/PinkhaNativeDerived/coherent_apple"))
import contract
import run_host
import simulator_selection
import test_coherent_runtime_admission as original_fixture


class CoherentBootOrchestrationControls(unittest.TestCase):
    def test_required_build_precedes_readiness_and_cleanup_cannot_replace_first_failure(self):
        with tempfile.TemporaryDirectory(prefix="coherent-boot-failure-control-") as temporary:
            root = Path(temporary)
            build = root / "build.json"
            build.write_text(json.dumps(dict(run_attempt="1", bridge_sha256="b" * 64, runtime_version="synthetic",
                frameworks={name: dict(binary_sha256=name) for name in ("production", "fixture")})))
            evidence = root / "proof"
            udid = "BAFA2C41-7334-4049-95AE-582A6418CEAC"
            wait = subprocess.TimeoutExpired(["xcrun", "simctl", "bootstatus", udid, "-b"], 180)
            calls = []
            def process(argv, cwd, env, log, timeout):
                calls.append((list(argv), timeout))
                if argv[:2] == ["xcodebuild", "-list"]:
                    raw = json.dumps({"workspace": {"schemes": [contract.PACKAGE]}}).encode()
                elif argv[:3] == ["xcrun", "simctl", "create"]:
                    raw = (udid + "\n").encode()
                elif argv[:3] == ["xcrun", "simctl", "list"]:
                    raw = b"{}\n"
                else:
                    raw = b""
                log.write_bytes(raw)
                if argv == wait.cmd:
                    raise wait
                if (argv[:3] in (["xcrun", "simctl", "shutdown"], ["xcrun", "simctl", "delete"])
                        or argv[:4] == ["xcrun", "simctl", "list", "devices"] or argv[0] == "/usr/bin/log"):
                    raise subprocess.TimeoutExpired(argv, timeout)
                return 2468
            original = SimpleNamespace(git=lambda _, *argv: "a" * 40 if argv[0] == "rev-parse" else "",
                command_json=lambda path: json.loads(path.read_bytes()), validate_pins=lambda _: {},
                native=SimpleNamespace(process_control=SimpleNamespace(run_process=process)))
            selected = dict(runtime={"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-2"},
                            device={"identifier": "com.apple.CoreSimulator.SimDeviceType.iPad-mini-A20-Pro"},
                            selection={"synthetic_control": True})
            argv = ["run_host.py", "--control", str(root), "--work", str(root / "work"), "--evidence", str(evidence),
                    "--build-receipt", str(build), "--frameworks", str(root / "frameworks"),
                    "--expected-app-sha", "a" * 40]
            with patch.object(sys, "argv", argv), patch.dict(os.environ, {"GITHUB_RUN_ID": "999123", "GITHUB_RUN_ATTEMPT": "1"}), \
                    patch.object(run_host, "load_helpers", return_value=(original, None)), \
                    patch.object(run_host.platform, "system", return_value="Darwin"), \
                    patch.object(run_host.platform, "machine", return_value="arm64"), \
                    patch.object(contract, "validate_build_receipt"), patch.object(contract, "verify_framework"), \
                    patch.object(run_host, "source_snapshot", return_value={}), \
                    patch.object(run_host, "prepare_harness", return_value=(root, {})), \
                    patch.object(simulator_selection, "choose_pair", return_value=selected):
                self.assertEqual(run_host.main(), 1)
            receipt = json.loads((evidence / "receipt.json").read_bytes())
            self.assertEqual(receipt["error_type"], "TimeoutExpired")
            self.assertEqual(receipt["error"], str(wait))
            self.assertEqual(receipt["primary_failure"], {"error_type": "TimeoutExpired", "error": str(wait)})
            commands = receipt["commands"]
            names = [entry["name"] for entry in commands]
            self.assertLess(names.index("boot-owned-simulator"), names.index("ios-coherent-build"))
            self.assertLess(names.index("ios-coherent-build"), names.index("wait-owned-simulator"))
            self.assertEqual(names.count("wait-owned-simulator"), 1)
            self.assertNotIn("ios-coherent-tests", names)
            self.assertNotIn("actual_execution", receipt)
            self.assertEqual(receipt["harness_build"]["tests_executed"], 0)
            self.assertEqual([entry["argv"][1] for entry in commands if entry["name"] == "ios-coherent-build"], ["build-for-testing"])
            failed = commands[names.index("wait-owned-simulator")]
            self.assertEqual((failed["status"], failed["timeout_seconds"], failed["log_bytes"]), ("FAIL", 180, 0))
            self.assertEqual(failed["log_sha256"], hashlib.sha256(b"").hexdigest())
            self.assertEqual(failed["error"], str(wait))
            self.assertGreaterEqual(failed["elapsed_seconds"], 0)
            self.assertTrue(failed["started_at"] and failed["finished_at"])
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
            self.assertEqual(set(receipt["owned_simulator_cleanup"]), {"shutdown", "delete"})
            self.assertEqual(set(receipt["diagnostic_failures"]),
                             {"owned-simulator-failure-state", "owned-simulator-failure-system-log"})
            self.assertEqual([timeout for command, timeout in calls if command[:3] in
                              (["xcrun", "simctl", "shutdown"], ["xcrun", "simctl", "delete"])], [30, 30])
            self.assertTrue(all(command[-1] == udid for command, _ in calls
                                if command[:3] in (["xcrun", "simctl", "shutdown"], ["xcrun", "simctl", "delete"])))

    def test_split_execution_admission_requires_same_build_destination_order_and_method(self):
        # Reuse only the existing synthetic input builder, never its old tests.
        original_fixture.CoherentAdmissionControls.setUpClass()
        def configure(value):
            host = value["host"]
            udid = original_fixture.UDID
            command = ["xcodebuild", "test-without-building", "-scheme", contract.PACKAGE,
                       "-destination", "platform=iOS Simulator,id=" + udid,
                       "-derivedDataPath", "/synthetic/DerivedData", "-resultBundlePath", "/synthetic/coherent-heart.xcresult",
                       "-only-testing:" + contract.TARGET + "/" + contract.METHOD]
            build = list(command); build[1] = "build-for-testing"
            build[build.index("-resultBundlePath") + 1] = "/synthetic/coherent-heart-build.xcresult"
            host.update(owned_simulator={"udid": udid}, harness_build=dict(status="BUILT_CURRENT_HARNESS_NOT_EXECUTED",
                tests_executed=0, boot_readiness="SEPARATE_BOUNDED_CHECK_REQUIRED"), commands=[
                dict(name="boot-owned-simulator", status="PASS_EXIT_0", argv=["xcrun", "simctl", "boot", udid]),
                dict(name="ios-coherent-build", status="PASS_EXIT_0", argv=build),
                dict(name="wait-owned-simulator", status="PASS_EXIT_0", argv=["xcrun", "simctl", "bootstatus", udid, "-b"]),
                dict(name="ios-coherent-tests", status="PASS_EXIT_0", argv=command)])
        def wrong_build(host):
            host["commands"][1]["argv"][host["commands"][1]["argv"].index("-derivedDataPath") + 1] = "/another/DerivedData"
        def wrong_order(host):
            host["commands"][1], host["commands"][2] = host["commands"][2], host["commands"][1]
        def wrong_destination(host):
            host["owned_simulator"]["udid"] = "00000000-0000-0000-0000-000000000000"
        mutations = [None, wrong_build, wrong_order, wrong_destination,
                     lambda host: host["commands"][1].update(status="FAIL"),
                     lambda host: host["commands"][-1]["argv"].append("-only-testing:Unrelated/testOther"),
                     lambda host: host["harness_build"].update(tests_executed=False)]
        for mutation in mutations:
            helper = original_fixture.CoherentAdmissionControls()
            helper.setUp()
            try:
                def mutate(value):
                    configure(value)
                    if mutation:
                        mutation(value["host"])
                value = helper.fixture(mutate=mutate)
                if mutation is None:
                    self.assertEqual(helper.run_fixture(value)["status"], "PASS")
                    self.assertFalse(any(argv[0] in ("xcodebuild", "go", "swift") for argv in helper.calls))
                else:
                    with self.subTest(mutation=mutation.__name__), self.assertRaises(RuntimeError):
                        helper.run_fixture(value)
                    helper.assert_not_installed()
            finally:
                helper.doCleanups()


if __name__ == "__main__":
    unittest.main()
