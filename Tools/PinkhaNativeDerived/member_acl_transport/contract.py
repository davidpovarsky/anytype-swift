"""Evidence contract for independent member ACL transport and native publication."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Tools/PinkhaNativeDerived"))
from coherent_peers import contract as retained

require, digest, sha, is_hash, load, save = retained.require, retained.digest, retained.sha, retained.is_hash, retained.load, retained.save
fields, one, validate_state = retained.fields, retained.one, retained.validate_state
HEART, PATCH, INVENTORY, VERSION, NATIVE_RUN, PROOF, IMAGE = (
    retained.HEART, retained.PATCH, retained.INVENTORY, retained.VERSION, retained.NATIVE_RUN, retained.PROOF, retained.IMAGE)
PROTOCOL = "pinkha-independent-member-acl-transport-v1"
METHOD = "TestIndependentMemberACLTransport"
BUILD = "BUILT_INDEPENDENT_MEMBER_ACL_FIXTURE_NOT_EXECUTED"
PASS = "PASS_INDEPENDENT_MEMBER_NATIVE_ACL_TRANSPORT_AND_OBSERVED_REVOCATION_FENCE"
LIMITS = dict(network_acl_transport="NOT_RUN", coordinator_invite_acceptance="NOT_RUN",
              discovery_bootstrap="STATIC_OWNED_PEER_ROUTE", mixed_versions="NOT_RUN",
              offline_unknown_revocation="LAST_KNOWN_AUTHORITY_NOT_GLOBAL_FRESHNESS",
              full_t2_acceptance="NOT_RUN", ios_acceptance="NOT_RUN", app_capability="OFF")
PHASES = {"owner": ("identity", "grant", "reader", "revoke", "final"),
          "member": ("identity", "grant", "reader", "offline", "unknown-revocation", "publication-fence", "revoked", "final")}
WIRE_PHASES = {"grant", "reader", "offline", "unknown-revocation", "publication-fence", "revoked", "final"}
PUBLISHED = {role: {phase + ".json" for phase in phases} | {phase + ".pb" for phase in phases if phase in WIRE_PHASES}
                  | {"native.log"} for role, phases in PHASES.items()}


def validate_build(value, app_sha, run_id, attempt):
    expected = dict(status=BUILD, app_sha=app_sha, run_id=run_id, run_attempt=attempt, heart_sha=HEART,
                    patch_sha256=PATCH, inventory_sha256=INVENTORY, native_source_run=NATIVE_RUN,
                    native_source_count=139, runtime_version=VERSION, old_test_methods_executed=0,
                    protobuf_generation_executed=0, binary_path="client-runtime/native.test")
    require(all(value.get(k) == v and type(value.get(k)) is type(v) for k,v in expected.items()), "Wrong exact member fixture build")
    require(is_hash(value.get("fixture_sha256")) and is_hash(value.get("binary_sha256")), "Unbound native fixture binary")
    sources = value.get("fixture_source_sha256", {})
    require("member_acl_transport_test.go" in sources and "pinkha_member_acl_fixture.go" in sources,
            "Missing bound member/fence fixture source")
    require(all(is_hash(v) for v in sources.values()), "Malformed fixture source closure")


def validate_positive_wire(raw, state, reader):
    outer = fields(raw)
    require({field for field, _, _ in outer} == {1, 2, 3} and one(outer, 2, 0) == 1, "Incomplete positive response")
    error = fields(one(outer, 1, 2))
    require({field for field, _, _ in error} <= {1, 2}
            and one(error, 1, 0, 0) == 0 and one(error, 2, 2, b"") == b"", "Positive wire is an error")
    snapshot = fields(one(outer, 3, 2))
    require({field for field, _, _ in snapshot} == set(range(1, 9))
            and one(snapshot, 1, 2) == b"pinkha-authorized-operation-read-v1"
            and one(snapshot, 2, 2) == reader.encode() and one(snapshot, 3, 2) == state["SpaceID"].encode()
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


def validate_denial(raw, allowed):
    outer = fields(raw)
    require(len(outer) == 2 and {field for field, _, _ in outer} == {1,2} and one(outer, 2, 0) == 1,
            "Native denial contains snapshot or invalid protocol")
    code = one(fields(one(outer, 1, 2)), 1, 0)
    require(code in allowed, "Native denial has an unrelated error")
    return code


def validate_common(value, phase, role, nonce, build, identity):
    expected = dict(protocol=PROTOCOL, phase=phase, role=role, nonce=nonce, pid=1,
                    source_sha=build["app_sha"], heart_sha=HEART, runtime_version=VERSION,
                    fixture_sha256=build["fixture_sha256"], account_id=identity["account_id"],
                    peer_id=identity["peer_id"], network_namespace=identity["network_namespace"],
                    wallet_create_count=1, wallet_recover_count=0,
                    full_t2_acceptance="NOT_RUN", ios_acceptance="NOT_RUN", app_capability="OFF")
    require(all(value.get(k) == v and type(value.get(k)) is type(v) for k,v in expected.items()),
            "Wrong native identity, source or scope")
    require(re.fullmatch(r"net:\[[0-9]+\]", value["network_namespace"]), "Missing actual namespace")
    require(value["actual_ipv4"] == [] if phase in {"offline","unknown-revocation"} else
            isinstance(value["actual_ipv4"], list) and len(value["actual_ipv4"]) == 1,
            "Native network state disagrees with phase")
    calls = value.get("rpc_calls", {})
    require(isinstance(calls, dict) and all(type(v) is int and v > 0 for v in calls.values())
            and calls.get("WalletCreate") == 1 and calls.get("WalletRecover", 0) == 0
            and calls.get("PinkhaTorahOperationsReadTarget", 0) == 0,
            "Identity was recovered or private history was primed")
    if phase != "identity":
        require(calls.get("PinkhaTorahOperationsAppend", 0) == (1 if role == "owner" else 0),
                "Member injected private operations")


def validate_acl(value, state, owner, member, permission, head=None):
    expected = dict(member_account_id=member["account_id"], owner_account_id=owner["account_id"],
                    space_id=state["SpaceID"], operation_id=state["OperationID"],
                    canonical_sha256=state["OperationSHA256"], member_permissions=permission,
                    append_count=1 if value["role"]=="owner" else 0, read_target_count=0)
    require(all(value.get(k) == v for k,v in expected.items()), "Wrong native ACL/member/operation")
    require(owner["account_id"] == state["AccountID"] and owner["account_id"] != member["account_id"],
            "Distinct wallets are required")
    records = value.get("acl_records_sha256", {})
    require(isinstance(records, dict) and value.get("acl_head") in records and
            all(isinstance(k, str) and k and is_hash(v) for k,v in records.items()), "Missing native signed ACL bytes")
    require(isinstance(value.get("read_key_id"), str) and value["read_key_id"], "Missing native read key identity")
    if head is not None:
        require(value["acl_head"] == head, "Native peer did not observe exact signed head")


def same_acl(owner, member):
    require(all(owner[k] == member[k] for k in ("acl_head","acl_records_sha256","member_permissions","read_key_id")),
            "Signed ACL records did not converge over native transport")


def export(private, evidence):
    needles = []
    for role in PHASES:
        path = private / role / "sensitive-needles.private"
        if not path.is_file() or path.is_symlink():
            return dict(status="WITHHELD_NO_COMPLETE_TWO_WALLET_SECRET_INVENTORY", files={})
        require(path.stat().st_size <= 64*1024, "Unsafe wallet secret inventory")
        values = json.loads(path.read_bytes())
        require(isinstance(values,list) and len(values)==2 and all(isinstance(v,str) and v for v in values),
                "Incomplete wallet secret inventory")
        needles.extend(value.encode() for value in values)
    require(len(set(needles))==4, "Independent wallets must not share recovery material")
    candidates=[]
    for role,names in PUBLISHED.items():
        for name in sorted(names):
            path=private/role/name
            if not path.exists(): continue
            require(path.is_file() and not path.is_symlink() and path.stat().st_size<=16*1024**2, "Unsafe raw export")
            raw=path.read_bytes()
            require(not any(secret in raw for secret in needles), "Raw evidence contains wallet recovery material")
            candidates.append((role+"/"+name,raw))
    require(not evidence.exists(), "Fresh member evidence export required")
    evidence.mkdir(parents=True)
    files={}
    for name,raw in candidates:
        path=evidence/name;path.parent.mkdir(exist_ok=True);path.write_bytes(raw);files[name]=sha(raw)
    return dict(status="PASS_TWO_DISTINCT_WALLET_SECRET_SCAN",files=files)
