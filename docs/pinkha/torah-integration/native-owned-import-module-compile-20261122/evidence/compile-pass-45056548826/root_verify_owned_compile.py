from pathlib import Path
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
E = HERE / 'retained/downloaded-evidence'
GATE = WORK / 'native-owned-import-audit/gate-tree-binding-fix'
read = lambda p: json.loads(p.read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()
intake = read(HERE / 'INTAKE.json')
raw = (HERE / 'raw-retained-intake.zip').read_bytes()
assert len(raw) == intake['bytes'] == 1793738
assert sha(raw) == intake['sha256'] == '3c15055682def6dfae0cfc685d170d3f849918b99d67fbe6a09334371896e7a9'
with zipfile.ZipFile(HERE / 'raw-retained-intake.zip') as z:
    assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == 51
    assert set(z.namelist()) == {row['path'] for row in intake['files']}
    for row in intake['files']:
        data = z.read(row['path'])
        assert data == (HERE / 'retained' / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
run = read(HERE / 'retained/RUN_TERMINAL_OR_LAST.json')
assert run['id'] == 45056548826 and run['run_attempt'] == 1
assert run['head_sha'] == '9e76d3c6868c0540636396e66ac9829e5f8dc14e'
assert run['status'] == 'completed' and run['conclusion'] == 'success'
arts = read(HERE / 'retained/ARTIFACTS.json')['artifacts']
assert len(arts) == 1 and arts[0]['id'] == 14767901351
assert arts[0]['size_in_bytes'] == 1734312
assert arts[0]['digest'] == 'sha256:2a1542ed11ad74df9290199aad6a801813efb64d3702101f6550e2497e47777b'
index = read(E / 'EVIDENCE_INDEX.json')['files']
assert len(index) == len({r['path'] for r in index}) == 34
assert {p.name for p in E.iterdir() if p.is_file()} == {r['path'] for r in index} | {'EVIDENCE_INDEX.json'}
for row in index:
    data = (E / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
r = read(E / 'RESULT.json')
assert sha((E / 'RESULT.json').read_bytes()) == '1d5e67148a33da422202ee12f791c05abeb98670441c430a959fa3610e2c36e9'
assert r['status'] == 'PASS_COMPILE_ONLY' and r['control_head'] == run['head_sha']
commands = read(E / 'COMMANDS.json')
assert len(commands) == r['commands'] == 13
assert len({c['pid'] for c in commands}) == 13
for command in commands:
    assert command['status'] == 'TERMINAL'
    assert command['returncode'] == command['effective_returncode'] == 0
    assert command['timed_out'] is False and command['start_new_session'] is True
    assert command['pid'] == command['process_group_id'] > 0
    assert command['cleanup'][-1]['drained'] is True
    assert not any(c.get('drained') is False for c in command['cleanup'])
    for stream in ('stdout', 'stderr'):
        assert sha((E / command[stream]).read_bytes()) == command[stream + '_sha256']
compile_command = commands[11]
assert compile_command['argv'] == r['compile_command']
assert compile_command['argv'] == [r['go']['path'], 'test', '-c', '-p', '2', '-o', r['compiled_binary']['path'], './core/block/import']
assert commands[12]['argv'] == [r['go']['path'], 'version', '-m', r['compiled_binary']['path']]
assert not any(c['argv'][0] == r['compiled_binary']['path'] for c in commands)
assert not any(row['path'].endswith('/original-importer.test') for row in intake['files'])
assert r['tests_executed'] == r['native_imports_executed'] == 0
assert r['test_binary_executed'] is r['compiled_binary']['executed'] is False
assert [r[k] for k in ('prior_unit_cases_not_replayed', 'prior_compatibility_cases_not_replayed', 'owned_unit_cases_not_replayed')] == [50, 7, 26]
manifest_bytes = (GATE / 'EXECUTION_INPUTS.json').read_bytes()
assert sha(manifest_bytes) == r['execution_manifest_sha256'] == '376af3e7d1dfbcc4729fbb7dc57f67c97e8a1c376e28021577e9c3e1fba1f4cf'
m = json.loads(manifest_bytes)
readback_counts = {}
for category, base in [('gate', GATE), ('origin', WORK / 'native-import-request-compat/packet'),
                       ('owned', WORK / 'native-owned-import-audit/packet')]:
    rows = m[category + '_inputs']
    assert rows == r[category + '_input_readback']
    for row in rows:
        data = (base / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob']
    readback_counts[category] = len(rows)
assert readback_counts == {'gate': 10, 'origin': 8, 'owned': 17}
for key in ('origin_commit', 'origin_source_packet_tree', 'origin_packet_commit', 'origin_packet_tree',
            'owned_source_commit', 'owned_source_packet_tree', 'original_module_hashes'):
    assert r[key] == m[key]
assert r['post_compile_input_recheck'] is True and r['owned_compiler_temp_removed'] is True
assert r['gofmt']['twenty_source_files_unchanged'] is True
assert (E / 'TANTIVY_INPUTS_BEFORE.json').read_bytes() == (E / 'TANTIVY_INPUTS_AFTER.json').read_bytes()
assert read(E / 'TANTIVY_INPUTS_BEFORE.json') == m['expected_tantivy_inputs']
origin = read(E / 'SOURCE_OVERLAY.json')
owned = read(E / 'OWNED_SOURCE_OVERLAY.json')
assert len(origin['files']) == 6 and len(owned['files']) == 15
assert origin['original_commit'] == owned['original_commit'] == r['heart_base']
composed = {row['path']: row['after_sha256'] for row in origin['files']}
overlaps = []
for row in owned['files']:
    if row['path'] in composed:
        assert row['before_sha256'] == composed[row['path']]
        overlaps.append(row['path'])
    composed[row['path']] = row['after_sha256']
assert overlaps == ['core/block/import/processor.go']
assert len(composed) == 20 and composed == m['final_product_hashes']
declared_bytes = (E / 'DECLARED_NATIVE_INPUTS.json').read_bytes()
assert sha(declared_bytes) == r['declared_native_inputs_sha256']
declared = json.loads(declared_bytes)
native = {row['path']: row for row in declared['files']}
assert len(native) == len(declared['files']) == r['declared_native_input_count'] == 9829
assert {row['path']: row['sha256'] for row in declared['required_product_test_coverage']} == composed
owned_paths = {row['path'] for row in owned['files']}
for path, digest in composed.items():
    base = WORK / ('native-owned-import-audit/packet/composition/native' if path in owned_paths else 'native-import-request-compat/packet/composition/r14/native')
    data = (base / path).read_bytes()
    observed = native[compile_command['cwd'] + '/' + path]
    assert sha(data) == digest == observed['sha256'] == r['composed_source_hashes'][path]
    assert len(data) == observed['bytes']
assert (E / '01-go-version.stdout').read_text().strip() == 'go version go1.26.5 darwin/arm64'
assert (E / '02-xcode-version.stdout').read_text().startswith('Xcode 27.0\n')
receipt = {
    'status': 'PASS_ROOT_ORIGINAL_OWNED_COMPILE_EVIDENCE_REVIEW',
    'run_id': run['id'], 'head': run['head_sha'], 'attempt': 1,
    'verified_retained_mirror': {'bytes': len(raw), 'sha256': sha(raw), 'members': 51, 'crc': True},
    'original_actions_zip_metadata_only': {'artifact_id': 14767901351, 'bytes': 1734312,
        'sha256': arts[0]['digest'].removeprefix('sha256:'),
        'distinction': 'The original observer downloaded/extracted once; root verifies the retained51-file mirror. The original Actions ZIP bytes are not retained in this mirror and are not independently rehashed.'},
    'indexed_payloads': 34, 'owned_commands': 13, 'command_streams': 26, 'all_owned_groups_drained': True,
    'local_source_readbacks_verified': readback_counts, 'native_declared_input_commitments': 9829,
    'all_twenty_product_bytes_bound_to_native_compiler_inputs': True,
    'overlay_composition': '6 original +15 owned; processor preimage matches the original overlay, yielding20unique final files',
    'compile_seconds': compile_command['duration_seconds'], 'go': r['go'],
    'compiled_binary_runner_observation': r['compiled_binary'],
    'original_modules_and_tantivy_preserved': True,
    'tests_executed': 0, 'imports_executed': 0, 'preserved_old_controls': [50, 7, 26],
    'scope': 'Actual original-module compile/link compatibility for the reviewed20files; new lifetime source, import execution, persisted semantics and native UI acceptance remain open.',
    'linker_warning': (E / '12-compile-original-importer.stderr').read_text(),
    'root_additional_actions_downloads': 0, 'root_test_replays': 0,
}
(HERE / 'ROOT_OWNED_COMPILE_PASS_REVIEW.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k:receipt[k] for k in ('status','indexed_payloads','owned_commands','command_streams','local_source_readbacks_verified','all_twenty_product_bytes_bound_to_native_compiler_inputs','compile_seconds','tests_executed')}))
