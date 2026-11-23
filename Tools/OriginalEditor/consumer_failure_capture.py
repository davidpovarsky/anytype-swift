"""Exact consumer launch output and bounded, attributable crash observations.

No runtime acceptance, retry, repair, host reset, simulator mutation or process
launch occurs here. The producer's existing owned command runner invokes the
capture CLI with a finite timeout before its existing simulator cleanup.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import sys
import time
import uuid

BUNDLE_ID = 'org.otzaria.acceptance.original-editor'
EXECUTABLE = 'OriginalEditorConsumer'
MAX_REPORT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_REPORTS = 8
MAX_DIRECTORY_ENTRIES = 2048
MAX_ATTEMPT_SECONDS = 120


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def read_regular(path, maximum):
    """Reject aliases/special files and bound a single observed file read."""
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
            'Unexpected or oversized diagnostic file')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and (opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
                'Diagnostic file changed before open')
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) <= maximum and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            'Diagnostic file changed during observation')
    return raw, before


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def instant(value):
    require(isinstance(value, str), 'Missing report timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Report timestamp has no timezone')
    return parsed.timestamp()


def validate_producer(producer):
    require(isinstance(producer, dict) and re.fullmatch(r'[0-9a-f]{40}', producer.get('source_sha', ''))
            and re.fullmatch(r'[1-9][0-9]*', producer.get('run_id', ''))
            and producer.get('run_attempt') == '1'
            and all(producer[key] == os.environ.get(env) for key, env in
                    [('source_sha', 'GITHUB_SHA'), ('run_id', 'GITHUB_RUN_ID'), ('run_attempt', 'GITHUB_RUN_ATTEMPT')]),
            'Capture producer differs or has incomplete identity')


def validate_launch(original_argv, language, udid):
    require(isinstance(original_argv, list) and len(original_argv) == 12
            and original_argv[:7] == ['xcrun', 'simctl', 'launch', '--terminate-running-process', udid,
                                     BUNDLE_ID, '--original-editor-nonce']
            and str(uuid.UUID(original_argv[7])).upper() == original_argv[7].upper()
            and original_argv[8:] == ['-AppleLanguages', '(' + language + ')', '-AppleLocale',
                                     'he_IL' if language == 'he' else 'en_US'], 'Unexpected original consumer launch')


def combine_launch_help(stdout, stderr):
    """Use both authentic streams after the owned help command succeeds."""
    require(isinstance(stdout, str) and isinstance(stderr, str)
            and len(stdout) + len(stderr) < 65536, 'Expected bounded simctl help streams')
    text = stdout + '\n' + stderr
    require(re.search(r'--stdout(?:=|\s|<|\[)', text)
            and re.search(r'--stderr(?:=|\s|<|\[)', text),
            'Actual simctl does not advertise the required output options')
    return text


def prepare_launch_capture(evidence, preflight, installed, original_argv, language, launch_help):
    """Add only stdout/stderr destinations to this exact original launch.

    launch_help must combine both streams from this producer's successful, bounded
    `xcrun simctl help launch`. The returned original command still controls
    launch timeout and error handling. It is never executed by this helper.
    """
    evidence, installed = Path(evidence).resolve(), Path(installed)
    require(evidence.is_dir() and language in {'en', 'he'}, 'Invalid capture destination/language')
    validate_producer({key: preflight.get(key) for key in ['source_sha', 'run_id', 'run_attempt']})
    require(preflight.get('status') == 'PREFLIGHT_PASS_UI_NOT_RUN',
            'Capture is not bound to the current producer preflight')
    selected = preflight['selected']['ipad']
    udid = selected.get('udid')
    require(isinstance(udid, str) and str(uuid.UUID(udid)).upper() == udid.upper()
            and selected.get('name') == 'Pinkha-UI27-' + preflight['run_id'] + '-ipad',
            'Capture requires the exact producer-owned simulator')
    require(isinstance(launch_help, str) and len(launch_help) <= 65536
            and re.search(r'--stdout(?:=|\s|<|\[)', launch_help)
            and re.search(r'--stderr(?:=|\s|<|\[)', launch_help),
            'Actual simctl does not advertise the required output options')
    validate_launch(original_argv, language, udid)
    device_root = Path.home() / 'Library/Developer/CoreSimulator/Devices' / udid
    expected_parent = device_root / 'data/Containers/Bundle/Application'
    require(installed.is_absolute() and installed.resolve(strict=True) == installed
            and installed.name == EXECUTABLE + '.app' and installed.is_relative_to(expected_parent)
            and len(installed.relative_to(expected_parent).parts) == 2, 'Consumer is not installed in the exact owned device')
    info, _ = read_regular(installed / 'Info.plist', 1024 * 1024)
    metadata = plistlib.loads(info)
    require(metadata.get('CFBundleIdentifier') == BUNDLE_ID and metadata.get('CFBundleExecutable') == EXECUTABLE,
            'Installed consumer identity differs')
    executable = installed / EXECUTABLE
    require(executable.is_file() and not executable.is_symlink(), 'Installed consumer executable is absent or aliased')
    destination = evidence / 'consumer-failure-capture' / ('consumer-' + language)
    destination.mkdir(parents=True, exist_ok=False)
    streams = {}
    for stream in ['stdout', 'stderr']:
        path = destination / ('application.' + stream + '.log')
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        streams[stream] = str(path)
    argv = original_argv[:3] + ['--stdout=' + streams['stdout'], '--stderr=' + streams['stderr']] + original_argv[3:]
    request = {'schema': 1, 'kind': 'EXACT_CONSUMER_FAILURE_CAPTURE', 'prepared_unix': time.time(),
               'producer': {key: preflight[key] for key in ['source_sha', 'run_id', 'run_attempt']},
               'owned_udid': udid, 'bundle_id': BUNDLE_ID, 'executable': EXECUTABLE,
               'installed_app': str(installed), 'expected_process_path': str(executable),
               'language': language, 'launch_argv': argv, 'original_launch_argv': original_argv,
               'launch_command_name': 'consumer-' + language + '-launch', 'evidence_root': str(evidence),
               'streams': streams, 'installed_info': identity(info),
               'actual_launch_help': identity(launch_help.encode()), 'runtime_authority': False}
    request_path = destination / 'REQUEST.json'
    write_new(request_path, request)
    return argv, request_path


def report_identity(raw, suffix):
    """Read the native identity fields; never search for a loose UDID substring."""
    text = raw.decode('utf-8')
    if suffix == '.ips':
        decoder = json.JSONDecoder()
        header, end = decoder.raw_decode(text.lstrip())
        remaining = text.lstrip()[end:].strip()
        body = json.loads(remaining) if remaining else header
        require(isinstance(header, dict) and isinstance(body, dict), 'Unexpected IPS report shape')
        bundle = body.get('bundleInfo', {}).get('CFBundleIdentifier')
        require(header.get('bundleID', bundle) == bundle, 'Conflicting IPS bundle identity')
        return {'bundle_id': bundle, 'process_name': body.get('procName'),
                'process_path': body.get('procPath'), 'captured_unix': instant(body.get('captureTime'))}
    require(suffix == '.crash', 'Unsupported crash format')
    def field(name):
        found = re.findall(r'^' + re.escape(name) + r':\s*(.*?)\s*$', text, re.M)
        require(len(found) == 1, 'Missing or ambiguous native crash field')
        return found[0]
    process = re.fullmatch(r'(.+) \[\d+\]', field('Process'))
    require(process is not None, 'Unexpected crash process field')
    return {'bundle_id': field('Identifier'), 'process_name': process[1],
            'process_path': field('Path'), 'captured_unix': instant(field('Date/Time'))}


def collect_failure(request_path):
    """One read-only snapshot; caller must run this CLI in its finite owner."""
    request_path = Path(request_path)
    raw, _ = read_regular(request_path, 65536)
    request = json.loads(raw)
    require(request.get('schema') == 1 and request.get('kind') == 'EXACT_CONSUMER_FAILURE_CAPTURE'
            and request.get('bundle_id') == BUNDLE_ID and request.get('executable') == EXECUTABLE
            and request.get('language') in {'en', 'he'}, 'Invalid consumer capture request')
    destination = request_path.parent
    evidence = Path(request['evidence_root'])
    require(request_path.name == 'REQUEST.json' and evidence.resolve(strict=True) == evidence
            and destination == evidence / 'consumer-failure-capture' / ('consumer-' + request['language'])
            and destination.resolve(strict=True) == destination, 'Capture destination is not the original owned path')
    validate_producer(request['producer'])
    udid = request['owned_udid']
    require(isinstance(udid, str) and str(uuid.UUID(udid)).upper() == udid.upper(), 'Malformed owned simulator identity')
    validate_launch(request['original_launch_argv'], request['language'], udid)
    installed = Path(request['installed_app'])
    expected_parent = Path.home() / 'Library/Developer/CoreSimulator/Devices' / udid / 'data/Containers/Bundle/Application'
    require(installed.is_absolute() and installed.resolve(strict=True) == installed
            and installed.name == EXECUTABLE + '.app' and installed.is_relative_to(expected_parent)
            and len(installed.relative_to(expected_parent).parts) == 2
            and request['expected_process_path'] == str(installed / EXECUTABLE), 'Capture app ownership changed')
    expected_streams = {stream: str(destination / ('application.' + stream + '.log')) for stream in ['stdout', 'stderr']}
    require(request['streams'] == expected_streams
            and request['launch_argv'] == request['original_launch_argv'][:3] +
                ['--stdout=' + expected_streams['stdout'], '--stderr=' + expected_streams['stderr']] + request['original_launch_argv'][3:]
            and request['launch_command_name'] == 'consumer-' + request['language'] + '-launch', 'Capture launch identity changed')
    end = time.time()
    require(0 <= end - request['prepared_unix'] <= MAX_ATTEMPT_SECONDS, 'Capture is outside this attempt time window')
    command_path = evidence / (request['launch_command_name'] + '.command.json')
    command_raw, _ = read_regular(command_path, 65536)
    command = json.loads(command_raw)
    require(command.get('command') == request['launch_argv'] and command.get('returncode') is not None,
            'Actual launch command is missing, changed or not terminal')
    start = instant(command['started_at'])
    require(request['prepared_unix'] <= start <= instant(command['finished_at']) <= end,
            'Actual launch timing differs')
    result = {'schema': 1, 'status': 'BOUNDED_READ_ONLY_FAILURE_OBSERVATION',
              'runtime_authority': False, 'producer': request['producer'], 'owned_udid': request['owned_udid'],
              'bundle_id': BUNDLE_ID, 'process_path': request['expected_process_path'],
              'window_started_unix': start, 'window_ended_unix': end, 'request': identity(raw),
              'actual_launch_command': identity(command_raw), 'launch_returncode': command['returncode'],
              'launch_timed_out': command.get('timed_out'), 'streams': {}, 'crash_reports': [],
              'scope': 'Observed exact app output and attributable crash files only; no runtime success, complete crash delivery or process drain inferred.'}
    for stream in ['stdout', 'stderr']:
        app_path = destination / ('application.' + stream + '.log')
        require(request['streams'][stream] == str(app_path), 'Application output path changed')
        for label, path in [('application_' + stream, app_path),
                            ('simctl_' + stream, evidence / (request['launch_command_name'] + '.' + stream + '.log'))]:
            try:
                observed, _ = read_regular(path, MAX_OUTPUT_BYTES)
                if label.startswith('simctl_'):
                    require(identity(observed)['sha256'] == command[stream + '_sha256'], 'Retained launch output changed')
                result['streams'][label] = {'status': 'OBSERVED_STABLE_AT_READ', 'path': str(path.relative_to(evidence)), **identity(observed)}
            except (OSError, RuntimeError) as error:
                result['streams'][label] = {'status': 'UNAVAILABLE_OR_UNSTABLE', 'error_type': type(error).__name__}
    report_root = Path.home() / 'Library/Logs/DiagnosticReports'
    deadline = time.monotonic() + 5
    examined = 0
    candidates = 0
    skipped = 0
    result['directory_observation'] = 'NOT_PRESENT'
    if report_root.exists():
        require(report_root.is_dir() and report_root.resolve(strict=True) == report_root, 'Crash report directory is aliased')
        result['directory_observation'] = 'ONE_NONRECURSIVE_BOUNDED_SCAN'
        with os.scandir(report_root) as entries:
            for entry in entries:
                examined += 1
                if examined > MAX_DIRECTORY_ENTRIES or time.monotonic() >= deadline or len(result['crash_reports']) >= MAX_REPORTS:
                    result['scan_bound_reached'] = True
                    break
                if not re.fullmatch(re.escape(EXECUTABLE) + r'[-_][^/\\]+\.(ips|crash)', entry.name):
                    continue
                try:
                    observed_stat = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(observed_stat.st_mode) or not start <= observed_stat.st_mtime <= end:
                        continue
                    candidates += 1
                    report_raw, captured_stat = read_regular(Path(entry.path), MAX_REPORT_BYTES)
                    require((captured_stat.st_dev, captured_stat.st_ino, captured_stat.st_mtime_ns) ==
                            (observed_stat.st_dev, observed_stat.st_ino, observed_stat.st_mtime_ns), 'Crash changed during selection')
                    actual = report_identity(report_raw, Path(entry.name).suffix)
                    if (actual['bundle_id'] != BUNDLE_ID or actual['process_name'] != EXECUTABLE
                            or actual['process_path'] != request['expected_process_path']
                            or not start <= actual['captured_unix'] <= end):
                        skipped += 1
                        continue
                    output = destination / ('crash-' + str(len(result['crash_reports']) + 1) + Path(entry.name).suffix)
                    with output.open('xb') as stream:
                        stream.write(report_raw)
                    result['crash_reports'].append({'path': output.name, 'native_identity': actual, **identity(report_raw)})
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError):
                    skipped += 1
        result['bounded_entries_examined'] = min(examined, MAX_DIRECTORY_ENTRIES)
    result['candidate_reports_read'] = candidates
    result['candidate_reports_unattributed_or_unreadable'] = skipped
    result['captured_report_count'] = len(result['crash_reports'])
    result['crash_delivery'] = 'OBSERVED_MATCHING_REPORTS' if result['crash_reports'] else 'NO_ATTRIBUTABLE_REPORT_OBSERVED_IN_THIS_SNAPSHOT'
    write_new(destination / 'OBSERVATION.json', result)
    return result


if __name__ == '__main__':
    require(len(sys.argv) == 3 and sys.argv[1] == '--capture-failure', 'Unexpected capture invocation')
    observed = collect_failure(sys.argv[2])
    print(json.dumps({'status': observed['status'], 'captured_report_count': observed['captured_report_count'], 'runtime_authority': False}))
