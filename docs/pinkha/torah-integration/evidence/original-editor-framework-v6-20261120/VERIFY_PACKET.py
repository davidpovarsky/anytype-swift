#!/usr/bin/env python3
"""Read-only proof replay for the v6 signing candidate; no runtime/test execution."""
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

PARENT = 'e147e0030edf7d9cf487522738f9d6d34f59d591'
EXPECTED = {
 '.github/workflows/pinkha-original-editor-framework.yml',
 'Tools/OriginalEditor/amplitude_simulator_signing.json',
 'Tools/OriginalEditor/amplitude_simulator_signing.py',
 'Tools/OriginalEditor/framework_profile.json',
 'Tools/OriginalEditor/framework_profile.py',
 'Tools/OriginalEditor/run_framework_acceptance.py',
 'Tools/OriginalEditor/test_amplitude_simulator_signing.py',
 'Tools/OriginalEditor/test_framework.py',
 'Tools/PinkhaNativeDerived/install_verified_heart.py',
}

def require(value, message):
    if not value:
        raise ValueError(message)

def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()}

def unzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and archive.testzip() is None, 'ZIP CRC/inventory differs')
        require(all(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
                    and chr(92) not in name for name in names), 'Unsafe archive path')
        return {name: archive.read(name) for name in names}

def declarations(items):
    result = set()
    for path, data in items.items():
        if path.startswith('Tools/OriginalEditor/test_') and path.endswith('.py'):
            for cls in ast.parse(data).body:
                if isinstance(cls, ast.ClassDef):
                    for method in cls.body:
                        if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                            result.add(PurePosixPath(path).stem + '.' + cls.name + '.' + method.name)
    return result

def cases(raw):
    return re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. (ok|FAIL|ERROR)$', raw.decode())

def verify(directory):
    directory = Path(directory)
    index = json.loads((directory / 'PACKET_INDEX.json').read_bytes())
    require(index['parent'] == PARENT and index['scope'] == 'PYTHON_ONLY_APPLE_SIGNING_NOT_RUN',
            'Wrong packet scope or parent')
    for path, expected in index['files'].items():
        require(PurePosixPath(path).name == path and record((directory / path).read_bytes()) == expected,
                'Sealed packet member differs: ' + path)
    projection = unzip((directory / 'source-projections.zip').read_bytes())
    old = {name.removeprefix('baseline/'): data for name, data in projection.items() if name.startswith('baseline/')}
    new = {name.removeprefix('candidate/'): data for name, data in projection.items() if name.startswith('candidate/')}
    require(len(old) == 29 and len(new) == 32 and len(projection) == 61, 'Wrong complete source inventory')
    authority = json.loads((directory / 'SOURCE_AUTHORITY.json').read_bytes())
    require(authority['source'] == PARENT and authority['tree'] == '62f7bea1455a571bf2fd4bae694dfc7bd4fdc06e'
            and authority['underlying_original_source'] == '196459fc9fa943f90e5c7f256545f94083e373e3'
            and len(authority['original_inputs']) == 29, 'Wrong canonical baseline')
    require({row['path'] for row in authority['original_inputs']} == set(old), 'Wrong canonical paths')
    for row in authority['original_inputs']:
        actual = record(old[row['path']])
        require(actual['git_blob'] == row['canonical_git_blob']
                and all(actual[key] == row[key] for key in actual), 'Canonical original bytes differ')
    changed = {path for path in set(old) | set(new) if old.get(path) != new.get(path)}
    require(changed == EXPECTED, 'Unexpected source delta')
    edits = json.loads((directory / 'SOURCE_EDITS.json').read_bytes())
    for path in changed & set(old):
        restored = new[path].decode()
        for edit in reversed([edit for edit in edits if edit['path'] == path]):
            require(restored.count(edit['new']) == edit['count'], 'Inverse edit match differs')
            restored = restored.replace(edit['new'], edit['old'], edit['count'])
        require(restored.encode() == old[path], 'Whole existing source inverse differs: ' + path)
    for path in old:
        if path.startswith('Tools/OriginalEditor/test_'):
            expected = old[path]
            if path.endswith('/test_framework.py'):
                expected = expected.replace(b'framework-v5-reviewed', b'framework-v6-reviewed')
            require(new[path] == expected, 'An original test changed beyond its branch literal')
    old_ids, new_ids = declarations(old), declarations(new)
    require(len(old_ids) == 99 and len(new_ids) == 131 and old_ids < new_ids, 'Original case inventory differs')
    preservation = json.loads((directory / 'PRESERVATION.json').read_bytes())
    require(set(preservation['candidate_inputs']) == set(new), 'Candidate input index differs')
    for path, data in new.items():
        require(record(data) == preservation['candidate_inputs'][path], 'Candidate source bytes differ')
    raw = unzip((directory / 'raw-controls.zip').read_bytes())
    final_prefix = 'runs/candidate-final/'
    before = json.loads(raw[final_prefix + 'INPUTS_BEFORE.json'])
    after = json.loads(raw[final_prefix + 'INPUTS_AFTER.json'])
    require(before == after and set(before) == set(new), 'Final whole inputs changed')
    require(all(before[path] == record(new[path])['sha256'] for path in new), 'Final sources differ from execution')
    final = json.loads(raw[final_prefix + 'RESULT.json'])
    actual = cases(raw[final_prefix + 'stderr.log'])
    require(final['returncode'] == 0 and final['executed'] == final['passed'] == 131
            and final['source_unchanged'] is True
            and len(actual) == len({full for _, full, _ in actual}) == 131
            and {full for _, full, _ in actual} == new_ids
            and all(outcome == 'ok' for _, _, outcome in actual)
            and raw[final_prefix + 'stderr.log'].decode().rstrip().endswith('OK'),
            'Actual final 131-case result differs')
    for method in ['test_whole_driver_keeps_strict_gate_and_exact_transformed_consumer_inputs',
                   'test_other_framework_signature_failure_still_blocks_consumer_and_boot',
                   'test_corrupt_signer_stops_original_driver_before_strict_gate_or_consumer']:
        trace = json.loads(raw[final_prefix + 'flow/' + method + '.json'])
        require(trace['apple_builds_executed'] == trace['native_tests_executed'] == 0
                and trace['receipt']['status'] == 'FAIL'
                and trace['receipt']['verified_runtime_observations'] == [], 'Synthetic flow earned native credit')
    first = json.loads(raw['runs/candidate-attempt1/RESULT.json'])
    first_cases = cases(raw['runs/candidate-attempt1/stderr.log'])
    require(first['returncode'] == 0 and first['source_unchanged'] is True
            and len(first_cases) == 131 and all(outcome == 'ok' for _, _, outcome in first_cases),
            'Earlier complete passing observation differs')
    red = json.loads(raw['runs/fat-gap-red/RESULT.json'])
    red_cases = cases(raw['runs/fat-gap-red/stderr.log'])
    require(red['returncode'] == 1 and len(red_cases) == 1 and red_cases[0][2] == 'FAIL'
            and red_cases[0][0] == 'test_extra_alignment_size_zero_fat_gap_is_refused'
            and b'AssertionError: ValueError not raised' in raw['runs/fat-gap-red/stderr.log'],
            'Discriminating prior rejection failure differs')
    prior_helper = raw['runs/fat-gap-red/helper-before.py']
    replacement = (b'and offset == (previous_end + (1 << alignment) - 1) // (1 << alignment) * (1 << alignment)',
                   b'and offset >= previous_end and offset % (1 << alignment) == 0')
    helper = new['Tools/OriginalEditor/amplitude_simulator_signing.py']
    require(helper.count(replacement[0]) == 1 and helper.replace(*replacement) == prior_helper,
            'FAT rejection is not the exact one-predicate correction')
    pin = json.loads(new['Tools/OriginalEditor/amplitude_simulator_signing.json'])
    upstream = new[pin['archive_path']]
    require(record(upstream)['sha256'] == pin['archive_sha256']
            == '2c0fbe60170efdf0b634ae73298803880098e1d352c9afef2baface15b45070c'
            and len(upstream) == 1964793, 'Pinned original fixture archive differs')
    archive = unzip(upstream)
    prefix = 'AmplitudeCore.xcframework/ios-arm64_x86_64-simulator/AmplitudeCore.framework/'
    files = {path.removeprefix(prefix): data for path, data in archive.items()
             if path.startswith(prefix) and not path.endswith('/')}
    require(len(files) == len(pin['files']) == 13 and set(files) == set(pin['files']), 'Pinned 13-file inventory differs')
    for path, data in files.items():
        require(len(data) == pin['files'][path]['bytes']
                and record(data)['sha256'] == pin['files'][path]['sha256'], 'Pinned original bytes differ')
    peer = unzip((directory / 'peer-macho-review.zip').read_bytes())
    require('STATIC_INSPECTION.json' in peer and len(peer) == 6, 'Original primary-source review differs')
    publication = json.loads((directory / 'SOURCE_PUBLICATION.json').read_bytes())
    require(publication['parent'] == PARENT and set(publication['changed_paths']) == EXPECTED
            and publication['source_only'] is True, 'Isolated source publication differs')
    return {'verification': 'PASS_READ_ONLY_V6_SIGNING_SOURCE_AND_EVIDENCE',
            'source_commit': publication['commit'], 'parent': PARENT,
            'canonical_baseline_inputs': 29, 'candidate_inputs': 32,
            'existing_whole_file_inverses': 6, 'added_ci_paths': 3, 'total_changed_ci_paths': 9,
            'original_cases_retained': 99, 'new_signing_controls': 32,
            'actual_final_python': {'executed': 131, 'passed': 131, 'failed': 0, 'errors': 0},
            'actual_initial_python': {'executed': 131, 'passed': 131},
            'actual_discriminating_red': {'executed': 1, 'failed': 1},
            'source_before_after': 'EQUAL', 'native_signing_qualification': 'NOT_RUN',
            'swift_or_apple_tools_run_by_replay': 0,
            'archives_verified': 4, 'source_zip_members': len(projection),
            'raw_zip_members': len(raw), 'peer_zip_members': len(peer),
            'full_original_gates_required': True}

if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent),
                     indent=2, sort_keys=True))
