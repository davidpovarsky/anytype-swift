#!/usr/bin/env python3
"""Bounded final-v7 regression of the added native guards and HTTP routes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from run_native_validation import source_manifest

NATIVE_SHA = '12c7fb62164c830410331aabf616194edb0711a083250f8e8dd34c3cba52078b'
MANIFEST_SHA = '62a13310a474d93d728258d0631618b09056a20c4454bd7be303f3ec071fb77c'
SDK_BASE = '854df54cdadd76006ae823cbd1b1d923138356d0'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def tests_in(root, files, prefix='Test'):
    result = {}
    for path in sorted(files):
        names = re.findall(r'^func (' + prefix + r'\w*)\(', path.read_text(encoding='utf-8'), re.M)
        if names:
            package = './' + path.parent.relative_to(root).as_posix()
            result.setdefault(package, []).extend(names)
    return result


def suite(name, root, selected, logs, env):
    names = sorted({test for tests in selected.values() for test in tests})
    if not names:
        raise RuntimeError('empty_selected_suite')
    module = re.search(r'^module\s+(\S+)', (root / 'go.mod').read_text(encoding='utf-8'), re.M).group(1)
    expected = {(module + package[1:], test) for package, tests in selected.items() for test in tests}
    command = ['go', 'test', '-json', '-count=1', '-p', '2', '-timeout', '240s',
               '-run', '^(' + '|'.join(names) + ')$', *sorted(selected)]
    path = logs / (name + '.jsonl')
    with path.open('wb') as output:
        completed = subprocess.run(command, cwd=root, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, timeout=650)
    passed, failed, skipped, ran = set(), set(), set(), set()
    invalid_lines = 0
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines += 1
            continue
        test = event.get('Test')
        if not test:
            continue
        identity = (event.get('Package'), test)
        if event.get('Action') == 'run':
            ran.add(identity)
        elif event.get('Action') == 'pass':
            passed.add(identity)
        elif event.get('Action') == 'fail':
            failed.add(identity)
        elif event.get('Action') == 'skip':
            skipped.add(identity)
    missing = expected - passed
    result = {
        'name': name, 'status': 'PASS' if completed.returncode == 0 and not missing and not failed and not skipped else 'FAIL',
        'command': command, 'exitCode': completed.returncode,
        'expectedTopLevelTests': len(expected), 'passedTopLevelTests': len(expected & passed),
        'passedIncludingSubtests': len(passed), 'skippedIncludingSubtests': len(skipped),
        'failedIncludingSubtests': len(failed),
        'selectedTests': [{'package': package, 'tests': sorted(tests)} for package, tests in sorted(selected.items())],
        'missingPasses': [list(value) for value in sorted(missing)],
        'failedTests': [list(value) for value in sorted(failed)],
        'skippedTests': [list(value) for value in sorted(skipped)],
        'rawLog': str(path), 'rawLogSHA256': digest(path), 'nonJSONDiagnosticLines': invalid_lines,
    }
    print(json.dumps({key: result[key] for key in ('name', 'status', 'passedTopLevelTests',
        'expectedTopLevelTests', 'passedIncludingSubtests', 'skippedIncludingSubtests', 'failedIncludingSubtests')}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('runtime-source', 'sdk-source', 'binary', 'native-manifest', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    runtime, sdk = args.runtime_source.resolve(), args.sdk_source.resolve()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError('refuse_to_overwrite_historical_regression')
    result = {'status': 'FAIL', 'scope': 'Final native v7 source: added SDK final-authority/row-CAS/definition/guard tests and native claims/HTTP routes; no Apple UI claim.',
              'startedAtUTC': datetime.now(timezone.utc).isoformat(), 'suites': []}
    try:
        if digest(args.binary) != NATIVE_SHA or digest(args.native_manifest) != MANIFEST_SHA:
            raise RuntimeError('v7_binary_or_manifest_identity_mismatch')
        before = {'any': source_manifest(runtime), 'sdk': source_manifest(sdk)}
        result.update(binarySHA256=NATIVE_SHA, nativeManifestSHA256=MANIFEST_SHA,
                      sourceBefore=before, harnessSHA256=digest(__file__))
        changed = subprocess.check_output(['git', 'diff', '--name-only', SDK_BASE, 'HEAD'],
                                          cwd=sdk, text=True).splitlines()
        sdk_tests = tests_in(sdk, [sdk / path for path in changed if path.endswith('_test.go')])
        claims_tests = tests_in(runtime, list((runtime / 'internal/pinkha').rglob('*_test.go')))
        server_tests = tests_in(runtime, list((runtime / 'internal/server').glob('*_test.go')), 'TestPinkha')
        if (sum(map(len, sdk_tests.values())), sum(map(len, claims_tests.values())),
                sum(map(len, server_tests.values()))) != (27, 12, 25):
            raise RuntimeError('expected_final_v7_test_selection_changed')
        logs = runtime / '.runtime-artifacts/native-v7-final-regression'
        logs.mkdir(exist_ok=False)
        temp = runtime / '.runtime-artifacts/go-temp-v7-regression'
        temp.mkdir(exist_ok=True)
        env = dict(os.environ)
        env['GOTMPDIR'] = str(temp)
        for name, root, selected in [('sdk_native_guards', sdk, sdk_tests),
                                     ('native_claim_contracts', runtime, claims_tests),
                                     ('native_http_routes', runtime, server_tests)]:
            result['suites'].append(suite(name, root, selected, logs, env))
            write(output, result)
        after = {'any': source_manifest(runtime), 'sdk': source_manifest(sdk)}
        result['sourceAfter'] = after
        result['sourceStable'] = before == after
        result['binaryStable'] = digest(args.binary) == NATIVE_SHA
        result['passedTopLevelTests'] = sum(value['passedTopLevelTests'] for value in result['suites'])
        result['passedIncludingSubtests'] = sum(value['passedIncludingSubtests'] for value in result['suites'])
        result['skippedIncludingSubtests'] = sum(value['skippedIncludingSubtests'] for value in result['suites'])
        if all(value['status'] == 'PASS' for value in result['suites']) and result['sourceStable'] and result['binaryStable']:
            result['status'] = 'PASS_FINAL_NATIVE_V7_GO_REGRESSION'
    except Exception as error:
        result['fatalFailure'] = type(error).__name__ + ': ' + str(error)[:300]
    finally:
        result['finishedAtUTC'] = datetime.now(timezone.utc).isoformat()
        write(output, result)
    print(json.dumps({'status': result['status'], 'passedTopLevelTests': result.get('passedTopLevelTests'),
                      'passedIncludingSubtests': result.get('passedIncludingSubtests'),
                      'skippedIncludingSubtests': result.get('skippedIncludingSubtests'),
                      'evidence': str(output), 'fatalFailure': result.get('fatalFailure')}), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
