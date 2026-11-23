import pathlib,json,hashlib,subprocess,stat,ast,datetime,collections
R=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-native-ui-readiness-20261123')
D=pathlib.Path('/mnt/development/projects/evidence/native-ui-owned-readiness-20261123/attempt1')
P=R/'docs/validation/20261123-native-ui-owned-readiness'
A=pathlib.Path('/mnt/development/projects/evidence/native-ui-owned-readiness-20261123/audit-only-attempt1/audit.json')
O=pathlib.Path(__file__).parent
def h(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=R,timeout=30)
assert git('rev-parse','HEAD').decode().strip()=='07b11b7ed790ccd0508824824a831506e1614c3d'
assert not git('status','--porcelain=v1','--untracked-files=all')
q=read(P/'qualification.json');index=read(P/'evidence-index.json');a=read(A);r=read(D/'result.json')
assert h((P/'qualification.json').read_bytes())=='9ea48ecd4f191c73781fa7705cbdd8ab8029ec5c62b1e7af9c6f9f45a84bcb19'
assert h((P/'evidence-index.json').read_bytes())==q['evidence_index_sha256']=='51c90b39befb5040378640977b307506932ced8ac45819f361f5bd45c5393ed9'
assert h(A.read_bytes())==q['audit_sha256']=='4e55f2bf26897765be2c5d7136c5d4e6829ffda28a4c62f219847fb31e167f26'
assert len(index['files'])==77
copies=[]
for f in index['files']:
 old=pathlib.Path(f['original_path']);new=R/f['committed_path'];b=old.read_bytes()
 assert h(b)==f['sha256'] and len(b)==f['bytes'] and stat.S_IMODE(old.stat().st_mode)==f['source_mode']
 assert new.read_bytes()==b and git('show','HEAD:'+f['committed_path'])==b
 copies.append(dict(path=f['committed_path'],bytes=len(b),sha256=h(b)))
assert h((D/'result.json').read_bytes())==q['original_aggregate_sha256']=='42969ef092224e45ad7b29e113ffd15712b2bde9d094f4028f60214154b1da97'
assert r['status']=='FAIL' and r['error']['type']=='AttributeError' and 'isSuccessful' in r['error']['message']
assert r['errors']==r['failures']==0 and r['old_test_methods_reexecuted']==r['new_builds']==r['apple_commands_executed']==0
assert len(r['originals'])==70
for name,wanted in r['originals'].items():
 p=D/name;b=p.read_bytes()
 assert h(b)==wanted['sha256'] and len(b)==wanted['bytes'] and stat.S_IMODE(p.stat().st_mode)==wanted['mode']
before=(D/'source-before.json').read_bytes();assert before==(D/'source-after.json').read_bytes()
sources=json.loads(before);assert len(sources['inputs'])==70
final=read(D/'originals/driver-composition/final-physical-source-bindings.json')
roots={name:pathlib.Path(v['root']) for name,v in final.items()}
pins={'current':'c30e20e42ae6c52b7c4d251fc59630c2ff2f677c','originalApp':'4b09cc5478c60c1c6728a54f2a27a115637a835b'}
for name,row in sources['inputs'].items():
 origin,relative=name.split(':',1);p=roots[origin]/relative;b=p.read_bytes();s=p.stat()
 assert len(b)==row['bytes'] and h(b)==row['sha256'] and stat.S_IMODE(s.st_mode)==row['mode']
 assert (s.st_dev,s.st_ino,s.st_mtime_ns)==(row['device'],row['inode'],row['mtime_ns'])
 assert git('show',pins[origin]+':'+relative)==b
events=read(D/'events.json')
assert [e['event'] for e in events]==['START','PASS','START','PASS']
assert [e['test'] for e in events if e['event']=='PASS']==q['actual_named_passes']==a['methods']['actual_named_passes']
assert not (D/'loaded-sources-after.json').exists()
assert q['post_runner_module_alias_map_claimed'] is False and q['future_corrected_wrapper_executed'] is False
actual={origin+':'+name:sha for origin,v in final.items() for name,sha in v['files'].items()}
loaded=read(D/'loaded-sources-before.json')
assert len(actual)==21 and actual=={name:v['sha256'] for name,v in loaded.items()}==a['actual_last_test_file_closure']['file_sha256']
initial=read(D/'originals/driver-composition/actual-import-origin-closures.json')['sourceBindings'];assert final==initial
test_path=R/'Tools/AnyEnginePort/test_native_ui_original_products_readiness.py';source=test_path.read_text()
method=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='test_driver_binds_real_both_origin_imports_before_exact_readiness')
last=method.body[-1];assert isinstance(last,ast.Expr) and isinstance(last.value,ast.Call) and isinstance(last.value.func,ast.Attribute) and last.value.func.attr=='write_new'
last_source=ast.get_source_segment(source,last);assert 'final-physical-source-bindings.json' in last_source and 'recheck_physical_sources(app, sources)' in last_source
pids=set();exits=collections.Counter()
for child in a['actual_owned_children']:
 p=D/child['path'];b=p.read_bytes();c=json.loads(b)
 assert h(b)==child['command_sha256'] and c['worker_pid']==child['pid']>1 and child['pid'] not in pids
 pids.add(child['pid']);exits[c['return_code']]+=1
 assert c['owned_group_cleanup']=='TERM_THEN_KILL' and c['cwd']==str(R) and c['argv'][0]=='/usr/bin/python3'
 proof=p.with_name(p.name.replace('.command.json','.ui-quiescence.json'));v=read(proof)
 assert h(proof.read_bytes())==child['quiescence_sha256'] and v['originalCommandSHA256']==h(b)
 assert v['command']==c['argv'] and v['cwd']==c['cwd'] and v['kernelBudgetSeconds']==10
 log=p.with_name(p.name.replace('.command.json','.log'));assert h(log.read_bytes())==v['originalLogSHA256']
 if c['return_code']==9:
  assert v['status']=='FAIL' and v['commandFailure']['type']=='CalledProcessError' and v['quiescenceFailure']['type']=='PermissionError'
  path=D/'originals/owned-command/nonzero-actual-owned-group-absence.json';z=read(path);assert h(path.read_bytes())==child['actual_absence_sha256']
 else:z=v['quiescence']
 assert z['status']=='PASS' and z['absenceSource']=='KERNEL_ESRCH' and z['liveMembers']==0 and z['pgid']==c['worker_pid'] and z['budgetSeconds']==10
 k=z['kernelObservation'];assert k['pgid']==c['worker_pid'] and k['operation']=='os.killpg' and k['signal']==0 and k['errno']==3 and k['outcome']=='ABSENT_ESRCH'
 assert k['before_monotonic']<k['deadline_monotonic'] and k['after_monotonic']<=k['deadline_monotonic']
assert len(pids)==8 and dict(exits)=={0:6,9:1,13:1}
original=(D/'controller.py').read_bytes();future=(P/'future-controller-static-correction.py').read_bytes()
assert original.count(b'.isSuccessful()')==1 and future==original.replace(b'.isSuccessful()',b'.wasSuccessful()')
out=dict(status='PASS_INDEPENDENT_AUDIT_TWO_NAMED_PASSES_WITH_WRAPPER_FAILURE',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reader_sha256=h(pathlib.Path(__file__).read_bytes()),source=pins['current'],proof_head='07b11b7ed790ccd0508824824a831506e1614c3d',source_inputs_exact_git_and_physical=70,original_bound_artifacts=70,committed_original_copies=77,copied_bytes=sum(x['bytes'] for x in copies),copied_files=copies,methods_started=2,methods_passed=2,wrapper_status='FAIL',wrapper_failure='AttributeError isSuccessful',source_before_after_identical=True,last_test_file_closure=21,outer_loaded_after='ABSENT_PRESERVED',post_runner_alias_map_claimed=False,distinct_actual_children=8,child_exit_distribution=dict(exits),timely_actual_kernel_absence=8,new_control_executions=0,new_product_executions=0,new_builds=0,future_wrapper_executed=False)
(O/'root-review.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='copied_files'}))
print('ROOT_REVIEW_SHA',h((O/'root-review.json').read_bytes()))
