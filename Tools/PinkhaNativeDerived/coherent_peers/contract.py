"""Bounded evidence contract for one new coherent native peer journey."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL = "pinkha-coherent-authorized-read-peers-v1"
METHOD = "TestCoherentAuthorizedReadNativePeer"
PASS = "PASS_COHERENT_AUTHORIZED_READ_NATIVE_PEERS_OFFLINE_REOPEN"
BUILD = "BUILT_COHERENT_NATIVE_PEER_FIXTURE_NOT_EXECUTED"
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
PATCH = "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
INVENTORY = "05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0"
VERSION = "v0.51.7-nightly.20261014.1-" + "-".join(part + PATCH for part in (
    "pinkha-native-derived-v1-", "pinkha-native-t5-lookup-v1-", "pinkha-torah-attachment-v1-",
    "pinkha-current-read-v1-", "pinkha-authorized-read-v1-"))
NATIVE_RUN = "45026227924"
PROOF = "docs/validation/20261122-coherent-heart-native-pass/original"
LIMITS = dict(network_acl_transport="NOT_RUN", mixed_versions="NOT_RUN", offline_unknown_revocation="NOT_PROVEN",
              full_t2_acceptance="NOT_RUN", ios_acceptance="NOT_RUN", app_capability="OFF")
STATE_KEYS = {"AccountID", "SpaceID", "DocumentID", "BlockID", "RootID", "OperationID", "OperationSHA256",
              "ClaimID", "ChangeID", "RawChanges", "Heads"}
PUBLISHED = {"creator": {"ready.json", "ready.pb", "final.json", "stopped.pb", "native.log", "cancel.json"},
             "recovered": {"ready.json", "ready.pb", "offline.json", "offline.pb", "final.json", "stopped.pb", "native.log", "cancel.json",
                           "reopen.json", "reopen.pb", "reopen-final.json", "reopen-stopped.pb", "reopen-native.log"}}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while part := stream.read(1024**2):
            value.update(part)
    return value.hexdigest()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def is_hash(value, length=64):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(length) + "}", value) is not None


def load(path, maximum=4 * 1024**2):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= maximum, "Missing/unsafe bounded evidence")
    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, "Duplicate original JSON key")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError("Non-finite original JSON number: " + value)
    value = json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=reject_constant)
    require(isinstance(value, dict), "Expected original object")
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def validate_build(build, app_sha, run_id, attempt):
    required = dict(status=BUILD, app_sha=app_sha, run_id=run_id, run_attempt=attempt, heart_sha=HEART,
                    patch_sha256=PATCH, inventory_sha256=INVENTORY, native_source_run=NATIVE_RUN,
                    native_source_count=139, old_test_methods_executed=0, protobuf_generation_executed=0)
    require(all(build.get(key) == value and type(build.get(key)) is type(value) for key, value in required.items()),
            "Peer executable lacks exact coherent source/run identity")
    require(is_hash(build.get("fixture_sha256")) and is_hash(build.get("binary_sha256"))
            and build.get("binary_path") == "client-runtime/native.test" and isinstance(build.get("runtime_version"), str),
            "Missing fixture/runtime binding")
    require(build["runtime_version"] == VERSION,
            "Another runtime profile cannot be a coherent peer")


def validate_state(state):
    require(isinstance(state, dict) and set(state) == STATE_KEYS, "Seed contains unreviewed fields")
    require(all(isinstance(value, str) and value for key, value in state.items() if key not in {"RawChanges", "Heads"}),
            "Missing public native identity")
    require(is_hash(state["OperationSHA256"]) and is_hash(state["OperationID"], 32), "Invalid operation identity")
    require(isinstance(state["RawChanges"], dict) and set(state["RawChanges"]) == {state["RootID"], state["ChangeID"]}
            and all(is_hash(value) for value in state["RawChanges"].values()) and state["Heads"] == [state["ChangeID"]],
            "Only original signed hashes may cross the seed boundary")


def fields(raw):
    require(isinstance(raw, bytes) and len(raw) <= 4 * 1024**2, "Unbounded original wire")
    at, result = 0, []
    def number():
        nonlocal at
        value = 0
        for shift in range(0, 70, 7):
            require(at < len(raw), "Truncated original varint")
            byte = raw[at]; at += 1
            require(shift < 63 or byte <= 1, "Overflowing original varint")
            value |= (byte & 127) << shift
            if byte < 128:
                require(shift == 0 or byte != 0, "Overlong original varint")
                return value
        raise ValueError("Oversized original varint")
    while at < len(raw):
        key = number(); field, kind = key >> 3, key & 7
        require(field > 0 and kind in (0, 2), "Unexpected original wire kind")
        if kind == 0:
            value = number()
        else:
            size = number()
            require(size <= len(raw) - at, "Truncated original field")
            value = raw[at:at + size]; at += size
        result.append((field, kind, value))
        require(len(result) <= 128, "Unbounded original wire fields")
    return result


def one(values, number, kind, default=None):
    matches = [(wire, value) for field, wire, value in values if field == number]
    require(len(matches) <= 1 and (not matches or matches[0][0] == kind), "Duplicate/mistyped singleton field")
    return matches[0][1] if matches else default


def validate_positive_wire(raw, state):
    outer = fields(raw)
    require({field for field, _, _ in outer} == {1, 2, 3} and one(outer, 2, 0) == 1, "Incomplete positive response")
    error = fields(one(outer, 1, 2))
    require({field for field, _, _ in error} <= {1, 2}
            and one(error, 1, 0, 0) == 0 and one(error, 2, 2, b"") == b"", "Positive wire is an error")
    snapshot = fields(one(outer, 3, 2))
    require({field for field, _, _ in snapshot} == set(range(1, 9))
            and one(snapshot, 1, 2) == b"pinkha-authorized-operation-read-v1"
            and one(snapshot, 2, 2) == state["AccountID"].encode() and one(snapshot, 3, 2) == state["SpaceID"].encode()
            and one(snapshot, 4, 2) == state["OperationID"].encode() and one(snapshot, 5, 0) == 1
            and one(snapshot, 6, 0) == 1 and re.fullmatch(b"[0-9a-f]{64}", one(snapshot, 7, 2, b"")),
            "Wrong authorized snapshot identity/completeness")
    variant_raw = one(snapshot, 8, 2)
    variant = fields(variant_raw)
    require({field for field, _, _ in variant} == set(range(1, 9))
            and one(variant, 1, 2) == state["ClaimID"].encode() and one(variant, 2, 2) == state["OperationID"].encode()
            and one(variant, 3, 2) == state["SpaceID"].encode() and one(variant, 4, 2) == state["AccountID"].encode()
            and sha(one(variant, 6, 2, b"")) == state["OperationSHA256"] and one(variant, 8, 0) == 2,
            "Original signed variant identity or bytes differ")
    target, provenance = fields(one(variant, 5, 2)), fields(one(variant, 7, 2))
    require({field for field, _, _ in target} == {1, 2} and {field for field, _, _ in provenance} == {1, 2, 3}
            and one(target, 1, 2) == state["DocumentID"].encode() and one(target, 2, 2) == state["BlockID"].encode()
            and one(provenance, 1, 2) == state["AccountID"].encode()
            and one(provenance, 2, 2) == state["ChangeID"].encode() and one(provenance, 3, 2),
            "Native target/provenance changed")
    return sha(variant_raw)


def validate_report(value, phase, role, nonce, build, state, state_hash, raw):
    expected = dict(protocol=PROTOCOL, phase=phase, role=role, nonce=nonce, pid=1, source_sha=build["app_sha"],
                    heart_sha=HEART, runtime_version=build["runtime_version"], fixture_sha256=build["fixture_sha256"],
                    state_sha256=state_hash, account_id=state["AccountID"], space_id=state["SpaceID"],
                    object_id=state["DocumentID"], block_id=state["BlockID"], operation_id=state["OperationID"],
                    claim_id=state["ClaimID"], change_id=state["ChangeID"], canonical_sha256=state["OperationSHA256"],
                    raw_changes_sha256=state["RawChanges"], heads=state["Heads"], read_target_count=0,
                    first_private_read="PinkhaTorahAuthorizedOperationRead", active_append_count=1 if role == "creator" else 0,
                    wire_sha256=sha(raw), variant_sha256=validate_positive_wire(raw, state), **LIMITS)
    require(all(value.get(key) == item and type(value.get(key)) is type(item) for key, item in expected.items()),
            "Native peer evidence identity/authority/scope differs")
    require(isinstance(value.get("peer_id"), str) and value["peer_id"]
            and re.fullmatch(r"net:\[[0-9]+\]", value.get("network_namespace", "")), "Missing actual peer/process namespace")
    addresses = value.get("actual_ipv4")
    require(addresses == [] if phase in {"offline", "reopen", "reopen-final"} or (phase == "final" and role == "recovered")
            else isinstance(addresses, list) and len(addresses) == 1, "Wrong actual connected/disconnected phase")
    calls = value.get("rpc_calls", {})
    require(isinstance(calls, dict) and all(type(count) is int and count > 0 for count in calls.values())
            and calls.get("PinkhaTorahOperationsReadTarget", 0) == 0
            and calls.get("PinkhaTorahOperationsAppend", 0) == expected["active_append_count"]
            and calls.get("PinkhaTorahAuthorizedOperationRead", 0) >= 1,
            "Unexpected private replay/read priming")
    if phase == "reopen":
        require(calls["PinkhaTorahAuthorizedOperationRead"] == 1, "Offline cold read retried or repaired by another read")
    return value


def validate_pair(creator, recovered):
    require(creator["peer_id"] != recovered["peer_id"] and creator["network_namespace"] != recovered["network_namespace"]
            and creator["actual_ipv4"] != recovered["actual_ipv4"], "Clients reused device or network identity")
    require(all(creator[key] == recovered[key] for key in ("variant_sha256", "raw_changes_sha256", "heads", "state_sha256")),
            "Actual peer did not receive the same original signed variant")


def validate_final(value, raw, log, initial, *, reopened=False):
    require(value.get("account_stop_verified") is True and value.get("test_passed") is True
            and value.get("stopped_error_code") == 5 and value.get("stopped_payload") is False
            and value.get("stopped_wire_sha256") == sha(raw), "Missing actual account stop/zero-payload denial")
    outer = fields(raw)
    require(len(outer) == 2 and {field for field, _, _ in outer} == {1, 2} and one(outer, 2, 0) == 1
            and one(fields(one(outer, 1, 2)), 1, 0) == 5, "Stopped native read exposed payload or another error")
    require(all(value.get(key) == initial[key] for key in ("peer_id", "network_namespace", "variant_sha256", "raw_changes_sha256", "heads", "state_sha256")),
            "Original data/process changed before clean shutdown")
    calls = value["rpc_calls"]
    require(calls.get("AccountStop") == calls.get("AppShutdown") == 1
            and value.get("returned_byte_calls") == calls, "Original native calls did not all return exactly once")
    if reopened:
        require(calls["PinkhaTorahAuthorizedOperationRead"] == 2, "Cold read plus stopped denial are the only reopened reads")
    starts = re.findall(r"^=== RUN\s+(\S+)\s*$", log, re.M)
    terminals = re.findall(r"^--- (PASS|FAIL|SKIP): (\S+) \(", log, re.M)
    require(starts == [METHOD] and terminals == [("PASS", METHOD)] and "PASS" in log.splitlines(),
            "Missing, extra, failed or skipped new native method")


def export(private, evidence):
    needle_path = private / "creator/sensitive-needles.private"
    if not needle_path.is_file() or needle_path.is_symlink():
        return dict(status="WITHHELD_NO_COMPLETE_SYNTHETIC_SECRET_INVENTORY", files={})
    require(not needle_path.parent.is_symlink() and needle_path.stat().st_size <= 64 * 1024, "Unsafe secret inventory")
    needles = json.loads(needle_path.read_bytes())
    require(isinstance(needles, list) and len(needles) == 2 and all(isinstance(value, str) and value for value in needles),
            "Incomplete native synthetic secret inventory")
    needles = [value.encode() for value in needles]
    candidates = []
    for role, names in PUBLISHED.items():
        require((private / role).is_dir() and not (private / role).is_symlink(), "Unsafe original evidence directory")
        for name in sorted(names):
            path = private / role / name
            if not path.exists():
                continue
            require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2, "Unsafe native export")
            raw = path.read_bytes()
            require(not any(needle in raw for needle in needles), "Native evidence contains disposable credentials")
            candidates.append((role + "/" + name, raw))
    require(not evidence.exists(), "Fresh screened export directory required")
    evidence.mkdir(parents=True)
    files = {}
    for name, raw in candidates:
        target = evidence / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(raw)
        files[name] = sha(raw)
    return dict(status="PASS_EXACT_SYNTHETIC_SECRET_SCAN", files=files)
