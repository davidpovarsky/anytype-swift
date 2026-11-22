import pathlib,json,hashlib,subprocess,base64,datetime,concurrent.futures,shutil
anchor=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-space-authority-20261122')
heart=pathlib.Path(r'C:\Users\DAVID\Code\anytype-heart-chatgpt-t2-20261118')
repo=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122')
branch='codex/otzaria-original-native-annotation-integration-20261122'
base='d33a41338bd0a56326fd02c05977c10d1c4c7baa'; meta='18ac6d39dfe76b12e5dead9627c831c6a88d073c'; audit='a432310c2c86871321c4c6939846a5c713b753c0'; baseline='b854e7f3f59690134bcabdef88527b61517d5ab5'
mp='docs/pinkha/torah-integration/production-native-metadata-20261122'; ap='docs/pinkha/torah-integration/native-annotation-schema-audit-20261122'
sha=lambda b:hashlib.sha256(b).hexdigest()
def need(v,m):
 if not v:raise AssertionError(m)
def git(r,*a):return subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.longpaths=true',*a],cwd=r,timeout=90)
def blob(r,ref,path):return git(r,'show',ref+':'+path)
def batch(r,requests):
 x=subprocess.run(['git','cat-file','--batch'],cwd=r,input=(''.join(q+'\n' for q in requests)).encode(),capture_output=True,check=True,timeout=90)
 out=[];pos=0
 for q in requests:
  e=x.stdout.index(b'\n',pos);h=x.stdout[pos:e].decode().split();need(len(h)==3 and h[1]=='blob','batch '+q)
  size=int(h[2]);pos=e+1;b=x.stdout[pos:pos+size];pos+=size;need(x.stdout[pos:pos+1]==b'\n','delimiter');pos+=1;out.append((h[0],b))
 need(pos==len(x.stdout),'batch remainder');return out
need(not repo.exists(),'worktree exists')
need(subprocess.run(['git','show-ref','--verify','refs/heads/'+branch],cwd=anchor,capture_output=True).returncode!=0,'branch exists')
mib=blob(anchor,meta,mp+'/EVIDENCE_INDEX.json');aib=blob(anchor,audit,ap+'/AUDIT_INDEX.json')
need(sha(mib)=='1c259ce9f311ad5cb00fce882961bba95dc407ace0b3f34d12e3079192fb7cd3','metadata index')
need(sha(aib)=='c12c919fb688f93fb89976684adac88b559470abdb89e1d155ea5c7433a1d7ce','audit index')
mi=json.loads(mib);ai=json.loads(aib);need(len(mi['payloads'])==80 and len(ai['files'])==5,'packet counts')
checks=[(meta,mp,r) for r in mi['payloads']]+[(audit,ap,r) for r in ai['files']]
results=batch(anchor,[ref+':'+prefix+'/'+r['path'] for ref,prefix,r in checks])
for (ref,prefix,r),(oid,b) in zip(checks,results):
 need(len(b)==r['bytes'] and sha(b)==r['sha256'],'retained payload '+prefix+'/'+r['path'])
sources=json.loads(blob(anchor,audit,ap+'/SOURCE_INDEX.json'))['sources'];need(len(sources)==47,'audit source count')
verified=[]
for name,rp in [('anyproto/anytype-heart',heart),('davidpovarsky/anytype-swift',anchor)]:
 subset=[s for s in sources if s['repository']==name];need(len(subset)==20,'source repo count')
 for row,(oid,b) in zip(subset,batch(rp,[s['commit']+':'+s['path'] for s in subset])):
  need(oid==row['git_blob'] and len(b)==row['bytes'] and sha(b)==row['sha256'],'local audit source '+row['path'])
  verified.append({'repository':name,'commit':row['commit'],'path':row['path'],'gitBlob':oid,'sha256':sha(b),'bytes':len(b),'method':'immutable local Git blob'})
remote=[s for s in sources if s['repository']=='anyproto/any-sync'];need(len(remote)==7,'public source count')
def fetch(s):
 url='repos/'+s['repository']+'/contents/'+s['path']+'?ref='+s['commit']
 p=subprocess.run(['gh','api',url],capture_output=True,check=True,timeout=60)
 data=json.loads(p.stdout);need(data['encoding']=='base64','public encoding');b=base64.b64decode(data['content'])
 oid=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()
 need(data['sha']==oid==s['git_blob'] and len(b)==s['bytes'] and sha(b)==s['sha256'],'public source '+s['path'])
 return {'repository':s['repository'],'commit':s['commit'],'path':s['path'],'gitBlob':oid,'sha256':sha(b),'bytes':len(b),'method':'original GitHub contents at exact commit, SHA1/SHA256'}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: verified.extend(list(pool.map(fetch,remote)))
product='Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift';attr='Anytype/Sources/Pinkha/Torah/Annotations/.gitattributes'
pb=blob(anchor,meta,product);need(len(pb)==8112 and sha(pb)=='21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5','published metadata product')
provisional=json.loads(blob(anchor,audit,ap+'/DESCRIPTOR_INPUT.json'))
need(provisional['status']=='PROVISIONAL_UNCOMMITTED_INPUT_AT_AUDIT_READ' and provisional['raw_sha256']==sha(pb),'historical descriptor binding')
prior_product=[x for x in git(anchor,'diff','--name-only',baseline,base,'--','Anytype','Modules','Resources','Scripts','.github').decode().splitlines() if x]
need(len(prior_product)==2 and {pathlib.PurePosixPath(x).name for x in prior_product}=={'ParticipantsStorage.swift','SpaceViewsStorage.swift'},'authority product delta')
expected={'ParticipantsStorage.swift':'7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1','SpaceViewsStorage.swift':'f1570f8cff28d87152ea455ded6bc0bdfeb729e0beb3a70e3a47fb06b4710a57'}
for p in prior_product:need(sha(blob(anchor,base,p))==expected[pathlib.PurePosixPath(p).name],'authority source')
oldpackets=['docs/pinkha/torah-integration/production-annotation-20261122','docs/pinkha/torah-integration/production-space-authority-20261122','docs/pinkha/torah-integration/production-space-composition-audit-20261122']
trees={p:git(anchor,'rev-parse',base+':'+p).decode().strip() for p in oldpackets}
git(anchor,'worktree','add','-b',branch,str(repo),base)
need(git(repo,'rev-parse','HEAD').decode().strip()==base and not git(repo,'status','--porcelain=v1').strip(),'new checkout')
git(repo,'merge','--no-ff','--no-commit',meta)
changed=git(repo,'diff','--cached','--name-only',base).decode().splitlines()
need(changed and all(p in [product,attr] or p.startswith(mp+'/') for p in changed),'metadata merge scope')
git(repo,'commit','-m','Merge verified native annotation metadata component')
metadata_merge=git(repo,'rev-parse','HEAD').decode().strip()
need(git(repo,'rev-list','--parents','-n','1',metadata_merge).decode().split()[1:]==[base,meta],'metadata parents')
git(repo,'merge','--no-ff','--no-commit',audit)
changed=git(repo,'diff','--cached','--name-only',metadata_merge).decode().splitlines()
need(len(changed)==6 and all(p.startswith(ap+'/') for p in changed),'schema audit merge scope')
git(repo,'commit','-m','Merge immutable native annotation schema audit')
audit_merge=git(repo,'rev-parse','HEAD').decode().strip()
need(git(repo,'rev-list','--parents','-n','1',audit_merge).decode().split()[1:]==[metadata_merge,audit],'audit parents')
final_product=git(repo,'diff','--name-only',baseline,'HEAD','--','Anytype','Modules','Resources','Scripts','.github').decode().splitlines()
need(set(final_product)==set(prior_product+[product,attr]),'final product delta')
for p in prior_product:need(blob(repo,'HEAD',p)==blob(anchor,base,p),'authority bytes changed')
need(blob(repo,'HEAD',product)==pb,'metadata bytes changed')
for ref,prefix,r in checks:need(blob(repo,'HEAD',prefix+'/'+r['path'])==blob(anchor,ref,prefix+'/'+r['path']),'merged payload changed')
need(blob(repo,'HEAD',mp+'/EVIDENCE_INDEX.json')==mib and blob(repo,'HEAD',ap+'/AUDIT_INDEX.json')==aib,'merged index changed')
for p,want in trees.items():need(git(repo,'rev-parse','HEAD:'+p).decode().strip()==want,'passed packet tree changed')
for p in ['Modules','Resources','Scripts','.github']:need(git(repo,'rev-parse','HEAD:'+p)==git(anchor,'rev-parse',base+':'+p),'shared tree changed '+p)
receipt_rel='docs/pinkha/torah-integration/native-annotation-component-integration-20261122'
e=repo/receipt_rel;need(not e.exists(),'integration proof exists');e.mkdir()
proof={'schema':1,'status':'VERIFIED_COMPONENT_INTEGRATION_ONLY','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':base,'metadataEvidence':meta,'metadataSource':'032a8320178ca702ed05327de168cbc2578f11eb','metadataMerge':metadata_merge,'auditSource':audit,'auditMerge':audit_merge,'metadataPayloadsVerified':80,'auditPayloadsVerified':5,'totalPayloadsAndTwoIndexes':87,'metadataIndexSHA256':sha(mib),'auditIndexSHA256':sha(aib),'metadataProductSHA256':sha(pb),'immutableAuditSourcesVerified':len(verified),'descriptorBinding':'Historical provisional audit input is byte-identical to published032a; old provenance is unchanged','preservedPassedPacketTrees':trees,'productPathsChangedFromB854':final_product,'reusedResults':{'metadata26':'Actual Windows SwiftTesting26 PASS at21321/18ac; complete previously verified exact dependency closure preserved','participant16plus1':'Original source-bound results retained unchanged; no replay','space22':'Original source-bound results retained unchanged; no replay'},'execution':{'tests':0,'builds':0,'nativeCalls':0,'schemaWrites':0,'ciDispatches':0},'openGates':['SourceBinding composition candidate still owned separately by author','Native schema observer/ensure and typed transport not integrated','Held-read callback and real body verifier not integrated','No writer, mapping, receipt or ACK accepted','No full Apple/Native116/Release114/StageB/device acceptance'],'scriptSHA256':sha(pathlib.Path(__file__).read_bytes())}
(e/'INTEGRATION.json').write_bytes((json.dumps(proof,indent=2)+'\n').encode())
(e/'AUDIT_SOURCE_VERIFICATION.json').write_bytes((json.dumps({'schema':1,'sources':verified},indent=2)+'\n').encode())
(e/'README.md').write_bytes(('# Native annotation component integration\n\nThis branch joins the original Participant/Space components at d33 with the published metadata source032a/evidence18ac and the immutable schema audit a432. Both merges retain their exact Git parents.\n\nAll80 metadata payloads,5 schema-audit payloads and both indexes are verified from immutable Git. All47 audit sources are independently bound to their exact historical commits. The audit provisional descriptor is byte-identical to the subsequently published source; historical provenance remains untouched.\n\nOnly three product Swift files differ from b854, plus the metadata file-specific CRLF preservation attribute. Original shared Modules/Resources/Scripts/workflows and the existing passed Participant/Space packets remain unchanged. No tests, builds, native calls, schema writes or CI were executed for these merges.\n\n[Integration receipt](INTEGRATION.json) defines retained component results and all open gates. This is not production runtime, schema, body, writer or full application acceptance. The author retains exclusive ownership of the separate in-progress SourceBinding composition worktree.\n').encode())
payloads=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(e.iterdir()) if p.is_file()]
(e/'INDEX.json').write_bytes((json.dumps({'schema':1,'payloads':payloads,'excludesSelf':True},indent=2)+'\n').encode())
git(repo,'add','--',receipt_rel);git(repo,'diff','--cached','--check')
git(repo,'commit','-m','docs: verify exact native annotation component integration')
head=git(repo,'rev-parse','HEAD').decode().strip();need(not git(repo,'status','--porcelain=v1').strip(),'dirty integration')
result={'status':'PASS','head':head,'branch':branch,'worktree':str(repo),'metadataMerge':metadata_merge,'auditMerge':audit_merge,'sourceInputsVerified':47,'payloadsAndIndexesVerified':87,'proofIndexSHA256':sha((e/'INDEX.json').read_bytes()),'productDelta':final_product,'testsRun':0,'nativeCalls':0}
p=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\native_annotation_integration_result.json');need(not p.exists(),'result already exists');p.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
