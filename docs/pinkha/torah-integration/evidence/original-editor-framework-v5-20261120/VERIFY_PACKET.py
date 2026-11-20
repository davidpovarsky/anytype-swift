#!/usr/bin/env python3
"""Replay source preservation and observed Python results without running tests."""
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

V4 = 'codex/otzaria-original-editor-framework-v4-reviewed-20261120'
V5 = 'codex/otzaria-original-editor-framework-v5-reviewed-20261120'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def unzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and archive.testzip() is None, 'Duplicate or corrupt archive')
        for name in names:
            p = PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'Unsafe archive path')
        return {name: archive.read(name) for name in names}


def methods(source):
    return sorted(n.name for n in ast.walk(ast.parse(source))
                  if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))


def verify(directory):
    directory = Path(directory)
    index = json.loads((directory / 'PACKET_INDEX.json').read_bytes())
    require(index['source'] == 'be2856140b1a5084176d325261dace7e2903a3e1', 'Wrong candidate source')
    for name, expected in index['files'].items():
        require(PurePosixPath(name).name == name, 'Unexpected packet path')
        require(record((directory / name).read_bytes()) == expected, 'Sealed packet file differs: ' + name)
    projections = unzip((directory / 'source-projections.zip').read_bytes())
    raw = unzip((directory / 'raw-controls.zip').read_bytes())
    source = lambda prefix: {n[len(prefix):]: b for n, b in projections.items() if n.startswith(prefix)}
    old, new, intermediate = source('baseline/'), source('candidate/'), source('candidate-before-branch-bindings/')
    require(len(old) == 26 and len(new) == len(intermediate) == 27, 'Source projection inventory differs')
    authority = json.loads((directory / 'SOURCE_AUTHORITY.json').read_bytes())
    require(authority['source'] == '962d050eb36b2511616c771b08d92a78b64d2349'
            and authority['failure_docs'] == '99ce9f9df4961b06ede70b3081d62837f5907e67', 'Wrong authentic baseline')
    require(len(authority['original_inputs']) == 25 and len(authority['auxiliary_canonical_inputs']) == 1,
            'Wrong canonical input count')
    for row in authority['original_inputs']:
        actual = record(old[row['path']])
        require(actual['git_blob'] == row['canonical_git_blob'] and actual['sha256'] == row['sha256']
                and actual['bytes'] == row['bytes'], 'Actual source admission bytes differ')
    for row in authority['auxiliary_canonical_inputs']:
        require(record(old[row['path']]) == {k: row[k] for k in ['bytes', 'sha256', 'git_blob']},
                'Original budget evidence differs')
    preservation = json.loads((directory / 'PRESERVATION.json').read_bytes())
    actual_changes = {p for p in set(old) | set(new) if old.get(p) != new.get(p)}
    require(len(actual_changes) == 8 and actual_changes == {r['path'] for r in preservation['changed_paths']},
            'Changed path set differs')
    for row in preservation['changed_paths']:
        p = row['path']
        require(row['before'] == (record(old[p]) if p in old else None) and row['after'] == record(new[p]),
                'Changed bytes differ')
    for path in ['.github/workflows/pinkha-original-editor-framework.yml', 'Tools/OriginalEditor/test_framework.py']:
        require(new[path].replace(V5.encode(), V4.encode()) == old[path], 'Original workflow/control changed')
    path = 'Tools/OriginalEditor/framework_profile.py'
    inverse = new[path].decode().replace(V4, 'codex/otzaria-original-editor-framework-v3-reviewed-20261120').replace(V5, V4)
    require(inverse.encode() == old[path], 'Original profile code changed beyond exact route choices')
    path = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
    extra = (",\n                             '" + V5 + "'").encode()
    require(new[path].count(extra) == 1 and new[path].replace(extra, b'', 1) == old[path], 'Original installer changed')
    a, b = json.loads(old['Tools/OriginalEditor/framework_profile.json']), json.loads(new['Tools/OriginalEditor/framework_profile.json'])
    require(set(a) == set(b) and {k for k in a if a[k] != b[k]} == {'branch', 'original_heart_installer_blob'}
            and b['branch'] == V5
            and b['original_heart_installer_blob'] == record(old['Tools/PinkhaNativeDerived/install_verified_heart.py'])['git_blob'],
            'Profile manifest changed beyond route binding')
    for path in ['Tools/OriginalEditor/framework_products.py', 'Tools/OriginalEditor/run_framework_acceptance.py',
                 'Tools/OriginalEditor/test_framework_flow.py', 'Anytype.xcodeproj/project.pbxproj',
                 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift', 'Tools/OriginalEditor/Consumer/ConsumerApp.swift']:
        require(old[path] == new[path], 'Protected executable/product changed')
    original = sorted(n for p, data in old.items() if p.startswith('Tools/OriginalEditor/test_') for n in methods(data))
    current = sorted(n for p, data in new.items() if p.startswith('Tools/OriginalEditor/test_') for n in methods(data))
    require(len(original) == len(set(original)) == 96 and len(current) == len(set(current)) == 99
            and set(original) < set(current), 'Original declarations were removed')
    expected_runs = [('frozen-v4-symlink-red', old, 96, 93, 2, 1),
                     ('candidate-path-green', intermediate, 99, 99, 0, 0),
                     ('candidate-final-alias-green', new, 99, 99, 0, 0),
                     ('candidate-final-native-path-green', new, 99, 99, 0, 0)]
    summary = {}
    for name, files, total, passed, failed, errors in expected_runs:
        prefix = name + '/'
        result = json.loads(raw[prefix + 'RESULT.json'])
        before = json.loads(raw[prefix + 'INPUTS_BEFORE.json'])
        require(before == json.loads(raw[prefix + 'INPUTS_AFTER.json']) and set(before) == set(files),
                'Test source changed or input inventory differs')
        for path, entry in before.items():
            require({k: record(files[path])[k] for k in entry} == entry, 'Retained tested source differs: ' + path)
        stderr = raw[prefix + 'stderr.log']
        require(record(stderr)['sha256'] == result['stderr_sha256']
                and record(raw[prefix + 'stdout.log'])['sha256'] == result['stdout_sha256'], 'Raw control stream differs')
        observed = re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. (ok|FAIL|ERROR)$', stderr.decode())
        cases = json.loads(raw[prefix + 'CASES.json'])
        require(cases == [{'method': method, 'id': identity, 'status': status} for method, identity, status in observed],
                'Stored cases differ from actual unittest output')
        require(len(cases) == len({c['method'] for c in cases}) == total
                and sum(c['status'] == 'ok' for c in cases) == passed
                and sum(c['status'] == 'FAIL' for c in cases) == failed
                and sum(c['status'] == 'ERROR' for c in cases) == errors, 'Actual case outcomes differ')
        require(result['exit_code'] == (1 if failed or errors else 0)
                and result['timeout_seconds'] == 300, 'Actual process exit or bound differs')
        if name == 'frozen-v4-symlink-red':
            require(result['real_directory_alias'] is True
                    and {c['method'] for c in cases if c['status'] == 'FAIL'} == {
                        'test_known_input_changed_during_copy_cannot_publish_success',
                        'test_changed_materialized_output_cannot_publish_success'}
                    and {c['method'] for c in cases if c['status'] == 'ERROR'} == {
                        'test_original_packager_retains_all_four_exact_raw_proofs_as_text'},
                    'Wrong discriminating baseline reproduction')
        summary[name] = {'executed': total, 'passed': passed, 'failed': failed, 'errors': errors}
    require(json.loads(raw['candidate-final-alias-green/RESULT.json'])['real_directory_alias'] is True
            and json.loads(raw['candidate-final-native-path-green/RESULT.json'])['real_directory_alias'] is False,
            'Missing both real pathname modes')
    return {'verification': 'PASS_READ_ONLY_V5_SOURCE_AND_ACTUAL_LINUX_CONTROLS',
            'source': index['source'], 'canonical_baseline_inputs': 26,
            'source_projection_streams': len(projections), 'raw_control_streams': len(raw),
            'all_original96_retained': True, 'runtime_driver_exporter_ABI_budgets_unchanged': True,
            'observations': summary, 'Apple_v5': 'NOT_RUN', 'editable_mount': 'NOT_EXPOSED',
            'tests_or_Apple_commands_executed_by_verifier': 0}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent),
                     indent=2, sort_keys=True))
