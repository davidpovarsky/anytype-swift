#!/usr/bin/env python3
"""One offline dependency enumeration; no compile or native method execution."""
import hashlib, json, os, pathlib, shutil, signal, stat, subprocess, time
from datetime import datetime, timezone

ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-native-owned-snapshot-20261123")
OUT=pathlib.Path("/mnt/development/projects/diagnostics/native-owned-snapshot-dependency-plan-20261123")
GO=pathlib.Path("/mnt/development/toolchains/go1.27.4/go/bin/go")
MOD=pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache/go-mod")
CACHE=pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-build-glibc")
GOPATH=pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-path")
FIELDS=("GoFiles","CgoFiles","CFiles","CXXFiles","MFiles","HFiles","FFiles","SFiles","SysoFiles","EmbedFiles","TestGoFiles","XTestGoFiles")
def require(ok,reason):
    if not ok: raise RuntimeError(reason)
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
    return h.hexdigest()
def save(name,obj):
    p=OUT/name
    with p.open("x") as f:json.dump(obj,f,sort_keys=True,indent=2);f.write("\n")
    p.chmod(0o600)
def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args],timeout=30).decode().strip()
def physical(p):
    st=p.lstat()
    require(stat.S_ISREG(st.st_mode) and not p.is_symlink(),"source_not_regular")
    return {"sha256":sha(p),"bytes":st.st_size,"mode":stat.S_IMODE(st.st_mode)}
def native_snapshot():
    raw=subprocess.check_output(["git","-C",str(ROOT),"ls-files","--cached","--others","--exclude-standard","-z"],timeout=30)
    return {rel:physical(ROOT/rel) for rel in sorted(set(raw.decode().split("\0"))-set([""]))
            if (rel.endswith(".go") or rel in ("go.mod","go.sum")) and (ROOT/rel).is_file()}
def parse(raw):
    d=json.JSONDecoder();at=0
    while at<len(raw):
        while at<len(raw) and raw[at].isspace():at+=1
        if at==len(raw):break
        v,at=d.raw_decode(raw,at);yield v
def kill_owned(child):
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        child.wait(timeout=5)
def main():
    require(shutil.disk_usage(ROOT).free>=2950000000,"dependency_plan_start_capacity")
    require(not OUT.exists(),"plan_original_already_exists")
    OUT.mkdir(mode=0o700);(OUT/"tmp").mkdir(mode=0o700)
    env=dict(os.environ,GOMAXPROCS="1",CGO_ENABLED="1",GOPROXY="off",GOSUMDB="off",GOTOOLCHAIN="local",GOFLAGS="",GOEXPERIMENT="",GOWORK="off",
             GOPATH=str(GOPATH),GOMODCACHE=str(MOD),GOCACHE=str(CACHE),TMPDIR=str(OUT/"tmp"),GOTMPDIR=str(OUT/"tmp"))
    argv=[str(GO),"list","-mod=readonly","-deps","-test","-json","-tags=pinkha_localstore_witness","./core/pinkha/localstorewitness"]
    result={"status":"FAILED","kind":"offline-source-dependency-enumeration-only","builds":0,"native_methods":0,
            "argv":argv,"cwd":str(ROOT),"native_head":git("rev-parse","HEAD"),"native_status":git("status","--porcelain"),
            "reader_sha256":sha(pathlib.Path(__file__)),"started":datetime.now(timezone.utc).isoformat(),
            "free_before":shutil.disk_usage(ROOT).free}
    child=None;before=None
    try:
        before=native_snapshot();save("native-before.json",before)
        require(sha(GO)=="59c65090beeda377c09007eb8fae1c6aadf0a7b551e65ee13d461092d29e8005","go_binary_changed")
        result["go_binary_sha256"]=sha(GO)
        result["go_version"]=subprocess.check_output([str(GO),"version"],env=env,timeout=20).decode().strip()
        require(result["go_version"]=="go version go1.27.4 linux/arm64","go_version_changed")
        result["environment"]={k:env[k] for k in ("GOMAXPROCS","CGO_ENABLED","GOPROXY","GOSUMDB","GOTOOLCHAIN","GOFLAGS","GOEXPERIMENT","GOWORK","GOPATH","GOMODCACHE","GOCACHE","TMPDIR","GOTMPDIR")}
        start=time.monotonic()
        with (OUT/"go-list.stdout").open("xb") as stdout,(OUT/"go-list.stderr").open("xb") as stderr:
            os.chmod(OUT/"go-list.stdout",0o600);os.chmod(OUT/"go-list.stderr",0o600)
            child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            result["pid"]=child.pid;result["pgid"]=os.getpgid(child.pid);result["interruption"]=None
            require(result["pid"]==result["pgid"],"owned_session_identity")
            while child.poll() is None:
                if shutil.disk_usage(ROOT).free<2600000000 or time.monotonic()-start>=120:
                    result["interruption"]="capacity" if shutil.disk_usage(ROOT).free<2600000000 else "timeout"
                    kill_owned(child);break
                time.sleep(0.25)
            result["returncode"]=child.wait();stdout.flush();stderr.flush()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        result["owned_group_absent"]=absent;result["elapsed_seconds"]=time.monotonic()-start
        require(absent and result["returncode"]==0 and result["interruption"] is None,"source_enumeration_failed")
        rows=list(parse((OUT/"go-list.stdout").read_text()))
        files={};modules={};missing=[];package_sources=[]
        for pkg in rows:
            require(not pkg.get("Error") and not pkg.get("DepsErrors"),"resolved_package_error")
            directory=pkg.get("Dir")
            package_sources.append({k:pkg[k] for k in ("ImportPath","Dir","ForTest","Standard","Module","Imports")+FIELDS if k in pkg})
            if directory:
                for field in FIELDS:
                    for rel in pkg.get(field,[]):
                        p=pathlib.Path(directory)/rel
                        if p.is_file():files[str(p.resolve())]=physical(p)
                        else:missing.append({"package":pkg.get("ImportPath"),"field":field,"path":str(p)})
            mod=pkg.get("Module")
            if mod:
                modules[mod["Path"]]=mod
                for m in (mod,mod.get("Replace",{})):
                    gp=m.get("GoMod")
                    if gp and pathlib.Path(gp).is_file():files[str(pathlib.Path(gp).resolve())]=physical(pathlib.Path(gp))
        for rel in ("go.mod","go.sum"):files[str(ROOT/rel)]=physical(ROOT/rel)
        require(not missing,"unmaterialized_reported_dependency")
        require(all(str(ROOT/rel) in files for rel in ("core/pinkha/localstorewitness/native_capture.go","core/pinkha/localstorewitness/native_capture_test.go","space/spacecore/storage/anystorage/owned_snapshot.go")),"new_native_dependency_missing")
        require(not any("tantivy" in p.lower() for p in files),"unexpected_tantivy_dependency")
        save("package-inputs.json",package_sources);save("dependency-inputs.json",files);save("resolved-modules.json",modules)
        after=native_snapshot();save("native-after.json",after);require(after==before,"native_source_changed_during_enumeration")
        result.update(status="PASS_SOURCE_ENUMERATION_ONLY",packages=len(rows),dependency_files=len(files),native_files=sum(str(ROOT)+"/" in p for p in files),modules=len(modules),missing=missing,
                      dependency_sha256=sha(OUT/"dependency-inputs.json"),modules_sha256=sha(OUT/"resolved-modules.json"))
    except BaseException as e:
        result["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        if child is not None and child.poll() is None:kill_owned(child)
        if before is not None and not (OUT/"native-after.json").exists():
            try:save("native-after.json",native_snapshot())
            except BaseException as e:result["source_after_error"]={"type":type(e).__name__,"message":str(e)}
        result["finished"]=datetime.now(timezone.utc).isoformat();result["free_after"]=shutil.disk_usage(ROOT).free
        result["originals"]={p.name:physical(p) for p in OUT.iterdir() if p.is_file()}
        save("result.json",result)
        print(json.dumps({"status":result["status"],"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),"files":result.get("dependency_files"),"free_bytes":result["free_after"]}))
if __name__=="__main__":main()
