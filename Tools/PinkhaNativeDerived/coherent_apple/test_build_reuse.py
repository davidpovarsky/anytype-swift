"""New controller controls for immutable build reuse; no build/XCTest reruns."""
from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import retain_controls
import reuse_build as reuse
import run_host

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL_ZIP = ROOT / "docs/validation/20261122-coherent-heart-apple-build/proof-original.zip"
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


class OriginalBuildReuseControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="coherent-original-proof-controls-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.original = Path(cls.temporary.name) / "original"
        assert ORIGINAL_ZIP.stat().st_size == reuse.ARTIFACTS["proof"]["size_in_bytes"]
        assert reuse.digest(ORIGINAL_ZIP) == reuse.ARTIFACTS["proof"]["zip_sha256"]
        reuse.admission.safe_zip(ORIGINAL_ZIP, cls.original)
        cls.build_raw = (cls.original / "proof/build.json").read_bytes()
        cls.before = reuse.admission.read_json(cls.original / "proof/host/control-source-before.json")

    def record(self, source=None):
        source = self.before if source is None else source
        return dict(schemaVersion=1, status=reuse.STATUS, build_origin=reuse.origin(),
                    execution_origin=dict(source_sha=CURRENT, run_id=CURRENT_RUN, run_attempt="1"),
                    original_build_receipt_sha256=reuse.BUILD_SHA,
                    original_failed_host_receipt_sha256=reuse.FAILED_HOST_SHA,
                    original_artifacts=deepcopy(reuse.ARTIFACTS), frameworks_built_this_run=0,
                    native_tests_executed_this_run=0, production_binary_execution="NOT_RUN",
                    apple_execution="SEPARATE_CURRENT_HOST_REQUIRED", current_control_source_sha256=source,
                    current_control_source_snapshot_sha256=reuse.profiles.json_digest(source),
                    runner_sha256=source.get("Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py"))

    def test_original_failed_host_and_both_built_receipts_remain_authentic(self):
        build, before, modules = reuse.verify_original_proof(self.original)
        self.assertEqual(build["run_id"], reuse.RUN)
        self.assertEqual(build["production_binary_execution"], "NOT_RUN")
        self.assertNotEqual(build["frameworks"]["production"]["binary_sha256"],
                            build["frameworks"]["fixture"]["binary_sha256"])
        self.assertEqual(before, self.before)
        self.assertTrue(modules)
        with tempfile.TemporaryDirectory(prefix="coherent-original-proof-tamper-") as directory:
            changed = Path(directory) / "proof"
            shutil.copytree(self.original, changed)
            receipt = changed / "proof/host/receipt.json"
            value = reuse.admission.read_json(receipt)
            value["status"] = reuse.admission.APPLE_PASS
            receipt.write_bytes(encoded(value))
            with self.assertRaisesRegex(RuntimeError, "Original build or failed host receipt changed"):
                reuse.verify_original_proof(changed)

    def test_original_run_and_artifact_context_cannot_be_relabelled(self):
        run, listing = metadata()
        self.assertEqual(set(reuse.validate_original_metadata(run, listing)), set(reuse.ARTIFACTS))
        for key, wrong in (("conclusion", "success"), ("run_attempt", 2), ("head_sha", CURRENT),
                           ("head_branch", "develop"), ("path", ".github/workflows/arbitrary.yml"),
                           ("display_title", "Pinkha coherent-heart-native · " + reuse.SOURCE)):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                reuse.validate_original_metadata(dict(run, **{key: wrong}), listing)
        for key, wrong in (("id", 1), ("expired", True), ("size_in_bytes", 1), ("digest", "sha256:" + "0" * 64)):
            changed = deepcopy(listing); changed["artifacts"][0][key] = wrong
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                reuse.validate_original_metadata(run, changed)
        changed = deepcopy(listing); changed["artifacts"][1]["workflow_run"]["head_sha"] = CURRENT
        with self.assertRaises(RuntimeError):
            reuse.validate_original_metadata(run, changed)

    def test_source_closure_allows_only_reviewed_controllers_and_rejects_compiled_changes(self):
        current = dict(self.before)
        for name in reuse.ALLOWED_CONTROL_CHANGES:
            current[name] = "a" * 64
        unchanged, changes = reuse.verify_control_maps(self.before, current)
        self.assertEqual({entry["path"] for entry in changes}, set(reuse.ALLOWED_CONTROL_CHANGES))
        self.assertTrue(all(unchanged[name] == sha for name, sha in self.before.items()
                            if name.startswith("Modules/")))
        for name in ("Tools/PinkhaNativeDerived/coherent_apple/fixture_bridge.go",
                     "Tools/PinkhaNativeDerived/coherent_apple/HostTests/CoherentHeartAuthorityTests.swift",
                     next(name for name in self.before if name.startswith("Modules/PinkhaKit/")),
                     next(name for name in self.before if name.startswith("Modules/PinkhaHeartEngine/")),
                     "Tools/PinkhaNativeDerived/unreviewed_new_builder.py"):
            changed = dict(current); changed[name] = "f" * 64
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, "Compiled native|shared module"):
                reuse.verify_control_maps(self.before, changed)
        changed = dict(current); del changed[next(name for name in self.before if name.startswith("Modules/"))]
        with self.assertRaises(RuntimeError):
            reuse.verify_control_maps(self.before, changed)

    def test_lineage_keeps_original_bytes_and_requires_the_current_host_source(self):
        current = dict(self.before, **{"Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py": "a" * 64})
        record = self.record(current)
        self.assertEqual(reuse.validate_reuse_record(record, self.build_raw, CURRENT, CURRENT_RUN, "1"), reuse.origin())
        mutations = [lambda value: value["build_origin"].update(workflow_conclusion="success"),
                     lambda value: value["execution_origin"].update(run_id=reuse.RUN),
                     lambda value: value.update(frameworks_built_this_run=1),
                     lambda value: value.update(native_tests_executed_this_run=False),
                     lambda value: value.update(production_binary_execution="PASS"),
                     lambda value: value.update(runner_sha256="b" * 64)]
        for mutate in mutations:
            changed = deepcopy(record); mutate(changed)
            with self.assertRaises(RuntimeError):
                reuse.validate_reuse_record(changed, self.build_raw, CURRENT, CURRENT_RUN, "1")
        with self.assertRaises(RuntimeError):
            reuse.validate_reuse_record(record, self.build_raw + b" ", CURRENT, CURRENT_RUN, "1")
        with tempfile.TemporaryDirectory(prefix="coherent-host-lineage-control-") as directory:
            root = Path(directory); build = root / "build.json"; line = root / "build-reuse.json"
            build.write_bytes(self.build_raw); line.write_bytes(encoded(record))
            with patch.object(run_host, "source_snapshot", return_value=current):
                self.assertEqual(reuse.validate_host_lineage(root, build, line, CURRENT, CURRENT_RUN, "1"), reuse.origin())
            with patch.object(run_host, "source_snapshot", return_value=dict(current, unexpected="b" * 64)):
                with self.assertRaisesRegex(RuntimeError, "Current host controller source changed"):
                    reuse.validate_host_lineage(root, build, line, CURRENT, CURRENT_RUN, "1")

    def test_fixture_extraction_never_uses_a_production_root_or_unsafe_member(self):
        with tempfile.TemporaryDirectory(prefix="coherent-reuse-archive-controls-") as directory:
            root = Path(directory)
            def archive(name, receipt, extra=None):
                target = root / (name + ".tar.gz")
                with tarfile.open(target, "w:gz") as packed:
                    for path in ("Lib.xcframework/test", receipt):
                        item = tarfile.TarInfo(path); raw = b"controller input"; item.size = len(raw)
                        packed.addfile(item, io.BytesIO(raw))
                    if extra is not None:
                        packed.addfile(extra)
                return target
            for kind, receipt in reuse.RECEIPTS.items():
                target = root / kind
                reuse.extract_runtime(archive(kind, receipt), target, kind)
                self.assertEqual((target / receipt).read_bytes(), b"controller input")
            wrong = archive("wrong", reuse.RECEIPTS["fixture"])
            with self.assertRaises(RuntimeError):
                reuse.extract_runtime(wrong, root / "wrong-root", "production")
            for index, name in enumerate(("../escape", "/absolute", "Lib.xcframework/link")):
                item = tarfile.TarInfo(name)
                if index == 2:
                    item.type = tarfile.SYMTYPE; item.linkname = "/outside"
                with self.subTest(name=name), self.assertRaises(RuntimeError):
                    reuse.extract_runtime(archive("unsafe" + str(index), reuse.RECEIPTS["fixture"], item),
                                          root / ("unsafe" + str(index)), "fixture")

    def test_retained_host_ast_pins_imports_executed_bodies_and_declaration_side_effects(self):
        path = Path(__file__).with_name("run_host.py")
        scope = retain_controls.host_control_scope(path)
        self.assertEqual(scope["unchanged_control_ast_sha256"], retain_controls.HOST_CONTROL_AST_SHA)
        source = path.read_text(encoding="utf8")
        mutations = [source.replace("0 < len(raw) <= 4096", "0 < len(raw) <= 8192", 1),
                     source.replace("import hashlib\n", "import hashlib as unexpected\n", 1),
                     source + "\nfields = lambda raw: []\n",
                     source.replace("def load_helpers():", "def load_helpers(side_effect=print('changed')):", 1),
                     source + "\ndef fields(raw):\n    return []\n"]
        with tempfile.TemporaryDirectory(prefix="retained-host-scope-tamper-") as directory:
            target = Path(directory) / "run_host.py"
            for changed in mutations:
                self.assertNotEqual(changed, source)
                target.write_text(changed, encoding="utf8")
                with self.assertRaises(ValueError):
                    retain_controls.host_control_scope(target)


if __name__ == "__main__":
    unittest.main()
