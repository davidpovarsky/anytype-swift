"""Synthetic native receipt custody controls; no Native model or App execution."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import g02_native_phase as n
from test_g02_ui_receipts import C, UDID, bound, encode, seed


def native_receipt(fixture, controller, seed_raw):
    docs = {}
    for role, object_id in fixture["documents"].items():
        raw = json.dumps({"id": object_id})
        canonical = '{"version":2,"items":[]}'
        docs[role] = {"native": {"objectID": object_id, "spaceID": fixture["spaceId"],
                     "typeID": fixture["types"][role], "name": fixture["names"][object_id],
                     "fields": {}, "protobufDetailsJSON": raw, "protobufDetailsSHA256": C.sha(raw.encode())},
                     "canonicalRaw": canonical, "canonicalSHA256": C.sha(canonical.encode()), "projections": {},
                     "tag": {"objectID": "synthetic-tag-" + role, "name": "synthetic tag"}}
    # Only receipt custody is tested here. These deliberately synthetic records
    # are not valid Native semantic acceptance and never reach a Swift reader.
    return {"schema": "pinkha-g02-word-native-readback-v1", "status": "PASS_BASELINE_READ_ONLY", "phase": "baseline",
            "controller": controller, "fixtureSHA256": controller["FIXTURE_SHA256"], "seedUIReceiptSHA256": C.sha(seed_raw),
            "processID": 1234, "directories": {"container": {}, "middleware": {}}, "verifierCallsMutationAPI": False,
            "scope": n.SCOPE, "permittedClockKeys": n.CLOCK_KEYS,
            "state": {"accountID": "synthetic-account", "spaceID": fixture["spaceId"], "canonicalPropertyKey": "synthetic-key",
                      "canonicalPropertyID": "synthetic-property", "tagProperty": {}, "documents": docs}}


class NativeControls(unittest.TestCase):
    def test_real_published_reader_and_original_preparation_inverse(self):
        path = Path(__file__).resolve().parents[2] / "wave2-editor-g02/TorahNativeDerivedProductIntegrationTests.swift"
        raw = path.read_bytes()
        self.assertEqual(n.qualify_native_source(C, raw)["casesPerInvocation"], 1)
        with self.assertRaises(ValueError): n.qualify_native_source(C, raw[:n.ORIGINAL_BYTES])
        with self.assertRaises(ValueError): n.qualify_native_source(C, raw+b"\n")

    def test_phase_environment_preserves_raw_fixture_and_original_invocation(self):
        f, controller, fixture_raw, startup = bound()
        seed_raw = encode(seed(f, controller)["seed-complete"])
        environment, actual_fixture, actual_controller = n.phase_environment(C, "baseline", startup, fixture_raw, UDID, seed_raw)
        self.assertEqual(actual_fixture, f); self.assertEqual(actual_controller, controller)
        self.assertEqual(environment["PINKHA_UI27_STARTUP_INVOCATION_SHA256"], controller["INVOCATION_SHA256"])
        self.assertTrue(all(environment[key] == "0" for key in n.DISABLED_FLAGS))
        self.assertEqual(environment["PINKHA_TYPE_PRESERVATION_POSTFLIGHT"], "0")
        self.assertNotIn("SIMULATOR_UDID", environment)
        self.assertNotEqual(C.sha(environment["PINKHA_NATIVE_UI_FIXTURE_JSON"].encode()), controller["FIXTURE_SHA256"])
        wrong = dict(startup, SIMULATOR_UDID=UDID)
        with self.assertRaises(ValueError): n.phase_environment(C, "baseline", wrong, fixture_raw, UDID, seed_raw)
        with self.assertRaises(ValueError): n.phase_environment(C, "postflight", startup, fixture_raw, UDID, seed_raw)

    def test_receipt_hash_phase_and_scope_do_not_accept_foreign_evidence(self):
        f, controller, _, _ = bound(); seed_raw = encode(seed(f, controller)["seed-complete"])
        value = native_receipt(f, controller, seed_raw)
        self.assertIs(n.validate_receipt(C, value, "baseline", "PASS_BASELINE_READ_ONLY", f, controller, C.sha(seed_raw)), value)
        for mutate in (
            lambda v: v.update(verifierCallsMutationAPI=True),
            lambda v: v.update(seedUIReceiptSHA256="f"*64),
            lambda v: v.update(phase="postflight"),
            lambda v: v.update(scope="WHOLE_STORE_ACCEPTED"),
            lambda v: v["state"]["documents"]["article"]["native"].update(spaceID="another-Space"),
            lambda v: v["state"]["documents"]["research"].update(canonicalSHA256="e"*64),
        ):
            wrong = copy.deepcopy(value); mutate(wrong)
            with self.assertRaises(ValueError): n.validate_receipt(C, wrong, "baseline", "PASS_BASELINE_READ_ONLY", f, controller, C.sha(seed_raw))

    def test_failed_native_observation_is_retained_without_masking_first_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); container = root / "owned-container"; support = container / n.lane.SUPPORT
            support.mkdir(parents=True)
            observed = support / "actual-observed.json"; observed.write_bytes(b"{retained-failed-observation}")
            accepted = support / "accepted.json"; accepted.write_bytes(b"unexpected partially written acceptance")
            common = SimpleNamespace(raw=C.raw, sha=C.sha, require=C.require, error=lambda exc: {"type": type(exc).__name__, "message": str(exc)})
            def copy_private(udid, relative, destination, label, maximum):
                if Path(relative).name == accepted.name: raise ValueError("later-retention-failure")
                raw = C.raw(container / relative, maximum)
                destination.mkdir(parents=True, exist_ok=True); (destination / Path(relative).name).write_bytes(raw)
                return raw, container
            consumer = SimpleNamespace(shared_module=common, container=lambda *args: container, read_private=copy_private)
            original = ValueError("original-XCTest-failure")
            result = {"status": "FAIL", "firstFailure": common.error(original), "retentionErrors": []}
            first = n.retain_outputs(consumer, root / "native-baseline", UDID, "baseline",
                         {"observed": observed.name, "baseline": accepted.name, "uiBaseline": "missing-ui.json"}, result, original)
            self.assertIs(first, original)
            self.assertEqual(result["firstFailure"], common.error(original)); self.assertEqual(result["status"], "FAIL")
            self.assertEqual(C.raw(result["observed"]["path"]), observed.read_bytes())
            self.assertEqual(result["retentionErrors"][0]["message"], "later-retention-failure")
            self.assertNotIn("baseline", result)
            no_first = {"status": "FAIL", "firstFailure": None, "retentionErrors": []}
            failure = n.retain_outputs(consumer, root / "native-postflight", UDID, "postflight",
                                      {"postflight": "missing-native.json"}, no_first, None)
            self.assertIsInstance(failure, ValueError)
            self.assertEqual(no_first["status"], "FAIL")


if __name__ == "__main__": unittest.main(verbosity=2)
