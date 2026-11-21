"""Synthetic rejection/orchestration controls, never Native acceptance.

No Docker daemon or account is used here. Actual native success remains two
separately selected source-bound Go methods after the unchanged baseline.
"""
import copy
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
from contextlib import redirect_stderr
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native_client_concurrent_replace as tail
import run_native_clients as lane
from test_native_clients import container_fixture, offline_branch_fixture, state_fixture


def hash_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def evidence(number, identifier, author, predecessor=None, role=None):
    return {"operation_id": f"{number:032x}", "claim_id": identifier, "digest": identifier.split("/")[1],
            "author_id": author, "kind": "REPLACE" if predecessor else "ADD", "target_sha256": "a" * 64,
            "source_sha256": "b" * 64, "payload_sha256": hash_text("t2-concurrent-replace-" + role if predecessor else
                "t2-offline-unique-" + ("creator" if number == 2 else "recovered")),
            "observed_claim_ids": [predecessor["claim_id"]] if predecessor else [], "claim_response_sha256": hash_text("claim-" + identifier)}


def fixtures():
    state = state_fixture()
    old = {role: offline_branch_fixture(role) for role in tail.ROLES}
    history = lane.merge_offline_histories(old, state)
    identities = {"heart_sha": "heart", "runtime_version": "runtime", "rpc_manifest_sha256": "schema", "registration_patch_sha256": "registry"}
    original_live = [old[role]["created_claim_ids"][0] for role in tail.ROLES]
    conflict = sorted(old[role]["created_claim_ids"][1] for role in tail.ROLES)
    predecessor = evidence(2, old["creator"]["created_claim_ids"][0], "native-signing-author")
    unrelated = evidence(3, old["recovered"]["created_claim_ids"][0], "native-signing-author")
    # Deliberately inverse physical-hash order for operations 8/9. Membership
    # alone, or sorting a received receipt, must not satisfy the new contract.
    successors = {role: evidence(index + 8, ("f" if index == 0 else "a") * 64 + "/" + chr(ord("c") + index) * 64,
                                 "native-signing-author", predecessor, role) for index, role in enumerate(tail.ROLES)}
    branches = {}
    for role in tail.ROLES:
        branch = copy.deepcopy(history)
        change = "replace-" + role
        branch["changes_sha256"][change] = hash_text(change)
        branch["parents"][change] = list(history["heads"])
        branch["heads"] = [change]
        branches[role] = branch
    merged = tail.merge_histories(history, branches)
    baselines, reports = {}, {phase: {} for phase in tail.PHASES[:-1]}
    mutations = {role: {"operation_id": successors[role]["operation_id"], "claim_id": successors[role]["claim_id"],
                        "disposition": "CREATED", "change_id": branches[role]["heads"][0], "request_sha256": hash_text("request-" + role),
                        "request_bytes": 310 + index, "returned_claim_sha256": successors[role]["claim_response_sha256"]}
                 for index, role in enumerate(tail.ROLES)}
    for index, role in enumerate(tail.ROLES):
        baselines[role] = {"nonce": "owner", "peer_id": "original-peer-" + role, "client_fixture_sha256": "b" * 64,
            "state_sha256": "c" * 64, "history": copy.deepcopy(history), "snapshot_sha256_without_local_sequence": "1" * 64}
        for step, phase in enumerate(tail.PHASES[:-1]):
            detached = role == "recovered" and phase in {"partitioned", "diverged"}
            report = {"protocol": tail.PROTOCOL, "phase": phase, "role": role, "nonce": "owner", "pid": 1,
                "network_namespace": "net:[" + role + "]", "actual_ipv4": [] if detached else ["172.30.0." + str(index + 2)],
                "native_network_mode": "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES", "native_network_state": "NOT_CONNECTED" if detached else "WIFI",
                "native_server_port": 4500, "peer_id": baselines[role]["peer_id"], "account_author_id": "native-signing-author", **identities,
                "client_fixture_sha256": "b" * 64, "state_sha256": "c" * 64, "clean_reopen_receipt_sha256": "d" * 64,
                "original_operation_sha256": state["OperationSHA256"], "original_claim_id": state["ClaimID"],
                "history": copy.deepcopy(history if step < 2 else branches[role] if phase == "diverged" else merged),
                "read_response_sha256": hash_text(role + "-read-" + phase),
                "snapshot_sha256_without_local_sequence": "1" * 64 if step < 2 else hash_text(phase + (role if phase == "diverged" else "")),
                "local_applied_sequence": step + index + 20, "live_claim_ids": list(original_live),
                "live_claims": copy.deepcopy([predecessor, unrelated]),
                "conflict_operation_id": f"{4:032x}", "conflict_claim_ids": list(conflict), "predecessor": copy.deepcopy(predecessor),
                "predecessor_observation_sha256": hash_text(role + "-read-" + (phase if step < 2 else "partitioned")),
                "successors": {}, "materialized_order": tail.ORDER, "rfc_causal_operation_id_display_order": "NOT_PROVEN",
                "app_capability": "OFF", "process_crash": "NOT_RUN", "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN",
                "two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "test_passed": False}
            if step >= 2:
                writers = (role,) if phase == "diverged" else tail.ROLES
                report["successors"] = {writer: copy.deepcopy(successors[writer]) for writer in writers}
                report["live_claims"] = copy.deepcopy([unrelated] + [successors[writer] for writer in writers])
                report["live_claim_ids"] = [value["claim_id"] for value in report["live_claims"]]
                report["mutation"] = copy.deepcopy(mutations[role])
            if phase == "merged":
                report["retries"] = {}
                for writer in (*tail.ROLES, "predecessor"):
                    chosen = predecessor if writer == "predecessor" else successors[writer]
                    original = old["creator"]["lost_client_reply"] if writer == "predecessor" else mutations[writer]
                    report["retries"][writer] = {"operation_id": chosen["operation_id"], "claim_id": chosen["claim_id"],
                        "disposition": "ALREADY_EXISTS_SAME_PAYLOAD", "change_id": "", "request_sha256": original["request_sha256"],
                        "request_bytes": original["request_bytes"], "returned_claim_sha256": chosen["claim_response_sha256"],
                        "before_response_sha256": report["read_response_sha256"], "after_response_sha256": report["read_response_sha256"],
                        "before_local_sequence": report["local_applied_sequence"], "after_local_sequence": report["local_applied_sequence"],
                        "history_before": copy.deepcopy(merged), "history_after": copy.deepcopy(merged)}
            reports[phase][role] = report
    return state, identities, baselines, reports, old["creator"]["lost_client_reply"]


def info_fixture(role, phase="ready"):
    info = container_fixture(role)
    index = tail.ROLES.index(role)
    info["Args"] = ["-test.run", "^" + tail.METHODS[role] + "$", "-test.count=1", "-test.v", "-test.timeout=720s"]
    info["Config"]["Env"] += ["PINKHA_T2_CLIENT_SCENARIO=" + lane.OFFLINE_PROTOCOL, "PINKHA_T2_CONCURRENT_REPLACE_PHASE=" + tail.PROTOCOL]
    info["State"].update(Pid=123 + index, StartedAt="synthetic-start")
    info["NetworkSettings"]["Networks"]["owned-network"]["IPAddress"] = "172.30.0." + str(index + 2)
    if role == "recovered" and phase in {"partitioned", "diverged"}:
        info["NetworkSettings"]["Networks"] = {}
    return info


def final_fixture(merged, hashes, role):
    final = copy.deepcopy(merged)
    counts = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen", "AccountStop", "AppShutdown"]}
    counts.update(DeviceNetworkStateSet=3 if role == "recovered" else 1, PinkhaTorahOperationsReadTarget=11, PinkhaTorahOperationsAppend=5)
    final.update(phase="final", test_passed=True, closed=True, account_stop_verified=True,
                 post_stop_rpc="READ_AND_APPEND_NOT_LOGGED_IN", rpc_calls=counts, returned_byte_calls=copy.deepcopy(counts))
    final.update({phase + "_receipt_sha256": hashes[phase] for phase in tail.PHASES[:-1]})
    return final


class PairFixture:
    """Metadata/temporary-file state machine. This is not a Native transport."""
    remaining = staticmethod(lane.OwnedDocker.remaining)

    def __init__(self, directory):
        self.owner, self.scenario = "owner", "offline"
        self.crash_after_commit, self.observed_remove_after_reopen, self.concurrent_replace_after_reopen = False, False, True
        self.state, self.identity, baselines, self.reports, predecessor = fixtures()
        self.network = {"Name": "owned-network", "Id": "network-id", "Internal": True}
        self.network_resource = {"kind": "network", "id": "network-id"}
        self.binary = directory / "native.test"
        self.binary.write_bytes(b"synthetic controller-only selection")
        self.directories, self.resources, self.infos, self.events, self.deadlines = {}, [], {}, [], []
        self.cancel_at, self.fault = None, None
        self.reopen = {"status": "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK", "results": {}}
        for role in tail.ROLES:
            root = directory / role
            root.mkdir()
            self.directories[role] = root
            (root / "account-root").mkdir()
            (root / "account-root/fixture.db").write_bytes(b"synthetic owned file, no database content")
            (root / "state.json").write_text(json.dumps(self.state))
            (root / "account-key.private").write_text("synthetic-key-for-boundary-tests-only")
            self.state_hash, self.key_hash = tail.digest(root / "state.json"), tail.digest(root / "account-key.private")
            baseline = {**baselines[role], "protocol": lane.OFFLINE_PROTOCOL, "phase": "reopened", "role": role,
                        "state_sha256": self.state_hash, "closed": True, "account_stop_verified": True,
                        "test_passed": True, "post_stop_rpc": "READ_AND_APPEND_NOT_LOGGED_IN"}
            (root / "reopened.json").write_text(json.dumps(baseline))
            old_id = "old-" + role
            self.resources.append({"kind": "container", "id": old_id, "role": role, "private": str(root)})
            self.infos[old_id] = {"State": {"Running": False, "ExitCode": 0}}
            self.reopen["results"][role] = {"container_id": old_id, "receipt_sha256": tail.digest(root / "reopened.json"), "native_named_pass": 1}
            for phase in self.reports.values():
                phase[role]["state_sha256"] = self.state_hash
                phase[role]["clean_reopen_receipt_sha256"] = tail.digest(root / "reopened.json")
        self.receipt = {"completed_offline_baseline": {"actual_counts": {"native_processes": 4, "native_named_pass": 4}},
                        "offline_convergence": {"lost_client_reply": {"clients": {"creator": predecessor}}}}

    def checkpoint(self):
        self.events.append(("checkpoint", self.receipt["concurrent_replace_after_reopen"]["phase"]))

    def find(self, resource, deadline=None):
        if deadline is not None:
            self.deadlines.append(deadline)
        if resource["kind"] == "network":
            return {**self.network, "Containers": {key: {} for key, info in self.infos.items()
                    if info["State"]["Running"] and info.get("NetworkSettings", {}).get("Networks")}}
        return self.infos.get(resource["id"])

    def start(self, role, network, directory, binary, fixture_sha, deadline, *, method):
        self.deadlines.append(deadline)
        assert not any(key.startswith("old-") for key in self.infos)
        assert method == tail.METHODS[role] and network == self.network and directory == self.directories[role]
        assert binary == self.binary and fixture_sha == "b" * 64
        info = info_fixture(role)
        info["Id"] = "new-" + role
        info["Config"]["User"] = f"{os.getuid()}:{os.getgid()}"
        info["Mounts"][0]["Source"], info["Mounts"][1]["Source"] = str(directory), str(binary)
        self.infos[info["Id"]] = info
        resource = {"kind": "container", "id": info["Id"], "role": role, "private": str(directory)}
        self.resources.append(resource)
        self.events.append(("start", role))
        return resource

    def command(self, args, name, timeout=30, destination=None):
        assert 0 < timeout <= 90
        if args[:2] == ["container", "rm"]:
            assert args[2].startswith("old-") and not self.infos[args[2]]["State"]["Running"]
            self.events.append(("retire", args[2]))
            del self.infos[args[2]]
            return ""
        if args[0] == "network":
            assert args[2:] == [self.network["Id"], "new-recovered"]
            if args[1] == "disconnect":
                assert all(("ready", role) in self.events for role in tail.ROLES)
                self.infos["new-recovered"]["NetworkSettings"]["Networks"] = {}
            else:
                assert args[1] == "connect" and all(("diverged", role) in self.events for role in tail.ROLES)
                self.infos["new-recovered"]["NetworkSettings"]["Networks"] = info_fixture("recovered")["NetworkSettings"]["Networks"]
            self.events.append((args[1], "recovered"))
            if self.fault == "detach_not_observed" and args[1] == "disconnect":
                self.infos["new-recovered"]["NetworkSettings"]["Networks"] = info_fixture("recovered")["NetworkSettings"]["Networks"]
            return ""
        role = args[2].removeprefix("new-")
        if args[:2] == ["container", "wait"]:
            root = self.directories[role]
            command = json.loads((root / "replace-stop.command.json").read_text())
            assert command["expected_history"] == self.reports["merged"][role]["history"]
            self.infos[args[2]]["State"].update(Running=False, ExitCode=0)
            final = final_fixture(self.reports["merged"][role], {phase: tail.digest(root / ("replace-" + phase + ".json")) for phase in tail.PHASES[:-1]}, role)
            if self.fault == "missing_shutdown":
                final["rpc_calls"]["AppShutdown"] = 0
            (root / "replace-final.json").write_text(json.dumps(final))
            self.events.append(("native-stop", role))
            return "0"
        assert args[:2] == ["container", "logs"] and destination is not None
        destination.write_text("--- PASS: " + tail.METHODS[role] + " (0.1s)\nPASS\n")
        return ""

    def wait_ready(self, resource, deadline, *, filename):
        self.deadlines.append(deadline)
        role, phase = resource["role"], filename.removeprefix("replace-").removesuffix(".json")
        if self.cancel_at == (role, phase):
            raise KeyboardInterrupt("synthetic control cancellation")
        if phase != "ready":
            selected = {"partitioned": "partition", "diverged": "write", "merged": "reconnect"}[phase]
            value = json.loads((self.directories[role] / ("replace-" + selected + ".command.json")).read_text())
            assert set(value) == {"protocol", "nonce", "role", "phase", "expected_history"}
            assert value["role"] == role and value["nonce"] == self.owner and value["protocol"] == tail.PROTOCOL
        self.events.append((phase, role))
        report = copy.deepcopy(self.reports[phase][role])
        if self.fault == "mount_order" and phase != "ready":
            self.infos[resource["id"]]["Mounts"].reverse()
        if self.fault == "container_rebound" and phase == "diverged":
            self.infos[resource["id"]]["Mounts"][0]["Source"] = "/foreign-store"
        if self.fault == "process_replaced" and phase == "merged":
            self.infos[resource["id"]]["State"]["StartedAt"] = "different-start"
        (self.directories[role] / filename).write_text(json.dumps(report))
        return report

    @staticmethod
    def validate_container(info, owner, role, network, directory, binary, image_id, uid, gid, *, scenario, method):
        lane.validate_container(info, owner, role, network, directory, binary, image_id, uid, gid,
                                scenario=scenario, method=method)

    def run(self):
        with patch.object(tail.os, "readlink", side_effect=lambda path: "net:[creator]" if "/123/" in path else "net:[recovered]"):
            return tail.sequence(self, self, self.directories, self.binary, "b" * 64, self.identity, "pinned-image-id",
                                 self.state, self.state_hash, self.key_hash, self.reopen, self.network_resource, self.network)


class ConcurrentReplaceControls(unittest.TestCase):
    def test_mount_identity_is_order_independent_but_preserves_every_field(self):
        original = info_fixture("creator")
        original["Mounts"][0]["FutureMountField"] = {"value": "must remain exact", "ordered": ["first", "second"]}
        original["HostConfig"]["FutureHostField"] = ["first", "second"]
        before = copy.deepcopy(original)
        wanted = tail.process_identity(original)
        for mounts in itertools.permutations(original["Mounts"]):
            value = copy.deepcopy(original)
            value["Mounts"] = list(mounts)
            self.assertEqual(tail.process_identity(value), wanted)
        self.assertEqual(original, before, "identity comparison cannot rewrite observed Docker metadata")
        mutations = {
            "source": lambda v: v["Mounts"][0].__setitem__("Source", "/foreign-store"),
            "destination": lambda v: v["Mounts"][0].__setitem__("Destination", "/foreign-target"),
            "rw": lambda v: v["Mounts"][0].__setitem__("RW", False),
            "type": lambda v: v["Mounts"][0].__setitem__("Type", "volume"),
            "unknown-field": lambda v: v["Mounts"][0]["FutureMountField"].__setitem__("value", "changed"),
            "nested-order": lambda v: v["Mounts"][0]["FutureMountField"]["ordered"].reverse(),
            "removed-field": lambda v: v["Mounts"][0].pop("FutureMountField"),
            "added-field": lambda v: v["Mounts"][0].__setitem__("AdditionalField", True),
            "added-mount": lambda v: v["Mounts"].append({"Destination": "/other", "Type": "tmpfs"}),
            "removed-mount": lambda v: v["Mounts"].pop(),
            "args-order": lambda v: v["Args"].reverse(),
            "env-order": lambda v: v["Config"]["Env"].reverse(),
            "host-config": lambda v: v["HostConfig"].__setitem__("Privileged", True),
            "host-order": lambda v: v["HostConfig"]["FutureHostField"].reverse(),
        }
        for name, mutate in mutations.items():
            value = copy.deepcopy(original)
            mutate(value)
            with self.subTest(name=name):
                self.assertNotEqual(tail.process_identity(value), wanted)

    def test_mount_identity_rejects_duplicate_or_malformed_destinations(self):
        original = info_fixture("creator")
        cases = [None, {}, [None], [{}], [{"Destination": ""}], [{"Destination": "relative"}],
                 [{"Destination": "/private\x00other"}], [{"Destination": 1}],
                 [copy.deepcopy(original["Mounts"][0]), copy.deepcopy(original["Mounts"][0])]]
        for mounts in cases:
            value = copy.deepcopy(original)
            value["Mounts"] = mounts
            with self.subTest(mounts=mounts), self.assertRaises(ValueError):
                tail.process_identity(value)

    def test_orchestration_accepts_only_mount_order_change(self):
        with tempfile.TemporaryDirectory() as temp:
            pair = PairFixture(Path(temp))
            pair.fault = "mount_order"
            result = pair.run()
            self.assertEqual(result["status"], tail.PASS)
            self.assertEqual(result["actual_counts"]["successor_retry_entries"], 4)
            self.assertEqual(result["actual_counts"]["predecessor_retry_entries"], 2)

    def test_identity_failure_diagnostic_exports_only_fixed_fields_and_booleans(self):
        original = info_fixture("creator")
        changed = copy.deepcopy(original)
        private = "private-value\n::error::must-not-be-exported"
        changed["Mounts"][0]["Source"] = private
        receipt = {}
        diagnostic = tail.phase_diagnostic(receipt, "creator", "partitioned")
        with self.assertRaises(ValueError):
            tail.require_same_identity(changed, tail.process_identity(original), diagnostic)
        self.assertEqual(diagnostic["check"], "PROCESS_METADATA")
        self.assertEqual(diagnostic["identity_fields_match"], {key: key != "Mounts" for key in tail.IDENTITY_FIELDS})
        self.assertNotIn(private, json.dumps(receipt))
        self.assertEqual(diagnostic["scope"], "DIAGNOSTIC_ONLY_NO_ACCEPTANCE")
        self.assertEqual(diagnostic["status"], "IN_PROGRESS")
        for role, phase in [(private, "ready"), ("creator", private)]:
            with self.subTest(role=role, phase=phase), self.assertRaises(ValueError):
                tail.phase_diagnostic(receipt, role, phase)

    def test_orchestration_preserves_failed_identity_and_process_check(self):
        for fault, check, field in [("container_rebound", "PROCESS_METADATA", "Mounts"),
                                    ("process_replaced", "PROCESS_CONTINUITY", "started_at")]:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                pair = PairFixture(Path(temp))
                pair.fault = fault
                with self.assertRaises(ValueError):
                    pair.run()
                diagnostic = pair.receipt["concurrent_replace_diagnostic"]
                self.assertEqual(diagnostic["check"], check)
                fields = "identity_fields_match" if fault == "container_rebound" else "process_fields_match"
                self.assertIs(diagnostic[fields][field], False)
                self.assertNotIn("/foreign-store", json.dumps(diagnostic))

    def test_selection_is_explicit_default_off_exclusive_and_offline_only(self):
        for scenario in ("bootstrap", "offline"):
            tail.validate_selection(scenario, False, False, False)
        for index in range(3):
            flags = [False] * 3
            flags[index] = True
            tail.validate_selection("offline", *flags)
        for values in [("bootstrap", False, False, True), ("offline", True, False, True), ("offline", False, True, True),
                       ("offline", True, True, False), ("foreign", False, False, False), ("offline", False, False, 1),
                       ("offline", "false", False, True)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                tail.validate_selection(*values)

    def test_original_signed_history_and_true_concurrent_branches_are_required(self):
        _, _, _, reports, _ = fixtures()
        before = reports["ready"]["creator"]["history"]
        branches = {role: reports["diverged"][role]["history"] for role in tail.ROLES}
        self.assertEqual(tail.merge_histories(before, branches), reports["merged"]["creator"]["history"])
        for mutation in (lambda v: v["changes_sha256"].__setitem__("root", "f" * 64),
                         lambda v: v["parents"].__setitem__("replace-creator", [before["heads"][0]]),
                         lambda v: v["parents"].__setitem__("change", ["replace-creator"]),
                         lambda v: v["changes_sha256"].__setitem__("extra", "a" * 64),
                         lambda v: v.__setitem__("heads", before["heads"])):
            candidate = copy.deepcopy(branches["creator"])
            mutation(candidate)
            with self.subTest(candidate=candidate["heads"]), self.assertRaises(ValueError):
                tail.branch(before, candidate)
        with self.assertRaises(ValueError):
            tail.merge_histories(before, {"creator": branches["creator"], "recovered": branches["creator"]})

    def test_history_rejects_unknown_raw_bytes_duplicate_heads_cycle_and_foreign_parent(self):
        _, _, _, reports, _ = fixtures()
        value = reports["merged"]["creator"]["history"]
        for mutation in (lambda h: h.__setitem__("signed_bytes", "not allowed"),
                         lambda h: h.__setitem__("heads", h["heads"] * 2),
                         lambda h: h["parents"].__setitem__("replace-creator", ["foreign"]),
                         lambda h: h["parents"].__setitem__("change", ["replace-creator"]),
                         lambda h: h["changes_sha256"].__setitem__("root", "not-sha")):
            changed = copy.deepcopy(value)
            mutation(changed)
            with self.subTest(changed=sorted(changed)), self.assertRaises(ValueError):
                tail.validate_history(changed, 10, 2)

    def test_source_account_namespace_network_and_scope_are_exact(self):
        state, identity, baseline, reports, _ = fixtures()
        network = {"Name": "owned-network", "Id": "network-id"}
        for phase in tail.PHASES[:-1]:
            for role in tail.ROLES:
                report, info = reports[phase][role], info_fixture(role, phase)
                with patch.object(tail.os, "readlink", return_value=report["network_namespace"]):
                    tail.validate_common(report, phase, role, baseline[role], "d" * 64, identity, state, info, network)
                    for key, replacement in [("peer_id", "foreign"), ("heart_sha", "other"), ("client_fixture_sha256", "other"),
                        ("state_sha256", "other"), ("clean_reopen_receipt_sha256", "other"), ("protocol", "other"),
                        ("network_namespace", "foreign"), ("native_network_state", "foreign"), ("pid", True),
                        ("test_passed", True), ("two_ios_apps", "PASS"), ("rfc_causal_operation_id_display_order", "PASS")]:
                        changed = copy.deepcopy(report)
                        changed[key] = replacement
                        with self.subTest(phase=phase, role=role, key=key), self.assertRaises(ValueError):
                            tail.validate_common(changed, phase, role, baseline[role], "d" * 64, identity, state, info, network)

    def test_successor_provenance_and_bytewise_order_are_not_repaired(self):
        state, identity, baseline, reports, _ = fixtures()
        report, info = reports["merged"]["creator"], info_fixture("creator", "merged")
        network = {"Name": "owned-network", "Id": "network-id"}
        self.assertNotEqual(report["live_claim_ids"], sorted(report["live_claim_ids"]),
                            "The synthetic successor hashes must distinguish OperationID order from physical-hash order")
        changes = [lambda r: r["live_claim_ids"].reverse(), lambda r: r["live_claim_ids"].pop(),
                   lambda r: r["live_claims"].reverse(), lambda r: r["live_claims"].pop(),
                   lambda r: r["live_claims"][0].__setitem__("operation_id", f"{2:032x}"),
                   lambda r: r["live_claims"][0].__setitem__("payload_sha256", "f" * 64),
                   lambda r: r["live_claims"][1].__setitem__("operation_id", f"{9:032x}"),
                   lambda r: r["live_claims"][1].__setitem__("claim_response_sha256", "f" * 64),
                   lambda r: r["successors"].pop("recovered"),
                   lambda r: r["successors"]["creator"].__setitem__("source_sha256", "f" * 64),
                   lambda r: r["successors"]["creator"].__setitem__("observed_claim_ids", []),
                   lambda r: r["successors"]["creator"].__setitem__("observed_claim_ids", [r["original_claim_id"]]),
                   lambda r: r["successors"]["creator"].__setitem__("payload_sha256", "f" * 64),
                   lambda r: r["successors"]["creator"].__setitem__("author_id", "foreign"),
                   lambda r: r["successors"]["creator"].__setitem__("kind", "ADD"),
                   lambda r: r["predecessor"].__setitem__("claim_id", r["original_claim_id"])]
        with patch.object(tail.os, "readlink", return_value=report["network_namespace"]):
            for index, change in enumerate(changes):
                candidate = copy.deepcopy(report)
                change(candidate)
                with self.subTest(index=index), self.assertRaises(ValueError):
                    tail.validate_common(candidate, "merged", "creator", baseline["creator"], "d" * 64, identity, state, info, network)
            candidate = copy.deepcopy(report)
            candidate["live_claims"].sort(key=lambda value: value["claim_id"])
            candidate["live_claim_ids"] = [value["claim_id"] for value in candidate["live_claims"]]
            self.assertEqual(set(candidate["live_claim_ids"]), set(report["live_claim_ids"]))
            before = copy.deepcopy(candidate)
            with self.subTest(correct_membership_wrong_physical_hash_order=True), self.assertRaisesRegex(ValueError, "actual native live order|Actual native live order"):
                tail.validate_common(candidate, "merged", "creator", baseline["creator"], "d" * 64, identity, state, info, network)
            self.assertEqual(candidate, before, "Validation must reject rather than repair received evidence")

    def test_write_requires_its_own_prior_native_observation_and_only_one_new_claim(self):
        _, _, _, reports, _ = fixtures()
        tail.validate_diverged(reports["diverged"], reports["partitioned"])
        changes = [lambda r: r.__setitem__("predecessor_observation_sha256", "f" * 64),
                   lambda r: r["mutation"].__setitem__("change_id", "foreign"),
                   lambda r: r["mutation"].__setitem__("operation_id", f"{9:032x}"),
                   lambda r: r["mutation"].__setitem__("returned_claim_sha256", "f" * 64),
                   lambda r: r["mutation"].__setitem__("disposition", "ALREADY_EXISTS_SAME_PAYLOAD"),
                   lambda r: r.__setitem__("live_claim_ids", reports["partitioned"]["creator"]["live_claim_ids"])]
        for index, change in enumerate(changes):
            candidate = copy.deepcopy(reports["diverged"])
            change(candidate["creator"])
            with self.subTest(index=index), self.assertRaises(ValueError):
                tail.validate_diverged(candidate, reports["partitioned"])

    def test_all_six_retries_require_actual_input_hash_length_and_no_native_change(self):
        _, _, _, reports, original = fixtures()
        args = reports["diverged"], reports["partitioned"], reports["merged"]["creator"]["history"], original
        tail.validate_merged(reports["merged"], *args)
        for role in tail.ROLES:
            for writer in (*tail.ROLES, "predecessor"):
                for key, value in [("request_sha256", "f" * 64), ("request_bytes", 1), ("change_id", "new-change"),
                                   ("returned_claim_sha256", "f" * 64), ("after_local_sequence", 999),
                                   ("after_response_sha256", "f" * 64), ("disposition", "CREATED"), ("history_after", {})]:
                    changed = copy.deepcopy(reports["merged"])
                    changed[role]["retries"][writer][key] = value
                    with self.subTest(role=role, writer=writer, key=key), self.assertRaises(ValueError):
                        tail.validate_merged(changed, *args)
        changed = copy.deepcopy(original)
        changed["request_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            tail.validate_merged(reports["merged"], *args[:-1], changed)

    def test_native_union_successor_variants_and_unrelated_conflict_are_preserved(self):
        _, _, _, reports, original = fixtures()
        args = reports["diverged"], reports["partitioned"], reports["merged"]["creator"]["history"], original
        for change in (lambda r: r.__setitem__("peer_id", reports["merged"]["recovered"]["peer_id"]),
                       lambda r: r.__setitem__("history", reports["diverged"]["creator"]["history"]),
                       lambda r: r["conflict_claim_ids"].pop(), lambda r: r["retries"].pop("predecessor"),
                       lambda r: r["successors"]["recovered"].__setitem__("digest", "f" * 64)):
            candidate = copy.deepcopy(reports["merged"])
            change(candidate["creator"])
            with self.subTest(keys=sorted(candidate["creator"])), self.assertRaises(ValueError):
                tail.validate_merged(candidate, *args)
        candidate = copy.deepcopy(reports["merged"])
        for report in candidate.values():
            report["live_claims"].sort(key=lambda value: value["claim_id"])
            report["live_claim_ids"] = [value["claim_id"] for value in report["live_claims"]]
        self.assertEqual(set(candidate["creator"]["live_claim_ids"]), set(reports["merged"]["creator"]["live_claim_ids"]))
        before = copy.deepcopy(candidate)
        with self.subTest(both_peers_agree_on_wrong_physical_hash_order=True), self.assertRaisesRegex(ValueError, "exact OperationID order"):
            tail.validate_merged(candidate, *args)
        self.assertEqual(candidate, before)

    def test_final_requires_exact_named_native_pass_shutdown_counters_and_prior_receipt_hashes(self):
        _, _, _, reports, _ = fixtures()
        for role in tail.ROLES:
            hashes = {phase: hash_text(phase) for phase in tail.PHASES[:-1]}
            value = final_fixture(reports["merged"][role], hashes, role)
            log = "--- PASS: " + tail.METHODS[role] + " (0.1s)\nPASS\n"
            tail.validate_final(value, reports["merged"][role], hashes, log, role)
            for key, replacement in [("closed", False), ("account_stop_verified", False), ("test_passed", False),
                                     ("post_stop_rpc", "not-denied"), ("ready_receipt_sha256", "f" * 64), ("rpc_calls", {}),
                                     ("returned_byte_calls", {})]:
                changed = copy.deepcopy(value)
                changed[key] = replacement
                with self.subTest(role=role, key=key), self.assertRaises(ValueError):
                    tail.validate_final(changed, reports["merged"][role], hashes, log, role)
            for changed_log in ("PASS\n", log * 2, log + "--- SKIP: foreign\n", log.replace("PASS:", "FAIL:"),
                                log.replace(tail.METHODS[role], "ForeignMethod")):
                with self.subTest(role=role, log=changed_log), self.assertRaises(ValueError):
                    tail.validate_final(value, reports["merged"][role], hashes, changed_log, role)

    def test_commands_never_carry_operations_or_replace_an_existing_owner_command(self):
        _, _, _, reports, _ = fixtures()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tail.command(directory, "creator", "owner", "partition", reports["ready"]["creator"]["history"])
            path = directory / "replace-partition.command.json"
            original = path.read_bytes()
            self.assertEqual(set(json.loads(original)), {"protocol", "nonce", "role", "phase", "expected_history"})
            for phase in ("partition", "../unsafe", "append-operation"):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    tail.command(directory, "creator", "owner", phase, reports["ready"]["creator"]["history"])
            self.assertEqual(path.read_bytes(), original)

    def test_orchestration_observes_both_clients_before_partition_and_write_before_reconnect(self):
        with tempfile.TemporaryDirectory() as temp:
            pair = PairFixture(Path(temp))
            baseline = copy.deepcopy(pair.receipt)
            result = pair.run()
            self.assertEqual(result["status"], tail.PASS)
            self.assertEqual(result["actual_counts"]["native_named_pass"], 2)
            self.assertEqual(result["actual_counts"]["new_signed_operations"], 2)
            self.assertEqual(result["actual_counts"]["signed_changes_after"], 10)
            self.assertEqual(pair.receipt["completed_offline_baseline"], baseline["completed_offline_baseline"])
            self.assertEqual(pair.receipt["offline_convergence"], baseline["offline_convergence"])
            self.assertEqual(len(set(pair.deadlines)), 1)
            self.assertEqual(pair.events, [("retire", "old-creator"), ("retire", "old-recovered"),
                ("start", "creator"), ("start", "recovered"), ("ready", "creator"), ("ready", "recovered"),
                ("disconnect", "recovered"), ("partitioned", "creator"), ("partitioned", "recovered"),
                ("diverged", "creator"), ("diverged", "recovered"), ("checkpoint", "DIVERGED"),
                ("connect", "recovered"), ("merged", "creator"), ("merged", "recovered"), ("native-stop", "creator"), ("native-stop", "recovered")])

    def test_cancel_propagates_to_existing_owner_cleanup_without_rewriting_baseline(self):
        for phase in ("partitioned", "diverged", "merged"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                pair = PairFixture(Path(temp))
                pair.cancel_at = ("recovered", phase)
                baseline = copy.deepcopy(pair.receipt["completed_offline_baseline"])
                with self.assertRaises(KeyboardInterrupt):
                    pair.run()
                self.assertEqual(pair.receipt["completed_offline_baseline"], baseline)
                self.assertNotIn(("native-stop", "creator"), pair.events)
                self.assertNotEqual(pair.receipt.get("concurrent_replace_after_reopen", {}).get("status"), tail.PASS)

    def test_orchestration_rejects_network_metadata_substitution_and_missing_native_shutdown(self):
        for fault in ("detach_not_observed", "container_rebound", "process_replaced", "missing_shutdown"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                pair = PairFixture(Path(temp))
                pair.fault = fault
                with self.assertRaises(ValueError):
                    pair.run()

    def test_original_store_recovery_or_baseline_changes_fail_before_new_native_start(self):
        for fault in ("live_owner", "baseline_changed", "recovery_changed", "shared_store", "stale_tail_receipt"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                pair = PairFixture(Path(temp))
                if fault == "live_owner":
                    pair.infos["old-creator"]["State"]["Running"] = True
                elif fault == "baseline_changed":
                    (pair.directories["creator"] / "reopened.json").write_text("{}")
                elif fault == "recovery_changed":
                    (pair.directories["creator"] / "account-key.private").write_text("changed synthetic key")
                elif fault == "stale_tail_receipt":
                    (pair.directories["creator"] / "replace-merged.json").write_text("{}")
                else:
                    root = pair.directories["recovered"] / "account-root"
                    (root / "fixture.db").unlink()
                    root.rmdir()
                    root.symlink_to(pair.directories["creator"] / "account-root", target_is_directory=True)
                with self.assertRaises(ValueError):
                    pair.run()
                self.assertFalse(any(event[0] == "start" for event in pair.events))


class ConcurrentReplaceIntegrationControls(unittest.TestCase):
    def test_cli_and_owner_reject_conflicting_tails_before_side_effects(self):
        flags = ["--crash-after-commit", "--observed-remove-after-reopen", "--concurrent-replace-after-reopen"]
        arguments = ["clients", "--evidence", "/unused", "--expected-app-sha", "a" * 40, "--scenario", "offline"]
        for chosen in itertools.combinations(flags, 2):
            with self.subTest(chosen=chosen), redirect_stderr(io.StringIO()), patch.object(lane, "OwnedDocker") as docker, \
                    patch.object(lane.base, "git") as git, self.assertRaises(SystemExit):
                lane.main(arguments + list(chosen))
            docker.assert_not_called()
            git.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            owner = lane.OwnedDocker(directory, {}, lambda: None)
            self.assertFalse(owner.concurrent_replace_after_reopen)
            for scenario, crash, observed in [("bootstrap", False, False), ("offline", True, False), ("offline", False, True)]:
                receipt = {}
                with self.subTest(scenario=scenario, crash=crash, observed=observed), self.assertRaises(ValueError):
                    lane.OwnedDocker(directory, receipt, lambda: None, scenario=scenario, crash_after_commit=crash,
                                     observed_remove_after_reopen=observed, concurrent_replace_after_reopen=True)
                self.assertEqual(receipt, {})
                self.assertEqual(list(directory.iterdir()), [])

    def test_exact_methods_and_native_container_authority_are_required(self):
        original_caps = {lane.METHOD: "2000s", lane.REOPEN_METHOD: "480s", lane.CRASH_COMMIT_METHOD: "480s",
                         **{name: "720s" for name in lane.observed_remove.METHODS.values()}}
        for method, cap in original_caps.items():
            self.assertEqual(lane.native_arguments("offline", method)[-1], "-test.timeout=" + cap)
        for role in tail.ROLES:
            method = tail.METHODS[role]
            self.assertEqual(lane.native_arguments("offline", method),
                             ["-test.run", "^" + method + "$", "-test.count=1", "-test.v", "-test.timeout=720s"])
            with self.assertRaises(ValueError):
                lane.native_arguments("bootstrap", method)
            info = info_fixture(role)
            def validate(value):
                lane.validate_container(value, "owner", role, {"Name": "owned-network", "Id": "network-id"},
                    Path("/owned/" + role), Path("/owned/native.test"), "pinned-image-id", 1001, 1001,
                    scenario="offline", method=method)
            validate(info)
            mutations = {
                "foreign-role": lambda v: v["Config"]["Env"].append("PINKHA_T2_CLIENT_ROLE=foreign"),
                "foreign-method": lambda v: v.__setitem__("Args", lane.native_arguments("offline", tail.METHODS[tail.ROLES[1-tail.ROLES.index(role)]])),
                "foreign-phase": lambda v: v["Config"]["Env"].append("PINKHA_T2_CONCURRENT_REPLACE_PHASE=foreign"),
                "crash-phase": lambda v: v["Config"]["Env"].append("PINKHA_T2_CRASH_PHASE=commit"),
                "observed-phase": lambda v: v["Config"]["Env"].append("PINKHA_T2_OBSERVED_REMOVE_PHASE=" + lane.observed_remove.PROTOCOL),
                "shared-store": lambda v: v["Mounts"][0].__setitem__("Source", "/other/account-root"),
                "writable-binary": lambda v: v["Mounts"][1].__setitem__("RW", True),
                "foreign-network": lambda v: v["NetworkSettings"]["Networks"].__setitem__("foreign", {"NetworkID": "other"}),
            }
            for name, mutate in mutations.items():
                wrong = copy.deepcopy(info); mutate(wrong)
                with self.subTest(role=role, fault=name), self.assertRaises(ValueError):
                    validate(wrong)
        with tempfile.TemporaryDirectory() as temp:
            for enabled, role, network, method in [(False, "creator", {"Name": "lan"}, tail.METHODS["creator"]),
                    (True, "creator", None, tail.METHODS["creator"]),
                    (True, "creator", {"Name": "lan"}, tail.METHODS["recovered"])]:
                docker = lane.OwnedDocker(Path(temp), {}, lambda: None, scenario="offline", concurrent_replace_after_reopen=enabled)
                with patch.object(docker, "command") as command, self.assertRaises(ValueError):
                    docker.start(role, network, Path(temp), Path(temp)/"binary", "f" * 64, None, method=method)
                command.assert_not_called()
        with self.assertRaises(ValueError):
            lane.native_arguments("offline", "TestArbitraryNativeMutation")

    def test_seven_fixture_pins_and_helper_controls_reject_source_drift(self):
        tools = Path(lane.__file__).parent
        manifest, files = lane.source_inputs(tools.parents[1])
        original = {
            "native_client_boundary_test.go": "42f77e6e330a8ba61d59043d4c08dc7326dd562f8bc40fff9f9a749874d33977",
            "native_client_crash_test.go": "55dc92b61c3d2c23811c5a86ab640b20b2f9dd88a50a26a472ee975c248eeac7",
            "native_client_observed_remove_test.go": "46a79040b22e08cbc6f5606ca6c1f60f041c82a3650563e1d682caae4def7f8a",
            "native_client_offline_test.go": "926bff2195377e3782730b9c126e63544f4589b41c82e8f1c460e8ed6f3fbcc2",
            "native_client_phase_test.go": "575772c30410362b7eb73455de322f03312a5fa683044b8b6dd91a94d3bba04f",
            "native_client_reopen_test.go": "0dc682139cf4ff334d7012c89d46999f4a78c3fa24187c76607dea486032a451",
        }
        self.assertEqual(set(files), set(original) | {"native_client_concurrent_replace_test.go"})
        self.assertEqual({name: manifest["go_sources_sha256"][name] for name in original}, original)
        baseline = set(lane.CONTROL_METHODS) | {name+"/"+case for name, cases in lane.CONTROL_METHODS.items() for case in cases}
        crash = set(lane.CRASH_CONTROL_METHODS) | {name+"/"+case for name, cases in lane.CRASH_CONTROL_METHODS.items() for case in cases}
        self.assertEqual((len(baseline), len(crash)), (42, 12))
        self.assertFalse((baseline | crash) & set(tail.METHODS.values()))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root/"Tools/TorahNativeOperations"
            for relative in ["two_clients/fixture.json", "two_clients/native-read-observation.patch",
                    *["two_clients/" + name for name in lane.GO_FILES], "run_account_rpc.py", "native_client_diagnostics.py",
                    "native_client_observed_remove.py", "native_client_concurrent_replace.py", "test_native_client_concurrent_replace.py"]:
                path = target/relative; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(tools/relative, path)
            lane.source_inputs(root)
            for relative in ["native_client_concurrent_replace.py", "test_native_client_concurrent_replace.py",
                             "two_clients/native_client_concurrent_replace_test.go", "run_account_rpc.py"]:
                path = target/relative; before = path.read_bytes(); path.write_bytes(before + b"\n# changed source\n")
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    lane.source_inputs(root)
                path.write_bytes(before)

    def test_new_publication_is_opt_in_fixed_and_secret_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); private = root/"private"
            for role in tail.ROLES:
                (private/role).mkdir(parents=True)
                for name in tail.FILES | {tail.LOG}:
                    (private/role/name).write_text("synthetic permitted receipt")
                (private/role/"replace-write.command.json").write_text("not an artifact")
                (private/role/"arbitrary.log").write_text("not an artifact")
            needles = ["synthetic-account-private-secret", "synthetic-mnemonic-private-secret"]
            (private/"creator/sensitive-needles.private").write_text(json.dumps(needles))
            for name in ["default", "enabled", "withheld", "symlink"]:
                (root/name).mkdir()
            self.assertEqual(lane.publish_native_evidence(private, root/"default", scenario="offline")["files_sha256"], {})
            result = lane.publish_native_evidence(private, root/"enabled", scenario="offline", concurrent_replace_after_reopen=True)
            self.assertEqual(set(result["files_sha256"]), {role+"/"+name for role in tail.ROLES for name in tail.FILES | {tail.LOG}})
            path = private/"recovered/replace-merged.json"
            path.write_text(needles[0])
            with self.assertRaises(ValueError):
                lane.publish_native_evidence(private, root/"withheld", scenario="offline", concurrent_replace_after_reopen=True)
            self.assertFalse((root/"withheld/native-clients").exists())
            path.unlink(); path.symlink_to(private/"creator/replace-merged.json")
            with self.assertRaises(ValueError):
                lane.publish_native_evidence(private, root/"symlink", scenario="offline", concurrent_replace_after_reopen=True)
            self.assertFalse((root/"symlink/native-clients").exists())

    def test_wrapper_and_workflow_use_the_same_closed_tail_selection(self):
        tools = Path(lane.__file__).parent
        wrapper = (tools/"run_native_clients_container.sh").read_text()
        workflow = (tools.parents[1]/".github/workflows/pinkha-t2-native-clients.yml").read_text()
        parent = (tools.parents[1]/".github/workflows/torah-inspector-ipados27.yml").read_text()
        wrapper_case = re.search(r"(?ms)^case .*?^esac$", wrapper).group(0)
        cases = re.findall(r"(?ms)^          case .*?^          esac$", workflow)
        self.assertEqual(len(cases), 2)
        cases = [textwrap.dedent(value) for value in cases]
        preflight, execution = cases
        flags = ["T2_NATIVE_CRASH_AFTER_COMMIT", "T2_NATIVE_OBSERVED_REMOVE_AFTER_REOPEN", "T2_NATIVE_CONCURRENT_REPLACE_AFTER_REOPEN"]
        choices = ["--crash-after-commit", "--observed-remove-after-reopen", "--concurrent-replace-after-reopen"]
        for scenario, values in itertools.product(["bootstrap", "offline"], itertools.product(["false", "true"], repeat=3)):
            allowed = values.count("true") == 0 or (scenario == "offline" and values.count("true") == 1)
            expected = choices[values.index("true")] if allowed and "true" in values else ""
            env = dict(os.environ, T2_NATIVE_SCENARIO=scenario, **dict(zip(flags, values)))
            scripts = [wrapper_case + '\nprintf "%s" "$*"', preflight,
                       'tail_args=()\n' + execution + '\nprintf "%s" "${tail_args[*]}"']
            for index, script in enumerate(scripts):
                with self.subTest(scenario=scenario, flags=values, entry=index):
                    result = subprocess.run(["bash", "-c", "set -e\n"+script], env=env, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0 if allowed else 2)
                    if allowed and index != 1:
                        self.assertEqual(result.stdout.decode(), expected)
            if not allowed:
                result = subprocess.run(["sh", str(tools/"run_native_clients_container.sh")], env=env, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, b"")
        for scenario, values in [("offline", ("false", "false", "unknown")),
                                 ("foreign", ("false", "false", "false"))]:
            env = dict(os.environ, T2_NATIVE_SCENARIO=scenario, **dict(zip(flags, values)))
            for index, script in enumerate([wrapper_case, preflight, 'tail_args=()\n' + execution]):
                with self.subTest(unknown_scenario=scenario, flags=values, entry=index):
                    result = subprocess.run(["bash", "-c", "set -e\n"+script], env=env, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 2)
        self.assertRegex(workflow, r"concurrent_replace_after_reopen:\n        type: boolean\n        default: false")
        self.assertIn("-e T2_NATIVE_CONCURRENT_REPLACE_AFTER_REOPEN", workflow)
        self.assertIn("if [ \"$T2_NATIVE_CONCURRENT_REPLACE_AFTER_REOPEN\" = true ]; then\n            python3 -B -m unittest -v test_native_client_concurrent_replace", workflow)
        self.assertIn("timeout-minutes: 60", workflow)
        self.assertEqual(parent.count("          - t2-native-clients-concurrent-replace\n"), 1)
        self.assertIn("concurrent_replace_after_reopen: ${{ inputs.route == 't2-native-clients-concurrent-replace' }}", parent)
        self.assertIn("crash_after_commit: ${{ inputs.route == 't2-native-clients-crash' }}", parent)
        self.assertIn("observed_remove_after_reopen: ${{ inputs.route == 't2-native-clients-observed-remove' }}", parent)

    def test_foreign_build_tail_selection_is_rejected_before_native_start(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            arguments = SimpleNamespace(control=directory, evidence=directory, expected_app_sha="a"*40,
                                        scenario="offline", crash_after_commit=False, observed_remove_after_reopen=False,
                                        concurrent_replace_after_reopen=True)
            receipt = {"run_id": "123", "run_attempt": "1"}
            built = {"status": "PASS_NATIVE_BUILD_AND_BASELINE_ONLY", "app_sha": "a"*40, "run_id": "123", "run_attempt": "1",
                     "scenario": "offline", "crash_after_commit_requested": False, "observed_remove_after_reopen_requested": False,
                     "fixture_sha256": "b"*64}
            for foreign in ({}, {"concurrent_replace_after_reopen_requested": False},
                            {"concurrent_replace_after_reopen_requested": True, "crash_after_commit_requested": True},
                            {"concurrent_replace_after_reopen_requested": True, "observed_remove_after_reopen_requested": True}):
                (directory/"native-clients-build.json").write_text(json.dumps(built | foreign))
                docker = lane.OwnedDocker(directory, {}, lambda: None, scenario="offline", concurrent_replace_after_reopen=True)
                with self.subTest(foreign=foreign), patch.object(lane, "source_inputs", return_value=({"fixture_sha256": "b"*64}, {})), \
                        patch.object(docker, "command") as command, self.assertRaisesRegex(ValueError, "Foreign or unsuccessful native build receipt"):
                    lane.clients(arguments, receipt, docker)
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
