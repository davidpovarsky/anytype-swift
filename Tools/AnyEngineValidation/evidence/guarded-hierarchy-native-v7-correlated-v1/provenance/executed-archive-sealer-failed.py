from pathlib import Path
import hashlib
import json
import shutil

root = Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
out = root / 'Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v7-correlated-v1'
target = out / 'provenance'
if target.exists():
    raise RuntimeError('sealed_provenance_already_exists')
target.mkdir()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


copied = []
allowed = {'.json', '.log', '.py', '.swift', '.diff', '.patch', '.LinkFileList'}


def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = sha(source)
    shutil.copyfile(source, dest)
    if sha(source) != expected or sha(dest) != expected:
        raise RuntimeError('archive_source_changed')
    copied.append({'path': dest.relative_to(out).as_posix(), 'source': str(source),
                   'sha256': expected, 'bytes': source.stat().st_size})


for source, dest in [
    (root / 'build/any-engine-port/guarded-hierarchy-correlated-components-v1', target / 'hierarchy-link'),
    (root / 'build/any-engine-port/http-trace-engine-v3-20261119-213528-034500', target / 'timestamp-engine'),
    (root / 'Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v7-v2', target / 'prior-untraced-control'),
    (root / 'Tools/AnyEngineValidation/evidence/guarded-hierarchy-native-v7-traced-v1', target / 'prior-traced-control'),
]:
    for file in sorted(source.rglob('*')):
        if file.is_file() and file.suffix in allowed and '__pycache__' not in file.parts:
            copy(file, dest / file.relative_to(source))

extra = [
    ('build/any-engine-port/build_http_trace_engine_v3.py', 'executed-timestamp-engine-builder.py'),
    ('Tools/AnyEngineValidation/run_native_torah_probe.py', 'executed-timestamp-bounded-helper.py'),
    ('Tools/AnyEngineValidation/evidence/native-document-metadata-v7-source.json', 'native/native-document-metadata-v7-source.json'),
    ('Tools/AnyEngineValidation/evidence/native-document-metadata-v7-any.patch', 'native/native-document-metadata-v7-any.patch'),
    ('Tools/AnyEngineValidation/evidence/native-document-metadata-v7-sdk.patch', 'native/native-document-metadata-v7-sdk.patch'),
    ('Tools/AnyEngineValidation/evidence/native-torah-workflow-scripts/reusable-trace-engine-v2.json', 'v2-trace/reusable-trace-engine-v2.json'),
    ('Tools/AnyEngineValidation/evidence/native-torah-workflow-scripts/AnyHTTPClient.trace-v2.diff', 'v2-trace/AnyHTTPClient.trace-v2.diff'),
    ('Tools/AnyEngineValidation/evidence/native-v7-http-contract-review-v1.json', 'native-v7-http-contract-review-v1.json'),
    ('Tools/AnyEngineValidation/evidence/native-v7-hierarchy-failed-health-correlation-v1.json', 'prior-health-correlation.json'),
]
for source, dest in extra:
    copy(root / source, target / dest)
if sha(target / 'executed-timestamp-bounded-helper.py') != '019bb3d4b20324c4a1e5987c602d6863b01770cd27553bf62dbc423f539336e4':
    raise RuntimeError('timestamp_bounded_helper_changed')
copy(Path(__file__), target / 'executed-archive-sealer.py')
report = json.loads((out / 'correlation.json').read_text(encoding='utf-8'))
manifest = {
    'status': 'FROZEN_FAILED_DIAGNOSTIC_EVIDENCE',
    'scope': 'Single correlated hierarchy continuation; unchanged20 assertions; HTTP metadata only. No PASS or transport fix claimed.',
    'acceptanceStatus': report['status'], 'passedCount': report['passedCount'], 'requiredCount': 20,
    'nativeBinarySHA256': report['nativeBinarySHA256'], 'nativeManifestSHA256': report['nativeManifestSHA256'],
    'probeSHA256': report['probeSHA256'],
    'nativeHandlerCompletionObservation': {
        'clientRoute': 'GET /v1/auth', 'clientBeginUnixMs': 1795124534403,
        'nativeCompletionTime': '2026-11-19T23:42:14.403+0200', 'nativeStatus': 200,
        'nativeDuration': '0s', 'clientErrorUnixMs': 1795124564417, 'clientErrorCode': -1001,
        'socketFlushAndClientDeliveryObserved': False,
    },
    'priorControlsRetainedInsideProvenance': True, 'privateNativeLogsOrHandshakeCopied': False,
    'originalUntracedFailureResolved': False, 'sourceStable': report['runtimeSourceStable'],
    'nativeBinaryStable': report['runtimeNativeBinaryStable'], 'producerFiles': copied,
    'files': [{'path': p.relative_to(out).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
              for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in p.parts],
}
file = out / 'checkpoint.json'
file.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': manifest['status'], 'passedCount': manifest['passedCount'], 'requiredCount': 20,
                  'files': len(manifest['files']), 'copiedProducerFiles': len(copied),
                  'checkpointSHA256': sha(file), 'prefix': out.relative_to(root).as_posix()}))
