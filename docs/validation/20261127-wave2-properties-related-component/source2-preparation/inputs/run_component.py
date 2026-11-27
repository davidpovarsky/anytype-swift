#!/usr/bin/env python3
"""One finite proposed run of the exact new Properties result model.

Tests are an explicitly derived import-prefixed new-suite suffix only.
This is not the full App/Kit target, SwiftUI, Native or the old five tests.
Never reuse an existing attempt. Owner review/admission is still required.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import traceback

import owned_process as owned_cleanup
from owned_process import now, group_members, observe_owned_group, finish_owned_process

ROOT = Path('/var/lib/pinkha-wave2-properties-related-lifetime-source2-20261127')
INPUTS = ROOT / 'inputs'
COMPONENT = ROOT / 'component'
PINS = {'Package.swift': 'b6aae03e2f5dab5d8e80b582f2def376c527ef115f51ed5fa2981fa794560548', 'Sources/TorahInspectorCore/Models.swift': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0', 'Sources/PinkhaAnyUI/AnyNativeSourceDocumentsPresentation.swift': '1cf8d0790e949b7592d4298dff0e788982ad3b0959c838350fe587d2c80e48c1', 'Tests/PinkhaAnyUITests/AnyNativeSourceDocumentsPublicationTests.swift': '15fa97a7e9467ab2657d4d87ea4cef8bd448819d75bf3a3a03182ac1f237fc4e'}
METHODS = ['queuedOldRequestCannotBorrowReopenedSheetAndCurrentFailureCanRetry', 'noncooperativeOldCompletionCannotReplaceReopenedRequest', 'retirementDiscardsRowsAndRejectsANoncooperativeCompletion', 'asyncWaiterJoinsReadAndForwardsCallerCancellation', 'temporarilyInactiveOwnerFinishesItsRequestAndCanRetry']
FLOOR = 2 * 1024**3
ALLOWANCE = 256 * 1024**2
CLEANUP_SHA = '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'
PROVENANCE_SHA = '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def cleanup_custody():
    helper = INPUTS / 'owned_process.py'
    provenance_path = INPUTS / 'owned-process-provenance.json'
    assert helper.is_file() and not helper.is_symlink()
    assert provenance_path.is_file() and not provenance_path.is_symlink()
    assert Path(owned_cleanup.__file__).resolve(strict=True) == helper.resolve(strict=True)
    assert sha(helper.read_bytes()) == CLEANUP_SHA
    raw = provenance_path.read_bytes()
    assert sha(raw) == PROVENANCE_SHA
    provenance = json.loads(raw)
    assert provenance['originalRunnerSHA256'] == '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'
    assert provenance['outputSHA256'] == CLEANUP_SHA
    return provenance


def resource_sample():
    memory = {line.split(':', 1)[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemAvailable:', 'SwapFree:'))}
    return {'atUTC': now(), 'freeBytes': shutil.disk_usage(ROOT).free,
            'memAvailableBytes': memory['MemAvailable'],
            'swapFreeBytes': memory['SwapFree'], 'load': os.getloadavg()}


def source_inventory(folder):
    observed = set()
    for base in ('Sources', 'Tests'):
        root = folder / base
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                p = Path(directory) / name
                assert not p.is_symlink(), 'Component source cannot be an alias: ' + str(p)
            observed.update((Path(directory) / name).relative_to(folder).as_posix() for name in files)
    assert observed == set(PINS) - {'Package.swift'}, 'Unexpected component compile input'
    result = {}
    for relative, expected in PINS.items():
        p = folder / relative
        assert p.is_file() and not p.is_symlink(), str(p)
        raw = p.read_bytes()
        assert sha(raw) == expected, relative
        result[relative] = {'sha256': expected, 'bytes': len(raw)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--coordination-story', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'attempt[1-9][0-9]*', args.attempt)
    assert re.fullmatch(r'[0-9]{16}', args.coordination_story)
    evidence = ROOT / args.attempt
    evidence.mkdir(exist_ok=False)
    started = time.monotonic()
    receipt = {'schema': 'pinkha.wave2.properties.actual-source-model-component.v1',
               'status': 'FAIL', 'startedAtUTC': now(),
               'runnerSHA256': sha(Path(__file__).read_bytes()),
               'coordinationStory': args.coordination_story,
               'methods': 5, 'declaredCases': 11, 'selectedSuite': 'AnyNativeSourceDocumentsPublicationTests',
               'originalKitBase': '9058b489e9acc271b4f8ef69e2ed24648f93b4ed',
               'minimalPackageIsDerived': True, 'productionModelBytesAreExact': True,
               'newTestSuiteSuffixBytesAreExact': True, 'testProjection': 'IMPORTS_PLUS_EXACT_NEW_SUITE_SUFFIX',
               'fullOriginalTestFileCompiled': False, 'oldIdentityMethodsSelected': 0,
               'productionModelSourceCommit': '21d63bef8950f8b927f0d8d3b4b052758bc98fcb',
               'testSourceBaseCommit': '21d63bef8950f8b927f0d8d3b4b052758bc98fcb',
               'testSourceStatus': 'UNPUBLISHED_TEST_ONLY_SUCCESSOR',
               'publishedTestSourceCommit': None,
               'fullSourceTestSHA256': '629b751244d0b87020ffa3a21e27c2123274b2c26e39aed3aae3bbdade36f2aa',
               'sourceTestSuffixSHA256': 'a9a92d220b39e3987fc8877f1cbf26ffcec67fce77c8d24a4b4fe99f35c5e851',
               'providerIsControlledNonCooperativeFixture': True,
               'baselineReplay': 'NONE_NEW_MODEL_SUITE', 'fullKitCompilation': 'NOT_RUN', 'fullAppTargetCompilation': 'NOT_RUN',
               'AppleCompilation': 'NOT_RUN', 'UIAcceptance': 'NOT_RUN',
               'nativeAcceptance': 'NOT_RUN', 'nativeServiceCalls': 0,
               'shippingSourceMutationsByRunner': 0, 'priorAcceptedTestsRerun': 0}
    process = None
    state = {}
    samples = []
    try:
        provenance = cleanup_custody()
        receipt['cleanupSourceProvenance'] = provenance
        admission = resource_sample()
        receipt['resourceAdmission'] = {**admission, 'incrementalAllowanceBytes': ALLOWANCE,
            'liveDiskFloorBytes': FLOOR, 'minimumAvailableMemoryBytes': 1536 * 1024**2,
            'jobs': 1, 'allowanceIsEstimate': True}
        assert admission['freeBytes'] >= FLOOR + ALLOWANCE, 'Coordinated disk floor plus allocation estimate do not fit'
        assert admission['memAvailableBytes'] >= 1536 * 1024**2, 'Available memory below one-job admission'
        before = source_inventory(INPUTS)
        write(evidence / 'source-inputs-before.json', before)
        COMPONENT.mkdir(exist_ok=False)
        for relative in PINS:
            destination = COMPONENT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(INPUTS / relative, destination)
        assert source_inventory(COMPONENT) == before
        toolchain = subprocess.run(['/usr/local/bin/swift', '--version'], capture_output=True, timeout=10, check=True)
        (evidence / 'toolchain.original.log').write_bytes(toolchain.stdout + toolchain.stderr)
        argv = ['/usr/local/bin/swift', 'test', '--package-path', str(COMPONENT),
                '--scratch-path', str(ROOT / 'build'), '--cache-path', str(ROOT / 'cache'),
                '--jobs', '1', '--no-parallel', '--disable-experimental-prebuilts', '-v',
                '--filter', 'AnyNativeSourceDocumentsPublicationTests']
        environment = dict(os.environ)
        environment['CLANG_MODULE_CACHE_PATH'] = str(ROOT / 'clang-module-cache')
        environment['SWIFTPM_MODULECACHE_OVERRIDE'] = str(ROOT / 'swiftpm-module-cache')
        environment['GIT_TERMINAL_PROMPT'] = '0'
        receipt['argv'] = argv
        write(evidence / 'invocation.json', {'argv': argv, 'timeoutSeconds': 300,
              'startedAtUTC': now(), 'coordinationStory': args.coordination_story})
        with (evidence / 'stdout.original.log').open('wb') as stdout, (evidence / 'stderr.original.log').open('wb') as stderr:
            process = subprocess.Popen(argv, cwd=COMPONENT, env=environment, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            write(evidence / 'process.json', {'pid': process.pid, 'processGroup': process.pid, 'startedAtUTC': now()})
            deadline = time.monotonic() + 300
            while process.poll() is None:
                sample = resource_sample()
                samples.append(sample)
                if sample['freeBytes'] < FLOOR or sample['memAvailableBytes'] < 512 * 1024**2:
                    receipt['resourceStop'] = sample
                    raise RuntimeError('Owned component stopped at the coordinated live resource floor')
                if time.monotonic() >= deadline:
                    receipt['timedOut'] = True
                    raise TimeoutError('Owned component exceeded300 seconds')
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            samples.append(resource_sample())
        receipt['processExit'] = process.returncode
        receipt['remainingOwnedProcessGroup'] = group_members(process.pid)
        receipt['memberListIsDiagnosticOnly'] = True
        receipt['ownedGroupAtExit'] = observe_owned_group(process, state)
        assert receipt['ownedGroupAtExit']['status'] == 'ABSENT_ESRCH', 'Owned group absence is not proven'
        after = source_inventory(INPUTS)
        assert after == before and source_inventory(COMPONENT) == before
        assert cleanup_custody() == provenance
        write(evidence / 'source-inputs-after.json', after)
        text = (evidence / 'stdout.original.log').read_text(errors='replace') + '\n' + (evidence / 'stderr.original.log').read_text(errors='replace')
        receipt['observedTestOutcomeLines'] = [line for line in text.splitlines()
            if (' Test ' in line and (' passed after ' in line or ' failed after ' in line)) or 'Test run with ' in line]
        assert process.returncode == 0, 'Actual compiler/test command failed'
        assert re.search(r'Test run with 5 tests in .* passed', text), 'Require the five actual Swift Testing methods, not zero XCTest methods'
        for name in METHODS:
            assert re.search(re.escape(name) + r'\([^\n]*\) passed after ', text), name + ' did not report PASS'
        assert not re.search(r' Test .* (skipped|failed)', text), 'Unexpected skipped or failed selected method'
        receipt['status'] = 'PASS_FIVE_METHODS_ELEVEN_DECLARED_CASES_EXACT_SOURCE_MODEL_COMPONENT_ONLY'
    except BaseException:
        receipt['status'] = 'FAIL'
        receipt['failure'] = traceback.format_exc()
    finally:
        if process is not None:
            finish_owned_process(process, state, receipt)
        receipt['finishedAtUTC'] = now()
        receipt['elapsedSeconds'] = round(time.monotonic() - started, 3)
        receipt_sha = None
        try:
            write(evidence / 'resource-samples.json', samples)
            receipt['freeBytesAfter'] = shutil.disk_usage(ROOT).free
            receipt['artifacts'] = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                for p in sorted(evidence.iterdir()) if p.is_file() and p.name != 'receipt.json']
        except BaseException:
            receipt['status'] = 'FAIL'
            receipt['evidenceFinalizationFailure'] = traceback.format_exc()
        try:
            write(evidence / 'receipt.json', receipt)
            receipt_sha = sha((evidence / 'receipt.json').read_bytes())
        except BaseException:
            receipt['status'] = 'FAIL'
            receipt['receiptWriteFailure'] = traceback.format_exc()
        print(json.dumps({'status': receipt['status'], 'receipt': str(evidence / 'receipt.json'),
              'receiptSHA256': receipt_sha, 'processExit': receipt.get('processExit'),
              'elapsedSeconds': receipt['elapsedSeconds'], 'failure': receipt.get('failure'),
              'ownedCleanup': receipt.get('ownedCleanup'),
              'evidenceFinalizationFailure': receipt.get('evidenceFinalizationFailure'),
              'receiptWriteFailure': receipt.get('receiptWriteFailure')}), flush=True)
    raise SystemExit(1 if receipt['status'] == 'FAIL' else 0)


if __name__ == '__main__':
    main()
