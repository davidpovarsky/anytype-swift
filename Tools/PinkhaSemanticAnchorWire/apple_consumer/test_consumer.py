"""Focused new controller controls; no Apple, native, or prior product test."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import consumer_contract as proof

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import early_build_products

BINDING = dict(sourceSHA="a" * 40, runID="45100000000", runAttempt="1", nonce="b" * 32)
UDID = "67621AE7-2788-4A27-B350-21D9C1D4C4E5"


def encoded(value):
    return base64.b64encode(value).decode("ascii")


def integer(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def field(number, value):
    if isinstance(value, int): return integer(number * 8) + integer(value)
    return integer(number * 8 + 2) + integer(len(value)) + value


def native_marks(values):
    result = b""
    for value in values:
        extent = (field(1, value["from"]) if value["from"] else b"") + field(2, value["to"])
        mark = field(1, extent) + field(2, value["kind"])
        if value["param"]: mark += field(3, value["param"].encode("utf8"))
        result += field(1, mark)
    return result


def native_block(raw_marks, *, extra=b"", body=None):
    text = field(1, (body or proof.BODY).encode("utf8")) + field(3, raw_marks)
    return field(1, b"native-block") + field(3, b"") + extra + field(14, text)


def observation():
    owner = dict(accountID="actual-account", spaceID="actual-space", objectID="actual-object",
                 blockID="native-block", anchorID="12345678-1234-4234-8234-123456789abc",
                 ownerGeneration="abcdefab-cdef-4abc-8abc-abcdefabcdef")
    component = lambda text: base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    marker = "pinkha-anchor://v1/" + component(owner["spaceID"]) + "/" + component(owner["objectID"]) + "/" + owner["anchorID"]
    before = [dict(from_=0, to=4, kind=3, param="")]
    after = before + [dict(from_=5, to=15, kind=5, param=marker)]
    before = [{"from": row["from_"], **{key: value for key, value in row.items() if key != "from_"}} for row in before]
    after = [{"from": row["from_"], **{key: value for key, value in row.items() if key != "from_"}} for row in after]
    before_bytes, after_bytes = native_marks(before), native_marks(after)
    digest = lambda marks: hashlib.sha256(json.dumps({"text": proof.BODY, "marks": marks},
        ensure_ascii=False, separators=(",", ":")).encode("utf8")).hexdigest()
    receipt = dict(version=1, **{key: owner[key] for key in ("spaceID", "objectID", "blockID", "anchorID")},
                   marker=marker, changeID="actual-native-change", nativeChangeSHA256="c" * 64,
                   beforeTextMarksSHA256=digest(before), afterTextMarksSHA256=digest(after))
    return {
        "protocol": proof.PROTOCOL, "status": proof.PASS, "binding": copy.deepcopy(BINDING),
        "runtime": dict(version=proof.VERSION, manifestSHA256=proof.MANIFEST_SHA,
                        producerRunID=proof.PRODUCER_RUN, processID=12345),
        "identity": owner,
        "selection": dict(location=5, length=10, textUTF8Base64=encoded(proof.BODY.encode("utf8")),
                          selectedUTF8Base64=encoded(proof.SELECTED.encode("utf8"))),
        "native": dict(beforeBlockBase64=encoded(native_block(before_bytes)),
                       afterBlockBase64=encoded(native_block(after_bytes)), receipt=receipt),
        "document": dict(spaceID=owner["spaceID"], objectID=owner["objectID"],
                         beforeTextUTF8Base64=encoded(proof.BODY.encode("utf8")),
                         afterTextUTF8Base64=encoded(proof.BODY.encode("utf8")),
                         beforeMarksBase64=encoded(before_bytes), afterMarksBase64=encoded(after_bytes)),
        "publication": dict(handler="InvocationMesagesHandler", serviceApplyCalls=1,
                            ownerGeneration=owner["ownerGeneration"],
                            documentObservedBeforeIndependentReadback=True),
        "cleanup": {key: True for key in ("documentClosed", "accountStopped", "accountNotRunning",
                                          "leaseRetired", "appShutdown")},
        "limits": copy.deepcopy(proof.LIMITS),
    }


def actual_results():
    device = dict(deviceId=UDID, architecture="arm64", platform="iOS Simulator",
                  osVersion="27.0", osBuildNumber="24A434")
    summary = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                   result="Passed", devicesAndConfigurations=[dict(device=device)])
    tree = dict(testNodes=[dict(nodeType="Test Case", nodeIdentifier=proof.SUITE + "/" + proof.METHOD + "()",
                               result="Passed")])
    return summary, tree


class ConsumerControls(unittest.TestCase):
    def test_original_protobuf_marks_and_document_bytes_form_one_scoped_observation(self):
        value = observation()
        result = proof.observation(value, BINDING)
        self.assertEqual(result["status"], proof.PASS)
        self.assertEqual(result["limits"], proof.LIMITS)
        self.assertEqual(len(proof.BODY.encode("utf-16-le")) // 2, 19)
        self.assertEqual(proof.BODY.encode("utf-16-le")[10:30].decode("utf-16-le"), proof.SELECTED)

    def test_replayed_source_run_attempt_and_nonce_are_rejected(self):
        for key, changed in (("sourceSHA", "d" * 40), ("runID", "45100000001"),
                             ("runAttempt", "2"), ("nonce", "e" * 32)):
            value = observation(); value["binding"][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.observation(value, BINDING)

    def test_changed_unicode_native_nonmark_bytes_and_document_bytes_are_rejected(self):
        for section, key, changed in (
            ("selection", "textUTF8Base64", encoded(proof.BODY.replace("e\u0301", "\u00e9").encode("utf8"))),
            ("document", "afterMarksBase64", observation()["document"]["beforeMarksBase64"]),
            ("native", "afterBlockBase64", encoded(native_block(
                proof.decode64(observation()["document"]["afterMarksBase64"]), extra=field(5, b"changed")))),
        ):
            value = observation(); value[section][key] = changed
            with self.subTest(section=section), self.assertRaises(ValueError):
                proof.observation(value, BINDING)

    def test_receipt_carrier_marker_digest_and_actual_generation_must_agree(self):
        for key, changed in (("spaceID", "other-space"), ("blockID", "other-block"),
                             ("marker", "pinkha-anchor://v1/unrelated"), ("afterTextMarksSHA256", "e" * 64)):
            value = observation(); value["native"]["receipt"][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.observation(value, BINDING)
        value = observation()
        value["publication"]["ownerGeneration"] = "00000000-0000-4000-8000-000000000000"
        with self.assertRaises(ValueError): proof.observation(value, BINDING)

    def test_extra_capture_incomplete_cleanup_and_broadened_acceptance_are_rejected(self):
        for section, key, changed in (("publication", "serviceApplyCalls", 2),
                                     ("publication", "serviceApplyCalls", True),
                                     ("publication", "documentObservedBeforeIndependentReadback", 1),
                                     ("cleanup", "leaseRetired", False),
                                     ("limits", "mountedEditorAcceptance", "PASS")):
            value = observation(); value[section][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.observation(value, BINDING)

    def test_unknown_fields_malformed_protobuf_and_oversized_observation_rejected(self):
        values = []
        value = observation(); value["unexpected"] = "unreviewed"; values.append(value)
        value = observation(); value["native"]["beforeBlockBase64"] = encoded(b"\x80"); values.append(value)
        value = observation(); value["identity"]["accountID"] = "x" * 66000; values.append(value)
        for value in values:
            with self.assertRaises(ValueError): proof.observation(value, BINDING)

    def test_actual_one_named_xctest_and_owned_destination_required(self):
        summary, tree = actual_results()
        self.assertEqual(proof.exact_execution(summary, tree, UDID)["counts"]["passedTests"], 1)
        for changes in ({"totalTestCount": 0, "passedTests": 0}, {"failedTests": 1},
                        {"skippedTests": 1}, {"passedTests": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                proof.exact_execution(summary | changes, tree, UDID)
        wrong = copy.deepcopy(tree); wrong["testNodes"][0]["nodeIdentifier"] = "Other/test()"
        with self.assertRaises(ValueError): proof.exact_execution(summary, wrong, UDID)
        duplicate = copy.deepcopy(tree); duplicate["testNodes"] *= 2
        with self.assertRaises(ValueError): proof.exact_execution(summary, duplicate, UDID)
        with self.assertRaises(ValueError):
            proof.exact_execution(summary, tree, "00000000-0000-4000-8000-000000000000")

    def test_descriptor_binding_preserves_original_xcode_injection_and_previous_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = root / "original.xctestrun"; copied = root / "bound.xctestrun"
            target = dict(BlueprintName="AnytypeTests", IsEnabled=True, TestHostPath="__TESTROOT__/Anytype.app",
                EnvironmentVariables={"original": "value"}, TestingEnvironmentVariables={"DYLD_INSERT_LIBRARIES": "original"},
                OnlyTestIdentifiers=[], SkipTestIdentifiers=["Existing/skip()"], CommandLineArguments=["--original"])
            value = {"__xctestrun_metadata__": {"FormatVersion": 2},
                     "TestConfigurations": [{"Name": "Original", "TestTargets": [target, {"BlueprintName": "Other"}]}]}
            original.write_bytes(plistlib.dumps(value)); before = original.read_bytes()
            result = proof.copied_descriptor(original, copied, BINDING)
            after = plistlib.loads(copied.read_bytes())["TestConfigurations"][0]["TestTargets"]
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(len(after), 1)
            self.assertEqual(after[0]["TestingEnvironmentVariables"], target["TestingEnvironmentVariables"])
            self.assertEqual(after[0]["SkipTestIdentifiers"], target["SkipTestIdentifiers"])
            self.assertEqual(after[0]["CommandLineArguments"], target["CommandLineArguments"])
            self.assertEqual(after[0]["EnvironmentVariables"]["original"], "value")
            self.assertEqual(after[0]["OnlyTestIdentifiers"], [proof.SUITE + "/" + proof.METHOD])
            self.assertTrue(result["testing_environment_unchanged"])
            with self.assertRaises(ValueError): proof.copied_descriptor(copied, root / "replayed.xctestrun", BINDING)

    def test_attachment_requires_actual_named_test_owned_device_and_safe_single_original_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "original.json").write_text(json.dumps(observation()))
            item = dict(suggestedHumanReadableName=proof.ATTACHMENT + "_0_test.json",
                        exportedFileName="original.json", deviceId=UDID, isAssociatedWithFailure=False)
            manifest = [dict(testIdentifier=proof.SUITE + "/" + proof.METHOD + "()", attachments=[item])]
            (root / "manifest.json").write_text(json.dumps(manifest))
            self.assertEqual(proof.attachment(root, UDID), root / "original.json")
            for patch_value in ({"exportedFileName": "../outside.json"}, {"deviceId": "another"},
                                {"isAssociatedWithFailure": True}):
                changed = copy.deepcopy(manifest); changed[0]["attachments"][0].update(patch_value)
                (root / "manifest.json").write_text(json.dumps(changed))
                with self.assertRaises(ValueError): proof.attachment(root, UDID)
            changed = copy.deepcopy(manifest); changed[0]["attachments"] *= 2
            (root / "manifest.json").write_text(json.dumps(changed))
            with self.assertRaises(ValueError): proof.attachment(root, UDID)

    def test_changed_or_replayed_producer_api_identity_is_rejected(self):
        actual = dict(id=int(proof.PRODUCER_RUN), run_attempt=1, head_sha=proof.PRODUCER_SHA,
                      event="workflow_dispatch", status="completed", conclusion="success",
                      repository={"full_name": proof.REPOSITORY}, path=".github/workflows/torah-inspector-ipados27.yml")
        proof.api_run(actual)
        for change in ({"head_sha": "0" * 40}, {"id": 1}, {"run_attempt": 2}, {"conclusion": "failure"}):
            with self.assertRaises(ValueError): proof.api_run(actual | change)
        expected = proof.ARTIFACTS["runtime"]
        artifact = dict(id=expected["id"], name=expected["name"], size_in_bytes=expected["bytes"],
                        digest="sha256:" + expected["sha256"], expired=False,
                        workflow_run=dict(id=int(proof.PRODUCER_RUN), head_sha=proof.PRODUCER_SHA))
        proof.api_artifact(artifact, "runtime")
        with self.assertRaises(ValueError): proof.api_artifact(artifact | {"digest": "sha256:" + "0" * 64}, "runtime")

    def test_installed_framework_extra_or_changed_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "Lib").write_bytes(b"original")
            expected = {"Lib": proof.digest(root / "Lib")}
            proof.framework_unchanged(root, expected)
            (root / "Lib").write_bytes(b"changed")
            with self.assertRaises(ValueError): proof.framework_unchanged(root, expected)
            (root / "Lib").write_bytes(b"original"); (root / "unreviewed").write_bytes(b"extra")
            with self.assertRaises(ValueError): proof.framework_unchanged(root, expected)

    def test_exact_semantic_scope_preserves_original_products_before_admission_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); derived = root / "derived"; products = derived / "Build/Products"
            products.mkdir(parents=True)
            (products / "Anytype").write_bytes(b"actual executable control"); (products / "Anytype").chmod(0o755)
            (products / "original.xctestrun").write_bytes(b"original configuration control")
            receipt = early_build_products.capture(derived, root / "evidence", source_sha=BINDING["sourceSHA"],
                run_id=BINDING["runID"], run_attempt="1", build_flags=["candidate-only"], scope="semantic-page154")
            archive = root / "evidence/semantic-page154-early-products/BuildProducts.tar.gz"
            with tarfile.open(archive) as packed:
                self.assertEqual(packed.extractfile("Build/Products/Anytype").read(), b"actual executable control")
                self.assertEqual(packed.extractfile("Build/Products/original.xctestrun").read(), b"original configuration control")
            self.assertEqual(receipt["capture_phase"], "AFTER_BUILD_BEFORE_ADMISSION")
            self.assertFalse(receipt["build_reuse_enabled"])
            with self.assertRaises(ValueError):
                early_build_products.capture(derived, root / "bad", source_sha=BINDING["sourceSHA"],
                    run_id=BINDING["runID"], run_attempt="1", build_flags=[], scope="arbitrary-archive")


if __name__ == "__main__":
    unittest.main()
