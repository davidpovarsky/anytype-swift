"""New continuation controls; never execute any native or prior Python test."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import contract
import resume_native as resume


class NativeWitnessContinuationTests(unittest.TestCase):
    def test_original_failure_retains_exact_seven_and_selects_only_missing_two(self):
        entries = resume.original_archive()
        run = contract.load(contract.ROOT / resume.PROOF_REL / "original-run-metadata.json")
        native139 = json.loads(entries["qualified139-source-before.json"])
        with tempfile.TemporaryDirectory() as directory:
            receipt = resume.retain(run, native139, contract.source_manifest(), Path(directory))
            self.assertEqual(receipt["retained_methods"], 7)
            self.assertEqual(receipt["retained_terminal_cases"], 25)
            self.assertEqual(receipt["retained_methods_executed_again"], 0)
            self.assertEqual(receipt["remaining_selection"], {
                resume.LEASE: {resume.FAILED_METHOD: ()}, "core": {resume.CORE_METHOD: ()}})
            self.assertEqual(receipt["results"][resume.LEASE]["original_package_status"], "FAIL_ONE_EXCLUDED_METHOD")
            self.assertEqual(receipt["original_lease_post_execution_source_guard"], "NOT_REACHED_AFTER_FAILED_PACKAGE")
            self.assertEqual(contract.digest(Path(directory) / "original-native-component-evidence.zip"), resume.ORIGINAL_ZIP_SHA)
            with self.assertRaises(ValueError):
                resume.combine(receipt["results"][resume.LEASE], receipt["results"][resume.LEASE])

    def test_partial_failure_and_original_run_cannot_be_relabelled_or_omit_cases(self):
        data = resume.original_archive()["execute-torahopsobject.log"]
        original = [json.loads(line) for line in data.decode().splitlines()]
        passed = next(i for i, row in enumerate(original) if row.get("Test") and row["Action"] == "pass")
        failed = next(i for i, row in enumerate(original) if row.get("Test") and row["Action"] == "fail")
        for scenario in ("missing_pass", "duplicate_pass", "skipped", "failure_relabelled"):
            rows = deepcopy(original)
            if scenario == "missing_pass":
                rows.pop(passed)
            elif scenario == "duplicate_pass":
                rows.insert(passed, deepcopy(rows[passed]))
            elif scenario == "skipped":
                rows[passed]["Action"] = "skip"
            else:
                rows[failed]["Action"] = "pass"
            with self.subTest(case=scenario), self.assertRaises(ValueError):
                resume.partial_lease_outcome("\n".join(map(json.dumps, rows)).encode())
        run = contract.load(contract.ROOT / resume.PROOF_REL / "original-run-metadata.json")
        for field, wrong in (("head_sha", "0" * 40), ("conclusion", "success"), ("run_attempt", 2)):
            changed = deepcopy(run)
            changed[field] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                resume.validate_run(changed)

    def test_exact_review_rejects_unreviewed_source_input_and_original_archive_bytes(self):
        old = contract.load(contract.ROOT / "docs/validation/20261122-semantic-anchor-native-candidate/controller-controls.json")["source_before_sha256"]
        current = {name: contract.digest(contract.HERE / name) for name in old}
        review = resume.reviewed_controller_inputs(old, current)
        self.assertEqual(set(review["changed_input_hashes"]), {"native/" + name for name in resume.NATIVE_CHANGES} | {"native-source.json"})
        changed = dict(current, **{"contract.py": "0" * 64})
        with self.assertRaises(ValueError):
            resume.reviewed_controller_inputs(old, changed)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / resume.PROOF_REL
            shutil.copytree(contract.ROOT / resume.PROOF_REL, proof)
            here = root / "Tools/PinkhaSemanticAnchor"
            for name in resume.NATIVE_CHANGES:
                target = here / "native" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(contract.HERE / "native" / name, target)
            shutil.copyfile(contract.HERE / "native-source.json", here / "native-source.json")
            with patch.object(contract, "ROOT", root), patch.object(contract, "HERE", here):
                resume.reviewed_native_sources()
                target = here / "native" / next(iter(resume.NATIVE_CHANGES))
                target.write_bytes(target.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    resume.reviewed_native_sources()
                archive = proof / "original-evidence.zip"
                archive.write_bytes(archive.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    resume.original_archive()


if __name__ == "__main__":
    unittest.main()
