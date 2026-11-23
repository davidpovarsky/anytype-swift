"""New schema-2 composition/retention controls only; no old suite or Apple run."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import reuse_build as reuse
import run_host

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import retain_current_composition_controls as retention

PROOF = ROOT / "docs/validation/20261122-coherent-heart-apple-build/proof-original.zip"
EVIDENCE = ROOT / retention.EVIDENCE
CURRENT = "a" * 40
CURRENT_RUN = "999123"


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def metadata():
    run = dict(id=int(reuse.RUN), run_attempt=1, head_sha=reuse.SOURCE, head_branch=reuse.BRANCH,
               status="completed", conclusion="failure", repository={"full_name": reuse.REPOSITORY},
               event="workflow_dispatch", path=reuse.WORKFLOW,
               display_title="Pinkha coherent-heart-apple · " + reuse.SOURCE)
    items = [dict(id=value["id"], name=value["name"], size_in_bytes=value["size_in_bytes"],
                  digest="sha256:" + value["zip_sha256"], expired=False,
                  workflow_run=dict(id=int(reuse.RUN), head_sha=reuse.SOURCE, head_branch=reuse.BRANCH))
             for value in reuse.ARTIFACTS.values()]
    return run, dict(total_count=3, artifacts=items)


class CurrentCompositionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert reuse.digest(PROOF) == reuse.ARTIFACTS["proof"]["zip_sha256"]
        with zipfile.ZipFile(PROOF) as archive:
            cls.before = json.loads(archive.read("proof/host/control-source-before.json"))
            cls.build_raw = archive.read("proof/build.json")
        cls.current = run_host.source_snapshot(ROOT)
        cls.review = json.loads((EVIDENCE / "source-review.json").read_bytes())

    def record(self):
        unchanged, controls, composition = reuse.verify_source_lineage(self.before, self.current)
        return dict(schemaVersion=2, status=reuse.COMPOSITION_STATUS, build_origin=reuse.origin(),
            execution_origin=dict(source_sha=CURRENT, run_id=CURRENT_RUN, run_attempt="1"),
            original_build_receipt_sha256=reuse.BUILD_SHA, original_failed_host_receipt_sha256=reuse.FAILED_HOST_SHA,
            original_artifacts=deepcopy(reuse.ARTIFACTS), frameworks_built_this_run=0,
            native_tests_executed_this_run=0, production_binary_execution="NOT_RUN",
            apple_execution="SEPARATE_CURRENT_HOST_REQUIRED", current_control_source_sha256=self.current,
            current_control_source_snapshot_sha256=reuse.profiles.json_digest(self.current),
            unchanged_source_sha256=unchanged, reviewed_control_changes=controls,
            copied_module_sha256=reuse.module_sources(self.current), shared_module_lineage=composition,
            runner_sha256=self.current["Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py"])

    def test_exact_composition_requires_new_swift_proof_with_unchanged_native_origin(self):
        record = self.record()
        self.assertEqual(reuse.validate_reuse_record(record, self.build_raw, CURRENT, CURRENT_RUN, "1"), reuse.origin())
        lineage = record["shared_module_lineage"]
        self.assertEqual(len(lineage["original_module_sha256"]), 112)
        self.assertEqual(len(record["copied_module_sha256"]), 116)
        self.assertNotEqual(lineage["original_module_sha256"], record["copied_module_sha256"])
        self.assertTrue(lineage["current_harness_build_required"])
        self.assertFalse(lineage["previous_swift_acceptance_reused"])
        self.assertEqual(lineage["actual_composition_method"], reuse.admission.METHOD)
        self.assertEqual(record["frameworks_built_this_run"], 0)
        self.assertEqual(record["native_tests_executed_this_run"], 0)
        self.assertIn("Tools/PinkhaNativeDerived/coherent_apple/fixture_bridge.go", record["unchanged_source_sha256"])
        self.assertEqual({row["path"] for row in lineage["reviewed_module_changes"]}, reuse.REVIEWED_MODULE_CHANGES.keys())
        with self.assertRaises(RuntimeError):
            reuse.verify_control_maps(self.before, self.current)

    def test_changed_native_harness_module_or_controller_bytes_are_rejected(self):
        mutations = [
            "Tools/PinkhaNativeDerived/coherent_apple/build.py",
            "Tools/PinkhaNativeDerived/coherent_apple/fixture_bridge.go",
            "Tools/PinkhaNativeDerived/coherent_apple/HostTests/CoherentHeartAuthorityTests.swift",
            "Tools/PinkhaNativeDerived/coherent_apple/HarnessPackage.swift",
            next(name for name in self.before if name.startswith("Tools/TorahNativeOperations/")),
            next(name for name in self.before if name.startswith("Modules/PinkhaHeartEngine/")),
            "Modules/PinkhaKit/Sources/PinkhaKit/unreviewed.swift",
            *reuse.REVIEWED_MODULE_CHANGES, *reuse.REVIEWED_COMPOSITION_CONTROLS,
        ]
        for name in mutations:
            changed = dict(self.current, **{name: "f" * 64})
            with self.subTest(path=name), self.assertRaises(RuntimeError):
                reuse.verify_source_lineage(self.before, changed)
        for name in (*reuse.REVIEWED_MODULE_CHANGES, *reuse.REVIEWED_COMPOSITION_CONTROLS):
            changed = dict(self.before, **{name: "f" * 64})
            with self.subTest(original_path=name), self.assertRaises(RuntimeError):
                reuse.verify_source_lineage(changed, self.current)
        changed = dict(self.current); del changed[reuse.COMPOSITION_CONTROL]
        with self.assertRaises(RuntimeError):
            reuse.verify_source_lineage(self.before, changed)

    def test_record_rejects_relabelled_build_and_old_or_unreviewed_current_modules(self):
        mutations = [
            lambda value: value.update(status=reuse.STATUS),
            lambda value: value.update(schemaVersion=2.0),
            lambda value: value.update(copied_module_sha256=reuse.module_sources(self.before)),
            lambda value: value["shared_module_lineage"].update(previous_swift_acceptance_reused=True),
            lambda value: value["shared_module_lineage"].update(current_harness_build_required=False),
            lambda value: value["shared_module_lineage"].update(current_module_map_sha256="f" * 64),
            lambda value: value["build_origin"].update(source_sha=CURRENT),
            lambda value: value["execution_origin"].update(run_id=reuse.RUN),
            lambda value: value.update(native_tests_executed_this_run=1),
        ]
        for index, mutate in enumerate(mutations):
            value = deepcopy(self.record()); mutate(value)
            with self.subTest(mutation=index), self.assertRaises(RuntimeError):
                reuse.validate_reuse_record(value, self.build_raw, CURRENT, CURRENT_RUN, "1")

    def test_admission_reconstructs_original_bytes_but_returns_current_executed_modules(self):
        with tempfile.TemporaryDirectory(prefix="current-composition-admission-") as directory:
            root = Path(directory); original = root / "original"
            reuse.admission.safe_zip(PROOF, original)
            proof = root / "proof"
            reuse.copy_original_proof(original, proof)
            archived = proof / "build-origin"; archived.mkdir()
            shutil.copyfile(PROOF, archived / "proof-original.zip")
            run, listing = metadata()
            (archived / "original-producer-run.json").write_bytes(encoded(run))
            (archived / "original-artifact-list.json").write_bytes(encoded(listing))
            record = self.record()
            (proof / "build-reuse.json").write_bytes(encoded(record))
            work, evidence = root / "work", root / "evidence"; work.mkdir(); evidence.mkdir()
            calls = []
            def command(argv, output, timeout):
                calls.append(argv)
                output.write_bytes(encoded(listing if "/artifacts?" in argv[-1] else run))
            execution = dict(source_sha=CURRENT, run_id=CURRENT_RUN, run_attempt="1",
                             repository=reuse.REPOSITORY, source_branch=reuse.BRANCH)
            result = reuse.validate_admission_lineage(proof, execution, work, evidence, command)
            self.assertEqual(result["build_producer"], reuse.origin())
            self.assertEqual(result["modules"], reuse.module_sources(self.current))
            self.assertNotEqual(result["modules"], reuse.module_sources(self.before))
            self.assertEqual((proof / "build.json").read_bytes(), self.build_raw)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(argv[:2] == ["gh", "api"] for argv in calls))
            changed = deepcopy(record)
            changed["copied_module_sha256"] = reuse.module_sources(self.before)
            (proof / "build-reuse.json").write_bytes(encoded(changed))
            with self.assertRaises(RuntimeError):
                reuse.validate_admission_lineage(proof, execution, root / "unused", evidence, command)

    def test_current_host_requires_the_exact_new_source_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="current-composition-host-") as directory:
            root = Path(directory); build = root / "build.json"; record = root / "build-reuse.json"
            build.write_bytes(self.build_raw); record.write_bytes(encoded(self.record()))
            with patch.object(run_host, "source_snapshot", return_value=self.current):
                self.assertEqual(reuse.validate_host_lineage(root, build, record, CURRENT, CURRENT_RUN, "1"), reuse.origin())
            changed = dict(self.current)
            changed[next(iter(reuse.REVIEWED_MODULE_CHANGES))] = "f" * 64
            with patch.object(run_host, "source_snapshot", return_value=changed), self.assertRaises(RuntimeError):
                reuse.validate_host_lineage(root, build, record, CURRENT, CURRENT_RUN, "1")

    def test_retention_restores_only_exact_original_tested_ast_and_constants(self):
        self.assertEqual({row["path"] for row in self.review["reviewed_sources"]}, retention.SOURCE_PATHS)
        for row in self.review["reviewed_sources"]:
            before, current = (ROOT / row["original_path"]).read_bytes(), (ROOT / row["path"]).read_bytes()
            restored = retention.restore_retained_source(current, before, row)
            self.assertEqual(restored, before)
            self.assertEqual(retention.ast_digest(restored), row["original_ast_sha256"])

    def test_retention_rejects_tampered_new_branch_helper_and_legacy_constant_even_with_new_file_hash(self):
        row = next(value for value in self.review["reviewed_sources"] if value["path"] == retention.REUSE)
        before = (ROOT / row["original_path"]).read_bytes()
        text = (ROOT / row["path"]).read_text()
        mutations = [
            text.replace('record.get("schemaVersion") == 2:', 'record.get("schemaVersion") >= 2:', 1),
            text.replace("len(original) == 112", "len(original) == 113", 1),
            text.replace('STATUS = "VERIFIED_ORIGINAL_COHERENT_APPLE_BUILD_REUSE"',
                         'STATUS = "UNREVIEWED_LEGACY_STATUS"', 1),
            text + "\ndef unreviewed_native_admission():\n    return True\n",
        ]
        for index, changed in enumerate(mutations):
            self.assertNotEqual(changed, text)
            raw = changed.encode()
            altered_review = dict(row, after_sha256=retention.sha(raw))
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                retention.restore_retained_source(raw, before, altered_review)


if __name__ == "__main__":
    unittest.main()
