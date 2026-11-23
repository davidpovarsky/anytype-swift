import pathlib,json,hashlib,subprocess,stat,datetime,collections
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-local-tree-census-20261123')
N=pathlib.Path('/mnt/development/projects/worktrees/anytype-heart-local-tree-census-20261123')
D=pathlib.Path('/mnt/development/projects/evidence/local-tree-census-20261123')
A=D/'attempt1';B=D/'audit-only-attempt1';Q=W/'docs/validation/20261123-native-local-tree-census'
O=pathlib.Path('/mnt/development/projects/diagnostics/native-local-tree-census-root-review-20261123')
S='5d6ec4b42db00ec01737ea150b4e288be9ab3743';C='6195e74381a68c2cd8da54f262bb296e1f074c5a';NS='35c169e7a39e3dafc0a1281f56a1fe37fce57533'
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(p,h=None):
 b=p.read_bytes()
 if h:assert sha(b)==h,str(p)
 return b
def data(p,h=None):return json.loads(raw(p,h))
def blob(w,s,p):return subprocess.check_output(['git','show',s+':'+p],cwd=w,timeout=30)
q=data(Q/'qualification.json','5cd4d9f392859f79cb04dbd000138beefad13ddb33ad6725a2d3b84a90bdeacc')
copies=0
for rel,r in q['copied_originals'].items():
 a=raw(pathlib.Path(r['original']),r['sha256']);assert a==raw(Q/rel,r['sha256']) and len(a)==r['bytes'];copies+=1
assert copies==24
idx=data(Q/'artifact-index.json','eb41d1e556a0b0e9da945620239cd92176e04b453a8896ce27f9c6c8c9a1496f')
for rel,r in idx.items():assert len(raw(Q/rel,r['sha256']))==r['bytes']
build=data(A/'build.json','20836a217bcdfcafbb769efbe77c087a2525b3aa9607e3b2ede84533f38f249b')
execute=data(A/'execute.json','7890eb0eecf6ba580fe82f1d62a250db52a1cf7f7f3fc0f8c97cc121efa9dd58')
assert build['status']=='BUILD_PASS_EXECUTION_NOT_RUN' and execute['status']=='FAILED'
assert execute['error']=={'message':'private_pair_directory_mode','type':'RuntimeError'}
for r in (build,execute):
 assert r['controller_source_sha']==S and r['native_source_sha']==NS
 assert r['command']['returncode']==0 and r['command']['owned_process_group_absent'] is True
 for k in ('old_methods_executed','actual_new_interleaving_proofs'):assert r[k]==0
 for k in ('hasNativeSourceAdmission','permitsDestinationWrites','semanticIdentityCensusComplete','production_capability_issuer'):assert r[k] is False
assert len(raw(A/'products/local-tree-census.test',build['binary_sha256']))==25744136
sb=raw(A/'build-source-before.json')
for n in ('build-source-after.json','build-source-final.json','execute-source-before.json','execute-source-final.json'):assert raw(A/n)==sb,n
sources=json.loads(sb);assert sum(map(len,sources.values()))==42
for p,h in sources['native'].items():assert raw(N/p,h)==blob(N,NS,p)
for p,h in sources['controller'].items():assert sha(blob(W,S,p))==h
for p,h in sources['native_schema_dependencies'].items():raw(pathlib.Path(p),h)
deps=raw(A/'dependency-inputs-before.json')
for n in ('dependency-inputs-after-build.json','build-dependency-inputs-final.json','execute-dependency-inputs-final.json'):assert raw(A/n)==deps
dep=json.loads(deps);assert len(dep)==4045
for p,h in dep.items():raw(pathlib.Path(p),h)
events=[json.loads(l) for l in raw(A/'private/execution-original.jsonl').splitlines()]
safe=data(A/'safe-events.json')
assert [{k:e[k] for k in ('Time','Action','Package','Test','Elapsed') if k in e} for e in events]==safe
starts=[e['Test'] for e in events if e['Action']=='run' and 'Test' in e]
passes=[e['Test'] for e in events if e['Action']=='pass' and 'Test' in e]
assert len(starts)==len(passes)==len(set(starts))==5
assert sorted(starts)==sorted(passes)==sorted(q['qualified_native_starts'])==sorted(q['qualified_native_passes'])
for method in starts:
 assert next(i for i,e in enumerate(events) if e.get('Test')==method and e['Action']=='run') < next(i for i,e in enumerate(events) if e.get('Test')==method and e['Action']=='pass')
assert not [e for e in events if e['Action'] in ('fail','skip')]
assert all(e['Package']=='github.com/anyproto/anytype-heart/core/pinkha/localstorewitness' for e in events)
selected=json.loads(blob(W,S,'Tools/AnyEngineValidation/native_localstore_witness/census/source.json'))['selected_top_level_methods']
assert sorted(selected)==sorted(starts)
selector='-test.run=^('+'|'.join(selected)+')$'
assert selector in execute['command']['argv'] and '-test.count=1' in execute['command']['argv']
for rel in ('private/build-original.log','private/execution-original.jsonl'):
 command=data(A/(rel+'.command.json'));raw(A/rel,command['original_log_sha256'])
audit=data(B/'receipt.json','890ccd8a7a36c0fe83c3c13b3435b02f331a5f81f7e2d698bef9148075c4e489')
assert audit['status']=='PASS_AUDIT_ONLY_RETAINED_NATIVE_FIVE' and audit['original_execute_remains']=='FAILED'
assert audit['current_audit_source_sha']==C and audit['original_controller_source_sha']==S and audit['native_source_sha']==NS
assert audit['new_builds']==audit['new_native_methods_executed']==0 and not audit['chmod_performed']
assert raw(B/'source-before.json')==raw(B/'source-after.json')
assert raw(B/'private-metadata-before.json')==raw(B/'private-metadata-after.json')
prefix='Tools/AnyEngineValidation/native_localstore_witness/census/'
old=blob(W,S,prefix+'audit_private.py');current=raw(W/(prefix+'audit_private.py'))
a=b'stat.S_IMODE(census.parent.stat().st_mode) in {0o700, 0o2700}'
b=b'stat.S_IMODE(census.parent.stat().st_mode) == 0o700'
assert current.count(a)==1 and current.replace(a,b)==old
assert sha(old)=='915973cfad4f0587a8ddd8fd8d975160a300e41592cb2205fd40bcf2eea2855c'
# Independent length-frame/row/reference reader; never loads either production census or prior auditor.
def frames(buf):
 result=[];i=0
 while i<len(buf):
  assert i+8<=len(buf);n=int.from_bytes(buf[i:i+8],'big');i+=8
  assert n<=64*1024*1024 and i+n<=len(buf);result.append(buf[i:i+n]);i+=n
 assert i==len(buf);return result
class Reader:
 def __init__(self,b):self.f=frames(b);self.i=0
 def take(self):v=self.f[self.i];self.i+=1;return v
 def num(self,low=0,high=100000):
  b=self.take();assert len(b)==8;v=int.from_bytes(b,'big',signed=True);assert low<=v<=high;return v
 def done(self):assert self.i==len(self.f)
receipts=data(A/'safe-native-receipts.json');ap=data(B/'private-pairs-audit.json');assert ap==q['independent_audit_pairs']
pair_results={};witnesses={}
for cp in sorted((A/'private/fixtures').rglob('*.census.bin')):
 label=cp.name.removesuffix('.census.bin');assert label in receipts and label not in pair_results
 wp=cp.with_name(label+'.witness.bin')
 for p in (cp,wp):
  st=p.lstat();assert stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o600 and st.st_uid==1001
 par=cp.parent
 while par!=A/'private':
  st=par.lstat();assert stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) in (0o700,0o2700) and st.st_uid==1001
  par=par.parent
 wr=raw(wp);cr=raw(cp);pub=receipts[label]
 assert sha(wr)==pub['SourceWitnessSHA256'] and sha(cr)==pub['CensusSHA256'] and len(cr)==pub['PrivateBytes']
 v=Reader(wr)
 assert v.take()==b'pinkha-localstore-witness-v1' and v.take()==b'anyenc-v1.0.3-decoded-value-roundtrip-v1' and v.take()==b'owned-fixture-only-v1'
 nonce,space=v.take(),v.take();generation=v.num(1,2**63-1);nc=v.num(1,64);cols=[];source_rows=[]
 for ci in range(nc):
  name=v.take();nr=v.num(0,10000);ids=[]
  for ordinal in range(nr):
   identity,value=v.take(),v.take();assert identity and value
   ids.append(identity);source_rows.append((ci,ordinal,identity,value))
  assert ids==sorted(set(ids));cols.append((name,nr))
 assert [x[0] for x in cols]==sorted({x[0] for x in cols});v.done()
 c=Reader(cr);assert c.take()==b'pinkha-local-tree-storage-census-v1' and c.take()==b'local-structural-identities-no-source-admission'
 assert c.take()==sha(wr).encode() and c.take()==wr
 nr=c.num(0,10000);assert nr==len(source_rows);rows=[]
 for i in range(nr):
  ci,ordn,kind,identity,ident,tree=c.num(0,63),c.num(0,9999),c.take(),c.take(),c.take(),c.take()
  deleted,derived,unresolved=c.num(-1,2),c.num(-1,1),c.num(0,1)
  assert (ci,ordn,identity)==source_rows[i][:3]
  if ident:assert identity==b'\x03'+ident+b'\x00'
  rows.append({'collection':ci,'kind':kind,'id':ident,'tree':tree,'unresolved':unresolved})
 nrefs=c.num();resolved=0
 domains={b'tree_head':{b'tree_head'},b'acl_head':{b'acl_head'},b'acl_root':{b'acl_root'},b'acl':{b'acl_root',b'acl_record'},b'tree_root':{b'tree_root'},b'change':{b'tree_root',b'tree_change'}}
 for i in range(nrefs):
  row,pos,kind,domain,field,ident,tree=c.num(0,nr-1),c.num(-1,99999),c.take(),c.take(),c.take(),c.take(),c.take()
  outcome,target,observed=c.take(),c.num(-1,nr-1),c.num(-1,nr-1)
  assert ident and domain in domains
  if observed>=0:assert rows[observed]['id']==ident
  if outcome==b'resolved_identity_only':
   assert target>=0 and observed==target and rows[target]['id']==ident and rows[target]['kind'] in domains[domain]
   if domain in (b'tree_root',b'change'):assert rows[target]['tree']==tree
   resolved+=1
  else:assert target==-1 and outcome in {b'not_in_capture',b'wrong_namespace',b'wrong_root',b'target_unresolved',b'cross_tree'}
 ni=c.num();issues=[]
 for i in range(ni):
  ci,row,field,pos,code=c.num(0,nc-1),c.num(-1,nr-1),c.take(),c.num(-1,99999),c.take()
  if row>=0:assert rows[row]['collection']==ci and rows[row]['unresolved']==1
  issues.append(code)
 c.done()
 counts={'Rows':nr,'Collections':nc,'EmptyCollections':sum(n==0 for _,n in cols),'Generation':generation,'References':nrefs,'ResolvedReferences':resolved,'Issues':ni,'UnresolvedRows':sum(x['unresolved'] for x in rows),'UnknownCollections':issues.count(b'unknown_collection')}
 assert all(pub[k]==v for k,v in counts.items())
 assert pub['OwnerSHA256']==sha(nonce) and pub['SpaceSHA256']==sha(space)
 for k in ('HasNativeSourceAdmission','PermitsDestinationWrites','SemanticIdentityCensusComplete'):assert pub[k] is False
 assert pub['AllCapturedRowsAccounted'] is True
 pair_results[label]={'source_sha256':sha(wr),'census_sha256':sha(cr),'exact_nested_source':True,'all_rows_byte_identity_bound':True,'resolved_reference_namespace_and_tree_bound':True,**counts}
 witnesses[label]=(nonce,space,generation,nc,nr)
assert len(pair_results)==6 and set(pair_results)==set(receipts)
old,new=witnesses['captured-old'],witnesses['captured-new']
assert old[:3]==new[:3] and new[3:]==(old[3]+1,old[4]+1)
out={'status':'PASS_INDEPENDENT_NATIVE_CENSUS_ORIGINALS_SOURCE_AND_PRIVATE_FRAME_REVIEW','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_source':NS,'original_controller':S,'audit_only_controller':C,'actual_native_methods':starts,'actual_native_starts':5,'actual_native_passes':5,'old_methods_reexecuted':0,'native_builds':1,'retained_binary_sha256':build['binary_sha256'],'dependency_bytes_independently_verified':4045,'original_source_bindings_verified':42,'exact_original_copies':copies,'six_private_pairs':pair_results,'original_execute_status':'FAILED','original_execute_counter_zero':'Counter is assigned only after its private audit; actual raw test2json proves five START/PASS before that original audit failure. Original counter/receipt not rewritten.','audit_only_correction_exact_inverse':True,'private_permissions_exact_allowed':['0700','02700'],'private_files':'0600','raw_private_values_published':False,'new_current_builds_or_tests_in_review':0,'native_source_admission':False,'destination_writes':False,'semantic_identity_census_complete':False,'full_migration_or_parity':False,'retained_first_root_reader_failure':'Reader compared execution order with sorted qualification inventory; exact five method identities and per-method run-before-pass are now checked, with unchanged actual selector from original source manifest. No native rerun.', 'script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(O/'root-review.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':out['status'],'root_review_sha256':sha(raw(O/'root-review.json')),'dependencies':4045,'sources':42,'pairs':6,'native_passes':5,'old_reruns':0}))
