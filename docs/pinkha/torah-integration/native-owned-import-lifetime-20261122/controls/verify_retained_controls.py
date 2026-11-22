"""Verify retained lifetime unit evidence without executing any control again."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
ROOT = HERE / 'evidence/attempt-v1'
EVIDENCE = ROOT / 'retained/evidence'
source = json.loads((HERE / 'SOURCE.json').read_bytes())
result = json.loads((EVIDENCE / 'RESULT.json').read_bytes())
assert result['status'] == 'PASS_NEW_OWNED_IMPORT_LIFETIME_UNIT_BOUNDARIES'
assert result['source_manifest'] == source == json.loads((EVIDENCE / 'SOURCE.json').read_bytes())
assert result['go_version'] == 'go version go1.25.6 windows/amd64'
assert result['tests_run'] == result['tests_passed'] == 23
assert result['tests_failed'] == result['tests_skipped'] == result['native_executions'] == result['prior_suites_replayed'] == 0
assert len(result['commands']) == 4
for command in result['commands']:
    assert command['exit'] == 0 and command['timed_out'] is False and command['process_wait_completed'] is True
    for name in ['stdout', 'stderr']:
        data = (EVIDENCE / (command['name'] + '.' + name + '.log')).read_bytes()
        assert len(data) == command[name]['bytes'] and hashlib.sha256(data).hexdigest() == command[name]['sha256']
for row in source['module_files']:
    expected = {key: row[key] for key in ['bytes', 'sha256']}
    for path in [HERE / 'module' / row['path'], ROOT / 'retained/module' / row['path']]:
        data = path.read_bytes()
        assert {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected
assert result['source_after'] == source['module_files']
for row in source['full_actual_source_files']:
    data = (WORK / row['source']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert data == (ROOT / 'retained/module' / row['compiled_path']).read_bytes()
for row in source['actual_source_fragments']:
    data = (WORK / row['source']).read_bytes()
    assert len(data) == row['source_bytes'] and hashlib.sha256(data).hexdigest() == row['source_sha256']
    text = data.decode()
    assert text.count(row['start']) == 1
    fragment = text[text.index(row['start']):]
    if row['end']:
        assert fragment.count(row['end']) == 1
        fragment = fragment[:fragment.index(row['end'])]
    assert len(fragment.encode()) == row['bytes'] and hashlib.sha256(fragment.encode()).hexdigest() == row['fragment_sha256']
events = [json.loads(line) for line in (EVIDENCE / 'controls.stdout.log').read_bytes().decode().splitlines() if line.strip()]
expected = {(item['package'], item['name']) for item in source['expected_tests']}
started, finished = {}, {}
for event in events:
    if 'Test' not in event:
        continue
    key = event['Package'], event['Test']
    if event['Action'] == 'run':
        started[key] = started.get(key, 0) + 1
    if event['Action'] in {'pass', 'fail', 'skip'}:
        finished.setdefault(key, []).append(event['Action'])
assert set(started) == set(finished) == expected and len(expected) == 23
assert all(started[key] == 1 and finished[key] == ['pass'] for key in expected)
receipt = {'status': 'PASS_RETAINED_23_NEW_LIFETIME_UNIT_CONTROLS',
           'result_sha256': hashlib.sha256((EVIDENCE / 'RESULT.json').read_bytes()).hexdigest(),
           'source_manifest_sha256': hashlib.sha256((HERE / 'SOURCE.json').read_bytes()).hexdigest(),
           'raw_go_json_events': len(events), 'leaf_controls_exactly_once': len(expected),
           'failed': 0, 'skipped': 0, 'old_suites_replayed': 0, 'native_executions': 0,
           'source_files_verified': len(source['module_files']),
           'whole_files_verified': len(source['full_actual_source_files']),
           'exact_fragments_verified': len(source['actual_source_fragments']),
           'commands_verified': len(result['commands']), 'streams_verified': 8,
           'compiler': result['go_version'], 'scope': source['scope'], 'fixture_scope': source['fixture_scope']}
(ROOT / 'VERIFICATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
