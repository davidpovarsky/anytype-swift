#!/usr/bin/env python3
import pathlib,zipfile,hashlib,json,io,stat,shutil,os,time
D=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-attempt2-original-result-20261123")
P=D/"original-14816672145.zip"
SHA="8fc2cac021e7c9a8a14cbcefc718a1f5eb35429994963aca8b771bb2ee2c2891"
def digest(b):return hashlib.sha256(b).hexdigest()
def identity(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
 return {"inode":s.st_ino,"mode":stat.S_IMODE(s.st_mode),"bytes":s.st_size,"mtime_ns":s.st_mtime_ns,"ctime_ns":s.st_ctime_ns}
def save(p,b):
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o400)
 return {"path":str(p),"bytes":len(b),"sha256":digest(b)}
def js(p,v):return save(p,(json.dumps(v,sort_keys=True,indent=2)+"\n").encode())
before=identity(P);b=P.read_bytes()
assert len(b)==2223532 and digest(b)==SHA and before["mode"]==0o400
with zipfile.ZipFile(io.BytesIO(b)) as outer:
 members=outer.infolist();assert len(members)==1
 m=members[0];assert m.filename=="Pinkha-Native-Derived-Evidence.zip" and stat.S_ISREG(m.external_attr>>16)
 inner=outer.read(m)
 assert len(inner)==2242518 and digest(inner)=="a55cdbfb5c27e6ff56d04aac2d5f64363353ed876c56073570b5d550bd58faad"
 outer_row={"path":m.filename,"bytes":m.file_size,"compressed_bytes":m.compress_size,"crc32":m.CRC,"mode":m.external_attr>>16,"sha256":digest(inner)}
with zipfile.ZipFile(io.BytesIO(inner)) as archive:
 members=archive.infolist()
 assert len(members)==109 and sum(x.file_size for x in members)==9205494
 names=set();parents=set()
 for m in members:
  p=pathlib.PurePosixPath(m.filename)
  assert m.filename and not p.is_absolute() and p.as_posix()==m.filename and not any(x in ("",".","..") for x in p.parts) and "\\" not in m.filename and ":" not in m.filename and "\x00" not in m.filename
  assert stat.S_ISREG(m.external_attr>>16) and not m.is_dir() and not m.flag_bits&1 and m.file_size<=2000000
  assert m.filename not in names;names.add(m.filename)
  for parent in p.parents:
   if parent.as_posix()!=".":parents.add(parent.as_posix())
 assert not names.intersection(parents)
 free=shutil.disk_usage(D).free
 assert free>=2500000000+9205494+16777216
 out=D/"private-originals";out.mkdir(mode=0o700)
 rows=[]
 for m in members:
  assert shutil.disk_usage(D).free>=2500000000+min(16777216,m.file_size)
  target=out/m.filename;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  for parent in target.parents:
   if parent==out:break
   assert parent.is_dir() and not parent.is_symlink()
  data=archive.read(m);assert len(data)==m.file_size
  row=save(target,data);row["path"]=m.filename;row["mode"]=0o400;row["crc32"]=m.CRC
  rows.append(row)
assert identity(P)==before and digest(P.read_bytes())==SHA
report={"protocol":"original-release-attempt2-safe-extraction-v1","archive_sha256":SHA,"archive_identity":before,"archive_identity_unchanged":True,"outer":outer_row,"inner_sha256":digest(inner),"logical_bytes":sum(x["bytes"] for x in rows),"file_count":len(rows),"files":rows,"private_root":str(out),"free_before":free,"free_after":shutil.disk_usage(D).free,"reader_sha256":digest(pathlib.Path(__file__).read_bytes()),"tests_run":0,"builds_run":0,"api_queries":0}
receipt=js(D/"original-extraction.json",report)
print(json.dumps({"status":"PASS_EXACT109_ORIGINALS_RETAINED","receipt":receipt,"free":shutil.disk_usage(D).free,"tests_run":0}))
