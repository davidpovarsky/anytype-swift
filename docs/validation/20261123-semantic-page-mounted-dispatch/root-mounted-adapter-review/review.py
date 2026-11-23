import pathlib,json,hashlib,subprocess,datetime,ast
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/semantic-page-mounted-known-pair-20261123')
O=pathlib.Path('/mnt/development/projects/diagnostics/semantic-page-mounted-adapter-root-review-20261123')
Q=W/'docs/validation/20261123-semantic-page-mounted-known-pair'
S='f24dc168c1755482b92e642d7c7296210795e0e5';B='8a6d64ba152ba3aa4bb4376d070f63f5c9daceca';A='68148339c275268795360d71d519a5baf003adf8'
def sha(b):return hashlib.sha256(b).hexdigest()
def file(p,h=None):
 b=p.read_bytes()
 if h is not None:assert sha(b)==h,str(p)
 return b
def git(args):return subprocess.check_output(['git']+args,cwd=W,timeout=30)
def blob(rev,p):return git(['show',rev+':'+p])
q=json.loads(file(Q/'qualification.json','0722e6b900a7f13c9fc5831fdcdda33a6e5b981f3129eb43917c91d9df173875'))
rv=json.loads(file(Q/'source-review.json','0782d3cbd0b88238884a1f1b529f0c32caae6702222132c7e2f8827262b29923'))
before=file(D/'attempt3/source-before.json','5a69e1c05f2efe4190359e90997a76e648eaf5ceca288360fb36c901a57850c1')
assert before==file(D/'attempt3/source-after.json')
inputs=json.loads(before);assert len(inputs)==172
current=git(['rev-parse','HEAD']).decode().strip()
trees={}
for ref in (S,current):
 out={}
 for item in git(['ls-tree','-r','-z',ref,'--']+list(inputs)).split(b'\0'):
  if not item:continue
  h,p=item.split(b'\t',1);m,k,o=h.decode().split();out[p.decode()]={'mode':m,'kind':k,'oid':o}
 trees[ref]=out
for p,row in inputs.items():
 b=file(W/p,row['sha256']);assert len(b)==row['bytes']
 assert trees[S][p]==row['git'] and trees[current][p]==row['git']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['git']['oid']
 assert rv['source_sha256'][p]==row['sha256']
loaded=json.loads(file(D/'attempt3/loaded-repo-modules.json'))
static=json.loads(file(D/'static-import-closure.json','2e7335a3b0c2a36cd1bca33ac7fbc1f01fcbbd0d73a242ec157863f384437b8e'))
assert len(loaded)==33 and set(loaded)==set(static['modules'])
for p,h in loaded.items():assert inputs[p]['sha256']==h==static['modules'][p]['sha256']
copies=[]
for r in q['copied_originals']:
 a=file(pathlib.Path(r['original_path']),r['sha256']);b=file(Q/r['copy_path'],r['sha256'])
 assert a==b and len(a)==r['bytes'];copies.append({'path':r['copy_path'],'sha256':r['sha256'],'bytes':r['bytes']})
assert len(copies)==21
receipt=json.loads(file(D/'attempt3/receipt.json','8ddb6cbf82ac1b52577c144969deb904e680f4f9372f8a8228a8b149ad371928'))
log=file(D/'attempt3/controls.log','e8b40e14a4b646715373da09ddad9a580d7dca4a9118c82b6300d37df28f3d3e').decode()
events=[json.loads(l) for l in file(D/'attempt3/events.jsonl','0fd2bdcbd954b61fdbe2b10d70aa054c1ba057c785f10f0765c7149f1fc1a855').splitlines()]
method='test_mounted_known_pair.MountedKnownPairAdapterControl.test_mounted_import_and_owned_region_use_qualified_pair_without_fallback'
assert [(e['event'],e['method']) for e in events]==[('START',method),('PASS',method)]
assert receipt['source_sha']==S and receipt['source_unchanged'] and receipt['returncode']==0
assert receipt['named_starts']==receipt['named_passes']==[method]
assert 'Ran 1 test in 0.196s' in log and log.rstrip().endswith('OK')
for k in ('builds','product_tests_executed','simulator_commands_executed','old_pair_controls_rerun','old_mounted_controls_rerun'):assert receipt[k]==0
first=json.loads(file(D/'attempt1/receipt.json','ca0d292fc1b7b6602ef0d13cf45309251a82f93dcd9093d0f89ff8575b70aa86'))
assert first['returncode']!=0 and not first['named_passes'] and first['named_starts']==[method]
assert q['attempt2']['actual_methods_started']==0 and q['attempt2']['guard_free_bytes']<q['attempt2']['required_free_bytes']
p='Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py';new=blob(S,p)
after=b'pair = consumer.consumer_simulator.choose_pair(runtimes, types)'
old=b'pair = consumer.simulator_selection.choose_pair(runtimes, types, product_family="iPad", major=27, architecture="arm64")'
assert new.count(after)==1 and new.replace(after,old)==blob(B,p)
p='Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py';new=blob(S,p);assert new==blob(A,p)
inverses=[(b'import consumer_simulator\n',b'import simulator_selection\n'),(b'pair = consumer_simulator.choose_pair(runtimes, devices)',b'pair = simulator_selection.choose_pair(runtimes, devices, product_family="iPad", major=27, architecture="arm64")')]
for a,b in inverses:assert new.count(a)==1;new=new.replace(a,b)
assert new==blob(B,p)
component=json.loads(file(D/'exact-original-component.json'))
assert component['source_origin']==A and len(component['files'])==18
for r in component['files']:assert file(W/r['path'],r['sha256'])==blob(A,r['path'])
for p,h in q['fixed_source_hashes'].items():file(W/p,h)
# Keep complete original admission proof and source-plan immutable.
for p,h in rv['original_admission_files'].items():file(W/p,h);assert blob(B,p)==blob(current,p)
tree=ast.parse(file(W/'Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_known_pair.py'))
tests=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert len(tests)==1
out={'status':'PASS_INDEPENDENT_ORIGINAL_AND_CURRENT_SOURCE_REVIEW','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'qualified_source_sha':S,'current_head_observed':current,'qualification_sha256':sha(file(Q/'qualification.json')),'exact_physical_and_git_input_files':172,'actual_loaded_modules_bound':33,'static_and_actual_loaded_closure_equal':True,'copied_originals_independently_verified':copies,'actual_control_starts':1,'actual_control_passes':1,'actual_failed':0,'actual_skipped':0,'old_pair_methods_retained_without_replay':4,'retained_original_import_error':True,'retained_capacity_stop_zero_methods':True,'test_scope':'Actual repository module/import closure and compiled actual checkout guard plus mounted inventory/create/boot region, using controlled external commands. This is not actual Apple or product execution.','exact_mounted_whole_file_inverse':True,'exact_consumer_two_change_whole_file_inverse':True,'retained_component_files_equal_original_681':18,'admission_and_all_admission_original_files_unchanged':True,'source_plan_unchanged':True,'current_mac_builds':0,'current_product_methods':0,'mounted_Apple_acceptance':'NOT_RUN','physical_device':'NOT_RUN','full_migration_or_parity':False,'script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(O/'root-review.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':out['status'],'root_review_sha256':sha(file(O/'root-review.json')),'inputs':172,'loaded':33,'copied_originals':21,'actual_new_pass':1,'old_reruns':0}))
