from pathlib import Path
import os, json, hashlib, subprocess, time, signal, shutil, argparse, datetime

ROOT = Path('/Users/m1/builds/pinkha-c-source-bridge-limits-20261125')
METHOD = 'TestPinkhaSourceCaptureBridgeActualBoundedDefaults'
GO = '/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go'
COMMITS = {
    'baseline': 'd59568f999c9f1e6aa1d014a743d16999de84006',
    'fixed': 'b7454dca344db7d32f0dc7b7eb5aff575b6a2535',
}
LIBRARY_SHA = '30c4bc974615e03575c2d1f796ff594f2d0a0f7dd21e5b97ffbd836c99c31788'
SYNC_SHA = 'c005bd6cde8d8f8a6007c35f06894f3d89f9f07c'
TEST_SHA = '0d34f7c8cb23aa7c43de49390cc53b69a4e8d8bd1058d734e16ed52bfe55a76c'
MANIFEST_SHAS = {
    'baseline-source.json': 'c21b6b1b83daf0dac6a85555c1bbb2c70a348ddfbcc7bd2bbee072b582e502bd',
    'fixed-source.json': 'c8138afcb70a01d8280927ec1e98c3f8e51d00807a8e14c9119b4d88847c28b8',
    'any-sync-native-witness-source.json': '38931d8fc69d0c35109cfbb17d5276dda3ca6800892a70cbd628773f022d7af4',
}

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p, value):
    with p.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    os.chmod(p, 0o600)

def verify(base, meta):
    actual = {}
    for path in base.rglob('*'):
        if path.is_file() or path.is_symlink():
            data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            actual[path.relative_to(base).as_posix()] = hashlib.sha1(
                b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    expected = {row['path']: row['gitBlob'] for row in meta['files']}
    if actual != expected:
        raise RuntimeError('complete source manifest differs')
    return {'files': len(actual), 'source': meta['source'],
            'censusSHA256': hashlib.sha256(json.dumps(
                actual, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}

def validate_inputs(phase):
    incoming = ROOT / 'incoming'
    for name, expected_hash in MANIFEST_SHAS.items():
        path = incoming / name
        if path.is_symlink() or digest(path) != expected_hash:
            raise RuntimeError('Git-bound complete source manifest changed')
    source = json.loads((incoming / (phase + '-source.json')).read_text())
    sync = json.loads((incoming / 'any-sync-native-witness-source.json').read_text())
    if source['source'] != COMMITS[phase] or sync['source'] != SYNC_SHA:
        raise RuntimeError('source revision differs')
    base = ROOT / 'source' / phase
    result = {'heart': verify(base, source),
              'anySync': verify(ROOT / 'source/any-sync', sync)}
    if digest(base / 'core/pinkha_native_source_capture_bridge_test.go') != TEST_SHA:
        raise RuntimeError('actual bridge method changed')
    if digest(ROOT / 'native-libs/libtantivy_go.a') != LIBRARY_SHA:
        raise RuntimeError('qualified Darwin library changed')
    mod = (base / 'go.mod').read_bytes()
    expected_mod = mod + b'\nreplace github.com/anyproto/any-sync => ' + str(
        ROOT / 'source/any-sync').encode() + b'\n'
    if (ROOT / (phase + '.mod')).read_bytes() != expected_mod:
        raise RuntimeError('isolated module replacement differs')
    if (ROOT / (phase + '.sum')).read_bytes() != (base / 'go.sum').read_bytes():
        raise RuntimeError('original dependency checksums differ')
    result['originalGoModSHA256'] = hashlib.sha256(mod).hexdigest()
    result['moduleSHA256'] = digest(ROOT / (phase + '.mod'))
    result['sumSHA256'] = digest(ROOT / (phase + '.sum'))
    result['nativeLibrarySHA256'] = LIBRARY_SHA
    return result

def group_present(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False

def stop_owned(process, errors):
    if process is None:
        return
    try:
        present = group_present(process.pid)
    except BaseException as error:
        errors.append({'phase': 'owned-group-observation', 'error': type(error).__name__})
        return
    if not present:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while group_present(process.pid) and time.monotonic() < deadline:
            time.sleep(.2)
        if group_present(process.pid):
            os.killpg(process.pid, signal.SIGKILL)
            deadline = time.monotonic() + 5
            while group_present(process.pid) and time.monotonic() < deadline:
                time.sleep(.2)
        if group_present(process.pid):
            errors.append({'phase': 'owned-group-remains'})
    except ProcessLookupError:
        pass
    except BaseException as error:
        errors.append({'phase': 'owned-group-cleanup', 'error': type(error).__name__})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=tuple(COMMITS), required=True)
    args = parser.parse_args()
    phase = args.phase
    out = ROOT / (phase + '-attempt1')
    out.mkdir(mode=0o700, exist_ok=False)
    result = {'protocol': 'pinkha-actual-core-source-bridge-regression-v1',
              'phase': phase, 'source': COMMITS[phase], 'method': METHOD,
              'status': 'FAIL', 'wholeSpaceMigrationComplete': False,
              'appleUIAccepted': False, 'newNativeSliceProduced': False}
    process = None
    log = None
    errors = []
    started = time.monotonic()
    initial_free = shutil.disk_usage(ROOT).free
    minimum_free = initial_free
    try:
        result['sourceBefore'] = validate_inputs(phase)
        # Previous warmed C core/application compilation used under 1.2GiB;
        # this phase adds only one native core test and private account.
        # The 1.5GiB estimate includes the test executable, compiler temp and
        # private recovery fixture; stop only this owned phase below 2GiB.
        if initial_free < (2 << 30) + (1536 << 20):
            raise RuntimeError('measured warmed core-test phase does not fit')
        env = os.environ.copy()
        env.update({
            'PATH': '/Users/m1/toolchains/anytapy-go1.27.4/go/bin:/usr/bin:/bin:/usr/sbin:/sbin',
            'GOWORK': 'off', 'GOTOOLCHAIN': 'local',
            'GOCACHE': '/Users/m1/caches/anytapy-go1.27.4-build',
            'GOMODCACHE': '/Users/m1/caches/anytapy-go-mod',
            'GOPROXY': 'file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct',
            'GOSUMDB': 'sum.golang.org', 'GOMAXPROCS': '2', 'GOMEMLIMIT': '2GiB',
            'CGO_ENABLED': '1', 'GOFLAGS': '', 'GOEXPERIMENT': '',
            'CGO_LDFLAGS': '-L' + str(ROOT / 'native-libs') + ' -framework CoreFoundation -framework Security',
        })
        for name in ('temporary', 'private'):
            (out / name).mkdir(mode=0o700)
        env['TMPDIR'] = str(out / 'temporary')
        env['GOTMPDIR'] = env['TMPDIR']
        env['PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT'] = str(out / 'private')
        command = [GO, 'test', '-mod=readonly', '-count=1', '-p=2',
                   '-timeout=480s', '-json', '-run', '^' + METHOD + '$',
                   '-tags', 'pinkha_loaded_account_witness,pinkha_loaded_account_witness_acceptance',
                   '-modfile=' + str(ROOT / (phase + '.mod')), './core']
        result['command'] = command
        result['cwd'] = str(ROOT / 'source' / phase)
        result['environment'] = {key: env[key] for key in (
            'GOWORK', 'GOTOOLCHAIN', 'GOCACHE', 'GOMODCACHE', 'GOPROXY',
            'GOSUMDB', 'GOMAXPROCS', 'GOMEMLIMIT', 'CGO_ENABLED',
            'GOFLAGS', 'GOEXPERIMENT', 'CGO_LDFLAGS', 'TMPDIR',
            'GOTMPDIR', 'PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT')}
        result['resourceAdmission'] = {
            'initialFreeBytes': initial_free, 'estimatedIncrementalBytes': 1536 << 20,
            'emergencyFreeBytes': 2 << 30, 'parallelism': 2,
            'nativeProducerOverlap': False, 'globalProcessWalk': False}
        save(out / 'launch.json', result)
        logpath = out / 'original-go-test.jsonl'
        log = logpath.open('xb')
        os.chmod(logpath, 0o600)
        process = subprocess.Popen(command, cwd=result['cwd'], env=env,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        save(out / 'started.json', {'pid': process.pid, 'pgid': process.pid,
             'command': command, 'startedAt': datetime.datetime.now(
                 datetime.timezone.utc).isoformat()})
        reason = None
        while process.poll() is None:
            minimum_free = min(minimum_free, shutil.disk_usage(ROOT).free)
            if minimum_free < 2 << 30:
                reason = 'owned emergency disk floor'
                break
            if time.monotonic() - started > 1000:
                reason = 'owned controller deadline'
                break
            time.sleep(2)
        if reason is not None:
            result['stopReason'] = reason
            stop_owned(process, errors)
        result['returncode'] = process.wait(timeout=20)
        log.close()
        log = None
        terminal = []
        rawlog = logpath.read_text(errors='replace')
        for line in rawlog.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if item.get('Action') in ('pass', 'fail', 'skip'):
                terminal.append({key: item[key] for key in (
                    'Action', 'Package', 'Test', 'Elapsed') if key in item})
        result['events'] = terminal
        result['logSHA256'] = digest(logpath)
        result['logBytes'] = logpath.stat().st_size
        actual = [row for row in terminal if row.get('Test') == METHOD]
        result['sourceAfter'] = validate_inputs(phase)
        if result['sourceBefore'] != result['sourceAfter']:
            raise RuntimeError('native source changed during actual test')
        if reason:
            raise RuntimeError(reason)
        if phase == 'baseline':
            marker = 'actual exported source capture failed (owned-limit refusal=true): current owned Space capability required'
            if result['returncode'] != 1 or len(actual) != 1 or actual[0]['Action'] != 'fail' or marker not in rawlog:
                raise RuntimeError('original zero-limit failure was not specifically reproduced')
            if any(row['Action'] == 'skip' for row in terminal):
                raise RuntimeError('baseline test skipped')
            if (out / 'private' / METHOD / 'source-bridge-result.json').exists():
                raise RuntimeError('baseline unexpectedly produced a completed bridge receipt')
            result['status'] = 'BASELINE_NATIVE_BRIDGE_FAILURE_REPRODUCED'
            result['testAcceptance'] = {'passed': 0, 'failed': 1, 'skipped': 0}
        else:
            if result['returncode'] != 0 or len(actual) != 1 or actual[0]['Action'] != 'pass':
                raise RuntimeError('actual fixed bridge regression did not pass')
            if any(row['Action'] in ('fail', 'skip') for row in terminal):
                raise RuntimeError('fixed bridge run has failure or skip')
            proofpath = out / 'private' / METHOD / 'source-bridge-result.json'
            proof = json.loads(proofpath.read_text())
            if proof.get('contract') != 'pinkha-actual-source-bridge-default-limits-v1' or \
               proof.get('actualCoreBridgeCaptures') != 2 or proof.get('actualNativeSessionGrants') != 2 or \
               proof.get('invalidLowerNativeLimitCasesRefused') != 3 or \
               proof.get('closedSessionRefused') is not True or \
               proof.get('releasedBindingRefused') is not True or \
               proof.get('privateSourceRecoveryRetained') is not True or \
               proof.get('permitsDestinationWrites') is not False or \
               proof.get('wholeSpaceMigrationComplete') is not False or proof.get('appleUIAccepted') is not False:
                raise RuntimeError('actual private bridge receipt differs')
            result['actualBridgeProof'] = proof
            result['actualBridgeProofSHA256'] = digest(proofpath)
            result['status'] = 'PASS_ACTUAL_CORE_BRIDGE_NOT_APP_UI'
            result['testAcceptance'] = {'passed': 1, 'failed': 0, 'skipped': 0}
    except BaseException as error:
        result['status'] = 'FAIL'
        result['error'] = {'type': type(error).__name__, 'description': str(error)}
    finally:
        stop_owned(process, errors)
        if process is not None:
            try:
                process.wait(timeout=10)
            except BaseException as error:
                errors.append({'phase': 'owned-process-wait', 'error': type(error).__name__})
        if log is not None:
            try:
                log.close()
            except BaseException as error:
                errors.append({'phase': 'owned-log-close', 'error': type(error).__name__})
        try:
            if process is not None:
                result['ownedProcessGroupAbsent'] = not group_present(process.pid)
                if not result['ownedProcessGroupAbsent']:
                    errors.append({'phase': 'final-owned-group-remains'})
        except BaseException as error:
            errors.append({'phase': 'final-owned-group-observation', 'error': type(error).__name__})
        try:
            p = out / 'original-go-test.jsonl'
            if p.exists():
                result['logSHA256'] = digest(p)
                result['logBytes'] = p.stat().st_size
        except BaseException as error:
            errors.append({'phase': 'final-log-retention', 'error': type(error).__name__})
        result['cleanupErrors'] = errors
        if errors:
            result['statusBeforeCleanupFailure'] = result['status']
            result['status'] = 'FAIL'
        result['seconds'] = round(time.monotonic() - started, 3)
        result['minimumFreeBytes'] = minimum_free
        result['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'result.json', result)
        print(json.dumps({'result': str(out / 'result.json'),
                          'sha256': digest(out / 'result.json'),
                          'status': result['status'],
                          'testAcceptance': result.get('testAcceptance'),
                          'seconds': result['seconds'],
                          'error': result.get('error')}), flush=True)
    return 0 if result['status'] in (
        'BASELINE_NATIVE_BRIDGE_FAILURE_REPRODUCED', 'PASS_ACTUAL_CORE_BRIDGE_NOT_APP_UI') else 1

if __name__ == '__main__':
    raise SystemExit(main())
