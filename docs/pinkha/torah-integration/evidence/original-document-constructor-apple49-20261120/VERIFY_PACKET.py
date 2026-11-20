#!/usr/bin/env python3
"""Verify bytes, actual Python results and source closure; never runs Swift or CI."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--root', type=Path, required=True)
args = parser.parse_args()
ROOT = args.root.resolve()
DOC = ROOT / 'docs/pinkha/torah-integration/evidence/original-document-constructor-apple49-20261120'

def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

def bytes_at(path):
    actual = (ROOT / path).resolve()
    assert actual.is_relative_to(ROOT) and actual.is_file() and not (ROOT / path).is_symlink()
    return actual.read_bytes()

index = json.loads((DOC / 'PACKET_INDEX.json').read_text())
for item in index['payloads']:
    assert record(bytes_at(item['path'])) == {key: item[key] for key in ['bytes', 'sha256', 'git_blob']}, item['path']
raw = {}
for item in json.loads((DOC / 'RAW_INDEX.json').read_text()):
    compressed = bytes_at(item['path'])
    assert record(compressed) == item['compressed']
    data = gzip.decompress(compressed)
    assert record(data) == item['original']
    raw[item['original_name']] = data
prior = {}
with tarfile.open(fileobj=io.BytesIO(gzip.decompress((DOC / 'constructor-source-packet.tar.gz').read_bytes())), mode='r:') as archive:
    for member in archive.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        prior[member.name] = archive.extractfile(member).read()
prior_name = 'docs/pinkha/torah-integration/evidence/original-document-constructor-20261120/PACKET_INDEX.json'
assert record(prior[prior_name])['sha256'] == '09dc98cd7784b87aca1c520b9cd11c22249b346ba962a4c120ce3ac9c3f5814d'
prior_index = json.loads(prior[prior_name])
assert len(prior_index['payloads']) == 31 and len(prior) == 32
for item in prior_index['payloads']:
    assert record(prior[item['path']]) == {key: item[key] for key in ['bytes', 'sha256', 'git_blob']}
for path in ['Anytype/Sources/Models/Documents/Document/BaseDocument.swift',
             'Anytype/Sources/Models/Documents/Events/DocumentViewModelSetter.swift',
             'AnytypeTests/Markdown/PreparedDocumentConstructorTests.swift']:
    assert bytes_at(path) == prior[path]

source_index = json.loads((DOC / 'SOURCE_INDEX.json').read_text())
assert len(source_index) == 11
for item in source_index:
    assert record(bytes_at(item['path'])) == {key: item[key] for key in ['bytes', 'sha256', 'git_blob']}
preservation = json.loads(raw['RUNTIME_PRESERVATION.json'])
host = bytes_at('Tools/Hanlin/run_host_tests.py').decode()
for item in reversed(preservation['host_exact_inverse']):
    assert host.count(item['after']) == 1
    host = host.replace(item['after'], item['before'], 1)
assert host.encode() == raw['baseline-inputs/Tools/Hanlin/run_host_tests.py']
installer = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
item = preservation['installer_exact_inverse']
text = bytes_at(installer).decode()
assert text.count(item['after']) == 1
assert text.replace(item['after'], item['before'], 1).encode() == raw['baseline-inputs/' + installer]
assert json.loads(raw['FINAL_PRESERVATION.json'])['original_workflow_semantic_inverse'] is True

tree = json.loads(raw['canonical/B4_TREE.json'])
assert tree['truncated'] is False and tree['sha'] == 'bd03e6a690f9a89f64c0124c6f81cf12cf0d8a06'
entries = {item['path']: dict(item) for item in tree['tree']}
def tree_hashes(entries):
    groups = {'': []}
    for path, item in entries.items():
        parent, _, name = path.rpartition('/')
        groups.setdefault(parent, []).append((name, item))
        if item['type'] == 'tree':
            groups.setdefault(path, [])
    result = {}
    for path in sorted(groups, key=lambda value: value.count('/') + bool(value), reverse=True):
        data = b''
        for name, item in sorted(groups[path], key=lambda value: value[0].encode() + (b'/' if value[1]['type'] == 'tree' else b'')):
            key = (path + '/' if path else '') + name
            oid = result[key] if item['type'] == 'tree' else item['sha']
            data += item['mode'].lstrip('0').encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(oid)
        result[path] = hashlib.sha1(b'tree ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    return result
assert tree_hashes(entries)[''] == tree['sha']
for item in source_index:
    path = item['path']
    assert str(Path(path).parent) in entries
    entries[path] = {'path': path, 'type': 'blob', 'mode': '100644', 'sha': item['git_blob']}
trees = tree_hashes(entries)
profile = json.loads(bytes_at('Tools/Hanlin/original_document_constructor_profile.json'))
assert {path: trees[path] for path in profile['application_trees']} == profile['application_trees']
old = json.loads(raw['baseline-inputs/Tools/Hanlin/original_editor_profile.json'])
assert profile['original_suites'] == old['suites'] and profile['heart'] == old['heart']
assert sum(len(item['methods']) for item in old['suites'].values()) == 43
assert len(profile['constructor_suite']['methods']) == 6

controls = json.loads(bytes_at('Tools/Hanlin/original_document_constructor_controls.json'))
execution = json.loads(raw['execution-attempt2/controls.json'])
assert execution['status'] == 'PASS_BASELINE74_AND_CANDIDATE_CONTROLS_APPLE_NOT_RUN'
assert execution['baseline_sha'] == 'b4ece8c2129124f6ec8ed00143e156b9d0e11383'
assert execution['original_baseline_restored'] is True and execution['candidate_inputs_unchanged'] is True
for path, sha in controls['baseline_inputs'].items():
    assert record(raw['baseline-inputs/' + path])['sha256'] == sha
    assert record(raw['baseline-inputs/' + path])['git_blob'] == next(x['sha'] for x in tree['tree'] if x['path'] == path)
for prefix, names in [('original74-baseline-profile', controls['original74_methods']),
                      ('candidate49-gate-controls', controls['candidate_control_methods'])]:
    receipt = json.loads(raw['execution-attempt2/' + prefix + '.json'])
    log = raw['execution-attempt2/' + prefix + '.log']
    assert receipt['returncode'] == 0 and receipt['status'] == 'PASS'
    assert receipt['output_sha256'] == record(log)['sha256']
    assert receipt['verified_complete_controls'] == sorted(names)
    text = log.decode()
    starts = list(re.finditer(r'^test\w+ \(([^\n]+)\) \.\.\. ', text, re.M))
    assert len(starts) == len(set(x.group(1) for x in starts)) == len(names)
    assert set(x.group(1) for x in starts) == set(names)
    summary = re.search(r'\n-+\nRan ' + str(len(names)) + r' tests in [\d.]+s\s+OK\s*$', text)
    assert summary
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else summary.start()
        value = text[match.end():end].rstrip()
        assert value == 'ok' or value.endswith('\nok')
assert len(controls['original74_methods']) == 74 and len(controls['candidate_control_methods']) == 23
assert json.loads(raw['execution-attempt1/controls.json'])['status'] == 'FAIL'
assert json.loads(raw['preservation-attempt1/RESULT.json'])['status'] == 'PRESERVATION_FIXTURE_FAILURE'
scope = json.loads((DOC / 'SCOPE.json').read_text())
assert scope['apple_execution'] == 'NOT_RUN' and scope['native_ui_tests'] == 0
print(json.dumps({'status': 'PASS', 'payloads': len(index['payloads']), 'source_files': 11,
                  'prior_constructor_payloads': 31, 'old_python_controls': 74, 'new_python_controls': 23,
                  'apple_methods_executed': 0, 'native_ui_tests': 0, 'verification_only': True}, sort_keys=True))
