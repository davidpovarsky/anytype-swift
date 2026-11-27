"""Finite synthetic source/evidence boundaries; never Apple/runtime acceptance."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
SPAWN_EVENTS = []


def forbid_children(event, args):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork"}:
        SPAWN_EVENTS.append(event)
        raise AssertionError("Portable control may not launch any child command")


sys.addaudithook(forbid_children)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    sys.modules[name] = result
    specification.loader.exec_module(result)
    return result


class FixedProfileControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="delta10-controls-", dir=ROOT)
        cls.root = Path(cls.temporary.name)
        cls.source = cls.root / "source"
        cls.source.mkdir()
        originals = WORK / "wave2-product-admission-delta/profile-feasibility/originals"
        pins = json.loads((originals / "original_sources.json").read_text())["files"]
        locators = json.loads((ROOT / "original-fixture-locators.json").read_text())
        cls.original_physical_before = {}
        for relative, pin in pins.items():
            original_path = WORK / locators[relative]
            raw = original_path.read_bytes()
            assert len(raw) == pin["bytes"] and sha(raw) == pin["sha256"]
            cls.original_physical_before[original_path] = sha(raw)
            destination = cls.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        cls.swift = {
            "g05": "torah-acceptance-prep/g05-cache-review/candidate/AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift",
            "g07": "wave2-quote-audit/patch/AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift",
            "bin": "interfaces_work/bin-read-failure/candidate/Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift",
        }
        cls.profile_spec = json.loads((ROOT / "profile/profile.json").read_text())
        for key, relative in cls.swift.items():
            raw = (WORK / relative).read_bytes()
            specification = cls.profile_spec["sources"][key]
            assert sha(raw) == specification["sha256"]
            destination = cls.source / specification["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        control = cls.root / "original-control"
        control.mkdir()
        for name in ("originals.py", "original_sources.json"):
            shutil.copyfile(originals / name, control / name)
        original_module = module("delta10_exact_core22_loader", control / "originals.py")
        cls.originals = original_module.Originals(cls.source)
        cls.originals.install()
        cls.profile_root = cls.root / "profile"
        shutil.copytree(ROOT / "profile", cls.profile_root)
        cls.profile = module("delta10_closed_profile_under_test", cls.profile_root / "profile.py")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.originals.unchanged()
            assert all(sha(path.read_bytes()) == value for path, value in cls.original_physical_before.items())
        finally:
            cls.originals.close()
            cls.temporary.cleanup()

    def test_exact_full_sources_preserve_old_scopes_and_select_only_new_ten(self):
        contracts = [self.profile.declared_contract(self.originals, lane) for lane in self.profile.LANES]
        self.assertEqual(sum(value["expected_methods"] for value in contracts), 10)
        self.assertEqual(sum(value["declared_cases"] for value in contracts), 18)
        self.assertEqual([value["complete_declarations"] for value in contracts], [15, 15, 35, 4])
        self.assertEqual([value["original_target"] for value in contracts],
                         ["AnytypeTests", "AnytypeTests", "AnytypeTests", "PinkhaAnyUITests"])
        self.assertEqual([len(value["source_inverse"]) for value in contracts], [2, 2, 1, 1])
        for value in contracts:
            self.assertIsNone(value["native_compilation_proof"])
            self.assertIsNone(value["actual_compiled_enumeration"])
            self.assertFalse(value["runtime_admission_performed"])
            self.assertEqual(value["tests_executed"], 0)
        g07 = contracts[2]
        self.assertEqual(g07["declaration_projection"]["removedAnnotations"], 2)
        self.assertEqual(g07["declaration_projection"]["declarationViewSHA256"],
                         "8becc019bda1bfa9aba80c8040d33df3230a36d1679968d2f01ccb6374ac1473")
        plan = self.profile.selection_plan(self.originals, self.profile.LANES[2])
        self.assertEqual(plan["proposed_invocation_selectors"], g07["expected_compiled_identifiers"])
        self.assertEqual(len(plan["proposed_invocation_selectors"]), 2)
        self.assertTrue(all(value.count("/") == 2 and value.endswith("()") for value in plan["proposed_invocation_selectors"]))
        self.assertFalse(plan["execution_authorized"])
        self.assertEqual(self.profile_spec["affectedOldG05"]["methods"], 3)
        self.assertEqual(self.profile_spec["affectedOldG05"]["newMethodCredit"], 0)

    def test_old_prefix_tamper_is_rejected_even_when_new_methods_are_unchanged(self):
        for key, lane in (("g05", self.profile.LANES[0]), ("g07", self.profile.LANES[2]), ("bin", self.profile.LANES[3])):
            with self.subTest(source=key):
                path = self.source / self.profile_spec["sources"][key]["path"]
                raw = path.read_bytes()
                try:
                    path.write_bytes(b"X" + raw[1:])
                    with self.assertRaisesRegex(ValueError, "Full published test input changed"):
                        self.profile.declared_contract(self.originals, lane)
                finally:
                    path.write_bytes(raw)

    def test_inverse_and_original_validator_custody_cannot_be_bypassed(self):
        inverse = self.profile_root / "source-inverse.json"
        raw = inverse.read_bytes()
        try:
            inverse.write_bytes(raw + b" ")
            with self.assertRaisesRegex(ValueError, "finite source inverses changed"):
                self.profile.declared_contract(self.originals, self.profile.LANES[0])
        finally:
            inverse.write_bytes(raw)
        helper = self.source / "Tools/Hanlin/wave15_core_profile.py"
        raw = helper.read_bytes()
        try:
            helper.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(ValueError, "original control source changed|Original control source changed"):
                self.profile.declared_contract(self.originals, self.profile.LANES[0])
        finally:
            helper.write_bytes(raw)

    def test_runtime_flags_unknown_lanes_and_declarations_cannot_authorize_compilation(self):
        for value in ({"runtimeReady": True}, {"sourceCompilerProof": {"status": "PASS"}}, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "runtime CLOSED"):
                    self.profile.require_runtime_ready(value)
        with self.assertRaisesRegex(ValueError, "four fixed"):
            self.profile.fixed_contract("TorahAssociationNativeRepositoryTests")
        declaration = self.profile.declared_contract(self.originals, self.profile.LANES[0])
        with self.assertRaisesRegex(ValueError, "declaration evidence is insufficient"):
            self.profile.validators(self.originals, self.profile.LANES[0],
                                    source_commit=declaration["source_commit"], native_compilation_proof=declaration["native_compilation_proof"])
        with self.assertRaisesRegex(ValueError, "validator instance"):
            self.profile.invocation_selectors(declaration["expected_compiled_identifiers"], declaration)
        self.assertEqual(SPAWN_EVENTS, [])

    def test_parameterized_evidence_requires_all_actual_cases_not_summary_counts(self):
        lane = self.profile.LANES[0]
        specification = self.profile_spec["lanes"][lane]
        suite = specification["suite"]
        nodes = []
        for name, definition in specification["methods"].items():
            identifier = "AnytypeTests/" + suite + "/" + name + "(" + "".join(p["name"] + ":" for p in definition["parameters"]) + ")"
            node = {"nodeType": "Test Case", "nodeIdentifier": identifier, "result": "Passed", "children": []}
            if definition["case_count"] > 1:
                node["children"] = [{"nodeType": "Arguments", "name": json.dumps(value), "result": "Passed"}
                                    for value in definition["argument_collections"][0]]
            nodes.append(node)
        tree = {"syntheticPortableFixture": True, "testNodes": nodes}
        udid = "SYNTHETIC-PORTABLE-NOT-A-DEVICE"
        summary = {"totalTestCount": 3, "passedTests": 3, "failedTests": 0, "skippedTests": 0,
                   "devicesAndConfigurations": [{"device": {"deviceId": udid, "osVersion": "27.0",
                       "osBuildNumber": "SYNTHETIC", "architecture": "arm64", "modelName": "iPad synthetic"}}]}
        observed = self.profile._result_evidence(self.originals, lane, summary, tree, udid)
        self.assertEqual((observed["actual_method_count"], observed["declared_case_count"]), (3, 7))
        for mutation in ("missing", "duplicate", "old-extra", "wrong-count"):
            with self.subTest(mutation=mutation):
                current, aggregate = copy.deepcopy(tree), copy.deepcopy(summary)
                parameterized = next(value for value in current["testNodes"] if len(value["children"]) > 1)
                if mutation == "missing":
                    parameterized["children"].pop()
                elif mutation == "duplicate":
                    parameterized["children"][1]["name"] = parameterized["children"][0]["name"]
                elif mutation == "old-extra":
                    current["testNodes"].append({"nodeType": "Test Case", "nodeIdentifier": "PropertyCreationSearchTests/preCancelledCatalogDoesNotSearch()", "result": "Passed"})
                else:
                    aggregate["totalTestCount"] = aggregate["passedTests"] = 18
                with self.assertRaises(ValueError):
                    self.profile._result_evidence(self.originals, lane, aggregate, current, udid)


if __name__ == "__main__":
    output = ROOT / "controls-attempt1"
    output.mkdir(mode=0o700)
    started = time.monotonic()
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixedProfileControls))
    raw = log.getvalue().encode()
    (output / "original.log").write_bytes(raw)
    receipt = {"schema": "pinkha-app-product-delta10-portable-controls-v1",
               "status": "PASS_SYNTHETIC_CONTROLS_NOT_RUNTIME" if result.wasSuccessful() and not SPAWN_EVENTS else "FAIL",
               "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "durationSeconds": time.monotonic() - started, "logSHA256": sha(raw),
               "profileSHA256": sha((ROOT / "profile/profile.py").read_bytes()),
               "manifestSHA256": sha((ROOT / "profile/profile.json").read_bytes()),
               "inverseSHA256": sha((ROOT / "profile/source-inverse.json").read_bytes()),
               "controlSHA256": sha(Path(__file__).read_bytes()), "childSpawnEvents": SPAWN_EVENTS,
               "AppleOrSwiftOrNativeCalls": 0, "sourceCompilerProof": None, "actualCompiledEnumeration": None,
               "runtimeAdmission": None, "runtimeReady": False, "syntheticEvidenceOnly": True}
    (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(log.getvalue(), end="")
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(0 if receipt["status"].startswith("PASS") else 1)
