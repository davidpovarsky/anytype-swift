#!/usr/bin/env python3
"""Actual core/account qualification of the explicitly inactive cutover candidate."""
import argparse,hashlib,importlib.util,json,os,shutil,stat
from pathlib import Path
BASE=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1")
BASE_SHA="32a701c389455d78d9a9271224921e3cc5772005481e3a7eac83312d2436c171"
CANDIDATE_SHA="db2018871482d911b15fce3002d3e15d25fd17d50ca0ae7f64c72725de18bb58"
HELPER_SHA="64b4310f7b1db57df0236074d4c7a9058041f6c06e6667797ceafe0099360a21"
METADATA_HELPER_SHA="a7ae9732da45d5e1235030ad061e7c3008ed6119b7ea84bcb5fba95028279dd5"
FIXTURE_RECEIPT=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-host/shared-fixture-qualification1/receipt.json")
FIXTURE_RECEIPT_SHA="db5b5a4682a474730a78c2a2637fbd38f1ee8a3079ec5bd5a6a56a444571809c"
FIXTURE_BINARY_SHA="6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7"
DEPENDENCY_MANIFEST=Path("/mnt/development/projects/evidence/c-source-asset-recovery-20261126/original-python-extraction1/metadata/manifest.json")
DEPENDENCY_MANIFEST_SHA="2a0a8807ffaae25b3596a387e47f42e5893d9a83ee64d161d029712d0acaced9"
DEPENDENCY_ROOT=DEPENDENCY_MANIFEST.parent.parent/"rootfs"
DEPENDENCY_NAME="/mnt/development/projects/worktrees/anytype-heart-semantic-page-20261123/deps/libs/linux-arm64-musl/libtantivy_go.a"
DEPENDENCY_SHA="efee68b0fdf23fd8c1c630f10f4cad497bbbcb7372b6b985933324ebe730a601"
METHOD="TestPinkhaTorahCutoverActualCoreRegistryAndReopen"
GO="/mnt/development/toolchains/go1.27.4/go/bin/go"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);a=ap.parse_args()
    directory=Path(__file__).resolve().parent;helper=directory/"darwin_owned_commands.py"
    if helper.is_symlink() or hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:raise ValueError("owned helper pin")
    spec=importlib.util.spec_from_file_location("cutover_core_commands",helper)
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    os.umask(0o077);root=a.root.absolute()
    if root.parent.resolve()!=root.parent or not str(root).startswith("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-core/"):
        raise ValueError("canonical protected E core root")
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    commands=c.Commands(root,2<<30);source=None;expected={}
    result={"status":"FAIL","scope":"actual LocalOnly core/account/private registry/native property and signed host qualification",
        "appBuilds":0,"nativeSliceBuilds":0,"generatedRPC":False,"peerTransport":False,"appleUI":False,"requestedMethods":[METHOD]}
    def inventory():
        return {str(p.relative_to(source)):{"bytes":p.stat().st_size,"sha256":c.digest(p)}
            for p in sorted(source.rglob("*")) if p.is_file()}
    try:
        if c.digest(BASE/"source-after.json")!=BASE_SHA or c.digest(directory/"native-core-registry-candidate.json")!=CANDIDATE_SHA:raise ValueError("native source identity")
        if c.digest(FIXTURE_RECEIPT)!=FIXTURE_RECEIPT_SHA:raise ValueError("shared-codec producer identity")
        fixture=json.loads(FIXTURE_RECEIPT.read_text());binary=Path(fixture["binary"])
        if fixture["status"]!="PASS_RETAINED_SHARED_SWIFT_GENERATOR_NOT_NATIVE_ACCEPTANCE" or c.digest(binary)!=FIXTURE_BINARY_SHA or binary.resolve()!=binary:raise ValueError("actual shared-codec binary")
        initial=shutil.disk_usage(root).free
        if initial<4<<30:raise ValueError("measured core build allowance plus emergency floor")
        result["resourceAdmission"]={"initialFreeBytes":initial,"estimatedIncrementalBytes":2<<30,"emergencyFreeBytes":2<<30,"parallelism":1}
        originals=json.loads((BASE/"source-after.json").read_text())
        candidate=json.loads((directory/"native-core-registry-candidate.json").read_text())
        if len(originals)!=4859 or candidate["baseManifestSHA256"]!=BASE_SHA or candidate["method"]!=METHOD:raise ValueError("closed source census")
        source=root/"source";source.mkdir()
        for rel,row in originals.items():
            name=Path(rel)
            if name.is_absolute() or ".." in name.parts:raise ValueError("source path")
            donor=BASE/"source"/name
            if donor.resolve()!=donor or donor.stat().st_size!=row["bytes"] or c.digest(donor)!=row["sha256"]:raise ValueError("original source differs: "+rel)
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest);expected[rel]=dict(row)
        for rel,row in candidate["sourceFiles"].items():
            donor=directory/"overlay"/rel
            if donor.resolve()!=donor or donor.stat().st_size!=row["bytes"] or c.digest(donor)!=row["sha256"]:raise ValueError("candidate source differs: "+rel)
            name="heart/"+rel
            if name in originals and originals[name]!=row and candidate["originalReplacements"].get(rel)!=originals[name]:
                raise ValueError("undeclared original replacement")
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest);expected[name]=dict(row)
        if c.digest(DEPENDENCY_MANIFEST)!=DEPENDENCY_MANIFEST_SHA:raise ValueError("original dependency authority")
        manifest=json.loads(DEPENDENCY_MANIFEST.read_text())
        rows=[r for r in manifest["files"]["rows"] if r[0]==DEPENDENCY_NAME]
        if len(rows)!=1 or rows[0][2]!="pinned_tantivy_archive" or rows[0][4]!=DEPENDENCY_SHA or int(rows[0][3][6])!=59821546:raise ValueError("original pinned library row")
        lib=DEPENDENCY_ROOT/DEPENDENCY_NAME.lstrip("/")
        if c.digest(lib)!=DEPENDENCY_SHA:raise ValueError("exact Linux native dependency")
        dest=source/"heart/deps/libs/linux-arm64-musl/libtantivy_go.a";dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib,dest)
        expected[str(dest.relative_to(source))]={"bytes":dest.stat().st_size,"sha256":DEPENDENCY_SHA}
        metadataHelper=directory/"core_workspace_metadata.py"
        if metadataHelper.resolve()!=metadataHelper or c.digest(metadataHelper)!=METADATA_HELPER_SHA:raise ValueError("exact metadata admission helper")
        mspec=importlib.util.spec_from_file_location("core_checksum_admission",metadataHelper)
        metadata=importlib.util.module_from_spec(mspec);mspec.loader.exec_module(metadata)
        checksumBytes,metadataProof,moduleProofs=metadata.admit()
        checksumPath=source/"go.work.sum"
        if expected["go.work.sum"]!=metadata.BEFORE or c.digest(checksumPath)!=metadata.BEFORE["sha256"]:raise ValueError("original candidate checksum")
        checksumPath.write_bytes(checksumBytes);expected["go.work.sum"]=dict(metadata.AFTER)
        c.save(root/"module-metadata-admission.json",metadataProof)
        metadataRoot=root/"module-metadata-originals";metadataRoot.mkdir(mode=0o700)
        for i,row in enumerate(moduleProofs): (metadataRoot/(str(i+1)+".mod")).write_bytes(row["raw"])
        before=inventory()
        if before!=expected:raise ValueError("complete source mismatch")
        c.save(root/"source-before.json",before);c.save(root/"candidate.json",candidate)
        private=root/"private";private.mkdir(mode=0o700)
        temporary=root/"temporary";temporary.mkdir(mode=0o700)
        env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOMEMLIMIT="2GiB",
            GOCACHE=str(BASE/"cache"),CGO_ENABLED="1",CGO_LDFLAGS="-L"+str(dest.parent),
            GOTMPDIR=str(temporary),TMPDIR=str(temporary),GOFLAGS="",GOEXPERIMENT="",
            PINKHA_CUTOVER_SHARED_FIXTURE=str(binary),PINKHA_CUTOVER_SHARED_FIXTURE_SHA256=FIXTURE_BINARY_SHA,
            PINKHA_CUTOVER_CORE_PRIVATE_ROOT=str(private))
        c.save(root/"environment.json",{key:env[key] for key in ["GOWORK","GOTOOLCHAIN","GOMAXPROCS","GOMEMLIMIT","GOCACHE","CGO_ENABLED","CGO_LDFLAGS","GOTMPDIR","TMPDIR","GOFLAGS","GOEXPERIMENT","PINKHA_CUTOVER_SHARED_FIXTURE","PINKHA_CUTOVER_SHARED_FIXTURE_SHA256","PINKHA_CUTOVER_CORE_PRIVATE_ROOT"]})
        result["goToolSHA256"]=c.digest(Path(GO))
        versionLog=commands.run("go-version",[GO,"version"],source/"heart",env,30)
        if versionLog.read_text().strip()!="go version go1.27.4 linux/arm64":raise ValueError("exact qualified Go toolchain")
        commands.run("go-environment",[GO,"env","-json","GOVERSION","GOROOT","GOTOOLDIR","GOOS","GOARCH","CGO_ENABLED","CC","CXX","GOMODCACHE","GOCACHE","GOWORK"],source/"heart",env,30)
        commands.run("module-graph",[GO,"list","-m","-json","all"],source/"heart",env,120)
        if inventory()!=expected:raise ValueError("module metadata changed before compilation")
        executable=root/"cutover-real-core.test"
        commands.run("build",[GO,"test","-c","-mod=readonly","-p","1","-tags=pinkha_loaded_account_witness,pinkha_cutover_acceptance","-o",str(executable),"./core"],source/"heart",env,900)
        c.save(root/"binary.json",{"path":str(executable),"bytes":executable.stat().st_size,"sha256":c.digest(executable)})
        commands.run("binary-modules",[GO,"version","-m",str(executable)],source/"heart",env,30)
        if inventory()!=expected:raise ValueError("compiler source changed before native account access")
        log=commands.run("actual-core",[GO,"tool","test2json","-t","-p","actual-core-cutover",str(executable),
            "-test.v","-test.count=1","-test.timeout=540s","-test.run=^"+METHOD+"$"],source/"heart",env,600)
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        runs=[r["Test"] for r in rows if r.get("Action")=="run" and r.get("Test")]
        passes=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
        if runs!=[METHOD] or passes!=[METHOD] or any(r.get("Action") in ("fail","skip") for r in rows) or not any(r.get("Action")=="pass" and not r.get("Test") for r in rows):
            raise ValueError("exact original core result")
        proofPath=private/METHOD/"core-cutover-proof.json"
        proof=json.loads(proofPath.read_text())
        if proof.get("contract")!="pinkha-actual-core-cutover-registry-v1" or proof.get("realAccounts")!=1 or proof.get("realLegacyFacts")!=2 or proof.get("signedMetadataRecords")!=4 or proof.get("signedV1ImportClaims")!=2 or proof.get("incompleteImportSealsRefused")!=2:
            raise ValueError("actual native proof counts")
        for key in ["finalUnlinkRetainsSeal","missingSourceReadCreatesNoRoots","omittedFactCreatesNoRoots","ordinaryV1ReaderRemainsCompatible","actualAccountStoppedAndReopened","reopenUsesSameOSProcess","stoppedAccountReadAndWriteRefused","olderPropertyWriterDivergenceVisible","legacyPropertyRetained"]:
            if proof.get(key) is not True:raise ValueError("actual proof boundary: "+key)
        if any(proof.get(key) is not False for key in ["peerTransport","generatedRPC","appleUI"]):raise ValueError("scope overclaim")
        if c.digest(binary)!=FIXTURE_BINARY_SHA or c.digest(FIXTURE_RECEIPT)!=FIXTURE_RECEIPT_SHA or c.digest(lib)!=DEPENDENCY_SHA:raise ValueError("immutable dependency changed")
        result.update(status="PASS_ACTUAL_CORE_REGISTRY_NOT_RPC_PEER_OR_APPLE",methods=passes,failures=0,skips=0,
            binarySHA256=c.digest(executable),logSHA256=c.digest(log),nativeProofSHA256=c.digest(proofPath),nativeProof=proof,candidateSHA256=CANDIDATE_SHA)
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    finally:
        failures=commands.cleanup();result["commands"]=commands.rows;result["cleanupFailures"]=failures
        if failures:result["status"]="FAIL"
        if source is not None:
            try:
                after=inventory();c.save(root/"source-after.json",after)
                if after!=expected:raise ValueError("whole source changed")
                result["sourceUnchanged"]=True;result["sourceSHA256"]=c.digest(root/"source-after.json")
            except Exception as error:result.update(status="FAIL",sourceError=str(error))
        if (root/"private").exists():
            try:
                privateFiles={str(p.relative_to(root/"private")):{"bytes":p.stat().st_size,"sha256":c.digest(p)} for p in sorted((root/"private").rglob("*")) if p.is_file()}
                c.save(root/"private-inventory.json",privateFiles)
            except Exception as error:result.update(status="FAIL",retentionError=str(error))
        if hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:result.update(status="FAIL",controlError="owned helper changed")
        if c.digest(directory/"core_workspace_metadata.py")!=METADATA_HELPER_SHA:result.update(status="FAIL",metadataControlError="metadata helper changed")
        if result.get("goToolSHA256") and c.digest(Path(GO))!=result["goToolSHA256"]:result.update(status="FAIL",toolError="Go toolchain changed")
        c.save(root/"receipt.json",result)
    print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
