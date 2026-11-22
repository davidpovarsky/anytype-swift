import pathlib, subprocess, json, hashlib, io, datetime, sys
root=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
ref="18668c3ec0521871c6993add297dbb91ffa8bef3"
base="37f48119609747c01ee92cf597e4216f63b7bfa4"
prefix="docs/pinkha/torah-integration/original-auth-release-20261122"
pub="docs/pinkha/torah-integration/original-auth-release-publication-20261122"
prod="Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\auth-release-published-root-review\output-marker-continuation")
out.mkdir(exist_ok=False)
(out/"ACTUAL_ROOT_REVIEW.py").write_bytes(pathlib.Path(__file__).read_bytes())
def h(b): return hashlib.sha256(b).hexdigest()
def git(*a,inp=None):
 p=subprocess.run(["git","-C",str(root),*a],input=inp,capture_output=True,timeout=60)
 if p.returncode: raise RuntimeError(p.stderr.decode("utf-8","replace"))
 return p.stdout
try:
 names=git("diff","--name-only","-z",base,ref).decode().strip("\0").split("\0")
 assert len(names)==138 and all(p==".gitattributes" or p==prod or p.startswith(prefix+"/") or p.startswith(pub+"/") for p in names)
 tree=git("ls-tree","-rz",ref,"--",".gitattributes",prod,prefix,pub)
 entries={}
 for record in tree.split(b"\0"):
  if not record: continue
  metadata,name=record.split(b"\t",1); mode,kind,oid=metadata.decode().split()
  assert kind=="blob" and mode=="100644"
  entries[name.decode()]=oid
 assert set(entries)==set(names)
 data=git("cat-file","--batch",inp=("".join(oid+"\n" for oid in entries.values())).encode())
 stream=io.BytesIO(data); blobs={}
 for name,oid in entries.items():
  fields=stream.readline().decode().split()
  assert fields[0]==oid and fields[1]=="blob"
  raw=stream.read(int(fields[2])); assert stream.read(1)==b"\n"
  assert hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()==oid
  blobs[name]=raw
 assert not stream.read()
 get=lambda p:blobs[prefix+"/"+p]
 indexraw=get("EVIDENCE_INDEX.json")
 assert h(indexraw)=="cf221fcbce1d5cf0b3bfc2fbda64daa950a065ec19fe6d2fdfccd6290e2a654f"
 idx=json.loads(indexraw); listed={r["path"]:r for r in idx["files"]}
 assert len(listed)==121 and set(listed)=={n[len(prefix)+1:] for n in entries if n.startswith(prefix+"/") and not n.endswith("/EVIDENCE_INDEX.json")}
 for name,row in listed.items():
  raw=get(name);assert len(raw)==row["bytes"] and h(raw)==row["sha256"],name
 assert h(blobs[prod])=="65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e"
 assert blobs[prod]==get("repair-proposal-v1/EditorAccountWriteTransition.candidate.swift")
 assert get("repair-proposal-v1/EditorAccountWriteTransition.preimage.swift")==git("show",base+":"+prod)
 assert git("diff","--name-only",base,"15ea8755a4e1cebf63314ab415fd809fbe9e8e84").decode().strip()==prod
 actual=json.loads(get("execution-v2/RESULT.json"))
 assert h(get("execution-v2/RESULT.json"))=="b305575b52b0e2badcbfff4182d1dae367580964b6715179bdeed12acd903555"
 assert actual["status"]=="PASS" and actual["canonical_and_compiled_inputs_before"]==actual["canonical_and_compiled_inputs_after"]=="PASS"
 commands=actual["commands"]
 assert [c["label"] for c in commands]==["compiler-version","compile-six-new-controls","execute-six-new-controls"]
 for c in commands:
  assert c["exit_code"]==0 and c["timed_out"] is False and c["parent_reaped"] is True and c["pid"]>0 and c["status"]=="COMPLETED"
  for kind in ["stdout","stderr"]: assert h(get("execution-v2/"+c["label"]+"."+kind))==c[kind+"_sha256"]
 cases=actual["actual_cases"]
 expected=["immediateVerifiedRelease","admittedOriginalOperationMustDrain","concurrentWaiterCannotSkipReleaseEffects","otherClosingLeaseStillDeniesCapture","cancelledWaiterDoesNotReleaseNativeOperation","duplicateFinishCannotUpgradeVerification"]
 assert cases["status"]=="PASS" and cases["processID"]==commands[2]["pid"]==4420
 assert [c["name"] for c in cases["cases"]]==expected and all(c["status"]=="PASS" for c in cases["cases"])
 raw_stdout=get("execution-v2/execute-six-new-controls.stdout").decode()
 matching=[line[len("CONTROL_RESULT="):] for line in raw_stdout.splitlines() if line.startswith("CONTROL_RESULT=")]
 assert len(matching)==1 and json.loads(matching[0])==cases
 binary=get("execution-v2/original-account-transition-controls.exe")
 assert len(binary)==263168 and h(binary)==actual["binary_before_execution"]["sha256"]==actual["binary_after_execution_sha256"]=="ad8035e5118bee97ee39f3bc03c01c944c88fcd22dcc4d9e21949a99a6484366"
 for row in actual["actual_compiled_copies"]:
  name=pathlib.PureWindowsPath(row["path"]).name
  raw=get("execution-v2/compiled-inputs/"+name)
  assert len(raw)==row["bytes"] and h(raw)==row["sha256"]
  frozen=get("controls-v2/Controls.swift") if name=="Controls.swift" else get("controls-v2/compiled-inputs/"+name)
  assert raw==frozen
 assert get("execution-v2/ACTUAL_RUNNER.py")==get("controls-v2/run_controls.py")
 assert h(get("execution-v2/ACTUAL_RUNNER.py"))=="614b9bfe7e0699ca5eef6da7cb6014c796b45f31ec5386dca98f7f743c3ce91b"
 assert h(get("execution-v2/EXECUTION_INPUTS.json"))==actual["manifest_sha256"]=="aedafa37e322e06559d04b2fd6704bf369037c4332023a37cdff79e67a998644"
 assert h(get("execution-v2-launch/root-control-review/ROOT_REVIEW.json"))=="a721efa0539a9c04c8973970325234b4ebe13b9efc42cb0f66dd3864b8c44636"
 assert h(get("repair-proposal-v1/TRANSITION_WAITER_DRAFT.patch"))=="3de561dafa7e05446a2885f65a7ba1c6c096c1302aa235395e45c02aab084117"
 actual_origin=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122\execution-v2")
 copied=0
 for name in ["RESULT.json","ACTUAL_RUNNER.py","EXECUTION_INPUTS.json","original-account-transition-controls.exe",*[c["label"]+"."+k for c in commands for k in ["stdout","stderr"]],*["compiled-inputs/"+pathlib.PureWindowsPath(r["path"]).name for r in actual["actual_compiled_copies"]]]:
  assert (actual_origin/name).read_bytes()==get("execution-v2/"+name),name
  copied+=1
 attrs=blobs[".gitattributes"].decode()
 assert all(not ln.strip() or ln.startswith(prefix+"/") or ln.startswith(pub+"/") for ln in attrs.splitlines())
 bindings={n:{"git_blob":entries[n],"bytes":len(raw),"sha256":h(raw)} for n,raw in blobs.items()}
 (out/"GIT_BLOB_BINDINGS.json").write_bytes((json.dumps(bindings,indent=2,sort_keys=True)+"\n").encode())
 result={"status":"PASS","prior_read_only_review_failure":"Parent ROOT_REVIEW.json retained; checker expected CONTROL_RESULT plus space, actual frozen stdout has CONTROL_RESULT=. No product/control/evidence bytes changed and no controls rerun.","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":"15ea8755a4e1cebf63314ab415fd809fbe9e8e84","publication_head":ref,"product_sha256":h(blobs[prod]),"all_changed_git_blobs_verified":len(entries),"packet_payloads_verified":len(listed),"actual_origin_copies_verified":copied,"actual_result_sha256":h(get("execution-v2/RESULT.json")),"actual_cases":expected,"actual_executable_pid":4420,"actual_executable_sha256":h(binary),"all_three_commands_exit_zero":True,"root_source_and_control_reviews_reused":True,"new_tests_builds_downloads":0,"scope":"Original portable release completion only. Full Auth/LoginState/Hanlin decorator and StageB integration remain unqualified."}
except BaseException as e:
 result={"status":"FAIL","traceback":__import__("traceback").format_exc(),"observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"error":str(e),"type":type(e).__name__}
 (out/"ROOT_REVIEW.json").write_bytes((json.dumps(result,indent=2)+"\n").encode()); print(json.dumps(result));sys.exit(1)
(out/"ROOT_REVIEW.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
print(json.dumps({**result,"review_sha256":h((out/"ROOT_REVIEW.json").read_bytes())}))
