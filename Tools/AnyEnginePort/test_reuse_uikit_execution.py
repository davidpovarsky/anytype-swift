#!/usr/bin/env python3
"""Reject stale, altered or misattributed UIKit evidence before skipping execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import reuse_uikit_execution as reuse

PRODUCER = "a" * 40
RUN_ID = "123"
UDID = "00000000-0000-0000-0000-000000000001"


def source(commit, path):
    if commit != PRODUCER:
        raise RuntimeError("wrong producer")
    return path.encode("utf-8")


class UIKitEvidenceReuseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        methods = sorted(reuse.execution.expected_methods(reuse.PROFILE))
        self.summary = {
            "totalTestCount": 14, "passedTests": 14, "failedTests": 0, "skippedTests": 0,
            "devicesAndConfigurations": [{"device": {
                "deviceId": UDID, "deviceName": "AnyNativePort-" + RUN_ID,
                "architecture": "arm64", "osVersion": "27.2", "osBuildNumber": "test",
            }}],
        }
        self.tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": method + "()",
                                    "result": "Passed"} for method in methods]}
        self.write("source-sha.txt", PRODUCER + "\n", text=True)
        self.write("simulator.json", {"ownedUDID": UDID})
        self.write(reuse.FILES[1], self.summary)
        self.write(reuse.FILES[2], self.tree)
        self.receipt = {
            "status": "PASS", "profile": reuse.PROFILE, "commit": PRODUCER,
            "scope": "actual_named_apple_test_execution", "observationOnly": False,
            "runnerSHA256": reuse.digest(source(PRODUCER, "Tools/AnyEnginePort/verify_native_test_execution.py")),
            "testSources": {path: reuse.digest(source(PRODUCER, path))
                            for path in reuse.execution.SOURCE_PATHS[reuse.PROFILE]},
            "summarySHA256": reuse.digest((self.directory / reuse.FILES[1]).read_bytes()),
            "testTreeSHA256": reuse.digest((self.directory / reuse.FILES[2]).read_bytes()),
            **reuse.execution.validate(self.summary, self.tree, reuse.PROFILE, UDID),
        }
        self.write(reuse.RECEIPT, self.receipt)

    def write(self, name, value, text=False):
        (self.directory / name).write_text(value if text else json.dumps(value), encoding="utf-8")

    def verify(self, run=RUN_ID):
        return reuse.verify_evidence(self.directory, PRODUCER, run, read_source=source)

    def test_original_fourteen_named_passes_are_accepted_without_relabeling(self):
        actual = self.verify()
        self.assertEqual(actual["commit"], PRODUCER)
        self.assertEqual(actual["counts"]["passedTests"], 14)
        self.assertNotIn("consumerCommit", actual)

    def test_different_producer_run_cannot_borrow_the_owned_device(self):
        with self.assertRaisesRegex(RuntimeError, "original_execution_run_mismatch"):
            self.verify("999")

    def test_changed_result_bytes_are_rejected(self):
        self.summary["passedTests"] = 13
        self.write(reuse.FILES[1], self.summary)
        with self.assertRaisesRegex(RuntimeError, "original_result_digest_mismatch"):
            self.verify()

    def test_failed_method_cannot_be_hidden_behind_passing_summary(self):
        self.tree["testNodes"][0]["result"] = "Skipped"
        self.write(reuse.FILES[2], self.tree)
        self.receipt["testTreeSHA256"] = reuse.digest((self.directory / reuse.FILES[2]).read_bytes())
        self.write(reuse.RECEIPT, self.receipt)
        with self.assertRaisesRegex(RuntimeError, "failed, or skipped"):
            self.verify()

    def test_changed_producer_test_source_or_verifier_is_rejected(self):
        for field in ("runnerSHA256", "testSources"):
            with self.subTest(field=field):
                changed = dict(self.receipt)
                changed[field] = "unverified"
                self.write(reuse.RECEIPT, changed)
                with self.assertRaises(RuntimeError):
                    self.verify()

    def test_receipt_cannot_relabel_actual_counts(self):
        self.receipt["counts"] = {**self.receipt["counts"], "totalTestCount": 15}
        self.write(reuse.RECEIPT, self.receipt)
        with self.assertRaisesRegex(RuntimeError, "original_receipt_result_mismatch_counts"):
            self.verify()

    def test_changed_component_or_dependency_requires_execution(self):
        with patch.object(reuse, "source_tree", side_effect=[{"editor": "old"}, {"editor": "new"}]):
            with self.assertRaisesRegex(RuntimeError, "tested_source_or_dependency_changed"):
                reuse.verify_sources(PRODUCER, "b" * 40)

    def test_dirty_tested_source_cannot_reuse_committed_identity(self):
        with patch.object(reuse, "source_tree", return_value={"editor": "same"}), \
             patch.object(reuse, "git", side_effect=[b"Modules/PinkhaAnyUI/Sources/changed.swift\0", b""]):
            with self.assertRaisesRegex(RuntimeError, "tested_worktree_source_is_dirty"):
                reuse.verify_sources(PRODUCER, "b" * 40)


if __name__ == "__main__":
    unittest.main()
