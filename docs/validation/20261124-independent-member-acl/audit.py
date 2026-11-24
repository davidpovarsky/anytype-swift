#!/usr/bin/env python3
"""Read-only qualification of original T2 member transport evidence."""
import hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ORIGINAL=ROOT/"artifact"
CONTROL=Path(sys.argv[1])
APP="a7ff33c7128ff706a0ed25bd4a777e7cc62269bb"
RUN="45430971070"
ZIP="e6d8253f97e17ba16f5e83d1ce8b4e98fce7b453430f3e5a0ebc0158a989cb8b"
def sha(x):return hashlib.sha256(x).hexdigest()
def load(p):return json.loads(p.read_bytes())
def fields(raw):
    position=0
    def varint():
        nonlocal position
        value=0
        for shift in range(0,70,7):
            assert position<len(raw)
            byte=raw[position];position+=1;value|=(byte&127)<<shift
            if byte<128:return value
        raise AssertionError("invalid varint")
    result=[]
    while position<len(raw):
        tag=varint();number,wire=tag>>3,tag&7
        assert number>0
        if wire==0:value=varint()
        elif wire==2:
            size=varint();assert size<=len(raw)-position
            value=raw[position:position+size];position+=size
        else:raise AssertionError("unexpected wire type")
        result.append((number,wire,value))
    return result
def one(fs,n,w,default=None):
    values=[v for f,t,v in fs if f==n and t==w]
    assert len(values)<=1
    if values:return values[0]
    assert default is not None
    return default
assert sha((ROOT/"original-artifact.zip").read_bytes())==ZIP
with zipfile.ZipFile(ROOT/"original-artifact.zip") as z:
    originals={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
assert len(originals)==46
assert {str(p.relative_to(ORIGINAL)) for p in ORIGINAL.rglob("*") if p.is_file()}==set(originals)
assert all((ORIGINAL/n).read_bytes()==raw for n,raw in originals.items())
run=load(ROOT/"run.json");r=load(ORIGINAL/"receipt.json");b=load(ORIGINAL/"build.json")
assert run["head_sha"]==APP and run["id"]==int(RUN) and run["run_attempt"]==1 and run["conclusion"]=="success"
assert r["run_id"]==b["run_id"]==RUN and r["run_attempt"]==b["run_attempt"]=="1"
assert r["app_sha"]==b["app_sha"]==APP
assert r["status"]=="PASS_INDEPENDENT_MEMBER_NATIVE_ACL_TRANSPORT_AND_OBSERVED_REVOCATION_FENCE"
assert b["status"]=="BUILT_INDEPENDENT_MEMBER_ACL_FIXTURE_NOT_EXECUTED"
assert sha((ORIGINAL/"build.json").read_bytes())==r["build_receipt_sha256"]
assert r["binary_sha256"]==b["binary_sha256"]
assert r["fixture_sha256"]==b["fixture_sha256"]=="bc3ac46b2cf4797fe1b9bdafcd9629599f5a518569a6d54e387900b99b924f37"
native=load(ORIGINAL/"native-source-before.json")
assert native==load(ORIGINAL/"native-source-after.json")==b["native_source_sha256"] and len(native)==139
assert b["patch_sha256"]==r["patch_sha256"]=="2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
assert b["inventory_sha256"]==r["inventory_sha256"]=="05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0"
controller=load(ORIGINAL/"build-control-source-before.json")
assert controller==load(ORIGINAL/"build-control-source-after.json")
for path,digest in controller.items():
    raw=subprocess.check_output(["git","-C",str(CONTROL),"show",APP+":"+path])
    assert sha(raw)==digest,path
assert all(x["status"]=="PASS_EXIT_0" for x in r["commands"])
assert b["old_test_methods_executed"]==r["old_test_methods_executed"]==0
assert b["protobuf_generation_executed"]==0
assert r["actual_named_pass"]==2 and r["actual_native_processes"]==2 and r["actual_fail"]==r["actual_skip"]==0
assert r["owned_cleanup"]=={"errors":[],"status":"PASS"} and r["owned_data_cleanup"]=="PASS"
assert r["evidence_export"]["status"]=="PASS_TWO_DISTINCT_WALLET_SECRET_SCAN"
assert r["independent_wallets"] and r["distinct_database_inodes"] and r["seeded_private_key_files"]==0
assert len(r["evidence_export"]["files"])==25
for name,digest in r["evidence_export"]["files"].items():
    assert sha((ORIGINAL/"actual"/name).read_bytes())==digest,name
def report(role,phase):return load(ORIGINAL/"actual"/role/(phase+".json"))
identity={role:report(role,"identity")["identity"] for role in ("owner","member")}
for field in ("account_id","peer_id","ip","network_namespace"):
    assert identity["owner"][field]!=identity["member"][field]
for field in ("container_id","host_pid","namespace","sandbox_id","peer_id"):
    assert r["native_peers"]["owner"][field]!=r["native_peers"]["member"][field]
phases={"owner":["identity","grant","reader","revoke","final"],"member":["identity","grant","reader","offline","unknown-revocation","publication-fence","revoked","final"]}
for role,names in phases.items():
    for phase in names:
        v=report(role,phase)
        assert v["source_sha"]==APP and v["fixture_sha256"]==b["fixture_sha256"]
        assert v["account_id"]==identity[role]["account_id"] and v["peer_id"]==identity[role]["peer_id"]
        assert v["network_namespace"]==identity[role]["network_namespace"] and v["pid"]==1
        assert v["wallet_create_count"]==1 and v["wallet_recover_count"]==0 and v["rpc_calls"].get("WalletRecover",0)==0
        assert v["nonce"]==r["owner_nonce"] and v["phase"]==phase and v["role"]==role
        if phase in ("offline","unknown-revocation"):assert v["actual_ipv4"]==[]
        else:assert len(v["actual_ipv4"])==1
    text=(ORIGINAL/"actual"/role/"native.log").read_text()
    assert re.findall(r"^=== RUN\s+(\S+)\s*$",text,re.M)==["TestIndependentMemberACLTransport"]
    assert re.findall(r"^--- (PASS|FAIL|SKIP): (\S+) \(",text,re.M)==[("PASS","TestIndependentMemberACLTransport")]
    final=report(role,"final")
    assert final["returned_byte_calls"]==final["rpc_calls"]
    assert final["rpc_calls"]["AccountStop"]==final["rpc_calls"]["AppShutdown"]==1
    assert final["account_stop_verified"] and final["test_passed"] and not final["snapshot_present"]
def same_acl(a,c,permission):
    assert all(a[k]==c[k] for k in ("acl_head","acl_records_sha256","member_permissions","read_key_id"))
    assert a["member_permissions"]==permission
grant=report("owner","grant");reader=report("owner","reader");revoke=report("owner","revoke")
same_acl(grant,report("member","grant"),3)
for phase in ("reader","offline","unknown-revocation"):same_acl(reader,report("member",phase),4)
for phase in ("publication-fence","revoked","final"):same_acl(revoke,report("member",phase),0)
assert len({grant["acl_head"],reader["acl_head"],revoke["acl_head"]})==3
assert revoke["read_key_id"]!=reader["read_key_id"]
assert report("member","offline")["real_native_preparation_captured"]
unknown=report("member","unknown-revocation")
assert unknown["unseen_owner_head"]==revoke["acl_head"] and unknown["policy"]=="last-known-local-authority-before-native-revocation-observation"
fence=report("member","publication-fence")
assert fence["prepared_before_revocation"] and fence["finalized_after_observed_revocation"]
assert fence["actual_ipv4"]==report("member","revoked")["actual_ipv4"]==[r["network_reconnect"]["assigned_ipv4"]]
assert r["network_reconnect"]["status"]=="PASS_SAME_NATIVE_PROCESS_RECONNECTED"
variants=[]
for role,phase in (("owner","grant"),("owner","reader"),("member","grant"),("member","reader"),("member","offline"),("member","unknown-revocation")):
    v=report(role,phase);raw=(ORIGINAL/"actual"/role/(phase+".pb")).read_bytes();assert sha(raw)==v["wire_sha256"]
    outer=fields(raw);assert {f for f,_,_ in outer}=={1,2,3} and one(outer,2,0)==1
    error=fields(one(outer,1,2));assert one(error,1,0,0)==0 and one(error,2,2,b"")==b""
    snapshot=fields(one(outer,3,2));assert {f for f,_,_ in snapshot}==set(range(1,9))
    assert one(snapshot,1,2)==b"pinkha-authorized-operation-read-v1"
    assert one(snapshot,2,2)==identity[role]["account_id"].encode()
    assert one(snapshot,3,2)==v["space_id"].encode() and one(snapshot,4,2)==v["operation_id"].encode()
    assert one(snapshot,5,0)==one(snapshot,6,0)==1
    variant=one(snapshot,8,2);variants.append(variant);vv=fields(variant)
    assert sha(variant)==v["variant_sha256"] and {f for f,_,_ in vv}==set(range(1,9))
    assert one(vv,4,2)==identity["owner"]["account_id"].encode()
    assert sha(one(vv,6,2))==v["canonical_sha256"] and one(vv,8,0)==2
    provenance=fields(one(vv,7,2))
    assert one(provenance,1,2)==identity["owner"]["account_id"].encode() and one(provenance,2,2) and one(provenance,3,2)
assert len(set(variants))==1
codes={}
for role,phase,expected in (("member","publication-fence",4),("member","revoked",4),("owner","final",5),("member","final",5)):
    raw=(ORIGINAL/"actual"/role/(phase+".pb")).read_bytes();outer=fields(raw)
    assert len(outer)==2 and {f for f,_,_ in outer}=={1,2} and one(outer,2,0)==1
    assert one(fields(one(outer,1,2)),1,0)==expected
    assert sha(raw)==report(role,phase)["wire_sha256"];codes[role+"/"+phase]=expected
for key,value in {"app_capability":"OFF","full_t2_acceptance":"NOT_RUN","ios_acceptance":"NOT_RUN","mixed_versions":"NOT_RUN","coordinator_invite_acceptance":"NOT_RUN","discovery_bootstrap":"STATIC_OWNED_PEER_ROUTE"}.items():assert r[key]==value
result={"status":"PASS_ORIGINAL_MEMBER_TRANSPORT_EVIDENCE_AUDIT","run_id":RUN,"app_sha":APP,
"artifact_id":14939671272,"zip_sha256":ZIP,"original_files_verified":46,"controller_git_blobs_verified":len(controller),
"native_inventory_unchanged":len(native),"native_fixture_files":len(b["fixture_source_sha256"]),
"actual_named_native_passes":2,"actual_failures":0,"actual_skips":0,
"native_runtime_exports_verified":25,"positive_raw_responses":len(variants),"exact_signed_variant_sha256":sha(variants[0]),
"zero_snapshot_wire_denials":codes,"independent_wallets":True,"native_signed_acl_converged":True,
"offline_last_known_authority_observed":True,"actual_reconnect_observed":True,
"prepared_read_fenced_after_observed_revocation":True,"both_accounts_stopped":True,
"original_failed_run_retained":"45426427384/1","full_t2_acceptance":"NOT_RUN","ios_acceptance":"NOT_RUN","mixed_versions":"NOT_RUN","app_capability":"OFF"}
(ROOT/"AUDIT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
