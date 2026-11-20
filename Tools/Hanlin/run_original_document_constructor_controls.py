"""Run unchanged74 against original43, then candidate49 gate controls; no Swift."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from host_command import cancellation_signals, stop_owned_group

MANIFEST = Path(__file__).with_name('original_document_constructor_controls.json')

def require(value, reason):
    if not value:
        raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular input: ' + str(path))
    return path.read_bytes().replace(b'\r\n', b'\n')

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])

def source_record(root, paths):
    result = {}
    for path in sorted(paths):
        raw = canonical(root / path)
        require(raw == git(root, 'show', 'HEAD:' + path), 'Input differs from Git: ' + path)
        result[path] = {'bytes': len(raw), 'sha256': sha(raw)}
    return result

def exact_success(log, expected, returncode):
    # Verbose unittest leaves are actual control outcomes; synthetic result
    # nodes used inside those controls are never reported as Apple execution.
    starts = list(re.finditer(r'^test\w+ \(([^\n]+)\) \.\.\. ', log, re.M))
    rows = [match.group(1) for match in starts]
    require(returncode == 0 and len(rows) == len(set(rows)) == len(expected)
            and set(rows) == set(expected), 'Missing, duplicate or nonpassing controls')
    summary = re.search(r'\n-+\nRan ' + str(len(expected)) + r' tests in [\d.]+s\s+OK\s*$', log)
    require(summary,
            'Incomplete or skipped control summary')
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else summary.start()
        result = log[match.end():end].rstrip()
        # Several unchanged controls intentionally print real command/cancellation
        # diagnostics before unittest writes its final status on a separate line.
        require(result == 'ok' or result.endswith('\nok'), 'Nonpassing named control: ' + match.group(1))
    return sorted(rows)

def command(argv, cwd, evidence, name, expected):
    require(not (evidence / (name + '.json')).exists(), 'Refuse overwritten control evidence')
    receipt = {'command': argv, 'cwd': str(cwd), 'timeout_seconds': 180,
               'started_at': datetime.now(timezone.utc).isoformat(), 'returncode': None,
               'status': 'RUNNING', 'verified_complete_controls': [], 'partial_execution': 'UNKNOWN'}
    process = None
    output = b''
    try:
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        with cancellation_signals():
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            output, _ = process.communicate(timeout=180)
        receipt['returncode'] = process.returncode
        receipt['verified_complete_controls'] = exact_success(output.decode('utf-8'), expected, process.returncode)
        receipt.update(status='PASS', partial_execution='NONE')
    except BaseException as error:
        if process is not None:
            receipt['owned_group_cleanup'] = stop_owned_group(process)
            remaining, _ = process.communicate(timeout=1)
            output = remaining if remaining else output
            receipt['returncode'] = process.poll()
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error),
                       observed_passing_leaves=re.findall(r'^test\w+ \(([^\n]+)\) \.\.\. ok$',
                                                         output.decode('utf-8', errors='replace'), re.M))
        raise
    finally:
        (evidence / (name + '.log')).write_bytes(output)
        receipt.update(finished_at=datetime.now(timezone.utc).isoformat(), output_sha256=sha(output))
        (evidence / (name + '.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt

def run(app, baseline, evidence):
    require(os.name == 'posix', 'Original cancellation controls require an actual POSIX host')
    require(app != baseline, 'Baseline controls must not replace candidate source')
    data = json.loads(MANIFEST.read_text())
    require(git(baseline, 'rev-parse', 'HEAD').decode().strip() == data['baseline_sha'],
            'Baseline is not the original immutable43 source')
    before = source_record(baseline, data['baseline_inputs'])
    require({path: value['sha256'] for path, value in before.items()} == data['baseline_inputs'],
            'Original74 or their original source dependencies changed')
    candidate_paths = set(data['baseline_inputs']) | set(data['candidate_runtime'])
    current = source_record(app, candidate_paths)
    for path, expected in data['baseline_inputs'].items():
        if path not in data['existing_modified_paths']:
            require(current[path]['sha256'] == expected, 'Original candidate gate input changed: ' + path)
    candidate_host = canonical(app / 'Tools/Hanlin/run_host_tests.py')
    inverse = candidate_host.decode()
    for change in reversed(data['host_inverse']):
        require(inverse.count(change['after']) == 1, 'Host inverse hunk missing or repeated')
        inverse = inverse.replace(change['after'], change['before'], 1)
    require(inverse.encode() == canonical(baseline / 'Tools/Hanlin/run_host_tests.py'),
            'Original host behavior changed outside the new profile')
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
               'status': 'RUNNING', 'baseline_sha': data['baseline_sha'],
               'candidate_sha': git(app, 'rev-parse', 'HEAD').decode().strip(),
               'before': {'baseline': before, 'candidate': current},
               'original74': 'NOT_RUN', 'candidate_gate_controls': 'NOT_RUN',
               'swift_methods_executed': 0, 'native_ui_tests': 0}
    host = baseline / 'Tools/Hanlin/run_host_tests.py'
    old_host = host.read_bytes()
    overlays = [Path(path) for path in data['baseline_overlay_new_paths']]
    require(all(not (baseline / path).exists() for path in overlays), 'Refuse an existing overlay file')
    written = []
    try:
        try:
            host.write_bytes(candidate_host)
            for path in overlays:
                value = canonical(app / path)
                (baseline / path).write_bytes(value)
                written.append((path, value))
            receipt['original74'] = command([sys.executable, '-B', '-m', 'unittest', 'discover',
                '-s', 'Tools/Hanlin', '-p', 'test_run_host*.py', '-v'], baseline, evidence,
                'original74-baseline-profile', data['original74_methods'])
        finally:
            require(host.read_bytes() == candidate_host, 'Overlaid host changed during controls')
            host.write_bytes(old_host)
            for path, expected in reversed(written):
                require((baseline / path).read_bytes() == expected, 'Overlay changed during controls')
                (baseline / path).unlink()
        require(source_record(baseline, data['baseline_inputs']) == before, 'Original baseline was not restored')
        receipt['candidate_gate_controls'] = command([sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', 'Tools/Hanlin', '-p', 'test_document_constructor_profile.py', '-v'], app, evidence,
            'candidate49-gate-controls', data['candidate_control_methods'])
        require(source_record(app, candidate_paths) == current, 'Candidate inputs changed during controls')
        receipt.update(status='PASS_BASELINE74_AND_CANDIDATE_CONTROLS_APPLE_NOT_RUN',
                       original_baseline_restored=True, candidate_inputs_unchanged=True)
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        (evidence / 'controls.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.app.resolve(), args.baseline.resolve(), args.evidence.resolve())
    print(json.dumps({key: result[key] for key in ['status', 'swift_methods_executed', 'native_ui_tests']}))
