import pathlib,os,subprocess,json,time,hashlib,signal,shutil,traceback,ast,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path("/Users/m1/development/anytype-d-active-20261125/main14")
SOURCE=ROOT/"source"
EVIDENCE=ROOT/"build14"
EXPECTED=sys.argv[1]
assert re.fullmatch(r"[0-9a-f]{40}",EXPECTED)
FLOOR=2*1024**3
PHASE_GROWTH={"app":int(24*1024**3),"ui":int(1*1024**3)}
FLAGS="$(inherited) -D DEBUG -D PINKHA_DUAL_ENGINE_RUNTIME -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1 -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1"
ENV=dict(os.environ,DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",PINKHA_ANY_NATIVE_ARTIFACT="verified-unified-v1",PINKHA_NATIVE_T2_AUTHORIZED_READ_V1="1")
ENV["PATH"]="/opt/homebrew/bin:/usr/local/bin:"+ENV.get("PATH","/usr/bin:/bin")
def write(path,data):
 temp=path.with_suffix(path.suffix+".new");temp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n");temp.replace(path)
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def git(*a):
 return subprocess.run(["git","-C",str(SOURCE),*a],capture_output=True,text=True,check=True).stdout
def source_state():
 files=git("ls-files","-z").split("\0")
 suffixes={".swift",".m",".mm",".h",".c",".cpp",".pbxproj",".xcconfig",".xcscheme",".xctestplan",".plist",".entitlements"}
 rows={}
 for name in files:
  if not name:continue
  p=SOURCE/name
  if p.suffix in suffixes or name.endswith("Package.resolved"):
   rows[name]={"bytes":p.stat().st_size,"sha256":sha(p)}
 return {"commit":git("rev-parse","HEAD").strip(),"status":git("status","--porcelain"),"tree":git("rev-parse","HEAD^{tree}").strip(),"files":rows}
def run_phase(name,argv,timeout=7200):
 d=EVIDENCE/name;d.mkdir()
 log=d/"original.log";start=time.time();minfree=shutil.disk_usage(ROOT).free
 if minfree<FLOOR+PHASE_GROWTH[name]:raise RuntimeError("Measured phase growth allowance plus 2 GiB emergency floor is unavailable")
 with log.open("wb") as f:
  p=subprocess.Popen(argv,cwd=SOURCE,env=ENV,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  result={"phase":name,"sourceCommit":EXPECTED,"argv":argv,"cwd":str(SOURCE),"started":start,"pid":p.pid,"pgid":p.pid,"status":"RUNNING","freeBytesBefore":minfree,"minimumFreeBytes":minfree,"timeoutSeconds":timeout,"jobs":4,"environment":{"DEVELOPER_DIR":ENV["DEVELOPER_DIR"],"PINKHA_ANY_NATIVE_ARTIFACT":ENV["PINKHA_ANY_NATIVE_ARTIFACT"],"PINKHA_NATIVE_T2_AUTHORIZED_READ_V1":"1"}}
  write(d/"command.json",result);write(EVIDENCE/"active.json",result)
  stop=None
  while p.poll() is None:
   free=shutil.disk_usage(ROOT).free;minfree=min(minfree,free)
   if free<FLOOR:stop="RESOURCE_DISK_FLOOR"
   elif time.time()-start>timeout:stop="TIMEOUT"
   if stop:
    try:os.killpg(p.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:
     try:os.killpg(p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     p.wait()
    break
   write(d/"monitor.json",{"time":time.time(),"elapsedSeconds":time.time()-start,"freeBytes":free,"minimumFreeBytes":minfree,"pid":p.pid})
   time.sleep(2)
  code=p.wait()
 result.update(exitCode=code,finished=time.time(),elapsedSeconds=time.time()-start,minimumFreeBytes=minfree,freeBytesAfter=shutil.disk_usage(ROOT).free,status=stop or ("PASS_BUILD_EXIT_0" if code==0 else "FAIL_BUILD"),logSHA256=sha(log),logBytes=log.stat().st_size)
 try:os.killpg(p.pid,0);result["ownedProcessGroup"]="STILL_PRESENT"
 except ProcessLookupError:result["ownedProcessGroup"]="ABSENT_ESRCH"
 except PermissionError as exc:result["ownedProcessGroup"]="UNRESOLVED_PERMISSION_DENIED";result["groupObservationError"]={"type":type(exc).__name__,"reason":str(exc)}
 write(d/"result.json",result);write(EVIDENCE/"active.json",result)
 if code or stop:raise RuntimeError(name+" "+result["status"])
 if result["ownedProcessGroup"]!="ABSENT_ESRCH":raise RuntimeError(name+" process group is not positively absent")
 return result

def verify_dependencies(stage):
 inventory_path=ROOT/"native-materialization-11619/framework-files.json"
 assert sha(inventory_path)=="c745a177f7d4239d31484a1a287db3debe016ec2e6064b78c5b13d8ae280817b"
 expected=json.loads(inventory_path.read_text())
 base=SOURCE/"Dependencies/Middleware/Lib.xcframework"
 assert not base.is_symlink()
 actual={}
 for p in sorted(base.rglob("*")):
  assert not p.is_symlink(),"Unexpected native symlink"
  if p.is_file():actual[str(p.relative_to(base))]={"bytes":p.stat().st_size,"sha256":sha(p)}
 assert actual==expected,"Native framework bytes changed"
 command=["python3",str(SOURCE/"Tools/Hanlin/prepare_sdk.py"),"--check"]
 result=subprocess.run(command,cwd=SOURCE,env=ENV,capture_output=True,text=True,timeout=60)
 (EVIDENCE/("sdk-"+stage+".log")).write_text(result.stdout+result.stderr)
 assert result.returncode==0,"Canonical SDK verification failed: "+result.stderr
 write(EVIDENCE/("dependencies-"+stage+".json"),{"status":"PASS_EXACT_NATIVE_AND_SDK_CONTENT","nativeInventorySHA256":sha(inventory_path),"nativeFiles":len(actual),"sdkCommand":command,"sdkExitCode":result.returncode,"sdkLogSHA256":sha(EVIDENCE/("sdk-"+stage+".log"))})

try:
 EVIDENCE.mkdir(exist_ok=False)
 before=source_state()
 assert before["commit"]==EXPECTED and before["status"]=="",before["status"]
 write(EVIDENCE/"source-before.json",before)
 verify_dependencies("before")
 assembly=ROOT/"native-materialization-11619/receipt.json"
 assert sha(assembly)=="a27b5f2f955d85b31157d7aedf7733e7d32e0acdac59920c0bd142ed304484bd"
 assert json.loads(assembly.read_text())["status"]=="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
 lock=SOURCE/"Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
 sdk=SOURCE/"Dependencies/Hanlin/.pinkha-source.json"
 native=SOURCE/"Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
 assert sha(lock)=="e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd"
 assert sha(sdk)=="b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150"
 assert sha(native)=="9f64b4469e221cd27b04c0f46b7479cf1fb079b36fce8a26c0fd8b0521ecaf5e"
 baseline={"freeBytes":shutil.disk_usage(ROOT).free,"memsize":subprocess.run(["sysctl","-n","hw.memsize"],capture_output=True,text=True).stdout.strip(),"cpus":subprocess.run(["sysctl","-n","hw.ncpu"],capture_output=True,text=True).stdout.strip(),"vmStat":subprocess.run(["vm_stat"],capture_output=True,text=True).stdout,"cacheSizes":subprocess.run(["du","-sk",str(ROOT/"app-derived/Build/Products"),str(ROOT/"app-derived/Build/Intermediates.noindex")],capture_output=True,text=True).stdout,"reasonForJobs4":"Measured 16 GiB/10 CPU host; actual free bytes and phase growth admission are recorded in this receipt. This is the sole Pinkha main compiler; other owners use isolated sources. Four jobs use an isolated APFS clone of retained Products and SDK precompiled modules. Original Intermediates and SourcePackages are absent, so source dependencies and intermediates must be recreated. A 2 GiB owned-process emergency floor and original process/memory samples are retained.","phaseGrowthAllowanceBytes":PHASE_GROWTH,"phaseBudgetEvidence":{"previousMeasuredGlobalPeakDropsBytes":[2239700992,1799016448,375001088],"interpretation":"Previous global samples include unrelated activity. Actual main13 inventory has no Intermediates or SourcePackages. The 24 GiB App allowance budgets source dependency materialization, cold compiler intermediates, products, and margin; this is an estimate, not an observed peak. UI has a separate 1 GiB allowance; the live emergency floor remains 2 GiB."},"lockSHA256":sha(lock),"sdkReceiptSHA256":sha(sdk),"nativeSHA256":sha(native),"nativeSourceManifestSHA256":"11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"}
 write(EVIDENCE/"input-and-resource-admission.json",baseline)
 settings=["OTHER_SWIFT_FLAGS="+FLAGS,"ENABLE_TESTABILITY=YES","ONLY_ACTIVE_ARCH=YES","ARCHS=arm64","SWIFT_OPTIMIZATION_LEVEL=-Onone","CODE_SIGN_IDENTITY=-","CODE_SIGNING_ALLOWED=YES","CODE_SIGNING_REQUIRED=YES","PROVISIONING_PROFILE_SPECIFIER="]
 app=["xcodebuild","build-for-testing","-project",str(SOURCE/"Anytype.xcodeproj"),"-scheme","Anytype","-configuration","Debug-Anytype","-destination","generic/platform=iOS Simulator","-derivedDataPath",str(ROOT/"app-derived"),"-clonedSourcePackagesDirPath",str(ROOT/"app-derived/SourcePackages"),"-resultBundlePath",str(EVIDENCE/"App.xcresult"),"-onlyUsePackageVersionsFromResolvedFile","-disableAutomaticPackageResolution","-jobs","4"]+settings
 appresult=run_phase("app",app)
 verify_dependencies("after-app")
 after=source_state();assert before==after,"Source changed during original app build"
 assert sha(sdk)==baseline["sdkReceiptSHA256"] and sha(native)==baseline["nativeSHA256"]
 ui_source=ROOT/"ui-source-build14";ui_source.mkdir()
 selected=[n for n in git("ls-files","-z","PinkhaStage1Acceptance").split("\0") if n]
 for name in selected:
  source=SOURCE/name;dest=ui_source/name;dest.parent.mkdir(parents=True,exist_ok=True)
  assert not source.is_symlink()
  shutil.copy2(source,dest)
  assert sha(source)==sha(dest)
 helper=SOURCE/"Tools/PinkhaNativeDerived/rerun_original_ui.py"
 nodes=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=="ui_only_project"]
 assert len(nodes)==1
 function=ast.get_source_segment(helper.read_text(),nodes[0])
 namespace={"shutil":shutil,"re":re,"ET":ET}
 exec(compile(function,str(helper),"exec"),namespace)
 ui_project=namespace["ui_only_project"](ui_source)
 write(EVIDENCE/"original-ui-copy.json",{"generatorSHA256":sha(helper),"copiedFiles":[{"path":n,"sha256":sha(SOURCE/n)} for n in selected],"generatedProject":str(ui_project)})
 ui=["xcodebuild","build-for-testing","-project",str(ui_project),"-scheme","PinkhaPrebuiltUI","-configuration","Debug-Anytype","-destination","generic/platform=iOS Simulator","-derivedDataPath",str(ROOT/"ui-derived"),"-resultBundlePath",str(EVIDENCE/"UI.xcresult"),"-jobs","4"]+settings
 uiresult=run_phase("ui",ui)
 verify_dependencies("after-ui")
 after=source_state();write(EVIDENCE/"source-after.json",after);assert before==after
 products={}
 for kind in ["app-derived","ui-derived"]:
  base=ROOT/kind/"Build/Products"
  rows=[]
  for p in base.rglob("*"):
   if p.is_file() and (p.name in ["Info.plist","Anytype","PinkhaStage1AcceptanceUITests","PinkhaStage1AcceptanceUITests-Runner"] or p.suffix==".xctestrun"):
    rows.append({"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)})
  products[kind]=rows
 write(EVIDENCE/"products.json",products)
 inventories={}
 for kind in ["app-derived","ui-derived"]:
  base=ROOT/kind/"Build/Products"
  rows=[]
  for p in sorted(base.rglob("*")):
   rel=str(p.relative_to(base))
   if p.is_symlink():rows.append({"path":rel,"kind":"symlink","target":os.readlink(p)})
   elif p.is_file():rows.append({"path":rel,"kind":"file","bytes":p.stat().st_size,"sha256":sha(p)})
  inventories[kind]={"base":str(base),"entries":rows}
 write(EVIDENCE/"products-all.json",inventories)
 write(EVIDENCE/"receipt.json",{"status":"PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE","sourceCommit":EXPECTED,"app":appresult,"ui":uiresult,"inputs":baseline,"sourceUnchanged":True,"testsExecuted":0,"controllerSHA256":sha(pathlib.Path(__file__)),"assemblyReceiptSHA256":sha(assembly),"products":products,"completeProductsInventory":{"path":str(EVIDENCE/"products-all.json"),"sha256":sha(EVIDENCE/"products-all.json"),"entries":sum(len(v["entries"]) for v in inventories.values())}})
except BaseException as exc:
 EVIDENCE.mkdir(exist_ok=True)
 try:write(EVIDENCE/"source-after.json",source_state())
 except BaseException:pass
 write(EVIDENCE/"failure.json",{"status":"FAIL","error":str(exc),"traceback":traceback.format_exc(),"time":time.time(),"sourceCommit":EXPECTED,"freeBytes":shutil.disk_usage(ROOT).free})
 raise
