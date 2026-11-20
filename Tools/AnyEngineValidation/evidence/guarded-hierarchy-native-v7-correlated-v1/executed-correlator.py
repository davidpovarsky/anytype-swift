"""Export only allowed HTTP metadata and correlate the owned diagnostic run."""
from pathlib import Path
from collections import Counter
import argparse
import datetime
import hashlib
import json
import re
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return int(parsed.timestamp() * 1000)
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--native-log-dir', type=Path, required=True)
    args = parser.parse_args()
    root, output, logs = args.repo_root.resolve(), args.output_dir.resolve(), args.native_log_dir.resolve()
    expected_logs = Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119\.runtime-artifacts\peer-native-v7-correlated-hierarchy')
    if logs != expected_logs.resolve():
        raise RuntimeError('exact_owned_native_log_directory_required')
    acceptance = output / 'acceptance'
    receipt = json.loads((acceptance / 'result.json').read_text(encoding='utf-8'))
    report = json.loads((acceptance / 'run/stdout.json').read_text(encoding='utf-8'))
    fixture = json.loads((output / 'fixture.json').read_text(encoding='utf-8'))
    if receipt.get('binarySHA256') != fixture['binarySHA256'] or receipt.get('endpoint') != fixture['endpoint']:
        raise RuntimeError('runtime_and_fixture_identity_differ')
    native_rows, native_metadata = [], []
    for name in ('stdout.private.log', 'stderr.private.log'):
        path = logs / name
        with path.open('rb') as stream:
            data = stream.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise RuntimeError('native_private_log_read_bound_exceeded')
        native_metadata.append({'path': str(path), 'capturedBytes': len(data),
                                'capturedPrefixSHA256': hashlib.sha256(data).hexdigest(),
                                'privateContentsExported': False, 'lastLineComplete': not data or data.endswith(b'\n')})
        for line in data.decode('utf-8', errors='replace').splitlines():
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, dict) or value.get('logger') != 'http' or value.get('msg') != 'http':
                continue
            if value.get('method') not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
                continue
            path_value, status = value.get('path'), value.get('status')
            if not isinstance(path_value, str) or not path_value.startswith('/') or len(path_value.encode()) > 8192:
                continue
            if not isinstance(status, int) or not 100 <= status <= 599:
                continue
            native_rows.append({'method': value['method'], 'path': path_value, 'status': status,
                                'duration': value.get('duration'), 'time': value.get('ts')})
    native_rows.sort(key=lambda row: parse_time(row['time']) or 0)
    native_path = output / 'native-http.json'
    if native_path.exists():
        raise RuntimeError('native_access_snapshot_already_exists')
    native_path.write_text(json.dumps(native_rows, indent=2) + '\n', encoding='utf-8')
    events, pairs = [], {}
    trace_path = acceptance / 'run/stderr.log'
    for number, line in enumerate(trace_path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.startswith('ANY_HTTP_TRACE '):
            continue
        value = json.loads(line[len('ANY_HTTP_TRACE '):])
        if not isinstance(value.get('timestampUnixMs'), int):
            raise RuntimeError('absolute_client_timestamp_missing')
        value['line'] = number
        events.append(value)
        bucket = pairs.setdefault(value['id'], {})
        if value['phase'] in bucket:
            raise RuntimeError('duplicate_client_trace_phase')
        bucket[value['phase']] = value
    if not events or not native_rows:
        raise RuntimeError('both_correlated_streams_required')
    failures = []
    for request_id, pair in pairs.items():
        if 'error' not in pair:
            continue
        begin, error = pair['begin'], pair['error']
        start, end = begin['timestampUnixMs'], error['timestampUnixMs']
        candidates = [row for row in native_rows
                      if row['method'] == begin['method'] and row['path'] == begin['path']
                      and parse_time(row['time']) is not None
                      and start - 2 <= parse_time(row['time']) <= end + 2]
        surrounding = [row for row in native_rows if parse_time(row['time']) is not None
                       and start - 1000 <= parse_time(row['time']) <= end + 1000]
        failures.append({'requestID': request_id, 'clientBegin': begin, 'clientError': error,
                         'matchingCompletedNativeRequests': candidates,
                         'surroundingNativeRecords': surrounding[-40:],
                         'classification': 'Time-correlated completion records only; no per-request wire identifier. A missing completion cannot distinguish never-arrived from still-running.',
                         'nativeHandlerCompletionLogging': True})
    checks = report.get('checks', {})
    passed = receipt.get('status') == 'PASS' and report.get('status') == 'PASS' and len(checks) == 20 and all(v is True for v in checks.values())
    summary = {
        'status': 'PASS_HIERARCHY20_WITH_DIAGNOSTIC_LOGGING' if passed else 'FAIL_HIERARCHY_ACCEPTANCE_CORRELATED_TRACE_AVAILABLE',
        'scope': 'One authorized fresh native fixture and fresh Space; unchanged20 hierarchy assertions; native HTTP Info access logging plus client absolute timestamps only.',
        'originalUntracedTransportFailureResolved': False, 'transportSettingsChanged': False,
        'nativeBinarySHA256': fixture['binarySHA256'], 'nativeManifestSHA256': fixture['nativeSourceManifestSHA256'],
        'probeSHA256': receipt['probeSHA256'], 'runtimeSourceStable': receipt.get('sourceStable'),
        'runtimeNativeBinaryStable': receipt.get('nativeBinaryStable'),
        'passedCount': len(checks), 'requiredCount': 20, 'checks': checks,
        'accountID': receipt['accountID'], 'spaceID': receipt['spaceID'], 'endpoint': receipt['endpoint'],
        'eventCounts': dict(Counter(event['phase'] for event in events)),
        'nativeAccessRecordCount': len(native_rows), 'failedAwaits': failures,
        'nativePrivateLogSnapshotMetadata': native_metadata,
        'evidence': {'runtimeReceiptSHA256': sha(acceptance / 'result.json'),
                     'swiftReportSHA256': sha(acceptance / 'run/stdout.json'),
                     'clientTraceSHA256': sha(trace_path), 'nativeAccessMetadataSHA256': sha(native_path),
                     'fixtureSHA256': sha(output / 'fixture.json')},
        'limits': ['Native access records are written after the handler returns, before transport delivery is established.',
                   'The client begin is before URLSession.data(for:); it does not prove dispatch to the native socket.',
                   'Time overlap may include an adjacent same-path request; candidate records do not invent a unique request identity.',
                   'All earlier failures remain retained; a passing diagnostic run does not establish untraced transport reliability.',
                   'No request bodies, response bodies, cookies, authorization, recovery material or private handshake contents are exported.'],
    }
    target = output / 'correlation.json'
    if target.exists():
        raise RuntimeError('correlation_summary_already_exists')
    shutil.copyfile(__file__, output / 'executed-correlator.py')
    target.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'passedCount': len(checks), 'requiredCount': 20,
                      'eventCounts': summary['eventCounts'], 'nativeAccessRecordCount': len(native_rows),
                      'failedRoutes': [{'method': p['clientBegin']['method'], 'path': p['clientBegin']['path'],
                                        'nativeCandidateCount': len(p['matchingCompletedNativeRequests'])} for p in failures],
                      'correlationSHA256': sha(target)}))


if __name__ == '__main__':
    main()
