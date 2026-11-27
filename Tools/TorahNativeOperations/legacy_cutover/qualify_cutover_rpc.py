#!/usr/bin/env python3
"""Bounded generated RPC, SIGKILL/reopen, and affected host qualification."""
import argparse,hashlib,json,os,re,secrets,shutil,signal,subprocess,time
from pathlib import Path
import qualify_current8ac_core as base
import continue_current8ac_core as retained
from prepare_rpc_source import FILES

METHODS={
"core":[
"TestPinkhaTorahCutoverWirePreservesFrozenIdentityAndCopies",
"TestPinkhaTorahCutoverGeneratedRPCRefusesUnloadedAccountAndVersions",
"TestPinkhaTorahCutoverWireFailureRetainsReceiptWithoutPrivateHistory",
"TestPinkhaTorahCutoverWireBoundRefusesWholeSnapshot",
"TestPinkhaTorahCutoverActualGeneratedRPCAndReopen"],
"host":[
"TestCutoverNativeSignedPhasesUnlinkAndReopen",
"TestCutoverNativeTwoAuthorsRetainAllBindingsAndOlderWriterDiverges",
"TestCutoverNativeCurrentACLAndRetiredLeaseRefuseReadAndRetry",
"TestCutoverNativeLostACKRetainsOneSignedBeginAndLeaseBoundary"],
"byte":["TestPinkhaTorahCutoverGeneratedByteBoundary"]}
PACKAGES={"core":"./core","host":"./core/block/editor/torahops","byte":"./clientlibrary/service"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--manifest-sha",required=True)
    parser.add_argument("--mode",choices=METHODS,required=True)
    parser.add_argument("--build-root",type=Path,help="Owned development directory for compiler temporary files and output only")
    parser.add_argument("--reuse-rpc-qualification",type=Path)
    parser.add_argument("--reuse-rpc-sha")
    parser.add_argument("--reuse-binary-receipt",type=Path)
    parser.add_argument("--reuse-binary-sha")
    args=parser.parse_args()
    assert (args.reuse_rpc_qualification is None)==(args.reuse_rpc_sha is None)
    assert args.reuse_rpc_qualification is None or args.mode=="core"
    assert (args.reuse_binary_receipt is None)==(args.reuse_binary_sha is None)
    assert args.reuse_binary_receipt is None or args.mode in ("host","byte")
    root=args.root
    assert root.is_absolute() and root.parent==retained.BASE.parent and root.parent.resolve()==root.parent and not root.exists()
    assert re.fullmatch("[a-f0-9]{64}",args.manifest_sha)
    os.umask(0o077);root.mkdir(mode=0o700)
    build_root=args.build_root or root
    if build_root!=root:
        assert build_root.is_absolute() and build_root.parent==Path("/mnt/development/projects/caches")
        assert build_root.parent.resolve()==build_root.parent and build_root.name=="pinkha-e-cutover-"+root.name+"-20261127"
        assert not build_root.exists()
        build_root.mkdir(mode=0o700)
    source=retained.BASE/"source"
    result={"status":"FAIL","mode":args.mode,"controllerSHA256":base.sha(Path(__file__).resolve()),"manifestSHA256":args.manifest_sha,
        "retainedSource":str(source),"buildRoot":str(build_root),"peerTransport":False,"appleUI":False,"commands":[]}
    expected=None
    def inventory():return {str(p.relative_to(source)):base.row(p) for p in sorted(source.rglob("*")) if p.is_file()}
    def absent(pid):
        try:os.killpg(pid,0);return False
        except ProcessLookupError:return True
    def resource_error():
        if shutil.disk_usage(root).free<2*1024**3:return "root filesystem reserve"
        if shutil.disk_usage(base.CACHE).free<512*1024**2:return "cache filesystem reserve"
        return None
    def run(label,argv,env,timeout,kill_barrier=None):
        directory=root/"commands"/label;directory.mkdir(parents=True)
        start=time.time();reason=None;barrier=None
        with (directory/"original.log").open("wb") as out:
            proc=subprocess.Popen(argv,cwd=source/"heart",env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
            base.save(directory/"started.json",{"pid":proc.pid,"argv":argv,"startedUTC":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
            try:
                while proc.poll() is None:
                    reason=resource_error()
                    if reason:break
                    if time.time()-start>timeout:reason="timeout";break
                    if kill_barrier is not None and kill_barrier.exists():
                        barrier=json.loads(kill_barrier.read_text())
                        assert barrier["pid"]==proc.pid and barrier["signedMetadata"]==1 and barrier["signedV1Imports"]==1
                        assert barrier["metadataWitnesses"]==0 and barrier["seals"]==0 and barrier["gracefulStop"] is False
                        assert barrier["nonce"]==json.loads((kill_barrier.parent/"ownership.json").read_text())["Nonce"]
                        os.killpg(proc.pid,signal.SIGKILL)
                        proc.wait(timeout=15)
                        reason="intentional SIGKILL after committed v1 before metadata"
                        break
                    time.sleep(0.2)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
        group_absent=absent(proc.pid)
        row={"argv":argv,"pid":proc.pid,"exitCode":proc.returncode,"seconds":time.time()-start,
             "processGroupAbsent":group_absent,"stopReason":reason,"logSHA256":base.sha(directory/"original.log")}
        base.save(directory/"result.json",row);result["commands"].append(row)
        if kill_barrier is not None:
            assert proc.returncode==-signal.SIGKILL and group_absent and barrier is not None,label+" did not reach the actual crash boundary"
            assert reason=="intentional SIGKILL after committed v1 before metadata"
            raw=(directory/"original.log").read_text()
            assert "=== RUN   TestPinkhaTorahCutoverCrashPrepare" in raw and "--- PASS:" not in raw and "--- FAIL:" not in raw
        else:
            assert proc.returncode==0 and group_absent and reason is None,label+" failed"
        return directory/"original.log"
    def require_tests(path,methods):
        events=[json.loads(x) for x in path.read_text().splitlines()]
        top=lambda action:sorted(x["Test"] for x in events if x.get("Action")==action and x.get("Test") and "/" not in x["Test"])
        assert top("run")==sorted(methods) and top("pass")==sorted(methods),(top("run"),top("pass"))
        assert not any(x.get("Action") in ("skip","fail") for x in events),"skip/failure is never accepted"
        assert any(x.get("Action")=="pass" and not x.get("Test") for x in events),"package completion missing"
    try:
        expected=json.loads(base.pinned(retained.BASE/"source-before.json",retained.SOURCE_MANIFEST).read_text())
        assert inventory()==expected,"retained exact source changed"
        base.pinned(retained.BASE/"receipt.json",retained.FAILED_RECEIPT)
        manifest=json.loads(base.pinned(base.HERE/"rpc-source-candidate.json",args.manifest_sha).read_text())
        assert set(manifest["files"])==set(FILES),"unreviewed RPC file scope"
        qualified=json.loads(base.pinned(base.HERE/"native-core-current8ac-qualified.json",manifest["coreManifestSHA256"]).read_text())
        generated=json.loads(base.pinned(Path(manifest["generatorReceipt"]),manifest["generatorReceiptSHA256"]).read_text())
        mapping={};input_manifest={}
        def freeze(rel,want,before):
            incoming=base.HERE/"overlay"/rel
            assert base.row(incoming)==want,rel
            original=source/"heart"/rel
            assert (base.row(original) if original.exists() else None)==before,rel+" original changed"
            copied=root/"inputs"/rel;copied.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(incoming,copied)
            mapping[str(original)]=str(copied)
            input_manifest[rel]={"before":before,"after":want}
        for rel,want in qualified["sourceFiles"].items():
            original=source/"heart"/rel
            if base.row(original)!=want:freeze(rel,want,expected["heart/"+rel])
        for rel,entry in manifest["files"].items():freeze(rel,entry["after"],entry["before"])
        for rel,want in generated["generatedFiles"].items():
            assert input_manifest[rel]["after"]==want,rel+" is not canonical generated output"
        overlay=root/"go-overlay.json"
        base.save(overlay,{"Replace":mapping})
        base.save(root/"source-inputs.json",input_manifest)
        base.save(root/"source-before.json",expected)
        reused=None
        if args.reuse_rpc_qualification is not None:
            assert re.fullmatch("[a-f0-9]{64}",args.reuse_rpc_sha)
            reused=json.loads(base.pinned(args.reuse_rpc_qualification,args.reuse_rpc_sha).read_text())
            assert reused["status"]=="PASS_ACTUAL_GENERATED_GRPC_FIVE_METHODS_CRASH_PENDING"
            assert reused["originalOverallStatus"]=="FAIL" and reused["executedAgain"] is False
            assert reused["methods"]==METHODS["core"] and reused["skips"]==0
            assert reused["nativeCoreManifestSHA256"]==manifest["coreManifestSHA256"]
            assert reused["sourceBeforeManifestSHA256"]==base.sha(root/"source-before.json")
            prior_inputs=reused["sourceInputs"]
            assert set(prior_inputs)==set(input_manifest)
            changed=[rel for rel in input_manifest if prior_inputs[rel]!=input_manifest[rel]]
            crash_path="core/pinkha_torah_cutover_crash_acceptance_test.go"
            assert changed==[crash_path],"RPC/product changes require new acceptance"
            assert prior_inputs[crash_path]["before"]==input_manifest[crash_path]["before"]
            assert prior_inputs[crash_path]["after"]["sha256"]=="979f7d52cdd81250f89c204f52c8fe74cf0dcaa6a00b608126ad1af5a84756cc"
            assert input_manifest[crash_path]["after"]["sha256"]=="6249ef6f3932837aedcb8d9f6aac3b7f584e0c386f213b1a608c8a151bf2b3fd"
            assert base.row(Path(reused["binary"]))==reused["binaryRow"]
            result["reusedRPCQualification"]={"path":str(args.reuse_rpc_qualification),"sha256":args.reuse_rpc_sha,
                "originalManifestSHA256":reused["manifestSHA256"],"currentManifestSHA256":args.manifest_sha,
                "onlyChangedPath":crash_path,"allProductAndFiveRPCMethodSourcesUnchanged":True,
                "originalOverallStatus":"FAIL","methodsExecutedAgain":False}
        private=root/"private";private.mkdir(mode=0o700)
        temporary=build_root/"temporary";temporary.mkdir(mode=0o700)
        if build_root!=root:(root/"temporary").symlink_to(temporary,target_is_directory=True)
        env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOMEMLIMIT="2GiB",
            GOCACHE=str(base.CACHE),CGO_ENABLED="1",CGO_LDFLAGS="-L"+str(source/"heart/deps/libs/linux-arm64-musl"),
            GOTMPDIR=str(temporary),TMPDIR=str(temporary),GOFLAGS="",GOEXPERIMENT="",
            PINKHA_CUTOVER_SHARED_FIXTURE=str(base.FIXTURE),PINKHA_CUTOVER_SHARED_FIXTURE_SHA256=base.FIXTURE_SHA,
            PINKHA_CUTOVER_RPC_PRIVATE_ROOT=str(private),PINKHA_CUTOVER_NATIVE_WORK=str(private))
        base.pinned(base.FIXTURE,base.FIXTURE_SHA)
        result["resourceAdmission"]={"rootFreeBytes":shutil.disk_usage(root).free,"cacheFreeBytes":shutil.disk_usage(base.CACHE).free,
            "rootStopsBelowBytes":2*1024**3,"cacheStopsBelowBytes":512*1024**2,
            "rootMustExceedBytes":2560*1024**2,"cacheMustExceedBytes":640*1024**2}
        assert result["resourceAdmission"]["rootFreeBytes"]>2560*1024**2 and result["resourceAdmission"]["cacheFreeBytes"]>640*1024**2,"coordinated root/cache reserve unavailable"
        if build_root!=root:
            result["resourceAdmission"]["buildFreeBytes"]=shutil.disk_usage(build_root).free
            result["resourceAdmission"]["buildMustExceedBytes"]=1536*1024**2
            assert result["resourceAdmission"]["buildFreeBytes"]>1536*1024**2,"development compiler placement reserve unavailable"
        executable=build_root/("cutover-"+args.mode+".test")
        compile_argv=[str(base.GO),"test","-c","-mod=readonly","-p","1","-overlay",str(overlay),
            "-tags=pinkha_loaded_account_witness,pinkha_cutover_acceptance","-o",str(executable),PACKAGES[args.mode]]
        if args.reuse_binary_receipt is None:
            run("compile",compile_argv,env,1200)
        else:
            assert re.fullmatch("[a-f0-9]{64}",args.reuse_binary_sha)
            previous_path=base.pinned(args.reuse_binary_receipt,args.reuse_binary_sha)
            previous=json.loads(previous_path.read_text());previous_root=previous_path.parent
            assert previous_root.parent==retained.BASE.parent and previous_root!=root
            assert previous["mode"]==args.mode and previous["manifestSHA256"]==args.manifest_sha
            assert previous["retainedSource"]==str(source) and previous["retainedSourceUnchanged"] is True
            assert json.loads((previous_root/"source-before.json").read_text())==expected
            assert json.loads((previous_root/"source-after.json").read_text())==expected
            assert json.loads((previous_root/"source-inputs.json").read_text())==input_manifest
            previous_overlay=json.loads((previous_root/"go-overlay.json").read_text())["Replace"]
            assert set(previous_overlay)==set(mapping)
            for rel,entry in input_manifest.items():
                original=str(source/"heart"/rel)
                frozen=previous_root/"inputs"/rel
                assert previous_overlay[original]==str(frozen) and base.row(frozen)==entry["after"]
            previous_binary=Path(previous["binaryPath"])
            assert base.sha(previous_binary)==previous["binarySHA256"]
            assert base.row(previous_binary)==json.loads((previous_root/"binary.json").read_text())
            assert os.access(previous_binary,os.X_OK)
            previous_compile=json.loads((previous_root/"commands/compile/result.json").read_text())
            expected_argv=list(compile_argv)
            expected_argv[7]=str(previous_root/"go-overlay.json")
            expected_argv[10]=str(previous_binary)
            assert previous_compile["argv"]==expected_argv
            assert previous_compile["exitCode"]==0 and previous_compile["processGroupAbsent"] is True and previous_compile["stopReason"] is None
            assert previous["commands"][0]==previous_compile
            assert base.sha(previous_root/"commands/compile/original.log")==previous_compile["logSHA256"]
            executable.symlink_to(previous_binary)
            result["reusedCompiledBinary"]={"receipt":str(previous_path),"receiptSHA256":args.reuse_binary_sha,
                "originalOverallStatus":previous["status"],"binary":str(previous_binary),"binarySHA256":previous["binarySHA256"],
                "allSourceAndOverlayInputsUnchanged":True,"compilerExecutedAgain":False,
                "fixtureEnvironment":{"PINKHA_CUTOVER_NATIVE_WORK":str(private),"PINKHA_CUTOVER_RPC_PRIVATE_ROOT":str(private)}}
        if build_root!=root:(root/executable.name).symlink_to(executable)
        base.save(root/"binary.json",base.row(executable));result["binarySHA256"]=base.sha(executable)
        result["binaryPath"]=str(executable)
        methods=METHODS[args.mode]
        selector="^("+"|".join(methods)+")$"
        if reused is None:
            log=run(args.mode,[str(base.GO),"tool","test2json","-t","-p","cutover-"+args.mode,str(executable),
                "-test.v","-test.count=1","-test.timeout=540s","-test.run="+selector],env,600)
            require_tests(log,methods)
            result["methodsExecutedThisRun"]=methods
        else:
            frame_source=Path(reused["nativeFramesRoot"])
            destination=private/"TestPinkhaTorahCutoverActualGeneratedRPCAndReopen"
            destination.mkdir(mode=0o700)
            proof_source=base.pinned(frame_source/"generated-rpc-proof.json",reused["generatedRPCProofSHA256"])
            shutil.copyfile(proof_source,destination/proof_source.name)
            for name,want in reused["nativeFrames"].items():
                assert Path(name).name==name and name.endswith(".pb")
                assert base.row(frame_source/name)==want
                shutil.copyfile(frame_source/name,destination/name)
                assert base.row(destination/name)==want
            result["methodsExecutedThisRun"]=[]
            result["reusedMethods"]=methods
        result["methods"]=methods
        if args.mode=="core":
            proof_path=private/"TestPinkhaTorahCutoverActualGeneratedRPCAndReopen/generated-rpc-proof.json"
            proof=json.loads(proof_path.read_text())
            for key,value in {"realAccounts":1,"realLegacyFacts":2,"signedMetadataRecords":4,"signedV1ImportClaims":2,"signedV1RemovalClaims":1}.items():assert proof[key]==value,key
            for key in ["generatedGRPC","allFiveGeneratedMethodsExecuted","sourceBytesRetained","nativeSignersVerified","sealedImportRetryIdempotent","accountStopAndReopen"]:assert proof[key] is True,key
            assert proof["newProcessReopen"] is False and proof["peerTransport"] is False and proof["appleUI"] is False
            result["generatedRPCProof"]=proof;result["generatedRPCProofSHA256"]=base.sha(proof_path)
            crash=private/"crash";crash.mkdir(mode=0o700)
            owner={"Protocol":"pinkha-cutover-process-crash-v1","Nonce":secrets.token_hex(24),"SyntheticOnly":True}
            owner_wire=json.dumps(owner,sort_keys=True)+"\n"
            (crash/"ownership.json").write_text(owner_wire)
            # A private network namespace retains only loopback for real gRPC.
            # No host firewall or networking is modified.
            runner=crash/"offline-exec.py"
            runner.write_text("""import json,os,pathlib,subprocess,sys
parent=os.environ["PINKHA_CUTOVER_PARENT_NET_NAMESPACE"]
namespace=os.readlink("/proc/self/ns/net")
assert namespace!=parent
subprocess.run([os.environ["PINKHA_CUTOVER_IP"],"link","set","lo","up"],check=True)
links=json.loads(subprocess.check_output([os.environ["PINKHA_CUTOVER_IP"],"-j","link"],text=True))
assert {x["ifname"] for x in links}=={"lo"}
routes=json.loads(subprocess.check_output([os.environ["PINKHA_CUTOVER_IP"],"-j","route","show","table","all"],text=True))
assert all(x.get("dev")=="lo" for x in routes)
receipt={"pid":os.getpid(),"namespace":namespace,"parentNamespace":parent,"interfaces":[x["ifname"] for x in links],"externalRoutes":0}
path=pathlib.Path(os.environ["PINKHA_CUTOVER_CRASH_ROOT"])/(os.environ["PINKHA_CUTOVER_CRASH_PHASE"]+"-namespace.json")
with path.open("x") as f:json.dump(receipt,f);f.flush();os.fsync(f.fileno())
os.execve(sys.argv[1],sys.argv[1:],dict(os.environ))
""")
            unshare=shutil.which("unshare");ip=shutil.which("ip")
            assert unshare and ip,"network namespace tools required"
            crash_env=dict(env,PINKHA_CUTOVER_CRASH_ROOT=str(crash),PINKHA_CUTOVER_CRASH_OWNER=owner_wire,
                PINKHA_CUTOVER_PARENT_NET_NAMESPACE=os.readlink("/proc/self/ns/net"),PINKHA_CUTOVER_IP=ip)
            pids=[]
            for phase in ["prepare","resume","verify"]:
                method="TestPinkhaTorahCutoverCrash"+phase.capitalize()
                phase_env=dict(crash_env,PINKHA_CUTOVER_CRASH_PHASE=phase)
                argv=[unshare,"--net","--","/usr/bin/python3",str(runner),str(executable),
                    "-test.v","-test.count=1","-test.timeout=540s","-test.run=^"+method+"$"]
                if phase=="prepare":
                    phase_log=run("crash-"+phase,argv,phase_env,600,kill_barrier=crash/"ready-for-sigkill.json")
                else:
                    # test2json wraps the unshare child; the native test PID is
                    # independently recorded and checked in namespace/proofs.
                    phase_log=run("crash-"+phase,[str(base.GO),"tool","test2json","-t","-p","cutover-crash-"+phase,*argv],phase_env,600)
                    require_tests(phase_log,[method])
                ns=json.loads((crash/(phase+"-namespace.json")).read_text())
                assert ns["interfaces"]==["lo"] and ns["externalRoutes"]==0 and ns["namespace"]!=ns["parentNamespace"]
                pids.append(ns["pid"])
            assert len(set(pids))==3,"distinct actual test PIDs required"
            resumed=json.loads((crash/"resume-proof.json").read_text())
            verified=json.loads((crash/"verify-proof.json").read_text())
            assert resumed["pid"]==pids[1] and verified["pid"]==pids[2] and resumed["createPID"]==verified["createPID"]==pids[0]
            assert resumed["nonce"]==verified["nonce"]==owner["Nonce"]
            for key in ["samePendingStateAfterCrash","frozenImportRetryIdempotent","originalNativeReceiptPreserved","sourceAndFactBytesPreserved","sealed","accountStopped"]:assert resumed[key] is True,key
            assert resumed["signedMetadata"]==4 and resumed["signedV1Imports"]==2
            for key in ["exactSealedNativeHistoryPreserved","sourceAndFactBytesPreserved","accountStopped","generatedGRPC","newProcessReopen"]:assert verified[key] is True,key
            assert verified["peerTransport"] is False and verified["appleUI"] is False
            needles=json.loads((crash/"sensitive-needles.private").read_text())
            assert len(needles)==2 and all(needles)
            for path in (root/"commands").glob("*/original.log"):
                data=path.read_bytes()
                assert not any(x.encode() in data for x in needles),"private credential appeared in retained command log"
            result.update(status="PASS_GENERATED_GRPC_AND_OFFLINE_PROCESS_CRASH_NOT_PEER_OR_APPLE",
                generatedRPC=True,newProcessReopen=True,osNetworkIsolated=True,
                crashProof={"actualTestPIDs":pids,"resume":resumed,"verify":verified,
                "checkpointSHA256":base.sha(crash/"checkpoint.json"),"sealedSnapshotSHA256":base.sha(crash/"sealed-snapshot.pb")},
                secretLogScanPassed=True)
        elif args.mode=="host":result["status"]="PASS_AFFECTED_NATIVE_SIGNED_HOST_REGRESSIONS"
        else:result["status"]="PASS_GENERATED_GOMOBILE_BYTE_BOUNDARY"
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
