#!/usr/bin/env python3
"""Offline byte/source/outcome verification only; no Swift, simulator or CI execution."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parent

def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}

def read(path):
    resolved = (ROOT / path).resolve()
    assert resolved.is_relative_to(ROOT), path
    return resolved.read_bytes()

def raw(item):
    compressed = read(item['path'])
    assert digest(compressed) == item['compressed'], item['path']
    value = gzip.decompress(compressed)
    assert digest(value) == item['original'], item['path']
    return value

index = json.loads(read('PACKET_INDEX.json'))
for item in index['files']:
    assert digest(read(item['path'])) == {key: item[key] for key in ['bytes', 'sha256', 'git_blob']}, item['path']
expected = {item['path'] for item in index['files']} | {'PACKET_INDEX.json'}
assert {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()} == expected
catalog = json.loads(read('RAW_INDEX.json'))
outer = read(catalog['outer_artifact']['path'])
assert digest(outer) == {key: catalog['outer_artifact'][key] for key in ['bytes', 'sha256', 'git_blob']}
with zipfile.ZipFile(io.BytesIO(outer)) as archive:
    assert archive.testzip() is None and archive.namelist() == ['Pinkha-Native-Derived-Evidence.zip']
    inner = archive.read(archive.namelist()[0])
assert digest(inner) == {key: catalog['nested_artifact'][key] for key in ['bytes', 'sha256', 'git_blob']}
members = {}
with zipfile.ZipFile(io.BytesIO(inner)) as archive:
    assert archive.testzip() is None and len(archive.infolist()) == 28
    assert set(archive.namelist()) == {item['zip_member'] for item in catalog['members']}
    for item in catalog['members']:
        value = raw(item)
        assert archive.read(item['zip_member']) == value
        assert format(archive.getinfo(item['zip_member']).CRC, '08x') == item['zip_crc32']
        members[item['zip_member']] = value

api = {Path(item['path']).name.removesuffix('.json.gz'): json.loads(raw(item)) for item in catalog['api']}
run, jobs, artifacts = api['RUN'], api['JOBS']['jobs'], api['ARTIFACTS']['artifacts']
assert (run['id'], run['run_attempt'], run['head_sha'], run['status'], run['conclusion']) == (
    44781744925, 2, 'dc3ac07cec63692c8b84877a56e3e3fd60a4c667', 'completed', 'failure')
assert len(jobs) == 1 and jobs[0]['id'] == 136464900723 and jobs[0]['status'] == 'completed'
assert jobs[0]['completed_at'] == '2026-11-20T18:00:17Z'
artifacts = [a for a in artifacts if a['id'] == 14656015255]
assert len(artifacts) == 1
assert artifacts[0]['digest'] == 'sha256:' + digest(outer)['sha256']
assert artifacts[0]['size_in_bytes'] == len(outer)
log = raw(catalog['job_log'])
assert digest(log)['sha256'] == '7fa72d9a4ffe66c289016f3cef41ddb233f13bfb5ec0382d3c5bbca629fd2d6a'

execution = json.loads(members['execution.json'])
boot = json.loads(members['boot-status.command.json'])
assert execution['status'] == 'FAIL' and execution['error_type'] == 'TimeoutExpired'
assert execution['original_framework_build'] == execution['external_consumer_build'] == 'NOT_RUN'
assert execution['native_editor_ui_tests'] == 0 and execution['verified_runtime_observations'] == []
assert boot['timed_out'] is True and boot['returncode'] == -15 and boot['timeout_seconds'] == 180
assert members['boot-status.stdout.log'] == members['boot-status.stderr.log'] == b''
assert not any('framework-build' in name or '.xcresult' in name for name in members)
controls = members['source-controls.stderr.log'].decode()
leaves = re.findall(r'^(test_\S+ \([^\n]+\)) \.\.\. ok$', controls, re.M)
assert len(leaves) == len(set(leaves)) == 44
assert re.search(r'Ran 44 tests in [\d.]+s\s+OK\s*$', controls)
assert members['source-before.json'] == members['source-after.json']
source = json.loads(members['source-before.json'])
assert source['head_sha'] == run['head_sha'] and len(source['source_files']) == 2237
assert len(source['source_inputs']) == 22
frozen = {}
for item in catalog['frozen_source']:
    value = raw(item)
    assert digest(value) == source['source_inputs'][item['source_path']]
    frozen[item['source_path']] = value.decode()
guard = frozen['Tools/OriginalEditor/framework_profile.py']
assert "re.fullmatch(r'[1-9][0-9]*', environment.get('GITHUB_RUN_ATTEMPT', ''))" in guard
workflow = frozen['.github/workflows/pinkha-original-editor-framework.yml']
assert 'EDITOR_WORK: build/original-editor-framework-${{ github.run_id }}-${{ github.run_attempt }}' in workflow
assert 'Evidence-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}' in workflow
for item in catalog['original43_comparison']:
    raw(item)
for item in catalog['auxiliary']:
    raw(item)
assert len(catalog['frozen_source']) == 22
proof = json.loads(read('SOURCE_GIT_PROOF.json'))
assert proof['status'] == 'PASS_CANONICAL_SOURCE_BINDING'
assert proof['source'] == run['head_sha'] and proof['original_trees'] == source['original_trees']
assert {r['path'] for r in proof['source_inputs']} == set(source['source_inputs'])
previous = read(catalog['previous_artifact']['path'])
assert digest(previous) == {key: catalog['previous_artifact'][key] for key in ['bytes', 'sha256', 'git_blob']}
assert digest(previous)['sha256'] == 'e3889818d605d9abfd2f826407bef41e2951fbcdfb0fad2077ebfa6a3cdc1037'
with zipfile.ZipFile(io.BytesIO(previous)) as z:
    assert z.testzip() is None
    prior_inner = z.read('Pinkha-Native-Derived-Evidence.zip')
with zipfile.ZipFile(io.BytesIO(prior_inner)) as z:
    assert z.testzip() is None and len(z.infolist()) == 28
    previous_source = json.loads(z.read('source-before.json'))
    assert z.read('source-before.json') == z.read('source-after.json')
    prior_boot = json.loads(z.read('boot-status.command.json'))
    assert prior_boot['timed_out'] is True and prior_boot['timeout_seconds'] == 180 and prior_boot['returncode'] == -15
assert source['run_attempt'] == '2' and previous_source['run_attempt'] == '1'
assert {k: v for k, v in source.items() if k != 'run_attempt'} == {k: v for k, v in previous_source.items() if k != 'run_attempt'}
cleanup = json.loads(members['owned-simulator-cleanup.json'])
selected = json.loads(members['preflight/preflight.json'])['selected']
assert {r['udid'] for r in cleanup} == {v['udid'] for v in selected.values()}
assert len([r for r in cleanup if r['operation'] == 'delete' and r['returncode'] == 0]) == 2
assert not any(r['operation'] not in {'shutdown', 'delete'} for r in cleanup)
driver = frozen['Tools/OriginalEditor/run_framework_acceptance.py']
assert "destination = 'platform=iOS Simulator,id=' + udid" in driver
assert 'destination = notices / checkout.name / source.name' in driver
assert "'-configuration', 'Debug', '-destination', destination" in driver
print(json.dumps({'status': 'PASS', 'payloads_verified': len(index['files']), 'outer_zip_members': 1,
                  'inner_zip_members': 28, 'actual_source_controls': '44/44',
                  'actual_framework_compile': 'NOT_RUN', 'actual_external_consumer': 'NOT_RUN',
                  'native_editor_tests': 0, 'verification_executes_tests': False}, sort_keys=True))
