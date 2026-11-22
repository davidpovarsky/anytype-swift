from pathlib import Path
import hashlib,json,subprocess,io,datetime
B=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
D=B/"controls-v5-r2";V=B/"candidate-v5";OLD=B/"controls-v5-r1"
H=Path(r"C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122")
A=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
OUT=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-root-controls-review")
assert not OUT.exists()
OUT.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def wr(p,v):p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+"\n").encode())
def cmd(repo,*args,input=None):
 p=subprocess.run(["git","-c","core.autocrlf=false",*args],cwd=repo,input=input,capture_output=True,timeout=45)
 assert p.returncode==0,(args,p.returncode,p.stderr.decode(errors="replace"))
 return p.stdout
def inventory(root,index_name,index_hash):
 raw=(root/index_name).read_bytes();assert sha(raw)==index_hash,(root,index_name)
 idx=json.loads(raw);rows=idx["files"]
 assert len({x["path"] for x in rows})==len(rows)
 expected={x["path"] for x in rows}
 assert expected|{index_name}=={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
 for e in rows:
  p=root/e["path"];assert p.resolve().is_relative_to(root.resolve()) and p.is_file() and not p.is_symlink()
  b=p.read_bytes();assert len(b)==e["bytes"] and sha(b)==e["sha256"],e["path"]
 return idx,rows
result={"schema":"otzaria.heart-v5-r2-root-control-source-review/1","status":"REVIEW_IN_PROGRESS","go_tests":0,"builds":0,"native_calls":0,"patch_applies":0,"downloads":0}
try:
 idx,rows=inventory(D,"REVIEW_INDEX.json","c8a125a81915b88b5da80f62f9cb7758d777630a652c501de0c24171f9d94e61")
 assert len(rows)==112 and sum(x["bytes"] for x in rows)==1944458
 vi,vrows=inventory(V,"SOURCE_REVIEW_INDEX.json","3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581")
 assert len(vrows)==138
 assert "SOURCE_MANIFEST.json" in {x["path"] for x in vrows}
 oldidx,oldrows=inventory(OLD,"REVIEW_INDEX.json","32343ff46151b027c8e8d6c81da26bda2f3941712dbc8e05f944c8bbb762c474")
 assert len(oldrows)==39
 assert (D/"R1_REVIEW_INDEX.json").read_bytes()==(OLD/"REVIEW_INDEX.json").read_bytes()
 m=read(D/"EXECUTION_INPUTS.json");sm=read(V/"SOURCE_MANIFEST.json")
 assert sha((D/"EXECUTION_INPUTS.json").read_bytes())=="0a9751cb534c184e35ee166ef6b1aff9d2756ab2cd3c2a20b20f9e0d7b25f792"
 assert m["source_manifest_sha256"]==sha((V/"SOURCE_MANIFEST.json").read_bytes())
 assert len(sm["candidate"])==5 and len(m["test_sources"])==4
 for e in m["control_inputs"]:
  p=D/e.get("retained_path",e["path"]);raw=p.read_bytes()
  assert sha(raw)==e["sha256"] and len(raw)==e["bytes"]
  if "commit" in e:
   repo=A if "anytype-swift" in e["repository"] else H
   original=cmd(repo,"show",e["commit"]+":"+e["path"])
   assert raw==original
   assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==e["git_blob"]
 for e in m["test_sources"]:
  raw=(D/e["retained_path"]).read_bytes()
  assert raw==(OLD/e["retained_path"]).read_bytes()
  assert raw==(H/e["path"]).read_bytes()
 for e in sm["candidate"]:
  assert sha((H/e["path"]).read_bytes())==e["sha256"]
 rootreview=D/"reviews/root-v5-source/ROOT_SOURCE_REVIEW.json"
 assert sha(rootreview.read_bytes())=="98f4aa277f9ee9ca3ca67eb6b7ca1fa612bac4ffd84adb8c273296ce91d08963"
 assert rootreview.read_bytes()==Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-root-source-review\ROOT_SOURCE_REVIEW.json").read_bytes()
 app=(D/"reviews/original/any-sync/app/app.go").read_bytes()
 tree=read(D/"reviews/root-v5-source/any-sync.immutable-tree.json")
 assert isinstance(tree,dict) and "tree" in tree
 appblob=next(x["sha"] for x in tree["tree"] if x["path"]=="app/app.go" and x["type"]=="blob")
 assert hashlib.sha1(b"blob "+str(len(app)).encode()+b"\0"+app).hexdigest()==appblob
 C=D/"source-composition";cr=read(C/"RESULT.json")
 assert sha((C/"RESULT.json").read_bytes())=="ca0079ab0011603e2e707fcf3d1638749f9e19dd2b118445db409cb92893f7f5"
 assert cr["status"]=="PASS_SOURCE_COMPOSITION_ONLY" and cr["base"]==m["heart_base"]
 assert cr["execution_manifest_sha256"]==sha((D/"EXECUTION_INPUTS.json").read_bytes())
 assert all(cr[x]==0 for x in ("builds","tests","native_calls","go_invocations"))
 originals=read(C/"ORIGINAL_BLOBS.json");assert len(originals)==21
 paths=[e["path"] for e in originals]
 rawtree=cmd(H,"ls-tree","-r","-z",m["heart_base"],"--",*paths)
 actualtree={}
 for raw in rawtree.split(b"\0"):
  if not raw:continue
  meta,path=raw.split(b"\t",1);mode,kind,oid=meta.decode().split()
  assert mode=="100644" and kind=="blob";actualtree[path.decode()]=oid
 assert set(actualtree)==set(paths)
 batch=cmd(H,"cat-file","--batch",input=("\n".join(m["heart_base"]+":"+p for p in paths)+"\n").encode())
 stream=io.BytesIO(batch)
 for e in originals:
  header=stream.readline().decode().split();assert header[:2]==[actualtree[e["path"]],"blob"]
  raw=stream.read(int(header[2]));assert stream.read(1)==b"\n"
  assert sha(raw)==e["sha256"] and len(raw)==e["bytes"] and header[0]==e["git_blob"]
 assert not stream.read()
 identity=read(C/"SCRIPT_IDENTITY.json")
 actualscript=Path(identity["actual_path"]).read_bytes()
 assert sha(actualscript)==identity["actual_sha256"]=="0fbccc4c7342bfb582cc1af3c5ac861f212a8222225c2b30537dc7d25e3066c2"
 assert actualscript==(C/"EXECUTED_SCRIPT.py").read_bytes()
 assert actualscript.replace(b"\r\n",b"\n")==(C/"SUBMITTED_SCRIPT.py").read_bytes()
 commands=read(C/"COMMANDS.json")
 assert len(commands)==7
 for e in commands:
  assert e["phase"]=="TERMINAL" and e["returncode"]==0 and not e.get("timed_out")
  assert e["pid"]>0 and e["finished"]>=e["started"]
  for streamname in ("stdout","stderr"):
   assert sha((C/e[streamname]).read_bytes())==e[streamname+"_sha256"]
 sr=read(C/"SENTINEL_RESULT.json")["job"]
 assert sr["id"]=="job_f2d920e21a43" and sr["status"]=="succeeded" and sr["exit_code"]==0
 assert json.loads(sr["output"])["result_sha256"]==sha((C/"RESULT.json").read_bytes())
 inv=read(D/m["r14_inventory"]["retained_path"])
 expected={}
 for e in inv["files"]:
  expected[e["path"]]=e["after_sha256"]
 assert len(expected)==35
 for e in sm["candidate"]+m["test_sources"]:
  assert e["path"] not in expected;expected[e["path"]]=e["sha256"]
 for p,s in m["original_module_hashes"].items():
  assert p not in expected;expected[p]=s
 assert len(expected)==47
 assert set(expected)=={p.relative_to(C/"materialized").as_posix() for p in (C/"materialized").rglob("*") if p.is_file()}
 for p,s in expected.items():assert sha((C/"materialized"/p).read_bytes())==s,p
 assert len(cr["r14_outputs"])==35 and len(cr["v5_outputs"])==5 and len(cr["test_outputs"])==4
 for e in cr["r14_outputs"]+cr["v5_outputs"]+cr["test_outputs"]:
  assert expected[e["path"]]==e["sha256"]
  assert (C/"materialized"/e["path"]).stat().st_size==e["bytes"]
 for kind,n in [("native",33),("strict",12)]:
  assert len(m["expected_cases"][kind])==len(set(m["expected_cases"][kind]))==n
 result.update({"status":"PASS_FROZEN_CONTROLS_AND_SOURCE_COMPOSITION_REVIEW_NO_EXECUTION",
 "utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "controls_index_sha256":sha((D/"REVIEW_INDEX.json").read_bytes()),"controls_payloads":112,"controls_bytes":1944458,
 "source_payloads_preserved":138,"source_manifest_sha256":sha((V/"SOURCE_MANIFEST.json").read_bytes()),
 "previous_r1_payloads_preserved":39,"unchanged_reviewed_tests":4,"unchanged_working_product_inputs":5,
 "new_immutable_control_source_inputs":sum("commit" in e for e in m["control_inputs"]),
 "additional_any_sync_original_blob":appblob,"composition_original_blobs":21,"composition_outputs":47,
 "composition_commands":7,"composition_result_sha256":sha((C/"RESULT.json").read_bytes()),
 "actual_source_composition_script_sha256":sha(actualscript),"runner_sha256":sha((D/"run_original_native_schema_controls.py").read_bytes()),
 "setup_child_sha256":sha((D/"prepare_original_tantivy.py").read_bytes()),"workflow_sha256":sha((D/"PROPOSED_WORKFLOW.yml").read_bytes()),
 "full_runner_workflow_setup_manifest_read":True,
 "expected_cases":{"native":33,"strict":12},
 "limits":["No Go build/test/native execution performed or replayed.",
 "The source composition is an affected-file materialization, not a compiled repository.",
 "Exact case execution, actual native source closure/library hashes and binary pre/post runner attestations remain future CI observations.",
 "Final reviewed Git control checkout and complementary R2 process review are required before one push."]})
except BaseException as error:
 result.update({"status":"FAIL_ROOT_REVIEW","error_type":type(error).__name__,"error":str(error)})
 wr(OUT/"ROOT_CONTROL_REVIEW.json",result)
 (OUT/"EXECUTED_ROOT_REVIEW.py").write_bytes(Path(__file__).read_bytes())
 print(json.dumps(result));raise
wr(OUT/"ROOT_CONTROL_REVIEW.json",result)
(OUT/"EXECUTED_ROOT_REVIEW.py").write_bytes(Path(__file__).read_bytes())
print(json.dumps({"status":result["status"],"path":str(OUT),"receipt_sha256":sha((OUT/"ROOT_CONTROL_REVIEW.json").read_bytes()),"payloads":112,"original_composition_blobs":21,"materialized_outputs":47,"new_execution":0}))
