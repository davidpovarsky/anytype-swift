"""Four new Page154 fixed-pair policy controls; no simulator or old suite runs."""
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import consumer_simulator as policy


EVIDENCE = ROOT / "docs/validation/20261123-page154-known-simulator"


class Page154KnownSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.runtimes = json.loads((EVIDENCE / "original-page-available-runtimes.log").read_text())
        self.devices = json.loads((EVIDENCE / "original-page-available-device-types.log").read_text())

    def runtime(self):
        return next(item for item in self.runtimes["runtimes"] if item["identifier"] == policy.RUNTIME_ID)

    def device(self):
        return next(item for item in self.devices["devicetypes"] if item["identifier"] == policy.DEVICE_ID)

    def test_original_inventory_selects_exact_observed_pair_without_mutating_or_reusing_uuid(self):
        original = copy.deepcopy((self.runtimes, self.devices))
        pair = policy.choose_pair(self.runtimes, self.devices)
        self.assertEqual(pair["runtime"]["identifier"], policy.RUNTIME_ID)
        self.assertEqual(pair["runtime"]["buildversion"], "24A434")
        self.assertEqual(pair["device"]["identifier"], policy.DEVICE_ID)
        self.assertEqual(pair["device"]["modelIdentifier"], "iPad17,4")
        self.assertEqual(pair["selection"]["architecture"], "arm64")
        self.assertEqual(pair["selection"]["selectionPolicy"], policy.POLICY)
        self.assertEqual(pair["selection"]["observedPairProvenance"]["originalLaneConclusion"], "FAIL")
        self.assertEqual(pair["selection"]["observedPairProvenance"]["originalSimulatorUDID"],
                         "6BA9F042-CEB5-49CF-9301-D8395698D8A5")
        self.assertNotIn("udid", pair)
        self.assertEqual((self.runtimes, self.devices), original)
        pair["selection"]["observedPairProvenance"]["runID"] = "changed returned copy"
        self.assertEqual(policy.ORIGIN["runID"], "45096079315")

    def test_missing_changed_unavailable_or_wrong_architecture_runtime_never_falls_back(self):
        cases = (
            ("missing", lambda: self.runtimes["runtimes"].remove(self.runtime())),
            ("version", lambda: self.runtime().update(version="27.1")),
            ("build", lambda: self.runtime().update(buildversion="24A434-unreviewed")),
            ("architecture", lambda: self.runtime().update(supportedArchitectures=["x86_64"])),
            ("unavailable", lambda: self.runtime().update(isAvailable=False)),
            ("internal", lambda: self.runtime().update(isInternal=True)),
            ("duplicate", lambda: self.runtimes["runtimes"].append(copy.deepcopy(self.runtime()))),
        )
        for label, mutate in cases:
            with self.subTest(case=label):
                self.setUp()
                mutate()
                self.assertTrue(any(item["version"] == "27.2" and item["isAvailable"]
                                    for item in self.runtimes["runtimes"]))
                with self.assertRaises(ValueError):
                    policy.choose_pair(self.runtimes, self.devices)

    def test_type_identity_support_matrix_and_both_runtime_bounds_are_required(self):
        def remove_support():
            self.runtime()["supportedDeviceTypes"] = [
                item for item in self.runtime()["supportedDeviceTypes"]
                if item["identifier"] != policy.DEVICE_ID]
        def duplicate_support():
            entry = next(item for item in self.runtime()["supportedDeviceTypes"]
                         if item["identifier"] == policy.DEVICE_ID)
            self.runtime()["supportedDeviceTypes"].append(copy.deepcopy(entry))
        cases = (
            ("missing", lambda: self.devices["devicetypes"].remove(self.device())),
            ("model", lambda: self.device().update(modelIdentifier="unreviewed")),
            ("family", lambda: self.device().update(productFamily="iPhone")),
            ("support", remove_support),
            ("duplicate-support", duplicate_support),
            ("minimum", lambda: self.device().update(minRuntimeVersion=(27 << 16) | (1 << 8),
                                                    minRuntimeVersionString="27.1.0")),
            ("maximum", lambda: self.device().update(maxRuntimeVersion=26 << 16,
                                                    maxRuntimeVersionString="26.0.0")),
            ("numeric-text-conflict", lambda: self.device().update(minRuntimeVersionString="25.0.0")),
            ("duplicate-type", lambda: self.devices["devicetypes"].append(copy.deepcopy(self.device()))),
        )
        for label, mutate in cases:
            with self.subTest(case=label):
                self.setUp()
                mutate()
                with self.assertRaises(ValueError):
                    policy.choose_pair(self.runtimes, self.devices)

    def test_real_consumer_region_uses_fresh_created_uuid_and_original_boot_deadline(self):
        path = Path(__file__).with_name("run.py")
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute")
        # The owned try contains the actual inventory/selection/create/boot region.
        owner = next(node for node in function.body if isinstance(node, ast.Try)
                     and any(isinstance(child, ast.Assign)
                             and any(isinstance(target, ast.Name) and target.id == "runtimes"
                                     for target in child.targets) for child in node.body))
        start = next(i for i, node in enumerate(owner.body) if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "runtimes" for target in node.targets))
        end = next(i for i in range(start, len(owner.body))
                   if isinstance(owner.body[i], ast.Expr)
                   and isinstance(owner.body[i].value, ast.Call)
                   and any(isinstance(node, ast.Constant) and node.value == "wait-owned-simulator"
                           for node in ast.walk(owner.body[i])))
        region = ast.Module(body=owner.body[start:end + 1], type_ignores=[])
        fresh = "11111111-2222-4333-8444-555555555555"
        nonce = "a" * 32
        queries, commands = [], []
        with tempfile.TemporaryDirectory() as temporary:
            stdout = Path(temporary) / "created-uuid.log"
            stdout.write_text(fresh + "\n")
            def query(command, label, timeout):
                queries.append((command, label, timeout))
                return copy.deepcopy(self.runtimes if label == "available-runtimes" else self.devices)
            def run(command, label, timeout):
                commands.append((command, label, timeout))
                return stdout, {"return_code": 0}
            def require(condition, reason):
                if not condition:
                    raise AssertionError(reason)
            receipt = {}
            context = {"runner": SimpleNamespace(json=query, run=run), "consumer_simulator": policy,
                       "run_binding": {"nonce": nonce}, "receipt": receipt,
                       "proof": SimpleNamespace(require=require),
                       "owned": SimpleNamespace(valid_udid=lambda value: value == fresh)}
            exec(compile(region, str(path), "exec"), context)
        self.assertEqual([item[2] for item in queries], [30, 30])
        self.assertEqual(commands, [
            (["xcrun", "simctl", "create", "Page154Consumer-" + nonce,
              policy.DEVICE_ID, policy.RUNTIME_ID], "create-owned-simulator", 60),
            (["xcrun", "simctl", "boot", fresh], "boot-owned-simulator", 90),
            (["xcrun", "simctl", "bootstatus", fresh, "-b"], "wait-owned-simulator", 180),
        ])
        self.assertEqual(receipt["owned_simulator"]["udid"], fresh)
        self.assertNotEqual(fresh, policy.ORIGIN["originalSimulatorUDID"])
        self.assertEqual(receipt["owned_simulator"]["selection"]["selectionPolicy"], policy.POLICY)


if __name__ == "__main__":
    unittest.main()
