import pathlib,hashlib,json,gzip,os,subprocess,shutil,importlib.util,sys
R=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-native-owned-snapshot-20261123')
N=pathlib.Path('/mnt/development/projects/worktrees/anytype-heart-native-owned-snapshot-20261123')
P=pathlib.Path('/mnt/development/projects/evidence/native-owned-snapshot-20261123/failed-shutdown-attempt1')
O=P.parent/'attempt1';H=R/'Tools/AnyEngineValidation/native_owned_snapshot';F=H/'failed_shutdown'
D=R/'docs/validation/20261123-native-owned-snapshot/failed-shutdown-attempt1'
Q=R/'docs/validation/20261123-native-owned-snapshot/qualification.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(v,s):
 if not v:raise RuntimeError(s)
def put(p,b):
 need(shutil.disk_usage(R).free-len(b)>=2500000000,'evidence_reserve')
 p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {'sha256':sha(p),'bytes':len(b)}
def js(p,x):return put(p,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
def git(r,*a):return subprocess.check_output(['git','-C',str(r),*a],timeout=30)
need(shutil.disk_usage(R).free>=2516777216,'evidence_start_reserve')
need(not D.exists() and not Q.exists(),'qualification_outputs_unused')
need(git(N,'rev-parse','HEAD').decode().strip()=='ba965ac243c6501a1a7083ce0e07d3557650db00' and not git(N,'status','--porcelain').strip(),'native_current_clean')
need(git(R,'rev-parse','HEAD').decode().strip()=='44e09f96353186e56ecdbefe0d0cd7e059097d9d' and not git(R,'status','--porcelain').strip(),'controller_current_clean')
need(sha(P/'execute.json')=='092fa2fe70326f8bd3a0d9fdac04673f47f9dfd597cf6c6e8c7cadf64689be72','actual_failed_only_receipt')
need(sha(P/'build.json')=='26bf9764c84619ec742bf3f637b2344189ed650ac7607abf6d09236278823205','failed_only_build_receipt')
need(sha(O/'execute.json')=='b0d8a59ab46b66125e4a903ee498743db319497000b98fbf9724f448a1945d0d','original_failed_receipt')
old=json.loads((O/'execute.json').read_bytes());new=json.loads((P/'execute.json').read_bytes());build=json.loads((P/'build.json').read_bytes())
oldbuild=json.loads((O/'build.json').read_bytes());observation=json.loads((P/'safe-shutdown-observation.json').read_bytes())
need(old['status']=='FAILED' and new['status']=='PASS_FAILED_SHUTDOWN_METHOD_ONLY' and not new['final_errors'] and new['command']['owned_group_absent'] and new['final_capacity_admitted'],'actual_failed_only_outcome')
need(old['actual_named_passes']+new['actual_named_passes']==old['actual_named_starts'] and len(old['actual_named_passes'])==3 and len(new['actual_named_passes'])==1 and new['retained_methods_reexecuted']==0,'exact_three_plus_one')
need(observation['fd_counts']=={'baseline':2,'inflight':3,'after_rejected_open':4,'after_original_close':0},'actual_numeric_outcome_changed')
for prefix,v in [(O,oldbuild),(P,build)]:
 p=prefix/'products/native-owned-snapshot.test';need(p.stat().st_size==v['binary']['bytes'] and sha(p)==v['binary']['sha256'] and p.stat().st_mode&0o7777==v['binary']['mode'],'original_binary_changed')
files={}
for stage in ['build','execute']:
 for scope in ['source','dependencies','tools','loaded']:
  before=P/(stage+'-'+scope+'-before.json');after=P/(stage+'-'+scope+'-after.json')
  x=json.loads(before.read_bytes());y=json.loads(after.read_bytes());need(x==y,'actual_before_after_integrity')
  for p in [before,after]:
   raw=p.read_bytes();dest=D/(p.name+'.gz');copy=put(dest,gzip.compress(raw,mtime=0))
   files[p.name]={'original_path':str(p),'sha256':sha(p),'bytes':len(raw),'compressed_copy':str(dest.relative_to(R)),'copy':copy}
for name in ['build.json','execute.json','binary-buildinfo-original.txt','safe-events.json','safe-shutdown-observation.json']:
 p=P/name;files[name]={'original_path':str(p),**put(D/name,p.read_bytes())}
for name in ['private/build-original.command.json','private/build-original.stdout','private/build-original.stderr','private/execution-original.command.json','private/execution-original.stdout','private/execution-original.stderr']:
 p=P/name;files[name]={'original_private_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'raw_published':False}
review=json.loads((R/'docs/validation/20261123-native-owned-snapshot/failed-shutdown-source/source-review.json').read_bytes())
test='core/pinkha/localstorewitness/native_capture_test.go';oldtest=git(N,'show','179509522c78e263c86c847e1cc78ad05ff43aeb:'+test);current=(N/test).read_text()
inv=review['literal_inverse'];need(current.count(inv['after'])==1 and current.replace(inv['after'],inv['before']).encode()==oldtest,'whole_original_test_inverse')
need(git(N,'diff','--name-only','179509522c78e263c86c847e1cc78ad05ff43aeb','HEAD').decode().splitlines()==[test],'only_failed_fixture_delta')
olddeps=json.loads((O/'execute-dependencies-after.json').read_bytes());newdeps=json.loads((P/'execute-dependencies-after.json').read_bytes())
need(set(olddeps)==set(newdeps) and [p for p in olddeps if olddeps[p]!=newdeps[p]]==[str(N/test)],'only_one_declared_dependency_changed')
native=json.loads((P/'execute-source-after.json').read_bytes())['native']
for rel,row in native.items():need(sha(N/rel)==row['sha256'],'current_native_bytes_changed')
method_receipts=[]
for e,origin in [(old,O),(new,P)]:
 ev=json.loads((origin/'safe-events.json').read_bytes())
 for name in e['actual_named_passes']:
  passes=[x for x in ev if x.get('Test')==name and x.get('Action')=='pass']
  need(len(passes)==1,'one_named_original_pass')
  method_receipts.append({'method':name,'source_native':e['native_source_sha'],'source_controller':e['controller_source_sha'],'original_execute_path':str(origin/'execute.json'),'original_execute_sha256':sha(origin/'execute.json'),'pass_event':passes[0],'reexecuted_after_original_pass':False})
qualification={'kind':'native-owned-localstore-lifetime-four-qualified-methods-v1','status':'PASS_SCOPE_NATIVE_STORAGE_LIFETIME_ONLY','current_native_sha':'ba965ac243c6501a1a7083ce0e07d3557650db00','current_controller_source_sha':'44e09f96353186e56ecdbefe0d0cd7e059097d9d',
'qualified_distinct_methods':4,'original_first_run_status':'FAILED','original_first_run_starts':4,'original_first_run_passes':3,'original_first_run_failures':1,'failed_only_continuation_starts':1,'failed_only_continuation_passes':1,'old_controls_replayed':0,'passed_methods_replayed':0,
'actual_native_builds':2,'reason_for_second_build':'Only failed test fixture changed; three original named passes retained with exact production/full-file inverse.','method_receipts':method_receipts,
'original_native_binary':oldbuild['binary'],'failed_only_native_binary':build['binary'],'original_private_frames':{'audit_path':'docs/validation/20261123-native-owned-snapshot/attempt1/retained-three-private-frame-audit.json','audit_sha256':sha(R/'docs/validation/20261123-native-owned-snapshot/attempt1/retained-three-private-frame-audit.json'),'count':2,'new_frame_replay':False},
'actual_fd_counts':observation['fd_counts'],'fd_interpretation':'Final all-handle closure established zero matching descriptors. Pinned SQLite deferred-close behavior explains why immediate baseline equality is not generally valid; the exact original failed-run descriptor identity remains unobserved.',
'source_integrity':{'native_inputs':43,'continuation_controller_inputs_including_manifest':64,'declared_dependency_inputs':4189,'tool_inputs':14,'loaded_before_after':75,'all_before_after_equal':True,'only_native_test_source_changed_between_runs':True},
'fixed_source_review':{'path':'docs/validation/20261123-native-owned-snapshot/failed-shutdown-source/source-review.json','sha256':sha(R/'docs/validation/20261123-native-owned-snapshot/failed-shutdown-source/source-review.json')},'failed_only_original_files':files,
'native_storage_lifetime_issuer':True,'accountSessionACLAuthorized':False,'hasNativeSourceAdmission':False,'permitsDestinationWrites':False,'semanticIdentityCensusComplete':False,'filePayloadCoverageComplete':False,
'remaining_acceptance':['actual application/account and already-loaded Space admission','semantic Object/block/type/property/file reconstruction with explicit unresolved identities','authoritative whole-Space and file-payload coverage','destination authority and durable mapping/idempotency/conflict recovery','separate Apple/current-product/device/external gates'],
'private_values_published':False,'free_at_seal':shutil.disk_usage(R).free}
v=js(Q,qualification)
print(json.dumps({'status':'PASS_JOINED_THREE_ORIGINAL_PLUS_ONE_FAILED_ONLY','qualification':str(Q),**v,'native_source':qualification['current_native_sha'],'original_failures_preserved':1,'actual_unique_methods':4,'old_reruns':0,'free':shutil.disk_usage(R).free}))
