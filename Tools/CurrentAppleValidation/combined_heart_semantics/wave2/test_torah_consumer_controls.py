"""Bounded portable controls, using synthetic commands/compiler/XCTest records.

No application admission, Swift compiler, simulator, native call or XCTest is
performed. The original parser/result/continuity function bodies are exercised
with explicitly synthetic inputs; these are not application acceptance results.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

import materialize_torah_control as materializer
import torah_hosted_profile as hosted
import torah_ui_consumer as consumer
import torah_ui_profile as profile

SOURCE = Path(os.environ["PINKHA_TORAH_CONTROL_SOURCE"])
HOST = Path(os.environ["PINKHA_TORAH_ORIGINAL_HOST"])
COMMON = Path(os.environ["PINKHA_TORAH_ORIGINAL_COMMON"])
RTL_PROFILE = Path(os.environ["PINKHA_TORAH_RTL_PROFILE"])
SYNTHETIC_UDID = "SYNTHETIC-PORTABLE-NO-DEVICE"


def functions(path, names, namespace):
    """Load exact original function nodes, without executing its runner/imports."""
    source = path.read_text()
    selected = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != set(names):
        raise ValueError("Missing exact original helper function")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


def shared_functions():
    namespace = dict(Path=Path, stat=stat, os=os, json=json, hashlib=hashlib, require=profile.require)
    return functions(COMMON, ("raw", "sha", "digest", "decode", "write", "write_bytes"), namespace)


class TorahConsumerControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pinkha-torah-portable-control-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_materializer_restores_original_and_preserves_all_original_plans(self):
        raw, proof = materializer.compose(HOST.read_bytes())
        self.assertTrue(proof["inverseRestoresEveryOriginalByte"])
        self.assertTrue(proof["unchangedMandatoryPropertiesSetPostflight"])
        self.assertTrue(proof["unchangedOwnedSimulatorFinally"])
        self.assertEqual(proof["XCTestInvocations"], 0)
        def plans(value):
            return ast.literal_eval(next(node.value for node in ast.parse(value).body if isinstance(node, ast.Assign)
                                         and any(isinstance(target, ast.Name) and target.id == "PLANS" for target in node.targets)))
        original, current = plans(HOST.read_bytes()), plans(raw)
        self.assertEqual({name: current[name] for name in original}, original)
        self.assertEqual({name: current[name] for name in materializer.NEW_PLANS}, materializer.NEW_PLANS)
        self.assertTrue(all(not any(lane.startswith("t5-") for lane in lanes) for lanes in materializer.NEW_PLANS.values()))
        with self.assertRaisesRegex(ValueError, "Exact reviewed e877"):
            materializer.compose(HOST.read_bytes() + b"\n# altered donor\n")

    def canonical_fixture(self, suffix="canonical"):
        root = self.root / suffix
        lane = "canonical-properties"
        directory = root / "evidence/lanes" / lane
        prep_path = directory / "preparation"
        command_root = root / "commands"
        command = {"status": "PASS_COMMAND", "exitCode": 0, "argv": ["synthetic-not-executed-xcodebuild"]}
        shared = shared_functions()
        shared.write(prep_path / "invocation.json", {"argv": command["argv"]})
        log_dir = command_root / (lane + "-preparation-test")
        shared.write(log_dir / "result.json", command)
        native = {"PINKHA_PROPERTIES_SPACE_ID": "synthetic-space", "PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED": "1",
                  "PINKHA_PROPERTIES_CHIDDUSH_ID": "synthetic-chiddush", "PINKHA_PROPERTIES_ARTICLE_ID": "synthetic-article",
                  "PINKHA_PROPERTIES_RESEARCH_ID": "synthetic-research",
                  "PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS": json.dumps({"synthetic-" + role: ["Native property"]
                                                                         for role in ("chiddush", "article", "research")})}
        console = b"SYNTHETIC PORTABLE CONSOLE\n" + b"PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON " + json.dumps(native).encode() + b"\n"
        shared.write_bytes(log_dir / "original.log", console)
        path = SOURCE / "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py"
        self.assertEqual(profile.sha(path.read_bytes()), consumer.ORIGINAL_HELPERS["run_wave15_acceptance"])
        original = functions(path, ("property_environment", "nonempty"), dict(json=json, require=profile.require))
        subject = SimpleNamespace(shared_module=shared, commands=SimpleNamespace(root=command_root),
                                  helpers={"run_wave15_acceptance": original})
        args = (subject, lane, directory, {"command": command}, prep_path, {"spaceId": "synthetic-space"})
        return args, console, native, log_dir

    def test_canonical_original_console_and_parser_are_retained_byte_exact(self):
        args, console, native, _ = self.canonical_fixture()
        environment, actual = consumer._canonical_environment(*args)
        self.assertEqual(actual, console)
        for key, value in native.items():
            self.assertEqual(environment[key], value)
        self.assertEqual(environment["PINKHA_PROPERTIES_SOURCE_QUERY"], "Genesis 1:1")
        parser_dir = args[4] / "canonical-original-console"
        self.assertEqual((parser_dir / "command-original-preparation.log").read_bytes(), console)
        evidence = json.loads((parser_dir / "provenance.json").read_text())
        self.assertEqual(evidence["originalConsoleSHA256"], profile.sha(console))
        self.assertFalse(evidence["writingIDsProvenByStage1FixtureAlone"])

    def test_canonical_foreign_console_or_unbound_command_fails(self):
        args, _, _, _ = self.canonical_fixture("foreign-space")
        args = (*args[:-1], {"spaceId": "different-space"})
        with self.assertRaisesRegex(ValueError, "another Space"):
            consumer._canonical_environment(*args)
        args, _, _, log_dir = self.canonical_fixture("unbound-command")
        value = json.loads((log_dir / "result.json").read_text())
        value["argv"] = ["another-command"]
        (log_dir / "result.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "this actual recorded command"):
            consumer._canonical_environment(*args)

    def compiler_fixture(self, kind):
        root = self.root / kind
        source = root / "source"
        source.mkdir(parents=True)
        suites = hosted.selected_suites(kind)
        for specification in suites.values():
            path = source / specification["source_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / specification["source_path"], path)
        git = ["git", "-C", str(source)]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "."], check=True)
        subprocess.run(git + ["-c", "user.name=Portable Control", "-c", "user.email=control@example.invalid",
                              "commit", "-q", "-m", "Synthetic compiler proof control"], check=True)
        commit = subprocess.check_output(git + ["rev-parse", "HEAD"]).decode().strip()
        rows = [{"repositoryPath": spec["source_path"], "compiledPath": str(source / spec["source_path"]),
                 "sha256": spec["source_sha256"], "bytes": (source / spec["source_path"]).stat().st_size} for spec in suites.values()]
        filelist = root / "retained.SwiftFileList"
        filelist.write_text("".join(row["compiledPath"] + "\n" for row in rows))
        original = root / "Synthetic/AnytypeTests.build/AnytypeTests.SwiftFileList"
        line = "builtin-SwiftDriver -- /synthetic/swiftc -module-name AnytypeTests @" + str(original)
        log = root / "synthetic-not-a-build.log"
        log.write_text(line + "\n")
        witness = {"lineNumber": 1, "lineSHA256": profile.sha(line.encode()), "moduleName": "AnytypeTests"}
        def pin(path):
            return {"path": str(path), "sha256": profile.sha(path.read_bytes())}
        proof = {"schema": "pinkha-exact-native-compiler-inputs-v1", "status": "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION",
                 "sourceCommit": commit, "testsExecuted": 0, "requiredSources": rows, "buildLog": pin(log),
                 "actualCompilerFileLists": [{**pin(filelist), "originalPath": str(original),
                                              "compilerInvocation": witness, "compilerInvocations": [witness]}]}
        proof_path = root / "synthetic-compiler-proof.json"
        def qualify(value=proof):
            proof_path.write_text(json.dumps(value))
            return hosted.source_contract(source, kind, source_commit=commit,
                                          native_compilation_proof=pin(proof_path), rtl_profile_path=RTL_PROFILE)
        return source, proof, qualify

    def test_four_source_bound_profiles_require_actual_target_proof(self):
        for kind in hosted.PROFILES:
            with self.subTest(profile=kind):
                source, proof, qualify = self.compiler_fixture(kind)
                contract = qualify()
                expected = hosted.PROFILES[kind]
                self.assertEqual(contract["expected_methods"], expected["methods"])
                self.assertEqual(contract["declared_cases"], expected["cases"])
                self.assertEqual(contract["tests_executed"], 0)
                self.assertEqual(contract["original_target"], expected["original_target"])
                self.assertEqual(len(hosted.invocation_selectors(contract["compiled_identifiers"], contract)), len(expected["suites"]))
                with self.assertRaisesRegex(ValueError, "source/compiler-qualified"):
                    hosted.invocation_selectors(contract["compiled_identifiers"], hosted.declared_contract(source, kind))
                missing = copy.deepcopy(proof)
                missing["requiredSources"].pop()
                with self.assertRaisesRegex(ValueError, "absent from native compiler proof"):
                    qualify(missing)
                foreign = copy.deepcopy(proof)
                foreign["actualCompilerFileLists"][0]["originalPath"] = str(self.root / "PinkhaAnyUITests.build/tests.SwiftFileList")
                with self.assertRaisesRegex(ValueError, "not from AnytypeTests"):
                    qualify(foreign)

    def test_exact_hosted_enumeration_rejects_partial_or_disabled_selection(self):
        _, _, qualify = self.compiler_fixture("related-hosted")
        contract = qualify()
        payload = {"errors": [], "values": [{"testPlan": hosted.TARGET,
                   "enabledTests": [{"identifier": value} for value in contract["compiled_identifiers"]], "disabledTests": []}]}
        validation = hosted.validators("related-hosted")
        self.assertEqual(len(validation.validate_enumeration(payload, contract)["identifiers"]), 5)
        partial, disabled = copy.deepcopy(payload), copy.deepcopy(payload)
        partial["values"][0]["enabledTests"].pop()
        disabled["values"][0]["disabledTests"] = [disabled["values"][0]["enabledTests"][0]]
        for value in (partial, disabled):
            with self.assertRaises(ValueError):
                validation.validate_enumeration(value, contract)

    def test_original_hosted_result_validators_reject_missing_methods_and_cases(self):
        for kind, specification in hosted.PROFILES.items():
            nodes = []
            for suite, value in hosted.selected_suites(kind).items():
                for name, method in value["methods"].items():
                    signature = "(" + "".join(p["name"] + ":" for p in method["parameters"]) + ")"
                    cases = [{"nodeType": "Arguments", "name": "synthetic-case-" + str(value), "result": "Passed"}
                             for value in method["argument_collections"][0]] if method["argument_collections"] else []
                    nodes.append({"nodeType": "Test Case", "nodeIdentifier": hosted.TARGET + "/" + suite + "/" + name + signature,
                                  "result": "Passed", "children": cases})
            summary = {"totalTestCount": specification["cases"], "passedTests": specification["cases"], "failedTests": 0,
                       "skippedTests": 0, "devicesAndConfigurations": [{"device": {"deviceId": SYNTHETIC_UDID,
                         "osVersion": "27.0", "osBuildNumber": "SYNTHETIC", "architecture": "arm64",
                         "modelName": "iPad synthetic portable control", "platform": "iOS Simulator"}}]}
            tree = {"testNodes": nodes}
            validator = hosted.validators(kind)
            self.assertEqual(validator.validate_results(summary, tree, SYNTHETIC_UDID)["declared_case_count"], specification["cases"])
            missing = copy.deepcopy(tree)
            missing["testNodes"].pop()
            with self.assertRaises(ValueError):
                validator.validate_results(summary, missing, SYNTHETIC_UDID)
            if kind in {"related-hosted", "inspector-hosted"}:
                incomplete = copy.deepcopy(tree)
                next(node for node in incomplete["testNodes"] if node["children"])["children"].pop()
                with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
                    validator.validate_results(summary, incomplete, SYNTHETIC_UDID)

    def test_combined_runtime_uses_common_identity_and_actual_inspector_package(self):
        shared = shared_functions()
        shared.MANIFEST, shared.VERSION = "a" * 64, "synthetic-common-runtime"
        source = self.root / "source"
        shared.write(source / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
                     {"pins": [{"identity": "torahinspectorkit", "state": {"revision": "b" * 40}}]})
        admitted = {"commit": "c" * 40, "sourceStateSHA256": "d" * 64,
                    "runtimeIdentity": {"identity": {"protocol": "pinkha-unified-runtime-full-identity-v1",
                      "sourceManifestSHA256": shared.MANIFEST, "heartVersion": shared.VERSION},
                      "nativeRuntimeExecutedByThisCheck": False, "producerRuntimeProofSHA256": "e" * 64}}
        subject = SimpleNamespace(shared_module=shared, source=source, source_admission=admitted,
                                  binding={"sourceSHA": "c" * 40, "runID": "1", "runAttempt": "1"})
        actual = consumer._combined_runtime_source(subject)
        self.assertEqual(actual["kit_sha"], "b" * 40)
        self.assertEqual(actual["candidate_inputs_sha256"], "d" * 64)
        subject.source_admission = copy.deepcopy(admitted)
        subject.source_admission["runtimeIdentity"]["identity"]["sourceManifestSHA256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact combined runtime"):
            consumer._combined_runtime_source(subject)

    def test_continuity_adapter_preserves_full_method_names_and_original_ax_bytes(self):
        shared = shared_functions()
        path = SOURCE / "Tools/PinkhaSimulatorGate/run_ui27.py"
        self.assertEqual(profile.sha(path.read_bytes()), consumer.ORIGINAL_HELPERS["run_ui27"])
        app = self.root / "synthetic-installed.app"
        shared.write_bytes(app / "Anytype", b"SYNTHETIC-NOT-EXECUTABLE")
        carriers = {"sha256": "a" * 64}
        live = {"pid": 12345, "installed_app": str(app), "process_start_identity": "SYNTHETIC-NO-PROCESS",
                "installed_app_executable_sha256": shared.digest(app / "Anytype"),
                "built_app_executable_sha256": shared.digest(app / "Anytype"),
                "installed_code_carriers": carriers, "built_code_carriers": carriers,
                "runtime_sha256": "b" * 64, "source_sha": "c" * 40, "run_id": "1", "run_attempt": "1",
                "kit_sha": "d" * 40, "native_marker": "SYNTHETIC", "candidate_inputs_sha256": "e" * 64}
        original = functions(path, ("verify_ui_process_continuity",), dict(
            json=json, re=re, Path=Path, digest=shared.digest, write=shared.write,
            read_process_identity=lambda *args, **kwargs: "SYNTHETIC-NO-PROCESS", code_carriers=lambda _: carriers))
        subject = SimpleNamespace(shared_module=shared, helpers={"run_ui27": original})
        ui_path = self.root / "ui"
        actual = ui_path / "private-attachments"
        methods = ["AnytypeComprehensiveAcceptanceUITests/testDocumentSourceSearchPresentation",
                   "AnytypeComprehensiveAcceptanceUITests/testInspectorEmbeddedSearchOpenReturnAndDocumentLink"]
        manifest = []
        for index, method in enumerate(methods):
            attachments = []
            for label in ("entry-hierarchy", "final-hierarchy"):
                filename = str(index) + "-" + label + ".txt"
                shared.write_bytes(actual / filename, b"Application, pid: 12345\nSynthetic AX control\n")
                attachments.append({"suggestedHumanReadableName": label, "exportedFileName": filename})
            manifest.append({"testIdentifier": method + "()", "attachments": attachments})
        shared.write(actual / "manifest.json", manifest)
        result = consumer._continuity(subject, "inspector", ui_path, live, methods)
        self.assertEqual(set(result["methods"]), set(methods))
        copied = ui_path / "original-process-continuity/original-attachments"
        self.assertEqual((copied / "manifest.json").read_bytes(), (actual / "manifest.json").read_bytes())
        for filename in actual.glob("*.txt"):
            self.assertEqual((copied / filename.name).read_bytes(), filename.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "missing selected UI methods"):
            original.verify_ui_process_continuity(ui_path / "original-process-continuity", "original", live,
                                                 [method.split("/", 1)[1] for method in methods])


if __name__ == "__main__":
    unittest.main()
