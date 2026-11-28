"""Fixed original156 bundle byte custody, never account/session admission."""
from pathlib import Path
import hashlib
import json
import os
import stat

MIB = 1024**2
PARENT = Path('/mnt/development/projects/evidence/pinkha-c-original156-bundle-recovery-20261127')
DESTINATION = Path('/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156/bundle')
PREFIX = 'private/fixtures/TestLoadedAccountCustomSchemaSource/native-source-2179973240/'
INDEX = Path('/var/lib/pinkha-w1-functional-migration-20261127/original156-source-custody2/private-original-index.json')
INDEX_SHA = '9e4fc63d587d194cf13fff4002329c25404490c166dd9ffc4fac9778767167b1'
AUDIT = Path('/var/lib/pinkha-w1-engine-contracts-20261127/original156-coherence-audit/result.json')
AUDIT_SHA = '68319ff3adca0da6191ce0a4df8ff9654bac6d5be745306922662da5d5454244'
READBACK = INDEX.parent/'recipient-readback.json'
READBACK_SHA = 'afc6663622d8ff47c09c08baa8b2f2909d0268269241b45f0833b2c51b79fc4d'
MANIFEST_SHA = 'cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4'
PRIOR_FAILURE = Path('/var/lib/pinkha-w1-functional-migration-20261127/source-facts-components-attempt1/result.json')
PRIOR_FAILURE_SHA = 'dfbf4573e999efd352a5c9d5eb57681f883a705562e16a67ce70e2f73c690277'
PRIVATE_AUDIT = Path('/mnt/development/projects/evidence/pinkha-c-original156-private-authority-20261127/attempt1/result.json')
PRIVATE_AUDIT_SHA = '74b4c03367bc4b1bd428fb6b0914303353cb3fc4b0fef909618db8afeac67bf2'
LIFECYCLE = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
STREAM_SHA = '03625d7770c10fd072034bc9ab0d84483a537bf1a5ea03e2d473b4147bf5ec82'
QUALIFIED_STREAM_SHA = '09ac70d01a322917fa4e11e9ba47eb018fc5fc730cf8b700f70ae6f02af74302'
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
ARCHIVE_SHA = 'f85036744b0cb76ffecb4e29f752dd293a74a1f76c2d13c273df57691a4a8c64'
ARCHIVE_BYTES = 106036361
EXPECTED_BYTES = 1526976
ROOT_FLOOR = DEV_FLOOR = 2*1024**3
OUTPUT_CAP = 8*MIB
_write_serial = 0


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_atime_ns,
            info.st_mtime_ns, info.st_ctime_ns]


def read(path, maximum=4*MIB):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'exact physical input')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum, 'bounded regular input')
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
    try:
        require(identity(os.fstat(descriptor)) == identity(before), 'input descriptor identity')
        parts, count = [], 0
        while True:
            part = os.read(descriptor, MIB)
            if not part:
                break
            count += len(part)
            require(count <= maximum, 'input length bound')
            parts.append(part)
        require(identity(os.fstat(descriptor)) == identity(before) == identity(path.lstat()), 'input changed during read')
        require(count == before.st_size, 'input length changed')
        return b''.join(parts)
    finally:
        os.close(descriptor)


def sha(path):
    return hashlib.sha256(read(path, 32*MIB)).hexdigest()


def pinned(path, digest):
    raw = read(path)
    require(hashlib.sha256(raw).hexdigest() == digest, 'retained exact control changed')
    return raw


def write(path, value):
    global _write_serial
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode()
    require(len(raw) <= MIB, 'bounded private recovery receipt')
    _write_serial += 1
    temporary = path.with_name(path.name+'.owned-next-'+str(os.getpid())+'-'+str(_write_serial))
    descriptor = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_directory(path.parent)


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def admitted_members():
    index = json.loads(pinned(INDEX, INDEX_SHA))
    audit = json.loads(pinned(AUDIT, AUDIT_SHA))
    recipient = json.loads(pinned(READBACK, READBACK_SHA))
    require(len(index['members']) == 1039 and audit['status'] == 'PASS_RETAINED_CAPTURE_COHERENCE_AND_MEMBER_HASHES_ONLY',
            'exact prior original byte provenance')
    originals = {}
    for row in index['members']:
        require(row['path'] not in originals, 'original index duplicate')
        originals[row['path']] = row
    selected = {}
    for path, row in originals.items():
        if not path.startswith(PREFIX):
            continue
        name = path[len(PREFIX):]
        require(name and Path(name).name == name and name not in ['.', '..'], 'original bundle flat member')
        selected[name] = {'bytes':row['bytes'], 'sha256':row['sha256']}
    require(len(selected) == 314 and selected['manifest.json'] == {'bytes':247643, 'sha256':MANIFEST_SHA}, 'full original314 bundle')
    referenced = {row['path']:{'bytes':row['bytes'], 'sha256':row['sha256']} for row in audit['members']}
    require(len(referenced) == len(audit['members']) == 313 and referenced == {k:v for k,v in selected.items() if k != 'manifest.json'},
            'every selected original member matches independent coherence audit')
    require(sum(row['bytes'] for row in selected.values()) == EXPECTED_BYTES, 'exact selected original byte count')
    bundle = [row for row in recipient['originalBundles'] if row['role'] == 'custom-schema']
    require(len(bundle) == 1 and bundle[0]['manifestSHA256'] == MANIFEST_SHA and bundle[0]['declaredMembers'] == 313 and
            bundle[0]['snapshots'] == 156 and bundle[0]['files'] == 0, 'original recipient bundle identity')
    return selected


def snapshot(folder, expected, metadata, check=None):
    if check is not None:
        check()
    require(folder.resolve() == folder and not folder.is_symlink(), 'physical bundle tree')
    descriptor = os.open(folder, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
    try:
        require(set(os.listdir(descriptor)) == set(expected), 'exact complete original bundle shape')
    finally:
        os.close(descriptor)
    actual = {}
    for name, row in sorted(expected.items()):
        if check is not None:
            check()
        path = folder/name
        raw = read(path)
        require({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} == row, 'restored original member byte identity')
        info = path.lstat()
        saved = metadata[name]
        observed = {'mode':stat.S_IMODE(info.st_mode),'uid':info.st_uid,'gid':info.st_gid,
                    'mtimeNS':info.st_mtime_ns,'atimeNS':info.st_atime_ns}
        require(observed == {key:saved[key] for key in observed}, 'restored original member portable metadata')
        require(os.listxattr(path, follow_symlinks=False) == [], 'unexpected restored extended attributes')
        actual[name] = dict(row, **observed)
    if check is not None:
        check()
    return actual


def allocated(folder):
    if not folder.exists():
        return 0
    total, count = 0, 0

    def visit(path):
        nonlocal total, count
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode), 'owned recovery output special file')
        total += info.st_blocks*512; count += 1
        require(count <= 1024, 'bounded recovery output shape')
        if stat.S_ISDIR(info.st_mode):
            descriptor = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
            try:
                names = os.listdir(descriptor)
            finally:
                os.close(descriptor)
            for name in names:
                visit(path/name)

    visit(folder)
    return total
