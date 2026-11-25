import pathlib,json,os,subprocess,time,hashlib,shutil,signal,re
w=pathlib.Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
base=pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/compiled-resolver")
root=w/"docs/validation/20261125-heart-source-ui/closed-native-reasons"
prior=root/"attempt2"
out=root/"attempt3";out.mkdir(exist_ok=False)
run=pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/closed-native-reasons/attempt3");run.mkdir(parents=True,exist_ok=False)
tmp=run/"tmp";tmp.mkdir()
alias=pathlib.Path("/tmp/pinkha-c-swift-cache-20261125")
stale=pathlib.Path("/tmp/pinkha-c-swift-cache-stale-20261125T1839")
assert alias.is_dir() and not alias.is_symlink() and alias.stat().st_uid==os.getuid() and not stale.exists()
alias.rename(stale);alias.symlink_to(base/"swift-cache",target_is_directory=True)
assert alias.resolve()==base/"swift-cache"
(run/"cache-alias-restoration.json").write_text(json.dumps({"restoredAlias":str(alias),"target":str(base/"swift-cache"),"preservedRecreatedCache":str(stale),"deletedFiles":0,"preflightUsers":0,"reason":"actual retained PCM paths bind this original cache alias"},indent=2)+"\n")
assert (base/"swift-cache").stat().st_uid==os.getuid(),{"cacheOwner":(base/"swift-cache").stat().st_uid,"executor":os.getuid()}
paths=["Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyHeartNativeSourceCaptureDiagnostics.swift","Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeSourceCaptureDiagnosticsTests.swift"]
before={p:hashlib.sha256((w/p).read_bytes()).hexdigest() for p in paths}
argv=["/usr/local/bin/swift","test","--disable-swift-testing","--cache-path",str(base/"swift-common-cache"),"--manifest-cache","local","-Xswiftc","-module-cache-path","-Xswiftc",str(base/"swift-module-cache"),"--package-path",str(w/"Modules/PinkhaAnyHost"),"--scratch-path","/tmp/pinkha-c-swift-cache-20261125","--disable-sandbox","--disable-automatic-resolution","--jobs","2","--filter","NativeSourceCaptureDiagnosticsTests"]
free=shutil.disk_usage(base).free
assert free>1536*1024**2,("measured512MiBPhasePlus1GiBEmergency",free)
env=os.environ.copy();env["TMPDIR"]=str(tmp);env["CLANG_MODULE_CACHE_PATH"]=str(base/"swift-module-cache")
result={"protocol":"native-closed-reason-qualification-v1","argv":argv,"sourceHashes":before,"startedAt":time.time(),"freeBytesBefore":free,"sourceAcceptance":False,"nativeCalls":0,"appBuilds":0,"uid":os.getuid(),"priorInfrastructureFailurePreserved":True}
log=run/"original-swift-test.log"
with log.open("wb") as stream:
 p=subprocess.Popen(argv,cwd=w,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 result["pid"]=p.pid;stop=None;minimum=free
 while p.poll() is None:
  current=shutil.disk_usage(base).free;minimum=min(minimum,current)
  if current<1024**3 or time.time()-result["startedAt"]>480:
   stop="resource" if current<1024**3 else "timeout";os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
   break
  time.sleep(2)
result.update(exitCode=p.returncode,finishedAt=time.time(),minimumFreeBytes=minimum,stopReason=stop,sourceHashesAfter={p:hashlib.sha256((w/p).read_bytes()).hexdigest() for p in paths})
text=log.read_text()
result["logSHA256"]=hashlib.sha256(log.read_bytes()).hexdigest()
result["actualPassedMethods"]=re.findall(r"Test Case 'NativeSourceCaptureDiagnosticsTests\.([^']+)' passed",text)
result["status"]="PASS" if p.returncode==0 and len(result["actualPassedMethods"])==3 and result["sourceHashes"]==result["sourceHashesAfter"] else "FAIL"
(run/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
for name in ["result.json","original-swift-test.log"]:
 q=out/name;q.write_bytes((run/name).read_bytes());os.chown(q,1001,1002)
for d in [root,prior,out]:os.chown(d,1001,1002)
print(json.dumps(result))
raise SystemExit(0 if result["status"]=="PASS" else 1)
