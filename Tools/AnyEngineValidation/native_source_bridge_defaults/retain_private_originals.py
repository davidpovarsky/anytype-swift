from pathlib import Path
import os,json,hashlib,tarfile,stat
root=Path('/Users/m1/builds/pinkha-c-source-bridge-limits-20261125')
expected={'baseline':'c8229b594f08446fe1660ff283a740504bd593fe841592b885a04f4f2475d4a9','fixed':'95ce3a2f31d997302bdcac612673de703ce742249c4741071c459956ff9be095'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inventory(base):
 rows=[]
 for p in sorted([base,*base.rglob('*')]):
  st=p.lstat(); rel='.' if p==base else p.relative_to(base).as_posix()
  row={'path':rel,'mode':stat.S_IMODE(st.st_mode)}
  if stat.S_ISREG(st.st_mode):row.update(kind='file',bytes=st.st_size,sha256=sha(p))
  elif stat.S_ISDIR(st.st_mode):row.update(kind='directory')
  else:raise RuntimeError('nonregular member in owned private native retention')
  rows.append(row)
 return rows
out=root/'private-source-recovery-retention'
if out.exists():raise RuntimeError('immutable private retention already exists; inspect')
out.mkdir(mode=0o700)
proof={'contract':'pinkha-original-native-bridge-private-retention-v1','status':'FAIL','capturesAcceptedByRetention':False,'cases':[]}
for phase,original in expected.items():
 result=root/(phase+'-attempt1/result.json')
 raw=result.read_bytes(); data=json.loads(raw)
 if hashlib.sha256(raw).hexdigest()!=original or data.get('ownedProcessGroupAbsent') is not True or data.get('cleanupErrors'):raise RuntimeError('actual original outcome/cleanup differs')
 base=root/(phase+'-attempt1/private')
 before=inventory(base)
 manifest=out/(phase+'-private-inventory.json');manifest.write_text(json.dumps(before,indent=2)+'\n');manifest.chmod(0o600)
 archive=out/(phase+'-private-source-recovery.tar.gz')
 with tarfile.open(archive,'w:gz') as tar:tar.add(base,arcname='private',recursive=True)
 archive.chmod(0o600)
 with tarfile.open(archive,'r:gz') as tar:
  members={x.name:x for x in tar.getmembers()}
  if len(members)!=len(before):raise RuntimeError('archive census differs')
  for row in before:
   name='private' if row['path']=='.' else 'private/'+row['path'];m=members.get(name)
   if m is None or stat.S_IMODE(m.mode)!=row['mode']:raise RuntimeError('archive identity/mode differs')
   if row['kind']=='directory':
    if not m.isdir():raise RuntimeError('archive directory differs')
   else:
    if not m.isfile() or m.size!=row['bytes']:raise RuntimeError('archive file differs')
    with tar.extractfile(m) as f:
     if hashlib.file_digest(f,'sha256').hexdigest()!=row['sha256']:raise RuntimeError('archive native bytes differ')
 if inventory(base)!=before:raise RuntimeError('private source changed during retention')
 proof['cases'].append({'phase':phase,'originalResultSHA256':original,'originalStatus':data['status'],'entries':len(before),'bytes':sum(r.get('bytes',0) for r in before),'inventorySHA256':sha(manifest),'archive':str(archive),'archiveBytes':archive.stat().st_size,'archiveSHA256':sha(archive),'sourceBeforeEqualsAfter':True,'allArchivedPathsModesBytesEqual':True})
proof['status']='PASS_PRIVATE_SOURCE_RETENTION_ONLY'
p=out/'retention.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
print(json.dumps({'retention':str(p),'sha256':sha(p),'proof':proof}))
