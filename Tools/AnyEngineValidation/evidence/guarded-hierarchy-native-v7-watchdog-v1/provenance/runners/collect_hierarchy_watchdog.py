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
    expected_logs = Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119\.runtime-artifacts\peer-native-v7-watchdog-hierarchy-v1')
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
    events, pairs, watchdog = [], {}, []
    trace_path = acceptance / 'run/stderr.log'
    for number, line in enumerate(trace_path.read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('ANY_HTTP_WATCHDOG '):
            value = json.loads(line[len('ANY_HTTP_WATCHDOG '):])
            value['line'] = number
            watchdog.append(value)
            continue
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
    control_path = acceptance / 'run/watchdog-python-control.json'
    independent = json.loads(control_path.read_text(encoding='utf8'))
    activations = [event for event in watchdog if event['phase'] == 'activate']
    if len(activations) > 1 or independent.get('activationCount') != len(activations):
        raise RuntimeError('watchdog_activation_count_invalid')
    observation = {'maximumActivations': 1, 'actualActivations': len(activations),
                   'sameProcessEvents': watchdog, 'independentPythonControl': independent,
                   'businessResultSuppliedByEitherControl': False,
                   'closedEventMeaning': 'Control-session invalidateAndCancel returned after its request completed/errored; no socket FIN or delegate acknowledgment claim.'}
    if activations:
        active = activations[0]
        original = pairs.get(active['originalRequestID'])
        if not original or 'begin' not in original:
            raise RuntimeError('activated_original_request_pair_missing')
        observation['originalRequest'] = original
        observation['nativeCompletedBeforeControlActivation'] = [row for row in native_rows
            if row['method'] == active['method'] and row['path'] == active['path']
            and parse_time(row['time']) is not None
            and original['begin']['timestampUnixMs'] - 2 <= parse_time(row['time']) < active['timestampUnixMs']]
        fresh_responses = [v for v in watchdog if v['phase'] == 'response' and v.get('originalRequestID') == active['originalRequestID']]
        python_report = independent.get('report', {})
        end = original.get('error', original.get('response', {})).get('timestampUnixMs')
        controls_success = (len(fresh_responses) == 1 and fresh_responses[0].get('status') == 200
            and python_report.get('status') == 200 and python_report.get('outcome') == 'response'
            and independent.get('process', {}).get('exitCode') == 0
            and independent.get('process', {}).get('timedOut') is False)
        both_before_original = (controls_success and end is not None
            and fresh_responses[0]['timestampUnixMs'] < end
            and python_report['finishedTimestampUnixMs'] < end)
        observation['bothControlReadsCompleted200'] = controls_success
        observation['bothCompletedBeforeOriginalAwaitEnded'] = both_before_original
        if both_before_original and 'error' in original:
            observation['classification'] = 'Original await failed while both independent fresh reads completed200; isolates the original request/connection/session path, without identifying native final-flush versus client completion ownership.'
        elif both_before_original:
            observation['classification'] = 'Both fresh reads completed before the original eventually succeeded; a delayed original was observed, not an original request failure.'
        else:
            observation['classification'] = 'Control outcomes retained; no stronger ownership conclusion supported.'
    else:
        observation['classification'] = 'No one-second armed pending auth/health await was observed; watchdog controls were not activated.'
    checks = report.get('checks', {})
    passed = receipt.get('status') == 'PASS' and report.get('status') == 'PASS' and len(checks) == 20 and all(v is True for v in checks.values())
    summary = {
        'status': 'PASS_HIERARCHY20_WITH_DIAGNOSTIC_LOGGING' if passed else 'FAIL_HIERARCHY_ACCEPTANCE_CORRELATED_TRACE_AVAILABLE',
        'scope': 'One authorized fresh native Info fixture and Space; unchanged20 assertions, timestamped client trace and one explicitly armed diagnostic watchdog. Original30s request unchanged; at most one fresh Swift and one bounded Python same-path read, no control result used by the hierarchy.',
        'watchdogObservation': observation,
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
                      'correlationSHA256': sha(target), 'watchdogActivations': len(activations), 'watchdogClassification': observation['classification']}))


if __name__ == '__main__':
    main()
