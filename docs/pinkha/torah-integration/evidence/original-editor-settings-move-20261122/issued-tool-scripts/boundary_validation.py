import pathlib,subprocess,json,hashlib,os,datetime,time,xml.etree.ElementTree as ET
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
package=out/"boundary-package"
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.parent/"swift.EXE"
runtime=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
inputs=json.loads((out/"BOUNDARY_INPUTS.json").read_bytes())
assert not (out/"VALIDATION_EXECUTION.json").exists(), "First execution already started; inspect outcome before any continuation"
probe=package/"Tests"/"OriginalBoundaryProbes"/"BoundaryProbes.swift"
assert hashlib.sha256(probe.read_bytes()).hexdigest()==inputs["probe_sha256"]
candidates=[]
for item in inputs["candidates"]:
 path=out/(pathlib.Path(item["path"]).stem+".candidate.swift")
 assert hashlib.sha256(path.read_bytes()).hexdigest()==item["candidate_sha256"]
 candidates.append(path)
env=dict(os.environ)
env["PATH"]=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get("PATH","")
env["PYTHONUTF8"]="1"
commands=[]
def persist(): (out/"VALIDATION_EXECUTION.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout):
 record={"label":label,"command":list(map(str,args)),"cwd":str(out),"wrapper_pid":os.getpid(),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"timeout_seconds":timeout,"phase":"STARTING"}
 commands.append(record);persist()
 with (out/(label+".stdout.log")).open("wb") as stdout,(out/(label+".stderr.log")).open("wb") as stderr:
  child=subprocess.Popen(list(map(str,args)),cwd=out,env=env,stdout=stdout,stderr=stderr)
  record["child_pid"]=child.pid;record["phase"]="RUNNING";persist()
  try: record["returncode"]=child.wait(timeout=timeout);record["timed_out"]=False
  except subprocess.TimeoutExpired:
   record["timed_out"]=True
   if child.poll() is None:
    cleanup=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=30)
    record["owned_tree_cleanup"]={"returncode":cleanup.returncode,"stdout":cleanup.stdout.decode("utf-8","replace"),"stderr":cleanup.stderr.decode("utf-8","replace")}
   try:record["returncode"]=child.wait(timeout=30)
   except subprocess.TimeoutExpired:record["returncode"]=None
 record["phase"]="TERMINAL" if record.get("returncode") is not None else "UNRESOLVED_NO_RETRY"
 record["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for stream in ["stdout","stderr"]:
  record[stream+"_sha256"]=hashlib.sha256((out/(label+"."+stream+".log")).read_bytes()).hexdigest()
 persist()
 if record["returncode"]!=0 or record["timed_out"]:
  print(json.dumps({"status":"ACTUAL_VALIDATION_FAILURE_PRESERVED","execution":record,"stdout":(out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")[-12000:],"stderr":(out/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace")[-20000:]}))
  raise SystemExit(1)
 return (out/(label+".stdout.log")).read_text(encoding="utf-8",errors="replace")
version=run("swift-version",[swiftc,"--version"],30)
run("changed-three-file-syntax",[swiftc,"-frontend","-parse",*candidates],90)
run("swift-testing-boundaries",[swift,"test","--verbose","--package-path",package,"--scratch-path",package/".build","--enable-swift-testing","--disable-xctest","--xunit-output",out/"BOUNDARY_TEST_RESULTS.xml","-Xswiftc","-strict-concurrency=complete"],420)
xml=out/"BOUNDARY_TEST_RESULTS.xml"
assert xml.is_file(),"Successful process without required xUnit receipt"
tree=ET.parse(xml)
cases=tree.findall(".//testcase")
assert len(cases)==3,len(cases)
assert all(not c.findall("failure") and not c.findall("error") and not c.findall("skipped") for c in cases)
for item,path in zip(inputs["candidates"],candidates):assert hashlib.sha256(path.read_bytes()).hexdigest()==item["candidate_sha256"]
assert hashlib.sha256(probe.read_bytes()).hexdigest()==inputs["probe_sha256"]
binaries=[p for p in (package/".build").rglob("*.exe") if "PackageTests" in p.name]
binary_records=[{"path":str(p.relative_to(out)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in binaries]
assert binary_records,"Missing actual generated test runner"
result={"schema":1,"status":"PASS_THREE_CHANGED_SYNTAX_AND_THREE_EXTRACTED_SWIFT_TESTING_BOUNDARIES","tests_run":3,"tests":[c.attrib for c in cases],"toolchain":version,"probe_sha256":inputs["probe_sha256"],"candidate_provenance_sha256":inputs["candidate_provenance_sha256"],"xunit_sha256":hashlib.sha256(xml.read_bytes()).hexdigest(),"binaries":binary_records,"limits":inputs["limits"]}
(out/"VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":result,"execution":commands}))
