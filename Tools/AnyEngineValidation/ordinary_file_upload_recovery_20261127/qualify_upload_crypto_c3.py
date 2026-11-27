"""Isolate C3-qualified Crypto imports for the ordinary-upload consumer.

The shared producer admission validates all current source/driver/link/product
inputs. This wrapper retains the original 94 Git-blob header proof and copies
only four module/doc files plus those exact headers. No dependency is compiled.
"""
import hashlib
import json
from pathlib import Path
import stat
import sys
import types

CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
SHARED_HELPER = Path(__file__).with_name('qualify_current_c3_crypto.py')
SHARED_HELPER_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
HEADER_PROVENANCE = Path(__file__).with_name('crypto-header-source-manifest.json')
HEADER_PROVENANCE_SHA256 = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
CUSTODY_SHA = 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
MODULES = ('Crypto', 'CryptoBoringWrapper')


def load_shared(base=None):
    assert SHARED_HELPER.resolve() == SHARED_HELPER and not SHARED_HELPER.is_symlink()
    raw = base.read(SHARED_HELPER, maximum=65536) if base is not None else SHARED_HELPER.read_bytes()
    assert len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == SHARED_HELPER_SHA
    module = types.ModuleType('ordinary_upload_current_c3_crypto')
    module.__file__ = str(SHARED_HELPER)
    exec(compile(raw, str(SHARED_HELPER), 'exec'), module.__dict__)
    return module


def qualify(root, base, guard=lambda: None):
    if sys.flags.optimize:
        raise RuntimeError('qualified producer guards must remain enabled')
    shared = load_shared(base)
    admission = shared.qualify(guard)
    assert admission['status'] == 'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_REUSE_ONLY'
    assert admission['producerExactStableToPhysicalMapping'] == {str(CACHE): str(PHYSICAL_CACHE)}
    assert admission['currentApplicationWorktreeClaimedUnchanged'] is False
    base.admit_retained_crypto_alias(CACHE, PHYSICAL_CACHE, CUSTODY_SHA)
    immutable = {path: {key: row[key] for key in ('bytes', 'sha256')} for path, row in admission['liveInputs'].items()}
    modes = {path: row['mode'] for path, row in admission['liveInputs'].items()}

    def keep(path):
        guard()
        immutable[str(path)] = base.row(path)
        modes[str(path)] = stat.S_IMODE(path.stat().st_mode)
        return immutable[str(path)]

    base.pinned(SHARED_HELPER, SHARED_HELPER_SHA)
    keep(SHARED_HELPER)
    base.pinned(HEADER_PROVENANCE, HEADER_PROVENANCE_SHA256)
    keep(HEADER_PROVENANCE)
    manifest = json.loads(base.read(HEADER_PROVENANCE, maximum=131072))
    assert manifest['sourceCommit'] == 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed'
    assert manifest['sourceRoot'] == str(PHYSICAL_CACHE/'checkouts/swift-crypto')
    assert manifest['exactIncludeRoots'] == ['Sources/CCryptoBoringSSL/include', 'Sources/CCryptoBoringSSLShims/include']
    assert manifest['fileCount'] == 94 and manifest['byteCount'] == 2571399
    expected_headers = {row['path']: row for row in manifest['files']}
    assert len(expected_headers) == 94 and set(expected_headers) == set(admission['headerFiles'])
    assert admission['headerSourceRoot'] == str(CACHE/'checkouts/swift-crypto')
    assert admission['productDirectory'] == str(CACHE/'out/Products/Debug-linux-aarch64')
    headers = root/'retained-crypto-headers'
    headers.mkdir(mode=0o700)
    header_copies = {}
    for relative, expected in sorted(expected_headers.items()):
        guard()
        row = admission['headerFiles'][relative]
        expected_bytes = {key: expected[key] for key in ('bytes', 'sha256')}
        assert expected['mode'] == '100644' and len(expected['gitBlobID']) == 40
        assert {key: row[key] for key in ('bytes', 'sha256')} == expected_bytes
        original = Path(admission['headerSourceRoot'])/relative
        assert keep(original) == expected_bytes
        raw = base.read(original, maximum=4*1024**2)
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == expected['gitBlobID']
        target = headers/Path(relative).relative_to('Sources')
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        base.copy_exact(original, target, expected_bytes)
        header_copies[str(target)] = base.row(target)

    imports = root/'retained-crypto-imports'
    imports.mkdir(mode=0o700)
    modules = {}
    expected_modules = {name+'.swiftmodule/aarch64-unknown-linux-gnu.'+extension
                        for name in MODULES for extension in ('swiftmodule', 'swiftdoc')}
    assert set(admission['moduleFiles']) == expected_modules
    for relative, row in sorted(admission['moduleFiles'].items()):
        guard()
        original = Path(admission['productDirectory'])/relative
        expected = {key: row[key] for key in ('bytes', 'sha256')}
        assert keep(original) == expected
        target = imports/relative
        target.parent.mkdir(mode=0o700, exist_ok=True)
        base.copy_exact(original, target, expected)
        modules[str(target)] = base.row(target)
    for name in MODULES:
        assert {path.name for path in (imports/(name+'.swiftmodule')).iterdir()} == {
            'aarch64-unknown-linux-gnu.swiftmodule', 'aarch64-unknown-linux-gnu.swiftdoc'}
    assert len(modules) == 4 and len(header_copies) == 94
    compiler = ['-I', str(imports)]
    for name in ('CCryptoBoringSSL', 'CCryptoBoringSSLShims'):
        path = headers/name/'include/module.modulemap'
        compiler += ['-Xcc', '-fmodule-map-file='+str(path), '-Xcc', '-I'+str(path.parent)]
    assert admission['additionalOriginalSystemLinkLibrary'] == 'stdc++' and len(admission['linkObjects']) == 4
    receipt = {
        'status': 'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_ORDINARY_UPLOAD_COMPONENTS_ONLY',
        'sharedProducerAdmission': admission, 'sharedAdmissionHelperSHA256': SHARED_HELPER_SHA,
        'currentProducerSHA256': admission['producer']['sha256'], 'previousProducerRemainsHistorical': True,
        'immutableFiles': immutable, 'modes': modes, 'isolatedCryptoModuleCopies': modules,
        'isolatedCryptoHeaderCopies': header_copies,
        'exactGitBoundHeaderProvenance': {'path': str(HEADER_PROVENANCE), 'sha256': HEADER_PROVENANCE_SHA256},
        'compilerImportFlags': compiler, 'linkObjects': admission['linkObjects'],
        'additionalOriginalSystemLinkLibrary': 'stdc++', 'dependencyCompilerInvocations': 0,
        'acceptance': 'none; all35 ordinary-upload component methods remain mandatory'}
    base.save(root/'retained-dependency-products.json', receipt)
    return {
        'receipt': {'path': str(root/'retained-dependency-products.json'), **base.row(root/'retained-dependency-products.json')},
        'immutableInputs': immutable, 'inputModes': modes, 'copiedModules': modules, 'copiedHeaders': header_copies,
        'compilerFlags': compiler, 'linkObjects': admission['linkObjects'], 'swiftDriver': admission['swiftDriver'],
        'producerExactStableToPhysicalMapping': admission['producerExactStableToPhysicalMapping'],
        'sharedAdmission': admission}


def validate_after(reused, guard=lambda: None):
    shared = load_shared()
    shared.validate_after(reused['sharedAdmission'], guard)
    for path, mode in reused['inputModes'].items():
        guard()
        assert stat.S_IMODE(Path(path).stat().st_mode) == mode, path+' original product mode changed'
