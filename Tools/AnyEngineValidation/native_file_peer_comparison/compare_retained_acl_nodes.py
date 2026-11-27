#!/usr/bin/env python3
"""Read each private tree node's signed ACL using exact copied retained inputs.

This diagnostic does not join, grant, replay, modify the original database,
change node configuration, or turn a node observation into membership acceptance.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
OUT = ROOT / 'retained-node-grant-comparison1'
PRIOR = ROOT / 'retained-acl-recovery1'
SDK = Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current/source/.runtime-artifacts/sdk-source')
HELPER = ROOT / 'compare_acl_nodes.go'
DEV = Path('/mnt/development/projects/caches/pinkha-w1-acl-node-diagnostic-20261127')
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
SOURCE = Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/resume_linux_filesv2_invite.py')
spec = importlib.util.spec_from_file_location('fv2', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
os.umask(0o077)
OUT.mkdir(exist_ok=False)
started = time.monotonic()
result = {'protocol': 'explicit-private-tree-peer-signed-acl-read-v1', 'status': 'RUNNING',
          'originalAccountProcesses': 0, 'mutatingRPCs': 0, 'grantCalls': 0, 'joinCalls': 0,
          'nodeConfigurationChanged': False, 'membershipAcceptance': False,
          'processes': [], 'errors': []}
expected = None
copy_manifest = None


def save():
    result['seconds'] = round(time.monotonic() - started, 3)
    m.atomic(OUT / 'result.json', result)


def inventory(path):
    return {str(p.relative_to(path)): m.sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def custody():
    return {name: m.account_inventory(ROOT / 'attempt1' / name) for name in ('alice', 'bob')}


def guard():
    root_free = shutil.disk_usage(OUT).free
    dev_free = shutil.disk_usage(CACHE_TARGET).free
    result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes', root_free), root_free)
    result['minimumDevelopmentFreeBytes'] = min(result.get('minimumDevelopmentFreeBytes', dev_free), dev_free)
    assert root_free >= 2 * 1024**3, '2 GiB root emergency floor'
    assert dev_free >= 512 * 1024**2, '512 MiB development emergency floor'
    assert time.monotonic() - started < 300, 'bounded complete diagnostic deadline'
    return root_free, dev_free


def run(label, command, env, cwd, deadline):
    row = {'label': label, 'command': command, 'forcedKill': False}
    result['processes'].append(row)
    begin = time.monotonic()
    log = OUT / (label + '.log')
    with log.open('xb') as stream:
        p = subprocess.Popen(command, env=env, cwd=cwd, stdout=stream,
                             stderr=subprocess.STDOUT, start_new_session=True)
        row.update(pid=p.pid, pgid=p.pid)
        save()
        try:
            while p.poll() is None:
                guard()
                assert log.stat().st_size < 8 * 1024**2, 'bounded diagnostic log'
                assert time.monotonic() - begin < deadline, 'bounded ' + label + ' deadline'
                time.sleep(.2)
        finally:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    row['forcedKill'] = True
                    p.wait(timeout=5)
            row.update(exitCode=p.returncode, seconds=round(time.monotonic() - begin, 3))
            try:
                os.killpg(p.pid, 0)
                row['groupPositivelyAbsent'] = False
            except ProcessLookupError:
                row['groupPositivelyAbsent'] = True
            row['logSHA256'] = m.sha(log)
            save()
    assert row['exitCode'] == 0 and row['groupPositivelyAbsent'] and not row['forcedKill'], label + ' did not close cleanly'
    return log


def interrupted(*_):
    raise RuntimeError('owned explicit-peer diagnostic interrupted')


signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
try:
    result['sourceBefore'] = m.source_admission()
    prior = json.loads(m.pinned(PRIOR / 'result.json', '8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d', 1024**2))
    assert prior['status'] == 'FAIL_RETAINED_ACL_RECOVERY'
    assert prior['error'] == "AssertionError('Reader grant did not materialize')"
    assert prior['grantCalls'] == 1 and prior['grantResponse']['status'] == 204
    assert prior['allOwnedGroupsPositivelyAbsent']
    assert prior['accountInitCalls'] == prior['joinCalls'] == prior['inviteCreateCalls'] == 0
    expected = json.loads(m.pinned(PRIOR / 'private-current-accounts.json', '9e0719b6bf2837c9717de89e61e5d49cf9b7478458e34a2117a61fbf4e95025c', 4 * 1024**2))
    assert custody() == expected
    result['priorGrantReceiptSHA256'] = m.sha(PRIOR / 'result.json')
    result['priorCustodySHA256'] = m.sha(PRIOR / 'private-current-accounts.json')
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
    assert not active, 'retained source account is in use'
    assert CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET
    root_free, dev_free = guard()
    mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    assert root_free >= 2 * 1024**3 + 64 * 1024**2 and dev_free >= 512 * 1024**2 + 384 * 1024**2
    assert mem >= 3 * 1024**3, '3 GiB available memory preflight'
    assert not DEV.exists()
    DEV.mkdir()
    (DEV / 'tmp').mkdir()
    result['resourcePolicy'] = {'rootEmergencyFloor': 2 * 1024**3, 'developmentEmergencyFloor': 512 * 1024**2,
        'rootReserveBytes': 64 * 1024**2, 'developmentReserveBytes': 384 * 1024**2,
        'rootFreeBefore': root_free, 'developmentFreeBefore': dev_free, 'memoryAvailableBefore': mem,
        'productAndTemp': str(DEV), 'cacheResolved': str(CACHE.resolve()), 'workers': 2}
    source_copy = OUT / 'sdk-source'
    original_sdk = inventory(SDK)
    assert len(original_sdk) == 713
    shutil.copytree(SDK, source_copy)
    assert inventory(source_copy) == original_sdk
    main_path = source_copy / 'cmd/retained-acl-node-diagnostic/main.go'
    assert not main_path.exists()
    main_path.parent.mkdir(parents=True)
    shutil.copyfile(HELPER, main_path)
    result['helperSourceSHA256'] = m.sha(main_path)
    result['controllerSHA256'] = m.sha(Path(__file__))
    copy_manifest = inventory(source_copy)
    assert set(copy_manifest) - set(original_sdk) == {'cmd/retained-acl-node-diagnostic/main.go'}
    assert all(copy_manifest[k] == v for k, v in original_sdk.items())
    m.atomic(OUT / 'diagnostic-source-manifest.json', copy_manifest)
    result['diagnosticSourceManifestSHA256'] = m.sha(OUT / 'diagnostic-source-manifest.json')
    aid, sid = prior['accounts']['alice'], prior['spaceId']
    src = ROOT / 'attempt1/alice' / aid / 'sdk/anysync' / (sid + '.db')
    dst = OUT / src.name
    result['copiedDatabaseAndSidecars'] = []
    for suffix in ('', '-wal', '-shm'):
        original = Path(str(src) + suffix)
        if original.exists():
            target = Path(str(dst) + suffix)
            shutil.copyfile(original, target)
            assert m.sha(original) == m.sha(target)
            result['copiedDatabaseAndSidecars'].append({'name': original.name, 'sha256': m.sha(original), 'bytes': original.stat().st_size})
    wallet = ROOT / 'attempt1/alice' / aid / 'wallet.key'
    wallet_row = next(v for v in expected['alice']['rows'] if v['path'] == aid + '/wallet.key')
    m.pinned(wallet, wallet_row['sha256'], 1024**2)
    copied_wallet = OUT / 'wallet.key'
    shutil.copyfile(wallet, copied_wallet)
    assert m.sha(copied_wallet) == wallet_row['sha256'] and custody() == expected
    m.pinned(m.NODECONF, m.NODECONF_SHA, 65536)
    env = os.environ.copy()
    env.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE),
               GOMODCACHE='/root/go/pkg/mod', GOTMPDIR=str(DEV / 'tmp'), TMPDIR=str(DEV / 'tmp'),
               CGO_ENABLED='1', GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off')
    binary = DEV / 'comparer'
    run('build', ['/usr/local/bin/go', 'build', '-p=2', '-o', str(binary), './cmd/retained-acl-node-diagnostic'], env, source_copy, 180)
    result['binarySHA256'] = m.sha(binary)
    log = run('direct-node-read', [str(binary), str(copied_wallet), str(dst), sid, str(m.NODECONF), str(OUT / 'independent-app-state'), aid], env, OUT, 90)
    observations = []
    for line in log.read_text().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get('status') == 'DIRECT_NODE_SIGNED_ACL_DIAGNOSTIC_NOT_MEMBERSHIP_ACCEPTANCE':
            observations.append(value)
    assert len(observations) == 1
    observed = observations[0]
    result['comparison'] = observed
    assert observed['account'] == aid and observed['space'] == sid and observed['mutatingRPCs'] == 0
    assert len(observed['nodes']) == 3 and len({n['requestedPeerID'] for n in observed['nodes']}) == 3
    assert observed['local']['count'] == 4 and observed['local']['head'] == 'bafyreig7uw2qjb4alanirk3cqg64gujdwyuuwcgaehtwcqa6xv2ed2gx5u'
    assert all(n['signedChainValidated'] and n['sameACLRoot'] for n in observed['nodes'])
    result['status'] = 'OBSERVED_ALL_THREE_NODE_SIGNED_CHAINS_NOT_MEMBERSHIP_ACCEPTANCE'
except BaseException as error:
    result.update(status='FAIL_EXPLICIT_NODE_DIAGNOSTIC', error=repr(error))
finally:
    try:
        result['sourceAfter'] = m.source_admission()
        assert result['sourceAfter'] == result['sourceBefore']
        result['originalAccountsUnchanged'] = expected is not None and custody() == expected
        assert result['originalAccountsUnchanged']
    except BaseException as error:
        result['status'] = 'FAIL_EXPLICIT_NODE_DIAGNOSTIC'
        result['errors'].append({'retainedIntegrity': repr(error)})
    try:
        result['diagnosticSourceUnchanged'] = copy_manifest is not None and inventory(OUT / 'sdk-source') == copy_manifest
        assert result['diagnosticSourceUnchanged']
    except BaseException as error:
        result['status'] = 'FAIL_EXPLICIT_NODE_DIAGNOSTIC'
        result['errors'].append({'diagnosticSourceIntegrity': repr(error)})
    result['allOwnedGroupsPositivelyAbsent'] = all(p.get('groupPositivelyAbsent', False) for p in result['processes'])
    if not result['allOwnedGroupsPositivelyAbsent']:
        result['status'] = 'FAIL_EXPLICIT_NODE_DIAGNOSTIC'
    save()
    print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'OBSERVED_ALL_THREE_NODE_SIGNED_CHAINS_NOT_MEMBERSHIP_ACCEPTANCE' else 1)
