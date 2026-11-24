"""Reuse exact previously authenticated generation and changed-Swift receipts.

These are immutable evidence inputs, not reruns. In particular the aggregate
generator failure remains a failure; only its qualified output scope is reused.
"""
import json

from local_execution import require

HISTORICAL_SHA256 = {
    'generation': 'd7e1074b46a52d7d559304045110da3e13b40630208520566ff840bf12c357e7',
    'swift': 'd860dfdc8cbc620af2aa6bb71962f6364f5fb25a615a2900838e7b1ee128729e',
    'generation_tools': '0bd85cabdd7feb27502e774fbde1c2687456dbc95c9d9727b51b9d1290dca334',
    'generated_index': 'c38fe4efadaa1c4676084b8ca6303387b0efa61fa540ba4d9af00d67c8c85070',
}


def history_proofs(base, rows, exact_file):
    require(set(rows) == set(HISTORICAL_SHA256), 'Incomplete authenticated historical evidence')
    values = {}
    for name, digest in HISTORICAL_SHA256.items():
        require(rows[name]['sha256'] == digest, 'Previously authenticated receipt identity differs: ' + name)
        values[name] = json.loads(exact_file(base, rows[name]).read_bytes())
    generation, swift = values['generation'], values['swift']
    require(generation['aggregate_outcome_preserved'] == 'FAIL at missing-SDK Swift invocation'
            and generation['result']['status'] == 'FAIL'
            and generation['all_744_outputs_stable'] is True
            and generation['result']['native_source_tree'] == swift['generated_native_tree'],
            'Historical generation outcome/source differs')
    require(swift['status'] == 'PASS' and swift['actual_input_files'] == 689
            and len(swift['primary_paths']) == 2 and swift['swift_typecheck_invocations'] == 1
            and swift['generator_invocations'] == 0 and swift['full_sdk_typechecked'] is False
            and swift['generated_index_sha256'] == HISTORICAL_SHA256['generated_index']
            and swift['run']['id'] == 45269355714 and swift['run']['conclusion'] == 'success'
            and swift['artifact']['digest'] == 'sha256:1f4074fe76a3b77d955d749e3169e2a8f444b849be0b834a60ad1c10c5893d34',
            'Historical changed-Swift qualification differs')
    counts = {name: len(value) for name, value in values['generated_index'].items()}
    require(counts == {'native': 11, 'swift': 696, 'middleware': 37}, 'Original generated output counts differ')
    go = [item for item in values['generation_tools']['tools'] if item['path'] == 'go']
    require(len(go) == 1, 'Qualified original Go compiler identity is ambiguous')
    return {
        'generation_qualification': {
            'status': 'PASS', 'output_counts': counts,
            'aggregate_producer_outcome': 'FAIL', 'generators_replayed_by_abi': 0,
            'generated_index_sha256': HISTORICAL_SHA256['generated_index'],
            'native_generated_tree': swift['generated_native_tree'],
            'go_compiler_driver': go[0],
            'source_receipt_sha256': HISTORICAL_SHA256['generation'],
            'artifact_sha256': swift['generation_artifact_sha256'],
            'source_sha': swift['generation_source'], 'run_id': swift['generation_run']},
        'changed_swift_qualification': {
            'status': 'PASS', 'primary_count': len(swift['primary_paths']),
            'input_files': swift['actual_input_files'],
            'typecheck_invocations': swift['swift_typecheck_invocations'],
            'generated_index_sha256': swift['generated_index_sha256'],
            'generation_replayed': False, 'full_sdk_typechecked': swift['full_sdk_typechecked'],
            'actual_compiler_context': swift['actual_compiler_context'],
            'source_receipt_sha256': HISTORICAL_SHA256['swift'],
            'artifact': swift['artifact'], 'run': swift['run']},
    }
