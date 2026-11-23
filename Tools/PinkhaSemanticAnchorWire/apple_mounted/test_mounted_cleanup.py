"""Only the new Page154 cleanup caller/namespace adapter controls."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock

import mounted_cleanup as cleanup

UDID = "DC20C505-8314-42B2-B90F-766F8E8260E7"
NONCE = "a" * 32


class TupleRunner:
    def __init__(self, root, receipt, *, timeout=False, bad=None):
        self.root, self.receipt, self.timeout, self.bad = root, receipt, timeout, bad
        self.calls = []; self.time = 0.0

    def run(self, argv, name, *, timeout):
        index = len(self.calls); self.calls.append((argv, name, timeout))
        path = self.root / (name + ".log")
        path.write_text(json.dumps({"devices": {"control-runtime": []}}))
        pid = 501 + index
        record = dict(name=name, argv=argv, return_code=0, worker_pid=pid,
            owned_group_cleanup="TERM_THEN_KILL",
            owned_group_quiescence=dict(status="PASS", live_members=0, pgid=pid),
            log_sha256=cleanup.mounted.digest(path))
        self.time += 30 if index == 0 and self.timeout else .1
        if self.bad == "group" and index == 0:
            record["quiescence_failure"] = {"error_type": "TimeoutExpired"}
            record["owned_group_quiescence"]["status"] = "FAIL"
        if self.bad == "nonzero" and index == 1: record["return_code"] = 1
        if not (self.bad == "missing-record" and index == 0):
            self.receipt.setdefault("commands", []).append(record)
        if index == 0 and self.timeout:
            record.update(status="TIMED_OUT", return_code=-9, error_type="TimeoutExpired")
            raise subprocess.TimeoutExpired(argv, timeout)
        return path, record


class MountedCleanupAdapterControls(unittest.TestCase):
    def test_qualified_policy_body_is_identical_and_import_names_remain_scoped(self):
        root = Path(cleanup.__file__).resolve().parents[3]
        original = Path(os.environ.get("PINKHA_ORIGINAL_CLEANUP_POLICY", str(root / cleanup.ORIGINAL_POLICY_PATH)))
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), cleanup.ORIGINAL_POLICY_SHA256)
        source = original.read_text(); adapted = Path(cleanup.__file__).read_text()
        def function(text):
            return next(v for v in ast.parse(text).body
                if isinstance(v, ast.FunctionDef) and v.name == "cleanup_owned_simulator")
        original_node = function(source); adapted_node = function(adapted)
        self.assertEqual(ast.dump(original_node, include_attributes=False),
                         ast.dump(adapted_node, include_attributes=False))
        original_body = ast.get_source_segment(source, original_node)
        self.assertEqual(ast.get_source_segment(adapted, adapted_node), original_body)
        self.assertEqual(hashlib.sha256(original_body.encode()).hexdigest(), cleanup.ORIGINAL_FUNCTION_SHA256)
        aliases = {name: ModuleType("unrelated_" + name) for name in ("contract", "execution", "proof")}
        with mock.patch.dict(sys.modules, aliases):
            spec = importlib.util.spec_from_file_location("page154_cleanup_namespace_control", cleanup.__file__)
            isolated = importlib.util.module_from_spec(spec); spec.loader.exec_module(isolated)
            for name, unrelated in aliases.items(): self.assertIs(sys.modules[name], unrelated)
            self.assertIsNot(isolated.contract, aliases["contract"])
            self.assertIsNot(isolated.execution, aliases["execution"])
            self.assertIsNot(isolated.proof, aliases["proof"])

    def test_tuple_path_adapter_retains_original_timeout_and_prior_product_failure(self):
        for timed_out in (False, True):
            for previous in (None, RuntimeError("original product failure")):
                with self.subTest(timeout=timed_out, previous=previous is not None), tempfile.TemporaryDirectory() as tmp:
                    receipt = {"owned_simulator": {"udid": UDID}}
                    runner = TupleRunner(Path(tmp), receipt, timeout=timed_out)
                    final = cleanup.finalize_mounted_simulator(runner, receipt, UDID, previous, clock=lambda: runner.time)
                    self.assertIs(final, previous)
                    self.assertEqual(receipt["owned_simulator_cleanup_status"], "COMPLETE")
                    self.assertEqual(receipt["mounted_cleanup_adapter"]["status"], "PASS")
                    self.assertEqual(len(runner.calls), 3 if timed_out else 2)
                    self.assertEqual(receipt["owned_simulator_cleanup_budget"]["total_seconds"], 60.0)
                    if timed_out:
                        self.assertEqual(receipt["owned_simulator_cleanup"]["shutdown"]["status"], "FAIL")
                        self.assertEqual(receipt["owned_simulator_cleanup"]["shutdown"]["error_type"], "TimeoutExpired")
                        self.assertEqual(receipt["commands"][0]["error_type"], "TimeoutExpired")
                        self.assertEqual(runner.calls[2][0], ["xcrun", "simctl", "list", "devices", UDID, "-j"])
                        self.assertEqual(receipt["owned_simulator_cleanup_reconciliation"]["status"],
                                         "VERIFIED_ABSENT_AFTER_DELETE")

    def test_incomplete_command_records_or_quiescence_never_turn_cleanup_into_pass(self):
        for bad in ("group", "nonzero", "missing-record"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                receipt = {"owned_simulator": {"udid": UDID}}
                runner = TupleRunner(Path(tmp), receipt, timeout=True, bad=bad)
                previous = RuntimeError("first product failure must remain primary")
                final = cleanup.finalize_mounted_simulator(runner, receipt, UDID, previous, clock=lambda: runner.time)
                self.assertIs(final, previous)
                self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")
                self.assertEqual(receipt["mounted_cleanup_adapter"]["status"], "FAIL")
                self.assertEqual(receipt["owned_simulator_cleanup"]["shutdown"]["error_type"], "TimeoutExpired")
        with tempfile.TemporaryDirectory() as tmp:
            receipt = {"owned_simulator": {"udid": UDID}}
            runner = TupleRunner(Path(tmp), receipt, timeout=True, bad="group")
            final = cleanup.finalize_mounted_simulator(runner, receipt, UDID, None, clock=lambda: runner.time)
            self.assertIsInstance(final, ValueError)
            self.assertEqual(receipt["owned_simulator_cleanup_status"], "INCOMPLETE")

    def test_recovered_creation_owner_is_bound_to_exact_original_command_and_log(self):
        argv = ["xcrun", "simctl", "create", "Page154Mounted-" + NONCE, "control-device-type", "control-runtime"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "create-owned-simulator.log"; path.write_text(UDID + "\n")
            original = {"commands": [dict(name="create-owned-simulator", argv=argv, log_sha256=cleanup.mounted.digest(path))]}
            receipt = copy.deepcopy(original)
            actual = cleanup.recover_original_created_simulator(path, receipt, argv, NONCE)
            self.assertEqual(actual, UDID)
            self.assertEqual(receipt["owned_simulator"]["udid"], UDID)
            self.assertTrue(receipt["owned_simulator"]["recovered_from_original_create_command"])
            self.assertEqual(receipt["owned_simulator"]["original_create_log_sha256"], cleanup.mounted.digest(path))
            for mode in ("different-command", "wrong-log", "duplicate-record", "existing-owner", "different-nonce"):
                receipt = copy.deepcopy(original)
                if mode == "different-command": receipt["commands"][0]["argv"] = argv[:-1] + ["other-runtime"]
                if mode == "wrong-log": receipt["commands"][0]["log_sha256"] = "0" * 64
                if mode == "duplicate-record": receipt["commands"].append(copy.deepcopy(receipt["commands"][0]))
                if mode == "existing-owner": receipt["owned_simulator"] = {"udid": "unrelated"}
                before = copy.deepcopy(receipt)
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    cleanup.recover_original_created_simulator(path, receipt, argv,
                        "b" * 32 if mode == "different-nonce" else NONCE)
                self.assertEqual(receipt, before)
            self.assertIsNone(cleanup.recover_original_created_simulator(Path(tmp) / "absent.log", {}, None, NONCE))


if __name__ == "__main__":
    unittest.main()
