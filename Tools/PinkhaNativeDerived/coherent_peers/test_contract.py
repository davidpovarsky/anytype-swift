"""New admission controls only; recorded original wire is not a new native run."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import contract


def varint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def encode(values):
    return b"".join(varint((field << 3) | kind) + (varint(value) if kind == 0 else varint(len(value)) + value)
                    for field, kind, value in values)


def replace(raw, field, kind, value):
    return encode([(number, kind if number == field else wire, value if number == field else item)
                   for number, wire, item in contract.fields(raw)])


class PeerContractControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = Path(os.environ.get("PINKHA_PEER_CONTROL_ORIGINAL", str(contract.ROOT / contract.PROOF)))
        path = original / "actual/coherent-owner.pb"
        if contract.digest(path) != "58919cffbb02a2ea279f3494060b3db2e75dc1adc1c94b3a8b8215741268a6df":
            raise ValueError("Controls require the untouched original successful native wire")
        cls.raw = path.read_bytes()
        snapshot = contract.fields(contract.one(contract.fields(cls.raw), 3, 2))
        variant = contract.fields(contract.one(snapshot, 8, 2))
        target = contract.fields(contract.one(variant, 5, 2))
        provenance = contract.fields(contract.one(variant, 7, 2))
        string = lambda rows, number: contract.one(rows, number, 2).decode()
        change = string(provenance, 2)
        cls.state = dict(AccountID=string(snapshot, 2), SpaceID=string(snapshot, 3), OperationID=string(snapshot, 4),
                         ClaimID=string(variant, 1), DocumentID=string(target, 1), BlockID=string(target, 2),
                         OperationSHA256=contract.sha(contract.one(variant, 6, 2)), RootID="synthetic-root-for-controls",
                         ChangeID=change, RawChanges={"synthetic-root-for-controls": "1" * 64, change: "2" * 64}, Heads=[change])
        cls.build = dict(status=contract.BUILD, app_sha="a" * 40, run_id="70001", run_attempt="1", heart_sha=contract.HEART,
                         patch_sha256=contract.PATCH, inventory_sha256=contract.INVENTORY, native_source_run=contract.NATIVE_RUN,
                         native_source_count=139, old_test_methods_executed=0, protobuf_generation_executed=0,
                         fixture_sha256="b" * 64, binary_sha256="c" * 64, binary_path="client-runtime/native.test",
                         runtime_version=contract.VERSION)
        cls.stopped = encode([(1, 2, encode([(1, 0, 5)])), (2, 0, 1)])
        cls.log = f"=== RUN   {contract.METHOD}\n--- PASS: {contract.METHOD} (1.00s)\nPASS\n"
        # Only retained infrastructure imports are mocked. All tested new
        # container admission methods are imported from their actual source.
        spec = importlib.util.spec_from_file_location("coherent_peer_runner_controls", contract.HERE / "run.py")
        cls.runner = importlib.util.module_from_spec(spec)
        infrastructure = SimpleNamespace(OwnedDocker=object, OWNER_LABEL="test.pinkha.owned")
        with patch.dict("sys.modules", {"run_native_clients": infrastructure, "build": SimpleNamespace(source_snapshot=None)}):
            spec.loader.exec_module(cls.runner)

    def report(self, role="recovered", phase="ready"):
        state, build = self.state, self.build
        calls = dict(InitialSetParameters=1, AppGetVersion=1, WalletRecover=1, AccountSelect=1,
                     WorkspaceOpen=1, DeviceNetworkStateSet=1, PinkhaTorahAuthorizedOperationRead=1)
        if role == "creator":
            calls.pop("WalletRecover"); calls.pop("AccountSelect")
            calls.update(WalletCreate=1, AccountCreate=1, PinkhaTorahOperationsAppend=1)
        return dict(protocol=contract.PROTOCOL, phase=phase, role=role, nonce="d" * 32, pid=1,
                    source_sha=build["app_sha"], heart_sha=contract.HEART, runtime_version=contract.VERSION,
                    fixture_sha256=build["fixture_sha256"], state_sha256="e" * 64, account_id=state["AccountID"],
                    space_id=state["SpaceID"], object_id=state["DocumentID"], block_id=state["BlockID"],
                    operation_id=state["OperationID"], claim_id=state["ClaimID"], change_id=state["ChangeID"],
                    canonical_sha256=state["OperationSHA256"], raw_changes_sha256=state["RawChanges"], heads=state["Heads"],
                    first_private_read="PinkhaTorahAuthorizedOperationRead", read_target_count=0,
                    active_append_count=int(role == "creator"), wire_sha256=contract.sha(self.raw),
                    variant_sha256=contract.validate_positive_wire(self.raw, state), peer_id="peer-" + role,
                    network_namespace="net:[42]" if role == "creator" else "net:[43]",
                    actual_ipv4=[] if phase == "reopen" else ["10.1.0.2" if role == "creator" else "10.1.0.3"],
                    rpc_calls=calls, **contract.LIMITS)

    def qualify(self, value, raw=None):
        return contract.validate_report(value, value["phase"], value["role"], "d" * 32, self.build, self.state,
                                        "e" * 64, self.raw if raw is None else raw)

    def final(self):
        initial = self.report(phase="reopen")
        final = copy.deepcopy(initial)
        final.update(phase="reopen-final", account_stop_verified=True, test_passed=True,
                     stopped_error_code=5, stopped_payload=False, stopped_wire_sha256=contract.sha(self.stopped))
        final["rpc_calls"].update(AccountStop=1, AppShutdown=1, PinkhaTorahAuthorizedOperationRead=2)
        final["returned_byte_calls"] = copy.deepcopy(final["rpc_calls"])
        return initial, final

    def test_original_wire_pair_and_exact_cold_read_are_accepted(self):
        contract.validate_build(self.build, "a" * 40, "70001", "1")
        contract.validate_state(self.state)
        creator, recovered = self.report("creator"), self.report()
        self.qualify(creator); self.qualify(recovered)
        contract.validate_pair(creator, recovered)
        initial, final = self.final()
        self.qualify(initial); self.qualify(final)
        contract.validate_final(final, self.stopped, self.log, initial, reopened=True)

    def test_source_profile_run_and_replayed_old_suite_are_rejected(self):
        changes = dict(app_sha="f" * 40, run_attempt="2", heart_sha="e" * 40, patch_sha256="0" * 64,
                       inventory_sha256="0" * 64, native_source_run="1", native_source_count=138,
                       old_test_methods_executed=1, protobuf_generation_executed=1,
                       runtime_version=contract.VERSION.replace("current-read", "current-write"),
                       binary_path="../native.test")
        for key, value in changes.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                contract.validate_build(dict(self.build, **{key: value}), "a" * 40, "70001", "1")

    def test_public_seed_cannot_copy_a_database_or_change_signed_heads(self):
        for changes in (dict(Database="copied"), dict(OperationID="0"), dict(Heads=[]),
                        dict(RawChanges={"different-root": "0" * 64})):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                contract.validate_state(dict(self.state, **changes))

    def test_unknown_duplicate_wrong_scope_or_truncated_wire_is_rejected(self):
        outer = contract.fields(self.raw)
        snapshot = contract.one(outer, 3, 2)
        mutations = [self.raw[:-1], self.raw + b"\x10\x01", self.raw + b"\x20\x00", b"\x80" * 11,
                     replace(self.raw, 2, 0, 2), replace(self.raw, 3, 2, replace(snapshot, 2, 2, b"foreign-account")),
                     replace(self.raw, 3, 2, replace(snapshot, 6, 0, 0)),
                     replace(self.raw, 3, 2, snapshot + encode([(8, 2, contract.one(contract.fields(snapshot), 8, 2))]))]
        for raw in mutations:
            with self.subTest(sha256=contract.sha(raw)), self.assertRaises(ValueError):
                contract.validate_positive_wire(raw, self.state)

    def test_canonical_payload_provenance_and_target_are_bound(self):
        for key in ("AccountID", "SpaceID", "OperationID", "ClaimID", "ChangeID", "DocumentID", "BlockID", "OperationSHA256"):
            with self.subTest(field=key), self.assertRaises(ValueError):
                contract.validate_positive_wire(self.raw, dict(self.state, **{key: "changed"}))

    def test_reopen_retries_old_read_priming_or_higher_acceptance_fail(self):
        for change in (dict(source_sha="f" * 40), dict(pid=2), dict(pid=True), dict(full_t2_acceptance="PASS"),
                       dict(network_acl_transport="PASS"), dict(offline_unknown_revocation="PASS"),
                       dict(actual_ipv4=["10.1.0.3"]), dict(first_private_read="PinkhaTorahOperationsReadTarget")):
            value = self.report(phase="reopen"); value.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.qualify(value)
        for key, count in (("PinkhaTorahOperationsReadTarget", 1), ("PinkhaTorahOperationsAppend", 1),
                           ("PinkhaTorahAuthorizedOperationRead", 2)):
            value = self.report(phase="reopen"); value["rpc_calls"][key] = count
            with self.subTest(call=key), self.assertRaises(ValueError):
                self.qualify(value)

    def test_second_peer_cannot_reuse_device_namespace_or_claim(self):
        a, b = self.report("creator"), self.report()
        for key in ("peer_id", "network_namespace", "actual_ipv4"):
            value = dict(b, **{key: a[key]})
            with self.subTest(identity=key), self.assertRaises(ValueError):
                contract.validate_pair(a, value)
        with self.assertRaises(ValueError):
            contract.validate_pair(a, dict(b, variant_sha256="0" * 64))

    def test_stop_denial_must_have_no_payload_and_all_calls_join(self):
        initial, final = self.final()
        for raw in (self.raw, self.stopped + encode([(3, 2, b"private-payload")]),
                    encode([(1, 2, encode([(1, 0, 4)])), (2, 0, 1)])):
            value = dict(final, stopped_wire_sha256=contract.sha(raw))
            with self.subTest(raw=contract.sha(raw)), self.assertRaises(ValueError):
                contract.validate_final(value, raw, self.log, initial, reopened=True)
        value = copy.deepcopy(final); value["returned_byte_calls"]["AccountStop"] = 0
        with self.assertRaises(ValueError):
            contract.validate_final(value, self.stopped, self.log, initial, reopened=True)

    def test_missing_extra_failed_or_skipped_go_method_cannot_pass(self):
        initial, final = self.final()
        logs = ["PASS\n", self.log.replace("--- PASS:", "--- SKIP:"), self.log.replace("--- PASS:", "--- FAIL:"),
                self.log + "=== RUN   TestOldBaseline\n--- PASS: TestOldBaseline (1.00s)\nPASS\n"]
        for log in logs:
            with self.subTest(log=log), self.assertRaises(ValueError):
                contract.validate_final(final, self.stopped, log, initial, reopened=True)

    def test_only_exact_screened_original_allowlist_is_exported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); private = root / "private"
            (private / "creator").mkdir(parents=True); (private / "recovered").mkdir()
            (private / "creator/sensitive-needles.private").write_text(json.dumps(["synthetic-secret-key", "synthetic-secret-mnemonic"]))
            (private / "creator/ready.pb").write_bytes(self.raw)
            (private / "creator/account-key.private").write_text("synthetic-secret-key")
            (private / "creator/unlisted-private.txt").write_text("synthetic-secret-key")
            value = contract.export(private, root / "export")
            self.assertEqual(value["files"], {"creator/ready.pb": contract.sha(self.raw)})
            self.assertEqual((root / "export/creator/ready.pb").read_bytes(), self.raw)
            with self.assertRaises(ValueError):
                contract.export(private, root / "export")

    def test_secret_leak_or_missing_inventory_withholds_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); private = root / "private"
            (private / "creator").mkdir(parents=True); (private / "recovered").mkdir()
            self.assertEqual(contract.export(private, root / "no-inventory")["files"], {})
            self.assertFalse((root / "no-inventory").exists())
            (private / "creator/sensitive-needles.private").write_text(json.dumps(["synthetic-secret-key", "synthetic-secret-mnemonic"]))
            (private / "creator/ready.pb").write_bytes(self.raw)
            (private / "recovered/native.log").write_text("oops: synthetic-secret-key")
            with self.assertRaises(ValueError):
                contract.export(private, root / "leaked")
            self.assertFalse((root / "leaked").exists())

    def test_unsafe_json_symlink_and_nonfinite_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / "evidence.json"
            for raw in ('{"x":1,"x":2}', '{"x":NaN}', '[]'):
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    contract.load(path)
            contract.save(path, {"x": 1}); self.assertEqual(contract.load(path), {"x": 1})
            linked = root / "linked.json"; linked.symlink_to(path)
            with self.assertRaises(ValueError):
                contract.load(linked)

    def container(self):
        return dict(Id="1" * 64, Image="sha256:mock-pinned-image", Path="/fixture/native.test", Args=self.runner.ARGS,
                    Config=dict(Labels={"test.pinkha.owned": "d" * 32}, Image=contract.IMAGE,
                                User=f"{os.getuid()}:{os.getgid()}", Env=["PINKHA_T2_CLIENT_ROLE=recovered",
                                    "PINKHA_T2_CLIENT_NONCE=" + "d" * 32, "PINKHA_T2_CLIENT_FIXTURE_SHA=" + self.build["fixture_sha256"],
                                    "PINKHA_COHERENT_PEER_PHASE=reopen", "PINKHA_COHERENT_RUNTIME_VERSION=" + contract.VERSION]),
                    HostConfig=dict(ReadonlyRootfs=True, Privileged=False, CapDrop=["ALL"], SecurityOpt=["no-new-privileges"],
                                    NanoCpus=1000000000, Memory=2 * 1024**3, PidsLimit=256, NetworkMode="none"),
                    Mounts=[dict(Type="bind", Destination="/private", Source="/owned/recovered", RW=True),
                            dict(Type="bind", Destination="/fixture/native.test", Source="/owned/native.test", RW=False)],
                    NetworkSettings=dict(Networks={"none": dict(IPAddress="")}))

    def test_actual_container_boundary_rejects_shared_root_extra_network_and_suite(self):
        qualify = lambda value: self.runner.validate_container(value, "d" * 32, "recovered", "reopen", None,
            Path("/owned/recovered"), Path("/owned/native.test"), "sha256:mock-pinned-image", self.build)
        qualify(self.container())
        cases = []
        value = self.container(); value["Mounts"][0]["Source"] = "/owned/creator"; cases.append(value)
        value = self.container(); value["Mounts"][1]["RW"] = True; cases.append(value)
        value = self.container(); value["HostConfig"]["NetworkMode"] = "host"; cases.append(value)
        value = self.container(); value["NetworkSettings"]["Networks"]["bridge"] = {}; cases.append(value)
        value = self.container(); value["Args"] = ["-test.run", ".*"]; cases.append(value)
        value = self.container(); value["Config"]["Env"].append("PINKHA_T2_CLIENT_SCENARIO=offline"); cases.append(value)
        value = self.container(); value["HostConfig"]["Privileged"] = True; cases.append(value)
        for number, value in enumerate(cases):
            with self.subTest(case=number), self.assertRaises(ValueError):
                qualify(value)

    def test_publication_failure_changes_receipt_to_fail_and_returns_nonzero(self):
        # Use the actual retained finalizer; inject only its filesystem failure.
        # No Docker command or native method is started by this control.
        import run_native_clients as actual_retained
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            exported = {role + "/" + name: "0" * 64 for role, names in contract.PUBLISHED.items()
                        for name in names if name != "cancel.json"}
            arguments = ["run.py", "--control", str(contract.ROOT), "--native-work", str(root / "runtime"),
                         "--private", str(root / "private"), "--evidence", str(evidence),
                         "--expected-app-sha", "a" * 40]
            def completed_native(_args, receipt, _docker):
                receipt["status"] = contract.PASS
            with patch.object(self.runner, "retained", actual_retained), \
                 patch.object(self.runner, "OwnedPeers", actual_retained.OwnedDocker), \
                 patch.object(actual_retained.OwnedDocker, "cleanup"), \
                 patch.object(self.runner, "execute", completed_native), \
                 patch.object(contract, "export", return_value=dict(status="PASS_EXACT_SYNTHETIC_SECRET_SCAN", files=exported)), \
                 patch.object(actual_retained, "normalize_evidence_permissions", side_effect=PermissionError("injected mode failure")), \
                 patch.object(sys, "argv", arguments):
                result = self.runner.main()
            receipt = contract.load(evidence / "receipt.json")
            self.assertEqual(result, 1)
            self.assertEqual(receipt["status"], "FAIL")
            self.assertEqual(receipt["evidence_permissions_error_type"], "PermissionError")


if __name__ == "__main__":
    unittest.main()
