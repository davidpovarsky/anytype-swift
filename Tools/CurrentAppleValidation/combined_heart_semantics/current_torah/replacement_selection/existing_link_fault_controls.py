"""Pure false-PASS controls; no Apple, simulator, network or native calls."""
import math
import sys
import unittest
sys.dont_write_bytecode = True
import semantic_link_route_observation as observation


class Contract:
    @staticmethod
    def require(condition, message):
        if not condition:
            raise AssertionError(message)


class ExistingLinkControls(unittest.TestCase):
    def setUp(self):
        self.binding = {"sourceSHA": "source", "runID": "run", "runAttempt": "1", "nonce": "nonce"}
        self.row = dict(self.binding, protocol="pinkha-semantic-existing-link-opening-v1",
                        budgetSeconds=20, realSemanticLinkTaps=1, nativeMenuActionTaps=0,
                        selectionKeysSent=0, status="OPENED_EXISTING_SEMANTIC_LINK",
                        admittedElapsedSeconds=1.0, elapsedSeconds=2.0)

    def test_valid_two_real_link_routes(self):
        for phase in ("linked", "unlinked"):
            self.assertEqual(observation.validate(Contract, [self.row, self.row], phase, self.binding)["realSemanticLinkTaps"], 2)

    def test_missing_or_extra_opening_refused(self):
        for count in (0, 1, 3):
            with self.assertRaises(AssertionError):
                observation.validate(Contract, [self.row] * count, "linked", self.binding)

    def test_foreign_fixture_refused(self):
        row = dict(self.row, nonce="other")
        with self.assertRaises(AssertionError):
            observation.validate(Contract, [self.row, row], "linked", self.binding)

    def test_selection_key_sent_behind_sheet_refused(self):
        row = dict(self.row, selectionKeysSent=1)
        with self.assertRaises(AssertionError):
            observation.validate(Contract, [self.row, row], "linked", self.binding)

    def test_direct_link_cannot_claim_native_menu_pass(self):
        row = dict(self.row, nativeMenuActionTaps=1)
        with self.assertRaises(AssertionError):
            observation.validate(Contract, [self.row, row], "linked", self.binding)

    def test_missed_deadline_or_nonfinite_time_refused(self):
        for value in (20.001, math.inf, math.nan, True):
            row = dict(self.row, admittedElapsedSeconds=value)
            with self.assertRaises(AssertionError):
                observation.validate(Contract, [self.row, row], "linked", self.binding)

    def test_wrong_outcome_extra_claim_or_boolean_count_refused(self):
        for delta in ({"status": "FAIL"}, {"unobservedNativePass": True}, {"realSemanticLinkTaps": True}):
            row = dict(self.row, **delta)
            with self.assertRaises(AssertionError):
                observation.validate(Contract, [self.row, row], "linked", self.binding)


if __name__ == "__main__":
    unittest.main()
