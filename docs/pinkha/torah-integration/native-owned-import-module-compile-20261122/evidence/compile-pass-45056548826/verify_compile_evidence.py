"""Read-only verification of the sole already-retained native compile result."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[2]
EVIDENCE = ROOT / 'retained/downloaded-evidence'
GATE = WORK / 'native-owned-import-audit/gate-tree-binding-fix'
manifest = json.loads((GATE / 'EXECUTION_INPUTS.json').read_bytes())
result = json.loads((EVIDENCE / 'RESULT.json').read_bytes())
commands = json.loads((EVIDENCE / 'COMMANDS.json').read_bytes())
index = json.loads((EVIDENCE / 'EVIDENCE_INDEX.json').read_bytes())['files']
declared = json.loads((EVIDENCE / 'DECLARED_NATIVE_INPUTS.json').read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert result['status'] == 'PASS_COMPILE_ONLY'
assert result['control_head'] == '9e76d3c6868c0540636396e66ac9829e5f8dc14e'
assert result['execution_manifest_sha256'] == digest(GATE / 'EXECUTION_INPUTS.json')
assert len(index) == 34 and len({row['path'] for row in index}) == 34
assert {path.name for path in EVIDENCE.iterdir()} == {row['path'] for row in index} | {'EVIDENCE_INDEX.json'}
for row in index:
    path = EVIDENCE / row['path']
    assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
assert len(commands) == result['commands'] == 13
for row in commands:
    assert row['status'] == 'TERMINAL' and row['returncode'] == row['effective_returncode'] == 0
    assert row['timed_out'] is False and row['start_new_session'] is True
    assert row['pid'] == row['process_group_id']
    assert any(event.get('drained') is True for event in row['cleanup'])
    assert all(event.get('drained') is not False for event in row['cleanup'])
    for stream in ['stdout', 'stderr']:
        assert digest(EVIDENCE / row[stream]) == row[stream + '_sha256']
assert commands[11]['argv'] == result['compile_command']
assert result['compile_command'][1:6] == ['test', '-c', '-p', '2', '-o']
assert result['compile_command'][-1] == './core/block/import'
assert commands[12]['argv'][1:3] == ['version', '-m']
assert all(row['argv'][0] != result['compiled_binary']['path'] for row in commands)
assert result['tests_executed'] == result['native_imports_executed'] == 0
assert result['test_binary_executed'] is False and result['compiled_binary']['executed'] is False
assert result['prior_unit_cases_not_replayed'] == 50 and result['prior_compatibility_cases_not_replayed'] == 7
assert result['owned_unit_cases_not_replayed'] == 26
assert result['origin_commit'] == manifest['origin_commit']
assert result['origin_source_packet_tree'] == manifest['origin_source_packet_tree']
assert result['origin_packet_commit'] == manifest['origin_packet_commit']
assert result['origin_packet_tree'] == manifest['origin_packet_tree']
assert result['owned_source_commit'] == manifest['owned_source_commit']
assert result['owned_source_packet_tree'] == manifest['owned_source_packet_tree']
assert result['gate_input_readback'] == manifest['gate_inputs']
assert result['origin_input_readback'] == manifest['origin_inputs']
assert result['owned_input_readback'] == manifest['owned_inputs']
assert result['original_module_hashes'] == manifest['original_module_hashes']
assert result['post_compile_input_recheck'] is True
assert result['gofmt']['twenty_source_files_unchanged'] is True
assert result['owned_compiler_temp_removed'] is True
assert digest(EVIDENCE / 'TANTIVY_INPUTS_BEFORE.json') == digest(EVIDENCE / 'TANTIVY_INPUTS_AFTER.json')
assert json.loads((EVIDENCE / 'TANTIVY_INPUTS_BEFORE.json').read_bytes()) == manifest['expected_tantivy_inputs']
assert digest(EVIDENCE / 'DECLARED_NATIVE_INPUTS.json') == result['declared_native_inputs_sha256']
assert len(declared['files']) == result['declared_native_input_count'] == 9829
assert len({row['path'] for row in declared['files']}) == 9829
assert {row['path']: row['sha256'] for row in declared['required_product_test_coverage']} == manifest['final_product_hashes']
assert len(manifest['final_product_hashes']) == 20
compiled_root = commands[11]['cwd']
native_files = {row['path']: row for row in declared['files']}
owned = {row['path']: row for row in json.loads((WORK / 'native-owned-import-audit/composition/SOURCE_MANIFEST.json').read_bytes())}
for relative, expected in manifest['final_product_hashes'].items():
    if relative in owned:
        local = WORK / 'native-owned-import-audit/composition/native' / relative
    else:
        local = WORK / 'native-import-request-compat/packet/composition/r14/native' / relative
    assert digest(local) == expected == result['composed_source_hashes'][relative]
    observed = native_files[compiled_root + '/' + relative]
    assert observed['sha256'] == expected and observed['bytes'] == local.stat().st_size
assert (EVIDENCE / '01-go-version.stdout').read_text().strip() == 'go version go1.26.5 darwin/arm64'
assert 'Xcode 27.0' in (EVIDENCE / '02-xcode-version.stdout').read_text()
receipt = {
    'status': 'PASS_RETAINED_COMPILE_EVIDENCE_AND_EXACT_SOURCE_BINDING',
    'head': result['control_head'], 'run_id': 45056548826, 'run_attempt': 1,
    'artifact_id': 14767901351, 'result_sha256': digest(EVIDENCE / 'RESULT.json'),
    'indexed_payloads_verified': len(index), 'retained_evidence_files_including_index': len(index) + 1,
    'actual_commands_verified': len(commands), 'all_command_streams_and_drained_groups_verified': True,
    'declared_native_input_commitment_count': len(declared['files']),
    'declared_native_inputs_sha256': digest(EVIDENCE / 'DECLARED_NATIVE_INPUTS.json'),
    'twenty_local_products_match_native_declared_inputs': True,
    'input_readbacks': {'gate': 10, 'origin': 8, 'owned': 17},
    'go': result['go'], 'compile_argv': result['compile_command'],
    'compiled_binary': result['compiled_binary'],
    'linker_warning_retained': (EVIDENCE / '12-compile-original-importer.stderr').read_text(),
    'tests_executed': 0, 'native_imports_executed': 0,
    'historical_controls_preserved_without_replay': [50, 7, 26],
    'qualification': result['scope'],
    'limitations': ['The complete 9,829-file dependency inventory is a runner-observed hash commitment; external module contents are not separately copied into this evidence.',
                    'The compiled executable hash is observed by the original runner; executable bytes were not uploaded or executed.',
                    'New lifetime source files are separate and are not included in this compilation.'],
}
(ROOT / 'COMPILE_EVIDENCE_VERIFICATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ['status', 'actual_commands_verified', 'indexed_payloads_verified', 'declared_native_input_commitment_count', 'tests_executed', 'native_imports_executed']}))
