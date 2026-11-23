import pathlib,zipfile,io,hashlib,json,os,stat,datetime
ROOT=pathlib.Path("/mnt/development/projects/diagnostics/coherent-kernel-actual-result-20261123")
OUT=ROOT/"diagnosis";DEST=OUT/"originals"
def sha(raw):return hashlib.sha256(raw).hexdigest()
v=os.statvfs("/mnt/development");free=v.f_bavail*v.f_frsize
assert free>=2500000000+16*1024**2,("capacity",free)
assert OUT.is_dir() and DEST.is_dir() and not any(DEST.rglob("*"))
outer=(ROOT/"artifact.zip").read_bytes()
assert len(outer)==1599793 and sha(outer)=="8741a6d631e3152f12fa49109a5c37484443b13aaea47e4765aabc6c89bd2198"
with zipfile.ZipFile(io.BytesIO(outer)) as z:
 infos=z.infolist()
 assert len(infos)==1 and infos[0].filename=="Pinkha-Native-Derived-Evidence.zip"
 inner=z.read(infos[0])
 assert len(inner)==1616135 and sha(inner)=="969439854b1b0d99ce0b50a52a52105b1eb2134357f3e2bcceeb7a2c7a8c3296"
rows=[]
with zipfile.ZipFile(io.BytesIO(inner)) as z:
 infos=z.infolist()
 assert len(infos)==85 and sum(x.file_size for x in infos)==7080758
 seen=set();fold=set()
 for i in infos:
  name=i.filename;parts=pathlib.PurePosixPath(name).parts
  assert name and not name.startswith("/") and "\\" not in name and ":" not in name
  assert all(x not in ["",".",".."] for x in parts)
  assert str(pathlib.PurePosixPath(name))==name and not any(ord(x)<32 for x in name)
  assert name not in seen and name.casefold() not in fold
  seen.add(name);fold.add(name.casefold())
  mode=i.external_attr>>16
  assert stat.S_ISREG(mode) and not i.is_dir() and i.file_size<=2*1024**2 and not i.flag_bits&1
  raw=z.read(i);assert len(raw)==i.file_size
  target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,"wb") as f:f.write(raw)
  assert target.read_bytes()==raw
  rows.append({"path":name,"bytes":len(raw),"compressed_bytes":i.compress_size,
               "zip_mode":oct(mode),"sha256":sha(raw)})
v=os.statvfs("/mnt/development")
receipt={"status":"SAFE_BOUNDED_EXTRACTION_COMPLETE","outer_sha256":sha(outer),
 "inner_sha256":sha(inner),"inner_member":"Pinkha-Native-Derived-Evidence.zip",
 "member_count":len(rows),"uncompressed_bytes":sum(x["bytes"] for x in rows),"links":0,
 "free_before":free,"free_after":v.f_bavail*v.f_frsize,
 "utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"entries":rows,
 "previous_guard":{"status":"BLOCKED_BEFORE_EXTRACTION","actual_extracted_files":0,
 "record_type":"POST_OBSERVATION_SUMMARY_NOT_ORIGINAL_STDERR",
 "condition":"free >= 2500000000 + 16*1024**2","exact_free_at_assertion":"NOT_CAPTURED",
 "subsequent_observation_utc":"2026-11-23T07:52:52.889771+00:00",
 "subsequent_free_bytes":2097020928,"source_or_artifact_mutations":0}}
raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
with (OUT/"inventory.json").open("xb") as f:f.write(raw)
print(json.dumps({"status":receipt["status"],"inventory_sha256":sha(raw),
 "members":len(rows),"bytes":receipt["uncompressed_bytes"],"free_before":free,"free_after":receipt["free_after"]}))
