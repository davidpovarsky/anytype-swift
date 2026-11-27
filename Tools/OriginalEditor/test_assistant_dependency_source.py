"""Negative controls for the actual reviewed original dependency transition."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from assistant_dependency_source import BASE, LOCK, validate_pin_transition

ROOT = Path(__file__).resolve().parents[2]

class AssistantDependencyControls(unittest.TestCase):
    def setUp(self):
        self.before = json.loads(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", BASE + ":" + LOCK]))
        self.after = json.loads((ROOT / LOCK).read_text())
        self.review = json.loads((ROOT / "Tools/Hanlin/assistant_component_route.json").read_text())["dependencyLock"]

    def check(self):
        return validate_pin_transition(self.before, self.after, self.review)

    def test_actual_reviewed_closure_is_67_with_57_unchanged(self):
        self.assertEqual(self.check()["retained"], 57)

    def test_dropping_a_retained_dependency_is_rejected(self):
        self.after["pins"] = [p for p in self.after["pins"] if p["identity"] != "swift-collections"]
        with self.assertRaises(ValueError): self.check()

    def test_changing_an_unrelated_retained_revision_is_rejected(self):
        next(p for p in self.after["pins"] if p["identity"] == "swift-collections")["state"]["revision"] = "0" * 40
        with self.assertRaises(ValueError): self.check()

    def test_changing_an_added_native_sdk_revision_is_rejected(self):
        next(p for p in self.after["pins"] if p["identity"] == "swift-sdk")["state"]["revision"] = "0" * 40
        with self.assertRaises(ValueError): self.check()

    def test_repeated_dependency_identity_is_rejected(self):
        self.after["pins"][-1] = copy.deepcopy(self.after["pins"][0])
        with self.assertRaises(ValueError): self.check()

    def test_relabeling_an_unreviewed_overlap_is_rejected(self):
        self.review["changed"]["swift-syntax"] = self.review["changed"].pop("swift-log")
        with self.assertRaises(ValueError): self.check()
