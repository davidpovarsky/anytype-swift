"""Rejection controls for source, isolated native clients and evidence publication.

These controls do not create accounts or claim Docker/Native acceptance.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
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


def offline_branch_fixture(role):
    state = state_fixture()
    ids = [role + "-change-" + str(index) for index in range(3)]
    prefixes = ["7", "9", "c"] if role == "creator" else ["8", "9", "d"]
    suffix = "e" if role == "creator" else "f"
    claims = [prefix * 64 + "/" + suffix * 64 for prefix in prefixes]
    history = {"changes_sha256": {**state["RawChanges"], **{name: str(index + 7) * 64 for index, name in enumerate(ids)}},
               "parents": {state["ChangeID"]: [state["RootID"]], ids[0]: [state["ChangeID"]], ids[1]: [ids[0]], ids[2]: [ids[1]]},
               "heads": [ids[2]]}
    return {"history": history, "created_change_ids": ids, "created_claim_ids": claims,
            "local_snapshot_sha256": suffix * 64, "retry_and_collision": "PASS_LOCAL_EXACT_RETRY_AND_REJECTED_DIFFERENT_BYTES",
            "removed_observed_original": True}


def convergence_fixture(history):
    return {"history": history, "live_count": 2, "conflict_count": 1, "conflict_variants": 2,
            "retry_and_collision": "PASS_CONFLICT_VARIANTS_PRESERVED_IDEMPOTENT_REPLAY",
            "concurrent_remove_add_remove": "OBSERVED_ORIGINAL_REMOVED_CONCURRENT_UNIQUE_ADDS_RETAINED",
            "restart": "NOT_RUN", "crash_after_commit": "NOT_RUN", "snapshot_sha256_without_local_sequence": "a" * 64,
            "local_applied_sequence": 7}


class NativeClientControls(unittest.TestCase):
    def test_original_read_observation_is_exact_compile_overlay_and_preserves_source(self):
        tools = Path(lane.__file__).parent
        original = tools / "rpc/overlay/core/pinkha_torah_rpc.go"
        observation_patch = tools / "two_clients/native-read-observation.patch"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            heart, work = root / "heart", root / "work"
            source = heart / lane.account.NATIVE_READ_OBSERVATION["source_path"]
            source.parent.mkdir(parents=True)
            shutil.copyfile(original, source)
            work.mkdir()
            calls = []
            def run(command, label, cwd, env):
                calls.append(label)
                subprocess.run(command, cwd=cwd, env=env, check=True, timeout=10,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            replacement, receipt = lane.account.prepare_native_read_observation(heart, observation_patch, work, run)
            self.assertEqual(lane.digest(source), lane.account.NATIVE_READ_OBSERVATION["before_sha256"])
            self.assertEqual(lane.digest(replacement), lane.account.NATIVE_READ_OBSERVATION["after_sha256"])
            self.assertEqual(calls, ["native-read-observation-check", "native-read-observation-apply"])
            self.assertEqual(receipt["scope"], "TEST_COMPILE_OVERLAY_ONLY_ORIGINAL_READ_ERROR")
            self.assertEqual(replacement.read_text().count("mw.NativeTorahTargetRead(ctx, native)"), 1)
            self.assertEqual(replacement.read_text().count("return pinkhaTorahReadToWire(result, err)"), 1)
            with self.assertRaises(ValueError):
                lane.account.prepare_native_read_observation(heart, observation_patch, work, run)

    def test_changed_read_source_or_observation_patch_rejected_before_copy(self):
        tools = Path(lane.__file__).parent
        original = tools / "rpc/overlay/core/pinkha_torah_rpc.go"
        good_patch = tools / "two_clients/native-read-observation.patch"
        for changed in ["source", "patch"]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                heart, work = root / "heart", root / "work"
                source = heart / lane.account.NATIVE_READ_OBSERVATION["source_path"]
                source.parent.mkdir(parents=True)
                source.write_bytes(original.read_bytes() + (b"\n// drift\n" if changed == "source" else b""))
                observation_patch = root / "native-read-observation.patch"
                observation_patch.write_bytes(good_patch.read_bytes() + (b"\n# drift\n" if changed == "patch" else b""))
                work.mkdir()
                def forbidden(*args): self.fail("Git patch must not run after source/patch drift")
                with self.assertRaises(ValueError):
                    lane.account.prepare_native_read_observation(heart, observation_patch, work, forbidden)
                self.assertEqual(list(work.iterdir()), [])

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
        self.assertEqual(lane.validate_native_controls(output)["pass_terminals"], 28)
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

    def test_offline_union_requires_two_original_disjoint_signed_branches(self):
        reports = {role: offline_branch_fixture(role) for role in ["creator", "recovered"]}
        actual = lane.merge_offline_histories(reports, state_fixture())
        self.assertEqual(len(actual["changes_sha256"]), 8)
        self.assertEqual(len(actual["parents"]), 7)
        self.assertEqual(len(actual["heads"]), 2)
        for mutation in [lambda x: x["recovered"]["history"]["changes_sha256"].update(root="0" * 64),
                         lambda x: x["recovered"]["history"]["parents"].update({"recovered-change-1": ["creator-change-0"]}),
                         lambda x: x["recovered"].update(created_change_ids=x["creator"]["created_change_ids"]),
                         lambda x: x["recovered"]["created_claim_ids"].__setitem__(1, "0" * 64 + "/" + "f" * 64),
                         lambda x: x["recovered"].update(local_snapshot_sha256=x["creator"]["local_snapshot_sha256"]),
                         lambda x: x["creator"]["history"].update(raw_signed_bytes="forbidden")]:
            bad = copy.deepcopy(reports); mutation(bad)
            with self.assertRaises(ValueError): lane.merge_offline_histories(bad, state_fixture())

    def test_convergence_requires_both_variants_and_preserves_local_clock_semantics(self):
        branches = {role: offline_branch_fixture(role) for role in ["creator", "recovered"]}
        history = lane.merge_offline_histories(branches, state_fixture())
        reports = {role: convergence_fixture(history) for role in branches}
        reports["recovered"]["local_applied_sequence"] = 99
        self.assertEqual(lane.validate_convergence(reports, history), "a" * 64)
        for key, value in [("live_count", 1), ("conflict_variants", 1), ("conflict_count", 0), ("history", {}),
                           ("snapshot_sha256_without_local_sequence", "b" * 64), ("restart", "PASS"), ("local_applied_sequence", True)]:
            bad = copy.deepcopy(reports); bad["recovered"][key] = value
            with self.subTest(field=key):
                with self.assertRaises(ValueError): lane.validate_convergence(bad, history)

    def test_native_network_state_cannot_substitute_for_actual_attachment(self):
        _, _, ready = ready_fixture()
        good = {"protocol": lane.OFFLINE_PROTOCOL, "phase": "partitioned", "role": "recovered", "nonce": "owner",
                "pid": 1, "client_fixture_sha256": ready["client_fixture_sha256"], "peer_id": ready["peer_id"],
                "actual_ipv4": [], "native_network_state": "NOT_CONNECTED", "app_capability": "OFF", "full_t2_acceptance": "NOT_RUN"}
        lane.validate_offline_report(good, "partitioned", "recovered", ready, [])
        for key, value in [("actual_ipv4", ["172.30.0.3"]), ("native_network_state", "WIFI"), ("nonce", "foreign"),
                           ("phase", "converged"), ("peer_id", "other-device"), ("full_t2_acceptance", "PASS")]:
            bad = dict(good); bad[key] = value
            with self.assertRaises(ValueError): lane.validate_offline_report(bad, "partitioned", "recovered", ready, [])

    def test_reopen_container_cannot_repair_data_through_a_peer_network(self):
        info = container_fixture()
        info["Args"] = lane.native_arguments("offline", lane.REOPEN_METHOD)
        info["Config"]["Env"].append("PINKHA_T2_CLIENT_SCENARIO=" + lane.OFFLINE_PROTOCOL)
        info["HostConfig"]["NetworkMode"] = "none"
        info["NetworkSettings"]["Networks"] = {"none": {"IPAddress": ""}}
        def validate(value):
            lane.validate_container(value, "owner", "recovered", None, Path("/owned/recovered"), Path("/owned/native.test"),
                                    "pinned-image-id", 1001, 1001, scenario="offline", method=lane.REOPEN_METHOD)
        validate(info)
        for change in [lambda x: x["NetworkSettings"]["Networks"].update({"owned-network": {"IPAddress": "172.30.0.3"}}),
                       lambda x: x["NetworkSettings"]["Networks"]["none"].update(IPAddress="172.30.0.3"),
                       lambda x: x["HostConfig"].update(NetworkMode="owned-network")]:
            bad = copy.deepcopy(info); change(bad)
            with self.assertRaises(ValueError): validate(bad)

    def test_fixed_offline_commands_cannot_be_replaced_or_import_history_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lane.offline_command(root, "recovered", "owner", "partition")
            with self.assertRaises(ValueError): lane.offline_command(root, "recovered", "owner", "partition")
            with self.assertRaises(ValueError): lane.offline_command(root, "recovered", "owner", "import-signed-history")
            payload = json.loads((root / "partition.command.json").read_text())
            self.assertEqual(set(payload), {"protocol", "nonce", "role", "phase", "expected_history"})
            self.assertEqual(payload["expected_history"], {"changes_sha256": {}, "parents": {}, "heads": []})
        expected = lane.merge_offline_histories({role: offline_branch_fixture(role) for role in ["creator", "recovered"]}, state_fixture())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lane.offline_command(root, "recovered", "owner", "reconnect", expected)
            self.assertEqual(json.loads((root / "reconnect.command.json").read_text())["expected_history"], expected)
        for change in [lambda x: x.update(raw_signed_bytes="forbidden"),
                       lambda x: x["changes_sha256"].update(root="signed-payload-not-a-hash"),
                       lambda x: x["parents"].update({"creator-change-0": ["unknown-parent"]}),
                       lambda x: x.update(heads=[x["heads"][0]] * 2)]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); bad = copy.deepcopy(expected); change(bad)
                with self.assertRaises(ValueError): lane.offline_command(root, "recovered", "owner", "reconnect", bad)
                self.assertFalse((root / "reconnect.command.json").exists())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError): lane.offline_command(root, "recovered", "owner", "write", expected)
            with self.assertRaises(ValueError): lane.offline_command(root, "recovered", "owner", "reconnect")

    def test_reopened_final_requires_exact_read_only_calls_and_actual_native_pass(self):
        ready = {"pid": 1, "peer_id": "original-peer", "native_network_mode": "DISCONNECTED_REOPEN_NO_PEER_REPAIR"}
        calls = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen",
                                      "DeviceNetworkStateSet", "AccountStop", "AppShutdown", "PinkhaTorahOperationsAppend"]}
        calls["PinkhaTorahOperationsReadTarget"] = 2
        final = {**ready, "rpc_calls": calls, "returned_byte_calls": dict(calls), "closed": True,
                 "account_stop_verified": True, "test_passed": True, "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN"}
        log = "--- PASS: " + lane.REOPEN_METHOD + " (0.1s)\nPASS\n"
        lane.validate_reopen_final(ready, final, log)
        bad = copy.deepcopy(final)
        bad["rpc_calls"]["PinkhaTorahOperationsAppend"] = bad["returned_byte_calls"]["PinkhaTorahOperationsAppend"] = 2
        with self.assertRaises(ValueError): lane.validate_reopen_final(ready, bad, log)
        with self.assertRaises(ValueError): lane.validate_reopen_final(ready, final, "PASS\n")


if __name__ == "__main__":
    unittest.main()
