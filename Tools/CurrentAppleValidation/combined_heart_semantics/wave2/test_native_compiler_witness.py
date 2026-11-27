"""Three source/proof boundary controls. No Swift/XCTest/simulator execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("selected_native_witness", HERE / "native_compiler_witness.py")
witness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(witness)
PROFILE = HERE / "rtl_hosted_profile.py"


def sha(value):
    return hashlib.sha256(value).hexdigest()


class SelectedCompilerWitnessControls(unittest.TestCase):
    def make_fixture(self, root):
        app = root / "source"
        app.mkdir()
        relative = "AnyTypeTests/Pinkha/SelectedWitness.swift"
        source = app / relative
        source.parent.mkdir(parents=True)
        source.write_text("// Synthetic control source, not an application test.\n")
        git = ["git", "-C", str(app)]
        subprocess.run(git + ["init", "--quiet"], check=True)
        subprocess.run(git + ["add", relative], check=True)
        subprocess.run(git + ["-c", "user.name=Control Fixture", "-c", "user.email=fixture@example.invalid",
                              "commit", "--quiet", "-m", "Synthetic compiler witness control"], check=True)
        commit = subprocess.check_output(git + ["rev-parse", "HEAD"]).decode().strip()
        original = root / "derived/AnytypeTests.build/AnytypeTests.SwiftFileList"
        original.parent.mkdir(parents=True)
        original.write_text(str(source) + "\n")
        retained = root / "retained.SwiftFileList"
        retained.write_bytes(original.read_bytes())
        line = "builtin-SwiftDriver -- /Xcode/usr/bin/swiftc -module-name AnytypeTests @" + str(original)
        log = root / "original.log"
        log.write_text(line + "\n")
        invocation = {"lineNumber": 1, "lineSHA256": sha(line.encode()), "moduleName": "AnytypeTests"}
        proof = {"schema": "pinkha-exact-native-compiler-inputs-v1",
                 "status": "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION",
                 "sourceCommit": commit, "testsExecuted": 0,
                 "requiredSources": [{"repositoryPath": relative, "compiledPath": str(source),
                    "sha256": sha(source.read_bytes()), "bytes": source.stat().st_size}],
                 "buildLog": {"path": str(log), "sha256": sha(log.read_bytes())},
                 "actualCompilerFileLists": [{"path": str(retained), "sha256": sha(retained.read_bytes()),
                    "originalPath": str(original), "compilerInvocation": invocation, "compilerInvocations": [invocation]}]}
        proof_path = root / "compiler-proof.json"
        proof_path.write_text(json.dumps(proof))
        args = dict(source_commit=commit, native_compilation_proof={"path": str(proof_path), "sha256": sha(proof_path.read_bytes())},
                    expected_sources={relative: sha(source.read_bytes())}, rtl_profile_path=PROFILE)
        return app, source, proof_path, proof, log, args

    def test_exact_source_and_original_witness_body_bind_selected_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, source, proof_path, proof, log, args = self.make_fixture(Path(temporary))
            result = witness.verify_native_compiler_sources(app, **args)
            self.assertEqual(result["source_hashes"], args["expected_sources"])
            self.assertEqual(len(result["actual_native_compiler_witnesses"]), 1)
            self.assertEqual(result["tests_executed"], 0)
            self.assertFalse(result["product_admission_performed"])
            self.assertFalse(result["application_execution_performed"])

    def test_wrong_compiler_module_cannot_receive_native_target_credit(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, source, proof_path, proof, log, args = self.make_fixture(Path(temporary))
            line = log.read_text().replace("-module-name AnytypeTests", "-module-name Anytype")
            log.write_text(line)
            proof["buildLog"]["sha256"] = sha(log.read_bytes())
            proof["actualCompilerFileLists"][0]["compilerInvocation"]["lineSHA256"] = sha(line.rstrip("\n").encode())
            proof_path.write_text(json.dumps(proof))
            args["native_compilation_proof"]["sha256"] = sha(proof_path.read_bytes())
            with self.assertRaisesRegex(ValueError, "Actual swiftc invocation"):
                witness.verify_native_compiler_sources(app, **args)

    def test_uncommitted_selected_source_and_changed_validator_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, source, proof_path, proof, log, args = self.make_fixture(Path(temporary))
            source.write_text("changed after admission\n")
            with self.assertRaisesRegex(ValueError, "exact clean commit"):
                witness.verify_native_compiler_sources(app, **args)
            altered = Path(temporary) / "changed_validator.py"
            altered.write_bytes(PROFILE.read_bytes() + b"\n# changed\n")
            args["rtl_profile_path"] = altered
            with self.assertRaisesRegex(ValueError, "Original reviewed witness validator changed"):
                witness.verify_native_compiler_sources(app, **args)


if __name__ == "__main__":
    unittest.main()
