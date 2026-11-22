from pathlib import Path
import hashlib
import json
import re
import zipfile

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]
OUT = HERE / 'evidence/attempt-v1'
E = OUT / 'retained/evidence'
read = lambda p: json.loads(p.read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()
archive = (OUT / 'lifetime-unit-evidence-v1.zip').read_bytes()
assert len(archive) == 52773 and sha(archive) == 'c46d00f970709a281caab364c4ad53a3eab7457cb608ad7e388d76d55b1c704e'
with zipfile.ZipFile(OUT / 'lifetime-unit-evidence-v1.zip') as z:
    assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == 33
    index = json.loads(z.read('ARCHIVE_INDEX.json'))
    assert len(index) == 32 and {r['path'] for r in index} == set(z.namelist()) - {'ARCHIVE_INDEX.json'}
    for row in index:
        data = z.read(row['path'])
        assert data == (OUT / 'retained' / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
s = read(HERE / 'SOURCE.json')
r = read(E / 'RESULT.json')
assert r['status'] == 'PASS_NEW_OWNED_IMPORT_LIFETIME_UNIT_BOUNDARIES'
assert r['source_manifest'] == read(E / 'SOURCE.json') == s
assert r['tests_run'] == r['tests_passed'] == len(s['expected_tests']) == 23
assert r['tests_failed'] == r['tests_skipped'] == r['native_executions'] == r['prior_suites_replayed'] == 0
assert r['go_version'] == 'go version go1.25.6 windows/amd64'
assert len(r['commands']) == 4 and [c['name'] for c in r['commands']] == ['go-version','compile-importer','compile-application','controls']
assert r['commands'][-1]['args'][1:] == ['test','-json','-count=1','-timeout','45s','./core/block/import','./core/application']
for c in r['commands']:
    assert c['exit'] == 0 and c['timed_out'] is False and c['process_wait_completed'] is True
    for name in ('stdout','stderr'):
        b = (E / (c['name'] + '.' + name + '.log')).read_bytes()
        assert len(b) == c[name]['bytes'] and sha(b) == c[name]['sha256']
assert len(s['module_files']) == 22 and r['source_after'] == s['module_files']
for row in s['module_files']:
    for base in (HERE / 'module', OUT / 'retained/module'):
        b = (base / row['path']).read_bytes()
        assert len(b) == row['bytes'] and sha(b) == row['sha256']
for row in s['full_actual_source_files']:
    data = (WORK / row['source']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert data == (OUT / 'retained/module' / row['compiled_path']).read_bytes()
assert len(s['full_actual_source_files']) == 5
fragment_bindings = []
for row in s['actual_source_fragments']:
    data = (WORK / row['source']).read_bytes()
    assert len(data) == row['source_bytes'] and sha(data) == row['source_sha256']
    text = data.decode(); assert text.count(row['start']) == 1
    fragment = text[text.index(row['start']):]
    if row['end']:
        assert fragment.count(row['end']) == 1
        fragment = fragment[:fragment.index(row['end'])]
    b = fragment.encode(); assert len(b) == row['bytes'] and sha(b) == row['fragment_sha256']
    if row['start'] == 'type ImportRequest struct {':target = 'core/block/import/actual_types.go'
    elif row['source'].endswith('/owned_import_files.go'):target = 'core/block/import/actual_owned_context.go'
    else:target = 'core/application/actual_lifecycle.go'
    actual = (OUT / 'retained/module' / target).read_bytes()
    assert actual.count(b) == 1, (row['source'], target)
    fragment_bindings.append({'source':row['source'],'start':row['start'],'compiled_path':target,'sha256':sha(b)})
assert len(fragment_bindings) == 8
events = [json.loads(line) for line in (E / 'controls.stdout.log').read_text().splitlines() if line.strip()]
assert len(events) == 100
expected = {(v['package'],v['name']) for v in s['expected_tests']}
actual = {}
for event in events:
    if 'Test' in event and event['Action'] in ('run','pass','fail','skip'):
        actual.setdefault((event['Package'],event['Test']),[]).append(event['Action'])
assert set(actual) == expected and len(expected) == 23
assert all(actions == ['run','pass'] for actions in actual.values())
assert not any(e['Action'] in ('fail','skip') for e in events)
manifest_path = HERE.parent / 'candidate/SOURCE_MANIFEST.json'
assert sha(manifest_path.read_bytes()) == s['product_manifest_sha256']
products = read(manifest_path)
assert len(products) == 8
inverse = []
guards = 0
for row in products:
    data = (HERE.parent / 'candidate/native' / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob']
    if row.get('preimage'):
        old_paths = [HERE.parent / 'original' / row['path'], WORK / 'native-owned-import-audit/original/anytype-heart' / row['path']]
        matching = [p for p in old_paths if p.is_file() and sha(p.read_bytes()) == row['preimage']['sha256']]
        assert matching, row['path']
        original = matching[0].read_bytes()
        text, count = re.subn(r'\n\treleaseOwnedRetirement, ownedErr := s.beginOwnedImportRetirement\(\)\n\tif ownedErr != nil \{\n\t\treturn [^\n]+\n\t}\n\tdefer releaseOwnedRetirement\(\)\n', '', data.decode())
        guards += count
        if row['path'].endswith('/application.go'):
            assert text.count('\tlock         sync.RWMutex\n\townedImports ownedImportRegistry') == 1
            text = text.replace('\tlock         sync.RWMutex\n\townedImports ownedImportRegistry','\tlock sync.RWMutex')
        assert text.encode() == original, row['path']
        inverse.append({'path':row['path'],'sha256':sha(original),'guards_removed':count})
assert len(inverse) == 6 and guards == 7
receipt = {'status':'PASS_ROOT_23_LIFETIME_CONTROL_AND_SOURCE_REVIEW',
    'archive':{'bytes':len(archive),'sha256':sha(archive),'payloads':32,'crc':True},
    'result_sha256':sha((E/'RESULT.json').read_bytes()),'module_files':22,'whole_files':5,
    'fragment_bytes_bound_to_actual_compiled_files':fragment_bindings,
    'raw_go_json_events':100,'unique_cases_started_and_passed_once':23,'failed':0,'skipped':0,
    'actual_windows_compiler':r['go_version'],'commands':4,'streams':8,'process_waits_completed':4,
    'product_files':8,'six_original_file_inverse':inverse,'guards_added':7,
    'historical_controls_replayed':0,'root_controls_replayed':0,'native_lifetime_executed':False,
    'scope':'Two complete new lifetime files plus exact original/context/lifecycle fragments in explicit ABI/callback fixture packages. Actual native application compilation and account/import execution are separate.',
    'source_findings':['Registration precedes actual Start; completion channel closes only after original Execute returns and outcome copies finish.',
        'Cancellation remains a request. Retirement cancels outside registry mutex and returns drain-pending instead of joining under Service writer lock.',
        'Counted retirement preserves overlapping legacy start/stop ordering when no owned work exists; six original files reconstruct exactly.',
        'Private application admission checks actual app and wallet/lease identity; future production route and permission/archive binding remain absent.'],
    'fixture_limits':s['fixture_scope']}
(OUT/'ROOT_LIFETIME_CONTROL_REVIEW.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','module_files','whole_files','raw_go_json_events','unique_cases_started_and_passed_once','product_files','guards_added','native_lifetime_executed')}))
