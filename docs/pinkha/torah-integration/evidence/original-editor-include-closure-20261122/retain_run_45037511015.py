import base64
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-sdk-v12-watch-45037511015')
EV = ROOT / 'evidence-unpacked-0'
OUT = ROOT / 'terminal-review'
OUT.mkdir(exist_ok=True)
GH = r'C:\Program Files\GitHub CLI\gh.EXE'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

execution = json.loads((EV / 'execution.json').read_bytes())
command = json.loads((EV / 'framework-build.command.json').read_bytes())
controls = json.loads((EV / 'source-controls-result.json').read_bytes())
surface = json.loads((EV / 'actual-public-surface.json').read_bytes())
collection = json.loads((EV / 'compiler-symbolgraph-collection.json').read_bytes())
distribution = json.loads((EV / 'framework-distribution.json').read_bytes())
terminal = json.loads((ROOT / 'RUN_TERMINAL_OR_LAST.json').read_bytes())
artifacts = json.loads((ROOT / 'ARTIFACTS.json').read_bytes())['artifacts']
assert str(terminal['id']) == '45037511015' and terminal['head_sha'] == 'a9aa64bb8556ba5504ed0f5fe528cd1ce5f91efc'
assert terminal['status'] == 'completed' and terminal['conclusion'] == 'failure'
assert execution['original_framework_build'] == 'PASS' and command['returncode'] == 0 and command['timed_out'] is False
assert execution['external_consumer_build'] == 'NOT_RUN' and execution['error'] == 'Original product include directory was not exported'
assert surface['reviewed_host_and_spi_requirements_observed'] == 38
assert surface['public_host_scope_verified'] is True and surface['qualification_spi_scope_verified'] is True
assert controls['status'] == 'PASS_SOURCE_CONTROLS_239' and controls['tests_run'] == 239
expected = controls['expected_ids']
for key in ['expected_ids', 'discovered_ids', 'started_ids', 'passed_ids']:
    assert len(controls[key]) == len(set(controls[key])) == 239
    assert sorted(controls[key]) == sorted(expected)
for key in ['errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes']:
    assert controls[key] == []
assert (EV / 'source-before.json').read_bytes() == (EV / 'source-after.json').read_bytes()

archive = ROOT / 'downloaded-evidence/Pinkha-Native-Derived-Evidence.zip'
raw = archive.read_bytes()
assert len(raw) == 15226371 and digest(raw) == 'd6555af2541be09872b7b61afc38b000376404e9a521c1130b859ffec421899c'
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None
    members = zipped.infolist()
    assert len(members) == 545
    for item in members:
        if item.is_dir():
            continue
        target = EV.joinpath(*pathlib.PurePosixPath(item.filename).parts)
        assert target.is_file() and target.read_bytes() == zipped.read(item.filename)

blob_id = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
blob_receipt = OUT / 'RAW_ARCHIVE_GIT_BLOB.json'
if blob_receipt.exists():
    blob_response = json.loads(blob_receipt.read_bytes())
    assert blob_response['sha'] == blob_id
else:
    payload = OUT / 'raw-archive-blob-upload.json'
    payload.write_text(json.dumps({'encoding': 'base64', 'content': base64.b64encode(raw).decode()}), encoding='utf-8')
    result = subprocess.run([GH, 'api', '-X', 'POST', 'repos/davidpovarsky/anytype-swift/git/blobs',
                             '--input', str(payload)], capture_output=True, timeout=180)
    (OUT / 'raw-archive-git-upload.stderr').write_bytes(result.stderr)
    assert result.returncode == 0, 'Raw archive Git retention failed: ' + result.stderr.decode(errors='replace')
    blob_response = json.loads(result.stdout)
    assert blob_response['sha'] == blob_id
    blob_receipt.write_bytes(result.stdout)
    payload.unlink()

summary = {
    'schema': 1, 'run_id': '45037511015', 'run_attempt': 1,
    'source_sha': execution['source_sha'], 'conclusion': 'failure',
    'source_controls': {'status': controls['status'], 'executed': 239, 'passed': 239,
                        'all_four_identity_sets_exact_and_unique': True,
                        'errors': 0, 'failures': 0, 'skipped': 0,
                        'sha256': digest((EV / 'source-controls-result.json').read_bytes())},
    'framework_build': {'status': 'PASS', 'returncode': 0, 'timed_out': False,
                        'started_at': command['started_at'], 'finished_at': command['finished_at'],
                        'command_sha256': digest((EV / 'framework-build.command.json').read_bytes()),
                        'actual_swift': execution['swift'], 'actual_sdk': execution['sdk']},
    'public_spi_surface': {key: surface[key] for key in ['status', 'reviewed_host_and_spi_requirements_observed',
                                                       'public_host_scope_verified', 'qualification_spi_scope_verified']},
    'failure_phase_raw': execution['phase'],
    'failure_phase_normalized': 'CLANG_DECLARATION_EXPORT_AFTER_FRAMEWORK_AND_PUBLIC_SURFACE_PASS',
    'failure_type': execution['error_type'], 'failure': execution['error'],
    'external_consumer_build': 'NOT_RUN', 'external_consumer_runtime': 'NOT_RUN',
    'qualified_sdk_artifact': None, 'source_before_equals_after': True,
    'unqualified_producer_artifact': next(a for a in artifacts if 'Unqualified-Producer-' in a['name']),
    'evidence_artifact': next(a for a in artifacts if 'Framework-Evidence-' in a['name']),
    'retained_distribution_file_count': len(distribution['files']),
    'retained_distribution_bytes': distribution['bytes'],
    'original_compiler_argument_contains_product_include': any(
        '/Build/Products/Debug-Anytype-iphonesimulator/include' in argument
        for argument in collection['compiler_arguments']),
    'exported_include_file_count': sum(name.startswith('Include/') for name in distribution['files']),
    'raw_archive': {'bytes': len(raw), 'sha256': digest(raw), 'git_blob': blob_id,
                    'members': len(members), 'expanded_bytes': sum(item.file_size for item in members),
                    'crc_verified': True, 'all_extracted_members_match': True},
    'no_consumer_continuation_admission': 'Retained upload contains distribution only, without actual producer generated maps/checkouts. No complete retained-input continuation is available.',
    'reviewed_at': datetime.now(timezone.utc).isoformat(),
}
write('TERMINAL_SUMMARY.json', summary)
write('RAW_ARCHIVE_VERIFICATION.json', summary['raw_archive'])

selected = ['source-controls-result.json', 'source-admission.json', 'source-before.json', 'source-after.json',
            'framework-build.command.json', 'compiler-symbolgraph-collection.json',
            'actual-public-surface.json', 'actual-swift.command.json', 'actual-swift.stdout.log', 'actual-swift.stderr.log']
compact = OUT / 'compact-terminal-evidence.zip'
with zipfile.ZipFile(compact, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
    for name in selected:
        zipped.write(EV / name, name)
    for name in ['TERMINAL_SUMMARY.json', 'RAW_ARCHIVE_VERIFICATION.json', 'RAW_ARCHIVE_GIT_BLOB.json']:
        zipped.write(OUT / name, name)
    zipped.write(ROOT / 'WATCH_RECEIPT.json', 'WATCH_RECEIPT.json')
packet = compact.read_bytes()
print(json.dumps({'summary': summary, 'compact_bytes': len(packet), 'compact_sha256': digest(packet),
                  'compact_base64': base64.b64encode(packet).decode() if len(packet) <= 70000 else None}))
