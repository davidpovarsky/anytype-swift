#!/usr/bin/env python3
"""Qualify 18 body methods after fixture-only graceful teardown repair; no rebuild."""
import gzip,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
PACKAGE=ROOT/"Modules/PinkhaAnyEngine"
OUT=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-components2")
OUT.mkdir(parents=True,exist_ok=False)
SCRATCH=pathlib.Path("/tmp/pinkha-w1-engine-contracts-indexed-20261127")
CACHE="/tmp/pinkha-w1-engine-contracts-cache-20261127"
RUNNER=SCRATCH/"out/Products/Debug-linux-aarch64/PinkhaAnyEngineTests-test-runner"
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(PACKAGE.rglob("*"))
            if p.is_file() and (p.suffix in (".swift",".py") or p.name=="Package.resolved") and ".build" not in p.parts}
def mem():
    return int(next(x.split()[1] for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")))*1024
def write():
    (OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
r={"status":"RUNNING","sourceBefore":sources(),"controllerSHA256":sha(pathlib.Path(__file__)),
   "started":time.time(),"freeBefore":shutil.disk_usage("/").free,"memAvailableBefore":mem(),
   "componentScope":"18 new scoped Markdown CAS, actual loopback HTTP, ambiguous write retention and authority fences; not native engine proof",
   "nativeAcceptance":False,"original182Rerun":False,"previous28Rerun":False}
cmd=["/usr/local/bin/swift","test","--skip-build","--package-path",str(PACKAGE),"--scratch-path",str(SCRATCH),
     "--cache-path",CACHE,"--skip-update","--enable-index-store","--jobs","2",
     "--filter","AnyNativeMarkdownBodyTests|AnyNativeMarkdownBodyHTTPTests",
     "--xunit-output",str(OUT/"tests.xml")]
r["command"]=cmd
write()
p=None
try:
    prior=OUT.parent/"file-durability-corrected1/result.json"
    accepted=json.loads(prior.read_text())
    assert accepted["status"]=="PASS_COMPONENT_28_METHODS_ZERO_SKIPS"
    assert accepted["sourceUnchanged"] is True
    old=accepted["sourceAfter"]
    assert all(r["sourceBefore"].get(k)==v for k,v in old.items()),"accepted production/test source changed"
    added=sorted(set(r["sourceBefore"])-set(old))
    wanted=sorted([
      "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyNativeMarkdownBody.swift",
      "Modules/PinkhaAnyEngine/Tests/Fixtures/markdown_body_server.py",
      "Modules/PinkhaAnyEngine/Tests/PinkhaAnyEngineTests/AnyNativeMarkdownBodyTests.swift",
      "Modules/PinkhaAnyEngine/Tests/PinkhaAnyEngineTests/AnyNativeMarkdownBodyNativeTests.swift"])
    assert added==wanted,(added,wanted)
    pins={
      wanted[0]:"7097c7c5f7bbf67eba21a961986a892064a1833425ff74b053917a0d4e11e4af",
      "Modules/PinkhaAnyEngine/Tests/Fixtures/markdown_body_server.py":"6b44579d6ef201c609c387ca96d86d905df90e3eadf52dd5f0886f00b6f326d5",
      "Modules/PinkhaAnyEngine/Tests/PinkhaAnyEngineTests/AnyNativeMarkdownBodyTests.swift":"e6831b865f4ab7168b60f6783765a056703c4c5a3dbe24a39a9565b3a0687dd0",
      "Modules/PinkhaAnyEngine/Tests/PinkhaAnyEngineTests/AnyNativeMarkdownBodyNativeTests.swift":"f2864d15f4407ab9434062a9066d5897d7e9e5c4f6c6f51d4566a7efde11078c"}
    assert all(r["sourceBefore"][k]==v for k,v in pins.items()),"new source pins differ"
    r["reusedAccepted28"]={"path":str(prior),"sha256":sha(prior),"unchangedOriginalSourceFiles":len(old),"added":added}
    r["dependencyAlternates"]=[]
    for alt in sorted((SCRATCH/"checkouts").glob("*/.git/objects/info/alternates")):
        values=alt.read_text().splitlines()
        assert values and all(pathlib.Path(v).is_dir() for v in values),"missing owned dependency mirror"
        assert all(pathlib.Path(v).is_relative_to(SCRATCH/"repositories") for v in values),"foreign dependency alternate"
        r["dependencyAlternates"].append({"path":str(alt),"sha256":sha(alt),"targets":values})
    current=None;expected=set()
    test=PACKAGE/"Tests/PinkhaAnyEngineTests/AnyNativeMarkdownBodyTests.swift"
    for line in test.read_text().splitlines():
        m=re.match(r"final class (AnyNativeMarkdownBody(?:HTTP)?Tests):",line)
        if m:current=m.group(1)
        m=re.search(r"func (test\w+)\(",line)
        if m:
            assert current
            expected.add(current+"."+m.group(1))
    assert len(expected)==18
    r["expectedMethods"]=sorted(expected)
    assert r["freeBefore"]>=2*1024**3+16*1024**2,"Swift storage preflight"
    assert r["memAvailableBefore"]>=512*1024**2,"Swift memory preflight"
    failed=OUT.parent/"markdown-body-components1/result.json"
    failure=json.loads(failed.read_text())
    assert failure["status"]=="FAIL" and failure["failure"]=="Swift components deadline"
    assert failure["sourceUnchanged"] is True
    changes=[k for k,v in r["sourceBefore"].items() if failure["sourceAfter"].get(k)!=v]
    assert changes==["Modules/PinkhaAnyEngine/Tests/Fixtures/markdown_body_server.py"]
    assert set(r["sourceBefore"])==set(failure["sourceAfter"])
    assert sha(RUNNER)==failure["runnerSHA256"]
    assert "Build complete! (19.71 secs)" in (failed.parent/"swift.log").read_text()
    stopped=failed.parent/"fixture-teardown-stop2/result.json"
    assert sha(stopped)=="abdb25ad0a139ad8a3172178db2c4388fb47384121e54f2a1a92671790ae21be"
    assert json.loads(stopped.read_text())["allCapturedOwnedProcessesStopped"] is True
    r["runnerBeforeSHA256"]=sha(RUNNER)
    r["unacceptedPriorRun"]={"result":str(failed),"sha256":sha(failed),"failedReason":failure["failure"],
        "actualCompileSeconds":19.71,"unchangedSwiftSources":True,"fixtureOnlyChanges":changes,
        "cleanupReceipt":str(stopped),"cleanupSHA256":sha(stopped),"skipBuild":True}
    write()
    with (OUT/"swift.log").open("x") as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        r["pid"]=p.pid;write()
        while p.poll() is None:
            assert shutil.disk_usage("/").free>=2*1024**3,"Swift storage floor"
            assert time.time()-r["started"]<180,"Swift components deadline"
            time.sleep(1)
        r["returncode"]=p.returncode
    output=(OUT/"swift.log").read_text(errors="replace")
    pattern=r"(AnyNativeMarkdownBody(?:HTTP)?Tests\.test\w+)"
    started=re.findall(r"Test Case '"+pattern+r"' started",output)
    terminal=re.findall(r"Test Case '"+pattern+r"' (passed|failed|skipped)",output)
    r["startedMethods"]=started;r["terminalMethods"]=terminal
    assert r["returncode"]==0,"Swift command failed"
    assert len(started)==len(expected) and set(started)==expected,"actual started methods differ"
    assert len(terminal)==len(expected) and {x[0] for x in terminal}==expected and all(x[1]=="passed" for x in terminal),"actual terminal methods differ"
    assert "Executed 18 tests, with 0 failures" in output,"actual XCTest aggregate differs"
    assert "skipped" not in output.lower(),"unexpected skipped test"
    r["status"]="PASS_COMPONENT_18_METHODS_ZERO_SKIPS"
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
            if (str(RUNNER)+" ") in args or ("python3 -B "+str(PACKAGE/"Tests/Fixtures/markdown_body_server.py")+" ") in args:
                active.append({"pid":int(proc.name),"command":args})
        except OSError:pass
    r["ownedFixtureAndRunnerProcessesAfter"]=active
    if active:r["status"]="FAIL"
    r["sourceAfter"]=sources();r["sourceUnchanged"]=r["sourceBefore"]==r["sourceAfter"]
    if not r["sourceUnchanged"]:r["status"]="FAIL"
    r["finished"]=time.time();r["freeAfter"]=shutil.disk_usage("/").free
    if RUNNER.exists():
        r["runnerSHA256"]=sha(RUNNER)
        r["runnerUnchanged"]=r["runnerSHA256"]==r.get("runnerBeforeSHA256")
        if not r["runnerUnchanged"]:r["status"]="FAIL"
    if (OUT/"swift.log").exists():r["logSHA256"]=sha(OUT/"swift.log")
    r["xunitArtifacts"]={q.name:{"sha256":sha(q),"bytes":q.stat().st_size} for q in OUT.glob("*.xml")}
    r["xunitNote"]="Actual XCTest started/terminal methods from original console; empty Swift Testing XML is not substituted."
    write()
    print(json.dumps({"status":r["status"],"failure":r.get("failure"),"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json")}))
    if (OUT/"swift.log").exists():print((OUT/"swift.log").read_text(errors="replace")[-16000:])

raise SystemExit(0 if r["status"]=="PASS_COMPONENT_18_METHODS_ZERO_SKIPS" else 1)
