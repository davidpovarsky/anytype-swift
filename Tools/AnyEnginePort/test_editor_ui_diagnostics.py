import unittest
import collect_editor_ui_diagnostics as collector


class EditorDiagnosticsPrivacyTests(unittest.TestCase):
    def test_noncontent_phase_and_readiness_are_accepted(self):
        event = {"phase": "addParagraphFailed", "timestamp": 1.5, "mounted": True,
                 "foreground": False, "ownerMatches": True,
                 "errorType": "PinkhaAnyHost.AnyHostError"}
        self.assertEqual(collector.validate_events([event]), [event])

    def test_text_or_identity_fields_are_refused(self):
        for field in ("text", "token", "accountID", "objectID", "blockID", "errorDescription"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "unexpected_diagnostic_field"):
                collector.validate_events([{"phase": "emptyButtonTapped", "timestamp": 1, field: "private"}])

    def test_boolean_and_finite_timestamp_types_are_exact(self):
        for update in ({"mounted": 1}, {"timestamp": True}, {"timestamp": float("nan")}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                collector.validate_events([{"phase": "emptyButtonTapped", "timestamp": 1, **update}])

    def test_event_bound_and_unknown_phase_are_refused(self):
        event = {"phase": "emptyButtonTapped", "timestamp": 1}
        with self.assertRaisesRegex(ValueError, "invalid_event_count"):
            collector.validate_events([event] * 257)
        with self.assertRaisesRegex(ValueError, "invalid_diagnostic_phase"):
            collector.validate_events([{**event, "phase": "free form native message"}])


if __name__ == "__main__":
    unittest.main()
