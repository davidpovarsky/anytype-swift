import pathlib,os,subprocess,json,time,hashlib,signal,shutil,traceback,ast,re,xml.etree.ElementTree as ET
ROOT=pathlib.Path("/Users/m1/builds/pinkha-dual-main-20261125")
SOURCE=ROOT/"source"
EVIDENCE=ROOT/"build5-ui1"
EXPECTED="6db4d065e007dc6c39ae510a77053f33b7de8247"
FLOOR=2*1024**3
PHASE_GROWTH={"app":int(2.5*1024**3),"ui":int(0.5*1024**3)}
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
 write(d/"result.json",result);write(EVIDENCE/"active.json",result)
 if code or stop:raise RuntimeError(name+" "+result["status"])
 return result
try:
 EVIDENCE.mkdir(exist_ok=False)
 before=source_state()
 assert before["commit"]==EXPECTED and before["status"]=="",before["status"]
 write(EVIDENCE/"source-before.json",before)
 lock=SOURCE/"Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
 sdk=SOURCE/"Dependencies/Hanlin/.pinkha-source.json"
 native=SOURCE/"Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
 assert sha(lock)=="bb5582d3f0b9bc17b909ade4751904fd7b2fee2d066fea50b7a1ef913a8fe513"
 assert sha(sdk)=="67edd8f955524044428bf583b51f2357ca290e5ded0aacd8def0dff92f6b1521"
 assert sha(native)=="08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc"
 baseline={"freeBytes":shutil.disk_usage(ROOT).free,"memsize":subprocess.run(["sysctl","-n","hw.memsize"],capture_output=True,text=True).stdout.strip(),"cpus":subprocess.run(["sysctl","-n","hw.ncpu"],capture_output=True,text=True).stdout.strip(),"vmStat":subprocess.run(["vm_stat"],capture_output=True,text=True).stdout,"cacheSizes":subprocess.run(["du","-sk",str(ROOT/"app-derived/Build/Products"),str(ROOT/"app-derived/Build/Intermediates.noindex")],capture_output=True,text=True).stdout,"reasonForJobs4":"Measured 16 GiB/10 CPU host; sole incremental main compiler, other owner runs test-without-building. Four jobs preserve available parallelism with an owned-process 2 GiB emergency disk guard.","phaseGrowthAllowanceBytes":PHASE_GROWTH,"phaseBudgetEvidence":{"previousMeasuredGlobalPeakDropsBytes":[2239700992,1799016448,375001088],"interpretation":"These global samples include unrelated activity. The next app allowance is 2.5 GiB, covering the largest observed peak plus not-yet-linked original test bundles; UI-only gets 0.5 GiB and is independently admitted."},"lockSHA256":sha(lock),"sdkReceiptSHA256":sha(sdk),"nativeSHA256":sha(native),"nativeSourceManifestSHA256":"70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"}
 write(EVIDENCE/"input-and-resource-admission.json",baseline)
 settings=["OTHER_SWIFT_FLAGS="+FLAGS,"ENABLE_TESTABILITY=YES","ONLY_ACTIVE_ARCH=YES","ARCHS=arm64","SWIFT_OPTIMIZATION_LEVEL=-Onone","CODE_SIGN_IDENTITY=-","CODE_SIGNING_ALLOWED=YES","CODE_SIGNING_REQUIRED=YES","PROVISIONING_PROFILE_SPECIFIER="]
 app=["xcodebuild","build-for-testing","-project",str(SOURCE/"Anytype.xcodeproj"),"-scheme","Anytype","-configuration","Debug-Anytype","-destination","generic/platform=iOS Simulator","-derivedDataPath",str(ROOT/"app-derived"),"-clonedSourcePackagesDirPath",str(ROOT/"app-derived/SourcePackages"),"-resultBundlePath",str(EVIDENCE/"App.xcresult"),"-onlyUsePackageVersionsFromResolvedFile","-disableAutomaticPackageResolution","-jobs","4"]+settings
 original_app_evidence=ROOT/"build5"
 appresult=json.loads((original_app_evidence/"app/result.json").read_text())
 assert appresult["status"]=="PASS_BUILD_EXIT_0" and appresult["exitCode"]==0 and appresult["sourceCommit"]==EXPECTED and appresult["ownedProcessGroup"]=="ABSENT_ESRCH"
 assert before==json.loads((original_app_evidence/"source-before.json").read_text())==json.loads((original_app_evidence/"source-after.json").read_text())
 assert sha(original_app_evidence/"app/original.log")==appresult["logSHA256"]
 write(EVIDENCE/"reused-original-app.json",{"originalEvidence":str(original_app_evidence),"commandResultSHA256":sha(original_app_evidence/"app/result.json"),"originalLogSHA256":appresult["logSHA256"],"sourceCommit":EXPECTED,"currentApplicationBuilds":0})
 app_products=ROOT/"app-derived/Build/Products"
 def app_inventory():
  rows=[]
  for p in sorted(app_products.rglob("*")):
   if p.is_symlink():rows.append({"path":str(p.relative_to(app_products)),"kind":"symlink","target":os.readlink(p)})
   elif p.is_file():rows.append({"path":str(p.relative_to(app_products)),"kind":"file","bytes":p.stat().st_size,"sha256":sha(p)})
  return rows
 app_before=app_inventory();write(EVIDENCE/"original-app-products-before.json",app_before)
 after=source_state();assert before==after,"Source changed before original UI-only continuation"
 assert sha(sdk)==baseline["sdkReceiptSHA256"] and sha(native)==baseline["nativeSHA256"]
 ui_source=ROOT/"ui-source2";ui_source.mkdir()
 selected=[n for n in git("ls-files","-z","PinkhaStage1Acceptance").split("\0") if n]
 for name in selected:
  source=SOURCE/name;dest=ui_source/name;dest.parent.mkdir(parents=True,exist_ok=True)
  assert not source.is_symlink()
  shutil.copy2(source,dest)
  assert sha(source)==sha(dest)
 helper=ROOT/"reviewed-ui-generator-0b9.py"
 nodes=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=="ui_only_project"]
 assert len(nodes)==1
 function=ast.get_source_segment(helper.read_text(),nodes[0])
 namespace={"shutil":shutil,"re":re,"ET":ET}
 exec(compile(function,str(helper),"exec"),namespace)
 ui_project=namespace["ui_only_project"](ui_source)
 write(EVIDENCE/"original-ui-copy.json",{"generatorSHA256":sha(helper),"copiedFiles":[{"path":n,"sha256":sha(SOURCE/n)} for n in selected],"generatedProject":str(ui_project)})
 ui=["xcodebuild","build-for-testing","-project",str(ui_project),"-scheme","PinkhaPrebuiltUI","-configuration","Debug-Anytype","-destination","generic/platform=iOS Simulator","-derivedDataPath",str(ROOT/"ui-derived"),"-resultBundlePath",str(EVIDENCE/"UI.xcresult"),"-jobs","4"]+settings
 uiresult=run_phase("ui",ui)
 after=source_state();write(EVIDENCE/"source-after.json",after);assert before==after
 assert app_inventory()==app_before,"Original main app Products changed during UI-only build"
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
 write(EVIDENCE/"receipt.json",{"status":"PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE","sourceCommit":EXPECTED,"app":appresult,"ui":uiresult,"inputs":baseline,"sourceUnchanged":True,"testsExecuted":0,"currentApplicationBuilds":0,"reusedOriginalAppEvidence":str(original_app_evidence),"reviewedUIGeneratorCommit":"0b9c5d75fec8fa4f4e17266010f7d79a47c08b87","products":products,"completeProductsInventory":{"path":str(EVIDENCE/"products-all.json"),"sha256":sha(EVIDENCE/"products-all.json"),"entries":sum(len(v["entries"]) for v in inventories.values())}})
except BaseException as exc:
 EVIDENCE.mkdir(exist_ok=True)
 try:write(EVIDENCE/"source-after.json",source_state())
 except BaseException:pass
 write(EVIDENCE/"failure.json",{"status":"FAIL","error":str(exc),"traceback":traceback.format_exc(),"time":time.time(),"sourceCommit":EXPECTED,"freeBytes":shutil.disk_usage(ROOT).free})
 raise
