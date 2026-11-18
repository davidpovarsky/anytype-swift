"""Adversarial selected-block receipt controls; these are not native UI acceptance."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import unittest

import hanlin_selection_evidence as gate
from hanlin_acceptance_evidence import APPLE_DATE_EPOCH


class HanlinSelectionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 18, 7, tzinfo=timezone.utc).timestamp()
        self.sha, self.run, self.attempt = "a" * 40, "44246590240", "1"
        nonce = "D44A0C61-3204-4D83-AE21-0FDC1B1F2145"
        base = dict(fixtureID=nonce, createdAt=self.now - 60 - APPLE_DATE_EPOCH,
                    sourceSHA=self.sha, runID=self.run, runAttempt=self.attempt, accountID="account",
                    spaceID="space", alternateSpaceID="other-space", sourceObjectID="document", sourceTitle="Prepared page",
                    sourceBlockID="selected", sourceText="Hanlin native body " + nonce,
                    createdTitle="Hanlin native created " + nonce, cancelledTitle="Hanlin native cancelled " + nonce)
        self.fixture = dict(base=base, excludedBlockID="other-block", excludedText="Hanlin unselected body " + nonce)
        context = dict(app="anytype", account="account", workspace="space", space="space", objectReference="document",
                       sceneID="E1186C53-1EA4-4577-8B03-D3A81E941B02", generation="910057A9-6040-46A1-9569-62B3D029C204",
                       selectionReferences=["selected"], sourceRevision="b" * 64)
        checks = {name: True for name in [
            "middleware_logging_disabled", "native_single_block_selection_context",
            "read_denied_before_native_consent", "native_selected_text_read", "unselected_text_excluded",
            "read_receipt_contains_metadata_only", "native_selected_block_mounted_on_return",
            "closed_selection_host_denies_read", "no_provider_configuration"]}
        session = "60C5B23D-7612-46E3-AD90-4361A9F60701"
        request = "4F1EA3BE-B748-4E01-864B-BC94D7E0A289"
        self.result = dict(
            fixtureID=nonce, sourceSHA=self.sha, runID=self.run, runAttempt=self.attempt,
            sessionID=session, navigationContext=context, processID=714, startedAt=self.now - 40 - APPLE_DATE_EPOCH,
            finishedAt=self.now - 10 - APPLE_DATE_EPOCH, phase="HANLIN_SELECTION_ACCEPTANCE_PASS", checks=checks,
            providerConfigured=False, deniedReadAttempts=3,
            deniedReadInvocationIDs=["9789B220-8B33-47E4-9CD2-18350B1C8D91", "756CD487-9261-4FA0-B898-C6C241B7B638",
                                     "6E7D4942-5B50-426F-8BF5-7824529AB507"],
            selectedRead=dict(invocationID="canonical-read-1", objectReference="document", spaceReference="space",
                              sourceRevision="b" * 64, title="Prepared page", blockReferences=["selected"],
                              textSHA256=hashlib.sha256(base["sourceText"].encode()).hexdigest(),
                              coverage="selectedTextBlocksOnly", effectState="confirmedNoEffect", metadataContentsCount=0),
            nativeReturn=dict(requestID=request, queuedRequestID=request, sessionID=session, context=copy.deepcopy(context),
                              objectReference="document", blockReference="selected", presentationAcknowledged=True))

    def validate(self):
        return gate.validate_result(self.result, self.fixture, self.sha, self.run, self.attempt, self.now)

    def test_exact_receipt_is_separate_from_ui22_and_not_itself_xctest_pass(self):
        actual = self.validate()
        self.assertEqual(actual["required_checks"], 9)
        self.assertEqual(actual["coverage"], "selectedTextBlocksOnly")
        self.assertTrue(actual["selected_block_receipt_verified"])
        self.assertFalse(actual["selected_block_ui_verified"])
        self.assertFalse(actual["full_sdk_acceptance"])

    def test_source_run_attempt_and_fixture_identity_are_bound(self):
        for field, value in [("sourceSHA", "c" * 40), ("runID", "9"), ("runAttempt", "2"),
                             ("fixtureID", "D44A0C61-3204-4D83-AE21-0FDC1B1F2146")]:
            with self.subTest(field=field):
                original = self.result[field]; self.result[field] = value
                with self.assertRaisesRegex(ValueError, "belongs to another"):
                    self.validate()
                self.result[field] = original

    def test_fixture_requires_distinct_native_paragraphs_with_same_nonce(self):
        for field, value in [("excludedBlockID", "selected"), ("excludedText", "foreign"), ("extra", True)]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.fixture); self.fixture[field] = value
                with self.assertRaises(ValueError): self.validate()
                self.fixture = original
        self.fixture["base"]["createdAt"] -= 3601
        with self.assertRaisesRegex(ValueError, "stale"): self.validate()

    def test_selection_environment_cannot_enable_document_ui22(self):
        raw = json.dumps(self.fixture)
        environment = gate.fixture_environment(self.fixture, self.sha, self.run, self.attempt, self.now, raw)
        self.assertEqual(environment["PINKHA_HANLIN_SELECTION_FIXTURE_JSON"], raw)
        self.assertEqual(environment["PINKHA_HANLIN_SELECTION_UI_TESTING"], "1")
        self.assertFalse(any(key.startswith("PINKHA_HANLIN_NATIVE_") for key in environment))
        with self.assertRaisesRegex(ValueError, "differs"):
            gate.fixture_environment(self.fixture, self.sha, self.run, self.attempt, self.now, "{}")

    def test_every_check_is_required_and_only_boolean_true_passes(self):
        for key in tuple(self.result["checks"]):
            for replacement in [False, 1, None]:
                with self.subTest(check=key, replacement=replacement):
                    self.result["checks"][key] = replacement
                    with self.assertRaisesRegex(ValueError, "checks"): self.validate()
                    self.result["checks"][key] = True
            del self.result["checks"][key]
            with self.assertRaisesRegex(ValueError, "checks"): self.validate()
            self.result["checks"][key] = True

    def test_whole_document_or_foreign_or_multiple_selection_is_rejected(self):
        for ids in [[], ["other-block"], ["selected", "other-block"], ["selected", "selected"]]:
            with self.subTest(ids=ids):
                self.result["navigationContext"]["selectionReferences"] = ids
                with self.assertRaisesRegex(ValueError, "exactly the prepared block"): self.validate()

    def test_account_space_scene_and_source_context_are_strict(self):
        for field, replacement in [("account", "other"), ("workspace", "other"), ("space", "other"),
                                   ("objectReference", "other"), ("sceneID", "not-a-uuid"),
                                   ("generation", "not-a-uuid"), ("sourceRevision", "")]:
            with self.subTest(field=field):
                original = self.result["navigationContext"][field]
                self.result["navigationContext"][field] = replacement
                with self.assertRaises(ValueError): self.validate()
                self.result["navigationContext"][field] = original

    def test_successful_read_must_be_exact_scoped_body_without_unselected_text(self):
        for field, replacement in [("blockReferences", ["selected", "other-block"]), ("blockReferences", ["other-block"]),
                                   ("coverage", "documentTextBlocksOnly"), ("textSHA256", "c" * 64),
                                   ("sourceRevision", "c" * 64), ("title", "other"),
                                   ("objectReference", "other"), ("spaceReference", "other"),
                                   ("effectState", "confirmedCommitted")]:
            with self.subTest(field=field):
                original = self.result["selectedRead"][field]; self.result["selectedRead"][field] = replacement
                with self.assertRaisesRegex(ValueError, "read differs"): self.validate()
                self.result["selectedRead"][field] = original

    def test_read_metadata_must_have_no_payload_and_no_unknown_fields(self):
        for value in [1, False, None]:
            self.result["selectedRead"]["metadataContentsCount"] = value
            with self.assertRaisesRegex(ValueError, "retained payload"): self.validate()
        self.result["selectedRead"]["metadataContentsCount"] = 0
        self.result["selectedRead"]["contents"] = ["payload"]
        with self.assertRaisesRegex(ValueError, "read receipt"): self.validate()

    def test_actual_mount_requires_nonempty_exact_block_and_matching_request(self):
        for field, replacement in [("blockReference", None), ("blockReference", "other-block"),
                                   ("objectReference", "other"), ("presentationAcknowledged", False),
                                   ("presentationAcknowledged", 1),
                                   ("queuedRequestID", "4F1EA3BE-B748-4E01-864B-BC94D7E0A288")]:
            with self.subTest(field=field):
                original = self.result["nativeReturn"][field]; self.result["nativeReturn"][field] = replacement
                with self.assertRaises(ValueError): self.validate()
                self.result["nativeReturn"][field] = original

    def test_mount_cannot_substitute_session_context_or_omit_receipt(self):
        original = copy.deepcopy(self.result["nativeReturn"])
        self.result["nativeReturn"]["sessionID"] = "60C5B23D-7612-46E3-AD90-4361A9F60702"
        with self.assertRaisesRegex(ValueError, "presentation or context"): self.validate()
        self.result["nativeReturn"] = copy.deepcopy(original)
        self.result["nativeReturn"]["context"]["generation"] = "910057A9-6040-46A1-9569-62B3D029C205"
        with self.assertRaisesRegex(ValueError, "presentation or context"): self.validate()
        self.result["nativeReturn"] = None
        with self.assertRaisesRegex(ValueError, "return receipt"): self.validate()

    def test_closed_host_denials_need_three_distinct_valid_invocations(self):
        for value in [0, 1, 2, 4, True]:
            self.result["deniedReadAttempts"] = value
            with self.assertRaisesRegex(ValueError, "two post-close"): self.validate()
        self.result["deniedReadAttempts"] = 3
        original = self.result["deniedReadInvocationIDs"][:]
        for values in [[], original[:2], [original[0]] * 3, original[:2] + ["invalid"]]:
            self.result["deniedReadInvocationIDs"] = values
            with self.assertRaises(ValueError): self.validate()
        self.result["deniedReadInvocationIDs"] = original
        self.result["selectedRead"]["invocationID"] = original[0]
        with self.assertRaisesRegex(ValueError, "cached invocation"): self.validate()

    def test_provider_process_failure_and_execution_dates_cannot_be_ignored(self):
        for field, value in [("providerConfigured", True), ("providerConfigured", 0), ("processID", 0),
                             ("processID", True), ("failure", "actual_failure"), ("phase", "SELECTION_READY_TO_RETURN"),
                             ("startedAt", self.now + 5 - APPLE_DATE_EPOCH), ("finishedAt", float("nan"))]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.result); self.result[field] = value
                with self.assertRaises(ValueError): self.validate()
                self.result = original


if __name__ == "__main__":
    unittest.main()
