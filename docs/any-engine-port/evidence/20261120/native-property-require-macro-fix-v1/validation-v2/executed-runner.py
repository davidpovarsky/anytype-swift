from pathlib import Path
import os,json,hashlib,importlib.util,shutil,datetime
root=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
out=root/"build/any-engine-port/native-property-require-macro-fix-v1"
e=root/"docs/any-engine-port/evidence/20261120/native-property-require-macro-fix-v1"/ "validation-v2"
e.mkdir()
source=root/"Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helperPath=root/"Tools/AnyEnginePort/run_live_provider_probe.py"
spec=importlib.util.spec_from_file_location("owned_process_helper",helperPath)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
shutil.copyfile(__file__,e/"executed-runner.py")
shutil.copyfile(helperPath,e/"executed-process-helper.py")
swift=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
sdk=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk")
testing=sdk.parents[1]/"Library/Testing-6.3.3/usr/lib/swift/windows"
dll=sdk.parents[1]/"Library/Testing-6.3.3/usr/bin64"
runtime=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")
os.environ["PATH"]=os.pathsep.join(map(str,[swift.parent,runtime,dll]))+os.pathsep+os.environ.get("PATH","")
result={"schema":1,"status":"RUNNING","startedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Exact complete generic continuation helper extracted from actual source before/after the two-site macro fix. Swift 6 Windows typecheck with actual Testing macro plugin; full test-file syntax parse only. No execution of seven presentation-model tests, UIKit semantic compile, Apple runtime, or native authority claim.","source":str(source.relative_to(root)),"sourceSHA256":sha(source),"beforeHelperSHA256":sha(out/"BeforeHelper.swift"),"afterHelperSHA256":sha(out/"AfterHelper.swift"),"steps":[],"compilerSHA256":sha(swift),"testingMacrosSHA256":sha(swift.parent/"TestingMacros.dll"),"testingDLLSHA256":sha(dll/"Testing.dll")}
def save():
    (e/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
def run(name,args,seconds):
    d=e/name;d.mkdir()
    step={"name":name,**helper.run_process(args,out,d,seconds)}
    result["steps"].append(step);save()
    if step.get("timedOut") or step.get("cleanupErrors") or step.get("runnerErrorType") or not step.get("parentExited"):
        raise RuntimeError("process_boundary_failed:"+name)
    return step,d
save()
try:
    version,d=run("compiler-version",[str(swift),"-version"],20)
    assert version["exitCode"]==0
    common=[str(swift),"-typecheck","-swift-version","6","-parse-as-library","-target","x86_64-unknown-windows-msvc","-j1","-sdk",str(sdk),"-libc","MD","-I",str(testing),"-I",str(testing/"x86_64"),"-module-cache-path",str(out/"ModuleCache")]
    before,d=run("before-typecheck",common+[str(out/"BeforeHelper.swift")],60)
    diag=(d/"stderr.log").read_text(encoding="utf-8",errors="replace")
    count=sum(line.startswith("macro expansion #require:2:6: error: cannot use mutating member on immutable value: '$0' is immutable") for line in diag.splitlines())
    assert before["exitCode"]!=0 and count==2,(before["exitCode"],count,diag[:2000])
    result["originalFailureReproduced"]=True
    result["primaryDiagnosticCounting"]="Anchored primary compiler error lines; duplicated rendered expansion messages excluded."
    assert "BeforeHelper.swift:49:73" in diag and "BeforeHelper.swift:54:73" in diag
    result["originalFailureLocations"]=[49,54]
    result["originalMacroFailureCount"]=count
    after,d=run("after-typecheck",common+[str(out/"AfterHelper.swift")],60)
    assert after["exitCode"]==0
    result["correctedHelperTypecheckPassed"]=True
    parsed,d=run("full-source-parse",[str(swift),"-frontend","-parse",str(source)],30)
    assert parsed["exitCode"]==0
    result["fullSourceSyntaxParsePassed"]=True
    result["sourceStable"]=sha(source)==result["sourceSHA256"]
    result["helperInputsStable"]=sha(out/"BeforeHelper.swift")==result["beforeHelperSHA256"] and sha(out/"AfterHelper.swift")==result["afterHelperSHA256"]
    assert result["sourceStable"] and result["helperInputsStable"]
    result["status"]="PASS"
except Exception as ex:
    result["status"]="FAIL";result["failureType"]=type(ex).__name__;result["failure"]=str(ex)[:4000]
finally:
    result["finishedAt"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    print(json.dumps(result))
