#!/usr/bin/env python3
"""Observe the retained production account quota without retrying or recreating files."""
import hashlib,importlib.util,json,os,pathlib,shutil,signal,socket,subprocess,sys,time,urllib.error,urllib.parse,urllib.request,traceback
ROOT=pathlib.Path("/var/lib/pinkha-w1-cloud-filesv2-20261127")
OUT=ROOT/"account-limits-read1"
DATA=ROOT/"attempt2/alice"
CONFIG=ROOT/"attempt2/config.yml"
HELPER=pathlib.Path("/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/run_linux_filesv2_comparison.py")
HELPER_SHA="bf7f478e939dedeb414a49cbd3ca4c6263350bea3985511707899e4e64f3b189"
PRIOR=ROOT/"attempt5/result.json"
PRIOR_SHA="84810888ba0be79546278f90286ff4da9e0a6052daf83922e787132ad628b59c"
ACCOUNT="AAgW9UF9iqUH1KrjQcAz5K2FDCc9kQgniwmnK2rei1M5ah2H"
SPACE="bafyreiet62u77nehvmtgn45ltxrk6itepoighks3u4y2f3pjjotaczcsfi.361psf76ieku2"
OBJECT="bafyreid5n5gg366h3lsqdolu5wi6hffwtqfyhzb53ylneh626bnapnzj6q"
FILES={"BEaHYwGfZiM":8192,"YhnuHkqoHza":49363,"AXSnqoZ52w3":8388608,"ahKeFKn7uta":12420}
FLOOR=2*1024**3
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1024**2),b""):h.update(b)
 return h.hexdigest()
assert sha(HELPER)==HELPER_SHA
sp=importlib.util.spec_from_file_location("retained_cloud_helper",HELPER);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
os.umask(0o077);OUT.mkdir(parents=True,exist_ok=False,mode=0o700)
start=time.monotonic();minimum=shutil.disk_usage("/").free;p=None;stream=None;phase="preflight"
r={"protocol":"pinkha-retained-production-account-limits-observation-v1","status":"RUNNING","startedUnix":time.time(),
 "controllerSHA256":sha(__file__),"builds":0,"accountCreates":0,"inviteCalls":0,"fileCreates":0,"fileRetryCalls":0,"offloadCalls":0,
 "cloudQuotaRecoveryAccepted":False,"originalFourFileCloudCustodyAccepted":False,"requests":[],"errors":[]}
def save():h.atomic(OUT/"result.json",r)
def guard():
 global minimum
 minimum=min(minimum,shutil.disk_usage("/").free)
 assert minimum>=FLOOR,"unchanged root native storage floor"
 assert time.monotonic()-start<120,"bounded quota observation deadline"
def interrupted(*_):raise RuntimeError("owned quota observation interrupted")
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
if hasattr(signal,"pthread_sigmask"):signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
def absent():
 if p is None:return True
 try:os.killpg(p.pid,0)
 except ProcessLookupError:return True
 return False
def close():
 if p is None:return
 live=p.poll() is None;group=not absent()
 if not live and group:r["unexpectedOwnedGroupSurvivor"]=True
 if live or group:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  end=time.monotonic()+15
  while time.monotonic()<end:
   p.poll()
   if absent():break
   time.sleep(.1)
  if not absent():
   os.killpg(p.pid,signal.SIGKILL);r["unexpectedForcedKill"]=True
   end=time.monotonic()+5
   while time.monotonic()<end:
    p.poll()
    if absent():break
    time.sleep(.1)
  if p.poll() is None:p.wait(timeout=1)
 if stream and not stream.closed:stream.close()
 r["process"].update(exitCode=p.returncode,groupAbsent=absent(),logSHA256=sha(OUT/"native.log"))
 assert p.returncode==0 and absent() and not r.get("unexpectedForcedKill") and not r.get("unexpectedOwnedGroupSurvivor"),"native cleanup failed"
def get(path,timeout=10):
 guard();assert p and p.poll() is None,"owned quota native exited"
 req=urllib.request.Request(base+path,method="GET")
 try:
  with urllib.request.urlopen(req,timeout=timeout) as response:status=response.status;raw=response.read(262145)
 except urllib.error.HTTPError as e:status=e.code;raw=e.read(262145)
 row={"method":"GET","path":path,"status":status,"observedBytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
 r["requests"].append(row);save()
 f=OUT/("response-"+str(len(r["requests"]))+".json");f.write_bytes(raw);row["rawPath"]=str(f)
 assert len(raw)<=262144 and status==200,"bounded account read failed"
 value=json.loads(raw);save();return value
def live_data_users():
 found=[]
 for q in pathlib.Path("/proc").iterdir():
  if not q.name.isdigit() or int(q.name)==os.getpid():continue
  try:
   args=(q/"cmdline").read_bytes().split(b"\0")
   if os.fsencode(str(DATA)) in args:found.append(int(q.name))
   for fd in (q/"fd").iterdir():
    try:
     target=os.readlink(fd)
     if target==str(DATA) or target.startswith(str(DATA)+"/"):found.append(int(q.name));break
    except OSError:pass
  except OSError:pass
 return sorted(set(found))
def cars():
 result=[]
 for x in sorted(DATA.rglob("*.car")):
  assert not x.is_symlink() and x.resolve()==x
  st=x.stat();result.append({"path":str(x.relative_to(DATA)),"bytes":st.st_size,"allocated":st.st_blocks*512,"sha256":sha(x)})
 assert len(result)>=4
 return result
try:
 assert minimum>=FLOOR+128*1024**2,"quota read admission floor"
 assert sha(PRIOR)==PRIOR_SHA
 prior=json.loads(PRIOR.read_text());assert prior["status"]=="FAIL" and prior["quotaLocalPreservationAccepted"] is True
 assert not live_data_users(),"retained account already open"
 r["sourceBefore"]=h.source_admission();assert r["sourceBefore"]==prior["sourceAfter"]
 assert sha(CONFIG)==prior["configSHA256"];r["configSHA256"]=sha(CONFIG)
 r["priorQuotaFailure"]={"path":str(PRIOR),"sha256":PRIOR_SHA}
 r["carsBefore"]=cars()
 with socket.socket() as sock:sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
 cmd=[str(h.BINARY),"run","--config",str(CONFIG),"--data-dir",str(DATA),"--addr","127.0.0.1:"+str(port)]
 env={k:v for k,v in os.environ.items() if not k.startswith("ANY_")};env.update(ANY_DATA_DIR=str(DATA),GOMAXPROCS="2",GOMEMLIMIT="1GiB")
 stream=(OUT/"native.log").open("xb");p=subprocess.Popen(cmd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 base="http://127.0.0.1:"+str(port)
 r["process"]={"pid":p.pid,"command":cmd,"network":"production nodes; original p2p-disabled config"};save()
 phase="native health"
 end=time.monotonic()+45
 while True:
  try:
   if get("/v1/health",timeout=1) is not None:break
  except (OSError,urllib.error.URLError):pass
  guard();assert time.monotonic()<end,"native health deadline";time.sleep(.25)
 phase="bound current account and Space"
 assert get("/v1/account")["id"]==ACCOUNT
 member=get("/v1/spaces/"+SPACE+"/members/me")
 assert member["identity"]==ACCOUNT and member["status"]=="active" and member["permission"]=="owner"
 sync=get("/v1/spaces/"+SPACE+"/sync-status")
 assert sync["localPeers"]==0 and sync["globalPeers"]==0
 r["syncBefore"]=sync
 phase="single account limits observation"
 r["limitsObservedAtUnix"]=time.time()
 limits=get("/v1/account/limits",timeout=12);r["limits"]=limits
 storage=limits.get("storage")
 if storage is not None:
  assert isinstance(storage,dict)
  assert all(type(storage[k]) is int and storage[k]>=0 for k in ("limitBytes","usageBytes"))
  assert "fetchedAt" in storage
  r["reportedRemainingBytes"]=max(0,storage["limitBytes"]-storage["usageBytes"])
  r["numericStorageAnswerPresent"]=True
 else:r["numericStorageAnswerPresent"]=False
 phase="observe unchanged original file identities and terminal status"
 listing=get("/v1/spaces/"+SPACE+"/files?"+urllib.parse.urlencode({"objectId":OBJECT}))
 rows=listing["files"];assert len(rows)==4 and {x["fileId"] for x in rows}==set(FILES)
 for row in rows:
  assert row["objectId"]==OBJECT and row["size"]==FILES[row["fileId"]] and row["cached"] is True
 r["files"]=rows
 r["limitedFileStatuses"]=[get("/v1/spaces/"+SPACE+"/files/"+fid+"/status") for fid in ("YhnuHkqoHza","AXSnqoZ52w3")]
 assert [x["fileId"] for x in r["limitedFileStatuses"]]==["YhnuHkqoHza","AXSnqoZ52w3"]
 r["syncAfter"]=get("/v1/spaces/"+SPACE+"/sync-status")
 assert r["syncAfter"]["localPeers"]==0 and r["syncAfter"]["globalPeers"]==0
 close();r["carsAfter"]=cars();assert r["carsBefore"]==r["carsAfter"],"original encrypted file bytes changed"
 r["status"]="OBSERVED_CLOUD_ACCOUNT_LIMITS_NO_EXPLICIT_RETRY"
except BaseException as e:
 r["status"]="FAILED_QUOTA_OBSERVATION";r["errors"].append({"phase":phase,"type":type(e).__name__,"message":str(e)})
 (OUT/"traceback.txt").write_text(traceback.format_exc())
finally:
 try:
  if p is not None and "exitCode" not in r.get("process",{}):close()
 except BaseException as e:r["status"]="FAILED_QUOTA_OBSERVATION";r["errors"].append({"cleanup":str(e)})
 try:
  r["sourceAfter"]=h.source_admission();r["sourceUnchanged"]=r["sourceAfter"]==r.get("sourceBefore")
  r["configUnchanged"]=sha(CONFIG)==r.get("configSHA256")
  if not r["sourceUnchanged"] or not r["configUnchanged"]:r["status"]="FAILED_QUOTA_OBSERVATION"
 except BaseException as e:r["status"]="FAILED_QUOTA_OBSERVATION";r["errors"].append({"finalAdmission":str(e)})
 r["elapsedSeconds"]=round(time.monotonic()-start,3);r["minimumFreeBytes"]=minimum;r["allOwnedGroupsAbsent"]=absent();save()
 print(json.dumps({"status":r["status"],"result":str(OUT/"result.json"),"sha256":sha(OUT/"result.json"),
  "limits":r.get("limits"),"reportedRemainingBytes":r.get("reportedRemainingBytes"),"errors":r["errors"],
  "fileRetryCalls":0,"cloudQuotaRecoveryAccepted":False,"elapsedSeconds":r["elapsedSeconds"]}))
sys.exit(0 if r["status"]=="OBSERVED_CLOUD_ACCOUNT_LIMITS_NO_EXPLICIT_RETRY" else 1)
