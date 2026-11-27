"""Explicit physical admission after the qualified E custody move.

Historical controllers and receipts are unchanged. This module accepts one
caller-pinned custody receipt and one fixed original-to-physical mapping. It
never treats an arbitrary symlink resolution as source admission, and it never
opens an account or starts a compiler. Runtime callers retain their original
functional gates and must check the actual root/development mount floors.
"""
import base64
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

PARENT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127')
RETAINED = PARENT/'retained'
RUN = RETAINED/'current8ac'
BASE = RUN/'attempt2'
SUCCESSOR_PARENT = PARENT/'successor-runs'
LLVM = RETAINED/'llvm-native'
CUSTODY_RECEIPT = PARENT/'attempt1/result.json'
CUSTODY_SHA = '331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772'
CONTROLLER_SHA = '4ddaa92aaa5fe2d13d39bab699dbe6c409a2900eb9713da48af2470435c635fd'
SOURCE_MANIFEST = 'ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28'
FAILED_RECEIPT = 'fbae1f7a1a628ab75317e2812613a6c96682c6bceef9d8f3187ab13cf5e7e3e6'
ROOT_MAP = {
    '/var/tmp/pinkha-e-cutover-current8ac-20261127': str(RUN),
    '/var/tmp/pinkha-e-cutover-llvm-native-20261126': str(LLVM),
    '/var/tmp/pinkha-e-cutover-core-dryrun-20261126': str(RETAINED/'core-dryrun'),
}
MANIFEST_PINS = {
    'current8ac': 'a53a7a9c029a9fc45ad3b02ae36b9a551699ca1b62d1a189f0ebf71cefa1581c',
    'llvm-native': 'f027609503a28b277687810e773468004b1351ae53614acdb59875eac3986502',
    'core-dryrun': '408352e0245278ac0bd0bc0f203eb43fdf85cfba3cd7e83e8005af9ea51c43cd',
}
ENTRY_COUNTS = {'current8ac':7927, 'llvm-native':13, 'core-dryrun':9}
RECEIPT_PINS = {
    'attempt2/source-before.json':SOURCE_MANIFEST,
    'attempt2/receipt.json':FAILED_RECEIPT,
    'rpc-core-attempt5/receipt.json':'73478d7b445484746b2504cd0e0136735a3893143e83230ced242394fdbc7bfb',
    'rpc-generated-qualification1/receipt.json':'b02f58b6a9c341bcc2c0820c599e0f6ed1cb699d457e936375aea8495865ee62',
    'rpc-host-attempt2/receipt.json':'ad68dc512105c751c6971e31702452f7f3ebebb73b1ecc1b3911c67b9dde01ea',
}


def physical(path, directory=False):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink(), str(path)+' must be the fixed physical path'
    info = path.lstat()
    assert stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    return info


def read(path, limit):
    before = physical(path)
    assert before.st_size <= limit
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            value = stream.read(limit+1)
    finally:
        os.close(descriptor)
    assert len(value) <= limit and len(value) == before.st_size
    assert path.lstat() == before, 'source changed during bounded noatime read'
    return value


def digest(path):
    before = physical(path)
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    value = hashlib.sha256()
    length = 0
    try:
        while block := os.read(descriptor, 1024**2):
            length += len(block)
            value.update(block)
    finally:
        os.close(descriptor)
    assert path.lstat() == before and length == before.st_size
    return {'bytes':length, 'sha256':value.hexdigest()}


def pinned_json(path, pin, limit):
    raw = read(path, limit)
    assert hashlib.sha256(raw).hexdigest() == pin, str(path)+' identity differs'
    value = json.loads(raw)
    assert isinstance(value, dict)
    return value


def manifest(label):
    assert label in MANIFEST_PINS
    value = pinned_json(PARENT/'attempt1'/(label+'-source-before.json'), MANIFEST_PINS[label], 16*1024**2)
    assert set(value) == {'entries', 'hardlinkTopology'} and value['hardlinkTopology'] == []
    rows = value['entries']
    assert len(rows) == ENTRY_COUNTS[label]
    result = {}
    for row in rows:
        name = row['path']
        rel = PurePosixPath(name)
        assert name == '.' or (str(rel) == name and not rel.is_absolute() and '..' not in rel.parts)
        assert name not in result and row['kind'] in ('file', 'directory', 'symlink')
        if row['kind'] == 'file':
            assert row['nlink'] == 1 and re.fullmatch('[a-f0-9]{64}', row['sha256'])
        result[name] = row
    return result


def verify_file(root, relative, row):
    path = root/relative
    info = physical(path)
    assert row['kind'] == 'file' and info.st_nlink == row['nlink'] == 1
    assert stat.S_IMODE(info.st_mode) == row['mode']
    assert (info.st_uid, info.st_gid, info.st_mtime_ns) == (row['uid'], row['gid'], row['mtimeNS'])
    attrs = {key:base64.b64encode(os.getxattr(path,key,follow_symlinks=False)).decode()
             for key in sorted(os.listxattr(path,follow_symlinks=False))}
    assert attrs == row['xattrs']
    assert digest(path) == {'bytes':row['bytes'], 'sha256':row['sha256']}
    # Custody retained access timestamps exactly. Subsequent ordinary reads can
    # advance atime; atime is not a source-content or ownership identity gate.
    # This verifier itself uses O_NOATIME and never rewrites source metadata.


def verify_subtree(label, relative):
    root = RETAINED/label
    rows = manifest(label)
    path = root/relative
    physical(path, directory=True)
    expected = {name:row for name,row in rows.items()
                if name == relative or name.startswith(relative+'/')}
    assert expected and expected[relative]['kind'] == 'directory'
    stack = [path]
    seen = set()
    file_count = 0
    while stack:
        current = stack.pop()
        name = current.relative_to(root).as_posix()
        assert name in expected and name not in seen
        seen.add(name)
        row = expected[name]
        assert row['kind'] in ('directory', 'file'), 'no source aliases admitted'
        if row['kind'] == 'file':
            verify_file(root, name, row)
            file_count += 1
        else:
            info = physical(current, directory=True)
            assert stat.S_IMODE(info.st_mode) == row['mode']
            assert (info.st_uid,info.st_gid,info.st_mtime_ns) == (row['uid'],row['gid'],row['mtimeNS'])
            attrs = {key:base64.b64encode(os.getxattr(current,key,follow_symlinks=False)).decode()
                     for key in sorted(os.listxattr(current,follow_symlinks=False))}
            assert attrs == row['xattrs']
            descriptor = os.open(current, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
            try:
                with os.scandir(descriptor) as entries:
                    names = sorted(entry.name for entry in entries)
            finally:
                os.close(descriptor)
            assert current.lstat() == info
            stack.extend(current/name for name in reversed(names))
        assert len(seen) <= ENTRY_COUNTS[label]
    assert seen == set(expected), 'complete retained source subtree differs'
    return {'physicalPath':str(path), 'entries':len(seen), 'files':file_count,
            'custodyManifestSHA256':MANIFEST_PINS[label],
            'bytesModesOwnersModificationTimesXattrsAndTopologyUnchanged':True}


def qualify(receipt_path, receipt_sha):
    if sys.flags.optimize:
        raise RuntimeError('acceptance assertions must remain enabled')
    assert Path(receipt_path) == CUSTODY_RECEIPT and receipt_sha == CUSTODY_SHA
    receipt = pinned_json(CUSTODY_RECEIPT, receipt_sha, 128*1024)
    assert receipt['protocol'] == 'pinkha-three-e-roots-physical-custody-v1'
    assert receipt['status'] == 'PASS_THREE_E_ROOTS_EXACT_PHYSICAL_CUSTODY_STABLE_ORIGINAL_ALIASES'
    assert receipt['controllerSHA256'] == CONTROLLER_SHA and receipt['controllerSourceUnchanged']
    assert receipt['errors'] == [] and receipt['usersBefore'] == []
    assert receipt['nativeInvocations'] == receipt['compilerInvocations'] == receipt['uniqueBytesRetired'] == 0
    assert receipt['exactOriginalToPhysicalRoots'] == ROOT_MAP
    assert receipt['entryCounts'] == ENTRY_COUNTS and receipt['sourceManifestSHA256'] == MANIFEST_PINS
    for flag in ('allCopiesVerified','allPortableMetadataAndTopologyRetained',
                 'originalAbsolutePathsPreserved','retainedPhysicalSourceRequalified',
                 'capturedRetainedReceiptBytesUnchanged','protectedPinsAfterEqual','finalIntegrityVerificationComplete'):
        assert receipt[flag] is True
    assert sorted(receipt['duplicateDirectoriesRetired']) == sorted(ENTRY_COUNTS)
    assert receipt['verifiedDestinationsAfterEqual'] == {name:True for name in ENTRY_COUNTS}
    for original,destination in ROOT_MAP.items():
        assert Path(original).is_symlink() and os.readlink(original) == destination
        physical(Path(destination), directory=True)
    for key,path in (('originalPhysicalSourceAdmission',Path(next(iter(ROOT_MAP)))/'attempt2/source'),
                     ('relocatedPhysicalSourceAdmission',BASE/'source')):
        admitted = receipt[key]
        assert admitted['physicalSource'] == str(path) and admitted['sourceManifestSHA256'] == SOURCE_MANIFEST
        assert admitted['files'] == 4893 and admitted['allSourceBytesAndPathsMatchOriginalInventory']
        assert admitted['retainedReceiptPins'] == RECEIPT_PINS
    rows = manifest('current8ac')
    for relative,pin in RECEIPT_PINS.items():
        assert rows[relative]['sha256'] == pin
        verify_file(RUN, relative, rows[relative])
    source = verify_subtree('current8ac', 'attempt2/source')
    original = pinned_json(BASE/'source-before.json', SOURCE_MANIFEST, 4*1024**2)
    captured = {name.removeprefix('attempt2/source/'):{'bytes':row['bytes'],'sha256':row['sha256']}
                for name,row in rows.items() if name.startswith('attempt2/source/') and row['kind'] == 'file'}
    assert original == captured and len(original) == source['files'] == 4893
    return {'status':'EXACT_RELOCATED_PHYSICAL_SOURCE_ADMITTED_NO_RUNTIME_CLAIM',
            'custodyReceipt':str(CUSTODY_RECEIPT), 'custodySHA256':CUSTODY_SHA,
            'custodyControllerSHA256':CONTROLLER_SHA, 'exactOriginalToPhysicalRoots':ROOT_MAP,
            'source':source, 'sourceManifestSHA256':SOURCE_MANIFEST,
            'originalReceiptsUnchanged':RECEIPT_PINS,
            'aliasFallbackAllowed':False, 'nativeInvocations':0, 'compilerInvocations':0}


def reserve_successor_output(root, family):
    if sys.flags.optimize:
        raise RuntimeError('acceptance assertions must remain enabled')
    assert family in ('swift-generation','swift-client')
    root = Path(root)
    physical(PARENT, directory=True)
    assert root.parent == SUCCESSOR_PARENT and re.fullmatch(family+r'-physical[1-9][0-9]{0,2}', root.name)
    if not SUCCESSOR_PARENT.exists():
        SUCCESSOR_PARENT.mkdir(mode=0o700)
    physical(SUCCESSOR_PARENT, directory=True)
    assert not os.path.lexists(root)
    root.mkdir(mode=0o700)
    return root
