"""Controller controls. Synthetic records are never native/Apple acceptance."""
import copy
import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

import type_preservation as gate

UDID = "11111111-1111-1111-1111-111111111111"
BINDING = gate.binding("a" * 40, "12345", "1", "b" * 32)


def linux_control_identity(path):
    """Use real directory dev/inode; a fixed birthtime substitutes macOS only."""
    info = path.stat()
    return {"path": str(path.resolve()), "device": str(info.st_dev), "inode": str(info.st_ino), "createdAt": 1_700_000_000.0}


def fixture():
    return {"spaceId": "space", "typeSwitch": {"objectId": "subject", "spaceId": "space", "initialTypeId": "chiddush"},
            "documents": {"chiddush": "writing1", "article": "writing2", "research": "writing3"},
            "universalDocuments": {"page": "blank1", "note": "blank2", "custom": "blank3"},
            "universalTypes": {"page": "page"}, "sourceHeaderCases": [{"objectId": "header" + str(x)} for x in range(4)],
            "setId": "set1", "universalSetId": "set2"}


def baseline(directories):
    records = [{"spaceId": "space", "objectId": "subject", "item": {
        "id": "association-" + kind, "kind": kind, "role": "context", "providerID": "sefaria", "canonicalKey": key,
        "externalID": key, "labelHe": key, "createdAt": "2026-11-18T21:00:00.000Z"}}
        for kind, key in (("ref", "Genesis 3:1"), ("topic", "creation"), ("word", "בראשית"))]
    raw = json.dumps({"version": 2, "records": records}, ensure_ascii=False)
    def row(oid, typ, tags, links, backlinks, seeded):
        return {"objectID": oid, "spaceID": "space", "typeID": typ, "tags": tags,
                "links": sorted(links), "backlinks": sorted(backlinks), "seededLinks": seeded}
    objects = [row("subject", "chiddush", ["native-tag"], ["outgoing", "other-retained-link"], ["incoming"],
                   [{"blockID": "out-block", "targetID": "outgoing"}]),
               row("outgoing", "page", [], [], ["subject", "other-retained-backlink"], []),
               row("incoming", "page", [], ["subject"], [], [{"blockID": "in-block", "targetID": "subject"}])]
    return {"schemaVersion": 1, "binding": BINDING, "preparationPID": 101, "state": {
        "accountID": "original-account", "spaceID": "space", "subjectID": "subject", "chiddushTypeID": "chiddush",
        "canonicalPropertyKey": "canonical-key", "canonicalRaw": raw, "canonicalSHA256": gate.sha256(raw.encode()),
        **directories, "objects": objects, "tagOption": {"objectID": "native-tag", "spaceID": "space",
            "name": "Original native Type-preservation Tag", "relationKey": "tag", "color": "red"}}}


def result():
    return {"status": "PASS", "command_exit_code": 0, "passed": 1, "failed": 0, "skipped": 0,
            "selected": [gate.METHOD], "actual_methods": {gate.METHOD + "()": "Passed"},
            "actual_devices": [{"deviceId": UDID, "architecture": "arm64", "osVersion": "27.0"}]}


def native_receipt(original, original_sha):
    return {"schemaVersion": 1, "status": "PASS", "scope": "FINAL_UI_TYPE_ROUNDTRIP", "binding": original["binding"],
            "baselineSHA256": original_sha, "preparationPID": original["preparationPID"], "postflightPID": 202,
            "verifierCallsMutationAPI": False, "state": copy.deepcopy(original["state"])}


class PreservationControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.container = self.root / UDID / "data"
        self.support = self.container / "Library/Application Support"
        (self.support / "Anytype/middleware-go").mkdir(parents=True)
        self.evidence = self.root / "evidence"; self.evidence.mkdir()
        self.patch = patch.object(gate, "directory_identity", side_effect=linux_control_identity)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.directories = {"container": linux_control_identity(self.container),
                            "middleware": linux_control_identity(self.support / "Anytype/middleware-go")}
        self.original = baseline(self.directories)
        self.raw = json.dumps(self.original, ensure_ascii=False).encode()
        (self.support / gate.BASELINE).write_bytes(self.raw)

    def freeze(self):
        return gate.freeze(self.container, self.evidence, BINDING, fixture(), UDID)

    def test_real_original_bytes_are_frozen_outside_mutable_container(self):
        frozen = self.freeze()
        self.assertEqual(frozen.path.read_bytes(), self.raw)
        self.assertFalse(frozen.path.is_relative_to(self.container))
        # Changing the mutable handoff must never redefine postflight expectations.
        (self.support / gate.BASELINE).write_bytes(b'{"foreign":true}')
        env = gate.environment(frozen)
        self.assertEqual(gate.base64.b64decode(env["PINKHA_TYPE_PRESERVATION_BASELINE_BASE64"]), self.raw)
        self.assertEqual(env["PINKHA_TYPE_PRESERVATION_BASELINE_SHA256"], gate.sha256(self.raw))

    def test_mutated_external_baseline_or_recreated_store_fails(self):
        frozen = self.freeze()
        frozen.path.write_bytes(self.raw + b" ")
        with self.assertRaisesRegex(ValueError, "baseline bytes changed"):
            gate.environment(frozen)
        frozen.path.write_bytes(self.raw)
        middleware = self.support / "Anytype/middleware-go"
        middleware.rename(middleware.with_name("old-owned-control-store"))
        middleware.mkdir()
        with self.assertRaisesRegex(ValueError, "recreated or replaced"):
            gate.verify_frozen(frozen)

    def test_full_native_sets_and_original_canonical_bytes_are_required(self):
        frozen = self.freeze()
        receipt = native_receipt(frozen.value, frozen.sha256)
        self.assertEqual(gate.validate_result(frozen, receipt, result())["native_postflight_methods"], 1)
        changes = [
            lambda x: x["state"].update(accountID="other-account"),
            lambda x: x["state"].update(canonicalRaw=x["state"]["canonicalRaw"] + " "),
            lambda x: x["state"].update(canonicalSHA256="c" * 64),
            lambda x: x["state"]["objects"][0].update(tags=[]),
            lambda x: x["state"]["objects"][0].update(links=["outgoing"]),
            lambda x: x["state"]["objects"][1].update(backlinks=["subject"]),
            lambda x: x["state"]["objects"][0]["seededLinks"][0].update(blockID="recreated-block"),
            lambda x: x["state"]["objects"][2]["seededLinks"][0].update(targetID="foreign"),
            lambda x: x["state"]["middleware"].update(inode="99999"),
            lambda x: x["state"]["container"].update(createdAt=1_700_000_001.0),
            lambda x: x.update(postflightPID=101),
            lambda x: x.update(baselineSHA256="d" * 64),
            lambda x: x["binding"].update(nonce="e" * 32),
            lambda x: x.update(verifierCallsMutationAPI=True),
        ]
        for change in changes:
            bad = copy.deepcopy(receipt); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_result(frozen, bad, result())

    def test_stale_foreign_or_unproved_baseline_is_rejected_before_ui(self):
        changes = [
            lambda x: x["binding"].update(runID="99999"),
            lambda x: x["state"].update(subjectID="another-object"),
            lambda x: x["state"].update(accountID=""),
            lambda x: x["state"]["objects"][1].update(objectID="blank1"),
            lambda x: x["state"]["objects"][0].update(links=[]),
            lambda x: x["state"]["objects"][1].update(backlinks=[]),
            lambda x: x["state"]["objects"][0].update(tags=[]),
            lambda x: x["state"]["tagOption"].update(relationKey="other-property"),
            lambda x: x["state"]["objects"][2]["seededLinks"][0].update(targetID="other"),
            lambda x: x["state"]["middleware"].update(path="/other-store"),
        ]
        for change in changes:
            bad = copy.deepcopy(self.original); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_baseline(bad, BINDING, fixture(), self.directories)

    def test_canonical_raw_v1_missing_identity_or_timestamps_cannot_be_lifted(self):
        changes = [lambda x: x.update(version=1),
                   lambda x: x["records"][0]["item"].pop("createdAt"),
                   lambda x: x["records"][0]["item"].update(createdAt="invalidZ"),
                   lambda x: x["records"][0]["item"].update(id=""),
                   lambda x: x["records"][0].update(blockId="unapproved-block-scope"),
                   lambda x: x["records"][0].update(spaceId="foreign-space")]
        for change in changes:
            bad = copy.deepcopy(self.original); canonical = json.loads(bad["state"]["canonicalRaw"]); change(canonical)
            raw = json.dumps(canonical); bad["state"].update(canonicalRaw=raw, canonicalSHA256=gate.sha256(raw.encode()))
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_baseline(bad, BINDING, fixture(), self.directories)

    def test_native_missing_skipped_extra_or_foreign_results_fail(self):
        frozen = self.freeze(); receipt = native_receipt(frozen.value, frozen.sha256)
        changes = [lambda x: x.update(status="NOT_RUN"), lambda x: x.update(command_exit_code=1),
                   lambda x: x.update(passed=True), lambda x: x.update(skipped=1),
                   lambda x: x.update(actual_methods={gate.METHOD: "Skipped"}),
                   lambda x: x["actual_methods"].update({"Preparation/createWallet": "Passed"}),
                   lambda x: x["actual_methods"].update({gate.METHOD: "Passed"}),
                   lambda x: x["actual_devices"][0].update(deviceId="foreign"),
                   lambda x: x["actual_devices"][0].update(osVersion="26.0")]
        for change in changes:
            bad = copy.deepcopy(result()); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_result(frozen, receipt, bad)

    def test_postflight_copy_clears_preparation_and_stays_beside_products(self):
        frozen = self.freeze(); env = gate.environment(frozen)
        products = self.root / "Products"; products.mkdir()
        original = products / "native.xctestrun"
        target = {"BlueprintName": "AnytypeTests", "TestBundlePath": "__TESTROOT__/AnytypeTests.xctest",
                  "TestHostPath": "__TESTROOT__/Anytype.app/Anytype", "CommandLineArguments": [],
                  "OnlyTestIdentifiers": ["TorahNativeDerivedProductIntegrationTests"],
                  "SkipTestIdentifiers": [gate.METHOD], "EnvironmentVariables": {
                      "PINKHA_NATIVE_DERIVED_ACCEPTANCE": "1", "PINKHA_UNEXPECTED_PREP": "1", "XCODE_REQUIRED": "kept"}}
        raw = plistlib.dumps({"TestConfigurations": [{"TestTargets": [target]}]}); original.write_bytes(raw)
        with patch.dict(os.environ, {"PINKHA_T5_APPLE_PAIR": "1", "SIMCTL_CHILD_PINKHA_OTHER": "1"}):
            selected = gate.selected_configuration(original, env)
        self.assertEqual(selected.parent, products); self.assertEqual(original.read_bytes(), raw)
        observed = plistlib.loads(selected.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
        self.assertEqual(observed["OnlyTestIdentifiers"], [gate.METHOD]); self.assertEqual(observed["SkipTestIdentifiers"], [])
        self.assertEqual(observed["TestHostPath"], target["TestHostPath"])
        self.assertEqual(observed["EnvironmentVariables"]["PINKHA_UNEXPECTED_PREP"], "0")
        self.assertEqual(observed["EnvironmentVariables"]["SIMCTL_CHILD_PINKHA_OTHER"], "0")
        self.assertEqual(observed["EnvironmentVariables"]["XCODE_REQUIRED"], "kept")
        self.assertTrue(all(observed["EnvironmentVariables"][k] == "0" for k in gate.DISABLED_FLAGS))

    def test_inherited_launch_injection_or_enabled_preparation_is_rejected(self):
        frozen = self.freeze(); env = gate.environment(frozen)
        with self.assertRaisesRegex(ValueError, "injection argument"):
            gate.configure_target({"CommandLineArguments": ["PINKHA_NATIVE_DERIVED_ACCEPTANCE=1"]}, env)
        env["PINKHA_NATIVE_DERIVED_ACCEPTANCE"] = "1"
        with self.assertRaisesRegex(ValueError, "not disabled"):
            gate.configure_target({}, env)

    def test_failed_missing_or_extra_ui_prevents_postflight_admission(self):
        methods = ["PinkhaNativeDerivedAcceptanceUITests/testRemainingNativeSourceFilterEditing",
                   "PinkhaNativeDerivedAcceptanceUITests/testRemainingUniversalTypePickersAndMixedSet"]
        passing = {"status": "PASS", "command_exit_code": 0, "passed": 2, "failed": 0, "skipped": 0,
                   "actual_methods": {x: "Passed" for x in methods}}
        gate.require_ui_passed(passing, methods)
        for change in (lambda x: x.update(status="FAIL"), lambda x: x.update(passed=1),
                       lambda x: x.update(skipped=1), lambda x: x.update(command_exit_code=65),
                       lambda x: x["actual_methods"].update({methods[0]: "Failed"}),
                       lambda x: x["actual_methods"].update({"Unexpected/test": "Passed"})):
            bad = copy.deepcopy(passing); change(bad)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "before native postflight"):
                gate.require_ui_passed(bad, methods)

    def test_saved_qualification_requires_original_receipt_and_binding(self):
        frozen = self.freeze(); receipt = native_receipt(frozen.value, frozen.sha256)
        (self.evidence / "postflight").mkdir()
        raw = json.dumps(receipt).encode(); (self.evidence / "postflight/native-result.json").write_bytes(raw)
        (self.evidence / "fixture-ids.json").write_text(json.dumps(fixture()))
        (self.evidence / "type-preservation-inputs.json").write_text(json.dumps({
            "binding": BINDING, "baseline_sha256": frozen.sha256, "directories": self.directories,
            "container": str(self.container), "simulator_udid": UDID, "source": "FROZEN_BEFORE_UI"}))
        execution = {"source_sha": BINDING["sourceSHA"], "run_id": BINDING["runID"], "run_attempt": BINDING["runAttempt"],
                     "postflight_binding": BINDING, "preservation_baseline_sha256": frozen.sha256,
                     "preservation_native_receipt_sha256": gate.sha256(raw), "postflight": result(),
                     "type_preservation": gate.validate_result(frozen, receipt, result())}
        self.assertEqual(gate.validate_saved(self.evidence, execution, UDID)["status"], "PASS")
        execution["run_id"] = "99999"
        with self.assertRaisesRegex(ValueError, "execution binding"):
            gate.validate_saved(self.evidence, execution, UDID)
        execution["run_id"] = BINDING["runID"]
        (self.evidence / "postflight/native-result.json").write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            gate.validate_saved(self.evidence, execution, UDID)


if __name__ == "__main__":
    unittest.main()
