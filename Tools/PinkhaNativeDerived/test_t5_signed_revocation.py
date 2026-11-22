"""Small rejection controls; synthetic fixtures do not certify native access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import t5_signed_revocation as gate

IDENTITY = dict(heart_sha=gate.HEART, runtime_version="fixture-runtime", fixture_sha256="a" * 64)
PID = 123
NONCE = "b" * 32


def observation():
    value = dict(protocol=gate.PROTOCOL, nonce=NONCE, pid=PID, **IDENTITY,
        account_id_sha256="c" * 64, space_id_sha256="d" * 64, object_id_sha256="e" * 64, canonical_sha256="f" * 64,
        same_engine_account=True, populated_native_cache=True, reader_positive=True,
        signed_acl_add_head="fixture-add", signed_acl_transfer_head="fixture-transfer", signed_acl_remove_head="fixture-remove",
        current_permission="none", had_read_permission=True, read_key_rotated=True,
        read_key_id_before="fixture-before", read_key_id_after="fixture-after",
        native_acl_updater="NOT_REPLACED_OR_SUPPRESSED", local_signed_delivery=True,
        object_search_error_code=2, object_search_error_description=gate.DENIED_DESCRIPTION,
        object_search_rows=0, object_search_total=0, object_search_explicit_denial=True,
        object_show_error_code=2, object_show_error_description=gate.DENIED_DESCRIPTION,
        object_show_has_payload=False, object_show_explicit_denial=True,
        account_stop_verified=True, network_acl_transport="NOT_RUN", offline_unknown_revocation="NOT_PROVEN",
        ios_acceptance="NOT_RUN", full_t5_acceptance="NOT_PROVEN", status=gate.PASS)
    value["rpc_calls"] = dict(InitialSetParameters=1, AppGetVersion=1, WalletCreate=1, AccountCreate=1,
        WorkspaceCreate=1, WorkspaceOpen=1, ObjectCreateRelation=1, ObjectCreateObjectType=3,
        ObjectCreate=2, ObjectSetDetails=2, BlockCreate=1, AccountStop=1, AppShutdown=1,
        ObjectSearch=3, ObjectShow=4)
    return value


class SignedRevocationControls(unittest.TestCase):
    def test_exact_native_observation_qualifies_only_local_scope(self):
        self.assertEqual(gate.validate_observation(observation(), IDENTITY, PID, NONCE), gate.PASS)

    def test_current_denial_or_retired_space_both_require_exact_zero_payload(self):
        for search in gate.AUTHORITY_STOPPED_DESCRIPTIONS:
            for show in gate.AUTHORITY_STOPPED_DESCRIPTIONS:
                value = observation()
                value.update(object_search_error_description=search, object_show_error_description=show)
                self.assertEqual(gate.validate_observation(value, IDENTITY, PID, NONCE), gate.PASS)
                value.update(object_show_has_payload=True, object_show_explicit_denial=False, status=gate.DENIAL_FAILURE)
                self.assertEqual(gate.validate_observation(value, IDENTITY, PID, NONCE), gate.DENIAL_FAILURE)

    def test_successful_empty_query_is_not_a_denial(self):
        value = observation()
        value.update(object_search_error_code=0, object_search_explicit_denial=False, status=gate.DENIAL_FAILURE)
        self.assertEqual(gate.validate_observation(value, IDENTITY, PID, NONCE), gate.DENIAL_FAILURE)
        value["status"] = gate.PASS
        with self.assertRaises(ValueError):
            gate.validate_observation(value, IDENTITY, PID, NONCE)

    def test_payload_and_counts_cannot_hide_behind_an_error(self):
        for change in (dict(object_search_rows=1, object_search_explicit_denial=False),
                       dict(object_search_total=1, object_search_explicit_denial=False),
                       dict(object_show_has_payload=True, object_show_explicit_denial=False),
                       dict(object_search_error_code=-1, object_search_explicit_denial=False)):
            value = observation()
            value.update(change, status=gate.DENIAL_FAILURE)
            with self.subTest(change=change):
                self.assertEqual(gate.validate_observation(value, IDENTITY, PID, NONCE), gate.DENIAL_FAILURE)
                value["status"] = gate.PASS
                with self.assertRaises(ValueError):
                    gate.validate_observation(value, IDENTITY, PID, NONCE)

    def test_foreign_identity_mocked_authority_or_overclaimed_scope_is_rejected(self):
        changes = [dict(pid=PID+1), dict(nonce="foreign"), dict(current_permission="reader"),
            dict(same_engine_account=False), dict(populated_native_cache=False), dict(reader_positive=False),
            dict(read_key_id_after="fixture-before"), dict(signed_acl_remove_head="fixture-transfer"),
            dict(native_acl_updater="REPLACED"), dict(account_stop_verified=False),
            dict(network_acl_transport="PASS"), dict(offline_unknown_revocation="PASS"),
            dict(ios_acceptance="PASS"), dict(raw_payload="not allowed")]
        for change in changes:
            value = observation()
            value.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_observation(value, IDENTITY, PID, NONCE)

    def test_only_exact_native_authority_denial_retires_access(self):
        for change in (
            dict(object_search_error_code=1, object_search_explicit_denial=False),
            dict(object_search_error_description="account must be started", object_search_explicit_denial=False),
            dict(object_search_error_description=gate.INVALIDATED_DESCRIPTION + " suffix", object_search_explicit_denial=False),
            dict(object_show_error_description=gate.DENIED_DESCRIPTION + " suffix", object_show_explicit_denial=False),
            dict(object_show_error_code=4, object_show_explicit_denial=False),
        ):
            value = observation()
            value.update(change, status=gate.DENIAL_FAILURE)
            with self.subTest(change=change):
                self.assertEqual(gate.validate_observation(value, IDENTITY, PID, NONCE), gate.DENIAL_FAILURE)
                value["status"] = gate.PASS
                with self.assertRaises(ValueError):
                    gate.validate_observation(value, IDENTITY, PID, NONCE)

    def test_component_requires_its_exact_one_actual_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "component.log"
            for _, method in gate.COMPONENTS:
                passing = "=== RUN   " + method + "\n--- PASS: " + method + " (0.01s)\nPASS\n"
                path.write_text(passing)
                self.assertEqual(gate.qualify_component(path, method)["passed"], 1)
                for text in ("PASS\n", passing + passing, passing.replace("--- PASS:", "--- SKIP:"),
                             passing.replace(method, "AnotherMethod")):
                    path.write_text(text)
                    with self.subTest(method=method, text=text), self.assertRaises(ValueError):
                        gate.qualify_component(path, method)

    def test_real_log_requires_one_exact_complete_native_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native.log"
            passed = "=== RUN   " + gate.METHOD + "\n--- PASS: " + gate.METHOD + " (0.01s)\nPASS\n"
            path.write_text(passed)
            self.assertEqual(gate.qualify_execution(path, 0, gate.PASS)["tests_passed"], 1)
            failures = ["PASS\n", passed + passed,
                passed.replace(gate.METHOD, "DifferentMethod"), passed.replace("--- PASS:", "--- SKIP:")]
            for text in failures:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    gate.qualify_execution(path, 0, gate.PASS)
            failed = "=== RUN   " + gate.METHOD + "\nactual revoked ObjectSearch must explicitly deny with no rows or total\n--- FAIL: " + gate.METHOD + " (0.01s)\nFAIL\n"
            path.write_text(failed)
            self.assertEqual(gate.qualify_execution(path, 1, gate.DENIAL_FAILURE)["tests_failed"], 1)
            with self.assertRaises(ValueError):
                gate.qualify_execution(path, 0, gate.DENIAL_FAILURE)
            path.write_text(failed.replace("actual revoked ObjectSearch must explicitly deny", "unrelated fixture panic"))
            with self.assertRaises(ValueError):
                gate.qualify_execution(path, 1, gate.DENIAL_FAILURE)

    def test_no_native_output_is_published_without_original_secret_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            private, public = Path(tmp) / "private", Path(tmp) / "public"
            private.mkdir()
            (private / "native.log").write_text("unreviewed native output")
            result = gate.export_private(private, public)
            self.assertEqual(result["status"], "WITHHELD_NATIVE_OUTPUT_WITHOUT_SECRET_INVENTORY")
            self.assertFalse(public.exists())

    def test_public_export_is_small_and_refuses_sensitive_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "private"
            private.mkdir()
            (private / "ownership.json").write_text(json.dumps(dict(protocol=gate.PROTOCOL)))
            (private / "native-observation.json").write_text(json.dumps(observation()))
            (private / "sensitive-needles.private").write_text(json.dumps(["secret-wallet", "secret phrase"]))
            (private / "account-root").mkdir()
            (private / "account-root/raw.db").write_bytes(b"never publish")
            (private / "native.log").write_text("secret-wallet")
            with self.assertRaises(ValueError):
                gate.export_private(private, Path(tmp) / "bad")
            self.assertFalse((Path(tmp) / "bad").exists())
            (private / "native.log").write_text("bounded native log")
            result = gate.export_private(private, Path(tmp) / "good")
            self.assertEqual(set(result["files"]), {"ownership.json", "native-observation.json", "native.log"})


if __name__ == "__main__":
    unittest.main()
