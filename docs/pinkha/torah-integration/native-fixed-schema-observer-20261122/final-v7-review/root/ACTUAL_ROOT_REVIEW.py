import pathlib,subprocess,json,hashlib,datetime,difflib,re,sys
p=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\controls-v7-r1")
root=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
head="d8ea2be0f42e51b35001c35509dd27c9035c3c66"
baseprefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
v6=baseprefix+"/controls-v6-r1";v5=baseprefix+"/candidate-v5"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v7-root-source-review")
out.mkdir(exist_ok=False);(out/"ACTUAL_ROOT_REVIEW.py").write_bytes(pathlib.Path(__file__).read_bytes())
def h(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(("blob "+str(len(x))+"\0").encode()+x).hexdigest()
def git(*a):
 q=subprocess.run(["git","-C",str(root),*a],capture_output=True,timeout=60)
 if q.returncode:raise RuntimeError(q.stderr.decode("utf-8","replace"))
 return q.stdout
def at(prefix,name):return git("show",head+":"+prefix+"/"+name)
try:
 assert git("rev-parse","HEAD").decode().strip()==head and not git("status","--porcelain=v1")
 raw=(p/"REVIEW_INDEX.json").read_bytes();assert h(raw)=="6cff458c0b945e755325d906add452e0b0fa676291f9391276dd8237c38d5e64"
 idx=json.loads(raw);files={r["path"]:r for r in idx["files"]}
 assert len(files)==idx["payload_count"]==112
 assert set(files)=={q.relative_to(p).as_posix() for q in p.rglob("*") if q.is_file() and q.name!="REVIEW_INDEX.json"}|{"v6-preimage/REVIEW_INDEX.json"}
 # The nested old index is payload; only the outer index is excluded.
 actual={q.relative_to(p).as_posix() for q in p.rglob("*") if q.is_file() and q!=p/"REVIEW_INDEX.json"}
 assert set(files)==actual
 for name,row in files.items():
  b=(p/name).read_bytes();assert len(b)==row["bytes"] and h(b)==row["sha256"],name
 manifest_raw=(p/"EXECUTION_INPUTS.json").read_bytes();assert h(manifest_raw)=="8b4306ca235e95a5990ddf9378755ca41aef5dffeba856bc2396c88b7b89e941"
 m=json.loads(manifest_raw)
 assert m["expected_cases"]=={"native":["ActualLocalZeroCounterAccepted","NativeComputedRemoteCounterAccepted"]}
 for row in m["control_inputs"]:
  raw=(p/row.get("retained_path",row["path"])).read_bytes()
  assert h(raw)==row["sha256"] and ("bytes" not in row or len(raw)==row["bytes"]),row["path"]
 originals={}
 for name in ["run_original_native_schema_controls.py","EXECUTION_INPUTS.json","PROPOSED_WORKFLOW.yml","REVIEW_INDEX.json","README.md","SOURCE_WRITTEN.json"]:
  frozen=(p/"v6-preimage"/name).read_bytes();canonical=at(v6,name)
  assert frozen==canonical,name
  originals[v6+"/"+name]={"git_blob":blob(canonical),"sha256":h(canonical),"bytes":len(canonical)}
 oldrunner=at(v6,"run_original_native_schema_controls.py").decode()
 replacements=json.loads((p/"V6_TO_V7_RUNNER_REPLACEMENTS.json").read_bytes())
 rebuilt=oldrunner
 for item in replacements:
  assert rebuilt.count(item["before"])==1
  rebuilt=rebuilt.replace(item["before"],item["after"],1)
 newrunner=(p/"run_original_native_schema_controls.py").read_bytes()
 assert rebuilt.encode()==newrunner and h(newrunner)=="78321fbd48e015874f08f5916663c2adf6ba59c95d2d76be5547062a21c0903b"
 srcraw=at(v5,"SOURCE_REVIEW_INDEX.json")
 assert h(srcraw)==m["source_index_sha256"]=="3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581"
 source_manifest=at(v5,"SOURCE_MANIFEST.json");assert h(source_manifest)==m["source_manifest_sha256"]
 sm=json.loads(source_manifest)
 product=[]
 for row in sm["candidate"]:
  path=row.get("retained_path","candidate/"+row["path"])
  original=at(v5,path);assert h(original)==row["sha256"] and len(original)==row["bytes"]
  if row["path"].endswith("/fixed_schema_replay.go"):
   old=at(v6,path);new=(p/path).read_bytes()
   assert old==new and h(new)=="fb2c8c245320efe002e4bbece3b38af572a33e262d22652f54388bb6391371c4"
   product.append({"path":row["path"],"sha256":h(new),"source":"unchanged exact published V6"})
  else:product.append({"path":row["path"],"sha256":h(original),"source":"unchanged exact published V5"})
  originals[v5+"/"+path]={"git_blob":blob(original),"sha256":h(original),"bytes":len(original)}
 for name in ["fixed_schema_native_fixture_test.go","fixed_schema_native_trace_test.go"]:
  rel="candidate/core/block/object/objectcreator/"+name
  assert at(v6,rel)==(p/rel).read_bytes()
 observer_rel="candidate/core/block/object/objectcreator/fixed_schema_native_observer_test.go"
 oldobs=at(v6,observer_rel);newobs=(p/observer_rel).read_bytes()
 oldlines,newlines=oldobs.splitlines(keepends=True),newobs.splitlines(keepends=True)
 changes=[]
 for tag,a,b,c,d in difflib.SequenceMatcher(a=oldlines,b=newlines,autojunk=False).get_opcodes():
  if tag=="equal":continue
  assert tag=="replace" and b-a==d-c==1
  assert oldlines[a]==b"\t\tf.observe(t, spc, definition, objectcreator.FixedSchemaPersistedMatch)\n"
  changes.append(newlines[c].decode().strip())
 assert changes==[
 "f.observeStableCounter(t, spc, definition, id, added.Added[0].Id, stored.SnapshotCounter)",
 "f.observeStableCounter(t, spc, definition, id, raw.Id, stored.SnapshotCounter)"]
 assert len(re.findall(rb'\tt.Run\("([^"]+)"',oldobs))==33
 recorder=(p/"candidate/core/block/object/objectcreator/fixed_schema_native_counter_observation_test.go").read_bytes()
 assert h(recorder)=="54041071214718844bcec0f8d4a6d8723d844d11bd30ca5129faeec87eab0078"
 trees=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v4-root-source-review")
 additionals=json.loads((p/"V7_ADDITIONAL_ORIGINAL_INPUTS.json").read_bytes())
 extra=[]
 for row in additionals:
  repo=row["repository"].split("/")[-1]
  treefile=trees/(repo+".immutable-tree.json");tree=json.loads(treefile.read_bytes())
  assert not tree["truncated"] and tree["sha"]==row["commit"]
  hits=[x for x in tree["tree"] if x["path"]==row["path"]]
  assert len(hits)==1 and hits[0]["type"]=="blob" and hits[0]["sha"]==row["git_blob"]
  raw=(p/row["retained_path"]).read_bytes()
  assert blob(raw)==row["git_blob"] and h(raw)==row["sha256"] and len(raw)==row["bytes"]
  extra.append({**row,"immutable_tree_receipt_sha256":h(treefile.read_bytes())})
 peer=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-heart-v7-counter-peer-review-20261122.json").read_bytes()
 assert h(peer)=="edba61bb5268c16060e823fba5e6a9ba6ac711bb2010817455c95d3c27055327"
 (out/"PEER_REVIEW.json").write_bytes(peer)
 workflow=(p/"PROPOSED_WORKFLOW.yml").read_text(encoding="utf-8")
 assert "controls-v7-r1" in workflow and "--execution-manifest-sha256 "+h(manifest_raw) in workflow
 assert "codex/otzaria-original-schema-native-20261122" in workflow and "cancel-in-progress: false" in workflow
 assert h((p/"prior-v6-actual/RESULT.json").read_bytes())==m["baseline_native_result_sha256"]
 assert h((p/"prior-v6-actual/ACTUAL_CASE_REVIEW.json").read_bytes())==m["baseline_actual_case_review_sha256"]
 assert m["baseline_run_id"]==45012913358 and m["baseline_control_head"]==head
 (out/"CANONICAL_GIT_BINDINGS.json").write_bytes((json.dumps(originals,indent=2,sort_keys=True)+"\n").encode())
 (out/"ADDITIONAL_ORIGINAL_BINDINGS.json").write_bytes((json.dumps(extra,indent=2)+"\n").encode())
 result={"status":"PASS_FOR_PREPARING_EXACT_TWO_CASE_COMMIT_NOT_A_CI_RESULT","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"baseline_head":head,"review_index_sha256":h((p/"REVIEW_INDEX.json").read_bytes()),"payloads_verified":len(files),"control_inputs_verified":len(m["control_inputs"]),"runner_exact_replacements_verified":len(replacements),"unchanged_product_files":product,"unchanged_other_test_bodies":31,"changed_case_calls":changes,"additional_original_git_blobs_verified":len(extra),"peer_review_sha256":h(peer),"execution_manifest_sha256":h(manifest_raw),"runner_sha256":h(newrunner),"recorder_sha256":h(recorder),"root_full_source_review":"Complete new recorder, complete V6-to-V7 runner delta, workflow and runner caller closure, two exact test call substitutions; original native API/transaction/delegation peer review retained.","new_go_compiler_native_runs_downloads":0,"next":"Owner may package/commit exact V7R1 with immutable root proof; root binds final Git head before one two-case trigger. No strict12, first13 or V6passed18 replay."}
except BaseException as e:
 result={"status":"FAIL","error":str(e),"type":type(e).__name__,"traceback":__import__("traceback").format_exc()}
 (out/"ROOT_REVIEW.json").write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps(result));sys.exit(1)
(out/"ROOT_REVIEW.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
print(json.dumps({**result,"root_review_sha256":h((out/"ROOT_REVIEW.json").read_bytes())}))
