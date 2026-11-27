#!/usr/bin/env python3
"""One new conditional Bookmark, validated crash, and a fresh offline reopen.

This consumer never compiles, replays the 13 component methods, opens a retained
account, or treats its new synthetic definition as an imported original Type.
Its only inputs are the explicitly qualified new product and public controls.
"""
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import sys
import time
import types
import urllib.parse

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
PARENT = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127')
PREPARED = PARENT/'prepared1'
QUALIFIER_SHA = 'a45b10800f1ea89530e38b1c6a5b7e34ee3e2ded5bc9d326ccc98762186ed712'
COMPLETION_CONTROLLER = Path('/var/lib/sentinelx/uploads/pinkha-c-bookmark-create-completion-20261127-193953b8.py')
COMPLETION_CONTROLLER_SHA = '193953b82d9f630006682187f9ece9169dfabd0a46d58f517e015c69139eb60c'
COMPLETION_RECEIPT_SHA = 'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d'
RETAINED_PRODUCER = PARENT/'qualification-attempt1'
RETAINED_RECEIPT_SHA = '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b'
RETAINED_SOURCE_SHA = '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0'
RETAINED_SDK_LOG_SHA = 'f6b1fdbd7308d2c3875a3465821b8ccb5dea339917d33fe314548d5d21cbdbc1'
RETAINED_ENV_LOG_SHA = '865117f0fe0f842b406e0a216c4f9c249a7a2df9b66e478067066f5ef3485c1d'
EMPTY_SHA = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
SOURCE_SHA = 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3'
DRAFT_SHA = 'ebd4b3c7379a9d8851118d42ba25a43e08bc6939d7e1328cc8b83c67693dbe4c'
INSTALL_SHA = '2f8eb0f7a73ddfc5ea57df10c79521d88215e964822f6afa65ee98ed91861400'
SUPPORT_SHA = 'db3a44aded9c819115cc531ecf8f3682b7d8e43c25af8f64d9cbb51d13dfebfd'
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_PROOF = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json')
OFFLINE_PROOF_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
PRIOR_CONSUMER = PARENT/'bodyless-native-attempt1/result.json'
PRIOR_CONSUMER_SHA = '6995033934f702d28af0611dab8535d6dc51d3069a32f43626182e73422ba9f3'
PRIOR_CONSUMER_SOURCE = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-bodyless-completion-source-20261127-attempt1/run_bodyless_bookmark.py')
PRIOR_CONSUMER_SOURCE_SHA = '99b132dd1ab0436cdb3b6639831e161d7e07c5eb962c71a0021b63140a01ed4e'
LIBRARY = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
LIBRARY_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
NODECONF = 'internal/pinkha/migrationnative/testdata/local.yml'
NODECONF_SHA = 'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'
MIB, GIB = 1024**2, 1024**3
ROOT_FLOOR, DEV_FLOOR = 2*GIB, 512*MIB
OWNED_CAP, ACCOUNT_CAP, LOG_CAP = 128*MIB, 96*MIB, 8*MIB
MAIN_SECONDS, FINAL_SECONDS, PHASE_SECONDS = 500, 60, 180
TITLE = 'Fresh conditional bodyless Bookmark'
SOURCE_URL = 'https://example.test/cafe\u0301?source=bookmark-native-proof'
FRAME_KEYS = {'contract', 'version', 'accountId', 'spaceId', 'typeId', 'collections',
              'propertyOwnerId', 'propertyId', 'canWrite', 'frame'}
MUTATIONS = ('space', 'type', 'editor-part', 'property-owner', 'url-property', 'layout', 'bookmark')


def require(value, label):
    if not value:
        raise RuntimeError(label)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def physical(path, directory=False):
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'physical fixed input or owned output')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'ordinary input or output kind')
    return info


def frozen(path, maximum=8*MIB):
    before = physical(path)
    require(before.st_nlink == 1 and 0 <= before.st_size <= maximum, 'bounded independent regular input')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno()) == before, 'input descriptor matches path')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno()) == before, 'input stable during read')
    require(path.lstat() == before and len(raw) == before.st_size, 'complete stable input read')
    return raw


def closed_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate native JSON member')
            value[key] = item
        return value
    def invalid_constant(_value):
        raise RuntimeError('nonfinite JSON constant')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    require(isinstance(value, dict), 'native JSON object response')
    return value


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive(path, raw):
    physical(path.parent, True)
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    sync_dir(path.parent)
    require(frozen(path, max(1, len(raw))) == raw, 'exact durable new evidence')


def allocation(root):
    physical(root, True)
    total, count, seen, pending = 0, 0, set(), [root]
    began = time.monotonic()
    while pending:
        directory = pending.pop()
        try:
            fd = os.open(directory, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
        except FileNotFoundError:
            continue
        try:
            with os.scandir(fd) as entries:
                names = [entry.name for entry in entries]
        finally:
            os.close(fd)
        for name in [None]+names:
            path = directory if name is None else directory/name
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'no special or aliased owned account/evidence output')
            key = (info.st_dev, info.st_ino)
            if key not in seen:
                seen.add(key)
                total += max(info.st_size, info.st_blocks*512) if stat.S_ISREG(info.st_mode) else info.st_blocks*512
            if name is not None and stat.S_ISDIR(info.st_mode):
                pending.append(path)
            if name == 'original.log':
                require(info.st_size <= LOG_CAP, 'bounded original native log')
            count += 1
            require(count <= 20000 and time.monotonic()-began <= 5, 'bounded owned allocation census')
    return total


def segment(value):
    require(type(value) is str and 1 <= len(value.encode()) <= 1024 and
            all(0x21 <= ord(char) <= 0x7e for char in value), 'exact printable native ID')
    return urllib.parse.quote(value, safe='')


def main():
    require(not sys.flags.optimize and os.geteuid() == 0 and os.uname().nodename == 'torah-social', 'authorized host and enabled guards')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--qualification-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qualified_root, output = args.qualification, args.output
    require(qualified_root.parent == output.parent == PARENT and
            qualified_root.name == 'qualification-completion-attempt1' and
            re.fullmatch(r'bodyless-native-attempt[1-9][0-9]{0,2}', output.name) and
            args.qualification_sha256 == COMPLETION_RECEIPT_SHA, 'fixed qualified producer, explicit actual receipt pin and new consumer path')
    physical(PARENT, True); physical(qualified_root, True)
    require(not os.path.lexists(output), 'preserve every prior consumer attempt')
    os.umask(0o077)
    output.mkdir(mode=0o700); sync_dir(PARENT)
    began, final_deadline, serial = time.monotonic(), None, 0
    inputs, retained_responses, source_before = {}, {}, None
    producer_source = RETAINED_PRODUCER/'source'
    compiler = support = owner = None
    owner_admission = None
    account_dir = output/'private/fresh-account'
    result = {'status': 'RUNNING', 'protocol': 'pinkha-bodyless-bookmark-native-crash-v1',
        'commands': [], 'requests': [], 'mutations': [], 'phases': [], 'errors': [], 'completionErrors': [],
        'compilerInvocations': 0, 'priorTestMethodsReexecuted': 0, 'nativeProductBuilds': 0,
        'originalAccountInputs': 0, 'originalAccountCopies': 0, 'C313SourceOrProductsAccessed': False,
        'C3CacheAccessed': False, 'originalMigrationOperationsReplayed': 0,
        'originalBuiltinTypeMigrationQualified': False, 'originalPlaintextHistoryReconstructed': False,
        'sourceAdmissionPromoted': False, 'wholeMigrationComplete': False,
        'accountInitializations': 0, 'nativeBodylessCreates': 0, 'controllerMutationRetries': 0,
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
            'rootAdmissionReserveBytes': 128*MIB, 'developmentAdmissionReserveBytes': OWNED_CAP,
            'ownedOutputCapBytes': OWNED_CAP, 'ownedAccountCapBytes': ACCOUNT_CAP,
            'originalLogCapBytes': LOG_CAP, 'estimatedNewAllocationNotMeasuredPeak': True,
            'controllerSeconds': MAIN_SECONDS, 'nativePhaseSeconds': PHASE_SECONDS,
            'finalVerificationSeconds': FINAL_SECONDS, 'requiredOuterTimeoutSeconds': 630,
            'controlledOutputPathsOnDevelopmentOnly': True, 'globalRootWritesMeasured': False}}

    def save_json(path, value):
        nonlocal serial
        require(path.is_relative_to(output), 'only owned evidence path')
        raw = json_bytes(value)
        require(len(raw) <= 4*MIB, 'bounded evidence record')
        serial += 1
        staging = path.with_name(path.name+'.owned-next-'+str(serial))
        exclusive(staging, raw)
        os.replace(staging, path); sync_dir(path.parent)

    def save():
        result['seconds'] = round(time.monotonic()-began, 6)
        save_json(output/'result.json', result)

    def checkpoint(admission=False):
        require(time.monotonic() < (final_deadline if final_deadline is not None else began+MAIN_SECONDS), 'absolute consumer/final deadline')
        require(not (output/'abort').exists(), 'explicit owned abort')
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        require(free['root'] >= ROOT_FLOOR+(128*MIB if admission else 0) and
                free['development'] >= DEV_FLOOR+(OWNED_CAP if admission else 0), 'unchanged native admission and emergency floors')
        for key, value in free.items():
            result.setdefault('minimumFreeBytes', {})[key] = min(value, result.get('minimumFreeBytes', {}).get(key, value))
        return free

    def guard(admission=False):
        free = checkpoint(admission)
        used = allocation(output)
        require(used <= OWNED_CAP, 'bounded whole native output')
        result['peakOwnedOutputBytes'] = max(used, result.get('peakOwnedOutputBytes', 0))
        if account_dir.is_dir():
            require(allocation(account_dir) <= ACCOUNT_CAP, 'bounded new account allocation')
        checkpoint()
        return free

    def observe():
        try:
            guard(); return None
        except BaseException as error:
            return type(error).__name__+': '+str(error)

    def pin(path, digest=None, maximum=8*MIB):
        checkpoint()
        raw = frozen(path, maximum)
        row = identity(raw)
        require(digest is None or row['sha256'] == digest, 'pinned public input identity')
        existing = inputs.setdefault(str(path), {'identity': row, 'maximum': maximum})
        require(existing['identity'] == row, 'unchanged repeated input')
        return raw

    def command(label, argv, environment, seconds, observer=None, expected_exit=0):
        def persist(path, row):
            require(path.parent == output/'commands'/label and path.name in ('started.json', 'result.json'), 'owned command records')
            save_json(path, row); save()
        log, row = owner.run(output/'commands'/label, argv, output, environment, seconds,
            observer or observe, persist, lambda path: identity(frozen(path, LOG_CAP))['sha256'],
            result['commands'], expected_exit=expected_exit)
        save()
        return log, row

    def interrupted(number, _frame):
        raise RuntimeError('bodyless consumer interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        result['initialFreeBytes'] = guard(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available >= GIB, 'one native process memory admission')
        result['memAvailableBefore'] = available
        result['controller'] = identity(pin(Path(__file__).absolute()))
        previous_source = pin(PRIOR_CONSUMER_SOURCE, PRIOR_CONSUMER_SOURCE_SHA)
        previous = closed_json(pin(PRIOR_CONSUMER, PRIOR_CONSUMER_SHA))
        require(previous['status'] == 'FAIL_BODYLESS_BOOKMARK_PRESERVED' and
                previous['controller'] == identity(previous_source) and
                previous['commands'] == previous['requests'] == previous['mutations'] == previous['phases'] == [] and
                previous['errors'] == [{'type': 'KeyError', 'message': "'actual'"}] and
                previous['completionErrors'] == [] and previous['allStartedOwnedGroupsPositivelyAbsent'] is False and
                previous['accountInitializations'] == previous['nativeBodylessCreates'] == 0 and
                previous['compilerInvocations'] == previous['priorTestMethodsReexecuted'] == 0 and
                previous['finalIntegrity'] == {'compiledSource': True, 'originalResponses': True,
                    'ownedLifetimeInputs': True, 'publicInputsAndNativeProduct': True},
                'original receipt-schema failure preserved with zero commands, requests or effects')
        result['priorNoChildFailure'] = {'receiptPath': str(PRIOR_CONSUMER), 'receiptSHA256': PRIOR_CONSUMER_SHA,
            'controllerSHA256': PRIOR_CONSUMER_SOURCE_SHA, 'status': previous['status'],
            'errors': previous['errors'], 'startedCommands': 0, 'requests': 0, 'mutations': 0,
            'accountInitializations': 0, 'originalAggregateAbsenceFlag': False,
            'historicalProcessIDsProbedOrSignaled': False}
        actual_install = closed_json(pin(PARENT/'installation-attempt1/result.json', INSTALL_SHA))
        require(actual_install['status'] == 'PASS_EXACT_FORMATTED_BOOKMARK_SOURCE_INSTALLATION_ONLY' and
                actual_install['publicControlsUnchanged'] is True and actual_install['errors'] == actual_install['completionErrors'] == [] and
                len(actual_install['installedSources']) == 23, 'actual exact prepared-source installation')
        qualifier_raw = pin(PREPARED/'qualify_bookmark_native.py', QUALIFIER_SHA)
        compiler = types.ModuleType('qualified_bookmark_source_helpers')
        compiler.__file__ = str(PREPARED/'qualify_bookmark_native.py')
        exec(compile(qualifier_raw, compiler.__file__, 'exec'), compiler.__dict__)
        completion_raw = pin(COMPLETION_CONTROLLER, COMPLETION_CONTROLLER_SHA)
        actual_raw = pin(qualified_root/'result.json', args.qualification_sha256)
        actual = closed_json(actual_raw)
        require(actual['protocol'] == 'pinkha-native-bookmark-conditional-create-completion-v1' and
                actual['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
                actual['controller'] == identity(completion_raw) and actual['sourceDraftSHA256'] == DRAFT_SHA and
                actual['sourceManifestSHA256'] == SOURCE_SHA and actual['sourceFiles'] == 1625 and
                actual['compiledSourceInputSHA256'] == RETAINED_SOURCE_SHA and
                actual['sourceRoot'] == str(producer_source) and actual['newSourceMaterializations'] == 0 and
                actual['nativeProductBuilds'] == 1 and actual['priorTestMethodsReexecuted'] == 0 and
                actual['retainedActualMethodCount'] == 8 and actual['newActualMethodCount'] == 5 and
                actual['runtimeBodylessWarmColdStatus'] == 'NOT_RUN_SEPARATE_CONSUMER' and
                actual['allOwnedGroupsPositivelyAbsent'] is True and actual['errors'] == actual['completionErrors'] == [] and
                actual['finalIntegrity'] == {'declaredInputsAndProducts': True, 'originalSource': True, 'compiledSource': True},
                'exact actual completion producer with eight retained and five new methods')
        retained_raw = pin(RETAINED_PRODUCER/'result.json', RETAINED_RECEIPT_SHA)
        retained = closed_json(retained_raw)
        require(retained['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
                retained['controller'] == identity(qualifier_raw) and retained['sourceDraftSHA256'] == DRAFT_SHA and
                retained['sourceManifestSHA256'] == SOURCE_SHA and retained['compiledSourceInputSHA256'] == RETAINED_SOURCE_SHA and
                retained['sourceFiles'] == 1625 and retained['allOwnedGroupsPositivelyAbsent'] is True and
                retained['finalIntegrity'] == actual['finalIntegrity'] and
                retained['errors'] == [{'type': 'RuntimeError', 'message': 'RuntimeError: measured shared cache incremental cap'}] and
                retained['completionErrors'] == [{'boundary': 'acceptanceAndResources', 'type': 'RuntimeError',
                    'message': 'measured shared cache incremental cap'}], 'original resource failure remains exactly failed')
        require(all(retained[key] == 0 for key in ('nativeProductBuilds', 'priorTestMethodsReexecuted',
                'originalAccountInputs', 'nativeCLIAccountProcesses', 'C313SourceWrites', 'C3CacheWrites')) and
                all(actual[key] == 0 for key in ('priorTestMethodsReexecuted', 'originalAccountInputs',
                    'nativeCLIAccountProcesses', 'C313SourceWrites', 'C3CacheWrites')), 'both producer effect scopes unchanged')
        old_rows = retained['processes']
        require(len(old_rows) == 3, 'exact original two normal commands and one failed compile')
        for row in old_rows[:2]:
            require(row['exitCode'] == 0 and row['processGroupAbsent'] is True and row['forcedCleanup'] is False and
                    row['cleanupErrors'] == row['signals'] == [] and row['stopReason'] is None and
                    row['unreapedLeaderDuringGroupCleanup'] is True, 'retained normal producer group closure')
        stopped = old_rows[2]
        require(stopped['exitCode'] == -signal.SIGTERM and stopped['processGroupAbsent'] is True and
                stopped['forcedCleanup'] is True and stopped['signals'] == [signal.SIGTERM] and
                stopped['cleanupErrors'] == [] and stopped['logSHA256'] == EMPTY_SHA and
                stopped['stopReason'] == 'RuntimeError: measured shared cache incremental cap' and
                stopped['unreapedLeaderDuringGroupCleanup'] is True, 'interrupted old compile is not a qualified group')
        pin(RETAINED_PRODUCER/'server-five/original.log', EMPTY_SHA)
        chain = actual['retainedQualification']
        require(chain == {'receiptPath': str(RETAINED_PRODUCER/'result.json'), 'receiptSHA256': RETAINED_RECEIPT_SHA,
                'sourceRoot': str(producer_source), 'compiledSourceInputsSHA256': RETAINED_SOURCE_SHA,
                'qualifiedProcesses': old_rows[:2], 'failedCompileProcess': stopped,
                'originalFailureStatusUnchanged': True, 'historicalProcessIDsNeverProbedOrSignaled': True,
                'sdkLogSHA256': RETAINED_SDK_LOG_SHA, 'environmentLogSHA256': RETAINED_ENV_LOG_SHA},
                'exact retained receipt/source/process/log chain')
        labels = ['current-native-compiler-environment', 'server-five', 'native-build', 'native-metadata']
        require(len(actual['processes']) == 4, 'exact four new qualified producer groups')
        logs = {}
        for label, row in zip(labels, actual['processes']):
            require(row['exitCode'] == 0 and row['processGroupAbsent'] is True and row['forcedCleanup'] is False and
                    row['cleanupErrors'] == row['signals'] == [] and row.get('stopReason') is None and
                    row['unreapedLeaderDuringGroupCleanup'] is True, 'normal new producer group closure')
            logs[label] = pin(qualified_root/label/'original.log', row['logSHA256'], 16*MIB)
        logs['sdk-eight'] = pin(RETAINED_PRODUCER/'sdk-eight/original.log', RETAINED_SDK_LOG_SHA, 16*MIB)
        environment_log = pin(RETAINED_PRODUCER/'go-environment/original.log', RETAINED_ENV_LOG_SHA, 65536)
        require(old_rows[0]['logSHA256'] == RETAINED_ENV_LOG_SHA and old_rows[1]['logSHA256'] == RETAINED_SDK_LOG_SHA and
                closed_json(environment_log) == actual['goToolchain']['metadata'] and
                retained['goToolchain'] == actual['goToolchain'], 'original Go-driver/source metadata remains explicit')
        require(actual['retainedCompilerEvidenceScope'] == {
                'originalGoDriverCompilerLinkerSourceAndRecordedEnvironmentOnly': True,
                'historicalNativeCompilerExecutablesObserved': False, 'historicalPATHObserved': False,
                'retainedSDKMethodsReexecuted': 0}, 'no invented historical C compiler or PATH observation')
        observed = actual['currentNativeCompilerObservation']
        require(closed_json(logs['current-native-compiler-environment']) == observed['metadata'] and
                observed['appliesTo'] == ['five-new-server-methods', 'one-new-native-product'] and
                observed['historicalCompilerEqualityClaimed'] is False and set(observed['tools']) == {'CC', 'CXX', 'AR'} and
                observed['explicitEnvironment'] == {key: row['path'] for key, row in observed['tools'].items()},
                'new current C compiler observation applies only to new server/build')
        draft = closed_json(pin(PREPARED/'BOOKMARK_SOURCE_FORMATTED.json', DRAFT_SHA))
        expected = {'sdk-eight': set(), 'server-five': set()}
        for name, methods in draft['tests'].items():
            sdk = name.startswith(compiler.SDK_PREFIX)
            suffix = name.removeprefix(compiler.SDK_PREFIX) if sdk else name
            package = ('github.com/anyproto/any-sync-sdk/' if sdk else 'github.com/anyproto/any/')+str(Path(suffix).parent)
            expected['sdk-eight' if sdk else 'server-five'].update((package, method) for method in methods)
        for label, count in (('sdk-eight', 8), ('server-five', 5)):
            parsed = compiler.parse_test_events(logs[label], expected[label])
            require(parsed == actual[label] and parsed['runs'] == parsed['passes'] == count,
                    'independent exact eight-retained/five-new raw event parsing')
            if label == 'sdk-eight':
                require(parsed == retained[label], 'retained eight are actual original events')
        driver = actual['goToolchain']['driver']['path']
        base_test = [sys.executable, '-B', str(PREPARED/'linux_outbound_denial.py'), '--exec', driver,
            'test', '-json', '-p', '2', '-count=1', '-timeout=300s', '-run']
        sdk_pattern = '^('+'|'.join(sorted(name for _, name in expected['sdk-eight']))+')$'
        server_pattern = '^('+'|'.join(sorted(name for _, name in expected['server-five']))+')$'
        require(old_rows[0]['argv'] == [driver, 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH'] and
                old_rows[0]['cwd'] == str(producer_source) and old_rows[1]['cwd'] == str(producer_source/compiler.SDK_PREFIX) and
                old_rows[1]['argv'] == base_test+[sdk_pattern, './internal/bookmarkcreate', './internal/spaceobjects'] and
                stopped['cwd'] == str(producer_source) and stopped['argv'] == base_test+[server_pattern, './internal/server'],
                'original exact metadata/SDK and failed server commands')
        binary = qualified_root/'any'
        new_argv = [[driver, 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH',
                'GOOS', 'GOARCH', 'CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR'],
            base_test+[server_pattern, './internal/server'], [driver, 'build', '-p', '2', '-o', str(binary), './cmd/any'],
            [driver, 'version', '-m', str(binary)]]
        require(all(row['argv'] == argv and row['cwd'] == str(producer_source)
                    for row, argv in zip(actual['processes'], new_argv)), 'four new exact commands use original compiled source')
        compiled_raw = pin(qualified_root/'compiled-source-inputs.json', RETAINED_SOURCE_SHA)
        require(compiled_raw == pin(RETAINED_PRODUCER/'compiled-source-inputs.json', RETAINED_SOURCE_SHA),
                'same complete original compiled-source manifest bytes')
        source_before = closed_json(compiled_raw)
        declared = closed_json(pin(qualified_root/'source-manifest.json', SOURCE_SHA))['files']
        require(len(declared) == 1625 and source_before['files'] == dict(declared, **{'staging.yml': {'bytes': 1137, 'sha256': NODECONF_SHA}}) and
                set(source_before['modes']) == set(source_before['files']), 'complete1625 source plus explicit runtime config')
        require(compiler.source_inventory(producer_source, checkpoint) == source_before,
                'complete live original compiled source bytes and modes')
        native = actual['nativeBinary']
        require(native['path'] == str(binary), 'fixed actual new native product')
        pin(binary, native['sha256'], 128*MIB)
        require(binary.stat().st_size == native['bytes'] and stat.S_IMODE(binary.stat().st_mode) == native['mode'] and
                native['mode'] & 0o111, 'exact qualified executable shape')
        result['qualifiedProducer'] = {'path': str(qualified_root/'result.json'), **identity(actual_raw),
            'retainedMethods': 13, 'rerunMethods': 0, 'sourceManifestSHA256': SOURCE_SHA,
            'compiledSourceInputSHA256': RETAINED_SOURCE_SHA, 'nativeBinary': native,
            'producerMethodComposition': {'retainedSDK': 8, 'newServer': 5},
            'producerCommandComposition': {'retainedNormal': 2, 'newNormal': 4, 'originalFailedCompileRetained': 1},
            'originalFailedReceiptSHA256': RETAINED_RECEIPT_SHA, 'sourceRoot': str(producer_source),
            'historicalCCompilerObservationClaimed': False}
        support_raw = pin(HERE/'native_boundary_support.py', SUPPORT_SHA)
        support = types.ModuleType('bodyless_qualified_native_boundary')
        support.__file__ = str(HERE/'native_boundary_support.py')
        exec(compile(support_raw, support.__file__, 'exec'), support.__dict__)
        owner, owner_admission = support.qualify()
        result['lifetimeAndDeadlineAdmission'] = owner_admission
        offline = PREPARED/'linux_outbound_denial.py'
        pin(offline, OFFLINE_SHA); pin(LIBRARY, LIBRARY_SHA, 4*MIB)
        policy = closed_json(pin(OFFLINE_PROOF, OFFLINE_PROOF_SHA))
        require(policy['status'] == 'PASS' and policy['allOwnedGroupsPositivelyAbsent'] is True and
                policy['offlinePolicy']['helperSHA256'] == OFFLINE_SHA and
                policy['offlinePolicy']['controls']['librarySHA256'] == LIBRARY_SHA and
                policy['offlinePolicy']['baselineTCPReachable'] is True and
                policy['offlinePolicy']['baselineUDPReceived'] is True and
                all(policy['offlinePolicy']['controls'][key] is True for key in
                    ('tcpDenied', 'udpDenied', 'noNewPrivileges', 'seccompFilterActive')),
                'same actual prior OS-denial controls and positive baselines')
        result['offlinePolicy'] = {'helperSHA256': OFFLINE_SHA, 'librarySHA256': LIBRARY_SHA,
            'priorActualReceiptSHA256': OFFLINE_PROOF_SHA, 'priorActualControls': policy['offlinePolicy'], 'priorControlsReexecuted': 0}
        nodeconf = producer_source/NODECONF
        require(identity(pin(nodeconf, NODECONF_SHA, 65536)) == {'bytes': 1137, 'sha256': NODECONF_SHA}, 'original public local network configuration')
        for name in ('private', 'commands', 'temporary'):
            (output/name).mkdir(mode=0o700)
        config = output/'native.yml'
        exclusive(config, ('network:\n  nodeconfPath: '+str(nodeconf)+'\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n').encode())
        pin(config)
        python = str(Path(sys.executable).resolve())
        pin(Path(python), maximum=32*MIB)
        environment = {key: value for key, value in os.environ.items()
            if not key.startswith(('ANY_', 'PINKHA_', 'PYTHON', 'LD_', 'DYLD_', 'GO', 'CGO_'))}
        environment.update(ANY_DATA_DIR=str(account_dir), GOMAXPROCS='2', GOMEMLIMIT='512MiB',
            TMPDIR=str(output/'temporary'), PYTHONDONTWRITEBYTECODE='1')
        require(not os.path.lexists(account_dir), 'one exclusively new fixture account')
        result['newAccountInitIntent'] = {'path': str(account_dir), 'copies': 0, 'originalInputs': 0, 'privateLogRetained': True}
        save()
        command('native-init', [python, '-B', str(offline), '--exec', str(binary), 'init', '--config', str(config), '--data-dir', str(account_dir)], environment, 30)
        result['accountInitializations'] = 1
        physical(account_dir, True)
        scope, warm = {}, {}

        def phase(label, cold):
            start = time.monotonic()
            item = {'name': label, 'cold': cold, 'status': 'RUNNING', 'stopDispatched': False}
            result['phases'].append(item)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
            command_index = len(result['commands'])
            completed = False

            def request(method, path, body=None, expected_status=200, mutation=None, health=False):
                guard()
                require(time.monotonic()-start < PHASE_SECONDS, 'absolute native phase deadline')
                require(method in ('GET', 'POST', 'PATCH'), 'closed HTTP vocabulary')
                base = '/v1/spaces/'+segment(scope['spaceID']) if 'spaceID' in scope else None
                readonly_post = base is not None and path in (base+'/pinkha/bookmark-create-frame', base+'/query')
                if method != 'GET':
                    require((mutation is None and method == 'POST' and readonly_post) or
                            (not cold and mutation in MUTATIONS), 'only fixed read-only POSTs or warm explicit writes')
                if mutation is not None:
                    require(not cold and len(result['mutations']) < len(MUTATIONS) and
                            mutation == MUTATIONS[len(result['mutations'])], 'each ordered new fixture write dispatches once')
                    expected_routes = {'space': ('POST', '/v1/spaces'),
                        'type': ('POST', base+'/types') if base else None,
                        'editor-part': ('POST', base+'/types/'+segment(scope['typeID'])+'/parts') if 'typeID' in scope else None,
                        'property-owner': ('POST', base+'/collections') if base else None,
                        'url-property': ('POST', base+'/collections/'+segment(scope['ownerID'])+'/properties') if 'ownerID' in scope else None,
                        'layout': ('PATCH', base+'/types/'+segment(scope['typeID'])) if 'typeID' in scope else None,
                        'bookmark': ('POST', base+'/pinkha/objects') if base else None}
                    require((method, path) == expected_routes[mutation], 'exact original setup/conditional-create route')
                require(len(result['requests']) < 180, 'finite total requests including readiness')
                wire = None if body is None else json_bytes(body)
                row = {'phase': label, 'method': method, 'path': path, 'stage': 'dispatching',
                    'readOnlyOperation': mutation is None, 'requestBody': identity(wire) if wire is not None else None}
                result['requests'].append(row)
                mutation_row = None
                if mutation is not None:
                    mutation_row = {'name': mutation, 'method': method, 'path': path, 'state': 'dispatching',
                        'requestBody': identity(wire), 'requestIndex': len(result['requests'])-1}
                    result['mutations'].append(mutation_row)
                save()
                response = connection = None
                try:
                    seconds = min(2 if health else 10, began+MAIN_SECONDS-time.monotonic(), start+PHASE_SECONDS-time.monotonic())
                    require(seconds > 0, 'remaining absolute HTTP budget')
                    with support.absolute_http_deadline(seconds):
                        prior_error = None
                        try:
                            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=seconds)
                            headers = {'Connection': 'close'}
                            if wire is not None:
                                headers['Content-Type'] = 'application/json'
                            connection.request(method, path, body=wire, headers=headers)
                            response = connection.getresponse()
                            row['status'] = response.status
                            maximum = 4096 if health else 262144
                            raw = response.read(maximum+1)
                            ack_path = output/'private'/('response-'+str(len(result['requests']))+'.body')
                            exclusive(ack_path, raw)
                            retained_responses[str(ack_path)] = {'identity': identity(raw), 'maximum': maximum+1}
                            row['rawResponse'] = {'path': str(ack_path), **identity(raw), 'completeBoundedBody': len(raw) <= maximum}
                            if mutation_row is not None:
                                mutation_row['state'] = 'acknowledged-unvalidated'
                                mutation_row['rawResponse'] = row['rawResponse']
                                mutation_row['status'] = response.status
                            save()
                            require(len(raw) <= maximum, 'bounded original response')
                            require(response.status == expected_status, 'exact native HTTP status')
                        except BaseException as error:
                            prior_error = error; raise
                        finally:
                            close_errors = []
                            for handle in (response, connection):
                                if handle is not None:
                                    try:
                                        handle.close()
                                    except BaseException as error:
                                        close_errors.append(error)
                            if close_errors:
                                row['closeErrors'] = [type(error).__name__ for error in close_errors]
                                if prior_error is None:
                                    raise close_errors[0]
                    value = {} if health or expected_status == 204 else closed_json(raw)
                    if expected_status == 204:
                        require(raw == b'', 'original204 has no invented acknowledgement body')
                    row['stage'] = 'received'; save()
                    return value, row, mutation_row
                except BaseException as error:
                    row['stage'] = 'failed'; row['failureType'] = type(error).__name__
                    if mutation_row is not None:
                        mutation_row['state'] = 'unqualified-effects-not-retried'
                    save(); raise

            def read(method, path, body=None):
                return request(method, path, body)[0]

            def mutate(name, method, path, body, status, id_key=None):
                value, _, row = request(method, path, body, status, name)
                if id_key is not None:
                    segment(value.get(id_key))
                    row['knownNativeID'] = value[id_key]
                row['state'] = 'validated-acknowledgement'; save()
                return value

            def base():
                return '/v1/spaces/'+segment(scope['spaceID'])

            def owner_now():
                membership = read('GET', base()+'/members/me')
                require({key: membership.get(key) for key in ('identity', 'status', 'permission')} ==
                        {'identity': scope['accountID'], 'status': 'active', 'permission': 'owner'}, 'current original fresh owner')

            def frame():
                value = read('POST', base()+'/pinkha/bookmark-create-frame', {'typeId': scope['typeID'], 'collections': []})
                require(set(value) == FRAME_KEYS and value['contract'] == 'pinkha-native-bookmark-create-v1' and type(value['version']) is int and
                        value['version'] == 1 and value['accountId'] == scope['accountID'] and value['spaceId'] == scope['spaceID'] and
                        value['typeId'] == scope['typeID'] and value['collections'] == [scope['ownerID']] and
                        value['propertyOwnerId'] == scope['ownerID'] and value['propertyId'] == scope['propertyID'] and value['canWrite'] is True,
                        'complete original-scope read-only Bookmark frame')
                token = value['frame']
                require(type(token) is str and 1 <= len(token) <= 87382 and re.fullmatch('[A-Za-z0-9_-]+', token), 'bounded opaque canonical frame')
                decoded = base64.b64decode(token+'='*((-len(token)) % 4), altchars=b'-_', validate=True)
                require(0 < len(decoded) <= 65536 and base64.urlsafe_b64encode(decoded).rstrip(b'=').decode() == token, 'exact canonical base64url')
                return value

            def steps():
                account = read('GET', '/v1/account')
                segment(account.get('id'))
                capabilities = read('GET', '/v1/pinkha/capabilities')
                require(capabilities.get('contract') == 'pinkha-torah-native-v1' and
                        type(capabilities.get('currentWriterObjectCreate')) is int and capabilities['currentWriterObjectCreate'] == 1 and
                        type(capabilities.get('nativeBookmarkObjectCreate')) is int and capabilities['nativeBookmarkObjectCreate'] == 1,
                        'advertised original current-writer and new conditional-definition routes')
                if cold:
                    require(account['id'] == scope['accountID'], 'same fresh account after actual process death')
                else:
                    scope['accountID'] = account['id']
                    created = mutate('space', 'POST', '/v1/spaces', {'name': 'New bodyless Bookmark native proof'}, 201, 'id')
                    scope['spaceID'] = created['id']; owner_now()
                    created = mutate('type', 'POST', base()+'/types', {'name': 'editor host', 'xKey': 'editor_host', 'layout': {'type': 'page'}}, 201, 'typeId')
                    scope['typeID'] = created['typeId']
                    mutate('editor-part', 'POST', base()+'/types/'+segment(scope['typeID'])+'/parts',
                        {'key': 'editor', 'name': 'editor', 'datasets': [{'module': 'editor'}]}, 201, 'partId')
                    created = mutate('property-owner', 'POST', base()+'/collections',
                        {'name': 'Fresh imported URL namespace', 'xKey': 'fresh_bookmark_url'}, 201, 'collectionId')
                    scope['ownerID'] = created['collectionId']
                    created = mutate('url-property', 'POST', base()+'/collections/'+segment(scope['ownerID'])+'/properties',
                        {'name': 'Source', 'kind': 'string', 'scope': 'synced', 'xFormat': {'type': 'url', 'pinkhaHeart': {
                            'sourceObjectID': 'original-source-definition', 'sourceUniqueKey': 'rel-source', 'relationKey': 'source'}}}, 201, 'propId')
                    scope['propertyID'] = created['propId']
                    address = {'ownerId': scope['ownerID'], 'propertyId': scope['propertyID']}
                    layout = {'type': 'bookmark', 'config': {'pinkhaHeart': {'contract': 'pinkha-heart-native-bookmark-presentation-v1',
                        'sourceRecommendedLayout': 11, 'propertyOwnerId': scope['ownerID'], 'sourceURL': address,
                        'recommended': [address], 'featured': [], 'hidden': [], 'files': []}}}
                    mutate('layout', 'PATCH', base()+'/types/'+segment(scope['typeID']), {'layout': layout}, 204)
                    warm['frame'] = frame()
                    owner_now()
                    created = mutate('bookmark', 'POST', base()+'/pinkha/objects',
                        {'type': scope['typeID'], 'collections': [scope['ownerID']],
                         'initialProperties': {'any': {'name': TITLE}, scope['ownerID']: {scope['propertyID']: SOURCE_URL}},
                         'bookmarkDefinitionFrame': warm['frame']['frame']}, 201, 'objectId')
                    scope['objectID'] = created['objectId']; result['nativeBodylessCreates'] = 1
                owner_now()
                snapshot = read('GET', base()+'/properties/'+segment(scope['objectID']))
                record = snapshot.get('record')
                require(isinstance(record, dict) and record.get('id') == scope['objectID'] and record.get('spaceId') == scope['spaceID'] and
                        isinstance(record.get('any'), dict) and record['any'].get('name') == TITLE and record['any'].get('type') == scope['typeID'] and
                        record['any'].get('collections') == [scope['ownerID']] and isinstance(record.get(scope['ownerID']), dict) and
                        type(record[scope['ownerID']].get(scope['propertyID'])) is str and
                        record[scope['ownerID']][scope['propertyID']].encode() == SOURCE_URL.encode() and '_ver' in record,
                        'exact original object/type/membership and decomposed sourceURL bytes')
                rows = read('POST', base()+'/query', {'objectId': scope['objectID'], 'dataset': 'editor_blocks',
                    'sort': ['nav.pos'], 'limit': 1, 'includeTotal': True})
                require(set(rows) == {'records', 'total', 'hasNext'} and rows['records'] == [] and
                        type(rows['total']) is int and rows['total'] == 0 and rows['hasNext'] is False,
                        'complete zero native editor records, no placeholder block')
                target = read('GET', base()+'/pinkha/document-targets/'+segment(scope['objectID']))
                require(target.get('spaceId') == scope['spaceID'] and target.get('objectId') == scope['objectID'] and
                        target.get('typeId') == scope['typeID'] and target.get('collections') == [scope['ownerID']] and
                        target.get('eligible') is True and target.get('canWrite') is True and
                        target.get('canonicalEditorDataset') == 'editor_blocks' and target.get('policy') == 'canonical-editor-module-v1',
                        'bodyless layout11 object is an actual current native editor target')
                markdown_path = base()+'/objects/'+segment(scope['objectID'])+'/editor/editor_blocks/markdown'
                markdown = read('GET', markdown_path)
                repeat = read('GET', markdown_path)
                require(type(markdown.get('content')) is str and markdown['content'].encode() == b'' and
                        type(markdown.get('version')) is str and markdown['version'] and markdown == repeat,
                        'empty body and a stable native whole-collection version')
                current_frame = frame()
                require(current_frame == warm['frame'], 'complete selected-definition identity remains exact across create/reopen')
                observation = {'objectID': scope['objectID'], 'typeID': scope['typeID'], 'collections': record['any']['collections'],
                    'sourceURL': identity(record[scope['ownerID']][scope['propertyID']].encode()),
                    'objectVersion': record['_ver'], 'editorRows': rows, 'markdown': markdown, 'frameSHA256': identity(json_bytes(current_frame))['sha256']}
                if cold:
                    require(observation == warm['observation'], 'same persisted identity/value/body/version after actual SIGKILL')
                else:
                    warm['observation'] = observation
                owner_now()
                peers = read('GET', base()+'/sync-status')
                require(all(type(peers.get(key)) is int and peers[key] == 0 for key in ('networkPeers', 'localPeers', 'globalPeers')), 'no native peers in either OS-denied process')
                require(len(result['mutations']) == 7 and [row['name'] for row in result['mutations']] == list(MUTATIONS) and
                        all(row['state'] == 'validated-acknowledgement' for row in result['mutations']), 'only seven actual validated new writes')
                item['observation'] = observation
                item['currentOwnerAndZeroPeers'] = True
                item['status'] = 'PASS_PHASE'; result['scope'] = dict(scope); save()

            def service_observer():
                nonlocal completed
                try:
                    guard()
                    require(time.monotonic()-start < PHASE_SECONDS, 'absolute native phase deadline')
                    if len(result['commands']) <= command_index:
                        return None
                    row = result['commands'][command_index]
                    if row.get('processGroupAbsent') is True or row.get('exitCode') is not None or item['stopDispatched'] or 'pid' not in row:
                        return None
                    pid = row['pid']
                    require(os.waitid(os.P_PID, pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and
                            os.getpgid(pid) == pid and os.getsid(pid) == pid, 'live unreaped original native process ownership')
                    if not completed:
                        try:
                            request('GET', '/v1/health', health=True)
                        except (OSError, http.client.HTTPException):
                            require(time.monotonic()-start < 45, 'bounded initial native readiness'); return None
                        raw_status = Path('/proc/'+str(pid)+'/status').read_text()
                        status = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
                        require(status['NoNewPrivs'].strip() == '1' and status['Seccomp'].strip() == '2' and
                                Path('/proc/'+str(pid)+'/exe').resolve() == binary, 'actual OS-denial inherited before original native process starts')
                        item['actualPID'] = pid
                        item['osDenial'] = {'noNewPrivileges': True, 'seccompFilterMode': 2, 'nativeExecutable': str(binary)}
                        steps(); completed = True
                    require(os.waitid(os.P_PID, pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and
                            os.getpgid(pid) == pid and os.getsid(pid) == pid, 'same still-unreaped process before stop')
                    number = signal.SIGTERM if cold else signal.SIGKILL
                    if not cold:
                        require(item['status'] == 'PASS_PHASE' and result['nativeBodylessCreates'] == 1 and
                                len(result['mutations']) == 7 and all(row['state'] == 'validated-acknowledgement' for row in result['mutations']),
                                'explicit crash gate after saved known-ID/bodyless acceptance')
                        row['intentionalCrashGateValidated'] = True
                        row['intentionalCrashSignal'] = int(number)
                    item['stopIntent'] = {'signal': int(number), 'leaderUnreaped': True, 'afterValidatedPhase': True}
                    save()
                    os.killpg(pid, number)
                    item['stopDispatched'] = True
                    row['callerStopSignal'] = int(number)
                    save(); return None
                except BaseException as error:
                    item.setdefault('error', {'type': type(error).__name__, 'message': str(error)})
                    return type(error).__name__+': '+str(error)

            argv = [python, '-B', str(offline), '--exec', str(binary), 'run', '--config', str(config),
                '--data-dir', str(account_dir), '--addr', '127.0.0.1:'+str(port)]
            expected_exit = 0 if cold else -signal.SIGKILL
            _, row = command(label, argv, environment, PHASE_SECONDS, service_observer, expected_exit)
            require(completed and item['status'] == 'PASS_PHASE' and item['stopDispatched'] and
                    row['exitCode'] == expected_exit and row['processGroupAbsent'] is True and not row['forcedCleanup'] and
                    row['cleanupErrors'] == row['signals'] == [], 'accepted actual phase and owned process closure')

        phase('native-warm-crash', False)
        phase('native-cold-offline', True)
        require(len(result['commands']) == 3 and result['accountInitializations'] == result['nativeBodylessCreates'] == 1 and
                [row['exitCode'] for row in result['commands']] == [0, -signal.SIGKILL, 0] and
                result['phases'][0]['actualPID'] != result['phases'][1]['actualPID'], 'one init, one actual kill and one fresh normal reopen')
        require(not any(row['phase'] == 'native-cold-offline' and not row['readOnlyOperation'] for row in result['requests']), 'cold uses only reads, including explicitly read-only POSTs')
        result.update(status='PASS_ONE_BODYLESS_BOOKMARK_ACTUAL_CRASH_AND_OFFLINE_REOPEN',
            actualNativeRuntimePhases=2, actualNativeCreates=1, actualSetupMutations=6,
            intentionalSIGKILLs=1, coldReadOnlyReopens=1, completeEmptyEditorRecords=True,
            sameOriginalURLBytesAndIdentity=True, sameNativeBodyVersion=True,
            syntheticDefinitionOnly=True, originalMigrationTypesStillUnqualified=True)
    except BaseException as error:
        result['status'] = 'FAIL_BODYLESS_BOOKMARK_PRESERVED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        result['allStartedOwnedGroupsPositivelyAbsent'] = bool(result['commands']) and all(row.get('processGroupAbsent') is True for row in result['commands'])
        final_deadline = time.monotonic()+FINAL_SECONDS
        audits = []
        def check_inputs():
            for name, expected in inputs.items():
                checkpoint()
                require(identity(frozen(Path(name), expected['maximum'])) == expected['identity'], 'declared public input or native product changed')
            if 'qualifiedProducer' in result:
                native = result['qualifiedProducer']['nativeBinary']
                require(stat.S_IMODE(physical(Path(native['path'])).st_mode) == native['mode'], 'qualified native executable mode unchanged')
            return True
        def check_responses():
            for name, expected in retained_responses.items():
                checkpoint()
                require(identity(frozen(Path(name), expected['maximum'])) == expected['identity'], 'original acknowledged response bytes changed')
            return True
        audits.append(('publicInputsAndNativeProduct', check_inputs))
        audits.append(('originalResponses', check_responses))
        if source_before is not None:
            audits.append(('compiledSource', lambda: compiler.source_inventory(producer_source, checkpoint) == source_before))
        if owner_admission is not None:
            audits.append(('ownedLifetimeInputs', lambda: support.recheck(owner_admission) is None))
        for label, action in audits:
            try:
                checkpoint(); require(action(), 'complete final '+label+' verification')
                result.setdefault('finalIntegrity', {})[label] = True
            except BaseException as error:
                result['status'] = 'FAIL_BODYLESS_BOOKMARK_PRESERVED'
                result.setdefault('finalIntegrity', {})[label] = False
                result['completionErrors'].append({'boundary': label, 'type': type(error).__name__, 'message': str(error)})
        try:
            if result['status'].startswith('PASS_'):
                require(result['allStartedOwnedGroupsPositivelyAbsent'] and len(result['commands']) == 3 and
                        all(not row['forcedCleanup'] and row['cleanupErrors'] == row['signals'] == [] for row in result['commands']) and
                        [row['exitCode'] for row in result['commands']] == [0, -signal.SIGKILL, 0], 'all exact actual owned groups closed without cleanup')
            result['finalFreeBytes'] = guard()
        except BaseException as error:
            result['status'] = 'FAIL_BODYLESS_BOOKMARK_PRESERVED'
            result['completionErrors'].append({'boundary': 'acceptanceAndResources', 'type': type(error).__name__, 'message': str(error)})
        try:
            save()
        except BaseException as error:
            result['status'] = 'FAIL_BODYLESS_BOOKMARK_PRESERVED'
            result['completionErrors'].append({'boundary': 'receiptRetention', 'type': type(error).__name__})
            try:
                save_json(output/'terminal-failure.json', result)
            except BaseException:
                pass
    print(json.dumps({'status': result['status'], 'receipt': str(output/'result.json'),
        'allStartedOwnedGroupsPositivelyAbsent': result['allStartedOwnedGroupsPositivelyAbsent'],
        'compilerInvocations': 0, 'priorTestMethodsReexecuted': 0,
        'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
