"""Default-off causal same-association tail for the existing owned native pair.

No payload, encoded request or signed history is copied between stores. Only
fixed commands and original IDs/hashes cross the assertion boundary. All Docker
execution, cancellation and cleanup remain in run_native_clients.OwnedDocker.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import time

import run_account_lifecycle as base

PROTOCOL = "pinkha-t2-native-observed-remove-readd-v1"
METHODS = {"creator": "TestT2NativeClientObservedRemoveCreatorPhase",
           "recovered": "TestT2NativeClientObservedRemoveRecoveredPhase"}
FILES = {"observed-" + phase + ".json" for phase in ["ready", "added", "removed", "readded", "final"]}
LOG = "observed-remove-native.log"
PASS = "PASS_NATIVE_SAME_ASSOCIATION_CAUSAL_REMOVE_READD_AND_EXACT_REMOVE_RETRY"
COMMON_KEYS = {"protocol", "phase", "role", "nonce", "pid", "network_namespace", "actual_ipv4", "native_network_mode",
               "native_server_port", "peer_id", "account_author_id", "heart_sha", "runtime_version", "client_fixture_sha256",
               "rpc_manifest_sha256", "registration_patch_sha256", "state_sha256", "clean_reopen_receipt_sha256",
               "original_operation_sha256", "original_claim_id", "history", "read_response_sha256",
               "snapshot_sha256_without_local_sequence", "local_applied_sequence", "live_claim_ids", "conflict_operation_id",
               "conflict_claim_ids", "app_capability", "power_loss", "disconnected_reopen_after_tail", "two_ios_apps",
               "full_t2_acceptance", "test_passed"}
EXTRA_KEYS = {"ready": set(), "added": {"mutation", "observed_add_claim_id"},
              "removed": {"mutation", "remove_retry", "observed_add_claim_id", "observation_before_remove_sha256"},
              "readded": {"mutation", "fresh_claim_id", "removed_claim_ids_verified"},
              "final": {"fresh_claim_id", "removed_claim_ids_verified", "added_receipt_sha256", "removed_receipt_sha256",
                        "rpc_calls", "returned_byte_calls", "closed", "account_stop_verified", "post_stop_rpc"}}
MUTATION_KEYS = {"operation_id", "claim_id", "disposition", "change_id", "request_sha256", "request_bytes"}
RETRY_KEYS = MUTATION_KEYS | {"before_response_sha256", "after_response_sha256", "before_local_sequence",
                            "after_local_sequence", "history_before", "history_after"}
COMMANDS = {"creator": {"start-add", "read-remove", "start-readd", "stop"},
            "recovered": {"read-add", "start-remove", "read-readd", "stop"}}
require, digest, write = base.require, base.digest, base.write_json


def validate_selection(scenario: str, crash: bool, observed: bool) -> None:
    require(type(crash) is bool and type(observed) is bool and scenario in {"bootstrap", "offline"}, "Unknown native tail selection")
    require(not (crash and observed), "Crash and observed-remove tails are mutually exclusive")
    require(not (crash or observed) or scenario == "offline", "Optional tails require the unchanged offline and clean-reopen baseline")


def sha(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def claim(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}/[0-9a-f]{64}", value) is not None


def validate_history(value: dict, count: int) -> None:
    require(isinstance(value, dict) and set(value) == {"changes_sha256", "parents", "heads"}, "Only signed IDs and hashes are permitted")
    changes, parents, heads = value["changes_sha256"], value["parents"], value["heads"]
    require(type(count) is int and 8 <= count <= 11 and isinstance(changes, dict) and len(changes) == count
            and all(isinstance(key, str) and 0 < len(key) <= 512 and "\x00" not in key for key in changes)
            and all(sha(item) for item in changes.values()), "Unexpected native signed-history identities")
    require(isinstance(parents, dict) and len(parents) == count - 1 and set(parents) < set(changes)
            and all(isinstance(items, list) and 1 <= len(items) <= 2 and items == sorted(set(items))
                    and all(item in changes and item != key for item in items) for key, items in parents.items()),
            "Unexpected signed parent graph")
    root = next(iter(set(changes) - set(parents)))
    for start in changes:
        visiting, done = set(), set()
        def visit(node):
            require(node not in visiting, "Cyclic signed parent metadata")
            if node in done: return
            visiting.add(node)
            for parent in parents.get(node, []): visit(parent)
            visiting.remove(node)
            done.add(node)
        visit(start)
        require(root in done, "Disconnected signed parent metadata")
    wanted = sorted(set(changes) - {parent for items in parents.values() for parent in items})
    require(isinstance(heads, list) and heads == wanted and len(heads) == (2 if count == 8 else 1),
            "Causal tail must join the original two heads, then retain one tip")


def child(before: dict, after: dict) -> str:
    validate_history(before, len(before.get("changes_sha256", {})))
    validate_history(after, len(before["changes_sha256"]) + 1)
    require(all(after["changes_sha256"].get(key) == value for key, value in before["changes_sha256"].items())
            and all(after["parents"].get(key) == value for key, value in before["parents"].items()),
            "Previously signed bytes or parents changed")
    added = set(after["changes_sha256"]) - set(before["changes_sha256"])
    require(len(added) == 1, "Exactly one new signed operation is required")
    identifier = added.pop()
    require(after["heads"] == [identifier] and after["parents"][identifier] == before["heads"],
            "New operation did not extend its actual causal predecessors")
    return identifier


def command(directory: Path, role: str, owner: str, phase: str, history: dict) -> None:
    require(role in COMMANDS and phase in COMMANDS[role], "Only fixed role-specific native commands are allowed")
    counts = {"start-add": 8, "read-add": 9, "start-remove": 9, "read-remove": 10, "start-readd": 10, "read-readd": 11, "stop": 11}
    validate_history(history, counts[phase])
    require(isinstance(owner, str) and bool(owner), "Actual owner required")
    path = directory / ("observed-" + phase + ".command.json")
    require(not path.exists() and not path.is_symlink(), "Native command cannot be replaced or replayed")
    write(path, {"protocol": PROTOCOL, "nonce": owner, "role": role, "phase": phase, "expected_history": history})


def validate_common(report: dict, phase: str, role: str, baseline: dict, baseline_sha: str,
                    identity: dict, state: dict, info: dict, network: dict) -> None:
    require(phase in EXTRA_KEYS and isinstance(report, dict) and set(report) == COMMON_KEYS | EXTRA_KEYS[phase],
            "Unexpected observed-remove receipt fields")
    require(report["protocol"] == PROTOCOL and report["phase"] == phase and report["role"] == role
            and report["nonce"] == baseline["nonce"] and type(report["pid"]) is int and report["pid"] == 1,
            "Foreign observed-remove process/phase")
    require(info["State"].get("Running") is True and type(info["State"].get("Pid")) is int and info["State"]["Pid"] > 0
            and report["network_namespace"] == os.readlink(f"/proc/{info['State']['Pid']}/ns/net")
            and report["actual_ipv4"] == [info["NetworkSettings"]["Networks"][network["Name"]]["IPAddress"]]
            and report["actual_ipv4"][0] and report["native_network_mode"] == "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES",
            "Native tail is not on the observed owned LAN")
    require(type(report["native_server_port"]) is int and 0 < report["native_server_port"] < 65536
            and report["peer_id"] == baseline["peer_id"] and report["client_fixture_sha256"] == baseline["client_fixture_sha256"]
            and report["state_sha256"] == baseline["state_sha256"] and report["clean_reopen_receipt_sha256"] == baseline_sha,
            "Original native device/store/source binding changed")
    require(isinstance(report["account_author_id"], str) and 0 < len(report["account_author_id"]) <= 512
            and report["original_operation_sha256"] == state["OperationSHA256"] and report["original_claim_id"] == state["ClaimID"],
            "Native signing author was not checked against the original claim")
    require(all(report[key] == identity[key] for key in ["heart_sha", "runtime_version", "rpc_manifest_sha256", "registration_patch_sha256"]),
            "Different native source identity")
    require(all(report[key] == "NOT_RUN" for key in ["power_loss", "disconnected_reopen_after_tail", "two_ios_apps", "full_t2_acceptance"])
            and report["app_capability"] == "OFF" and report["test_passed"] is (phase == "final"),
            "Causal Native proof overstates its acceptance")
    count = {"ready": 8, "added": 9, "removed": 10, "readded": 11, "final": 11}[phase]
    validate_history(report["history"], count)
    require(all(sha(report[key]) for key in ["read_response_sha256", "snapshot_sha256_without_local_sequence"])
            and type(report["local_applied_sequence"]) is int and report["local_applied_sequence"] > 0,
            "Actual native read/sequence evidence missing")
    for key, length in [("live_claim_ids", 3 if phase in {"added", "readded", "final"} else 2), ("conflict_claim_ids", 2)]:
        values = report[key]
        require(isinstance(values, list) and len(values) == length and values == sorted(set(values)) and all(claim(v) for v in values),
                "Actual live/conflict claims missing or duplicated")
    require(not set(report["live_claim_ids"]).intersection(report["conflict_claim_ids"])
            and report["original_claim_id"] not in report["live_claim_ids"]
            and report["conflict_operation_id"] == f"{4:032x}", "Removed original or conflicting variant became live")
    if phase == "ready":
        require(report["history"] == baseline["history"]
                and report["snapshot_sha256_without_local_sequence"] == baseline["snapshot_sha256_without_local_sequence"],
                "Causal tail does not start from the exact clean-reopen baseline")


def validate_mutation(value, operation: int, claim_id: str, change_id: str) -> None:
    require(isinstance(value, dict) and set(value) == MUTATION_KEYS, "Actual generated append receipt is missing")
    require(value["operation_id"] == f"{operation:032x}" and value["claim_id"] == claim_id and claim(claim_id)
            and value["disposition"] == "CREATED" and value["change_id"] == change_id
            and sha(value["request_sha256"]) and type(value["request_bytes"]) is int and 0 < value["request_bytes"] <= 65536,
            "Unexpected operation identity, native disposition or encoded bytes")


def validate_pair(reports: dict) -> None:
    require(set(reports) == {"creator", "recovered"}, "Both actual Native observations are required")
    a, b = reports["creator"], reports["recovered"]
    require(a["peer_id"] != b["peer_id"] and a["network_namespace"] != b["network_namespace"]
            and a["actual_ipv4"] != b["actual_ipv4"], "The two original native devices must stay distinct")
    for key in ["account_author_id", "history", "snapshot_sha256_without_local_sequence", "live_claim_ids", "conflict_claim_ids",
                "conflict_operation_id", "original_operation_sha256", "original_claim_id"]:
        require(a[key] == b[key], "Native peers did not converge to the same complete causal state")


def validate_transition(before: dict, current: dict, phase: str, ready: dict) -> None:
    require(set(before) == set(current) == set(ready) == {"creator", "recovered"}, "Complete native pair required")
    for role, report in current.items():
        old, baseline = before[role], ready[role]
        require(report["account_author_id"] == baseline["account_author_id"]
                and report["conflict_claim_ids"] == baseline["conflict_claim_ids"], "Native author or original conflict variants changed")
        new_change = child(old["history"], report["history"])
        original_live = set(baseline["live_claim_ids"])
        if phase == "added":
            new_claim = report["observed_add_claim_id"]
            require(claim(new_claim) and new_claim != baseline["original_claim_id"]
                    and set(report["live_claim_ids"]) == original_live | {new_claim} and len(original_live | {new_claim}) == 3,
                    "Fresh ADD did not preserve the two unrelated live claims")
            if role == "creator": validate_mutation(report["mutation"], 8, new_claim, new_change)
            else: require(report["mutation"] is None, "Observer must obtain ADD through native transport")
        elif phase == "removed":
            observed = report["observed_add_claim_id"]
            require(observed == old["observed_add_claim_id"] and report["observation_before_remove_sha256"] == old["read_response_sha256"]
                    and set(report["live_claim_ids"]) == original_live, "REMOVE was not causally based on this client's own observed fresh claim")
            retry = report["remove_retry"]
            require(isinstance(retry, dict) and set(retry) == RETRY_KEYS and retry["operation_id"] == f"{9:032x}"
                    and claim(retry["claim_id"]) and retry["claim_id"] not in original_live | {observed, baseline["original_claim_id"]}
                    and retry["disposition"] == "ALREADY_EXISTS_SAME_PAYLOAD" and retry["change_id"] == ""
                    and sha(retry["request_sha256"]) and type(retry["request_bytes"]) is int and 0 < retry["request_bytes"] <= 65536,
                    "Exact REMOVE retry did not resolve to the existing native REMOVE claim")
            require(retry["before_response_sha256"] == retry["after_response_sha256"] == report["read_response_sha256"]
                    and type(retry["before_local_sequence"]) is int and type(retry["after_local_sequence"]) is int
                    and retry["before_local_sequence"] == retry["after_local_sequence"] == report["local_applied_sequence"]
                    and retry["history_before"] == retry["history_after"] == report["history"],
                    "REMOVE retry changed the full local snapshot, local sequence or signed history")
            if role == "recovered":
                validate_mutation(report["mutation"], 9, retry["claim_id"], new_change)
                require(report["mutation"]["request_sha256"] == retry["request_sha256"]
                        and report["mutation"]["request_bytes"] == retry["request_bytes"], "B's actual REMOVE retry bytes differ")
            else: require(report["mutation"] is None, "A must receive REMOVE through native transport before its no-op retry")
        elif phase == "readded":
            new_claim = report["fresh_claim_id"]
            require(claim(new_claim) and report["removed_claim_ids_verified"] == [baseline["original_claim_id"], old["observed_add_claim_id"]]
                    and new_claim not in report["removed_claim_ids_verified"]
                    and set(report["live_claim_ids"]) == original_live | {new_claim} and len(original_live | {new_claim}) == 3,
                    "Fresh re-ADD revived a removed physical claim or lost an independent claim")
            if role == "creator": validate_mutation(report["mutation"], 10, new_claim, new_change)
            else: require(report["mutation"] is None, "Observer must obtain the final ADD through native transport")
        else: raise ValueError("Unknown causal phase")
    validate_pair(current)
    if phase == "removed":
        first = current["recovered"]["mutation"]
        for report in current.values():
            retry = report["remove_retry"]
            require(all(retry[key] == first[key] for key in ["operation_id", "claim_id", "request_sha256", "request_bytes"]),
                    "A and B did not invoke byte-identical independently encoded REMOVE requests")


def validate_final(final: dict, ready: dict, added_hash: str, removed_hash: str, log: str, role: str) -> None:
    require(set(final) == COMMON_KEYS | EXTRA_KEYS["final"], "Unexpected final native receipt")
    expected = {key: value for key, value in ready.items() if key not in {"phase", "test_passed", "mutation"}}
    require(all(final.get(key) == value for key, value in expected.items()) and final["phase"] == "final"
            and final["test_passed"] is True and final["closed"] is True and final["account_stop_verified"] is True
            and final["post_stop_rpc"] == "READ_AND_APPEND_NOT_LOGGED_IN"
            and final["added_receipt_sha256"] == added_hash and final["removed_receipt_sha256"] == removed_hash,
            "Native completion lost causal observations, account shutdown or post-stop denial")
    expected_calls = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen",
                                         "DeviceNetworkStateSet", "AccountStop", "AppShutdown"]}
    calls = final["rpc_calls"]
    require(isinstance(calls, dict) and set(calls) == set(expected_calls) | {"PinkhaTorahOperationsReadTarget", "PinkhaTorahOperationsAppend"}
            and all(type(calls[key]) is int and calls[key] == value for key, value in expected_calls.items())
            and type(calls["PinkhaTorahOperationsAppend"]) is int and calls["PinkhaTorahOperationsAppend"] == (4 if role == "creator" else 3)
            and type(calls["PinkhaTorahOperationsReadTarget"]) is int and 7 <= calls["PinkhaTorahOperationsReadTarget"] <= 2000
            and calls == final["returned_byte_calls"], "Unexpected account creation, mutation, missing response or shutdown boundary")
    passed = re.findall(r"^\s*--- PASS: (\S+) \(", log, re.M)
    require(passed == [METHODS[role]] and "--- FAIL:" not in log and "--- SKIP:" not in log,
            "Exactly one actual new named Native PASS per original client is required")


def sequence(api, docker, directories: dict, binary: Path, fixture_sha: str, identity: dict, image_id: str,
             state: dict, state_hash: str, key_hash: str, reopen: dict, network_resource: dict, network: dict) -> dict:
    """Use only the established controller's owned Docker and byte test binary."""
    require(docker.observed_remove_after_reopen and not docker.crash_after_commit and docker.scenario == "offline",
            "Observed-remove is an explicit mutually exclusive offline tail")
    deadline = time.monotonic() + 600
    require(reopen.get("status") == "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK"
            and set(reopen.get("results", {})) == set(METHODS), "Exact two-store disconnected reopen must precede the optional tail")
    baselines, baseline_hashes, directory_ids = {}, {}, {}
    for role, directory in directories.items():
        path = directory / "reopened.json"
        require(path.is_file() and not path.is_symlink() and digest(path) == reopen["results"][role]["receipt_sha256"],
                "The frozen clean-reopen receipt changed")
        baselines[role], baseline_hashes[role] = json.loads(path.read_text()), digest(path)
        require(baselines[role]["closed"] is True and baselines[role]["account_stop_verified"] is True
                and baselines[role]["test_passed"] is True and baselines[role]["post_stop_rpc"] == "READ_AND_APPEND_NOT_LOGGED_IN"
                and digest(directory / "state.json") == state_hash and digest(directory / "account-key.private") == key_hash,
                "Original account is not closed or its recovery identity changed")
        root = directory / "account-root"
        require(root.is_dir() and not root.is_symlink(), "Original native store missing")
        directory_ids[role] = (root.stat().st_dev, root.stat().st_ino)
        matches = [resource for resource in docker.resources if resource.get("id") == reopen["results"][role]["container_id"]]
        require(len(matches) == 1 and matches[0]["role"] == role and matches[0]["private"] == str(directory),
                "Cannot retire a different native process")
        stopped = docker.find(matches[0], deadline)
        require(stopped and stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0,
                "A previous native process still owns the original database")
        docker.command(["container", "rm", matches[0]["id"]], "retire-reopen-for-observed-" + role, docker.remaining(deadline))
    require(len(set(directory_ids.values())) == 2, "The original native stores alias")
    current_network = docker.find(network_resource, deadline)
    require(current_network and current_network["Id"] == network["Id"] and not current_network.get("Containers"),
            "The original owned LAN contains another peer")
    resources = {role: docker.start(role, network, directories[role], binary, fixture_sha, deadline, method=METHODS[role]) for role in METHODS}
    require(len({r["id"] for r in resources.values()}) == 2
            and not {r["id"] for r in resources.values()}.intersection(item["container_id"] for item in reopen["results"].values()),
            "The causal pair must use two fresh native OS processes")
    live, phases, file_hashes = {}, {}, {}
    def read_phase(role, phase):
        report = docker.wait_ready(resources[role], deadline, filename="observed-" + phase + ".json")
        info = docker.find(resources[role], deadline)
        api.validate_container(info, docker.owner, role, network, directories[role], binary, image_id, os.getuid(), os.getgid(),
                               scenario="offline", method=METHODS[role])
        validate_common(report, phase, role, baselines[role], baseline_hashes[role], identity, state, info, network)
        process = {"container_id": info["Id"], "host_pid": info["State"]["Pid"], "namespace": report["network_namespace"],
                   "started_at": info["State"]["StartedAt"]}
        if role in live: require(live[role] == process, "Native causal process changed mid-sequence")
        else: live[role] = process
        file_hashes[(role, phase)] = digest(directories[role] / ("observed-" + phase + ".json"))
        return report
    phases["ready"] = {role: read_phase(role, "ready") for role in METHODS}
    validate_pair(phases["ready"])
    require(len({value["host_pid"] for value in live.values()}) == 2, "Two native process IDs required")
    require(set(docker.find(network_resource, deadline).get("Containers", {})) == {r["id"] for r in resources.values()},
            "Unexpected peer joined the owned causal LAN")
    steps = [("added", "creator", "start-add", "recovered", "read-add", "ready"),
             ("removed", "recovered", "start-remove", "creator", "read-remove", "added"),
             ("readded", "creator", "start-readd", "recovered", "read-readd", "removed")]
    for phase, writer, write_command, observer, read_command, previous in steps:
        command(directories[writer], writer, docker.owner, write_command, phases[previous][writer]["history"])
        writer_report = read_phase(writer, phase)
        # Check the writer's one-change extension before forwarding even its
        # IDs/hashes as an expectation to the independently reading peer.
        child(phases[previous][writer]["history"], writer_report["history"])
        command(directories[observer], observer, docker.owner, read_command, writer_report["history"])
        phases[phase] = {writer: writer_report, observer: read_phase(observer, phase)}
        validate_transition(phases[previous], phases[phase], phase, phases["ready"])
        docker.receipt["observed_remove_after_reopen"] = {"status": "IN_PROGRESS", "phase": phase,
            "completed_native_named_pass": 0, "signed_changes": len(writer_report["history"]["changes_sha256"])}
        docker.checkpoint()
    for role in METHODS:
        command(directories[role], role, docker.owner, "stop", phases["readded"][role]["history"])
    results, database_ids = {}, {}
    for role, resource in resources.items():
        require(docker.command(["container", "wait", resource["id"]], "wait-observed-remove-" + role, docker.remaining(deadline, 90)) == "0",
                "Native observed-remove process failed")
        info = docker.find(resource, deadline)
        require(info["State"].get("Running") is False and info["State"].get("ExitCode") == 0, "Native observed-remove process did not close normally")
        log_path = directories[role] / LOG
        docker.command(["container", "logs", resource["id"]], "read-observed-remove-" + role, docker.remaining(deadline), log_path)
        final_path = directories[role] / "observed-final.json"
        require(final_path.is_file() and not final_path.is_symlink(), "Missing exact final native receipt")
        final = json.loads(final_path.read_text())
        validate_final(final, phases["readded"][role], file_hashes[(role, "added")], file_hashes[(role, "removed")], log_path.read_text(), role)
        directory = directories[role]
        root = directory / "account-root"
        require((root.stat().st_dev, root.stat().st_ino) == directory_ids[role]
                and digest(directory / "state.json") == state_hash and digest(directory / "account-key.private") == key_hash
                and digest(directory / "reopened.json") == baseline_hashes[role], "Original store/recovery/baseline identity changed")
        for phase in ["ready", "added", "removed", "readded"]:
            require(digest(directory / ("observed-" + phase + ".json")) == file_hashes[(role, phase)], "Native observation changed after validation")
        databases = list(root.rglob("*.db"))
        require(databases and all(p.is_file() and not p.is_symlink() for p in databases), "Actual original-store databases missing")
        database_ids[role] = {(p.stat().st_dev, p.stat().st_ino) for p in databases}
        results[role] = {**live[role], "peer_id": final["peer_id"], "receipt_sha256": digest(final_path),
                         "native_named_pass": 1, "account_stop_verified": True, "post_stop_rpc": final["post_stop_rpc"]}
    require(not database_ids["creator"].intersection(database_ids["recovered"]), "Native pair shares a database inode")
    require(set(docker.find(network_resource, deadline).get("Containers", {})) <= {r["id"] for r in resources.values()},
            "Foreign peer used the causal LAN")
    return {"protocol": PROTOCOL, "status": PASS, "phase": "COMPLETE", "results": results,
            "actual_counts": {"native_processes": 2, "native_named_pass": 2, "native_fail": 0, "native_skip": 0,
                              "new_signed_operations": 3, "signed_changes_before": 8, "signed_changes_after": 11},
            "history": phases["readded"]["creator"]["history"],
            "operation_ids": [f"{number:032x}" for number in [8, 9, 10]],
            "actual_remove_request_sha256": phases["removed"]["recovered"]["mutation"]["request_sha256"],
            "independent_native_encoding": "BYTE_IDENTICAL_AT_THREE_GENERATED_ENTRIES",
            "same_native_author_verified_against_original_claim": True, "distinct_original_peer_ids_and_databases": True,
            "original_offline_and_reopen_receipts_unchanged": True,
            "transport_scope": "NATIVE_OWNED_LAN_CAUSAL_OBSERVATION_BARRIERS_NO_HISTORY_INJECTION",
            "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN", "two_ios_apps": "NOT_RUN",
            "full_t2_acceptance": "NOT_RUN", "app_capability": "OFF"}
