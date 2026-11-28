#!/usr/bin/env python3
"""Stage one exact Bookmark6 input packet, then exec its fixed reviewed command.

This is inert without an explicit recorded coordination story. The story is
evidence of external scheduling, never an authority granted by this script.
Failure retains the partial owned directory and never retries or overwrites it.
"""
from pathlib import Path
import argparse
import base64
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import traceback

sys.dont_write_bytecode = True
ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-inputs-14e9844ac5959bb7.json.gz')
PAYLOAD_SHA = '14e9844ac5959bb70537d4b366c9a64cc7f7f9f955c7ccb5b28ed2ae52b60a23'
RAW_SHA = '8d37c7881f66b902f7f7c137a981eff1e2073e627b9e2739ee96d6c149aeef2e'
PACKET_SHA = '2341bdb226521d368b37f37c402c83b6bb20ae1db6efe4d7f65938198f5f1353'
CONTROLLER_SHA = '3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c'
CRYPTO_SHA = '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'
EXEC_ARGV = ['/usr/bin/python3', '-B', str(ROOT / 'inputs/run_component.py'), '--execute-reviewed-candidate']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def physical(path):
    assert path.resolve(strict=True) == path and not path.is_symlink(), str(path)


def budget():
    root_free = shutil.disk_usage('/').free
    dev_free = shutil.disk_usage(ROOT.parent).free
    assert root_free >= 2 * 1024**3 + 32 * 1024**2, 'Original root admission floor'
    assert dev_free >= 512 * 1024**2 + 256 * 1024**2 + 32 * 1024**2, 'Original Development admission'
    return {'atUTC': now(), 'rootFreeBytes': root_free, 'developmentFreeBytes': dev_free}


def mkdir_owned(path):
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    physical(path)
    st = path.stat()
    assert stat.S_IMODE(st.st_mode) == 0o700 and st.st_uid == os.geteuid(), str(path)


def crypto_sources(raw):
    # Read only the exact retained102 dependency rows. Their documented historical
    # aliases are read-only references; no alias is admitted in the new input tree.
    assert sha(raw) == CRYPTO_SHA
    closure = json.loads(raw)
    assert len(closure['files']) == 102
    observations = []
    for row in closure['files']:
        assert row['kind'] in ('swift-import', 'c-header-or-module-map', 'aggregated-link-object')
        source = Path(row['freshCopySourcePath'])
        original = Path(row['originalManifestPath'])
        alias = Path(row['actualOriginalPackageLinkerPath'] if row['kind'] == 'aggregated-link-object'
                     else row['recordedHistoricalAliasPath'])
        assert alias.resolve(strict=True) == original.resolve(strict=True), 'Retained dependency alias changed'
        item = {'kind': row['kind'], 'relativePath': row['relativePath'],
                'bytes': row['bytes'], 'sha256': row['sha256'], 'alias': str(alias), 'physicalFiles': []}
        for path in (source, original):
            physical(path)
            before = path.stat()
            assert stat.S_ISREG(before.st_mode) and before.st_size == row['bytes'], str(path)
            data = path.read_bytes()
            after = path.stat()
            identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_nlink)
            assert identity(before) == identity(after), 'Dependency changed while reading: ' + str(path)
            assert len(data) == row['bytes'] and sha(data) == row['sha256'], str(path)
            item['physicalFiles'].append({'path': str(path), 'identity': identity(after)})
        observations.append(item)
    assert sum(row['bytes'] for row in closure['files']) == 19775715
    return {'manifestSHA256': CRYPTO_SHA, 'files': 102, 'logicalPayloadBytes': 19775715,
            'physicalSourceAndAliasCustodySHA256': sha(json.dumps(observations, sort_keys=True).encode()),
            'readOnly': True, 'copiesCreated': 0, 'atimePreservationClaim': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coordination-story', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9]{16}', args.coordination_story), 'Exact scheduling story required'
    receipt = {'schema': 'pinkha-bookmark6-input-materialization-receipt/v1',
               'status': 'FAIL_NOT_EXECUTED', 'startedAtUTC': now(),
               'coordinationStory': args.coordination_story, 'slotGrantedByThisScript': False,
               'root': str(ROOT), 'payload': str(PAYLOAD), 'payloadSHA256': PAYLOAD_SHA,
               'packetSHA256': PACKET_SHA, 'controllerSHA256': CONTROLLER_SHA,
               'productSourceCommit': '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3',
               'inputAuthority': 'Exact packet/controller hashes; published preparation binding is external, never inferred from the product commit.',
               'rootRunnerReviewSHA256': '4e829323bf17271712bfbb8696ed832d621be8ca3a6e794c2bcae5b21d44e8f0',
               'createdFiles': [], 'runtimeExecuted': False, 'errors': []}
    try:
        physical(ROOT.parent)
        assert ROOT.parent.is_dir()
        assert not ROOT.exists() and not ROOT.is_symlink(), 'Never reuse an existing attempt'
        receipt['before'] = budget()
        physical(PAYLOAD)
        before = PAYLOAD.stat()
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == 389854
        packed = PAYLOAD.read_bytes()
        after = PAYLOAD.stat()
        assert (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
        assert len(packed) == 389854 and sha(packed) == PAYLOAD_SHA
        raw = gzip.decompress(packed)
        assert len(raw) == 1839657 and sha(raw) == RAW_SHA
        payload = json.loads(raw)
        assert set(payload) == {'schema', 'packetBase64', 'entries'}
        assert payload['schema'] == 'pinkha-bookmark6-fixed-input-materialization/v1'
        packet_raw = base64.b64decode(payload['packetBase64'], validate=True)
        assert sha(packet_raw) == PACKET_SHA
        packet = json.loads(packet_raw)
        assert packet['futureFixedRoot'] == str(ROOT) and packet['productCommit'] == '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'
        assert packet['runtimeReady'] is False and packet['runtimeSlotGranted'] is False
        assert packet['fileCount'] == len(packet['files']) == len(payload['entries']) == 90
        assert packet['bytes'] == 1344177
        expected = {'inputs/' + item['path']: item for item in packet['files']}
        assert len(expected) == 90
        decoded = {}
        for entry in payload['entries']:
            assert set(entry) == {'path', 'contentBase64'}
            relative = Path(entry['path'])
            assert not relative.is_absolute() and '..' not in relative.parts and relative.parts[0] == 'inputs'
            assert relative.as_posix() == entry['path'] and entry['path'] in expected and entry['path'] not in decoded
            data = base64.b64decode(entry['contentBase64'], validate=True)
            row = expected[entry['path']]
            assert len(data) == row['bytes'] and sha(data) == row['sha256']
            decoded[entry['path']] = data
        assert set(decoded) == set(expected) and sum(map(len, decoded.values())) == 1344177
        assert sha(decoded['inputs/run_component.py']) == CONTROLLER_SHA
        receipt['cryptoBefore'] = crypto_sources(decoded['inputs/retained-crypto-closure.json'])
        mkdir_owned(ROOT)
        for name, data in sorted(decoded.items()):
            relative = Path(name)
            parent = ROOT
            for part in relative.parent.parts:
                parent = parent / part
                if not parent.exists():
                    mkdir_owned(parent)
                physical(parent)
                assert parent.is_dir() and parent.stat().st_uid == os.geteuid() and stat.S_IMODE(parent.stat().st_mode) == 0o700
            target = ROOT / relative
            with target.open('xb') as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            physical(target)
            st = target.stat()
            assert st.st_nlink == 1 and st.st_uid == os.geteuid() and stat.S_IMODE(st.st_mode) == 0o600
            assert target.read_bytes() == data
            receipt['createdFiles'].append({'path': str(target), 'bytes': len(data), 'sha256': sha(data)})
        actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
        assert actual == set(expected) and all(not p.is_symlink() for p in ROOT.rglob('*'))
        assert set(p.name for p in ROOT.iterdir()) == {'inputs'}
        receipt['cryptoAfter'] = crypto_sources(decoded['inputs/retained-crypto-closure.json'])
        assert receipt['cryptoAfter'] == receipt['cryptoBefore'], 'Original dependency custody changed during staging'
        receipt['after'] = budget()
        os.chdir(ROOT)
        os.environ['PWD'] = str(ROOT)
        assert Path.cwd() == ROOT and os.environ['PWD'] == str(ROOT)
        receipt['launchCwd'] = str(Path.cwd())
        receipt['launchPWD'] = os.environ['PWD']
        receipt['status'] = 'PASS_EXACT_INPUTS_MATERIALIZED_PENDING_EXEC'
        receipt['nextExecArgv'] = EXEC_ARGV
    except BaseException:
        receipt['errors'].append(traceback.format_exc())
        raise
    finally:
        receipt['finishedAtUTC'] = now()
        print(json.dumps(receipt, sort_keys=True), flush=True)
    # Replace this tool-launched interpreter; no extra controller child or group.
    # The fixed reviewed driver owns its single Swift process and original cleanup.
    os.execv(EXEC_ARGV[0], EXEC_ARGV)


if __name__ == '__main__':
    main()
