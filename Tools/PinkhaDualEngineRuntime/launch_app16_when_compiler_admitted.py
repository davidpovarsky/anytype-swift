"""Bounded resource queue for one exact owned App16 builder; no cleanup of other work."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import time

ROOT = pathlib.Path('/Users/m1/development/anytype-d-active-20261125/main16-wave2-20261127')
SOURCE = ROOT.parent / 'main14/source'
DERIVED = ROOT.parent / 'main14/app-derived'
CONTROL = ROOT / 'control'
BUILDER = CONTROL / 'build_wave2_app16_compiler_qualified.py'
SOURCE_COMMIT = 'a089ff29a5c0a7e415aac800844505f099a5561d'
PINS = {
    BUILDER: '9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c',
    CONTROL / 'build_wave2_app16_compiler_qualified_delta.json': '5e18f0a7cdb25cc30d010eb0c19819fe778cb338366763f06f76fef649189970',
    ROOT / 'cache-requalification1/receipt.json': '26b16e0bb4266f6f15bd445f70a4032f027c36ca6ec6c255b2e6f9608f7f7245',
    ROOT / 'source-staging1/receipt.json': 'ed896be868e973f0bdd704612b641547f51b15509805d4d66b7461be88507d21',
}
REQUIRED = 6 * 1024**3 + 2 * 1024**3 + 512 * 1024**2
QUEUE = ROOT / 'resource-queue2'

def write(path, value):
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)

def exact_inputs():
    for path, pin in PINS.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin, str(path)
    assert not (ROOT / 'build16').exists()
    assert not (CONTROL / 'build16-launch.json').exists()
    for args, expected in [(['rev-parse', 'HEAD'], SOURCE_COMMIT), (['status', '--porcelain'], '')]:
        result = subprocess.run(['git', '-C', str(SOURCE)] + args, capture_output=True, text=True, check=True, timeout=60)
        assert result.stdout.strip() == expected, args

def conflicts():
    result = subprocess.run(['ps', '-axo', 'pid=,comm=,args='], capture_output=True, text=True, check=True, timeout=20)
    return [line for line in result.stdout.splitlines()
            if any(name in line for name in ['xcodebuild', 'swift-frontend', 'clang', 'XCBBuildService'])
            and (str(SOURCE) in line or str(DERIVED) in line)]

def main():
    QUEUE.mkdir(mode=0o700)
    start = time.time()
    record = {'protocol': 'wave2-app16-bounded-resource-queue-v1', 'started': start,
              'deadline': start + 1800, 'requiredBytes': REQUIRED, 'status': 'WAITING_FOR_MEASURED_RESOURCES',
              'testsExecuted': 0, 'buildsStarted': 0, 'observations': []}
    try:
        exact_inputs()
        while time.time() < record['deadline']:
            free = shutil.disk_usage(ROOT).free
            active = conflicts()
            record['observations'].append({'at': time.time(), 'freeBytes': free, 'conflicts': active})
            write(QUEUE / 'receipt.json', record)
            if free >= REQUIRED and not active:
                exact_inputs()
                database = DERIVED / 'Build/Intermediates.noindex/XCBuildData/build.db'
                if database.exists():
                    observed = subprocess.run(['/usr/sbin/lsof', str(database)], capture_output=True, text=True, timeout=15)
                    assert observed.returncode == 1 and not observed.stdout, observed.stdout
                free = shutil.disk_usage(ROOT).free
                if free < REQUIRED or conflicts():
                    time.sleep(10)
                    continue
                argv = ['/opt/homebrew/bin/python3.12', '-B', str(BUILDER), SOURCE_COMMIT]
                log = CONTROL / 'build16-original-wrapper.log'
                with log.open('xb') as stream:
                    process = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                launch = {'protocol': 'wave2-app16-owned-builder-launch-v1', 'pid': process.pid, 'pgid': process.pid,
                          'started': time.time(), 'argv': argv, 'log': str(log), 'sourceCommit': SOURCE_COMMIT,
                          'sourceRoot': str(SOURCE), 'appDerived': str(DERIVED), 'freeBytes': free,
                          'requiredAdmissionBytes': REQUIRED, 'compilerConflicts': [],
                          'buildDatabasePresentAtLaunch': database.exists(), 'status': 'LAUNCHED_NOT_BUILD_ACCEPTANCE',
                          'builderSHA256': PINS[BUILDER], 'pinnedInputs': {str(k): v for k, v in PINS.items()}}
                with (CONTROL / 'build16-launch.json').open('x') as stream:
                    stream.write(json.dumps(launch, indent=2, sort_keys=True) + '\n')
                record.update(status='EXACT_BUILDER_LAUNCHED_NOT_BUILD_ACCEPTANCE', buildsStarted=1,
                              builderPID=process.pid, finished=time.time())
                write(QUEUE / 'receipt.json', record)
                return
            time.sleep(10)
        record.update(status='RESOURCE_QUEUE_DEADLINE_NO_BUILD_STARTED', finished=time.time())
        write(QUEUE / 'receipt.json', record)
    except BaseException as error:
        record.update(status='FAIL_RESOURCE_QUEUE', error=repr(error), finished=time.time())
        write(QUEUE / 'receipt.json', record)
        raise

if __name__ == '__main__':
    main()
