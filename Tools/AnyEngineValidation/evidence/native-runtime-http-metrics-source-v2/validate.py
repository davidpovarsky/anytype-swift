import datetime,hashlib,json,os,pathlib,subprocess,time
root=pathlib.Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
work=root/"build/any-engine-port/runtime-http-metrics-v2"
out=root/"Tools/AnyEngineValidation/evidence/native-runtime-http-metrics-source-v2"
source=root/"Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyEmbeddedRuntimeTests.swift"
swift=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/"validation.json").exists()
before=digest(source);helper=(out/"observer.swift").read_text(encoding="utf-8")
check=work/"ObserverTypecheck.swift"
check.write_text("import Foundation\nimport FoundationNetworking\n"+helper,encoding="utf-8")
stages=[]
def run(name,args,limit):
 t=time.monotonic()
 proc=subprocess.Popen(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 timed=False
 try:stdout,stderr=proc.communicate(timeout=limit)
 except subprocess.TimeoutExpired:
  timed=True
  if proc.poll() is None:
   subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
  stdout,stderr=proc.communicate(timeout=10)
 (out/(name+".stdout.log")).write_bytes(stdout)
 (out/(name+".stderr.log")).write_bytes(stderr)
 row={"name":name,"args":args,"deadlineSeconds":limit,"durationSeconds":round(time.monotonic()-t,3),"exitCode":proc.returncode,"timedOut":timed,"stdoutBytes":len(stdout),"stderrBytes":len(stderr),"stdoutSHA256":hashlib.sha256(stdout).hexdigest(),"stderrSHA256":hashlib.sha256(stderr).hexdigest()}
 stages.append(row)
 return proc.returncode==0 and not timed
syntax=run("ios-syntax",[str(swift),"-frontend","-parse","-target","arm64-apple-ios18.4-simulator",str(source)],45)
typecheck=False
if syntax:
 typecheck=run("portable-helper-typecheck",[str(swift),"-typecheck","-swift-version","6","-module-cache-path",str(work/"ModuleCache"),str(check)],60)
stable=before==digest(source)
result={"status":"PASS_SYNTAX_AND_PORTABLE_HELPER_TYPECHECK" if syntax and typecheck and stable else "FAIL_VALIDATION","capturedAtUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"sourceSHA256":before,"sourceStable":stable,"helperSHA256":digest(out/"observer.swift"),"typecheckInputSHA256":digest(check),"compilerSHA256":digest(swift),"stages":stages,"actualAppleSemanticOrRuntimeTests":0,"HTTPRequests":0,"scope":"Full test syntax for iOS target using Windows compiler; exact helper Swift6 typecheck against installed FoundationNetworking declarations. Neither is actual Apple compilation/execution."}
(out/"validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":result["status"],"sourceStable":stable,"stages":stages}))
raise SystemExit(0 if syntax and typecheck and stable else 1)
