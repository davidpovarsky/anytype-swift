#!/usr/bin/env python3
"""Distinct-account native FilesV2 LAN bytes, variants, partial crash recovery and cold OS denial.

No Go or Apple build. The initial real ACL grant uses the separately qualified
private network; subsequent file phases retain its identity but make every node
endpoint unreachable and require real native LAN peers with zero network peers.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

BUILD_ROOT = Path("/var/lib/pinkha-root-t2-linux-20261126/build1/current")
BINARY = BUILD_ROOT / "any"
BINARY_SHA = "1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"
BUILD_SHA = "6d0f00da205846575bfd49e3fba8121aa1570a940ea3e13cc571aa4b4734e2f0"
MANIFEST_SHA = "12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"
INVENTORY_SHA = "7101539ffeb0d039afd5ba6eca4827f6389b2ce0a1311ee493331e2f6db31138"
COMMITS = {"any":"8fbd1e819fb132ac0e0a848d2ddf5c5714189b81",
           "sdk":"c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"}
REPO = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
OFFLINE = REPO / "Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py"
OFFLINE_SHA = "6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1"
NODECONF = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network/mac-public-nodeconf.yml")
NODECONF_SHA = "fc43639b27c8c7ab50897542a99ecddd3266e85eedf575625d20391684e476e0"
ARCHIVE = Path("/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1/private-work/original-source.pinkha-heart-source")
ARCHIVE_SHA = "5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463"
FLOOR = 2 * 1024**3
ESTIMATE = 512 * 1024**2
SERVICE = "_pinkha-fv2._tcp"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()

def identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns)

def pinned(path, expected, maximum=100*1024**2):
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum
    raw = path.read_bytes()
    assert identity(path.lstat()) == identity(before) and len(raw) == before.st_size
    assert digest(raw) == expected
    return raw

def atomic(path, value):
    pending = path.with_name(path.name + ".pending")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)

def source_admission():
    source = BUILD_ROOT / "source"
    assert source.resolve() == source and not source.is_symlink()
    root_id = identity(source.stat())
    manifest_bytes = pinned(BUILD_ROOT/"source-manifest.json", MANIFEST_SHA, 4*1024**2)
    manifest = json.loads(manifest_bytes)
    before_bytes = pinned(BUILD_ROOT/"source-before.json", INVENTORY_SHA, 4*1024**2)
    after_bytes = pinned(BUILD_ROOT/"source-after.json", INVENTORY_SHA, 4*1024**2)
    assert before_bytes == after_bytes
    original = json.loads(before_bytes)
    build_bytes = pinned(BUILD_ROOT/"BUILD.json", BUILD_SHA, 65536)
    build = json.loads(build_bytes)
    assert build["status"] == "PASS_BUILD_ONLY" and build["exitCode"] == 0
    assert build["ownedGroupAbsent"] is True and build["sourceUnchanged"] is True
    assert build["sourceFiles"] == 1594 and build["sourceManifestSHA256"] == MANIFEST_SHA
    assert build["commits"] == COMMITS and build["cwd"] == str(source)
    assert build["command"] == ["/usr/local/bin/go","build","-p","2","-o",str(BINARY),"./cmd/any"]
    assert build["binary"] == {"path":str(BINARY),"bytes":78072016,"sha256":BINARY_SHA}
    assert manifest["schema"] == "pinkha-t2-permission-native-source-v1"
    assert manifest["commits"] == COMMITS and len(manifest["files"]) == 1594
    assert set(original) == set(manifest["files"])
    found = set()
    for path in source.rglob("*"):
        assert not path.is_symlink()
        if path.is_file():
            found.add(path.relative_to(source).as_posix())
    assert found == set(original)
    for name,row in manifest["files"].items():
        assert not Path(name).is_absolute() and all(v not in ("", ".", "..") for v in name.split("/"))
        path = source/name
        assert path.resolve() == path and path.is_file()
        current = path.lstat()
        assert stat.S_ISREG(current.st_mode) and current.st_nlink == 1
        assert row["kind"] == "file" and current.st_size == row["bytes"]
        assert stat.S_IMODE(current.st_mode) == row["mode"]
        assert original[name] == {k:row[k] for k in ("bytes","kind","mode","sha256")}
        assert sha(path) == row["sha256"] and identity(path.lstat()) == identity(current)
    assert identity(source.stat()) == root_id
    assert pinned(BUILD_ROOT/"source-manifest.json", MANIFEST_SHA) == manifest_bytes
    assert pinned(BUILD_ROOT/"source-before.json", INVENTORY_SHA) == before_bytes
    assert pinned(BUILD_ROOT/"source-after.json", INVENTORY_SHA) == after_bytes
    assert pinned(BUILD_ROOT/"BUILD.json", BUILD_SHA) == build_bytes
    assert len(pinned(BINARY, BINARY_SHA)) == 78072016
    pinned(OFFLINE, OFFLINE_SHA, 65536)
    pinned(NODECONF, NODECONF_SHA, 65536)
    return {"commits":COMMITS,"sourceFiles":1594,"sourceManifestSHA256":MANIFEST_SHA,
            "buildSHA256":BUILD_SHA,"binarySHA256":BINARY_SHA,"sourceUnchanged":True}

def png_bytes(width, height, label):
    pixels = hashlib.shake_256(label.encode()).digest(width*height*3)
    scan = b"".join(b"\x00"+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(scan))+chunk(b"IEND",b"")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    out = args.output
    assert out.is_absolute() and out.parent.resolve() == out.parent
    assert str(out).startswith("/var/lib/pinkha-c-filesv2-20261126/")
    os.umask(0o077)
    out.mkdir(mode=0o700,exist_ok=False)
    logs=out/"private-logs"; logs.mkdir(mode=0o700)
    started=time.monotonic()
    minimum=shutil.disk_usage(out).free
    processes=[]; streams=[]; absent_ids=set(); phase="preflight"
    result={"protocol":"pinkha-distinct-account-filesv2-linux-lan-v1","status":"RUNNING",
            "appBuilds":0,"goBuilds":0,"wholeSpaceMigrationAccepted":False,"cloudCustodyAccepted":False,
            "actualFilesV2Acceptance":False,"processes":[],"phases":[],"files":[],"errors":[],
            "resourcePolicy":{"estimatedNewBytes":ESTIMATE,"emergencyFreeBytes":FLOOR,
                "reason":"Two fresh native account stores, less than 11 MiB plaintext, sparse encrypted caches and bounded logs; no compiler or download."}}
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
        env.update(ANY_DATA_DIR=str(data),GOMAXPROCS="2",GOMEMLIMIT="2GiB")
        return env
    def start(name,data,cfg,initialize=False,offline=False):
        guard();pinned(cfg,config_hashes[str(cfg)],65536)
        pinned(NODECONF,NODECONF_SHA,65536)
        assert sha(BINARY)==BINARY_SHA and sha(OFFLINE)==OFFLINE_SHA
        if initialize:
            data.mkdir(mode=0o700,exist_ok=False)
            run_short(name+"-init",[str(BINARY),"init","--config",str(cfg),"--data-dir",str(data)],env_for(data))
        assert data.is_dir() and data.resolve()==data and not data.is_symlink()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0));port=listener.getsockname()[1]
        command=[str(BINARY),"run","--config",str(cfg),"--data-dir",str(data),"--addr","127.0.0.1:"+str(port)]
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
            assert executable==BINARY and sha(executable)==BINARY_SHA
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
    def expect_info(value,attached,oid,size,cached):
        for key in ("fileId","rootCid","name","mime"):
            assert value[key]==attached[key]
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
    try:
        assert minimum>=FLOOR+ESTIMATE,"measured native phase does not fit"
        result["sourcesBefore"]=source_admission()
        result["controllerSHA256"]=sha(Path(__file__))
        public=pinned(NODECONF,NODECONF_SHA,65536)
        assert b"fileV2" not in public
        endpoints=re.findall(rb"127[.]0[.]0[.]1:2400[1-6]",public)
        assert len(endpoints)==6 and set(endpoints)=={("127.0.0.1:"+str(p)).encode() for p in range(24001,24007)}
        health=[]
        for port in range(24001,24007):
            with socket.create_connection(("127.0.0.1",port),timeout=2):health.append(port)
        result["initialNetworkHealth"]={"actualConnectedPorts":health,"publicConfigSHA256":NODECONF_SHA}
        original_config=out/"public-nodeconf.yml";original_config.write_bytes(public)
        dead=re.sub(rb"127[.]0[.]0[.]1:2400[1-6]",b"127.0.0.1:1",public)
        itr=iter(endpoints)
        assert re.sub(rb"127[.]0[.]0[.]1:1(?![0-9])",lambda _:next(itr),dead)==public
        with socket.socket() as probe:
            probe.settimeout(1);assert probe.connect_ex(("127.0.0.1",1)) in (errno.ECONNREFUSED,errno.EHOSTUNREACH,errno.ETIMEDOUT)
        lan_conf=out/"lan-only-nodeconf.yml";lan_conf.write_bytes(dead)
        result["LANConfiguration"]={"originalSHA256":NODECONF_SHA,"derivedSHA256":digest(dead),
          "onlyChangedFields":[x.decode() for x in endpoints],"sameNetworkIdentity":True,
          "replacementEndpoint":"127.0.0.1:1","originalBytesPreserved":True}
        setup_cfg=out/"setup-config.yml";lan_cfg=out/"lan-config.yml"
        config(setup_cfg,original_config);config(lan_cfg,lan_conf)
        phase="fresh distinct native accounts"
        alice_data=out/"alice";bob_data=out/"bob"
        alice=start("alice-setup",alice_data,setup_cfg,initialize=True)
        bob=start("bob-setup",bob_data,setup_cfg,initialize=True)
        aid=js(alice,"GET","/v1/account")["id"];bid=js(bob,"GET","/v1/account")["id"]
        assert aid and bid and aid!=bid and alice["process"].pid!=bob["process"].pid
        result["accounts"]={"alice":aid,"bob":bid}
        phase="actual native invite and Reader grant"
        sid=js(alice,"POST","/v1/spaces",{"name":"C FilesV2 distinct native peer comparison"},201)["id"]
        oid=js(alice,"POST","/v1/spaces/"+segment(sid)+"/objects",{"type":"page"},201)["objectId"]
        result["spaceId"]=sid;result["objectId"]=oid
        token=js(alice,"POST","/v1/spaces/"+segment(sid)+"/invites",expected=201)["inviteToken"]
        joined=js(bob,"POST","/v1/spaces/join",{"inviteToken":token},202);del token
        assert joined["id"]==sid and joined["status"]=="joining"
        def pending():
            rows=js(alice,"GET","/v1/spaces/"+segment(sid)+"/members/requests")["requests"]
            matches=[x for x in rows if x.get("identity")==bid]
            assert len(matches)<=1
            return matches[0] if matches else False
        join=until(90,pending,"actual recipient join request")
        js(alice,"POST","/v1/spaces/"+segment(sid)+"/acl/accept",{"requestRecordId":join["recordId"],"permission":"reader"},204)
        def accepted():
            code,raw,_=request(bob,"GET","/v1/spaces/"+segment(sid)+"/members/me")
            if code!=200:return False
            value=json.loads(raw)
            return value if value.get("status")=="active" else False
        until(90,accepted,"actual Reader grant materialization")
        member(alice,sid,aid,"owner");member(bob,sid,bid,"reader")
        mark("distinct accounts and actual native Reader grant",nativeAccountsDistinct=True)
        complete(alice);complete(bob)
        phase="LAN-only native restart"
        alice=start("alice-lan",alice_data,lan_cfg);bob=start("bob-lan",bob_data,lan_cfg)
        assert js(alice,"GET","/v1/account")["id"]==aid and js(bob,"GET","/v1/account")["id"]==bid
        member(alice,sid,aid,"owner");member(bob,sid,bid,"reader")
        result["initialLANDiscovery"]=discovery(alice,bob,sid)
        mark("actual native LAN discovery with zero network peers")
        phase="native attachments and asynchronous metadata convergence"
        archive=pinned(ARCHIVE,ARCHIVE_SHA,2*1024**2);assert len(archive)==1634696
        payloads=[("historical-source.pinkha-heart-source",archive,"application/octet-stream"),
                  ("binary-8192.bin",hashlib.shake_256(b"C-distinct-files-small").digest(8192),"application/octet-stream"),
                  ("partial-8388608.bin",hashlib.shake_256(b"C-distinct-files-partial").digest(8*1024**2),"application/octet-stream"),
                  ("original-image.png",png_bytes(128,128,"C-original-png"),"image/png")]
        records=[]
        for name,content,mime in payloads:
            zero_network(alice,sid);zero_network(bob,sid)
            code,raw,_=request(alice,"POST","/v1/spaces/"+segment(sid)+"/objects/"+segment(oid)+"/files?"+urllib.parse.urlencode({"name":name}),content,{"Content-Type":mime},timeout=60)
            assert code==201,"actual native attach failed"
            attached=json.loads(raw)
            assert attached["inline"] is False and attached["durable"] is False and attached["cached"] is True
            assert attached["size"]==len(content) and attached["objectId"]==oid and attached["name"]==name and attached["mime"]==mime and attached["rootCid"]
            record={"fileId":attached["fileId"],"attached":attached,"bytes":content}
            def row_arrived():
                code,raw,_=request(bob,"GET",file_path(sid,record["fileId"]))
                return json.loads(raw) if code==200 else False
            arrived=until(90,row_arrived,"recipient native file metadata")
            expect_info(arrived,attached,oid,len(content),False)
            record["initial"]=arrived;records.append(record)
            result["files"].append({"fileId":record["fileId"],"name":name,"plaintextBytes":len(content),"plaintextSHA256":digest(content),
                                   "rootCid":attached["rootCid"],"objectId":oid,"mime":mime,"inline":False,"durable":False,"recipientInitiallyCached":False})
            save()
        image=records[3];thumb=png_bytes(64,64,"C-thumbnail-png")
        code,raw,_=request(alice,"POST","/v1/spaces/"+segment(sid)+"/objects/"+segment(oid)+"/files?"+urllib.parse.urlencode({"name":"thumb.png","variant":"thumb","variantOf":image["fileId"]}),thumb,{"Content-Type":"image/png"},timeout=60)
        assert code==201
        attached=json.loads(raw)
        assert attached["variant"]=="thumb" and attached["variantOf"]==image["fileId"]
        assert attached["objectId"]==oid and attached["inline"] is False and attached["durable"] is False
        variant={"fileId":attached["fileId"],"attached":attached,"bytes":thumb}
        def variant_arrived():
            code,raw,_=request(bob,"GET",file_path(sid,variant["fileId"]))
            return json.loads(raw) if code==200 else False
        expect_info(until(90,variant_arrived,"recipient variant metadata"),attached,oid,len(thumb),False)
        records.append(variant)
        result["files"].append({"fileId":variant["fileId"],"name":"thumb.png","plaintextBytes":len(thumb),"plaintextSHA256":digest(thumb),
            "rootCid":attached["rootCid"],"objectId":oid,"mime":"image/png","inline":False,"durable":False,
            "recipientInitiallyCached":False,"variant":"thumb","variantOf":image["fileId"]})
        mark("five native attachments and exact variant metadata",sourceArchiveSHA256=ARCHIVE_SHA)
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
            assert headers.get("Content-Type")==record["attached"]["mime"]
            expect_info(info(bob,sid,record["fileId"]),record["attached"],oid,len(raw),True)
            selected=range_bytes(bob,sid,record,min(200000,len(raw)//3),min(32768,len(raw)-min(200000,len(raw)//3)))
            result["files"][i].update(recipientComplete=True,destinationSHA256=digest(raw),range=selected)
        code,raw,headers=request(bob,"GET",file_path(sid,image["fileId"])+"/content?variant=thumb",timeout=40)
        assert code==200 and raw==thumb and headers.get("Content-Type")=="image/png"
        result["variantResolution"]={"nativeVariantOf":image["fileId"],"variantFileId":variant["fileId"],"byteEquality":True,"sha256":digest(raw)}
        result["finalLANSync"]={"alice":zero_network(alice,sid),"bob":zero_network(bob,sid)}
        mark("full plaintext and ranges equal after completing existing partial cache",files=5)
        complete(alice);complete(bob)
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
        assert zero_network(bob,sid,offline=True)["networkPeers"]==0
        complete(bob)
        mark("all five files and native variant equal in fresh OS-offline process",files=5)
        result["sourcesAfter"]=source_admission()
        assert pinned(ARCHIVE,ARCHIVE_SHA,2*1024**2)==archive
        assert pinned(NODECONF,NODECONF_SHA)==public
        assert original_config.read_bytes()==public and lan_conf.read_bytes()==dead
        for path,value in config_hashes.items():pinned(Path(path),value,65536)
        result["actualFilesV2Acceptance"]=True
        result["status"]="PASS_DISTINCT_ACCOUNT_LAN_PARTIAL_CRASH_COLD_FILE_BYTES"
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
        if result["status"]!="PASS_DISTINCT_ACCOUNT_LAN_PARTIAL_CRASH_COLD_FILE_BYTES":
            result["actualFilesV2Acceptance"]=False
        save()
    print(json.dumps({"status":result["status"],"result":str(out/"result.json"),"sha256":sha(out/"result.json"),
                      "actualFilesV2Acceptance":result["actualFilesV2Acceptance"],"seconds":result["seconds"]}))
    return 0 if result["status"]=="PASS_DISTINCT_ACCOUNT_LAN_PARTIAL_CRASH_COLD_FILE_BYTES" else 1

if __name__=="__main__":
    raise SystemExit(main())
