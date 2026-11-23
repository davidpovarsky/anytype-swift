"""New identity/descriptor admission controls; no native or Apple execution."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import contract
import descriptor

ROOT = Path(__file__).resolve().parents[3]
NATIVE = ROOT / contract.HELPER
spec = importlib.util.spec_from_file_location("inline_native_admission_controls", NATIVE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class InlineDescriptorAdmissionTests(unittest.TestCase):
    def binding(self):
        return dict(sourceSHA="a" * 40, runID="123", runAttempt="1", nonce="b" * 32)

    def target(self):
        return dict(BlueprintName=contract.TARGET,
                    TestBundlePath="__TESTROOT__/Debug-iphonesimulator/RuntimeTests.xctest",
                    TestHostPath="__TESTROOT__/Debug-iphonesimulator/RuntimeTests-Runner.app/Runner",
                    TestingEnvironmentVariables={"XCInjectBundleInto": "__TESTHOST__/Runner", "XCODE_REQUIRED": "kept"},
                    EnvironmentVariables={"KEEP_ORIGINAL": "yes"},
                    OnlyTestIdentifiers=["OriginalUnusedSelector"],
                    SkipTestIdentifiers=["UnselectedSuite/oldMethod"])

    def modern(self):
        return {"__xctestrun_metadata__": {"FormatVersion": 2},
                "TestConfigurations": [{"Name": "Test Scheme Action", "IsEnabled": True,
                                        "TestTargets": [self.target()]}]}

    def test_actual_target_environment_is_bound_without_mutating_injection_or_original(self):
        for value in (self.modern(), {contract.TARGET:self.target(), "__xctestrun_metadata__":{"FormatVersion":1}}):
            with self.subTest(layout="modern" if "TestConfigurations" in value else "legacy"):
                before = copy.deepcopy(value)
                changed = descriptor.bind_document(value, self.binding())
                self.assertEqual(value, before)
                original, target = descriptor.targets(value)[0], descriptor.targets(changed)[0]
                self.assertEqual(target["TestingEnvironmentVariables"], original["TestingEnvironmentVariables"])
                self.assertEqual(target["EnvironmentVariables"],
                                 {**original["EnvironmentVariables"], **descriptor.validate_binding(self.binding())})
                self.assertEqual(target["OnlyTestIdentifiers"], [contract.METHOD])
                self.assertNotIn("TestEnvironmentVariables", target)
                for key in set(original) - {"EnvironmentVariables","OnlyTestIdentifiers"}:
                    self.assertEqual(target[key], original[key])

    def test_wrong_target_ambiguous_configuration_excluded_method_and_replayed_binding_are_refused(self):
        def wrong_target(v): v["TestConfigurations"][0]["TestTargets"][0]["BlueprintName"] = "UnrelatedUITests"
        def multiple_targets(v): v["TestConfigurations"][0]["TestTargets"].append(self.target())
        def multiple_configs(v): v["TestConfigurations"].append(copy.deepcopy(v["TestConfigurations"][0]))
        def disabled(v): v["TestConfigurations"][0]["IsEnabled"] = False
        def excluded(v): v["TestConfigurations"][0]["TestTargets"][0]["SkipTestIdentifiers"] = [contract.METHOD]
        def excluded_suite(v): v["TestConfigurations"][0]["TestTargets"][0]["SkipTestIdentifiers"] = [contract.METHOD.split("/")[0]]
        def replay(v): v["TestConfigurations"][0]["TestTargets"][0]["EnvironmentVariables"]["PINKHA_PREPARED_INLINE_APPLE_NONCE"] = "c" * 32
        for mutation in (wrong_target,multiple_targets,multiple_configs,disabled,excluded,excluded_suite,replay):
            with self.subTest(mutation=mutation.__name__):
                value=self.modern(); mutation(value); before=copy.deepcopy(value)
                with self.assertRaises(ValueError): descriptor.bind_document(value,self.binding())
                self.assertEqual(value,before)

    def test_malformed_source_run_nonce_and_extra_binding_fields_are_refused(self):
        for key,value in (("sourceSHA","a"*39),("sourceSHA","A"*40),("runID","0"),("runID",1),
                          ("runAttempt","01"),("nonce","b"*31),("nonce",False),("foreign","unexpected")):
            with self.subTest(key=key,value=value):
                binding=self.binding();binding[key]=value
                with self.assertRaises(ValueError):descriptor.bind_document(self.modern(),binding)

    def test_fresh_descriptor_keeps_original_testroot_and_never_overwrites_prior_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);products=root/"Products";products.mkdir();evidence=root/"evidence"
            original=products/"Original.xctestrun"
            raw=plistlib.dumps(self.modern(),fmt=plistlib.FMT_BINARY)
            original.write_bytes(raw)
            bound,audit=descriptor.bind_generated(products,evidence,self.binding())
            self.assertEqual(bound.parent,original.parent)
            self.assertEqual(original.read_bytes(),raw)
            self.assertEqual(audit["bound_descriptor_sha256"],contract.digest(bound))
            self.assertEqual(plistlib.loads(bound.read_bytes()),descriptor.bind_document(self.modern(),self.binding()))
            with self.assertRaises(ValueError):descriptor.bind_generated(products,evidence,self.binding())
            self.assertEqual(original.read_bytes(),raw)


class InlineNativeVersionAdmissionTests(unittest.TestCase):
    def manifest(self,version):
        return {"nativeVersion":version,"any":{"upstreamCommit":native.PINNED_COMMITS["any"]},
                "sdk":{"upstreamCommit":native.PINNED_COMMITS["sdk"],
                       "upstreamTagObject":"b161a0475479bbe7d9d693bc496c6fdd90c3969b"}}

    def test_explicit_inline_version_cli_and_prior_selection_identities_stay_separate(self):
        expected={native.VERSION:"verified-v1",native.PREPARED_MIGRATION_VERSION:"verified-prepared-v1",
                  native.PREPARED_INLINE_FILE_VERSION:"verified-prepared-inline-v1"}
        for version,mode in expected.items():
            value=self.manifest(version);before=copy.deepcopy(value)
            self.assertEqual(native.native_selection(value),mode);self.assertEqual(value,before)
        self.assertEqual(native.native_selection({}),"verified-v1")
        result=subprocess.run([sys.executable,"-B",str(NATIVE),"--manifest",str(ROOT/contract.MANIFEST),"version"],
                              capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,contract.VERSION+"\n")
        for version in (contract.VERSION+" ",contract.VERSION.upper(),None,False,1,[],{}):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):native.native_selection(self.manifest(version))

    def test_inline_and_both_prior_binary_versions_cannot_cross_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=root/"source.json";artifact=root/"artifact";artifact.mkdir()
            for left,right in ((native.VERSION,contract.VERSION),(native.PREPARED_MIGRATION_VERSION,contract.VERSION),
                               (contract.VERSION,native.VERSION),(contract.VERSION,native.PREPARED_MIGRATION_VERSION)):
                with self.subTest(manifest=left,binary=right):
                    manifest.write_text(json.dumps(self.manifest(left)))
                    (artifact/"native-artifact.json").write_text(json.dumps({"schemaVersion":1,"version":right}))
                    with patch.object(native,"validate_artifact_source",side_effect=AssertionError("foreign binary reached source admission")):
                        with self.assertRaisesRegex(ValueError,"Unrecognized native artifact"):
                            native.install(SimpleNamespace(manifest=manifest,artifact=artifact,producer_commit=None))
            self.assertFalse((root/"Vendor").exists())


if __name__=="__main__":
    unittest.main()
