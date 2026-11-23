"""Three new controls for the exact failed-journey source review."""
from pathlib import Path
import unittest
import native_continuation_sources as source
import native_ui_followup_retention as followup
ROOT = source.ROOT

class CandidateScopeControls(unittest.TestCase):
    def test_hanlin_input_and_send_calls_cannot_escape_the_failed_hanlin_closure(self):
        before = source.source(followup.SOURCE, source.TEST, ROOT)
        after = (ROOT / source.TEST).read_bytes()
        source.verify_test_declarations(before, after)
        for helper in (source.HANLIN_INPUT_HELPER, source.HANLIN_SEND_HELPER):
            start, _ = source.declaration(after, source.FILES_NAME)
            point = after.index(b"{", start) + 1
            bad = after[:point] + b"\n        " + helper.encode() + b"(app)\n" + after[point:]
            with self.subTest(helper=helper), self.assertRaisesRegex(ValueError, "exclusive_to_failed_method"):
                source.verify_test_declarations(before, bad)

    def test_exact_label_drag_reversal_preserves_context_menu_and_native_drop(self):
        before = source.source(followup.SOURCE, source.LIBRARY_VIEW, ROOT)
        after = (ROOT / source.LIBRARY_VIEW).read_bytes()
        self.assertTrue(source.verify_hierarchy_drag_scope(before, after)["exactReversalMatchesOriginalFile"])
        for old, new in ((b".contentShape(Rectangle())", b".contentShape(Capsule())"),
                         (b"payloads.count == 1", b"payloads.count == 2"),
                         (b".contextMenu {", b".contextMenu {\n            // unreviewed")):
            bad = after.replace(old, new)
            self.assertNotEqual(bad, after)
            with self.subTest(edit=old), self.assertRaises(ValueError):
                source.verify_hierarchy_drag_scope(before, bad)

    def test_exact_shared_row_review_cannot_mask_other_file_changes(self):
        before = source.source(followup.SOURCE, source.LIBRARY_VIEW, ROOT)
        after = (ROOT / source.LIBRARY_VIEW).read_bytes()
        with self.assertRaisesRegex(ValueError, "other_source"):
            source.verify_hierarchy_drag_scope(before, after + b"\n")
        with self.assertRaisesRegex(ValueError, "not_exact"):
            source.verify_hierarchy_drag_scope(before, before)

if __name__ == "__main__":
    unittest.main(verbosity=2)
