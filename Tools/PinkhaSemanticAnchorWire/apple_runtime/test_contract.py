"""Only new Page154 Apple producer controls; retained Go tests never execute."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import contract
import build

ROOT = Path(__file__).resolve().parents[3]


def originals():
    manifest = json.loads((ROOT / contract.MANIFEST_PATH).read_bytes())
    directory = ROOT / contract.PROOF
    build_receipt = json.loads((directory / "build.json").read_bytes())
    acceptance = json.loads((directory / "page-acceptance.json").read_bytes())
    audit = json.loads((directory / "INDEPENDENT_AUDIT.json").read_bytes())
    phases = [json.loads((directory / "page-results" / (phase + ".json")).read_bytes())
              for phase, _ in contract.PHASES]
    return manifest, build_receipt, acceptance, audit, phases


class Page154ProducerControls(unittest.TestCase):
    def test_retains_exact_original154_and_two_named_native_passes(self):
        manifest = contract.candidate(ROOT)
        value = contract.retained_native(ROOT, manifest)
        self.assertEqual(value["status"], "RETAINED_ORIGINAL_PAGE2_PASS_NO_TEST_RERUN")
        self.assertEqual(len(value["source_sha256"]), 154)
        self.assertEqual(value["original_actual_methods"], 2)
        self.assertEqual(value["methods_executed_this_run"], 0)
        self.assertEqual(value["original_distinct_native_pids"], [33558, 33641])
        self.assertIn("Apple Lib.xcframework symbol or app callability", value["original_scope_limits"])

    def test_modified_candidate_manifest_is_rejected_before_source_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / contract.MANIFEST_PATH
            path.parent.mkdir(parents=True)
            value = json.loads((ROOT / contract.MANIFEST_PATH).read_bytes())
            value["files"][contract.SERVICE]["after_sha256"] = "0" * 64
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                contract.candidate(root)

    def test_wrong_source_runtime_binary_or_native_counts_cannot_reuse_receipts(self):
        baseline = originals()
        modifications = [
            (1, "app_sha", "0" * 40), (1, "runtime_version", "old-coherent139"),
            (1, "binary_sha256", "0" * 64), (2, "actual_methods_executed", 0),
            (2, "actual_methods_passed", 0), (2, "actual_methods_executed", True),
            (2, "candidate_sha256", "0" * 64), (2, "apple", "PASS"),
            (2, "mounted_editor", "PASS"), (2, "previous_methods_rerun", 1),
        ]
        for index, key, value in modifications:
            inputs = copy.deepcopy(baseline)
            inputs[index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                contract.native_observations(*inputs)
        inputs = copy.deepcopy(baseline)
        inputs[2]["current_source_sha256"][contract.SERVICE] = "0" * 64
        with self.assertRaises(ValueError):
            contract.native_observations(*inputs)

    def test_same_pid_or_changed_native_object_cannot_claim_cold_reopen(self):
        for field, value in [("pid", 33558), ("create_pid", 777), ("native_change_id", "different"),
                             ("object_id", "another-object"), ("runtime_version", "another-runtime"),
                             ("account_stop_verified", False)]:
            inputs = copy.deepcopy(originals())
            inputs[4][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                contract.native_observations(*inputs)

    def test_named_native_events_reject_zero_wrong_duplicate_failed_or_skipped(self):
        method = contract.PHASES[0][1]
        valid = [{"Package": contract.PACKAGE, "Test": method, "Action": "run"},
                 {"Package": contract.PACKAGE, "Test": method, "Action": "pass"},
                 {"Package": contract.PACKAGE, "Action": "pass"}]
        contract.named_events(valid, method)
        cases = [[], valid[1:], valid + [valid[1]],
                 [dict(row, Test="WrongMethod") if row.get("Test") else row for row in valid],
                 [dict(row, Action="fail") if row.get("Action") == "pass" else row for row in valid],
                 [dict(row, Action="skip") if row.get("Test") and row["Action"] == "pass" else row for row in valid]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                contract.named_events(rows, method)

    def test_changed_native_or_module_bytes_fail_exact_hash_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("service.go", "go.mod"):
                (root / name).write_text("original-" + name)
            expected = {name: contract.digest(root / name) for name in ("service.go", "go.mod")}
            contract.file_hashes(root, expected)
            for name in expected:
                before = (root / name).read_bytes()
                (root / name).write_text("changed")
                with self.subTest(path=name), self.assertRaises(ValueError):
                    contract.file_hashes(root, expected)
                (root / name).write_bytes(before)

    def test_generated_header_requires_real_byte_signature_and_defined_global_symbol(self):
        declaration = "FOUNDATION_EXPORT NSData* _Nullable ServicePinkhaSemanticAnchorCapture(NSData* _Nullable raw);"
        headers = declaration + "\nFOUNDATION_EXPORT void ServicePinkhaTorahAuthorizedOperationRead(void);"
        symbol = "0000000000000128 T _ServicePinkhaSemanticAnchorCapture\n"
        value = contract.generated_entry(headers, symbol)
        self.assertEqual(value["entry"], contract.ENTRY)
        for wrong_header, wrong_symbols in [
            (headers.replace("NSData* _Nullable raw", "NSString* _Nullable raw"), symbol),
            (headers.replace(contract.ENTRY, "ServiceAnotherEntry"), symbol),
            (headers + "\n" + declaration, symbol), (headers, ""),
            (headers, symbol.replace(" T ", " U ")), (headers, symbol + symbol),
            (headers + "\nServicePinkhaCoherentAppleAuthorityFixture", symbol),
        ]:
            with self.subTest(header=wrong_header, symbols=wrong_symbols), self.assertRaises(ValueError):
                contract.generated_entry(wrong_header, wrong_symbols)

    def test_bind_selects_only_new154_production_version_and_simulator(self):
        command = build.bind_command(Path("/owned/heart"), Path("/owned/production/Lib.xcframework"))
        self.assertEqual(command[1], "bind")
        self.assertIn("-target=iossimulator/arm64", command)
        self.assertIn(contract.PACKAGE, command)
        flags = command[command.index("-ldflags") + 1]
        self.assertIn("vcs.GitSummary=" + contract.VERSION, flags)
        self.assertIn("vcs.GitCommit=" + contract.HEART, flags)
        self.assertNotIn("test", command)
        self.assertNotIn("generate", command)
        self.assertNotIn("fixture", command[command.index("-tags") + 1].lower())
        self.assertIn("Lib.ServicePinkhaSemanticAnchorCapture(request)", build.SWIFT_CHECK)

    def test_source_and_proof_paths_cannot_escape_the_owned_root(self):
        for value in ("../outside", "/absolute", "a/../../outside", "a\\outside", "a//b", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.relative(value)


if __name__ == "__main__":
    unittest.main()
