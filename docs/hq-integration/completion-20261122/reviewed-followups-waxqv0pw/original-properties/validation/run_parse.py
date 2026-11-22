from pathlib import Path, PurePosixPath
import json, hashlib, base64, zlib, subprocess, datetime, time

PACKED = '__PROPERTY_SOURCE_PAYLOAD__'
PAYLOAD_SHA = '__PAYLOAD_SHA__'
raw = zlib.decompress(base64.b64decode(PACKED, validate=True))
assert hashlib.sha256(raw).hexdigest() == PAYLOAD_SHA
payload = json.loads(raw)
manifest = payload['manifest']
assert manifest['combined_patch']['sha256'] == '90605b0cb2576c87c3102729ef4784733fc4e24989045acd756b3b9d1f6d5a25'
assert len(manifest['files']) == len(payload['source']) == 16
root = Path(r'C:\Users\DAVID\Code\Codex-Agent-HQ\build\property-source-90605b0c-waxqv0pw-20261122')
assert not root.exists(), 'Existing validation checkpoint needs read-only diagnosis; do not repeat the compiler blindly'
root.mkdir(parents=True)
(root / 'PAYLOAD.json').write_bytes(raw)
(root / 'START.json').write_text(json.dumps({'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'payload_sha256': PAYLOAD_SHA, 'patch_sha256': manifest['combined_patch']['sha256']}), encoding='utf-8')
for source, expected in zip(payload['source'], manifest['files']):
    assert source['path'] == expected['path']
    path = PurePosixPath(source['path'])
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in source['path']
    data = base64.b64decode(source['base64'], validate=True)
    assert hashlib.sha256(data).hexdigest() == expected['source_sha256'] and len(data) == expected['source_bytes']
    dest = root / 'source' / source['path']
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
command = [r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE',
           '-frontend', '-parse', '-target', 'arm64-apple-ios27.0-simulator', '-D', 'DEBUG']
command += [str(root / 'source' / f['path']) for f in manifest['files']]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
timer = time.monotonic()
result = subprocess.run(command, capture_output=True, timeout=120)
for f in manifest['files']:
    assert hashlib.sha256((root / 'source' / f['path']).read_bytes()).hexdigest() == f['source_sha256']
report = {'status': 'PASS_16_COMPLETE_SWIFT_FILES_SYNTAX' if result.returncode == 0 else 'FAILED_SYNTAX',
          'scope': 'One syntax parse of the16 complete changed Swift files. No Apple SDK semantic/module typecheck or native execution.',
          'source_base': manifest['base_commit'], 'patch': manifest['combined_patch'], 'inputs': manifest['files'],
          'payload_sha256': PAYLOAD_SHA, 'compiler_processes': 1, 'prior_suites_rerun': False,
          'started_at': started, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'duration_s': time.monotonic() - timer, 'command': command, 'exit_code': result.returncode,
          'stdout': result.stdout.decode('utf-8', 'replace'), 'stderr': result.stderr.decode('utf-8', 'replace'),
          'Apple_typecheck': 'NOT_RUN', 'Native': 'NOT_RUN'}
receipt = json.dumps(report, indent=2).encode()
(root / 'PARSE_RESULT.json').write_bytes(receipt)
print(json.dumps({'status': report['status'], 'exit_code': result.returncode, 'files': len(manifest['files']),
                  'duration_s': report['duration_s'], 'receipt': str(root / 'PARSE_RESULT.json'),
                  'receipt_sha256': hashlib.sha256(receipt).hexdigest(), 'receipt_bytes': len(receipt),
                  'stderr': report['stderr'][-5000:]}))
raise SystemExit(result.returncode)
