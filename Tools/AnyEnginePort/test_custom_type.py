"""New controller controls only. No simulator, native library, or old tests run."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_custom_type as gate
import verify_native_test_execution as execution


SCOPE = "8D7DF152-A257-4A27-9AB7-5644E15FA190"
GENERATION = "F86FB04D-31B1-4D1A-B774-2AE131782727"
COLD_GENERATION = "CA2AE339-7DC0-44BD-A58C-B23907A38198"
UDID = "9E0B04F3-A517-43F5-85C2-671BD4300F2D"


def valid_receipt():
    suffix, token = SCOPE[:8], SCOPE.lower().replace("-", "")
    seed = {
        "contract": gate.CONTRACT, "scopeUUID": SCOPE, "attemptUUID": "42B00D57-AC72-4E42-8D7C-2C45A25FA8EA",
        "accountID": "owned-account", "spaceID": "owned-space", "ownerGeneration": GENERATION,
        "engineStartedAt": "2026-11-22T01:00:00.000Z", "processID": 3001,
        "typeID": "native-custom-type", "typeName": "UI canonical Type " + suffix,
        "typeKey": "ui_custom_type_" + token, "pageTypeName": "Page",
        "propertyID": "native-property", "propertyName": "UI custom value " + suffix,
        "propertyKey": "ui_custom_value_" + token, "canonicalEditorDataset": "editor_blocks",
        "eligible": True, "nativeWrites": 3, "documentWrites": 0, "bodyWrites": 0, "membershipWrites": 0,
    }
    prepare = {"contract": gate.CONTRACT, "phase": "prepare", "seed": copy.deepcopy(seed),
               "nativeWritesThisProcess": 3, "ownerGeneration": GENERATION,
               "engineStartedAt": seed["engineStartedAt"], "processID": 3001}
    audit = {"contract": gate.CONTRACT, "phase": "audit", "seed": copy.deepcopy(seed),
             "nativeWritesThisProcess": 0, "ownerGeneration": COLD_GENERATION,
             "engineStartedAt": "2026-11-22T01:01:40.000Z", "processID": 3011}
    before = ("שלום סוג מסמך מותאם ABC 482 " + suffix).encode()
    after = before + " — נשמר בסוג החדש 739".encode()
    def body(raw):
        return {"nativeBlockID": "native-block", "sha256": gate.sha(raw), "utf8Count": len(raw)}
    value = "ערך משותף " + suffix + " 864"
    return {
        "schemaVersion": 1, "contract": "pinkha-native-custom-type-ui-journey-v1", "method": gate.METHOD,
        "scopeUUID": SCOPE, "documentName": "Custom Type UI Document " + suffix, "objectID": "native-document",
        "initialTypeID": "page", "initialTypeName": "Page", "selectedTypeID": seed["typeID"],
        "selectedTypeName": seed["typeName"], "coldTypeName": seed["typeName"],
        "propertyID": seed["propertyID"], "propertyValue": value, "coldPropertyValue": value,
        "beforeType": body(before), "afterType": body(before), "afterEdit": body(after), "afterCold": body(after),
        "prepare": prepare, "audit": audit, "coldProcessReopen": True, "creationFlagRemoved": True,
        "auditFlagPresent": True, "blockCountBefore": 1, "blockCountAfter": 1,
    }


def named_execution():
    summary = {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0,
               "devicesAndConfigurations": [{"device": {"deviceId": UDID, "osVersion": "27.2",
                    "osBuildNumber": "24C82", "architecture": "arm64"}}]}
    tree = {"nodeType": "Test Case", "nodeIdentifier": gate.METHOD + "()", "result": "Passed"}
    return summary, tree


class NativeCustomTypeGateTests(unittest.TestCase):
    def test_exact_one_receipt_requires_actual_named_success(self):
        result = gate.validate_receipt(valid_receipt())
        self.assertEqual(result["coldFixtureNativeWrites"], 0)
        self.assertTrue(result["freshIOSProcessReopen"])
        summary, tree = named_execution()
        executed = execution.validate(summary, tree, gate.PROFILE, UDID)
        self.assertEqual(executed["observedRequiredMethods"], [gate.METHOD])

    def test_cold_audit_rejects_fixture_writes_and_side_effects(self):
        for change in ("audit_write", "documentWrites", "bodyWrites", "membershipWrites", "boolean_count"):
            receipt = valid_receipt()
            if change == "audit_write":
                receipt["audit"]["nativeWritesThisProcess"] = 1
            elif change == "boolean_count":
                receipt["blockCountAfter"] = True
            else:
                receipt["prepare"]["seed"][change] = 1
                receipt["audit"]["seed"][change] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_receipt(receipt)

    def test_cold_read_requires_original_scope_seed_and_fresh_owner(self):
        for change in ("scope", "seed", "process", "generation", "boot", "creation_flag"):
            receipt = valid_receipt()
            if change == "scope":
                receipt["scopeUUID"] = SCOPE.lower()
            elif change == "seed":
                receipt["audit"]["seed"]["accountID"] = "another-owned-account"
            elif change == "process":
                receipt["audit"]["processID"] = receipt["prepare"]["processID"]
            elif change == "generation":
                receipt["audit"]["ownerGeneration"] = GENERATION
            elif change == "boot":
                receipt["audit"]["engineStartedAt"] = receipt["prepare"]["engineStartedAt"]
            else:
                receipt["creationFlagRemoved"] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_receipt(receipt)

    def test_type_transition_rejects_page_alias_ineligible_or_wrong_property(self):
        for change in ("page", "alias", "ineligible", "dataset", "property"):
            receipt = valid_receipt()
            for observation in (receipt["prepare"], receipt["audit"]):
                if change == "page":
                    observation["seed"]["typeID"] = "page"
                elif change == "alias":
                    observation["seed"]["pageTypeName"] = observation["seed"]["typeName"]
                elif change == "ineligible":
                    observation["seed"]["eligible"] = False
                elif change == "dataset":
                    observation["seed"]["canonicalEditorDataset"] = "another-editor"
            if change == "property":
                receipt["coldPropertyValue"] = "different"
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_receipt(receipt)

    def test_body_and_one_native_block_are_exact_at_every_boundary(self):
        for change in ("body_before", "body_type", "body_edit", "body_cold", "block", "extra_block"):
            receipt = valid_receipt()
            key = {"body_before": "beforeType", "body_type": "afterType",
                   "body_edit": "afterEdit", "body_cold": "afterCold"}.get(change)
            if key:
                receipt[key]["sha256"] = gate.sha(b"wrong bytes")
            elif change == "block":
                receipt["afterCold"]["nativeBlockID"] = "replacement-block"
            else:
                receipt["blockCountAfter"] = 2
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_receipt(receipt)

    def test_named_execution_refuses_missing_extra_failed_skipped_and_wrong_destination(self):
        for change in ("missing", "extra", "failed", "skipped", "wrong_destination"):
            summary, tree = named_execution()
            if change == "missing":
                tree["nodeIdentifier"] = "NativeLaunchTests/testAnotherMethod()"
            elif change == "extra":
                summary["totalTestCount"] = summary["passedTests"] = 2
                tree = [tree, {"nodeType": "Test Case", "nodeIdentifier": "NativeLaunchTests/testAnotherMethod()", "result": "Passed"}]
            elif change == "failed":
                summary.update(passedTests=0, failedTests=1); tree["result"] = "Failed"
            elif change == "skipped":
                summary.update(passedTests=0, skippedTests=1); tree["result"] = "Skipped"
            else:
                summary["devicesAndConfigurations"][0]["device"]["deviceId"] = SCOPE
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                execution.validate(summary, tree, gate.PROFILE, UDID)

    def test_original_attachment_rejects_duplicate_json_and_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            entry = {"suggestedHumanReadableName": gate.ATTACHMENT, "exportedFileName": "receipt.json"}
            manifest = [{"testIdentifier": gate.METHOD + "()", "attachments": [entry]}]
            path = directory / "manifest.json"
            path.write_text(json.dumps(manifest))
            (directory / "receipt.json").write_text(json.dumps(valid_receipt()))
            self.assertEqual(gate.original_receipt(directory)[0]["scopeUUID"], SCOPE)
            (directory / "receipt.json").write_bytes(b'{"schemaVersion":1,"schemaVersion":2}')
            with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
                gate.original_receipt(directory)
            entry["exportedFileName"] = "../receipt.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "unsafe_attachment_basename"):
                gate.original_receipt(directory)
            entry["exportedFileName"] = "receipt.json"
            manifest[0]["attachments"].append(dict(entry))
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "exactly_one_original_ui_receipt"):
                gate.original_receipt(directory)

    def test_source_closure_preserves_original_methods_and_get_only_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in gate.SOURCES:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(gate.ROOT / name, root / name)
            self.assertEqual(len(gate.validate_sources(root)), len(gate.SOURCES))
            test = root / gate.SOURCES[2]
            raw = test.read_bytes()
            test.write_bytes(raw.replace(b"continueAfterFailure = false", b"continueAfterFailure = true", 1))
            with self.assertRaisesRegex(ValueError, "existing_tests_or_helpers_changed"):
                gate.validate_sources(root)
            test.write_bytes(raw)
            fixture = root / gate.SOURCES[1]
            original = fixture.read_text()
            before, audit = original.split("private nonisolated static func audit(", 1)
            fixture.write_text(before + "private nonisolated static func audit(" + audit.replace('method: "GET"', 'method: "POST"', 1))
            with self.assertRaisesRegex(ValueError, "cold_audit_must_be_read_only"):
                gate.validate_sources(root)

    def test_frozen_inventory_detects_changed_code_resources_and_external_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "Native.app"; bundle.mkdir()
            executable = bundle / "Native"; executable.write_bytes(bytes.fromhex("cffaedfe") + b"synthetic-controller-input")
            resource = bundle / "Resource.txt"; resource.write_text("original")
            frozen = gate.inventory(bundle)
            gate.validate_frozen(frozen, gate.inventory(bundle))
            resource.write_text("changed")
            with self.assertRaisesRegex(ValueError, "compiled_products_changed"):
                gate.validate_frozen(frozen, gate.inventory(bundle))
            resource.write_text("original")
            executable.write_bytes(bytes.fromhex("cffaedfe") + b"changed-controller-input")
            with self.assertRaisesRegex(ValueError, "compiled_products_changed"):
                gate.validate_frozen(frozen, gate.inventory(bundle))
            outside = Path(temporary) / "outside"; outside.write_text("external")
            (bundle / "external").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "external_bundle_dependency"):
                gate.inventory(bundle)

    def test_workflow_has_one_new_last_stage_using_same_products(self):
        raw = (gate.ROOT / ".github/workflows/pinkha-any-engine-port.yml").read_text()
        capture = raw.index("id: native-shared-products")
        entry = raw.index("id: native-ui-tests")
        final = raw.index("id: native-custom-type-tests")
        self.assertLess(capture, entry)
        self.assertGreater(final, raw.index("id: archive-roundtrip-postflight"))
        section = raw[final:raw.index("- name: Preserve bounded noncontent", final)]
        self.assertEqual(section.count("xcodebuild test-without-building"), 1)
        self.assertNotIn("build-for-testing", section)
        self.assertEqual(section.count("-only-testing:PinkhaAnyNativeUITests/" + gate.METHOD), 1)
        for expected in ("steps.native-ui-tests.outcome == 'success'", "steps.native-ui-followup-tests.outcome == 'success'",
                         "steps.archive-roundtrip-postflight.outcome == 'success'", "verify_custom_type.py check",
                         "verify_custom_type.py postflight", 'build/any-native-app-derived'):
            self.assertIn(expected, section)
        self.assertIn("-skip-testing:PinkhaAnyNativeUITests/" + gate.METHOD, raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
