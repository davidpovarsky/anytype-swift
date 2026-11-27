"""Fixture-only controls for the new receipt gate; no Apple/native acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest import mock

import receipt_admission as gate
from run_receipt_acceptance import verify_test_result

ORIGINAL_GIT_SOURCE = gate.git_source


class ReceiptAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="miniapps-receipt-controls-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.commit, self.tree = "a" * 40, "b" * 40
        self.source = self.root / "source"; self.source.mkdir()
        self.source_files = {}
        source_names = gate.REQUIRED_PRODUCT_SOURCES | gate.REQUIRED_PIN_SOURCES | {
            "PinkhaStage1Acceptance/Tests/SecondOriginalFixture.swift",
            "PinkhaStage1Acceptance/README.md",
            "AnyTypeTests/Pinkha/SecondOriginalNativeFixture.swift",
        }
        for name in source_names:
            path = self.source / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original committed source fixture: " + name)
            self.source_files[name] = {"bytes": path.stat().st_size, "sha256": gate.sha256(path)}
        observation = {"commit": self.commit, "tree": self.tree, "status": "",
                       "files": {name: row for name, row in self.source_files.items() if name.endswith(".swift")}}
        self.git_observed = {"commit": self.commit, "tree": self.tree, "status": "",
                            "files": {name: row for name, row in self.source_files.items()
                                      if name in gate.REQUIRED_PIN_SOURCES or name.startswith("PinkhaStage1Acceptance/")}}
        patch = mock.patch.object(gate, "git_source", return_value=self.git_observed)
        patch.start()
        self.addCleanup(patch.stop)
        before = self.save("source-before.json", observation); after = self.save("source-after.json", observation)
        self.control = self.root / "controls"; self.control.mkdir()
        control_files = {}
        for name in gate.REQUIRED_CONTROLS:
            path = self.control / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# original fixture control\n")
            control_files[name] = {"bytes": path.stat().st_size, "sha256": gate.sha256(path)}
        controls = self.save("controls.json", {"commit": self.commit, "files": control_files})
        self.inputs = {}
        for name in gate.REQUIRED_INPUTS | {"stagingReceiptSHA256", "cacheRequalificationReceiptSHA256"}:
            path = self.root / (name + ".input"); path.write_bytes(name.encode())
            self.inputs[name] = gate.make_ref(path)
        producer_path = self.root / "producer.py"; producer_path.write_text("# exact fixture producer\n")
        generator_path = self.root / "ui-generator.py"; generator_path.write_text("# exact fixture generator\n")
        assembly = self.save("assembly.json", {
            "status": "PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE",
            "sourceManifestSHA256": self.inputs["nativeSourceManifestSHA256"]["sha256"],
            "runtimeIdentity": {
                "sourceManifestSHA256": self.inputs["nativeSourceManifestSHA256"]["sha256"],
                "sourcePins": {name: "exact-fixture-pin" for name in ("any", "heart", "sdk", "sync")}},
        })
        ui_root = self.root / "ui-copy"; ui_root.mkdir()
        copied_rows = []
        for name, original in sorted(self.source_files.items()):
            if name.startswith("PinkhaStage1Acceptance/"):
                path = ui_root / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((self.source / name).read_bytes())
                copied_rows.append({"path": name, "sha256": original["sha256"]})
        self.project = ui_root / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
        scheme = self.project / "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"
        scheme.parent.mkdir(parents=True)
        scheme.write_text("<Scheme fixture='true'/>")
        (self.project / "project.pbxproj").write_text("original generated project fixture")
        entries = {}
        for name in ("xcshareddata", "xcshareddata/xcschemes"):
            path = self.project / name
            entries[name] = {"kind": "directory", "mode": path.stat().st_mode & 0o7777}
        for name in ("project.pbxproj", "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"):
            path = self.project / name
            entries[name] = {"kind": "file", "mode": path.stat().st_mode & 0o7777,
                             "bytes": path.stat().st_size, "sha256": gate.sha256(path)}
        project_inventory = {"schema": "pinkha-generated-ui-project-inventory-v1",
                             "root": str(self.project), "entries": entries}
        project_before = self.save("project-before.json", project_inventory)
        project_after = self.save("project-after.json", project_inventory)
        self.copy = {"generatorSHA256": gate.sha256(generator_path), "copiedFiles": copied_rows,
                     "generatedProject": str(self.project)}
        copied = self.save("original-ui-copy.json", self.copy)
        self.steps, self.logs, self.proofs = {}, {}, {}
        proof_refs = {}
        for label, step, prefix, compiled_root, module, status in (
            ("native", "app", "AnyTypeTests/", self.source, "AnytypeTests",
             "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION"),
            ("ui", "ui", "PinkhaStage1Acceptance/", ui_root, "PinkhaStage1AcceptanceUITests",
             "PASS_EXACT_UI_COPY_PROJECT_AND_COMPILER_INPUTS_NOT_TEST_EXECUTION"),
        ):
            rows = [{"repositoryPath": name, "compiledPath": str(compiled_root / name), **original}
                    for name, original in sorted(self.source_files.items())
                    if name.startswith(prefix) and name.endswith(".swift")]
            retained = self.root / (label + "-retained.SwiftFileList")
            retained.write_text("".join(row["compiledPath"] + "\n" for row in rows))
            original_path = str(self.root / ("derived/" + module + ".SwiftFileList"))
            line = "/usr/bin/builtin-SwiftDriver -- /fixture/swiftc -module-name " + module + " @" + original_path
            log = self.root / (step + ".log"); log.write_text(line + "\n** TEST BUILD SUCCEEDED **\n")
            self.logs[step] = gate.make_ref(log)
            self.steps[step] = {"sourceCommit": self.commit, "exitCode": 0, "status": "PASS_COMMAND",
                                "cleanupErrors": [], "argv": ["xcodebuild", "build-for-testing"],
                                "logSHA256": gate.sha256(log), "logBytes": log.stat().st_size}
            if label == "ui":
                self.steps[step]["argv"] += ["-project", str(self.project)]
            proof = {
                "schema": "pinkha-exact-" + label + "-compiler-inputs-v1", "status": status,
                "sourceCommit": self.commit, "requiredSources": rows, "buildLog": self.logs[step], "testsExecuted": 0,
                "actualCompilerFileLists": [{
                    **gate.make_ref(retained), "originalPath": original_path,
                    "requiredSourcePaths": [row["compiledPath"] for row in rows],
                    "compilerInvocation": {"lineNumber": 1, "lineSHA256": hashlib.sha256(line.encode()).hexdigest(),
                                           "moduleName": module}}],
            }
            if label == "ui":
                proof.update(originalUICopySHA256=copied["sha256"], generatorSHA256=gate.sha256(generator_path),
                             generatedProjectBefore=project_before, generatedProjectAfter=project_after)
            self.proofs[label] = proof
            proof_refs[label + "CompilationProof"] = self.save(label + "-compiler-inputs.json", proof)
        self.products = {}
        for slot in ("app-derived", "ui-derived"):
            root = self.root / slot; root.mkdir()
            (root / "original.xctestrun").write_bytes(b"descriptor fixture")
            (root / "original-product.bin").write_bytes(b"original binary fixture")
            self.products[slot] = {"base": str(root), "entries": gate.inventory(root)}
        products = self.save("products-all.json", self.products)
        retention = self.save("original-retention.json", {"fixture": "original retained products"})
        root_admission = self.save("root-admission.json", {
            "schema": "pinkha-root-frozen-build-admission-v1", "readyForBuild": True,
            "appSourceSHA": self.commit, "sourceRoot": str(self.source), "originalRetention": retention,
            "pins": {
                "nativeSourceManifestSHA256": self.inputs["nativeSourceManifestSHA256"]["sha256"],
                "packageResolvedSHA256": self.inputs["lockSHA256"]["sha256"],
                "sdkMaterializationReceiptSHA256": self.inputs["sdkReceiptSHA256"]["sha256"],
                "nativeSimulatorBinarySHA256": self.inputs["nativeSHA256"]["sha256"],
                "nativeAssemblyReceiptSHA256": assembly["sha256"],
                "uiGeneratorSHA256": gate.sha256(generator_path),
            },
            "sourceStaging": self.inputs["stagingReceiptSHA256"],
            "cacheQualification": self.inputs["cacheRequalificationReceiptSHA256"],
            "selectedNativeTestSources": [row["repositoryPath"] for row in self.proofs["native"]["requiredSources"]],
            "selectedUITestSources": [row["repositoryPath"] for row in self.proofs["ui"]["requiredSources"]],
        })
        self.build = {
            "status": gate.BUILD_STATUS, "sourceCommit": self.commit, "sourceUnchanged": True, "testsExecuted": 0,
            "sourceBeforeSHA256": before["sha256"], "sourceAfterSHA256": after["sha256"],
            "controlAdmission": {
                "schema": "pinkha-root-build-control-binding-v1", "appSourceSHA": self.commit,
                "admission": root_admission, "originalRetention": retention,
                "originalProducerCommit": "204f8fbb25c3b21f419fc1a8818eb46ed492e561",
                "originalProducerSHA256": "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c",
            },
            "inputs": {name: ref["sha256"] for name, ref in self.inputs.items()}, **self.steps,
            "controllerSHA256": gate.sha256(producer_path), "assemblyReceiptSHA256": assembly["sha256"],
            "originalUICopySHA256": copied["sha256"], **proof_refs,
            "completeProductsInventory": {**products, "entries": sum(len(x["entries"]) for x in self.products.values())},
        }
        build = self.save("receipt.json", self.build)
        dependency_path = self.root / "dependency.json"; dependency_path.write_text('{"fixture":true}\n')
        tools = []
        for index, argv in enumerate((["xcodebuild", "-version"], ["xcrun", "swift", "--version"],
                                      ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version"])):
            path = self.root / ("toolchain-" + str(index)); path.write_text("original observed fixture")
            tools.append({"argv": argv, "original": gate.make_ref(path)})
        self.contract = {
            "schema": gate.SCHEMA,
            "source": {"root": str(self.source), "commit": self.commit, "tree": self.tree,
                       "before": before, "after": after},
            "controls": {"root": str(self.control), "commit": self.commit, "manifest": controls},
            "build": {"receipt": build, "products": products, "inputs": self.inputs, "logs": self.logs,
                      "producer": gate.make_ref(producer_path), "assembly": assembly,
                      "originalUICopy": copied, "uiGenerator": gate.make_ref(generator_path), **proof_refs},
            "descriptors": {kind: {"slot": kind + "-derived", "path": "original.xctestrun"} for kind in ("app", "ui")},
            "dependencyEvidence": {name: [gate.make_ref(dependency_path)] for name in
                                   ("Hanlin", "Heart", "Any", "TorahInspectorKit")},
            "runtime": {"family": "ipad", "architecture": "arm64", "version": "27.0"},
            "toolchain": tools,
        }

    def refresh_build(self):
        self.contract["build"]["receipt"] = self.save("receipt.json", self.build)

    def refresh_proof(self, label):
        reference = self.save(label + "-compiler-inputs.json", self.proofs[label])
        self.contract["build"][label + "CompilationProof"] = reference
        self.build[label + "CompilationProof"] = reference
        self.refresh_build()

    def save(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, sort_keys=True))
        return gate.make_ref(path)

    def admit(self):
        reference = self.save("contract.json", self.contract)
        return gate.admit(reference["path"], reference["sha256"])

    def test_matching_original_source_inputs_and_products_admit_without_claiming_tests(self):
        _, proof, _ = self.admit()
        self.assertEqual(proof["status"], "ADMITTED_ORIGINAL_BUILD_NOT_APPLICATION_ACCEPTANCE")
        self.assertEqual(proof["testMethodsExecuted"], 0)
        self.assertEqual(len(proof["methods"]), 8)

    def test_source_mutation_rejected(self):
        path = self.source / next(iter(gate.REQUIRED_PRODUCT_SOURCES))
        path.write_text("changed")
        with self.assertRaises(ValueError): self.admit()

    def test_extra_unrecorded_product_rejected(self):
        (self.root / "app-derived/unrecorded.bin").write_bytes(b"extra")
        with self.assertRaises(ValueError): self.admit()

    def test_product_symlink_escape_rejected(self):
        outside = self.root / "outside"; outside.write_text("outside")
        (self.root / "app-derived/alias").symlink_to(outside)
        with self.assertRaises(ValueError): self.admit()

    def test_duplicate_product_inventory_rejected(self):
        rows = self.products["app-derived"]["entries"]; rows.append(copy.deepcopy(rows[0]))
        self.contract["build"]["products"] = self.save("products-all.json", self.products)
        with self.assertRaises(ValueError): self.admit()

    def test_old_source_build_cannot_be_relabelled(self):
        self.build["sourceCommit"] = "c" * 40
        self.contract["build"]["receipt"] = self.save("receipt.json", self.build)
        with self.assertRaises(ValueError): self.admit()

    def test_ui_command_from_another_commit_rejected(self):
        self.build["ui"]["sourceCommit"] = "c" * 40
        self.contract["build"]["receipt"] = self.save("receipt.json", self.build)
        with self.assertRaises(ValueError): self.admit()

    def test_unbound_original_sdk_input_rejected(self):
        del self.contract["build"]["inputs"]["sdkReceiptSHA256"]
        with self.assertRaises(ValueError): self.admit()

    def test_zero_exit_without_original_successful_build_output_rejected(self):
        path = self.root / "app.log"; path.write_text("** BUILD FAILED **\n")
        self.build["app"].update(logSHA256=gate.sha256(path), logBytes=path.stat().st_size)
        self.contract["build"]["logs"]["app"] = gate.make_ref(path)
        self.contract["build"]["receipt"] = self.save("receipt.json", self.build)
        with self.assertRaises(ValueError): self.admit()

    def test_before_after_source_disagreement_rejected(self):
        after = json.loads(Path(self.contract["source"]["after"]["path"]).read_bytes())
        after["status"] = "source changed"
        self.contract["source"]["after"] = self.save("source-after.json", after)
        with self.assertRaises(ValueError): self.admit()

    def test_unbound_transitive_helper_rejected(self):
        (self.control / "Tools/unbound.py").write_text("raise RuntimeError('foreign helper')")
        with self.assertRaises(ValueError): self.admit()

    def test_missing_original_toolchain_observation_rejected(self):
        self.contract["toolchain"].pop()
        with self.assertRaises(ValueError): self.admit()

    def test_missing_any_engine_evidence_rejected(self):
        del self.contract["dependencyEvidence"]["Any"]
        with self.assertRaises(ValueError): self.admit()

    def test_historical_app15_success_status_rejected(self):
        self.build["status"] = "PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
        self.refresh_build()
        with self.assertRaises(ValueError): self.admit()

    def test_producer_byte_mutation_rejected(self):
        (self.root / "producer.py").write_text("# different producer")
        with self.assertRaises(ValueError): self.admit()

    def test_assembly_from_another_native_manifest_rejected(self):
        assembly = json.loads(Path(self.contract["build"]["assembly"]["path"]).read_bytes())
        assembly["sourceManifestSHA256"] = "c" * 64
        reference = self.save("assembly.json", assembly)
        self.contract["build"]["assembly"] = reference
        self.build["assemblyReceiptSHA256"] = reference["sha256"]
        self.refresh_build()
        with self.assertRaises(ValueError): self.admit()

    def test_unbound_complete_product_inventory_rejected(self):
        self.build["completeProductsInventory"]["sha256"] = "c" * 64
        self.refresh_build()
        with self.assertRaises(ValueError): self.admit()

    def test_actual_ui_copy_mutation_rejected(self):
        path = Path(self.proofs["ui"]["requiredSources"][0]["compiledPath"])
        path.write_text("mutated compiled UI source")
        with self.assertRaises(ValueError): self.admit()

    def test_generated_scheme_mutation_rejected(self):
        (self.project / "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme").write_text("<DifferentScheme/>")
        with self.assertRaises(ValueError): self.admit()

    def test_missing_selected_native_compiler_input_rejected(self):
        proof = self.proofs["native"]
        proof["requiredSources"] = [row for row in proof["requiredSources"]
                                    if not row["repositoryPath"].endswith("PinkhaMiniAppsNativePreparationTests.swift")]
        self.refresh_proof("native")
        with self.assertRaises(ValueError): self.admit()

    def test_duplicate_actual_compiler_source_rejected(self):
        row = self.proofs["ui"]["actualCompilerFileLists"][0]
        path = Path(row["path"])
        path.write_text(path.read_text() + row["requiredSourcePaths"][0] + "\n")
        row["sha256"] = gate.sha256(path)
        self.refresh_proof("ui")
        with self.assertRaises(ValueError): self.admit()

    def test_write_auxiliary_file_without_compiler_invocation_rejected(self):
        proof = self.proofs["ui"]
        original_path = proof["actualCompilerFileLists"][0]["originalPath"]
        line = "WriteAuxiliaryFile " + original_path
        path = self.root / "ui.log"; path.write_text(line + "\n** TEST BUILD SUCCEEDED **\n")
        reference = gate.make_ref(path)
        self.contract["build"]["logs"]["ui"] = reference
        self.build["ui"].update(logSHA256=reference["sha256"], logBytes=path.stat().st_size)
        proof["buildLog"] = reference
        proof["actualCompilerFileLists"][0]["compilerInvocation"]["lineSHA256"] = hashlib.sha256(line.encode()).hexdigest()
        self.refresh_proof("ui")
        with self.assertRaises(ValueError): self.admit()

    def test_compiler_proof_for_different_target_rejected(self):
        self.proofs["ui"]["actualCompilerFileLists"][0]["compilerInvocation"]["moduleName"] = "UnrelatedTests"
        self.refresh_proof("ui")
        with self.assertRaises(ValueError): self.admit()

    def test_unbound_ui_compiler_proof_rejected(self):
        self.proofs["ui"]["sourceCommit"] = "c" * 40
        self.contract["build"]["uiCompilationProof"] = self.save("foreign-proof.json", self.proofs["ui"])
        with self.assertRaises(ValueError): self.admit()


    def test_changed_actual_git_head_rejected(self):
        self.git_observed["commit"] = "c" * 40
        with self.assertRaises(ValueError): self.admit()

    def test_changed_pin_json_omitted_by_original_suffix_snapshot_rejected(self):
        (self.source / "Tools/Hanlin/source.json").write_text("different SDK pin")
        with self.assertRaises(ValueError): self.admit()

    def test_root_selected_native_source_omission_rejected(self):
        admission = json.loads(Path(self.build["controlAdmission"]["admission"]["path"]).read_bytes())
        admission["selectedNativeTestSources"].append("AnyTypeTests/Pinkha/UncompiledFixture.swift")
        self.build["controlAdmission"]["admission"] = self.save("root-admission.json", admission)
        self.refresh_build()
        with self.assertRaises(ValueError): self.admit()

    def test_case_alias_with_same_bytes_but_different_file_rejected(self):
        proof = self.proofs["native"]
        selected = proof["requiredSources"][0]
        expected = Path(selected["compiledPath"])
        other = Path(str(expected).replace("/AnyTypeTests/", "/anytypetests/"))
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_bytes(expected.read_bytes())
        row = proof["actualCompilerFileLists"][0]
        path = Path(row["path"])
        path.write_text(path.read_text().replace(str(expected), str(other)))
        row["sha256"] = gate.sha256(path)
        self.refresh_proof("native")
        with self.assertRaises(ValueError): self.admit()

    def test_original_git_probe_reads_exact_committed_pin_and_ui_blobs(self):
        subprocess.run(["git", "init", str(self.source)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "user.name=Fixture Controls",
                        "-c", "user.email=fixture@example.invalid", "commit", "-m", "Disposable original Git input fixture"],
                       check=True, capture_output=True)
        commit = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        observed = ORIGINAL_GIT_SOURCE(self.source, commit)
        self.assertEqual(observed["commit"], commit)
        self.assertEqual(observed["status"], "")
        self.assertEqual(observed["files"], self.git_observed["files"])



class OriginalResultControls(unittest.TestCase):
    def setUp(self):
        self.udid = "actual-owned-device-fixture"
        self.runtime = {"family": "ipad", "version": "27.0", "build": "24A434", "architecture": "arm64"}
        self.method = gate.METHODS[6][2]
        self.summary = {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0,
                        "devicesAndConfigurations": [{"device": {"deviceId": self.udid, "osVersion": "27.0",
                            "osBuildNumber": "24A434", "architecture": "arm64", "modelName": "iPad fixture"}}]}
        self.tree = {"nodeType": "Test Case", "nodeIdentifier": self.method + "()", "result": "Passed"}

    def validate(self):
        return verify_test_result(self.summary, self.tree, "PinkhaStage1AcceptanceUITests",
                                  self.method, self.udid, self.runtime)

    def test_exact_actual_case_and_destination_are_required(self):
        self.assertEqual(self.validate()["counts"]["passedTests"], 1)

    def test_zero_test_success_rejected(self):
        self.summary.update(totalTestCount=0, passedTests=0)
        with self.assertRaises(ValueError): self.validate()

    def test_skipped_case_rejected(self):
        self.summary.update(passedTests=0, skippedTests=1)
        with self.assertRaises(ValueError): self.validate()

    def test_foreign_method_rejected(self):
        self.tree["nodeIdentifier"] = "UnrelatedSuite/testSomethingElse()"
        with self.assertRaises(ValueError): self.validate()

    def test_foreign_runtime_rejected(self):
        self.summary["devicesAndConfigurations"][0]["device"]["deviceId"] = "other-device"
        with self.assertRaises(ValueError): self.validate()


if __name__ == "__main__":
    unittest.main()
