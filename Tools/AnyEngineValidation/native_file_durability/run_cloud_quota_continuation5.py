#!/usr/bin/env python3
"""Continue the retained synthetic production pair after a real quota refusal.

First prove cached bytes and native offload refusal under OS network denial.
Then request at most one explicit retry per still-nondurable file and preserve
all original signatures, source pins, custody, range, crash and offline gates.
"""
import hashlib, importlib.util, json, os, pathlib, signal, socket, subprocess, sys, time
import shutil, urllib.error, urllib.parse, urllib.request, traceback

ROOT = pathlib.Path("/var/lib/pinkha-w1-cloud-filesv2-20261127")
OUT = ROOT / "attempt5"
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
          "environment":"production nodes; newly generated isolated synthetic accounts",
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
    previous=json.loads((prior/"result.json").read_text())
    assert previous["failure"]=="'mime'" and previous["sourceBefore"]==previous["sourceAfter"]
    assert previous["nativeACLAccepted"] is True
    assert all(p["exitCode"]==0 and p["groupPositivelyAbsent"] and not p["forcedKill"] for p in previous["processes"])
    result["continuationOf"]={"path":str(prior/"result.json"),"sha256":sha(prior/"result.json")}
    result["sourceBefore"]=h.source_admission()
    assert result["sourceBefore"]==previous["sourceAfter"]
    result["controllerSHA256"]=sha(pathlib.Path(__file__))
    result["productionNodeconfSHA256"]=sha(PROD)
    assert sha(PROD)==sha(prior/"public-nodeconf.yml")
    # Reuse the exact qualified production config and existing independent accounts.
    (OUT/"config.yml").write_bytes((prior/"config.yml").read_bytes())
    result["configSHA256"]=sha(OUT/"config.yml")

    quota_prior=ROOT/"attempt4/result.json"
    limited=json.loads(quota_prior.read_text())
    assert limited["status"]=="FAIL" and limited["failure"]=="actual cloud storage limit refusal"
    assert limited["latestFileStatus"]["state"]=="limited"
    assert limited["latestFileStatus"]["fileId"]=="YhnuHkqoHza"
    assert "storage limit exceeded" in limited["latestFileStatus"]["lastErr"]
    assert limited["sourceBefore"]==limited["sourceAfter"]==result["sourceBefore"]
    assert all(p["exitCode"]==0 and p["groupPositivelyAbsent"] and not p["forcedKill"] for p in limited["processes"])
    result["originalQuotaRefusal"]={"path":str(quota_prior),"sha256":sha(quota_prior),"status":limited["latestFileStatus"]}
    alice_data,bob_data=prior/"alice",prior/"bob"
    aid,bid=previous["accounts"]["alice"],previous["accounts"]["bob"]
    sid,oid=previous["spaceID"],previous["objectID"]
    result.update(accounts=previous["accounts"],spaceID=sid,objectID=oid)
    payloads=[
        ("cloud-binary.bin",hashlib.shake_256(b"wave1-cloud-small").digest(8192),"application/octet-stream"),
        ("cloud-original.png",h.png_bytes(128,128,"wave1-cloud-image"),"image/png"),
        ("cloud-large.bin",hashlib.shake_256(b"wave1-cloud-large").digest(8*1024**2),"application/octet-stream"),
        ("cloud-thumb.png",h.png_bytes(64,64,"wave1-cloud-thumbnail"),"image/png")]

    phase="OS-offline owner reopen preserves quota-limited files and refuses removal of their only copy"
    local=start("alice-quota-local-offline",alice_data,offline=True)
    assert js(local,"GET","/v1/account")["id"]==aid
    offline_status=status(local,sid)
    assert offline_status["networkPeers"]==0
    rows=js(local,"GET","/v1/spaces/"+seg(sid)+"/files?"+urllib.parse.urlencode({"objectId":oid}))["files"]
    assert len(rows)==4 and {r["name"] for r in rows}=={x[0] for x in payloads}
    preserved=[]
    for name,body,mime in payloads:
        candidates=[r for r in rows if r["name"]==name]
        assert len(candidates)==1
        f=candidates[0];fid=f["fileId"]
        assert f["objectId"]==oid and f["size"]==len(body) and f["cached"] and not f["inline"]
        assert (f.get("mime") or "application/octet-stream")==mime
        car_before=observe_car(alice_data,f["rootCid"])
        row={"fileId":fid,"rootCid":f["rootCid"],"durableBefore":f["durable"],
             "cachedBefore":True,"carBefore":car_before}
        if f["durable"] is False:
            code,data,_=request(local,"POST","/v1/spaces/"+seg(sid)+"/files/"+seg(fid)+"/offload")
            denial=json.loads(data)
            row["offloadRefusal"]={"status":code,"body":denial}
            h.atomic(OUT/"quota-offload-observations.json",preserved+[row])
            assert code==409 and denial.get("error",{}).get("code")=="file.not_durable"
            assert info(local,sid,fid)["cached"] is True
            assert observe_car(alice_data,f["rootCid"])==car_before
        code,data,headers=request(local,"GET",content_path(sid,fid),timeout=45)
        assert code==200 and data==body and headers["Content-Type"]==mime
        row["plaintextSHA256"]=hashlib.sha256(data).hexdigest()
        row["cachedAfter"]=info(local,sid,fid)["cached"]
        assert row["cachedAfter"] is True
        preserved.append(row)
        h.atomic(OUT/"quota-offline-preservation.json",preserved)
    assert {r["fileId"] for r in preserved if "offloadRefusal" in r}.issuperset({"YhnuHkqoHza","AXSnqoZ52w3"}), "both original limited/nondurable files need actual native offload refusals"
    stop(local)
    result["quotaLocalPreservationAccepted"]=True
    mark("all original cached plaintext exact under OS network denial; both nondurable originals reject offload")
    phase="reopen the two existing synthetic cloud accounts"
    alice=start("alice-cloud-quota-retry",alice_data)
    bob=start("bob-cloud-quota-retry",bob_data)
    assert js(alice,"GET","/v1/account")["id"]==aid
    assert js(bob,"GET","/v1/account")["id"]==bid and aid!=bid
    grant=js(bob,"GET","/v1/spaces/"+seg(sid)+"/members/me")
    assert grant["identity"]==bid and grant["permission"]=="reader" and grant["status"]=="active"
    result["nativeACLAccepted"]=True
    mark("same independent identities and Reader grant rechecked without account/invite/file recreation")
    phase="wait for both reopened accounts to reconnect to cloud sync"
    ready_samples=[]
    def cloud_ready():
        a,b=status(alice,sid),status(bob,sid)
        ready_samples.append({"elapsedSeconds":round(time.monotonic()-started,3),"alice":a,"bob":b})
        h.atomic(OUT/"cloud-reconnect-observations.json",ready_samples)
        return a if a["networkPeers"]>0 and b["networkPeers"]>0 and a["state"]=="synced" and b["state"]=="synced" else False
    until(90,cloud_ready,"both existing cloud accounts reconnect")
    result["previousContinuation"]={"path":str(quota_prior),"sha256":sha(quota_prior),
        "failure":"native storage limit refused existing original image; all original bytes and accounts retained"}
    phase="qualified custody and complete decrypted remote metadata for existing four files"
    rows=js(alice,"GET","/v1/spaces/"+seg(sid)+"/files?"+urllib.parse.urlencode({"objectId":oid}))["files"]
    h.atomic(OUT/"owner-files-before.json",rows)
    assert len(rows)==4 and {r["name"] for r in rows}=={x[0] for x in payloads}
    records=[]
    for name,body,mime in payloads:
        hits=[r for r in rows if r["name"]==name];assert len(hits)==1
        f=hits[0]
        assert f["objectId"]==oid and f["size"]==len(body) and not f["inline"] and f["cached"]
        # API omits unknown MIME; the content endpoint documents octet-stream fallback.
        assert (f.get("mime") or "application/octet-stream")==mime
        records.append({"info":f,"bytes":body,"expectedMIME":mime})
    image=records[1];thumb=records[3]["bytes"]
    assert records[3]["info"]["variant"]=="thumb" and records[3]["info"]["variantOf"]==image["info"]["fileId"]
    metadata_observations=[]
    for record in records:
        f,body=record["info"],record["bytes"];fid=f["fileId"]
        status_path="/v1/spaces/"+seg(sid)+"/files/"+seg(fid)+"/status"
        before_retry=js(alice,"GET",status_path)
        if info(alice,sid,fid).get("durable") is not True:
            # One explicit native retry. A 204 never substitutes for a verified receipt.
            retry_intent={"fileId":fid,"stateBefore":before_retry,"dispatches":1,"acknowledged":False}
            result["explicitQuotaRetries"].append(retry_intent);save()
            code,data,_=request(alice,"POST","/v1/spaces/"+seg(sid)+"/files/"+seg(fid)+"/retry")
            retry_intent.update(httpStatus=code,responseBytes=len(data))
            save()
            assert code==204 and data==b"", "native retry not acknowledged"
            retry_intent["acknowledged"]=True;save()
        def durable():
            state=js(alice,"GET","/v1/spaces/"+seg(sid)+"/files/"+seg(fid)+"/status")
            record["lastStatus"]=state
            result["latestFileStatus"]=state;save()
            result["quotaRecoveryObservations"].append({"fileId":fid,"elapsedSeconds":round(time.monotonic()-started,3),"status":state})
            save()
            current=info(alice,sid,fid)
            return current if current.get("durable") is True else False
        durable_info=until(120,durable,"cloud quota recovery still lacks a real fileV2 verified custody receipt")
        def arrived():
            code,data,_=request(bob,"GET","/v1/spaces/"+seg(sid)+"/files/"+seg(fid))
            if code!=200:return False
            remote=json.loads(data)
            metadata_observations.append({"fileId":fid,"elapsedSeconds":round(time.monotonic()-started,3),"info":remote})
            h.atomic(OUT/"receiver-metadata-observations.json",metadata_observations)
            # Metadata visible without a payload key must not qualify as a member read.
            return remote if remote.get("durable") is True and remote.get("name")==f["name"] and remote.get("mime","")==f.get("mime","") else False
        receiver=until(90,arrived,"complete decrypted recipient file metadata")
        for key in ("fileId","rootCid","objectId","size","name"):
            assert receiver[key]==durable_info[key]==f[key]
        for key in ("mime","variant","variantOf"):
            assert receiver.get(key,"")==durable_info.get(key,"")==f.get(key,"")
        assert receiver["cached"] is False
        assert status(alice,sid)["networkPeers"]>0 and status(bob,sid)["networkPeers"]>0
        result["files"].append({"fileId":fid,"rootCid":f["rootCid"],"objectId":oid,"name":f["name"],
          "bytes":len(body),"plaintextSHA256":hashlib.sha256(body).hexdigest(),"mime":record["expectedMIME"],
          "durable":True,"receiverInitiallyCached":False,"metadataExact":True})
        save()
    result["cloudCustodyAccepted"]=True
    assert result["quotaLocalPreservationAccepted"] is True
    result["quotaFailureRecoveryAccepted"]=True
    result["quotaObservation"]=js(alice,"GET","/v1/spaces/"+seg(sid)+"/files/stats")
    mark("four real cloud custody receipts and remote metadata; P2P disabled")
    phase="partial cloud read and actual recipient crash"
    large=records[2]; fid=large["info"]["fileId"]
    code,data,headers=request(bob,"GET",content_path(sid,fid),headers={"Range":"bytes=0-65535"},timeout=60)
    assert code==206 and data==large["bytes"][:65536]
    assert headers["Content-Range"]=="bytes 0-65535/8388608"
    assert info(bob,sid,fid)["cached"] is False
    result["partialBeforeCrash"]=observe_car(bob_data,large["info"]["rootCid"])
    before_pid=bob["process"].pid
    stop(bob,crash=True)
    bob=start("bob-cloud-after-crash",bob_data)
    assert bob["process"].pid!=before_pid and js(bob,"GET","/v1/account")["id"]==bid
    result["partialAfterCrash"]=observe_car(bob_data,large["info"]["rootCid"])
    assert result["partialAfterCrash"]==result["partialBeforeCrash"]
    assert info(bob,sid,fid)["cached"] is False
    code,data,headers=request(bob,"GET",content_path(sid,fid),headers={"Range":"bytes=4194304-4259839"},timeout=60)
    assert code==206 and data==large["bytes"][4194304:4259840]
    assert headers["Content-Range"]=="bytes 4194304-4259839/8388608"
    result["partialCrashResumeAccepted"]=True
    phase="complete remote bytes and thumbnail read"
    for record in records:
        f,body=record["info"],record["bytes"]
        status(bob,sid)
        code,data,content_headers=request(bob,"GET",content_path(sid,f["fileId"]),timeout=90)
        assert content_headers["Content-Type"]==record["expectedMIME"]
        assert code==200 and data==body and info(bob,sid,f["fileId"])["cached"] is True
        car=observe_car(bob_data,f["rootCid"])
        assert car["sha256"]!=hashlib.sha256(body).hexdigest(),"encrypted CAR must differ from plaintext"
        record["cachedCAR"]=car
    code,data,_=request(bob,"GET",content_path(sid,image["info"]["fileId"])+"?variant=thumb",timeout=40)
    assert code==200 and data==thumb
    result["crossAccountContentAccepted"]=True
    mark("real range/crash/resume and complete cross-account cloud reads")
    phase="reader permission denies attachment"
    code,body,_=request(bob,"POST","/v1/spaces/"+seg(sid)+"/objects/"+seg(oid)+"/files?name=reader-denied.bin",b"reader must not write",{"Content-Type":"application/octet-stream"})
    denial=json.loads(body); result["readerWriteDenial"]={"status":code,"body":denial}
    save()
    assert code==403 and denial.get("error",{}).get("code") in ("space.read_only","acl.forbidden"), "reader write did not return typed native authority refusal"
    result["readerWriteDenialAccepted"]=True
    phase="cold OS-offline reopening in original recipient account"
    stop(alice); stop(bob)
    offline=start("bob-cold-os-offline",bob_data,offline=True)
    assert js(offline,"GET","/v1/account")["id"]==bid
    s=status(offline,sid); assert s["networkPeers"]==0
    for record in records:
        f,body=record["info"],record["bytes"]
        assert info(offline,sid,f["fileId"])["cached"] is True
        code,data,content_headers=request(offline,"GET",content_path(sid,f["fileId"]),timeout=40)
        assert content_headers["Content-Type"]==record["expectedMIME"]
        assert code==200 and data==body
    stop(offline)
    result["offlineReopenAccepted"]=True
    result["status"]="PASS_CLOUD_FILES_WITH_REAL_QUOTA_RECOVERY"
    mark("fresh recipient process reads all four cached files under OS TCP/UDP denial")
except BaseException as e:
    result["status"]="FAIL"
    result["failureType"]=type(e).__name__; result["failure"]=str(e)
    (OUT/"traceback.txt").write_text(traceback.format_exc())
finally:
    cleanup=[]
    for child in reversed(processes):
        try: stop(child,crash=child["row"].get("intentionalCrash",False))
        except BaseException as e:cleanup.append(str(e))
    if cleanup: result["cleanupErrors"]=cleanup; result["status"]="FAIL"
    for stream in handles:
        if not stream.closed:stream.close()
    try:
        result["sourceAfter"]=h.source_admission()
        if "sourceBefore" in result:
            assert result["sourceBefore"]==result["sourceAfter"]
        else:
            result["sourceAdmissionNotReached"]=True
            result["status"]="FAIL_PRENATIVE"
    except BaseException as e:
        result["sourceRecheckError"]=str(e);result["status"]="FAIL"
    save()
    print(json.dumps({"status":result["status"],"phase":phase,"failure":result.get("failure"),
                      "result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),
                      "cloudCustodyAccepted":result["cloudCustodyAccepted"],
                      "sourceUnchanged":result.get("sourceBefore")==result.get("sourceAfter")}))
