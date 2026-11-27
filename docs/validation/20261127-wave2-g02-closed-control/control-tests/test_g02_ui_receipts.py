"""Portable synthetic receipt controls only; no App/native/XCTest execution."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "patch/Tools/CurrentAppleValidation/combined_heart_semantics/wave2"))
import g02_ui_receipts as g
import torah_ui_profile as original


class Common:
    @staticmethod
    def require(value, reason):
        if not value: raise ValueError(reason)

    @staticmethod
    def sha(value): return hashlib.sha256(value).hexdigest()

    @staticmethod
    def decode(value): return json.loads(value)

    @staticmethod
    def raw(path, maximum=64 * 1024**2):
        value = Path(path).read_bytes()
        Common.require(len(value) <= maximum, "oversized portable fixture")
        return value


C = Common()
UDID = "11111111-2222-3333-4444-555555555555"
TOKEN = "12345678" * 4


def encode(value): return json.dumps(value, ensure_ascii=False, sort_keys=True).encode()


def fixture():
    return {"spaceId": "synthetic-space", "documents": {r: "object-" + r for r in g.ROLES},
            "types": {r: "type-" + r for r in g.ROLES},
            "names": {"object-" + r: "Synthetic " + r for r in g.ROLES},
            "typeSwitch": {"types": {r: {"id": "type-" + r, "label": "Type " + r, "propertyName": "Type"} for r in g.ROLES}},
            "nativeProperties": [g.SOURCE_PROPERTY, g.TOPIC_PROPERTY, g.WORD_PROPERTY],
            "sourceLabel": "Genesis 1:1", "topicLabel": "Creation"}


def bound():
    f = fixture()
    raw = json.dumps(f, ensure_ascii=False, indent=2).encode() + b"\n"
    binding = {"sourceSHA": "a" * 40, "runID": "123", "runAttempt": "1", "nonce": TOKEN}
    preparation = original.LANES["properties"]["preparation"]
    admission = {"schema": "pinkha-combined-host-acceptance-admission-v1", "executionEnvironment": "SentinelX-owned-Mac",
                 "sourceCommit": binding["sourceSHA"], "appLanguage": "en", "deviceType": "synthetic-ipad", "deviceFamily": "ipad"}
    invocation = {"binding": binding, "argv": ["platform=iOS Simulator,id=" + UDID,
                  "-only-testing:AnytypeTests/" + preparation + "()"]}
    prepared = {"status": "PASS", "testInvoked": True, "selected": [preparation], "command_exit_code": 0,
                "passed": 1, "failed": 0, "skipped": 0, "actual_devices": [{"deviceId": UDID, "platform": "iOS Simulator"}],
                "installedOriginalCode": {"codeCarriersSHA256": "b" * 64}}
    owned = {"udid": UDID, "name": "F-Combined-" + TOKEN + "-properties", "deviceType": "synthetic-ipad", "deviceFamily": "ipad"}
    environment = {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_NATIVE_UI_FIXTURE_JSON": json.dumps(f),
                   "PINKHA_UI27_APP_LANGUAGE": "en", "PINKHA_UI27_SELECTION_SCOPE": "WAVE15_ACCEPTANCE"}
    env = original.startup_environment(lane="properties", fixture_raw=raw, ui_environment=environment,
              preparation_raw=encode(prepared), invocation_raw=encode(invocation), admission_raw=encode(admission),
              owned_simulator_raw=encode(owned), binding=binding, udid=UDID, token=TOKEN, code_carriers_sha256="b" * 64)
    actual, controller = g.fixture_binding(C, raw, env, UDID)
    return actual, controller, raw, env


def rows(f, role, word):
    return {g.SOURCE_PROPERTY: f["sourceLabel"], g.TOPIC_PROPERTY: f["topicLabel"], g.WORD_PROPERTY: word,
            "Tags": "G02 " + role + " " + TOKEN[:8], "Type": "Type " + role}


def record(f, controller, phase, **fields):
    return dict(fields, schema="pinkha-g02-word-ui-observation-v1", phase=phase, spaceID=f["spaceId"],
                controller=controller, evidenceScope=g.EVIDENCE_SCOPE, controllerProvenance=g.PROVENANCE,
                observedAtUTC="2026-11-27T06:00:00Z")


def seed(f, controller):
    docs, records = {}, {}
    for i, role in enumerate(g.ROLES):
        docs[role] = dict(objectID=f["documents"][role], typeID=f["types"][role], name=f["names"][f["documents"][role]],
                          sourceLabel=f["sourceLabel"], topicLabel=f["topicLabel"], wordLabel="בראשית",
                          sourceAction="LINKED_THROUGH_ORIGINAL_PICKER", topicAction="OBSERVED_EXISTING_SOLE_SELECTION",
                          wordAction="LINKED_THROUGH_ORIGINAL_PICKER", tagPropertyName="Tags", tagName="G02 " + role + " " + TOKEN[:8],
                          observedRows=rows(f, role, "בראשית"), appPID=1000+i)
        records["seed-" + role] = record(f, controller, "seed-" + role, role=role, document=docs[role])
    records["seed-complete"] = record(f, controller, "seed-complete", documents=docs, nativeIdentifiersEstablishedByThisUIStage=False)
    return records


def native_baseline(f, controller, seed_raw):
    docs = {}
    for role in g.ROLES:
        docs[role] = dict(objectID=f["documents"][role], typeID=f["types"][role], name=f["names"][f["documents"][role]],
                          sourceLabel=f["sourceLabel"], topicLabel=f["topicLabel"], wordRecordID="record-"+role,
                          wordIdentity="word-identity-"+role, wordLabel="בראשית", tagPropertyName="Tags", tagID="tag-"+role,
                          tagName="G02 " + role + " " + TOKEN[:8])
    return dict(schema="pinkha-g02-word-native-ui-baseline-v1", spaceID=f["spaceId"], controller=controller,
                nativeBaselineSHA256="c" * 64, seedUIReceiptSHA256=C.sha(seed_raw), documents=docs)


def unlink(f, controller, baseline):
    docs, records = {}, {}
    for i, role in enumerate(g.ROLES):
        base = baseline["documents"][role]
        key = "cancel-query-" + role
        records[key] = record(f, controller, key, role=role, query="G02 cancel " + TOKEN[:8],
                              wordRecordIDFromNativeBaseline=base["wordRecordID"], wordIdentityFromNativeBaseline=base["wordIdentity"])
        key = "cancelled-" + role
        records[key] = record(f, controller, key, role=role, observedRows=rows(f, role, base["wordLabel"]),
                              wordRecordIDFromNativeBaseline=base["wordRecordID"], cancelMechanism="DISMISS_CHANGED_QUERY_PICKER_WITHOUT_LINK_OR_UNLINK")
        key = "unlinked-warm-" + role
        records[key] = record(f, controller, key, role=role, wordRecordIDFromNativeBaseline=base["wordRecordID"],
                              wordIdentityFromNativeBaseline=base["wordIdentity"], confirmationDialogExpected=False)
        docs[role] = dict(objectID=base["objectID"], typeID=base["typeID"], name=base["name"],
                          wordRecordIDFromNativeBaseline=base["wordRecordID"], wordIdentityFromNativeBaseline=base["wordIdentity"],
                          tagIDFromNativeBaseline=base["tagID"], observedRows=rows(f, role, g.EMPTY_WORD), previousPID=2000+i, appPID=3000+i)
        key = "cold-reopen-" + role
        records[key] = record(f, controller, key, role=role, document=docs[role])
    records["unlink-complete"] = record(f, controller, "unlink-complete", documents=docs,
               nativeBaselineSHA256=baseline["nativeBaselineSHA256"], seedUIReceiptSHA256=baseline["seedUIReceiptSHA256"],
               nativePersistencePostflightRequired=True)
    return records


def exports(directory, phase, records, baseline_raw=None):
    # Deliberately synthetic bytes. They exercise artifact boundaries, not pixels.
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 10, 20) + b"\x08\x06\0\0\0\0\0\0\0"
    items = []
    for label in (*g.PHASES[phase], phase + "-final"):
        kinds = (".txt", ".png") if label.endswith("-final") else (".json", ".txt", ".png")
        for kind in kinds:
            stem = "word-unlink-" + label + {".txt": "-ax", ".png": "-visual"}.get(kind, "")
            name = str(len(items)) + kind
            value = encode(records[label]) if kind == ".json" else png if kind == ".png" else b"synthetic AX\n"
            (directory / name).write_bytes(value)
            items.append(dict(suggestedHumanReadableName=stem+kind, exportedFileName=name, deviceId=UDID, isAssociatedWithFailure=False))
    if phase == "unlink":
        name = "compact.json"; (directory / name).write_bytes(baseline_raw)
        items.append(dict(suggestedHumanReadableName="word-unlink-native-ui-baseline.json", exportedFileName=name, deviceId=UDID, isAssociatedWithFailure=False))
    manifest = [{"testIdentifier": g.TARGET + "/" + g.METHODS[phase] + "()", "attachments": items}]
    (directory / "manifest.json").write_bytes(encode(manifest))
    return manifest


class PortableControls(unittest.TestCase):
    def test_exact_source_inverse_and_two_allowances(self):
        source = (HERE.parent / "word-unlink-ui/AnytypeComprehensiveAcceptanceUITests.swift").read_bytes()
        proof = (HERE.parent / "word-unlink-ui/source-inverse.json").read_bytes()
        self.assertEqual(g.qualify_source(C, source, proof)["caseCount"], 2)
        with self.assertRaises(ValueError): g.qualify_source(C, source+b"\n", proof)
        for phase, allowance in g.ALLOWANCES.items():
            self.assertEqual(g.ui_time_budget(g.TARGET, [g.METHODS[phase]])["maximum_seconds"], allowance)
        with self.assertRaises(ValueError): g.ui_time_budget(g.TARGET, list(g.METHODS.values()))
        with self.assertRaises(ValueError): g.ui_time_budget(g.TARGET, ["AnytypeComprehensiveAcceptanceUITests/testDocumentSourceSearchPresentation"])

    def test_original_raw_fixture_semantics_and_scope(self):
        f, controller, raw, env = bound()
        self.assertNotEqual(C.sha(raw), C.sha(env["PINKHA_NATIVE_UI_FIXTURE_JSON"].encode()))
        self.assertEqual(g.fixture_binding(C, raw, env, UDID)[0], f)
        with self.assertRaises(ValueError): g.fixture_binding(C, raw, env, "66666666-2222-3333-4444-555555555555")
        wrong = copy.deepcopy(env); wrong["PINKHA_NATIVE_UI_FIXTURE_JSON"] = env["PINKHA_NATIVE_UI_FIXTURE_JSON"].replace("object-article", "other-object")
        with self.assertRaises(ValueError): g.fixture_binding(C, raw, wrong, UDID)

    def test_seed_typed_groups_and_foreign_evidence_rejected(self):
        f, controller, _, _ = bound(); records = seed(f, controller)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp).resolve(); manifest = exports(directory, "seed", records)
            result = g.attachments(C, directory, UDID, "seed", f, controller)
            self.assertEqual(len(result["artifacts"]), 5)
            self.assertFalse(result["nativePersistenceAccepted"])
            wrong = copy.deepcopy(manifest); wrong[0]["attachments"][0]["deviceId"] = "other-device"
            (directory / "manifest.json").write_bytes(encode(wrong))
            with self.assertRaises(ValueError): g.attachments(C, directory, UDID, "seed", f, controller)
            wrong = copy.deepcopy(manifest); wrong[0]["attachments"][0]["isAssociatedWithFailure"] = True
            (directory / "manifest.json").write_bytes(encode(wrong))
            with self.assertRaises(ValueError): g.attachments(C, directory, UDID, "seed", f, controller)
            wrong = copy.deepcopy(manifest); wrong[0]["attachments"].pop()
            (directory / "manifest.json").write_bytes(encode(wrong))
            with self.assertRaises(ValueError): g.attachments(C, directory, UDID, "seed", f, controller)

    def test_unlink_native_identity_cold_process_and_retained_values(self):
        f, controller, _, _ = bound(); seed_raw = encode(seed(f, controller)["seed-complete"])
        baseline = native_baseline(f, controller, seed_raw); baseline_raw = encode(baseline)
        records = unlink(f, controller, baseline)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp).resolve(); exports(directory, "unlink", records, baseline_raw)
            result = g.attachments(C, directory, UDID, "unlink", f, controller, baseline_raw=baseline_raw, seed_sha=C.sha(seed_raw))
            self.assertEqual(len(result["artifacts"]), 15)
            self.assertEqual(result["metadata"]["documents"]["chiddush"]["wordRecordIDFromNativeBaseline"], "record-chiddush")
            with self.assertRaises(ValueError): g.attachments(C, directory, UDID, "unlink", f, controller, baseline_raw=baseline_raw+b" ", seed_sha=C.sha(seed_raw))
        for field, value in (("wordRecordIDFromNativeBaseline", "wrong-word"), ("appPID", 2000)):
            wrong = copy.deepcopy(records)
            wrong["unlink-complete"]["documents"]["chiddush"][field] = value
            with self.assertRaises(ValueError): g.validate_metadata(C, "unlink", wrong, f, controller, baseline=baseline, seed_sha=C.sha(seed_raw))
        wrong = copy.deepcopy(records)
        wrong["cancelled-chiddush"]["observedRows"][g.WORD_PROPERTY] = g.EMPTY_WORD
        with self.assertRaises(ValueError): g.validate_metadata(C, "unlink", wrong, f, controller, baseline=baseline, seed_sha=C.sha(seed_raw))
        wrong = copy.deepcopy(records)
        wrong["unlink-complete"]["documents"]["research"]["observedRows"][g.SOURCE_PROPERTY] = "different Source"
        with self.assertRaises(ValueError): g.validate_metadata(C, "unlink", wrong, f, controller, baseline=baseline, seed_sha=C.sha(seed_raw))


if __name__ == "__main__": unittest.main(verbosity=2)
