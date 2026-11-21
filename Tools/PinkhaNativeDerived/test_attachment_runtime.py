"""Admission controls for corrected-runtime composition; no native tests are simulated."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

import attachment_runtime as runtime
import build_t5_r15_runtime as builder


class AttachmentRuntimeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = Path(__file__).resolve().parents[2]
        cls.repository = Path(os.environ.get("T5_ATTACHMENT_SOURCE_REPOSITORY", cls.control)).resolve()
        cls.bases = {}
        for variant, config in runtime.VARIANTS.items():
            approval = runtime.APPROVAL_ROOT + "/revision-" + str(config["revision"])
            cls.bases[variant] = (
                runtime.frozen_blob(cls.repository, approval + "/native-heart-integration.patch"),
                runtime.frozen_blob(cls.repository, approval + "/native-heart-integration.json"),
            )
        cls.candidate = (
            (cls.control / runtime.CANDIDATE_ROOT / "native-heart-integration.patch").read_bytes(),
            (cls.control / runtime.CANDIDATE_ROOT / "native-heart-integration.json").read_bytes(),
        )

    def compose(self, variant="r15-attachment-v1", *, base=None, candidate=None):
        return runtime.compose(variant, *(base or self.bases[variant]), *(candidate or self.candidate))

    def test_r14_is_exactly_the_original_native_pass_not_a_recreated_claim(self):
        result = self.compose("r14-attachment-v1")
        self.assertEqual(result.patch, runtime.normalized(self.candidate[0]))
        self.assertEqual(result.patch_sha256, runtime.CANDIDATE_PATCH_SHA)
        original = json.loads(self.candidate[1])
        inventory = json.loads(result.inventory)
        self.assertEqual(inventory["files"], original["files"])
        self.assertEqual(len(inventory["files"]), 37)
        self.assertEqual(result.lookup_capability, 0)
        self.assertNotIn("pinkha-native-t5-lookup", result.version)
        self.assertEqual(inventory["correction_provenance"]["native_package_proof_scope"], "EXACT_TESTED_R14_SOURCE")

    def test_r15_retains_every_lookup_section_and_changes_only_one_source_plus_two_fixtures(self):
        result = self.compose()
        original = runtime.sections(self.bases[result.variant][0])
        composed = runtime.sections(result.patch)
        unchanged = set(original) - set(runtime.FIXED_FILES)
        self.assertTrue(unchanged)
        for path in unchanged:
            self.assertEqual(composed[path], original[path], path)
        self.assertEqual(set(composed) - set(original), {
            "core/block/editor/basic/pinkha_torah_attachment_test.go",
            "core/block/detailservice/pinkha_torah_attachment_test.go",
        })
        before = runtime.file_inventory(json.loads(self.bases[result.variant][1]))
        after = runtime.file_inventory(json.loads(result.inventory))
        self.assertEqual({p for p in before if before[p] != after[p]}, {runtime.DETAILS})
        self.assertEqual(len(after), 44)
        self.assertEqual(result.lookup_capability, 1)
        self.assertIn("core/pinkha/torah/related_sources_test.go", after)
        self.assertEqual(json.loads(result.inventory)["correction_provenance"]["native_package_proof_scope"],
                         "CORRECTION_IDENTICAL_COMBINED_R15_NOT_RUN")

    def test_complete_r14_candidate_cannot_be_substituted_for_r15(self):
        with self.assertRaises(RuntimeError):
            self.compose(base=self.bases["r14-attachment-v1"])
        with self.assertRaises(RuntimeError):
            self.compose(base=self.candidate)

    def test_changed_immutable_sources_or_unproven_correction_are_rejected(self):
        base = self.bases["r15-attachment-v1"]
        for index in range(3):
            values = [base[0], base[1], self.candidate[0]]
            values[index] += b"\n"
            with self.subTest(input=index), self.assertRaises(RuntimeError):
                self.compose(base=tuple(values[:2]), candidate=(values[2], self.candidate[1]))

    def test_hashes_are_stable_across_windows_checkout_line_endings(self):
        original = self.compose()
        crlf = lambda value: runtime.normalized(value).replace(b"\n", b"\r\n")
        transformed = self.compose(base=tuple(map(crlf, self.bases[original.variant])),
                                   candidate=tuple(map(crlf, self.candidate)))
        self.assertEqual(transformed, original)

    def test_fixture_and_details_identity_cannot_be_changed_in_inventory(self):
        for path in runtime.FIXED_FILES:
            for field in ("before_sha256", "after_sha256"):
                candidate = json.loads(self.candidate[1])
                entry = next(e for e in candidate["files"] if e["path"] == path)
                entry[field] = "0" * 64
                with self.subTest(path=path, field=field), self.assertRaises(RuntimeError):
                    self.compose(candidate=(self.candidate[0], json.dumps(candidate).encode()))

    def test_duplicate_or_missing_correction_inventory_file_is_rejected(self):
        for duplicate in (False, True):
            candidate = json.loads(self.candidate[1])
            if duplicate:
                candidate["files"].append(candidate["files"][0])
            else:
                candidate["files"].pop()
            with self.subTest(duplicate=duplicate), self.assertRaises(RuntimeError):
                self.compose(candidate=(self.candidate[0], json.dumps(candidate).encode()))

    def test_new_source_identity_never_relabels_legacy_runtime_or_claims_acceptance(self):
        for variant in runtime.VARIANTS:
            result = self.compose(variant)
            inventory = json.loads(result.inventory)
            self.assertNotEqual(result.patch_sha256, runtime.VARIANTS[variant]["patch_sha256"])
            self.assertTrue(result.version.endswith("-pinkha-torah-attachment-v1-" + result.patch_sha256))
            self.assertIn(result.patch_sha256, result.version)
            proof = inventory["correction_provenance"]
            self.assertFalse(proof["full_t5_acceptance"])
            self.assertEqual(proof["apple_runtime"], "NOT_RUN")
            self.assertEqual(proof["account_pair"], "NOT_RUN")
            self.assertEqual(proof["original_r14_r15_write_compatibility"], "KNOWN_ATTACHMENT_DRIFT_NOT_PROVEN")

    def test_output_cannot_overwrite_an_existing_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / "existing"
            sentinel.write_text("preserve")
            with self.assertRaises(RuntimeError):
                self.compose().write(root)
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_legacy_builder_selection_keeps_original_identity_and_artifact_name(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            approval = source / runtime.APPROVAL_ROOT / "revision-15"
            approval.mkdir(parents=True)
            for name, raw in zip(("native-heart-integration.patch", "native-heart-integration.json"),
                                 self.bases["r15-attachment-v1"]):
                (approval / name).write_bytes(raw)
            selected = builder.select_runtime_inputs(source, self.control, source / "proof")
            self.assertEqual(selected.version, builder.VERSION)
            self.assertEqual(selected.patch_sha256, builder.coverage.PATCH)
            self.assertEqual(selected.inventory_sha256, builder.INVENTORY_SHA)
            self.assertEqual(selected.artifact_name, "Pinkha-Universal-Verified-Heart-r15.tar.gz")
            self.assertEqual(selected.lookup_capability, 1)

    def test_corrected_builder_requires_frozen_profile_and_exact_full_version(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = builder.select_runtime_inputs(self.repository, self.control, Path(directory), "r15-attachment-v1")
            self.assertEqual(selected.patch_sha256, self.compose().patch_sha256)
            self.assertEqual(selected.version, self.compose().version)
            self.assertEqual(selected.artifact_name, "Pinkha-Universal-Verified-Heart-r15-attachment-v1.tar.gz")
            self.assertNotEqual(selected.version, builder.VERSION)
            self.assertEqual(selected.inventory["runtime_variant"], "r15-attachment-v1")

    def test_dependency_reuse_records_original_baseline_and_actual_corrected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = builder.select_runtime_inputs(self.repository, self.control, Path(directory), "r15-attachment-v1")
            original = builder.post_tidy_source_inputs()
            preparation = {"source_inputs": copy.deepcopy(original)}
            builder.bind_corrected_dependency_provenance(preparation, selected)
            self.assertEqual(preparation["dependency_baseline_source_inputs"], original)
            self.assertEqual(preparation["source_inputs"]["patch_sha256"], selected.patch_sha256)
            self.assertNotEqual(preparation["source_inputs"]["patch_sha256"], original["patch_sha256"])
            self.assertEqual(preparation["source_composition"]["replaced_or_added_files"], sorted(runtime.FIXED_FILES))

    def test_corrected_slice_validation_rejects_legacy_or_partly_corrected_framework(self):
        plist = {"AvailableLibraries": [
            {"LibraryIdentifier": "ios-arm64", "LibraryPath": "Lib.framework",
             "SupportedPlatform": "ios", "SupportedArchitectures": ["arm64"]},
            {"LibraryIdentifier": "ios-arm64_x86_64-simulator", "LibraryPath": "Lib.framework",
             "SupportedPlatform": "ios", "SupportedPlatformVariant": "simulator",
             "SupportedArchitectures": ["arm64", "x86_64"]},
        ]}
        version = self.compose().version
        slices = [dict(path=path, architecture=arch, sha256="a" * 64, marker=version)
                  for path, arch in sorted(builder.EXPECTED_SLICES)]
        self.assertEqual(builder.validate_framework(plist, slices, version)["verified_architecture_count"], 3)
        for index in range(3):
            foreign = copy.deepcopy(slices)
            foreign[index]["marker"] = builder.VERSION
            with self.subTest(slice=index), self.assertRaises(RuntimeError):
                builder.validate_framework(plist, foreign, version)
        with self.assertRaises(RuntimeError):
            builder.validate_framework(plist, slices)

    def focused_events(self):
        basic = "github.com/anyproto/anytype-heart/core/block/editor/basic"
        details = "github.com/anyproto/anytype-heart/core/block/detailservice"
        top = "TestTorahOrdinaryDetailsDoNotAttachProjectedProperties"
        names = [(basic, top), (details, "TestTorahExplicitAttachmentsSurviveOrdinaryDetailsEdits")]
        names += [(basic, top + "/" + api + "/" + attached)
                  for api in ("SetDetails", "UpdateDetails")
                  for attached in ("unattached", "explicit-source-already-attached")]
        events = []
        for package, name in names:
            events += [dict(Package=package, Test=name, Action="run"),
                       dict(Package=package, Test=name, Action="pass")]
        events += [dict(Package=package, Action="pass") for package in (basic, details)]
        return events

    def qualify(self, events):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "synthetic-controller-input.log"
            log.write_text("".join(json.dumps(event) + "\n" for event in events))
            return builder.qualify_corrected_fixtures(log)

    def test_exact_focused_fixture_inventory_is_admitted_with_correct_counts(self):
        result = self.qualify(self.focused_events())
        self.assertEqual(result["native_test_methods"], 2)
        self.assertEqual(result["native_test_and_subtest_records"], 6)
        self.assertEqual(result["status"], "PASS_COMBINED_RUNTIME_ATTACHMENT_FIXTURES")

    def test_missing_duplicate_failed_skipped_or_extra_native_records_are_rejected(self):
        for mode in ("missing", "duplicate", "fail", "skip", "extra"):
            events = self.focused_events()
            if mode == "missing":
                del events[:2]
            elif mode == "duplicate":
                events += events[:2]
            elif mode in ("fail", "skip"):
                events[1]["Action"] = mode
            else:
                events += [dict(Package=events[0]["Package"], Test="UnselectedNativeTest", Action=action)
                           for action in ("run", "pass")]
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                self.qualify(events)


if __name__ == "__main__":
    unittest.main(verbosity=2)
