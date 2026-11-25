import pathlib,subprocess,json,hashlib,os
base=pathlib.Path("/mnt/development/projects/evidence/migration-final-20261125/private-current9d-source-custody")
base.mkdir(mode=0o700,exist_ok=False)
remote=r'''import pathlib,json,hashlib,stat,subprocess,os
r=pathlib.Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/current9d-installed-observer-attempt1")
d=r/"private/owned-account-originals";proof=d/"retention.json"
def digest(p):return hashlib.file_digest(p.open("rb"),"sha256").hexdigest()
assert digest(proof)=="c52e7d9a23cd27a08648cf4eab9d0bb90f8328cbf926ec6817af024a7b99fa06"
receipt=json.loads(proof.read_text());assert receipt["status"]=="PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
assert receipt["executionSHA256"]=="8b92db25cb90b599ba8cf50e2c53435de036b9213f73d02514eca8bbb508f580"
def inv(root):
 out={}
 for p in sorted(root.rglob("*")):
  e=p.lstat();row={"mode":stat.S_IMODE(e.st_mode)}
  if stat.S_ISLNK(e.st_mode):
   target=p.readlink();assert not target.is_absolute() and p.resolve(strict=True).is_relative_to(root)
   row.update(kind="symlink",target=str(target))
  elif stat.S_ISDIR(e.st_mode):row.update(kind="directory")
  elif stat.S_ISREG(e.st_mode):row.update(kind="file",bytes=e.st_size,sha256=digest(p))
  else:raise AssertionError("unexpected nonpersistent entry")
  out[p.relative_to(root).as_posix()]=row
 return out
def verify():
 for label,row in receipt["scopes"].items():
  assert row["status"]=="PRESERVED_ORIGINAL_BYTES_AND_MODES"
  m=d/(label+"-before.json");assert digest(m)==row["manifestSHA256"]
  expected=json.loads(m.read_text());assert inv(d/label)==expected
 assert digest(proof)=="c52e7d9a23cd27a08648cf4eab9d0bb90f8328cbf926ec6817af024a7b99fa06"
 assert digest(d/"device.plist")=="5d8e8abb2bbb943da549ca2002b508e96a8169328efba00c8916b3f936f977de"
verify()
dest=r/"private/c52e-account-backup.tgz";assert not dest.exists()
os.umask(0o077)
subprocess.run(["tar","-czf",str(dest),"-C",str(d.parent),d.name],check=True,timeout=60)
verify()
print(json.dumps({"archive":str(dest),"bytes":dest.stat().st_size,"sha256":digest(dest),"originalRetentionSHA256":digest(proof),"accountInventoriesVerifiedBeforeAfter":True,"nativeCalls":0,"sqliteOpened":False}))
'''
p=subprocess.run(["sudo","-n","-u","ubuntu","ssh","-o","BatchMode=yes","scaleway-mac","/opt/homebrew/bin/python3.12","-B","-"],input=remote,text=True,capture_output=True,timeout=90)
assert p.returncode==0,(p.stdout,p.stderr)
d=json.loads(p.stdout);dest=base/"c52e-account-backup.tgz"
fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"wb") as out:
 q=subprocess.run(["sudo","-n","-u","ubuntu","ssh","-o","BatchMode=yes","scaleway-mac","/bin/cat",d["archive"]],stdout=out,stderr=subprocess.PIPE,timeout=90)
assert q.returncode==0 and dest.stat().st_size==d["bytes"]
with dest.open("rb") as s:actual=hashlib.file_digest(s,"sha256").hexdigest()
assert actual==d["sha256"]
d.update(oracleArchive=str(dest),transferSHA256=actual,status="PASS_SEALED_PRIVATE_ACCOUNT_CUSTODY_NOT_ACCEPTANCE",publicUpload=False)
path=base/"receipt.json";path.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n");path.chmod(0o600)
print(json.dumps(d))
