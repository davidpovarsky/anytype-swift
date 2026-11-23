"""Control tests for evidence rejection; these do not run the iOS application."""
import copy
import json
import unittest
from hanlin_acceptance_evidence import (
    APPLE_DATE_EPOCH, REQUIRED_CHECKS, SCENE_EVENT_KEYS, fixture_environment, validate_fixture, validate_result,
)

SHA = "1" * 40
NOW = APPLE_DATE_EPOCH + 800000000
NONCE = "6302CF05-5264-4C9F-99BE-49F81B7D28EF"
SESSIONS = ["BDAAC613-26E5-4CAB-9A3B-58D38181E43A", "8BE24B77-F28F-4A80-A407-E6E33F74F502",
            "5E2DF89A-8D85-41DC-9722-1115FC3C07B5", "19A777F6-6F4D-4788-8E29-3A324B060554"]
RETURN_REQUEST = "CD5057ED-9D9F-4F07-B709-58E30F6073D3"


def fixture():
    return dict(fixtureID=NONCE, createdAt=799999900, sourceSHA=SHA, runID="123", runAttempt="1",
                accountID="disposable-account", spaceID="origin-space", alternateSpaceID="alternate-space",
                sourceObjectID="source-page", sourceBlockID="source-block", sourceTitle="Native source",
                sourceText="Hanlin native body " + NONCE, createdTitle="Hanlin native created " + NONCE,
                cancelledTitle="Hanlin native cancelled " + NONCE)


def result():
    context = dict(app="anytype", account="disposable-account", workspace="origin-space", space="origin-space",
                   sceneID="6D4E7287-9813-4AFC-A1B4-48FFED9B82B3",
                   generation="B6F807B5-0266-4020-B086-A68CF13F4F5B", objectReference="source-page",
                   selectionReferences=[], sourceRevision="a" * 64)
    return dict(fixtureID=NONCE, sourceSHA=SHA, runID="123", runAttempt="1",
                sessionID=SESSIONS[0], backgroundSessionID=SESSIONS[1],
                staleConsentSessionID=SESSIONS[2], freshSessionID=SESSIONS[3], processID=1234,
                invalidationCauses={session: "nativeAuthorityChanged" for session in SESSIONS},
                sceneEventCounts={key: 3 for key in SCENE_EVENT_KEYS},
                backgroundCycleSceneDelta={key: 1 for key in SCENE_EVENT_KEYS},
                documentExitSceneDelta={key: 1 for key in SCENE_EVENT_KEYS},
                documentExitAttribution="navigationWithSceneTransition",
                startedAt=799999910, finishedAt=799999990, phase="NATIVE_ACCEPTANCE_PASS",
                checks={key: True for key in REQUIRED_CHECKS}, createdObjectID="created-page",
                navigationContext=context,
                nativeReturn=dict(requestID=RETURN_REQUEST, queuedRequestID=RETURN_REQUEST,
                                  sessionID=SESSIONS[0], context=copy.deepcopy(context),
                                  objectReference="source-page", presentationAcknowledged=True),
                providerConfigured=False, logoutRootState="auth")


class HanlinNativeEvidenceTests(unittest.TestCase):
    def verify(self, value):
        return validate_result(value, fixture(), SHA, "123", "1", NOW)

    def test_complete_receipt_does_not_itself_claim_sdk_acceptance(self):
        verified = self.verify(result())
        self.assertEqual(verified["required_checks"], 22)
        self.assertEqual(verified["presentation_count"], 4)
        self.assertEqual(verified["document_exit_attribution"], "navigationWithSceneTransition")
        self.assertFalse(verified["full_sdk_acceptance"])
        self.assertIn("XCTEST_REQUIRED_SEPARATELY", verified["status"])
        self.assertEqual(verified["native_return"]["request_id"], RETURN_REQUEST)
        self.assertEqual(verified["native_return"]["scope"], "originalDocumentOnly")
        self.assertFalse(verified["native_return"]["selected_block_ui_verified"])

    def test_completed_authority_checks_cannot_replace_the_original_logout_root_transition(self):
        for state in [None, "initial", "launch", "home", "delete", True]:
            candidate = result()
            candidate["logoutRootState"] = state
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, "original auth root"):
                self.verify(candidate)
        candidate = result()
        del candidate["logoutRootState"]
        with self.assertRaisesRegex(ValueError, "original auth root"):
            self.verify(candidate)
        verified = self.verify(result())
        self.assertEqual(verified["required_checks"], 22)
        self.assertEqual(verified["logout_root_state"], "auth")
        self.assertFalse(verified["logout_root_ui_verified"])

    def test_missing_or_unmounted_native_return_cannot_pass_from_label(self):
        for mutation in ["missing", "null", "empty", "queued", "numeric-ack"]:
            candidate = result()
            if mutation == "missing": del candidate["nativeReturn"]
            elif mutation == "null": candidate["nativeReturn"] = None
            elif mutation == "empty": candidate["nativeReturn"] = {}
            elif mutation == "queued": candidate["nativeReturn"]["presentationAcknowledged"] = False
            else: candidate["nativeReturn"]["presentationAcknowledged"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.verify(candidate)

    def test_native_return_requires_the_queued_request_and_original_session(self):
        for key, replacement in [("requestID", None), ("requestID", "invalid"),
                                 ("queuedRequestID", "invalid"), ("requestID", NONCE),
                                 ("queuedRequestID", NONCE), ("sessionID", SESSIONS[1])]:
            candidate = result(); candidate["nativeReturn"][key] = replacement
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                self.verify(candidate)

    def test_native_return_cannot_change_any_original_context_field(self):
        replacements = dict(app="other-app", account="other-account", workspace="alternate-space",
                            space="alternate-space", sceneID=NONCE, generation=NONCE,
                            objectReference="created-page", selectionReferences=["source-block"],
                            sourceRevision="b" * 64)
        for key, replacement in replacements.items():
            candidate = result(); candidate["nativeReturn"]["context"][key] = replacement
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "original context"):
                self.verify(candidate)

    def test_original_navigation_anchor_must_match_fixture_and_document_only_scope(self):
        replacements = dict(app="other-app", account="other-account", workspace="alternate-space",
                            space="alternate-space", sceneID="invalid", generation="invalid",
                            objectReference="created-page", selectionReferences=["source-block"], sourceRevision=None)
        for key, replacement in replacements.items():
            candidate = result()
            candidate["navigationContext"][key] = replacement
            candidate["nativeReturn"]["context"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(candidate)

    def test_native_return_rejects_foreign_object_or_selected_block_target(self):
        for key, replacement in [("objectReference", "created-page"), ("objectReference", None),
                                 ("blockReference", "source-block"), ("blockReference", "")]:
            candidate = result(); candidate["nativeReturn"][key] = replacement
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                self.verify(candidate)
        candidate = result(); candidate["nativeReturn"]["blockReference"] = None
        self.verify(candidate)  # Codable may omit nil; an explicit JSON null is equivalent.

    def test_native_return_and_anchor_schemas_cannot_drop_fields_or_add_claims(self):
        for field in ["navigationContext", "nativeReturn"]:
            for key in result()[field]:
                candidate = result(); del candidate[field][key]
                with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                    self.verify(candidate)
            candidate = result(); candidate[field]["sdkAuthorityRestored"] = True
            with self.subTest(field=field, mutation="extra"), self.assertRaises(ValueError):
                self.verify(candidate)

    def test_actual_return_still_requires_closed_host_read_and_create_denial(self):
        for key in ["native_return_mounted_original_document", "closed_presentation_denies_read_and_create"]:
            for mutation in ["missing", "false"]:
                candidate = result()
                if mutation == "missing": del candidate["checks"][key]
                else: candidate["checks"][key] = False
                with self.subTest(key=key, mutation=mutation), self.assertRaisesRegex(ValueError, "incomplete"):
                    self.verify(candidate)

    def test_four_real_presentation_identities_cannot_be_missing_or_reused(self):
        for key in ["backgroundSessionID", "staleConsentSessionID", "freshSessionID"]:
            for replacement in [None, "invalid", SESSIONS[0], SESSIONS[0].lower()]:
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                    candidate = result(); candidate[key] = replacement
                    self.verify(candidate)

    def test_invalidation_must_be_observed_for_exactly_the_four_presentations(self):
        for mutation in ["missing", "foreign", "extra", "unknown-cause"]:
            candidate = result()
            if mutation == "missing": del candidate["invalidationCauses"][SESSIONS[0]]
            elif mutation == "foreign":
                del candidate["invalidationCauses"][SESSIONS[0]]
                candidate["invalidationCauses"][NONCE] = "presentationRemoved"
            elif mutation == "extra": candidate["invalidationCauses"][NONCE] = "explicitCloseOrOwner"
            else: candidate["invalidationCauses"][SESSIONS[0]] = "assumedDocumentFence"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.verify(candidate)

    def test_scene_evidence_requires_exact_nonnegative_integer_counters(self):
        for field in ["sceneEventCounts", "backgroundCycleSceneDelta", "documentExitSceneDelta"]:
            for mutation in ["missing", "extra", "negative", "boolean", "fraction"]:
                candidate = result(); counts = candidate[field]; key = "sceneDidActivate"
                if mutation == "missing": del counts[key]
                elif mutation == "extra": counts["inventedEvent"] = 1
                elif mutation == "negative": counts[key] = -1
                elif mutation == "boolean": counts[key] = True
                else: counts[key] = 0.5
                with self.subTest(field=field, mutation=mutation), self.assertRaises(ValueError):
                    self.verify(candidate)

    def test_background_requires_both_directions_and_disjoint_deltas_fit_total(self):
        for missing in ["sceneDidEnterBackground", "sceneWillEnterForeground", "sceneDidActivate"]:
            candidate = result(); candidate["backgroundCycleSceneDelta"][missing] = 0
            with self.subTest(missing=missing), self.assertRaises(ValueError): self.verify(candidate)
        candidate = result(); candidate["sceneEventCounts"]["sceneDidActivate"] = 1
        with self.assertRaisesRegex(ValueError, "exceed"): self.verify(candidate)

    def test_document_exit_retains_observed_causal_scope(self):
        candidate = result(); candidate["documentExitAttribution"] = "navigationWithoutSceneTransition"
        with self.assertRaisesRegex(ValueError, "attribution"): self.verify(candidate)
        candidate["documentExitSceneDelta"] = {key: 0 for key in SCENE_EVENT_KEYS}
        verified = self.verify(candidate)
        self.assertEqual(verified["document_exit_attribution"], "navigationWithoutSceneTransition")
        candidate["documentExitAttribution"] = "navigationWithSceneTransition"
        with self.assertRaisesRegex(ValueError, "attribution"): self.verify(candidate)

    def test_fixture_preserves_exact_native_json(self):
        value = fixture()
        raw = json.dumps(value, indent=2)
        env = fixture_environment(value, SHA, "123", "1", NOW, raw)
        self.assertEqual(env["PINKHA_HANLIN_NATIVE_FIXTURE_JSON"], raw)
        foreign = copy.deepcopy(value); foreign["accountID"] = "other-account"
        with self.assertRaisesRegex(ValueError, "differs"):
            fixture_environment(value, SHA, "123", "1", NOW, json.dumps(foreign))

    def test_foreign_run_attempt_source_or_nonce_rejected(self):
        for key, value in [("runID", "124"), ("runAttempt", "2"), ("sourceSHA", "2" * 40),
                           ("fixtureID", "E0BEFA17-B242-424F-9E0A-C53E294CC405")]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "another"):
                candidate = result(); candidate[key] = value
                self.verify(candidate)

    def test_native_fixture_rejects_stale_future_or_wrong_nonce(self):
        for key, value in [("createdAt", 799996400), ("createdAt", 800000001),
                           ("sourceText", "content from another fixture"),
                           ("alternateSpaceID", "origin-space")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                candidate = fixture(); candidate[key] = value
                validate_fixture(candidate, SHA, "123", "1", NOW)

    def test_label_without_all_exact_boolean_checks_is_rejected(self):
        for mutation in ["missing", "false", "numeric", "extra"]:
            candidate = result()
            key = next(iter(REQUIRED_CHECKS))
            if mutation == "missing": del candidate["checks"][key]
            elif mutation == "false": candidate["checks"][key] = False
            elif mutation == "numeric": candidate["checks"][key] = 1
            else: candidate["checks"]["unreviewed_claim"] = True
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "incomplete"):
                self.verify(candidate)

    def test_failure_provider_missing_commit_and_fake_process_are_rejected(self):
        for key, value in [("phase", "READY_TO_CLOSE"), ("failure", "native_operation_failed"),
                           ("providerConfigured", True), ("createdObjectID", ""),
                           ("createdObjectID", "source-page"), ("processID", 0), ("processID", True),
                           ("sessionID", "not-a-session")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                candidate = result(); candidate[key] = value
                self.verify(candidate)

    def test_result_dates_cannot_precede_fixture_or_run_into_the_future(self):
        for key, value in [("startedAt", 799999899), ("finishedAt", None),
                           ("finishedAt", 799999905), ("finishedAt", 800000001),
                           ("finishedAt", float("nan")), ("startedAt", True)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                candidate = result(); candidate[key] = value
                self.verify(candidate)


if __name__ == "__main__":
    unittest.main()
