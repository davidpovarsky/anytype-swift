#!/usr/bin/env python3
"""Pinned HTTP4 bootstrap; no dispatch until Root assigns its finite slot."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MIB = 1024**2
SOURCE = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-http-source-20261127-attempt1')
INSTALL = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-http-source-install-20261127-attempt1/result.json')
CONTROLLER = SOURCE/'verify_runtime_state_http.py'
CONTROLLER_SHA = 'a7f0fbe8067946d35865be61d3c35a1b82fe3e1b85df6f06040c758273c4a18d'
INSTALLER_SHA = '89c362fa63870517e29a068671173c8b3afd3e17a5423fb716c936cdabe58a27'
ENVELOPE_SHA = 'b110bba954d5813c43b6672e0624004fcc79c2ad2b946e67a4848cb8a05eac4f'
PRODUCER = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/result.json')
PRODUCER_SHA = 'f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2'
OUTPUT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-http-20261127/attempt1')


def frozen(path, maximum):
    before = path.lstat()
    assert path.is_absolute() and path.resolve() == path and stat.S_ISREG(before.st_mode)
    assert before.st_nlink == 1 and before.st_size <= maximum
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        assert os.fstat(stream.fileno()) == before
        raw = stream.read(maximum+1)
        assert os.fstat(stream.fileno()) == before
    assert path.lstat() == before and len(raw) == before.st_size
    return raw


def available(path):
    value = os.statvfs(path)
    return value.f_bavail*value.f_frsize


assert __debug__ and os.geteuid() == 0 and os.uname().nodename == 'torah-social'
assert len(sys.argv) == 2 and len(sys.argv[1]) == 64 and all(c in '0123456789abcdef' for c in sys.argv[1])
assert SOURCE.resolve() == SOURCE and SOURCE.is_dir()
assert OUTPUT.parent.parent.resolve() == OUTPUT.parent.parent and OUTPUT.parent.parent.is_dir()
assert not os.path.lexists(OUTPUT)
if os.path.lexists(OUTPUT.parent):
    assert OUTPUT.parent.resolve() == OUTPUT.parent and OUTPUT.parent.is_dir() and not OUTPUT.parent.is_symlink()
raw = frozen(CONTROLLER, 65536)
assert len(raw) == 41423 and hashlib.sha256(raw).hexdigest() == CONTROLLER_SHA
ast.parse(raw)
install_raw = frozen(INSTALL, MIB)
assert hashlib.sha256(install_raw).hexdigest() == sys.argv[1]
installed = json.loads(install_raw)
assert installed['status'] == 'PASS_EXACT_RUNTIME_STATE_HTTP4_SOURCE_INSTALL_ONLY_NOT_RUN'
assert installed['controller'] == {'bytes': 58540, 'sha256': INSTALLER_SHA}
assert installed['sourceRoot'] == str(SOURCE) and installed['sourceEnvelopeSHA256'] == ENVELOPE_SHA
assert installed['errors'] == [] and installed['commands'] == []
assert installed['newChildren'] == installed['nativeProcesses'] == installed['compilerInvocations'] == installed['testInvocations'] == installed['accountInputs'] == 0
assert installed['installerUnchangedAtCompletion'] and installed['sourceMembersUnchangedAtCompletion']
assert set(installed['installedFiles']) == {'verify_runtime_state_http.py', 'runtime_product_admission.py', 'runtime_wire_validation.py', 'owned_swift_commands.py'}
for name, expected in installed['installedFiles'].items():
    member = SOURCE/name
    assert member.is_relative_to(SOURCE) and Path(name).name == name
    data = frozen(member, MIB)
    assert {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected
producer_raw = frozen(PRODUCER, 65536)
assert len(producer_raw) == 19865 and hashlib.sha256(producer_raw).hexdigest() == PRODUCER_SHA
producer = json.loads(producer_raw)
assert producer['status'] == 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT'
assert producer['errors'] == producer['completionErrors'] == []
assert producer['allOwnedGroupsPositivelyAbsent'] and len(producer['processes']) == 6
assert all(p['exitCode'] == 0 and p['processGroupAbsent'] and not p['forcedCleanup'] and p['signals'] == [] and p['cleanupErrors'] == [] for p in producer['processes'])
assert producer['actualMethods']['runs'] == producer['actualMethods']['passes'] == 18 and producer['actualMethods']['skips'] == 0
assert producer['sourceFiles'] == 1638 and producer['sdkSourceFiles'] == 750 and all(producer['finalIntegrity'].values())
assert producer['nativeBinary'] == {'bytes': 78294169, 'mode': 448, 'path': str(PRODUCER.parent/'any'), 'sha256': '84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974'}
assert available('/') >= (2048+128)*MIB
assert available('/mnt/development') >= (512+32)*MIB
memory = int(next(row.split()[1] for row in Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:')))*1024
assert memory >= 2*1024**3
print(json.dumps({'status': 'PINNED_RUNTIME_HTTP4_DISPATCH', 'controllerSHA256': CONTROLLER_SHA,
    'sourceInstallationReceiptSHA256': hashlib.sha256(install_raw).hexdigest(), 'producerReceiptSHA256': PRODUCER_SHA,
    'output': str(OUTPUT), 'rootFreeBytes': available('/'), 'developmentFreeBytes': available('/mnt/development'),
    'memAvailableBytes': memory, 'requiredOuterSeconds': 480}, sort_keys=True), flush=True)
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-B', str(CONTROLLER), '--output', str(OUTPUT),
    '--producer-receipt', str(PRODUCER), '--producer-sha256', PRODUCER_SHA])
