#!/usr/bin/env python3
"""Continue the original recipient after all three nodes expose its signed grant."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
OUT = ROOT / 'retained-recipient-continuation1'
PRIOR = ROOT / 'retained-acl-recovery1'
BUILD = ROOT / 'acl-refresh-native1'
REPO = Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec = importlib.util.spec_from_file_location('fv2', REPO / 'resume_linux_filesv2_invite.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
os.umask(0o077)
OUT.mkdir(exist_ok=False)
START = time.monotonic()
children = []
known_absent = set()
expected_custody = None
result = {'protocol': 'original-pending-recipient-signed-grant-continuation-v1', 'status': 'RUNNING',
          'accountInitCalls': 0, 'joinCalls': 0, 'grantCalls': 0, 'inviteCreateCalls': 0,
          'attachmentCalls': 0, 'originalOwnerOpened': False, 'actualFilesV2Acceptance': False,
          'processes': [], 'readerObservations': [], 'deniedWriteAttempts': [], 'errors': []}


def save():
    result['seconds'] = round(time.monotonic() - START, 3)
    m.atomic(OUT / 'result.json', result)


def guard():
    free = shutil.disk_usage(OUT).free
    result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes', free), free)
    assert free >= 2 * 1024**3, '2 GiB root emergency floor'
    assert time.monotonic() - START < 240, 'bounded original-recipient continuation'
    assert not (OUT / 'abort').exists(), 'owned continuation abort'


def interrupted(*_):
    raise RuntimeError('owned original-recipient continuation interrupted')


signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)


def native_inventory():
    manifest = json.loads(m.pinned(BUILD / 'source-manifest.json', '44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68', 4 * 1024**2))['files']
    actual = {str(p.relative_to(BUILD / 'source')): {'sha256': m.sha(p), 'bytes': p.stat().st_size}
              for p in (BUILD / 'source').rglob('*') if p.is_file()}
    assert actual == manifest
    assert m.sha(BUILD / 'any') == '79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857'
    return {'sourceManifestSHA256': m.sha(BUILD / 'source-manifest.json'), 'sourceFiles': len(actual),
            'binarySHA256': m.sha(BUILD / 'any')}


def req(child, path, method='GET', body=None, headers=None):
    guard()
    assert child['p'].poll() is None
    request = urllib.request.Request(child['base'] + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=8) as reply:
            raw = reply.read(1048577)
            assert len(raw) <= 1048576
            return {'status': reply.status, 'value': json.loads(raw) if raw else None}
    except urllib.error.HTTPError as error:
        raw = error.read(65537)
        assert len(raw) <= 65536
        return {'status': error.code, 'value': json.loads(raw) if raw else None}


def absent(pid):
    if pid in known_absent:
        return True
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        known_absent.add(pid)
        return True
    return False


def stop(child):
    p, row = child['p'], child['row']
    if row.get('closed'):
        return
    try:
        if p.poll() is None and not absent(p.pid):
            os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            if not absent(p.pid):
                os.killpg(p.pid, signal.SIGKILL)
                row['forcedKill'] = True
            p.wait(timeout=5)
        row['exitCode'] = p.returncode
        row['groupPositivelyAbsent'] = absent(p.pid)
        assert p.returncode == 0 and row['groupPositivelyAbsent'] and not row.get('forcedKill', False), 'native clean-close failure'
    finally:
        child['stream'].close()
        row['logSHA256'] = m.sha(Path(row['log']))
        row['closed'] = p.poll() is not None and absent(p.pid)
        save()


def start(label, offline=False):
    guard()
    assert m.sha(BUILD / 'any') == result['nativeBefore']['binarySHA256']
    data = ROOT / 'attempt1/bob'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    command = [str(BUILD / 'any'), 'run', '--config', str(OUT / 'config.yml'), '--data-dir', str(data), '--addr', '127.0.0.1:' + str(port)]
    if offline:
        m.pinned(m.OFFLINE, m.OFFLINE_SHA, 65536)
        command = ['/usr/bin/python3', '-B', str(m.OFFLINE), '--exec'] + command
    stream = (OUT / (label + '.log')).open('xb')
    env = {k: v for k, v in os.environ.items() if not k.startswith('ANY_')}
    env.update(ANY_DATA_DIR=str(data), GOMAXPROCS='2', GOMEMLIMIT='512MiB')
    p = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    row = {'label': label, 'pid': p.pid, 'pgid': p.pid, 'command': command, 'offline': offline,
           'log': str(OUT / (label + '.log')), 'forcedKill': False}
    child = {'p': p, 'row': row, 'stream': stream, 'base': 'http://127.0.0.1:' + str(port)}
    children.append(child)
    result['processes'].append(row)
    save()
    end = time.monotonic() + 45
    while True:
        guard()
        assert p.poll() is None, 'native startup exited'
        try:
            if req(child, '/v1/health')['status'] == 200:
                break
        except (OSError, urllib.error.URLError):
            pass
        assert time.monotonic() < end, 'native readiness timeout'
        time.sleep(.25)
    response = req(child, '/v1/account')
    assert response['status'] == 200 and response['value']['id'] == accounts['bob']
    if offline:
        fields = dict(line.split(':', 1) for line in (Path('/proc') / str(p.pid) / 'status').read_text().splitlines() if ':' in line)
        assert fields['NoNewPrivs'].strip() == '1' and fields['Seccomp'].strip() == '2'
        assert (Path('/proc') / str(p.pid) / 'exe').resolve() == BUILD / 'any'
        row.update(actualInheritedNoNewPrivs=1, actualInheritedSeccomp=2)
    return child


def reader(child, seconds):
    end = time.monotonic() + seconds
    while True:
        response = req(child, prefix + '/members/me')
        result['readerObservations'].append({'phase': child['row']['label'], 'seconds': round(time.monotonic() - START, 3), **response})
        save()
        if response['status'] == 200:
            value = response['value']
            assert value['identity'] == accounts['bob'] and value['status'] == 'active' and value['permission'] == 'reader'
            return value
        assert response['status'] == 409 and response['value']['error']['code'] == 'space.not_accepted'
        assert time.monotonic() < end, 'existing signed grant still not materialized'
        time.sleep(.4)


def denied_write(child):
    response = req(child, prefix + '/objects/' + oid + '/files?name=denied-original-reader-continuation.bin',
                   'POST', b'owned Reader denial fixture', {'Content-Type': 'application/octet-stream'})
    result['deniedWriteAttempts'].append({'phase': child['row']['label'], **response})
    assert response['status'] == 403 and response['value']['error']['code'] in ('space.read_only', 'acl.forbidden')


try:
    guard()
    assert shutil.disk_usage(OUT).free >= 2 * 1024**3 + 128 * 1024**2
    result['sourceBefore'] = m.source_admission()
    result['nativeBefore'] = native_inventory()
    prior = json.loads(m.pinned(PRIOR / 'result.json', '8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d', 1024**2))
    assert prior['status'] == 'FAIL_RETAINED_ACL_RECOVERY' and prior['grantCalls'] == 1
    assert prior['grantResponse']['status'] == 204 and prior['allOwnedGroupsPositivelyAbsent']
    expected_custody = json.loads(m.pinned(PRIOR / 'private-current-accounts.json', '9e0719b6bf2837c9717de89e61e5d49cf9b7478458e34a2117a61fbf4e95025c', 4 * 1024**2))
    for name in ('alice', 'bob'):
        assert m.account_inventory(ROOT / 'attempt1' / name) == expected_custody[name]
    observed = json.loads(m.pinned(ROOT / 'retained-node-grant-comparison1/result.json', 'b4ea294a8090cd867bae1246a635d0afba8a48e12ee073a9362f2598591321c6', 1024**2))
    assert observed['status'] == 'OBSERVED_ALL_THREE_NODE_SIGNED_CHAINS_NOT_MEMBERSHIP_ACCEPTANCE'
    assert observed['originalAccountsUnchanged'] and observed['allOwnedGroupsPositivelyAbsent']
    assert all(n['signedChainValidated'] and n['sameACLRoot'] and n['sameHead'] and n['acl']['count'] == 4 for n in observed['comparison']['nodes'])
    accounts, sid, oid = prior['accounts'], prior['spaceId'], prior['objectId']
    prefix = '/v1/spaces/' + sid
    assert observed['comparison']['account'] == accounts['alice'] and observed['comparison']['space'] == sid
    result.update(accounts=accounts, spaceId=sid, objectId=oid, priorGrantReceiptSHA256=m.sha(PRIOR / 'result.json'),
                  priorCustodySHA256=m.sha(PRIOR / 'private-current-accounts.json'), nodeReadReceiptSHA256=m.sha(ROOT / 'retained-node-grant-comparison1/result.json'))
    active = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            args = (proc / 'cmdline').read_bytes()
            if any(str(ROOT / 'attempt1' / name).encode() in args for name in ('alice', 'bob')):
                active.append(int(proc.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    assert not active, 'original account currently in use'
    m.pinned(m.NODECONF, m.NODECONF_SHA, 65536)
    (OUT / 'config.yml').write_bytes(m.pinned(PRIOR / 'config.yml', prior['configSHA256'], 65536))
    (OUT / 'controller.py').write_bytes(Path(__file__).read_bytes())
    result['controllerSHA256'] = m.sha(OUT / 'controller.py')
    accepted_offline = json.loads(m.pinned(ROOT / 'production-lan-files2/result.json', 'c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692', 1024**2))['offlinePolicy']
    assert accepted_offline['helperSHA256'] == m.OFFLINE_SHA
    assert accepted_offline['actual']['tcpDenied'] and accepted_offline['actual']['udpDenied'] and accepted_offline['actual']['seccompFilterActive'] and accepted_offline['actual']['noNewPrivileges']
    result['offlineControlEvidenceReused'] = {'receiptSHA256': 'c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692', 'policy': accepted_offline, 'freshProbeRerun': False, 'freshNativeSeccompFlagsRequired': True}
    online = start('bob-existing-grant-online')
    result['activeReaderOnline'] = reader(online, 90)
    result['onlineSync'] = req(online, prefix + '/sync-status')
    denied_write(online)
    stop(online)
    offline = start('bob-existing-grant-offline', offline=True)
    result['activeReaderOffline'] = reader(offline, 15)
    sync = req(offline, prefix + '/sync-status')
    assert sync['status'] == 200
    assert sync['value']['networkPeers'] == sync['value']['localPeers'] == sync['value']['globalPeers'] == 0
    result['offlineSync'] = sync
    denied_write(offline)
    stop(offline)
    assert len(children) == 2 and len({c['p'].pid for c in children}) == 2
    result['status'] = 'PASS_ORIGINAL_RECIPIENT_EXISTING_GRANT_AND_COLD_READER_AUTHORITY'
except BaseException as error:
    result.update(status='FAIL_ORIGINAL_RECIPIENT_CONTINUATION', error=repr(error))
finally:
    for child in reversed(children):
        try:
            stop(child)
        except BaseException as error:
            result['status'] = 'FAIL_ORIGINAL_RECIPIENT_CONTINUATION'
            result['errors'].append({'cleanup': repr(error)})
    result['allOwnedGroupsPositivelyAbsent'] = all(c['row'].get('groupPositivelyAbsent', False) for c in children)
    if result['status'].startswith('PASS') and not (len(children) == 2 and result['allOwnedGroupsPositivelyAbsent'] and all(c['row']['exitCode'] == 0 and not c['row']['forcedKill'] for c in children)):
        result['status'] = 'FAIL_ORIGINAL_RECIPIENT_CONTINUATION'
    try:
        result['sourceAfter'] = m.source_admission()
        result['nativeAfter'] = native_inventory()
        assert result['sourceBefore'] == result['sourceAfter'] and result['nativeBefore'] == result['nativeAfter']
        assert result['allOwnedGroupsPositivelyAbsent']
        current = {name: m.account_inventory(ROOT / 'attempt1' / name) for name in ('alice', 'bob')}
        assert expected_custody is not None and current['alice'] == expected_custody['alice']
        assert {name: m.account_inventory(ROOT / 'attempt1' / name) for name in ('alice', 'bob')} == current
        m.atomic(OUT / 'private-current-accounts.json', current)
        result['finalAccountInventorySHA256'] = m.sha(OUT / 'private-current-accounts.json')
        result['unopenedOwnerUnchanged'] = True
    except BaseException as error:
        result['status'] = 'FAIL_ORIGINAL_RECIPIENT_CONTINUATION'
        result['errors'].append({'finalCustody': repr(error)})
    save()
    print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'PASS_ORIGINAL_RECIPIENT_EXISTING_GRANT_AND_COLD_READER_AUTHORITY' else 1)
