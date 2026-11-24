"""Read-only real-Git controls for new Native6 product source admission."""
import copy
import json
from pathlib import Path
import subprocess
import unittest

import current_execution as current
import native_ui_retained as retained


class CurrentNativeProductControls(unittest.TestCase):
    def setUp(self):
        self.fixed = current.read(current.MANIFEST)
        self.head = current.git("rev-parse", "HEAD").decode().strip()
        self.revision = dict(schemaVersion=1, profile="native-ui-failed", sourceCommit=self.head,
            productTrees={name: current.git("rev-parse", self.head + ":" + name).decode().strip()
                          for name in ("Modules", "NativeApp")})
        self.fixed["currentNativeProductRevision"] = self.revision

    def test_complete_real_git_origin_is_selected_without_mutating_history(self):
        before = copy.deepcopy(self.fixed)
        self.assertEqual(current.native_product_revision(self.fixed, "native-ui-failed", self.head), self.revision)
        self.assertEqual(self.fixed, before)

    def test_legacy_release_and_absent_revision_keep_their_existing_admission(self):
        self.assertIsNone(current.native_product_revision(self.fixed, "release-return-rtl", self.head))
        self.fixed.pop("currentNativeProductRevision")
        self.assertIsNone(current.native_product_revision(self.fixed, "native-ui-failed", self.head))

    def test_incomplete_foreign_or_boolean_revision_is_rejected(self):
        for change in ("missing", "extra", "profile", "boolean"):
            with self.subTest(change=change):
                fixed = copy.deepcopy(self.fixed)
                revision = fixed["currentNativeProductRevision"]
                if change == "missing":
                    revision["productTrees"].pop("NativeApp")
                elif change == "extra":
                    revision["productTrees"]["Anytype"] = "0" * 40
                elif change == "profile":
                    revision["profile"] = "release-return-rtl"
                else:
                    revision["schemaVersion"] = True
                with self.assertRaises(ValueError):
                    current.native_product_revision(fixed, "native-ui-failed", self.head)

    def test_tree_bytes_must_belong_to_the_declared_immutable_origin(self):
        self.revision["productTrees"]["NativeApp"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "current_native_product_revision_origin_changed"):
            current.native_product_revision(self.fixed, "native-ui-failed", self.head)

    def test_new_revision_cannot_claim_old_source_as_its_origin(self):
        self.revision["sourceCommit"] = self.fixed["inventoryRecovery"]["sourceCommit"]
        with self.assertRaisesRegex(ValueError, "current_native_product_revision_origin_changed"):
            current.native_product_revision(self.fixed, "native-ui-failed", self.head)

    def test_retained_old_products_still_reject_new_native_source(self):
        old = dict(compiledTrees=self.fixed["inventoryRecovery"]["productTrees"]["native-ui-failed"],
                   compiledOrigin=self.fixed["inventoryRecovery"]["sourceCommit"])
        new = dict(compiledTrees=self.revision["productTrees"], compiledOrigin=self.revision["sourceCommit"])
        with self.assertRaisesRegex(ValueError, "retained_compiled_sources_changed"):
            retained.qualify_source_delta(old, new, {})


if __name__ == "__main__":
    unittest.main()
