import pathlib,os,subprocess,json,time,hashlib,signal,shutil,traceback,ast,re,sys,importlib.util,xml.etree.ElementTree as ET
ROOT=pathlib.Path("/Users/m1/development/anytype-d-active-20261125/main15")
SOURCE=ROOT.parent/"main14/source"
APP_DERIVED=ROOT.parent/"main14/app-derived"
EVIDENCE=ROOT/"build15"
EXPECTED=sys.argv[1]
assert EXPECTED=="379ca3568f247d2fc218ed63df24796d461713c0"
FLOOR=2*1024**3
PHASE_GROWTH={"app":int(3*1024**3),"ui":int(1*1024**3)}
CONCURRENT_GROWTH=512*1024**2
LIFECYCLE=None
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
 if minfree<FLOOR+PHASE_GROWTH[name]+CONCURRENT_GROWTH:raise RuntimeError("Warm phase allowance, concurrent growth and 2 GiB emergency floor are unavailable")
 with log.open("wb") as f:
  p=subprocess.Popen(argv,cwd=SOURCE,env=ENV,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  result={"phase":name,"sourceCommit":EXPECTED,"argv":argv,"cwd":str(SOURCE),"started":start,"pid":p.pid,"pgid":p.pid,"status":"RUNNING","freeBytesBefore":minfree,"minimumFreeBytes":minfree,"timeoutSeconds":timeout,"jobs":4,"cleanupErrors":[],"termination":[],"environment":{"DEVELOPER_DIR":ENV["DEVELOPER_DIR"],"PINKHA_ANY_NATIVE_ARTIFACT":ENV["PINKHA_ANY_NATIVE_ARTIFACT"],"PINKHA_NATIVE_T2_AUTHORIZED_READ_V1":"1"}}
  write(d/"command.json",result);write(EVIDENCE/"active.json",result)
  stop=None
  while p.poll() is None:
   free=shutil.disk_usage(ROOT).free;minfree=min(minfree,free)
   if free<FLOOR:stop="RESOURCE_DISK_FLOOR"
   elif time.time()-start>timeout:stop="TIMEOUT"
   if stop:
    LIFECYCLE._terminate_owned_process(p,result)
    break
   write(d/"monitor.json",{"time":time.time(),"elapsedSeconds":time.time()-start,"freeBytes":free,"minimumFreeBytes":minfree,"pid":p.pid})
   time.sleep(2)
  try:code=p.wait(timeout=1)
  except BaseException as exc:code=None;result["cleanupErrors"].append({"phase":"final-owned-wait","type":type(exc).__name__,"reason":str(exc)})
 result.update(exitCode=code,finished=time.time(),elapsedSeconds=time.time()-start,minimumFreeBytes=minfree,freeBytesAfter=shutil.disk_usage(ROOT).free,status=stop or ("PASS_BUILD_EXIT_0" if code==0 else "FAIL_BUILD"),logSHA256=sha(log),logBytes=log.stat().st_size)
 # Original exit and log evidence is persisted before bounded read-only observation.
 write(d/"process-exit.json",result)
 observed=LIFECYCLE._observe_exited_group(p.pid)
 result["ownedProcessGroup"]=observed["status"]
 result["ownedGroupObservations"]=observed["observations"]
 result["processExitReceiptSHA256"]=sha(d/"process-exit.json")
 write(d/"result.json",result);write(EVIDENCE/"active.json",result)
 if code!=0 or stop or result["cleanupErrors"]:raise RuntimeError(name+" "+result["status"])
 if result["ownedProcessGroup"]!="ABSENT_ESRCH":raise RuntimeError(name+" process group is not positively absent")
 return result

def verify_runtime_identity(stage):
 helper=SOURCE/"Tools/PinkhaDualEngineRuntime/runtime_identity.py"
 assert sha(helper)=="306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0"
 spec=importlib.util.spec_from_file_location("app15_exact_runtime_identity",helper)
 runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
 manifest=(SOURCE/"Tools/PinkhaDualEngineRuntime/source-permission-manifest.json").read_bytes()
 assert hashlib.sha256(manifest).hexdigest()=="8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
 inputs={}
 pins={
  "simulator":("946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b","efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903"),
  "device":("c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208","fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546")}
 for kind,(receipt_sha,command_sha) in pins.items():
  base=ROOT/"native-materialization-8ac"/kind
  values={key:(base/name).read_bytes() for key,name in (("receipt","receipt.json"),("command","combined-gomobile-bind.command.json"),("log","combined-gomobile-bind.log"))}
  receipt=json.loads(values["receipt"]);command=json.loads(values["command"])
  assert [row for row in receipt["commands"] if row["name"]=="combined-gomobile-bind"]==[command]
  inputs[kind]=dict(values,expectedReceiptSHA256=receipt_sha,expectedCommandSHA256=command_sha)
 result=runtime.qualify_application(manifest,"2026-11-26",(SOURCE/"Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift").read_bytes(),inputs)
 assembly=ROOT/"native-materialization-8ac/receipt.json"
 assert sha(assembly)=="c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231"
 original=json.loads(assembly.read_bytes())
 assert original["status"]=="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE" and result["identity"]==original["runtimeIdentity"]
 for kind,identifier in (("simulator","ios-arm64-simulator"),("device","ios-arm64")):
  binary=SOURCE/"Dependencies/Middleware/Lib.xcframework"/identifier/"Lib.framework/Lib"
  assert sha(binary)==result["slices"][kind]["binarySHA256"]==original["inputs"][kind]["binarySHA256"]
  assert binary.stat().st_size==result["slices"][kind]["binaryBytes"]==original["inputs"][kind]["binaryBytes"]
 write(EVIDENCE/("runtime-identity-"+stage+".json"),result)
 return result

def verify_new_test_compiler_inputs():
 required=[SOURCE/"AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift",
           SOURCE/"AnyTypeTests/Pinkha/TextViewLinkGestureArbitrationTests.swift"]
 lists=[p for p in (APP_DERIVED/"Build/Intermediates.noindex").rglob("*SwiftFileList")
        if "AnytypeTests.build" in p.parts and p.is_file()]
 matched=[]
 for path in lists:
  data=path.read_text()
  if all(str(item) in data for item in required):
   matched.append({"path":str(path),"sha256":sha(path)})
 assert matched,"The actual AnytypeTests compiler input list must contain both new UIKit test sources"
 write(EVIDENCE/"new-uikit-compiler-inputs.json",{"status":"PASS_ACTUAL_COMPILED_TEST_SOURCE_INPUTS_NOT_TEST_EXECUTION",
       "sourceFiles":[{"path":str(p.relative_to(SOURCE)),"sha256":sha(p)} for p in required],
       "actualCompilerFileLists":matched,"testsExecuted":0})

def verify_dependencies(stage):
 inventory_path=ROOT/"native-materialization-8ac/framework-files.json"
 assert sha(inventory_path)=="fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf"
 expected=json.loads(inventory_path.read_text())
 base=SOURCE/"Dependencies/Middleware/Lib.xcframework"
 assert not base.is_symlink()
 actual={}
 for p in sorted(base.rglob("*")):
  assert not p.is_symlink(),"Unexpected native symlink"
  if p.is_file():actual[str(p.relative_to(base))]={"bytes":p.stat().st_size,"sha256":sha(p)}
 assert actual==expected,"Native framework bytes changed"
 verify_runtime_identity(stage)
 command=["python3",str(SOURCE/"Tools/Hanlin/prepare_sdk.py"),"--check"]
 result=subprocess.run(command,cwd=SOURCE,env=ENV,capture_output=True,text=True,timeout=60)
 (EVIDENCE/("sdk-"+stage+".log")).write_text(result.stdout+result.stderr)
 assert result.returncode==0,"Canonical SDK verification failed: "+result.stderr
 write(EVIDENCE/("dependencies-"+stage+".json"),{"status":"PASS_EXACT_NATIVE_AND_SDK_CONTENT","nativeInventorySHA256":sha(inventory_path),"nativeFiles":len(actual),"sdkCommand":command,"sdkExitCode":result.returncode,"sdkLogSHA256":sha(EVIDENCE/("sdk-"+stage+".log"))})

try:
 EVIDENCE.mkdir(exist_ok=False)
 core_path=ROOT/"source-inputs379/combined_heart_semantics_owned_outcomes.py"
 assert sha(core_path)=="73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
 core_spec=importlib.util.spec_from_file_location("app15_original_owned_outcomes",core_path)
 core=importlib.util.module_from_spec(core_spec);core_spec.loader.exec_module(core)
 LIFECYCLE=core.Commands(EVIDENCE/"owned-builder-lifecycle",SOURCE)
 assert sha(ROOT/"source-staging1/receipt.json")=="dc0617be03813129b76a09a347c15f835611e6520f4f261825abacab16a71781"
 staging=json.loads((ROOT/"source-staging1/receipt.json").read_bytes())
 assert staging["status"]=="PASS_EXACT_APP15_SOURCE_AND_NATIVE_MATERIALIZED_ORIGINALS_RETAINED" and staging["sourceCommit"]==EXPECTED
 assert staging["sourceRoot"]==str(SOURCE) and staging["appDerived"]==str(APP_DERIVED)
 before=source_state()
 assert before["commit"]==EXPECTED and before["status"]=="",before["status"]
 write(EVIDENCE/"source-before.json",before)
 verify_dependencies("before")
 assembly=ROOT/"native-materialization-8ac/receipt.json"
 assert sha(assembly)=="c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231"
 assert json.loads(assembly.read_text())["status"]=="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
 lock=SOURCE/"Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
 sdk=SOURCE/"Dependencies/Hanlin/.pinkha-source.json"
 native=SOURCE/"Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
 assert sha(lock)=="e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd"
 assert sha(sdk)=="b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150"
 assert sha(native)=="f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763"
 baseline={"freeBytes":shutil.disk_usage(ROOT).free,"memsize":subprocess.run(["sysctl","-n","hw.memsize"],capture_output=True,text=True).stdout.strip(),"cpus":subprocess.run(["sysctl","-n","hw.ncpu"],capture_output=True,text=True).stdout.strip(),"vmStat":subprocess.run(["vm_stat"],capture_output=True,text=True).stdout,"cacheSizes":subprocess.run(["du","-sk",str(APP_DERIVED/"Build/Products"),str(APP_DERIVED/"Build/Intermediates.noindex")],capture_output=True,text=True).stdout,"reasonForJobs4":"Measured 16 GiB/10 CPU host. This is the sole Pinkha main compiler, reusing the released existing physical source, DerivedData, SourcePackages and module-cache paths. Original App14 source and complete Products were separately preserved byte/mode/link exactly before update. Four jobs retain the prior qualified scheduling; measured phase admission and a live 2 GiB own-process floor remain explicit.","phaseGrowthAllowanceBytes":PHASE_GROWTH,"phaseBudgetEvidence":{"previousMeasuredGlobalPeakDropsBytes":[2239700992,1799016448,375001088],"interpretation":"Previous global samples include unrelated activity. Actual main14 retains the complete warm physical compiler and package paths. The 3 GiB App allowance covers changed local-module intermediates and relinked products; it is an estimate, not an observed peak. UI has 1 GiB, concurrent unrelated growth has 512 MiB, and the original live emergency floor remains 2 GiB. Current original-workspace preservation receipt is separately pinned in the staging input."},"lockSHA256":sha(lock),"sdkReceiptSHA256":sha(sdk),"nativeSHA256":sha(native),"nativeSourceManifestSHA256":"8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b","stagingReceiptSHA256":sha(ROOT/"source-staging1/receipt.json"),"sourceRoot":str(SOURCE),"appDerived":str(APP_DERIVED),"concurrentGrowthAllowanceBytes":CONCURRENT_GROWTH}
 write(EVIDENCE/"input-and-resource-admission.json",baseline)
 settings=["OTHER_SWIFT_FLAGS="+FLAGS,"ENABLE_TESTABILITY=YES","ONLY_ACTIVE_ARCH=YES","ARCHS=arm64","SWIFT_OPTIMIZATION_LEVEL=-Onone","CODE_SIGN_IDENTITY=-","CODE_SIGNING_ALLOWED=YES","CODE_SIGNING_REQUIRED=YES","PROVISIONING_PROFILE_SPECIFIER="]
 app=["xcodebuild","build-for-testing","-project",str(SOURCE/"Anytype.xcodeproj"),"-scheme","Anytype","-configuration","Debug-Anytype","-destination","generic/platform=iOS Simulator","-derivedDataPath",str(APP_DERIVED),"-clonedSourcePackagesDirPath",str(APP_DERIVED/"SourcePackages"),"-resultBundlePath",str(EVIDENCE/"App.xcresult"),"-onlyUsePackageVersionsFromResolvedFile","-disableAutomaticPackageResolution","-jobs","4"]+settings
 appresult=run_phase("app",app)
 verify_new_test_compiler_inputs()
 verify_dependencies("after-app")
 after=source_state();assert before==after,"Source changed during original app build"
 assert sha(sdk)==baseline["sdkReceiptSHA256"] and sha(native)==baseline["nativeSHA256"]
 ui_source=ROOT/"ui-source-build15";ui_source.mkdir()
 selected=[n for n in git("ls-files","-z","PinkhaStage1Acceptance").split("\0") if n]
 for name in selected:
  source=SOURCE/name;dest=ui_source/name;dest.parent.mkdir(parents=True,exist_ok=True)
  assert not source.is_symlink()
  shutil.copy2(source,dest)
  assert sha(source)==sha(dest)
 helper=SOURCE/"Tools/PinkhaNativeDerived/rerun_original_ui.py"
 assert sha(helper)=="7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
 assert sha(SOURCE/"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift")=="8834541f5a47da80b460ecb96b20c930813b743d94f285fc1efba8a93f65ee4d"
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
  base=(APP_DERIVED if kind=="app-derived" else ROOT/kind)/"Build/Products"
  rows=[]
  for p in base.rglob("*"):
   if p.is_file() and (p.name in ["Info.plist","Anytype","PinkhaStage1AcceptanceUITests","PinkhaStage1AcceptanceUITests-Runner"] or p.suffix==".xctestrun"):
    rows.append({"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)})
  products[kind]=rows
 write(EVIDENCE/"products.json",products)
 inventories={}
 for kind in ["app-derived","ui-derived"]:
  base=(APP_DERIVED if kind=="app-derived" else ROOT/kind)/"Build/Products"
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
