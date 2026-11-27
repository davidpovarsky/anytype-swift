#!/usr/bin/env python3
"""Scoped actual-core continuation using Go's overlay; retained source is immutable."""
import argparse, hashlib, json, os, signal, shutil, subprocess, time
from pathlib import Path
import qualify_current8ac_core as base

BASE = Path("/var/tmp/pinkha-e-cutover-current8ac-20261127/attempt2")
SOURCE_MANIFEST = "ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28"
FAILED_RECEIPT = "fbae1f7a1a628ab75317e2812613a6c96682c6bceef9d8f3187ab13cf5e7e3e6"
DELTA = {'core/block/editor/factory.go': ('1dd988a0727518ea91ac8cf25fee7e7e2c18937814f5739ca6ef7af378816882', 'f6a7f7e1e7187731229f8095f5980cc5bef46ece38271f11067b3a2a9436cd4b'), 'core/block/editor/torahops/cutover_native_host.go': ('96874282e4e332cfee1207911c4e37d5a1bcae5c370ce3753088404e90237647', '2c5c0ea752139a14d75365702c9552d6bb3d683ae8c8ea118a8a0607d76682da'), 'core/block/editor/torahops/cutover_native_operations.go': ('dac1af78a7542b6f2d9d72bb9297af58199140bad65c590f9405de783e24d7da', 'cf8ffc3c87eea4d1beb0f8b078c7ec3ee6bae3a0722c998c1a215c21c58f99f8'), 'core/block/editor/torahops/cutover_projection.go': ('0804326995989deb461b1eba8f8b9e25ca4c3e4e7b9d3b90901b70b200f77858', 'bf5f8452b2f52ac459938d34c97833e5059081238b9608e9a8bd0269e8164615'), 'core/pinkha_torah_cutover_registry_test.go': ('aff39523e149eebbe40d405c7e4faca9a8b72c9bbf34ee2d9f345f1d79a07e52', 'bd265a1f498448fd61426ca78165722c545044817aff8998c9b96087c01bc87d')}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True,type=Path)
    args=parser.parse_args()
    root=args.root
    assert root.is_absolute() and str(root).startswith(str(BASE.parent)+"/")
    assert root.parent.resolve()==root.parent and not root.exists()
    os.umask(0o077);root.mkdir(mode=0o700)
    source=BASE/"source"
    result={"status":"FAIL","controllerSHA256":base.sha(Path(__file__).resolve()),"retainedBase":str(BASE),"generatedRPC":False,"peerTransport":False,"appleUI":False,"commands":[]}
    def inventory():
        return {str(p.relative_to(source)):base.row(p) for p in sorted(source.rglob("*")) if p.is_file()}
    expected=None
    try:
        expected=json.loads(base.pinned(BASE/"source-before.json",SOURCE_MANIFEST).read_text())
        base.pinned(BASE/"receipt.json",FAILED_RECEIPT)
        assert inventory()==expected, "retained exact source changed"
        mapping={}
        delta={}
        for rel,(before,after) in DELTA.items():
            original=base.pinned(source/"heart"/rel,before)
            replacement=base.pinned(base.HERE/"overlay"/rel,after)
            copy=root/"inputs"/rel;copy.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(replacement,copy)
            mapping[str(original)]=str(copy)
            delta[rel]={"beforeSHA256":before,"afterSHA256":after}
        overlay=root/"go-overlay.json"
        base.save(overlay,{"Replace":mapping})
        base.save(root/"source-delta.json",delta)
        base.save(root/"source-before.json",expected)
        private=root/"private";private.mkdir(mode=0o700)
        temporary=root/"temporary";temporary.mkdir()
        env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOMEMLIMIT="2GiB",
          GOCACHE=str(base.CACHE),CGO_ENABLED="1",CGO_LDFLAGS="-L"+str(source/"heart/deps/libs/linux-arm64-musl"),
          GOTMPDIR=str(temporary),TMPDIR=str(temporary),GOFLAGS="",GOEXPERIMENT="",
          PINKHA_CUTOVER_SHARED_FIXTURE=str(base.FIXTURE),PINKHA_CUTOVER_SHARED_FIXTURE_SHA256=base.FIXTURE_SHA,
          PINKHA_CUTOVER_CORE_PRIVATE_ROOT=str(private))
        base.pinned(base.FIXTURE,base.FIXTURE_SHA)
        assert shutil.disk_usage(root).free>2560*1024*1024 and shutil.disk_usage(base.CACHE).free>640*1024*1024, "coordinated root/cache reserve unavailable"
        result["resourceAdmission"]={"rootFreeBytes":shutil.disk_usage(root).free,"cacheFreeBytes":shutil.disk_usage(base.CACHE).free,"rootStopsBelowBytes":2*1024*1024*1024,"cacheStopsBelowBytes":512*1024*1024}
        def run(label,argv,timeout):
            directory=root/"commands"/label;directory.mkdir(parents=True)
            start=time.time()
            with (directory/"original.log").open("wb") as out:
                proc=subprocess.Popen(argv,cwd=source/"heart",env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
                base.save(directory/"started.json",{"pid":proc.pid,"argv":argv,"startedUTC":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
                reason=None
                try:
                    while proc.poll() is None:
                        if time.time()-start>timeout:reason="timeout";break
                        if shutil.disk_usage(root).free<2*1024*1024*1024 or shutil.disk_usage(base.CACHE).free<512*1024*1024:reason="coordinated filesystem reserve";break
                        time.sleep(1)
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid,signal.SIGTERM)
                        try:proc.wait(timeout=15)
                        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
            absent=False
            try:os.killpg(proc.pid,0)
            except ProcessLookupError:absent=True
            row={"argv":argv,"pid":proc.pid,"exitCode":proc.returncode,"seconds":time.time()-start,"processGroupAbsent":absent,"stopReason":reason,"logSHA256":base.sha(directory/"original.log")}
            base.save(directory/"result.json",row);result["commands"].append(row)
            assert proc.returncode==0 and absent and reason is None,label+" failed"
            return directory/"original.log"
        executable=root/"cutover-core.test"
        run("compile",[str(base.GO),"test","-c","-mod=readonly","-p","1","-overlay",str(overlay),"-tags=pinkha_loaded_account_witness,pinkha_cutover_acceptance","-o",str(executable),"./core"],900)
        base.save(root/"binary.json",base.row(executable))
        log=run("core",[str(base.GO),"tool","test2json","-t","-p","actual-core-cutover",str(executable),"-test.v","-test.count=1","-test.timeout=540s","-test.run=^"+base.METHOD+"$"],600)
        events=[json.loads(x) for x in log.read_text().splitlines()]
        runs=[x["Test"] for x in events if x.get("Action")=="run" and x.get("Test")]
        passes=[x["Test"] for x in events if x.get("Action")=="pass" and x.get("Test")]
        assert runs==[base.METHOD] and passes==[base.METHOD] and not any(x.get("Action") in ("skip","fail") for x in events)
        assert any(x.get("Action")=="pass" and not x.get("Test") for x in events)
        proofPath=private/base.METHOD/"core-cutover-proof.json";proof=json.loads(proofPath.read_text())
        for key,value in {"realAccounts":1,"realLegacyFacts":2,"signedMetadataRecords":4,"signedV1ImportClaims":2,"incompleteImportSealsRefused":2}.items():
            assert proof[key]==value,key
        for key in ["finalUnlinkRetainsSeal","missingSourceReadCreatesNoRoots","omittedFactCreatesNoRoots","ordinaryV1ReaderRemainsCompatible","actualAccountStoppedAndReopened","reopenUsesSameOSProcess","stoppedAccountReadAndWriteRefused","olderPropertyWriterDivergenceVisible","legacyPropertyRetained","divergedMetadataRetryRefused","divergedImportRetryRefused"]:
            assert proof[key] is True,key
        assert all(proof[k] is False for k in ["peerTransport","generatedRPC","appleUI"])
        result.update(status="PASS_ACTUAL_CORE_REGISTRY_NOT_RPC_PEER_OR_APPLE",methods=passes,nativeProof=proof,nativeProofSHA256=base.sha(proofPath),binarySHA256=base.sha(executable))
    except Exception as error:
        result["error"]=type(error).__name__+": "+str(error)
    finally:
        if expected is not None:
            after=inventory();base.save(root/"source-after.json",after);result["retainedSourceUnchanged"]=after==expected
            if after!=expected:result["status"]="FAIL"
        result["completedUTC"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
        base.save(root/"receipt.json",result)
    print(json.dumps({"status":result["status"],"error":result.get("error"),"receipt":str(root/"receipt.json")}))
    return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
