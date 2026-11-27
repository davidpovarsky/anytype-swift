#!/usr/bin/env python3
"""Actual scoped Swift body CAS followed by SIGKILL and new-PID OS-offline read."""
import gzip,hashlib,importlib.util,json,os,pathlib,re,shutil,signal,socket,subprocess,sys,tarfile,time,traceback,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
PACKAGE=ROOT/"Modules/PinkhaAnyEngine"
OUT=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-native1")
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
r={"status":"RUNNING","protocol":"pinkha-native-markdown-body-cas-crash-v1","controllerSHA256":sha(pathlib.Path(__file__)),
   "started":time.time(),"original182Rerun":False,"appBuilds":0,"goBuilds":0,"swiftBuilds":0,
   "originalArchiveSHA256":ARCHIVE_SHA,"originalAccountModified":False,"actualBodyAcceptance":False,
   "spaceWideReadinessAccepted":False,"filesV2Acceptance":False,"processes":[],"phases":[],"errors":[]}
children=[];phase="preflight";minimum=shutil.disk_usage("/").free
def save():helper.atomic(OUT/"result.json",r)
def guard():
    global minimum
    minimum=min(minimum,shutil.disk_usage("/").free)
    assert minimum>=FLOOR,"owned native body storage floor"
    assert time.time()-r["started"]<360,"owned native body deadline"
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
def fixture(child,obj):
    value={"accountID":ACCOUNT,"spaceID":SPACE,"objectID":obj,"baseURL":child["base"],"bodyPath":str(OUT/"body.txt"),"proofDirectory":str(PROOF)}
    helper.atomic(OUT/"native-fixture.json",value)
def swift_method(name,method):
    assert sha(RUNNER)==r["runnerSHA256"] and source_inventory()==r["swiftSources"],"qualified Swift inputs changed"
    cmd=["/usr/local/bin/swift","test","--skip-build","--package-path",str(PACKAGE),"--scratch-path",str(SCRATCH),"--cache-path",CACHE,"--skip-update","--enable-index-store","--jobs","2","--filter","AnyNativeMarkdownBodyNativeTests."+method,"--xunit-output",str(OUT/(name+".xml"))]
    env=dict(os.environ);env["PINKHA_MARKDOWN_NATIVE_FIXTURE"]=str(OUT/"native-fixture.json")
    output=bounded(name,cmd,env,90)
    qualified="AnyNativeMarkdownBodyNativeTests."+method
    started=re.findall(r"Test Case '(AnyNativeMarkdownBodyNativeTests\.test\w+)' started",output)
    terminal=re.findall(r"Test Case '(AnyNativeMarkdownBodyNativeTests\.test\w+)' (passed|failed|skipped)",output)
    assert started==[qualified] and terminal==[(qualified,"passed")],"actual native XCTest method not PASS"
    assert "Executed 1 test, with 0 failures" in output and "skipped" not in output.lower()
    assert source_inventory()==r["swiftSources"] and sha(RUNNER)==r["runnerSHA256"]
    r["phases"].append({"name":name,"method":qualified,"actualPASS":True,"sourceQualifiedSkipBuild":True});save()
try:
    assert minimum>=FLOOR+128*1024**2,"native body preflight"
    accepted=json.loads(COMPONENT.read_text())
    assert accepted["status"]=="PASS_COMPONENT_18_METHODS_ZERO_SKIPS" and accepted["sourceUnchanged"] is True
    r["componentQualification"]={"path":str(COMPONENT),"sha256":sha(COMPONENT),"actualMethods":18}
    r["swiftSources"]=source_inventory()
    assert r["swiftSources"]==accepted["sourceAfter"]
    r["runnerSHA256"]=sha(RUNNER);assert r["runnerSHA256"]==accepted["runnerSHA256"]
    r["nativeSourceBefore"]=helper.source_admission()
    assert sha(ARCHIVE)==ARCHIVE_SHA
    prefix="peer-attempt1/alice/"
    extracted=[]
    with tarfile.open(ARCHIVE,"r:gz") as t:
        members=[m for m in t.getmembers() if m.name.startswith(prefix)]
        assert members and sum(m.size for m in members)<8*1024**2
        names=set()
        for m in members:
            rel=pathlib.PurePosixPath(m.name[len(prefix):])
            assert str(rel) not in ("",".") and not rel.is_absolute() and ".." not in rel.parts
            assert str(rel) not in names;names.add(str(rel))
            assert m.isfile() or m.isdir(),"unsafe original member"
            dest=DATA.joinpath(*rel.parts)
            if m.isdir():dest.mkdir(mode=m.mode,parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                with t.extractfile(m) as src,dest.open("xb") as dst:shutil.copyfileobj(src,dst)
                os.chmod(dest,m.mode)
                assert dest.stat().st_size==m.size
                extracted.append({"path":str(rel),"bytes":m.size,"mode":m.mode,"sha256":sha(dest)})
    helper.atomic(OUT/"private-copy-inventory.json",extracted)
    r["retainedCopy"]={"sourceArchiveSHA256":ARCHIVE_SHA,"copiedFiles":len(extracted),"inventorySHA256":sha(OUT/"private-copy-inventory.json"),"destination":str(DATA),"originalArchiveUnchanged":sha(ARCHIVE)==ARCHIVE_SHA}
    CONFIG=OUT/"offline-native-config.yml"
    CONFIG.write_text("network:\n  nodeconfPath: "+str(helper.NODECONF)+"\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n")
    r["configSHA256"]=sha(CONFIG)
    with socket.socket() as tcp,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
        tcp.bind(("127.0.0.1",0));tcp.listen();port=tcp.getsockname()[1]
        udp.bind(("127.0.0.1",port));udp.settimeout(2)
        socket.create_connection(("127.0.0.1",port),timeout=2).close()
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:sender.sendto(b"baseline",("127.0.0.1",port))
        assert udp.recvfrom(64)[0]==b"baseline"
        probe=json.loads(bounded("os-denial-probe",[sys.executable,"-B",str(helper.OFFLINE),"--probe",str(port)],timeout=10))
        assert all(probe[k] is True for k in ["tcpDenied","udpDenied","noNewPrivileges","seccompFilterActive"])
        r["networkDenialProbe"]={"baselineTCPUDPReachable":True,"actual":probe,"helperSHA256":helper.OFFLINE_SHA}
    phase="fresh page on isolated retained account copy"
    warm=start_native("native-body-warm")
    r["createDispatch"]={"count":1,"originalObjectID":None};save()
    created=request(warm,"POST","/v1/spaces/"+SPACE+"/objects",{"type":"page"},201)
    object_id=created["objectId"];assert object_id and "/" not in object_id
    r["createDispatch"]["originalObjectID"]=object_id
    helper.atomic(OUT/"creation-receipt.json",created);save()
    paragraphs=["א"*512]+[("P"+str(i).zfill(3)+"x").ljust(1022,"a") for i in range(255)]
    body="\n\n".join(paragraphs).encode()
    assert len(paragraphs)==256 and len(body)==262144
    (OUT/"body.txt").write_bytes(body)
    r["syntheticBody"]={"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"paragraphs":256,"includesMultibyteHebrew":True}
    fixture(warm,object_id)
    phase="actual Swift native conditional body write and stale CAS refusal"
    swift_method("native-write","testNativeConditionalBodyCommitAndStaleVersionRefusal")
    write=json.loads((PROOF/"write-proof.json").read_text())
    assert write["objectID"]==object_id and write["accountID"]==ACCOUNT and write["spaceID"]==SPACE
    assert write["newNativeWrites"]==1 and write["staleCASRefused"] is True
    assert write["contentBytes"]==len(body) and write["contentSHA256"]==hashlib.sha256(body).hexdigest()
    assert len(write["insertedBlockIDs"])==256 and len(set(write["insertedBlockIDs"]))==256
    r["writeProofSHA256"]=sha(PROOF/"write-proof.json");save()
    phase="intentional native process SIGKILL after acknowledged body"
    assert warm["p"].poll() is None and not absent(warm)
    warm["row"]["intentionalCrash"]=True
    os.killpg(warm["p"].pid,signal.SIGKILL);warm["p"].wait(timeout=10)
    close(warm,expected=-signal.SIGKILL,terminate=False)
    phase="new PID cold OS-offline read of exact original body"
    cold=start_native("native-body-cold")
    assert cold["p"].pid!=warm["p"].pid
    fixture(cold,object_id)
    swift_method("native-cold","testNativeColdReopenReadsOriginalBodyAfterProcessCrash")
    proof=json.loads((PROOF/"cold-proof.json").read_text())
    assert proof["writes"]==0
    for key in ["accountID","spaceID","objectID","contentBytes","contentSHA256"]:assert proof[key]==write[key]
    r["coldProofSHA256"]=sha(PROOF/"cold-proof.json")
    close(cold)
    assert sha(ARCHIVE)==ARCHIVE_SHA and sha(CONFIG)==r["configSHA256"]
    assert r["nativeSourceBefore"]==helper.source_admission()
    r["status"]="PASS_ACTUAL_NATIVE_BODY_CAS_STALE_REFUSAL_SIGKILL_COLD_OFFLINE"
    r["actualBodyAcceptance"]=True
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
        r["runnerUnchanged"]=sha(RUNNER)==r.get("runnerSHA256")
        r["originalArchiveUnchanged"]=sha(ARCHIVE)==ARCHIVE_SHA
        if not all([r["nativeSourceAfter"]==r.get("nativeSourceBefore"),r["swiftSourceUnchanged"],r["runnerUnchanged"],r["originalArchiveUnchanged"],r["allOwnedGroupsAbsent"]]):r["status"]="FAIL"
    except BaseException as e:r["status"]="FAIL";r["errors"].append({"finalAdmission":str(e)})
    if r["status"]!="PASS_ACTUAL_NATIVE_BODY_CAS_STALE_REFUSAL_SIGKILL_COLD_OFFLINE":r["actualBodyAcceptance"]=False
    r["finished"]=time.time();r["minimumFreeBytes"]=minimum;r["seconds"]=round(r["finished"]-r["started"],3)
    save()
    print(json.dumps({"status":r["status"],"actualBodyAcceptance":r["actualBodyAcceptance"],"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),"errors":r["errors"],"seconds":r["seconds"]}))
sys.exit(0 if r["actualBodyAcceptance"] else 1)
