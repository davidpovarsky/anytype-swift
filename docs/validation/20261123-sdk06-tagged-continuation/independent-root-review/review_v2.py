import pathlib,json,hashlib,subprocess,re,datetime
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-sdk06-tagged-continuation-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/sdk06-tagged-continuation-20261123')
O=pathlib.Path('/mnt/development/projects/diagnostics/sdk06-tagged-root-review-20261123')
S='7f97d04b3eb9ba5cabbe7d9ed1e4a25eb54af3a1'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p,h=None):
 b=p.read_bytes()
 if h:assert sha(b)==h,str(p)
 return b
def git(*args):return subprocess.check_output(['git',*args],cwd=W,timeout=30)
def blob(ref,p):return git('show',ref+':'+p)
before=read(D/'attempt1/source-before.json','07779c04769e7ab22a71644dcf705e7aabae558d68c2a78c6a80da806c441af5')
assert before==read(D/'attempt1/source-after.json')
snap=json.loads(before);rows=snap['files'];assert snap['source_sha']==S and len(rows)==322
tree={}
for item in git('ls-tree','-r','-z',S,'--',*rows).split(b'\0'):
 if item:
  h,p=item.split(b'\t',1);m,k,o=h.decode().split();tree[p.decode()]=(m,k,o)
for p,r in rows.items():
 b=read(W/p,r['sha256']);assert len(b)==r['bytes']
 assert tree[p]==(r['git_mode'],'blob',r['git_object'])
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_object']
loaded=read(D/'attempt1/loaded-before.json','623f83fd0882666573dd820a4073874c6901917640328415eaa8ba6ad3b6b8d7')
assert loaded==read(D/'attempt1/loaded-after.json')
modules=json.loads(loaded);assert len(modules)==40
for p,h in modules.items():assert rows[p]['sha256']==h
tests=[p for p in modules if pathlib.PurePosixPath(p).name.startswith('test_')]
assert tests==['Tools/PinkhaSimulatorGate/test_sdk06_tagged_continuation.py'],tests
r=json.loads(read(D/'attempt1/receipt.json','7690d8f53718bdc2173d77b41daefe6326832f5de8cf1ece2a009833f64df511'))
events=json.loads(read(D/'attempt1/events.json','3bba877b915fe3570ddb3670f3a9e162ddd4ca08c43020d0498cca500974ae54'))
starts=[v['method'] for v in events if v['event']=='start'];passes=[v['method'] for v in events if v['event']=='PASS']
assert starts==passes==r['requested_methods'] and len(starts)==len(set(starts))==4
assert all(v.get('result') in (None,'PASS') for v in events)
assert r['status']=='PASS' and r['tests_run']==4 and r['source_sha']==S and r['sources_unchanged'] and r['loaded_sources_unchanged']
for k in ('failures','errors','skipped','old_controller_methods_executed','apple_builds','product_tests'):assert r[k]==0
assert r['actual_compiled_tag_enumeration']=='NOT_RUN' and r['original_products_relabelled'] is False
log=read(D/'attempt1/tests.log','eb7a9668663ea2c7c53657795049b2716b3b7a4ee99119c77afec33f192d6352').decode()
assert log.count(' ... ok')==4 and 'Ran 4 tests in 3.238s' in log and log.rstrip().endswith('OK')
process=json.loads(read(D/'attempt1-process.json'));assert process['source_sha']==S and process['return_code']==0 and process['status']=='COMPLETE' and process['cwd']==str(W)
assert process['old_tests']==process['product_commands']==0 and process['argv']==['/usr/bin/python3','-B','docs/validation/20261123-sdk06-tagged-continuation/run-controls.py','--evidence',str(D/'attempt1')]
tag=json.loads(read(W/'Tools/PinkhaSimulatorGate/sdk06-tagged-selection.json')) if (W/'Tools/PinkhaSimulatorGate/sdk06-tagged-selection.json').exists() else None
if tag is None:
 candidates=[(p,json.loads(read(p))) for p in (W/'Tools/PinkhaSimulatorGate').glob('*tagged*.json')]
 tag=next(o for p,o in candidates if 'historical_view' in o)
comp=json.loads(read(W/'Tools/PinkhaSimulatorGate/sdk06-tagged-composition.json','8d30cf445a125af9da99b8f90fdc4a818bd7c9ff1f7d457f175b52256e93149c'))
def inv(data,row,first='before_sha256',last='after_sha256',key='hunks'):
 assert sha(data)==row[last]
 for h in reversed(row[key]):
  a,b=h['after'].encode(),h['before'].encode()
  assert a!=b and data.count(a)==1;data=data.replace(a,b,1)
 assert sha(data)==row[first]
 return data
hist=tag['historical_view']['files'];assert len(hist)==260
for p,row in hist.items():
 b=read(W/p)
 if p in comp['historical_inverses']:b=inv(b,comp['historical_inverses'][p])
 if p in tag['source_inverses']:b=inv(b,tag['source_inverses'][p])
 assert sha(b)==row['sha256'] and rows[p]['git_mode']==row['git_mode'],p
assert len(tag['source_inverses'])==5 and len(comp['historical_inverses'])==3
views=comp['root_qualification']['actual_loaded_sources'];assert len(views)==9
for p,row in views.items():
 b=inv(read(W/p),row,'tested_sha256','current_sha256','inverses')
 assert b==blob(comp['root_qualification']['source_commit'],p)
assert len(tag['selection']['selected'])==23 and len(tag['selection']['excluded'])==7
wf='.github/workflows/torah-inspector-ipados27.yml'
for p,h in comp['executing_workflows'].items():read(W/p,h)
targets=sorted(set(re.findall(r'uses:\s+\./(\.github/workflows/\S+)',blob(S,wf).decode())))
for p in targets:git('cat-file','-e',S+':'+p)
files={}
for p in sorted(D.glob('attempt1*')):
 if p.is_file():files[str(p.relative_to(D))]={'bytes':p.stat().st_size,'sha256':sha(read(p))}
for p in sorted((D/'attempt1').iterdir()):
 if p.is_file():files[str(p.relative_to(D))]={'bytes':p.stat().st_size,'sha256':sha(read(p))}
out={'status':'PASS_INDEPENDENT_FOUR_NEW_CONTROL_ORIGINALS_AND_SOURCE_REVIEW','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha':S,'actual_methods':starts,'actual_started':4,'actual_passed':4,'actual_failures':0,'actual_errors':0,'actual_skipped':0,'original_unittest_seconds':3.238,'outer_receipt_seconds':r['duration_seconds'],'physical_and_frozen_git_inputs':322,'actual_loaded_modules':40,'old_test_modules_loaded':0,'loaded_before_after_equal':True,'source_before_after_equal':True,'historical_fixed_members_recovered_exactly':260,'tag_inverse_files':5,'current_shared_composition_inverse_files':3,'actual_coherent_loaded_source_views_match_original_git':9,'historical_300_inventory_is_coverage':False,'local_reusable_workflow_targets_exist_in_git':len(targets),'only_test_module_loaded':tests[0],'original_artifacts':files,'actual_Apple_builds':0,'actual_compiled_tag_enumeration':'NOT_RUN','actual_Apple_product_methods':0,'old_controller_methods_reexecuted':0,'original_7293_products_relabelled':False,'full_sdk_or_parity_accepted':False,'retained_first_auditor_error':'Lowercase event spelling in root reader; original actual events use uppercase PASS. No product/control rerun.', 'script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(O/'root-review.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':out['status'],'sha256':sha(read(O/'root-review.json')),'inputs':322,'loaded':40,'new_passes':4,'source_sha':S,'original_artifacts':len(files)}))
