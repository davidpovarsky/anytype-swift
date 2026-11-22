"""New controls for the observed bind ownership failure; no native test reruns.

The stdlib-only launcher is imported unchanged. The two controller functions
are compiled directly from their actual source AST to isolate these filesystem
and identity checks from Apple-only build imports. This does not claim an
Apple framework build or iOS execution.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace
import unittest

import contract
import retain_controls


def exact_functions(path, names, namespace, constants=()):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    selected = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in names) or (
        isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name) and node.targets[0].id in constants)]
    if {node.name for node in selected if isinstance(node, ast.FunctionDef)} != set(names):
        raise AssertionError("Expected exact controller functions")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def module(path):
    spec = importlib.util.spec_from_file_location("unchanged_r15_launcher", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class CoherentBindingScopeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launcher = module(contract.ROOT / "Tools/PinkhaNativeDerived/r15_runtime_go.py")
        namespace = dict(Path=Path, contract=contract, binding=SimpleNamespace(launcher=cls.launcher))
        cls.prepare = staticmethod(exact_functions(contract.HERE / "build.py",
            {"prepare_variant_binding"}, namespace)["prepare_variant_binding"])
        namespace = exact_functions(contract.ROOT / "Tools/TorahNativeOperations/authorized_read/build_apple.py",
            {"validate_simulator_framework"}, dict(require=contract.require, re=re), constants=("CANDIDATE", "VERSION"))
        cls.validate_framework = staticmethod(namespace["validate_simulator_framework"])
        cls.legacy_version = namespace["VERSION"]

    def fixture(self, root):
        binding, evidence, heart = root / "binding", root / "proof", root / "heart"
        for path in (binding, evidence, heart):
            path.mkdir()
        seed = binding / "generated-dependency-seed"
        seed.mkdir()
        original = dict(Module={"Path": "gobind"}, Go="1.26", Require=[], Replace=[dict(
            Old=dict(Path=self.launcher.GENPROTO, Version="v0.0.0-20200101000000-old"),
            New=dict(Path=self.launcher.GENPROTO, Version=self.launcher.VERSION))])
        value = dict(schema="pinkha-generated-module-graph-v2", native_directory=str(heart.resolve()),
            before_tidy_manifest=original, prepared_tidy_manifest=self.launcher.reviewed_generated_manifest(original),
            selected_dependencies={"example.org/fixed": {"version": "v1.0.0"}})
        target = seed / "bind-contract.json"
        contract.save(target, value)
        prepared = dict(env={"GOPROXY": "off", "GOWORK": "original-native-workspace",
            "PINKHA_T5_GENERATED_CONTRACT": str(target),
            "PINKHA_T5_GENERATED_CONTRACT_SHA256": contract.digest(target)})
        return binding, evidence, heart, target, prepared

    def test_variant_roots_use_the_unchanged_ownership_gate_and_remain_distinct(self):
        with tempfile.TemporaryDirectory(prefix="coherent-scope-control-") as directory:
            root = Path(directory).resolve()
            binding, evidence, heart, target, prepared = self.fixture(root)
            before = target.read_bytes(), deepcopy(prepared)
            # Reproduce the original failure layout with the real unchanged gate.
            old = root / "production" / "gomobile-tmp"
            old.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "Owned generated-graph"):
                self.launcher.load_seed_contract(target, contract.digest(target), heart, old)
            outputs = [self.prepare(prepared, binding, evidence, heart, kind) for kind in ("production", "fixture")]
            self.assertNotEqual(outputs[0][0]["TMPDIR"], outputs[1][0]["TMPDIR"])
            self.assertNotEqual(outputs[0][1], outputs[1][1])
            for kind, (env, audit) in zip(("production", "fixture"), outputs):
                temporary = Path(env["PINKHA_T5_MOBILE_TMP"])
                self.assertEqual(temporary.parent, binding)
                self.assertEqual(audit, evidence / (kind + "-go-launcher"))
                self.assertEqual(env["GOPROXY"], "off")
                self.assertEqual(self.launcher.select_scope(temporary / "gomobile-work" / "iossimulator/src-arm64",
                    heart, temporary, binding / "go.work"), ("generated-gobind", "off"))
                self.launcher.load_seed_contract(target, env["PINKHA_T5_GENERATED_CONTRACT_SHA256"], heart, temporary)
                self.assertEqual(json.loads((evidence / (kind + "-binding-scope.json")).read_bytes())["status"],
                                 "PASS_OWNED_BINDING_SCOPE")
            self.assertEqual(before, (target.read_bytes(), prepared))

    def test_unowned_tampered_and_foreign_native_contracts_are_rejected_before_bind(self):
        for bad in ("unowned", "tampered", "wrong-hash", "foreign-native", "symlink"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory(prefix="coherent-scope-negative-") as directory:
                root = Path(directory).resolve()
                binding, evidence, heart, target, prepared = self.fixture(root)
                if bad == "unowned":
                    binding = root / "unowned"; binding.mkdir()
                elif bad == "tampered":
                    target.write_bytes(target.read_bytes() + b" ")
                elif bad == "wrong-hash":
                    prepared["env"]["PINKHA_T5_GENERATED_CONTRACT_SHA256"] = "0" * 64
                elif bad == "foreign-native":
                    heart = root / "foreign-heart"; heart.mkdir()
                else:
                    symlink = target.parent / "symlink-contract.json"
                    symlink.symlink_to(target)
                    prepared["env"]["PINKHA_T5_GENERATED_CONTRACT"] = str(symlink)
                with self.assertRaisesRegex(RuntimeError, "Owned generated-graph|Generated-graph contract identity"):
                    self.prepare(prepared, binding, evidence, heart, "production")
                self.assertFalse((evidence / "production-binding-scope.json").exists())

    def test_exact_coherent_framework_version_and_legacy_default_both_remain_strict(self):
        info = dict(AvailableLibraries=[dict(LibraryIdentifier="ios-arm64-simulator", SupportedPlatform="ios",
            SupportedPlatformVariant="simulator", SupportedArchitectures=["arm64"], LibraryPath="Lib.framework")])
        expected = "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + contract.PATCH
        slices = [dict(path="ios-arm64-simulator/Lib.framework/Lib", architecture="arm64", marker=expected,
                       sha256="1" * 64)]
        self.validate_framework(info, slices, expected_version=expected)
        with self.assertRaisesRegex(ValueError, "Wrong candidate binary identity"):
            self.validate_framework(info, slices)
        legacy = [dict(slices[0], marker=self.legacy_version)]
        self.validate_framework(info, legacy)
        with self.assertRaisesRegex(ValueError, "Wrong candidate binary identity"):
            self.validate_framework(info, legacy, expected_version=expected)
        for bad in ("other-version", expected + "-changed", ""):
            with self.subTest(version=bad), self.assertRaises(ValueError):
                self.validate_framework(info, slices, expected_version=bad)
        for field, bad in (("architecture", "x86_64"), ("path", "ios-arm64/Lib.framework/Lib"),
                           ("sha256", "")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate_framework(info, [dict(slices[0], **{field: bad})], expected_version=expected)
        with self.assertRaises(ValueError):
            self.validate_framework(dict(AvailableLibraries=[dict(info["AvailableLibraries"][0],
                SupportedPlatformVariant="device")]), slices, expected_version=expected)

    def test_retained_controls_reject_changed_source_or_original_evidence(self):
        retained = retain_controls.qualify(contract.ROOT)
        self.assertEqual(retained["python_methods_passed"], 5)
        self.assertEqual(retained["embedded_go_methods_passed"], 3)
        self.assertEqual(retained["methods_executed_again"], 0)
        dependencies = list(retain_controls.SOURCES) + [retain_controls.PROOF + "/" + name for name in
            ("original-evidence.zip", "original-controls.log", "original-build.json")]
        for changed in ("Tools/PinkhaNativeDerived/coherent_apple/fixture_bridge.go",
                        retain_controls.PROOF + "/original-controls.log",
                        retain_controls.PROOF + "/original-build.json",
                        retain_controls.PROOF + "/original-evidence.zip"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(prefix="retained-control-negative-") as directory:
                root = Path(directory)
                for name in dependencies:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(contract.ROOT / name, target)
                target = root / changed
                target.write_bytes(target.read_bytes() + b" ")
                with self.assertRaisesRegex(ValueError, "Retained control dependency changed|Original control evidence changed"):
                    retain_controls.qualify(root)


if __name__ == "__main__":
    unittest.main()
