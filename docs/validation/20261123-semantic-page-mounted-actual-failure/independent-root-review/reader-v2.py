import pathlib,zipfile,json,subprocess,hashlib,datetime,ast,time,collections
R=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/semantic-page-mounted-actual-result-20261123')
SHA='bb046d988d57bf5f530f71b8b86588b21ab7ded2'
APP='68148339c275268795360d71d519a5baf003adf8'
def h(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.run(['git',*args],cwd=R,capture_output=True,check=True).stdout
started=time.monotonic()
run=json.loads((D/'run.json').read_bytes())
assert (run['id'],run['head_sha'],run['head_branch'],run['run_attempt'],run['event'],run['status'],run['conclusion'])==(45134312784,SHA,'codex/chatgpt-wave15-page154-mounted-admission-20261123',1,'workflow_dispatch','completed','failure')
a=json.loads((D/'artifacts.json').read_bytes())['artifacts'];assert len(a)==1
a=a[0];raw=(D/'artifact.zip').read_bytes()
assert a['id']==14800634578 and a['size_in_bytes']==len(raw)==1110727 and a['digest']=='sha256:'+h(raw)
assert h(raw)=='e7749a6935c689bd2f33b0cad990106db876c3d3375ac98797d4c1fc6b1dcd3c'
jobs=json.loads((D/'jobs.json').read_bytes())['jobs'];selected=[j for j in jobs if j['id']==137556822152];assert len(selected)==1 and selected[0]['conclusion']=='failure' and all(j['conclusion']=='skipped' for j in jobs if j['id']!=137556822152)
assert h((D/'job.log').read_bytes())=='fbf497bc55630fe89e41d06c5fe5fc978e7f4c8ccba03eb47538b44ea40b2952'
with zipfile.ZipFile(D/'artifact.zip') as z:
 members=z.infolist();assert len(members)==33 and len({x.filename for x in members})==33
 assert sum(x.file_size for x in members)==4169900
 member_inventory=[]
 for x in members:
  p=pathlib.PurePosixPath(x.filename);assert not p.is_absolute() and '..' not in p.parts
  data=z.read(x);assert len(data)==x.file_size
  member_inventory.append(dict(name=x.filename,bytes=len(data),sha256=h(data),zip_external_attr=x.external_attr))
 e=json.loads(z.read('evidence/execution.json'))
 assert e['controller_source_sha']==SHA and e['compiled_app_source_sha']==APP and e['status']=='FAIL'
 assert e['phase']=='EXACT_ORIGINAL_PRODUCTS' and e['error_type']=='TimeoutExpired'
 for k in ('app_builds','native_builds','ui_builds','new_preparation_methods_passed','new_ui_methods_passed','previous_native_or_boundary_methods_rerun'):assert e[k]==0
 assert e['binding']['runID']=='45134312784' and e['binding']['runAttempt']=='1' and e['binding']['sourceSHA']==APP
 before=z.read('evidence/controller-source-before.json');assert before==z.read('evidence/controller-source-after.json')
 source_map=json.loads(before);assert len(source_map)==12135
 tree={}
 for row in git('ls-tree','-rz','--full-tree',SHA).split(b'\0'):
  if row:
   info,path=row.split(b'\t',1);mode,typ,oid=info.split()
   assert typ==b'blob'
   tree[path.decode()]={'mode':mode.decode(),'oid':oid.decode()}
 assert set(tree)==set(source_map)
 p=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 hashed={};mismatches=[]
 try:
  for path,t in tree.items():
   oid=t['oid']
   if oid not in hashed:
    p.stdin.write((oid+'\n').encode());p.stdin.flush()
    header=p.stdout.readline().split();assert header[0].decode()==oid and header[1]==b'blob'
    remain=int(header[2]);digest=hashlib.sha256()
    while remain:
     block=p.stdout.read(min(remain,1024*1024));assert block;digest.update(block);remain-=len(block)
    assert p.stdout.read(1)==b'\n';hashed[oid]=digest.hexdigest()
   if hashed[oid]!=source_map[path]:mismatches.append(path)
  p.stdin.close();assert p.wait(timeout=5)==0
 finally:
  if p.poll() is None:p.kill();p.wait()
 assert not mismatches,mismatches[:5]
 commands=e['commands'];assert len(commands)==13
 raw_commands={}
 for n in z.namelist():
  if n.endswith('.command.json'):
   c=json.loads(z.read(n));raw_commands[n]=c
   matches=[r for r in commands if r['argv']==c['argv'] and r['worker_pid']==c['worker_pid'] and r['started_at']==c['started_at']]
   assert len(matches)==1
   for k,v in c.items():assert matches[0][k]==v,(n,k)
 assert len(raw_commands)==12
 kernel_or_ps=[]
 for r in commands:
  assert type(r['worker_pid']) is int and r['worker_pid']>1 and r['owned_group_cleanup']=='TERM_THEN_KILL'
  if 'owned_group_quiescence' in r:
   q=r['owned_group_quiescence'];assert q['status']=='PASS' and q['pgid']==r['worker_pid'] and q['live_members']==0 and q['budget_seconds']==10
   kernel_or_ps.append(q)
 assert len(kernel_or_ps)==12
 boot=[r for r in commands if 'bootstatus' in r['argv']];assert len(boot)==1;boot=boot[0]
 assert boot['worker_pid']==2927 and boot['return_code']==0 and boot['status']=='COMPLETE' and boot['timeout_seconds']==180
 q=boot['quiescence_failure'];assert q['error']==e['error'] and q['error_type']=='TimeoutExpired' and q['quiescence_observation'] is None
 assert len(q['timeout_observations'])==1 and 9.9<q['timeout_observations'][0]['timeout_seconds']<=10
 assert "['ps', '-axo', 'pid=,pgid=,stat=']" in q['error']
 diag=[r for r in commands if 'get_app_container' in r['argv']];assert len(diag)==1 and diag[0]['return_code']==-15 and diag[0]['status']=='TIMED_OUT' and diag[0]['timeout_seconds']==30
 assert diag[0]['started_at']>boot['finished_at']
 product_commands=[r for r in commands if any(x in r['argv'] for x in ('test-without-building','build-for-testing','test','build'))]
 assert product_commands==[]
 udid='401A68CC-12C3-42ED-A95D-5ECA6302C9AC'
 for action in ('shutdown','delete'):
  matches=[r for r in commands if r['argv']==['xcrun','simctl',action,udid]]
  assert len(matches)==1 and matches[0]['return_code']==0 and matches[0]['status']=='COMPLETE'
 assert e['owned_simulator_cleanup_status']=='COMPLETE' and e['owned_simulator_cleanup_budget']['within_budget'] is True and e['owned_simulator_cleanup_budget']['elapsed_seconds']<=60
 assert e['mounted_cleanup_adapter']['status']=='PASS' and e['mounted_cleanup_adapter']['previous_primary_failure_preserved'] is True
 assert e['restored_native']['entries']==5008 and e['restored_ui']['entries']==30
 assert e['restored_native']['source_sha']==e['restored_ui']['source_sha']==APP
 assert e['restored_native']['status']==e['restored_ui']['status']=='PASS_EXACT_SELF_CONTAINED_PRODUCTS_RESTORE'
 assert e['restored_products_unchanged']==[{'original_entries_checked':5008,'owned_descriptors_only':0},{'original_entries_checked':30,'owned_descriptors_only':0}]
 assert e['admission']['artifact_sha256']=='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'
 assert e['limits']=={'fullProductAcceptance':False,'physicalDevice':'NOT_RUN','shipping':'OFF'}
 controller_paths=['Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py','Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py','Tools/PinkhaSimulatorGate/run_owned_single_lane.py']
 sources={path:git('show',SHA+':'+path).decode() for path in controller_paths}
 consumer=ast.parse(sources[controller_paths[1]])
 calls=[n for n in ast.walk(consumer) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='verify_owned_group_stopped']
 assert len(calls)==1 and any(k.arg=='cleanup_profile' and isinstance(k.value,ast.Constant) and k.value.value=='semantic-page154' for k in calls[0].keywords)
 supervisor=ast.parse(sources[controller_paths[2]])
 verify=next(n for n in supervisor.body if isinstance(n,ast.FunctionDef) and n.name=='verify_owned_group_stopped')
 assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_sdk06_kernel_group_observation' for n in ast.walk(verify))
 mounted=sources[controller_paths[0]]
 assert mounted.index('"bootstatus"')<mounted.index('receipt["phase"] = "ACTUAL_NEW_PREPARATION"')
 result=dict(status='PASS_INDEPENDENT_AUDIT_OF_PRESERVED_PRODUCT_NOT_RUN_FAILURE',reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reader_sha256=h(_source.encode()),original_run=45134312784,source=SHA,compiled_app_source=APP,conclusion='failure',artifact_sha256=h(raw),archive_members=len(members),archive_member_bytes=sum(x.file_size for x in members),archive_member_inventory=member_inventory,controller_source_map=dict(entries=len(source_map),sha256=h(before),before_after_equal=True,all_exact_git_blobs=True,unique_git_blobs=len(hashed)),original_commands=len(commands),raw_command_records=12,command_pid_group_bindings_checked=13,prior_group_pass_observations=12,bootstatus=dict(return_code=0,pid=2927,primary_group_error=q),diagnostic_container_lookup=dict(status='TIMED_OUT',return_code=-15,timeout_seconds=30,absence_proved=False),product_commands=0,new_preparation_methods_passed=0,new_ui_methods_passed=0,old_methods_rerun=0,builds=0,restored_products=dict(native_entries=5008,ui_entries=30,unchanged=True),cleanup=dict(shutdown_exit=0,delete_exit=0,within_60_seconds=True,post_delete_inventory='NOT_RECORDED'),controller_call_binding=dict(profile='semantic-page154',current_controller=True,old_page_supervisor_has_kernel_branch=False,files={p:h(s.encode()) for p,s in sources.items()}),limitations=e['limits'],read_only=True,new_test_executions=0,new_downloads=0,elapsed_seconds=time.monotonic()-started)
 print(json.dumps(result,sort_keys=True))
