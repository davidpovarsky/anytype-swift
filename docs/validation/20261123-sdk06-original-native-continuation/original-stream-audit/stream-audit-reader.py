import ast,gzip,hashlib,json,os,pathlib,re,shutil,stat,subprocess,tarfile,time,traceback,zipfile
ROOT=pathlib.Path(r"C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\sdk06-tagged-45139431216-1")
ARCHIVE=ROOT/"artifact-14803859457.zip"
OUT=ROOT/"full-products-stream-audit"
OUTER_BYTES=699372357
OUTER_SHA="af9ae3c1736b7eea395160c5cebabfe394bc11cfe083cc62df682ce870dea81b"
INNER_NAME="Pinkha-Native-Derived-Evidence.zip"
INNER_BYTES=699191123
INNER_SHA="15524c36f1f8e60ccf272577357c140a01d7aaed1d8bca118d3cdfd8eedb5b30"
TAR_PATH="sdk06-early-products/BuildProducts.tar.gz"
TAR_BYTES=715817922
TAR_SHA="478d17c0517a983830410d80b1f9630e42fb09e2293a2360d91ebf887a7ed18a"
MANIFEST_PATH="bounded-original-audit/selected/sdk06-early-products/manifest.json"
FILE_ID="0x0000000000000000003500000019eb23"
OWNER="S-1-5-21-2914620446-786530585-2031499938-1001"
PRIVATE_SIDS=["S-1-5-18",OWNER,"S-1-5-32-544"]
MAX_SELECTED=16*1024**2
INPUT_PINS={
 "download-attempt2.json": "2018084ca3226cf8ec245bc78737c800082628ca556abe85cd7a9947d3780983",
 "bounded-original-audit/selection-audit.json": "ee48438b7a2e8ec17d7ae73c0aa56619aec867207fcdba876a7a7ab5c95ea9f5",
 "descriptor-only-originals/descriptor-audit.json": "db9a920e7eb7ff1cdb623555403d0d49084f0a46b1cab8f2b300ddc66e8ef2bd",
 "descriptor-only-audit-reader.py": "4448ab020eb3f8cbcac36135fe86abd22c7b89f6b59a6204a8cea3e940cb4eac",
 "bounded-original-audit/selected/sdk06-early-products/manifest.json": "331ad15a50b7c0d815fde3b2597b63d24f4de48b206f005aecbf0316f5fe5707"
}
EXPECTED_ARCHIVE_METADATA={
 "st_dev": "5400942862240111193",
 "st_ino": "14918173767363363",
 "st_mode": "33060",
 "st_size": "699372357",
 "st_mtime_ns": "1795428744095634900",
 "st_ctime_ns": "1795427710871391300",
 "st_nlink": "1",
 "st_file_attributes": "33",
 "st_reparse_tag": "0"
}
HELPER_PINS={
 "BoundedInner": "56bee4ad557290365d0eb5cecae9a6295232f9de6b8c9d712bf278944dc3388e",
 "HashReader": "5bb359c3088c306de50d3b5c2c2e7f31f9a19dda494a18ad1356eb45836f174a",
 "safe_name": "af8c3c15e84ad24d63751b6fbfe7b63d074d03ef73db90e62a001475ca927fe1"
}
def sha(b):return hashlib.sha256(b).hexdigest()

class BoundedInner:
 def __init__(self,stream,size):
  self.stream=stream;self.size=size;self.position=0;self.total_read=0;self.resets=0;self.digest=hashlib.sha256();self.complete_passes=[]
 def tell(self):return self.position
 def seekable(self):return True
 def _part(self,n):
  assert 0<=n<=1024**2 and self.total_read+n<=self.size*8
  b=self.stream.read(n);assert len(b)==n
  self.digest.update(b);self.position+=len(b);self.total_read+=len(b)
  if self.position==self.size:self.complete_passes.append(self.digest.hexdigest())
  return b
 def seek(self,offset,whence=0):
  target=offset+(self.position if whence==1 else self.size if whence==2 else 0)
  assert whence in (0,1,2) and 0<=target<=self.size
  if target<self.position:
   assert self.resets<8
   self.stream.seek(0);self.position=0;self.digest=hashlib.sha256();self.resets+=1
  while self.position<target:self._part(min(1024**2,target-self.position))
  return self.position
 def read(self,n=-1):
  if n<0:n=self.size-self.position
  n=min(n,self.size-self.position)
  assert 0<=n<=MAX_SELECTED
  chunks=[]
  while n:
   b=self._part(min(1024**2,n));chunks.append(b);n-=len(b)
  return b"".join(chunks)

class HashReader:
 def __init__(self,stream,size):
  self.stream=stream;self.size=size;self.count=0;self.digest=hashlib.sha256()
 def read(self,n=-1):
  assert 0<=n<=1024**2
  b=self.stream.read(n);self.count+=len(b);assert self.count<=self.size;self.digest.update(b);return b

def safe_name(name):
 assert isinstance(name,str) and 0<len(name)<=1024 and "\\" not in name and "\x00" not in name
 p=pathlib.PurePosixPath(name)
 assert not p.is_absolute() and all(x not in ("",".","..") and ":" not in x for x in p.parts)
 assert str(p)==name.rstrip("/")
 return name

def strict_pairs(pairs):
 out={}
 for k,v in pairs:
  assert k not in out,"duplicate JSON key"
  out[k]=v
 return out
def read_json(path):
 return json.loads(path.read_bytes(),object_pairs_hook=strict_pairs)
def now():return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def metadata(path):
 s=path.stat()
 return {k:str(getattr(s,k)) for k in EXPECTED_ARCHIVE_METADATA}
def file_id():
 p=subprocess.run(["fsutil","file","queryfileid",str(ARCHIVE)],capture_output=True,text=True,timeout=15)
 assert p.returncode==0 and not p.stderr
 m=re.fullmatch(r"File ID is (0x[0-9a-fA-F]{32})\s*",p.stdout)
 assert m and m.group(1).lower()==FILE_ID
 return m.group(1).lower()
def access_state():
 quoted=",".join("'"+str(p).replace("'","''")+"'" for p in (ROOT,ARCHIVE,OUT))
 command="$ErrorActionPreference='Stop';$rows=@(foreach($p in @("+quoted+")){$a=Get-Acl -LiteralPath $p;$i=Get-Item -LiteralPath $p -Force;[ordered]@{path=$p;owner_sid=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value;sddl=$a.Sddl;access_sids=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier])|ForEach-Object{$_.IdentityReference.Value}|Sort-Object -Unique);protected=$a.AreAccessRulesProtected;attributes=[int]$i.Attributes}});ConvertTo-Json -InputObject $rows -Depth 6 -Compress"
 p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],capture_output=True,text=True,timeout=20)
 assert p.returncode==0 and not p.stderr
 rows=json.loads(p.stdout);assert len(rows)==3
 for row,path in zip(rows,(ROOT,ARCHIVE,OUT)):
  assert row["path"]==str(path) and row["owner_sid"]==OWNER
  assert set(row["access_sids"])==set(PRIVATE_SIDS)
  assert not row["attributes"]&1024
 assert rows[1]["protected"] is True and rows[1]["attributes"]&1
 return rows
def check_source_helpers():
 original=(ROOT/"descriptor-only-audit-reader.py").read_bytes()
 assert sha(original)==INPUT_PINS["descriptor-only-audit-reader.py"]
 current=pathlib.Path(__file__).read_bytes()
 for raw in (original,current):
  lines=raw.splitlines(keepends=True);tree=ast.parse(raw)
  for name,expected in HELPER_PINS.items():
   n=next(n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
   assert sha(b"".join(lines[n.lineno-1:n.end_lineno]))==expected
def output(relative,data):
 p=OUT/relative
 assert pathlib.PurePosixPath(relative).name==relative and not p.exists()
 with p.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.chmod(p,stat.S_IREAD)
 return {"path":relative,"bytes":len(data),"sha256":sha(data)}
def save(relative,value):
 return output(relative,(json.dumps(value,sort_keys=True,indent=2)+"\n").encode())
def bounded_name(name):
 safe_name(name)
 assert name==str(pathlib.PurePosixPath(name)) and not name.endswith("/")
 name.encode("utf-8","strict")
 assert name=="Build/PinkhaSourceInputs.json" or name=="Build/Products" or name.startswith("Build/Products/")
 return name
def deadline():
 assert time.monotonic()<DEADLINE,"bounded audit deadline exceeded"
def exception_row(error):
 return {"type":type(error).__name__,"message":str(error)[:1000]}
started=now();DEADLINE=time.monotonic()+250
report={"protocol":"sdk06-original-products-full-stream-audit-v1","status":"STARTED","started_utc":started,"run_id":"45139431216","run_attempt":"1","source_sha":"75bd6d7af18dfd511e85582ce7f994d2801b7703","artifact_id":"14803859457","reader_sha256":sha(pathlib.Path(__file__).read_bytes()),"original_outer_sha256":OUTER_SHA,"outer_full_hash_reexecuted":False,"original_outer_hash_admission":"PINNED_PREVIOUS_FULL_READBACK_AND_CURRENT_IMMUTABLE_FILE_ID_METADATA_ACCESS","source_input_pins":INPUT_PINS,"helper_source_slice_pins":HELPER_PINS,"products_materialized":False,"regular_payloads_written":0,"native_builds":0,"product_tests":0,"oracle_files_written":0,"build_reuse_enabled":False,"every_entry_build_origin_verified":False,"native_acceptance_reused":False,"ui_acceptance_reused":False,"restoration_authorized":False,"restoration_performed":False,"all_manifest_entries_verified":False}
entries=[];seen=set();case_seen=set();stage="fixed_inputs";before=None;access_before=None;observed_bytes=0;tar_reader=None;bounded=None
try:
 assert OUT==pathlib.Path(__file__).parent and OUT.is_dir() and not OUT.is_symlink()
 assert not (OUT/"stream-audit.json").exists() and not (OUT/"entry-map.json.gz").exists()
 assert shutil.disk_usage(ROOT).free>=2500000000+MAX_SELECTED
 for name,expected in INPUT_PINS.items():
  p=ROOT/name;assert p.is_file() and not p.is_symlink() and sha(p.read_bytes())==expected
 check_source_helpers()
 freeze=read_json(OUT/"source-freeze.json")
 assert freeze["reader_sha256"]==report["reader_sha256"] and freeze["audit_executions_before_freeze"]==0
 report["source_freeze_sha256"]=sha((OUT/"source-freeze.json").read_bytes())
 receipt=read_json(ROOT/"download-attempt2.json")
 prior=read_json(ROOT/"bounded-original-audit/selection-audit.json")
 descriptor=read_json(ROOT/"descriptor-only-originals/descriptor-audit.json")
 assert receipt["status"]=="VERIFIED_ORIGINAL_ARCHIVE" and receipt["full_archive_verified"] is True
 assert receipt["final_file"]["sha256"]==OUTER_SHA and receipt["final_file"]["bytes"]==OUTER_BYTES and receipt["final_file"]["file_id"]==FILE_ID
 assert prior["status"]=="VERIFIED_ORIGINAL_ARTIFACT_AND_SELECTION_DIAGNOSIS" and prior["outer"]["sha256"]==OUTER_SHA and prior["nested_zip"]["sha256"]==INNER_SHA
 assert descriptor["status"]=="EXACT_ORIGINAL_DESCRIPTOR_AND_ARCHIVE_BYTES_VERIFIED" and descriptor["archive_stream_verification"]["sha256"]==TAR_SHA
 assert ARCHIVE.is_file() and not ARCHIVE.is_symlink()
 before=metadata(ARCHIVE);assert before==EXPECTED_ARCHIVE_METADATA
 assert int(before["st_file_attributes"])&1 and not int(before["st_file_attributes"])&1024 and before["st_reparse_tag"]=="0"
 assert file_id()==FILE_ID
 access_before=access_state();assert access_before[1]["sddl"]==receipt["final_file"]["acl_sddl"]
 report["archive_before"]={"path":str(ARCHIVE),"metadata_strings":before,"file_id":FILE_ID,"access":access_before}
 manifest=read_json(ROOT/MANIFEST_PATH);products=manifest["products"]
 assert len(products)==5011 and manifest["archive_bytes"]==TAR_BYTES and manifest["archive_sha256"]==TAR_SHA and manifest["archive_path"]==TAR_PATH
 assert manifest["source_sha"]==report["source_sha"] and manifest["run_id"]==report["run_id"] and manifest["run_attempt"]==report["run_attempt"]
 for flag in ("build_reuse_enabled","every_entry_build_origin_verified","native_acceptance_reused","ui_acceptance_reused"):assert manifest[flag] is False
 kinds={};manifest_case=set();regular_total=0
 for name,row in products.items():
  bounded_name(name);assert name.casefold() not in manifest_case;manifest_case.add(name.casefold())
  assert row["kind"] in ("file","directory") and type(row["mode"]) is int and 0<=row["mode"]<=0o7777
  assert set(row)==({"kind","mode","bytes","sha256"} if row["kind"]=="file" else {"kind","mode"})
  if row["kind"]=="file":
   assert type(row["bytes"]) is int and 0<=row["bytes"]<=316294696 and re.fullmatch(r"[0-9a-f]{64}",row["sha256"])
   regular_total+=row["bytes"]
  for parent in pathlib.PurePosixPath(name).parents:
   if str(parent) in ("Build","."):continue
   assert str(parent) in products and products[str(parent)]["kind"]=="directory"
  kinds[row["kind"]]=kinds.get(row["kind"],0)+1
 assert kinds=={"file":3779,"directory":1232} and regular_total==2375184946
 report["manifest"]={"path":MANIFEST_PATH,"sha256":INPUT_PINS[MANIFEST_PATH],"entries":5011,"kind_counts":kinds,"regular_bytes":regular_total,"identity_rule":"EXACT_UNICODE_PATH_BYTES_WITH_CASEFOLD_COLLISION_REFUSAL"}
 stage="bounded_stream_all_entries"
 with zipfile.ZipFile(ARCHIVE) as outer:
  oi=outer.infolist();assert len(oi)==1
  o=oi[0]
  assert o.filename==INNER_NAME and o.file_size==INNER_BYTES and o.compress_size==699372175 and o.CRC==0xa9d47bbb and o.compress_type==8 and not o.flag_bits&1
  with outer.open(o,"r") as stream:
   bounded=BoundedInner(stream,INNER_BYTES)
   with zipfile.ZipFile(bounded) as inner:
    infos=inner.infolist();assert len(infos)==124
    names=set();case_names=set()
    for z in infos:
     safe_name(z.filename);assert z.filename not in names and z.filename.casefold() not in case_names
     names.add(z.filename);case_names.add(z.filename.casefold())
     assert not stat.S_ISLNK(z.external_attr>>16) and not z.flag_bits&1
    z=inner.getinfo(TAR_PATH)
    assert z.file_size==TAR_BYTES and z.CRC==0x4bb49adf and not z.is_dir()
    with inner.open(z,"r") as compressed:
     tar_reader=HashReader(compressed,TAR_BYTES)
     with tarfile.open(fileobj=tar_reader,mode="r|gz") as archive:
      for t in archive:
       deadline();name=bounded_name(t.name)
       assert len(entries)<5011 and name not in seen and name.casefold() not in case_seen and name in products
       expected=products[name]
       assert t.mode==expected["mode"] and not t.linkname and t.sparse is None
       if expected["kind"]=="directory":
        assert t.type==tarfile.DIRTYPE and t.isdir() and t.size==0
        row={"path":name,"kind":"directory","mode":t.mode,"bytes":0,"sha256":None}
       else:
        assert t.type in (tarfile.REGTYPE,tarfile.AREGTYPE) and t.isfile() and t.size==expected["bytes"]
        f=archive.extractfile(t);assert f is not None
        count=0;h=hashlib.sha256()
        with f:
         while True:
          deadline();chunk=f.read(1024**2)
          if not chunk:break
          assert len(chunk)<=1024**2;count+=len(chunk);assert count<=expected["bytes"]
          h.update(chunk)
        assert count==expected["bytes"] and h.hexdigest()==expected["sha256"]
        observed_bytes+=count
        row={"path":name,"kind":"file","mode":t.mode,"bytes":count,"sha256":h.hexdigest()}
       seen.add(name);case_seen.add(name.casefold())
       row.update(ordinal=len(entries)+1,header_offset=t.offset,data_offset=t.offset_data,header_type_hex=t.type.hex(),matches_original_manifest=True,build_origin_verified=False)
       entries.append(row)
     while True:
      deadline()
      if not tar_reader.read(1024**2):break
     assert tar_reader.count==TAR_BYTES and tar_reader.digest.hexdigest()==TAR_SHA
     report["compressed_tar_stream"]={"path":TAR_PATH,"bytes":tar_reader.count,"sha256":tar_reader.digest.hexdigest(),"zip_crc32":format(z.CRC,"08x"),"compressed_member_EOF_reached":True,"tail_drained_after_tar_EOF":True}
   assert bounded.complete_passes and set(bounded.complete_passes)=={INNER_SHA}
   report["nested_zip_stream"]={"member":INNER_NAME,"bytes":INNER_BYTES,"sha256":INNER_SHA,"verified_complete_passes":len(bounded.complete_passes),"reader_resets":bounded.resets,"stream_bytes_read":bounded.total_read,"reader_reset_limit":8,"reader_total_limit":INNER_BYTES*8}
 assert len(entries)==len(seen)==5011 and seen==set(products) and observed_bytes==regular_total
 assert sum(e["kind"]=="directory" for e in entries)==1232 and sum(e["kind"]=="file" for e in entries)==3779
 report.update(all_manifest_entries_verified=True,verified_entries=5011,verified_regular_bytes=observed_bytes,status="PASS_EXACT_5011_MANIFEST_ENTRIES_STREAM_VERIFIED")
except BaseException as error:
 report.update(status="FAILED_STREAM_AUDIT_ORIGINALS_PRESERVED",failed_stage=stage,error=exception_row(error))
 report["traceback"]=traceback.format_exc()
finally:
 try:
  if before is not None:
   after=metadata(ARCHIVE);assert after==before and file_id()==FILE_ID
   access_after=access_state();assert access_after==access_before
   report["archive_after"]={"metadata_strings":after,"file_id":FILE_ID,"access":access_after}
   report["original_archive_metadata_identity_and_access_unchanged"]=True
  for name,expected in INPUT_PINS.items():assert sha((ROOT/name).read_bytes())==expected
  assert report["reader_sha256"]==sha(pathlib.Path(__file__).read_bytes())
  report["source_inputs_unchanged"]=True
 except BaseException as error:
  report["postflight_failure"]=exception_row(error);report["status"]="FAILED_STREAM_AUDIT_ORIGINALS_PRESERVED"
  report["all_manifest_entries_verified"]=False
 entry_data=(json.dumps({"protocol":"sdk06-original-entry-byte-observations-v1","manifest_sha256":INPUT_PINS[MANIFEST_PATH],"manifest_total":5011,"observed_verified_entries":len(entries),"complete":report["status"]=="PASS_EXACT_5011_MANIFEST_ENTRIES_STREAM_VERIFIED","entries":entries},sort_keys=True,separators=(",",":"))+"\n").encode()
 assert len(entry_data)<=8*1024**2
 report["entry_map"]=output("entry-map.json.gz",gzip.compress(entry_data,mtime=0))
 report["entry_map"]["uncompressed_bytes"]=len(entry_data);report["entry_map"]["uncompressed_sha256"]=sha(entry_data)
 report["finished_utc"]=now();report["elapsed_seconds"]=250-(DEADLINE-time.monotonic());report["verified_entry_count_on_exit"]=len(entries)
 proof=save("stream-audit.json",report)
 print(json.dumps({"status":report["status"],"audit_receipt":proof,"verified_entries":len(entries),"entry_map":report["entry_map"],"regular_bytes":observed_bytes,"products_materialized":False,"build_reuse_enabled":False,"restoration_authorized":False,"product_tests":0},sort_keys=True),flush=True)
if report["status"]!="PASS_EXACT_5011_MANIFEST_ENTRIES_STREAM_VERIFIED":raise SystemExit(1)
