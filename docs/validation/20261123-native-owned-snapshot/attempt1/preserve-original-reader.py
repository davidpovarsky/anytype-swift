import pathlib,hashlib,json,os,stat,gzip,importlib.util,sys,shutil
R=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-native-owned-snapshot-20261123')
P=pathlib.Path('/mnt/development/projects/evidence/native-owned-snapshot-20261123/attempt1')
D=R/'docs/validation/20261123-native-owned-snapshot/attempt1'
H=R/'Tools/AnyEngineValidation/native_owned_snapshot'
assert shutil.disk_usage(R).free>=2516777216 and not D.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {'sha256':sha(p),'bytes':len(b)}
def js(p,x):return put(p,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
assert sha(P/'build.json')=='e125ee571c391d3327b50bad80169c74b73efd0dca03ed2c390018d177ec5fc5'
assert sha(P/'execute.json')=='b0d8a59ab46b66125e4a903ee498743db319497000b98fbf9724f448a1945d0d'
assert sha(H/'audit.py')=='cb1371ebc82d1f493feb4ebe631176a4c9646c2123fa9229903d1a5b6e1e5695'
sp=importlib.util.spec_from_file_location('retained_native_original_auditor',H/'audit.py');a=importlib.util.module_from_spec(sp);sys.modules[sp.name]=a;sp.loader.exec_module(a)
build=json.loads((P/'build.json').read_bytes());execution=json.loads((P/'execute.json').read_bytes())
assert build['status']=='BUILD_PASS_EXECUTION_NOT_RUN' and execution['status']=='FAILED'
assert not build['final_errors'] and not execution['final_errors']
assert build['command']['owned_group_absent'] and execution['command']['owned_group_absent']
inspected=a.inspect_events(P/'private/execution-original.stdout')
assert inspected['starts']==a.METHODS and inspected['passes']==a.METHODS[:3]
assert set(inspected['observations'])==set(a.METHODS[:3]) and set(inspected['receipts'])==set(a.LABELS)
frames=a.audit_private(P/'private/fixtures',inspected['receipts'])
private_audit={'status':'PASS_AUDIT_ONLY_TWO_ORIGINAL_FRAMES','native_methods_reexecuted':0,'original_aggregate_status':'FAILED','audit_source_sha256':sha(H/'audit.py'),'frames':frames}
js(P/'retained-three-private-frame-audit.json',private_audit)
files={}
names=['build.json','execute.json','binary-buildinfo-original.txt','safe-events.json','safe-native-observations.json','safe-native-receipts.json','retained-three-private-frame-audit.json']
for stage in ['build','execute']:
 for scope in ['source','dependencies','tools','loaded']:
  before=P/(stage+'-'+scope+'-before.json');after=P/(stage+'-'+scope+'-after.json')
  x=json.loads(before.read_bytes());y=json.loads(after.read_bytes())
  assert x==y
  for p in [before,after]:
   raw=p.read_bytes();dest=D/(p.name+'.gz');z=put(dest,gzip.compress(raw,mtime=0))
   files[p.name]={'original_path':str(p),'sha256':sha(p),'bytes':len(raw),'compressed_copy':str(dest.relative_to(R)),**{'copy':z}}
for n in names:
 p=P/n;dest=D/n;row=put(dest,p.read_bytes());files[n]={'original_path':str(p),**row}
for n in ['private/build-original.command.json','private/build-original.stdout','private/build-original.stderr','private/execution-original.command.json','private/execution-original.stdout','private/execution-original.stderr']:
 p=P/n;files[n]={'original_private_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'published_raw':False}
receipt={'kind':'native-owned-snapshot-original-attempt1-preservation-v1','build_status':build['status'],'original_execution_status':'FAILED','retained_actual_passes':inspected['passes'],'actual_failed_method':a.METHODS[3],'exact_failure':'native_capture_test.go:490: unpublished native database handle leaked after shutdown','failure_classification':'Observed global FD-count assertion failure while the original native database remains open; no exact retained descriptor identity was logged, so the particular cause is not established.','source_integrity_pass':True,'dependency_integrity_pass':True,'tool_integrity_pass':True,'loaded_integrity_pass':True,'final_capacity_pass':True,'owned_groups_absent':True,'binary':build['binary'],'source':{'native':build['native_source_sha'],'controller':build['controller_source_sha'],'manifest_sha256':build['manifest_sha256']},'two_private_frames_audit':private_audit,'original_files':files,'new_test_execution':False,'accountSessionACLAuthorized':False,'hasNativeSourceAdmission':False,'permitsDestinationWrites':False,'semanticIdentityCensusComplete':False,'filePayloadCoverageComplete':False}
row=js(D/'preservation.json',receipt)
print(json.dumps({'status':'PASS_ORIGINAL_PRESERVATION_NO_TEST_REPLAY','receipt':str(D/'preservation.json'),**row,'original_failures_preserved':1,'retained_named_passes':3,'private_frames':len(frames),'free':shutil.disk_usage(R).free}))
