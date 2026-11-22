import collections, datetime, hashlib, json
from pathlib import Path
P = Path(__file__).resolve().parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
blob = lambda b: hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
prefix = 'docs/pinkha/torah-integration/native-import-origin-observation-20261122/'
remote = json.loads((P/'audit/ROOT_REMOTE_BINDINGS.json').read_bytes())
assert remote['head']=='20cb8998211eaefa5ddb00ef60ff2462dd3271e9'
for row in remote['files']:
    assert row['path'].startswith(prefix) and row['status']=='added'
    relative=row['path'][len(prefix):]
    local=P/('publication/SOURCE_MANIFEST.json' if relative=='SOURCE_MANIFEST.json' else relative)
    data=local.read_bytes()
    assert blob(data)==row['sha'], row['path']
assert len(remote['files'])==94
E=P/'evidence/controls-v1'
result=json.loads((E/'RESULT.json').read_bytes())
assert sha((E/'RESULT.json').read_bytes())=='cdd51f4581c2d78bacc072cf81956b51f94a8370c3e1d57f22e95ee2fd8d1cfb'
for command in result['commands']:
    assert command['exit']==0 and not command['timed_out']
    for stream in ['stdout','stderr']:
        assert sha((E/(command['name']+'.'+stream+'.log')).read_bytes())==command[stream+'_sha256']
events=[json.loads(x) for x in (E/'controls.stdout.log').read_text().splitlines() if x.strip()]
starts=collections.Counter(x['Test'] for x in events if x.get('Test') and x['Action']=='run')
passed=collections.Counter(x['Test'] for x in events if x.get('Test') and x['Action']=='pass')
assert not [x for x in events if x.get('Test') and x['Action'] in ['fail','skip']]
leaves={n for n in starts if not any(k.startswith(n+'/') for k in starts)}
assert len(leaves)==50
assert leaves=={x['name'] for x in result['tests']}
assert all(starts[n]==passed[n]==1 for n in leaves)
S=result['source_manifest']
for row in S['module_files']:
    data=(P/'controls/module'/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256'], row['path']
for row in result['product_files']:
    data=(P/'candidate/native'/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256'], row['path']
for row in S['actual_source_fragments']:
    if 'full_file_sha256' in row:
        assert sha((P/row['path']).read_bytes())==row['full_file_sha256']
        continue
    data=(P/'composition/r14/native'/row['path']).read_text()
    fragment=data[data.index(row['start']):]
    if row['end'] is not None: fragment=fragment[:fragment.index(row['end'])]
    assert sha(fragment.encode())==row['fragment_sha256'], row['path']
composed=(P/'composition/r14/native/core/block/import/processor.go').read_text()
delta=(P/'composition/r14/COMPOSITION_DELTA.diff').read_text()
added=[line[1:] for line in delta.splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++')]
assert len(added)==12
assert composed.count(added[0])==1
block=''.join(added[1:])
assert composed.count(block)==1
restored=composed.replace(added[0],'',1).replace(block,'',1)
assert restored==(P/'candidate/native/core/block/import/processor.go').read_text()
receipt={'schema':'otzaria.root-origin-observation-review/1','verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':remote['head'],'git_blobs_independently_matched':94,'raw_result_sha256':sha((E/'RESULT.json').read_bytes()),'actual_leaf_cases':50,'pass':50,'fail':0,'skip':0,'every_leaf_started_and_passed_once':True,'raw_commands':len(result['commands']),'compiled_input_files':len(S['module_files']),'frozen_product_files':len(result['product_files']),'r14_inverse_exact':True,'eight_compiled_fragments_preserved':True,'native_executions':0,'prior_cases_reexecuted':0,'review_scope':'Observation-only source; full original-module compilation and native import, archive/account binding, complete failure drain, file remaps and durable map remain required.'}
(P/'audit/ROOT_UNIT_AND_SOURCE_VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
