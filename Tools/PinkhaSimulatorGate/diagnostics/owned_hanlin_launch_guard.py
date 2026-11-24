"""Observe the original failed SDK UI launch on one owned local Simulator.

This is a local LLDB diagnostic, never CI or product acceptance. It reuses
immutable original App/test products, creates a new disposable native fixture,
and stops its own UI test after observing the production launch guard.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

RETAINED = Path('/Users/m1/builds/_retained-anytype/45423982997-1/build')
OLD = '/Users/m1/builds/actions-anytype/anytype-swift/anytype-swift/build/'
SOURCE = '75bd6d7af18dfd511e85582ce7f994d2801b7703'
PREP = RETAINED / 'sdk06-original-native-derived-45423982997-1/Build/Products/UI27-prepare.xctestrun'
UI = RETAINED / 'sdk06-original-native-derived-45423982997-1-ui/Build/Products/UI27-wave15-hanlin-native.xctestrun'
APP = PREP.parent / 'Debug-Anytype-iphonesimulator/Anytype.app'
OPEN_SYMBOL = '$s7Anytype20PinkhaHanlinLauncher33_96E161B22774096C48BB981B20A68D5DLLC4open10routeOwneryAA28SpaceHubCoordinatorViewModelC_tF'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(argv, *, timeout=30, check=True):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('Command failed: ' + argv[0] + ' ' + str(result.returncode))
    return result


def relocated(value, original_root):
    if isinstance(value, dict):
        return {k: relocated(v, original_root) for k, v in value.items()}
    if isinstance(value, list):
        return [relocated(v, original_root) for v in value]
    if isinstance(value, str):
        return value.replace(OLD, str(RETAINED) + '/').replace('__TESTROOT__', str(original_root))
    return value


def write_descriptor(original, destination, *, environment, preparation):
    value = relocated(plistlib.loads(original.read_bytes()), original.parent)
    if preparation:
        configurations = value['TestConfigurations']
        assert len(configurations) == 1
        selected = [v for v in configurations[0]['TestTargets'] if v['BlueprintName'] == 'AnytypeTests']
        assert len(selected) == 1
        configurations[0]['TestTargets'] = selected
        target = selected[0]
    else:
        target = value['PinkhaStage1AcceptanceUITests']
    target['EnvironmentVariables'].update(environment)
    destination.write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML))
    os.chmod(destination, 0o600)


def owned_process_stop(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def main():
    assert sys.platform == 'darwin' and os.uname().machine == 'arm64'
    os.umask(0o077)
    work = Path(tempfile.mkdtemp(prefix='sdk-ui-launch-guard-', dir='/Users/m1/builds/_diagnostics'))
    local_id = str(time.time_ns())
    receipt = {'scope': 'LOCAL_LLDB_DIAGNOSTIC_NOT_PRODUCT_ACCEPTANCE', 'localDiagnosticID': local_id,
               'originalRun': '45423982997', 'originalAppSource': SOURCE,
               'appBuilds': 0, 'nativeBuilds': 0, 'uiRunnerBuilds': 0, 'sdk23Replayed': False,
               'ack7Replayed': False, 'productAcceptance': False, 'work': str(work)}
    originals = [PREP, UI, APP / 'Anytype', APP / 'Anytype.debug.dylib']
    before = {str(p): digest(p) for p in originals}
    assert before[str(PREP)] == 'decef96cbccc57a42d9debbccb91da4e9ad8b3e9dbc89afbf439a3151fbc2515'
    assert before[str(UI)] == '550a7279b31e0c9a50406b644b650516172e46c17e2bca95bf8b7a54cf9a94b1'
    receipt['originalInputs'] = before
    udid = None
    ui_process = None
    debugger = None
    try:
        inventory = json.loads(run(['xcrun', 'simctl', 'list', '--json']).stdout)
        devices = [v for v in inventory['devicetypes'] if v['name'] == 'iPad Pro 13-inch (M5) (16GB)']
        runtimes = [v for v in inventory['runtimes'] if v.get('version') == '27.0'
                    and v.get('buildversion') == '24A434' and v.get('isAvailable') is True]
        assert len(devices) == len(runtimes) == 1
        name = 'Anytype SDK launch diagnostic ' + str(uuid.uuid4())
        udid = run(['xcrun', 'simctl', 'create', name, devices[0]['identifier'], runtimes[0]['identifier']]).stdout.strip()
        assert re.fullmatch('[0-9A-Fa-f-]{36}', udid)
        receipt['ownedSimulator'] = {'name': name, 'udid': udid, 'runtime': runtimes[0]['identifier']}
        (work / 'ownership.json').write_text(json.dumps(receipt, indent=2))
        run(['xcrun', 'simctl', 'boot', udid], timeout=45)
        run(['xcrun', 'simctl', 'bootstatus', udid, '-b'], timeout=150)
        environment = {'PINKHA_HANLIN_NATIVE_SOURCE_SHA': SOURCE,
                       'PINKHA_HANLIN_NATIVE_RUN_ID': local_id, 'PINKHA_HANLIN_NATIVE_RUN_ATTEMPT': '1',
                       'PINKHA_SIMULATOR_UI_DISPOSABLE': '1'}
        prepare = work / 'prepare.xctestrun'
        write_descriptor(PREP, prepare, environment={**environment,
            'PINKHA_HANLIN_NATIVE_PREPARATION': '1', 'PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION': '1'}, preparation=True)
        def test_command(descriptor, method, result):
            return ['xcodebuild', 'test-without-building', '-xctestrun', str(descriptor),
                    '-destination', 'platform=iOS Simulator,id=' + udid,
                    '-parallel-testing-enabled', 'NO', '-maximum-concurrent-test-simulator-destinations', '1',
                    '-only-testing:' + method, '-resultBundlePath', str(result)]
        with (work / 'prepare.log').open('wb') as log:
            prep_process = subprocess.Popen(test_command(prepare,
                'AnytypeTests/HanlinNativeAcceptancePreparationTests/prepareRealHostFixture', work / 'prepare.xcresult'),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                prep_exit = prep_process.wait(timeout=240)
            finally:
                owned_process_stop(prep_process)
        receipt['prepareExit'] = prep_exit
        assert prep_exit == 0
        container = Path(run(['xcrun', 'simctl', 'get_app_container', udid, 'io.anytype.app', 'data']).stdout.strip())
        fixture_paths = list(container.glob('Library/Application Support/**/pinkha-hanlin-native-fixture.json'))
        assert len(fixture_paths) == 1
        fixture_raw = fixture_paths[0].read_bytes()
        assert 0 < len(fixture_raw) <= 16384
        fixture = json.loads(fixture_raw)
        assert fixture['sourceSHA'] == SOURCE and fixture['runID'] == local_id
        receipt['fixtureSHA256'] = hashlib.sha256(fixture_raw).hexdigest()
        app_path = Path(run(['xcrun', 'simctl', 'get_app_container', udid, 'io.anytype.app', 'app']).stdout.strip())
        run(['xcrun', 'simctl', 'terminate', udid, 'io.anytype.app'], check=False)
        ui = work / 'ui.xctestrun'
        write_descriptor(UI, ui, environment={**environment, 'PINKHA_HANLIN_NATIVE_UI_TESTING': '1',
            'PINKHA_HANLIN_NATIVE_FIXTURE_JSON': fixture_raw.decode()}, preparation=False)
        with (work / 'ui.log').open('wb') as log:
            ui_process = subprocess.Popen(test_command(ui,
                'PinkhaStage1AcceptanceUITests/HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation',
                work / 'ui.xcresult'), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 60
            pid = None
            while time.monotonic() < deadline and ui_process.poll() is None:
                listing = run(['ps', '-axo', 'pid=,command=']).stdout
                matches = [line.strip().split(None, 1)[0] for line in listing.splitlines()
                           if ('/Devices/' + udid + '/') in line and '/Anytype.app/Anytype' in line]
                if len(matches) == 1:
                    pid = int(matches[0]); break
                assert not matches, 'Ambiguous owned app process'
                time.sleep(0.1)
            assert pid is not None, 'Owned App process was not observed'
            receipt['ownedAppPID'] = pid
            commands = [
                'target create ' + str(APP / 'Anytype'),
                'breakpoint set --name ' + OPEN_SYMBOL,
                'process attach --pid ' + str(pid),
                'continue',
                'frame info',
                'frame variable --show-types self',
                'expression --language Swift -- (self.anchor == nil, self.anchor?.viewIfLoaded == nil, self.anchor?.viewIfLoaded?.window == nil, self.anchor?.viewIfLoaded?.window?.windowScene?.activationState.rawValue ?? -999, self.anchor?.viewIfLoaded?.window?.rootViewController == nil, self.anchor?.viewIfLoaded?.window?.rootViewController?.presentedViewController == nil)',
                'expression --language Swift -- self.anchor?.viewIfLoaded?.window?.rootViewController?.description',
                'expression --language Swift -- self.anchor?.viewIfLoaded?.window?.rootViewController?.presentedViewController?.description',
                'process detach', 'quit']
            script = work / 'observe.lldb'; script.write_text('\n'.join(commands) + '\n')
            with (work / 'lldb.log').open('wb') as output:
                debugger = subprocess.Popen(['xcrun', 'lldb', '--batch', '--source', str(script)],
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    receipt['debuggerExit'] = debugger.wait(timeout=120)
                finally:
                    owned_process_stop(debugger)
            receipt['diagnosticObserved'] = 'stop reason = breakpoint' in (work / 'lldb.log').read_text(errors='replace')
            owned_process_stop(ui_process)
            receipt['uiExit'] = ui_process.returncode
    except BaseException as error:
        receipt['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        owned_process_stop(debugger)
        owned_process_stop(ui_process)
        if udid:
            for action in ('shutdown', 'delete'):
                try:
                    receipt[action + 'Exit'] = run(['xcrun', 'simctl', action, udid], timeout=60, check=False).returncode
                except BaseException as error:
                    receipt[action + 'Failure'] = {'type': type(error).__name__, 'message': str(error)}
        after = {str(p): digest(p) for p in originals}
        receipt['originalInputsUnchanged'] = before == after
        receipt['status'] = ('BREAKPOINT_OBSERVED_GUARD_REVIEW_REQUIRED'
            if receipt.get('diagnosticObserved') and not receipt.get('failure')
            and receipt.get('deleteExit') == 0 and receipt['originalInputsUnchanged'] else 'DIAGNOSTIC_FAILED')
        (work / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))
    return 0 if receipt['status'] == 'BREAKPOINT_OBSERVED_GUARD_REVIEW_REQUIRED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
