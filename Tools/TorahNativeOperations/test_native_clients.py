"""Rejection controls for source, isolated native clients and evidence publication.

These controls do not create accounts or claim Docker/Native acceptance.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_native_clients as lane


def state_fixture():
    return {"AccountID": "account", "SpaceID": "space", "DocumentID": "document", "BlockID": "block",
            "RootID": "root", "OperationID": "1" * 32, "OperationSHA256": "2" * 64,
            "ClaimID": "3" * 64 + "/" + "4" * 64, "ChangeID": "change",
            "RawChanges": {"root": "5" * 64, "change": "6" * 64}, "Heads": ["change"]}


def container_fixture(role="recovered"):
    return {"Id": "id-" + role, "Name": "/owned-" + role, "Image": "pinned-image-id",
            "Path": "/fixture/native.test", "Args": ["-test.run", "^" + lane.METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=1000s"],
            "Config": {"Labels": {lane.OWNER_LABEL: "owner"}, "Image": lane.IMAGE, "User": "1001:1001",
                       "Env": ["PINKHA_T2_CLIENT_ROLE=" + role, "PINKHA_T2_CLIENT_NONCE=owner"]},
            "HostConfig": {"ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"],
                           "SecurityOpt": ["no-new-privileges"], "NetworkMode": "owned-network", "PortBindings": {}, "PidMode": "", "Init": False},
            "Mounts": [{"Type": "bind", "Destination": "/private", "Source": str(Path("/owned/" + role)), "RW": True},
                       {"Type": "bind", "Destination": "/fixture/native.test", "Source": str(Path("/owned/native.test")), "RW": False}],
            "State": {"Running": True, "Pid": 123},
            "NetworkSettings": {"SandboxID": "sandbox-" + role,
                                "Networks": {"owned-network": {"NetworkID": "network-id", "IPAddress": "172.30.0.3"}}}}


def ready_fixture(role="recovered"):
    state = state_fixture()
    identity = {"heart_sha": "heart", "runtime_version": "runtime", "fixture_sha256": "account-fixture",
                "rpc_manifest_sha256": "schema", "registration_patch_sha256": "registry"}
    report = {"protocol": lane.PROTOCOL, "role": role, "nonce": "owner", "pid": 1, "network_namespace": "net:[native]",
              "bridge_ipv4": "172.30.0.3", "peer_id": "peer", "native_server_port": 4000, "heart_sha": "heart",
              "runtime_version": "runtime", "account_fixture_sha256": "account-fixture", "rpc_manifest_sha256": "schema",
              "registration_patch_sha256": "registry", "client_fixture_sha256": "clients-fixture", "state_sha256": "state-hash",
              "account_id": state["AccountID"], "space_id": state["SpaceID"], "document_id": state["DocumentID"],
              "block_id": state["BlockID"], "private_root_id": state["RootID"], "raw_changes_sha256": state["RawChanges"],
              "heads": state["Heads"], "initial_account_root": "OBSERVED_EMPTY", "native_local_only_requested": True,
              "native_lan_enabled_requested": True, "ordinary_document": "PASS_NATIVE_OBJECT_SHOW",
              "private_read": "PASS_GENERATED_RPC_ORIGINAL_SIGNED_HISTORY", "app_capability": "OFF",
              "two_ios_apps": "NOT_RUN", "offline_conflict_merge": "NOT_RUN",
              "active_private_append": "NONE_RECOVERED_CLIENT_READ_ONLY" if role == "recovered" else "ONE_CREATOR_GENERATED_RPC_APPEND"}
    return state, identity, report


class NativeClientControls(unittest.TestCase):
    def test_public_seed_rejects_device_database_and_signed_history_payloads(self):
        lane.validate_public_state(state_fixture())
        for field in ["DeviceKey", "PortKey", "Database", "RawTreeBytes"]:
            with self.subTest(field=field):
                state = state_fixture()
                state[field] = "synthetic-private-payload"
                with self.assertRaises(ValueError): lane.validate_public_state(state)
        state = state_fixture()
        state["RawChanges"]["root"] = "not-a-sha256-digest"
        with self.assertRaises(ValueError): lane.validate_public_state(state)

    def test_native_controls_require_every_named_case_and_no_skip(self):
        names = set(lane.CONTROL_METHODS)
        names.update(parent + "/" + child for parent, children in lane.CONTROL_METHODS.items() for child in children)
        output = "\n".join("--- PASS: " + name + " (0.01s)" for name in sorted(names))
        self.assertEqual(lane.validate_native_controls(output)["pass_terminals"], 13)
        for bad in [output.replace(sorted(names)[0], "OtherTest", 1), output + "\n--- SKIP: ignored (0s)",
                    output + "\n--- FAIL: ignored (0s)", output + "\n--- PASS: OtherTest (0s)"]:
            with self.subTest(bad=bad[-40:]):
                with self.assertRaises(ValueError): lane.validate_native_controls(bad)

    def test_container_rejects_foreign_owner_shared_data_and_external_network(self):
        network = {"Name": "owned-network", "Id": "network-id"}
        def validate(info):
            lane.validate_container(info, "owner", "recovered", network, Path("/owned/recovered"),
                                    Path("/owned/native.test"), "pinned-image-id", 1001, 1001)
        validate(container_fixture())
        mutations = [lambda x: x["Config"]["Labels"].update({lane.OWNER_LABEL: "foreign"}),
                     lambda x: x["Mounts"][0].update(Source="/owned/creator"),
                     lambda x: x["Mounts"].append({"Type": "bind", "Destination": "/other", "Source": "/owned/creator", "RW": False}),
                     lambda x: x["NetworkSettings"]["Networks"].update({"public-network": {"NetworkID": "other"}}),
                     lambda x: x["HostConfig"].update(Privileged=True),
                     lambda x: x["Config"].update(Image="golang:latest"),
                     lambda x: x["HostConfig"].update(Init=True)]
        for mutate in mutations:
            info = container_fixture(); mutate(info)
            with self.assertRaises(ValueError): validate(info)

    def test_same_peer_namespace_pid_or_sandbox_cannot_be_two_clients(self):
        reports = {role: ready_fixture(role)[2] for role in ["creator", "recovered"]}
        infos = {role: container_fixture(role) for role in reports}
        for index, role in enumerate(reports):
            reports[role].update(peer_id="peer-" + role, network_namespace="ns-" + role, bridge_ipv4=str(index))
            infos[role]["State"]["Pid"] = 100 + index
        lane.validate_pair(reports, infos)
        for key in ["peer_id", "network_namespace", "bridge_ipv4"]:
            bad = copy.deepcopy(reports)
            bad["recovered"][key] = bad["creator"][key]
            with self.assertRaises(ValueError): lane.validate_pair(bad, infos)
        for outer, key in [("State", "Pid"), ("NetworkSettings", "SandboxID")]:
            bad = copy.deepcopy(infos)
            bad["recovered"][outer][key] = bad["creator"][outer][key]
            with self.assertRaises(ValueError): lane.validate_pair(reports, bad)

    def test_readiness_does_not_accept_wrong_source_or_partial_history(self):
        state, identity, good = ready_fixture()
        def validate(report):
            with patch.object(lane.os, "readlink", return_value="net:[native]"):
                lane.validate_ready(report, "recovered", "owner", state, "state-hash", identity, "clients-fixture",
                                    container_fixture(), {"Name": "owned-network", "Id": "network-id"})
        validate(good)
        for key, value in [("heads", []), ("raw_changes_sha256", {}), ("client_fixture_sha256", "wrong"),
                           ("active_private_append", "ONE_CREATOR_GENERATED_RPC_APPEND"), ("app_capability", "ON"),
                           ("test_passed", True), ("private_read", "MISSING_HISTORY")]:
            bad = copy.deepcopy(good); bad[key] = value
            with self.subTest(field=key):
                with self.assertRaises(ValueError): validate(bad)

    def test_final_acceptance_requires_native_log_account_stop_and_no_active_b_append(self):
        _, _, ready = ready_fixture()
        calls = {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1, "DeviceNetworkStateSet": 1,
                 "ObjectShow": 1, "AccountStop": 1, "AppShutdown": 1, "WalletRecover": 1, "AccountSelect": 1,
                 "PinkhaTorahOperationsReadTarget": 2, "PinkhaTorahOperationsAppend": 1}
        good = {**ready, "closed": True, "account_stop_verified": True, "test_passed": True,
                "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN", "rpc_calls": calls, "returned_byte_calls": dict(calls)}
        log = "--- PASS: " + lane.METHOD + " (0.1s)\nPASS\n"
        lane.validate_final(ready, good, log, "recovered")
        for key in ["closed", "account_stop_verified", "test_passed"]:
            bad = copy.deepcopy(good); bad[key] = False
            with self.assertRaises(ValueError): lane.validate_final(ready, bad, log, "recovered")
        bad = copy.deepcopy(good)
        bad["rpc_calls"]["PinkhaTorahOperationsAppend"] = bad["returned_byte_calls"]["PinkhaTorahOperationsAppend"] = 2
        with self.assertRaises(ValueError): lane.validate_final(ready, bad, log, "recovered")
        with self.assertRaises(ValueError): lane.validate_final(ready, good, "PASS\n", "recovered")

    def test_missing_secret_inventory_withholds_all_native_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            private, evidence = Path(tmp) / "private", Path(tmp) / "evidence"
            (private / "creator").mkdir(parents=True); evidence.mkdir()
            (private / "creator/native.log").write_text("synthetic unknown secret")
            result = lane.publish_native_evidence(private, evidence)
            self.assertEqual(result["status"], "WITHHELD_NO_SECRET_INVENTORY")
            self.assertFalse((evidence / "native-clients").exists())

    def test_all_secret_scanning_precedes_publication_and_excludes_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            private, evidence = Path(tmp) / "private", Path(tmp) / "evidence"
            creator = private / "creator"
            creator.mkdir(parents=True); evidence.mkdir()
            needles = ["synthetic-account-key-long", "synthetic mnemonic words long"]
            (creator / "sensitive-needles.private").write_text(json.dumps(needles))
            (creator / "native.log").write_text("contains " + needles[0])
            (creator / "ownership.json").write_text('{}')
            with self.assertRaises(ValueError): lane.publish_native_evidence(private, evidence)
            self.assertFalse((evidence / "native-clients").exists())
            (creator / "native.log").write_text("public synthetic native result")
            (creator / "account-key.private").write_text(needles[0])
            (creator / "store.db").write_bytes(b"synthetic database")
            result = lane.publish_native_evidence(private, evidence)
            self.assertEqual(result["status"], "PASS_SECRET_SCANNED_EXACT_ALLOWLIST")
            self.assertEqual(set(result["files_sha256"]), {"creator/ownership.json", "creator/native.log"})

    def test_daemon_mutation_records_owner_intent_before_a_cancelled_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            with patch.object(owner, "command", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): owner.network()
            self.assertEqual(owner.resources, [{"kind": "network", "name": owner.prefix, "id": None}])
            self.assertIs(owner.receipt["owned_resources"], owner.resources)

    def test_foreign_container_is_never_removed_by_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            resource = {"kind": "container", "name": owner.prefix + "-recovered", "id": None, "private": tmp}
            owner.resources.append(resource)
            foreign = container_fixture()
            foreign["Name"] = "/" + resource["name"]
            with patch.object(owner, "command", side_effect=["abc123", json.dumps([foreign])]) as command:
                with self.assertRaises(ValueError): owner.cleanup()
            self.assertEqual(command.call_count, 2)
            self.assertTrue(all("rm" not in call.args[0] and "stop" not in call.args[0] for call in command.call_args_list))
            self.assertIn("name=^/" + resource["name"] + "$", command.call_args_list[0].args[0])

    def test_owned_container_removal_is_attempted_even_if_log_capture_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lane.OwnedDocker(Path(tmp), {"commands": []}, lambda: None)
            owner.resources.append({"kind": "container", "name": owner.prefix + "-recovered", "id": "owned-id", "private": tmp})
            commands = []
            def command(args, name, *unused):
                commands.append(args)
                if name == "capture-owned-log": raise RuntimeError("synthetic capture failure")
                return ""
            with patch.object(owner, "find", return_value={"State": {"Running": False}}), patch.object(owner, "command", side_effect=command):
                with self.assertRaises(ValueError): owner.cleanup()
            self.assertIn(["container", "rm", "--force", "owned-id"], commands)
            self.assertEqual(owner.receipt["owned_cleanup"]["status"], "FAIL")

    def test_fixed_phase_deadline_does_not_reset_for_metadata_requests(self):
        with patch.object(lane.time, "monotonic", side_effect=[1, 9, 10]):
            self.assertEqual(lane.OwnedDocker.remaining(10), 9)
            self.assertEqual(lane.OwnedDocker.remaining(10), 1)
            with self.assertRaises(ValueError): lane.OwnedDocker.remaining(10)


if __name__ == "__main__":
    unittest.main()
