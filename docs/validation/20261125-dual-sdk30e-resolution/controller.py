import pathlib,subprocess,json,hashlib,os,time,signal,shutil
r=pathlib.Path("/Users/m1/builds/pinkha-dual-main-20261125");s=r/"source";e=r/"resolve-sdk30e-1";e.mkdir(mode=0o700)
shutil.copyfile(__file__,e/"controller.py")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(["git","-C",str(s),*args],text=True).strip()
assert git("rev-parse","HEAD")=="6433fb3e9abd896dd2901a137b35b1f4665bdfdd" and not git("status","--porcelain")
lock=s/"Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
assert sha(lock)=="bb5582d3f0b9bc17b909ade4751904fd7b2fee2d066fea50b7a1ef913a8fe513"
assert sha(s/"Dependencies/Hanlin/.pinkha-source.json")=="0ae5a1476c899b1790f01a2a3b4118034e848d8ad8dcf2d97f12104f7387f798"
shutil.copyfile(lock,e/"Package.resolved.before")
env={**os.environ,"DEVELOPER_DIR":"/Applications/Xcode.app/Contents/Developer","PINKHA_ANY_NATIVE_ARTIFACT":"verified-unified-v1","PINKHA_NATIVE_T2_AUTHORIZED_READ_V1":"1"}
env["PATH"]="/opt/homebrew/bin:/usr/local/bin:"+env.get("PATH","/usr/bin:/bin")
argv=["xcodebuild","-resolvePackageDependencies","-project",str(s/"Anytype.xcodeproj"),"-scheme","Anytype","-configuration","Debug-Anytype","-derivedDataPath",str(r/"app-derived"),"-clonedSourcePackagesDirPath",str(r/"app-derived/SourcePackages"),"-skipPackagePluginValidation","-skipMacroValidation","CODE_SIGNING_ALLOWED=NO"]
receipt={"status":"RUNNING","sourceCommit":git("rev-parse","HEAD"),"controllerSHA256":sha(e/"controller.py"),"argv":argv,"started":time.time(),"freeBytesBefore":shutil.disk_usage("/System/Volumes/Data").free,"originalLockSHA256":sha(lock),"sdkReceiptSHA256":sha(s/"Dependencies/Hanlin/.pinkha-source.json"),"sourceFilesAllowedToChange":["Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"],"appBuilds":0,"testsExecuted":0}
assert receipt["freeBytesBefore"]>3*1024**3
def write():
 t=e/"receipt.json.tmp";t.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n");t.replace(e/"receipt.json")
with (e/"original.log").open("xb") as stream:
 p=subprocess.Popen(argv,cwd=s,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 receipt.update(pid=p.pid,pgid=p.pid);write()
 while p.poll() is None:
  free=shutil.disk_usage("/System/Volumes/Data").free;receipt["minimumFreeBytes"]=min(receipt.get("minimumFreeBytes",free),free)
  reason="DISK_FLOOR" if free<2*1024**3 else ("TIMEOUT" if time.time()-receipt["started"]>900 else None)
  if reason:
   receipt["stopReason"]=reason;os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=15)
   break
  time.sleep(2)
 receipt.update(exitCode=p.returncode,elapsedSeconds=time.time()-receipt["started"],logSHA256=sha(e/"original.log"))
changed=git("diff","--name-only").splitlines()
receipt["changedTrackedFiles"]=changed;receipt["sourceUnchangedExceptLock"]=changed in [[],receipt["sourceFilesAllowedToChange"]]
shutil.copyfile(lock,e/"Package.resolved.after")
receipt["resolvedLockSHA256"]=sha(lock);receipt["resolvedPinCount"]=len(json.loads(lock.read_text())["pins"])
receipt["freeBytesAfter"]=shutil.disk_usage("/System/Volumes/Data").free
receipt["status"]="PASS_ACTUAL_PACKAGE_RESOLUTION_REQUIRES_PIN_REVIEW" if p.returncode==0 and receipt["sourceUnchangedExceptLock"] else "FAIL_PACKAGE_RESOLUTION"
write();print(json.dumps(receipt))
