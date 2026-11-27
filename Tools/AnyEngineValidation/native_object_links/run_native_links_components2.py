#!/usr/bin/env python3
import hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
PACKAGE=ROOT/"Modules/PinkhaAnyEngine"
OUT=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127/native-links-components2")
OUT.mkdir(parents=True,exist_ok=False)
scratch="/tmp/pinkha-w1-engine-contracts-indexed-20261127"
cache="/tmp/pinkha-w1-engine-contracts-cache-20261127"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(PACKAGE.rglob("*"))
        if p.is_file() and (p.suffix in (".swift",".py") or p.name=="Package.resolved") and ".build" not in p.parts}
def write(v):(OUT/"result.json").write_text(json.dumps(v,indent=2)+"\n")
r={"status":"RUNNING","sourceBefore":sources(),"controllerSHA256":sha(pathlib.Path(__file__)),
   "started":time.time(),"freeBefore":shutil.disk_usage("/").free,
   "componentScope":"native API parser, loopback HTTP and lifetime; not native index-delivery or ACL acceptance",
   "nativeAcceptance":False,"original182Rerun":False}
cmd=["/usr/local/bin/swift","test","--package-path",str(PACKAGE),"--scratch-path",scratch,
     "--cache-path",cache,"--skip-update","--enable-index-store","--jobs","2",
     "--filter","AnyNativeObjectLinksTests|AnyNativeObjectLinksHTTPTests",
     "--skip-build","--xunit-output",str(OUT/"tests.xml")]
r["command"]=cmd
previous=OUT.parent/"native-links-components1"
baseline=json.loads((previous/"result.json").read_text())
assert baseline["status"]=="FAIL" and baseline["returncode"]==-9 and baseline["sourceUnchanged"]
assert "Build complete! (24.90 secs)" in (previous/"swift.log").read_text()
changed=[p for p in r["sourceBefore"] if r["sourceBefore"][p]!=baseline["sourceBefore"].get(p)]
assert changed==["Modules/PinkhaAnyEngine/Tests/Fixtures/native_links_server.py"], changed
runner=pathlib.Path(scratch)/"out/Products/Debug-linux-aarch64/PinkhaAnyEngineTests-test-runner"
r["reusedBuild"]={"result":str(previous/"result.json"),"sha256":sha(previous/"result.json"),
                 "runner":str(runner),"runnerSHA256":sha(runner),"onlyRuntimeFixtureChanged":changed,
                 "originalCompilerSeconds":24.90,"newBuilds":0}

expected=set()
text=(PACKAGE/"Tests/PinkhaAnyEngineTests/AnyNativeObjectLinksTests.swift").read_text()
current=None
for line in text.splitlines():
    m=re.match(r"final class (AnyNativeObjectLinks\w*Tests):",line)
    if m:current=m.group(1)
    m=re.search(r"func (test\w+)\(",line)
    if m:expected.add(current+"."+m.group(1))
assert len(expected)==13
r["expectedMethods"]=sorted(expected)
write(r)
p=None
try:
    assert r["freeBefore"]>=2*1024**3+128*1024**2, "Swift components storage preflight"
    with (OUT/"swift.log").open("x") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        r["pid"]=p.pid;write(r)
        while p.poll() is None:
            assert shutil.disk_usage("/").free>=2*1024**3,"Swift components storage floor"
            assert time.time()-r["started"]<600,"Swift components deadline"
            time.sleep(1)
        r["returncode"]=p.returncode
    output=(OUT/"swift.log").read_text(errors="replace")
    started=re.findall(r"Test Case '(AnyNativeObjectLinks\w*Tests\.test\w+)' started",output)
    terminal=re.findall(r"Test Case '(AnyNativeObjectLinks\w*Tests\.test\w+)' (passed|failed|skipped)",output)
    r["startedMethods"]=started;r["terminalMethods"]=terminal
    assert r["returncode"]==0,"Swift command failed"
    assert len(started)==len(expected) and set(started)==expected,"actual started methods differ"
    assert len(terminal)==len(expected) and {x[0] for x in terminal}==expected and all(x[1]=="passed" for x in terminal),"actual terminal methods differ"
    assert "Executed 13 tests, with 0 failures" in output,"actual XCTest aggregate differs"
    assert "skipped" not in output.lower(),"unexpected skipped test"
    r["status"]="PASS_COMPONENT_13_METHODS_ZERO_SKIPS"
except BaseException as e:
    r["status"]="FAIL";r["failure"]=str(e)
    (OUT/"traceback.txt").write_text(traceback.format_exc())
finally:
    if p is not None and p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
    if p is not None:
        try:os.killpg(p.pid,0);r["groupAbsent"]=False
        except ProcessLookupError:r["groupAbsent"]=True
        if not r["groupAbsent"]:r["status"]="FAIL"
    active=[]
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():continue
        try:
            args=(proc/"cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace")
            if (str(runner)+" ") in args or ("python3 -B "+str(PACKAGE/"Tests/Fixtures/native_links_server.py")+" ") in args:
                active.append({"pid":int(proc.name),"command":args})
        except OSError:pass
    r["ownedFixtureAndRunnerProcessesAfter"]=active
    if active:r["status"]="FAIL"
    r["sourceAfter"]=sources();r["sourceUnchanged"]=r["sourceBefore"]==r["sourceAfter"]
    if not r["sourceUnchanged"]:r["status"]="FAIL"
    r["finished"]=time.time();r["freeAfter"]=shutil.disk_usage("/").free
    if (OUT/"swift.log").exists():r["logSHA256"]=sha(OUT/"swift.log")
    r["xunitArtifacts"]={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in OUT.glob("*.xml")}
    r["xunitNote"]="XCTest names and terminal status are qualified from original console; Swift Testing XML is not substituted."
    write(r)
    print(json.dumps({"status":r["status"],"failure":r.get("failure"),"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json")}))
    if (OUT/"swift.log").exists():print((OUT/"swift.log").read_text(errors="replace")[-12000:])
