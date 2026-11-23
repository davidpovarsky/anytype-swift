#!/usr/bin/env python3
"""Audit the original hardening receipts only; never compile or execute product tests."""
from pathlib import Path
import collections,hashlib,json,subprocess,re
E=Path("/mnt/development/projects/evidence/localstore-witness-20261123/hardening-attempt1")
OLD=Path("/mnt/development/projects/evidence/localstore-witness-20261123/attempt1")
N=Path("/mnt/development/projects/worktrees/anytype-heart-localstore-witness-hardening-20261123")
ON=Path("/mnt/development/projects/worktrees/anytype-heart-localstore-witness-20261123")
S=Path("/mnt/development/projects/worktrees/anytype-wave15-localstore-witness-20261123")
SOURCE="1e9832bf41e1083cb757a8de0528dd98606a7b6f"
NATIVE="102f6243edb17068048869b85bc151f177897a68"
ORIGINAL="74b5f2c844ac3879125888c538d5990af3db3cb8"
REL="Tools/AnyEngineValidation/native_localstore_witness/hardening"
METHODS=["TestLocalStoreWitnessConcreteCapabilityRejectsExternalEmbeddingAndZero","TestLocalStoreWitnessOwnershipAndCancellation"]
CHILDREN=["retired-before","retired-after-inventory","wrong-space","unsupported-authority","cancel-after-inventory","lease-close"]
PACKAGE="github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
def sha(data):return hashlib.sha256(data).hexdigest()
def filehash(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for part in iter(lambda:f.read(1048576),b""):h.update(part)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def blob(root,revision,rel):
 return subprocess.check_output(["git","-C",str(root),"show",revision+":"+rel])
def normalized(paths,prefix):
 return {("NATIVE/"+p[len(str(prefix))+1:]) if p.startswith(str(prefix)+"/") else p:v for p,v in paths.items()}
def main():
 build=load(E/"build.json");execute=load(E/"execute.json")
 assert build["status"]=="BUILD_PASS_EXECUTION_NOT_RUN" and build["actual_product_methods_executed"]==0
 assert execute["status"]=="PASS_CONCRETE_CAPABILITY_SCOPE_ONLY"
 assert execute["actual_product_methods_executed"]==2 and execute["actual_named_starts_and_passes"]==8
 assert execute["new_external_methods_executed"]==execute["directly_affected_existing_methods_executed"]==1
 assert execute["old_unchanged_methods_run"]==execute["actual_interleaving_proofs"]==0
 for receipt in [build,execute]:
  assert receipt["native_source_sha"]==NATIVE and receipt["controller_source_sha"]==SOURCE
  assert receipt["free_bytes_final"]>=2500000000
  c=receipt["command"]
  assert c["returncode"]==0 and c["interruption"] is None and c["owned_process_group_absent"]
  assert c["free_bytes_before"]>=2600000000 and c["free_bytes_after"]>=2600000000
  assert c["owned_pid"]==c["owned_pgid"]
 assert build["environment"]["GOMAXPROCS"]=="1" and build["environment"]["GOPROXY"]=="off"
 assert "-p=1" in build["command"]["argv"] and "-c" in build["command"]["argv"]
 selector="^("+"|".join(METHODS)+")$"
 assert "-test.run="+selector in execute["command"]["argv"] and "-test.count=1" in execute["command"]["argv"]
 assert execute["command"]["argv"][1:3]==["tool","test2json"]
 for name in ["dependencies-original.json","build-original.log","execution-original.jsonl"]:
  p=E/"private"/name;command=load(p.with_suffix(p.suffix+".command.json"))
  assert command["original_log_sha256"]==filehash(p) and command["original_log_bytes"]==p.stat().st_size
  assert command["returncode"]==0 and command["owned_process_group_absent"] and command["interruption"] is None
  if name!="dependencies-original.json":
   assert command==(build if name=="build-original.log" else execute)["command"]
 original=[json.loads(line) for line in (E/"private/execution-original.jsonl").read_text().splitlines()]
 assert all(v.get("Package")==PACKAGE for v in original)
 safe=[{k:v[k] for k in ["Time","Action","Package","Test","Elapsed"] if k in v} for v in original]
 assert safe==load(E/"safe-events.json")
 starts=collections.Counter(v["Test"] for v in original if v.get("Action")=="run" and "Test" in v)
 passes=collections.Counter(v["Test"] for v in original if v.get("Action")=="pass" and "Test" in v)
 wanted=set(METHODS)|{METHODS[1]+"/"+x for x in CHILDREN}
 assert starts==passes and set(starts)==wanted and set(starts.values())=={1}
 assert not any(v.get("Action") in ("fail","skip") for v in original)
 assert sum(v.get("Action")=="pass" and "Test" not in v for v in original)==1
 assert load(E/"safe-native-receipts.json")==[]
 manifest_bytes=blob(S,SOURCE,REL+"/source.json")
 assert manifest_bytes==(S/REL/"source.json").read_bytes()
 manifest=json.loads(manifest_bytes)
 assert manifest["selected_top_level_methods"]==METHODS
 for r in (build,execute):
  assert r["manifest_sha256"]==sha(manifest_bytes)
  assert r["controller_sha256"]==manifest["controller_sha256"]
 for name,key in [("run.py","controller_sha256"),("PROTOCOL.md","protocol_sha256"),("retention.json","retention_sha256"),("controller-adaptation.diff","controller_adaptation_sha256")]:
  raw=blob(S,SOURCE,REL+"/"+name)
  assert sha(raw)==manifest[key] and raw==(S/REL/name).read_bytes()
 bound={}
 for row in manifest["files"]:
  raw=blob(N,NATIVE,row["native_path"])
  assert len(raw)==row["bytes"] and sha(raw)==row["sha256"]
  assert raw==(N/row["native_path"]).read_bytes()==blob(S,SOURCE,row["copy_path"])==(S/row["copy_path"]).read_bytes()
  bound[row["native_path"]]=row["sha256"]
 for path,h in manifest["module_sha256"].items():
  assert filehash(N/path)==sha(blob(N,NATIVE,path))==h
  bound[path]=h
 for stage in ["build","execute"]:
  for when in ["before","after","final"]:
   assert load(E/(stage+"-source-"+when+".json"))==bound
 deps=load(E/"dependency-inputs-before.json")
 assert deps==load(E/"dependency-inputs-after-build.json")==load(E/"dependency-inputs-after-execute.json")
 for p,h in deps.items():assert filehash(p)==h,p
 old_deps=normalized(load(OLD/"dependency-inputs-before.json"),ON)
 new_deps=normalized(deps,N)
 added=sorted(set(new_deps)-set(old_deps))
 removed=sorted(set(old_deps)-set(new_deps))
 changed=sorted(p for p in old_deps.keys()&new_deps.keys() if old_deps[p]!=new_deps[p])
 assert added==["NATIVE/core/pinkha/localstorewitness/export_test.go","NATIVE/core/pinkha/localstorewitness/external_capability_test.go"]
 assert removed==[]
 assert changed==["NATIVE/core/pinkha/localstorewitness/capture.go","NATIVE/core/pinkha/localstorewitness/capture_test.go","NATIVE/core/pinkha/localstorewitness/fixture_test.go"]
 binary=E/"products/localstore-witness.test"
 assert filehash(binary)==build["binary_sha256"]==execute["binary_sha256"]
 assert binary.stat().st_size==build["binary_bytes"]
 private=load(E/"private-artifacts-hashes.json")
 found=set()
 for p in (E/"private/fixtures").rglob("*"):
  assert not p.is_symlink()
  if p.is_file():found.add(str(p.relative_to(E/"private")))
 assert found==set(private)
 for rel,r in private.items():
  p=E/"private"/rel
  assert filehash(p)==r["sha256"] and p.stat().st_size==r["bytes"] and oct(p.stat().st_mode&0o777)==r["mode"]
 assert (E/"private").stat().st_mode&0o777==0o700 and (E/"private/fixtures").stat().st_mode&0o777==0o700
 assert filehash(OLD/"execute.json")=="3ca194d76d66dd1035dae6d077231e81e13c16fac524b05f11a226facb8f313b"
 assert filehash(OLD/"products/localstore-witness.test")=="99036b6b74b9914f9fd008d1f97a2d02146e0de55baf2dd4cd8a2b81a07636d2"
 assert subprocess.check_output(["git","-C",str(ON),"rev-parse","HEAD"],text=True).strip()==ORIGINAL
 old_paths=subprocess.check_output(["git","-C",str(S),"ls-tree","-r","--name-only","dfc14f3dd6c769f1ddf74880165d86a47a5277d8","--","Tools/AnyEngineValidation/native_localstore_witness","docs/validation/20261123-native-localstore-witness"],text=True).splitlines()
 for p in old_paths:assert (S/p).read_bytes()==blob(S,"dfc14f3dd6c769f1ddf74880165d86a47a5277d8",p)
 receipt={"kind":"independent-original-hardening-evidence-audit-v1","status":"PASS_ORIGINAL_EVIDENCE_AUDIT","native_source_sha":NATIVE,"controller_source_sha":SOURCE,"source_manifest_sha256":sha(manifest_bytes),"actual_named_starts":8,"actual_named_passes":8,"actual_top_methods":2,"new_external_methods":1,"directly_affected_existing_methods":1,"old_unchanged_methods_run":0,"new_interleaving_proofs":0,"retained_original_interleaving_proof_at":ORIGINAL,"native_git_inputs":len(bound),"resolved_source_dependency_inputs":len(deps),"normalized_dependency_delta":{"added":added,"removed":removed,"changed":changed},"original_baseline_files_unchanged":len(old_paths),"private_artifacts_verified":len(private),"binary":{"path":str(binary),"sha256":filehash(binary),"bytes":binary.stat().st_size},"build_receipt_sha256":filehash(E/"build.json"),"execute_receipt_sha256":filehash(E/"execute.json"),"safe_event_log_sha256":filehash(E/"safe-events.json"),"raw_event_log_sha256":filehash(E/"private/execution-original.jsonl"),"auditor_sha256":filehash(__file__),"hasNativeSourceAdmission":False,"permitsDestinationWrites":False,"nativeSnapshotProofRequired":True,"nativeIdentityCensusRequired":True,"tests_executed_by_this_auditor":0}
 out=E/"independent-audit.json"
 with out.open("x") as f:f.write(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"audit":str(out),"sha256":filehash(out),"actual_top_methods":2,"actual_named_starts_and_passes":8,"resolved_source_dependency_inputs":len(deps),"private_artifacts":len(private),"new_interleaving_proofs":0}))
if __name__=="__main__":main()
