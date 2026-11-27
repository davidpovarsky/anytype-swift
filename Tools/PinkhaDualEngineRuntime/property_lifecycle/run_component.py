#!/usr/bin/env python3
"""Run one finite Properties regression phase in the handed-off component cache."""
from pathlib import Path
import datetime
import errno
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path('/var/lib/pinkha-wave2-property-lifecycle-20261127')
SHARED = Path('/var/lib/pinkha-wave2-native-block-menu-20261127')
COMPONENT = SHARED / 'component'
INPUTS = ROOT / 'inputs'
HANDOFF = SHARED / 'attempt1/cache-handoff.json'
HANDOFF_SHA = '493a7d628bdce5642f54b3b3f99deedfe24b28f6d8e68267c18c7629f227367b'
ORIGINAL_RESULT_SHA = 'bbf101c3821fafca51f6d6e9a0bef009f1f415ff935ab4e2606ca0feb599e231'
MODEL_SHA = 'aa40239c5ba749b20974735337c0af11ba477c9aac870261f4ae5ae76f76c731'
TEST_SHA = '7df1a45aa85cd71bc7ec8353b98150609bc2d2fb07a2aa1ebf08f7fb40fdab61'
BASELINE_SHA = 'c5935470e1c515461ad11b764e0169297eeb645a3ba4a522d0a7111070437dfb'
PREPARE_SHA = 'ef7b3195584ee599737ec86cef5da49bff1946f2fc0bc0a4d491915f1a829cff'
ERROR_ENUM_SHA = '25d49c71f60b613cf3131b9e31d8c2a29b2743ff62d332873835e5a3341a42bb'
ERROR_PROVENANCE_SHA = 'e1257b04a74d8e68d3ff9e596e26b2d1b087764787ebf471bf304dcdb961e29e'
DEPENDENCY_SHA = '67c6696b3d3e760553acd6a9d493cb6190c8093e702fef1d8c2a8ae96a5f9f08'
DEPENDENCIES = ['PinkhaAnyEngine', 'PinkhaAnyHost', 'PinkhaAnyIntegration', 'PinkhaKit']
GENERATED_PATHS = {'Sources/PinkhaAnyUI/AnyNativePropertyPresentation.swift',
                   'Sources/PinkhaAnyUI/AnyUIErrorText.swift',
                   'Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift'}
NEW_METHODS = ['currentReadFailureDiscardsDisplayedValuesAndUndoUntilReviewed',
               'deactivationDiscardsDisplayedValuesAndUndoBeforeNewOwnerRead']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def group_members(pgid):
    rows = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            stat = (p / 'stat').read_text()
            fields = stat[stat.rindex(')') + 2:].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                rows.append(int(p.name))
        except (OSError, ValueError, IndexError):
            pass
    return sorted(rows)


def resource_sample():
    memory = {line.split(':', 1)[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemAvailable:', 'SwapFree:'))}
    return {'atUTC': now(), 'freeBytes': shutil.disk_usage(SHARED).free,
            'memAvailableBytes': memory['MemAvailable'],
            'swapFreeBytes': memory['SwapFree'], 'load': os.getloadavg()}


def observe_owned_group(process, state):
    """Observe only this new owned group; an absence latch is irreversible."""
    assert state.setdefault('processGroup', process.pid) == process.pid
    if state.get('absence') is not None:
        return state['absence']
    observation = {'atUTC': now(), 'processGroup': process.pid, 'signal': 0}
    try:
        os.killpg(process.pid, 0)
        observation['status'] = 'PRESENT'
    except OSError as error:
        observation.update(errno=error.errno, error=str(error))
        observation['status'] = 'ABSENT_ESRCH' if error.errno == errno.ESRCH else 'UNKNOWN_ERROR'
        if error.errno == errno.ESRCH:
            state['absence'] = observation
    state.setdefault('observations', []).append(observation)
    return observation


def drain_owned_process(process, state):
    """Resolve only this newly created session, including surviving children."""
    result = {'processGroup': process.pid, 'signals': [], 'errors': []}
    try:
        process.poll()  # Reap only this Popen child when it has already exited.
        if state.get('absence') is None:
            try:
                result['initialMembersDiagnosticOnly'] = group_members(process.pid)
            except Exception:
                result['memberDiagnosticFailure'] = traceback.format_exc()
        observation = observe_owned_group(process, state)
        result['terminationRequired'] = observation['status'] == 'PRESENT' or process.returncode is None
        for sig, allowance in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            if state.get('absence') is not None:
                break
            assert observation['status'] == 'PRESENT', 'Owned group observation is unknown; absence is not established'
            try:
                os.killpg(process.pid, sig)
                result['signals'].append(sig.name)
            except OSError as error:
                if error.errno != errno.ESRCH:
                    raise
                # An intervening exit retires this group ID immediately. Do not
                # probe it again to manufacture a signal-zero proof after reuse
                # could become possible. This race remains a failed strict proof.
                observation = {'atUTC': now(), 'processGroup': process.pid,
                    'signal': int(sig), 'errno': error.errno, 'status': 'ABSENT_DURING_SIGNAL_WITHOUT_ZERO_PROOF'}
                state['absence'] = observation
                state.setdefault('observations', []).append(observation)
                break
            end = time.monotonic() + allowance
            while time.monotonic() < end:
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
                observation = observe_owned_group(process, state)
                if state.get('absence') is not None:
                    break
                assert observation['status'] == 'PRESENT', 'Owned group observation is unknown; absence is not established'
                if process.poll() is not None:
                    time.sleep(0.1)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            result['errors'].append('Owned Popen child did not reap within the final one-second bound')
        result['processExit'] = process.poll()
        absence = state.get('absence')
        result['status'] = ('PASS_OWNED_GROUP_ABSENT'
            if absence is not None and absence['status'] == 'ABSENT_ESRCH'
            and absence['signal'] == 0 and process.returncode is not None
            else 'FAIL_OWNED_GROUP_ABSENCE_NOT_PROVEN')
    except BaseException:
        result['errors'].append(traceback.format_exc())
        result['status'] = 'FAIL_OWNED_GROUP_CLEANUP'
    result['absenceEvidence'] = state.get('absence')
    result['groupObservations'] = list(state.get('observations', []))
    result['historicalGroupReprobed'] = False
    return result


def finish_owned_process(process, state, receipt):
    """Preserve the original failure while resolving this owned process once."""
    if state.get('absence') is not None and state['absence']['status'] == 'ABSENT_ESRCH' and process.poll() is not None:
        receipt['ownedCleanup'] = {'status': 'PASS_OWNED_GROUP_ABSENT',
            'processGroup': process.pid, 'absenceEvidence': state['absence'],
            'historicalGroupReprobed': False}
    else:
        receipt['ownedCleanup'] = drain_owned_process(process, state)
        if receipt['ownedCleanup']['status'] != 'PASS_OWNED_GROUP_ABSENT' or receipt['ownedCleanup'].get('terminationRequired'):
            receipt['status'] = 'FAIL'
    receipt['processExit'] = process.poll()


def physical_files(root):
    """Full package input set; only root build/VCS metadata is excluded."""
    found = set()
    for directory, directories, files in os.walk(root, followlinks=False):
        current = Path(directory)
        if current == root:
            directories[:] = [name for name in directories if name not in {'.git', '.build', '.swiftpm'}]
            files = [name for name in files if name not in {'.git', '.build', '.swiftpm'}]
        for name in list(directories):
            path = current / name
            if path.is_symlink():
                found.add(path.relative_to(root).as_posix())
                directories.remove(name)
        found.update((current / name).relative_to(root).as_posix() for name in files)
    return found


def checkout_custody(checkout):
    root = Path(checkout['path'])
    args = ['git', '--no-optional-locks', '-C', str(root)]
    head = subprocess.run(args + ['rev-parse', 'HEAD'], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    assert head == checkout['head'], str(root)
    tree = subprocess.run(args + ['ls-tree', '-rz', 'HEAD'], check=True, capture_output=True, timeout=10).stdout
    entries = {}
    for entry in filter(None, tree.split(b'\0')):
        header, raw_path = entry.split(b'\t', 1)
        mode, kind, expected = header.decode().split()
        relative = raw_path.decode()
        assert kind == 'blob' and mode in {'100644', '100755', '120000'}, relative
        path = root / relative
        if mode == '120000':
            assert path.is_symlink(), relative
            data = os.fsencode(os.readlink(path))
        else:
            assert path.is_file() and not path.is_symlink(), relative
            data = path.read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == expected, relative
        entries[relative] = {'sha256': sha(data), 'bytes': len(data), 'gitBlob': expected, 'mode': mode}
    assert entries and physical_files(root) == set(entries), 'Added, missing or aliased dependency inputs: ' + str(root)
    return {'path': str(root), 'head': head, 'files': len(entries),
            'physicalSourceClosureSHA256': sha(json.dumps(entries, sort_keys=True).encode())}


def pinned_inputs(handoff):
    for name, expected in [('AnyNativePropertyPresentation.swift', MODEL_SHA),
                           ('AnyNativePropertyPresentation.original.swift', BASELINE_SHA),
                           ('AnyNativePropertyPresentationTests.swift', TEST_SHA),
                           ('prepare_component_sources.py', PREPARE_SHA),
                           ('AnyUIErrorText.exact.swift', ERROR_ENUM_SHA),
                           ('error-text-source.json', ERROR_PROVENANCE_SHA)]:
        assert sha((INPUTS / name).read_bytes()) == expected, name
    original = SHARED / 'attempt1/receipt.json'
    assert sha(original.read_bytes()) == ORIGINAL_RESULT_SHA
    original_receipt = json.loads(original.read_bytes())
    for row in handoff['originalComponentSourceCopies']:
        assert sha((COMPONENT / row['path']).read_bytes()) == row['sha256'], row['path']
        assert sha((SHARED / 'attempt1/compiled-source' / row['path']).read_bytes()) == row['sha256'], row['path']
    original_deps = SHARED / 'attempt1/dependency-sources-after.json'
    dependency_bytes = original_deps.read_bytes()
    witness = [row for row in original_receipt['artifacts'] if row['path'] == str(original_deps)]
    assert len(witness) == 1 and witness[0]['sha256'] == sha(dependency_bytes) == DEPENDENCY_SHA
    assert witness[0]['bytes'] == len(dependency_bytes) == 78696
    closure = json.loads(dependency_bytes)
    assert closure['baseCommit'] == '8f2c11713fb8a40ae13444104723666ffef68afe'
    assert closure['dependencies'] == DEPENDENCIES and len(closure['files']) == 370
    dependency_root = Path(handoff['sourceDependencyRoot']).parent
    expected_paths = {row['path'] for row in closure['files']}
    assert len(expected_paths) == len(closure['files'])
    physical = {('Modules/' + name + '/' + relative) for name in DEPENDENCIES
                for relative in physical_files(dependency_root / 'Modules' / name)}
    assert physical == expected_paths, 'Added or missing local package input'
    for row in closure['files']:
        path = dependency_root / row['path']
        assert path.is_file() and not path.is_symlink(), row['path']
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    checkouts = [checkout_custody(checkout) for checkout in handoff['completeDependencies']]
    original_sources = {row['path'] for row in handoff['originalComponentSourceCopies']
                        if row['path'].startswith(('Sources/', 'Tests/'))}
    component_sources = {folder + '/' + relative for folder in ['Sources', 'Tests']
                         for relative in physical_files(COMPONENT / folder)}
    assert original_sources <= component_sources <= original_sources | GENERATED_PATHS, 'Unexpected component compile input'
    return {'dependencyClosureSHA256': sha(original_deps.read_bytes()),
            'dependencySourceFiles': len(closure['files']),
            'componentResolvedSHA256': sha((COMPONENT / 'Package.resolved').read_bytes()),
            'originalAddBlockReceiptSHA256': ORIGINAL_RESULT_SHA,
            'originalAddBlockSourceAndResultsRetained': True,
            'exactDependencyPhysicalSetsVerified': True, 'checkoutClosures': checkouts,
            'unchangedErrorEnumSHA256': ERROR_ENUM_SHA, 'errorEnumProvenanceSHA256': ERROR_PROVENANCE_SHA}


def main():
    variant, attempt = sys.argv[1:]
    assert variant in ('baseline', 'fixed')
    assert re.fullmatch(r'[a-z]+[0-9]+', attempt)
    evidence = ROOT / attempt
    assert not evidence.exists(), 'Never replace an original phase'
    evidence.mkdir()
    started = time.monotonic()
    receipt = {'schema': 'pinkha.wave2.properties.actual-model-component.v1',
               'variant': variant, 'startedAtUTC': now(), 'status': 'FAIL',
               'runnerSHA256': sha(Path(__file__).read_bytes()),
               'AppleCompilation': 'NOT_RUN', 'UIAcceptance': 'NOT_RUN',
               'nativeAcceptance': 'NOT_RUN', 'nativeServiceCalls': 0,
               'shippingSourceMutationsByRunner': 0, 'originalAddBlockMethodsRerun': 0}
    process = None
    group_state = {}
    samples = []
    try:
        assert sha(HANDOFF.read_bytes()) == HANDOFF_SHA
        handoff = json.loads(HANDOFF.read_bytes())
        assert handoff['nextOwner'] == 'wave2-root-properties' and handoff['noOwnedProcessGroupRemains']
        receipt['originalAddBlockProcessCustody'] = {
            'handoffSHA256': HANDOFF_SHA, 'originalReceiptSHA256': ORIGINAL_RESULT_SHA,
            'absenceReportedByOriginalOwner': handoff['noOwnedProcessGroupRemains'],
            'scope': 'Retained exact owner handoff; no current historical-PGID observation',
            'historicalGroupReprobed': False}
        # Only three small sources and their test binary are added to an already
        # compiled exact dependency cache. No full dependency rebuild is planned.
        admission = resource_sample()
        # This is a conservative incremental estimate, not a measured peak.
        # Keep the coordinated host's 2 GiB live disk floor and use one job.
        receipt['resourceAdmission'] = {**admission, 'incrementalAllowanceBytes': 256 * 1024**2,
            'liveDiskFloorBytes': 2 * 1024**3, 'minimumAvailableMemoryBytes': 1536 * 1024**2,
            'jobs': 1, 'allowanceIsEstimate': True}
        assert admission['freeBytes'] >= 2 * 1024**3 + 256 * 1024**2, 'Incremental allowance and coordinated live disk floor do not fit'
        assert admission['memAvailableBytes'] >= 1536 * 1024**2, 'Available memory below one-job component admission'
        before = pinned_inputs(handoff)
        write(evidence / 'dependency-and-custody-before.json', before)
        prepare = ['/usr/bin/python3', str(INPUTS / 'prepare_component_sources.py'),
                   '--inputs', str(INPUTS), '--output', str(COMPONENT), '--variant', variant]
        result = subprocess.run(prepare, check=True, capture_output=True, text=True, timeout=15)
        (evidence / 'prepare.original.log').write_text(result.stdout + result.stderr)
        envelope_path = COMPONENT / (variant + '-component-envelope.json')
        envelope = json.loads(envelope_path.read_bytes())
        shutil.copyfile(envelope_path, evidence / 'component-envelope.json')
        for relative, row in envelope['outputs'].items():
            raw = (COMPONENT / relative).read_bytes()
            assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
            target = evidence / 'compiled-source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        test_filter = '(' + '|'.join(NEW_METHODS) + ')' if variant == 'baseline' else 'AnyNativePropertyPresentationTests'
        argv = ['/usr/local/bin/swift', 'test', '--package-path', str(COMPONENT),
                '--scratch-path', handoff['scratchPath'], '--cache-path', handoff['cachePath'],
                '--jobs', '1', '--no-parallel', '--disable-experimental-prebuilts', '-v', '--filter', test_filter]
        environment = dict(os.environ)
        environment['CLANG_MODULE_CACHE_PATH'] = handoff['clangModuleCachePath']
        environment['GIT_TERMINAL_PROMPT'] = '0'
        write(evidence / 'invocation.json', {'argv': argv, 'timeoutSeconds': 300,
              'componentEnvelopeSHA256': sha(envelope_path.read_bytes()), 'startedAtUTC': now()})
        receipt['argv'] = argv
        with (evidence / 'stdout.original.log').open('wb') as stdout, (evidence / 'stderr.original.log').open('wb') as stderr:
            process = subprocess.Popen(argv, cwd=COMPONENT, env=environment, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            write(evidence / 'process.json', {'pid': process.pid, 'processGroup': process.pid, 'startedAtUTC': now()})
            deadline = time.monotonic() + 300
            while process.poll() is None:
                sample = resource_sample()
                samples.append(sample)
                if sample['freeBytes'] < 2 * 1024**3 or sample['memAvailableBytes'] < 512 * 1024**2:
                    receipt['resourceStop'] = sample
                    raise RuntimeError('Owned component stopped at the coordinated resource floor')
                if time.monotonic() >= deadline:
                    receipt['timedOut'] = True
                    raise TimeoutError('Owned component exceeded its 300 second deadline')
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            code = process.returncode
            samples.append(resource_sample())
        receipt['processExit'] = code
        receipt['remainingOwnedProcessGroup'] = group_members(process.pid)
        receipt['memberListIsDiagnosticOnly'] = True
        receipt['ownedGroupAtExit'] = observe_owned_group(process, group_state)
        assert receipt['ownedGroupAtExit']['status'] == 'ABSENT_ESRCH', 'Owned compiler group absence is not established by signal-zero ESRCH'
        after = pinned_inputs(handoff)
        write(evidence / 'dependency-and-custody-after.json', after)
        assert after == before
        for relative, row in envelope['outputs'].items():
            assert sha((COMPONENT / relative).read_bytes()) == row['sha256']
        text = (evidence / 'stdout.original.log').read_text(errors='replace') + '\n' + (evidence / 'stderr.original.log').read_text(errors='replace')
        receipt['observedTestOutcomeLines'] = [line for line in text.splitlines()
            if (' Test ' in line and (' passed after ' in line or ' failed after ' in line)) or 'Test run with ' in line]
        assert not receipt.get('timedOut')
        assert not receipt.get('resourceStop')
        if variant == 'baseline':
            assert code != 0 and re.search(r'Test run with 2 tests in .* failed', text), 'Require actual two-method completion, not a build failure or zero-test run'
            assert all(name + '() failed after ' in text for name in NEW_METHODS)
            receipt['status'] = 'OBSERVED_TWO_METHOD_FAILURES_PENDING_REGRESSION_ISSUE_REVIEW'
            receipt['regressionReproduced'] = False
            receipt['requiredReview'] = 'Read actual intended expectation issues; setup throws and rendezvous timeouts are not regression proof'
        else:
            assert code == 0 and re.search(r'Test run with 9 tests in .* passed', text), 'All nine Properties methods must actually pass'
            assert all(name + '() passed after ' in text for name in NEW_METHODS)
            receipt['status'] = 'PASS_NINE_PROPERTIES_METHODS_COMPONENT_ONLY'
    except BaseException:
        receipt['status'] = 'FAIL'
        receipt['failure'] = traceback.format_exc()
    finally:
        # This runs after every post-Popen failure, including receipt/resource
        # exceptions. A positive original absence observation is not reprobed.
        if process is not None:
            finish_owned_process(process, group_state, receipt)
        receipt['finishedAtUTC'] = now()
        receipt['elapsedSeconds'] = round(time.monotonic() - started, 3)
        receipt_sha = None
        try:
            write(evidence / 'resource-samples.json', samples)
            receipt['freeBytesAfter'] = shutil.disk_usage(SHARED).free
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
              'receiptSHA256': receipt_sha,
              'processExit': receipt.get('processExit'), 'elapsedSeconds': receipt['elapsedSeconds'],
              'failure': receipt.get('failure', ''), 'ownedCleanup': receipt.get('ownedCleanup'),
              'evidenceFinalizationFailure': receipt.get('evidenceFinalizationFailure'),
              'receiptWriteFailure': receipt.get('receiptWriteFailure')}), flush=True)
    raise SystemExit(1 if receipt['status'] == 'FAIL' else 0)


if __name__ == '__main__':
    main()
