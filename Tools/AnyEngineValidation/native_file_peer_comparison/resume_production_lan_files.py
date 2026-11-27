#!/usr/bin/env python3
"""Read the existing production-test pair's files on exact private copies, within an isolated OS LAN."""
import argparse,errno,hashlib,importlib.util,json,os,re,shutil,signal,socket,stat,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path('/var/lib/pinkha-c-filesv2-20261126')
REPO=Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2_original',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=m.sha;digest=m.digest;pinned=m.pinned;atomic=m.atomic;identity=m.identity;source_admission=m.source_admission;account_inventory=m.account_inventory;png_bytes=m.png_bytes
OFFLINE=m.OFFLINE;OFFLINE_SHA=m.OFFLINE_SHA;SERVICE=m.SERVICE
FLOOR=2*1024**3
ESTIMATE=128*1024**2
NATIVE=ROOT/'acl-refresh-native1'
CUSTODY=ROOT/'production-lan-custody1'
PREVIOUS=ROOT/'production-lan-files1'
ACCOUNTS=CUSTODY
NODECONF=CUSTODY/'source-evidence/attempt2/public-nodeconf.yml'
NODECONF_SHA='6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060'
def native_admission():
    manifest=json.loads((NATIVE/'source-manifest.json').read_text())['files']
    actual={str(p.relative_to(NATIVE/'source')):{'sha256':sha(p),'bytes':p.stat().st_size} for p in (NATIVE/'source').rglob('*') if p.is_file()}
    assert actual==manifest
    return {'sourceManifestSHA256':sha(NATIVE/'source-manifest.json'),'files':len(actual),'binarySHA256':sha(NATIVE/'any')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--custody-receipt-sha",required=True)
    parser.add_argument("--previous-receipt-sha",required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{64}",args.custody_receipt_sha)
    assert re.fullmatch(r"[0-9a-f]{64}",args.previous_receipt_sha)
    out = args.output
    assert out.is_absolute() and out.parent.resolve() == out.parent
    assert str(out).startswith("/var/lib/pinkha-c-filesv2-20261126/")
    os.umask(0o077)
    out.mkdir(mode=0o700,exist_ok=False)
    logs=out/"private-logs"; logs.mkdir(mode=0o700)
    started=time.monotonic()
    minimum=shutil.disk_usage(out).free
    processes=[]; streams=[]; absent_ids=set(); phase="preflight"
    result={"protocol":"pinkha-copied-production-pair-existing-files-isolated-lan-v2","status":"RUNNING",
            "appBuilds":0,"goBuilds":0,"wholeSpaceMigrationAccepted":False,"cloudCustodyAccepted":False,
            "actualFilesV2Acceptance":False,"processes":[],"phases":[],"files":[],"errors":[],
            "resourcePolicy":{"estimatedNewBytes":ESTIMATE,"emergencyFreeBytes":FLOOR,
                "reason":"Already copied granted stores; four existing payloads total under 9 MiB, partial receiver cache and bounded WAL/log growth; no account initialization, attachment, compiler or cloud transfer. 2 GiB emergency floor unchanged."},
            "originalPrivateInviteFixed":False,"originalCloudStoresOpenedByThisController":False,
            "accountInitCalls":0,"joinCalls":0,"grantCalls":0,"attachmentCalls":0}
    config_hashes={}
    def save():
        result["seconds"]=round(time.monotonic()-started,3)
        result["minimumFreeBytes"]=minimum
        atomic(out/"result.json",result)
    def guard():
        nonlocal minimum
        minimum=min(minimum,shutil.disk_usage(out).free)
        assert minimum>=FLOOR,"runtime disk emergency"
        assert time.monotonic()-started<1200,"bounded FilesV2 controller deadline"
        assert not (out/"abort").exists(),"owned controller abort"
    def interrupted(*_):
        raise RuntimeError("owned FilesV2 controller interrupted")
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def mark(name,**values):
        result["phases"].append({"name":name,"seconds":round(time.monotonic()-started,3),**values});save()
    def absent(p):
        if p.pid in absent_ids:return True
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent_ids.add(p.pid);return True
        return False
    def spawn(name,command,env):
        guard()
        log_path=logs/(name+".log")
        stream=log_path.open("xb");streams.append(stream)
        p=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        row={"name":name,"pid":p.pid,"command":command,"log":log_path.name,
             "forcedKill":False,"intentionalCrash":False,"startedSeconds":round(time.monotonic()-started,3)}
        child={"process":p,"row":row,"stream":stream}
        processes.append(child);result["processes"].append(row);save()
        return child
    def complete(child,expected=0,timeout=20,terminate=True):
        p=child["process"];row=child["row"]
        if p.pid not in absent_ids and p.poll() is None:
            if terminate and not absent(p):os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if not absent(p):
                    os.killpg(p.pid,signal.SIGKILL);row["forcedKill"]=True
                p.wait(timeout=5)
                raise RuntimeError("owned process exceeded termination deadline")
        p.wait(timeout=5)
        row["exitCode"]=p.returncode
        row["groupPositivelyAbsent"]=absent(p)
        child["stream"].close()
        save()
        assert row["groupPositivelyAbsent"],"owned process group unresolved; no historical signal"
        assert not row["forcedKill"] and p.returncode==expected,"owned process exit differs"
    def run_short(name,command,env=None,seconds=60):
        child=spawn(name,command,env)
        end=time.monotonic()+seconds
        while child["process"].poll() is None:
            guard();assert time.monotonic()<end,"bounded owned short command"
            time.sleep(.2)
        complete(child,terminate=False)
        return (logs/child["row"]["log"]).read_bytes()
    def request(peer,method,path,body=None,headers=None,timeout=20,maximum=12*1024**2):
        guard();assert peer["process"].poll() is None,"native process exited"
        h=dict(headers or {})
        if isinstance(body,(dict,list)):
            body=json.dumps(body,separators=(",",":")).encode();h["Content-Type"]="application/json"
        req=urllib.request.Request(peer["base"]+path,data=body,method=method,headers=h)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read(maximum+1);assert len(raw)<=maximum,"bounded native response"
                return response.status,raw,dict(response.headers)
        except urllib.error.HTTPError as error:
            raw=error.read(65537);assert len(raw)<=65536
            return error.code,raw,dict(error.headers)
    def js(peer,method,path,body=None,expected=200):
        code,raw,_=request(peer,method,path,body)
        if code!=expected:
            errfile=out/("private-http-failure-"+str(len(result["errors"]))+".json")
            atomic(errfile,{"method":method,"path":path,"status":code,"body":raw.decode("utf-8","replace")})
            raise RuntimeError("HTTP "+str(code)+" expected "+str(expected)+"; private original retained")
        return json.loads(raw) if raw else None
    def until(seconds,predicate,label):
        end=time.monotonic()+seconds
        while True:
            guard();value=predicate()
            if value:return value
            assert time.monotonic()<end,label
            time.sleep(.4)
    def segment(value):
        assert isinstance(value,str) and value and "\x00" not in value and len(value.encode())<=4096
        return urllib.parse.quote(value,safe="")
    def config(path,nodeconf):
        text="network:\n  nodeconfPath: "+str(nodeconf)+"\nindex:\n  embedder: none\np2p:\n  enabled: true\n  localDiscovery: true\n  serviceName: "+SERVICE+"\n  global:\n    enabled: false\n"
        path.write_text(text)
        config_hashes[str(path)]=digest(text.encode())
    def env_for(data):
        env={k:v for k,v in os.environ.items() if not k.startswith("ANY_")}
        env.update(ANY_DATA_DIR=str(data),GOMAXPROCS="2",GOMEMLIMIT="1GiB")
        return env
    def start(name,data,cfg,initialize=False,offline=False):
        guard();pinned(cfg,config_hashes[str(cfg)],65536)
        pinned(NODECONF,NODECONF_SHA,65536)
        assert sha(native_binary)==native_sha and sha(OFFLINE)==OFFLINE_SHA
        if initialize:
            data.mkdir(mode=0o700,exist_ok=False)
            run_short(name+"-init",[str(native_binary),"init","--config",str(cfg),"--data-dir",str(data)],env_for(data))
        assert data.is_dir() and data.resolve()==data and not data.is_symlink()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0));port=listener.getsockname()[1]
        command=[str(native_binary),"run","--config",str(cfg),"--data-dir",str(data),"--addr","127.0.0.1:"+str(port)]
        if offline:command=[sys.executable,"-B",str(OFFLINE),"--exec"]+command
        child=spawn(name,command,env_for(data))
        child.update(base="http://127.0.0.1:"+str(port),data=data,offline=offline)
        child["row"]["offline"]=offline
        def healthy():
            if child["process"].poll() is not None:raise RuntimeError("native startup exited; original log retained")
            try:return request(child,"GET","/v1/health",timeout=1)[0]==200
            except (OSError,urllib.error.URLError):return False
        until(60,healthy,"native readiness timeout")
        if offline:
            fields=dict(line.split(":",1) for line in Path("/proc/"+str(child["process"].pid)+"/status").read_text().splitlines() if ":" in line)
            assert fields["NoNewPrivs"].strip()=="1" and fields["Seccomp"].strip()=="2"
            executable=Path("/proc/"+str(child["process"].pid)+"/exe").resolve()
            assert executable==native_binary and sha(executable)==native_sha
            child["row"]["actualInheritedNoNewPrivs"]=1;child["row"]["actualInheritedSeccomp"]=2
        pinned(cfg,config_hashes[str(cfg)],65536)
        return child
    def sync(peer,sid):
        value=js(peer,"GET","/v1/spaces/"+segment(sid)+"/sync-status")
        return {k:value[k] for k in ("state","networkPeers","localPeers","globalPeers")}
    def zero_network(peer,sid,offline=False):
        value=sync(peer,sid)
        assert value["networkPeers"]==0 and value["globalPeers"]==0
        if offline:assert value["localPeers"]==0
        return value
    def discovery(alice,bob,sid):
        def connected():
            a=js(alice,"GET","/v1/debug/p2p");b=js(bob,"GET","/v1/debug/p2p")
            sa=zero_network(alice,sid);sb=zero_network(bob,sid)
            if not a.get("peerId") or not b.get("peerId") or a["peerId"]==b["peerId"]:return False
            def actual(value,other):
                return [p for p in value.get("peers",[]) if p.get("peerId")==other and p.get("connected") is True and "lan" in (p.get("sources") or []) and sid in (p.get("spaceIds") or [])]
            aa=actual(a,b["peerId"]);bb=actual(b,a["peerId"])
            if aa and bb and sa["localPeers"]>0 and sb["localPeers"]>0:
                return {"alice":{"peerId":a["peerId"],"matching":aa,"sync":sa},
                        "bob":{"peerId":b["peerId"],"matching":bb,"sync":sb}}
            return False
        return until(90,connected,"actual native LAN shared-space discovery")
    def policy_probe():
        with socket.socket() as tcp,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            tcp.bind(("127.0.0.1",0));tcp.listen();port=tcp.getsockname()[1]
            udp.bind(("127.0.0.1",port));udp.settimeout(2)
            socket.create_connection(("127.0.0.1",port),timeout=2).close()
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:sender.sendto(b"baseline",("127.0.0.1",port))
            assert udp.recvfrom(64)[0]==b"baseline"
            raw=run_short("os-denial-probe",[sys.executable,"-B",str(OFFLINE),"--probe",str(port)],seconds=10)
            value=json.loads(raw)
            assert value["tcpDenied"] is True and value["udpDenied"] is True
            assert value["noNewPrivileges"] is True and value["seccompFilterActive"] is True
            return {"helperSHA256":OFFLINE_SHA,"baselineTCPAndUDPReachable":True,"actual":value}
    def member(peer,sid,account,permission):
        value=js(peer,"GET","/v1/spaces/"+segment(sid)+"/members/me")
        assert value["identity"]==account and value["status"]=="active" and value["permission"]==permission
        return value
    def file_path(sid,fid):
        return "/v1/spaces/"+segment(sid)+"/files/"+segment(fid)
    def info(peer,sid,fid):
        return js(peer,"GET",file_path(sid,fid))
    def metadata_complete(value,attached,oid,size,cached):
        for key in ("fileId","rootCid","name"):
            if value.get(key)!=attached[key]:return False
        if value.get('mime','')!=attached.get('mime',''):return False
        if value.get("size")!=size or value.get("objectId")!=oid:return False
        if value.get("inline") is not False or value.get("durable") is not attached["durable"] or value.get("cached") is not cached:return False
        for key in ("variant","variantOf"):
            if key in attached and value.get(key)!=attached[key]:return False
        return True
    def expect_info(value,attached,oid,size,cached):
        assert metadata_complete(value,attached,oid,size,cached)
        for key in ("fileId","rootCid","name"):
            assert value[key]==attached[key]
        assert value.get('mime','')==attached.get('mime','')
        assert value["size"]==size and value["objectId"]==oid
        assert value["inline"] is False and value["durable"] is attached["durable"] and value["cached"] is cached
    def range_bytes(peer,sid,record,start,length):
        path=file_path(sid,record["fileId"])+"/content"
        code,raw,headers=request(peer,"GET",path,headers={"Range":"bytes="+str(start)+"-"+str(start+length-1)},timeout=40)
        assert code==206 and raw==record["bytes"][start:start+length]
        assert headers.get("Content-Range")==("bytes "+str(start)+"-"+str(start+length-1)+"/"+str(len(record["bytes"])))
        return {"offset":start,"bytes":length,"sha256":digest(raw),"contentRange":headers["Content-Range"]}
    def car_observation(data,cid):
        assert Path(cid).name==cid and "\\" not in cid and len(cid)<256
        paths=[p for p in data.rglob(cid+".car") if p.is_file()]
        assert len(paths)==1
        path=paths[0];assert path.resolve()==path and not path.is_symlink()
        s=path.stat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
        value={"relativePath":str(path.relative_to(data)),"bytes":s.st_size,"allocatedBytes":s.st_blocks*512,"sha256":sha(path)}
        assert identity(path.stat())==identity(s)
        value["hasSparseAllocation"]=value["allocatedBytes"]<value["bytes"]
        return value
    def encrypted_car(data,record):
        observation=car_observation(data,record["attached"]["rootCid"])
        path=data/observation["relativePath"];raw=pinned(path,observation["sha256"],16*1024**2)
        plain=record["bytes"];assert len(plain)>=96 and raw!=plain
        offsets=sorted({0,len(plain)//2,len(plain)-64})
        for offset in offsets:assert plain[offset:offset+64] not in raw
        observation.update(plaintextSHA256=digest(plain),plaintextSampleBytes=64,plaintextSampleOffsetsAbsent=offsets)
        return observation
    try:
        assert minimum>=FLOOR+ESTIMATE,"measured native phase does not fit"
        result["sourcesBefore"]=source_admission()
        result["controllerSHA256"]=sha(Path(__file__))
        (out/'controller.py').write_bytes(pinned(Path(__file__),result['controllerSHA256'],65536))
        public=pinned(NODECONF,NODECONF_SHA,65536)
        assert b"fileV2" in public
        phase="exact copied production-account custody and isolated network"
        prior=json.loads(pinned(CUSTODY/"result.json",args.custody_receipt_sha,4*1024**2))
        assert prior["status"]=="PASS_EXACT_COPY_CUSTODY_NOT_LAN_ACCEPTANCE"
        assert prior["originalAccountsUnchanged"] and prior["allCopiesByteAndModeIdentical"]
        assert prior["accountInitCalls"]==prior["joinCalls"]==prior["grantCalls"]==prior["attachments"]==prior["nativeRuns"]==0
        assert prior["sourceBefore"]==prior["sourceAfter"]==result["sourcesBefore"]
        previous=json.loads(pinned(PREVIOUS/'result.json',args.previous_receipt_sha,4*1024**2))
        assert previous['status']=='FAIL' and previous['failedPhase']=='existing file metadata and original qualified plaintext admission'
        assert previous['errors']==[{'message':'original owner complete native file metadata','type':'AssertionError'}]
        assert previous['files']==[] and previous['attachmentCalls']==previous['grantCalls']==previous['joinCalls']==previous['accountInitCalls']==0
        assert previous['allOwnedGroupsPositivelyAbsent'] and len(previous['processes'])==2
        assert all(p['exitCode']==0 and p['groupPositivelyAbsent'] and not p['forcedKill'] for p in previous['processes'])
        assert previous['priorCopyReceiptSHA256']==args.custody_receipt_sha
        assert previous['finalAccountInventorySHA256']=='ca3aa80146f7a441fdab83397a47a27422d822e187f1f42067f3ffa1dfb75833'
        assert previous['sourcesBefore']==previous['finalSourceAdmission']==result['sourcesBefore']
        if 'sourcesAfter' in previous:assert previous['sourcesAfter']==result['sourcesBefore']
        pinned(PREVIOUS/'controller.py',previous['controllerSHA256'],65536)
        custody=json.loads(pinned(PREVIOUS/"private-current-accounts.json",previous["finalAccountInventorySHA256"],4*1024**2))
        for name in ("alice","bob"):assert account_inventory(ACCOUNTS/name)==custody[name]
        cloud=json.loads(pinned(CUSTODY/'source-evidence/attempt5/result.json','84810888ba0be79546278f90286ff4da9e0a6052daf83922e787132ad628b59c',2*1024**2))
        assert cloud['nativeACLAccepted'] and cloud['quotaLocalPreservationAccepted']
        assert cloud['accounts']==prior['accounts'] and cloud['spaceID']==prior['spaceId'] and cloud['objectID']==prior['objectId']
        assert all(p['exitCode']==0 and p['groupPositivelyAbsent'] and not p['forcedKill'] for p in cloud['processes'])
        result['copiedProductionGrantAndQuotaReceiptSHA256']=sha(CUSTODY/'source-evidence/attempt5/result.json')
        build=json.loads(pinned(NATIVE/"result.json",'bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380',4*1024**2))
        assert build["status"]=="PASS_BUILD_ONLY" and build["allOwnedGroupsPositivelyAbsent"] and build["isolatedSourceUnchanged"]
        native_binary=NATIVE/"any";native_sha=build["binary"]["sha256"]
        assert sha(native_binary)==native_sha
        assert sha(NATIVE/"source-manifest.json")==build["sourceManifestSHA256"]
        result["nativeBefore"]=native_admission()
        assert result['nativeBefore']==previous['nativeBefore']==previous['finalNativeAdmission']
        result["priorCopyReceiptSHA256"]=args.custody_receipt_sha
        result["priorCustodySHA256"]=previous["finalAccountInventorySHA256"]
        result['previousAttemptSHA256']=args.previous_receipt_sha
        result['preservedPreviousLANObservation']=previous['initialLANDiscovery']
        result['metadataContractCorrection']='Compare stored MIME exactly, including documented omission; use native octet-stream fallback only for HTTP content type. PNG must retain explicit image/png.'
        result["nativeBuildReceiptSHA256"]=sha(NATIVE/'result.json')
        result["noAccountInit"]=True;result["noSpaceOrObjectCreate"]=True;result["noJoinOrInviteMint"]=True
        alice_data=ACCOUNTS/"alice";bob_data=ACCOUNTS/"bob"
        aid=prior["accounts"]["alice"];bid=prior["accounts"]["bob"];assert aid!=bid
        sid=prior["spaceId"];oid=prior["objectId"]
        result["accounts"]=prior["accounts"];result["spaceId"]=sid;result["objectId"]=oid
        own_ns=os.readlink('/proc/self/ns/net');host_ns=os.readlink('/proc/1/ns/net')
        assert own_ns!=host_ns,"must launch through unshare --net; host network changes prohibited"
        original_if=json.loads(subprocess.check_output(['ip','-j','link','show'],text=True))
        assert [v['ifname'] for v in original_if]==['lo'],"namespace must be fresh"
        for cmd in [['ip','link','set','lo','up'],['ip','link','add','pfv2a','type','veth','peer','name','pfv2b'],['ip','addr','add','198.18.0.1/30','dev','pfv2a'],['ip','addr','add','198.18.0.2/30','dev','pfv2b'],['ip','link','set','pfv2a','up'],['ip','link','set','pfv2b','up']]:
            subprocess.run(cmd,check=True,timeout=5)
        routes=json.loads(subprocess.check_output(['ip','-j','route','show'],text=True))
        assert len(routes)==2 and all(v['dst']=='198.18.0.0/30' and v['dev'] in ('pfv2a','pfv2b') for v in routes)
        assert json.loads(subprocess.check_output(['ip','-j','-6','route','show','default'],text=True))==[]
        refused=[]
        for port in range(24001,24007):
            with socket.socket() as probe:
                probe.settimeout(1);observed=probe.connect_ex(('127.0.0.1',port))
                assert observed==errno.ECONNREFUSED;refused.append({'port':port,'connectErrno':observed})
        with socket.socket() as external_probe:
            external_probe.settimeout(1);wan_errno=external_probe.connect_ex(('198.51.100.1',443))
            assert wan_errno==errno.ENETUNREACH,'fresh namespace must have no route outside its internal LAN'
        result['networkNamespace']={'own':own_ns,'host':host_ns,'distinct':True,'routes':routes,'nodePortsRefused':refused,'noIPv6DefaultRoute':True,'externalConnectErrno':wan_errno,'hostNetworkChanged':False}
        original_config=out/"public-nodeconf.yml";original_config.write_bytes(public)
        lan_cfg=out/"lan-config.yml";config(lan_cfg,original_config)
        result['LANConfiguration']={'nodeConfigSHA256':NODECONF_SHA,'cachedAccountConfigPreserved':True,'sameNetworkIdentity':True,'isolation':'fresh OS network namespace; only internal veth and loopback'}
        phase="LAN-only native restart"
        alice=start("alice-lan",alice_data,lan_cfg);bob=start("bob-lan",bob_data,lan_cfg)
        assert js(alice,"GET","/v1/account")["id"]==aid and js(bob,"GET","/v1/account")["id"]==bid
        member(alice,sid,aid,"owner");member(bob,sid,bid,"reader")
        result["initialLANDiscovery"]=discovery(alice,bob,sid)
        mark("actual native LAN discovery with zero network peers")
        phase="existing file metadata and original qualified plaintext admission"
        descriptors=json.loads(pinned(CUSTODY/'source-evidence/attempt3/owner-files-before.json','11a8d9d497501a8a2fec17571be1b7b6f55ba05607542ccbbce6fe19190ed21f',65536))
        preserved=json.loads(pinned(CUSTODY/'source-evidence/attempt5/quota-offline-preservation.json','08e3fdd7288ce14674e22e4fd76fd31fd79e9f6ff49f24e506f6c0b345c97723',65536))
        assert len(descriptors)==len(preserved)==4
        by_name={v['name']:v for v in descriptors};by_id={v['fileId']:v for v in preserved}
        assert len(by_name)==len(by_id)==4 and set(by_id)=={v['fileId'] for v in descriptors}
        ordered=['cloud-binary.bin','cloud-original.png','cloud-large.bin','cloud-thumb.png']
        assert set(by_name)==set(ordered)
        records=[]
        for name in ordered:
            zero_network(alice,sid);zero_network(bob,sid)
            descriptor=by_name[name];file_id=descriptor['fileId'];proof=by_id[file_id]
            mime='image/png' if name.endswith('.png') else 'application/octet-stream'
            assert proof['rootCid']==descriptor['rootCid'] and proof['cachedBefore'] and proof['cachedAfter']
            assert descriptor['objectId']==oid and descriptor['inline'] is False and descriptor['durable'] is proof['durableBefore']
            def complete_owner_metadata():
                value=info(alice,sid,file_id)
                result.setdefault('ownerMetadataObserved',{})[file_id]=value
                for key in ('fileId','rootCid','name','objectId','size','inline','durable'):
                    if value.get(key)!=descriptor[key]:return False
                if value.get('mime','')!=descriptor.get('mime',''):return False
                if (value.get('mime') or 'application/octet-stream')!=mime or value.get('cached') is not True:return False
                for key in ('variant','variantOf'):
                    if key in descriptor and value.get(key)!=descriptor[key]:return False
                return value
            attached=until(60,complete_owner_metadata,'original owner complete native file metadata')
            code,content,headers=request(alice,'GET',file_path(sid,file_id)+'/content',timeout=60)
            assert code==200 and len(content)==descriptor['size'] and digest(content)==proof['plaintextSHA256']
            assert headers.get('Content-Type')==mime
            record={"fileId":attached["fileId"],"attached":attached,"bytes":content,'contentType':mime}
            def row_arrived():
                code,raw,_=request(bob,"GET",file_path(sid,record["fileId"]))
                if code!=200:return False
                value=json.loads(raw)
                return value if metadata_complete(value,attached,oid,len(content),False) else False
            arrived=until(90,row_arrived,"recipient complete native file metadata")
            expect_info(arrived,attached,oid,len(content),False)
            record["initial"]=arrived;records.append(record)
            result["files"].append({"fileId":record["fileId"],"name":name,"plaintextBytes":len(content),"plaintextSHA256":digest(content),
                                   "rootCid":attached["rootCid"],"objectId":oid,"mime":mime,'storedMIME':attached.get('mime',''),'storedMIMEOmitted':'mime' not in attached,"inline":False,"durable":attached['durable'],"recipientInitiallyCached":False,'alreadyAttachedBeforeThisRun':True})
            save()
        image=records[1];variant=records[3];thumb=variant['bytes']
        assert variant['attached']['variant']=='thumb' and variant['attached']['variantOf']==image['fileId']
        for record,dimension in ((image,128),(variant,64)):
            assert record['bytes'][:8]==b'\x89PNG\r\n\x1a\n'
            assert int.from_bytes(record['bytes'][16:20],'big')==dimension
            assert int.from_bytes(record['bytes'][20:24],'big')==dimension
        result['imageDimensions']={'original':[128,128],'thumbnail':[64,64]}
        result['files'][3].update(variant='thumb',variantOf=image['fileId'])
        assert len(records[2]['bytes'])==8*1024**2
        mark("four existing native files and exact variant metadata admitted without reattachment",files=4)
        phase="partial encrypted range then intentional owned crash"
        partial=records[2]
        part=range_bytes(bob,sid,partial,0,32768)
        expect_info(info(bob,sid,partial["fileId"]),partial["attached"],oid,len(partial["bytes"]),False)
        zero_network(alice,sid);zero_network(bob,sid)
        p=bob["process"];assert p.poll() is None and p.pid not in absent_ids and not absent(p)
        bob["row"]["intentionalCrash"]=True
        os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
        complete(bob,expected=-signal.SIGKILL,terminate=False)
        complete(alice)
        partial_car=car_observation(bob_data,partial["attached"]["rootCid"])
        assert partial_car["hasSparseAllocation"],"actual partial CAR must retain sparse holes"
        result["partialCrash"]={"downloadedRange":part,"cachedBeforeCrash":False,"receiverExitCode":-signal.SIGKILL,
                                "actualOwnedCrash":True,"partialEncryptedCAR":partial_car}
        result["offlinePolicy"]=policy_probe()
        phase="new recipient process reads persisted partial range under OS denial"
        bob=start("bob-partial-offline",bob_data,lan_cfg,offline=True)
        assert js(bob,"GET","/v1/account")["id"]==bid
        member(bob,sid,bid,"reader")
        result["partialColdSync"]=zero_network(bob,sid,offline=True)
        assert range_bytes(bob,sid,partial,0,32768)==part
        expect_info(info(bob,sid,partial["fileId"]),partial["attached"],oid,len(partial["bytes"]),False)
        complete(bob)
        assert car_observation(bob_data,partial["attached"]["rootCid"])==partial_car
        mark("persisted partial native range survived crash and new-PID OS-offline read")
        phase="resume partial native file over actual LAN"
        alice=start("alice-resume-lan",alice_data,lan_cfg);bob=start("bob-resume-lan",bob_data,lan_cfg)
        assert js(alice,"GET","/v1/account")["id"]==aid and js(bob,"GET","/v1/account")["id"]==bid
        member(alice,sid,aid,"owner");member(bob,sid,bid,"reader")
        result["resumeLANDiscovery"]=discovery(alice,bob,sid)
        expect_info(info(bob,sid,partial["fileId"]),partial["attached"],oid,len(partial["bytes"]),False)
        for i,record in enumerate(records):
            zero_network(alice,sid);zero_network(bob,sid)
            code,raw,headers=request(bob,"GET",file_path(sid,record["fileId"])+"/content",timeout=60)
            assert code==200 and raw==record["bytes"]
            assert headers.get("Content-Type")==record['contentType']
            expect_info(info(bob,sid,record["fileId"]),record["attached"],oid,len(raw),True)
            selected=range_bytes(bob,sid,record,min(200000,len(raw)//3),min(32768,len(raw)-min(200000,len(raw)//3)))
            result["files"][i].update(recipientComplete=True,destinationSHA256=digest(raw),range=selected)
        code,raw,headers=request(bob,"GET",file_path(sid,image["fileId"])+"/content?variant=thumb",timeout=40)
        assert code==200 and raw==thumb and headers.get("Content-Type")=="image/png"
        result["variantResolution"]={"nativeVariantOf":image["fileId"],"variantFileId":variant["fileId"],"byteEquality":True,"sha256":digest(raw)}
        result["finalLANSync"]={"alice":zero_network(alice,sid),"bob":zero_network(bob,sid)}
        mark("full plaintext and ranges equal after completing existing partial cache",files=4)
        complete(alice);complete(bob)
        result['encryptedCacheObservations']=[{'fileId':record['fileId'],'alice':encrypted_car(alice_data,record),'bob':encrypted_car(bob_data,record)} for record in records]
        phase="fresh recipient OS-offline full byte and variant read"
        bob=start("bob-complete-offline",bob_data,lan_cfg,offline=True)
        assert js(bob,"GET","/v1/account")["id"]==bid
        member(bob,sid,bid,"reader")
        result["fullColdSync"]=zero_network(bob,sid,offline=True)
        cold=[]
        for record in records:
            code,raw,_=request(bob,"GET",file_path(sid,record["fileId"])+"/content",timeout=40)
            assert code==200 and raw==record["bytes"]
            expect_info(info(bob,sid,record["fileId"]),record["attached"],oid,len(raw),True)
            cold.append({"fileId":record["fileId"],"bytes":len(raw),"sha256":digest(raw)})
        code,raw,_=request(bob,"GET",file_path(sid,image["fileId"])+"/content?variant=thumb")
        assert code==200 and raw==thumb
        result["coldFiles"]=cold
        code,raw,_=request(bob,"POST","/v1/spaces/"+segment(sid)+"/objects/"+segment(oid)+"/files?name=denied-offline-reader.bin",b"reader denial fixture",{"Content-Type":"application/octet-stream"})
        denied=json.loads(raw);assert code==403 and denied["error"]["code"] in ("space.read_only","acl.forbidden")
        result['offlineReaderWriteDenial']={'status':code,'errorCode':denied['error']['code']}
        assert zero_network(bob,sid,offline=True)["networkPeers"]==0
        complete(bob)
        mark("all four files and native variant equal in fresh OS-offline process",files=4)
        result["sourcesAfter"]=source_admission()
        assert pinned(NODECONF,NODECONF_SHA)==public
        assert original_config.read_bytes()==public
        result["nativeAfter"]=native_admission();assert result["nativeAfter"]==result["nativeBefore"]
        for path,value in config_hashes.items():pinned(Path(path),value,65536)
        result["actualFilesV2Acceptance"]=True
        result["status"]="PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES"
    except BaseException as error:
        result.update(status="FAIL",failedPhase=phase)
        result["errors"].append({"type":type(error).__name__,"message":str(error)})
    finally:
        for child in reversed(processes):
            try:
                if child["process"].pid not in absent_ids:
                    expected=-signal.SIGKILL if child["row"]["intentionalCrash"] else 0
                    complete(child,expected=expected)
            except BaseException as error:
                result["status"]="FAIL";result["actualFilesV2Acceptance"]=False
                result["errors"].append({"cleanup":child["row"]["name"],"type":type(error).__name__,"message":str(error)})
        for stream in streams:
            try:stream.close()
            except BaseException as error:
                result["status"]="FAIL";result["errors"].append({"logClose":type(error).__name__})
        try:
            result["retainedPrivateLogs"]=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(logs.iterdir()) if p.is_file()]
        except BaseException as error:
            result["status"]="FAIL";result["errors"].append({"logInventory":type(error).__name__})
        try:
            result["finalSourceAdmission"]=source_admission()
        except BaseException as error:
            result["status"]="FAIL";result["errors"].append({"sourceRetention":type(error).__name__,"message":str(error)})
        result["allOwnedGroupsPositivelyAbsent"]=all(p["process"].pid in absent_ids for p in processes)
        try:
            pinned(CUSTODY/"result.json",args.custody_receipt_sha,4*1024**2)
            if processes:
                assert result["allOwnedGroupsPositivelyAbsent"],"account custody requires owned absence"
                current={name:account_inventory(ACCOUNTS/name) for name in ("alice","bob")}
                for name in current:assert account_inventory(ACCOUNTS/name)==current[name]
                atomic(out/"private-current-accounts.json",current)
                result["finalAccountInventorySHA256"]=sha(out/"private-current-accounts.json")
            result["finalNativeAdmission"]=native_admission()
            if result.get("nativeBefore"):assert result["nativeBefore"]==result["finalNativeAdmission"]
        except BaseException as error:
            result["status"]="FAIL";result["actualFilesV2Acceptance"]=False
            result["errors"].append({"accountCustody":type(error).__name__,"message":str(error)})
        if result["status"]!="PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES":
            result["actualFilesV2Acceptance"]=False
        save()
    print(json.dumps({"status":result["status"],"result":str(out/"result.json"),"sha256":sha(out/"result.json"),
                      "actualFilesV2Acceptance":result["actualFilesV2Acceptance"],"seconds":result["seconds"]}))
    return 0 if result["status"]=="PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES" else 1

if __name__=="__main__":
    raise SystemExit(main())
