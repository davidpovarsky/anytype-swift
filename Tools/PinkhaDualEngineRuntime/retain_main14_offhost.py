from pathlib import Path
import os,json,hashlib,subprocess,shlex,tarfile,shutil,time,stat
D=Path('/mnt/development/projects/evidence/native-d-final-20261125/app14-original-retention1')
REMOTE='/Users/m1/development/anytype-d-active-20261125/main14'
EXPECTED='f99556f2870f519502e9da3fe2686b6f182cf238e1f04f75678ef31bcf497086'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ssh(argv,**kwargs):
 return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','scaleway-mac',shlex.join(argv)],user=1001,group=1001,env=dict(os.environ,USER='ubuntu',LOGNAME='ubuntu'),timeout=900,**kwargs)
assert not D.exists()
assert shutil.disk_usage(D.parent).free>2*1024**3+1200*1024**2
D.mkdir(mode=0o700)
start=time.time()
files=['original-build-retention1/receipt.json','original-build-retention1/members-before.json','original-build-retention1/members-after.json','original-build-retention1/originals.tar.gz','retention-control1/launch.json','retention-control1/retain_main14_originals.py','retention-control1/original.log']
script='import pathlib,json,hashlib; root=pathlib.Path('+repr(REMOTE)+'); names='+repr(files)+'; out={};\nfor name in names:\n p=root/name\n with p.open("rb") as f: h=hashlib.file_digest(f,"sha256").hexdigest()\n out[name]={"bytes":p.stat().st_size,"sha256":h}\nprint(json.dumps(out))'
first=ssh(['/opt/homebrew/bin/python3.12','-B','-c',script],capture_output=True,text=True);assert first.returncode==0,first.stderr
before=json.loads(first.stdout);assert before[files[0]]['sha256']==EXPECTED
(D/'remote-before.json').write_text(json.dumps(before,indent=2,sort_keys=True)+'\n')
copies={}
for name in files:
 target=D/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 temporary=target.with_suffix(target.suffix+'.partial')
 with temporary.open('xb') as f:
  os.chmod(temporary,0o600)
  result=ssh(['/bin/cat',REMOTE+'/'+name],stdout=f,stderr=subprocess.PIPE)
 assert result.returncode==0,result.stderr[-1000:]
 assert temporary.stat().st_size==before[name]['bytes'] and sha(temporary)==before[name]['sha256'],name
 temporary.rename(target);copies[name]=before[name]
 (D/'transfer-progress.json').write_text(json.dumps({'copied':list(copies),'time':time.time()},sort_keys=True)+'\n')
afterraw=ssh(['/opt/homebrew/bin/python3.12','-B','-c',script],capture_output=True,text=True);assert afterraw.returncode==0
after=json.loads(afterraw.stdout);assert before==after
(D/'remote-after.json').write_text(json.dumps(after,indent=2,sort_keys=True)+'\n')
receipt=json.loads((D/files[0]).read_bytes());members=json.loads((D/files[1]).read_bytes())
assert (D/files[1]).read_bytes()==(D/files[2]).read_bytes()
assert len(members)==receipt['members']==6433
assert sha(D/files[1])==receipt['memberManifestSHA256']
assert sha(D/files[3])==receipt['archiveSHA256']
seen=set()
with tarfile.open(D/files[3],'r|gz') as tf:
 for m in tf:
  name=m.name.rstrip('/')
  assert name in members and name not in seen,name
  assert not name.startswith('/') and '..' not in Path(name).parts
  record=members[name];assert stat.S_IMODE(m.mode)==record['mode'],name
  if record['kind']=='directory':assert m.isdir(),name
  elif record['kind']=='symlink':assert m.issym() and m.linkname==record['target'],name
  else:
   assert m.isfile() and not m.islnk() and m.size==record['bytes'],name
   f=tf.extractfile(m);assert f is not None
   assert hashlib.file_digest(f,'sha256').hexdigest()==record['sha256'],name
  seen.add(name)
assert seen==set(members)
out={'protocol':'original-App14-build-offhost-retention-v1','status':'PASS_ORIGINAL_ARCHIVE_AND_ALL_MEMBERS','sourceCommit':receipt['sourceCommit'],'originalRetentionReceiptSHA256':EXPECTED,'producerReceiptSHA256':receipt['producerReceiptSHA256'],'archiveSHA256':receipt['archiveSHA256'],'archiveBytes':receipt['archiveBytes'],'members':len(seen),'beforeCopyAfterEqual':True,'allArchivedMemberBytesModesLinksEqual':True,'files':copies,'started':start,'finished':time.time(),'tests':0,'builds':0,'acceptanceClaim':False}
p=D/'receipt.json';p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');os.chmod(p,0o600)
print(json.dumps({'status':out['status'],'receipt':str(p),'sha256':sha(p),'members':len(seen),'elapsedSeconds':time.time()-start}))
