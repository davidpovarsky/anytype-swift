import pathlib,subprocess,json,hashlib,os,datetime,re,struct,xml.etree.ElementTree as ET
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-unsplash-init-20261122")
package=out/"semantic-package";tests=package/"Tests/UnsplashInitialization"
swiftc=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
swift=swiftc.parent/"swift.EXE";runtime=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
def sha(b):return hashlib.sha256(b).hexdigest()
assert not (out/"SEMANTIC_EXECUTION.json").exists()
assert sha((out/"SEMANTIC_INPUTS.json").read_bytes())=="9e289004f92b4798ee68a147d5c2137dea2d297f243163921e44387a5b888907"
inputs=json.loads((out/"SEMANTIC_INPUTS.json").read_bytes())
def verify():
 for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"],item["path"]
 assert sha((out/"RED_UnsplashViewModel.swift").read_bytes())==inputs["red_projection_sha256"]
 assert sha((out/"UNSPLASH_BASE.swift").read_bytes())==inputs["base_sha256"]
 assert sha((out/"UNSPLASH_CANDIDATE.swift").read_bytes())==inputs["candidate_sha256"]
 assert sha((package/"Package.swift").read_bytes())==inputs["package_sha256"]
verify()
(out/"run_initialization_control.py").write_bytes(pathlib.Path(__file__).read_bytes())
env=dict(os.environ);env["PATH"]=str(runtime)+os.pathsep+str(swift.parent)+os.pathsep+env.get("PATH","");env["PYTHONUTF8"]="1"
execution={"schema":1,"wrapper_pid":os.getpid(),"inputs_sha256":sha((out/"SEMANTIC_INPUTS.json").read_bytes()),"runner_sha256":sha((out/"run_initialization_control.py").read_bytes()),"commands":[]}
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
run("swift-version",[swiftc,"--version"],30)
run("complete-unsplash-syntax",[swiftc,"-frontend","-parse",out/"UNSPLASH_CANDIDATE.swift"],90)
red=run("expected-old-initialization-error",[swiftc,"-emit-object","-whole-module-optimization","-parse-as-library","-module-name","OriginalUnsplashInitializerRED","-swift-version","5","-strict-concurrency=complete","-module-cache-path",inputs["module_cache"],tests/"DependencyProbes.swift",tests/"Injected.swift",tests/"NativeServiceValues.swift",out/"RED_UnsplashViewModel.swift","-o",out/"RED.o"],180,True)
red_text=(out/"expected-old-initialization-error.stderr.log").read_text(encoding="utf-8",errors="replace")
errors=[line for line in red_text.splitlines() if re.search(r":\d+:\d+: error:",line)]
assert len(errors)==1 and "'self' used in property access 'unsplashService' before all stored properties are initialized" in errors[0],errors
assert "'self.documentWriteOwner' not initialized" in red_text
assert not (out/"RED.o").exists()
run("swift-testing-new-initialization",[swift,"test","--verbose","--package-path",package,"--scratch-path",package/".build","--enable-swift-testing","--disable-xctest","--xunit-output",out/"SEMANTIC_TEST_RESULTS.xml","-Xswiftc","-strict-concurrency=complete","-Xswiftc","-module-cache-path","-Xswiftc",inputs["module_cache"]],480)
xml=out/"SEMANTIC_TEST_RESULTS.xml";cases=ET.parse(xml).findall(".//testcase")
assert len(cases)==1 and cases[0].attrib["name"].removesuffix("()")==inputs["expected_tests"][0]
assert not list(cases[0])
binaries=list((package/".build").rglob("OriginalUnsplashInitializationPackageTests.xctest"));assert len(binaries)==1
binary=binaries[0];data=binary.read_bytes();assert data[:2]==b"MZ";pe=struct.unpack_from("<I",data,0x3c)[0];assert data[pe:pe+4]==b"PE\0\0" and struct.unpack_from("<H",data,pe+4)[0]==0x8664
combined=(out/"swift-testing-new-initialization.stdout.log").read_text(encoding="utf-8",errors="replace")+"\n"+(out/"swift-testing-new-initialization.stderr.log").read_text(encoding="utf-8",errors="replace")
assert binary.name in combined
verify()
result={"schema":1,"status":"PASS_EXACT_EXPECTED_OLD_INIT_ERROR_AND_ONE_CANDIDATE_INITIALIZATION_CONTROL","candidate_sha256":inputs["candidate_sha256"],"inputs_sha256":sha((out/"SEMANTIC_INPUTS.json").read_bytes()),"expected_red_errors":errors,"expected_red_exit":red["returncode"],"new_tests":1,"test":cases[0].attrib,"xunit_sha256":sha(xml.read_bytes()),"binary":{"path":str(binary.relative_to(out)),"sha256":sha(data),"bytes":len(data)},"all_inputs_unchanged":True,"limits":inputs["limits"]}
(out/"SEMANTIC_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":result,"execution":execution}))
