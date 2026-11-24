from pathlib import Path
import os,sys,json,subprocess,plistlib,copy,hashlib,uuid,signal
BASE=Path("/Users/m1/builds/_retained-anytype/45446055084-1/build/current-apple-release-return-rtl-45446055084-1")
ROOT=Path("/Users/m1/builds/actions-anytype/anytype-swift/anytype-swift")
WORK=Path(__file__).parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/"Tools/CurrentAppleValidation"))
sys.path.insert(0,str(ROOT/"Tools/AnyEnginePort"))
import contracts as c
import current_execution as d
import native_ui_transition_contract as parser
env={k:v for k,v in os.environ.items() if not k.startswith("GITHUB_")}
env["DEVELOPER_DIR"]="/Applications/Xcode.app/Contents/Developer"
def run(argv,name,timeout=45,check=True):
 with (WORK/(name+".log")).open("xb") as out:
  p=subprocess.Popen(argv,stdout=out,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:rc=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:rc=p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   raise
 if check and rc!=0:raise RuntimeError(name+"_exit_"+str(rc))
 return rc,(WORK/(name+".log")).read_bytes()
def rewrite(value,products,host):
 if isinstance(value,str):return value.replace("__TESTROOT__",str(products)).replace("__TESTHOST__",str(host))
 if isinstance(value,list):return [rewrite(x,products,host) for x in value]
 if isinstance(value,dict):return {k:rewrite(v,products,host) for k,v in value.items()}
 return value
receipt={"mode":"LOCAL_COMPILED_ENUMERATION_QUALIFICATION","sourceRun":"45446055084","source":"af1f73a1c0dd98c68f8263ce4f9c95370c196df0","appBuilds":0,"uiBuilds":0,"nativeBuilds":0,"testMethodsExecuted":0,"status":"FAIL","stages":{},"scriptSHA256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
udid=None
try:
 assert subprocess.run(["pgrep","-f","/bin/Runner.Worker"],capture_output=True).returncode==1
 assert subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()==receipt["source"]
 original=d.read(BASE/"evidence/original-products.json");execution=d.read(BASE/"evidence/execution.json")
 products=BASE/"work/derived/Build/Products"
 expected={**original["files"],**execution["integrity"]["products"]["newDescriptors"]}
 assert d.inventory(products)==expected
 for name,sha in execution["integrity"]["loadedAfter"].items():
  assert d.digest(ROOT/name)==sha,name
 spec=c.PROFILES["release-return-rtl"]
 _,raw=run(["xcodebuild","-version"],"xcode")
 assert raw.decode().strip()=="Xcode 27.0\nBuild version 27A266a"
 _,raw=run(["xcrun","simctl","create","Owned Release Selector "+uuid.uuid4().hex,spec["device"],spec["runtime"]],"create")
 udid=raw.decode().strip();uuid.UUID(udid)
 receipt["ownedSimulator"]=udid
 (WORK/"ownership.json").write_text(json.dumps(receipt,indent=2)+"\n")
 run(["xcrun","simctl","boot",udid],"boot",45)
 run(["xcrun","simctl","bootstatus",udid,"-b"],"bootstatus",120)
 original_descriptor=(BASE/"evidence/original.xctestrun").read_bytes()
 for stage in ["return-controls","preparation"]:
  scoped,binding=c.scope_descriptor(original_descriptor,"release-return-rtl",stage,products)
  value=plistlib.loads(scoped)
  target=value["TestConfigurations"][0]["TestTargets"][0]
  names=[x+"()" for x in spec["stages"][stage][0]]
  target["OnlyTestIdentifiers"]=names
  host=Path(binding["testHostPath"])
  value=rewrite(value,products,host)
  descriptor=WORK/(stage+".xctestrun");descriptor.write_bytes(plistlib.dumps(value,sort_keys=False))
  argv=["xcodebuild","test-without-building","-xctestrun",str(descriptor),"-destination","platform=iOS Simulator,id="+udid,"-parallel-testing-enabled","NO",*["-only-testing:AnytypeTests/"+n for n in names],"-enumerate-tests","-test-enumeration-style","flat","-test-enumeration-format","json","-test-enumeration-output-path",str(WORK/(stage+"-enumeration.json"))]
  run(argv,stage+"-enumeration",120)
  result=c.validate_enumeration(d.read(WORK/(stage+"-enumeration.json")),"release-return-rtl",stage,parser.enumerated_identifiers)
  receipt["stages"][stage]={"status":"PASS","actual":result,"descriptorSHA256":d.digest(descriptor),"selection":names}
 assert d.inventory(products)==expected
 receipt["originalInputsUnchanged"]=True;receipt["status"]="PASS"
except BaseException as e:
 receipt["failure"]={"type":type(e).__name__,"message":str(e)}
finally:
 if udid:
  receipt["shutdownExit"]=run(["xcrun","simctl","shutdown",udid],"shutdown",45,False)[0]
  receipt["deleteExit"]=run(["xcrun","simctl","delete",udid],"delete",45,False)[0]
  if receipt["deleteExit"]!=0:receipt["status"]="FAIL"
 (WORK/"result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print(json.dumps(receipt))
raise SystemExit(0 if receipt["status"]=="PASS" else 1)
