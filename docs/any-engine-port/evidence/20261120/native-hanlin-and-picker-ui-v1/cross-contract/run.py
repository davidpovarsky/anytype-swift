from pathlib import Path
import json,hashlib,subprocess,datetime,time,os,shutil
r=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
e=r/"docs/any-engine-port/evidence/20261120/native-hanlin-and-picker-ui-v1"
d=r/"build/any-engine-port/hanlin-ui-cross-contract-v1"
swift=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
runtime=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
source=r/"NativeApp/UITests/NativeLaunchTests.swift"
helper=e/"HanlinFixtureSupport.exact.swift"
inputs=e/"cross-contract/inputs.json"
producer=r/"build/any-engine-port/hanlin-provider-fixture-validation-v3/lifecycle/result.json"
paths=[source,helper,inputs,producer,d/"CrossContract.swift"]+sorted((e/"cross-contract/received").glob("*.json"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(r)):sha(p) for p in paths}
assert shutil.disk_usage(d).free>536870912,"Insufficient task build headroom"
env=os.environ.copy();env["PATH"]=str(swift.parent)+os.pathsep+str(runtime)+os.pathsep+env.get("PATH","")
exe=d/"HanlinFixtureCrossContract.exe"
phases=[]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
commands=[
("native-launch-syntax",[str(swift),"-frontend","-parse",str(source)],45),
("cross-contract-compile",[str(swift),"-swift-version","6","-parse-as-library","-module-name","HanlinFixtureCrossContract","-module-cache-path",str(d/"module-cache"),"-j","1",str(d/"CrossContract.swift"),"-o",str(exe)],75),
("cross-contract-run",[str(exe),str(inputs)],15)]
for name,args,deadline in commands:
 start=time.monotonic()
 logPath=e/"cross-contract"/(name+".log")
 with logPath.open("wb") as log:
  p=subprocess.Popen(args,cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT)
  timeout=False
  try:code=p.wait(timeout=deadline)
  except subprocess.TimeoutExpired:
   timeout=True
   subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   code=p.wait(timeout=10)
 phases.append({"name":name,"command":args,"exitCode":code,"timedOut":timeout,"seconds":round(time.monotonic()-start,3),"log":str(logPath.relative_to(r)),"logSHA256":sha(logPath)})
 if code!=0 or timeout:break
after={str(p.relative_to(r)):sha(p) for p in paths}
execution=None
if len(phases)==3:
 try: execution=json.loads((e/"cross-contract/cross-contract-run.log").read_text(encoding="utf-8"))
 except Exception as ex:execution={"status":"UNPARSEABLE","errorType":type(ex).__name__}
result={"schema":1,"scope":"Source-bound Python actual HTTPS response snapshots decoded by exact Swift Foundation helper; no network/trust/UIKit/native acceptance execution.",
"startedUTC":started,"finishedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"sourceBefore":before,"sourceAfter":after,"sourceStable":before==after,"phases":phases,
"executableSHA256":sha(exe) if exe.exists() else None,"execution":execution,
"status":"PASS" if len(phases)==3 and all(p["exitCode"]==0 and not p["timedOut"] for p in phases) and before==after and execution and execution.get("status")=="PASS" else "FAIL"}
(e/"cross-contract/result-v1.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({"status":result["status"],"sourceStable":result["sourceStable"],"phases":phases,"execution":execution,"receiptSHA256":sha(e/"cross-contract/result-v1.json")}))
