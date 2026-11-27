#!/usr/bin/env python3
"""Actual unchanged native styled/empty/nested block creation and cold durability."""
import gzip,hashlib,importlib.util,json,os,pathlib,re,shutil,signal,socket,subprocess,sys,tarfile,time,traceback,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
PACKAGE=ROOT/"Modules/PinkhaAnyEngine"
OUT=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127/native-block-styles1")
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
r={"status":"RUNNING","protocol":"pinkha-native-styled-block-creation-v1","controllerSHA256":sha(pathlib.Path(__file__)),
   "started":time.time(),"original182Rerun":False,"appBuilds":0,"goBuilds":0,"swiftBuilds":0,
   "originalArchiveSHA256":ARCHIVE_SHA,"originalAccountModified":False,"actualNativeBlockAcceptance":False,
   "processes":[],"phases":[],"mutations":[],"errors":[]}
children=[];phase="preflight";minimum=shutil.disk_usage("/").free
def save():helper.atomic(OUT/"result.json",r)
def guard():
    global minimum
    minimum=min(minimum,shutil.disk_usage("/").free)
    assert minimum>=FLOOR,"owned native block storage floor"
    assert time.time()-r["started"]<240,"owned native block deadline"
def stop_signal(*_):raise RuntimeError("owned native block controller interrupted")
signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
if hasattr(signal,"pthread_sigmask"):signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
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
    leader_alive=p.poll() is None
    group_present=not absent(child)
    if not leader_alive and group_present:child["row"]["unexpectedSurvivingOwnedGroup"]=True
    if leader_alive or group_present:
        if terminate or child["row"].get("unexpectedSurvivingOwnedGroup"):
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        end=time.monotonic()+15
        while time.monotonic()<end:
            p.poll()
            if absent(child):break
            time.sleep(.1)
        if not absent(child):
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child["row"]["forcedUnexpectedKill"]=True
            end=time.monotonic()+5
            while time.monotonic()<end:
                p.poll()
                if absent(child):break
                time.sleep(.1)
        if p.poll() is None:p.wait(timeout=1)
    child["row"]["exitCode"]=p.returncode
    child["f"].close();child["row"]["logSHA256"]=sha(pathlib.Path(child["row"]["log"]))
    assert absent(child),"owned process group remains"
    assert p.returncode==expected and not child["row"].get("forcedUnexpectedKill") and not child["row"].get("unexpectedSurvivingOwnedGroup"),"owned exit differs"
    save()
def bounded(name,cmd,env=None,timeout=60):
    child=spawn(name,cmd,env);end=time.time()+timeout
    while child["p"].poll() is None:
        guard();assert time.time()<end,"bounded "+name+" deadline";time.sleep(.2)
    close(child,terminate=False)
    return pathlib.Path(child["row"]["log"]).read_text(errors="replace")
def request(child,method,path,body=None,expected=200,mutation=None):
    guard();assert child["p"].poll() is None,"native process exited"
    raw=None;headers={}
    if body is not None:raw=json.dumps(body,separators=(",",":")).encode();headers["Content-Type"]="application/json"
    req=urllib.request.Request(child["base"]+path,data=raw,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=8) as response:
            value=response.read(2*1024**2+1);status=response.status
    except urllib.error.HTTPError as e:status=e.code;value=e.read(65537)
    if mutation is not None:
        receipt=OUT/("private-mutation-http-"+str(r["mutations"].index(mutation))+".bin")
        with receipt.open("xb") as f:f.write(value)
        mutation["httpReceipt"]={"status":status,"rawPath":str(receipt),"rawSHA256":sha(receipt),
          "observedBytes":len(value),"bodyMayBeTruncated":len(value)>2*1024**2 or (status>=400 and len(value)>=65537)}
        mutation["acknowledgementValidated"]=False;save()
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

HOST_SOURCE="Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift"
HOST_SHA="58a3ce0653a8973a07dce7e7dde80e1cb66a8bcce692652a47a8c8c60db684bc"
PRE="/v1/spaces/"+SPACE
def record(name,value):
    helper.atomic(PROOF/(name+".json"),value)
    r["phases"].append({"name":name,"sha256":sha(PROOF/(name+".json"))});save()
    return value
def all_rows(child):
    value=request(child,"POST",PRE+"/query",{"objectId":r["objectID"],"dataset":"editor_blocks","sort":["nav.pos","id"],"limit":100,"includeTotal":True})
    assert value["hasNext"] is False and value["total"]==len(value["records"])<=100
    return value["records"]
def assert_row(row,body,record_id):
    assert row["id"]==record_id and row["type"]==body["type"]
    assert row["nav"]["parentId"]==body["nav"]["parentId"] and row["nav"]["pos"]==body["nav"]["pos"]
    if body["text"]:
        assert row["text"].encode()==body["text"].encode()
    else:
        assert "text" not in row
    if body["style"]:
        assert json.dumps(row["style"],ensure_ascii=False,sort_keys=True,separators=(",",":"))==json.dumps(body["style"],ensure_ascii=False,sort_keys=True,separators=(",",":"))
    else:
        assert "style" not in row
def create_block(child,name,body):
    item={"kind":"block-create","name":name,"request":body,"dispatched":True,"response":None}
    r["mutations"].append(item);save()
    response=request(child,"POST",PRE+"/pinkha/objects/"+r["objectID"]+"/editor/editor_blocks/blocks",body,201,mutation=item)
    item["response"]=response;item["acknowledgementValidated"]=False;save()
    assert isinstance(response.get("recordIds"),list) and len(response["recordIds"])==1
    record_id=response["recordIds"][0]
    assert isinstance(record_id,str) and record_id and "/" not in record_id and len(record_id.encode())<=256
    assert isinstance(response.get("versionId"),str) and response["versionId"]
    assert response.get("rejections",[])==[]
    assert record_id not in r["blockIDs"]
    item["acknowledgementValidated"]=True;r["blockIDs"].append(record_id);save()
    rows=all_rows(child);assert len(rows)==len(r["blockIDs"])
    selected=[row for row in rows if row["id"]==record_id]
    assert len(selected)==1;assert_row(selected[0],body,record_id)
    item["currentRowSHA256"]=hashlib.sha256(json.dumps(selected[0],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    save()
    return record_id
try:
    assert minimum>=FLOOR+128*1024**2
    r["nativeSourceBefore"]=helper.source_admission()
    host_bytes=subprocess.check_output(["git","-C",str(ROOT),"show","HEAD:"+HOST_SOURCE],timeout=20)
    assert hashlib.sha256(host_bytes).hexdigest()==HOST_SHA
    r["hostCreationSource"]={"path":HOST_SOURCE,"sha256":HOST_SHA,"executed":False}
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
    helper.atomic(OUT/"private-copy-inventory.json",extracted)
    r["retainedCopy"]={"sourceArchiveSHA256":ARCHIVE_SHA,"copiedFiles":len(extracted),"inventorySHA256":sha(OUT/"private-copy-inventory.json"),"destination":str(DATA)}
    CONFIG=OUT/"offline-native-config.yml"
    CONFIG.write_text("network:\n  nodeconfPath: "+str(helper.NODECONF)+"\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n")
    r["configSHA256"]=sha(CONFIG)
    oldproof=OUT.parent/"markdown-body-native1/result.json"
    assert sha(oldproof)=="7c467547ec6c8158a861fc3c870647b3c8c2d1e3c29af9e3834ac5ce12202464"
    r["reusedOSDenialProbe"]={"resultSHA256":sha(oldproof),"policy":json.loads(oldproof.read_text())["networkDenialProbe"],"newNativePIDFlagsChecked":True}
    phase="exact native capability and one new empty Page"
    warm=start_native("blocks-warm")
    caps=record("capabilities",request(warm,"GET","/v1/pinkha/capabilities"))
    assert caps["contract"]=="pinkha-torah-native-v1" and caps["currentWriterBlockCreate"]==1
    page_intent={"kind":"page-create","dispatched":True,"response":None};r["mutations"].append(page_intent);save()
    created=request(warm,"POST",PRE+"/objects",{"type":"page"},201,mutation=page_intent)
    page_intent["response"]=created;save()
    assert created["objectId"] and "/" not in created["objectId"]
    page_intent["acknowledgementValidated"]=True;r["objectID"]=created["objectId"];r["blockIDs"]=[];save()
    assert all_rows(warm)==[]
    phase="six empty typed blocks, style variants, nesting and exact64KiB text"
    cases=[
      ("empty-paragraph","paragraph","",{},""),
      ("empty-heading-one","heading","",{"level":1},""),
      ("empty-quote","quote","",{},""),
      ("empty-code","code","",{"lang":"swift"},""),
      ("empty-unordered-list","list_item","",{"ordered":False},""),
      ("empty-unchecked","check_list_item","",{"checked":False},""),
      ("heading-six","heading","כותרת שש",{"level":6},""),
      ("code-text","code","let answer = 42\nprint(answer)",{"lang":"swift"},""),
      ("ordered-number-ten","list_item","פריט מספר עשר",{"ordered":True,"number":10},""),
      ("checked-item","check_list_item","פריט שהושלם",{"checked":True},""),
      ("nested-paragraph","paragraph","ילד של הכותרת",{},"@heading"),
      ("max64k-hebrew","paragraph","שלום"*8192,{},"")
    ]
    assert len(cases)==12 and len(cases[-1][2].encode())==65536
    heading_id=None
    for index,(name,kind,body_text,style,parent) in enumerate(cases):
        parent_id=heading_id if parent=="@heading" else parent
        assert parent_id is not None
        body={"type":kind,"text":body_text,"style":style,"nav":{"parentId":parent_id,"pos":chr(ord("A")+index)}}
        block_id=create_block(warm,name,body)
        if name=="empty-heading-one":heading_id=block_id
    rows=record("warm-block-rows",all_rows(warm));assert len(rows)==12
    for row,item in zip(rows,[x for x in r["mutations"] if x["kind"]=="block-create"]):
        assert_row(row,item["request"],item["response"]["recordIds"][0])
    assert {row["type"] for row in rows}=={"paragraph","heading","quote","code","list_item","check_list_item"}
    assert r["blockIDs"]==[row["id"] for row in rows]
    r["createdPageCount"]=1;r["createdBlockCount"]=12;r["emptyBlockTypes"]=6
    r["nativeCreateCalls"]=12;r["hostIntentDispatchCalls"]=0;save()
    phase="actual SIGKILL and new PID offline exact block readback"
    assert warm["p"].poll() is None and not absent(warm)
    warm["row"]["intentionalCrash"]=True
    os.killpg(warm["p"].pid,signal.SIGKILL);warm["p"].wait(timeout=10);close(warm,expected=-signal.SIGKILL,terminate=False)
    cold=start_native("blocks-cold");assert cold["p"].pid!=warm["p"].pid
    cold_rows=record("cold-block-rows",all_rows(cold));assert cold_rows==rows
    for row,item in zip(cold_rows,[x for x in r["mutations"] if x["kind"]=="block-create"]):
        assert_row(row,item["request"],item["response"]["recordIds"][0])
    r["coldNativeCreateCalls"]=0
    close(cold)
    r["status"]="PASS_ACTUAL_NATIVE_TWELVE_TYPED_BLOCK_CREATES_SIGKILL_COLD"
    r["actualNativeBlockAcceptance"]=True
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
        r["originalArchiveUnchanged"]=sha(ARCHIVE)==ARCHIVE_SHA
        r["hostCreationSourceUnchanged"]=hashlib.sha256(subprocess.check_output(["git","-C",str(ROOT),"show","HEAD:"+HOST_SOURCE],timeout=20)).hexdigest()==HOST_SHA
        if not all([r["nativeSourceAfter"]==r.get("nativeSourceBefore"),r["originalArchiveUnchanged"],r["hostCreationSourceUnchanged"],r["allOwnedGroupsAbsent"]]):r["status"]="FAIL"
    except BaseException as e:r["status"]="FAIL";r["errors"].append({"finalAdmission":str(e)})
    if r["status"]!="PASS_ACTUAL_NATIVE_TWELVE_TYPED_BLOCK_CREATES_SIGKILL_COLD":r["actualNativeBlockAcceptance"]=False
    r["finished"]=time.time();r["minimumFreeBytes"]=minimum;r["seconds"]=round(r["finished"]-r["started"],3);save()
    print(json.dumps({"status":r["status"],"actualNativeBlockAcceptance":r["actualNativeBlockAcceptance"],"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),"errors":r["errors"],"seconds":r["seconds"]}))
sys.exit(0 if r["actualNativeBlockAcceptance"] else 1)
