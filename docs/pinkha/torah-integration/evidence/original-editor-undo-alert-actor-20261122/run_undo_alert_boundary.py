import pathlib,subprocess,json,hashlib,os,datetime,re,struct,xml.etree.ElementTree as ET
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122")
package=out/"semantic-package";tests=package/"Tests/UndoAlertBoundary"
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.parent/"swift.EXE";runtime=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
def sha(b):return hashlib.sha256(b).hexdigest()
assert not (out/"SEMANTIC_EXECUTION.json").exists(),"Do not repeat execution"
assert sha((out/"SEMANTIC_INPUTS.json").read_bytes())=="c59911d8388694fd1337df5de6ebb5c1076fe4dbeb1b83328be70ca793dd2093"
inputs=json.loads((out/"SEMANTIC_INPUTS.json").read_bytes())
def verify():
 for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"],item["path"]
 for item in inputs["original_inputs"]:assert sha((out/item["snapshot"]).read_bytes())==item["sha256"],item["path"]
 assert sha((out/"OriginalAlertModel.RED.swift").read_bytes())==inputs["red_model_sha256"]
 assert sha((out/"AlertModel.candidate.swift").read_bytes())==inputs["candidate_sha256"]
 assert sha((out/"ALERT_CALLBACK_ACTOR.patch").read_bytes())==inputs["patch_sha256"]
 assert sha((package/"Package.swift").read_bytes())==inputs["package_sha256"]
verify()
env=dict(os.environ);env["PATH"]=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get("PATH","");env["PYTHONUTF8"]="1"
execution={"schema":1,"wrapper_pid":os.getpid(),"inputs_sha256":sha((out/"SEMANTIC_INPUTS.json").read_bytes()),"runner_sha256":sha(pathlib.Path(__file__).read_bytes()),"commands":[]}
def persist():(out/"SEMANTIC_EXECUTION.json").write_text(json.dumps(execution,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout,expect_nonzero=False):
 row={"label":label,"command":list(map(str,args)),"cwd":str(out),"wrapper_pid":os.getpid(),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"timeout_seconds":timeout,"phase":"STARTING"}
 execution["commands"].append(row);persist()
 with (out/(label+".stdout.log")).open("wb") as so,(out/(label+".stderr.log")).open("wb") as se:
  child=subprocess.Popen(list(map(str,args)),cwd=out,env=env,stdout=so,stderr=se);row["child_pid"]=child.pid;row["phase"]="RUNNING";persist()
  try:row["returncode"]=child.wait(timeout=timeout);row["timed_out"]=False
  except subprocess.TimeoutExpired:
   row["timed_out"]=True
   if child.poll() is None:
    kill=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=30)
    row["owned_cleanup"]={"exit":kill.returncode,"stdout":kill.stdout.decode(errors="replace"),"stderr":kill.stderr.decode(errors="replace")}
   try:row["returncode"]=child.wait(timeout=30)
   except subprocess.TimeoutExpired:row["returncode"]=None
 row["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();row["phase"]="TERMINAL" if row.get("returncode") is not None else "UNRESOLVED_NO_RETRY"
 for stream in ("stdout","stderr"):row[stream+"_sha256"]=sha((out/(label+"."+stream+".log")).read_bytes())
 verify();row["all_inputs_unchanged"]=True;persist()
 successful=(row["returncode"]!=0 if expect_nonzero else row["returncode"]==0) and row["returncode"] is not None and not row["timed_out"]
 if not successful:
  print(json.dumps({"status":"ACTUAL_INPUT_FAILURE_PRESERVED","record":row,"stdout":(out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")[-6000:],"stderr":(out/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace")[-16000:]}));raise SystemExit(1)
 return row
red=run("expected-old-undo-alert-actor-error",[swiftc,"-typecheck","-parse-as-library","-module-name","OriginalUndoAlertRed","-swift-version","5","-strict-concurrency=complete","-module-cache-path",inputs["module_cache"],tests/"DependencyProbes.swift",out/"OriginalAlertModel.RED.swift",tests/"OriginalScheduler.swift",tests/"OriginalShake.swift"],120,expect_nonzero=True)
error_lines=[x for x in (out/"expected-old-undo-alert-actor-error.stderr.log").read_text(encoding="utf8",errors="replace").splitlines() if re.search(r"\.swift:\d+:\d+: error:",x)]
red_proof={"record":red,"errors":error_lines,"required_error":"call to main actor-isolated instance method 'scheduleMutationTask(operation:)' in a synchronous nonisolated context"}
(out/"EXPECTED_OLD_ERROR.json").write_text(json.dumps(red_proof,indent=2)+"\n",encoding="utf8")
assert len(error_lines)==1 and "OriginalShake.swift:" in error_lines[0] and red_proof["required_error"] in error_lines[0],error_lines
run("complete-alert-model-syntax",[swiftc,"-frontend","-parse",out/"AlertModel.candidate.swift"],90)
run("swift-testing-new-undo-alert-boundary",[swift,"test","--verbose","--package-path",package,"--scratch-path",package/".build","--enable-swift-testing","--disable-xctest","--xunit-output",out/"SEMANTIC_TEST_RESULTS.xml","-Xswiftc","-strict-concurrency=complete","-Xswiftc","-module-cache-path","-Xswiftc",inputs["module_cache"]],480)
xml=out/"SEMANTIC_TEST_RESULTS.xml";cases=ET.parse(xml).findall(".//testcase")
assert len(cases)==2 and {x.attrib["name"].removesuffix("()") for x in cases}==set(inputs["expected_tests"])
assert all(not list(x) for x in cases)
binaries=list((package/".build").rglob("OriginalUndoAlertActorBoundaryPackageTests.xctest"));assert len(binaries)==1
binary=binaries[0];data=binary.read_bytes();assert data[:2]==b"MZ";pe=struct.unpack_from("<I",data,0x3c)[0];assert data[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",data,pe+4)[0]==0x8664
combined=(out/"swift-testing-new-undo-alert-boundary.stdout.log").read_text(encoding="utf-8",errors="replace")+"\n"+(out/"swift-testing-new-undo-alert-boundary.stderr.log").read_text(encoding="utf-8",errors="replace")
assert binary.name in combined
verify()
result={"schema":1,"status":"PASS_EXPECTED_OLD_ACTOR_ERROR_AND_TWO_NEW_UNDO_ALERT_BOUNDARY_GROUPS","candidate_sha256":inputs["candidate_sha256"],"inputs_sha256":sha((out/"SEMANTIC_INPUTS.json").read_bytes()),"expected_red_errors":error_lines,"expected_red_exit":red["returncode"],"new_tests":2,"tests":[x.attrib for x in cases],"xunit_sha256":sha(xml.read_bytes()),"binary":{"path":str(binary.relative_to(out)),"sha256":sha(data),"bytes":len(data)},"all_inputs_unchanged":True,"limits":inputs["limits"]}
(out/"SEMANTIC_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":result,"execution":execution}))
