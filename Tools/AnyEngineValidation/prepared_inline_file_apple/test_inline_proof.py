"""New synthetic admission controls; these do not execute or qualify a product."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from uuid import UUID

import contract
import proof

BINDING = {"sourceSHA": "1" * 40, "runID": "45099999999", "runAttempt": "1", "nonce": "0123456789abcdef" * 2}
UDID = "12345678-1234-1234-1234-123456789ABC"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return base64.b64encode(value).decode("ascii")


def source_intent(identity, source_key, *, utf8_lengths=True):
    parts = ["pinkha-native-prepared-migration-intent/v1", identity["accountId"], identity["spaceId"],
             identity["storeId"], identity["planId"], source_key, "inlineFile"]
    lengths = [len(item.encode("utf-8")) if utf8_lengths else len(item) for item in parts]
    material = "|".join(str(size) + ":" + item for size, item in zip(lengths, parts))
    return digest(material.encode("utf-8"))


def fixture():
    """Invented controller inputs, never saved as purported Apple observations."""
    runtime = [str(UUID(int=number)).upper() for number in (10, 11, 12)]
    owners = [str(UUID(int=number)).upper() for number in (20, 21, 22)]
    identity = dict(accountId="synthetic-account", spaceId="synthetic-space", storeId="synthetic-store",
                    ownerObjectIds=["synthetic-owner-empty", "synthetic-owner-maximum"],
                    planId=digest(("apple-inline-plan|" + BINDING["nonce"]).encode()),
                    planSHA256=digest(b"inline-file-cases:empty+4095/v1"))
    value = dict(
        schema="pinkha-prepared-inline-file-apple-v1", status="OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED",
        method=contract.METHOD, **BINDING, expectedNativeManifestSHA256=contract.MANIFEST_SHA,
        expectedRuntimeVersion=contract.VERSION, processId=123,
        runtimeVersions=["any " + contract.VERSION + " (synthetic control)"] * 3,
        runtimeGenerations=runtime, ownerGenerations=owners, identity=identity,
        capabilities=dict(contract="pinkha-native-prepared-migration-v1", maximumInlineBytes=4095, networkVerified=False),
        files=[], orderlyReopenCount=2, journeyComplete=True, completedCleanup=True,
        limits=dict(restartKind="orderly-native-sdk-store-same-xctest-process", osProcessCrash="NOT_RUN",
                    lostHTTPAcknowledgement="NOT_INJECTED", networkSynchronization="NOT_RUN",
                    SSEDelivery="NOT_EVALUATED_TRANSIENT", fullSpaceMigration="NOT_PROVEN"))
    for index, label in enumerate(("empty", "maximum")):
        content = b"" if index == 0 else bytes(range(256)) * 15 + bytes(range(255))
        name = "" if index == 0 else "\u05e7\u05d5\u05d1\u05e5 e\u0301 \U0001f9ea.bin"
        mime = "" if index == 0 else "application/octet-stream"
        native_owner = identity["ownerObjectIds"][index]
        source_key = "apple-inline-" + label + "-" + BINDING["nonce"]
        spec = dict(ownerObjectId=native_owner, name=name, mime=mime,
                    content=encoded(content), contentSHA256=digest(content))
        raw = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        row = dict(label=label, sourceKey=source_key, intentId=source_intent(identity, source_key),
                   ownerObjectId=native_owner, specBase64=encoded(raw), specSHA256=digest(raw),
                   expectedSize=len(content), expectedContentSHA256=digest(content),
                   nameUTF8Base64=encoded(name.encode()), mime=mime)
        native_ids = dict(fingerprint=digest(("synthetic-fingerprint-" + label).encode()),
                          payloadObjectId="synthetic-carrier-" + label, changeId="synthetic-change-" + label,
                          fileId="synthetic-file-" + label, recordIds=["synthetic-file-" + label])
        phases = (("prepared", 0, "file-prepared", "prepared"),
                  ("afterPreparedReopen", 1, "file-prepared", "prepared"),
                  ("committed", 1, "complete", "committed"), ("currentStatus", 1, "complete", "committed"),
                  ("retry", 1, "complete", "committed"), ("afterCommittedReopenStatus", 2, "complete", "committed"),
                  ("afterCommittedReopenRetry", 2, "complete", "committed"))
        for phase, generation, stage, outcome in phases:
            row[phase] = dict(copy.deepcopy(native_ids), runtimeGeneration=runtime[generation],
                              ownerGeneration=owners[generation], stage=stage, outcome=outcome)
        metadata = dict(fileId=native_ids["fileId"], objectId=native_owner, size=len(content),
                        inline=True, durable=True, cached=True)
        if name:
            metadata.update(name=name, mime=mime)
        read = dict(metadata=metadata, status=dict(fileId=native_ids["fileId"], objectId=native_owner,
                                                  state="durable", cached=True),
                    content=dict(httpStatus=200, mediaType="application/octet-stream",
                                 byteCount=len(content), sha256=digest(content), base64=encoded(content)))
        for phase, generation in (("currentRead", 1), ("reopenedRead", 2)):
            row[phase] = dict(copy.deepcopy(read), runtimeGeneration=runtime[generation], ownerGeneration=owners[generation])
        value["files"].append(row)
    return value


def actual_summary():
    return dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                devicesAndConfigurations=[dict(device=dict(deviceId=UDID, osVersion="27.0",
                                                           architecture="arm64", osBuildNumber="24A1"))])


class InlineProofControls(unittest.TestCase):
    def rejects(self, value, binding=None):
        with self.assertRaises(ValueError):
            proof.observation(value, BINDING if binding is None else binding)

    def test_qualified_shape_remains_observations_only(self):
        value = fixture()
        admitted = proof.observation(value, BINDING)
        self.assertEqual(admitted["status"], "VALIDATED_OBSERVATIONS_ORIGINAL_XCTEST_REQUIRED")
        self.assertEqual([row["byteCount"] for row in admitted["files"]], [0, 4095])
        self.assertEqual(admitted["receipt_observations"], 14)
        self.assertEqual(admitted["ordinary_content_readbacks"], 4)
        self.assertEqual(admitted["limits"]["networkSynchronization"], "NOT_RUN")
        self.assertEqual(value, fixture(), "Admission may not rewrite original observations")

    def test_frozen_schema_and_runtime_source_are_bound(self):
        root = Path(__file__).resolve().parents[3]
        schema = root / "docs/validation/20261123-prepared-inline-runtime/observation.schema.json"
        self.assertEqual(digest(schema.read_bytes()), proof.SCHEMA_SHA256)
        value = json.loads(schema.read_bytes())
        self.assertEqual(set(value["required"]), proof.TOP_KEYS)
        self.assertEqual(set(value["$defs"]["file"]["required"]), proof.FILE_KEYS)
        test = root / contract.TEST_SOURCE
        self.assertEqual(digest(test.read_bytes()), "ab60925b31502972fad2025476ac3e5b11de9ef3870eb606f7ef002712425b2b")

    def test_replayed_source_run_attempt_or_nonce_is_rejected(self):
        for name, other in (("sourceSHA", "2" * 40), ("runID", "45099999998"),
                            ("runAttempt", "2"), ("nonce", "a" * 32)):
            with self.subTest(field=name):
                value = fixture()
                value[name] = other
                self.rejects(value)
        for change in ({"extra": "not-authorized"}, {"runAttempt": "01"}, {"nonce": "A" * 32}):
            self.rejects(fixture(), dict(BINDING, **change))

    def test_exact_deterministic_bytes_are_required_even_when_all_self_hashes_change(self):
        value = fixture()
        row = value["files"][1]
        original = bytes(range(256)) * 15 + bytes(range(255))
        changed = bytes([99]) + original[1:]
        self.assertEqual(len(changed), 4095)
        row["expectedContentSHA256"] = digest(changed)
        spec = json.loads(base64.b64decode(row["specBase64"]))
        spec.update(content=encoded(changed), contentSHA256=digest(changed))
        raw = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        row.update(specBase64=encoded(raw), specSHA256=digest(raw))
        for phase in ("currentRead", "reopenedRead"):
            row[phase]["content"].update(base64=encoded(changed), sha256=digest(changed))
        self.rejects(value)

    def test_source_intent_uses_length_prefixed_utf8_material(self):
        value = fixture()
        value["identity"]["accountId"] = "synthetic-e\u0301-account"
        for row in value["files"]:
            row["intentId"] = source_intent(value["identity"], row["sourceKey"])
        proof.observation(value, BINDING)
        value["files"][0]["intentId"] = source_intent(value["identity"], value["files"][0]["sourceKey"], utf8_lengths=False)
        self.rejects(value)
        value = fixture()
        value["files"][0]["sourceKey"] = value["files"][1]["sourceKey"]
        self.rejects(value)

    def test_original_specification_hash_base64_and_duplicate_members_are_checked(self):
        for mutation in ("hash", "base64", "duplicate", "owner"):
            with self.subTest(mutation=mutation):
                value = fixture()
                row = value["files"][0]
                if mutation == "hash":
                    row["specSHA256"] = "f" * 64
                elif mutation == "base64":
                    row["specBase64"] += "\n"
                else:
                    raw = base64.b64decode(row["specBase64"])
                    if mutation == "duplicate":
                        raw = b'{"name":"different",' + raw[1:]
                    else:
                        spec = json.loads(raw)
                        spec["ownerObjectId"] = value["identity"]["ownerObjectIds"][1]
                        raw = json.dumps(spec, separators=(",", ":")).encode()
                    row.update(specBase64=encoded(raw), specSHA256=digest(raw))
                self.rejects(value)

    def test_ordered_native_owners_and_carrier_identity_are_enforced(self):
        for mutation in ("duplicate_owner", "swap_owners", "carrier", "owner_as_carrier", "records", "change"):
            with self.subTest(mutation=mutation):
                value = fixture()
                row = value["files"][0]
                if mutation == "duplicate_owner":
                    value["identity"]["ownerObjectIds"][1] = value["identity"]["ownerObjectIds"][0]
                elif mutation == "swap_owners":
                    value["identity"]["ownerObjectIds"].reverse()
                elif mutation == "carrier":
                    row["retry"]["payloadObjectId"] = "different-carrier"
                elif mutation == "change":
                    row["afterCommittedReopenStatus"]["changeId"] = "different-change"
                elif mutation == "records":
                    row["prepared"]["recordIds"] = [row["ownerObjectId"]]
                else:
                    for phase, _, _, _ in proof.RECEIPT_PHASES:
                        row[phase]["payloadObjectId"] = row["ownerObjectId"]
                self.rejects(value)

    def test_prepared_complete_and_obsolete_phases_cannot_be_relabelled(self):
        for phase, field, other in (("prepared", "stage", "file-root-committed"),
                                    ("afterPreparedReopen", "outcome", "obsolete"),
                                    ("committed", "outcome", "prepared"),
                                    ("retry", "stage", "file-prepared")):
            with self.subTest(phase=phase):
                value = fixture()
                value["files"][0][phase][field] = other
                self.rejects(value)

    def test_reopen_observations_must_belong_to_the_actual_three_generations(self):
        for phase, field, old_index in (("afterPreparedReopen", "runtimeGeneration", 0),
                                        ("currentRead", "ownerGeneration", 0),
                                        ("reopenedRead", "runtimeGeneration", 1)):
            with self.subTest(phase=phase):
                value = fixture()
                collection = "ownerGenerations" if field == "ownerGeneration" else "runtimeGenerations"
                value["files"][0][phase][field] = value[collection][old_index]
                self.rejects(value)
        value = fixture()
        value["runtimeGenerations"][2] = value["runtimeGenerations"][0].lower()
        self.rejects(value)

    def test_native_reads_require_exact_owner_file_and_durable_bytes(self):
        for name, replacement in (("objectId", "different-owner"), ("fileId", "different-file"),
                                  ("cached", False), ("durable", False), ("inline", 1), ("rootCid", "remote-root")):
            with self.subTest(field=name):
                value = fixture()
                value["files"][0]["reopenedRead"]["metadata"][name] = replacement
                self.rejects(value)
        value = fixture()
        value["files"][1]["reopenedRead"]["content"]["base64"] = encoded(b"wrong")
        self.rejects(value)

    def test_unicode_filename_bytes_and_current_reopened_metadata_must_match(self):
        value = fixture()
        value["files"][1]["currentRead"]["metadata"]["name"] = "\u05e7\u05d5\u05d1\u05e5 \u00e9 \U0001f9ea.bin"
        self.rejects(value)
        value = fixture()
        value["files"][0]["reopenedRead"]["status"]["attempts"] = 1
        self.rejects(value)

    def test_cleanup_scope_and_strict_types_cannot_overclaim(self):
        for mutation in ("cleanup", "network", "scope", "integer", "extra"):
            with self.subTest(mutation=mutation):
                value = fixture()
                if mutation == "cleanup": value["completedCleanup"] = False
                elif mutation == "network": value["capabilities"]["networkVerified"] = True
                elif mutation == "scope": value["limits"]["osProcessCrash"] = "PASS"
                elif mutation == "integer": value["files"][0]["expectedSize"] = False
                else: value["files"][0]["nativePASS"] = True
                self.rejects(value)
        value = fixture()
        value["runtimeVersions"] = ["any " + contract.VERSION + " " + "a" * 65536] * 3
        self.rejects(value)

    def test_exactly_one_actual_method_on_owned_ios27_is_required(self):
        actual = {contract.SELECTOR + "()": "Passed"}
        result = proof.exact_execution(actual_summary(), actual, UDID, lambda tree: tree)
        self.assertEqual(result["counts"]["totalTestCount"], 1)
        for tree in ({}, {"Different/test()": "Passed"}, {contract.SELECTOR: "Skipped"},
                     {contract.SELECTOR: "Passed", "Different/test()": "Passed"}):
            with self.subTest(tree=tree):
                with self.assertRaises(ValueError):
                    proof.exact_execution(actual_summary(), tree, UDID, lambda item: item)

    def test_zero_failed_skipped_or_boolean_xctest_counts_are_rejected(self):
        for changes in (dict(totalTestCount=0, passedTests=0), dict(failedTests=1),
                        dict(skippedTests=1), dict(passedTests=True), dict(totalTestCount=2, passedTests=2)):
            with self.subTest(counts=changes):
                summary = dict(actual_summary(), **changes)
                with self.assertRaises(ValueError):
                    proof.exact_execution(summary, {contract.SELECTOR: "Passed"}, UDID, lambda tree: tree)
        for key, other in (("deviceId", str(UUID(int=999))), ("osVersion", "26.0"), ("architecture", "x86_64")):
            summary = actual_summary()
            summary["devicesAndConfigurations"][0]["device"][key] = other
            with self.assertRaises(ValueError):
                proof.exact_execution(summary, {contract.SELECTOR: "Passed"}, UDID, lambda tree: tree)


if __name__ == "__main__":
    unittest.main(verbosity=2)
