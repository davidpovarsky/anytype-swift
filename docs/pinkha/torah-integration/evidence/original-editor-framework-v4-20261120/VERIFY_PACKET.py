#!/usr/bin/env python3
"""Read-only replay of source preservation and retained Python results; no tests."""
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

BASE = 'a75443e4244762051cb0a99367188dc35645bfbf'
SOURCE = '756db79987428692e443e5793db936f75496fcbd'

def require(value, message):
    if not value: raise ValueError(message)

def record(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}

def archive(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and z.testzip() is None, 'Archive inventory/CRC failure')
        require(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                    and '\\' not in n for n in names), 'Unsafe archive name')
        return {n: z.read(n) for n in names}

def functions(raw):
    source = raw.decode(); lines = source.splitlines(keepends=True)
    return {n.name: ''.join(lines[n.lineno - 1:n.end_lineno])
            for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}

def verify(directory):
    directory = Path(directory)
    index = json.loads((directory / 'PACKET_INDEX.json').read_bytes())
    require(index['source_commit'] == SOURCE and index['base_source'] == BASE, 'Wrong packet source')
    for name, expected in index['files'].items():
        require(PurePosixPath(name).name == name and record((directory / name).read_bytes()) == expected,
                'Sealed file differs: ' + name)
    sources = archive(directory / 'source-projections.zip')
    runs = archive(directory / 'raw-controls.zip')
    references = archive(directory / 'source-references.zip')
    publication = json.loads((directory / 'SOURCE_PUBLICATION.json').read_bytes())
    require(publication['source_commit'] == SOURCE and publication['base_frozen_source'] == BASE
            and publication['tree'] == '0857cc91f1467641d27703a751cbbb4cb9b7c759'
            and publication['status'] == 'PUSHED_AUTHORING_ONLY_NOT_ACTIVATED', 'Wrong source publication')
    authority = json.loads((directory / 'SOURCE_AUTHORITY.json').read_bytes())
    require(authority['source'] == BASE and len(authority['source_inputs']) == 23, 'Wrong canonical baseline closure')
    for row in authority['source_inputs']:
        require(record(sources['base/' + row['path']]) == {k: row[k] for k in ['bytes', 'sha256', 'git_blob']}
                and row['git_blob'] == row['canonical_git_entry']['sha'], 'Canonical baseline input differs')
    proof = json.loads((directory / 'PRESERVATION.json').read_bytes())
    require(proof['status'] == 'PASS_EXACT_SOURCE_PRESERVATION' and proof['base_source'] == BASE,
            'Wrong preservation authority')
    changes = {r['path']: r for r in proof['changed_paths']}
    require(len(changes) == 9 and set(changes) == set(publication['changed_paths']), 'Source change inventory differs')
    candidate = {n[10:]: raw for n, raw in sources.items() if n.startswith('candidate/')}
    base = {n[5:]: raw for n, raw in sources.items() if n.startswith('base/')}
    actual_changes = {n for n, raw in candidate.items() if base.get(n) != raw}
    require(actual_changes == set(changes) and set(base) <= set(candidate), 'Undeclared source change')
    for path, row in changes.items():
        require(record(candidate[path]) == row['after']
                and (row['before'] is None if path not in base else record(base[path]) == row['before']),
                'Source delta bytes differ: ' + path)
    require(not any(n.startswith(('Anytype/', 'Modules/', 'Anytype.xcodeproj/', 'OriginalEditorFramework/'))
                    for n in changes), 'Unreviewed application/SDK/project change')
    v3 = b'codex/otzaria-original-editor-framework-v3-reviewed-20261120'
    v4 = b'codex/otzaria-original-editor-framework-v4-reviewed-20261120'
    for path in ['Tools/OriginalEditor/test_framework.py', '.github/workflows/pinkha-original-editor-framework.yml']:
        require(candidate[path].replace(v4, v3) == base[path], 'Original test/workflow differs beyond exact branch')
    require(candidate['Tools/OriginalEditor/test_framework_flow.py'] == base['Tools/OriginalEditor/test_framework_flow.py'],
            'Original ten flow controls changed')
    installer = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
    suffix = b",\n                             '" + v4 + b"'"
    require(candidate[installer].count(suffix) == 1
            and candidate[installer].replace(suffix, b'', 1) == base[installer], 'Original Heart installer changed')
    old_driver = functions(base['Tools/OriginalEditor/run_framework_acceptance.py'])
    new_driver = functions(candidate['Tools/OriginalEditor/run_framework_acceptance.py'])
    require(old_driver.keys() == new_driver.keys()
            and [k for k in old_driver if old_driver[k] != new_driver[k]] == ['source_file_proof'],
            'Original build/signature/platform/consumer/boot/cleanup functions changed')
    old_products = functions(base['Tools/OriginalEditor/framework_products.py'])
    new_products = functions(candidate['Tools/OriginalEditor/framework_products.py'])
    require([k for k in old_products if old_products[k] != new_products[k]] == ['export_products'],
            'Original copy/resource/runtime/public-surface methods changed')
    for path in proof['protected_exact_files']:
        require(candidate[path] == base[path], 'Original protected file changed: ' + path)
    original = set(proof['original_test_methods']); added = set(proof['new_test_methods'])
    require(len(original) == 54 and len(added) == 42 and not original & added, 'Case declaration inventory differs')
    stages = {
        'baseline-red': ('baseline', 85, 80, 1, 4, 1),
        'candidate-green': ('candidate-linux-only-attempt1', 85, 85, 0, 0, 0),
        'darwin-api-red': ('darwin-api-baseline', 1, 0, 0, 1, 1),
        'candidate-portable-green': ('candidate-portable-attempt1', 96, 96, 0, 0, 0),
        'darwin-api-red-final': ('darwin-api-baseline-final', 1, 0, 0, 1, 1),
        'candidate-final-green': ('candidate', 96, 96, 0, 0, 0),
    }
    for stage, (projection, total, passed, failed, errors, exit_code) in stages.items():
        prefix = stage + '/'
        receipt = json.loads(runs[prefix + 'RESULT.json'])
        require([receipt[k] for k in ['executed', 'passed', 'failed', 'errors', 'exit_code']]
                == [total, passed, failed, errors, exit_code], 'Actual result differs: ' + stage)
        require(runs[prefix + 'INPUTS_BEFORE.json'] == runs[prefix + 'INPUTS_AFTER.json'], 'Inputs changed during controls')
        for path, expected in json.loads(runs[prefix + 'INPUTS_BEFORE.json']).items():
            actual = record(sources[projection + '/' + path])
            require({k: actual[k] for k in ['bytes', 'sha256']} == expected, 'Tested source differs: ' + stage + '/' + path)
        for stream in ['stdout', 'stderr']:
            require(record(runs[prefix + stream + '.log'])['sha256'] == receipt[stream + '_sha256'], 'Control log differs')
        stderr = runs[prefix + 'stderr.log'].decode()
        rows = re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. (ok|FAIL|ERROR|skipped[^\n]*)$', stderr)
        cases = [{'method': m, 'id': i, 'status': s} for m, i, s in rows]
        require(cases == json.loads(runs[prefix + 'CASES.json']) and len(cases) == total,
                'Parsed raw case inventory differs')
        require(sum(c['status'] == 'ok' for c in cases) == passed
                and sum(c['status'] == 'FAIL' for c in cases) == failed
                and sum(c['status'] == 'ERROR' for c in cases) == errors, 'Actual case status differs')
        if total > 1:
            old = {c['method']: c['status'] for c in cases if c['method'] in original}
            require(len(old) == 54 and all(status == 'ok' for status in old.values()), 'Original controls regressed')
        if stage == 'candidate-final-green':
            require({c['method'] for c in cases} == original | added and stderr.rstrip().endswith('OK'), 'Final control set differs')
    require('Missing or ambiguous genuine framework products' in runs['baseline-red/stderr.log'].decode(),
            'Original duplicate-export RED missing')
    require("AttributeError: module 'framework_products' has no attribute 'sys'" in runs['darwin-api-red/stderr.log'].decode()
            and json.loads(runs['darwin-api-red/CLASSIFICATION.json'])['status'] == 'UNQUALIFIED_BASELINE_FIXTURE_ERROR',
            'Initial unqualified fixture attempt was not preserved honestly')
    require('for name in sorted(os.listxattr(path, follow_symlinks=follow)):' in runs['darwin-api-red-final/stderr.log'].decode()
            and 'AttributeError: Darwin CPython has no Linux os xattr API' in runs['darwin-api-red-final/stderr.log'].decode(),
            'Actual whole-exporter portability refusal missing')
    require(len([n for n in runs if n.startswith('candidate-final-green/flow/')]) == 10,
            'Original ten synthetic command-flow receipts missing')
    refs = json.loads(references['REFERENCES.json'])
    require(record(references['apple-xnu-xattr.h']) == {k: refs['apple_header'][k] for k in ['bytes', 'sha256', 'git_blob']},
            'Original documented Darwin ABI header differs')
    return {'status': 'PASS_READ_ONLY_V4_SOURCE_AND_PYTHON_EVIDENCE', 'source_commit': SOURCE,
            'base_source': BASE, 'source_changes': 9, 'canonical_base_inputs': 23,
            'source_projection_streams': len(sources), 'raw_control_streams': len(runs),
            'retained_original_cases': 54, 'final_python_cases': 96, 'final_python_pass': 96,
            'original_v3_baseline': {'executed': 85, 'pass': 80, 'fail': 1, 'errors': 4},
            'unqualified_portability_attempt_retained': True, 'whole_exporter_portability_red_retained': True,
            'source_sdk_compiler_runtime_budgets_unchanged': True,
            'real_Darwin_xattrs': 'NOT_RUN', 'real_duplicate_Lib_equivalence': 'NOT_RUN',
            'v4_Apple_build_consumer_runtime': 'NOT_RUN', 'native_editor_ui_tests': 0,
            'tests_or_compilers_executed_by_verifier': 0}

if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent),
                     indent=2, sort_keys=True))
