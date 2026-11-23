import os, pathlib, json, hashlib, subprocess, zipfile, datetime, fcntl, re
os.setgid(1001)
os.setuid(1001)
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-otzaria-owned-import-contract-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/otzaria-native-archive-20261123/45125326998')
P='docs/pinkha/torah-integration/native-owned-annotation-contract-20261123'
HEAD='fabd2fd824ce819b28dfad01fc24b204e3391bab'
HEART='d98420b1113536afd08cde6de9a5816f6d27ffff'
SW=pathlib.Path('/mnt/development/projects/git-mirrors/anytype-swift.git')
HT=pathlib.Path('/mnt/development/projects/git-mirrors/anytype-heart.git')
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(m,*args): return subprocess.check_output(['git','-C',str(m),*args])
def at(m,rev,path): return git(m,'show',rev+':'+path)
def checked(raw,row):
    assert len(raw)==row['bytes'], row
    assert sha(raw)==row['sha256'], row
    if 'git_blob' in row: assert blob(raw)==row['git_blob'], row
def write(name,value):
    (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
run=json.loads((D/'RUN.json').read_text())
assert (run['id'],run['run_attempt'],run['head_sha'],run['event'],run['status'],run['conclusion'])==(45125326998,1,HEAD,'push','completed','failure')
artifact=json.loads((D/'ARTIFACTS.json').read_text())['artifacts']
assert len(artifact)==1
a=artifact[0];rawzip=(D/'original-native-archive-evidence.zip').read_bytes()
assert (a['id'],a['size_in_bytes'],a['workflow_run']['head_sha'])==(14796205075,len(rawzip),HEAD)
assert a['digest']=='sha256:'+sha(rawzip)
assert sha(rawzip)=='7c87d6897acf5ee454f3005e3ba4b5915324044625b5ed475c8642e0e40143d3'
mraw=at(SW,HEAD,P+'/slice-a/EXECUTION_INPUTS.json')
m=json.loads(mraw)
assert m['heart_base']==HEART
source_rows=[]
for row in m['source_inputs']:
    raw=at(SW,row['revision'],row['source_path'])
    checked(raw,row)
    retained=at(SW,HEAD,P+'/slice-a/retained-inputs/'+row['destination'])
    assert raw==retained
    source_rows.append({**row,'actual_original_git_bytes_match':True,'actual_retained_git_bytes_match':True})
control_rows=[]
for row in m['control_inputs']:
    raw=at(SW,HEAD,P+'/'+row['path']);checked(raw,row)
    control_rows.append({**row,'actual_final_git_bytes_match':True})
new_rows=[]
for row in m['new_native_inputs']:
    raw=at(SW,row['source_revision'],P+'/'+row['path']);checked(raw,row)
    assert raw==at(SW,HEAD,P+'/'+row['path'])
    new_rows.append({**row,'actual_authored_revision_bytes_match':True})
original_rows=[]
for row in m['original_model_and_rpc_inputs']:
    raw=at(HT,HEART,row['path']);checked(raw,row)
    original_rows.append({**row,'actual_original_git_bytes_match':True})
r14=json.loads(at(SW,HEAD,P+'/slice-a/retained-inputs/r14/native-heart-integration.json'))
assert r14['heart_sha']==HEART
expected={r['path']:r['after_sha256'] for r in r14['files']}
for row in m['source_inputs']:
    if row['destination'].startswith('native/'):expected[row['destination'][7:]]=row['sha256']
for row in m['new_native_inputs']:expected[row['heart_path']]=row['sha256']
with zipfile.ZipFile(D/'original-native-archive-evidence.zip') as z:
    names=z.namelist()
    assert len(names)==len(set(names))==29
    assert all(not n.startswith('/') and '\\' not in n and '..' not in pathlib.PurePosixPath(n).parts for n in names)
    assert z.testzip() is None
    index=json.loads(z.read('EVIDENCE_INDEX.json'))['files']
    assert len(index)==28 and {r['path'] for r in index}==set(names)-{'EVIDENCE_INDEX.json'}
    for row in index:checked(z.read(row['path']),row)
    result=json.loads(z.read('RESULT.json'));commands=json.loads(z.read('COMMANDS.json'))
    composed=json.loads(z.read('COMPOSED_NATIVE_SOURCES.json'))
    assert result['control_head']==HEAD and result['heart_base']==HEART
    runtime_source_keys=('revision','source_path','destination','bytes','sha256','git_blob')
    assert result['source_inputs']==[{key:r[key] for key in runtime_source_keys} for r in m['source_inputs']]
    assert result['control_inputs']==m['control_inputs']
    assert result['execution_manifest_sha256']==sha(mraw)
    assert result['status']=='FAIL' and result['archive_admission']=='NOT_RUN'
    assert composed['all_declared_afterimages']==expected
    assert composed['unchanged_original_model_proto_rpc_inputs']==m['original_model_and_rpc_inputs']
    req=composed['required_actual_compiler_coverage']
    assert len(req)==19
    declared=json.loads(z.read('DECLARED_NATIVE_INPUTS.json'))
    assert {r['path']:r['sha256'] for r in declared['required_product_test_coverage']}==req
    prefix='/Users/runner/work/anytype-swift/anytype-swift/build/Heart-Native-Archive/'
    filemap={r['path']:r for r in declared['files']}
    for path,h in req.items():assert filemap[prefix+path]['sha256']==h
    raw=z.read('08-declared-native-inputs.stdout').decode()
    decoder=json.JSONDecoder();pos=0;packages=[]
    while pos<len(raw):
        while pos<len(raw) and raw[pos].isspace():pos+=1
        if pos==len(raw):break
        value,pos=decoder.raw_decode(raw,pos);packages.append(value)
    byimport={x['ImportPath']:x for x in packages}
    testpkg='github.com/anyproto/anytype-heart/core/application.test'
    closure=set(byimport[testpkg]['Deps'])|{testpkg}
    app_files={}
    for name in closure:
        pp=byimport[name]
        for fn in pp.get('GoFiles',[])+pp.get('CgoFiles',[]):
            full=str(pathlib.PurePosixPath(pp['Dir'])/fn)
            if full.startswith(prefix):app_files.setdefault(full[len(prefix):],[]).append(name)
    coverage=[]
    for path,h in sorted(req.items()):
        coverage.append({'path':path,'sha256':h,'declared_in_combined_go_list':True,
                         'included_in_compiled_application_test_closure':path in app_files,
                         'actual_package_variants':sorted(app_files.get(path,[])),
                         'runtime_execution_claim':False})
    not_compiled=[r['path'] for r in coverage if not r['included_in_compiled_application_test_closure']]
    assert not_compiled==['core/block/import/owned_annotation_archive_test.go'],not_compiled
    labels=[x['label'] for x in commands]
    assert len(commands)==11 and labels[-1]=='execute-native_exports'
    assert 'compile-archive_admission' not in labels and 'execute-archive_admission' not in labels
    assert all(x['effective_returncode']==0 for x in commands[:-1]) and commands[-1]['effective_returncode']==1
    assert all(not x['timed_out'] and x['status']=='TERMINAL' and any(y.get('drained') is True for y in x['cleanup']) for x in commands)
    for cmd in commands:
        for stream in ['stdout','stderr']:
            assert sha(z.read(cmd[stream]))==cmd[stream+'_sha256']
    eventraw=z.read('11-execute-native_exports.stdout')
    events=[json.loads(line) for line in eventraw.splitlines() if line.strip()]
    starts=[e['Test'] for e in events if e.get('Action')=='run']
    assert starts==['TestOtzariaOwnedAnnotationNativeExports']
    fails=[e for e in events if e.get('Action')=='fail' and e.get('Test')]
    assert len(fails)==1
    assert not any(n.startswith('fixtures/') and n.endswith('.zip') for n in names)
    cleanup=json.loads(z.read('fixtures/native-export-cleanup.json'))
    assert cleanup['original_account_stop_returned_or_app_absent'] and cleanup['owned_directory_removed']
    assert result['owned_command_groups_drained'] and result['owned_native_temporary_removed']
    assert not cleanup['import_started']
    errors=[{'event_index':i,**e} for i,e in enumerate(events) if 'fixed schema context or persisted input changed while reading' in e.get('Output','')]
    assert len(errors)==1
    names_seen=[]
    for i,e in enumerate(events[:errors[0]['event_index']]):
        match=re.search(r'\((Torah annotation[^)]*)\)',e.get('Output',''))
        if match:names_seen.append({'event_index':i,'time':e['Time'],'native_logged_definition_name':match.group(1)})
    assert len(names_seen)==15
    diagnostics={'native_log_sha256':sha(eventraw),'native_json_events':len(events),
                 'error_events':errors,'prior_named_schema_state_log_events':names_seen,
                 'logged_names_are_not_complete_creation_receipts':True,
                 'actual_registration_phase_history_not_retained':True,
                 'exact_changed_guard_not_identifiable_from_retained_result':True,
                 'zero_creation_or_untouched_schema_claim':False}
watch=json.loads((D/'WATCH_RESULT_1.json').read_text())
assert watch['state']=='TERMINAL_OBSERVED' and watch['lock_released'] and watch['watch_exit_code']==0
assert not pathlib.Path('/proc/'+str(watch['pid'])).exists()
with (D/'observer.lock').open() as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
compiler={'schema':1,'source':HEAD,'go_list_sha256':sha(raw.encode()),'go_package_records':len(packages),
          'actual_successful_compiler_command':next(x for x in commands if x['label']=='compile-native_exports'),
          'actual_application_test_input_rows':18,'combined_declared_required_rows':19,
          'not_compiled_in_this_run':not_compiled,'rows':coverage,
          'compiled_application_does_not_qualify_unexecuted_archive_functions':True,
          'archive_test_binary_compiled':False,'archive_test_execution':'NOT_RUN',
          'native_binary':result['native_binaries']['native_exports']}
intake={'schema':1,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'run_id':run['id'],'attempt':1,'source':HEAD,'head_tree':git(SW,'rev-parse',HEAD+'^{tree}').decode().strip(),
        'run_url':run['html_url'],'event':'push','native_outcome':'FAIL','failure_stage':'original schema registration in parent fixture setup',
        'artifact_id':a['id'],'artifact_bytes':len(rawzip),'artifact_sha256':sha(rawzip),'github_digest_matches':True,
        'zip_members':len(names),'unique_safe_crc_valid':True,'index_rows_verified':len(index),
        'source_input_rows_verified':len(source_rows),'control_input_rows_verified':len(control_rows),
        'authored_native_rows_verified':len(new_rows),'unchanged_original_model_rpc_rows_verified':len(original_rows),
        'composed_native_afterimages_verified':len(expected),'execution_manifest_sha256':sha(mraw),
        'actual_application_compile':'PASS','actual_application_parent_tests':{'pass':0,'fail':1,'skip':0},
        'export_leaf_tests_started':0,'genuine_export_archives_retained':0,'archive_leaf_tests_started':0,
        'archive_test_binary_compiled':False,'archive_admission':'NOT_RUN',
        'owned_command_groups_drained':True,'native_account_cleanup':cleanup,
        'owned_native_temporary_removed':True,'watcher_process_absent':True,'watcher_lock_available':True,
        'commands':[{'label':x['label'],'effective_returncode':x['effective_returncode'],'duration_seconds':x['duration_seconds'],'timed_out':x['timed_out']} for x in commands],
        'native_import_activated':False,'existing_importer_changed':False,'generated_rpc_changed':False,
        'body_ack_authority':False,'cold_reopen_qualified':False,'swift_invocation_qualified':False,'historical_controls_replayed':False,
        'next_step':'Trace retained registration guard and preserve actual per-definition call history before any bounded read-only readiness continuation is proposed; no CI retry authorized by this intake.'}
write('SOURCE_INTAKE.json',{'source_rows':source_rows,'control_rows':control_rows,'authored_rows':new_rows,'original_model_rpc_rows':original_rows,'composed_afterimages':expected})
write('COMPILER_COVERAGE.json',compiler)
write('REGISTRATION_FAILURE_DIAGNOSTIC.json',diagnostics)
write('INTAKE.json',intake)
print(json.dumps({'intake':intake,'coverage_summary':{'compiled_application_rows':18,'uncompiled_required_rows':not_compiled},
                  'receipt_hashes':{n:sha((D/n).read_bytes()) for n in ['INTAKE.json','SOURCE_INTAKE.json','COMPILER_COVERAGE.json','REGISTRATION_FAILURE_DIAGNOSTIC.json']}},ensure_ascii=False))
