"""Falsify account-wire evidence; these controls are not native acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import run_account_rpc as runner
import test_account_lifecycle as baseline

SCHEMA = "9" * 64


def identity(role):
    return {**baseline.identity(role), "rpc_manifest_sha256": SCHEMA if role == "new" else "none"}


def report(phase="new-reopen", role="new"):
    value = baseline.phase_report(phase, role)
    if role == "new":
        value["runtime_observation"] = runner.expected_observation(phase, baseline.state(), SCHEMA)
    return value


def validate(value, phase="new-reopen", role="new"):
    runner.validate_phase(value, phase, role, identity(role), "fresh-nonce", Path("/disposable/account-root"),
                          42, baseline.state(), "f" * 64)


class AccountRPCControls(unittest.TestCase):
    def test_all_four_phases_require_exact_native_and_wire_observations(self):
        for phase, role in runner.base.PHASES:
            with self.subTest(phase=phase):
                validate(report(phase, role), phase, role)

    def test_valid_wire_evidence_cannot_hide_bad_baseline_before_or_after_observer(self):
        mutations = [
            (("heads",), ["different-change"]), (("raw_changes_sha256",), {}),
            (("nonce",), "other-process"), (("pid",), 43), (("account_id",), "other-account"),
            (("fixture_sha256",), "0" * 64), (("state_sha256",), "0" * 64),
            (("account_stop_verified",), False), (("closed",), False), (("test_passed",), False),
            (("app_capability",), "ON"), (("two_app_clients",), "PASS"),
            (("visibility", "exports"), {"document.json": "a" * 64}),
            (("visibility", "private_export"), "NOT_RUN"), (("visibility", "private_search"), "VISIBLE"),
            (("visibility", "ordinary_fulltext_control"), "NOT_RUN"), (("visibility", "block_sha256"), "0" * 64),
            (("visibility", "ordinary_name"), runner.base.VISIBLE),
            (("cleanup",), "NOT_RUN"), (("rpc_calls", "AccountCreate"), 1), (("rpc_calls", "AccountStop"), 0),
        ]
        for keys, wrong in mutations:
            with self.subTest(keys=keys):
                value = report("new-recover")
                target = value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = wrong
                with self.assertRaises(ValueError):
                    validate(value, "new-recover")

    def test_wire_and_baseline_observation_fields_cannot_be_missing_or_forged(self):
        value = report()
        for boundary in ["wire_boundary", "handler_boundary"]:
            for key in value["runtime_observation"][boundary]:
                for missing in [True, False]:
                    with self.subTest(boundary=boundary, key=key, missing=missing):
                        bad = copy.deepcopy(value)
                        if missing:
                            del bad["runtime_observation"][boundary][key]
                        else:
                            bad["runtime_observation"][boundary][key] = "NOT_RUN"
                        with self.assertRaises(ValueError):
                            validate(bad)
        for key in value["runtime_observation"]:
            bad = copy.deepcopy(value)
            del bad["runtime_observation"][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                validate(bad)

    def test_baseline_and_legacy_cannot_be_silently_upgraded_to_wire_acceptance(self):
        with self.assertRaises(ValueError):
            validate(baseline.phase_report("new-reopen", "new"))
        with self.assertRaises(ValueError):
            baseline.validate(report())
        legacy = report("legacy-edit", "legacy")
        legacy["runtime_observation"]["wire_boundary"] = runner.expected_observation("new-reopen", baseline.state(), SCHEMA)["wire_boundary"]
        with self.assertRaises(ValueError):
            validate(legacy, "legacy-edit", "legacy")

    def test_generation_must_match_exact_source_run_attempt_schema_and_outputs(self):
        generated = {"pb/commands.pb.go": "a" * 64}
        good = {"status": "PASS_PINNED_RPC_GENERATION", "app_sha": "b" * 40, "run_id": "123", "run_attempt": "1",
                "rpc_manifest_sha256": SCHEMA, "generated_sha256": generated,
                "app_capability": "OFF", "account_wire_acceptance": "NOT_RUN"}
        runner.generation_identity(good, "b" * 40, "123", "1", SCHEMA, generated)
        for run_id, attempt in [(None, "1"), ("123", None), ("0", "1"), ("123", "0")]:
            with self.subTest(run_id=run_id, attempt=attempt), self.assertRaises(ValueError):
                runner.generation_identity(good, "b" * 40, run_id, attempt, SCHEMA, generated)
        for key, wrong in [("status", "FAIL"), ("app_sha", "c" * 40), ("run_id", "124"), ("run_attempt", "2"),
                           ("rpc_manifest_sha256", "0" * 64), ("generated_sha256", {}),
                           ("app_capability", "ON"), ("account_wire_acceptance", "PASS")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                runner.generation_identity({**good, key: wrong}, "b" * 40, "123", "1", SCHEMA, generated)

    @unittest.skipUnless(sys.platform == "linux", "Real SIGTERM through account-RPC command ownership")
    def test_sigterm_while_command_runs_cannot_be_reported_as_account_wire_pass(self):
        harness = """
import json, os, signal, sys
from unittest import mock
import run_account_rpc as runner
def execute(args, receipt, run):
    child = "import os,signal,time; print('owned-ready',flush=True); time.sleep(.05); os.kill(os.getppid(),signal.SIGTERM); time.sleep(60)"
    run([sys.executable,'-c',child], 'owned', args.work.parent, os.environ.copy(), 5)
    return {'status':runner.PASS,'account_wire_acceptance':'PASS_REGISTERED_NATIVE_BYTES_SAME_ACCOUNT_FOUR_PROCESSES'}
old = signal.getsignal(signal.SIGTERM)
with mock.patch.object(runner, 'execute', execute):
    code=runner.main(sys.argv[1:])
assert signal.getsignal(signal.SIGTERM)==old
sys.exit(code)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = []
            for name in ["approved-source", "heart-legacy", "heart-new", "work", "evidence"]:
                args.extend(["--" + name, str(root / name)])
            result = subprocess.run([sys.executable, "-c", harness, *args, "--expected-app-sha", "a" * 40],
                                    cwd=Path(__file__).parent, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 1, result.stderr)
            receipt = json.loads((root / "evidence/receipt.json").read_text())
            self.assertEqual(receipt["status"], "CANCELLED")
            self.assertEqual(receipt["account_wire_acceptance"], "NOT_RUN")
            self.assertTrue(receipt["finished_at"])
            self.assertEqual(receipt["commands"][0]["status"], "CANCELLED")
            self.assertIn("owned-ready", (root / "evidence/owned.log").read_text())


if __name__ == "__main__":
    unittest.main()
