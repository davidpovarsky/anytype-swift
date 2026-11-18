"""Control tests for evidence rejection; these do not run the iOS application."""
import copy
import json
import unittest
from hanlin_acceptance_evidence import (
    APPLE_DATE_EPOCH, REQUIRED_CHECKS, fixture_environment, validate_fixture, validate_result,
)

SHA = "1" * 40
NOW = APPLE_DATE_EPOCH + 800000000
NONCE = "6302CF05-5264-4C9F-99BE-49F81B7D28EF"


def fixture():
    return dict(fixtureID=NONCE, createdAt=799999900, sourceSHA=SHA, runID="123", runAttempt="1",
                accountID="disposable-account", spaceID="origin-space", alternateSpaceID="alternate-space",
                sourceObjectID="source-page", sourceBlockID="source-block", sourceTitle="Native source",
                sourceText="Hanlin native body " + NONCE, createdTitle="Hanlin native created " + NONCE,
                cancelledTitle="Hanlin native cancelled " + NONCE)


def result():
    return dict(fixtureID=NONCE, sourceSHA=SHA, runID="123", runAttempt="1",
                sessionID="BDAAC613-26E5-4CAB-9A3B-58D38181E43A", processID=1234,
                startedAt=799999910, finishedAt=799999990, phase="NATIVE_ACCEPTANCE_PASS",
                checks={key: True for key in REQUIRED_CHECKS}, createdObjectID="created-page",
                providerConfigured=False)


class HanlinNativeEvidenceTests(unittest.TestCase):
    def verify(self, value):
        return validate_result(value, fixture(), SHA, "123", "1", NOW)

    def test_complete_receipt_does_not_itself_claim_sdk_acceptance(self):
        verified = self.verify(result())
        self.assertEqual(verified["required_checks"], 14)
        self.assertFalse(verified["full_sdk_acceptance"])
        self.assertIn("XCTEST_REQUIRED_SEPARATELY", verified["status"])

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
