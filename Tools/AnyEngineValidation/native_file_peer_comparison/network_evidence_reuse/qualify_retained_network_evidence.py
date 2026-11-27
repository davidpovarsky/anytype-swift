#!/usr/bin/env python3
"""Read-only audit of retained T2 results and the explicit current source delta.

This does not execute a native peer, compiler, test, account, or network request.
Raw native logs and account files stay in their original private archives.
"""
import argparse
import hashlib
import json
import os
import tarfile
import time
from pathlib import Path

MIXED = Path('/mnt/development/projects/evidence/pinkha-t2-mixed-originals-retained-20261126')
FIXED = Path('/mnt/development/projects/evidence/pinkha-t2-fixed-originals-retained-20261126')
P2P = Path('/var/lib/pinkha-root-t2-linux-20261126/p2p-cold-originals1')
BASE = Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current')
CURRENT = Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 ** 2), b''):
            h.update(data)
    return h.hexdigest()


def pinned_json(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected, str(path)
    return json.loads(raw)


def archive_rows(root, archive, archive_sha, index, index_sha, wanted):
    index_value = pinned_json(root / index, index_sha)
    entries = ({row['path']: row for row in index_value}
               if isinstance(index_value, list) else index_value)
    path = root / archive
    before = path.stat()
    assert sha(path) == archive_sha
    selected = {}
    # Streaming reads; no member is extracted to the filesystem.
    with tarfile.open(path, 'r|gz') as bundle:
        for member in bundle:
            name = member.name[2:] if member.name.startswith('./') else member.name
            if name not in wanted:
                continue
            assert name not in selected and member.isfile()
            assert 0 < member.size < 2 * 1024 ** 2
            with bundle.extractfile(member) as stream:
                raw = stream.read(2 * 1024 ** 2 + 1)
            assert len(raw) == entries[name]['bytes'] == member.size
            assert digest(raw) == entries[name]['sha256']
            selected[name] = raw
    after = path.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    assert set(selected) == set(wanted)
    return selected, {'path': str(path), 'sha256': archive_sha,
                      'bytes': before.st_size, 'inventorySHA256': index_sha,
                      'selectedOriginalMembersVerified': len(selected)}


def terminal_methods(raw):
    terminals = {}
    for line in raw.splitlines():
        event = json.loads(line)
        if event.get('Test') and event.get('Action') in ('pass', 'fail', 'skip'):
            assert event['Test'] not in terminals
            terminals[event['Test']] = {'status': event['Action'],
                                        'elapsed': event.get('Elapsed')}
    return terminals


def proof(rows, prefix, accepted_suffixes, expected_count):
    receipt_name = prefix + '/RESULT.json'
    log_name = prefix + '/original-go-test.jsonl'
    receipt = json.loads(rows[receipt_name])
    terminals = terminal_methods(rows[log_name])
    assert receipt['logSHA256'] == digest(rows[log_name])
    assert receipt['tests'] == terminals
    assert receipt['sourceAfterVerified'] is True
    assert receipt['forcedNativeStops'] == 0
    accepted = {name: item for name, item in terminals.items()
                if any(name.endswith('_' + suffix) for suffix in accepted_suffixes)}
    assert len(accepted) == expected_count
    assert all(item['status'] == 'pass' for item in accepted.values())
    return {'receiptMember': receipt_name, 'receiptSHA256': digest(rows[receipt_name]),
            'originalRunStatus': receipt['status'], 'originalExitCode': receipt['exitCode'],
            'originalPassed': receipt['passed'], 'originalFailed': receipt['failed'],
            'originalSkipped': receipt['skipped'], 'logMember': log_name,
            'logSHA256': digest(rows[log_name]), 'acceptedMethods': accepted,
            'otherOriginalMethodResults': {name: item for name, item in terminals.items()
                                           if name not in accepted},
            'new': receipt.get('new'), 'old': receipt.get('old'),
            'sourceAfterVerifiedByOriginalController': True,
            'originalForcedNativeStops': 0,
            'originalGroupAbsent': receipt.get('ownedGroupAbsent'),
            'originalGroupRemaining': receipt.get('ownedGroupRemaining')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    started = time.monotonic()
    first_prefixes = ['mixed-invite-network-recovery-attempt1',
                      'mixed-network-remaining-attempt1']
    first_wanted = [prefix + '/' + name for prefix in first_prefixes
                    for name in ('RESULT.json', 'original-go-test.jsonl')]
    qualification_name = first_prefixes[0] + '/process-observation-qualification.json'
    first_wanted.append(qualification_name)
    first, first_archive = archive_rows(
        MIXED, 'original-t2-mixed-build-and-executions.tar.gz',
        '8999a6a781ae416050c828e48b0d0d72e7b85e7f62511459f66a49d0d8ca0d7d',
        'members.json', '9d1c291f873a2d1719e660a2d7e30e5eb0d1971df5abf2072b21054c4ba095a0', first_wanted)
    second_prefixes = ['original-failures/mixed-remote-authority-attempt1',
                       'fixed-permission/mixed-fixed-authority-attempt1']
    second_wanted = [prefix + '/' + name for prefix in second_prefixes
                     for name in ('RESULT.json', 'original-go-test.jsonl')]
    second, second_archive = archive_rows(
        FIXED, 't2-fixed-originals-private.tar.gz',
        'eb56b9e55ef24aa87e6d732f36d112f9e7cbb1adca29309dc66d80b1cc2eb546',
        'inventory.json', '52ab4da287fcd19a6abd3aa2481e6523bbf056343d1c9acb10f410102f42517a', second_wanted)
    invite = proof(first, first_prefixes[0], ['InviteAccept'], 2)
    assert invite['originalRunStatus'] == 'FAIL' and invite['originalExitCode'] == 0
    qualification = json.loads(first[qualification_name])
    assert qualification['originalResultSHA256'] == invite['receiptSHA256']
    assert qualification['originalLogSHA256'] == invite['logSHA256']
    assert qualification['nativeGroupAbsentByKernelESRCH'] is True
    assert qualification['newTestInvocations'] == 0
    assert qualification['passed'] == 2 and qualification['failed'] == qualification['skipped'] == 0
    invite['separateProcessQualification'] = {'member': qualification_name,
                                            'sha256': digest(first[qualification_name]),
                                            'status': qualification['status'],
                                            'newTestInvocations': 0,
                                            'nativeGroupAbsentByKernelESRCH': True}
    remaining = proof(first, first_prefixes[1],
                      ['CRDTConvergence', 'PermissionChange', 'StopSharing', 'OverviewConcurrentEdits'], 8)
    assert remaining['originalGroupRemaining'] is False
    refusals = proof(second, second_prefixes[0], ['InviteRefusals'], 2)
    assert refusals['originalRunStatus'] == 'FAIL' and refusals['originalFailed'] == 2
    assert refusals['originalGroupRemaining'] is False
    authority = proof(second, second_prefixes[1], ['RemoteRoleEnforcement'], 2)
    assert authority['originalGroupAbsent'] is True and authority['originalFailed'] == 0
    p2p_raw = (P2P / 'RESULT.json').read_bytes()
    assert digest(p2p_raw) == '13931e7aba8941b0d71113626ec9349e3495cd99ba1cc1bc79723b81e3cd410f'
    p2p = json.loads(p2p_raw)
    p2p_log = (P2P / 'original-go-test.jsonl').read_bytes()
    assert digest(p2p_log) == p2p['logSHA256'] == '55eb7f90b4c7214b645c5583c45218ac55ab9074853a86a0c1056575b0c607dd'
    assert terminal_methods(p2p_log) == p2p['tests']
    assert p2p['passed'] == 2 and p2p['failed'] == p2p['skipped'] == p2p['forcedNativeStops'] == 0
    assert p2p['ownedGroupAbsent'] and p2p['sourceAfterVerified'] and p2p['exitCode'] == 0
    assert sha(P2P / 'qualification.json') == p2p['qualificationSHA256']
    base_manifest = pinned_json(BASE / 'source-manifest.json',
        '12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c')
    current_manifest = pinned_json(CURRENT / 'source-manifest.json',
        'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a')
    def normalized(value):
        return {name: {'bytes': item['bytes'], 'sha256': item['sha256']}
                for name, item in value['files'].items()}
    base, current = normalized(base_manifest), normalized(current_manifest)
    delta = [{'path': name, 'before': base.get(name), 'after': current.get(name)}
             for name in sorted(base.keys() | current.keys()) if base.get(name) != current.get(name)]
    expected_delta = {
        '.runtime-artifacts/sdk-source/internal/anysyncx/' + name
        for name in ['aclrefresh.go', 'aclrefresh_test.go', 'peermanager.go', 'peerprogress.go', 'peerprogress_test.go']}
    expected_delta |= {'.runtime-artifacts/sdk-source/internal/spaceimpl/' + name
                       for name in ['members.go', 'members_refresh.go']}
    assert {item['path'] for item in delta} == expected_delta
    assert len(base) == 1594 and len(current) == 1599
    current_binary_sha = sha(CURRENT / 'any')
    assert current_binary_sha == '0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07'
    for item in delta:
        assert sha(CURRENT / 'source' / item['path']) == item['after']['sha256']
    network_names = set(invite['acceptedMethods']) | set(remaining['acceptedMethods']) | set(refusals['acceptedMethods'])
    assert len(network_names) == 12
    report = {
        'protocol': 'pinkha-retained-t2-evidence-source-delta-v1',
        'status': 'PASS_READ_ONLY_RETAINED_EVIDENCE_AUDIT_NOT_NEW_NATIVE_ACCEPTANCE',
        'newNativeRuns': 0, 'newTestInvocations': 0, 'newCompilers': 0,
        'accountsOpened': 0, 'sourceEdits': 0, 'rawPrivateLogsPublished': False,
        'archives': [first_archive, second_archive],
        'historicalNetworkMethodCount': 12, 'historicalAuthorityMethodCount': 2,
        'historicalLinuxP2PMethodCount': 2,
        'retainedNetworkProofs': [invite, remaining, refusals],
        'retainedAuthorityProof': authority,
        'retainedLinuxP2PProof': {'path': str(P2P), 'receiptSHA256': digest(p2p_raw),
             'originalRunStatus': p2p['status'], 'logSHA256': p2p['logSHA256'],
             'qualificationSHA256': p2p['qualificationSHA256'],
             'binaries': p2p['binaries'], 'acceptedMethods': p2p['tests'],
             'originalForcedNativeStops': 0, 'originalGroupAbsent': True},
        'sourceBoundary': {'baseManifestSHA256': sha(BASE / 'source-manifest.json'),
             'baseFiles': len(base), 'currentManifestSHA256': sha(CURRENT / 'source-manifest.json'),
             'currentFiles': len(current), 'delta': delta,
             'allOriginalFilesOutsideDeltaMatchManifests': all(base[name] == current.get(name)
                                                           for name in base if name not in expected_delta),
             'sameSourceClaimForOldNetworkRuns': False,
             'currentNativeBinarySHA256': current_binary_sha},
        'limits': ['Historical passes retain their original versions and platforms.',
                   'The current transport/membership delta has separate signed-ACL, focused peer and original-file native receipts.',
                   'No current mixed-version rerun, current file-revocation acceptance, Apple UI, Heart/Any compatibility or full release acceptance is claimed.'],
        'controllerSHA256': sha(Path(__file__)), 'seconds': round(time.monotonic() - started, 3)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'path': str(args.output),
                      'sha256': sha(args.output), 'networkMethods': 12,
                      'authorityMethods': 2, 'linuxP2PMethods': 2,
                      'newTestInvocations': 0, 'sourceDeltaFiles': len(delta)}))


if __name__ == '__main__':
    main()
