#!/usr/bin/env python3
"""Continue original retained file IDs with strict live metadata diagnostics; never reattach confirmed files."""
import argparse,errno,hashlib,importlib.util,json,os,re,shutil,signal,socket,stat,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path('/var/lib/pinkha-c-filesv2-20261126')
REPO=Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2_original',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=m.sha;digest=m.digest;pinned=m.pinned;atomic=m.atomic;identity=m.identity;source_admission=m.source_admission;account_inventory=m.account_inventory;png_bytes=m.png_bytes
NODECONF=m.NODECONF;NODECONF_SHA=m.NODECONF_SHA;OFFLINE=m.OFFLINE;OFFLINE_SHA=m.OFFLINE_SHA;ARCHIVE=m.ARCHIVE;ARCHIVE_SHA=m.ARCHIVE_SHA;SERVICE=m.SERVICE
FLOOR=2*1024**3
ESTIMATE=128*1024**2
NATIVE=ROOT/'acl-refresh-native1'
GRANT=ROOT/'retained-recipient-continuation1'
PRIORFILES=ROOT/'original-files-after-join1'
PRIORFILES_SHA='39d0d0a6887a7766d9a73012178f38f1f2d4af8cc2bade924bcf81daaf1131d2'
ACCOUNTS=ROOT/'attempt1'
def native_admission():
    manifest=json.loads((NATIVE/'source-manifest.json').read_text())['files']
    actual={str(p.relative_to(NATIVE/'source')):{'sha256':sha(p),'bytes':p.stat().st_size} for p in (NATIVE/'source').rglob('*') if p.is_file()}
    assert actual==manifest
    return {'sourceManifestSHA256':sha(NATIVE/'source-manifest.json'),'files':len(actual),'binarySHA256':sha(NATIVE/'any')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--continuation-receipt-sha",required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{64}",args.continuation_receipt_sha)
    out = args.output
    assert out.is_absolute() and out.parent.resolve() == out.parent
    assert str(out).startswith("/var/lib/pinkha-c-filesv2-20261126/")
    os.umask(0o077)
    out.mkdir(mode=0o700,exist_ok=False)
    logs=out/"private-logs"; logs.mkdir(mode=0o700)
    started=time.monotonic()
    minimum=shutil.disk_usage(out).free
    processes=[]; streams=[]; absent_ids=set(); phase="preflight"
    result={"protocol":"pinkha-original-retained-file-continuation-and-live-sync-diagnostics-v2","status":"RUNNING",
            "appBuilds":0,"goBuilds":0,"wholeSpaceMigrationAccepted":False,"cloudCustodyAccepted":False,
            "actualFilesV2Acceptance":False,"processes":[],"phases":[],"files":[],"errors":[],
            "accountInitCalls":0,"joinCalls":0,"grantCalls":0,"inviteCreateCalls":0,"attachmentCalls":0,"attachmentLedger":[],"metadataObservations":[],"stallDiagnostics":[],
            "resourcePolicy":{"estimatedNewBytes":ESTIMATE,"emergencyFreeBytes":FLOOR,
                "reason":"Original retained granted stores; five payloads under11MiB plus8KiB uncached permission canary, two encrypted caches and bounded WAL/log growth. Reuse accepted crash/partial/integrity proof without rerun. No init, new grant, compiler or cloud transfer; 2GiB floor unchanged."}}
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
        env.update(ANY_DATA_DIR=str(data),GOMAXPROCS="2",GOMEMLIMIT="512MiB")
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
        if value.get("mime","")!=attached.get("mime",""):return False
        if value.get("size")!=size or value.get("objectId")!=oid:return False
        if value.get("inline") is not False or value.get("durable") is not False or value.get("cached") is not cached:return False
        for key in ("variant","variantOf"):
            if key in attached and value.get(key)!=attached[key]:return False
        return True
    def expect_info(value,attached,oid,size,cached):
        assert metadata_complete(value,attached,oid,size,cached)
        for key in ("fileId","rootCid","name"):
            assert value[key]==attached[key]
        assert value.get("mime","")==attached.get("mime","")
        assert value["size"]==size and value["objectId"]==oid
        assert value["inline"] is False and value["durable"] is False and value["cached"] is cached
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
        public=pinned(NODECONF,NODECONF_SHA,65536)
        assert b"fileV2" not in public
        phase="retained granted-account admission and isolated network"
        prior=json.loads(pinned(GRANT/"result.json",args.continuation_receipt_sha,4*1024**2))
        assert prior["status"]=="PASS_ORIGINAL_RECIPIENT_EXISTING_GRANT_AND_COLD_READER_AUTHORITY"
        assert prior["allOwnedGroupsPositivelyAbsent"] and all(p["exitCode"]==0 for p in prior["processes"])
        assert prior["accountInitCalls"]==prior["joinCalls"]==prior["inviteCreateCalls"]==prior["grantCalls"]==prior["attachmentCalls"]==0
        assert prior["priorGrantReceiptSHA256"]=="8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d"
        assert prior["activeReaderOnline"]==prior["activeReaderOffline"] and prior["activeReaderOnline"]["permission"]=="reader"
        assert prior["sourceBefore"]==prior["sourceAfter"]==result["sourcesBefore"]
        prior_files=json.loads(pinned(PRIORFILES/"result.json",PRIORFILES_SHA,4*1024**2))
        assert prior_files["status"]=="FAIL" and not prior_files["actualFilesV2Acceptance"]
        assert prior_files["allOwnedGroupsPositivelyAbsent"] and all(p["exitCode"]==0 and p["groupPositivelyAbsent"] and not p["forcedKill"] for p in prior_files["processes"])
        assert prior_files["priorRecipientContinuationSHA256"]==args.continuation_receipt_sha
        assert prior_files["attachmentCalls"]==len(prior_files["attachmentLedger"])==2
        assert all(v["stage"]=="confirmed" and v["status"]==201 for v in prior_files["attachmentLedger"])
        assert [v["metadata"]["fileId"] for v in prior_files["attachmentLedger"]]==["QZmWabwjqP3","Bst4MGoLyBW"]
        custody=json.loads(pinned(PRIORFILES/"private-current-accounts.json",prior_files["finalAccountInventorySHA256"],4*1024**2))
        result["priorFilesReceiptSHA256"]=PRIORFILES_SHA
        result["existingAttachmentLedger"]=prior_files["attachmentLedger"]
        result["confirmedAttachmentsReissued"]=0
        active=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
            try:
                command=(proc/'cmdline').read_bytes()
                if any(str(ACCOUNTS/name).encode() in command for name in ('alice','bob')):active.append(int(proc.name))
            except (FileNotFoundError,PermissionError,ProcessLookupError):pass
        assert not active,"retained account process already active"
        for name in ("alice","bob"):assert account_inventory(ACCOUNTS/name)==custody[name]
        available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        assert available>=2*1024**3,"two native processes require2GiB available-memory reserve"
        result['resourcePolicy']['memAvailableBefore']=available
        build_sha="bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380"
        build=json.loads(pinned(NATIVE/"result.json",build_sha,4*1024**2))
        assert build["status"]=="PASS_BUILD_ONLY" and build["allOwnedGroupsPositivelyAbsent"] and build["isolatedSourceUnchanged"]
        native_binary=NATIVE/"any";native_sha=build["binary"]["sha256"]
        assert sha(native_binary)==native_sha
        assert sha(NATIVE/"source-manifest.json")==build["sourceManifestSHA256"]
        result["nativeBefore"]=native_admission()
        assert prior["nativeBefore"]==prior["nativeAfter"]
        assert result["nativeBefore"]["files"]==prior["nativeBefore"]["sourceFiles"]==1597
        assert all(result["nativeBefore"][k]==prior["nativeBefore"][k] for k in ("binarySHA256","sourceManifestSHA256"))
        result["priorRecipientContinuationSHA256"]=args.continuation_receipt_sha
        result["originalSoleGrantReceiptSHA256"]=prior["priorGrantReceiptSHA256"]
        result["priorCustodySHA256"]=prior_files["finalAccountInventorySHA256"]
        result["nativeBuildReceiptSHA256"]=build_sha
        accepted=json.loads(pinned(ROOT/"production-lan-files2/result.json","c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692",1024**2))
        assert accepted["actualFilesV2Acceptance"] and accepted["allOwnedGroupsPositivelyAbsent"] and accepted["nativeBefore"]==result["nativeBefore"]
        crypto=json.loads(pinned(ROOT/"files-crypto-integrity1/result.json","99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac",1024**2))
        assert crypto["status"]=="PASS_ORIGINAL_NATIVE_CIPHER_CID_INTEGRITY_TESTS_ONLY" and len(crypto["tests"])==9
        result["reusedQualifiedBoundaries"]={"partialCrashResumeReceiptSHA256":"c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692","cryptoIntegrityReceiptSHA256":"99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac","sameNativeSource":True,"crashRerun":False,"cryptoMethodsRerun":0}
        result["offlinePolicy"]=accepted["offlinePolicy"]
        assert result["offlinePolicy"]["helperSHA256"]==OFFLINE_SHA and result["offlinePolicy"]["actual"]["tcpDenied"] and result["offlinePolicy"]["actual"]["udpDenied"]
        (out/"controller.py").write_bytes(Path(__file__).read_bytes())
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
        with socket.socket() as probe:
            probe.settimeout(1);external=probe.connect_ex(('203.0.113.1',443));assert external==errno.ENETUNREACH
        result['networkNamespace']={'own':own_ns,'host':host_ns,'distinct':True,'routes':routes,'nodePortsRefused':refused,'externalConnectErrno':external,'noIPv6DefaultRoute':True,'hostNetworkChanged':False}
        original_config=out/"public-nodeconf.yml";original_config.write_bytes(public)
        lan_cfg=out/"lan-config.yml";config(lan_cfg,original_config)
        result['LANConfiguration']={'nodeConfigSHA256':NODECONF_SHA,'cachedAccountConfigPreserved':True,'sameNetworkIdentity':True,'isolation':'fresh OS network namespace; only internal veth and loopback'}
        phase="LAN-only native restart"
        alice=start("alice-lan",alice_data,lan_cfg);bob=start("bob-lan",bob_data,lan_cfg)
        assert js(alice,"GET","/v1/account")["id"]==aid and js(bob,"GET","/v1/account")["id"]==bid
        member(alice,sid,aid,"owner");member(bob,sid,bid,"reader")
        result["initialLANDiscovery"]=discovery(alice,bob,sid)
        mark("actual native LAN discovery with zero network peers")
        phase="native attachments and asynchronous metadata convergence"
        archive=pinned(ARCHIVE,ARCHIVE_SHA,2*1024**2);assert len(archive)==1634696
        payloads=[("historical-source.pinkha-heart-source",archive,"application/x-pinkha-heart-source"),
                  ("binary-8192.bin",hashlib.shake_256(b"C-distinct-files-small").digest(8192),"application/octet-stream"),
                  ("partial-8388608.bin",hashlib.shake_256(b"C-distinct-files-partial").digest(8*1024**2),"application/octet-stream"),
                  ("original-image.png",png_bytes(128,128,"C-original-png"),"image/png")]
        names={v[0] for v in payloads}|{"thumb.png","acl-revocation-canary.bin"}
        owner_before=js(alice,"GET","/v1/spaces/"+segment(sid)+"/files?"+urllib.parse.urlencode({"objectId":oid}))
        assert isinstance(owner_before["files"],list)
        existing={v["name"]:v for v in prior_files["attachmentLedger"]}
        retained_rows=[v for v in owner_before["files"] if v.get("name") in names]
        assert len(retained_rows)==len(existing)==2
        for value in retained_rows:
            row=existing[value["name"]]
            expect_info(value,row["metadata"],oid,row["plaintextBytes"],True)
        result["existingAttachmentsVerified"]=True
        atomic(out/"owner-files-before.json",owner_before);result["ownerFilesBeforeSHA256"]=sha(out/"owner-files-before.json")
        def attach(name,content,mime,variant_of=None):
            assert name in names and not any(v["name"]==name for v in result["attachmentLedger"])
            query={"name":name}
            if variant_of is not None:query.update(variant="thumb",variantOf=variant_of)
            row={"name":name,"accountId":aid,"spaceId":sid,"objectId":oid,"plaintextBytes":len(content),"plaintextSHA256":digest(content),"contentType":mime,"stage":"dispatching"}
            result["attachmentLedger"].append(row);result["attachmentCalls"]+=1
            atomic(out/"attachment-ledger.json",result["attachmentLedger"]);save()
            code,raw,_=request(alice,"POST","/v1/spaces/"+segment(sid)+"/objects/"+segment(oid)+"/files?"+urllib.parse.urlencode(query),content,{"Content-Type":mime},timeout=60)
            row["status"]=code;row["responseBytes"]=len(raw)
            if code==201:row.update(stage="confirmed",metadata=json.loads(raw))
            else:row.update(stage="rejected",errorBody=raw.decode("utf-8","replace"))
            atomic(out/"attachment-ledger.json",result["attachmentLedger"]);save()
            assert code==201,"actual native attach failed; immutable dispatch ledger retained"
            return row["metadata"]
        def await_metadata(name, attached, content):
            begin=time.monotonic();last_recorded=-10;last_value=None;sampled=set()
            observations=[]
            result["metadataObservations"].append({"name":name,"fileId":attached["fileId"],"samples":observations})
            def diagnostic(at):
                sample={"fileId":attached["fileId"],"secondsWaiting":round(time.monotonic()-begin,3),"peers":{}}
                for label,peer in (("alice",alice),("bob",bob)):
                    items={};sample["peers"][label]=items
                    for key,path in (("sync","/v1/spaces/"+segment(sid)+"/sync-status"),("debug","/v1/spaces/"+segment(sid)+"/debug"),("p2p","/v1/debug/p2p")):
                        try:
                            code,raw,_=request(peer,"GET",path,timeout=3,maximum=256*1024)
                            items[key]={"status":code,"value":json.loads(raw)}
                        except (OSError,ValueError,urllib.error.URLError) as error:items[key]={"diagnosticError":type(error).__name__}
                    try:
                        code,raw,_=request(peer,"GET","/debug/pprof/goroutine?debug=2",timeout=5,maximum=4*1024**2)
                        target=logs/(label+"-"+attached["fileId"]+"-"+str(at)+"-goroutines.txt")
                        target.write_bytes(raw)
                        items["goroutines"]={"status":code,"path":target.name,"bytes":len(raw),"sha256":sha(target)}
                    except (OSError,ValueError,urllib.error.URLError) as error:items["goroutines"]={"diagnosticError":type(error).__name__}
                result["stallDiagnostics"].append(sample);save()
            def row_arrived():
                nonlocal last_value,last_recorded
                code,raw,_=request(bob,"GET",file_path(sid,attached["fileId"]),maximum=65536)
                value=json.loads(raw);elapsed=time.monotonic()-begin
                sample={"status":code,"value":value}
                if sample!=last_value or elapsed-last_recorded>=5:
                    observations.append({"secondsWaiting":round(elapsed,3),**sample});last_value=sample;last_recorded=elapsed;save()
                complete=code==200 and metadata_complete(value,attached,oid,len(content),False)
                if not complete:
                    for at in (15,60):
                        if elapsed>=at and at not in sampled:
                            sampled.add(at);diagnostic(at)
                return value if complete else False
            return until(90,row_arrived,"recipient complete native file metadata")
        records=[]
        for name,content,mime in payloads:
            zero_network(alice,sid);zero_network(bob,sid)
            if name in existing:
                row=existing[name]
                assert row["plaintextBytes"]==len(content) and row["plaintextSHA256"]==digest(content) and row["contentType"]==mime
                attached=row["metadata"]
            else:attached=attach(name,content,mime)
            assert attached["inline"] is False and attached["durable"] is False and attached["cached"] is True
            assert attached["size"]==len(content) and attached["objectId"]==oid and attached["name"]==name and (attached.get("mime") or "application/octet-stream")==mime and attached["rootCid"]
            record={"fileId":attached["fileId"],"attached":attached,"bytes":content}
            arrived=await_metadata(name,attached,content)
            expect_info(arrived,attached,oid,len(content),False)
            record["initial"]=arrived;records.append(record)
            result["files"].append({"fileId":record["fileId"],"name":name,"plaintextBytes":len(content),"plaintextSHA256":digest(content),
                                   "rootCid":attached["rootCid"],"objectId":oid,"mime":mime,"storedMIME":attached.get("mime",""),"inline":False,"durable":False,"recipientInitiallyCached":False})
            save()
        image=records[3];thumb=png_bytes(64,64,"C-thumbnail-png")
        attached=attach("thumb.png",thumb,"image/png",image["fileId"])
        assert attached["name"]=="thumb.png" and attached["mime"]=="image/png" and attached["size"]==len(thumb) and attached["cached"] is True
        assert attached["variant"]=="thumb" and attached["variantOf"]==image["fileId"]
        assert attached["objectId"]==oid and attached["inline"] is False and attached["durable"] is False
        variant={"fileId":attached["fileId"],"attached":attached,"bytes":thumb}
        expect_info(await_metadata("thumb.png",attached,thumb),attached,oid,len(thumb),False)
        records.append(variant)
        result["files"].append({"fileId":variant["fileId"],"name":"thumb.png","plaintextBytes":len(thumb),"plaintextSHA256":digest(thumb),
            "rootCid":attached["rootCid"],"objectId":oid,"mime":"image/png","inline":False,"durable":False,
            "recipientInitiallyCached":False,"variant":"thumb","variantOf":image["fileId"]})
        mark("five native attachments and exact variant metadata",sourceArchiveSHA256=ARCHIVE_SHA)
        canary_bytes=hashlib.shake_256(b"C-original-retained-revocation-canary-v1").digest(8192)
        canary=attach("acl-revocation-canary.bin",canary_bytes,"application/octet-stream")
        assert canary["size"]==8192 and canary["objectId"]==oid and canary["name"]=="acl-revocation-canary.bin" and (canary.get("mime") or "application/octet-stream")=="application/octet-stream"
        assert canary["inline"] is False and canary["durable"] is False and canary["cached"] is True
        canary_info=await_metadata("acl-revocation-canary.bin",canary,canary_bytes)
        result["revocationCanary"]={"ownerMetadata":canary,"recipientMetadata":canary_info,"plaintextSHA256":digest(canary_bytes),"plaintextBytes":len(canary_bytes),"recipientContentReadCalls":0}
        phase="original retained full native LAN file transfer"
        for i,record in enumerate(records):
            zero_network(alice,sid);zero_network(bob,sid)
            code,raw,headers=request(bob,"GET",file_path(sid,record["fileId"])+"/content",timeout=60)
            assert code==200 and raw==record["bytes"]
            assert headers.get("Content-Type")== (record["attached"].get("mime") or "application/octet-stream")
            expect_info(info(bob,sid,record["fileId"]),record["attached"],oid,len(raw),True)
            result["files"][i].update(recipientComplete=True,destinationSHA256=digest(raw))
        code,raw,headers=request(bob,"GET",file_path(sid,image["fileId"])+"/content?variant=thumb",timeout=40)
        assert code==200 and raw==thumb and headers.get("Content-Type")=="image/png"
        result["variantResolution"]={"nativeVariantOf":image["fileId"],"variantFileId":variant["fileId"],"byteEquality":True,"sha256":digest(raw)}
        result["finalLANSync"]={"alice":zero_network(alice,sid),"bob":zero_network(bob,sid)}
        expect_info(info(bob,sid,canary["fileId"]),canary,oid,len(canary_bytes),False)
        mark("all five original-account payloads equal over native LAN; permission canary remains uncached",files=5)
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
        expect_info(info(bob,sid,canary["fileId"]),canary,oid,len(canary_bytes),False)
        result["revocationCanary"]["recipientStillUncachedAfterColdReopen"]=True
        code,raw,_=request(bob,"POST","/v1/spaces/"+segment(sid)+"/objects/"+segment(oid)+"/files?name=denied-offline-reader.bin",b"reader denial fixture",{"Content-Type":"application/octet-stream"})
        denied=json.loads(raw);assert code==403 and denied["error"]["code"] in ("space.read_only","acl.forbidden")
        result['offlineReaderWriteDenial']={'status':code,'errorCode':denied['error']['code']}
        assert zero_network(bob,sid,offline=True)["networkPeers"]==0
        complete(bob)
        mark("all five files and native variant equal in fresh OS-offline process",files=5)
        result["sourcesAfter"]=source_admission()
        assert pinned(ARCHIVE,ARCHIVE_SHA,2*1024**2)==archive
        assert pinned(NODECONF,NODECONF_SHA)==public
        assert original_config.read_bytes()==public
        result["nativeAfter"]=native_admission();assert result["nativeAfter"]==result["nativeBefore"]
        for path,value in config_hashes.items():pinned(Path(path),value,65536)
        assert len(result["files"])==5 and len(result["attachmentLedger"])==result["attachmentCalls"]==4
        assert len(result["existingAttachmentLedger"])==2 and result["confirmedAttachmentsReissued"]==0
        assert all(row["stage"]=="confirmed" and row["status"]==201 for row in result["attachmentLedger"])
        result["attachmentLedgerSHA256"]=sha(out/"attachment-ledger.json")
        result["originalPrivateInviteFixed"]=True
        result["actualFilesV2Acceptance"]=True
        result["status"]="PASS_ORIGINAL_RETAINED_ACCOUNTS_FIVE_FILES_AND_COLD_BYTES"
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
        if result["status"].startswith("PASS") and not (len(processes)==3 and result["allOwnedGroupsPositivelyAbsent"] and all(c["row"].get("exitCode")==0 and not c["row"].get("forcedKill",False) for c in processes)):
            result["status"]="FAIL";result["actualFilesV2Acceptance"]=False
        try:
            pinned(GRANT/"result.json",args.continuation_receipt_sha,4*1024**2)
            pinned(PRIORFILES/"result.json",PRIORFILES_SHA,4*1024**2)
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
        if result["status"]!="PASS_ORIGINAL_RETAINED_ACCOUNTS_FIVE_FILES_AND_COLD_BYTES":
            result["actualFilesV2Acceptance"]=False
        save()
    print(json.dumps({"status":result["status"],"result":str(out/"result.json"),"sha256":sha(out/"result.json"),
                      "actualFilesV2Acceptance":result["actualFilesV2Acceptance"],"seconds":result["seconds"]}))
    return 0 if result["status"]=="PASS_ORIGINAL_RETAINED_ACCOUNTS_FIVE_FILES_AND_COLD_BYTES" else 1

if __name__=="__main__":
    raise SystemExit(main())
