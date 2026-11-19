"""Default-off native concurrent REPLACE tail; no account/history injection.

The caller retains ownership of Docker, source binding, cancellation, credential
scanning, artifact publication and cleanup. This module adds only two exact
native methods and validation of their original observations.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time

import run_account_lifecycle as base

PROTOCOL = "pinkha-t2-native-concurrent-replace-v1"
ROLES = ("creator", "recovered")
METHODS = {"creator": "TestT2NativeClientConcurrentReplaceCreatorPhase",
           "recovered": "TestT2NativeClientConcurrentReplaceRecoveredPhase"}
PHASES = ("ready", "partitioned", "diverged", "merged", "final")
FILES = {"replace-" + phase + ".json" for phase in PHASES}
LOG = "concurrent-replace-native.log"
PASS = "PASS_NATIVE_CONCURRENT_REPLACE_BOTH_SUCCESSORS_AND_RETAINED_PROVENANCE"
ORDER = "BYTEWISE_OPERATION_ID_CLAIM_ID_FALLBACK_BOTH_SUCCESSORS_RETAINED"
COMMON_KEYS = {"protocol", "phase", "role", "nonce", "pid", "network_namespace", "actual_ipv4", "native_network_mode",
               "native_network_state", "native_server_port", "peer_id", "account_author_id", "heart_sha", "runtime_version",
               "client_fixture_sha256", "rpc_manifest_sha256", "registration_patch_sha256", "state_sha256",
               "clean_reopen_receipt_sha256", "original_operation_sha256", "original_claim_id", "history", "read_response_sha256",
               "snapshot_sha256_without_local_sequence", "local_applied_sequence", "live_claim_ids", "live_claims", "conflict_operation_id",
               "conflict_claim_ids", "predecessor", "predecessor_observation_sha256", "successors", "materialized_order",
               "rfc_causal_operation_id_display_order", "app_capability", "process_crash", "power_loss",
               "disconnected_reopen_after_tail", "two_ios_apps", "full_t2_acceptance", "test_passed"}
EXTRA_KEYS = {"ready": set(), "partitioned": set(), "diverged": {"mutation"}, "merged": {"mutation", "retries"},
              "final": {"mutation", "retries", "ready_receipt_sha256", "partitioned_receipt_sha256", "diverged_receipt_sha256",
                        "merged_receipt_sha256", "rpc_calls", "returned_byte_calls", "closed", "account_stop_verified", "post_stop_rpc"}}
CLAIM_KEYS = {"operation_id", "claim_id", "digest", "author_id", "kind", "target_sha256", "source_sha256", "payload_sha256",
              "observed_claim_ids", "claim_response_sha256"}
MUTATION_KEYS = {"operation_id", "claim_id", "disposition", "change_id", "request_sha256", "request_bytes", "returned_claim_sha256"}
RETRY_KEYS = MUTATION_KEYS | {"before_response_sha256", "after_response_sha256", "before_local_sequence", "after_local_sequence",
                            "history_before", "history_after"}
require, digest, write = base.require, base.digest, base.write_json


def validate_selection(scenario: str, crash: bool, observed: bool, replace: bool) -> None:
    require(scenario in {"bootstrap", "offline"} and all(type(flag) is bool for flag in (crash, observed, replace)),
            "Unknown native tail selection")
    require(sum((crash, observed, replace)) <= 1, "Native crash, observed-remove and concurrent-replace tails are mutually exclusive")
    require(not (crash or observed or replace) or scenario == "offline", "A tail requires the unchanged offline and clean-reopen baseline")


def sha(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def claim_id(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}/[0-9a-f]{64}", value) is not None


def validate_history(value: dict, count: int, heads_count: int) -> None:
    require(isinstance(value, dict) and set(value) == {"changes_sha256", "parents", "heads"}, "Only signed identities/hashes are allowed")
    changes, parents, heads = value["changes_sha256"], value["parents"], value["heads"]
    require(type(count) is int and count in {8, 9, 10} and type(heads_count) is int and heads_count in {1, 2}
            and isinstance(changes, dict) and len(changes) == count
            and all(isinstance(key, str) and 0 < len(key) <= 512 and "\x00" not in key for key in changes)
            and all(sha(item) for item in changes.values()), "Wrong signed history cardinality or identity")
    require(isinstance(parents, dict) and len(parents) == count - 1 and set(parents) < set(changes)
            and all(isinstance(items, list) and 1 <= len(items) <= 2 and items == sorted(set(items))
                    and all(item in changes and item != key for item in items) for key, items in parents.items()),
            "Invalid native parent graph")
    root = next(iter(set(changes) - set(parents)))
    for start in changes:
        visiting, done = set(), set()
        def visit(node):
            require(node not in visiting, "Cyclic native signed parent graph")
            if node in done:
                return
            visiting.add(node)
            for parent in parents.get(node, []):
                visit(parent)
            visiting.remove(node)
            done.add(node)
        visit(start)
        require(root in done, "Disconnected native signed history")
    wanted = sorted(set(changes) - {parent for items in parents.values() for parent in items})
    require(isinstance(heads, list) and heads == wanted and len(heads) == heads_count, "Wrong actual native heads")


def branch(before: dict, after: dict) -> str:
    validate_history(before, 8, 2)
    validate_history(after, 9, 1)
    require(all(after["changes_sha256"].get(key) == value for key, value in before["changes_sha256"].items())
            and all(after["parents"].get(key) == value for key, value in before["parents"].items()),
            "Original signed bytes/parents changed")
    extra = set(after["changes_sha256"]) - set(before["changes_sha256"])
    require(len(extra) == 1, "A branch must append exactly one real replacement")
    change = extra.pop()
    require(after["heads"] == [change] and after["parents"][change] == before["heads"],
            "Concurrent replacement did not observe both original heads")
    return change


def merge_histories(before: dict, branches: dict) -> dict:
    require(set(branches) == set(ROLES), "Both native branches are required")
    changes = {role: branch(before, history) for role, history in branches.items()}
    require(changes["creator"] != changes["recovered"], "Replacement branches alias")
    result = copy.deepcopy(before)
    for role, history in branches.items():
        change = changes[role]
        result["changes_sha256"][change] = history["changes_sha256"][change]
        result["parents"][change] = list(history["parents"][change])
    result["heads"] = sorted(changes.values())
    validate_history(result, 10, 2)
    return result


def validate_claim(value: dict, operation: int, author: str, predecessor: dict | None = None, role: str | None = None) -> None:
    require(isinstance(value, dict) and set(value) == CLAIM_KEYS and value["operation_id"] == f"{operation:032x}"
            and claim_id(value["claim_id"]) and value["digest"] == value["claim_id"].split("/")[1]
            and value["author_id"] == author and all(sha(value[key]) for key in
                ["digest", "target_sha256", "source_sha256", "payload_sha256", "claim_response_sha256"]),
            "Incomplete or altered native claim provenance")
    if predecessor is None:
        baseline_role = {2: "creator", 3: "recovered"}.get(operation)
        require(baseline_role is not None and value["kind"] == "ADD" and value["observed_claim_ids"] == []
                and value["payload_sha256"] == hashlib.sha256(("t2-offline-unique-" + baseline_role).encode()).hexdigest(),
                "Actual claim is not the expected native baseline ADD2/ADD3")
    else:
        require(role in ROLES and operation == (8 if role == "creator" else 9) and value["kind"] == "REPLACE"
                and value["observed_claim_ids"] == [predecessor["claim_id"]]
                and value["claim_id"] != predecessor["claim_id"]
                and value["source_sha256"] == predecessor["source_sha256"]
                and value["target_sha256"] == predecessor["target_sha256"]
                and value["payload_sha256"] == hashlib.sha256(("t2-concurrent-replace-" + role).encode()).hexdigest(),
                "Successor did not retain its exact locally observed predecessor/source/target")


def validate_live_order(report: dict, count: int, successor_roles: set) -> None:
    values, ids = report["live_claims"], report["live_claim_ids"]
    numbers = {2, 3} if count == 8 else {3} | {8 if role == "creator" else 9 for role in successor_roles}
    expected = {f"{number:032x}": number for number in numbers}
    require(isinstance(values, list) and len(values) == len(expected) and isinstance(ids, list) and len(ids) == len(values),
            "Complete actual ordered live-claim provenance is required")
    seen, order = set(), []
    for value in values:
        require(isinstance(value, dict) and value.get("operation_id") in expected,
                "Unexpected operation in native live order")
        number = expected[value["operation_id"]]
        if number in {2, 3}:
            validate_claim(value, number, report["account_author_id"])
            require(value["source_sha256"] == report["predecessor"]["source_sha256"]
                    and value["target_sha256"] == report["predecessor"]["target_sha256"],
                    "Unrelated baseline live claim changed source/target")
            if number == 2:
                require(value == report["predecessor"], "Live predecessor differs from its actual native observation")
        else:
            writer = "creator" if number == 8 else "recovered"
            require(value == report["successors"][writer], "Live successor differs from its canonical native provenance")
        require(value["operation_id"] not in seen, "Duplicate live operation")
        seen.add(value["operation_id"])
        order.append((value["operation_id"], value["claim_id"]))
    require(seen == set(expected) and ids == [value["claim_id"] for value in values] and len(set(ids)) == len(ids),
            "Live IDs do not match the complete ordered native claims")
    require(all(left < right for left, right in zip(order, order[1:])),
            "Actual native live order is not bytewise OperationID then ClaimID; input must not be repaired")


def validate_common(report: dict, phase: str, role: str, baseline: dict, baseline_sha: str,
                    identity: dict, state: dict, info: dict, network: dict) -> None:
    require(phase in EXTRA_KEYS and role in ROLES and isinstance(report, dict) and set(report) == COMMON_KEYS | EXTRA_KEYS[phase],
            "Unexpected native replacement receipt fields")
    require(report["protocol"] == PROTOCOL and report["phase"] == phase and report["role"] == role
            and report["nonce"] == baseline["nonce"] and type(report["pid"]) is int and report["pid"] == 1,
            "Foreign replacement process/phase")
    detached = role == "recovered" and phase in {"partitioned", "diverged"}
    networks = info["NetworkSettings"]["Networks"]
    if detached:
        require(networks == {}, "Recovered native peer is not actually detached")
        wanted_ips = []
    else:
        require(set(networks) == {network["Name"]} and networks[network["Name"]]["NetworkID"] == network["Id"],
                "Unexpected native LAN attachment")
        wanted_ips = [networks[network["Name"]]["IPAddress"]]
        require(bool(wanted_ips[0]), "Missing actual owned native interface")
    require(info["State"].get("Running") is True and type(info["State"].get("Pid")) is int and info["State"]["Pid"] > 0
            and report["network_namespace"] == os.readlink(f"/proc/{info['State']['Pid']}/ns/net")
            and report["actual_ipv4"] == wanted_ips and report["native_network_state"] == ("NOT_CONNECTED" if detached else "WIFI")
            and report["native_network_mode"] == "NATIVE_LOCAL_ONLY_LAN_ORIGINAL_STORES",
            "Native observation differs from its real process/namespace/network")
    require(type(report["native_server_port"]) is int and 0 < report["native_server_port"] < 65536
            and report["peer_id"] == baseline["peer_id"] and report["client_fixture_sha256"] == baseline["client_fixture_sha256"]
            and report["state_sha256"] == baseline["state_sha256"] and report["clean_reopen_receipt_sha256"] == baseline_sha,
            "Original device/store/source identity changed")
    require(isinstance(report["account_author_id"], str) and 0 < len(report["account_author_id"]) <= 512
            and report["original_operation_sha256"] == state["OperationSHA256"] and report["original_claim_id"] == state["ClaimID"]
            and all(report[key] == identity[key] for key in ["heart_sha", "runtime_version", "rpc_manifest_sha256", "registration_patch_sha256"]),
            "Native account-author or pinned source binding missing")
    require(all(report[key] == "NOT_RUN" for key in ["process_crash", "power_loss", "disconnected_reopen_after_tail", "two_ios_apps", "full_t2_acceptance"])
            and report["app_capability"] == "OFF" and report["test_passed"] is (phase == "final")
            and report["materialized_order"] == ORDER and report["rfc_causal_operation_id_display_order"] == "NOT_PROVEN",
            "Concurrent native proof overstates its acceptance")
    count, heads = (8, 2) if phase in {"ready", "partitioned"} else ((9, 1) if phase == "diverged" else (10, 2))
    validate_history(report["history"], count, heads)
    require(all(sha(report[key]) for key in ["read_response_sha256", "snapshot_sha256_without_local_sequence", "predecessor_observation_sha256"])
            and type(report["local_applied_sequence"]) is int and report["local_applied_sequence"] > 0,
            "Actual native response/projection/sequence missing")
    validate_claim(report["predecessor"], 2, report["account_author_id"])
    require(report["predecessor"]["claim_id"] != report["original_claim_id"], "Predecessor aliases the removed original")
    successor_roles = set() if phase in {"ready", "partitioned"} else ({role} if phase == "diverged" else set(ROLES))
    require(isinstance(report["successors"], dict) and set(report["successors"]) == successor_roles, "Missing or prematurely observed successor")
    for writer, value in report["successors"].items():
        validate_claim(value, 8 if writer == "creator" else 9, report["account_author_id"], report["predecessor"], writer)
    validate_live_order(report, count, successor_roles)
    conflicts = report["conflict_claim_ids"]
    require(isinstance(conflicts, list) and len(conflicts) == 2 and conflicts == sorted(set(conflicts))
            and all(claim_id(value) for value in conflicts), "Actual conflict variants are missing or duplicated")
    require(report["conflict_operation_id"] == f"{4:032x}" and report["original_claim_id"] not in report["live_claim_ids"]
            and not set(report["live_claim_ids"]).intersection(report["conflict_claim_ids"]), "A removed or conflicting claim became live")
    predecessor_id = report["predecessor"]["claim_id"]
    if count == 8:
        require(predecessor_id in report["live_claim_ids"] and report["predecessor_observation_sha256"] == report["read_response_sha256"]
                and report["history"] == baseline["history"]
                and report["snapshot_sha256_without_local_sequence"] == baseline["snapshot_sha256_without_local_sequence"],
                "Both peers must actually observe the original predecessor before their writes")
    else:
        require(predecessor_id not in report["live_claim_ids"] and all(value["claim_id"] in report["live_claim_ids"]
                for value in report["successors"].values()), "Predecessor was revived or a successor was lost")


def validate_pair(reports: dict) -> None:
    require(set(reports) == set(ROLES), "Two actual Native clients are required")
    a, b = reports["creator"], reports["recovered"]
    require(a["peer_id"] != b["peer_id"] and a["network_namespace"] != b["network_namespace"]
            and a["actual_ipv4"] != b["actual_ipv4"], "Original devices/namespaces/interfaces alias")
    for key in ["account_author_id", "predecessor", "history", "snapshot_sha256_without_local_sequence", "live_claim_ids", "live_claims",
                "conflict_claim_ids", "conflict_operation_id", "successors", "original_operation_sha256", "original_claim_id"]:
        require(a[key] == b[key], "Native peers did not return the same complete ordered projection/provenance")


def validate_mutation(value: dict, evidence: dict, change: str) -> None:
    require(isinstance(value, dict) and set(value) == MUTATION_KEYS
            and value["operation_id"] == evidence["operation_id"] and value["claim_id"] == evidence["claim_id"]
            and value["disposition"] == "CREATED" and value["change_id"] == change
            and sha(value["request_sha256"]) and type(value["request_bytes"]) is int and 0 < value["request_bytes"] <= 65536
            and value["returned_claim_sha256"] == evidence["claim_response_sha256"],
            "Missing actual generated REPLACE append identity/bytes/receipt")


def validate_diverged(reports: dict, partitioned: dict) -> dict:
    require(set(reports) == set(partitioned) == set(ROLES), "Both independent branches required")
    for role in ROLES:
        old, current = partitioned[role], reports[role]
        require(current["predecessor"] == old["predecessor"]
                and current["predecessor_observation_sha256"] == old["read_response_sha256"]
                and current["conflict_claim_ids"] == old["conflict_claim_ids"], "Native write was not based on its local pre-partition state")
        change = branch(old["history"], current["history"])
        evidence = current["successors"][role]
        validate_mutation(current["mutation"], evidence, change)
        require(set(current["live_claim_ids"]) == (set(old["live_claim_ids"]) - {old["predecessor"]["claim_id"]}) | {evidence["claim_id"]},
                "Replacement removed an unrelated claim or retained its predecessor")
        unrelated = [value for value in old["live_claims"] if value["claim_id"] != old["predecessor"]["claim_id"]]
        require(len(unrelated) == 1 and unrelated[0]["operation_id"] == f"{3:032x}"
                and current["live_claims"] == unrelated + [evidence]
                and current["live_claim_ids"] == [value["claim_id"] for value in unrelated + [evidence]],
                "Local replacement changed native live order or unrelated claim provenance")
    require(partitioned["creator"]["history"] == partitioned["recovered"]["history"], "Branches did not start from the same actual predecessor history")
    return merge_histories(partitioned["creator"]["history"], {role: reports[role]["history"] for role in ROLES})


def validate_retry(value: dict, evidence: dict, report: dict, input_proof: dict) -> None:
    require(isinstance(value, dict) and set(value) == RETRY_KEYS and value["operation_id"] == evidence["operation_id"]
            and value["claim_id"] == evidence["claim_id"] and value["disposition"] == "ALREADY_EXISTS_SAME_PAYLOAD"
            and value["change_id"] == "" and value["returned_claim_sha256"] == evidence["claim_response_sha256"]
            and sha(input_proof.get("request_sha256")) and type(input_proof.get("request_bytes")) is int
            and 0 < input_proof["request_bytes"] <= 65536
            and value["request_sha256"] == input_proof["request_sha256"] and type(value["request_bytes"]) is int
            and value["request_bytes"] == input_proof["request_bytes"],
            "Retry was not the exact actual byte input or lost retained claim provenance")
    require(value["before_response_sha256"] == value["after_response_sha256"] == report["read_response_sha256"]
            and value["before_local_sequence"] == value["after_local_sequence"] == report["local_applied_sequence"]
            and type(value["before_local_sequence"]) is int and type(value["after_local_sequence"]) is int
            and value["history_before"] == value["history_after"] == report["history"],
            "Idempotent retry changed native response, local sequence, signed bytes or heads")


def validate_merged(reports: dict, diverged: dict, partitioned: dict, expected: dict, predecessor_input: dict) -> None:
    validate_pair(reports)
    require(expected == validate_diverged(diverged, partitioned), "Merge expectation was not the two actual native branches")
    require(predecessor_input.get("claim_id") == partitioned["creator"]["predecessor"]["claim_id"],
            "Original baseline byte entry is not the chosen predecessor")
    for role, report in reports.items():
        require(report["history"] == expected and report["predecessor"] == partitioned[role]["predecessor"]
                and report["predecessor_observation_sha256"] == partitioned[role]["read_response_sha256"]
                and report["mutation"] == diverged[role]["mutation"]
                and report["conflict_claim_ids"] == partitioned[role]["conflict_claim_ids"], "Merge lost original or branch provenance")
        wanted = (set(partitioned[role]["live_claim_ids"]) - {report["predecessor"]["claim_id"]}) | {
            diverged[writer]["successors"][writer]["claim_id"] for writer in ROLES}
        unrelated = [value for value in partitioned[role]["live_claims"] if value["claim_id"] != report["predecessor"]["claim_id"]]
        expected_claims = unrelated + [diverged[writer]["successors"][writer] for writer in ROLES]
        require(len(unrelated) == 1 and unrelated[0]["operation_id"] == f"{3:032x}" and len(wanted) == 3
                and set(report["live_claim_ids"]) == wanted and report["live_claims"] == expected_claims
                and report["live_claim_ids"] == [value["claim_id"] for value in expected_claims],
                "Merged materialization lost a successor, exact OperationID order or native provenance")
        require(isinstance(report["retries"], dict) and set(report["retries"]) == {*ROLES, "predecessor"}, "Exact successor and predecessor retries missing")
        for writer in ROLES:
            require(report["successors"][writer] == diverged[writer]["successors"][writer], "Concurrent successor content/provenance changed")
            validate_retry(report["retries"][writer], report["successors"][writer], report, diverged[writer]["mutation"])
        validate_retry(report["retries"]["predecessor"], report["predecessor"], report, predecessor_input)


def validate_final(final: dict, merged: dict, phase_hashes: dict, log: str, role: str) -> None:
    require(isinstance(final, dict) and set(final) == COMMON_KEYS | EXTRA_KEYS["final"], "Unexpected final replacement receipt")
    require(all(final[key] == value for key, value in merged.items() if key not in {"phase", "test_passed"})
            and final["phase"] == "final" and final["test_passed"] is True and final["closed"] is True
            and final["account_stop_verified"] is True and final["post_stop_rpc"] == "READ_AND_APPEND_NOT_LOGGED_IN"
            and all(sha(phase_hashes.get(phase)) and final[phase + "_receipt_sha256"] == phase_hashes[phase]
                    for phase in PHASES[:-1]), "Final receipt lost native observations, closure or post-stop denial")
    expected = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen", "AccountStop", "AppShutdown"]}
    expected["DeviceNetworkStateSet"] = 3 if role == "recovered" else 1
    expected["PinkhaTorahOperationsAppend"] = 5  # one create, three retries, one denied post-stop call
    calls = final["rpc_calls"]
    require(isinstance(calls, dict) and set(calls) == set(expected) | {"PinkhaTorahOperationsReadTarget"}
            and all(type(calls[key]) is int and calls[key] == value for key, value in expected.items())
            and type(calls["PinkhaTorahOperationsReadTarget"]) is int and 11 <= calls["PinkhaTorahOperationsReadTarget"] <= 2000
            and calls == final["returned_byte_calls"], "Unexpected account creation/mutation or unjoined byte response")
    passed = re.findall(r"^\s*--- PASS: (\S+) \(", log, re.M)
    require(passed == [METHODS[role]] and "--- FAIL:" not in log and "--- SKIP:" not in log,
            "Exactly one actual selected native PASS required per client")


def command(directory: Path, role: str, owner: str, phase: str, history: dict) -> None:
    require(role in ROLES and isinstance(owner, str) and bool(owner) and phase in {"partition", "write", "reconnect", "stop"},
            "Unknown fixed replacement command")
    validate_history(history, 8 if phase in {"partition", "write"} else 10, 2)
    path = directory / ("replace-" + phase + ".command.json")
    require(not path.exists() and not path.is_symlink(), "A native phase command cannot be replaced")
    write(path, {"protocol": PROTOCOL, "nonce": owner, "role": role, "phase": phase, "expected_history": history})


def process_identity(info: dict) -> dict:
    return copy.deepcopy({key: info[key] for key in ["Id", "Image", "Path", "Args", "Config", "HostConfig", "Mounts"]})


def sequence(api, docker, directories: dict, binary: Path, fixture_sha: str, identity: dict, image_id: str,
             state: dict, state_hash: str, key_hash: str, reopen: dict, network_resource: dict, network: dict) -> dict:
    """Called only after exact shared method/env/source hooks are reviewed."""
    validate_selection(docker.scenario, docker.crash_after_commit, docker.observed_remove_after_reopen,
                       docker.concurrent_replace_after_reopen)
    require(docker.concurrent_replace_after_reopen and set(directories) == set(ROLES), "Replacement tail was not explicitly selected")
    deadline = time.monotonic() + 600
    require(reopen.get("status") == "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK"
            and set(reopen.get("results", {})) == set(ROLES), "Exact original-store clean reopen must precede this tail")
    # Original append-byte proof was already produced by the unchanged offline
    # phase. Only its hashes/length/claim identity are used, never its request.
    predecessor_input = copy.deepcopy(docker.receipt["offline_convergence"]["lost_client_reply"]["clients"]["creator"])
    predecessor_proof_hash = hashlib.sha256(json.dumps(predecessor_input, sort_keys=True).encode()).hexdigest()
    baselines, baseline_hashes, store_ids = {}, {}, {}
    for role, directory in directories.items():
        reserved = FILES | {LOG} | {"replace-" + phase + ".command.json" for phase in ("partition", "write", "reconnect", "stop")}
        require(all(not (directory / name).exists() and not (directory / name).is_symlink() for name in reserved),
                "Fresh replacement process receipts and commands are required")
        path = directory / "reopened.json"
        require(path.is_file() and not path.is_symlink() and digest(path) == reopen["results"][role]["receipt_sha256"], "Frozen clean-reopen receipt changed")
        baselines[role], baseline_hashes[role] = json.loads(path.read_text()), digest(path)
        require(baselines[role]["closed"] is True and baselines[role]["account_stop_verified"] is True
                and baselines[role]["test_passed"] is True and baselines[role]["post_stop_rpc"] == "READ_AND_APPEND_NOT_LOGGED_IN"
                and digest(directory / "state.json") == state_hash and digest(directory / "account-key.private") == key_hash,
                "Original account is not closed or its recovery identity changed")
        root = directory / "account-root"
        require(root.is_dir() and not root.is_symlink(), "Original native store is missing")
        store_ids[role] = (root.stat().st_dev, root.stat().st_ino)
        matches = [r for r in docker.resources if r.get("id") == reopen["results"][role]["container_id"]]
        require(len(matches) == 1 and matches[0]["role"] == role and matches[0]["private"] == str(directory), "Foreign previous native process")
        old = docker.find(matches[0], deadline)
        require(old and old["State"].get("Running") is False and old["State"].get("ExitCode") == 0, "Original store still has a live owner")
        docker.command(["container", "rm", matches[0]["id"]], "retire-reopen-for-replace-" + role, docker.remaining(deadline))
    require(len(set(store_ids.values())) == 2, "Original native stores alias")
    lan = docker.find(network_resource, deadline)
    require(lan and lan["Id"] == network["Id"] and lan["Internal"] is True and not lan.get("Containers"), "Foreign peer occupies the owned LAN")
    resources = {role: docker.start(role, network, directories[role], binary, fixture_sha, deadline, method=METHODS[role]) for role in ROLES}
    require(len({r["id"] for r in resources.values()}) == 2 and not {r["id"] for r in resources.values()}.intersection(
        item["container_id"] for item in reopen["results"].values()), "Two new native processes are required")
    frozen, live, phases, hashes = {}, {}, {}, {}
    def read_phase(role, phase):
        report = docker.wait_ready(resources[role], deadline, filename="replace-" + phase + ".json")
        info = docker.find(resources[role], deadline)
        if role not in frozen:
            api.validate_container(info, docker.owner, role, network, directories[role], binary, image_id,
                                   os.getuid(), os.getgid(), scenario="offline", method=METHODS[role])
            frozen[role] = process_identity(info)
        else:
            require(process_identity(info) == frozen[role], "Native executable/configuration/mount ownership changed")
        validate_common(report, phase, role, baselines[role], baseline_hashes[role], identity, state, info, network)
        process = {"container_id": info["Id"], "host_pid": info["State"]["Pid"], "namespace": report["network_namespace"],
                   "started_at": info["State"]["StartedAt"]}
        if role in live:
            require(live[role] == process, "A native process was replaced during partition/reconnect")
        else:
            live[role] = process
        hashes[(role, phase)] = digest(directories[role] / ("replace-" + phase + ".json"))
        return report
    phases["ready"] = {role: read_phase(role, "ready") for role in ROLES}
    validate_pair(phases["ready"])
    require(len({item["host_pid"] for item in live.values()}) == 2, "Distinct native process IDs required")
    expected_ids = {r["id"] for r in resources.values()}
    require(set(docker.find(network_resource, deadline).get("Containers", {})) == expected_ids, "Unexpected peer before partition")
    docker.command(["network", "disconnect", network["Id"], resources["recovered"]["id"]], "detach-replace-recovered", docker.remaining(deadline))
    detached = docker.find(resources["recovered"], deadline)
    require(detached["State"].get("Running") is True and detached["State"]["Pid"] == live["recovered"]["host_pid"]
            and detached["NetworkSettings"]["Networks"] == {} and set(docker.find(network_resource, deadline).get("Containers", {})) == {resources["creator"]["id"]},
            "Actual native network partition was not established")
    for role in ROLES:
        command(directories[role], role, docker.owner, "partition", phases["ready"][role]["history"])
    phases["partitioned"] = {role: read_phase(role, "partitioned") for role in ROLES}
    validate_pair(phases["partitioned"])
    for role in ROLES:
        require(phases["partitioned"][role]["predecessor"] == phases["ready"][role]["predecessor"]
                and phases["partitioned"][role]["live_claims"] == phases["ready"][role]["live_claims"],
                "Local predecessor or ordered native live provenance changed before a write")
        command(directories[role], role, docker.owner, "write", phases["partitioned"][role]["history"])
    phases["diverged"] = {role: read_phase(role, "diverged") for role in ROLES}
    expected = validate_diverged(phases["diverged"], phases["partitioned"])
    require(docker.find(resources["recovered"], deadline)["NetworkSettings"]["Networks"] == {}
            and set(docker.find(network_resource, deadline).get("Containers", {})) == {resources["creator"]["id"]},
            "Both native writes must finish under the actual partition")
    docker.receipt["concurrent_replace_after_reopen"] = {"status": "IN_PROGRESS", "phase": "DIVERGED",
        "completed_native_named_pass": 0, "signed_changes_per_branch": 9, "partition": "OBSERVED_NATIVE_NETWORK_DETACH"}
    docker.checkpoint()
    docker.command(["network", "connect", network["Id"], resources["recovered"]["id"]], "rejoin-replace-recovered", docker.remaining(deadline))
    require(set(docker.find(network_resource, deadline).get("Containers", {})) == expected_ids, "Actual owned native reconnect failed")
    for role in ROLES:
        info = docker.find(resources[role], deadline)
        require(process_identity(info) == frozen[role] and info["State"].get("Running") is True
                and info["State"]["Pid"] == live[role]["host_pid"], "Reconnect substituted the native process")
        api.validate_container(info, docker.owner, role, network, directories[role], binary, image_id,
                               os.getuid(), os.getgid(), scenario="offline", method=METHODS[role])
        command(directories[role], role, docker.owner, "reconnect", expected)
    phases["merged"] = {role: read_phase(role, "merged") for role in ROLES}
    validate_merged(phases["merged"], phases["diverged"], phases["partitioned"], expected, predecessor_input)
    for role in ROLES:
        command(directories[role], role, docker.owner, "stop", expected)
    results, database_ids = {}, {}
    for role, resource in resources.items():
        require(docker.command(["container", "wait", resource["id"]], "wait-replace-" + role, docker.remaining(deadline, 90)) == "0", "Native replacement process failed")
        info = docker.find(resource, deadline)
        require(info["State"].get("Running") is False and info["State"].get("ExitCode") == 0, "Native process did not close normally")
        log_path = directories[role] / LOG
        docker.command(["container", "logs", resource["id"]], "read-replace-" + role, docker.remaining(deadline), log_path)
        final_path = directories[role] / "replace-final.json"
        require(final_path.is_file() and not final_path.is_symlink(), "Missing exact native final receipt")
        final = json.loads(final_path.read_text())
        validate_final(final, phases["merged"][role], {phase: hashes[(role, phase)] for phase in PHASES[:-1]}, log_path.read_text(), role)
        directory, root = directories[role], directories[role] / "account-root"
        require((root.stat().st_dev, root.stat().st_ino) == store_ids[role]
                and digest(directory / "state.json") == state_hash and digest(directory / "account-key.private") == key_hash
                and digest(directory / "reopened.json") == baseline_hashes[role], "Original account/store/baseline identity changed")
        for phase in PHASES[:-1]:
            require(digest(directory / ("replace-" + phase + ".json")) == hashes[(role, phase)], "Native observation changed after validation")
        databases = list(root.rglob("*.db"))
        require(databases and all(p.is_file() and not p.is_symlink() for p in databases), "Actual native databases missing")
        database_ids[role] = {(p.stat().st_dev, p.stat().st_ino) for p in databases}
        results[role] = {**live[role], "peer_id": final["peer_id"], "receipt_sha256": digest(final_path), "native_named_pass": 1,
                         "account_stop_verified": True, "post_stop_rpc": final["post_stop_rpc"]}
    require(not database_ids["creator"].intersection(database_ids["recovered"]), "Native pair shares a database inode")
    require(hashlib.sha256(json.dumps(docker.receipt["offline_convergence"]["lost_client_reply"]["clients"]["creator"], sort_keys=True).encode()).hexdigest()
            == predecessor_proof_hash, "Original predecessor entry evidence changed")
    require(set(docker.find(network_resource, deadline).get("Containers", {})) <= expected_ids, "Foreign peer occupied the native tail LAN")
    return {"protocol": PROTOCOL, "status": PASS, "phase": "COMPLETE", "results": results,
            "actual_counts": {"native_processes": 2, "native_named_pass": 2, "native_fail": 0, "native_skip": 0,
                              "new_signed_operations": 2, "signed_changes_before": 8, "signed_changes_per_partitioned_branch": 9,
                              "signed_changes_after": 10, "successor_retry_entries": 4, "predecessor_retry_entries": 2},
            "history": expected, "operation_ids": [f"{number:032x}" for number in (8, 9)],
            "predecessor_claim_id": phases["ready"]["creator"]["predecessor"]["claim_id"],
            "successor_claims": phases["merged"]["creator"]["successors"],
            "actual_append_inputs": {role: {key: phases["diverged"][role]["mutation"][key] for key in ("request_sha256", "request_bytes")} for role in ROLES},
            "predecessor_original_entry_sha256": predecessor_input["request_sha256"],
            "independent_native_encoding": "EACH_SUCCESSOR_BYTE_IDENTICAL_AT_THREE_ENTRIES_PREDECESSOR_AT_BASELINE_PLUS_TWO",
            "materialized_order": ORDER, "rfc_causal_operation_id_display_order": "NOT_PROVEN",
            "distinct_original_peer_ids_and_databases": True, "original_offline_and_reopen_receipts_unchanged": True,
            "transport_scope": "ACTUAL_PARTITION_AND_NATIVE_RECONNECT_NO_HISTORY_INJECTION",
            "process_crash": "NOT_RUN", "power_loss": "NOT_RUN", "disconnected_reopen_after_tail": "NOT_RUN",
            "two_ios_apps": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "app_capability": "OFF"}
