from pathlib import Path
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / 'schema_rpc_copy_fix/packet'
E = HERE / 'extracted'
read = lambda p: json.loads(p.read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()
archive_path = HERE / 'Heart_Schema_RPC_Copy_Generation_45055852172.zip'
raw = archive_path.read_bytes()
assert len(raw) == 11898059 and sha(raw) == '8d76ee6f186f32985c276dba1f79e2ee82e0db7c1ad9c259ce4c2350b43fc769'
index = read(E / 'EVIDENCE_INDEX.json')['files']
assert len(index) == len({r['path'] for r in index}) == 2986
with zipfile.ZipFile(archive_path) as z:
    assert z.testzip() is None
    names = {n for n in z.namelist() if not n.endswith('/')}
    assert len(z.namelist()) == len(set(z.namelist()))
    assert names == {r['path'] for r in index} | {'EVIDENCE_INDEX.json'}
    for row in index:
        b = z.read(row['path'])
        assert b == (E / row['path']).read_bytes()
        assert len(b) == row['bytes'] and sha(b) == row['sha256']
r = read(E / 'RESULT.json')
assert r['status'] == 'FAIL' and r['commands'] == 33
assert r['control_head'] == 'ca6eb576d0ac105ef260bc2703b7d0dc186a8656'
assert r['error'] == 'owned command failed: baseline-typecheck-generated-swift'
assert r['owned_work_removed'] is r['owned_command_groups_drained'] is True
assert r['full_sdk_typecheck'] is r['ios_build'] is r['integration_authority'] is False
assert r['native_tests_executed'] == 0
commands = read(E / 'COMMANDS.json')
assert len(commands) == 33
for i, command in enumerate(commands):
    assert command['status'] == 'TERMINAL' and command['start_new_session'] is True
    assert command['timed_out'] is False and command['pid'] == command['process_group_id']
    assert command['cleanup'][-1]['drained'] is True
    assert not any(x.get('drained') is False for x in command['cleanup'])
    assert command['returncode'] == command['effective_returncode'] == (1 if i == 32 else 0)
    for stream in ('stdout','stderr'):
        assert sha((E / command[stream]).read_bytes()) == command[stream + '_sha256']
assert commands[29]['label'] == 'baseline-original-native-generation'
assert commands[30]['label'] == 'baseline-original-swift-generation'
assert commands[31]['label'] == 'baseline-compile-generated-go'
assert commands[31]['argv'][-3:] == ['build','./pb','./pb/service']
assert commands[-1]['label'] == 'baseline-typecheck-generated-swift'
error = (E / commands[-1]['stderr']).read_text()
assert "no such module 'SwiftProtobuf'" in error
assert commands[-1]['argv'][5] == '-I' and commands[-1]['argv'][6].endswith('/.build/release/Modules')
for name in ('BASELINE_SDK_COPY.json','CANDIDATE_SDK_COPY.json'):
    copy = read(E / name)
    assert copy['status'] == 'EXACT_PRIVATE_COPY' and copy['head'] == '3be6ecab805b17e2c90fee897fdab45a0b03bfdc'
    assert copy['files'] == 1038 and copy['bytes'] == 20082375
    assert copy['source_and_copy_unchanged_after_readback'] is copy['file_identities_disjoint'] is True
    assert copy['lazy_fetch_disabled_for_git_reads'] is True and copy['remote_clone_or_hydration'] is False
assert read(E / 'BASELINE_SDK_COPY.json')['inventory_sha256'] == read(E / 'CANDIDATE_SDK_COPY.json')['inventory_sha256']
mbytes = (PACKET / 'EXECUTION_INPUTS.json').read_bytes()
assert sha(mbytes) == r['manifest_sha256'] == '48c43f21ac8f31b3c6bd7022e838273046c3baa001813bb598be6f4aaf35c7a6'
m = json.loads(mbytes)
for row in m['control_inputs']:
    b = (PACKET / row['path']).read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256']
assert len(m['control_inputs']) == 12
generated = read(E / 'GENERATED_OUTPUT_INDEX.json')
failure = read(E / 'FAILURE_OUTPUT_INDEX.json')['lanes']
assert set(generated) == {'baseline','tracked'} and set(failure) == {'baseline','candidate'}
counts = {}
for family, rows in generated['baseline'].items():
    assert len(rows) == len({row['path'] for row in rows})
    counts[family] = len(rows)
    failure_family = 'heart' if family == 'native' else 'swift'
    generated_family = 'native' if family == 'native' else 'swift'
    failed_rows = {row['path']:row for row in failure['baseline'][failure_family]}
    for row in rows:
        b = (E / 'generated/baseline' / generated_family / row['path']).read_bytes()
        assert len(b) == row['bytes'] and sha(b) == row['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest() == row['git_blob']
        assert row == failed_rows[row['path']]
        assert b == (E / 'failure-time/baseline' / failure_family / row['path']).read_bytes()
    if family in ('native','swift'):
        tracked = {row['path']:row for row in generated['tracked'][family]}
        assert {row['path']:row for row in rows} == tracked
        for row in rows:
            assert (E / 'generated/tracked' / family / row['path']).read_bytes() == (E / 'generated/baseline' / family / row['path']).read_bytes()
assert counts == {'middleware':37,'native':11,'swift':693}
receipt = {'status':'PASS_ROOT_ORIGINAL_RPC_BASELINE_FAILURE_REVIEW',
    'run_id':45055852172,'attempt':1,'head':r['control_head'],
    'artifact_id':14768420988,'archive_bytes':len(raw),'archive_sha256':sha(raw),
    'payloads_verified':2986,'crc':True,'commands':33,'successful_commands':32,'failed_commands':1,
    'command_streams_verified':66,'owned_groups_drained':33,'owned_work_removed':True,
    'local_control_inputs_verified':12,
    'private_materialized_copies':{'count':2,'files_each':1038,'bytes_each':20082375},
    'baseline_generated_and_failure_time_rows_identical':counts,
    'baseline_tracked_drift':{'native':0,'swift':0},
    'baseline_go_packages':'Actual go build ./pb ./pb/service PASS',
    'swift_failure':{'error':"no such module 'SwiftProtobuf'",'search_path':commands[-1]['argv'][6],
        'precise_built_module_location':'NOT_RETAINED_OR_OBSERVED','duration_seconds':commands[-1]['duration_seconds']},
    'candidate_generation':'NOT_REACHED; candidate failure-time files are not generated-candidate acceptance',
    'limitations':['Compiled SwiftProtobuf module tree and generator binaries were not archived; executable fingerprints do not replace those bytes.',
        'Final source/tool immutability checks were not reached. Their absence is preserved.',
        'Original generators and baseline Go compile succeeded; Swift baseline typecheck, candidate generation/typechecks, fullSDK and native integration remain open.'],
    'verifier_layout_correction':'Initial root verifier assumed separate middleware directories in failure-time and generated namespaces and stopped at each. The actual37 middleware rows live under swift in both namespaces; only the verifier mappings were corrected, with original artifact untouched.',
    'new_controls_or_artifact_downloads_by_root':0,'native_tests_executed':0}
(HERE/'ROOT_BASELINE_FAILURE_REVIEW.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','payloads_verified','commands','successful_commands','command_streams_verified','baseline_generated_and_failure_time_rows_identical','baseline_tracked_drift')}))
