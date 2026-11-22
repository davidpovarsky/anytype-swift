import pathlib,subprocess,json,hashlib,os,datetime,xml.etree.ElementTree as ET,struct
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-selected-space-20261122")
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.parent/"swift.EXE"
runtime=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
def sha(data):return hashlib.sha256(data).hexdigest()
assert not (out/"EXECUTION.json").exists(),"First actual execution exists; inspect it instead of replay"
assert sha((out/"INPUTS.json").read_bytes())=="ef6b5d2758ad78da46e6c152f16d41f050ff478832b41e0cb4db618ed53b0f69"
assert sha(swiftc.read_bytes())=="e1d0a0b20d95a92b22f4906e7ca331a7c8b89be86b2d9a2d215ac24f753e945a"
inputs=json.loads((out/"INPUTS.json").read_bytes())
def verify_inputs():
 for item in inputs["compiled_inputs"]:
  assert sha((out/item["path"]).read_bytes())==item["sha256"],item["path"]
 for item in inputs["original_inputs"]:
  assert sha((out/item["saved_path"]).read_bytes())==item["sha256"],item["path"]
 for item in inputs["product_candidates"]:
  assert sha((out/item["saved_path"]).read_bytes())==item["canonical_sha256"],item["saved_path"]
 for key in ("package","projection_map","preparation","fixture_revision"):
  item=inputs[key];assert sha((out/item["path"]).read_bytes())==item["sha256"],item["path"]
 actual={p.relative_to(out).as_posix() for p in (out/"Tests").rglob("*.swift")}
 assert actual=={item["path"] for item in inputs["compiled_inputs"]},"Unbound or missing test source"
 assert (out/"Tests/SelectedSpaceControls/Controls.swift").read_text(encoding="utf-8").count("@Test @MainActor")==10
verify_inputs()
p=subprocess.run(["git","rev-parse","HEAD"],cwd=repo,capture_output=True,timeout=60);p.check_returncode()
assert p.stdout.decode().strip()==inputs["base"]
p=subprocess.run(["git","status","--porcelain"],cwd=repo,capture_output=True,timeout=60);p.check_returncode()
assert not p.stdout,"Product worktree must remain clean before portable execution"
env=dict(os.environ)
env["PATH"]=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get("PATH","")
env["PYTHONUTF8"]="1"
execution={"schema":"original-selected-space-execution/v1","wrapper_pid":os.getpid(),
 "input_sha256":sha((out/"INPUTS.json").read_bytes()),
 "runner_sha256":sha(pathlib.Path(__file__).read_bytes()),
 "toolchain":[{"path":str(path),"sha256":sha(path.read_bytes()),"bytes":path.stat().st_size} for path in (swift,swiftc)],
 "commands":[],"prior_tests_replayed":False,"native_rpc_calls":0,"product_applied":False}
def persist():
 (out/"EXECUTION.json").write_bytes((json.dumps(execution,indent=2)+"\n").encode())
def run(label,args,timeout):
 record={"label":label,"command":list(map(str,args)),"cwd":str(out),"wrapper_pid":os.getpid(),
 "started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"timeout_seconds":timeout,"phase":"STARTING"}
 execution["commands"].append(record);persist()
 with (out/(label+".stdout.log")).open("wb") as stdout,(out/(label+".stderr.log")).open("wb") as stderr:
  child=subprocess.Popen(list(map(str,args)),cwd=out,env=env,stdout=stdout,stderr=stderr)
  record["child_pid"]=child.pid;record["phase"]="RUNNING";persist()
  try:
   record["returncode"]=child.wait(timeout=timeout);record["timed_out"]=False
  except subprocess.TimeoutExpired:
   record["timed_out"]=True
   if child.poll() is None:
    cleanup=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=30)
    record["owned_tree_cleanup"]={"returncode":cleanup.returncode,
     "stdout":cleanup.stdout.decode("utf-8","replace"),"stderr":cleanup.stderr.decode("utf-8","replace")}
   try:record["returncode"]=child.wait(timeout=30)
   except subprocess.TimeoutExpired:record["returncode"]=None
 record["phase"]="TERMINAL" if record["returncode"] is not None else "UNRESOLVED_NO_RETRY"
 record["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for stream in ("stdout","stderr"):
  raw=(out/(label+"."+stream+".log")).read_bytes()
  record[stream+"_sha256"]=sha(raw);record[stream+"_bytes"]=len(raw)
 verify_inputs();record["all_inputs_unchanged"]=True;persist()
 if record["returncode"]!=0 or record["timed_out"]:
  print(json.dumps({"status":"ACTUAL_FIRST_FAILURE_PRESERVED","failed_command":record,
   "stdout_tail":(out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")[-12000:],
   "stderr_tail":(out/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace")[-18000:]}))
  raise SystemExit(1)
 return (out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")
version=run("swift-version",[swiftc,"--version"],30)
run("actual-manager-syntax",[swiftc,"-frontend","-parse",out/"product-inputs/CANDIDATE_CANONICAL.swift"],90)
run("actual-service-syntax",[swiftc,"-frontend","-parse",out/"product-inputs/WORKSPACE_SERVICE_CANONICAL.swift"],90)
run("swift-testing-selected-space",[
 swift,"test","--verbose","--package-path",out,"--scratch-path",out/".build",
 "--enable-swift-testing","--disable-xctest","--xunit-output",out/"TEST_RESULTS.xml",
 "-Xswiftc","-strict-concurrency=complete"
],900)
xml=out/"TEST_RESULTS.xml"
tree=ET.parse(xml);cases=tree.findall(".//testcase")
assert len(cases)==len(inputs["expected_tests"])==10,len(cases)
assert sorted(c.attrib["name"].removesuffix("()") for c in cases)==sorted(inputs["expected_tests"]),[c.attrib for c in cases]
assert all(not c.findall("failure") and not c.findall("error") and not c.findall("skipped") for c in cases)
binaries=list((out/".build").rglob("OriginalSelectedSpacePackageTests.xctest"))
assert len(binaries)==1,[str(path) for path in binaries]
binary=binaries[0];data=binary.read_bytes();assert data[:2]==b"MZ"
pe=struct.unpack_from("<I",data,0x3c)[0];assert data[pe:pe+4]==b"PE\0\0"
assert struct.unpack_from("<H",data,pe+4)[0]==0x8664
assert binary.name in (out/"swift-testing-selected-space.stdout.log").read_text(encoding="utf-8",errors="replace")
verify_inputs()
result={"schema":"original-selected-space-result/v1","status":"PASS_TEN_NEW_SELECTED_SPACE_GROUPS",
 "tests_run":10,"tests":[c.attrib for c in cases],"toolchain":version,
 "inputs_sha256":sha((out/"INPUTS.json").read_bytes()),"xunit_sha256":sha(xml.read_bytes()),
 "binary":{"path":str(binary.relative_to(out)),"sha256":sha(data),"bytes":len(data),
 "format":"PE32+ x86_64 Windows runner with .xctest filename"},
 "all_inputs_unchanged":True,"product_applied":False,"limits":inputs["limits"]}
(out/"RESULT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
print(json.dumps({"result":result,"commands":execution["commands"]}))
