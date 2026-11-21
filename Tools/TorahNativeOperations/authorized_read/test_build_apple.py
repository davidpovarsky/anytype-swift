#!/usr/bin/env python3
"""New candidate admission controls. No native or prior Swift tests execute."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_apple as candidate


class CandidateAppleControls(unittest.TestCase):
    def testOriginalNativeCompletionBindsExactCandidate(self):
        source = candidate.qualified_generation(candidate.ROOT)
        candidate.require_same_candidate(source, source)
        self.assertEqual(candidate.account.candidate_identity(source), candidate.CANDIDATE)

    def testAnyChangedGeneratedBindingIsRejected(self):
        source = candidate.qualified_generation(candidate.ROOT)
        changed = copy.deepcopy(source)
        name = next(iter(changed["generated_sha256"]))
        changed["generated_sha256"][name] = "0" * 64
        with self.assertRaisesRegex(ValueError, "qualified input"):
            candidate.require_same_candidate(changed, source)

    def testProductionOrModuleDriftCannotReuseNativePasses(self):
        source = candidate.qualified_generation(candidate.ROOT)
        for key in ["source_sha256", "module_sha256", "protobuf_inputs_sha256"]:
            changed = copy.deepcopy(source)
            name = next(iter(changed[key])); changed[key][name] = "0" * 64
            with self.assertRaisesRegex(ValueError, "qualified input"):
                candidate.require_same_candidate(changed, source)

    def testOriginalReceiptTamperIsRejectedBeforeBuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proof = root / candidate.PROOF
            proof.mkdir(parents=True)
            original = candidate.ROOT / candidate.PROOF
            document = json.loads((original / "evidence.json").read_bytes())
            document["run_id"] = 1
            (proof / "evidence.json").write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "qualified native proof"):
                candidate.qualified_generation(root)

    def testSimulatorSliceMustBeExactAndCannotClaimDeviceBuild(self):
        info, slices = self.framework()
        candidate.validate_simulator_framework(info, slices)
        for key, value in [("SupportedPlatformVariant", ""), ("SupportedArchitectures", ["x86_64"]),
                           ("LibraryIdentifier", "ios-arm64")]:
            changed = copy.deepcopy(info); changed["AvailableLibraries"][0][key] = value
            with self.assertRaisesRegex(ValueError, "destination"):
                candidate.validate_simulator_framework(changed, slices)

    def testWrongRuntimeMarkerCannotBeRelabelled(self):
        info, slices = self.framework()
        slices[0]["marker"] = "r15-attachment-v1"
        with self.assertRaisesRegex(ValueError, "identity"):
            candidate.validate_simulator_framework(info, slices)

    def testMissingActualGeneratedScopeCannotQualify(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Exactly one"):
                candidate.validate_generated_scopes({"audit": Path(temporary)}, Path(temporary))

    def testUnknownCompilerProfileRejectsBeforeNativeMutation(self):
        arguments = type("Args", (), {"control": Path("control"), "heart_source": Path("heart"),
                    "work": Path("work"), "evidence": Path("proof"), "rpc_profile": "retained-v1"})()
        with patch.object(candidate.rpc, "source_inputs", return_value=({"generation": {"protoc": {}}}, {})), \
             patch.object(candidate.rpc.registry, "apply_sources") as mutation:
            with self.assertRaisesRegex(ValueError, "compiler profile"):
                candidate.rpc.generate(arguments, {}, lambda *args: None, protoc_profile="unreviewed")
            mutation.assert_not_called()

    @staticmethod
    def framework():
        return ({"AvailableLibraries": [{"LibraryIdentifier": "ios-arm64-simulator", "LibraryPath": "Lib.framework",
                    "SupportedPlatform": "ios", "SupportedPlatformVariant": "simulator", "SupportedArchitectures": ["arm64"]}]},
                [{"path": "ios-arm64-simulator/Lib.framework/Lib", "architecture": "arm64",
                    "marker": candidate.VERSION, "sha256": "a" * 64}])


if __name__ == "__main__": unittest.main()
