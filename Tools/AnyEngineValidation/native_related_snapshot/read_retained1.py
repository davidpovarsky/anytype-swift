#!/usr/bin/env python3
"""Read-only native full-Space/related snapshot discovery on an owned retained copy."""
import hashlib,importlib.util,json,os,pathlib,shutil,signal,socket,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("/mnt/development/projects/worktrees/anytype-engine-contracts-20261127")
BASE=pathlib.Path("/var/lib/pinkha-w1-engine-contracts-20261127")
OUT=BASE/"native-related-snapshot1"
BODY=BASE/"markdown-body-native1"
HELPER=pathlib.Path("/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/run_linux_filesv2_comparison.py")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(HELPER)=="bf7f478e939dedeb414a49cbd3ca4c6263350bea3985511707899e4e64f3b189"
spec=importlib.util.spec_from_file_location("native_helper",HELPER);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
r={"status":"RUNNING","readOnlyHTTP":True,"writes":0,"builds":0,"actualWholeSpaceAcceptance":False,"started":time.time(),"controllerSHA256":sha(pathlib.Path(__file__)),"observations":[]}
def save():h.atomic(OUT/"result.json",r)
p=None;log=None
def guard():
    assert shutil.disk_usage("/").free>=2*1024**3
    assert time.time()-r["started"]<120
def req(name,path,maximum=16*1024**2):
    guard();assert p.poll() is None
    request=urllib.request.Request(base+path,method="GET")
    try:
        with urllib.request.urlopen(request,timeout=10) as x:status=x.status;raw=x.read(maximum+1)
    except urllib.error.HTTPError as e:status=e.code;raw=e.read(maximum+1)
    assert len(raw)<=maximum
    dst=OUT/(name+".json");dst.write_bytes(raw)
    value=json.loads(raw)
    row={"name":name,"path":path,"status":status,"responseSHA256":sha(dst),"bytes":len(raw)}
    if isinstance(value,dict):
        row["keys"]=sorted(value)
        for k in ["contract","version","scope","coverage","readiness","unsupportedClaimsPresent"]:
            if k in value:row[k]=value[k]
        for k in ["claims","targets","conflictingTargets","records"]:
            if isinstance(value.get(k),list):row[k+"Count"]=len(value[k])
    r["observations"].append(row);save()
    return status,value
try:
    assert shutil.disk_usage("/").free>=2*1024**3+128*1024**2
    accepted=BODY/"result.json"
    assert sha(accepted)=="7c467547ec6c8158a861fc3c870647b3c8c2d1e3c29af9e3834ac5ce12202464"
    prior=json.loads(accepted.read_text());assert prior["actualBodyAcceptance"] and prior["allOwnedGroupsAbsent"]
    r["nativeBefore"]=h.source_admission()
    data=BODY/"private-account-copy";config=BODY/"offline-native-config.yml"
    assert sha(config)==prior["configSHA256"]
    with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    base="http://127.0.0.1:"+str(port)
    cmd=[sys.executable,"-B",str(h.OFFLINE),"--exec",str(h.BINARY),"run","--config",str(config),"--data-dir",str(data),"--addr","127.0.0.1:"+str(port)]
    env={k:v for k,v in os.environ.items() if not k.startswith("ANY_")};env.update(ANY_DATA_DIR=str(data),GOMAXPROCS="2",GOMEMLIMIT="512MiB")
    log=(OUT/"private-native.log").open("xb");p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    r["nativePID"]=p.pid;r["command"]=cmd;save()
    deadline=time.time()+45
    while True:
        assert p.poll() is None
        try:
            with urllib.request.urlopen(base+"/v1/health",timeout=1) as x:
                if x.status==200:break
        except (OSError,urllib.error.URLError):pass
        guard();assert time.time()<deadline;time.sleep(.25)
    fields=dict(x.split(":",1) for x in pathlib.Path("/proc/"+str(p.pid)+"/status").read_text().splitlines() if ":" in x)
    assert fields["NoNewPrivs"].strip()=="1" and fields["Seccomp"].strip()=="2"
    assert pathlib.Path("/proc/"+str(p.pid)+"/exe").resolve()==h.BINARY
    r["actualOSDenial"]={"NoNewPrivs":1,"Seccomp":2,"helperSHA256":h.OFFLINE_SHA}
    account="A7uNCqK2QB6J48HEDWGGX2Zv37vxFXZMxvF96R6sjzk7YPbx"
    space="bafyreicbctkf6ogqxta4pn2lfoijoesvmrtub2spj2ei2wbagywgcqau2y.11113vcq7lykz"
    target="bafyreigcv3i3omngn7eivsxmumj2ihui2kyke5v7aivrytxq6anwbag3e4"
    code,value=req("account","/v1/account");assert code==200 and value["id"]==account
    pre="/v1/spaces/"+space
    code,value=req("member",pre+"/members/me");assert code==200 and value["identity"]==account and value["permission"]=="owner"
    code,value=req("sync",pre+"/sync-status");assert code==200 and all(value[k]==0 for k in ["networkPeers","localPeers","globalPeers"])
    req("capabilities","/v1/pinkha/capabilities")
    req("bundle",pre+"/bundles/"+urllib.parse.quote("pinkha/torah-native/v1",safe=""))
    req("space-claims",pre+"/pinkha/claims?limit=10000")
    req("target-claims",pre+"/pinkha/objects/"+target+"/claims?limit=10000")
    for label,ref in [("removed-genesis","Genesis 1:1"),("retained-exodus","Exodus 1:1")]:
        parts=["ref","sefaria",ref];identity="torah1|"+"|".join(str(len(x.encode()))+":"+x for x in parts)
        path=pre+"/pinkha/related?"+urllib.parse.urlencode({"identity":identity,"limit":1000})
        req(label,path);req(label+"-repeat",path)
    identity="torah1|3:ref|7:sefaria|10:Exodus 1:1"
    req("invalid-limit",pre+"/pinkha/related?"+urllib.parse.urlencode({"identity":identity,"limit":0}))
    r["status"]="READ_ONLY_DISCOVERY_COMPLETE_NOT_ACCEPTANCE"
except BaseException as e:r["status"]="FAIL";r["error"]={"type":type(e).__name__,"message":str(e)}
finally:
    if p:
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5);r["forcedKill"]=True
        r["exitCode"]=p.returncode
        try:os.killpg(p.pid,0);r["groupAbsent"]=False
        except ProcessLookupError:r["groupAbsent"]=True
        if not r["groupAbsent"] or p.returncode!=0:r["status"]="FAIL"
    if log:log.close();r["logSHA256"]=sha(OUT/"private-native.log")
    r["nativeAfter"]=h.source_admission()
    r["sourceUnchanged"]=r.get("nativeBefore")==r["nativeAfter"]
    if not r["sourceUnchanged"]:r["status"]="FAIL"
    r["seconds"]=round(time.time()-r["started"],3);save()
    print(json.dumps({"status":r["status"],"seconds":r["seconds"],"observations":r["observations"],"error":r.get("error"),"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json")}))
sys.exit(0 if r["status"]=="READ_ONLY_DISCOVERY_COMPLETE_NOT_ACCEPTANCE" else 1)
