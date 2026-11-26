#!/usr/bin/env python3
"""Original native StoreState/disk component qualification, not native transport."""
import argparse,datetime,hashlib,json,os,re,shutil,signal,subprocess,tarfile,time
from pathlib import Path

ARCHIVE=Path("/mnt/development/projects/evidence/native-d-final-20261125/native410b-inputs/native-source-410b441e5726.tar.gz")
ARCHIVE_SHA="eba6a0354006c9cfc363c4769bd08951d3b4be4ef3fa8a65eb0cde9b6376e008"
MANIFEST_SHA="410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9"
PINS={
"pkg/lib/pinkha/torahcutovercontract/contract.go":"a725194a6a3e43ec7b65c1279831e6ac8289871fac4b938cd41f5940194d89cc",
"pkg/lib/pinkha/torahcutovercontract/contract_test.go":"a600720c34e80532bc487bbc939c1e38059627b8f86ca1f43225deed91a3dfeb",
"core/block/editor/torahops/cutover_store.go":"cec81959c5112ed4e4255fe109f1fba72e71498d752f23f4a5803819ad00b752",
"core/block/editor/torahops/cutover_store_test.go":"3fe41a43d9b249d404f3e51a1571172cb16bb9116e3cd6d334985d7079cba1c7",
}
EXPECTED=[
"TestCutoverMetadataKeepsV1NamespaceAndOrdinaryClaims",
"TestCutoverMetadataIndependentDisksRetainActualComponentAuthors",
"TestCutoverMetadataRecordCollisionHasNoWinnerOrSilentRetry",
"TestCutoverMetadataCommitExitAndFrozenRetry",
"TestCutoverMetadataRefusesForeignAuthorSpaceAndMissingACL",
"TestCutoverMetadataNeverTruncatesHistoryOrHidesCrossObjectCollision",
"TestCutoverMetadataModifyDeleteAndRawWireForgeryRefuse",
"TestCutoverMetadataCancelledContextCannotWrite",
]
def digest(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(root,name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");temporary.replace(path)
def group_members(pgid):
    members=[]
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit():continue
        try:
            stat=(directory/"stat").read_text();fields=stat[stat.rfind(")")+2:].split()
            if int(fields[2])==pgid:members.append(int(directory.name))
        except (FileNotFoundError,ProcessLookupError):pass
    return sorted(members)
class Commands:
    def __init__(self,root):self.root=root;self.rows=[];self.absent=set()
    def run(self,name,argv,cwd,env,timeout):
        folder=self.root/"commands"/name;folder.mkdir(parents=True,exist_ok=False)
        row={"argv":argv,"cwd":str(cwd),"startedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start=time.monotonic()
        with (folder/"original.log").open("wb") as log:
            process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row.update(pid=process.pid,pgid=process.pid);save(folder,"started.json",row);self.rows.append(row)
            try:row["exitCode"]=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                row["timedOut"]=True
                for sig in (signal.SIGTERM,signal.SIGKILL):
                    try:os.killpg(process.pid,sig)
                    except ProcessLookupError:self.absent.add(process.pid);break
                    try:row["exitCode"]=process.wait(timeout=5);break
                    except subprocess.TimeoutExpired:continue
            try:
                remaining=[] if process.pid in self.absent else group_members(process.pid)
                row["ownedProcessGroupRemaining"]=remaining
                if not remaining:self.absent.add(process.pid)
            except Exception as error:row["observationError"]=type(error).__name__+": "+str(error)
        row.update(durationSeconds=time.monotonic()-start,logSHA256=digest(folder/"original.log"))
        save(folder,"result.json",row)
        if row.get("exitCode")!=0 or row.get("timedOut") or row.get("ownedProcessGroupRemaining")!=[]:
            raise RuntimeError("owned command failed: "+name)
        return folder/"original.log"
    def cleanup(self):
        failures=[]
        for row in self.rows:
            if row["pgid"] in self.absent:continue
            try:
                members=group_members(row["pgid"])
                if members:failures.append({"pgid":row["pgid"],"unresolvedMembers":members})
                else:self.absent.add(row["pgid"])
            except Exception as error:failures.append({"pgid":row["pgid"],"error":str(error)})
        return failures
def inventory(source,entries):
    result={}
    for relative in sorted(entries):
        path=source/relative
        if not path.is_file() or path.is_symlink():raise ValueError("not regular: "+relative)
        result[relative]={"bytes":path.stat().st_size,"sha256":digest(path)}
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--root",required=True,type=Path);args=parser.parse_args()
    root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
    result={"status":"FAIL","scope":"actual native StoreState/SQLite component only","nativePeers":0,"applicationTests":0}
    commands=Commands(root);entries={};source=root/"source"
    try:
        if digest(ARCHIVE)!=ARCHIVE_SHA:raise ValueError("original native archive hash")
        if shutil.disk_usage(root).free < 2*1024**3:raise ValueError("insufficient materialization/build headroom")
        source.mkdir()
        with tarfile.open(ARCHIVE,"r:gz") as archive:
            original=archive.extractfile("source-manifest.json").read()
            if hashlib.sha256(original).hexdigest()!=MANIFEST_SHA:raise ValueError("original native manifest")
            (root/"baseline-source-manifest.json").write_bytes(original)
            manifest=json.loads(original)
            if len(manifest["files"])!=4855:raise ValueError("original source census")
            for relative,expected in manifest["files"].items():
                path=Path(relative)
                if path.is_absolute() or ".." in path.parts:raise ValueError("unsafe archive member")
                member=archive.getmember(relative)
                if not member.isfile():raise ValueError("nonregular original member")
                raw=archive.extractfile(member).read()
                if len(raw)!=expected["bytes"] or hashlib.sha256(raw).hexdigest()!=expected["sha256"]:raise ValueError("original native bytes: "+relative)
                target=source/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            entries=dict(manifest["files"])
        overlay=Path(__file__).resolve().parent/"overlay"
        for relative,pin in PINS.items():
            donor=overlay/relative;target=source/"heart"/relative
            if donor.is_symlink() or digest(donor)!=pin or target.exists():raise ValueError("additive overlay pin: "+relative)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(donor.read_bytes())
            entries["heart/"+relative]={"bytes":target.stat().st_size,"sha256":pin}
        before=inventory(source,entries)
        if before!=entries:raise ValueError("complete native source materialization")
        save(root,"source-before.json",before)
        package=source/"heart/core/block/editor/torahops"
        selected=sorted(path.name for path in package.glob("*.go") if not path.name.endswith("_test.go"))
        selected+=["store_test.go","cutover_store_test.go"]
        if any(not (package/name).is_file() for name in selected):raise ValueError("missing original test/source")
        save(root,"compiled-source-selection.json",{"scope":"every actual torahops production file plus unchanged original store fixture/test source and the additive cutover tests","files":{name:before[str((package/name).relative_to(source))] for name in selected},"selectors":EXPECTED,"originalExistingMethodsInvoked":0})
        env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOCACHE=str(root/"cache"))
        env.pop("PINKHA_CUTOVER_COMPONENT_CHILD",None);env.pop("PINKHA_CUTOVER_COMPONENT_DB",None)
        commands.run("toolchain",["/usr/local/bin/go","version"],package,env,10)
        if (root/"commands/toolchain/original.log").read_text().strip()!="go version go1.27.4 linux/arm64":raise ValueError("unqualified Go")
        binary=root/"cutover-store.test"
        commands.run("build",["/usr/local/bin/go","test","-c","-mod=readonly","-p","1","-o",str(binary)]+selected,package,env,600)
        save(root,"binary.json",{"bytes":binary.stat().st_size,"sha256":digest(binary)})
        commands.run("binary-modules",["/usr/local/bin/go","version","-m",str(binary)],package,env,10)
        pattern="^("+"|".join(EXPECTED)+")$"
        log=commands.run("original-tests",["/usr/local/bin/go","tool","test2json","-t","-p","cutover-store-component",str(binary),"-test.v","-test.count=1","-test.run="+pattern],package,env,180)
        rows=[]
        for line in log.read_text().splitlines():
            try:rows.append(json.loads(line))
            except json.JSONDecodeError:continue
        passed=[row["Test"] for row in rows if row.get("Action")=="pass" and row.get("Test")]
        failed=[row.get("Test","package") for row in rows if row.get("Action")=="fail"]
        skipped=[row["Test"] for row in rows if row.get("Action")=="skip"]
        methods=[name for name in passed if "/" not in name]
        result.update(passedMethods=methods,passedCases=passed,failed=failed,skipped=skipped,originalLogSHA256=digest(log))
        if methods!=EXPECTED or len(passed)!=12 or failed or skipped:raise ValueError("exact original actual result did not qualify")
        after=inventory(source,entries);save(root,"source-after.json",after)
        if after!=before:raise ValueError("source changed during compile/run")
        result.update(status="PASS",sourceUnchanged=True,binarySHA256=digest(binary),sourceManifestSHA256=digest(root/"source-before.json"))
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    finally:
        try:
            failures=commands.cleanup();result["cleanupFailures"]=failures
            if failures:result["status"]="FAIL"
        except Exception as error:result["cleanupError"]=str(error);result["status"]="FAIL"
        result["commands"]=commands.rows
        save(root,"result.json",result)
    print(json.dumps(result))
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
