import pathlib,subprocess,zipfile,tarfile,io,json,hashlib,os,re,datetime
OUT=pathlib.Path(r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\sdk06-mock-fix-original-45262248686-1\root-original-audit1')
ROOT=OUT.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,b):
 with (OUT/name).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {'path':name,'bytes':len(b),'sha256':sha(b)}
remote=r"""
import pathlib,subprocess,hashlib,json,signal,resource
signal.alarm(60);resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
r='/run/anytapy-wave15-source-overlay-20261123/root';head='56b4caafae1c0898b483717abed495f2e3b9281b'
def git(*a):
 p=subprocess.run(['git','-c','gc.auto=0','-c','core.packedGitWindowSize=16m','-c','core.packedGitLimit=64m','-C',r,*a],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20);assert p.returncode==0,p.stderr[:1000];return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
mname='Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json'
raw=git('show',head+':'+mname);assert sha(raw)=='a92efe23a4488c7ab7d40f243ba81a8fb9d7b5263e5872f352328cb532e770d7'
m=json.loads(raw);assert len(m['inputs'])==85
rows=dict(m['inputs']);rows[mname]={'git_mode':'100644','sha256':sha(raw)}
for p,pin in rows.items():
 b=git('show',head+':'+p);assert sha(b)==pin['sha256']
 meta=git('ls-tree',head,'--',p).decode().split()[0];assert meta==pin['git_mode']
fixed=json.loads(git('show',head+':Tools/PinkhaSimulatorGate/sdk06-component-projection-source.json'))
for p,pin in fixed['source_files'].items():
 b=git('show',fixed['source_sha']+':'+p);assert sha(b)==pin['sha256'] and len(b)==pin['bytes']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin['git_blob']
print(json.dumps({'head':head,'fixed_source':fixed['source_sha'],'controller':rows,'modules':m['modules'],'preloads':m['preload_modules'],'original_source_files':fixed['source_files'],'selected':fixed['selection'],'source_inspection_only':True},sort_keys=True))
"""
p=subprocess.run(['ssh','-T','torah-dev','python3','-B','-u','-'],input=remote.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75)
assert p.returncode==0,p.stderr.decode(errors='replace')[:1500]
proof=json.loads(p.stdout);save('git-source-proof.json',p.stdout)
inventory=json.loads((OUT/'archive-inventory.json').read_bytes())
assert sha((OUT/'archive-inventory.json').read_bytes())=='5932e2eca0c81263de13e9e50088ad5c2a1a9bdb97f0754d115e2689334771a8'
raw=(ROOT/'original-14863182566.zip').read_bytes();assert sha(raw)=='5eb1723489babdf8f58f206ed83bae66c214c09ec09e34747578bb6152faa2f6'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 with zipfile.ZipFile(io.BytesIO(z.read('Pinkha-Native-Derived-Evidence.zip'))) as zz:
  admission=json.loads(zz.read('original-native-admission.json'))
  c=admission['current_controller_sources']
  assert c['binding']=={'run_attempt':'1','run_id':'45262248686','source_sha':proof['head']}
  assert c['actual_current_inputs']==proof['controller'] and len(c['actual_current_inputs'])==86
  assert len(c['loaded_repository_sources'])==68
  for path,h in c['loaded_repository_sources'].items():assert proof['controller'][path]['sha256']==h
  save('current-controller.original.json',(json.dumps(c,indent=2)+'\n').encode())
  projection=json.loads(zz.read('shared-editor-components/source-projection.json'))
  for path,pin in proof['original_source_files'].items():
   assert projection['inputs'][path]['original_sha256']==pin['sha256'] and projection['inputs'][path]['bytes']==pin['bytes']
  products=json.loads(zz.read('shared-editor-components/current-component-products.json'))
  payload=z.read('shared-editor-components/SDK06PendingProducts.tar.gz')
  assert len(payload)==products['archive_bytes'] and sha(payload)==products['archive_sha256']=='275080eefdb7a4ffe1b1ef69b3bae946fd21846c8f7795f61c6c6a80b9ec0694'
  tarfiles={}
  with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as tf:
   for m in tf:
    if m.isfile():tarfiles[m.name]=tf.extractfile(m).read()
  matches={}
  for rel,h in projection['generated_files'].items():
   names=[n for n in tarfiles if n=='Source/'+rel or n.endswith('/Source/'+rel)]
   assert len(names)==1,(rel,names)
   assert sha(tarfiles[names[0]])==h
   matches[rel]=h
  authority='AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift'
  name='Sources/TorahRelatedReadAuthorityMappingTests.swift'
  assert matches[name]==proof['original_source_files'][authority]['sha256']=='364902afbdbe451bbe80cb8959be8fc74edb6db274f0ccf071db70de4d8f8d68'
  actual=[b for n,b in tarfiles.items() if n=='Source/'+name or n.endswith('/Source/'+name)][0]
  assert b'import SwiftProtobuf' not in actual and actual.count(b'.Error.with {')==2
  save('authority-source.original.swift',actual)
  log=zz.read('shared-editor-components/projected-component-build.log')
  assert sha(log)=='cbe4f44bc89d2a90e3837ef10d099243e5a4945ff6d95a00b71f0db8b9d0a2ac'
  errors=[line for line in log.decode().splitlines() if 'error:' in line and 'TorahRelatedReadAuthorityMappingTests.swift:' in line]
  assert len(errors)==2 and ':14:63:' in errors[0] and ':19:61:' in errors[1]
  assert all("has no member 'with'" in l for l in errors)
  e=json.loads(zz.read('shared-editor-components/execution.json'))
  assert e['status']=='FAIL' and e['phase']=='TEST_BUNDLE_BUILD' and e['component_bundle_builds']==1
  assert e['additional_app_builds']==e['native_library_builds']==e['product_tests_executed']==e['old_passed_methods_replayed']==0
  assert e['final_integrity']=={'completed_new_products_bound':False,'descriptor_bound':False,'enumeration_bound':False,'errors':[],'generated_source_bound':True,'original_failure_preserved':True,'source_products_archive_bound':True,'staged_original_app_bound':True,'status':'PASS'}
  assert len(e['commands'])==1
  command=e['commands'][0];assert command['return_code']==65 and command['output_sha256']==sha(log) and command['owned_group_quiescence']['kernel_group_observation']['outcome']=='ABSENT_ESRCH'
  supervisor=json.loads(zz.read('single-lane-supervisor.json'))
  assert supervisor['owned_group_quiescence']['kernel_group_observation']['outcome']=='ABSENT_ESRCH'
  cleanup=json.loads(zz.read('preflight/lifecycle-cleanup.json'));assert cleanup==supervisor['cleanup'] and cleanup['status']=='PASS'
  devices=cleanup['fallback_cleanup']['devices']
  assert len(devices)==2 and all(x['delete_exit_code']==0 and x['status']=='DELETED_OWNED_SIMULATOR' for x in devices)
  main=json.loads(zz.read('execution.json'));assert main['current_controller_sources_unchanged'] and main['original_native_products_unchanged'] and main['ui_build_status']=='NOT_RUN'
  swift={k:v for k,v in admission['restoration']['product_fingerprints'].items() if '/SwiftProtobuf.' in k}
  assert len(swift)==6
qualification={'status':'QUALIFIED_ORIGINAL_FAILURE_NO_PRODUCT_ACCEPTANCE','run_id':45262248686,'attempt':1,'source':proof['head'],'artifact_id':14863182566,'artifact_bytes':len(raw),'artifact_sha256':sha(raw),'archive_inventory_sha256':sha((OUT/'archive-inventory.json').read_bytes()),'original_source_git_sha':proof['fixed_source'],'actual_controller_git_inputs':86,'actual_loaded_repository_sources':68,'all_controller_hashes_and_git_modes_match_immutable_source':True,'original_swift_inputs':8,'generated_source_files_bound':len(matches),'actual_test_source_sha256':sha(actual),'first_errors':errors,'original_build_log_sha256':sha(log),'component_build_exit_code':65,'component_bundle_builds':1,'new_app_builds':0,'new_native_builds':0,'ui_builds':0,'product_tests':0,'historical_tests_replayed':0,'selection_not_enumerated':True,'expected_pending_selection':{'methods':23,'argument_cases':32},'incomplete_component_outputs_eligible_for_reuse':False,'worker_and_build_groups_absent':True,'owned_simulators_deleted':2,'original_app_and_current_controller_unchanged':True,'original_swiftprotobuf_compiled_carriers':swift,'diagnosis':'Original projected authority test omits SwiftProtobuf import; both protocol-extension .with lookups fail. Module carriers are present in the retained original configuration. Source repair must preserve all method bodies/assertions and immutable original source.','read_only_audit_no_product_execution':True,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
receipt=save('failure-qualification.json',(json.dumps(qualification,indent=2)+'\n').encode())
print(json.dumps({'qualification':receipt,'status':qualification['status'],'actual_controller_git_inputs':86,'actual_loaded_sources':68,'generated_files_bound':len(matches),'owned_simulators_deleted':2,'partial_products_reusable':False}))