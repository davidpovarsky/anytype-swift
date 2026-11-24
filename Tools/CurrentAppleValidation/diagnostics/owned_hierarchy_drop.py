"""Observe native drop dispatch after the original UI method's cold reopen.

This bounded local LLDB diagnostic executes one original UI method on a newly
owned Simulator. It records symbol hits and call stacks, never frame values.
It grants no acceptance credit, changes no product code, and builds nothing.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

PRODUCTS = Path('/Users/m1/builds/_retained-anytype/45438097556-1/build/'
    'current-apple-native-ui-failed-45438097556-1/work/derived/Build/Products')
DESCRIPTOR = PRODUCTS / 'PinkhaAnyNativeApp_iphonesimulator27.0-arm64.xctestrun'
APP = PRODUCTS / 'Debug-iphonesimulator/PinkhaAnyNative.app'
RUNNER = PRODUCTS / 'Debug-iphonesimulator/PinkhaAnyNativeUITests-Runner.app'
TARGET = 'PinkhaAnyNativeUITests'
SELECTOR = 'NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen'
SYMBOL_FILE = Path(__file__).with_name('drop-symbols.json')
SYMBOLS = json.loads(SYMBOL_FILE.read_text())
assert set(SYMBOLS) == {'dropDestination', 'listOnMove', 'modelMove'}
PINNED = {
    DESCRIPTOR: '6a954a8c523142352b259c635fd3a925f9936549986fb1743663d1b5e389ffd1',
    APP / 'PinkhaAnyNative': 'fb1b6fb75715a8096d57e93bd4b620ea80be0efa3ffdafa14bbc12d5b43a63f5',
    APP / 'PinkhaAnyNative.debug.dylib': '2afcff089404f07c77763ac0bcdd73e8e236b243f2cfa78a1062efef71e08112',
}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        row = {'mode': stat.S_IMODE(info.st_mode)}
        if path.is_symlink():
            row.update(kind='symlink', target=os.readlink(path))
        elif path.is_dir():
            row.update(kind='directory')
        elif path.is_file():
            row.update(kind='file', bytes=info.st_size, sha256=digest(path))
        else:
            raise RuntimeError('Unexpected retained product type')
        result[str(path.relative_to(root))] = row
    return result


def run(argv, *, timeout=30, check=True):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('Command failed: ' + argv[0] + ' ' + str(result.returncode))
    return result


def relocated(value):
    if isinstance(value, dict):
        return {key: relocated(item) for key, item in value.items()}
    if isinstance(value, list):
        return [relocated(item) for item in value]
    if isinstance(value, str):
        return value.replace('__TESTROOT__', str(PRODUCTS))
    return value


def stop_owned(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def stop_owned_diagnostics(work, udid):
    actions = []
    def owned_groups():
        matches = []
        listing = run(['ps', '-axo', 'pid=,pgid=,command=']).stdout
        for line in listing.splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) != 3:
                continue
            pid, group, command = int(parts[0]), int(parts[1]), parts[2]
            if str(work) in command and udid in command and 'simctl diagnose' in command:
                assert pid == group, 'Unexpected owned diagnostic process group'
                matches.append(group)
        return matches
    for group in owned_groups():
        try:
            os.killpg(group, signal.SIGTERM)
            actions.append({'processGroup': group, 'signal': 'SIGTERM'})
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 10
    remaining = owned_groups()
    while remaining and time.monotonic() < deadline:
        time.sleep(0.2)
        remaining = owned_groups()
    return {'actions': actions, 'remainingOwnedGroups': remaining}


def callback_module(work):
    # A false return resumes the process immediately after the bounded read.
    # No Swift expression evaluation or access to private document values.
    return '''import json,time,lldb
from pathlib import Path
LOG = Path(%r)
LABELS = {}
def hit(frame, location, internal_dict):
    stack=[]
    thread=frame.GetThread()
    for i in range(min(7, thread.GetNumFrames())):
        item=thread.GetFrameAtIndex(i)
        address=item.GetPCAddress()
        symbol=item.GetSymbol()
        line=item.GetLineEntry()
        stack.append({"function":item.GetFunctionName(),
            "module":str(item.GetModule().GetFileSpec()),
            "fileAddress":address.GetFileAddress(),
            "symbolAddress":symbol.GetStartAddress().GetFileAddress() if symbol.IsValid() else None,
            "sourceLine":line.GetLine() if line.IsValid() else None})
    row={"timeNS":time.time_ns(),"label":LABELS.get(location.GetBreakpoint().GetID()),"stack":stack}
    with LOG.open("a") as stream:stream.write(json.dumps(row)+"\\n")
    return False
def register(debugger):
    target=debugger.GetSelectedTarget()
    module=target.AddModule(%r,None,None)
    if not module.IsValid():raise RuntimeError("Pinned debug module not admitted")
    for label,symbol in %r.items():
        bp=target.BreakpointCreateByName(symbol)
        if bp.GetNumLocations()!=1:raise RuntimeError("Expected exactly one original symbol location: "+label)
        LABELS[bp.GetID()]=label
        bp.SetScriptCallbackFunction(__name__+".hit")
    print("ORIGINAL_SYMBOL_LOCATIONS_ADMITTED",json.dumps(LABELS))
''' % (str(work / 'symbol-hits.jsonl'), str(APP / 'PinkhaAnyNative.debug.dylib'), SYMBOLS)


def main():
    assert sys.platform == 'darwin' and os.uname().machine == 'arm64'
    assert not any(os.environ.get(key) for key in ('GITHUB_ACTIONS', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))
    os.umask(0o077)
    work = Path(tempfile.mkdtemp(prefix='native-hierarchy-drop-', dir='/Users/m1/builds/_diagnostics'))
    receipt = {'scope': 'LOCAL_LLDB_DIAGNOSTIC_NOT_PRODUCT_ACCEPTANCE',
        'start': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'localDiagnosticID': str(time.time_ns()), 'originalRun': '45438097556',
        'originalProducerRun': '45425747246', 'originalSource': '95cd30c9e0d70fec368a1605a21b155a652a7afd',
        'originalRuntime': {'version': '27.2', 'build': '24B8117'},
        'appBuilds': 0, 'nativeBuilds': 0, 'uiRunnerBuilds': 0,
        'selectedMethod': TARGET + '/' + SELECTOR, 'productAcceptance': False,
        'controllerSHA256': digest(__file__), 'symbolsSHA256': digest(SYMBOL_FILE),
        'observedPhase': 'SECOND_APP_PROCESS_AFTER_REAL_COLD_REOPEN',
        'automaticSystemDiagnostics': 'never', 'work': str(work)}
    before = None
    udid = None
    ui = None
    debugger = None
    try:
        assert all(digest(path) == expected for path, expected in PINNED.items())
        receipt['pinnedInputs'] = {str(path): expected for path, expected in PINNED.items()}
        before = inventory(PRODUCTS)
        (work / 'original-products.json').write_text(json.dumps(before, sort_keys=True, indent=2) + '\n')
        receipt['originalProductEntries'] = len(before)
        receipt['originalInventorySHA256'] = digest(work / 'original-products.json')
        for bundle in (APP, RUNNER):
            run(['codesign', '--verify', '--deep', '--strict', str(bundle)], timeout=60)
        receipt['originalSignaturesVerified'] = True
        value = relocated(plistlib.loads(DESCRIPTOR.read_bytes()))
        assert [key for key in value if key != '__xctestrun_metadata__'] == [TARGET]
        value[TARGET]['OnlyTestIdentifiers'] = [SELECTOR]
        copied = work / 'hierarchy.xctestrun'
        copied.write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML))
        receipt['copiedDescriptorSHA256'] = digest(copied)
        device_inventory = json.loads(run(['xcrun', 'simctl', 'list', '--json']).stdout)
        devices = [item for item in device_inventory['devicetypes']
                   if item['identifier'] == 'com.apple.CoreSimulator.SimDeviceType.iPad-mini-A17-Pro']
        runtimes = [item for item in device_inventory['runtimes'] if item.get('version') == '27.2'
                    and item.get('buildversion') == '24B8117' and item.get('isAvailable') is True]
        assert len(devices) == len(runtimes) == 1
        name = 'Anytype hierarchy drop diagnostic ' + str(uuid.uuid4())
        udid = run(['xcrun', 'simctl', 'create', name, devices[0]['identifier'], runtimes[0]['identifier']]).stdout.strip()
        assert re.fullmatch('[0-9A-Fa-f-]{36}', udid)
        receipt['ownedSimulator'] = {'name': name, 'udid': udid, 'runtime': runtimes[0]['identifier']}
        (work / 'ownership.json').write_text(json.dumps(receipt, indent=2))
        run(['xcrun', 'simctl', 'boot', udid], timeout=45)
        run(['xcrun', 'simctl', 'bootstatus', udid, '-b'], timeout=150)
        command = ['xcodebuild', 'test-without-building', '-xctestrun', str(copied),
            '-destination', 'platform=iOS Simulator,id=' + udid,
            '-parallel-testing-enabled', 'NO', '-maximum-concurrent-test-simulator-destinations', '1',
            '-collect-test-diagnostics', 'never',
            '-only-testing:' + TARGET + '/' + SELECTOR,
            '-resultBundlePath', str(work / 'hierarchy.xcresult')]
        with (work / 'ui.log').open('wb') as output:
            ui = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                  stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 180
            pid = None
            first_app_pid = None
            while time.monotonic() < deadline and ui.poll() is None:
                rows = run(['ps', '-axo', 'pid=,command=']).stdout.splitlines()
                matches = [line.strip().split(None, 1)[0] for line in rows
                    if ('/Devices/' + udid + '/') in line and '/PinkhaAnyNative.app/PinkhaAnyNative' in line]
                assert len(matches) <= 1, 'Ambiguous owned app process'
                if matches:
                    observed = int(matches[0])
                    if first_app_pid is None:
                        first_app_pid = observed
                        receipt['originalLaunchAppPID'] = observed
                    elif observed != first_app_pid:
                        pid = observed
                        break
                time.sleep(0.1)
            assert pid is not None, 'Second owned App process after cold reopen was not observed'
            receipt['ownedAppPID'] = pid
            module = work / 'hierarchy_trace.py'
            module.write_text(callback_module(work))
            commands = [
                'target create --no-dependents ' + str(APP / 'PinkhaAnyNative'),
                'command script import ' + str(module),
                'script hierarchy_trace.register(lldb.debugger)',
                'process attach --pid ' + str(pid),
                'continue',
                'process detach',
                'quit',
            ]
            script = work / 'observe.lldb'
            script.write_text('\n'.join(commands) + '\n')
            with (work / 'lldb.log').open('wb') as debug_output:
                debugger = subprocess.Popen(['xcrun', 'lldb', '--batch', '--source', str(script)],
                    stdin=subprocess.DEVNULL, stdout=debug_output, stderr=subprocess.STDOUT, start_new_session=True)
                receipt['uiExit'] = ui.wait(timeout=230)
                time.sleep(1)
                receipt['debuggerExitBeforeCleanup'] = debugger.poll()
        result = work / 'hierarchy.xcresult'
        if result.is_dir():
            for kind in ('summary', 'tests'):
                summary = run(['xcrun', 'xcresulttool', 'get', 'test-results', kind,
                               '--path', str(result), '--format', 'json'], timeout=40, check=False)
                (work / (kind + '.json')).write_text(summary.stdout)
                receipt[kind + 'ExtractionExit'] = summary.returncode
    except BaseException as error:
        receipt['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        stop_owned(debugger)
        stop_owned(ui)
        if udid:
            receipt['detachedDiagnosticCleanup'] = stop_owned_diagnostics(work, udid)
            for action in ('shutdown', 'delete'):
                try:
                    receipt[action + 'Exit'] = run(['xcrun', 'simctl', action, udid], timeout=60, check=False).returncode
                except BaseException as error:
                    receipt[action + 'Failure'] = {'type': type(error).__name__, 'message': str(error)}
            remaining_devices = json.loads(run(['xcrun', 'simctl', 'list', 'devices', '--json']).stdout)
            receipt['ownedDeviceAbsent'] = all(item.get('udid') != udid
                for devices in remaining_devices['devices'].values() for item in devices)
        receipt['originalProductsUnchanged'] = before is not None and before == inventory(PRODUCTS)
        receipt['controllerUnchanged'] = (digest(__file__) == receipt['controllerSHA256']
            and digest(SYMBOL_FILE) == receipt['symbolsSHA256'])
        hits = work / 'symbol-hits.jsonl'
        rows = [json.loads(line) for line in hits.read_text().splitlines()] if hits.exists() else []
        receipt['symbolHitCounts'] = {label: sum(row['label'] == label for row in rows) for label in SYMBOLS}
        receipt['symbolEvidenceSHA256'] = digest(hits) if hits.exists() else None
        debug_log = (work / 'lldb.log').read_text(errors='replace') if (work / 'lldb.log').exists() else ''
        receipt['originalBreakpointsAdmitted'] = 'ORIGINAL_SYMBOL_LOCATIONS_ADMITTED' in debug_log
        receipt['secondAppResumedUnderObservation'] = ('Process ' + str(receipt.get('ownedAppPID')) + ' resuming') in debug_log
        receipt['status'] = ('ORIGINAL_DROP_DIAGNOSTIC_COMPLETED_REVIEW_REQUIRED'
            if receipt['originalBreakpointsAdmitted'] and receipt['secondAppResumedUnderObservation']
            and receipt.get('summaryExtractionExit') == 0 and not receipt.get('failure') and receipt.get('deleteExit') == 0
            and receipt.get('ownedDeviceAbsent') and not receipt.get('detachedDiagnosticCleanup', {}).get('remainingOwnedGroups', [None])
            and receipt['originalProductsUnchanged'] and receipt['controllerUnchanged'] else 'DIAGNOSTIC_FAILED')
        receipt['finish'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (work / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))
    return 0 if receipt['status'] == 'ORIGINAL_DROP_DIAGNOSTIC_COMPLETED_REVIEW_REQUIRED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
