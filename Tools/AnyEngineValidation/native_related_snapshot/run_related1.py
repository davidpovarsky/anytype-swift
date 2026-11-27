#!/usr/bin/env python3
"""Actual native local-Space readiness, bounded results and global opaque-payload fencing."""
import gzip,hashlib,importlib.util,json,os,pathlib,re,shutil,signal,socket,subprocess,sys,tarfile,time,traceback,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
PACKAGE=ROOT/"Modules/PinkhaAnyEngine"
OUT=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127/native-related-functional1")
SCRATCH=pathlib.Path("/tmp/pinkha-w1-engine-contracts-indexed-20261127")
CACHE="/tmp/pinkha-w1-engine-contracts-cache-20261127"
RUNNER=SCRATCH/"out/Products/Debug-linux-aarch64/PinkhaAnyEngineTests-test-runner"
COMPONENT=OUT.parent/"markdown-body-components2/result.json"
ARCHIVE=pathlib.Path("/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network/private-native-account-retention1/actual-accounts-and-originals.tar.gz")
ARCHIVE_SHA="be1806e5c72c3ee30dc2612fb3cb4148747247cb4771262f779303cf6a51b147"
HELPER=pathlib.Path("/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/run_linux_filesv2_comparison.py")
HELPER_SHA="bf7f478e939dedeb414a49cbd3ca4c6263350bea3985511707899e4e64f3b189"
ACCOUNT="A7uNCqK2QB6J48HEDWGGX2Zv37vxFXZMxvF96R6sjzk7YPbx"
SPACE="bafyreicbctkf6ogqxta4pn2lfoijoesvmrtub2spj2ei2wbagywgcqau2y.11113vcq7lykz"
FLOOR=2*1024**3
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def source_inventory():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(PACKAGE.rglob("*"))
            if p.is_file() and (p.suffix in (".swift",".py") or p.name=="Package.resolved") and ".build" not in p.parts}
assert sha(HELPER)==HELPER_SHA
spec=importlib.util.spec_from_file_location("qualified_files_helper",HELPER)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
os.umask(0o077)
OUT.mkdir(mode=0o700,parents=True,exist_ok=False)
LOG=OUT/"private-logs";LOG.mkdir()
DATA=OUT/"private-account-copy";DATA.mkdir()
PROOF=OUT/"proof";PROOF.mkdir()
r={"status":"RUNNING","protocol":"pinkha-native-related-local-snapshot-v1","controllerSHA256":sha(pathlib.Path(__file__)),
   "started":time.time(),"original182Rerun":False,"appBuilds":0,"goBuilds":0,"swiftBuilds":0,
   "originalArchiveSHA256":ARCHIVE_SHA,"originalAccountModified":False,"actualRelatedReadinessAcceptance":False,
   "spaceWideReadinessAccepted":False,"filesV2Acceptance":False,"processes":[],"phases":[],"errors":[]}
children=[];phase="preflight";minimum=shutil.disk_usage("/").free
def save():helper.atomic(OUT/"result.json",r)
def guard():
    global minimum
    minimum=min(minimum,shutil.disk_usage("/").free)
    assert minimum>=FLOOR,"owned native body storage floor"
    assert time.time()-r["started"]<240,"owned native body deadline"
def stop_signal(*_):raise RuntimeError("owned native body controller interrupted")
signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
def spawn(name,cmd,env=None):
    guard();log=LOG/(name+".log");f=log.open("xb")
    p=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    row={"name":name,"pid":p.pid,"command":cmd,"log":str(log),"intentionalCrash":False}
    child={"p":p,"f":f,"row":row};children.append(child);r["processes"].append(row);save()
    return child
def absent(child):
    if child["row"].get("groupAbsent") is True:return True
    try:os.killpg(child["p"].pid,0)
    except ProcessLookupError:child["row"]["groupAbsent"]=True;return True
    return False
def close(child,expected=0,terminate=True):
    p=child["p"]
    if p.poll() is None:
        if terminate:os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
            child["row"]["forcedUnexpectedKill"]=True
    child["row"]["exitCode"]=p.returncode
    child["f"].close();child["row"]["logSHA256"]=sha(pathlib.Path(child["row"]["log"]))
    assert absent(child),"owned process group remains"
    assert p.returncode==expected and not child["row"].get("forcedUnexpectedKill"),"owned exit differs"
    save()
def bounded(name,cmd,env=None,timeout=60):
    child=spawn(name,cmd,env);end=time.time()+timeout
    while child["p"].poll() is None:
        guard();assert time.time()<end,"bounded "+name+" deadline";time.sleep(.2)
    close(child,terminate=False)
    return pathlib.Path(child["row"]["log"]).read_text(errors="replace")
def request(child,method,path,body=None,expected=200):
    guard();assert child["p"].poll() is None,"native process exited"
    raw=None;headers={}
    if body is not None:raw=json.dumps(body,separators=(",",":")).encode();headers["Content-Type"]="application/json"
    req=urllib.request.Request(child["base"]+path,data=raw,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=8) as response:
            value=response.read(2*1024**2+1);status=response.status
    except urllib.error.HTTPError as e:status=e.code;value=e.read(65537)
    assert len(value)<=2*1024**2
    if status!=expected:
        helper.atomic(OUT/("private-http-error-"+str(len(r["errors"]))+".json"),{"method":method,"path":path,"status":status,"body":value.decode(errors="replace")})
        raise AssertionError("actual native status "+str(status)+" expected "+str(expected))
    return json.loads(value) if value else None
def start_native(name):
    assert sha(helper.BINARY)==helper.BINARY_SHA and sha(helper.OFFLINE)==helper.OFFLINE_SHA
    assert sha(CONFIG)==r["configSHA256"]
    with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    cmd=[sys.executable,"-B",str(helper.OFFLINE),"--exec",str(helper.BINARY),"run","--config",str(CONFIG),"--data-dir",str(DATA),"--addr","127.0.0.1:"+str(port)]
    env={k:v for k,v in os.environ.items() if not k.startswith("ANY_")}
    env.update(ANY_DATA_DIR=str(DATA),GOMAXPROCS="2",GOMEMLIMIT="1GiB")
    child=spawn(name,cmd,env);child["base"]="http://127.0.0.1:"+str(port)
    end=time.time()+60
    while True:
        assert child["p"].poll() is None,"native start exited"
        try:
            if request(child,"GET","/v1/health") is not None:break
        except (OSError,urllib.error.URLError):pass
        guard();assert time.time()<end,"native readiness deadline";time.sleep(.25)
    fields=dict(line.split(":",1) for line in pathlib.Path("/proc/"+str(child["p"].pid)+"/status").read_text().splitlines() if ":" in line)
    assert fields["NoNewPrivs"].strip()=="1" and fields["Seccomp"].strip()=="2"
    assert pathlib.Path("/proc/"+str(child["p"].pid)+"/exe").resolve()==helper.BINARY
    child["row"].update(noNewPrivs=1,seccomp=2,actualOSNetworkDenial=True)
    account=request(child,"GET","/v1/account")
    assert account["id"]==ACCOUNT,"original account identity mismatch"
    member=request(child,"GET","/v1/spaces/"+SPACE+"/members/me")
    assert member["identity"]==ACCOUNT and member["status"]=="active" and member["permission"]=="owner"
    sync=request(child,"GET","/v1/spaces/"+SPACE+"/sync-status")
    assert all(sync[k]==0 for k in ["networkPeers","localPeers","globalPeers"])
    child["row"]["scope"]={"accountID":ACCOUNT,"spaceID":SPACE,"permission":"owner","peerCounts":{k:sync[k] for k in ["networkPeers","localPeers","globalPeers"]}}
    save();return child

PROBE=SCRATCH/"out/Products/Debug-linux-aarch64/PinkhaAnyEngineProbe"
PROBE_SHA="034a594b7e77ae13566a52b400f5535c4bf1aa045630b9b1da9b18aa8d9a2e40"
ORIGINAL_TARGET="bafyreigcv3i3omngn7eivsxmumj2ihui2kyke5v7aivrytxq6anwbag3e4"
IDENTITY="torah1|3:ref|7:sefaria|10:Exodus 1:1"
PRE="/v1/spaces/"+SPACE
r["newTargetCreates"]=0;r["newCanonicalClaims"]=0;r["newOpaqueClaims"]=0;r["probeBundleEnsureCalls"]=0
r["mutations"]=[]
def record(name,value):
    helper.atomic(PROOF/(name+".json"),value)
    r["phases"].append({"name":name,"sha256":sha(PROOF/(name+".json"))});save()
    return value
def get(name,child,path,expected=200):
    return record(name,request(child,"GET",path,expected=expected))
def related(name,child,limit=1000):
    return get(name,child,PRE+"/pinkha/related?"+urllib.parse.urlencode({"identity":IDENTITY,"limit":limit}))
def claims(name,child,limit=10000):
    value=get(name,child,PRE+"/pinkha/claims?limit="+str(limit))
    assert value["contract"]=="pinkha-torah-native-v1" and value["spaceId"]==SPACE
    assert value["complete"] is True and value["dataset"]=="pinkha_torah_claims_v1" and "scope" not in value
    assert value["limit"]==limit and len(value["records"])<=limit
    for row in value["records"]:
        assert row["spaceId"]==SPACE and row["authorId"]==row["creator"] and row["nativeChangeId"] and row["nativeACLHeadId"]
        assert row["id"]==row["logicalKey"]+row["contentHash"]
    return value
def claimids(snapshot):return sorted(x["logicalKey"]+"/"+x["contentHash"] for x in snapshot["records"])
def ready(value,ids,complete):
    assert value["contract"]=="pinkha-torah-native-v1" and value["version"]==1 and value["identity"]==IDENTITY
    assert {x["objectId"] for x in value["targets"]}==set(ids)
    assert all(x["spaceId"]==SPACE and not x.get("blockId") and x["canSafelyUnlink"] is True and x["contextItemIds"] and not x["sourceQuoteItemIds"] for x in value["targets"])
    assert value["conflictingTargets"]==[]
    stamp=value["readiness"];assert stamp["version"]==1 and re.fullmatch("[0-9a-f]{64}",stamp["generation"])
    if complete:
        assert value["coverage"]=="complete" and stamp["state"]=="ready-local-snapshot" and value["unsupportedClaimsPresent"] is False
    else:
        assert value["coverage"]=="incomplete-unsupported-payload" and stamp["state"]=="incomplete" and value["unsupportedClaimsPresent"] is True
def verify_swift(name,child,expected):
    assert sha(PROBE)==PROBE_SHA and source_inventory()==r["swiftSources"]
    cmd=[str(PROBE),"--endpoint",child["base"],"--account-id",ACCOUNT,"--space-id",SPACE,"--lane","native","--mode","verify","--expected-claims",",".join(sorted(expected))]
    output=bounded(name,cmd,timeout=30)
    value=json.loads(output);assert value["status"]=="PASS_REAL_NATIVE_ANY_HTTP_READ"
    assert sorted(value["allClaimIds"])==sorted(expected) and value["conflictKeys"]==[]
    record(name+"-proof",value)
def page(name,child):
    item={"name":name,"operation":"create-page","dispatched":True,"response":None};r["mutations"].append(item);save()
    value=request(child,"POST",PRE+"/objects",{"type":"page"},201)
    assert value["objectId"] and "/" not in value["objectId"]
    item["response"]=value;r["newTargetCreates"]+=1;save();return value["objectId"]
def append(name,child,target,operation_id,payload,provider,ref):
    assert sha(PROBE)==PROBE_SHA and source_inventory()==r["swiftSources"]
    encoded=__import__("base64").b64encode(payload).decode()
    cmd=[str(PROBE),"--endpoint",child["base"],"--account-id",ACCOUNT,"--space-id",SPACE,"--lane","native","--mode","append","--allow-disposable-writes","--kind","add","--operation-id",operation_id,"--target-id",target,"--provider-id",provider,"--source-ref",ref,"--payload-base64",encoded]
    row={"name":name,"operationID":operation_id,"target":target,"payloadBytes":len(payload),"payloadSHA256":hashlib.sha256(payload).hexdigest(),"probeBundleEnsureCalls":1,"dispatched":True,"response":None}
    r["mutations"].append(row);r["probeBundleEnsureCalls"]+=1;save()
    output=bounded(name,cmd,timeout=30)
    proof=json.loads(output)
    assert proof["status"]=="PASS_REAL_NATIVE_ANY_APPEND" and proof["created"] is True and proof["conflicted"] is False
    assert proof["targetObjectId"]==target and re.fullmatch("[0-9a-f]{64}/[0-9a-f]{64}",proof["claimId"])
    row["response"]=proof;record(name+"-proof",proof)
    return proof["claimId"]
try:
    assert minimum>=FLOOR+128*1024**2
    accepted=json.loads(COMPONENT.read_text())
    assert sha(COMPONENT)=="25a6c48dfb95dec2689682bdf80da6798dabb1a670f769f740e2357de7c8882e"
    assert accepted["sourceUnchanged"] is True and accepted["status"]=="PASS_COMPONENT_18_METHODS_ZERO_SKIPS"
    r["swiftSources"]=source_inventory();assert r["swiftSources"]==accepted["sourceAfter"]
    r["runnerSHA256"]=sha(RUNNER);assert r["runnerSHA256"]==accepted["runnerSHA256"]
    assert sha(PROBE)==PROBE_SHA
    r["probeSHA256"]=PROBE_SHA;r["probeSourceSHA256"]=sha(PACKAGE/"Sources/PinkhaAnyEngineProbe/Probe.swift")
    built=OUT.parent/"markdown-body-components1"
    assert "Build complete! (19.71 secs)" in (built/"swift.log").read_text()
    assert "PinkhaAnyEngineProbe-product" in (built/"swift.log").read_text()
    r["retainedSwiftProductQualification"]={"sourceReceipt":str(COMPONENT),"sourceReceiptSHA256":sha(COMPONENT),"originalCompileLogSHA256":sha(built/"swift.log"),"newCompilerInvocations":0}
    r["nativeSourceBefore"]=helper.source_admission()
    assert sha(ARCHIVE)==ARCHIVE_SHA
    prefix="peer-attempt1/alice/";extracted=[]
    with tarfile.open(ARCHIVE,"r:gz") as t:
        members=[m for m in t.getmembers() if m.name.startswith(prefix)]
        assert members and sum(m.size for m in members)<8*1024**2
        names=set()
        for m in members:
            rel=pathlib.PurePosixPath(m.name[len(prefix):])
            assert str(rel) not in ("",".") and not rel.is_absolute() and ".." not in rel.parts
            assert str(rel) not in names;names.add(str(rel));assert m.isfile() or m.isdir()
            dest=DATA.joinpath(*rel.parts)
            if m.isdir():dest.mkdir(mode=m.mode,parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                with t.extractfile(m) as src,dest.open("xb") as dst:shutil.copyfileobj(src,dst)
                os.chmod(dest,m.mode);assert dest.stat().st_size==m.size
                extracted.append({"path":str(rel),"bytes":m.size,"mode":m.mode,"sha256":sha(dest)})
        fixture=json.loads(t.extractfile("network-attempt1/semantic-original-fixture.json").read())
    helper.atomic(OUT/"private-copy-inventory.json",extracted)
    r["retainedCopy"]={"sourceArchiveSHA256":ARCHIVE_SHA,"copiedFiles":len(extracted),"inventorySHA256":sha(OUT/"private-copy-inventory.json"),"destination":str(DATA)}
    CONFIG=OUT/"offline-native-config.yml"
    CONFIG.write_text("network:\n  nodeconfPath: "+str(helper.NODECONF)+"\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n")
    r["configSHA256"]=sha(CONFIG)
    oldproof=OUT.parent/"markdown-body-native1/result.json"
    assert sha(oldproof)=="7c467547ec6c8158a861fc3c870647b3c8c2d1e3c29af9e3834ac5ce12202464"
    r["reusedOSDenialProbe"]={"resultSHA256":sha(oldproof),"policy":json.loads(oldproof.read_text())["networkDenialProbe"],"newNativePIDFlagsChecked":True}
    phase="baseline current-local full Space"
    warm=start_native("related-warm")
    initial=claims("baseline-space",warm);assert len(initial["records"])==3
    root_id=initial["rootObjectId"];original_ids=claimids(initial)
    baseline=related("baseline-related",warm);ready(baseline,[ORIGINAL_TARGET],True)
    verify_swift("baseline-swift-full-snapshot",warm,original_ids)
    phase="new target and actual canonical native claim"
    a=page("new-canonical-target",warm)
    source=__import__("base64").b64decode(fixture["unlinkedCanonical"],validate=True)
    canonical=json.loads(source);assert canonical["version"]==2 and len(canonical["records"])==1
    canonical["records"][0]["objectId"]=a
    canonical["records"][0]["item"]["id"]="readiness-canonical-target-20261127"
    payload=json.dumps(canonical,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode()
    a_claim=append("append-canonical",warm,a,"d0f10203040506070809101112131415",payload,"sefaria","Exodus 1:1")
    r["newCanonicalClaims"]=1
    added=related("after-new-target",warm);ready(added,[ORIGINAL_TARGET,a],True)
    assert added["readiness"]["generation"]!=baseline["readiness"]["generation"]
    repeated=related("stable-new-target",warm);assert repeated==added
    full=claims("space-after-new-target",warm);assert full["rootObjectId"]==root_id and claimids(full)==sorted(original_ids+[a_claim])
    verify_swift("new-target-swift-full-snapshot",warm,original_ids+[a_claim])
    closure=get("original-object-closure",warm,PRE+"/pinkha/objects/"+ORIGINAL_TARGET+"/claims?limit=10000")
    assert closure["scope"]=="object-logical-closure" and closure["targetObjectId"]==ORIGINAL_TARGET and len(closure["records"])==3
    assert closure["complete"] is True and claimids(closure)==original_ids and claimids(closure)!=claimids(full)
    phase="explicit limit refusal cannot certify truncated data"
    error=get("related-limit-refusal",warm,PRE+"/pinkha/related?"+urllib.parse.urlencode({"identity":IDENTITY,"limit":1}),409)
    assert error["error"]["code"]=="pinkha.read_limit" and "targets" not in error and "readiness" not in error
    error=get("full-space-limit-refusal",warm,PRE+"/pinkha/claims?limit=3",409)
    assert error["error"]["code"]=="pinkha.read_limit" and "records" not in error and "complete" not in error
    phase="unrelated opaque claim invalidates global semantic readiness"
    b=page("new-opaque-target",warm)
    b_claim=append("append-opaque",warm,b,"e0f10203040506070809101112131415",b"opaque-t2-readiness-fixture-v1","future-provider","opaque-readiness-reference")
    r["newOpaqueClaims"]=1
    incomplete=related("global-unsupported",warm);ready(incomplete,[ORIGINAL_TARGET,a],False)
    assert incomplete["readiness"]["generation"]!=added["readiness"]["generation"]
    assert related("stable-global-unsupported",warm)==incomplete
    full_unknown=claims("space-with-opaque",warm)
    assert full_unknown["rootObjectId"]==root_id and claimids(full_unknown)==sorted(original_ids+[a_claim,b_claim])
    opaque=[x for x in full_unknown["records"] if x["logicalKey"]+"/"+x["contentHash"]==b_claim]
    assert len(opaque)==1 and opaque[0]["pinkhaSemanticStatus"]=="unsupported-opaque"
    assert opaque[0]["targetObjectId"]==b and opaque[0]["pinkhaRelatedSource"]==""
    verify_swift("opaque-swift-full-snapshot",warm,original_ids+[a_claim,b_claim])
    r["baselineClaimCount"]=3;r["finalClaimCount"]=5;r["rootObjectId"]=root_id
    r["targetIDs"]={"original":ORIGINAL_TARGET,"canonical":a,"opaque":b};r["addedClaimIDs"]=[a_claim,b_claim];save()
    phase="intentional crash and new native PID retains global fail-closed readiness"
    assert warm["p"].poll() is None and not absent(warm)
    warm["row"]["intentionalCrash"]=True
    os.killpg(warm["p"].pid,signal.SIGKILL);warm["p"].wait(timeout=10);close(warm,expected=-signal.SIGKILL,terminate=False)
    cold=start_native("related-cold");assert cold["p"].pid!=warm["p"].pid
    cold_related=related("cold-related",cold);ready(cold_related,[ORIGINAL_TARGET,a],False)
    cold_full=claims("cold-space",cold)
    assert cold_full["rootObjectId"]==root_id and cold_full["records"]==full_unknown["records"]
    verify_swift("cold-swift-full-snapshot",cold,original_ids+[a_claim,b_claim])
    r["readinessGenerationChangedAcrossProcess"]=cold_related["readiness"]["generation"]!=incomplete["readiness"]["generation"]
    close(cold)
    assert sha(ARCHIVE)==ARCHIVE_SHA and sha(PROBE)==PROBE_SHA and sha(CONFIG)==r["configSHA256"]
    r["status"]="PASS_ACTUAL_NATIVE_LOCAL_SPACE_READINESS_LIMIT_AND_OPAQUE_FENCE_COLD"
    r["actualRelatedReadinessAcceptance"]=True
    r["spaceWideReadinessAccepted"]=True
except BaseException as e:
    r["status"]="FAIL";r["failedPhase"]=phase;r["errors"].append({"type":type(e).__name__,"message":str(e)})
    (OUT/"traceback.txt").write_text(traceback.format_exc())
finally:
    for child in reversed(children):
        if child["row"].get("groupAbsent") is True:continue
        try:close(child,expected=-signal.SIGKILL if child["row"]["intentionalCrash"] else 0)
        except BaseException as e:r["status"]="FAIL";r["errors"].append({"cleanup":child["row"]["name"],"error":str(e)})
    r["allOwnedGroupsAbsent"]=all(child["row"].get("groupAbsent") is True for child in children)
    try:
        r["nativeSourceAfter"]=helper.source_admission()
        r["swiftSourceUnchanged"]=source_inventory()==r.get("swiftSources")
        r["probeUnchanged"]=sha(PROBE)==PROBE_SHA
        r["originalArchiveUnchanged"]=sha(ARCHIVE)==ARCHIVE_SHA
        if not all([r["nativeSourceAfter"]==r.get("nativeSourceBefore"),r["swiftSourceUnchanged"],r["probeUnchanged"],r["originalArchiveUnchanged"],r["allOwnedGroupsAbsent"]]):r["status"]="FAIL"
    except BaseException as e:r["status"]="FAIL";r["errors"].append({"finalAdmission":str(e)})
    if r["status"]!="PASS_ACTUAL_NATIVE_LOCAL_SPACE_READINESS_LIMIT_AND_OPAQUE_FENCE_COLD":
        r["actualRelatedReadinessAcceptance"]=False;r["spaceWideReadinessAccepted"]=False
    r["finished"]=time.time();r["minimumFreeBytes"]=minimum;r["seconds"]=round(r["finished"]-r["started"],3)
    save()
    print(json.dumps({"status":r["status"],"actualRelatedReadinessAcceptance":r["actualRelatedReadinessAcceptance"],"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),"errors":r["errors"],"seconds":r["seconds"]}))
sys.exit(0 if r["actualRelatedReadinessAcceptance"] else 1)
