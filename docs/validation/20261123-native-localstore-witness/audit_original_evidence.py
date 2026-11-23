#!/usr/bin/env python3
"""Read original native receipts/private witnesses; emit only safe audit metadata."""
from pathlib import Path
import collections,hashlib,json,struct,subprocess
E=Path("/mnt/development/projects/evidence/localstore-witness-20261123/attempt1")
N=Path("/mnt/development/projects/worktrees/anytype-heart-localstore-witness-20261123")
S=Path("/mnt/development/projects/worktrees/anytype-wave15-localstore-witness-20261123")
SOURCE="e49f9b137a24dfb3507b3d932ed09382ec58e0b2"
NATIVE="74b5f2c844ac3879125888c538d5990af3db3cb8"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def filehash(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_bytes())
def git(root,rev,path):
 return subprocess.check_output(["git","-C",str(root),"show",rev+":"+path])
def original_events():
 raw=(E/"private/execution-original.jsonl").read_text()
 events=[json.loads(line) for line in raw.splitlines()]
 safe=[{k:v[k] for k in ["Time","Action","Package","Test","Elapsed"] if k in v} for v in events]
 assert safe==load(E/"safe-events.json")
 starts=collections.Counter(v["Test"] for v in events if v.get("Action")=="run" and "Test" in v)
 passes=collections.Counter(v["Test"] for v in events if v.get("Action")=="pass" and "Test" in v)
 assert starts==passes and len(starts)==21 and set(starts.values())=={1}
 assert sum("/" not in k for k in starts)==6
 assert not any(v.get("Action") in ("fail","skip") for v in events)
 return safe,events

# Independent parser of the pinned native anyenc decoded-value representation.
# Number payloads stay exact encoded 8-byte tokens; no numeric conversion needed.
def decoded(data):
 def at(pos,depth):
  assert depth<=64 and pos<len(data)
  tag=data[pos];pos+=1
  if tag in (1,4,5):return (tag,None),pos
  if tag==2:
   assert pos+8<=len(data);return (tag,data[pos:pos+8]),pos+8
  if tag==3:
   end=data.index(0,pos);return (tag,data[pos:end]),end+1
  if tag==8:
   assert pos+4<=len(data)
   size=int.from_bytes(data[pos:pos+4],"big");pos+=4
   assert pos+size<=len(data);return (tag,data[pos:pos+size]),pos+size
  if tag==6:
   values=[]
   while data[pos]!=0:
    value,pos=at(pos,depth+1);values.append(value)
   return (tag,tuple(values)),pos+1
  if tag==7:
   values=[]
   while data[pos]!=0:
    end=data.index(0,pos);key=data[pos:end]
    if key==bytes([31]):key=b""
    value,pos=at(end+1,depth+1);values.append((key,value))
   return (tag,tuple(values)),pos+1
  raise AssertionError("unsupported native encoding tag")
 value,end=at(0,0);assert end==len(data);return value
def field(value,key):
 assert value[0]==7
 found=[v for k,v in value[1] if k==key]
 assert len(found)==1
 return found[0]
def parsed_witness(path):
 raw=path.read_bytes();pos=0
 def frame():
  nonlocal pos
  assert pos+8<=len(raw)
  size=int.from_bytes(raw[pos:pos+8],"big");pos+=8
  assert size<=32*1024*1024 and pos+size<=len(raw)
  out=raw[pos:pos+size];pos+=size;return out
 assert frame()==b"pinkha-localstore-witness-v1"
 assert frame()==b"anyenc-v1.0.3-decoded-value-roundtrip-v1"
 assert frame()==b"owned-fixture-only-v1"
 nonce,space=frame(),frame()
 generation=int.from_bytes(frame(),"big")
 count=int.from_bytes(frame(),"big")
 assert len(nonce)==32 and generation==1 and 0<count<=64
 cols={}
 value_bytes=0
 for _ in range(count):
  name=frame();assert name not in cols
  n=int.from_bytes(frame(),"big");assert n<=10000
  rows={}
  for _ in range(n):
   id_encoded,value_encoded=frame(),frame()
   identity=decoded(id_encoded);value=decoded(value_encoded)
   assert identity==field(value,b"id") and id_encoded not in rows
   rows[id_encoded]=(identity,value,value_encoded)
   value_bytes+=len(value_encoded)
  cols[name]=rows
 assert pos==len(raw)
 return {"nonce":nonce,"space":space,"generation":generation,"collections":cols,"value_bytes":value_bytes,"digest":sha(raw)}
def native_row(w,name,identity):
 rows=w["collections"][name]
 found=[v for k,v in rows.items() if v[0]==(3,identity)]
 assert len(found)==1
 return found[0][1]
def verify_private_witnesses():
 paths=sorted((E/"private/fixtures").glob("*/first-transaction.private.bin"))
 assert len(paths)==1
 first=parsed_witness(paths[0])
 later_path=paths[0].with_name("later-transaction.private.bin")
 later=parsed_witness(later_path)
 receipts=load(E/"safe-native-receipts.json")
 for w,r in zip([first,later],receipts):
  assert w["digest"]==r["WitnessSHA256"]
  assert sha(w["nonce"])==r["OwnerSHA256"] and sha(w["space"])==r["SpaceSHA256"]
  assert w["generation"]==r["Generation"]
  assert len(w["collections"])==r["Collections"]
  assert sum(len(v) for v in w["collections"].values())==r["Rows"]
  assert w["value_bytes"]==r["EncodedValueBytes"]
  state=native_row(w,b"state",w["space"])
  assert sha(field(state,b"e")[1])==r["SpaceHeaderSHA256"]
  acl=field(state,b"a")[1]
  coverage={sha(name):(len(rows),sum(len(v[2]) for v in rows.values()),name not in (b"state",b"heads",b"changes",b"_client",acl)) for name,rows in w["collections"].items()}
  assert coverage=={r["NameSHA256"]:(r["Rows"],r["EncodedValueBytes"],r["UnresolvedCollection"]) for r in r["CollectionCoverage"]}
  assert r["NativeSnapshotProofRequired"] and r["NativeIdentityCensusRequired"]
  assert not r["HasNativeSourceAdmission"] and not r["PermitsDestinationWrites"]
 assert first["nonce"]==later["nonce"] and first["space"]==later["space"]
 assert len(first["collections"])==5 and len(later["collections"])==6
 a=native_row(first,b"state",first["space"]);b=native_row(later,b"state",later["space"])
 assert field(a,b"nh")==field(a,b"oh")==(3,b"before")
 assert field(b,b"nh")==field(b,b"oh")==(3,b"after")
 assert [(k,v) for k,v in a[1] if k not in (b"nh",b"oh")]==[(k,v) for k,v in b[1] if k not in (b"nh",b"oh")]
 probe=b"witness-owned-probe"
 assert len(first["collections"][probe])==2 and len(later["collections"][probe])==3
 for w,key,expected in [(first,b"a",bytes([0,1,2,255])),(first,b"b",bytes([9,0,8,255])),(later,b"a",bytes([4,5,6,255])),(later,b"c",bytes([7,0,7]))]:
  value=native_row(w,probe,key)
  assert field(value,b"payload")==(8,expected)
  assert field(value,b"unicode")==(3,"\u05e9\u05dc\u05d5\u05dd e\u0301 \u00e9".encode())
 new=b"witness-created-after-first-read"
 assert new not in first["collections"]
 assert field(native_row(later,new,b"new"),b"payload")==(8,bytes([33,0,44]))
 for name in first["collections"]:
  if name not in (b"state",probe):assert first["collections"][name]==later["collections"][name]
 return [{"path":str(paths[0].relative_to(E)),"sha256":first["digest"],"collections":5,"rows":7},{"path":str(later_path.relative_to(E)),"sha256":later["digest"],"collections":6,"rows":9}]
def main():
 manifest=load(S/"Tools/AnyEngineValidation/native_localstore_witness/source.json")
 assert manifest["native_source_sha"]==NATIVE
 build,execute=load(E/"build.json"),load(E/"execute.json")
 assert build["status"]=="BUILD_PASS_EXECUTION_NOT_RUN"
 assert execute["status"]=="PASS_NATIVE_LOCAL_STORAGE_SCOPE_ONLY"
 assert build["actual_product_methods_executed"]==0
 assert execute["actual_product_methods_executed"]==6 and execute["actual_named_starts_and_passes"]==21
 assert build["controller_source_sha"]==execute["controller_source_sha"]==SOURCE
 for name in ["build","execute"]:
  result=load(E/(name+".json"))
  assert result["command"]["returncode"]==0 and result["command"]["owned_process_group_absent"]
  raw=E/"private"/("build-original.log" if name=="build" else "execution-original.jsonl")
  assert filehash(raw)==result["command"]["original_log_sha256"]
  assert load(raw.with_suffix(raw.suffix+".command.json"))==result["command"]
 paths=load(E/"build-source-before.json")
 for name in ["build-source-after.json","build-source-final.json","execute-source-before.json","execute-source-after.json","execute-source-final.json"]:
  assert load(E/name)==paths
 for rel,expected in paths.items():
  assert filehash(N/rel)==sha(git(N,NATIVE,rel))==expected
 for row in manifest["files"]:
  assert filehash(S/row["copy_path"])==sha(git(S,SOURCE,row["copy_path"]))==row["sha256"]
 deps=load(E/"dependency-inputs-before.json")
 for name in ["dependency-inputs-after-build.json","dependency-inputs-after-execute.json"]:assert load(E/name)==deps
 for path,expected in deps.items():assert filehash(path)==expected
 binary=E/"products/localstore-witness.test"
 assert filehash(binary)==build["binary_sha256"]==execute["binary_sha256"]
 assert binary.stat().st_size==build["binary_bytes"]==25485911
 safe,events=original_events()
 witnesses=verify_private_witnesses()
 private=load(E/"private-artifacts-hashes.json")
 for rel,expected in private.items():
  path=E/"private"/rel
  assert filehash(path)==expected["sha256"] and path.stat().st_size==expected["bytes"]
 originals={str(p.relative_to(E)):{"sha256":filehash(p),"bytes":p.stat().st_size} for p in sorted(E.iterdir()) if p.is_file() and p.name!="independent-audit.json"}
 for name in ["dependencies-original.json","build-original.log","execution-original.jsonl"]:
  p=E/"private"/name
  originals["private/"+name]={"sha256":filehash(p),"bytes":p.stat().st_size,"private_original_not_published":True}
  meta=p.with_suffix(p.suffix+".command.json")
  originals[str(meta.relative_to(E))]={"sha256":filehash(meta),"bytes":meta.stat().st_size}
 report={"status":"PASS_INDEPENDENT_ORIGINAL_RECEIPT_AND_PRIVATE_WITNESS_AUDIT",
  "native_source_sha":NATIVE,"controller_source_sha":SOURCE,
  "top_level_methods":6,"named_starts":21,"named_passes":21,"failures":0,"skips":0,"old_methods":0,
  "native_transaction_proofs":1,"private_witnesses":witnesses,"private_files_hash_verified":len(private),
  "native_git_inputs":len(paths),"resolved_source_dependency_inputs":len(deps),
  "unique_input_paths":len(set(deps)|{str(N/p) for p in paths}),
  "binary":{"path":str(binary),"sha256":filehash(binary),"bytes":binary.stat().st_size},
  "actual_dependency_modules":sum(line.startswith("\tdep\t") for line in (E/"binary-buildinfo-original.txt").read_text().splitlines()),
  "originals":originals,"scope":"fixture-owned registered local collection decoded rows only",
  "nativeSnapshotProofRequired":True,"nativeIdentityCensusRequired":True,"hasNativeSourceAdmission":False,"permitsDestinationWrites":False,
  "native_state_before_after_and_unchanged_other_rows_verified_from_private_bytes":True,
  "native_probe_binary_and_unicode_bytes_verified_from_private_bytes":True,
  "runtime_tests_rerun":0}
 (E/"independent-audit.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k not in ("originals","private_witnesses")},sort_keys=True))
 print("AUDIT_SHA256 "+filehash(E/"independent-audit.json"))
if __name__=="__main__":main()
