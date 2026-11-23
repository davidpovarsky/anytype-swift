#!/usr/bin/env python3
"""Eight new controls for exact retention of the original450876 partial batch."""
import copy
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest import mock
import continue_native_acceptance as base
import native_ui_followup_retention as followup
import native_continuation_sources as sources
import verify_native_test_execution as execution
ROOT = sources.ROOT

class FollowupRetentionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / "docs/validation/20261123-native-ui-followup-retention/original-controls.json").read_bytes())
        cls.before = sources.source(followup.SOURCE, sources.TEST, ROOT)
        cls.after = (ROOT / sources.TEST).read_bytes()

    def verify(self, value=None):
        v = copy.deepcopy(value or self.original)
        return followup.verify_raw_results(v["summary"], v["tree"], v["record"], v["simulator"], v["namedLog"].encode(), base)

    def test_actual_two_pass_four_fail_batch_keeps_failure_and_exact_two_origins(self):
        value = self.verify()
        self.assertEqual(value["counts"], dict(totalTestCount=6, passedTests=2, failedTests=4, skippedTests=0))
        self.assertEqual(set(value["retainedMethods"]), followup.PASSED)
        self.assertEqual(set(value["originalCases"].values()), {"Passed", "Failed"})

    def test_zero_boolean_skipped_or_relabelled_counts_are_refused(self):
        for key, value in [("totalTestCount", 0), ("passedTests", 6), ("failedTests", 0), ("skippedTests", 1), ("passedTests", True)]:
            with self.subTest(key=key, value=value):
                bad = copy.deepcopy(self.original); bad["summary"][key] = value
                with self.assertRaises(ValueError): self.verify(bad)

    def test_wrong_named_inventory_source_status_or_device_is_refused(self):
        bad = copy.deepcopy(self.original); bad["tree"] = {}
        with self.assertRaises(ValueError): self.verify(bad)
        for key, value in (("status", "PASS"), ("commit", "0" * 40), ("observationOnly", True)):
            bad = copy.deepcopy(self.original); bad["record"][key] = value
            with self.assertRaises(ValueError): self.verify(bad)
        bad = copy.deepcopy(self.original); bad["simulator"]["ownedUDID"] = "00000000-0000-0000-0000-000000000000"
        with self.assertRaises(ValueError): self.verify(bad)

    def test_original_stdout_requires_every_started_and_finished_case(self):
        bad = copy.deepcopy(self.original)
        bad["namedLog"] = bad["namedLog"].replace("]' passed", "]' failed", 1)
        self.assertNotEqual(bad["namedLog"], self.original["namedLog"])
        with self.assertRaises(ValueError): self.verify(bad)
        bad["namedLog"] = ""
        with self.assertRaises(ValueError): self.verify(bad)

    def test_original_run_and_artifact_identity_cannot_be_replayed(self):
        expected = followup.manifest(ROOT)
        run, artifact = self.original["run"], self.original["artifact"]
        followup.verify_api(run, artifact, expected)
        for key, value in (("id", 1), ("head_sha", "0" * 40), ("run_attempt", 2), ("conclusion", "success")):
            bad = copy.deepcopy(run); bad[key] = value
            with self.assertRaises(ValueError): followup.verify_api(bad, artifact, expected)
        for key, value in (("id", 1), ("digest", "sha256:" + "0" * 64), ("expired", True)):
            bad = copy.deepcopy(artifact); bad[key] = value
            with self.assertRaises(ValueError): followup.verify_api(run, bad, expected)

    def test_passed_declarations_and_all_common_helpers_are_byte_identical(self):
        proof = followup.declaration_proof(self.before, self.after)
        self.assertEqual(set(proof["retainedDeclarationsByteIdentical"]), set(followup.PASSED_NAMES))
        for name in followup.PASSED_NAMES:
            start, end = sources.declaration(self.after, name)
            changed = self.after[:end - 1] + b" " + self.after[end - 1:]
            with self.assertRaises(ValueError): followup.declaration_proof(self.before, changed)
        with self.assertRaises(ValueError): followup.declaration_proof(self.before, self.after + b"\n")

    def test_inactive_review_cannot_admit_another_production_dependency(self):
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        proof = followup.verify_sources(head, ROOT)
        self.assertEqual(set(proof["changedProtectedPaths"]), {sources.TEST, followup.ARCHIVE_VIEW})
        review = followup.data(ROOT / followup.REVIEW)
        bad = copy.deepcopy(review)
        bad["inactiveSourceChanges"][0]["path"] = "Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeWorkspace.swift"
        with mock.patch.object(followup, "data", return_value=bad):
            with self.assertRaises(ValueError): followup.verify_sources(head, ROOT)
        bad = copy.deepcopy(review); bad["inactiveSourceChanges"][0]["afterSHA256"] = "0" * 64
        with mock.patch.object(followup, "data", return_value=bad):
            with self.assertRaises(ValueError): followup.verify_sources(head, ROOT)

    def test_workflow_selects_four_and_preserves_the_original_six_profile(self):
        self.assertEqual(execution.expected_methods(followup.PROFILE), followup.FAILED)
        self.assertEqual(execution.expected_methods(base.PROFILE), followup.FAILED | followup.PASSED)
        self.assertIn(followup.PROFILE, execution.EXACT_PROFILES)
        text = (ROOT / ".github/workflows/pinkha-any-engine-port.yml").read_text()
        step = text.split("        id: native-ui-continuation-tests\n", 1)[1].split("      - name: Run one real Files archive roundtrip", 1)[0]
        selectors = set(re.findall(r"-only-testing:PinkhaAnyNativeUITests/(NativeLaunchTests/\w+)", step))
        self.assertEqual(selectors, followup.FAILED)
        self.assertFalse(selectors & followup.PASSED)
        self.assertIn("--profile " + followup.PROFILE, step)
        self.assertIn("continue_native_acceptance.py retain --followup-450876", text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
