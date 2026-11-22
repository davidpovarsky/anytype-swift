from pathlib import Path,PurePosixPath
import subprocess,hashlib,json,datetime,io,os,concurrent.futures
packet=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\candidate-v4')
out=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v4-root-source-review')
assert not out.exists();out.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,value):
 (out/name).write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
ib=(packet/'SOURCE_REVIEW_INDEX.json').read_bytes();mb=(packet/'SOURCE_MANIFEST.json').read_bytes()
assert sha(ib)=='64d7121cbf5b7b687c1d53df2d7206fb35dab979db788fbefa50e7618f2ba0d9'
assert sha(mb)=='dc6bf97b2d1ff3509504517ccfe7894f20c30d46765e8c81ad061308c863cb58'
index=json.loads(ib);manifest=json.loads(mb)
items=index['files'];assert len(items)==133
seen=set();total=0
for item in items:
 name=item['path'];p=PurePosixPath(name)
 assert not p.is_absolute() and '..' not in p.parts and '\\' not in name and name not in seen
 seen.add(name);f=packet/name;assert f.is_file() and not f.is_symlink()
 b=f.read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256'],name
 total+=len(b)
assert total==4176863
refs=manifest['review_inputs'];assert len(refs)==108
local={'anyproto/anytype-heart':Path(r'C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122'),
 'davidpovarsky/anytype-swift':Path(r'C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122')}
remote=sorted({(x['repository'],x['commit']) for x in refs if x['repository'] not in local})
assert remote==[('anyproto/any-store','ebdcd277c3188538fbbc29a2b2ddbdf5f39cbe1d'),('anyproto/any-sync','5d71ccad5db77997df2d2426011ebae4e7600d98')]
env=dict(os.environ)
for key in ['GEMINI_API_KEY','OTZARIA_HANLIN_LIVE_API_KEY','OTZARIA_LIVE_GEMINI_API_KEY']:env.pop(key,None)
def fetch_tree(pair):
 repo,commit=pair
 p=subprocess.run(['gh','api','repos/'+repo+'/git/trees/'+commit+'?recursive=1'],env=env,capture_output=True,timeout=60)
 assert p.returncode==0,(repo,p.stderr.decode(errors='replace')[:1000])
 j=json.loads(p.stdout);assert j['truncated'] is False
 name=repo.split('/')[-1]+'.immutable-tree.json';(out/name).write_bytes(p.stdout)
 return pair,{'tree':{v['path']:v for v in j['tree']},'raw_sha256':sha(p.stdout),'raw_file':name,'tree_sha':j['sha']}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:trees=dict(pool.map(fetch_tree,remote))
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
 verified.append({'repository':item['repository'],'commit':item['commit'],'path':item['path'],'git_blob':blob,'sha256':sha(data),'bytes':len(data),'method':'independently fetched fixed-commit GitHub tree plus exact Git blob identity'})
assert len(verified)==108
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
receipt={'schema':1,'status':'PASS_INDEPENDENT_FROZEN_V4_SOURCE_INVENTORY_ONLY','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(mb),'index_sha256':sha(ib),'payload_count':133,'payload_bytes':total,'original_inputs_verified':108,'originals':verified,'candidate_files':manifest['candidate'],'remote_commit_trees':[{'repository':r,'commit':c,**{k:v for k,v in data.items() if k!='tree'}} for (r,c),data in trees.items()],'prior_v3_preserved':True,'r14_original_verified_not_applied':True,'compiled_dependency_closure':'not yet produced','new_test_executions':0,'native_calls':0,'review_scope':'Root read complete four observer/snapshot/ACL/replay files; native independently reviewed strict source.go. This receipt verifies immutable source inventory and exact candidate bytes, not Go compilation or native runtime acceptance.','executed_script_sha256':sha(Path(__file__).read_bytes())}
write('ROOT_SOURCE_REVIEW.json',receipt)
(out/'EXECUTED_ROOT_SOURCE_REVIEW.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'status':receipt['status'],'receipt':str(out/'ROOT_SOURCE_REVIEW.json'),'receipt_sha256':sha((out/'ROOT_SOURCE_REVIEW.json').read_bytes()),'payloads':133,'payload_bytes':total,'original_inputs':108,'candidate_files':len(manifest['candidate']),'remote_tree_reads':2,'tests':0}))
