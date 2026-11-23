import pathlib,hashlib,json,zipfile,stat,os,zlib
ROOT=pathlib.Path(r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\loaded-account-compiler-original-45262244082-1')
OUT=ROOT/'audit1'
assert OUT.is_dir()
archive=ROOT/'original-14860902326.zip'
def meta(s):
 return {k:str(getattr(s,k)) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns','st_nlink')}
before=meta(archive.stat())
assert stat.S_ISREG(archive.stat().st_mode) and archive.stat().st_size==328616
assert archive.stat().st_file_attributes&1 and not archive.stat().st_file_attributes&1024
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='543e97bbd659ed25b78aad7eed340340524894051eebcd209328914c63545ddb'
target=OUT/'originals';target.mkdir(mode=0o700)
rows={};names=set();case=set();total=0;count=0
with zipfile.ZipFile(archive) as z:
 assert len(z.infolist())<=4096
 for info in z.infolist():
  name=info.filename
  relative=pathlib.PurePosixPath(name.rstrip('/'))
  assert name and '\\' not in name and '\0' not in name and not relative.is_absolute()
  assert str(relative)==name.rstrip('/') and all(x not in ('.','..') and not x.endswith(('.',' ')) and ':' not in x for x in relative.parts)
  assert name not in names and str(relative).casefold() not in case
  names.add(name);case.add(str(relative).casefold())
  mode=(info.external_attr>>16)&65535
  assert stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR) and not info.flag_bits&1
  dest=target/pathlib.Path(*relative.parts)
  if info.is_dir():
   dest.mkdir(parents=True,exist_ok=True);continue
  assert info.file_size<=32*1024**2
  total+=info.file_size;assert total<=96*1024**2
  dest.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();crc=0;size=0
  with z.open(info) as src,dest.open('xb') as out:
   while True:
    raw=src.read(1024**2)
    if not raw:break
    h.update(raw);crc=zlib.crc32(raw,crc);size+=len(raw);out.write(raw)
   out.flush();os.fsync(out.fileno())
  assert size==info.file_size and crc==info.CRC
  rows[name]={'bytes':size,'sha256':h.hexdigest(),'crc32':format(crc,'08x'),'compressed_bytes':info.compress_size,'external_attr':info.external_attr,'type':'regular'}
  count+=1
assert before==meta(archive.stat())
result=json.loads((target/'result.json').read_text(encoding='utf-8'))
commands=[]
for value in result.get('commands',[]):
 row={k:value.get(k) for k in ('name','started','returncode','primary_error','cleanup_error','persistence_errors','elapsed_seconds','owned_group_cleanup')}
 if value.get('primary_error') is not None or value.get('cleanup_error') is not None:
  stderr=value.get('stderr',{}).get('path')
  if stderr:
   local=target/'commands'/pathlib.PurePosixPath(stderr).name
   if local.exists():row['original_stderr_excerpt']=local.read_bytes()[:8192].decode('utf-8','replace')
 commands.append(row)
summary={'schema':'loaded-account-compiler-original-artifact-audit-v1','status':'PASS_ORIGINAL_ARTIFACT_INTEGRITY',
 'run_id':45262244082,'attempt':1,'source_sha':'56b4caafae1c0898b483717abed495f2e3b9281b',
 'artifact_id':14860902326,'archive_sha256':'543e97bbd659ed25b78aad7eed340340524894051eebcd209328914c63545ddb',
 'original_before':before,'original_after':meta(archive.stat()),'members':len(names),'regular_files':count,'uncompressed_bytes':total,
 'all_member_crc_and_sha256_verified':True,'producer_status':result.get('status'),
 'primary_error':result.get('primary_error'),'final_errors':result.get('final_errors'),
 'native_builds':result.get('native_builds'),'native_tests':result.get('native_tests'),'go_queries':result.get('go_queries'),
 'commands':commands,'compiler_image_tar_present':(target/'compiler-image.tar').exists(),
 'consumer_admission':False,'compiler_production_pass':False,'new_downloads':1,'new_ci_queries':0,'new_executions':0}
for name,value in (('member-map.json',rows),('audit.json',summary)):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 with (OUT/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps({'audit_sha256':hashlib.sha256((OUT/'audit.json').read_bytes()).hexdigest(),
 'member_map_sha256':hashlib.sha256((OUT/'member-map.json').read_bytes()).hexdigest(),'summary':summary},ensure_ascii=True))
