"""Portable admission/transport regressions; these execute no Apple tests."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).parent))
import native_inputs as native
import run


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def plan():
    return {"schema": "pinkha-hosted-original-shared-build-plan-v1", "readyForBuild": True,
            "readyForExport": False, "repository": run.REPOSITORY, "controlCommit": "1" * 40,
            "appSourceSHA": "2" * 40, "appSourceTree": "3" * 40, "hanlinRevision": "4" * 40,
            "nativeBuildDate": "2026-11-26", "originalProducerCommit": run.ORIGINAL_COMMIT,
            "originalProducerSHA256": run.ORIGINAL_SHA, "compilerProofAdapterSHA256": run.ADAPTER_SHA,
            "pins": dict(run.NATIVE_PINS, packageResolvedSHA256="e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd",
                         sdkSourcePinSHA256=digest("sdk-pin"), sdkMaterializerSHA256=digest("sdk-materializer"),
                         sdkMaterializationReceiptSHA256=digest("sdk-materialization"),
                         uiGeneratorSHA256="7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0",
                         page154UITestSHA256="8834541f5a47da80b460ecb96b20c930813b743d94f285fc1efba8a93f65ee4d"),
            "toolchain": {"developerDir": run.DEVELOPER, "xcodeVersion": "Xcode 27.0\nBuild version 27A266a",
                          "simulatorSDKBuild": "24A430", "swiftIdentity": "swiftlang-6.4.0.34.1 clang-2100.3.34.1"},
            "resourcePolicy": {"phaseGrowthAllowanceBytes": run.PHASE_GROWTH, "emergencyFloorBytes": run.FLOOR,
                               "concurrentGrowthAllowanceBytes": run.CONCURRENT, "jobs": 4,
                               "phaseTimeoutSeconds": 7200, "resultArchiveAllowanceBytes": run.PACK_GROWTH},
            "compilerInputs": {"native": {"AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift": {"bytes": 10, "sha256": digest("native")}},
                               "ui": {"PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift": {"bytes": 10, "sha256": digest("ui")}}},
            "nativeArtifact": {"id": 1, "runID": 2, "runAttempt": 1, "zipBytes": 50, "payloadBytes": 40,
                               "zipSHA256": digest("zip"), "payloadSHA256": digest("payload"),
                               "payloadManifestSHA256": digest("manifest"), "producerCommit": "5" * 40,
                               "name": "Pinkha-Native8ac-Inputs-2-1"},
            "resourceRationale": {"kind": "PORTABLE_CONTROL_FIXTURE_ONLY"}}


class AdmissionTests(unittest.TestCase):
    def test_explicit_source_and_artifact_plan_admits(self):
        self.assertEqual(run.validate_plan(plan(), "1" * 40), plan())

    def test_false_ready_does_not_build(self):
        item = plan()
        item["readyForBuild"] = False
        with self.assertRaisesRegex(ValueError, "finalize"):
            run.validate_plan(item, "1" * 40)

    def test_branch_tip_is_not_an_immutable_source(self):
        item = plan()
        item["appSourceSHA"] = "codex/current"
        with self.assertRaisesRegex(ValueError, "immutable"):
            run.validate_plan(item, "1" * 40)

    def test_other_native_manifest_rejected(self):
        item = plan()
        item["pins"]["nativeSourceManifestSHA256"] = digest("changed-native")
        with self.assertRaisesRegex(ValueError, "native8ac"):
            run.validate_plan(item, "1" * 40)

    def test_warm_budget_cannot_be_used_as_cold_hosted_budget(self):
        item = copy.deepcopy(plan())
        item["resourcePolicy"]["phaseGrowthAllowanceBytes"]["app"] = 6 * run.GIB
        with self.assertRaisesRegex(ValueError, "cold hosted resource"):
            run.validate_plan(item, "1" * 40)

    def test_missing_concrete_artifact_rejected(self):
        item = plan()
        item["nativeArtifact"]["id"] = 0
        with self.assertRaisesRegex(ValueError, "Concrete native artifact"):
            run.validate_plan(item, "1" * 40)

    def test_newer_xcode_does_not_qualify_original_toolchain(self):
        item = plan()
        item["toolchain"]["xcodeVersion"] = "Xcode 27.2\nBuild version 27B52"
        with self.assertRaisesRegex(ValueError, "Exact original Xcode"):
            run.validate_plan(item, "1" * 40)

    def test_dispatch_request_preserves_exact_plan_final_newline(self):
        raw = (json.dumps(plan(), indent=2) + "\n").encode()
        request = run.dispatch_body(raw, "codex/chatgpt-wave15-hosted-build-20261127", "wave3-hosted-shared-build")
        encoded = request["inputs"]["shared_build_plan_json"].encode()
        self.assertEqual(encoded, raw)
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), request["inputs"]["shared_build_plan_sha256"])


class OriginalProducerTests(unittest.TestCase):
    def test_actual_original_inverse_and_owned_runtime_guards(self):
        control = Path(__file__).resolve().parents[3]
        adapter_path = control / "Tools/PinkhaDualEngineRuntime/wave3_shared_build.py"
        spec = importlib.util.spec_from_file_location("original_adapter_test", adapter_path)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        base = (adapter_path.parent / "build_wave2_app16_compiler_qualified.py").read_text()
        self.assertEqual(hashlib.sha256(base.encode()).hexdigest(), run.ORIGINAL_SHA)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def reference(name):
                p = root / name
                p.write_text(json.dumps({"fixture": name}) + "\n")
                return run.ref(p)
            data = plan()
            admission = {"appSourceSHA": data["appSourceSHA"], "buildRoot": str(root / "build"),
                         "sourceRoot": str(root / "source"), "appDerived": str(root / "derived"),
                         "nativeMaterializationRoot": str(root / "native"), "nativeBuildDate": "2026-11-26",
                         "sourceStaging": reference("stage.json"), "cacheQualification": reference("cache.json"),
                         "originalRetention": reference("retention.json"), "pins": data["pins"],
                         "selectedNativeTestSources": list(data["compilerInputs"]["native"]),
                         "selectedUITestSources": list(data["compilerInputs"]["ui"]), "hostedColdBuild": True,
                         "hostedResourceRationale": data["resourceRationale"]}
            p = root / "admission.json"
            p.write_text(json.dumps(admission))
            expanded, proof = run.expand(base, adapter, admission, p, native.sha(Path(run.__file__)))
            self.assertTrue(proof["inverseRestoresEveryOriginalByte"])
            inverse = expanded
            for row in reversed(proof["hostedChanges"]):
                inverse = inverse.replace(row["new"], row["old"])
            for row in reversed(proof["wave3Inverse"]["changes"]):
                inverse = inverse.replace(row["new"], row["old"])
            self.assertEqual(inverse, base)
            for name in ("run_phase", "source_state", "verify_new_test_compiler_inputs"):
                self.assertEqual(adapter.function_source(expanded, name), adapter.function_source(base, name))
            self.assertNotIn("PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED", expanded)
            self.assertIn("hosted_package_closure(\"after-app\")", expanded)
            self.assertIn("--untracked-files=all", expanded)
            self.assertIn("w3_native_proof()", expanded)
            self.assertIn("w3_ui_after(ui_snapshot,ui_source,ui_project)", expanded)
            ast.parse(expanded)


class NativeTransportTests(unittest.TestCase):
    def fixture(self, directory):
        original = directory / "original"
        original.write_bytes(b"native transport fixture only\n")
        payload = directory / "fixture.tar.gz"
        receipt = native.pack({"native/source.txt": original}, payload, {"fixtureOnly": True})
        return payload, receipt

    def rewrite(self, original, destination, changes):
        with tarfile.open(original, "r:gz") as source, tarfile.open(destination, "w:gz", format=tarfile.PAX_FORMAT) as output:
            for row in source:
                content = source.extractfile(row).read() if row.isfile() else None
                for member, data in changes(row, content):
                    output.addfile(member, io.BytesIO(data) if data is not None else None)

    def test_complete_native_transport_bytes_mode_and_timestamp_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload, receipt = self.fixture(root)
            native.read_payload(payload, expected_manifest=receipt["payloadManifestSHA256"], destination=root / "restored")
            self.assertEqual(native.regular(root / "original"), native.regular(root / "restored/native/source.txt"))

    def test_changed_native_payload_file_rejected_before_materialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload, receipt = self.fixture(root)
            def change(member, data):
                if member.name == "native/source.txt":
                    data = b"x" * len(data)
                return [(member, data)]
            self.rewrite(payload, root / "bad.tar.gz", change)
            with self.assertRaisesRegex(ValueError, "Archived native bytes differ"):
                native.read_payload(root / "bad.tar.gz", expected_manifest=receipt["payloadManifestSHA256"], destination=root / "restored")
            self.assertFalse((root / "restored").exists())

    def test_symlink_payload_member_rejected_before_materialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload, receipt = self.fixture(root)
            def change(member, data):
                if member.name == "native/source.txt":
                    member.type, member.linkname, member.size = tarfile.SYMTYPE, "/private/account", 0
                    data = None
                return [(member, data)]
            self.rewrite(payload, root / "bad.tar.gz", change)
            with self.assertRaisesRegex(ValueError, "nonregular"):
                native.read_payload(root / "bad.tar.gz", expected_manifest=receipt["payloadManifestSHA256"], destination=root / "restored")
            self.assertFalse((root / "restored").exists())

    def test_duplicate_native_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload, receipt = self.fixture(root)
            self.rewrite(payload, root / "bad.tar.gz", lambda m, d: [(m, d)] * (2 if m.name == "native/source.txt" else 1))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                native.read_payload(root / "bad.tar.gz", expected_manifest=receipt["payloadManifestSHA256"])

    def test_traversal_name_rejected(self):
        for name in ("../secret", "/secret", "native/../secret", "native\\secret", "native//source"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                native.safe_relative(name)


class ActualPackageCheckoutTests(unittest.TestCase):
    def test_nonignored_untracked_source_cannot_qualify_as_locked_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, derived, evidence = root / "source", root / "derived", root / "evidence"
            checkout = derived / "SourcePackages/checkouts/pinned-package"
            checkout.mkdir(parents=True)
            evidence.mkdir()
            subprocess.run(["git", "init", "-q", str(checkout)], check=True)
            (checkout / "Package.swift").write_text("// portable package source witness\n")
            subprocess.run(["git", "-C", str(checkout), "add", "Package.swift"], check=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Control Test", "-c", "user.email=control@example.invalid",
                            "commit", "-qm", "Create exact package fixture"], check=True)
            revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
            lock = source / run.LOCK
            lock.parent.mkdir(parents=True)
            lock.write_text(json.dumps({"pins": [{"identity": "pinned-package", "state": {"revision": revision}}]}))
            namespace = {"SOURCE": source, "APP_DERIVED": derived, "EVIDENCE": evidence,
                         "w3_require": run.require, "write": run.write, "sha": native.sha,
                         "json": json, "subprocess": subprocess}
            text = Path(run.__file__).read_text()
            node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "hosted_package_closure")
            exec(compile(ast.get_source_segment(text, node), "<actual-checkout-control>", "exec"), namespace)
            namespace["hosted_package_closure"]("clean")
            (checkout / "Sources").mkdir()
            (checkout / "Sources/Injected.swift").write_text("let wouldBeCompiled = true\n")
            with self.assertRaisesRegex(ValueError, "untracked source differs"):
                namespace["hosted_package_closure"]("injected")
            self.assertFalse((evidence / "package-checkouts-injected.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
