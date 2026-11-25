"""Source and compiler-cache integrity controls; not native file acceptance."""
import copy
import json
from pathlib import Path
import unittest
import native_files_source as source
import qualified_cache_seed as cache

HERE = Path(__file__).resolve().parent


class NativeFileSourceControls(unittest.TestCase):
    def document(self):
        value = json.loads((HERE / "MiniApps/native_files_source_adoption.json").read_text())
        binding = {"path": source.RELATIVE, "reviewed_source": source.REVIEWED}
        return value, binding

    def test_exact_three_source_paths_are_required(self):
        value, binding = self.document()
        self.assertEqual([row["path"] for row in source.validate_document(value, binding)], list(source.FILES))

    def test_missing_extra_reordered_or_native_paths_are_rejected(self):
        original, binding = self.document()
        variants = [original["files"][:-1], original["files"] + [original["files"][0]],
                    list(reversed(original["files"]))]
        wrong = copy.deepcopy(original["files"])
        wrong[0]["path"] = "Modules/ProtobufMessages/Sources/Generated.swift"
        variants.append(wrong)
        for rows in variants:
            with self.subTest(paths=[r["path"] for r in rows]):
                value = copy.deepcopy(original); value["files"] = rows
                with self.assertRaises(ValueError):
                    source.validate_document(value, binding)

    def test_source_provenance_cannot_claim_native_acceptance(self):
        value, binding = self.document()
        value["native_acceptance_reused_by_this_document"] = True
        with self.assertRaises(ValueError):
            source.validate_document(value, binding)

    def fixture(self):
        delta = json.loads((HERE / "MiniApps/qualified_cache_seed.json").read_text())["native_files_continuation"]
        names = sorted(list(source.FILES) + ["OriginalEditorFramework/unchanged-%02d.swift" % i for i in range(20)])
        old = {"framework_facade_sources": names, "original_trees": {"native": "same"},
               "source_inputs": {name: {"sha256": "unchanged", "git_blob": "same", "bytes": 9} for name in names},
               "public_host_contract_sha256": delta["previous_contract_sha256"]}
        for row in delta["files"]: old["source_inputs"][row["path"]] = row["before"]
        current = copy.deepcopy(old)
        current["public_host_contract_sha256"] = delta["current_contract_sha256"]
        for row in delta["files"]: current["source_inputs"][row["path"]] = row["after"]
        current["generated_import_source"] = {"annotation_exchange": {"miniapps": {"lifecycle_batch": {"native_files": {
            "reviewed_source": source.REVIEWED, "adoption_sha256": delta["adoption_sha256"],
            "native_acceptance_reused_by_this_document": False}}}}}
        return current, old, {"native_files_continuation": delta}

    def test_exact_facade_delta_is_only_compiler_input(self):
        current, old, policy = self.fixture()
        self.assertEqual(cache.verify_facade_records(current, old, policy), list(source.FILES))

    def test_unreviewed_facade_or_native_mutation_is_rejected(self):
        current, old, policy = self.fixture()
        for mutate in [
            lambda v: v["source_inputs"]["OriginalEditorFramework/unchanged-01.swift"].update(sha256="other"),
            lambda v: v["source_inputs"][source.FILES[0]].update(sha256="other"),
            lambda v: v["original_trees"].update(native="other"),
            lambda v: v["framework_facade_sources"].append("OriginalEditorFramework/unreviewed.swift"),
            lambda v: v.update(public_host_contract_sha256="other"),
        ]:
            value = copy.deepcopy(current); mutate(value)
            with self.assertRaises(RuntimeError): cache.verify_facade_records(value, old, policy)

    def test_historical_abi_source_cannot_be_relabelled_as_current(self):
        current, old, policy = self.fixture()
        current["generated_import_source"]["annotation_exchange"]["miniapps"]["lifecycle_batch"]["native_files"]["reviewed_source"] = "0" * 40
        with self.assertRaises(RuntimeError): cache.verify_facade_records(current, old, policy)


if __name__ == "__main__":
    unittest.main()
