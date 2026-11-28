#!/usr/bin/env python3
"""Qualify only cold checkpoint9, content correspondence5, Bookmark6 and affected Page2.

The exact118 whole source files are compiled in an isolated package. Qualified
Crypto products are the sole imported dependency products; no prior application
Products, migration operation, native account or previous method is reused.
This source is not test or native acceptance until its actual receipt closes.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import datetime
import signal
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import time

MIB = 1024 * 1024
GIB = 1024 * MIB
PARENT = Path('/mnt/development/projects/evidence/pinkha-c-cold-bookmark22-20261128')
PREPARED = PARENT/'prepared1'
CONTROL = Path(__file__).parent
GRAPH_ROOT = Path('/mnt/development/projects/evidence/pinkha-c-cold-bookmark22-graph-preparation-20261128-attempt1')
MANIFEST = GRAPH_ROOT/'SOURCE_GRAPH.json'
MANIFEST_SHA = 'be001f4ecebd9143580fc6d67b21dd60e6c6c65698382c8e1be521145cc01867'
GRAPH_INPUTS = GRAPH_ROOT/'PUBLIC_INPUTS.json'
GRAPH_INPUTS_SHA = 'b41c7e2e0b80ee25c63b0e1eb08376b62e496729b8c9171a05bcb8e552440666'
GRAPH_RECEIPT = GRAPH_ROOT/'result.json'
GRAPH_RECEIPT_SHA = '25082133e2b4be33e85c34374c44b91575db65fd85ad7a6a4c5c96b7107eb94b'
DONOR_ROOT = Path('/mnt/development/projects/evidence/pinkha-original-navigation26-20261128')
DONOR_RECEIPT = DONOR_ROOT/'components-attempt3/result.json'
DONOR_RECEIPT_SHA = '6325a1a204bb2fbd485a3bd55aa9634425e8945570077d71740694f3b7413d23'
DONOR_MANIFEST = DONOR_ROOT/'prepared3/navigation-component-inputs.json'
DONOR_MANIFEST_SHA = 'fdac37214d2f8c1ac561278df5ac37ad2606ea1e2333023a502b0ba3d8e5c0cf'
DONOR_CONTROLLER = DONOR_ROOT/'prepared3/run_navigation_components.py'
DONOR_CONTROLLER_SHA = '928d5683992686091370cbc68ca2823dd474e1dec38ec9d136a60021ccb03448'
CRYPTO_HELPER = CONTROL/'qualify_provider_crypto_c3.py'
CRYPTO_HELPER_SHA = '9ec68e6db7ad722866236ab4494df3108fee60791a40a8d218c93a82d817805b'
SHARED_CRYPTO_HELPER = CONTROL/'qualify_current_c3_crypto.py'
SHARED_CRYPTO_HELPER_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
OWNED_HELPER = CONTROL/'owned_swift_commands.py'
OWNED_HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HEADER_MANIFEST = CONTROL/'crypto-header-source-manifest.json'
HEADER_MANIFEST_SHA = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
LIFECYCLE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_RECEIPT_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
DRIVER_ALIASES = {
    TOOLCHAIN/'swift': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'swiftc': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'clang': TOOLCHAIN/'clang-21',
    TOOLCHAIN/'clang++': TOOLCHAIN/'clang-21',
}
ROOT_FLOOR = 2 * GIB
ROOT_ADMISSION = ROOT_FLOOR + 32 * MIB
DEVELOPMENT_FLOOR = 512 * MIB
OWNED_ALLOCATION_CAP = 384 * MIB
DEVELOPMENT_ADMISSION = DEVELOPMENT_FLOOR + OWNED_ALLOCATION_CAP + 32 * MIB
LOG_CAP = 16 * MIB
FIXTURE_CAP = 16 * MIB
RECEIPT_CAP = 4 * MIB
TOTAL_SECONDS = 900
SWIFT_SECONDS = 600
FIXTURE_INPUTS = CONTROL/'provider_fixture_inputs.py'
FIXTURE_INPUTS_SHA = '32cec96b4984b02d1cae76c94ccc73e958f0f890f32e68e9729ab7db4b13b5cf'
BUNDLE_INPUTS = CONTROL/'bundle_recovery_inputs.py'
BUNDLE_INPUTS_SHA = 'f7b8155be19a890cd7e7351c22ca46c4d337ca9b1052bc7b4c80be84abb4c3e4'
BASELINE_INPUTS = CONTROL/'compiled-source-313.json'
BASELINE_INPUTS_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
EXPECTED_METHODS = json.loads("{\"NativeImportedCheckpointTests\":[\"testCompletedCheckpointColdReadsKeepExactMappingsAndDoNotCallTheDriver\",\"testMissingAndIncompleteCheckpointNeverCreatesOrReconcilesJournalEntries\",\"testOriginalExclusiveWriterAndSharedColdReaderUseOneLockWithoutWrites\",\"testChangedReceiptIdentityRefusesEvenWhenItsJournalEnvelopeIsValid\",\"testExactBindingRejectsUnicodeAliasAndChangedPlanWithoutRepair\",\"testAliasAndReplacedOwnerLockRefuseBeforeColdDelivery\",\"testCancelledColdReadLeavesCompletedCheckpointAndDriverUntouched\"],\"NativeImportedContextReferenceTests\":[\"testClosedReferenceWireRejectsMissingExtraDuplicateAndMalformedFields\",\"testReferenceBindingKeepsOpaqueUTF8AndNeverAuthenticatesAChangedCheckpointHash\"],\"NativeImportedContentContextTests\":[\"testOriginalCompletedPlanRoutesBothEditablePagesWithoutCatalogCarrierFallback\",\"testDocumentProjectionRejectsCarrierSubstitutionAndChangedOperationIdentity\",\"testEditedDocumentCreationReceiptRetainsIdentityAndRefusesDeletedOrForeignState\",\"testClosedContentLocatorBindsTheSameWholeCheckpointAndExactPreservationBytes\",\"testOwnerRefusesForeignRetiredAndChangedRunBeforeOpeningPrivateInputs\"],\"NativeBookmarkCompositionTests\":[\"testBoundBookmarkHeaderKeepsDescriptionAndOrderedBodySeparate\",\"testBookmarkCompositionKeepsExactURLAndDistinctReferenceCycles\",\"testBodylessBookmarkPreservesAbsentAndExplicitEmptyDescriptionAndURL\",\"testChangedHeaderBindingsAndObjectSpecificFeaturedOverridesAreRefused\",\"testBookmarkNeverDropsUnsupportedDetailsMetadataOrBody\",\"testExactTypeCanonicalDescriptionAndReferenceIdentityRemainMandatory\"],\"NativePageCompositionTests\":[\"testPageCompositionKeepsOneTitleAndDefersExactReferenceCycles\",\"testUnaccountedDetailsSourceMetadataAndAmbiguousIdentitiesAreRefused\"]}")
EXCLUDED_METHODS = json.loads("{\"NativeCanonicalDefinitionSupplementTests\":[\"testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics\",\"testSupplementRefusesDuplicateExistingAndCallerChosenAliases\",\"testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace\"],\"NativePageCompositionTests\":[\"testOriginalCapturedPageComposesCurrentStateAndRetainsSourceBlockers\",\"testOriginalCustomCapturePreservesBothPagesAllValuesAndDistinctIdentities\"]}")
CHUNK = MIB
_save_serial = 0

class Inputs:
    """Exact regular-file reads; no generic symlink admission or whole-file hash."""
    def __init__(self):
        self.alias_admitted = False

    def admit_retained_crypto_alias(self, original, physical, receipt_sha):
        assert original == CACHE and physical == PHYSICAL_CACHE
        assert receipt_sha == 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
        assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
        assert CACHE.resolve() == PHYSICAL_CACHE and PHYSICAL_CACHE.resolve() == PHYSICAL_CACHE
        self.alias_admitted = True

    def physical(self, value):
        path = Path(value)
        assert path.is_absolute()
        if path in DRIVER_ALIASES:
            target = DRIVER_ALIASES[path]
            assert path.resolve() == target and target.resolve() == target
            if path.name == 'swift' or path.name == 'swiftc':
                assert os.readlink(path) == 'swift-driver'
            elif path.name == 'clang':
                assert os.readlink(path) == 'clang-21'
            else:
                assert os.readlink(path) == 'clang' and os.readlink(TOOLCHAIN/'clang') == 'clang-21'
            return target
        if path.is_relative_to(CACHE):
            assert self.alias_admitted, 'retained cache custody not yet admitted'
            assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
            target = PHYSICAL_CACHE/path.relative_to(CACHE)
            assert path.resolve() == target and target.resolve() == target
            return target
        assert path.resolve() == path and not path.is_symlink(), 'unqualified input alias'
        return path

    @staticmethod
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def consume(self, value, maximum, retain=False, destination=None):
        path = self.physical(value)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum
        assert self.identity(path.lstat()) == self.identity(before)
        digest = hashlib.sha256()
        collected = bytearray() if retain else None
        copied = 0
        try:
            while True:
                part = os.read(fd, CHUNK)
                if not part:
                    break
                copied += len(part)
                assert copied <= maximum and copied <= before.st_size
                digest.update(part)
                if retain:
                    collected.extend(part)
                if destination is not None:
                    view = memoryview(part)
                    while view:
                        written = os.write(destination, view)
                        assert written > 0
                        view = view[written:]
            assert copied == before.st_size
            assert self.identity(os.fstat(fd)) == self.identity(before)
            assert self.identity(path.lstat()) == self.identity(before)
        finally:
            os.close(fd)
        result = {'bytes': copied, 'sha256': digest.hexdigest()}
        return (result, bytes(collected)) if retain else result

    def row(self, path):
        return self.consume(path, maximum=512*MIB)

    def sha(self, path):
        return self.row(path)['sha256']

    def read(self, path, maximum):
        return self.consume(path, maximum=maximum, retain=True)[1]

    def pinned(self, path, expected):
        assert re.fullmatch(r'[0-9a-f]{64}', expected)
        assert self.sha(path) == expected, str(path)+' changed'

    def copy_exact(self, original, destination, expected):
        destination = Path(destination)
        assert destination.parent.resolve() == destination.parent
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            copied = self.consume(original, maximum=8*MIB, destination=descriptor)
            assert copied == expected
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        assert self.row(destination) == expected

    def save(self, path, value):
        save(path, value)


def save(path, value):
    global _save_serial
    path = Path(path)
    assert path.parent.resolve() == path.parent
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    assert len(data) <= RECEIPT_CAP
    _save_serial += 1
    # Retain an interrupted staging file; finalization always gets a fresh name.
    temporary = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(_save_serial))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            assert count > 0
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_module(path, name, expected, base):
    base.pinned(path, expected)
    ast.parse(base.read(path, maximum=256*1024))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base.pinned(path, expected)
    return module


def allocation(root):
    total = 0
    count = 0
    seen = set()
    began = time.monotonic()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for filename in [None]+dirs+files:
            path = Path(directory) if filename is None else Path(directory)/filename
            try:
                row = path.lstat()
            except FileNotFoundError:
                continue  # A compiler may retire its own temporary member.
            count += 1
            assert count <= 200000 and time.monotonic()-began <= 5
            key = (row.st_dev, row.st_ino)
            if key not in seen:
                seen.add(key)
                total += row.st_blocks * 512
    return total


def retained_products(build, base, guard):
    """Pin the complete physical Products tree, including Linux test launchers.

    A suffix list omits the executable *-test-runner which --skip-build uses.
    Keep every regular product file and every executable mode, and refuse any
    alias/special file. The independent source manifest is a separate input.
    """
    root = build/'out/Products'
    assert root.is_dir() and root.resolve() == root and not root.is_symlink()
    files, modes, directories, executables = {}, {}, {}, {}
    for path in [root]+sorted(root.rglob('*')):
        guard()
        before = path.lstat()
        assert path.resolve() == path and not path.is_symlink(), 'physical compiled product required'
        key = str(path)
        mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            directories[key] = mode
        else:
            assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'regular private compiled product required'
            assert before.st_size <= 128*1024**2, 'bounded compiled product file'
            files[key] = base.row(path)
            modes[key] = mode
            if mode & 0o111:
                executables[key] = dict(files[key], mode=mode)
        after = path.lstat()
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_nlink,
                                row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        assert identity(before) == identity(after), 'compiled product changed during census'
        assert len(files)+len(directories) <= 4096, 'bounded compiled product tree'
    assert 1 <= len(files) <= 2048
    runners = [name for name in files if Path(name).name == 'ColdBookmarkContractTests-test-runner']
    assert len(runners) == 1 and runners[0] in executables, 'one actual executable Linux XCTest runner'
    libraries = [name for name in files if Path(name).name == 'ColdBookmarkContractTests.so']
    assert len(libraries) == 1, 'one actual test shared library'
    assert any('PinkhaAnyEngine' in name and '.swiftmodule' in name for name in files)
    assert any('PinkhaAnyHost' in name and '.swiftmodule' in name for name in files)
    return {'root':str(root), 'files':files, 'modes':modes, 'directories':directories,
            'executables':executables, 'testRunner':dict(path=runners[0], **executables[runners[0]])}


def package_text(flags, links):
    swift = lambda value: json.dumps(value, ensure_ascii=False)
    compile_flags = '['+', '.join(map(swift, flags))+']'
    link_flags = '['+', '.join(map(swift, links+['-lstdc++']))+']'
    targets = [
        ('TorahInspectorCore', []),
        ('PinkhaKit', ['TorahInspectorCore']),
        ('PinkhaAnyEngine', []),
        ('PinkhaAnyIntegration', ['PinkhaKit', 'PinkhaAnyEngine']),
        ('PinkhaAnyHost', ['PinkhaAnyEngine', 'PinkhaAnyIntegration']),
    ]
    rows = []
    for name, dependencies in targets:
        deps = '['+', '.join(map(swift, dependencies))+']'
        rows.append('        .target(name: '+swift(name)+', dependencies: '+deps+', swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')])')
    rows.append('        .testTarget(name: "ColdBookmarkContractTests", dependencies: ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost"], swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')], linkerSettings: [.unsafeFlags('+link_flags+')])')
    return '// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: "ColdBookmarkProof", targets: [\n'+',\n'.join(rows)+'\n])\n'



def admit_graph(base):
    graph = json.loads(base.read(MANIFEST, maximum=256*1024))
    public = json.loads(base.read(GRAPH_INPUTS, maximum=256*1024))
    receipt = json.loads(base.read(GRAPH_RECEIPT, maximum=64*1024))
    donor = json.loads(base.read(DONOR_RECEIPT, maximum=RECEIPT_CAP))
    dependencies = json.loads(base.read(DONOR_MANIFEST, maximum=256*1024))
    assert receipt['status'] == 'PASS_SOURCE_GRAPH_ONLY_NOT_COMPILED_NOT_RUN'
    assert receipt['errors'] == receipt['completionErrors'] == []
    assert all(receipt[key] == 0 for key in ('children','compilerInvocations','testInvocations','nativeInvocations','accountFilesRead'))
    assert receipt['unchangedInputs'] is True
    assert receipt['graph'] == {'path':str(MANIFEST),'bytes':101601,'sha256':MANIFEST_SHA,'mode':0o600}
    assert receipt['inputLedger'] == {'path':str(GRAPH_INPUTS),'bytes':71614,'sha256':GRAPH_INPUTS_SHA,'mode':0o600}
    expected_counts = {
        'wholeSwiftFiles':118, 'productionFiles':112, 'testFiles':6, 'selectedMethods':22,
        'newColdCheckpointAndLocatorMethods':9, 'newContentCorrespondenceMethods':5,
        'newBookmarkSemanticMethods':6, 'affectedPageRegressionMethods':2,
        'compileOnlyEarlierCanonicalMethods':3, 'unselectedOriginalPageMethods':2,
        'modifiedProductionFiles':7, 'addedProductionFiles':5, 'nativeAccounts':0, 'nativeHTTPRequests':0}
    assert graph['counts'] == receipt['counts'] == expected_counts
    assert graph['selectedMethods'] == EXPECTED_METHODS
    assert graph['donor']['actual'] == {'path':str(DONOR_RECEIPT),'bytes':76224,'sha256':DONOR_RECEIPT_SHA,'mode':0o600}
    assert graph['donor']['manifest'] == {'path':str(DONOR_MANIFEST),'bytes':73913,'sha256':DONOR_MANIFEST_SHA,'mode':0o600}
    assert graph['donor']['methodEventsReused'] == graph['donor']['productsReused'] == 0
    assert graph['donor']['sourceRowsReusedOnly'] is True
    assert graph['scope']['ordinary14Included'] is False
    assert graph['scope']['sharedC3Modified'] is False
    assert graph['scope']['oldPreservation182Reexecuted'] == 0
    assert graph['scope']['oldType25Metadata6NavigationMethodsSelected'] == 0
    assert graph['scope']['oldOriginalPageFixtureContextLocatorEstablished'] is False
    assert graph['scope']['originalPageMethodsRequiringMissingContextSelected'] is False
    assert graph['observations']['all118PhysicalFilesAndSevenPreimagesHashChecked'] is True
    assert graph['observations']['allModesObserved'] is True
    assert graph['observations']['noCompiledTypecheckingClaim'] is True
    assert graph['observations']['originalDonorProducerProductsReadOrReused'] is False
    assert graph['observations']['sourceBytes'] == receipt['sourceBytes'] == 1435258
    assert len(graph['sourceFiles']) == 118
    assert len({row['sourcePath'] for row in graph['sourceFiles']}) == 118
    assert len({row['isolatedPath'] for row in graph['sourceFiles']}) == 118
    assert sum(row['bytes'] for row in graph['sourceFiles']) == 1435258
    assert sum(row['kind'] == 'production' for row in graph['sourceFiles']) == 112
    assert sum(row['kind'] != 'production' for row in graph['sourceFiles']) == 6
    assert all(row['compile'] is True for row in graph['sourceFiles'])
    assert len(graph['changedProduction']) == 7 and len(graph['addedProduction']) == 5
    entries = public['entries']
    assert public['accountOrFixturePayloadsRead'] is False
    assert len(entries) == len({row['path'] for row in entries}) and len(entries) <= 256
    recorded = {row['path']:row for row in entries}
    expected_paths = {row['sourcePath'] for row in graph['sourceFiles']}
    expected_paths.update(pair['before']['sourcePath'] for pair in graph['changedProduction'])
    expected_paths.update(row['path'] for row in graph['controls'])
    expected_paths.update((str(DONOR_RECEIPT),str(DONOR_MANIFEST),str(MANIFEST)))
    assert set(recorded) == expected_paths
    for row in graph['sourceFiles'] + [pair['before'] for pair in graph['changedProduction']]:
        old = recorded[row['sourcePath']]
        assert all(old[key] == row[key] for key in ('bytes','sha256','mode'))
        relative = Path(row['isolatedPath'])
        assert not relative.is_absolute() and relative.parts and '..' not in relative.parts
        assert relative.parts[0] in ('Sources','Tests') and len(relative.parts) == 3
        assert relative.suffix == '.swift' and row['mode'] in (0o444,0o600,0o644)
    for row in graph['controls']:
        assert all(recorded[row['path']][key] == row[key] for key in ('bytes','sha256'))
    assert donor['status'] == 'PASS' and donor['errors'] == []
    assert donor['controllerSHA256'] == DONOR_CONTROLLER_SHA
    assert donor['inputManifestSHA256'] == DONOR_MANIFEST_SHA
    assert donor['actualMethods']['total'] == 3 and donor['actualMethods']['skipped'] == 0
    assert donor['qualifiedMethods']['total'] == 26 and donor['qualifiedMethods']['retained'] == 23
    assert donor['qualifiedMethods']['newlyExecuted'] == 3
    assert len(donor['commands']) == 7 and donor['allStartedOwnedGroupsPositivelyAbsent'] is True
    assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup']
               and not row['cleanupErrors'] and not row['signals'] for row in donor['commands'])
    assert all(donor[key] is True for key in ('sourceUnchanged','admittedInputsUnchanged',
        'compiledSourceInputsUnchanged','compiledProductsAndModesUnchanged',
        'originalSourceFixtureInputsAndCopiesUnchanged','retainedNavigationEvidenceUnchanged'))
    assert donor['nativeAccountsOpened'] is False and donor['nativeStorageQualified'] is False
    assert dependencies['original313ManifestSHA256'] == BASELINE_INPUTS_SHA
    assert dependencies['dependencySourcePins'] == {
        'swift-asn1':'917b472dbe53ba699cbb0495f9a95a084bc6364d',
        'swift-crypto':'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed'}
    assert dependencies['originalCoreRoot'] == str(PHYSICAL_CACHE/'checkouts/TorahInspectorKit')
    assert dependencies['originalCoreCommit'] == '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'
    assert len(dependencies['originalCoreFiles']) == 8
    core_rows = {row['path']:(row['bytes'],row['sha256']) for row in graph['sourceFiles'] if row['target']=='TorahInspectorCore'}
    assert core_rows == {row['path']:(row['bytes'],row['sha256']) for row in dependencies['originalCoreFiles']}
    return graph, recorded, dependencies


def require_empty_fixture_root(root):
    info = root.lstat()
    assert root.resolve() == root and stat.S_ISDIR(info.st_mode)
    assert info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700
    assert list(root.iterdir()) == [], 'synthetic journal fixture teardown must close its owned paths'


def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification requires Python assertions enabled')
    sys.dont_write_bytecode = True
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controller-sha', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{64}', args.controller_sha)
    assert CONTROL.resolve() == CONTROL and CONTROL == PREPARED
    assert PREPARED.resolve() == PREPARED and PARENT.resolve() == PARENT
    output = args.output
    assert output.parent == PARENT and output.name == 'components-attempt1'
    assert not output.exists() and not output.is_symlink()
    base = Inputs()
    controls = {
        Path(__file__):args.controller_sha, MANIFEST:MANIFEST_SHA,
        GRAPH_INPUTS:GRAPH_INPUTS_SHA, GRAPH_RECEIPT:GRAPH_RECEIPT_SHA,
        DONOR_RECEIPT:DONOR_RECEIPT_SHA, DONOR_MANIFEST:DONOR_MANIFEST_SHA,
        DONOR_CONTROLLER:DONOR_CONTROLLER_SHA,
        CRYPTO_HELPER:CRYPTO_HELPER_SHA, SHARED_CRYPTO_HELPER:SHARED_CRYPTO_HELPER_SHA,
        OWNED_HELPER:OWNED_HELPER_SHA, HEADER_MANIFEST:HEADER_MANIFEST_SHA,
        LIFECYCLE_RECEIPT:LIFECYCLE_RECEIPT_SHA, FIXTURE_INPUTS:FIXTURE_INPUTS_SHA,
        BUNDLE_INPUTS:BUNDLE_INPUTS_SHA, BASELINE_INPUTS:BASELINE_INPUTS_SHA}
    for path, expected in controls.items():
        base.pinned(path, expected)
    lifecycle = json.loads(base.read(LIFECYCLE_RECEIPT, maximum=MIB))
    assert lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
    assert lifecycle['helperSHA256'] == OWNED_HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'] is True
    assert len(lifecycle['methods']) == len(lifecycle['commands']) == 5
    assert {row['name'] for row in lifecycle['methods']} == {
        'normal','started-journal-failure','leader-exits-with-descendant','controller-SIGTERM','controller-SIGINT'}
    assert all(row['status'] == 'PASS' and row['groupPositivelyAbsent'] for row in lifecycle['methods'])
    assert all(row['processGroupAbsent'] for row in lifecycle['commands'])
    assert lifecycle['compilerInvocations'] == lifecycle['nativeInvocations'] == 0
    graph, graph_records, dependencies = admit_graph(base)
    owned = load_module(OWNED_HELPER, 'cold_bookmark_owned_commands', OWNED_HELPER_SHA, base)
    owned.install_interrupt_handlers()
    owned_output = False
    owned_output_identity = None
    owned_output_identity_fields = ('st_dev','st_ino','st_mode','st_uid','st_gid')
    started_at = time.monotonic()
    result = {
        'status':'RUNNING',
        'scope':'Cold checkpoint9, content correspondence5, Bookmark6 and affected Page2; isolated source components',
        'nativeAccountsOpened':False, 'nativeStorageQualified':False, 'cloudDurabilityQualified':False,
        'currentNativeOwnerAuthorityQualified':False, 'sourceAdmissionGranted':False,
        'originalMigration182Reexecuted':0, 'priorType25Metadata6NavigationMethodsReplayed':0,
        'earlierTestReplayRequested':False, 'earlierTestReplayStatus':'NOT_DISPATCHED',
        'historicalMethodsReused':0, 'historicalApplicationProductsReused':False,
        'errors':[], 'commands':[], 'sourceUnchanged':False,
        'controllerSHA256':args.controller_sha, 'inputManifestSHA256':MANIFEST_SHA,
        'sourceGraphReceipt':{'path':str(GRAPH_RECEIPT),'sha256':GRAPH_RECEIPT_SHA},
        'sourceGraphInputLedger':{'path':str(GRAPH_INPUTS),'sha256':GRAPH_INPUTS_SHA},
        'historicalSourceDonor':{
            'receipt':str(DONOR_RECEIPT),'sha256':DONOR_RECEIPT_SHA,
            'controllerSHA256':DONOR_CONTROLLER_SHA,'manifestSHA256':DONOR_MANIFEST_SHA,
            'historicalStatus':'PASS','sourceRowsUsed':True,'newCommandsReused':0,'newMethodsReused':0,
            'priorProductsOpenedOrImported':False,'oldGroupsReprobedOrReplayed':False},
        'scopeLimits':graph['scope'], 'plannedCounts':graph['counts'],
        'unchangedOwnedHelperFiveControlsReused':{
            'path':str(LIFECYCLE_RECEIPT),'sha256':LIFECYCLE_RECEIPT_SHA,'newlyExecutedControls':0},
        'budget':{
            'rootRuntimeFloorBytes':ROOT_FLOOR,'rootAdmissionBytes':ROOT_ADMISSION,
            'developmentRuntimeFloorBytes':DEVELOPMENT_FLOOR,'developmentAdmissionBytes':DEVELOPMENT_ADMISSION,
            'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP,'declaredControlledOutputBytesOnRoot':0,
            'finalVerificationSeconds':120,'mainControllerSeconds':TOTAL_SECONDS,'requiredOuterSeconds':1080,
            'allocationCapIsFiniteEstimateNotMeasuredPeak':True,
            'allExplicitBuildIndexCacheTemporaryAndEvidencePathsOnDevelopment':True,
            'noGlobalRootWriteAuditClaim':True},
        'minimumRootFreeBytes':shutil.disk_usage('/').free,
        'minimumDevelopmentFreeBytes':shutil.disk_usage(PARENT).free}
    immutable, copies, original_modes, copy_modes = {}, {}, {}, {}
    reused = None
    helper = None
    env = None
    last_allocation = 0.0
    source_admission_complete = False
    fixture_input_helper = None
    fixture_input_admission = None
    final_deadline = None
    expected = {name+'.'+method for name,methods in EXPECTED_METHODS.items() for method in methods}
    excluded = {name+'.'+method for name,methods in EXCLUDED_METHODS.items() for method in methods}

    def observe():
        nonlocal last_allocation
        try:
            root_free = shutil.disk_usage('/').free
            development_free = shutil.disk_usage(PARENT).free
            result['minimumRootFreeBytes'] = min(result['minimumRootFreeBytes'], root_free)
            result['minimumDevelopmentFreeBytes'] = min(result['minimumDevelopmentFreeBytes'], development_free)
            if root_free < ROOT_FLOOR:
                return 'root 2 GiB runtime emergency floor'
            if development_free < DEVELOPMENT_FLOOR:
                return 'development 512 MiB runtime emergency floor'
            if final_deadline is None and time.monotonic()-started_at > TOTAL_SECONDS:
                return 'bounded component controller deadline'
            if final_deadline is not None and time.monotonic() >= final_deadline:
                return 'bounded component final verification deadline'
            if (output/'abort').exists():
                return 'owned component abort requested'
            for path in output.glob('commands/*/original.log'):
                if path.stat().st_size > LOG_CAP:
                    return 'bounded command log limit'
            if time.monotonic()-last_allocation >= 1:
                last_allocation = time.monotonic()
                used = allocation(output)
                result['maximumOwnedAllocatedBytes'] = max(result.get('maximumOwnedAllocatedBytes',0), used)
                if used > OWNED_ALLOCATION_CAP:
                    return 'bounded entire component allocation limit'
                fixtures = output/'context-fixtures'
                if fixtures.exists() and allocation(fixtures) > FIXTURE_CAP:
                    return 'bounded synthetic journal fixture allocation limit'
        except BaseException as error:
            return 'resource observation failed: '+type(error).__name__
        return None

    def guard():
        reason = observe()
        if reason is not None:
            raise RuntimeError(reason)

    def remember_input(path, expected_row):
        guard()
        path = Path(path)
        info = base.physical(path).lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        assert info.st_size == expected_row['bytes'] and info.st_size <= 4*MIB
        if 'mode' in expected_row:
            assert stat.S_IMODE(info.st_mode) == expected_row['mode'], str(path)+' source mode changed'
        actual = base.row(path)
        assert actual == {key:expected_row[key] for key in ('bytes','sha256')}, str(path)+' source changed'
        immutable[str(path)] = actual
        original_modes[str(path)] = stat.S_IMODE(info.st_mode)

    def command(name, argv, cwd, command_env, timeout):
        log, row = owned.run(output/'commands'/name, argv, cwd, command_env, timeout,
                             observe, save, base.sha, result['commands'])
        return base.read(log, maximum=LOG_CAP), row

    def dependency_status(phase, manifest):
        for name, revision in manifest['dependencySourcePins'].items():
            directory = PHYSICAL_CACHE/'checkouts'/name
            assert directory.resolve() == directory
            raw, _ = command(phase+'-'+name, ['git','-c','safe.directory='+str(directory),'-C',str(directory),
                'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
            rows = raw.decode().splitlines()
            assert '# branch.oid '+revision in rows and all(row.startswith('# ') for row in rows), name+' source checkout changed'
        directory = Path(manifest['originalCoreRoot'])
        raw, _ = command(phase+'-torah-core', ['git','-c','safe.directory='+str(directory),'-C',str(directory),
            'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
        rows = raw.decode().splitlines()
        assert '# branch.oid '+manifest['originalCoreCommit'] in rows and all(row.startswith('# ') for row in rows), 'Core source checkout changed'

    try:
        assert result['minimumRootFreeBytes'] >= ROOT_ADMISSION, 'initial root 2 GiB plus 32 MiB admission'
        assert result['minimumDevelopmentFreeBytes'] >= DEVELOPMENT_ADMISSION, 'initial development budget admission'
        with open('/proc/meminfo','r',encoding='ascii') as source:
            memory_text = source.read(65537)
        assert len(memory_text) <= 65536
        available = re.findall(r'(?m)^MemAvailable:\s+([0-9]+)\s+kB$',memory_text)
        assert len(available) == 1 and int(available[0])*1024 >= 3*GIB, 'initial 3 GiB memory admission'
        result['initialMemAvailableBytes'] = int(available[0])*1024
        setup_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            output.mkdir(mode=0o700)
            owned_output = True
            output_info = output.lstat()
            owned_output_identity = tuple(getattr(output_info,key) for key in owned_output_identity_fields)
            for path in (output, output.parent):
                descriptor = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, setup_mask)
        save(output/'result.json', result)
        for name in ('temporary','module-cache','clang-module-cache','swift-cache','swift-config','swift-security','context-fixtures'):
            (output/name).mkdir(mode=0o700)
        # Clear inherited setgid only on the new fixture parent with its strict700 contract.
        os.chmod(output/'context-fixtures',0o700)
        require_empty_fixture_root(output/'context-fixtures')
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('PINKHA_', 'SWIFT_', 'SWIFTPM_', 'CLANG_', 'DYLD_', 'LD_'))}
        env.update(TMPDIR=str(output/'temporary'), SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
                   CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'), XDG_CACHE_HOME=str(output/'swift-cache'),
                   GIT_OPTIONAL_LOCKS='0', SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2')
        baseline = json.loads(base.read(BASELINE_INPUTS,maximum=131072))
        assert len(baseline) == 313
        project_root = Path(dependencies['originalProjectRoot'])
        for row in graph['sourceFiles'] + [pair['before'] for pair in graph['changedProduction']]:
            path = Path(row['sourcePath'])
            if path.is_relative_to(project_root):
                assert baseline[str(path.relative_to(project_root))] == row['sha256']
        for path, expected_sha in controls.items():
            base.pinned(path, expected_sha)
            immutable[str(path)] = base.row(path)
            original_modes[str(path)] = stat.S_IMODE(base.physical(path).lstat().st_mode)
        for path, row in graph_records.items():
            remember_input(Path(path), row)
        dependency_status('before', dependencies)
        helper = load_module(CRYPTO_HELPER, 'cold_bookmark_crypto', CRYPTO_HELPER_SHA, base)
        guard()
        reused = helper.qualify(output, base, guard)
        immutable.update(reused['immutableInputs'])
        copies.update(reused['copiedModules'])
        copies.update(reused['copiedHeaders'])
        copies[reused['receipt']['path']] = {key:reused['receipt'][key] for key in ('bytes','sha256')}
        guard()
        fixture_input_helper = load_module(FIXTURE_INPUTS, 'provider_fixture_inputs', FIXTURE_INPUTS_SHA, base)
        fixture_input_admission = fixture_input_helper.qualify(output/'source-fixtures', base, guard, immutable, copies)
        result['originalFixtureCustody'] = fixture_input_admission['receipt']
        guard()
        package = output/'package'
        package.mkdir(mode=0o700)

        def materialize(path, target, expected_row):
            remember_input(path, expected_row)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            base.copy_exact(path, target, {key:expected_row[key] for key in ('bytes','sha256')})
            descriptor = os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
            try:
                os.fchmod(descriptor,expected_row['mode'])
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            copies[str(target)] = base.row(target)
            copy_modes[str(target)] = stat.S_IMODE(target.lstat().st_mode)
            assert copy_modes[str(target)] == expected_row['mode']

        core_root = Path(dependencies['originalCoreRoot'])
        assert {str(path.relative_to(core_root)) for path in (core_root/'Sources/TorahInspectorCore').rglob('*.swift')} == {
            row['path'] for row in dependencies['originalCoreFiles']}
        for row in graph['sourceFiles']:
            source = Path(row['sourcePath'])
            target = package/row['isolatedPath']
            materialize(source,target,row)
            if row['kind'] != 'production':
                text = base.read(target,maximum=256*1024).decode('utf-8')
                declared = re.findall(r'\bfunc\s+(test\w+)\s*\(',text)
                classname = target.stem
                selected = EXPECTED_METHODS.get(classname,[])
                not_selected = EXCLUDED_METHODS.get(classname,[])
                assert len(declared) == len(set(declared))
                assert set(declared) == set(selected) | set(not_selected)
                assert not set(selected) & set(not_selected)
        expected_package_files = {row['isolatedPath'] for row in graph['sourceFiles']}
        assert {str(path.relative_to(package)) for path in package.rglob('*.swift')} == expected_package_files
        assert len(list((package/'Sources').rglob('*.swift'))) == 112
        assert len(list((package/'Tests/ColdBookmarkContractTests').glob('*.swift'))) == 6
        package_file = package/'Package.swift'
        package_bytes = package_text(reused['compilerFlags'], reused['linkObjects']).encode('utf-8')
        descriptor = os.open(package_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        try:
            view = memoryview(package_bytes)
            while view:
                written = os.write(descriptor,view)
                assert written > 0
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        copies[str(package_file)] = base.row(package_file)
        copy_modes[str(package_file)] = stat.S_IMODE(package_file.lstat().st_mode)
        source_admission_complete = True
        source_input_file = output/'compiled-source-inputs.json'
        save(source_input_file, {
            'originalInputs':immutable,'isolatedCopies':copies,
            'originalSourceModes':original_modes,'isolatedSourceModes':copy_modes,
            'counts':graph['counts'],'selectedMethods':EXPECTED_METHODS,'excludedMethods':EXCLUDED_METHODS,
            'graphSHA256':MANIFEST_SHA,'indexStore':'enabled; no disable-index-store flag',
            'noExistingProjectModuleImportDirectories':True})
        result['compiledSourceInputs'] = dict(path=str(source_input_file), **base.row(source_input_file))
        copies[str(source_input_file)] = {key:result['compiledSourceInputs'][key] for key in ('bytes','sha256')}
        filter_names = '|'.join(re.escape(name)+r'[/\.]'+re.escape(method)+r'$'
                                for name,methods in EXPECTED_METHODS.items() for method in methods)
        test_env = dict(env,
            PINKHA_IMPORTED_CONTEXT_FIXTURE_ROOT=str(output/'context-fixtures'),
            PINKHA_NATIVE_DEFINITION_RETAINED=fixture_input_admission['retainedDirectory'],
            PINKHA_NATIVE_ORIGINAL156=fixture_input_admission['originalDirectory'])
        argv = [reused['swiftDriver'],'test','--package-path',str(package),'--scratch-path',str(output/'build'),
                '--cache-path',str(output/'swift-cache'),'--config-path',str(output/'swift-config'),
                '--security-path',str(output/'swift-security'),'--disable-automatic-resolution','--jobs','2',
                '--filter',filter_names]
        raw, swift = command('swift-components', argv, package, test_env, SWIFT_SECONDS)
        log = raw.decode(errors='strict')
        starts = re.findall(r"Test Case '([^']+)' started", log)
        passes = re.findall(r"Test Case '([^']+)' passed", log)
        result['earlierTestStarts'] = [name for name in starts if name in excluded]
        result['earlierTestReplayStatus'] = 'NOT_RUN' if not result['earlierTestStarts'] else 'UNEXPECTED_COMPONENT_START'
        assert not result['earlierTestStarts']
        assert len(expected) == len(starts) == len(passes) == 22
        assert set(starts) == set(passes) == expected, 'actual XCTest inventory differs from the exact22 selected methods'
        assert all(starts.count(name) == passes.count(name) == 1 for name in expected)
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|Skipping XCTest discovery|XCTSkip", log)
        assert re.search(r'Executed 22 tests?, with 0 failures', log)
        result['actualMethods'] = {
            'started':starts,'passed':passes,'skipped':0,'total':22,
            'coldCheckpointAndLocator':9,'contentCorrespondence':5,'bookmark':6,'affectedPage':2,
            'historicalMethodsReused':0}
        require_empty_fixture_root(output/'context-fixtures')
        result['syntheticJournalFixtureRootEmpty'] = True
        result['retainedDependencyProducts'] = reused['receipt']
        product_closure = retained_products(output/'build', base, guard)
        result['compiledProducts'] = product_closure['files']
        result['compiledProductModes'] = product_closure['modes']
        result['compiledProductDirectories'] = product_closure['directories']
        result['compiledExecutables'] = product_closure['executables']
        result['compiledTestRunner'] = product_closure['testRunner']
        result['compiledProductsRoot'] = product_closure['root']
        dependency_status('after', dependencies)
        result['status'] = 'PASS'
    except BaseException as error:
        result['status'] = 'FAIL'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        owned.ignore_interrupts()
        final_deadline = time.monotonic()+120
        result['allStartedOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') is True for row in result['commands'])
        try:
            for path, expected_row in immutable.items():
                guard()
                assert base.row(Path(path)) == expected_row, path+' final original input mismatch'
            for path, expected_row in copies.items():
                guard()
                assert base.row(Path(path)) == expected_row, path+' final copied input mismatch'
            for path, mode in original_modes.items():
                assert stat.S_IMODE(base.physical(path).lstat().st_mode) == mode, path+' final original mode mismatch'
            for path, mode in copy_modes.items():
                assert stat.S_IMODE(Path(path).lstat().st_mode) == mode, path+' final copied mode mismatch'
            if source_admission_complete:
                package = output/'package'
                assert {str(path.relative_to(package)) for path in package.rglob('*.swift')} == expected_package_files | {'Package.swift'}
                result['compiledSourceModesAndMembershipUnchanged'] = True
            if 'compiledSourceInputs' in result:
                original = result['compiledSourceInputs']
                assert base.row(Path(original['path'])) == {key:original[key] for key in ('bytes','sha256')}
                result['compiledSourceInputsUnchanged'] = True
            if 'compiledProducts' in result:
                after_products = retained_products(output/'build', base, guard)
                assert after_products['root'] == result['compiledProductsRoot']
                assert after_products['files'] == result['compiledProducts']
                assert after_products['modes'] == result['compiledProductModes']
                assert after_products['directories'] == result['compiledProductDirectories']
                assert after_products['executables'] == result['compiledExecutables']
                assert after_products['testRunner'] == result['compiledTestRunner']
                result['compiledProductsAndModesUnchanged'] = True
            for path, expected_sha in controls.items():
                guard()
                base.pinned(path,expected_sha)
            assert admit_graph(base) == (graph,graph_records,dependencies)
            result['sourceGraphAndDonorUnchanged'] = True
            if reused is not None:
                helper.validate_after(reused,guard)
            if fixture_input_admission is not None:
                fixture_input_helper.validate_after(fixture_input_admission,base,guard)
                result['originalSourceFixtureInputsAndCopiesUnchanged'] = True
            result['admittedInputsUnchanged'] = True
            result['sourceUnchanged'] = source_admission_complete
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-integrity','type':type(error).__name__,'message':str(error)})
        try:
            swift_log = output/'commands/swift-components/original.log'
            if swift_log.exists():
                log = base.read(swift_log,maximum=LOG_CAP).decode(errors='replace')
                starts = re.findall(r"Test Case '([^']+)' started",log)
                passes = re.findall(r"Test Case '([^']+)' passed",log)
                fails = re.findall(r"Test Case '([^']+)' failed",log)
                skips = re.findall(r"Test Case '([^']+)' skipped",log)
                result['observedTestEvents'] = {'started':starts,'passed':passes,'failed':fails,'skipped':skips}
                result['earlierTestStarts'] = [name for name in starts if name in excluded]
                result['earlierTestReplayStatus'] = 'NOT_RUN' if not result['earlierTestStarts'] else 'UNEXPECTED_COMPONENT_START'
                assert not set(starts)-expected, 'unexpected method start outside the declared22'
            reason = observe()
            if reason is not None:
                raise RuntimeError(reason)
            assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup']
                       and not row['cleanupErrors'] and not row['signals'] for row in result['commands'])
            if result['status'] == 'PASS':
                assert len(result['commands']) == 7 and result['actualMethods']['total'] == 22
                assert result['sourceGraphAndDonorUnchanged'] is True
                assert result['compiledSourceModesAndMembershipUnchanged'] is True
                require_empty_fixture_root(output/'context-fixtures')
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-lifecycle-and-budget','type':type(error).__name__,'message':str(error)})
        try:
            result['seconds'] = round(time.monotonic()-started_at,3)
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-time-observation','type':type(error).__name__,'message':str(error)})
            result['seconds'] = None
        result['declaredControlledOutputBytesOnRoot'] = 0
        result['noGlobalRootWriteAuditClaim'] = True
        result['ownedOutputCreated'] = owned_output
        terminal_receipt = None
        terminal_sha256 = None
        if owned_output:
            try:
                output_info = base.physical(output).lstat()
                assert owned_output_identity is not None
                assert tuple(getattr(output_info,key) for key in owned_output_identity_fields) == owned_output_identity
                assert stat.S_ISDIR(output_info.st_mode), 'owned final output is not a directory'
                receipt_bytes = (json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
                assert len(receipt_bytes) <= RECEIPT_CAP
                save(output/'result.json',result)
                expected_receipt = {'bytes':len(receipt_bytes),'sha256':hashlib.sha256(receipt_bytes).hexdigest()}
                assert base.row(output/'result.json') == expected_receipt, 'final receipt byte identity'
                output_info = base.physical(output).lstat()
                assert tuple(getattr(output_info,key) for key in owned_output_identity_fields) == owned_output_identity
                terminal_receipt = str(output/'result.json')
                terminal_sha256 = expected_receipt['sha256']
            except BaseException as error:
                result['status'] = 'FAIL'
                result['errors'].append({'phase':'final-receipt-persistence-or-identity',
                                         'type':type(error).__name__,'message':str(error)})
                # The first terminal write may have reached disk. It is not a
                # qualified result after this error. Preserve it and report a
                # separately owned FAIL receipt; never rerun the workload.
                result['unqualifiedPrimaryReceipt'] = str(output/'result.json')
                try:
                    output_info = base.physical(output).lstat()
                    assert owned_output_identity is not None
                    assert tuple(getattr(output_info,key) for key in owned_output_identity_fields) == owned_output_identity
                    assert stat.S_ISDIR(output_info.st_mode), 'owned failure output is not a directory'
                    failure_receipt = output/'terminal-persistence-failure.json'
                    assert not os.path.lexists(failure_receipt), 'failure receipt already exists'
                    receipt_bytes = (json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
                    assert len(receipt_bytes) <= RECEIPT_CAP
                    save(failure_receipt,result)
                    expected_receipt = {'bytes':len(receipt_bytes),'sha256':hashlib.sha256(receipt_bytes).hexdigest()}
                    assert base.row(failure_receipt) == expected_receipt, 'failure receipt byte identity'
                    output_info = base.physical(output).lstat()
                    assert tuple(getattr(output_info,key) for key in owned_output_identity_fields) == owned_output_identity
                    terminal_receipt = str(failure_receipt)
                    terminal_sha256 = expected_receipt['sha256']
                except BaseException as fallback_error:
                    result['errors'].append({'phase':'final-failure-receipt-persistence-or-identity',
                                             'type':type(fallback_error).__name__,'message':str(fallback_error)})
    print(json.dumps({'status':result['status'],'receipt':terminal_receipt,
                      'sha256':terminal_sha256,'ownedOutputCreated':owned_output,
                      'seconds':result['seconds'],'errors':result['errors']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
