"""New controller checks only; these never compile or execute native Go code."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import contract


class NativeSemanticControllerTests(unittest.TestCase):
    def test_original_five_are_source_bound_and_retained_without_execution(self):
        value = contract.retained_contract()
        self.assertEqual(value["methods_executed_again"], 0)
        self.assertEqual(set(value["methods"]), contract.CONTRACT_METHODS)
        self.assertFalse(value["native_apply_executed"])

    def test_named_output_rejects_missing_repeated_skipped_and_unselected_cases(self):
        original = [json.loads(line) for line in
                    (contract.HERE / contract.RETAINED / "semantic-contract-controls.jsonl").read_text().splitlines()]
        first_pass = next(index for index, event in enumerate(original) if event.get("Test") and event["Action"] == "pass")
        missing = deepcopy(original); missing.pop(first_pass)
        repeated = deepcopy(original); repeated.insert(first_pass, deepcopy(repeated[first_pass]))
        skipped = deepcopy(original); skipped[first_pass]["Action"] = "skip"
        unselected = deepcopy(original); unselected.insert(first_pass, {"Package": "command-line-arguments", "Action": "run", "Test": "TestPriorUnselected"})
        wrong_package = deepcopy(original); wrong_package[first_pass]["Package"] = "unrelated"
        for label, events in (("missing", missing), ("repeated", repeated), ("skipped", skipped),
                              ("unselected", unselected), ("wrong_package", wrong_package)):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temporary:
                log = Path(temporary) / "changed.jsonl"
                log.write_text("".join(json.dumps(event) + "\n" for event in events))
                with self.assertRaises(ValueError):
                    contract.outcomes(log, "command-line-arguments", {name: () for name in contract.CONTRACT_METHODS})

    def test_candidate_inventory_rejects_changed_source_extra_files_and_old_source_claims(self):
        self.assertEqual(set(contract.source_manifest()), contract.SOURCE_PATHS)
        for scenario in ("changed_source", "extra_source", "changed_original_pin"):
            with self.subTest(case=scenario), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                shutil.copytree(contract.HERE / "native", folder / "native")
                shutil.copyfile(contract.HERE / "native-source.json", folder / "native-source.json")
                if scenario == "changed_source":
                    target = folder / "native/core/pinkha_semantic_anchor.go"
                    target.write_bytes(target.read_bytes() + b"\n")
                elif scenario == "extra_source":
                    (folder / "native/unreviewed.go").write_text("package core\n")
                else:
                    value = json.loads((folder / "native-source.json").read_bytes())
                    value["qualified_patch_sha256"] = "0" * 64
                    (folder / "native-source.json").write_text(json.dumps(value))
                with patch.object(contract, "HERE", folder), self.assertRaises(ValueError):
                    contract.source_manifest()

    def test_selected_methods_are_exactly_the_new_native_declarations(self):
        observed = {}
        for package, cases in contract.CASES.items():
            sources = list((contract.HERE / "native" / package).glob("*_test.go"))
            methods = [name for path in sources for name in re.findall(
                r"^func (Test\w+)\(t \*testing\.T\)", path.read_text(encoding="utf8"), re.MULTILINE)]
            self.assertEqual(set(methods), set(cases))
            self.assertEqual(len(methods), len(set(methods)))
            observed[package] = {"parents": len(cases), "terminals": sum(len(children) or 1 for children in cases.values())}
        self.assertEqual(sum(value["parents"] for value in observed.values()), 9)
        self.assertEqual(sum(value["terminals"] for value in observed.values()), 27)
        self.assertFalse(set().union(*(set(value) for value in contract.CASES.values())) & contract.CONTRACT_METHODS)


if __name__ == "__main__":
    unittest.main()
