"""Synthetic receipt/ownership controls, separate from the two real Native tests.

These tests neither create accounts nor simulate acceptance of native transport.
The workflow must execute both new byte-boundary methods after the old baseline.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import native_client_observed_remove as tail
import run_native_clients as lane
from test_native_clients import container_fixture, offline_branch_fixture, state_fixture


ROLES = ("creator", "recovered")
NEW_CLAIMS = {8: "a" * 64 + "/" + "b" * 64, 9: "c" * 64 + "/" + "d" * 64, 10: "e" * 64 + "/" + "f" * 64}


def add_history(before, number):
    value = copy.deepcopy(before)
    change = "causal-change-" + str(number)
    value["changes_sha256"][change] = format(number, "x") * 64
    value["parents"][change] = list(before["heads"])
    value["heads"] = [change]
    return value


def fixtures():
    state = state_fixture()
    history = lane.merge_offline_histories({role: offline_branch_fixture(role) for role in ROLES}, state)
    histories = {"ready": history}
    for phase, old, number in [("added", "ready", 8), ("removed", "added", 9), ("readded", "removed", 10)]:
        histories[phase] = add_history(histories[old], number)
    identity = {"heart_sha": "heart", "runtime_version": "runtime", "rpc_manifest_sha256": "schema", "registration_patch_sha256": "registry"}
    baselines, reports = {}, {phase: {} for phase in histories}
    original_live = sorted(offline_branch_fixture(role)["created_claim_ids"][0] for role in ROLES)
    conflict = sorted(offline_branch_fixture(role)["created_claim_ids"][1] for role in ROLES)
    for index, role in enumerate(ROLES):
        baselines[role] = {"nonce": "owner", "peer_id": "original-peer-" + role,
            "client_fixture_sha256": "b" * 64, "state_sha256": "c" * 64, "history": copy.deepcopy(history),
            "snapshot_sha256_without_local_sequence": "1" * 64}
        for step, phase in enumerate(histories):
            report = {"protocol": tail.PROTOCOL, "phase": phase, "role": role, "nonce": "owner", "pid": 1,
                "network_namespace": "net:[" + role + "]", "actual_ipv4": ["172.30.0." + str(index + 2)],
                "native_network_mode": "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES", "native_server_port": 4500,
                "peer_id": baselines[role]["peer_id"], "account_author_id": "actual-signing-account", **identity,
                "client_fixture_sha256": "b" * 64, "state_sha256": "c" * 64, "clean_reopen_receipt_sha256": "d" * 64,
                "original_operation_sha256": state["OperationSHA256"], "original_claim_id": state["ClaimID"],
                "history": copy.deepcopy(histories[phase]), "read_response_sha256": str(step + index + 1) * 64,
                "snapshot_sha256_without_local_sequence": str(step + 1) * 64, "local_applied_sequence": step + 20 + index,
                "live_claim_ids": list(original_live), "conflict_operation_id": f"{4:032x}", "conflict_claim_ids": list(conflict),
                "app_capability": "OFF", "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN",
                "two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "test_passed": False}
            if phase != "ready":
                operation = {"added": 8, "removed": 9, "readded": 10}[phase]
                writer = "recovered" if phase == "removed" else "creator"
                mutation = {"operation_id": f"{operation:032x}", "claim_id": NEW_CLAIMS[operation], "disposition": "CREATED",
                    "change_id": histories[phase]["heads"][0], "request_sha256": format(operation, "x") * 64, "request_bytes": 250}
                report["mutation"] = mutation if role == writer else None
                if phase in {"added", "readded"}:
                    report["live_claim_ids"] = sorted(original_live + [NEW_CLAIMS[operation]])
                if phase in {"added", "removed"}:
                    report["observed_add_claim_id"] = NEW_CLAIMS[8]
                if phase == "removed":
                    report["observation_before_remove_sha256"] = reports["added"][role]["read_response_sha256"]
                    report["remove_retry"] = {**mutation, "disposition": "ALREADY_EXISTS_SAME_PAYLOAD", "change_id": "",
                        "before_response_sha256": report["read_response_sha256"], "after_response_sha256": report["read_response_sha256"],
                        "before_local_sequence": report["local_applied_sequence"], "after_local_sequence": report["local_applied_sequence"],
                        "history_before": copy.deepcopy(histories[phase]), "history_after": copy.deepcopy(histories[phase])}
                if phase == "readded":
                    report.update(fresh_claim_id=NEW_CLAIMS[10], removed_claim_ids_verified=[state["ClaimID"], NEW_CLAIMS[8]])
            reports[phase][role] = report
    return state, identity, baselines, reports


def actual_container(role):
    value = container_fixture(role)
    index = ROLES.index(role)
    value["Args"] = lane.native_arguments("offline", tail.METHODS[role])
    value["Config"]["Env"] += ["PINKHA_T2_CLIENT_SCENARIO=" + lane.OFFLINE_PROTOCOL,
                               "PINKHA_T2_OBSERVED_REMOVE_PHASE=" + tail.PROTOCOL]
    value["State"].update(Pid=123 + index, StartedAt="synthetic-start")
    value["NetworkSettings"]["Networks"]["owned-network"]["IPAddress"] = "172.30.0." + str(index + 2)
    return value


def final_fixture(readded, role):
    value = copy.deepcopy(readded)
    value.pop("mutation")
    calls = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen",
                                  "DeviceNetworkStateSet", "AccountStop", "AppShutdown"]}
    calls.update(PinkhaTorahOperationsReadTarget=7, PinkhaTorahOperationsAppend=4 if role == "creator" else 3)
    value.update(phase="final", test_passed=True, closed=True, account_stop_verified=True,
                 post_stop_rpc="READ_AND_APPEND_NOT_LOGGED_IN", added_receipt_sha256="a" * 64, removed_receipt_sha256="b" * 64,
                 rpc_calls=calls, returned_byte_calls=copy.deepcopy(calls))
    return value


class CausalDockerFixture:
    """In-memory Docker responses plus temporary assertion files; not Native."""
    remaining = staticmethod(lane.OwnedDocker.remaining)

    def __init__(self, directory):
        self.owner, self.scenario = "owner", "offline"
        self.crash_after_commit, self.observed_remove_after_reopen = False, True
        self.state, self.identity, baseline, self.reports = fixtures()
        self.network = {"Name": "owned-network", "Id": "network-id"}
        self.network_resource = {"kind": "network", "id": "network-id"}
        self.binary = directory/"native.test"; self.binary.write_bytes(b"synthetic selection only")
        self.directories, self.resources, self.infos, self.events, self.deadlines = {}, [], {}, [], []
        self.reopen = {"status": "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK", "results": {}}
        for role in ROLES:
            root = directory/role; root.mkdir(); self.directories[role] = root
            (root/"account-root").mkdir(); (root/"account-root/fixture.db").write_bytes(b"synthetic controller fixture")
            (root/"state.json").write_text(json.dumps(self.state)); (root/"account-key.private").write_text("synthetic-only-private-key")
            self.state_hash, self.key_hash = lane.digest(root/"state.json"), lane.digest(root/"account-key.private")
            old = {**baseline[role], "protocol": lane.OFFLINE_PROTOCOL, "phase": "reopened", "role": role,
                   "state_sha256": self.state_hash, "closed": True, "account_stop_verified": True,
                   "test_passed": True, "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN"}
            (root/"reopened.json").write_text(json.dumps(old))
            identifier = "old-" + role
            self.resources.append({"kind": "container", "id": identifier, "role": role, "private": str(root)})
            self.infos[identifier] = {"State": {"Running": False, "ExitCode": 0}}
            self.reopen["results"][role] = {"container_id": identifier, "receipt_sha256": lane.digest(root/"reopened.json"), "native_named_pass": 1}
            for reports in self.reports.values():
                reports[role]["state_sha256"] = self.state_hash
                reports[role]["clean_reopen_receipt_sha256"] = lane.digest(root/"reopened.json")
        self.receipt = {"completed_offline_baseline": {"actual_counts": {"native_processes": 4, "native_named_pass": 4},
                                                     "disconnected_reopen": copy.deepcopy(self.reopen)}}
        self.cancel_at = None

    def checkpoint(self): pass

    def find(self, resource, deadline=None):
        if deadline is not None: self.deadlines.append(deadline)
        if resource["kind"] == "network":
            return {**self.network, "Containers": {key: {} for key, info in self.infos.items() if info["State"]["Running"]}}
        return self.infos.get(resource["id"])

    def start(self, role, network, directory, binary, fixture_sha, deadline, *, method):
        self.deadlines.append(deadline)
        assert all("old-" not in key for key in self.infos)
        assert network == self.network and method == tail.METHODS[role] and binary == self.binary and fixture_sha == "b" * 64
        info = actual_container(role); info["Id"] = "new-" + role
        info["Config"]["User"] = f"{os.getuid()}:{os.getgid()}"
        info["Mounts"][0]["Source"], info["Mounts"][1]["Source"] = str(directory), str(binary)
        self.infos[info["Id"]] = info
        resource = {"kind": "container", "id": info["Id"], "role": role, "private": str(directory)}
        self.resources.append(resource); self.events.append(("start", role))
        return resource

    def command(self, args, name, timeout=30, destination=None):
        assert 0 < timeout <= 90
        if args[:2] == ["container", "rm"]:
            assert args[2].startswith("old-") and self.infos[args[2]]["State"]["Running"] is False
            self.events.append(("retire", args[2])); del self.infos[args[2]]; return ""
        role = args[2].removeprefix("new-")
        if args[:2] == ["container", "wait"]:
            root = self.directories[role]
            assert json.loads((root/"observed-stop.command.json").read_text())["expected_history"] == self.reports["readded"][role]["history"]
            self.infos[args[2]]["State"].update(Running=False, ExitCode=0)
            final = final_fixture(self.reports["readded"][role], role)
            final.update(added_receipt_sha256=lane.digest(root/"observed-added.json"),
                         removed_receipt_sha256=lane.digest(root/"observed-removed.json"))
            (root/"observed-final.json").write_text(json.dumps(final))
            self.events.append(("native-stop", role)); return "0"
        assert args[:2] == ["container", "logs"] and destination is not None
        destination.write_text("--- PASS: " + tail.METHODS[role] + " (0.1s)\nPASS\n")
        return ""

    def wait_ready(self, resource, deadline, *, filename):
        self.deadlines.append(deadline)
        role, phase = resource["role"], filename.removeprefix("observed-").removesuffix(".json")
        if (role, phase) == self.cancel_at: raise KeyboardInterrupt("synthetic cancellation")
        commands = {("creator", "added"): "start-add", ("recovered", "added"): "read-add",
                    ("recovered", "removed"): "start-remove", ("creator", "removed"): "read-remove",
                    ("creator", "readded"): "start-readd", ("recovered", "readded"): "read-readd"}
        if phase != "ready":
            command = json.loads((self.directories[role]/("observed-"+commands[(role, phase)]+".command.json")).read_text())
            assert set(command) == {"protocol", "nonce", "role", "phase", "expected_history"}
            assert command["role"] == role and command["nonce"] == self.owner
        self.events.append((phase, role))
        report = copy.deepcopy(self.reports[phase][role])
        (self.directories[role]/filename).write_text(json.dumps(report))
        return report

    def run(self):
        with patch.object(tail.os, "readlink", side_effect=lambda path: "net:[creator]" if "/123/" in path else "net:[recovered]"):
            return tail.sequence(lane, self, self.directories, self.binary, "b" * 64, self.identity, "pinned-image-id",
                                 self.state, self.state_hash, self.key_hash, self.reopen, self.network_resource, self.network)


class ObservedRemoveControls(unittest.TestCase):
    def test_orchestration_keeps_baseline_separate_orders_real_observation_barriers_and_propagates_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            docker = CausalDockerFixture(Path(temp))
            baseline = copy.deepcopy(docker.receipt["completed_offline_baseline"])
            result = docker.run()
            self.assertEqual(result["status"], tail.PASS)
            self.assertEqual(result["actual_counts"], {"native_processes": 2, "native_named_pass": 2, "native_fail": 0,
                "native_skip": 0, "new_signed_operations": 3, "signed_changes_before": 8, "signed_changes_after": 11})
            self.assertEqual(docker.receipt["completed_offline_baseline"], baseline)
            self.assertEqual(len(set(docker.deadlines)), 1)
            self.assertEqual(docker.events, [("retire", "old-creator"), ("retire", "old-recovered"),
                ("start", "creator"), ("start", "recovered"), ("ready", "creator"), ("ready", "recovered"),
                ("added", "creator"), ("added", "recovered"), ("removed", "recovered"), ("removed", "creator"),
                ("readded", "creator"), ("readded", "recovered"), ("native-stop", "creator"), ("native-stop", "recovered")])
        with tempfile.TemporaryDirectory() as temp:
            docker = CausalDockerFixture(Path(temp)); docker.cancel_at = ("recovered", "removed")
            baseline = copy.deepcopy(docker.receipt["completed_offline_baseline"])
            with self.assertRaises(KeyboardInterrupt): docker.run()
            self.assertEqual(docker.receipt["completed_offline_baseline"], baseline)
            self.assertEqual(docker.receipt["observed_remove_after_reopen"]["status"], "IN_PROGRESS")
            self.assertNotIn(("readded", "creator"), docker.events)
            # The exception reaches the existing caller's owned cleanup; this
            # unit fixture does not claim an actual Docker/Native cleanup run.

    def test_tail_is_default_off_exclusive_and_requires_full_offline_baseline(self):
        for scenario, crash, observed in [("bootstrap", False, False), ("offline", False, False),
                                           ("offline", True, False), ("offline", False, True)]:
            tail.validate_selection(scenario, crash, observed)
        for values in [("bootstrap", False, True), ("bootstrap", True, False), ("offline", True, True),
                       ("foreign", False, False), ("offline", "false", True), ("offline", False, 1)]:
            with self.subTest(values=values), self.assertRaises(ValueError): tail.validate_selection(*values)
        args = ["clients", "--evidence", "/unused", "--expected-app-sha", "a" * 40, "--scenario", "offline",
                "--crash-after-commit", "--observed-remove-after-reopen"]
        with redirect_stderr(io.StringIO()), patch.object(lane, "OwnedDocker") as docker, self.assertRaises(SystemExit):
            lane.main(args)
        docker.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            value = lane.OwnedDocker(Path(temp), {}, lambda: None)
            self.assertFalse(value.observed_remove_after_reopen)

    def test_original_42_and_crash_12_control_inventories_do_not_gain_tail_methods(self):
        baseline = {name for name in lane.CONTROL_METHODS}
        baseline |= {name + "/" + case for name, cases in lane.CONTROL_METHODS.items() for case in cases}
        crash = {name for name in lane.CRASH_CONTROL_METHODS}
        crash |= {name + "/" + case for name, cases in lane.CRASH_CONTROL_METHODS.items() for case in cases}
        self.assertEqual(len(baseline), 42)
        self.assertEqual(len(crash), 12)
        self.assertEqual(len(set(tail.METHODS.values())), 2)
        self.assertFalse((baseline | crash) & set(tail.METHODS.values()))
        self.assertEqual(lane.native_arguments("offline")[-1], "-test.timeout=2000s")
        self.assertEqual(lane.native_arguments("offline", lane.REOPEN_METHOD)[-1], "-test.timeout=480s")
        self.assertEqual(lane.native_arguments("offline", lane.CRASH_COMMIT_METHOD)[-1], "-test.timeout=480s")

    def test_history_requires_exact_one_child_and_preserves_every_old_byte_and_parent(self):
        _, _, _, reports = fixtures()
        before, after = reports["ready"]["creator"]["history"], reports["added"]["creator"]["history"]
        self.assertEqual(tail.child(before, after), "causal-change-8")
        changes = {
            "changed-old-byte": lambda r: r["changes_sha256"].update(root="f" * 64),
            "extra-signed-change": lambda r: r["changes_sha256"].update(extra="f" * 64),
            "missing-original": lambda r: r["changes_sha256"].pop("change"),
            "changed-old-parent": lambda r: r["parents"].update(change=["creator-change-0"]),
            "missing-causal-parent": lambda r: r["parents"].update({"causal-change-8": [before["heads"][0]]}),
            "cycle": lambda r: r["parents"].update({"causal-change-8": ["causal-change-8"]}),
            "fake-head": lambda r: r.update(heads=["root"]),
            "signed-payload": lambda r: r.update(raw_signed_changes="private bytes"),
        }
        for name, mutate in changes.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                altered = copy.deepcopy(after); mutate(altered); tail.child(before, altered)
        for old, phase in [("added", "removed"), ("removed", "readded")]:
            tail.child(reports[old]["creator"]["history"], reports[phase]["creator"]["history"])

    def test_common_receipt_requires_original_device_author_source_actual_lan_and_scope(self):
        state, identity, baseline, reports = fixtures()
        report, info = reports["ready"]["creator"], actual_container("creator")
        network = {"Name": "owned-network"}
        def validate(value):
            with patch.object(tail.os, "readlink", return_value="net:[creator]"):
                tail.validate_common(value, "ready", "creator", baseline["creator"], "d" * 64, identity, state, info, network)
        validate(report)
        for key, value in {"peer_id": "other", "nonce": "other", "role": "recovered", "pid": True,
                           "client_fixture_sha256": "f" * 64, "state_sha256": "f" * 64, "clean_reopen_receipt_sha256": "f" * 64,
                           "original_operation_sha256": "f" * 64, "account_author_id": "", "heart_sha": "foreign",
                           "actual_ipv4": [], "network_namespace": "net:[foreign]", "test_passed": True,
                           "power_loss": "PASS", "disconnected_reopen_after_tail": "PASS", "app_capability": "ON",
                           "local_applied_sequence": True, "native_server_port": 0}.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                altered = copy.deepcopy(report); altered[key] = value; validate(altered)
        with self.assertRaises(ValueError): validate({**report, "request_payload": "not permitted"})

    def test_native_pair_cannot_alias_author_device_namespace_or_semantic_result(self):
        _, _, _, reports = fixtures()
        tail.validate_pair(reports["ready"])
        for key, value in {"peer_id": reports["ready"]["creator"]["peer_id"],
                           "network_namespace": reports["ready"]["creator"]["network_namespace"],
                           "actual_ipv4": reports["ready"]["creator"]["actual_ipv4"],
                           "account_author_id": "different-native-author", "snapshot_sha256_without_local_sequence": "f" * 64}.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                altered = copy.deepcopy(reports["ready"]); altered["recovered"][key] = value; tail.validate_pair(altered)

    def test_causal_added_removed_readded_require_local_observation_and_three_identical_entry_hashes(self):
        _, _, _, reports = fixtures()
        for old, phase in [("ready", "added"), ("added", "removed"), ("removed", "readded")]:
            tail.validate_transition(reports[old], reports[phase], phase, reports["ready"])
        mutations = {
            "A-foreign-request": lambda r: r["creator"]["remove_retry"].update(request_sha256="0" * 64),
            "B-reencoded-different": lambda r: r["recovered"]["remove_retry"].update(request_sha256="0" * 64),
            "different-byte-count": lambda r: r["creator"]["remove_retry"].update(request_bytes=251),
            "new-commit-on-retry": lambda r: r["creator"]["remove_retry"].update(disposition="CREATED", change_id="extra"),
            "wrong-remove-id": lambda r: r["recovered"]["remove_retry"].update(operation_id=f"{8:032x}"),
            "stale-original-claim": lambda r: r["creator"].update(observed_add_claim_id=r["creator"]["original_claim_id"]),
            "no-own-read": lambda r: r["recovered"].update(observation_before_remove_sha256="0" * 64),
            "retry-local-seq-change": lambda r: r["creator"]["remove_retry"].update(after_local_sequence=999),
            "retry-response-change": lambda r: r["creator"]["remove_retry"].update(after_response_sha256="0" * 64),
            "retry-history-change": lambda r: r["creator"]["remove_retry"]["history_after"]["changes_sha256"].update(extra="0" * 64),
            "observer-created": lambda r: r["creator"].update(mutation=copy.deepcopy(r["recovered"]["mutation"])),
            "lost-unrelated-add": lambda r: r["creator"]["live_claim_ids"].pop(),
            "changed-original-conflict": lambda r: r["creator"]["conflict_claim_ids"].reverse(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                changed = copy.deepcopy(reports["removed"]); mutate(changed)
                tail.validate_transition(reports["added"], changed, "removed", reports["ready"])

    def test_final_readd_cannot_revive_old_claim_or_replace_independent_live_set(self):
        _, _, _, reports = fixtures()
        for mutate in [lambda r: r.update(fresh_claim_id=NEW_CLAIMS[8]),
                       lambda r: r.update(removed_claim_ids_verified=[r["original_claim_id"]]),
                       lambda r: r["mutation"].update(operation_id=f"{8:032x}"),
                       lambda r: r.update(live_claim_ids=[NEW_CLAIMS[10]]),
                       lambda r: r.update(account_author_id="changed")]:
            changed = copy.deepcopy(reports["readded"]); mutate(changed["creator"])
            with self.assertRaises(ValueError): tail.validate_transition(reports["removed"], changed, "readded", reports["ready"])

    def test_final_requires_exact_two_separate_methods_native_shutdown_and_unmodified_reports(self):
        _, _, _, reports = fixtures()
        for role in ROLES:
            ready = reports["readded"][role]
            final = final_fixture(ready, role)
            log = "--- PASS: " + tail.METHODS[role] + " (0.01s)\nPASS\n"
            tail.validate_final(final, ready, "a" * 64, "b" * 64, log, role)
            for key, value in {"closed": False, "account_stop_verified": False, "post_stop_rpc": "NOT_RUN",
                               "added_receipt_sha256": "0" * 64, "removed_receipt_sha256": "0" * 64, "test_passed": False}.items():
                with self.subTest(role=role, key=key), self.assertRaises(ValueError):
                    changed = copy.deepcopy(final); changed[key] = value
                    tail.validate_final(changed, ready, "a" * 64, "b" * 64, log, role)
            for changed_log in ["", log.replace("PASS:", "SKIP:"), log + log, log + "--- FAIL: other (1s)",
                                log.replace(tail.METHODS[role], lane.METHOD)]:
                with self.subTest(log=changed_log[:50]), self.assertRaises(ValueError):
                    tail.validate_final(final, ready, "a" * 64, "b" * 64, changed_log, role)
            for mutate in [lambda r: r["rpc_calls"].update(AccountCreate=1),
                           lambda r: r["returned_byte_calls"].update(PinkhaTorahOperationsAppend=0),
                           lambda r: r["rpc_calls"].update(AccountStop=0)]:
                changed = copy.deepcopy(final); mutate(changed)
                with self.assertRaises(ValueError): tail.validate_final(changed, ready, "a" * 64, "b" * 64, log, role)

    def test_fixed_commands_carry_only_expected_hashes_and_cannot_replay_or_inject_history(self):
        _, _, _, reports = fixtures()
        history = reports["added"]["creator"]["history"]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tail.command(directory, "recovered", "owner", "read-add", history)
            data = json.loads((directory / "observed-read-add.command.json").read_text())
            self.assertEqual(set(data), {"protocol", "nonce", "role", "phase", "expected_history"})
            self.assertEqual(data["expected_history"], history)
            with self.assertRaises(ValueError): tail.command(directory, "recovered", "owner", "read-add", history)
            for role, phase, changed in [("creator", "read-add", history), ("recovered", "read-add/../bad", history),
                                         ("recovered", "start-remove", {**history, "signed_bytes": "private"}),
                                         ("creator", "start-readd", history)]:
                with self.subTest(role=role, phase=phase), self.assertRaises(ValueError):
                    tail.command(directory, role, "owner", phase, changed)

    def test_owned_native_selection_rejects_wrong_role_network_and_implicit_tail(self):
        for role in ROLES:
            info = actual_container(role)
            lane.validate_container(info, "owner", role, {"Name": "owned-network", "Id": "network-id"},
                Path("/owned/" + role), Path("/owned/native.test"), "pinned-image-id", 1001, 1001,
                scenario="offline", method=tail.METHODS[role])
            wrong = copy.deepcopy(info); wrong["Config"]["Env"].append("PINKHA_T2_CRASH_PHASE=recover")
            with self.assertRaises(ValueError):
                lane.validate_container(wrong, "owner", role, {"Name": "owned-network", "Id": "network-id"},
                    Path("/owned/" + role), Path("/owned/native.test"), "pinned-image-id", 1001, 1001,
                    scenario="offline", method=tail.METHODS[role])
        with tempfile.TemporaryDirectory() as temp:
            for enabled, role, network, method in [(False, "creator", {"Name": "lan"}, tail.METHODS["creator"]),
                    (True, "creator", None, tail.METHODS["creator"]),
                    (True, "creator", {"Name": "lan"}, tail.METHODS["recovered"])]:
                docker = lane.OwnedDocker(Path(temp), {}, lambda: None, scenario="offline", observed_remove_after_reopen=enabled)
                with patch.object(docker, "command") as command, self.assertRaises(ValueError):
                    docker.start(role, network, Path(temp), Path(temp)/"binary", "f" * 64, None, method=method)
                command.assert_not_called()

    def test_publication_is_opt_in_allowlisted_and_secret_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); private = root/"private"
            for role in ROLES: (private/role).mkdir(parents=True)
            for name in ["ordinary", "enabled", "withheld"]: (root/name).mkdir()
            needles = ["synthetic-account-private-secret", "synthetic-mnemonic-private-secret"]
            (private/"creator/sensitive-needles.private").write_text(json.dumps(needles))
            for role in ROLES:
                (private/role/"observed-ready.json").write_text("{}")
                (private/role/tail.LOG).write_text("synthetic log only")
                (private/role/"observed-start-add.command.json").write_text("not an artifact")
            ordinary = lane.publish_native_evidence(private, root/"ordinary", scenario="offline")
            self.assertEqual(ordinary["files_sha256"], {})
            enabled = lane.publish_native_evidence(private, root/"enabled", scenario="offline", observed_remove_after_reopen=True)
            self.assertEqual(set(enabled["files_sha256"]), {role+"/"+name for role in ROLES for name in ["observed-ready.json", tail.LOG]})
            (private/"recovered/observed-ready.json").write_text(needles[0])
            with self.assertRaises(ValueError):
                lane.publish_native_evidence(private, root/"withheld", scenario="offline", observed_remove_after_reopen=True)

    def test_source_binding_rejects_changed_causal_controller_and_go_bytes(self):
        tools = Path(lane.__file__).parent
        lane.source_inputs(tools.parents[1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root/"Tools/TorahNativeOperations"
            for relative in ["two_clients/fixture.json", "two_clients/native-read-observation.patch",
                             *["two_clients/" + name for name in lane.GO_FILES], "run_account_rpc.py",
                             "native_client_diagnostics.py", "native_client_observed_remove.py",
                             "native_client_concurrent_replace.py", "test_native_client_concurrent_replace.py"]:
                path = target/relative; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(tools/relative, path)
            lane.source_inputs(root)
            for relative in ["native_client_observed_remove.py", "two_clients/native_client_observed_remove_test.go"]:
                path = target/relative; original = path.read_bytes(); path.write_bytes(original+b"\n// source changed\n")
                with self.subTest(relative=relative), self.assertRaises(ValueError): lane.source_inputs(root)
                path.write_bytes(original)

    def test_wrapper_rejects_incompatible_selection_before_install_or_build(self):
        script = Path(lane.__file__).with_name("run_native_clients_container.sh")
        for scenario, crash, observed in [("offline", "true", "true"), ("bootstrap", "false", "true"),
                                           ("offline", "false", "unknown")]:
            env = dict(os.environ, T2_NATIVE_SCENARIO=scenario, T2_NATIVE_CRASH_AFTER_COMMIT=crash,
                       T2_NATIVE_OBSERVED_REMOVE_AFTER_REOPEN=observed)
            result = subprocess.run(["sh", str(script)], env=env, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, b"")
            self.assertIn(b"Unsupported or mutually exclusive", result.stdout)


if __name__ == "__main__":
    unittest.main()
