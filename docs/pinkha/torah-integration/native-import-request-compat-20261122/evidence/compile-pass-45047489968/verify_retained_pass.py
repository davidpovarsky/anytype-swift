"""Read-only audit of the sole retained compile pass; never executes the binary."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'retained/downloaded-evidence'
PROJECT = ROOT.parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def check_row(path, row):
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], str(path)
    if 'git_blob' in row:
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob'], str(path)

index = read(EVIDENCE / 'EVIDENCE_INDEX.json')['files']
assert len(index) == len({r['path'] for r in index}) == 31
assert {p.name for p in EVIDENCE.iterdir()} == {r['path'] for r in index} | {'EVIDENCE_INDEX.json'}
for row in index: check_row(EVIDENCE / row['path'], row)
result = read(EVIDENCE / 'RESULT.json')
assert sha(EVIDENCE / 'RESULT.json') == '96705538739843ddd9cfffd9b276de85a5ecf74af717b9d520d3a9874a1ed121'
assert result['status'] == 'PASS_COMPILE_ONLY' and result['control_head'] == '32adc5c78db70a586a81c761de19efc46298bb06'
assert result['tests_executed'] == result['native_imports_executed'] == 0 and result['test_binary_executed'] is False
commands = read(EVIDENCE / 'COMMANDS.json')
assert len(commands) == result['commands'] == 12
for command in commands:
    assert command['status'] == 'TERMINAL' and command['returncode'] == command['effective_returncode'] == 0
    assert command['timed_out'] is False and command['start_new_session'] is True
    assert command['cleanup'][-1]['event'] == 'OWNED_GROUP_ABSENT_AFTER_WAIT' and command['cleanup'][-1]['drained'] is True
    for stream in ['stdout', 'stderr']:
        assert sha(EVIDENCE / command[stream]) == command[stream + '_sha256']
compile_command = next(row for row in commands if row['label'] == 'compile-original-importer')
assert compile_command['argv'] == result['compile_command']
assert compile_command['argv'][1:] == ['test', '-c', '-p', '2', '-o', result['compiled_binary']['path'], './core/block/import']
assert commands[-1]['argv'] == [result['go']['path'], 'version', '-m', result['compiled_binary']['path']]
assert not any(row['argv'][0] == result['compiled_binary']['path'] for row in commands)

manifest_path = PROJECT / 'gate/EXECUTION_INPUTS.json'
manifest = read(manifest_path)
assert sha(manifest_path) == result['execution_manifest_sha256']
assert result['gate_input_readback'] == manifest['gate_inputs'] and result['origin_input_readback'] == manifest['origin_inputs']
for row in result['gate_input_readback']:
    candidates = [PROJECT / 'gate' / row['path'], PROJECT.parent / 'native-import-compile/candidate' / row['path']]
    path = next(p for p in candidates if p.is_file())
    check_row(path, row)
for row in result['origin_input_readback']:
    check_row(PROJECT / 'packet' / row['path'], row)
declared = read(EVIDENCE / 'DECLARED_NATIVE_INPUTS.json')
assert len(declared['files']) == len({r['path'] for r in declared['files']}) == result['declared_native_input_count'] == 9821
assert sha(EVIDENCE / 'DECLARED_NATIVE_INPUTS.json') == result['declared_native_inputs_sha256']
assert {r['path']:r['sha256'] for r in declared['required_product_test_coverage']} == manifest['six_product_hashes']
for name, expected in manifest['six_product_hashes'].items():
    assert result['composed_source_hashes'][name] == expected
    actual = [r for r in declared['files'] if r['path'].endswith('/Heart-Import-Compile/' + name)]
    assert len(actual) == 1 and actual[0]['sha256'] == expected
assert result['original_module_hashes'] == manifest['original_module_hashes']
assert (EVIDENCE / 'TANTIVY_INPUTS_BEFORE.json').read_bytes() == (EVIDENCE / 'TANTIVY_INPUTS_AFTER.json').read_bytes()
assert read(EVIDENCE / 'TANTIVY_INPUTS_BEFORE.json') == manifest['expected_tantivy_inputs']
assert result['post_compile_input_recheck'] is True and result['owned_compiler_temp_removed'] is True
assert result['go']['version'] == 'go version go1.26.5 darwin/arm64'
assert result['compiled_binary']['executed'] is False
archive = PROJECT / 'evidence/run-45047489968-intake.zip'
assert archive.stat().st_size == 1785333 and sha(archive) == 'b1738f18c2a42ca8095ad91a79f8ef652b2c53d43256414c08d0e22b4474acb1'
receipt = dict(status='PASS_RETAINED_COMPILE_AND_INPUT_AUDIT', run_id=45047489968,
    source=result['control_head'], result_sha256=sha(EVIDENCE / 'RESULT.json'),
    evidence_index_sha256=sha(EVIDENCE / 'EVIDENCE_INDEX.json'), indexed_payloads=31,
    commands_verified=12, declared_input_commitments=9821, exact_gate_inputs=8, exact_origin_inputs=8,
    actual_original_module_compile_seconds=compile_command['duration_seconds'],
    original_module_and_tantivy_unchanged=True, compiled_binary=result['compiled_binary'],
    test_executions=0, import_executions=0, prior_control_replays=0, new_artifact_downloads=0,
    scope='Original module compile/link compatibility only. Preserves original50 and request7 evidence. Newly drafted owned upload/import layer is outside this compile closure; native lifetime, mapping authority, body readback and ACK remain open.')
(ROOT / 'RETAINED_PASS_VERIFICATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
