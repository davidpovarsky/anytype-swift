"""Three synthetic API/custody controls; no W2-control replay or Apple command."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

import admission
from originals import Originals
import profile_binding
import run

SPAWN_EVENTS = []
INPUTS = {}


def forbid_children(event, args):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork"}:
        SPAWN_EVENTS.append(event)
        raise AssertionError("This portable binding control may not launch a child command")


sys.addaudithook(forbid_children)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original(path, expected):
    raw = path.read_bytes()
    actual = profile_binding.identity(raw)
    if actual != expected:
        raise AssertionError("Exact original fixture source changed: " + str(path))
    INPUTS[str(path)] = actual
    return raw


class PublishedW2BindingControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="app10-binding-only-")
        self.source = Path(self.temporary.name) / "source"
        self.source.mkdir()
        control = Path(__file__).resolve().parent
        manifest = json.loads((control / "original_sources.json").read_bytes())
        base = Path(os.environ["PINKHA_APP10_ORIGINAL_SOURCE"]).resolve(strict=True)
        for relative, pin in manifest["files"].items():
            self.copy(relative, original(base / relative, pin))
        dependency = json.loads((control / "profile-dependency.json").read_bytes())
        published = Path(os.environ["PINKHA_APP10_PRIMARY_PROFILE"]).resolve(strict=True)
        for relative, pin in dependency["files"].items():
            self.copy(relative, original(published / relative, pin))
        inventory_path = Path(os.environ["PINKHA_APP10_SWIFT_INVENTORY"]).resolve(strict=True)
        inventory_raw = inventory_path.read_bytes()
        self.assertEqual(sha(inventory_raw), "3e51d4dc0af88735938cd4b4eca8da5b3755d88d0050ec860b57ef0b19642942")
        inventory = json.loads(inventory_raw)
        specification = json.loads((self.source / profile_binding.W2_PREFIX / "profile.json").read_bytes())
        for key, inventory_key in (("g05", "G05"), ("g07", "G07"), ("bin", "Bin")):
            row = inventory["sourceInputs"][inventory_key]["test"]
            raw = original(Path(row["path"]), {k: row[k] for k in ("bytes", "sha256", "gitBlob")})
            self.assertEqual(sha(raw), specification["sources"][key]["sha256"])
            self.copy(specification["sources"][key]["path"], raw)
        self.originals = Originals(self.source)
        try:
            self.originals.install()
            self.gate = SimpleNamespace(is_open=True)
            self.binding = profile_binding.RuntimeBindings(self.originals, self.gate)
        except BaseException:
            self.originals.close()
            raise
        self.witness_calls = []
        self.fixture_source_commit = "1" * 40
        self.fixture_proof = {"path": str(self.source / "SYNTHETIC-NOT-A-COMPILER-RECEIPT.json"), "sha256": "2" * 64}

    def copy(self, relative, raw):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.open("xb").write(raw)

    def tearDown(self):
        try:
            self.binding.unchanged()
            self.originals.unchanged()
            self.assertFalse(SPAWN_EVENTS)
        finally:
            self.originals.close()
            self.temporary.cleanup()

    def witness(self, source, *, source_commit, native_compilation_proof, expected_sources, rtl_profile_path):
        # Only the inherited compiler-witness I/O is replaced in this local
        # synthetic control. All published profile and original host code runs
        # from its actual exact bytes. This is never a producer receipt.
        self.assertTrue(self.gate.is_open)
        self.witness_calls.append({"source": str(source), "source_commit": source_commit,
            "expected_sources": copy.deepcopy(expected_sources)})
        return {"source_hashes": expected_sources, "tests_executed": 0,
                "actual_native_compiler_witnesses": [{"SYNTHETIC_BINDING_CONTROL_ONLY": True}],
                "witness_validator_sha256": "60fbe9557ad82cd9ee33016e7bd264ac55843c9b27b2eb3862a35481c0741967"}

    def contract(self, lane):
        return self.binding.source_contract(lane, source_commit=self.fixture_source_commit,
            native_compilation_proof=self.fixture_proof)

    @staticmethod
    def enumeration(identifiers):
        return {"errors": [], "values": [{"testPlan": "AnytypeTests",
            "enabledTests": [{"identifier": value} for value in identifiers], "disabledTests": []}]}

    def test_same_published_instance_reaches_all_original_host_callbacks(self):
        self.assertEqual(self.binding.originals.proof["manifestSHA256"],
                         "b0afbd53aef99cc44adc77432c6fba6b7b060faf4808e81ec01799df3d2e627c")
        self.assertEqual(len(self.binding.proof["unchangedOriginalDeclarations"]), 12)
        instances = []
        with patch.object(self.originals.witness, "verify_native_compiler_sources", self.witness):
            with patch.object(self.binding.profile, "validators", wraps=self.binding.profile.validators) as factory:
                for lane in run.LANES:
                    contract = self.contract(lane)
                    wrapper = self.binding.validators(lane)
                    qualified = wrapper.qualified
                    instances.append(qualified)
                    self.assertIs(type(qualified), self.binding.profile.CompilerQualifiedProfile)
                    self.assertIs(qualified.originals, self.originals)
                    self.assertEqual(contract["original_target"], profile_binding.ORIGINAL_TARGETS[lane])
                    expected = contract["expected_compiled_identifiers"]
                    actual = self.binding.host_functions.invocation_selectors(expected, contract)
                    if lane == "product-g07-drop-authority-hosted":
                        self.assertEqual(actual, expected)
                    else:
                        self.assertEqual(actual, ["AnytypeTests/" + contract["suite"]])
                    selected = self.binding.host_functions.host_validation_module(contract, {})
                    self.assertIs(selected, wrapper)
                    payload = self.enumeration(expected)
                    self.binding.host_functions.exact_enumeration(payload, expected)
                    selected.validate_enumeration(payload, contract)
                    self.assertEqual(qualified.enumeration, payload)
                    self.assertIs(self.contract(lane), contract)
                    # Observe the exact result-call receiver without replaying
                    # W2's existing result-validator fixture controls.
                    with patch.object(qualified, "validate_results", return_value={"SYNTHETIC_BINDING_PROBE": True}) as result_call:
                        self.assertEqual(self.binding.host_functions.host_validation_module(contract, {}).validate_results(
                            {"summary": "synthetic"}, {"tree": "synthetic"}, "synthetic-udid"),
                            {"SYNTHETIC_BINDING_PROBE": True})
                        result_call.assert_called_once_with({"summary": "synthetic"}, {"tree": "synthetic"}, "synthetic-udid")
                self.assertEqual(factory.call_count, 4)
        self.assertEqual(len({id(value) for value in instances}), 4)
        self.assertEqual(len(self.binding.instances), 4)

    def test_closed_command_barrier_blocks_all_witness_entry_points(self):
        lane = run.LANES[2]
        with patch.object(self.originals.witness, "verify_native_compiler_sources", self.witness):
            self.gate.is_open = False
            with self.assertRaisesRegex(ValueError, "unresolved"):
                self.contract(lane)
            self.assertEqual(self.witness_calls, [])
            self.gate.is_open = True
            contract = self.contract(lane)
            wrapper = self.binding.validators(lane)
            before = copy.deepcopy(self.witness_calls)
            self.gate.is_open = False
            calls = [lambda: self.contract(lane),
                lambda: self.binding.host_functions.invocation_selectors(contract["expected_compiled_identifiers"], contract),
                lambda: self.binding.host_functions.host_validation_module(contract, {}),
                lambda: wrapper.validate_enumeration(self.enumeration(contract["expected_compiled_identifiers"]), contract),
                lambda: wrapper.validate_results({}, {}, "synthetic-udid")]
            for call in calls:
                with self.assertRaisesRegex(ValueError, "unresolved"):
                    call()
            self.assertEqual(self.witness_calls, before)
            self.assertIsNone(wrapper.qualified.enumeration)
            self.binding.unchanged()  # Permitted file-only custody after closure.

    def test_closed_runtime_and_profile_bytes_refuse_before_external_work(self):
        with patch.object(admission, "bind_job", side_effect=AssertionError("No runtime job may be admitted")) as admission_call:
            with self.assertRaisesRegex(ValueError, "CLOSED"):
                run.run(None, None)
            admission_call.assert_not_called()
        path = self.source / profile_binding.W2_PREFIX / "profile.py"
        original_bytes = path.read_bytes()
        try:
            path.write_bytes(original_bytes + b"\n# synthetic mutation\n")
            with patch.object(self.originals.witness, "verify_native_compiler_sources", self.witness):
                with self.assertRaisesRegex(ValueError, "profile bytes changed"):
                    self.contract(run.LANES[0])
            self.assertEqual(self.witness_calls, [])
        finally:
            path.write_bytes(original_bytes)


if __name__ == "__main__":
    output = Path(os.environ["PINKHA_APP10_BINDING_CONTROL_OUTPUT"]).absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    files = sorted(path for path in Path(__file__).resolve().parent.iterdir() if path.is_file())
    before = {str(path): profile_binding.identity(path.read_bytes()) for path in files}
    started = time.time()
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PublishedW2BindingControls))
    raw_log = log.getvalue().encode()
    (output / "original.log").open("xb").write(raw_log)
    after = {str(path): profile_binding.identity(path.read_bytes()) for path in files}
    original_unchanged = all(profile_binding.identity(Path(path).read_bytes()) == expected for path, expected in INPUTS.items())
    passed = result.wasSuccessful() and result.testsRun == 3 and before == after and original_unchanged and not SPAWN_EVENTS
    receipt = {"schema": "pinkha-app10-published-profile-binding-portable-controls-v1",
        "status": "PASS_SYNTHETIC_BINDING_CONTROLS_ONLY" if passed else "FAIL",
        "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "durationSeconds": time.time() - started, "childSpawnEvents": SPAWN_EVENTS,
        "sourceBefore": before, "sourceAfter": after, "sourceUnchanged": before == after,
        "originalInputs": INPUTS, "originalInputsUnchanged": original_unchanged,
        "log": profile_binding.identity(raw_log), "W2FiveControlsReexecuted": False,
        "compiledWitness": "SYNTHETIC_SPY_ONLY", "actualAppleCalls": 0, "actualGitCalls": 0,
        "AppOrSwiftTestsExecuted": 0, "runtimeActivation": False,
        "reusedOriginalW2ControlReceiptSHA256": "44ac1700798ad580cf6c598b0019796ce77649c4876936ca5ffccd456f051c8d"}
    data = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    (output / "receipt.json").open("xb").write(data)
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"),
                      "sha256": sha(data), "methods": result.testsRun}, sort_keys=True))
    raise SystemExit(0 if passed else 1)
