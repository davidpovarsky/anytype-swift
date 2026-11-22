import os,sys,pathlib,json,hashlib,subprocess,time,datetime,re,shutil,zipfile,xml.etree.ElementTree as ET
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
packet=repo/"docs/pinkha/torah-integration/production-native-metadata-20261122/controls"
temp=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\omd-20261122")
harness=temp/"harness";build=temp/"build"
dep=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\omd-protobuf-20261122")
swift=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swift.exe")
evidence=packet/"validation/windows-swift-testing-26"
assert not evidence.exists(),"First execution directory already exists; never replay without inspecting receipt"
evidence.mkdir(parents=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
inputs=json.loads((packet/"INPUTS.json").read_bytes())
assert sha((packet/"INPUTS.json").read_bytes())=="5e504b35b9a21485264701ec1691fbb9b14cd6fead5d0164da45447ccc05f717"
dependency=json.loads((packet/"provenance/SWIFTPROTOBUF_SOURCE_MANIFEST.json").read_bytes())
preparation=json.loads((packet/"provenance/DEPENDENCY_PREPARATION.json").read_bytes())
expected=inputs["test_methods"];assert len(expected)==26
def source_state():
 result=[]
 for item in inputs["source_inputs"]:
  retained=packet/"harness"/item["retained"];used=harness/item["retained"]
  b=used.read_bytes();assert sha(b)==item["sha256"] and b==retained.read_bytes(),item["retained"]
  result.append({"kind":"frozen_harness","path":str(used),"bytes":len(b),"sha256":sha(b)})
 product=repo/"Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift"
 assert sha(product.read_bytes())==inputs["product_sha256"]
 for item in dependency["files"]:
  b=(dep/item["path"]).read_bytes();assert len(b)==item["bytes"] and sha(b)==item["sha256"],item["path"]
 p=subprocess.run(["git","status","--porcelain","--untracked-files=all"],cwd=dep,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
 assert p.returncode==0 and not p.stdout,p.stdout.decode("utf-8","replace")
 assert sha(swift.read_bytes())==preparation["swift_sha256"]
 result.append({"kind":"genuine_dependency","commit":inputs["dependency_revision"],"files":len(dependency["files"]),"exact":True})
 return result
before=source_state();put(evidence/"SOURCE_BEFORE.json",before)
env=os.environ.copy();env.update({"PYTHONUTF8":"1","OTZARIA_METADATA_SWIFTPROTOBUF_CHECKOUT":str(dep),"PROTOBUF_NO_PROTOC":"true","NO_COLOR":"1","CLICOLOR":"0"})
env["PATH"]=str(swift.parent)+os.pathsep+env.get("PATH","")
xunit=temp/"swift-testing-26.xml"
args=[str(swift),"test","--package-path",str(harness),"--scratch-path",str(build),"--configuration","debug","--jobs","4","--disable-xctest","--enable-swift-testing","--filter","OriginalAnnotationNativeMetadataTests","--xunit-output",str(xunit),"--verbose"]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
put(evidence/"PHASE.json",{"phase":"STARTING_SINGLE_SWIFT_TEST","at":start,"args":args,"expected_cases":26})
timeout=False;cleanup=None
with (evidence/"swift-test.stdout").open("wb") as out,(evidence/"swift-test.stderr").open("wb") as err:
 process=subprocess.Popen(args,cwd=harness,env=env,stdout=out,stderr=err)
 put(evidence/"PHASE.json",{"phase":"RUNNING_SINGLE_SWIFT_TEST","at":start,"pid":process.pid,"args":args,"timeout_s":900,"expected_cases":26})
 print(json.dumps({"phase":"RUNNING_SINGLE_SWIFT_TEST","pid":process.pid,"timeout_s":900}),flush=True)
 try:rc=process.wait(timeout=900)
 except subprocess.TimeoutExpired:
  timeout=True
  killed=subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
  cleanup={"pid":process.pid,"action":"taskkill owned command process tree only","exit_code":killed.returncode,"stdout":killed.stdout.decode("utf-8","replace"),"stderr":killed.stderr.decode("utf-8","replace")}
  rc=process.wait(timeout=30)
finish=datetime.datetime.now(datetime.timezone.utc).isoformat()
source_after_error=None
try:after=source_state();source_exact=after==before
except Exception as error:after=[];source_exact=False;source_after_error=repr(error)
put(evidence/"SOURCE_AFTER.json",{"exact":source_exact,"inputs":after,"error":source_after_error})
stdout=(evidence/"swift-test.stdout").read_bytes();stderr=(evidence/"swift-test.stderr").read_bytes()
text=stdout.decode("utf-8","replace")+"\n"+stderr.decode("utf-8","replace")
clean=re.sub(r"\x1b\[[0-9;]*m","",text)
caseproof={"method":None,"executed":0,"passed":0,"failed":None,"skipped":None,"names":[]}
if xunit.is_file():
 shutil.copyfile(xunit,evidence/"swift-testing-26.xml")
 try:
  tree=ET.fromstring(xunit.read_bytes());cases=tree.findall(".//testcase")
  names=[];failed=skipped=0
  for case in cases:
   raw=case.attrib.get("name","")
   match=[name for name in expected if name in raw]
   names.append(match[0] if len(match)==1 else raw)
   failed+=int(case.find("failure") is not None or case.find("error") is not None)
   skipped+=int(case.find("skipped") is not None)
  caseproof={"method":"actual_swift_testing_xunit","executed":len(cases),"passed":len(cases)-failed-skipped,"failed":failed,"skipped":skipped,"names":names,"xunit_sha256":sha(xunit.read_bytes())}
 except Exception as error:caseproof["xunit_parse_error"]=repr(error)
summary_lines=[line for line in clean.splitlines() if "Test run with" in line]
passed_logged=[name for name in expected if re.search(r"\bTest\s+"+re.escape(name)+r"\(\).*?\bpassed\b",clean)]
caseproof["actual_summary_lines"]=summary_lines
caseproof["named_passes_in_raw_log"]=passed_logged
if caseproof["method"] is None and len(passed_logged)==26 and any(re.search(r"\b26 tests?\b.*\bpassed\b",line) for line in summary_lines):
 caseproof.update({"method":"all26_exact_named_pass_lines_and_actual_swift_testing_summary","executed":26,"passed":26,"failed":0,"skipped":0,"names":passed_logged})
case_exact=(caseproof["executed"]==26 and caseproof["passed"]==26 and caseproof["failed"]==0 and caseproof["skipped"]==0 and len(caseproof["names"])==26 and set(caseproof["names"])==set(expected))
binary_files=[]
if build.exists():
 for p in sorted(build.rglob("*")):
  if p.is_file() and "OriginalMetadataControlsPackageTests" in p.name and p.suffix.lower() in (".exe",".xctest"):
   b=p.read_bytes()
   if b[:2]==b"MZ":binary_files.append({"path":str(p),"bytes":len(b),"sha256":sha(b)})
 if binary_files:
  archive=evidence/"ACTUAL_TEST_BINARY.zip"
  with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
   for item in binary_files:z.write(item["path"],arcname=pathlib.Path(item["path"]).relative_to(build).as_posix())
  with zipfile.ZipFile(archive) as z:assert z.testzip() is None
  put(evidence/"BINARY.json",{"files":binary_files,"archive_bytes":archive.stat().st_size,"archive_sha256":sha(archive.read_bytes())})
 selected=[]
 for p in build.rglob("*"):
  if p.is_file() and (p.name in ["description.json","workspace-state.json","debug.yaml","runner.swift","resource_bundle_accessor.swift"] or p.name.endswith("discovered-tests.swift")):
   rel=p.relative_to(build).as_posix()
   target=evidence/"build-metadata"/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
   selected.append({"path":rel,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())})
 put(evidence/"BUILD_METADATA.json",selected)
execution={"schema":1,"args":args,"cwd":str(harness),"environment_overrides":{"OTZARIA_METADATA_SWIFTPROTOBUF_CHECKOUT":str(dep),"PROTOBUF_NO_PROTOC":"true","PATH_prepend":str(swift.parent),"NO_COLOR":"1","CLICOLOR":"0"},"parent_pid":os.getpid(),"child_pid":process.pid,"started_at":start,"finished_at":finish,"duration_s":round(time.monotonic()-clock,3),"timeout_s":900,"timed_out":timeout,"exit_code":rc,"owned_timeout_cleanup":cleanup,"stdout_sha256":sha(stdout),"stderr_sha256":sha(stderr),"runner_sha256":sha(pathlib.Path(__file__).read_bytes()),"source_manifest_sha256":sha((packet/"INPUTS.json").read_bytes()),"compiler_sha256":preparation["swiftc_sha256"],"swift_version":preparation["swift_version"],"source_after_exact":source_exact}
put(evidence/"EXECUTION.json",execution)
passed=(rc==0 and not timeout and case_exact and source_exact and bool(binary_files))
result={"schema":1,"status":"PASS" if passed else "FAIL_OR_REQUIRES_RECEIPT_TRIAGE","actual_swift_test_exit_code":rc,"actual_cases":caseproof,"source_after_exact":source_exact,"compiled_binary_files":binary_files,"product_sha256":inputs["product_sha256"],"dependency_revision":inputs["dependency_revision"],"module_scopes":inputs["module_scopes"],"old_policy52_or_native_tests_rerun":False,"native_calls":0,"Apple_or_original_app_module_acceptance":"NOT_RUN","full_original_ProtobufMessages_or_PinkhaKit_package_acceptance":"NOT_CLAIMED","timed_out":timeout}
put(evidence/"RESULT.json",result)
put(evidence/"PHASE.json",{"phase":"TERMINAL","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":result["status"],"exit_code":rc})
print(json.dumps({"status":result["status"],"result":str(evidence/"RESULT.json"),"actual_exit":rc,"case_proof":caseproof,"source_after_exact":source_exact,"binaries":binary_files,"duration_s":execution["duration_s"],"diagnostic_tail":clean[-10000:] if not passed else None}),flush=True)
sys.exit(0 if passed else 1)
