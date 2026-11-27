#!/usr/bin/env python3
"""Qualify the real cutover core on retained current8ac source. No RPC/Apple claim."""
import argparse, hashlib, json, os, signal, shutil, subprocess, tarfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE = Path("/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126")
OLD = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-core/attempt3/source")
CACHE = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1/cache")
GO = Path("/mnt/development/toolchains/go1.27.4/go/bin/go")
MANIFEST = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
ARCHIVE = "c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830"
CANDIDATE = "498d428d81a0b8146d22c6aec433f0cdc4d3da348fb9129747c860b39f83a9c4"
FIXTURE = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-host/shared-fixture-attempt1/swift-build/out/Products/Debug-linux-aarch64/CutoverSharedFixture")
FIXTURE_SHA = "6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7"
LIB_SHA = "eb659a16cf763a47b41c837eeeb10d8743ed5bb96eb4b675582b6ca7c5ebb5f7"
SUM_SHA = "0ce118248f3e2580833e915dbd3ef14925d3a71a1601e4c7d679b9217a368586"
METHOD = "TestPinkhaTorahCutoverActualCoreRegistryAndReopen"
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def row(path): return {"bytes":path.stat().st_size,"sha256":sha(path)}
def save(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def pinned(path,digest):
    assert path.is_file() and not path.is_symlink() and path.resolve()==path, str(path)
    assert sha(path)==digest, str(path)+" digest differs"
    return path
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--root",required=True,type=Path);args=parser.parse_args()
    root=args.root
    assert root.is_absolute() and str(root).startswith("/var/tmp/pinkha-e-cutover-current8ac-20261127/")
    assert root.parent.resolve()==root.parent and not root.exists()
    os.umask(0o077);root.mkdir(parents=True,mode=0o700)
    source=root/"source";source.mkdir()
    result={"status":"FAIL","baseManifestSHA256":MANIFEST,"candidateSHA256":CANDIDATE,
        "generatedRPC":False,"peerTransport":False,"appleUI":False,"commands":[]}
    expected=None
    def inventory():
        return {str(p.relative_to(source)):row(p) for p in sorted(source.rglob("*")) if p.is_file()}
    def run(label,argv,env,timeout):
        directory=root/"commands"/label;directory.mkdir(parents=True)
        start=time.time()
        with (directory/"original.log").open("wb") as out:
            proc=subprocess.Popen(argv,cwd=source/"heart",env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
            save(directory/"started.json",{"pid":proc.pid,"argv":argv,"startedUTC":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(start))})
            reason=None
            try:
                while proc.poll() is None:
                    if time.time()-start>timeout:reason="timeout";break
                    if min(shutil.disk_usage(root).free,shutil.disk_usage(CACHE).free)<512*1024*1024:reason="actual ENOSPC risk";break
                    time.sleep(1)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
        absent=False
        try:os.killpg(proc.pid,0)
        except ProcessLookupError:absent=True
        receipt={"argv":argv,"pid":proc.pid,"exitCode":proc.returncode,"seconds":time.time()-start,
            "processGroupAbsent":absent,"stopReason":reason,"logSHA256":sha(directory/"original.log")}
        save(directory/"result.json",receipt);result["commands"].append(receipt)
        assert proc.returncode==0 and absent and reason is None, label+" failed"
        return directory/"original.log"
    try:
        pinned(BASE/"source-manifest.json",MANIFEST)
        archive=pinned(BASE/"native-source-8ac407e75a4b.tar.gz",ARCHIVE)
        manifest=json.loads((BASE/"source-manifest.json").read_text())["files"]
        candidate=json.loads(pinned(HERE/"native-core-current8ac-candidate.json",CANDIDATE).read_text())
        assert len(manifest)==4868
        with tarfile.open(archive) as tar:
            members=tar.getmembers()
            assert all(m.isfile() and (m.name in manifest or m.name == "source-manifest.json") and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts for m in members), "unexpected archive member"
            assert len(members)==len(manifest)+1 and len({m.name for m in members})==len(members), "exact archive census"
            embedded=tar.extractfile("source-manifest.json").read()
            assert embedded==(BASE/"source-manifest.json").read_bytes(), "embedded manifest differs"
            tar.extractall(source,members=[m for m in members if m.name in manifest],filter="data")
        assert inventory()==manifest,"base archive/source manifest mismatch"
        changes=[]
        for rel,expectedRow in candidate["sourceFiles"].items():
            donor=HERE/"overlay"/rel
            assert row(donor)==expectedRow, rel
            dest=source/"heart"/rel
            original=manifest.get("heart/"+rel)
            if original and original!=expectedRow:assert candidate["originalReplacements"].get(rel)==original, "unreviewed replacement "+rel
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest)
            changes.append({"path":"heart/"+rel,"before":original,"after":expectedRow})
        lib=pinned(OLD/"heart/deps/libs/linux-arm64-musl/libtantivy_go.a",LIB_SHA)
        dest=source/"heart/deps/libs/linux-arm64-musl/libtantivy_go.a";dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib,dest)
        sums=pinned(OLD/"go.work.sum",SUM_SHA).read_bytes();oldSums=(source/"go.work.sum").read_bytes()
        assert set(oldSums.splitlines())<=set(sums.splitlines()),"qualified checksum additions must retain every current source checksum"
        (source/"go.work.sum").write_bytes(sums)
        save(root/"materialization.json",{"changes":changes,"library":row(lib),"originalGoWorkSumSHA256":hashlib.sha256(oldSums).hexdigest(),
            "qualifiedGoWorkSumSHA256":SUM_SHA,"addedChecksumLines":[x.decode() for x in sums.splitlines() if x not in oldSums.splitlines()]})
        pinned(FIXTURE,FIXTURE_SHA)
        temporary=root/"temporary";temporary.mkdir();private=root/"private";private.mkdir(mode=0o700)
        env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOMEMLIMIT="2GiB",
            GOCACHE=str(CACHE),CGO_ENABLED="1",CGO_LDFLAGS="-L"+str(dest.parent),GOTMPDIR=str(temporary),TMPDIR=str(temporary),
            GOFLAGS="",GOEXPERIMENT="",PINKHA_CUTOVER_SHARED_FIXTURE=str(FIXTURE),PINKHA_CUTOVER_SHARED_FIXTURE_SHA256=FIXTURE_SHA,
            PINKHA_CUTOVER_CORE_PRIVATE_ROOT=str(private))
        expected=inventory();save(root/"source-before.json",expected)
        result["resourceAdmission"]={"rootFreeBytes":shutil.disk_usage(root).free,"cacheFreeBytes":shutil.disk_usage(CACHE).free,
            "scratchEstimateBytes":1536*1024*1024,"cacheEstimateBytes":384*1024*1024,"stopsBelowBytes":512*1024*1024}
        assert shutil.disk_usage(root).free>2048*1024*1024 and shutil.disk_usage(CACHE).free>896*1024*1024
        result["toolchainSHA256"]=sha(GO)
        run("go-version",[str(GO),"version"],env,30)
        executable=root/"cutover-core.test"
        run("compile",[str(GO),"test","-c","-mod=readonly","-p","1","-tags=pinkha_loaded_account_witness,pinkha_cutover_acceptance","-o",str(executable),"./core"],env,900)
        assert inventory()==expected,"source changed during compile"
        save(root/"binary.json",row(executable))
        log=run("core",[str(GO),"tool","test2json","-t","-p","actual-core-cutover",str(executable),"-test.v","-test.count=1","-test.timeout=540s","-test.run=^"+METHOD+"$"],env,600)
        events=[json.loads(x) for x in log.read_text().splitlines()]
        runs=[x["Test"] for x in events if x.get("Action")=="run" and x.get("Test")]
        passes=[x["Test"] for x in events if x.get("Action")=="pass" and x.get("Test")]
        assert runs==[METHOD] and passes==[METHOD] and not any(x.get("Action") in ("skip","fail") for x in events)
        assert any(x.get("Action")=="pass" and not x.get("Test") for x in events)
        proofPath=private/METHOD/"core-cutover-proof.json";proof=json.loads(proofPath.read_text())
        assert proof["realAccounts"]==1 and proof["realLegacyFacts"]==2 and proof["signedMetadataRecords"]==4 and proof["signedV1ImportClaims"]==2 and proof["incompleteImportSealsRefused"]==2
        for key in ["finalUnlinkRetainsSeal","missingSourceReadCreatesNoRoots","omittedFactCreatesNoRoots","ordinaryV1ReaderRemainsCompatible","actualAccountStoppedAndReopened","reopenUsesSameOSProcess","stoppedAccountReadAndWriteRefused","olderPropertyWriterDivergenceVisible","legacyPropertyRetained"]:
            assert proof[key] is True,key
        assert all(proof[k] is False for k in ["peerTransport","generatedRPC","appleUI"])
        result.update(status="PASS_ACTUAL_CORE_REGISTRY_NOT_RPC_PEER_OR_APPLE",methods=passes,nativeProof=proof,nativeProofSHA256=sha(proofPath),binarySHA256=sha(executable))
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    finally:
        if expected is not None:
            after=inventory();save(root/"source-after.json",after);result["sourceUnchanged"]=after==expected
            if after!=expected:result["status"]="FAIL"
        result["completedUTC"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime());save(root/"receipt.json",result)
    print(json.dumps({"status":result["status"],"error":result.get("error"),"receipt":str(root/"receipt.json")}))
    return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
