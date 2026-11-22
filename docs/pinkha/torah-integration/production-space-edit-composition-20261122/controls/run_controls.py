import pathlib,subprocess,json,hashlib,os,datetime,xml.etree.ElementTree as ET,re,struct
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-space-bind-20261122")
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.parent/"swift.EXE"
runtime=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-authority-integration-20261122")
def sha(data):return hashlib.sha256(data).hexdigest()
assert not (out/"EXECUTION.json").exists(),"Actual first execution already exists; inspect it instead of replay"
assert sha((out/"INPUTS.json").read_bytes())=="74a0bf1c732e7d579814c4658d1f718e3c476b0d817fbf1871c481fc490f3d07"
inputs=json.loads((out/"INPUTS.json").read_bytes())
def verify_inputs():
 for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"],item["path"]
 for item in inputs["original_inputs"]:assert sha((out/"original"/item["path"]).read_bytes())==item["sha256"],item["path"]
 assert sha((out/"Package.swift").read_bytes())==inputs["package_sha256"]
 assert sha((w/inputs["product_path"]).read_bytes())==inputs["candidate_sha256"]
 assert sha((out/"Owner.candidate.swift").read_bytes())==inputs["candidate_sha256"]
verify_inputs()
(out/"run_controls.py").write_bytes(pathlib.Path(__file__).read_bytes())
env=dict(os.environ);env["PATH"]=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get("PATH","");env["PYTHONUTF8"]="1"
execution={"schema":1,"wrapper_pid":os.getpid(),"input_sha256":sha((out/"INPUTS.json").read_bytes()),"runner_sha256":sha((out/"run_controls.py").read_bytes()),"toolchain":[{"path":str(p),"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for p in (swift,swiftc)],"commands":[]}
def persist():(out/"EXECUTION.json").write_text(json.dumps(execution,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout):
 record={"label":label,"command":list(map(str,args)),"cwd":str(out),"wrapper_pid":os.getpid(),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"timeout_seconds":timeout,"phase":"STARTING"}
 execution["commands"].append(record);persist()
 with (out/(label+".stdout.log")).open("wb") as stdout,(out/(label+".stderr.log")).open("wb") as stderr:
  child=subprocess.Popen(list(map(str,args)),cwd=out,env=env,stdout=stdout,stderr=stderr)
  record["child_pid"]=child.pid;record["phase"]="RUNNING";persist()
  try:record["returncode"]=child.wait(timeout=timeout);record["timed_out"]=False
  except subprocess.TimeoutExpired:
   record["timed_out"]=True
   if child.poll() is None:
    cleanup=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=30)
    record["owned_tree_cleanup"]={"returncode":cleanup.returncode,"stdout":cleanup.stdout.decode("utf-8","replace"),"stderr":cleanup.stderr.decode("utf-8","replace")}
   try:record["returncode"]=child.wait(timeout=30)
   except subprocess.TimeoutExpired:record["returncode"]=None
 record["phase"]="TERMINAL" if record.get("returncode") is not None else "UNRESOLVED_NO_RETRY"
 record["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for stream in ("stdout","stderr"):record[stream+"_sha256"]=sha((out/(label+"."+stream+".log")).read_bytes())
 verify_inputs();record["all_inputs_unchanged"]=True;persist()
 if record["returncode"]!=0 or record["timed_out"]:
  print(json.dumps({"status":"ACTUAL_FIRST_EXECUTION_FAILURE_PRESERVED","execution":record,"stdout_tail":(out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")[-14000:],"stderr_tail":(out/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace")[-18000:]}))
  raise SystemExit(1)
 return (out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")
version=run("swift-version",[swiftc,"--version"],30)
run("new-owner-syntax",[swiftc,"-frontend","-parse",out/"Owner.candidate.swift"],90)
run("swift-testing-composition",[swift,"test","--verbose","--package-path",out,"--scratch-path",out/".build","--enable-swift-testing","--disable-xctest","--xunit-output",out/"TEST_RESULTS.xml","-Xswiftc","-strict-concurrency=complete"],720)
xml=out/"TEST_RESULTS.xml";tree=ET.parse(xml);cases=tree.findall(".//testcase")
assert len(cases)==len(inputs["expected_tests"])==10,len(cases)
assert sorted(c.attrib["name"].removesuffix("()") for c in cases)==sorted(inputs["expected_tests"]),[c.attrib for c in cases]
assert all(not c.findall("failure") and not c.findall("error") and not c.findall("skipped") for c in cases)
binaries=list((out/".build").rglob("OriginalSpaceEditCompositionPackageTests.xctest"))
assert len(binaries)==1,[str(p) for p in binaries]
binary=binaries[0];data=binary.read_bytes();assert data[:2]==b"MZ"
pe=struct.unpack_from("<I",data,0x3c)[0];assert data[pe:pe+4]==b"PE\0\0";machine=struct.unpack_from("<H",data,pe+4)[0];assert machine==0x8664
assert binary.name in (out/"swift-testing-composition.stdout.log").read_text(encoding="utf-8",errors="replace")
verify_inputs()
result={"schema":1,"status":"PASS_TEN_NEW_COMPOSED_BOUNDARY_GROUPS","tests_run":10,"tests":[c.attrib for c in cases],"toolchain":version,"inputs_sha256":sha((out/"INPUTS.json").read_bytes()),"candidate_sha256":inputs["candidate_sha256"],"xunit_sha256":sha(xml.read_bytes()),"binary":{"path":str(binary.relative_to(out)),"sha256":sha(data),"bytes":len(data),"format":"PE32+ x86_64 Windows test runner with .xctest filename"},"all_inputs_unchanged":True,"limits":inputs["limits"]}
(out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":result,"execution":execution}))
