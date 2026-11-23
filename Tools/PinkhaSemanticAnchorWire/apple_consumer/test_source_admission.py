"""Additional new source/native lineage rejection controls, separate from prior12."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import consumer_contract as proof
import run as consumer

ROOT = Path(__file__).resolve().parents[3]


def original_shape():
    manifest = json.loads((ROOT / "Tools/PinkhaSemanticAnchorWire/page-source.json").read_bytes())
    files = json.loads((Path(__file__).parent / "framework-files.json").read_bytes())
    native = {name: row["after_sha256"] for name, row in manifest["files"].items()}
    build = dict(status="BUILT_PAGE154_APPLE_FRAMEWORK_NOT_EXECUTED", phase="COMPLETE",
        app_sha=proof.PRODUCER_SHA, run_id=proof.PRODUCER_RUN, run_attempt="1",
        source_manifest_sha256=proof.MANIFEST_SHA, runtime_version=proof.VERSION,
        native_source_count=154, native_source_sha256=copy.deepcopy(native),
        native_module_sha256=copy.deepcopy(manifest["module_sha256"]), framework_files_sha256=copy.deepcopy(files),
        archive_sha256=proof.ARCHIVE_SHA, archive_bytes=proof.ARCHIVE_BYTES,
        packaged_receipt_sha256=proof.RECEIPT_SHA, native_tests_executed=0,
        old_tests_executed=0, apple_product_tests_executed=0, app_builds=0)
    packaged = dict(status="APPLE_FRAMEWORK_BUILT_NOT_EXECUTED", integration_sha=proof.PRODUCER_SHA,
        github_run_id=proof.PRODUCER_RUN, github_run_attempt="1",
        source_manifest_sha256=proof.MANIFEST_SHA, expected_app_get_version=proof.VERSION,
        native_source_sha256=copy.deepcopy(native), native_module_sha256=copy.deepcopy(manifest["module_sha256"]),
        files_sha256=copy.deepcopy(files), fixture_included=False,
        target_architecture="arm64", target_environment="simulator",
        generated_entry=dict(entry="ServicePinkhaSemanticAnchorCapture",
            swift_typecheck="PASS_ACTUAL_GENERATED_MODULE", runtime_execution="NOT_RUN",
            status="ACTUAL_GENERATED_HEADER_AND_DEFINED_BINARY_SYMBOL"))
    return build, packaged, manifest, files


class SourceAdmissionControls(unittest.TestCase):
    def test_changed_native_source_module_graph_or_framework_producer_refused(self):
        originals = original_shape()
        proof.producer_proof(*originals)
        for owner, field in ((0, "native_source_sha256"), (0, "native_module_sha256"),
                             (1, "files_sha256"), (1, "native_source_sha256")):
            values = copy.deepcopy(originals)
            first = next(iter(values[owner][field]))
            values[owner][field][first] = "0" * 64
            with self.subTest(owner=owner, field=field), self.assertRaises(ValueError):
                proof.producer_proof(*values)
        values = copy.deepcopy(originals); values[1]["fixture_included"] = True
        with self.assertRaises(ValueError): proof.producer_proof(*values)

    def test_exact_checkout_guard_detects_hidden_changed_native_or_module_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for name in ("native-input.go", "module-input.swift"):
                (root / name).write_text("original input\n")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Controller test fixture",
                "-c", "user.email=controller-fixture@example.invalid", "commit", "-qm", "New isolated source-control fixture"], check=True)
            head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            self.assertEqual(len(consumer.checkout_inputs(root, head)), 2)
            for name in ("native-input.go", "module-input.swift"):
                subprocess.run(["git", "-C", str(root), "update-index", "--assume-unchanged", name], check=True)
                (root / name).write_text("altered input\n")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    consumer.checkout_inputs(root, head)
                (root / name).write_text("original input\n")
                subprocess.run(["git", "-C", str(root), "update-index", "--no-assume-unchanged", name], check=True)


if __name__ == "__main__":
    unittest.main()
