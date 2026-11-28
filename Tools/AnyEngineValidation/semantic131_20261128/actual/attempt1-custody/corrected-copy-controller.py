import datetime,hashlib,json,os,shutil,stat,time
from pathlib import Path
SOURCE=Path("/run/pinkha-e-swift-semantic131-20261128-attempt1")
PARENT=Path("/mnt/development/projects/evidence")
DEST=PARENT/"pinkha-w1-semantic131-attempt1-20261128-custody2"
FILES=[
("result.json","result.json",63686,"b02a84d1962061de7e98152e00541480653a46555bd779e267e94e688b2c6c6b"),
("archive/manifest.json","archive_manifest.json",61564,"7f477fe5102ccbd3cb13a2bed06cd5fb200d32ab7e87d3b80ec7405a8c6eff28"),
("archive/content.bin.gz","content.bin.gz",1805742,"ab3bbb2a63e60f81216acd47a098996414dc686e0657dc6367cf24eeda3909df"),
("commands/01-TorahInspectorCore-typecheck/original.log","original.log",241,"2562e45a098bf04d703ab0f07afb8937fff4559b6e2c12c22e324dc3e96d7b6b")
]
started=time.monotonic(); rootfd=None; destfd=None
result={"schema":"pinkha-semantic131-attempt1-durable-custody-v1","status":"RUNNING","startedAtUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"destination":str(DEST),"originalsRemoved":False,"compilerInvocations":0,"nativeInvocations":0,"newDecompressionOrAcceptanceRun":False,"files":[],"errors":[]}
os.umask(0o077)
def need(value,message):
 if not value: raise RuntimeError(message)
def ident(s): return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_atime_ns)
def did(s): return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)
def guard():
 need(time.monotonic()-started<35,"finite custody deadline")
 need(shutil.disk_usage("/").free>=1073741824,"root emergency reserve")
 need(shutil.disk_usage(PARENT).free>=536870912+16777216,"development copy envelope and reserve")
def read_hash(path,size,sha,writer=None):
 guard(); need(path.resolve()==path and not path.is_symlink(),"physical exact file")
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
 try:
  before=os.fstat(fd)
  need(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode)==0o600 and before.st_nlink==1 and before.st_size==size,"single-link exact bounded source")
  need(ident(path.lstat())==ident(before),"source descriptor identity")
  h=hashlib.sha256(); count=0
  while count<=size:
   guard(); data=os.read(fd,min(262144,size+1-count))
   if not data: break
   count+=len(data); need(count<=size,"bounded source read"); h.update(data)
   if writer is not None:
    view=memoryview(data)
    while view:
     n=os.write(writer,view); need(n>0,"copy write progress"); view=view[n:]
  need(count==size and h.hexdigest()==sha,"whole exact source bytes")
  need(ident(os.fstat(fd))==ident(before)==ident(path.lstat()),"source full ns identity unchanged")
  return {"path":str(path),"bytes":count,"sha256":sha,"identity":list(ident(before))}
 finally: os.close(fd)
try:
 guard(); need(PARENT.resolve()==PARENT and PARENT.is_dir() and not PARENT.is_symlink(),"physical existing evidence parent")
 need(SOURCE.resolve()==SOURCE and SOURCE.is_dir() and not SOURCE.is_symlink(),"physical retained failure namespace")
 need(not os.path.lexists(DEST),"exclusive new custody destination")
 before=[]
 for relative,name,size,sha in FILES:
  before.append(read_hash(SOURCE/relative,size,sha))
 rootfd=os.open(PARENT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 parent_identity=did(os.fstat(rootfd))
 need(parent_identity==did(PARENT.lstat()),"parent identity")
 os.mkdir(DEST.name,0o700,dir_fd=rootfd)
 destfd=os.open(DEST.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=rootfd)
 created=os.fstat(destfd)
 need(stat.S_ISDIR(created.st_mode) and created.st_uid==os.geteuid() and did(created)==did(DEST.lstat()),"exact newly created owned directory before mode normalization")
 os.fchmod(destfd,0o700)
 dest_identity=did(os.fstat(destfd))
 need(dest_identity==did(DEST.lstat()) and os.fstat(destfd).st_uid==os.geteuid() and stat.S_IMODE(os.fstat(destfd).st_mode)==0o700,"private owned custody")
 os.fsync(rootfd); os.fsync(destfd)
 for (relative,name,size,sha),initial in zip(FILES,before):
  guard(); need(did(DEST.lstat())==dest_identity and did(PARENT.lstat())==parent_identity,"owned namespace unchanged")
  fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=destfd)
  try:
   again=read_hash(SOURCE/relative,size,sha,writer=fd)
   need(again==initial,"original source unchanged across copy")
   os.fsync(fd)
  finally: os.close(fd)
  copied=read_hash(DEST/name,size,sha)
  result["files"].append({"source":again,"copy":copied})
 os.fsync(destfd); os.fsync(rootfd)
 guard()
 result["copiedBytes"]=sum(x[2] for x in FILES)
 result["sourceFailureStatus"]="FAIL"
 result["inheritedArchiveInverse"]="Original failed controller verified all241 members; identical archive bytes retained here without rerunning that inverse."
 result["destinationOnDifferentDevice"]=SOURCE.stat().st_dev!=DEST.stat().st_dev
 need(result["destinationOnDifferentDevice"],"off-tmpfs durable filesystem")
 result["status"]="PASS_DURABLE_COPY_OF_FAILED_ATTEMPT"
except BaseException as error:
 result["status"]="FAIL_CUSTODY"; result["errors"].append({"type":type(error).__name__,"message":str(error)})
finally:
 result["endedAtUTC"]=datetime.datetime.now(datetime.timezone.utc).isoformat(); result["seconds"]=time.monotonic()-started
 if destfd is not None:
  raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
  fd=os.open("CUSTODY.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=destfd)
  try:
   view=memoryview(raw)
   while view:
    n=os.write(fd,view); need(n>0,"receipt progress"); view=view[n:]
   os.fsync(fd)
  finally: os.close(fd)
  os.fsync(destfd); os.fsync(rootfd)
  receipt=read_hash(DEST/"CUSTODY.json",len(raw),hashlib.sha256(raw).hexdigest())
  result["custodyReceipt"]={k:receipt[k] for k in ("path","bytes","sha256")}
 if destfd is not None: os.close(destfd)
 if rootfd is not None: os.close(rootfd)
 print(json.dumps(result,sort_keys=True),flush=True)
if result["status"]!="PASS_DURABLE_COPY_OF_FAILED_ATTEMPT": raise SystemExit(1)
