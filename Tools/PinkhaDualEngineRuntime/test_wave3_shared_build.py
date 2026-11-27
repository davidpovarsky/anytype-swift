"""Admission/producer controls only. These do not run Apple product tests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess

MODULE = Path(__file__).with_name("wave3_shared_build.py")
spec = importlib.util.spec_from_file_location("wave3_shared_build", MODULE)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def frozen_example():
    result = json.loads(MODULE.with_name("wave3_build_admission.template.json").read_text())
    result.update(readyForBuild=True, appSourceSHA="1" * 40,
                  buildRoot="/Users/m1/development/anytype-d-active-20261125/main16-wave3-control-fixture")
    result["sourceStaging"]["sha256"] = "2" * 64
    result["cacheQualification"]["sha256"] = "3" * 64
    result["pins"]["sdkMaterializationReceiptSHA256"] = "4" * 64
    return result


class ProducerControls(unittest.TestCase):
    def test_adapter_preserves_original_functions_and_all_other_original_bytes(self):
        original_path = MODULE.with_name("build_wave2_app16_compiler_qualified.py")
        original = (original_path.read_text() if original_path.exists() else
                    subprocess.check_output(["git", "-C", str(MODULE.parent), "show",
                                             control.BASE_COMMIT + ":Tools/PinkhaDualEngineRuntime/build_wave2_app16_compiler_qualified.py"], text=True))
        candidate, proof = control.expand_controller(original, frozen_example(), Path("/admission.json"), "5" * 64, "6" * 64)
        self.assertTrue(proof["inverseRestoresEveryOriginalByte"])
        for name in ("run_phase", "source_state"):
            self.assertEqual(control.function_source(candidate, name), control.function_source(original, name))
        self.assertIn("w3_native_proof()", candidate)
        self.assertIn("w3_ui_after(ui_snapshot,ui_source,ui_project)", candidate)
        self.assertIn("**w3_final_bindings()", candidate)
        self.assertIn('"sourceUnchanged":True', candidate)
        self.assertIn('"products-all.json"', candidate)
        with self.assertRaises(ValueError):
            control.expand_controller(original.replace('p.wait(timeout=1)', 'p.wait(timeout=99)'),
                                      frozen_example(), Path("/admission.json"), "5" * 64, "6" * 64)

    def test_unapproved_or_wrong_source_admission_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "admission.json"
            data = frozen_example()
            path.write_text(json.dumps(data))
            self.assertEqual(control.load_admission(path, control.digest(path), "1" * 40)["appSourceSHA"], "1" * 40)
            with self.assertRaises(ValueError):
                control.load_admission(path, control.digest(path), "7" * 40)
            data["readyForBuild"] = False
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                control.load_admission(path, control.digest(path), "1" * 40)

    def setup_compile(self, root):
        source = root / "source/Test.swift"
        source.parent.mkdir()
        source.write_text("import XCTest\n")
        derived = root / "derived"
        filelist = derived / "Build/Intermediates.noindex/Fixture.build/AnytypeTests.build/Objects-normal/arm64/AnytypeTests.SwiftFileList"
        filelist.parent.mkdir(parents=True)
        filelist.write_text(str(source) + "\n")
        log = root / "original.log"
        line = "    builtin-SwiftDriver -- /Xcode/usr/bin/swiftc -module-name AnytypeTests @" + str(filelist)
        log.write_text(line + "\n")
        evidence = root / "evidence"
        evidence.mkdir()
        rows = [dict(repositoryPath="Test.swift", compiledPath=str(source), **control.w3_file(source))]
        return source, derived, filelist, log, line, evidence, rows

    def test_actual_compiler_command_and_exact_file_bytes_qualify(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, derived, filelist, log, line, evidence, rows = self.setup_compile(Path(temporary))
            result = control.w3_compiler_lists(derived, "AnytypeTests", rows, log, evidence, "native")
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["originalPath"], str(filelist))
            self.assertEqual(result[0]["sha256"], control.w3_sha(filelist))
            self.assertEqual(Path(result[0]["path"]).read_bytes(), filelist.read_bytes())
            self.assertEqual(result[0]["compilerInvocation"]["lineNumber"], 1)
            self.assertEqual(result[0]["compilerInvocation"]["lineSHA256"], hashlib.sha256(line.encode()).hexdigest())

    def test_stale_duplicate_missing_changed_or_wrong_module_inputs_are_rejected(self):
        for change in ("auxiliary-only", "wrong-module", "wrong-list", "duplicate-source", "missing-source", "changed-source"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                source, derived, filelist, log, line, evidence, rows = self.setup_compile(Path(temporary))
                if change == "auxiliary-only":
                    log.write_text("WriteAuxiliaryFile " + str(filelist) + "\n")
                elif change == "wrong-module":
                    log.write_text(line.replace("-module-name AnytypeTests", "-module-name Anytype") + "\n")
                elif change == "wrong-list":
                    log.write_text(line.replace("@" + str(filelist), "@/old/AnytypeTests.SwiftFileList") + "\n")
                elif change == "duplicate-source":
                    filelist.write_text((str(source) + "\n") * 2)
                elif change == "missing-source":
                    filelist.write_text("/elsewhere/Test.swift\n")
                elif change == "changed-source":
                    source.write_text("changed after source admission\n")
                with self.assertRaises(ValueError):
                    control.w3_compiler_lists(derived, "AnytypeTests", rows, log, evidence, "native")

    def test_generated_project_inventory_detects_scheme_bytes_and_mode_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "PinkhaPrebuiltUI.xcodeproj"
            scheme = project / "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"
            scheme.parent.mkdir(parents=True)
            (project / "project.pbxproj").write_text("// original generated project\n")
            scheme.write_text("<Scheme/>\n")
            original = control.w3_project_inventory(project)
            scheme.write_text("<ChangedScheme/>\n")
            self.assertNotEqual(original, control.w3_project_inventory(project))
            scheme.write_text("<Scheme/>\n")
            scheme.chmod(0o600)
            self.assertNotEqual(original, control.w3_project_inventory(project))


if __name__ == "__main__":
    unittest.main()
