import pathlib,json,hashlib,subprocess,ast,re,datetime,difflib,traceback
FAILED=json.loads("[\"ActualLocalZeroCounterAccepted\",\"ArchiveUsesOriginalNativeLinkTree\",\"ExactNativeRootOnly\",\"ExplicitLongtextPresenceCannotDefault\",\"FullACLIntermediateRecordRequired\",\"NativeComputedRemoteCounterAccepted\",\"NativeLocalMissingWithoutCreation\",\"OlderNativeCommonSnapshotAccepted\",\"OriginalACLSignatureCIDVerification\",\"OriginalObjectTypeMatch\",\"OriginalPooledReaderAndACLLockOrder\",\"OriginalRelationMatch\",\"SecondSnapshotSeesCompleteSettingsRootRowChange\",\"SecondSnapshotSeesCompleteStateRowChange\",\"SecondSnapshotSeesExtraNonHeadChange\",\"SecondSnapshotSeesInvisibleEncodedRowChange\"]")

B=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
D=B/"controls-v6-r1";R2=B/"controls-v5-r2";V=B/"candidate-v5"
H=pathlib.Path(r"C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122")
E=B/"execution-382e5ac6/artifact-intake-01/extracted"
O=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v6-root-controls-review")
assert not O.exists();O.mkdir(parents=True)
(O/"ACTUAL_ROOT_REVIEW.py").write_bytes(pathlib.Path(__file__).read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_bytes())
def git(*a):
 p=subprocess.run(["git","-c","core.autocrlf=false",*a],cwd=H,capture_output=True,timeout=30);p.check_returncode();return p.stdout
result={"schema":1,"status":"STARTED","review_started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"tests_executed":0,"artifact_downloads":0,"source_mutations":0}
try:
 assert sha((D/"REVIEW_INDEX.json").read_bytes())=="a1eed44cfbc80089ae97868d5cec16728f8c482879944824635a8d3531c04ca9"
 idx=j(D/"REVIEW_INDEX.json");assert len(idx["files"])==idx["payload_count"]==73
 paths=set()
 for x in idx["files"]:
  p=pathlib.PurePosixPath(x["path"]);assert not p.is_absolute() and ".." not in p.parts
  b=(D/x["path"]).read_bytes();assert len(b)==x["bytes"] and sha(b)==x["sha256"],x["path"];paths.add(x["path"])
 assert len(paths)==73 and {p.relative_to(D).as_posix()for p in D.rglob("*")if p.is_file()}==paths|{"REVIEW_INDEX.json"}
 m=j(D/"EXECUTION_INPUTS.json")
 assert sha((D/"EXECUTION_INPUTS.json").read_bytes())=="dc843c2a08a1a55fc96ebe822f2c6e70b3c46bf83edd248266761a1cda8137e7"
 for x in m["control_inputs"]:
  b=(D/x.get("retained_path",x["path"])).read_bytes()
  assert len(b)==x["bytes"] and sha(b)==x["sha256"],x["path"]
 assert sha((R2/"REVIEW_INDEX.json").read_bytes())=="c8a125a81915b88b5da80f62f9cb7758d777630a652c501de0c24171f9d94e61"
 r2idx=j(R2/"REVIEW_INDEX.json")
 tree_rel="reviews/root-v5-source/any-sync.immutable-tree.json"
 tree_row=next(x for x in r2idx["files"] if x["path"]==tree_rel)
 assert sha((R2/tree_rel).read_bytes())==tree_row["sha256"]
 tree=j(R2/tree_rel);assert not tree.get("truncated",False)
 members={x["path"]:x["sha"]for x in tree["tree"]if x["type"]=="blob"}
 original=j(D/"ADDITIONAL_ORIGINAL_INPUTS.json")
 assert len(original["inputs"])==16
 for x in original["inputs"]:
  b=(D/x["retained_path"]).read_bytes()
  assert sha(b)==x["sha256"] and len(b)==x["bytes"]
  blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
  assert blob==x["git_blob"]
  if x["repository"]=="anyproto/any-sync":assert members[x["path"]]==blob
  else:assert git("show",x["commit"]+":"+x["path"])==b
 old_runner=(R2/"run_original_native_schema_controls.py").read_bytes()
 assert sha(old_runner)=="e9cebdaac6326374098db331bfe1b05e2d3141a0c1759d77897cb5d1ac83a1e1"
 revised=old_runner.decode("utf-8")
 replacements=j(D/"R2_TO_V6_RUNNER_REPLACEMENTS.json");assert len(replacements)==9
 for x in replacements:
  assert revised.count(x["old"])==1,x["old"];revised=revised.replace(x["old"],x["new"],1)
 runner=(D/"run_original_native_schema_controls.py").read_bytes()
 assert revised.encode("utf-8")==runner and sha(runner)=="de9b69ff773602a22042489fde5e1901bc9639315b623a072ae9f3e05d8225c7"
 ast.parse(runner.decode("utf-8"))
 assert (D/"prepare_original_tantivy.py").read_bytes()==(R2/"prepare_original_tantivy.py").read_bytes()
 assert sha((V/"SOURCE_MANIFEST.json").read_bytes())==m["source_manifest_sha256"]
 assert sha((V/"SOURCE_REVIEW_INDEX.json").read_bytes())==m["source_index_sha256"]
 baseline=j(E/"RESULT.json");assert sha((E/"RESULT.json").read_bytes())=="4c1f27019674c4ddd9a1198f933e71e02d2452e93f3cbc1cdfbf1dc7a932aaab"
 native_log=list(E.rglob("13-run-native.stdout"));assert len(native_log)==1
 assert sha(native_log[0].read_bytes())==m["baseline_native_event_sha256"]
 terminals={}
 for line in native_log[0].read_text(encoding="utf-8").splitlines():
  event=json.loads(line)
  if event.get("Action") in ["pass","fail","skip"] and "/" in event.get("Test",""):
   name=event["Test"].split("/",1)[1];assert name not in terminals;terminals[name]=event["Action"]
 assert len(terminals)==33 and list(terminals.values()).count("fail")==16 and list(terminals.values()).count("pass")==17
 assert set(FAILED)=={n for n,s in terminals.items()if s=="fail"}
 mapping=j(D/"PASS_FIRST_FAILURE_MAP.json")
 assert mapping["native_event_sha256"]==m["baseline_native_event_sha256"] and len(mapping["mapping"])==17
 assert {x["name"]for x in mapping["mapping"]}=={n for n,s in terminals.items()if s=="pass"}
 masked={x["name"]for x in mapping["mapping"]if x["replay_selected"]};assert len(masked)==4
 selected=set(m["expected_cases"]["native"]);assert len(selected)==20 and selected==set(FAILED)|masked
 assert set(m["expected_cases"])=={"native"} and m["prior_cases_not_replayed"]=={"native":13,"strict":12}
 assert len(m["test_sources"])==3 and all("strict" not in x["path"]for x in m["test_sources"])
 native_path="core/block/object/objectcreator/fixed_schema_native_observer_test.go"
 old=(R2/"candidate"/native_path).read_text(encoding="utf-8")
 new=(D/"candidate"/native_path).read_text(encoding="utf-8")
 pattern=r'(?ms)^\tt\.Run\("([^"]+)", func\(t \*testing\.T\) \{\n.*?^\t\}\)'
 old_cases={z.group(1):z.group(0)for z in re.finditer(pattern,old)}
 new_cases={z.group(1):z.group(0)for z in re.finditer(pattern,new)}
 assert len(old_cases)==len(new_cases)==33 and set(old_cases)==set(new_cases)==set(terminals)
 changed={n for n in old_cases if old_cases[n]!=new_cases[n]}
 assert changed==masked|{"FullACLIntermediateRecordRequired","OriginalACLSignatureCIDVerification"}
 ancestry=j(D/"CONTROL_ANCESTRY.json")
 assert ancestry["unchanged_body_count"]==27 and ancestry["selected_count"]==20
 proof=D/"source-composition/delta-composition-v6-r1-lf"
 composition=j(proof/"RESULT.json");assert composition["status"]=="PASS_SOURCE_COMPOSITION_ONLY" and len(composition["outputs"])==8
 actual={x["path"]:x for x in baseline["composed_product_and_test_inputs"]}
 for x in composition["baseline_actual_product_inputs"]:assert x==actual[x["path"]]
 expected={x["path"]:x["sha256"]for x in composition["baseline_actual_product_inputs"]}
 expected[m["observer_product_delta"][0]["path"]]=m["observer_product_delta"][0]["sha256"]
 expected.update({x["path"]:x["sha256"]for x in m["test_sources"]})
 for x in composition["outputs"]:
  b=(proof/"materialized"/x["path"]).read_bytes()
  assert len(b)==x["bytes"] and sha(b)==x["sha256"]==expected[x["path"]]
 commands=j(proof/"COMMANDS.json");assert len(commands)==2 and commands==composition["commands"]
 for x in commands:
  assert x["exit_code"]==0 and x["argv"][:5]==["git","-c","core.autocrlf=false","-c","core.eol=lf"]
  for stream in ["stdout","stderr"]:assert sha((proof/x[stream]).read_bytes())==x[stream+"_sha256"]
 wrong=D/"source-composition/delta-composition-v6-r1/materialized/core/block/object/objectcreator/fixed_schema_replay.go"
 assert sha(wrong.read_bytes())=="42e3ca4de030dc219e9f0260ac49b72319fa926e7a96106d22d60fed3b5b49bd"
 assert wrong.read_bytes().replace(b"\r\n",b"\n")==(D/"candidate/core/block/object/objectcreator/fixed_schema_replay.go").read_bytes()
 script=(proof/"EXECUTED_SCRIPT.py").read_text(encoding="utf-8")
 assert 'source=json.loads((base/"candidate-v5"/"SOURCE_MANIFEST.json").read_text())' in script
 assert "core.autocrlf=false" in script and "core.eol=lf" in script
 workflow=(D/"PROPOSED_WORKFLOW.yml").read_text(encoding="utf-8")
 assert m["heart_base"] in workflow and sha((D/"EXECUTION_INPUTS.json").read_bytes()) in workflow
 assert "Build and execute only 20 unresolved native cases" in workflow and "persist-credentials: false" in workflow and "cancel-in-progress: false" in workflow
 result.update(status="PASS_FOR_FINAL_GIT_SEAL",payloads=73,payload_bytes=sum(x["bytes"]for x in idx["files"]),review_index_sha256=sha((D/"REVIEW_INDEX.json").read_bytes()),original_inputs_independently_verified=16,any_sync_originals_verified_against_retained_immutable_tree=14,heart_original_git_blobs_verified=2,runner_exact_replacements=9,runner_lifecycle_unchanged_from_reviewed_R2=True,original_test_cases=33,unchanged_case_bodies=27,strengthened_negative_cases=6,selected_cases=sorted(selected),strict_cases_not_replayed=12,unaffected_native_cases_not_replayed=13,actual_prior_native_events_rehashed_and_counted=True,composition_outputs_verified=8,local_line_ending_failure_preserved=True,peer_localonly_review_sha256="488f11415c434e1bf927367f1da5cabb486b326fcd453d8668b7d9c94e4e1129",limitations=["Four masked prior passes remain unproven until corrected execution; 13 reuse paths are explicitly source-constrained or cause-asserted, not newly traced.","Original LocalOnly ACL ingestion retains native author/CID/state/storage validation but does not establish remote consensus acceptance.","No Go/native/Swift/test/sourceapply or network fetch performed by root review; final Git commit binding still required before one push."])
except Exception:result.update(status="FAIL",error=traceback.format_exc())
finally:
 result["review_finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 b=(json.dumps(result,indent=2)+"\n").encode();(O/"ROOT_REVIEW.json").write_bytes(b)
 print(json.dumps({"receipt":str(O/"ROOT_REVIEW.json"),"sha256":sha(b),"result":result}))
if result["status"]!="PASS_FOR_FINAL_GIT_SEAL":raise SystemExit(1)
