from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,re,shutil,subprocess,sys

root=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
debug=root/"Modules/PinkhaAnyHost/.build/x86_64-unknown-windows-msvc/debug"
work=root/"build/any-engine-port/native-recovery-boundary-components-v1"
swift=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
sdk=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk")
libraries=sdk.parents[1]/"Library"
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):h.update(data)
    return h.hexdigest()
def relative(path):return path.relative_to(root).as_posix()
def now():return datetime.now(timezone.utc).isoformat()
if shutil.disk_usage(root).free<2*1024**3:
    raise RuntimeError("Do not start: fewer than2GiB free")
work.mkdir(parents=True,exist_ok=True)
selected={"AnyNativeLibraryRecoveryTests.swift"}
ui=[root/"Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryRecovery.swift"]
presentation=[]
tests=[root/"Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeLibraryRecoveryTests.swift"]
executed=[f for f in tests if f.name in selected]
expected=[n for f in executed for n in re.findall(r"@Test\s+func\s+(\w+)",f.read_text(encoding="utf-8"))]
assert len(expected)==8 and len(set(expected))==8
sources=list(ui)+list(presentation)+list(tests)
for package in ["PinkhaAnyHost","PinkhaAnyEngine","PinkhaAnyIntegration","PinkhaKit"]:
    sources.extend((root/"Modules"/package/"Sources").rglob("*.swift"))
    sources.append(root/"Modules"/package/"Package.swift")
before={relative(f):digest(f) for f in sources}
objects=[Path(line.strip().strip('"')) for line in (debug/"pinkha-any-host-probe.product/Objects.LinkFileList").read_text().splitlines() if line.strip()]
excluded=[f for f in objects if "PinkhaAnyHostProbe.build" in str(f)]
objects=[f for f in objects if f not in excluded]
assert objects and all(f.is_file() for f in objects)
dependencies=objects+list((debug/"Modules").glob("*.swiftmodule"))
dependency_before={relative(f):digest(f) for f in dependencies}
(work/"objects.rsp").write_text("\n".join('"'+str(f)+'"' for f in objects),encoding="utf-8")
driver=work/"Run.swift"
driver.write_text("import Testing\n@main struct PortableUIComponents {\n static func main() async { await Testing.__swiftPMEntryPoint() as Never }\n}\n",encoding="utf-8")
common=[str(swift),"-swift-version","6","-parse-as-library","-enable-testing","-I",str(work),"-I",str(debug/"Modules"),"-module-cache-path",str(root/"build/any-engine-port/native-ui-portable-components-v2/ModuleCache"),"-sdk",str(sdk),"-use-ld=lld","-DSWIFT_PACKAGE","-DDEBUG"]
for module in ["CCryptoBoringSSLShims","CCryptoBoringSSL"]:
    include=root/"Modules/PinkhaAnyHost/.build/checkouts/swift-crypto/Sources"/module/"include"
    common+=["-Xcc","-fmodule-map-file="+str(include/"module.modulemap"),"-Xcc","-I"+str(include)]
for family in ["XCTest","Testing"]:
    path=libraries/(family+"-6.3.3")/"usr/lib/swift/windows"
    common+=["-I",str(path),"-I",str(path/"x86_64"),"-L",str(path/"x86_64")]
environment=os.environ.copy()
environment["PATH"]=os.pathsep.join([str(swift.parent),str(libraries/"Testing-6.3.3/usr/bin64"),str(libraries/"XCTest-6.3.3/usr/bin64"),environment.get("PATH","")])
provenance=root/"docs/any-engine-port/evidence/20261119/native-torah-workflow-20261119-201618-378627.json"
assert provenance.is_file()
steps=[]
receipt={
 "status":"RUNNING","scope":"Exact current production recovery source and8 original/focused recovery tests against source-bound cached native dependencies. No UIKit or native HTTP execution.",
 "startedAt":now(),"gitHEADBefore":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
 "expectedTests":expected,"expectedCount":8,"sourceBefore":before,"cachedDependenciesBefore":dependency_before,
 "cachedHostBuildProvenance":{"path":relative(provenance),"sha256":digest(provenance),"scope":"Successful Host build; its subsequent native probe failure is retained and not counted as a pass"},
 "actualAppleRegression":{"run":44609865615,"job":135864438257,"failedTest":"invalidSelectionAndMultipartRecoveryAreRefused","issue":"Emoji UTF16 offset1 was incorrectly accepted"},
 "driverSHA256":digest(driver),"runnerSHA256":digest(Path(__file__)),"steps":steps,"uiKitExecuted":False
}
out=root/"docs/any-engine-port/evidence/20261119/native-recovery-boundary-components-v1.json"
out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def run(label,command,timeout=120):
    logfile=work/(label+".log")
    with logfile.open("wb") as stream:
        result=subprocess.run(command,cwd=work,env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    steps.append({"step":label,"exitCode":result.returncode,"command":command,"log":relative(logfile),"logSHA256":digest(logfile)})
    if result.returncode:raise RuntimeError(label)
error=None
try:
    for module,inputs in [("PinkhaAnyUI",ui)]:
        run(module,common+["-module-name",module,"-whole-module-optimization","-emit-module","-emit-module-path",str(work/(module+".swiftmodule")),"-emit-object","-o",str(work/(module+".o"))]+[str(f) for f in inputs],120)
    run("all-ui-tests-typecheck",common+["-module-name","PinkhaAnyUITests","-typecheck"]+[str(f) for f in tests],120)
    run("component-link",common+["-module-name","PortableUIComponents",str(driver)]+[str(f) for f in executed]+[str(work/"PinkhaAnyUI.o"),"@"+str(work/"objects.rsp"),"-o",str(work/"validation.exe"),"-Xlinker","/threads:1","-Xlinker","/debug:none"],120)
    run("component-tests",[str(work/"validation.exe")],60)
except Exception as problem:
    error=type(problem).__name__+": "+str(problem)
testlog=work/"component-tests.log"
text=testlog.read_text(encoding="utf-8",errors="replace") if testlog.exists() else ""
passed=re.findall(r"Test (\w+)\(\) passed",text)
summaries=re.findall(r"Test run with (\d+) tests? in (\d+) suites? passed",text)
after={relative(f):digest(f) for f in sources}
dependency_after={relative(f):digest(f) for f in dependencies}
success=(error is None and set(passed)==set(expected) and len(passed)==8 and summaries and int(summaries[-1][0])==8 and before==after and dependency_before==dependency_after)
receipt.update(status="PASS" if success else "FAIL",finishedAt=now(),error=error,passedTests=passed,executedTests=len(passed),sourceAfter=after,sourceStable=before==after,cachedDependenciesAfter=dependency_after,cachedDependenciesStable=dependency_before==dependency_after,gitHEADAfter=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),steps=steps,binarySHA256=digest(work/"validation.exe") if (work/"validation.exe").exists() else None,freeBytesAfter=shutil.disk_usage(root).free)
out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:receipt[k] for k in ["status","error","executedTests","sourceStable","cachedDependenciesStable","freeBytesAfter"]},ensure_ascii=False),flush=True)
if not success:
    for step in steps[-2:]:print((root/step["log"]).read_text(encoding="utf-8",errors="replace")[-14000:])
else:print(text[-12000:])
sys.exit(0 if success else 1)
