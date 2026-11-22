"""Only new candidate source-composition controls; no native execution claim."""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

import attachment_runtime as base
import current_read_runtime as candidate


class CurrentReadCompositionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = Path(__file__).resolve().parents[2]
        cls.source = Path(os.environ.get("T5_CURRENT_READ_SOURCE", cls.control))
        cls.heart = Path(os.environ["T5_CURRENT_READ_HEART"])
        cls.retained = base.prepare(cls.source, cls.control, candidate.BASE_VARIANT)
        cls.originals = {path: (cls.heart / path).read_bytes() for path in candidate.BEFORE}
        cls.additions = {path: (cls.control / candidate.OVERLAY / path).read_bytes() for path in candidate.ADDITIONS}

    def test_every_retained_lookup_and_attachment_section_is_preserved(self):
        result = candidate.compose(self.retained, self.originals, self.additions)
        old, new = base.sections(self.retained.patch), base.sections(result.patch)
        self.assertEqual(set(new) - set(old), set(candidate.BEFORE) | set(candidate.ADDITIONS))
        for path, section in old.items():
            self.assertEqual(new[path], section, path)
        inventory = json.loads(result.inventory)
        self.assertEqual(inventory["features"]["t5_related_lookup"], 1)
        self.assertEqual(inventory["features"]["ordinary_details_preserve_torah_attachment"], 1)
        self.assertEqual(inventory["features"]["current_authority_read_fence"], 1)
        self.assertEqual(inventory["product_source_changes"], len(candidate.PRODUCT_PATHS))
        self.assertEqual(inventory["patch_sha256"], result.patch_sha256)
        self.assertEqual(inventory["expected_app_get_version"], result.version)
        self.assertEqual(inventory["current_authority_provenance"]["unchanged_r15_paths"], sorted(old))
        self.assertIn("-pinkha-current-read-v1-" + result.patch_sha256, result.version)
        self.assertEqual(inventory["client_enablement"], "DISABLED_PENDING_NATIVE_AND_RUNTIME_PROOF")

    def test_changed_heart_input_or_unreviewed_overlay_paths_are_rejected(self):
        altered = dict(self.originals)
        altered["core/object.go"] += b"\n// different upstream\n"
        with self.assertRaisesRegex(RuntimeError, "Immutable source bytes changed"):
            candidate.compose(self.retained, altered, self.additions)
        for additions in ({}, dict(self.additions, **{"core/foreign.go": b"package core\n"})):
            with self.assertRaisesRegex(ValueError, "Unreviewed native authority source paths"):
                candidate.compose(self.retained, self.originals, additions)

    def test_disguised_or_mutated_base_runtime_cannot_be_promoted(self):
        for retained in (
            base.RuntimeSource("r14-attachment-v1", self.retained.patch, self.retained.inventory),
            base.RuntimeSource(candidate.BASE_VARIANT, self.retained.patch + b"\n", self.retained.inventory),
            base.RuntimeSource(candidate.BASE_VARIANT, self.retained.patch, self.retained.inventory + b"\n"),
        ):
            with self.assertRaises(ValueError):
                candidate.compose(retained, self.originals, self.additions)


if __name__ == "__main__":
    unittest.main()
