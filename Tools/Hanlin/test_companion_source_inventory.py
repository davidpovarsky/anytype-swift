import unittest

from companion_source_inventory import verify_tracked_inventory


class CompanionSourceInventoryTests(unittest.TestCase):
    def test_preserves_both_names_for_actual_docs_case_alias(self):
        canonical = "docs/a2ui/MediaReplayUI/App.swift"
        observed = "Docs/a2ui/MediaReplayUI/App.swift"
        self.assertEqual(
            verify_tracked_inventory(
                {canonical: "exact-source-hash"},
                {observed: {"kind": "file", "sha256": "exact-source-hash"}},
            ),
            {canonical: observed},
        )

    def test_case_collisions_are_not_silently_combined(self):
        record = {"kind": "file", "sha256": "same-hash"}
        with self.assertRaisesRegex(ValueError, "ambiguous case alias"):
            verify_tracked_inventory(
                {"docs/a.swift": "same-hash"},
                {"Docs/a.swift": record, "docs/a.swift": record},
            )
        with self.assertRaisesRegex(ValueError, "ambiguous canonical path"):
            verify_tracked_inventory(
                {"docs/a.swift": "same-hash", "Docs/a.swift": "same-hash"},
                {"Docs/a.swift": record},
            )

    def test_case_matching_keeps_missing_hash_and_file_kind_guards(self):
        for inventory in (
            {},
            {"Docs/a.swift": {"kind": "file", "sha256": "changed"}},
            {"Docs/a.swift": {"kind": "symlink", "sha256": "expected"}},
        ):
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                verify_tracked_inventory({"docs/a.swift": "expected"}, inventory)


if __name__ == "__main__":
    unittest.main()
