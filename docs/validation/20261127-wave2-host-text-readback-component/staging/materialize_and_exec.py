#!/usr/bin/env python3
"""Stage one exact Host2 input packet, then exec its original fixed command.

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
ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-host-text-readback-20261127')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-wave2-host2-inputs-ecd195f9ab6156f9.json.gz')
PAYLOAD_SHA = 'ecd195f9ab6156f92dabd14ab26dd16cedfc014aaa54303247a82eeb28e57d67'
RAW_SHA = '9de9a66c55b60026ec61054094ffc7f12afdf310d8a04139f8376821df8744df'
PACKET_SHA = 'ef37ebaa47b8d84b8e4d5eb4b89ad25c38fd6c704d2e9b8bbf90bcd0ed063aa5'
CONTROLLER_SHA = 'cb85418882d403318e786dae2564bbd2c4a2313be622a39139b84fb67090dce0'
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coordination-story', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9]{16}', args.coordination_story), 'Exact scheduling story required'
    receipt = {'schema': 'pinkha-host2-input-materialization-receipt/v1',
               'status': 'FAIL_NOT_EXECUTED', 'startedAtUTC': now(),
               'coordinationStory': args.coordination_story, 'slotGrantedByThisScript': False,
               'root': str(ROOT), 'payload': str(PAYLOAD), 'payloadSHA256': PAYLOAD_SHA,
               'packetSHA256': PACKET_SHA, 'controllerSHA256': CONTROLLER_SHA,
               'inputSourceCommit': 'f6b7d9622af1d9f567a7680a423b8ff7920c8117',
               'createdFiles': [], 'runtimeExecuted': False, 'errors': []}
    try:
        physical(ROOT.parent)
        assert ROOT.parent.is_dir()
        assert not ROOT.exists() and not ROOT.is_symlink(), 'Never reuse an existing attempt'
        receipt['before'] = budget()
        physical(PAYLOAD)
        before = PAYLOAD.stat()
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == 131419
        packed = PAYLOAD.read_bytes()
        after = PAYLOAD.stat()
        assert (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
        assert len(packed) == 131419 and sha(packed) == PAYLOAD_SHA
        raw = gzip.decompress(packed)
        assert len(raw) == 611097 and sha(raw) == RAW_SHA
        payload = json.loads(raw)
        assert set(payload) == {'schema', 'packetBase64', 'entries'}
        assert payload['schema'] == 'pinkha-host2-fixed-input-materialization/v1'
        packet_raw = base64.b64decode(payload['packetBase64'], validate=True)
        assert sha(packet_raw) == PACKET_SHA
        packet = json.loads(packet_raw)
        assert packet['root'] == str(ROOT) and packet['executeArgv'] == EXEC_ARGV
        assert packet['inputFiles'] == len(packet['files']) == len(payload['entries']) == 35
        assert packet['inputBytes'] == 448292
        expected = {item['path']: item for item in packet['files']}
        assert len(expected) == 35
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
        assert set(decoded) == set(expected) and sum(map(len, decoded.values())) == 448292
        assert sha(decoded['inputs/run_component.py']) == CONTROLLER_SHA
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
        receipt['after'] = budget()
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
