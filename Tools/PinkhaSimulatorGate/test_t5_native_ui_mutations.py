"""Parser/controller controls only; these fixtures are not native acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import run_t5_native_ui as runner
import t5_native_ui_mutations as gate


def fixture_and_receipt():
    fixture = dict(token="a" * 32, appSourceSHA="b" * 40, runID="123", runtimeVersion="reviewed-corrected-native",
                   preparationProcessID=123, accountID="native-account", spaceID="native-space",
                   accountRootPathSHA256="c" * 64, providerID="sefaria", canonicalReference="Genesis 1:1",
                   targets=[], excluded=[dict(objectID="foreign-object")])
    rows = []
    for role in ["page", "note", "writing", "block", "quote"]:
        obj = "object-" + role
        block = "block-" + role if role in {"block", "quote"} else None
        kind = "note" if role == "note" else "document"
        type_key = role if role in {"note", "writing"} else "page"
        identity = gate._identity(fixture["spaceID"], obj, block)
        fixture["targets"].append(dict(role=role, objectID=obj, blockID=block, associationID="association-" + role,
                                       title="Native " + role, resultID=identity, typeKey=type_key))
        row = dict(resultID=identity, objectID=obj, spaceID=fixture["spaceID"], title="Native " + role,
                   typeID="type-" + type_key, kind=kind, canUnlink=block is None)
        if block:
            row["blockID"] = block
        rows.append(row)
    observations = []
    for index, stage in enumerate(gate.STAGES):
        actual_rows = copy.deepcopy(rows)
        observation = dict(stage=stage, nativeReadStatus="objectDeleted" if index == 2 else "present",
                           coverage="indexedTargetsOnly", limitations=["indexFreshnessUnverified"])
        if index < 2:
            type_key = "page" if index == 0 else "note"
            title = "Native transient " + type_key
            actual_rows.append(dict(resultID=gate._identity(fixture["spaceID"], "transient-object"),
                                    objectID="transient-object", spaceID=fixture["spaceID"], title=title,
                                    typeID="type-" + type_key, kind="document" if index == 0 else "note", canUnlink=True))
            observation.update(nativeTypeID="type-" + type_key, nativeTypeKey=type_key, nativeLayout=index,
                               nativeTitle=title, canonicalSHA256="d" * 64, blockReachable=True,
                               associationID="transient-association", bodySHA256=hashlib.sha256(
                                   ("T5 native type/delete preserved body " + fixture["token"]).encode()).hexdigest())
        observation["relatedRows"] = sorted(actual_rows, key=lambda row: row["resultID"])
        observations.append(observation)
    receipt = {key: fixture[key] for key in gate.BOUND_KEYS}
    receipt.update(protocolVersion=1, status="PASS", scope="type-change-and-whole-object-delete",
                   transientObjectID="transient-object", transientBlockID="transient-block",
                   transientAssociationID="transient-association", canonicalPropertyKey="registered-canonical-key",
                   observations=observations, productLookupFlag="OFF", fullT5Accepted=False)
    return fixture, receipt


class NativeMutationEvidenceControls(unittest.TestCase):
    def test_exact_three_observations_qualify_only_two_new_native_mutations(self):
        fixture, receipt = fixture_and_receipt()
        result = gate.validate(receipt, fixture)
        self.assertEqual(result, dict(status=gate.PASS, actual_mutations=2, actual_observations=3,
                                     stages=gate.STAGES, final_ui_targets=5, full_t5_accepted=False))

    def test_wrong_runtime_source_account_process_attempt_or_expanded_scope_fails(self):
        fixture, receipt = fixture_and_receipt()
        for key in gate.BOUND_KEYS:
            value = copy.deepcopy(receipt)
            value[key] = value[key] + 1 if isinstance(value[key], int) else value[key] + "foreign"
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.validate(value, fixture)
        for key, replacement in [("fullT5Accepted", True), ("productLookupFlag", "ON"), ("protocolVersion", True),
                                 ("status", "PENDING"), ("transientObjectID", fixture["targets"][0]["objectID"])]:
            value = copy.deepcopy(receipt); value[key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.validate(value, fixture)

    def test_type_change_requires_actual_current_type_link_and_exact_body_canonical_preservation(self):
        fixture, receipt = fixture_and_receipt()
        for key, value in [("nativeTypeID", "type-page"), ("nativeTypeKey", "page"), ("nativeLayout", 0),
                           ("bodySHA256", "e" * 64), ("canonicalSHA256", "e" * 64),
                           ("associationID", "other-link"), ("blockReachable", False), ("nativeTitle", "stale title")]:
            changed = copy.deepcopy(receipt); changed["observations"][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.validate(changed, fixture)
        changed = copy.deepcopy(receipt)
        next(row for row in changed["observations"][1]["relatedRows"] if row["objectID"] == "transient-object")["kind"] = "document"
        with self.assertRaises(ValueError):
            gate.validate(changed, fixture)

    def test_whole_object_deletion_requires_native_state_and_no_retained_row_or_payload(self):
        fixture, receipt = fixture_and_receipt()
        for status in ["isDeleted", "notFound", "objectDeleted"]:
            value = copy.deepcopy(receipt); value["observations"][2]["nativeReadStatus"] = status
            self.assertEqual(gate.validate(value, fixture)["status"], gate.PASS)
        mutations = [lambda o: o.update(nativeReadStatus="archived"), lambda o: o.update(canonicalSHA256="d" * 64),
                     lambda o: o["relatedRows"].append(copy.deepcopy(receipt["observations"][1]["relatedRows"][-1]))]
        for mutate in mutations:
            value = copy.deepcopy(receipt); mutate(value["observations"][2])
            with self.assertRaises(ValueError):
                gate.validate(value, fixture)

    def test_duplicate_missing_extra_rows_or_changed_original_five_are_rejected(self):
        fixture, receipt = fixture_and_receipt()
        mutations = [lambda o: o["relatedRows"].pop(), lambda o: o["relatedRows"].append(o["relatedRows"][0]),
                     lambda o: o["relatedRows"][0].update(title="changed original document"),
                     lambda o: o["relatedRows"][0].update(spaceID="foreign-space"),
                     lambda o: o.update(coverage="spaceWide"), lambda o: o.update(limitations=[])]
        for mutate in mutations:
            value = copy.deepcopy(receipt); mutate(value["observations"][2])
            with self.assertRaises(ValueError):
                gate.validate(value, fixture)
        for observations in [receipt["observations"][:2], list(reversed(receipt["observations"]))]:
            value = copy.deepcopy(receipt); value["observations"] = observations
            with self.assertRaises(ValueError):
                gate.validate(value, fixture)

    def test_capture_preserves_exact_original_bytes_and_refuses_reused_destination(self):
        fixture, receipt = fixture_and_receipt()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); container = root / "container"; private = root / "private"; private.mkdir()
            source = container / gate.RELATIVE; source.parent.mkdir(parents=True)
            raw = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf8")
            source.write_bytes(raw)
            result = gate.capture(container, private, fixture, gate.PROFILE)
            self.assertEqual((private / gate.COPY_NAME).read_bytes(), raw)
            self.assertEqual(result["receipt_sha256"], hashlib.sha256(raw).hexdigest())
            with self.assertRaises(FileExistsError):
                gate.capture(container, private, fixture, gate.PROFILE)
            self.assertEqual(source.read_bytes(), raw)

    def test_missing_oversize_or_invalid_receipt_never_publishes(self):
        fixture, receipt = fixture_and_receipt()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); container = root / "container"; private = root / "private"; private.mkdir()
            source = container / gate.RELATIVE; source.parent.mkdir(parents=True)
            with self.assertRaises(ValueError):
                gate.capture(container, private, fixture, gate.PROFILE)
            source.write_bytes(b" " * (64 * 1024 + 1))
            with self.assertRaises(ValueError):
                gate.capture(container, private, fixture, gate.PROFILE)
            receipt["observations"][1]["canonicalSHA256"] = "e" * 64
            source.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                gate.capture(container, private, fixture, gate.PROFILE)
            self.assertFalse((private / gate.COPY_NAME).exists())

    def test_historical_pair_profile_does_not_read_or_change_any_fixture(self):
        self.assertEqual(gate.capture(Path("missing-container"), Path("missing-private"), None, "r15"),
                         dict(status="NOT_SELECTED", actual_mutations=0, actual_observations=0))

    def test_original_native_mutation_bytes_remain_bound_across_ui_lifetimes(self):
        fixture, receipt = fixture_and_receipt()
        with tempfile.TemporaryDirectory() as temp:
            container = Path(temp)
            (container / runner.NATIVE_ROOT).mkdir(parents=True)
            (container / runner.UI_FIXTURE).write_text(json.dumps(fixture))
            secrets = container / runner.UI_SECRETS; secrets.parent.mkdir()
            secrets.write_text(json.dumps(dict(token=fixture["token"], mnemonic="parser-control-only", accountKey="parser-key-only")))
            path = container / gate.RELATIVE
            path.write_text(json.dumps(receipt))
            identity, _ = runner.native_ui_identity(container)
            self.assertEqual(identity["native_mutations_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            pair = SimpleNamespace(app_container=lambda *args: container)
            self.assertEqual(runner.current_ui_container(pair, "owned-simulator", identity), container)
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                runner.current_ui_container(pair, "owned-simulator", identity)
            path.unlink()
            with self.assertRaises(ValueError):
                runner.current_ui_container(pair, "owned-simulator", identity)


if __name__ == "__main__":
    unittest.main()
