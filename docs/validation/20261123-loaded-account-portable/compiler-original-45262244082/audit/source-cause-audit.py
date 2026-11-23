import pathlib,hashlib,json,os,stat,sys,time
ROOT=pathlib.Path(r"C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\loaded-account-compiler-original-45262244082-1")
A=ROOT/"audit1";O=A/"originals"
def unique(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError("duplicate:"+k)
  out[k]=v
 return out
def read(p):return json.loads(p.read_bytes(),object_pairs_hook=unique)
def sha(b):return hashlib.sha256(b).hexdigest()
def row(p):
 b=p.read_bytes()
 return {"bytes":len(b),"sha256":sha(b)}
def save(p,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 return row(p)
assert sha((A/"audit.json").read_bytes())=="206d4d3a87ef24c7cad4f24e9d303634d9fe36cf7ed81b1c42e3e84797e3d53f"
assert sha((A/"member-map.json").read_bytes())=="cf1619940af2395943ceb932c172177983dd429b2ccba2d84aafea574bebfef4"
m=read(A/"member-map.json")
assert len(m)==114 and set(m)=={p.relative_to(O).as_posix() for p in O.rglob("*") if p.is_file()}
for rel,x in m.items():
 p=O/rel;s=p.stat()
 assert not s.st_file_attributes&1024 and stat.S_ISREG(s.st_mode)
 assert row(p)=={k:x[k] for k in ("bytes","sha256")}
r=read(O/"result.json");before=read(O/"source-before.json");after=read(O/"source-after.json")
assert before==after==r["source_after"] and len(before)==6
assert r["loaded_source_before"]==r["loaded_source_after"]
assert r["host_tool_before"]==r["host_tool_after"]
assert set(r["loaded_source_before"])=={"__main__"}
assert r["loaded_source_before"]["__main__"]["sha256"]=="0fd72d2024a5b3a1bdccb5cb9392a5ae8b646f685b0c56493c7f44feb62370e3"
assert r["context"]=={"job":"compiler","ref":"refs/heads/codex/chatgpt-wave15-shared-20261121","run_attempt":"1","run_id":"45262244082","source_sha":"56b4caafae1c0898b483717abed495f2e3b9281b","workflow_ref":"davidpovarsky/anytype-swift/.github/workflows/torah-inspector-ipados27.yml@refs/heads/codex/chatgpt-wave15-shared-20261121"}
commands={}
for i,c in enumerate(r["commands"]):
 assert c["name"] not in commands
 assert c==read(O/"commands"/("%03d-%s.json"%(i,c["name"])))
 assert c["started"] is True and c["returncode"]==0 and c["primary_error"] is None and c["cleanup_error"] is None and c["persistence_errors"]==[]
 assert c["pid"]==c["pgid"] and c["pid"]>0
 assert c["owned_group_cleanup"]=={"already_absent":True,"returncode":0}
 assert 0<=c["elapsed_seconds"]<=c["timeout_seconds"]
 for stream in ("stdout","stderr"):
  name="%03d-%s.%s"%(i,c["name"],stream)
  assert c[stream]["path"]=="/home/runner/work/_temp/pinkha-loaded-account-compiler/commands/"+name
  assert row(O/"commands"/name)=={k:c[stream][k] for k in ("bytes","sha256")}
 commands[c["name"]]=c
assert len(commands)==36
def output(name):
 c=commands[name]
 return (O/"commands"/pathlib.PurePosixPath(c["stdout"]["path"]).name).read_bytes()
sourceproof={}
for phase in ("before","after"):
 assert output(phase+"-head")==b"56b4caafae1c0898b483717abed495f2e3b9281b\n"
 assert output(phase+"-status")==b""
 for i in range(6):
  c=commands[phase+"-blob-%02d"%i]
  ref=c["argv"][-1];head,rel=ref.split(":",1)
  assert head==r["context"]["source_sha"] and rel in before
  b=output(c["name"]);x=before[rel]
  assert len(b)==x["bytes"] and sha(b)==x["sha256"]
  oid=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
  assert output(phase+"-oid-%02d"%i)==(oid+"\n").encode() and oid==x["git_blob"]
  sourceproof[rel]={"git_blob":oid,"bytes":len(b),"sha256":sha(b),"actual_physical_tuple_before_after_equal":True}
assert r["primary_error"]=={"message":"container_bindings","type":"Refusal"} and r["status"]=="FAILED"
assert r["final_errors"]==[{"message":"compiler_container_cleanup_failed","phase":"owned_cleanup","type":"Refusal"}]
assert all(r[k]==0 for k in ("native_builds","native_tests","go_queries"))
assert r["consumer_admission"] is False and r["account_or_semantic_authority"] is False and r["destination_writes_permitted"] is False
assert set(r["containers"])=={"acquire"}
owned=r["containers"]["acquire"]
assert owned["creation_attempted"] is True
assert output("acquire-create")== (owned["cid"]+"\n").encode()
create=commands["acquire-create"]["argv"]
binds=[create[i+1] for i,x in enumerate(create) if x=="--volume"]
assert binds==owned["binds"] and len(binds)==len(set(binds))==2
states=[]
for name in ("acquire-inspect-before","acquire-cleanup-before"):
 inspected=json.loads(output(name),object_pairs_hook=unique)
 assert type(inspected) is list and len(inspected)==1
 info=inspected[0]
 assert info["Id"]==owned["cid"] and info["Name"]=="/"+owned["name"]
 actual=info["HostConfig"]["Binds"]
 assert type(actual) is list and actual==list(reversed(binds)) and sorted(actual)==sorted(binds)
 assert info["State"]["Status"]=="created" and info["State"]["Running"] is False and info["State"]["Pid"]==0 and info["State"]["StartedAt"]=="0001-01-01T00:00:00Z"
 expected_mounts=[{"Type":"bind","Source":x.rsplit(":",2)[0],"Destination":x.rsplit(":",2)[1],"Mode":x.rsplit(":",2)[2],"RW":x.rsplit(":",2)[2]=="rw","Propagation":"rprivate"} for x in binds]
 assert sorted(info["Mounts"],key=lambda x:x["Destination"])==sorted(expected_mounts,key=lambda x:x["Destination"])
 states.append({"original_command":name,"original_stdout":commands[name]["stdout"],"state":info["State"],"declared_binds":binds,"actual_binds":actual,"equal_as_ordered_list":False,"equal_as_complete_multiset":True,"exact_mount_rows":True})
assert not any("start" in c["argv"][1:3] for c in commands.values())
assert not any(name.startswith("install") or name.startswith("acquire-start") for name in commands)
cleanup=read(O/"cleanup.json")
assert len(cleanup)==1 and cleanup[0]["error"]=={"type":"Refusal","message":"container_bindings"}
result={"schema":"loaded-account-compiler-original-source-cause-audit-v1","status":"PASS_ORIGINAL_DIAGNOSIS","time_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"archive":{"path":str(ROOT/"original-14860902326.zip"),"bytes":328616,"sha256":"543e97bbd659ed25b78aad7eed340340524894051eebcd209328914c63545ddb","artifact_id":14860902326},"context":r["context"],"original_members_verified":114,"original_uncompressed_bytes":sum(x["bytes"] for x in m.values()),"original_command_count":36,"all_actual_commands_exit_zero":True,"all_owned_command_groups_observed_absent":True,"source_before_after_equal":True,"source_bindings":sourceproof,"loaded_before_after_equal":True,"loaded_source":r["loaded_source_before"],"host_tool_before_after_equal":True,"host_tools":r["host_tool_before"],"original_status":r["status"],"original_primary_error":r["primary_error"],"original_final_errors":r["final_errors"],"original_cleanup":cleanup,"container_observations":states,"cause":"The exact declared bind multiset was returned in reversed order; original check_container used ordered-list equality before acquire-start and again during cleanup.","container_not_started_as_of_original_inspections":True,"historical_cleanup_pass":False,"compiler_image_produced":False,"package_acquisition_started":False,"native_builds":0,"native_tests":0,"go_queries":0,"source_control_tests":0,"consumer_admission":False,"account_or_semantic_authority":False,"destination_writes_permitted":False,"resources_start":r["resources_start"],"resources_final":r["final_resources"],"audit_scope":"Read retained originals only; no CI API, artifact download, container, build or product execution."}
rr=save(A/"source-cause-audit.json",result)
print(json.dumps({"result":rr,"status":result["status"],"source_rows":len(sourceproof),"commands":len(commands),"producer_status":r["status"],"primary":r["primary_error"],"final":r["final_errors"]},sort_keys=True))
