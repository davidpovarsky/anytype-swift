#!/usr/bin/env python3
"""Forensic inspection of original ZIP bytes, not native acceptance or a production parser."""
import collections, difflib, hashlib, io, json, pathlib, re, struct, subprocess, zipfile
OUT=pathlib.Path("/mnt/development/projects/diagnostics/otzaria-native-archive-readiness-20261123/45130249062")
BASE="d98420b1113536afd08cde6de9a5816f6d27ffff"
SOURCE="0ab05476960c6bbc563c12e038f16c6ceb25c1cd"
PREFIX="docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
def read(repo,rev,path):
 return subprocess.run(["runuser","-u","ubuntu","--","git","--git-dir=/mnt/development/projects/git-mirrors/"+repo+".git","show",rev+":"+path],check=True,capture_output=True).stdout
def sha(b):return hashlib.sha256(b).hexdigest()
def tags(source, name):
 m=re.search(r"type "+name+r" struct \{.*?\n\}",source,re.S);assert m
 return m.group(0)
snapshot=read("anytype-heart",BASE,"pb/snapshot.pb.go")
changes=read("anytype-heart",BASE,"pb/changes.pb.go")
models=read("anytype-heart",BASE,"pkg/lib/pb/model/models.pb.go")
assert 'protobuf:"bytes,2,opt,name=snapshot,' in tags(snapshot.decode(),"SnapshotWithType")
assert 'protobuf:"bytes,2,opt,name=data,' in tags(changes.decode(),"ChangeSnapshot")
sbt=tags(models.decode(),"SmartBlockSnapshotBase")
for text in ['protobuf:"bytes,2,opt,name=details,','protobuf:"bytes,5,rep,name=objectTypes,','protobuf:"bytes,9,opt,name=key,']:
 assert text in sbt
struct_source=(OUT/"original-struct.pb.go").read_bytes()
assert sha(struct_source)=="f4d14166c59147c90960066976c5cbad7884bb9a0950184bffbf9402f691f814"
assert 'protobuf:"bytes,1,rep,name=fields,' in tags(struct_source.decode(),"Struct")
for typ,wire,num,field in [("Value_NullValue","varint",1,"null_value"),("Value_NumberValue","fixed64",2,"number_value"),("Value_StringValue","bytes",3,"string_value"),("Value_BoolValue","varint",4,"bool_value"),("Value_StructValue","bytes",5,"struct_value"),("Value_ListValue","bytes",6,"list_value")]:
 assert 'protobuf:"'+wire+','+str(num)+',opt,name='+field+',' in tags(struct_source.decode(),typ)

def varint(raw,offset):
 value=0
 for shift in range(0,70,7):
  assert offset<len(raw)
  b=raw[offset];offset+=1;value|=(b&127)<<shift
  if b<128:return value,offset
 raise ValueError("overlong varint")
def fields(raw):
 assert len(raw)<=8<<20
 offset=0;result=[]
 while offset<len(raw):
  tag,offset=varint(raw,offset);number,wire=tag>>3,tag&7;assert number>0
  if wire==0:value,offset=varint(raw,offset)
  elif wire in (1,5):
   n=8 if wire==1 else 4;value=raw[offset:offset+n];offset+=n
  elif wire==2:
   n,offset=varint(raw,offset);value=raw[offset:offset+n];offset+=n
  else:raise ValueError("unsupported forensic wire form")
  assert offset<=len(raw);result.append((number,wire,value));assert len(result)<=262144
 return result
def values(raw,number):return [v for n,w,v in fields(raw) if n==number]
def one(raw,number,default=None):
 result=values(raw,number);assert len(result)<=1
 return result[0] if result else default
def val(raw,depth=0):
 assert depth<=64
 f=fields(raw);assert len(f)==1
 n,w,v=f[0]
 if n==1:assert w==0;return None
 if n==2:assert w==1;return struct.unpack("<d",v)[0]
 if n==3:assert w==2;return v.decode("utf-8")
 if n==4:assert w==0;return bool(v)
 if n==5:assert w==2;return object_details(v,depth+1)
 if n==6:assert w==2;return [val(x,depth+1) for x in values(v,1)]
 raise ValueError("unknown value")
def object_details(raw,depth=0):
 assert depth<=64
 result={}
 for n,w,v in fields(raw):
  assert (n,w)==(1,2)
  k=one(v,1,b"").decode("utf-8");assert k not in result
  result[k]=val(one(v,2),depth+1)
 return result
def write(name,data):
 raw=(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode();(OUT/name).write_bytes(raw);return sha(raw)

fixture_path=PREFIX+"/native/core/application/owned_annotation_export_native_test.go"
fixture=read("anytype-swift",SOURCE,fixture_path)
assert sha(fixture)=="a59c2f6eb6424d943d238d13d47f9701c5fc7eeda0a29ddd26b428553b48c1eb"
old=b"slices.Contains(root.Snapshot.Data.ObjectTypes, f.typeKey.String())"
new=b"slices.Contains(root.Snapshot.Data.ObjectTypes, f.typeKey.URL())"
assert fixture.count(old)==1
candidate=fixture.replace(old,new)
patch="".join(difflib.unified_diff(fixture.decode().splitlines(True),candidate.decode().splitlines(True),fromfile="a/"+fixture_path,tofile="b/"+fixture_path))
(OUT/"TYPE_KEY_REPAIR.patch").write_text(patch)
assert candidate.replace(new,old)==fixture
domain_types=read("anytype-heart",BASE,"core/domain/types.go")
domain_unique=read("anytype-heart",BASE,"core/domain/uniquekey.go")
pbc=read("anytype-heart",BASE,"core/converter/pbc/pbc.go")
assert "ObjectTypes: domain.MarshalTypeKeys(st.ObjectTypeKeys())" in pbc.decode()
assert "res = append(res, tk.URL())" in domain_types.decode()
assert "return TypeKey(uk.InternalKey()), nil" in domain_unique.decode()

with zipfile.ZipFile(OUT/"original-native-annotation-archive.zip") as outer:
 phase=json.loads(outer.read("fixtures/schema-registration-00.json"))
 expected_space=phase["observation_space_id"]
 native_type=next(r["native"]["native_key"] for r in phase["definitions"] if r["native"]["native_key"].startswith("ot-"))
 assert native_type=="ot-pinkhatorahannotationv1"
 internal_type=native_type[3:]
 specimens=[]
 for kind in ("text","format","nested","attachment"):
  raw=outer.read("fixtures/"+kind+".zip");snapshots=[]
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   for name in z.namelist():
    if not name.endswith(".pb"):continue
    body=z.read(name);data=one(one(body,2),2);details=object_details(one(data,2))
    types=[x.decode("utf-8") for x in values(data,5)]
    snapshots.append({"member":name,"sha256":sha(body),"id":details.get("id"),"space_id":details.get("spaceId"),"smart_block_type":one(body,1,0),
     "key":one(data,9,b"").decode(),"object_types":types,"details":details,"block_count":len(values(data,1)),
     "snapshot_data_field_numbers":sorted(set(n for n,w,v in fields(data)))})
  roots=[r for r in snapshots if r["details"].get("name")=="Native archive "+kind]
  assert len(roots)==1
  root=roots[0]
  assert root["id"] and root["space_id"]==expected_space
  assert root["object_types"]==[native_type]
  assert internal_type not in root["object_types"]
  rows={"kind":kind,"archive_bytes":len(raw),"archive_sha256":sha(raw),"snapshots":snapshots,
   "root_from_actual_exported_native_name":{k:root[k] for k in ("member","id","space_id","smart_block_type","object_types","block_count")},
   "actual_space_matches_original_registration":True,"expected_original_internal_type":internal_type,
   "expected_original_serialized_type":native_type,"existing_fixture_string_comparison_matches":False,
   "original_url_representation_comparison_matches":True,
   "native_body_assertions_reexecuted":False,"standalone_forensic_parser_only":True,
   "kinds":dict(collections.Counter(r["member"].split("/")[0] for r in snapshots)),
   "raw_graph_bytes":sum(len(outer.read("fixtures/"+kind+".zip")) for _ in [])}
  rows.pop("raw_graph_bytes")
  specimens.append(rows)
 result={"status":"ORIGINAL_SERIALIZED_TYPE_REPRESENTATION_MISMATCH_OBSERVED","native_run":45130249062,"source":SOURCE,
  "failing_assertion":"root exists + internal TypeKey.String membership + same Space",
  "exact_source_cause":"Original PBC serializes domain.MarshalTypeKeys, which calls TypeKey.URL; the fixture compared the unprefixed internal key.",
  "patch_sha256":sha(patch.encode()),"candidate_fixture_sha256":sha(candidate),"candidate_changes":1,
  "fixture_not_modified":True,"candidate_inverse_restores_exact_fixture":True,
  "unchanged_assertions":["native root identity","same native Space","text and style","marks","nested block and object","attachment original upload identity and bytes","original export report","native cleanup"],
  "forensic_scope":"Exact retained original bytes interpreted using authenticated generated field tags; this does not convert failed native leaves to PASS.",
  "models":[{"path":p,"revision":BASE,"sha256":sha(b)} for p,b in [("pb/snapshot.pb.go",snapshot),("pb/changes.pb.go",changes),("pkg/lib/pb/model/models.pb.go",models),("core/domain/types.go",domain_types),("core/domain/uniquekey.go",domain_unique),("core/converter/pbc/pbc.go",pbc)]],
  "struct_generated_input_sha256":sha(struct_source),"specimens":specimens}
 h=write("TYPE_REPRESENTATION_DIAGNOSIS.json",result)
 print(json.dumps({"status":result["status"],"receipt_sha256":h,"patch_sha256":result["patch_sha256"],"candidate_fixture_sha256":result["candidate_fixture_sha256"],"roots":[r["root_from_actual_exported_native_name"] for r in specimens],"kinds":[r["kinds"] for r in specimens]}))
