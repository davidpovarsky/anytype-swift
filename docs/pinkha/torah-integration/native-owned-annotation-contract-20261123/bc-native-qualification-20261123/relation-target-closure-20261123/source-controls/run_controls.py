import copy,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
W=Path("/mnt/development/projects/worktrees/anytype-otzaria-file-native-metadata-20261124")
P=W/"docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/bc-native-qualification-20261123"
D=Path("/mnt/development/projects/diagnostics/otzaria-file-native-metadata-20261124/relation-source-controls")
D.mkdir(exist_ok=True)
assert not (D/"RESULT.json").exists()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
helper=P/"relation-target-closure-20261123/relation_target_controls.py"
unionpath=P/"rpc-union-20261123/source_union.py"
m=load("relation_target_controls",helper);u=load("native_source_union",unionpath)
assert sha(helper.read_bytes())=="4fa32bc721cbb84dda7616d4599e70ba2f4ec34652512095546eff94f1068e33"
assert sha(unionpath.read_bytes())=="e5c860e64bb83f6d501bfafc0e8c6ba192b437afa91c98cd62cdacd971452a86"
results=[]
def control(name,fn,expect_refusal=False):
 try:
  value=fn()
  if expect_refusal:raise AssertionError("tamper was accepted")
  assert value is not False
  results.append({"name":name,"status":"PASS","expectation":"REFUSAL" if expect_refusal else "ACCEPT"})
 except Exception as e:
  if expect_refusal and not (isinstance(e,AssertionError) and str(e)=="tamper was accepted"):
   results.append({"name":name,"status":"PASS","expectation":"REFUSAL","actual_error_type":type(e).__name__,"actual_error":str(e)})
  else:results.append({"name":name,"status":"FAIL","error_type":type(e).__name__,"error":str(e)})
with tempfile.TemporaryDirectory(prefix="relation-target-source-controls-",dir=D) as tmp:
 tmp=Path(tmp);log=tmp/"events.jsonl"
 names=[m.GROUP["parent"]]+[m.GROUP["parent"]+"/"+leaf for leaf in m.GROUP["leaves"]]
 events=[{"Action":a,"Package":m.PACKAGE,"Test":name} for name in names for a in ("run","pass")]
 events.append({"Action":"pass","Package":m.PACKAGE})
 def parsed(es,good=False):
  log.write_text("".join(json.dumps(e)+"\n" for e in es));r=m.case_intake(log)
  return r["status"]=="PASS" and r["leaf_pass"]==12 if good else r["status"]!="PASS"
 control("exact_twelve_unique_leaves_pass",lambda:parsed(events,True))
 control("empty_events_refused",lambda:parsed([]))
 for action in ["fail","skip"]:
  changed=copy.deepcopy(events);changed[3]["Action"]=action
  control("leaf_"+action+"_refused",lambda changed=changed:parsed(changed))
 for name,index in [("missing_leaf_run",2),("missing_leaf_terminal",3),("missing_parent_run",0),("missing_parent_terminal",1),("missing_package_terminal",len(events)-1)]:
  changed=copy.deepcopy(events);changed.pop(index)
  control(name+"_refused",lambda changed=changed:parsed(changed))
 for name,index in [("duplicate_leaf_run",2),("duplicate_leaf_pass",3),("duplicate_package_pass",len(events)-1)]:
  changed=copy.deepcopy(events);changed.append(copy.deepcopy(changed[index]))
  control(name+"_refused",lambda changed=changed:parsed(changed))
 changed=copy.deepcopy(events);changed[3]["Package"]="other"
 control("foreign_package_refused",lambda:parsed(changed))
 control("extra_test_refused",lambda:parsed(events+[{"Action":"pass","Package":m.PACKAGE,"Test":"Unexpected"}]))
 def malformed():
  log.write_text("not json\n");m.case_intake(log)
 control("malformed_event_refused",malformed,True)
 def nonobject():
  log.write_text("[]\n");m.case_intake(log)
 control("nonobject_event_refused",nonobject,True)
 real=tmp/"regular-events";real.write_text("{}\n")
 def aliased():
  log.unlink();log.symlink_to(real);m.case_intake(log)
 control("event_symlink_refused",aliased,True)
 if log.is_symlink():log.unlink()
 heart=tmp/"heart";heart.mkdir();work=tmp/"work";work.mkdir()
 binary=work/"schema-closure-controls/export.test";binary.parent.mkdir();binary.write_bytes(b"synthetic-source-guard-only")
 go="/owned/go"
 receipt={"argv":[go,"test","-c","-p","2","-o",str(binary),"./core/block/export"],"cwd":str(heart),"status":"TERMINAL","returncode":0,"effective_returncode":0,"timed_out":False,"start_new_session":True,"cleanup":[{"drained":True}]}
 record={"path":str(binary),"bytes":binary.stat().st_size,"sha256":sha(binary.read_bytes()),"package":m.PACKAGE,"compile_command":receipt}
 class Commands:pass
 def admit_record(row=None,items=None):
  commands=Commands();commands.items=items if items is not None else [receipt]
  return m.existing_export_binary(commands=commands,go=go,heart=heart,work=work,record=row or record)
 control("exact_current_compile_receipt_accepted",lambda:admit_record()==binary)
 for field,value in [("sha256","0"*64),("bytes",1),("package","other"),("path",str(work/"other.test"))]:
  bad=copy.deepcopy(record);bad[field]=value
  control("binary_"+field+"_mismatch_refused",lambda bad=bad:admit_record(bad),True)
 control("missing_owner_compile_receipt_refused",lambda:admit_record(items=[]),True)
 control("duplicate_owner_compile_receipt_refused",lambda:admit_record(items=[receipt,receipt]),True)
 for field,value in [("argv",["other"]),("cwd","/other"),("returncode",1),("effective_returncode",1),("timed_out",True),("start_new_session",False),("cleanup",[{"drained":False}])]:
  bad=copy.deepcopy(record);bad["compile_command"][field]=value
  control("compile_"+field+"_refused",lambda bad=bad:admit_record(bad,[bad["compile_command"]]),True)
 manifest=json.loads((P/"EXECUTION_INPUTS.json").read_text())
 def bound(relative,row,alter=None):
  raw=(P/relative).read_bytes()
  if alter is not None:raw=alter(relative,raw)
  assert len(raw)==row["bytes"] and sha(raw)==row["sha256"] and blob(raw)==row["git_blob"],"bound bytes differ"
  return raw
 def git(path,*args):return subprocess.check_output(["git","-C",str(path),*args])
 def target_admit(data=None,alter=None):
  return u.admit_relation_target(control=W,packet_name=str(P.relative_to(W)),manifest=data or manifest,
   bound=lambda relative,row:bound(relative,row,alter),safe=lambda root,relative:root/relative,git=git)
 control("actual_reviewed_target_overlay_admitted",lambda:len(target_admit()["inputs"])==2)
 bad=copy.deepcopy(manifest);bad["fresh_control_counts"]["relation_target"]=7
 control("wrong_fresh_count_refused",lambda:target_admit(bad),True)
 control("altered_afterimage_refused",lambda:target_admit(alter=lambda name,raw:raw+b"\n" if name.endswith("/native/core/block/export/collection.go") else raw),True)
 control("altered_previous_result_refused",lambda:target_admit(alter=lambda name,raw:raw.replace(b'"FAIL"',b'"PASS"') if name.endswith("/previous-run/RESULT.json") else raw),True)
 old=json.loads(git(W,"show","c6b4ebd03d25433b8a47073d84e2efa874c777ec:"+str((P/"EXECUTION_INPUTS.json").relative_to(W))))
 target=target_admit();creation=u.admit_imported_creation(control=W,packet_name=str(P.relative_to(W)),manifest=manifest,bound=bound,safe=lambda root,relative:root/relative,git=git);metadata=u.admit_bounded_native_metadata(control=W,packet_name=str(P.relative_to(W)),manifest=manifest,bound=bound,safe=lambda root,relative:root/relative,git=git);overlay={"overlays":target["inputs"]+creation["inputs"]+metadata["inputs"]}
 control("reviewed_target_and_creation_union_applied_exactly",lambda:u.expected_union(overlay,old["final_union_afterimages"],old["required_compiler_inputs"])==(manifest["final_union_afterimages"],manifest["required_compiler_inputs"]))
 wrong=copy.deepcopy(old["final_union_afterimages"]);wrong["core/block/export/collection.go"]="0"*64
 control("wrong_preceding_exporter_refused",lambda:u.expected_union(overlay,wrong,old["required_compiler_inputs"]),True)
 wrong=copy.deepcopy(old["final_union_afterimages"]);wrong["core/block/export/owned_annotation_relation_target_closure_test.go"]="0"*64
 control("new_test_path_collision_refused",lambda:u.expected_union(overlay,wrong,old["required_compiler_inputs"]),True)
report={"schema":1,"scope":"Synthetic source, event collector, current binary reuse and overlay admission controls only; no native compiler/execution and no generator/Swift replay",
 "sources":[{"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in [helper,unionpath]],
 "results":results,"counts":{s:sum(row["status"]==s for row in results) for s in ["PASS","FAIL"]},
 "native_execution":False,"status":"PASS" if all(row["status"]=="PASS" for row in results) else "FAIL"}
(D/"RESULT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":report["status"],"counts":report["counts"],"failures":[r for r in results if r["status"]!="PASS"],"result_sha256":sha((D/"RESULT.json").read_bytes())},indent=2))
