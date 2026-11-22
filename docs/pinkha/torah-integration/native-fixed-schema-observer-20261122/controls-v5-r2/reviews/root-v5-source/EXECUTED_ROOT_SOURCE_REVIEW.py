from pathlib import Path,PurePosixPath
import subprocess,hashlib,json,datetime,io,os,concurrent.futures
packet=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\candidate-v5')
out=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-root-source-review')
assert not out.exists();out.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,value):
 (out/name).write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
ib=(packet/'SOURCE_REVIEW_INDEX.json').read_bytes();mb=(packet/'SOURCE_MANIFEST.json').read_bytes()
assert sha(ib)=='3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581'
assert sha(mb)=='c091fa3696f8b3f2610997aed65c988010529c59caeac3d53a47c1d3e028ac4d'
index=json.loads(ib);manifest=json.loads(mb)
items=index['files'];assert len(items)==138
seen=set();total=0
for item in items:
 name=item['path'];p=PurePosixPath(name)
 assert not p.is_absolute() and '..' not in p.parts and '\\' not in name and name not in seen
 seen.add(name);f=packet/name;assert f.is_file() and not f.is_symlink()
 b=f.read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256'],name
 total+=len(b)
assert total==4198338
refs=manifest['review_inputs'];assert len(refs)==113
local={'anyproto/anytype-heart':Path(r'C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122'),
 'davidpovarsky/anytype-swift':Path(r'C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122')}
remote=sorted({(x['repository'],x['commit']) for x in refs if x['repository'] not in local})
assert remote==[('anyproto/any-store','ebdcd277c3188538fbbc29a2b2ddbdf5f39cbe1d'),('anyproto/any-sync','5d71ccad5db77997df2d2426011ebae4e7600d98')]
prior_root=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v4-root-source-review')
old_receipt=(prior_root/'ROOT_SOURCE_REVIEW.json').read_bytes()
assert sha(old_receipt)=='b4e08f42d4863fe89a68c2da16040053af79adaad03f581e99d0fca43861ab86'
prior_tree_records={(x['repository'],x['commit']):x for x in json.loads(old_receipt)['remote_commit_trees']}
trees={}
for pair in remote:
 rec=prior_tree_records[pair];raw=(prior_root/rec['raw_file']).read_bytes()
 assert sha(raw)==rec['raw_sha256']
 j=json.loads(raw);assert j['truncated'] is False and j['sha']==rec['tree_sha']
 (out/rec['raw_file']).write_bytes(raw)
 trees[pair]={'tree':{v['path']:v for v in j['tree']},'raw_sha256':sha(raw),'raw_file':rec['raw_file'],'tree_sha':j['sha'],'provenance':'unchanged independently fetched fixed-commit tree retained in original root V4 review'}
verified=[]
for repository,worktree in local.items():
 subset=[x for x in refs if x['repository']==repository]
 specs=[x['commit']+':'+x['path'] for x in subset]
 p=subprocess.run(['git','-c','core.autocrlf=false','cat-file','--batch'],cwd=worktree,input=('\n'.join(specs)+'\n').encode(),capture_output=True,timeout=60)
 assert p.returncode==0,p.stderr
 stream=io.BytesIO(p.stdout)
 for item,spec in zip(subset,specs):
  header=stream.readline().decode().strip().split();assert len(header)==3 and header[1]=='blob',(spec,header)
  data=stream.read(int(header[2]));assert stream.read(1)==b'\n'
  frozen=(packet/item['retained_path']).read_bytes()
  assert data==frozen and header[0]==item['git_blob'] and sha(data)==item['sha256'] and len(data)==item['bytes'],spec
  verified.append({'repository':repository,'commit':item['commit'],'path':item['path'],'git_blob':header[0],'sha256':sha(data),'bytes':len(data),'method':'actual local immutable Git object'})
 assert stream.read()==b''
for item in refs:
 if item['repository'] in local:continue
 rec=trees[(item['repository'],item['commit'])]['tree'][item['path']]
 assert rec['type']=='blob' and rec['sha']==item['git_blob']
 data=(packet/item['retained_path']).read_bytes()
 blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert blob==rec['sha'] and sha(data)==item['sha256'] and len(data)==item['bytes']
 verified.append({'repository':item['repository'],'commit':item['commit'],'path':item['path'],'git_blob':blob,'sha256':sha(data),'bytes':len(data),'method':'retained independently fetched fixed-commit GitHub tree plus exact Git blob identity'})
assert len(verified)==113
for item in manifest['candidate']:
 data=(packet/item['retained_path']).read_bytes()
 assert (Path(manifest['worktree'])/item['path']).read_bytes()==data
 assert sha(data)==item['sha256'] and len(data)==item['bytes']
r14=manifest['r14'];p=subprocess.run(['git','show',r14['source_commit']+':'+r14['path']],cwd=local['davidpovarsky/anytype-swift'],capture_output=True,timeout=30)
assert p.returncode==0 and sha(p.stdout)==r14['sha256']
assert manifest['r14_applied'] is False and manifest['tests']==0 and manifest['builds']==0
prior=Path(manifest['prior_v3']['path'])
assert sha((prior/'SOURCE_MANIFEST.json').read_bytes())==manifest['prior_v3']['manifest_sha256']
assert sha((prior/'INDEX.json').read_bytes())==manifest['prior_v3']['index_sha256']
v4=Path(manifest['prior_v4']['path'])
assert sha((v4/'SOURCE_MANIFEST.json').read_bytes())==manifest['prior_v4']['manifest_sha256']
assert sha((v4/'SOURCE_REVIEW_INDEX.json').read_bytes())==manifest['prior_v4']['index_sha256']
prior_index=json.loads((v4/'SOURCE_REVIEW_INDEX.json').read_bytes())
assert len(prior_index['files'])==133
for x in prior_index['files']:
 raw=(v4/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha(raw)==x['sha256']
assert (packet/'candidate/core/block/source/sourceimpl/source.go').read_bytes()==(v4/'candidate/core/block/source/sourceimpl/source.go').read_bytes()
receipt={'schema':1,'status':'PASS_INDEPENDENT_FROZEN_V5_SOURCE_INVENTORY_ONLY','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(mb),'index_sha256':sha(ib),'payload_count':138,'payload_bytes':total,'original_inputs_verified':113,'originals':verified,'candidate_files':manifest['candidate'],'remote_commit_trees':[{'repository':r,'commit':c,**{k:v for k,v in data.items() if k!='tree'}} for (r,c),data in trees.items()],'prior_v3_preserved':True,'prior_v4_preserved':True,'prior_v4_payloads_verified':133,'prior_v4_root_receipt_sha256':sha(old_receipt),'r14_original_verified_not_applied':True,'compiled_dependency_closure':'not yet produced','new_test_executions':0,'native_calls':0,'review_scope':'Root reused complete V4 four-file source read and independently reviewed full V4-to-V5 delta, exact original StateStorage and all original Space payload validation functions. Native strict source.go review still applies because its bytes are unchanged. This receipt verifies immutable source inventory and exact candidate bytes, not Go compilation or native runtime acceptance.','executed_script_sha256':sha(Path(__file__).read_bytes())}
write('ROOT_SOURCE_REVIEW.json',receipt)
(out/'EXECUTED_ROOT_SOURCE_REVIEW.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'status':receipt['status'],'receipt':str(out/'ROOT_SOURCE_REVIEW.json'),'receipt_sha256':sha((out/'ROOT_SOURCE_REVIEW.json').read_bytes()),'payloads':138,'payload_bytes':total,'original_inputs':113,'candidate_files':len(manifest['candidate']),'new_remote_tree_reads':0,'retained_original_remote_trees':2,'tests':0}))
