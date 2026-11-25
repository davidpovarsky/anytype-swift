import pathlib,json,hashlib,tarfile,os,subprocess,shutil
root=pathlib.Path('/Users/m1/builds/pinkha-c-source-bridge-limits-20261125')
expected=json.loads("{\"contract\":\"pinkha-native-bridge-qualification-input-transfer-v1\",\"remote\":\"/Users/m1/builds/pinkha-c-source-bridge-limits-20261125\",\"files\":{\"heart-baseline-d59568f9.tar.gz\":{\"bytes\":19654810,\"sha256\":\"8cefd6a0d741d9c003c6defc1be20c52f4b423432a6a9f712d96c80e6cd085d8\"},\"baseline-source.json\":{\"bytes\":674209,\"sha256\":\"c21b6b1b83daf0dac6a85555c1bbb2c70a348ddfbcc7bd2bbee072b582e502bd\"},\"fixed-source.json\":{\"bytes\":674226,\"sha256\":\"c8138afcb70a01d8280927ec1e98c3f8e51d00807a8e14c9119b4d88847c28b8\"},\"fixed-core-source.go\":{\"bytes\":4903,\"sha256\":\"d8f062bbec1e7bfc626a21ed6048140809fc8cca177e0c2dbee9a8ffa1f8573d\"},\"darwin-arm64-v1.0.6.tar.gz\":{\"bytes\":14997958,\"sha256\":\"f0e4fa9bdca31da3b115db4fbe6689c5d6cab771be8f9468e5309c818b3f8add\"},\"original-libtantivy_go.a\":{\"bytes\":42087136,\"sha256\":\"506128732fae00d9b66ea11262b9e99bf5376a3ae4eaafae2a54770362d680fa\"},\"native-libtantivy_go.a\":{\"bytes\":33624816,\"sha256\":\"30c4bc974615e03575c2d1f796ff594f2d0a0f7dd21e5b97ffbd836c99c31788\"},\"darwin-transform.json\":{\"bytes\":1421,\"sha256\":\"ddb2a63b58dcdd1b8dfa4ccae73fa023c46f349c8ae350dcfe753664e55314c6\"},\"input-recovery.json\":{\"bytes\":723,\"sha256\":\"92aff14e7d4f6902ee379535d572b221365b2901f60cd64a2eadfe2a36e37a46\"},\"any-sync-native-witness-source.tar.gz\":{\"bytes\":846847,\"sha256\":\"481b3aa9aeace3de01e3b184b3965ce57a50c3fded425b81a180b2b8ec31a837\"},\"any-sync-native-witness-source.json\":{\"bytes\":103020,\"sha256\":\"38931d8fc69d0c35109cfbb17d5276dda3ca6800892a70cbd628773f022d7af4\"}},\"newRuntimeTests\":0}")
incoming=root/'incoming'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,row in expected['files'].items():
 p=incoming/name
 if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('transferred input differs: '+name)
(root/'transfer.json').write_text(json.dumps(expected,indent=2)+'\n')
src=root/'source';src.mkdir(mode=0o700,exist_ok=False)
def verify(base,meta):
 observed={}
 for path in base.rglob('*'):
  if path.is_file() or path.is_symlink():
   relative=path.relative_to(base).as_posix()
   data=os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
   observed[relative]=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 expected={r['path']:r['gitBlob'] for r in meta['files']}
 if observed!=expected:raise RuntimeError('full source closure differs')
 return {'files':len(observed),'manifestSHA256':hashlib.sha256(json.dumps(observed,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
def extract(archive,base,meta):
 base.mkdir(mode=0o700,exist_ok=False)
 rows={r['path']:r for r in meta['files']};seen=set()
 with tarfile.open(archive,'r:gz') as tf:
  for m in tf.getmembers():
   if m.isdir():continue
   if m.name not in rows or m.name in seen or pathlib.PurePosixPath(m.name).is_absolute() or '..' in pathlib.PurePosixPath(m.name).parts:raise RuntimeError('source archive path rejected')
   seen.add(m.name);q=base/m.name;q.parent.mkdir(parents=True,exist_ok=True)
   mode=rows[m.name].get('gitMode',rows[m.name].get('mode'))
   if m.isfile() and mode in ['100644','100755']:
    data=tf.extractfile(m).read();q.write_bytes(data);os.chmod(q,0o755 if mode=='100755' else 0o644)
   elif m.issym() and mode=='120000':
    target=pathlib.PurePosixPath(m.linkname)
    if target.is_absolute():raise RuntimeError('absolute source symlink')
    os.symlink(m.linkname,q)
    if not q.resolve().is_relative_to(base.resolve()):raise RuntimeError('escaping source symlink')
   else:raise RuntimeError('source file kind rejected')
 if seen!=set(rows):raise RuntimeError('incomplete source archive')
 return verify(base,meta)
baseline=json.loads((incoming/'baseline-source.json').read_text());fixed=json.loads((incoming/'fixed-source.json').read_text());sync=json.loads((incoming/'any-sync-native-witness-source.json').read_text())
baselineProof=extract(incoming/'heart-baseline-d59568f9.tar.gz',src/'baseline',baseline)
syncProof=extract(incoming/'any-sync-native-witness-source.tar.gz',src/'any-sync',sync)
r=subprocess.run(['/bin/cp','-cRp',str(src/'baseline'),str(src/'fixed')],capture_output=True,text=True,timeout=45)
if r.returncode:raise RuntimeError(r.stderr)
(src/'fixed/core/pinkha_native_source_capture.go').write_bytes((incoming/'fixed-core-source.go').read_bytes())
fixedProof=verify(src/'fixed',fixed)
lib=root/'native-libs';lib.mkdir(mode=0o700,exist_ok=False)
shutil.copyfile(incoming/'native-libtantivy_go.a',lib/'libtantivy_go.a')
originalMod=(src/'baseline/go.mod').read_bytes()
originalSum=(src/'baseline/go.sum').read_bytes()
for name in ['baseline','fixed']:
 if (src/name/'go.mod').read_bytes()!=originalMod or (src/name/'go.sum').read_bytes()!=originalSum:raise RuntimeError('original module pins differ')
 (root/(name+'.mod')).write_bytes(originalMod+b'\nreplace github.com/anyproto/any-sync => '+str(src/'any-sync').encode()+b'\n')
 (root/(name+'.sum')).write_bytes(originalSum)
go='/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go'
version=subprocess.run([go,'version'],capture_output=True,text=True,timeout=20)
if version.returncode or version.stdout.strip()!='go version go1.27.4 darwin/arm64':raise RuntimeError('exact native toolchain differs')
checks={}
for label,p in [('original',incoming/'original-libtantivy_go.a'),('native',lib/'libtantivy_go.a')]:
 r=subprocess.run(['/usr/bin/xcrun','nm','--no-llvm-bc','-g',str(p)],capture_output=True,text=True,timeout=45)
 if r.returncode:raise RuntimeError('native symbol reader failed')
 lines=sorted(v for v in r.stdout.splitlines() if v and not v.endswith(':') and not v.startswith('Archive :'))
 checks[label]={'rows':len(lines),'sha256':hashlib.sha256(('\n'.join(lines)+'\n').encode()).hexdigest()}
if checks['original']!=checks['native']:raise RuntimeError('native symbol census differs')
arch=subprocess.run(['/usr/bin/xcrun','lipo','-info',str(lib/'libtantivy_go.a')],capture_output=True,text=True,timeout=20)
if arch.returncode or 'arm64' not in arch.stdout:raise RuntimeError('wrong host architecture')
record={'contract':'pinkha-native-bridge-host-source-admission-v1','status':'PASS_SOURCE_ADMISSION_NOT_RUNTIME','baseline':baselineProof,'fixed':fixedProof,'sync':syncProof,'baselineCommit':baseline['source'],'fixedCommit':fixed['source'],'syncCommit':sync['source'],'nativeLibrarySHA256':sha(lib/'libtantivy_go.a'),'nativeSymbolCensus':checks,'toolchain':version.stdout.strip(),'originalGoModSHA256':hashlib.sha256(originalMod).hexdigest(),'originalGoSumSHA256':hashlib.sha256(originalSum).hexdigest(),'freeBytes':shutil.disk_usage(root).free,'newRuntimeTests':0}
(root/'source-admission.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
