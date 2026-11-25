import pathlib,subprocess,json,hashlib,tarfile,gzip,io,copy,ast
w=pathlib.Path('/mnt/development/projects/worktrees/anytype-native-d-completion-20261125')
t=w/'Tools/PinkhaDualEngineRuntime'
donor=pathlib.Path('/mnt/development/projects/worktrees/anytype-heart-source-capture-bridge-20261125')
g=['git','-c','safe.directory='+str(donor),'-C',str(donor)]
old_sha='70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683'
base='a2916b27eaa16fc291f438fe620b3d09bc0a85e0'; new='5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5'
sha=lambda x:hashlib.sha256(x).hexdigest()
old_raw=(t/'source-manifest.json').read_bytes();assert sha(old_raw)==old_sha
m=json.loads(old_raw);archive=json.loads((t/'source-archive.json').read_text())
assert subprocess.check_output(g+['rev-parse','HEAD'],text=True).strip()==new
assert not subprocess.check_output(g+['status','--porcelain'],text=True).strip()
delta=[x.split('\t') for x in subprocess.check_output(g+['diff','--name-status',base,new],text=True).splitlines()]
assert len(delta)==8 and sorted(x[0] for x in delta)==['A']*3+['M']*5
replacements={};review=[]
for kind,path in delta:
 name='heart/'+path
 content=subprocess.check_output(g+['show',new+':'+path])
 if kind=='M':
  original=subprocess.check_output(g+['show',base+':'+path])
  assert m['files'][name]=={'bytes':len(original),'sha256':sha(original)},name
  old=m['files'][name]
 else:
  assert name not in m['files'];old=None
 replacements[name]=content
 m['files'][name]={'bytes':len(content),'sha256':sha(content)}
 review.append({'path':name,'kind':kind,'before':old,'after':m['files'][name]})
assert len(m['files'])==4855
m['heartCaptureBridgeCommit']=new
m['predecessorSourceManifestSHA256']=old_sha
m['nativeSourceAuthorityLogSHA256']='a014f77f3129e562627d172594e9344d9ba30b7f1a12b45f50b76115d91429ae'
m['nativeSourceAuthorityStatus']='REAL_NATIVE_COMPILED_DEFINITIONS_AND_CHECKPOINT_PASS_GOMOBILE_BINDING_AND_UI_PENDING'
m['nativeCapturedSwiftReaderLogSHA256']='848ae082fec6e17c7bcf92071a852a34bc21e1b9ed078f4306fe82106e1d8690'
raw=(json.dumps(m,sort_keys=True,indent=2)+'\n').encode();manifest_sha=sha(raw)
old_path=pathlib.Path(archive['archive']);assert sha(old_path.read_bytes())==archive['sha256']
out=old_path.parent/('native-source-'+manifest_sha[:12]+'.tar.gz');assert not out.exists()
seen=set();oldm=json.loads(old_raw)
with old_path.open('rb') as original,tarfile.open(fileobj=original,mode='r:gz') as incoming,out.open('xb') as target,gzip.GzipFile(fileobj=target,mode='wb',filename='',mtime=0) as zipped,tarfile.open(fileobj=zipped,mode='w') as final:
 for member in incoming:
  assert member.isfile() and member.name not in seen;seen.add(member.name)
  content=incoming.extractfile(member).read()
  if member.name=='source-manifest.json':
   assert content==old_raw;content=raw
  else:
   assert oldm['files'][member.name]=={'bytes':len(content),'sha256':sha(content)},member.name
   content=replacements.pop(member.name,content)
  item=tarfile.TarInfo(member.name);item.mode=member.mode;item.mtime=0;item.size=len(content);item.uid=0;item.gid=0
  final.addfile(item,io.BytesIO(content))
 for name,content in sorted(replacements.items()):
  assert name not in oldm['files']
  item=tarfile.TarInfo(name);item.mode=0o644;item.mtime=0;item.size=len(content);item.uid=0;item.gid=0
  final.addfile(item,io.BytesIO(content))
assert seen==set(oldm['files'])|{'source-manifest.json'}
actual={}
with tarfile.open(out,'r:gz') as check:
 for member in check:
  assert member.isfile() and member.name not in actual
  content=check.extractfile(member).read()
  actual[member.name]={'bytes':len(content),'sha256':sha(content)}
assert actual=={**m['files'],'source-manifest.json':{'bytes':len(raw),'sha256':manifest_sha}}
new_archive={**archive,'archive':str(out),'bytes':out.stat().st_size,'sha256':sha(out.read_bytes()),'manifestSHA256':manifest_sha,'sourceFiles':len(m['files']),'heartVersion':'pinkha-dual-runtime-v1-'+manifest_sha,'anyVersion':'v0.5.0-pinkha.dual.1-'+manifest_sha,'qualification':'NATIVE_COMPILED_DEFINITION_SOURCE_AND_READER_QUALIFIED_COMBINED_APPLE_BUILD_PENDING'}
proof=w/'docs/validation/20261125-dual-engine-compiled-source';proof.mkdir()
(proof/'source-delta.json').write_text(json.dumps({'status':'PASS_EXACT_SOURCE_COMPOSITION_NOT_APPLE_BUILD','predecessorManifestSHA256':old_sha,'predecessorArchiveSHA256':archive['sha256'],'heartDonorBase':base,'heartDonorCommit':new,'changes':review,'sourceFiles':len(m['files']),'unchangedSourceFiles':len(oldm['files'])-5,'nativeModuleFilesChanged':False,'fullPage154OverlayPreserved':True,'newManifestSHA256':manifest_sha,'newArchive':new_archive},sort_keys=True,indent=2)+'\n')
(proof/'compose-source-original.py').write_bytes(pathlib.Path(__file__).read_bytes())
(t/'source-manifest.json').write_bytes(raw)
(t/'source-archive.json').write_text(json.dumps(new_archive,sort_keys=True,indent=2)+'\n')
p=t/'build_apple.py';s=p.read_text();assert s.count(old_sha)==1;assert s.count(archive['sha256'])==1
p.write_text(s.replace(old_sha,manifest_sha).replace(archive['sha256'],new_archive['sha256']))
for name in ['Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift','Modules/PinkhaKit/Sources/PinkhaKit/Torah/T5NativeRelatedLookupCapability.swift']:
 p=w/name;s=p.read_text();assert s.count(old_sha)==1;p.write_text(s.replace(old_sha,manifest_sha))
print(json.dumps({'manifestSHA256':manifest_sha,'archive':new_archive,'delta':review,'proof':str(proof)},indent=2))
