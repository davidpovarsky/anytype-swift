#!/usr/bin/env python3
"""SOURCE-ONLY one-group qualification of two fresh HTTP deadline controls.

This controller launches only a Python loopback fixture. It does not launch
Any, open an account, compile code, or rerun the five owned-command controls.
An assigned root runtime slot and unchanged resource gates remain mandatory.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time

PARENT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127')
HERE = Path(__file__).resolve().parent
INPUTS = {
    HERE/'verify_current_authority_http.py': '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84',
    HERE/'http_deadline_controls.py': '4ffd006042ede3f0cb494ea3fa89ece8b3f68bce0c4873887b9d9d27ccfee876',
    HERE/'owned_swift_commands.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json'):
        '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d',
}
MIB = 1024**2


def frozen(path, maximum=2*MIB):
    assert path.is_absolute() and path.resolve()==path and not path.is_symlink()
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_size<=maximum
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        assert os.fstat(stream.fileno())==before
        data = stream.read(maximum+1)
        assert os.fstat(stream.fileno())==before
    assert path.lstat()==before and len(data)==before.st_size
    return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification requires assertions enabled')
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    output = args.output
    assert output.parent==PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', output.name)
    os.umask(0o077)
    assert PARENT.parent.resolve()==PARENT.parent and PARENT.parent.is_dir()
    if not PARENT.exists(): PARENT.mkdir(mode=0o700)
    assert PARENT.resolve()==PARENT and PARENT.is_dir() and not PARENT.is_symlink()
    output.mkdir(mode=0o700, exist_ok=False)
    receipt = output/'result.json'
    with receipt.open('xb') as stream:
        stream.write(b'{}\n'); stream.flush(); os.fsync(stream.fileno())
    began = time.monotonic()
    serial = 0
    admitted = {}
    result = {'status': 'RUNNING', 'commands': [], 'errors': [], 'completionErrors': [],
              'nativeProcesses': 0, 'accountInputs': 0, 'compilerInvocations': 0,
              'previousLifecycleControlsRerun': 0, 'rootFloorBytes': 2*1024**3,
              'developmentFloorBytes': 512*MIB, 'outputCapBytes': 8*MIB,
              'rootAdmissionReserveBytes': 4*MIB, 'developmentAdmissionReserveBytes': 8*MIB,
              'controllerDeadlineSeconds': 60, 'commandDeadlineSeconds': 15,
              'requiredOuterTimeoutSeconds': 120}

    def save(path, value):
        nonlocal serial
        assert path.is_relative_to(output)
        serial += 1
        temporary = path.with_name(path.name+'.next-'+str(serial))
        with temporary.open('x') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def guard(admit=False):
        assert time.monotonic()-began<60, 'bounded deadline-control qualifier'
        assert not (output/'abort').exists()
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', 2*1024**3, 4*MIB), ('development', 512*MIB, 8*MIB)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
            assert free[name]>=floor+(reserve if admit else 0), name+' original emergency floor/reserve'
        used = 0; count = 0
        for parent, dirs, files in os.walk(output, followlinks=False):
            for name in dirs:
                assert not (Path(parent)/name).is_symlink()
            for name in files:
                info = (Path(parent)/name).lstat()
                assert stat.S_ISREG(info.st_mode)
                used += max(info.st_size, info.st_blocks*512); count += 1
                if name=='original.log': assert info.st_size<=256*1024
        assert count<=200 and used<=8*MIB
        result['peakOwnedBytes'] = max(used, result.get('peakOwnedBytes', 0))
        return free

    def observe():
        try: guard(); return None
        except BaseException as error: return type(error).__name__+': '+str(error)

    def interrupted(number, _frame):
        raise RuntimeError('HTTP-deadline qualifier interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    try:
        result['admissionFreeBytes'] = guard(True)
        for path, expected in INPUTS.items():
            raw = frozen(path); assert sha(raw)==expected
            admitted[str(path)] = {'bytes': len(raw), 'sha256': expected, 'maximum': 2*MIB}
        own = Path(__file__).resolve(); own_raw = frozen(own)
        admitted[str(own)] = {'bytes': len(own_raw), 'sha256': sha(own_raw), 'maximum': 2*MIB}
        proof_path = next(path for path in INPUTS if path.name=='result.json')
        proof = json.loads(frozen(proof_path))
        assert proof['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
        assert proof['helperSHA256']==INPUTS[HERE/'owned_swift_commands.py']
        assert proof['allOwnedGroupsPositivelyAbsent'] and len(proof['commands'])==5
        assert len(proof['methods'])==5 and all(row['status']=='PASS' for row in proof['methods'])
        specification = importlib.util.spec_from_file_location('qualified_deadline_owned', HERE/'owned_swift_commands.py')
        owned = importlib.util.module_from_spec(specification); specification.loader.exec_module(owned)
        driver = Path(sys.executable).resolve(strict=True)
        driver_raw = frozen(driver, 32*MIB)
        admitted[str(driver)] = {'bytes': len(driver_raw), 'sha256': sha(driver_raw), 'maximum': 32*MIB}
        result['pythonDriver'] = {'path': str(driver), 'sha256': sha(driver_raw), 'version': sys.version}
        argv = [str(driver), '-B', str(HERE/'http_deadline_controls.py'),
                '--controller', str(HERE/'verify_current_authority_http.py'),
                '--controller-sha256', INPUTS[HERE/'verify_current_authority_http.py'],
                '--output', str(output/'controls')]
        env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
        raw_log, command = owned.run(output/'command', argv, output, env, 15, observe, save,
            lambda path: sha(frozen(path, 256*1024)), result['commands'])
        log = frozen(raw_log, 256*1024).decode()
        assert re.search(r'Ran 2 tests in [0-9.]+s', log)
        assert '\nOK\n' in log
        controls_raw = frozen(output/'controls/result.json')
        controls = json.loads(controls_raw)
        result['actualControls'] = controls
        result['actualControlsSHA256'] = sha(controls_raw)
        assert controls['status']=='PASS_TWO_FRESH_ABSOLUTE_HTTP_DEADLINE_CONTROLS'
        assert controls['controllerSHA256']==INPUTS[HERE/'verify_current_authority_http.py']
        assert controls['actualMethods']=={'runs': 2, 'failures': 0, 'errors': 0, 'skips': 0}
        assert len(controls['controls'])==2 and {r['name'] for r in controls['controls']}=={'slow-header', 'slow-body'}
        assert all(row['status']=='PASS' and row['threadJoined'] and row['successfulDripWrites']>=3 and not row['peerErrors'] for row in controls['controls'])
        assert controls['sourceUnchanged'] and controls['errors']==[]
        assert command['exitCode']==0 and command['processGroupAbsent'] and not command['forcedCleanup']
        result['status'] = 'PASS_TWO_ACTUAL_HTTP_DEADLINES_AND_OWNED_CLOSURE'
    except BaseException as error:
        result['status'] = 'FAIL_HTTP_DEADLINE_QUALIFIER'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') for row in result['commands'])
        try:
            for name, wanted in admitted.items():
                raw = frozen(Path(name), wanted['maximum'])
                assert len(raw)==wanted['bytes'] and sha(raw)==wanted['sha256']
            result['publicInputsUnchanged'] = True
            if result['status'].startswith('PASS_'):
                assert len(result['commands'])==1 and result['allOwnedGroupsPositivelyAbsent']
                assert all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['commands'])
            result['freeAfter'] = guard()
        except BaseException as error:
            result['status'] = 'FAIL_HTTP_DEADLINE_QUALIFIER'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        result['seconds'] = time.monotonic()-began
        save(receipt, result)
    print(json.dumps({'status': result['status'], 'result': str(receipt), 'sha256': sha(frozen(receipt))}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
