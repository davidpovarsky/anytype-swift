#!/usr/bin/env python3
"""Continue the retained synthetic production pair after a real quota refusal.

First prove cached bytes and native offload refusal under OS network denial.
Then request at most one explicit retry per still-nondurable file and preserve
all original signatures, source pins, custody, range, crash and offline gates.
"""
import hashlib, importlib.util, json, os, pathlib, signal, socket, subprocess, sys, time
import shutil, urllib.error, urllib.parse, urllib.request, traceback

ROOT = pathlib.Path("/var/lib/pinkha-w1-cloud-filesv2-20261127")
OUT = ROOT / "attempt6-small-cloud"
HELPER = pathlib.Path("/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/run_linux_filesv2_comparison.py")
HELPER_SHA = "bf7f478e939dedeb414a49cbd3ca4c6263350bea3985511707899e4e64f3b189"
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location("qualified_filesv2", HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
BINARY, OFFLINE = h.BINARY, h.OFFLINE
PROD = h.BUILD_ROOT / "source/internal/config/nodeconf-prod.yml"
os.umask(0o077)
OUT.mkdir(parents=True, exist_ok=False, mode=0o700)
LOGS = OUT / "private-logs"
LOGS.mkdir(mode=0o700)
started = time.monotonic()
processes, handles = [], []
phase = "source and production descriptor qualification"
result = {"schema":"pinkha-cloud-filesv2-two-accounts-v1","status":"RUNNING",
          "environment":"production nodes; existing synthetic recipient; P2P disabled and sender stopped",
          "retainedPrivateAccountsModified":False,"builds":0,"phase":phase,
          "phases":[],"processes":[],"files":[],"errors":[],
          "cloudCustodyAccepted":False,"crossAccountContentAccepted":False,
          "partialCrashResumeAccepted":False,"offlineReopenAccepted":False,
          "nativeACLAccepted":False,"readerWriteDenialAccepted":False,"quotaFailureRecoveryAccepted":False,"quotaLocalPreservationAccepted":False,
          "explicitQuotaRetries":[],"quotaRecoveryObservations":[],"encryptionEvidence":"native encrypted CAR plus verified plaintext; ciphertext difference alone is not cryptographic acceptance"}
minimum = shutil.disk_usage(OUT).free

def sha(p): return h.sha(p)
def save():
    result["elapsedSeconds"] = round(time.monotonic()-started,3)
    result["minimumFreeBytes"] = minimum
    result["phase"] = phase
    h.atomic(OUT/"result.json",result)
def guard():
    global minimum
    minimum = min(minimum, shutil.disk_usage(OUT).free)
    assert minimum >= 2*1024**3, "owned cloud validation storage floor"
    assert time.monotonic()-started < 950, "owned cloud validation deadline"
    assert not (OUT/"abort").exists(), "owned controller abort"
def mark(name, **data):
    result["phases"].append({"name":name,"elapsedSeconds":round(time.monotonic()-started,3),**data})
    save()
def absent(p):
    try: os.killpg(p.pid,0)
    except ProcessLookupError: return True
    return False
def spawn(name, command, env):
    guard()
    log=LOGS/(name+".log")
    stream=log.open("xb"); handles.append(stream)
    p=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    row={"name":name,"pid":p.pid,"command":command,"log":log.name,
         "forcedKill":False,"intentionalCrash":False}
    value={"process":p,"row":row,"stream":stream}
    processes.append(value); result["processes"].append(row); save()
    return value
def stop(peer, crash=False):
    p=peer["process"]; row=peer["row"]
    if "exitCode" in row: return
    if p.poll() is None:
        os.killpg(p.pid,signal.SIGKILL if crash else signal.SIGTERM)
        row["intentionalCrash"]=crash
    try: p.wait(timeout=20)
    except subprocess.TimeoutExpired:
        if p.poll() is None: os.killpg(p.pid,signal.SIGKILL); row["forcedKill"]=True
        p.wait(timeout=5)
    row["exitCode"]=p.returncode; row["groupPositivelyAbsent"]=absent(p)
    peer["stream"].close(); save()
    assert row["groupPositivelyAbsent"] and not row["forcedKill"], "owned cleanup not accepted"
    assert p.returncode == (-signal.SIGKILL if crash else 0), "native exit differs"
def env(data):
    e={k:v for k,v in os.environ.items() if not k.startswith("ANY_")}
    e.update(ANY_DATA_DIR=str(data),GOMAXPROCS="2",GOMEMLIMIT="2GiB")
    return e
def request(peer,method,path,body=None,headers=None,timeout=20,maximum=12*1024**2):
    guard(); assert peer["process"].poll() is None, "native exited"
    headers=dict(headers or {})
    if isinstance(body,(dict,list)):
        body=json.dumps(body,separators=(",",":")).encode(); headers["Content-Type"]="application/json"
    req=urllib.request.Request(peer["base"]+path,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            data=r.read(maximum+1); assert len(data)<=maximum
            return r.status,data,dict(r.headers)
    except urllib.error.HTTPError as e:
        data=e.read(65537); assert len(data)<=65536
        return e.code,data,dict(e.headers)
def js(peer,method,path,body=None,expected=200):
    code,data,_=request(peer,method,path,body)
    if code!=expected:
        q=OUT/("private-http-"+str(len(result["errors"]))+".json")
        h.atomic(q,{"method":method,"path":path,"status":code,"body":data.decode("utf8","replace")})
        result["errors"].append({"status":code,"expected":expected,"privateEvidence":q.name})
        save()
        raise RuntimeError("native HTTP status "+str(code)+"; original private response preserved")
    return json.loads(data) if data else None
def until(seconds,fn,label):
    end=time.monotonic()+seconds
    while True:
        guard()
        value=fn()
        if value: return value
        assert time.monotonic()<end,label
        time.sleep(.5)
def seg(value): return urllib.parse.quote(value,safe="")
def start(name,data,initialize=False,offline=False):
    guard()
    assert sha(BINARY)==h.BINARY_SHA and sha(OFFLINE)==h.OFFLINE_SHA
    assert sha(OUT/"config.yml")==result["configSHA256"]
    if initialize:
        data.mkdir(mode=0o700,exist_ok=False)
        child=spawn(name+"-init",[str(BINARY),"init","--config",str(OUT/"config.yml"),"--data-dir",str(data)],env(data))
        child["process"].wait(timeout=60)
        stop(child)
    with socket.socket() as s:
        s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
    command=[str(BINARY),"run","--config",str(OUT/"config.yml"),"--data-dir",str(data),"--addr","127.0.0.1:"+str(port)]
    if offline: command=[sys.executable,"-B",str(OFFLINE),"--exec"]+command
    child=spawn(name,command,env(data))
    child.update(base="http://127.0.0.1:"+str(port),data=data)
    child["row"]["offline"]=offline
    def healthy():
        assert child["process"].poll() is None,"native startup exited"
        try: return request(child,"GET","/v1/health",timeout=1)[0]==200
        except (OSError,urllib.error.URLError): return False
    until(60,healthy,"native readiness deadline")
    if offline:
        status=dict(l.split(":",1) for l in pathlib.Path("/proc/"+str(child["process"].pid)+"/status").read_text().splitlines() if ":" in l)
        assert status["NoNewPrivs"].strip()=="1" and status["Seccomp"].strip()=="2"
        assert pathlib.Path("/proc/"+str(child["process"].pid)+"/exe").resolve()==BINARY
        child["row"].update(actualInheritedNoNewPrivs=1,actualInheritedSeccomp=2)
    return child
def status(peer,sid):
    s=js(peer,"GET","/v1/spaces/"+seg(sid)+"/sync-status")
    assert s["localPeers"]==0 and s["globalPeers"]==0, "cloud proof contaminated by direct peers"
    return s
def info(peer,sid,fid): return js(peer,"GET","/v1/spaces/"+seg(sid)+"/files/"+seg(fid))
def content_path(sid,fid): return "/v1/spaces/"+seg(sid)+"/files/"+seg(fid)+"/content"
def observe_car(data,cid):
    files=list(data.rglob(cid+".car")); assert len(files)==1
    p=files[0]; s=p.stat(); assert p.resolve()==p and not p.is_symlink()
    return {"relativePath":str(p.relative_to(data)),"bytes":s.st_size,
            "allocatedBytes":s.st_blocks*512,"sha256":sha(p)}
def signal_stop(*_): raise RuntimeError("owned cloud validation interrupted")
signal.signal(signal.SIGTERM,signal_stop); signal.signal(signal.SIGINT,signal_stop)

try:
    guard()
    assert minimum >= 2*1024**3+256*1024**2
    prior=ROOT/"attempt2"
    original=json.loads((prior/"result.json").read_text())
    last_path=ROOT/"attempt5/result.json"
    last=json.loads(last_path.read_text())
    assert sha(last_path)=="84810888ba0be79546278f90286ff4da9e0a6052daf83922e787132ad628b59c"
    assert last["status"]=="FAIL" and last["quotaLocalPreservationAccepted"]
    assert all(p["exitCode"]==0 and p["groupPositivelyAbsent"] and not p["forcedKill"] for p in last["processes"])
    result["sourceBefore"]=h.source_admission()
    assert result["sourceBefore"]==last["sourceAfter"]
    result["controllerSHA256"]=sha(pathlib.Path(__file__))
    result["continuationOf"]={"path":str(last_path),"sha256":sha(last_path)}
    (OUT/"config.yml").write_bytes((prior/"config.yml").read_bytes())
    result["configSHA256"]=sha(OUT/"config.yml")
    assert sha(PROD)==sha(prior/"public-nodeconf.yml")
    result["productionNodeconfSHA256"]=sha(PROD)
    aid,bid=original["accounts"]["alice"],original["accounts"]["bob"]
    sid,oid=original["spaceID"],original["objectID"]
    result.update(accounts=original["accounts"],spaceID=sid,objectID=oid,
                  scope="only the two already-durable originals; large/image quota remains open",
                  selectedFilesCloudCustodyAccepted=False,selectedFilesCrossAccountBytesAccepted=False,
                  selectedFilesOfflineAccepted=False,allFourFilesAccepted=False)
    old_rows=json.loads((ROOT/"attempt3/owner-files-before.json").read_text())
    payloads=[
       ("cloud-binary.bin",hashlib.shake_256(b"wave1-cloud-small").digest(8192),"application/octet-stream"),
       ("cloud-thumb.png",h.png_bytes(64,64,"wave1-cloud-thumbnail"),"image/png")]
    pinned={}
    for name,body,mime in payloads:
        matches=[x for x in old_rows if x["name"]==name];assert len(matches)==1
        f=matches[0];assert f["objectId"]==oid and f["size"]==len(body) and not f["inline"]
        pinned[f["fileId"]]={"info":f,"body":body,"mime":mime}
    assert set(pinned)=={"BEaHYwGfZiM","ahKeFKn7uta"}
    # The production sender must remain stopped; independently copied LAN accounts use other paths.
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():continue
        try:args=(proc/"cmdline").read_bytes().split(b"\0")
        except OSError:continue
        assert not (str(BINARY).encode() in args and str(prior/"alice").encode() in args), "original sender must remain stopped"
    phase="reopen existing Reader on production cloud with direct peers disabled"
    bob=start("bob-durable-cloud-read",prior/"bob")
    assert js(bob,"GET","/v1/account")["id"]==bid
    grant=js(bob,"GET","/v1/spaces/"+seg(sid)+"/members/me")
    assert grant["identity"]==bid and grant["permission"]=="reader" and grant["status"]=="active"
    result["nativeACLAccepted"]=True
    until(90,lambda: status(bob,sid)["networkPeers"]>0,"actual recipient production network peers")
    phase="two original durable files start uncached and arrive from the cloud"
    records=[]
    for fid,record in pinned.items():
        f,body,mime=record["info"],record["body"],record["mime"]
        current=info(bob,sid,fid)
        for key in ("fileId","objectId","rootCid","size","name"):assert current[key]==f[key]
        assert (current.get("mime") or "application/octet-stream")==mime
        assert current["durable"] is True and current["cached"] is False and not current["inline"]
        assert status(bob,sid)["networkPeers"]>0
        t=time.monotonic()
        code,data,headers=request(bob,"GET",content_path(sid,fid),timeout=60)
        assert code==200 and data==body and headers["Content-Type"]==mime
        assert info(bob,sid,fid)["cached"] is True
        records.append({"fileId":fid,"rootCid":f["rootCid"],"name":f["name"],"bytes":len(body),
            "plaintextSHA256":hashlib.sha256(data).hexdigest(),"mime":mime,
            "durableBeforeRead":True,"initiallyCached":False,"nativeReadSeconds":round(time.monotonic()-t,3),
            "cachedCAR":observe_car(prior/"bob",f["rootCid"])})
        result["files"]=records;save()
    thumb=pinned["ahKeFKn7uta"]
    assert thumb["info"]["variant"]=="thumb" and thumb["info"]["variantOf"]=="YhnuHkqoHza"
    code,data,headers=request(bob,"GET",content_path(sid,"YhnuHkqoHza")+"?variant=thumb",timeout=40)
    assert code==200 and data==thumb["body"] and headers["Content-Type"]=="image/png"
    result["selectedFilesCloudCustodyAccepted"]=True
    result["selectedFilesCrossAccountBytesAccepted"]=True
    mark("two exact remote plaintexts plus original-image thumbnail resolver; sender stopped and P2P disabled")
    phase="actual Reader authority refuses a new attachment"
    files_before=js(bob,"GET","/v1/spaces/"+seg(sid)+"/files?"+urllib.parse.urlencode({"objectId":oid}))["files"]
    assert len(files_before)==4
    code,data,_=request(bob,"POST","/v1/spaces/"+seg(sid)+"/objects/"+seg(oid)+"/files?name=reader-denied.bin",
                        b"reader must not write",{"Content-Type":"application/octet-stream"})
    denial=json.loads(data)
    result["readerWriteDenial"]={"status":code,"body":denial};save()
    assert code==403 and denial.get("error",{}).get("code") in ("space.read_only","acl.forbidden")
    files_after=js(bob,"GET","/v1/spaces/"+seg(sid)+"/files?"+urllib.parse.urlencode({"objectId":oid}))["files"]
    assert {x["fileId"] for x in files_before}=={x["fileId"] for x in files_after}
    result["readerWriteDenialAccepted"]=True
    previous_pid=bob["process"].pid
    stop(bob)
    phase="fresh OS-offline recipient verifies the same two cached originals"
    offline=start("bob-durable-cold-offline",prior/"bob",offline=True)
    assert offline["process"].pid!=previous_pid and js(offline,"GET","/v1/account")["id"]==bid
    assert status(offline,sid)["networkPeers"]==0
    for fid,record in pinned.items():
        assert info(offline,sid,fid)["cached"] is True
        code,data,headers=request(offline,"GET",content_path(sid,fid),timeout=40)
        assert code==200 and data==record["body"] and headers["Content-Type"]==record["mime"]
    code,data,_=request(offline,"GET",content_path(sid,"YhnuHkqoHza")+"?variant=thumb",timeout=40)
    assert code==200 and data==thumb["body"]
    stop(offline)
    result["selectedFilesOfflineAccepted"]=True
    result["status"]="PASS_TWO_DURABLE_CLOUD_FILES_AND_RECIPIENT_OFFLINE_ONLY"
    mark("new native PID with actual NoNewPrivs1/Seccomp2 reads exact original cached bytes")
except BaseException as e:
    result["status"]="FAIL";result["failureType"]=type(e).__name__;result["failure"]=str(e)
    (OUT/"traceback.txt").write_text(traceback.format_exc())
finally:
    cleanup=[]
    for child in reversed(processes):
        try:stop(child,crash=child["row"].get("intentionalCrash",False))
        except BaseException as e:cleanup.append(str(e))
    if cleanup:result["cleanupErrors"]=cleanup;result["status"]="FAIL"
    for stream in handles:
        if not stream.closed:stream.close()
    try:
        result["sourceAfter"]=h.source_admission()
        assert result.get("sourceBefore")==result["sourceAfter"]
    except BaseException as e:result["sourceRecheckError"]=str(e);result["status"]="FAIL"
    save()
    print(json.dumps({"status":result["status"],"failure":result.get("failure"),
        "result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),
        "selectedFilesCrossAccountBytesAccepted":result.get("selectedFilesCrossAccountBytesAccepted"),
        "selectedFilesOfflineAccepted":result.get("selectedFilesOfflineAccepted"),
        "readerWriteDenialAccepted":result["readerWriteDenialAccepted"],"allFourFilesAccepted":False}))
