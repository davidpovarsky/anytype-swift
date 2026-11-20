#!/usr/bin/env python3
"""Read-only replay of the sealed v3 Python/source evidence. No tools are run."""
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


index = read('PACKET_INDEX.json')
require(index['scope'] == 'SOURCE_AND_ACTUAL_PYTHON_ONLY_APPLE_NOT_RUN', 'Wrong evidence scope')
for item in index['files']:
    data = (ROOT / item['path']).read_bytes()
    require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'Packet differs: ' + item['path'])
raw_index = read('RAW_INDEX.json')['files']
require(len(raw_index) == len({r['path'] for r in raw_index}) == 101, 'Raw inventory differs')
with zipfile.ZipFile(ROOT / 'evidence.zip') as archive:
    require(len(archive.namelist()) == len(set(archive.namelist())) == len(raw_index), 'Repeated ZIP member')
    require(set(archive.namelist()) == {r['path'] for r in raw_index}, 'ZIP member inventory differs')
    require(archive.testzip() is None, 'ZIP CRC failure')
    raw = {}
    for item in raw_index:
        path = PurePosixPath(item['path'])
        require(not path.is_absolute() and '..' not in path.parts and str(path) == item['path'], 'Unowned ZIP path')
        data = archive.read(item['path'])
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'Raw bytes differ: ' + item['path'])
        raw[item['path']] = data

authority = read('SOURCE_AUTHORITY.json')
require(authority['source'] == 'dc3ac07cec63692c8b84877a56e3e3fd60a4c667', 'Wrong prior source')
inputs = authority['source_inputs'] + [authority['extra_control_input']]
require(len(inputs) == 23, 'Wrong original source closure')
for item in inputs:
    data = raw['base/' + item['path']]
    require(sha(data) == item['sha256'] and blob(data) == item['git_blob'] and len(data) == item['bytes'],
            'Original Git input differs: ' + item['path'])
    require(raw['baseline/' + item['path']] == data, 'Baseline source changed')

source = read('SOURCE_COMMIT.json')
require(source['source_commit'] == '35dbb7bf54b18a8974d4c1bc820fe7d95ecb26e6', 'Wrong candidate source')
require(source['reviewed_route_ref_created'] is False and source['apple_execution'] == 'NOT_RUN', 'Activation overclaim')
require(len(source['files']) == 7, 'Wrong source delta count')
changed = set()
for path in [p.removeprefix('candidate/') for p in raw if p.startswith('candidate/')]:
    if raw.get('base/' + path) != raw['candidate/' + path]:
        changed.add(path)
require(changed == {r['path'] for r in source['files']}, 'Unexpected source delta')
for item in source['files']:
    data = raw['candidate/' + item['path']]
    require(len(data) == item['bytes'] and sha(data) == item['sha256'] and blob(data) == item['git_blob'],
            'Candidate Git input differs: ' + item['path'])

old = 'codex/otzaria-original-editor-framework-reviewed-20261120'
new = 'codex/otzaria-original-editor-framework-v3-reviewed-20261120'
pair = ("    command(['xcrun', 'simctl', 'boot', udid], root, evidence, 'boot-owned-simulator', 60)\n"
        "    command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], root, evidence, 'boot-status', 180)\n")
driver_path = 'Tools/OriginalEditor/run_framework_acceptance.py'
prior_driver = raw['base/' + driver_path].decode()
candidate_driver = raw['candidate/' + driver_path].decode()
require(candidate_driver.count(pair) == 1, 'Boot pair differs')
inverse = candidate_driver.replace(pair, '', 1)
anchor = "    udid = preflight['selected']['ipad']['udid']\n"
require(inverse.count(anchor) == 1, 'Simulator source differs')
inverse = inverse.replace(anchor, anchor + pair, 1)
notice = ("                destination = notices / checkout.name / source.name\n"
          "                destination.parent.mkdir(parents=True, exist_ok=True)\n"
          "                shutil.copyfile(source, destination)\n"
          "                notice_files.append({'path': destination.relative_to(exported).as_posix(), 'sha256': sha256(destination)})\n")
require(inverse.count(notice.replace('destination', 'notice_destination')) == 1, 'Notice block differs')
inverse = inverse.replace(notice.replace('destination', 'notice_destination'), notice, 1)
require(inverse == prior_driver, 'Complete driver inverse differs')

def commands(text):
    return sorted(ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'command')

require(commands(candidate_driver) == commands(prior_driver), 'Original command arguments or bounds differ')
installer_path = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
installer_before = raw['base/' + installer_path]
installer = raw['candidate/' + installer_path].decode()
suffix = ",\n                             '" + new + "'"
require(installer.count(suffix) == 1 and installer.replace(suffix, '', 1).encode() == installer_before,
        'Original Heart installer inverse differs')
for path in ['.github/workflows/pinkha-original-editor-framework.yml', 'Tools/OriginalEditor/test_framework.py']:
    require(raw['candidate/' + path].decode().replace(new, old).encode() == raw['base/' + path],
            'Exact route-only inverse differs: ' + path)
profile_path = 'Tools/OriginalEditor/framework_profile.json'
profile = json.loads(raw['candidate/' + profile_path])
prior = json.loads(raw['base/' + profile_path])
require(profile['branch'] == new and profile['original_heart_installer_blob'] == blob(installer_before),
        'Exact installer/route pin differs')
profile['branch'] = prior['branch']
profile['original_heart_installer_blob'] = prior['original_heart_installer_blob']
require(profile == prior, 'Original product, package, resource or helper pin changed')
profile_path = 'Tools/OriginalEditor/framework_profile.py'
inverse = raw['candidate/' + profile_path].decode().replace(new, old, 1)
for name in ['reviewed', 'original']:
    inverse = inverse.replace(name + ' = "                             \'' + old,
                              name + ' = "                             \'codex/otzaria-original-editor-owned43-apple-reviewed-20261120', 1)
require(inverse.encode() == raw['base/' + profile_path], 'Complete profile inverse differs')
new_test = 'Tools/OriginalEditor/test_framework_flow.py'
require(raw['baseline/' + new_test] == raw['candidate/' + new_test], 'New controls changed between RED and GREEN')

case_sets = {}
for mode, passed, failed, exit_code in [('baseline-red', 45, 9, 1), ('candidate-green', 54, 0, 0)]:
    prefix = 'runs/' + mode + '/'
    result = json.loads(raw[prefix + 'RESULT.json'])
    require(result['returncode'] == exit_code and result['source_before_after_identical'] is True, 'Run result differs')
    scope = 'baseline' if mode == 'baseline-red' else 'candidate'
    require(result['source_inputs'] == {p.removeprefix(scope + '/'): sha(b) for p, b in raw.items() if p.startswith(scope + '/')},
            'Execution inputs differ from whole source projection')
    observed = []
    for line in raw[prefix + 'stderr.log'].decode().splitlines():
        match = re.fullmatch(r'(test_[^( ]+) \(([^)]+)\) \.\.\. (ok|FAIL|ERROR|skipped.*)', line)
        if match:
            observed.append({'method': match[1], 'qualified_id': match[2], 'result': match[3]})
    cases = json.loads(raw[prefix + 'CASES.json'])
    require(observed == cases['cases'] and len(observed) == len({r['qualified_id'] for r in observed}) == 54,
            'Actual unittest leaves differ')
    require(sum(r['result'] == 'ok' for r in observed) == passed and sum(r['result'] == 'FAIL' for r in observed) == failed,
            'Actual success/failure counts differ')
    originals = [r for r in observed if r['qualified_id'].startswith('test_framework.')]
    require(len(originals) == 44 and all(r['result'] == 'ok' for r in originals), 'An original control regressed')
    case_sets[mode] = {r['qualified_id'] for r in observed}
require(case_sets['baseline-red'] == case_sets['candidate-green'], 'Case declarations differ')
for prefix in ['runs/baseline-red/flow/', 'runs/candidate-green/flow/']:
    traces = [json.loads(data) for path, data in raw.items() if path.startswith(prefix)]
    require(len(traces) == 10, 'Incomplete whole-driver control traces')
    require(all(t['apple_builds_executed'] == t['native_tests_executed'] == 0 for t in traces), 'Synthetic boundary overclaim')
    for trace in traces:
        require(trace['receipt']['verified_runtime_observations'] == [] and trace['receipt']['native_editor_ui_tests'] == 0,
                'Synthetic flow received runtime credit')

print(json.dumps({'status': 'SEALED_V3_SOURCE_AND_PYTHON_REPLAY_PASS',
                  'sealed_payloads': len(index['files']), 'raw_members': len(raw),
                  'canonical_original_inputs': 23, 'candidate_source_delta': 7,
                  'original_controls': 44, 'baseline_passed': 45, 'baseline_failed': 9,
                  'candidate_passed': 54, 'candidate_failed': 0,
                  'original_command_expressions_and_budgets_identical': True,
                  'complete_existing_file_inverses': 6, 'apple_execution': 'NOT_RUN'}, sort_keys=True))
