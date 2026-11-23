import os,json,pathlib,hashlib,subprocess,stat,ast,datetime,collections
os.environ['GIT_OPTIONAL_LOCKS']='0'
R=pathlib.Path('/mnt/development/projects')
W=R/'worktrees/anytype-wave15-coherent-owned-continuation-20261123'
M=R/'worktrees/anytype-wave15-shared-20261123'
D=W/'docs/validation/20261123-coherent-owned-continuation'
A=R/'diagnostics/coherent-owned-continuation-controls-20261123'
HEAD='6acab36f450ce411a8614f23e55cb14a5602ed58'
BASE='75bd6d7af18dfd511e85582ce7f994d2801b7703'
MAIN='9cafd32811e50f4e883efb034888d7ce1e349c02'
TEST='Tools/PinkhaSimulatorGate/test_coherent_owned_continuation.py'
def require(c,m):
 if not c:raise AssertionError(m)
def h(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def git(w,*args):return subprocess.check_output(['git','-c','gc.auto=0','-C',str(w),*args])
def safe(p):return p.is_file() and not p.is_symlink() and p.resolve()==p
def blob(ref,path):return git(W,'show',ref+':'+path)
require(git(W,'rev-parse','HEAD').decode().strip()==HEAD,'writer_head')
require(not git(W,'status','--porcelain').strip(),'writer_dirty')
require(git(M,'rev-parse','HEAD').decode().strip()==MAIN,'main_head')
require(not git(M,'status','--porcelain').strip(),'main_dirty')
seal=read(D/'attempt1-originals/seal.json')
q=read(D/'attempt2-originals/qualification.json')
require(h((D/'attempt1-originals/seal.json').read_bytes())=='ddd18e031df3a4c4070939a040e3358d0f83905e03ee0dadec26cd934e4c0764','seal_sha')
require(h((D/'attempt2-originals/qualification.json').read_bytes())=='b3592ba2899703a58147b72bb4b3ae7e81901cf7c919c5897dcd4490ee723647','qualification_sha')
copies=[]
for sub,decl,count in [('attempt1-originals',seal,63),('attempt2-originals',q,18)]:
 require(len(decl['originals'])==count,'original_count_'+sub)
 total=0
 for rel,row in sorted(decl['originals'].items()):
  require(not pathlib.Path(rel).is_absolute() and '..' not in pathlib.Path(rel).parts,'unsafe_copy_path')
  p=D/sub/rel;orig=pathlib.Path(row['original_path'])
  require(safe(p) and safe(orig),'copy_or_origin_missing_'+rel)
  b=p.read_bytes()
  require(len(b)==row['bytes'] and h(b)==row['sha256'],'copy_hash_'+rel)
  require(orig.read_bytes()==b,'origin_copy_diverged_'+rel)
  require(blob(HEAD,p.relative_to(W).as_posix())==b,'copy_git_diverged_'+rel)
  total+=len(b)
 copies.append({'scope':sub,'copies':count,'bytes':total,'original_and_git_exact':True})
old=blob('3a6f932925a7cadd37490b91eed59c27f58da446',TEST)
new=(W/TEST).read_bytes()
pairs=[
(b'with self.assertRaises(RuntimeError):\n                        origin._preload_cleanup_sources()',b'with self.assertRaises(ValueError):\n                        origin._preload_cleanup_sources()'),
(b'with self.assertRaises(RuntimeError if case in {"changed_intent", "changed_admission"} else ValueError):',b'with self.assertRaises(ValueError):')]
inv=new
for a,b in pairs:
 require(inv.count(a)==1,'exact_assertion_inverse')
 inv=inv.replace(a,b,1)
require(inv==old,'whole_test_inverse')
scope=read(D/'control-inputs.json')['tests'];retry=read(D/'failed-control-inputs.json')['tests']
require(len(scope)==4 and retry==scope[3:],'failed_only_selected_scope')
def methods(b):
 tree=ast.parse(b)
 return {n.name:ast.get_source_segment(b.decode(),n) for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef)}
om,nm=methods(old),methods(new)
for name in scope[:3]:require(om[name.split('.')[-1]]==nm[name.split('.')[-1]],'retained_method_changed')
changes=git(W,'diff','--name-only','3a6f932925a7cadd37490b91eed59c27f58da446','ad05ea15beb10b98feb74ab5ec705e18535fa8ba').decode().splitlines()
require([p for p in changes if not p.startswith('docs/')]==[TEST],'production_changed_for_retry')
require(blob('9abf690fd418f042313ee627029ed862715b22a5','docs/validation/20261123-coherent-owned-continuation/run-controls.py')==(D/'run-controls.py').read_bytes(),'original_wrapper_changed')
require(h((D/'run-controls.py').read_bytes())=='36964117af425caf65a8216d5143871f6de40b3942622833c34909d2c1bce916','wrapper1')
require(h((D/'run-failed-cleanup-control.py').read_bytes())=='d2d2cb874a83bfb54efe9c9a519c47cb93e96e8027027a99c93af90eb4b8b590','wrapper2')
attempts=[];allpasses=[]
for num,expected_count,run_count,pass_count,sub_pass,sub_fail,loaded_counts,exsha in [
 (1,70,4,3,22,5,(22,26),'e9e566eb8c19a972c146a6b24583d5c1dc0a03e7ae826e54e5aa94e23a59df2d'),
 (2,79,1,1,13,0,(22,22),'45e4c2d8d0132f6ff5646129d8ade28ecb779b1f0b8f13082b409837eb12de7f')]:
 name='attempt'+str(num);p=A/name
 ex=read(p/'execution.json');before=read(p/'source-before.json');after=read(p/'source-after.json')
 require(h((p/'execution.json').read_bytes())==exsha,'execution_sha_'+name)
 require((p/'source-before.json').read_bytes()==(p/'source-after.json').read_bytes(),'physical_snapshot_drift_'+name)
 require(before==after and len(before['files'])==expected_count==before['input_count'],'source_count_'+name)
 require(ex['source_before_after_identical'] is True,'declared_source_drift')
 require(ex['methods_run']==run_count and ex['skipped']==0 and ex['failures']==0 and ex['errors']==(5 if num==1 else 0),'execution_counts_'+name)
 require(ex['status']==('FAIL' if num==1 else 'PASS_FAILED_METHOD_ONLY'),'original_status_'+name)
 require(all(ex[k]==0 for k in ['old_control_methods_executed','product_methods_executed','simulator_commands_executed']),'scope_escape')
 ctl=ex['controller_commit']
 for path,row in before['files'].items():
  b=blob(ctl,path)
  require(h(b)==row['sha256'] and len(b)==row['bytes'],'source_git_hash_'+path)
  tree=git(W,'ls-tree',ctl,'--',path).decode().strip().split(None,3)
  require(tree[0]==row['mode'] and tree[2]==row['blob'],'source_git_mode_blob_'+path)
  curr=W/path;require(safe(curr),'source_physical_absence_'+path)
  require(oct(stat.S_IMODE(curr.stat().st_mode))==row['physical_mode'],'source_mode_drift_'+path)
  if num==1 and path==TEST:require(inv==b,'old_test_inverse')
  else:require(curr.read_bytes()==b,'current_physical_drift_'+path)
 lb=read(p/'loaded-before.json');la=read(p/'loaded-after.json')
 require((len(lb),len(la))==loaded_counts,'loaded_count')
 require(all(la.get(k)==v for k,v in lb.items()),'loaded_alias_drift')
 if num==2:require(lb==la,'retry_loaded_drift')
 for label,data in [('before',lb),('after',la)]:
  for alias,row in data.items():
   sr=before['files'][row['path']]
   require(row['sha256']==sr['sha256'] and row['bytes']==sr['bytes'],'loaded_binding_'+alias)
 events=[json.loads(line) for line in (p/'events.jsonl').read_text().splitlines()]
 starts=[x['test'] for x in events if x['action']=='start']
 passes=[x['test'] for x in events if x['action']=='pass']
 expected=['test_coherent_owned_continuation.'+x for x in (scope if num==1 else retry)]
 require(starts==expected and passes==expected[:pass_count],'named_method_outcomes')
 require(len([x for x in events if x['action']=='subtest-pass'])==sub_pass,'subpass_count')
 failures=[x for x in events if x['action']=='subtest-fail']
 require(len(failures)==sub_fail and all(x['error_type']=='RuntimeError' and x['test']==expected[-1] for x in failures),'original_failure_scopes')
 require(all(x['action'] in ['start','pass','subtest-pass','subtest-fail'] for x in events),'unexpected_event_type')
 allpasses+=passes
 ap=p/'control-produced-originals/actual-source-admission'
 check=read(ap/'coherent-cleanup-source-check.json')
 snapshots=list((ap/'control-source-snapshots').glob('*/*.json'))
 require(len(snapshots)==1,'production_snapshot_count')
 snap=read(snapshots[0]);bound=snap['controller_source_hashes'];aliases=snap['loaded_module_names']
 require(check['admitted_sources']==47 and check['loaded_source_paths']==47 and check['loaded_module_names']==47 and check['git_subprocesses']==0,'production_admission_summary')
 require(len(bound)==47 and len(aliases)==47 and set(aliases.values())==set(bound),'production_snapshot_closure')
 require(snapshots[0].stem==snap['snapshot_sha256']==check['source_snapshot_sha256'],'production_snapshot_identity')
 require(check['original_intent_sha256']==h((ap/'batch-intent.json').read_bytes()),'production_intent_binding')
 for path,digest in bound.items():require(h(blob(ctl,path))==digest,'production_admission_git_'+path)
 attempts.append({'attempt':num,'execution_sha256':exsha,'status':ex['status'],'source_bindings':expected_count,
 'loaded_before_after':list(loaded_counts),'actual_named_passes':passes,'subtest_passes':sub_pass,'subtest_failures':sub_fail,
 'production_subcase_git_sources':47,'events_sha256':h((p/'events.jsonl').read_bytes()),'source_before_after_sha256':h((p/'source-before.json').read_bytes())})
require(len(allpasses)==4 and len(set(allpasses))==4,'distinct_scope')
e1=[json.loads(x) for x in (A/'attempt1/events.jsonl').read_text().splitlines()]
retained_subs=[x for x in e1 if x['action']=='subtest-pass' and x['test'] in allpasses[:3]]
require(len(retained_subs)==14,'retained_subtest_count')
paths=['Tools/PinkhaSimulatorGate/'+x for x in ['coherent_cleanup_snapshot.py','coherent_fresh_construction.py','coherent_original_products.py','coherent_heart_release.py','wave15_batch.py','run_wave15_acceptance.py','test_coherent_owned_continuation.py']]
patch=git(W,'diff','--binary',BASE,HEAD,'--',*paths)
require(h(patch)=='d88abc00125f9f2f0946c413fbc42995b1ee8b8026d886908fb96575e7c9916a','integration_patch_sha')
basepaths=set(git(W,'ls-tree','-r','--name-only',BASE,'--',*paths).decode().splitlines())
require(len(basepaths)==4,'existing_hook_count')
for path in paths:
 if path in basepaths:require((M/path).read_bytes()==blob(BASE,path),'main_hook_drift_'+path)
 else:require(not (M/path).exists(),'main_new_path_collision_'+path)
package='Tools/PinkhaNativeDerived/package_evidence.py'
require(h((M/package).read_bytes())=='8400bd4ac7bbc61871b51f1021c3dbbb1de5800094e07129417a784d24337309','main_package_policy_changed')
report={'protocol':'root-coherent-owned-originals-audit-v1','status':'PASS_READ_ONLY_AUDIT',
 'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':HEAD,'integration_main':MAIN,
 'original_copy_groups':copies,'attempts':attempts,'complete_distinct_methods':4,'distinct_subtests':27,
 'retained_method_bodies_exact':3,'test_expectation_changes':2,'test_whole_file_inverse_exact':True,
 'production_changed_for_retry':False,'original_failed_attempt_retained':True,
 'original_wrapper_unchanged':True,'integration_paths':paths,'integration_patch_sha256':h(patch),
 'main_package_policy_preserved_sha256':h((M/package).read_bytes()),
 'tests_executed_by_this_audit':0,'products_executed_by_this_audit':0,
 'actual_release_acceptance':'NOT_RUN','free_bytes':os.statvfs(R).f_bavail*os.statvfs(R).f_frsize}
print(json.dumps(report,sort_keys=True))
