import pathlib,subprocess,json,hashlib,os,tarfile,urllib.request,time,traceback
base=pathlib.Path('/mnt/development/projects/evidence/migration-final-20261125/native-bridge-limits-qualification')
base.mkdir(mode=0o700,exist_ok=False)
repo=pathlib.Path('/mnt/development/projects/worktrees/anytype-heart-source-capture-limits-20261125')
baseline='d59568f999c9f1e6aa1d014a743d16999de84006';fixed='b7454dca344db7d32f0dc7b7eb5aff575b6a2535'
def git(*args):
 r=subprocess.run(['git','-c','safe.directory='+str(repo),'-C',str(repo),*args],capture_output=True,timeout=60)
 if r.returncode:raise RuntimeError(r.stderr.decode())
 return r.stdout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n');os.chmod(p,0o600)
record={'contract':'pinkha-native-source-bridge-regression-inputs-v1','baseline':baseline,'fixed':fixed,'status':'PREPARING','started':time.time()}
try:
 archive=base/'heart-baseline-d59568f9.tar.gz'
 git('archive','--format=tar.gz','--output='+str(archive),baseline)
 treeRows={}
 for raw in git('ls-tree','-r','-z','--long',baseline).split(b'\0'):
  if not raw:continue
  a,path=raw.split(b'\t',1);mode,kind,oid,size=a.decode().split()
  if kind!='blob':raise RuntimeError('unexpected native nonblob')
  treeRows[path.decode()]={'path':path.decode(),'gitMode':mode,'gitBlob':oid,'bytes':int(size)}
 members=[]
 with tarfile.open(archive,'r:gz') as t:
  for m in t.getmembers():
   if m.isdir():continue
   if m.name not in treeRows or m.name.startswith('/') or '..' in pathlib.PurePosixPath(m.name).parts:raise RuntimeError('unexpected archive path')
   if m.isfile():data=t.extractfile(m).read()
   elif m.issym():data=m.linkname.encode()
   else:raise RuntimeError('unexpected archive member type')
   row=treeRows.pop(m.name)
   if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['gitBlob']:raise RuntimeError('archive differs from Git blob')
   row['sha256']=hashlib.sha256(data).hexdigest();members.append(row)
 if treeRows:raise RuntimeError('incomplete native source archive')
 members.sort(key=lambda x:x['path'])
 baselineManifest={'source':baseline,'tree':git('rev-parse',baseline+'^{tree}').decode().strip(),'files':members,'archiveSHA256':sha(archive),'archiveBytes':archive.stat().st_size}
 save(base/'baseline-source.json',baselineManifest)
 changed=git('diff','--name-only',baseline,fixed).decode().splitlines()
 if changed!=['core/pinkha_native_source_capture.go']:raise RuntimeError('unscoped fixed native source')
 fixedRaw=git('show',fixed+':'+changed[0])
 (base/'fixed-core-source.go').write_bytes(fixedRaw)
 fixedMembers=[dict(x) for x in members]
 for row in fixedMembers:
  if row['path']==changed[0]:
   row.update(bytes=len(fixedRaw),gitBlob=git('rev-parse',fixed+':'+row['path']).decode().strip(),sha256=hashlib.sha256(fixedRaw).hexdigest())
 fixedManifest={'source':fixed,'tree':git('rev-parse',fixed+'^{tree}').decode().strip(),'files':fixedMembers,'baseSource':baseline,'onlyChangedPaths':changed}
 save(base/'fixed-source.json',fixedManifest)
 sync=pathlib.Path('/mnt/development/projects/evidence/migration-final-20261125/native-default-test-inputs/any-sync-native-witness-source.tar.gz')
 if sha(sync)!='481b3aa9aeace3de01e3b184b3965ce57a50c3fded425b81a180b2b8ec31a837':raise RuntimeError('sync archive hash mismatch')
 url='https://github.com/anyproto/tantivy-go/releases/download/v1.0.6/darwin-arm64.tar.gz'
 dep=base/'darwin-arm64-v1.0.6.tar.gz'
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Pinkha-native-qualified-input-recovery'}),timeout=35) as src,dep.open('xb') as dst:
  count=0
  while True:
   buf=src.read(1024*1024)
   if not buf:break
   count+=len(buf)
   if count>64<<20:raise RuntimeError('pinned archive exceeds bounded recovery size')
   dst.write(buf)
 if sha(dep)!='f0e4fa9bdca31da3b115db4fbe6689c5d6cab771be8f9468e5309c818b3f8add':raise RuntimeError('pinned original release digest mismatch')
 with tarfile.open(dep,'r:gz') as t:
  libs=[m for m in t.getmembers() if pathlib.PurePosixPath(m.name).name=='libtantivy_go.a' and m.isfile()]
  if len(libs)!=1:raise RuntimeError('single native static archive required')
  data=t.extractfile(libs[0]).read()
 if hashlib.sha256(data).hexdigest()!='506128732fae00d9b66ea11262b9e99bf5376a3ae4eaafae2a54770362d680fa':raise RuntimeError('original static library mismatch')
 orig=base/'original-libtantivy_go.a';orig.write_bytes(data)
 helper=pathlib.Path('/mnt/development/projects/evidence/migration-final-20261125/llvm-native-bitcode-tools/strip_embedded_llvm.py')
 if sha(helper)!='7b398498217ed6c25060892b9fe06e8e6baea507572a97e8666fc7c688f2488b':raise RuntimeError('qualified transformation helper changed')
 cmd=['python3',str(helper),'--llvm-objcopy',str(helper.parent/'llvm-objcopy'),'--input',str(orig),'--output',str(base/'native-libtantivy_go.a'),'--expected-input-sha256',sha(orig),'--receipt',str(base/'darwin-transform.json')]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
 save(base/'transform-command.json',{'command':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode:raise RuntimeError('exact pinned native transform failed')
 if sha(base/'native-libtantivy_go.a')!='30c4bc974615e03575c2d1f796ff594f2d0a0f7dd21e5b97ffbd836c99c31788':raise RuntimeError('recovered transformed library differs')
 record.update(status='INPUTS_RECOVERED_NOT_TESTED',nativeSourceFiles=len(members),baselineArchiveSHA256=sha(archive),fixedCoreSHA256=hashlib.sha256(fixedRaw).hexdigest(),originalDependencySHA256=sha(dep),nativeLibrarySHA256=sha(base/'native-libtantivy_go.a'),sourceRuntimeTests=0)
except BaseException as e:
 record.update(status='FAIL',errorType=type(e).__name__,error=str(e));raise
finally:
 record['finished']=time.time();save(base/'input-recovery.json',record);print(json.dumps(record),flush=True)
