"""Negative provenance controls; no native/compiler/UI acceptance is asserted."""
import copy
import json
from pathlib import Path
import unittest

from additive_facade_source import validate_document, RELATIVE, REVIEWED
from donor_abi_input import validate_reference, SCHEMA

HERE = Path(__file__).resolve().parent


class FacadeAdoptionControls(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((HERE / "AnnotationExchange/source_adoption.json").read_text())
        self.binding = {"path": RELATIVE, "reviewed_source": REVIEWED}

    def test_actual_reviewed_membership_is_source_only(self):
        self.assertEqual(len(validate_document(self.doc, self.binding)), 11)

    def test_missing_or_additional_product_file_rejected(self):
        for edit in ("missing", "native", "duplicate"):
            with self.subTest(edit=edit):
                doc = copy.deepcopy(self.doc)
                if edit == "missing":
                    doc["files"].pop()
                elif edit == "native":
                    doc["files"][0]["path"] = "Modules/ProtobufMessages/Unexpected.swift"
                else:
                    doc["files"].append(copy.deepcopy(doc["files"][0]))
                with self.assertRaises(ValueError):
                    validate_document(doc, self.binding)

    def test_wrong_source_or_acceptance_claim_rejected(self):
        for key, value in [("base_source", "0"*40), ("reviewed_source", "1"*40),
                           ("scope", "SDK_ACCEPTED"),
                           ("native_acceptance_reused_by_this_document", True)]:
            with self.subTest(key=key):
                doc = copy.deepcopy(self.doc); doc[key] = value
                with self.assertRaises(ValueError):
                    validate_document(doc, self.binding)

    def test_wrong_document_binding_rejected(self):
        for key, value in [("path", "../source_adoption.json"), ("reviewed_source", "2"*40)]:
            with self.subTest(key=key):
                binding = dict(self.binding); binding[key] = value
                with self.assertRaises(ValueError):
                    validate_document(self.doc, binding)


class DonorReferenceControls(unittest.TestCase):
    def setUp(self):
        self.source = {"head_sha": "1"*40, "execution_identity": {
            "local_execution_sha256": "2"*64, "producer_kind": "local-mac"}}
        self.policy_sha = "3"*64
        self.value = {"schema": SCHEMA, "status": "EVIDENCE_REFERENCE_ONLY_REQUIRES_VERIFICATION",
                      "consumer_source_sha": "1"*40, "consumer_local_execution_sha256": "2"*64,
                      "policy_sha256": self.policy_sha, "donor_root": "/actual/original-owner",
                      "new_sdk_acceptance_granted": False}

    def test_reference_grants_no_acceptance(self):
        validate_reference(self.value, self.source, self.policy_sha)

    def test_identity_and_claim_mutations_rejected(self):
        cases = [("schema", "unknown"), ("status", "PASS"),
                 ("consumer_source_sha", "4"*40),
                 ("consumer_local_execution_sha256", "5"*64),
                 ("policy_sha256", "6"*64), ("new_sdk_acceptance_granted", True)]
        for key, value in cases:
            with self.subTest(key=key):
                item = dict(self.value); item[key] = value
                with self.assertRaises(ValueError):
                    validate_reference(item, self.source, self.policy_sha)

    def test_missing_extra_or_nonlocal_identity_rejected(self):
        missing = dict(self.value); missing.pop("donor_root")
        extra = dict(self.value); extra["native_tests_passed"] = True
        for item in (missing, extra):
            with self.assertRaises(ValueError):
                validate_reference(item, self.source, self.policy_sha)
        source = copy.deepcopy(self.source)
        source["execution_identity"]["producer_kind"] = "github-actions"
        with self.assertRaises(ValueError):
            validate_reference(self.value, source, self.policy_sha)


if __name__ == "__main__":
    unittest.main()
