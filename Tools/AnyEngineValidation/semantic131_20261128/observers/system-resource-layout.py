import os,stat,json,time,resource,signal
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(134217728,134217728));signal.alarm(12)
start=time.monotonic()
paths=["/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/swift","/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/swift/linux","/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/swift/linux/Swift.swiftmodule"]
def ident(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_uid,s.st_gid,s.st_size,s.st_atime_ns,s.st_mtime_ns,s.st_ctime_ns,s.st_blocks]
out=[];total=0
for p in paths:
 try:a=os.lstat(p)
 except FileNotFoundError:out.append({"path":p,"absent":True});continue
 row={"path":p,"identity":ident(a),"kind":"directory" if stat.S_ISDIR(a.st_mode) else "symlink" if stat.S_ISLNK(a.st_mode) else "file"}
 if stat.S_ISDIR(a.st_mode):
  fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NOATIME)
  try:
   assert ident(os.fstat(fd))==ident(a)
   children=[]
   with os.scandir(fd) as it:
    for e in it:
     assert time.monotonic()-start<8 and len(children)<256 and total<768
     s=e.stat(follow_symlinks=False);total+=1
     children.append({"name":e.name,"identity":ident(s),"kind":"directory" if stat.S_ISDIR(s.st_mode) else "symlink" if stat.S_ISLNK(s.st_mode) else "file"})
   row["entries"]=sorted(children,key=lambda x:x["name"])
   assert ident(os.fstat(fd))==ident(a)==ident(os.lstat(p))
  finally:os.close(fd)
 row["metadataUnchangedIncludingAtime"]=ident(os.lstat(p))==ident(a);assert row["metadataUnchangedIncludingAtime"];out.append(row)
print(json.dumps({"schema":"pinkha-e-swift-resource-layout-metadata-v1","status":"PASS_READ_ONLY_METADATA","rows":out,"entries":total,"seconds":time.monotonic()-start,"projectWrites":0,"compilerInvocations":0,"payloadBytesOpened":0},sort_keys=True))
