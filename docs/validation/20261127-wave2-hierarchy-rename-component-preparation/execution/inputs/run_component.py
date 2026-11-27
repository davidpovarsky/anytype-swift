#!/usr/bin/env python3
"""One source-bound hierarchy rename component, four methods/eight argument cases.

Preparation is inert by default and does not grant a coordinated runtime slot.
All54 production bodies and the full27-method Integration test file are exact.
Only AnyHierarchyRawTitleTests is selected; old23 tests and Host2 are not replayed.
This is controlled-store Integration coverage, not HTTP/Native/Apple/account UI.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import owned_process

ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127')
INPUTS = ROOT / 'inputs'
COMPONENT = ROOT / 'component'
EVIDENCE = ROOT / 'attempt1'
SWIFT = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')
PRODUCT_COMMIT = '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'
CLEANUP_SHA = '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'
PROVENANCE_SHA = '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'
CRYPTO_SHA = '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'
SOURCE_CLOSURE_SHA = '510a00d5fb0065bcc5292d83443b9e4b6774f9dda4a7fd1d1d0ef4cfddeb8ca0'
SOURCE_PINS = {'Package.swift': 'bf6b4e867ea96c9fe8a51fb148867c33885b2c5ee335c07070cacb53d3ac305c', 'Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift': 'cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1', 'Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift': '048ebd2d82e3a22265c3fea4ead6ba406b4f8d7d8f00367ec0c7779fac1b0d8f', 'Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift': '7205b72e687975bfda695bcccbcdbdd486af45c13ef7f0ddd20fcf58c9d5a312', 'Sources/PinkhaAnyEngine/AnyHTTPClient.swift': '8fce86456dfdfd7237a999fb56b6dcdf6d0917c068a797ed5d9a88c5e33d5182', 'Sources/PinkhaAnyEngine/AnyJSON.swift': 'fb8937994d7db5728a7872386670eaeb2e74dcb84abba92814316bb3d458008d', 'Sources/PinkhaAnyEngine/AnyLiveQuery.swift': '445930138f7aefe46f6d41995059acafad9363178da4bc17574d2a0e399c8cf4', 'Sources/PinkhaAnyEngine/AnyNativeFileDurability.swift': '364a1bea4e4cae6134c9bb5935c0432f257657f3ae0c889a669354de975c2dc6', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadResponse.swift': '08635cd324835923b713674c359694a380005585cadd1de3075270f41ed0f6d2', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadStaging.swift': 'd0a02b1be20973b87c9be01bbf04e40f734f9ccddc39d0c4e61b83d1212bc349', 'Sources/PinkhaAnyEngine/AnyNativeFileUploader.swift': '83e4618ee93a04ce407a62926a0bffbb1752756a59b38e6e5e5d636bad9138a6', 'Sources/PinkhaAnyEngine/AnyObjectCreationUncertain.swift': 'c4635b23304e60b1d27b546c53e8901a841160bd79bd43a066b50bc02b2b0704', 'Sources/PinkhaAnyEngine/AnySSEParser.swift': '1b5b55f99d357418d0df7ec43bc61e8bac1e1f246c613019f8c8b025c03cbdad', 'Sources/PinkhaAnyEngine/AnyTorahClaimsRepository.swift': 'cd11b4cc0e54b4593d5a9111ca37ef7556bf3bcaa71ddb1532e900dd94ac0145', 'Sources/PinkhaAnyEngine/AnyTorahLiveQuery.swift': 'd2cdada5bf2a639127e58dbbe7b422188df76cb145d32023d4b1011006fd69af', 'Sources/PinkhaAnyEngine/AnyTorahOperation.swift': 'c5cdbf04c36554a1c4a74dc164014a3cc9bd33b201479702d7c1224d3d661980', 'Sources/PinkhaAnyIntegration/AnyConditionalPropertyFence.swift': 'baec5f9838f1bdbf6d6aedb557998cd334b3a77bbc73ce42f0c1408e14d40129', 'Sources/PinkhaAnyIntegration/AnyGuardedHTTPHierarchyRecordStore.swift': 'e07269b03f4ed48bea10db4cc237f4017aef30eab283192d1615c7b0696861bc', 'Sources/PinkhaAnyIntegration/AnyHTTPHierarchyRecordStore.swift': '7ede044c02fffbd4c0d9c9f81b78993af2ffce12ee9816e5703264200d82e963', 'Sources/PinkhaAnyIntegration/AnyHeartInlineProjection.swift': 'ecd9e751715263ab6c592be9d2cf22129d5e295c5b7510595ff5886d630529fe', 'Sources/PinkhaAnyIntegration/AnyHeartNativeBundledDefinition.swift': '524deb8119421132b0b802c7dfc40d0718a4e01235afc3e7697aa5c09ee79a3c', 'Sources/PinkhaAnyIntegration/AnyHeartNativeCompiledRelation.swift': 'abce8533e20f169fc431bd1d851d0c56fde878974d6eadef8a42fc1035de4096', 'Sources/PinkhaAnyIntegration/AnyHeartNativeDefinitionCatalog.swift': '437131d2f7095af0a450e7c695aa9c9bed13ea290f576d49870c5224b60a3965', 'Sources/PinkhaAnyIntegration/AnyHeartNativeRecoveredDefinitions.swift': 'de4b8b0596954a3f476bfff2c3af63b15f789d6ed17d806e54a2cd221c9bd449', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSnapshotView.swift': '8128c8e00ff10f4904ea1bf1638741a0de1d68565b8a2e30f9a8b5c97ebfc0d0', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSpaceBundle.swift': '9f7aa90550b3ab54cd86928a5c254b6f4af13762e14ce80fb62199f444879977', 'Sources/PinkhaAnyIntegration/AnyHeartNativeStoreContext.swift': '42617085d07295f4eb8a67973380d6a5174ef29bba4b9b29b1e58105d99c6a81', 'Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift': 'df4bf42404eaeed6be85dfe32779683e991a392dfa39c1726d58cfbefd255f5b', 'Sources/PinkhaAnyIntegration/AnyHierarchyModels.swift': '0a594737c72b9f065cd4e70aff425f521a6d7ff86ce7b1ebd21dd1221d150700', 'Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift': '7a1af6090a300a17e1427abb97423a49fbd26031d0578d17e6cba5f719016463', 'Sources/PinkhaAnyIntegration/AnyLexicographicPosition.swift': '079984b4d7aabdb375ca7bb466337db3f6282e5cd3f535ad8f8ae90b4ad86c73', 'Sources/PinkhaAnyIntegration/AnyNativeDocumentPolicy.swift': 'a4fa5fc4fc1185b1778ae960b60e39a03e3d4ce487c34bd4d69401946ff7e366', 'Sources/PinkhaAnyIntegration/AnyTorahSemanticAnchorMigration.swift': 'a8968f34c5f3af00537ba9b183ce0065ff7dadd31e55ca413dddc26fbe96728d', 'Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift': 'a40e49f4d3424e5625498e1a95baad171e22391a786d16c3f3e0c4c1ea926541', 'Sources/PinkhaAnyIntegration/AnyTorahWorkspace.swift': '7a51c02baafba146fac43ab0b5737ab3db6465ebdc142bce3d1a6ea33bf36c56', 'Sources/PinkhaKit/PinkhaHierarchyBuilder.swift': '7ac6eea3d287c43afd9849e82093466987764c518d81880208dd5452c4112b97', 'Sources/PinkhaKit/PinkhaHierarchyModels.swift': '7f201585eb76b34271e49fe686770302ece2d67d3e2ba4304167637ea0ddcb0b', 'Sources/PinkhaKit/PinkhaHierarchyMutationValidator.swift': '3f5f9e21035851c171ee5c64e4789048ce2fcf78163d839ef69155499fbf0d21', 'Sources/PinkhaKit/PinkhaHierarchyOrdering.swift': '7e33fc757c7c2888a8715fa7f110503bf9dc577ea06cf5bbbcd71e0793a9adf8', 'Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift': 'bfefc94965cfe6dbdf910452eaec3a9530854a6d5b6a09a1a9b10339c6c30274', 'Sources/PinkhaKit/TorahAssociationIdentity.swift': '85738df63c9ae987c1180c20e661cd21cd4acc20afcd376592f87ca32dcdb626', 'Sources/PinkhaKit/TorahAssociationModels.swift': '0007274a78d39fd4c8e0105eb50cec106c807cf53735caa0de1f4a85cd7fbde1', 'Sources/PinkhaKit/TorahAssociationPayloadCodec.swift': '9956aa25174812c5878927b5c62cff5f5d1d16e8becb536e23dadb25a01422d1', 'Sources/PinkhaKit/TorahAssociationRepository.swift': '63c789b1e14b85fb8032f2cf8fecb4fcb7e768453c03b9304e78ac77775fb66e', 'Sources/PinkhaKit/TorahCanonicalAssociations.swift': 'e5c988ebb64572e5228592f8a833ca8e5c2638fd991d0f7fc7e9bb114e4e3f3d', 'Sources/PinkhaKit/TorahSemanticAnchorAssociation.swift': '17c469ea127bf01211c7e819c00a2e15ea07facbe2c6d86505a5f0fce82cb3f4', 'Sources/PinkhaKit/TorahSourceJSONGuard.swift': 'ad856a6ed49f645ec2d5cb6a0bc3c7b6e7566c5cd7ad2a3081ccd748849ab9f6', 'Sources/TorahInspectorCore/Models.swift': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0', 'Sources/TorahInspectorCore/ProviderProtocols.swift': '9f5f28f1d71a97831827dce5dfe2324a60460fc7760137b9527e4c3815d20273', 'Sources/TorahInspectorCore/TorahInspectorCoordinator.swift': 'fccfc25ee56e165c6559aba52a1ccec39d10db6fd6a94a91c867cd38dc693116', 'Sources/TorahInspectorCore/TorahInspectorRepository.swift': '519828f3d602811758d2698e00a06567b41d31d465b143175441f08873300040', 'Sources/TorahInspectorCore/TorahReaderScrollStateMachine.swift': '90173f3198133c6a746d00c9a6af9ad8cd854f5643f924d98e9095133da5bbdc', 'Sources/TorahInspectorCore/TorahRelatedDocumentsAccessError.swift': '0ff22bb5a56ddff0235e7b6c5188c737b110cb2848d7e17dcaefc3ca1d6df2e6', 'Sources/TorahInspectorCore/TorahSourceTransfer.swift': '994da5da2cb6b163083c7f3dea20cfe74c781211eea0f144b394a6d047affc97', 'Sources/TorahInspectorCore/TorahToolSelectorStateMachine.swift': '34dda44a571764ea98e43449422340ad7a00dbe4b0d43c0036d7d48ad8119729', 'Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift': '3a11428238fabc27fc93f8cfb98535864dfbb7c2b09ae501c14f699d47b292c1'}
METHODS = ('canonicallyEquivalentRequestedRenameReachesTheOriginalStore', 'canonicallyEquivalentStaleExpectedTitleRefusesBeforeDispatch', 'canonicallyEquivalentSuccessfulReadbackCannotCertifyRename', 'canonicallyEquivalentReadbackPreservesTheOriginalWriteError')
SUITE = 'AnyHierarchyRawTitleTests'
TEST_FILTER = SUITE

ROOT_FLOOR = 2 * 1024**3
DEVELOPMENT_FLOOR = 512 * 1024**2
ALLOCATION_CAP = 256 * 1024**2
FINAL_EVIDENCE_RESERVE = 1024**2
ADMISSION_MARGIN = 32 * 1024**2
MEMORY_FLOOR = 512 * 1024**2
SECONDS = 300


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def pinned(path, expected, size=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.resolve(strict=True) == path, 'Physical path changed: ' + str(path)
    raw = path.read_bytes()
    assert sha(raw) == expected and (size is None or len(raw) == size), str(path)
    return raw


def source_inventory(folder):
    actual = {}
    for path in sorted(folder.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            actual[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    assert actual == SOURCE_PINS, 'Complete source/Package inventory changed'
    return actual


def cleanup_custody():
    assert Path(owned_process.__file__).resolve(strict=True) == INPUTS / 'owned_process.py'
    pinned(INPUTS / 'owned_process.py', CLEANUP_SHA)
    value = json.loads(pinned(INPUTS / 'owned-process-provenance.json', PROVENANCE_SHA))
    assert value['originalRunnerSHA256'] == '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'
    assert value['outputSHA256'] == CLEANUP_SHA
    return value


def allocated_bytes():
    total = ROOT.stat().st_blocks * 512
    for base, directories, files in os.walk(ROOT, followlinks=False):
        for name in directories + files:
            p = Path(base) / name
            if p.is_symlink():
                if p == ROOT / 'xdg-config/swiftpm/cache':
                    # The sole additional alias actually observed in attempt1;
                    # retain no-follow traversal and count this link only once.
                    target = ROOT / 'xdg-cache/org.swift.swiftpm'
                    assert os.readlink(p) == str(target) and p.resolve() == target, str(p)
                else:
                    # SwiftPM's debug/release convenience links stay inside this
                    # owned scratch tree; walk never follows them or counts twice.
                    assert p.is_relative_to(ROOT / 'build') and p.resolve().is_relative_to(ROOT / 'build'), str(p)
            total += p.lstat().st_blocks * 512
    return total


def resource_sample():
    memory = {line.split(':', 1)[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemAvailable:', 'SwapFree:'))}
    return {'atUTC': owned_process.now(), 'rootFreeBytes': shutil.disk_usage('/').free,
            'developmentFreeBytes': shutil.disk_usage(ROOT).free,
            'ownedAllocatedBytes': allocated_bytes(), 'memAvailableBytes': memory['MemAvailable'],
            'swapFreeBytes': memory['SwapFree'], 'load': os.getloadavg()}


def require_budget(sample, admission=False):
    assert sample['rootFreeBytes'] >= ROOT_FLOOR + (ADMISSION_MARGIN if admission else 0), 'Root floor'
    assert sample['developmentFreeBytes'] >= DEVELOPMENT_FLOOR + (ALLOCATION_CAP + ADMISSION_MARGIN if admission else 0), 'Development floor'
    assert sample['ownedAllocatedBytes'] <= ALLOCATION_CAP - FINAL_EVIDENCE_RESERVE, 'Whole owned allocation cap with final-evidence reserve'
    assert sample['memAvailableBytes'] >= MEMORY_FLOOR, 'Memory floor'


def private_directory(path):
    path.mkdir(mode=0o700)
    path.chmod(0o700)  # Only this newly created owned directory; inherited setgid is removed.
    current = path.stat()
    assert stat.S_IMODE(current.st_mode) == 0o700 and current.st_uid == os.geteuid()


def copy_crypto():
    closure = json.loads(pinned(INPUTS / 'retained-crypto-closure.json', CRYPTO_SHA))
    assert len(closure['files']) == 102
    destinations = {'swift-import': 'retained-crypto-imports',
                    'c-header-or-module-map': 'retained-crypto-headers',
                    'aggregated-link-object': 'retained-crypto-objects'}
    for name in destinations.values():
        private_directory(ROOT / name)
    result = []
    for row in closure['files']:
        source = Path(row['freshCopySourcePath'])
        original = Path(row['originalManifestPath'])
        alias = Path(row['actualOriginalPackageLinkerPath'] if row['kind'] == 'aggregated-link-object'
                     else row['recordedHistoricalAliasPath'])
        assert alias.resolve(strict=True) == original.resolve(strict=True), 'Historical alias changed; stop before borrowing dependencies'
        raw = pinned(source, row['sha256'], row['bytes'])
        assert pinned(original, row['sha256'], row['bytes']) == raw
        relative = Path(row['relativePath'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = ROOT / destinations[row['kind']] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        target.chmod(0o600)
        assert pinned(target, row['sha256'], row['bytes']) == raw
        result.append({'kind': row['kind'], 'source': str(source), 'original': str(original),
                       'alias': str(alias), 'target': str(target), 'sha256': row['sha256'], 'bytes': row['bytes']})
    assert sum(x['bytes'] for x in result) == 19_775_715
    return result


def verify_crypto(copies):
    for item in copies:
        pinned(Path(item['source']), item['sha256'], item['bytes'])
        pinned(Path(item['original']), item['sha256'], item['bytes'])
        pinned(Path(item['target']), item['sha256'], item['bytes'])
        assert Path(item['alias']).resolve(strict=True) == Path(item['original']).resolve(strict=True)


def compiler_inputs(log):
    assert 'Swift version 6.4.3 (swift-6.4.3-RELEASE)' in log
    assert 'aarch64-unknown-linux-gnu' in log
    # Exact layout observed with this same 6.4.3 compiler in retained source2
    # (4d4aaa998116af4ea4a31ba0ad9714a3dd4f56bc195632314f0fe2cd9ad9673d).
    # Generated test inputs are named individually, never admitted by directory.
    build = ROOT / 'build'
    project = build / 'out/Intermediates.noindex/HierarchyRawTitleProof.build/Debug-linux-aarch64'
    swiftc = str(SWIFT.with_name('swiftc'))
    test_module = 'PinkhaAnyIntegrationTests'
    runner_module = test_module + '_test_runner'
    anchor = project / (test_module + '-p.build/DerivedSources/test_anchor.swift')
    entry = project / (test_module + '-test-runner.build/DerivedSources/test_entry_point.swift')

    def physical(path, maximum=16 * 1024**2):
        assert path.is_relative_to(ROOT) and path.resolve(strict=True) == path, str(path)
        assert path.is_file() and not path.is_symlink(), str(path)
        raw = path.read_bytes()
        assert 0 < len(raw) <= maximum, str(path)
        return raw

    def value(argv, flag):
        assert argv.count(flag) == 1, (flag, argv)
        return argv[argv.index(flag) + 1]

    groups = {}
    for relative in SOURCE_PINS:
        parts = Path(relative).parts
        if len(parts) == 3 and parts[0] in ('Sources', 'Tests') and relative.endswith('.swift'):
            groups.setdefault(parts[1], set()).add(str(COMPONENT / relative))
    assert sum(len(x) for x in groups.values()) == 55 and len(groups) == 5
    groups[test_module].add(str(anchor))
    groups[runner_module] = {str(entry)}
    anchor_raw = physical(anchor)
    assert anchor_raw == b'public func __test_anchor_PinkhaAnyIntegrationTests() {}'
    entry_raw = physical(entry)
    entry_text = entry_raw.decode('utf-8')
    assert 'import PinkhaAnyIntegrationTests' in entry_text and '__test_anchor_PinkhaAnyIntegrationTests()' in entry_text
    assert 'struct __SwiftPMGeneratedTestRunner' in entry_text and 'XCTMain(__allDiscoveredTests())' in entry_text
    # The retained actual G04 run uses the same Swift6.4.3 Swift Testing entry
    # point with empty XCTest discovery. Only its two module-name literals vary.
    assert sha(entry_raw) == 'ef1ea588c48abfb9df451d79abb95237c2380da8b15cc97422bbfcccd532993b'
    assert 'await Testing.__swiftPMEntryPoint() as Never' in entry_text
    generated = {str(anchor): anchor_raw, str(entry): entry_raw}
    assert {str(p) for p in build.rglob('*.swift')} == set(generated), 'Unexpected generated Swift input'

    driver_lines = {}
    anchor_writes = []
    entry_generators = []
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.startswith('builtin-SwiftDriver -- '):
            argv = shlex.split(stripped)
            assert argv[:3] == ['builtin-SwiftDriver', '--', swiftc]
            module = value(argv, '-module-name')
            assert module in groups and module not in driver_lines, 'Unexpected or duplicate Swift driver'
            driver_lines[module] = (line, argv)
        elif stripped.startswith('write-file '):
            if shlex.split(stripped) == ['write-file', str(anchor)]:
                anchor_writes.append(line)
        elif stripped.startswith('builtin-generateTestEntryPoint '):
            argv = shlex.split(stripped)
            assert value(argv, '--output') == str(entry)
            assert '--discover-tests' in argv
            assert value(argv, '--test-anchor-module') == test_module
            assert value(argv, '--linker-file-list-format') == 'unixShellQuotedNewlineSeparated'
            assert value(argv, '--index-store-library-path') == str(SWIFT.parent.parent / 'lib/libIndexStore.so')
            assert value(argv, '--index-store') == str(build / 'out')
            assert value(argv, '--index-unit-base-path') == str(build / 'out/Intermediates.noindex')
            link_list = Path(value(argv, '--linker-filelist'))
            assert link_list == project / (test_module + '-p.build/Objects-normal/aarch64/' + test_module + '.LinkFileList')
            raw = physical(link_list)
            entry_generators.append({'actualCommandLine': line, 'linkerFileList': str(link_list),
                                     'linkerFileListSHA256': sha(raw), 'linkerFileListText': raw.decode('utf-8')})
    assert set(driver_lines) == set(groups) and len(anchor_writes) == len(entry_generators) == 1

    proof = []
    qualified_lists = set()
    for module, expected in sorted(groups.items()):
        if module == runner_module:
            stem, target = test_module + '-test-runner', test_module + '-test-runner.build'
        else:
            stem, target = module, module + ('-p.build' if module == test_module else '-t.build')
        object_root = project / target / 'Objects-normal/aarch64'
        source_list = object_root / (stem + '.SwiftFileList')
        source_list_raw = physical(source_list)
        sources = shlex.split(source_list_raw.decode('utf-8'))
        assert len(sources) == len(set(sources)) and set(sources) == expected, module
        qualified_lists.add(source_list)
        map_path = object_root / (stem + '-OutputFileMap.json')
        map_raw = physical(map_path)
        output_map = json.loads(map_raw)
        assert set(output_map) - {''} == expected, module
        line, argv = driver_lines[module]
        assert [arg for arg in argv if arg.startswith('@')] == ['@' + str(source_list)]
        assert value(argv, '-output-file-map') == str(map_path)
        assert value(argv, '-target') == 'aarch64-unknown-linux-gnu'
        assert value(argv, '-swift-version') == ('5' if module == runner_module else '6')
        assert value(argv, '-working-directory') == str(ROOT)
        assert '-j2' in argv and '-c' in argv and '-enable-testing' in argv
        module_path = object_root / 'Modules' / (module + '.swiftmodule')
        assert value(argv, '-emit-module-path') == str(module_path)
        module_raw = physical(module_path)
        objects = []
        for source in sorted(expected):
            source_raw = physical(Path(source))
            if source in generated:
                assert source_raw == generated[source]
            else:
                assert sha(source_raw) == SOURCE_PINS[Path(source).relative_to(COMPONENT).as_posix()]
            object_path = Path(output_map[source]['object'])
            assert object_path.is_relative_to(object_root) and object_path.suffix == '.o'
            raw = physical(object_path)
            objects.append({'source': source, 'sourceSHA256': sha(source_raw), 'sourceBytes': len(source_raw),
                            'generatedSource': source in generated,
                            'object': str(object_path), 'objectSHA256': sha(raw), 'objectBytes': len(raw)})
        proof.append({'module': module, 'sourceList': str(source_list),
                      'sourceListSHA256': sha(source_list_raw), 'sourceListText': source_list_raw.decode('utf-8'),
                      'outputFileMap': str(map_path), 'outputFileMapSHA256': sha(map_raw), 'outputFileMapValue': output_map,
                      'actualCompilerLines': [line], 'actualCompilerArgv': argv,
                      'emittedModule': str(module_path), 'emittedModuleSHA256': sha(module_raw),
                      'objects': objects,
                      'generatedInputs': [{'path': source, 'bytes': len(raw), 'sha256': sha(raw), 'text': raw.decode('utf-8'),
                                           'actualGeneration': anchor_writes if source == str(anchor) else entry_generators}
                                          for source, raw in generated.items() if source in expected]})
    assert set(build.rglob('*.SwiftFileList')) == qualified_lists, 'Unexpected compiler source list'
    return proof


def swift_testing_result(log):
    # Event grammar comes from retained, actually executed G04 Swift Testing6.4.3
    # stdout. Runtime descriptions of the private enum are retained as observed;
    # their exact spelling is not fabricated as a pre-execution compiled ID.
    lines = log.splitlines()
    assert not re.search(r"^Test Case '[^']+' started", log, re.M), 'Unexpected XCTest execution'
    assert not re.search(r'^.*(?:Test|Suite) .*\b(?:failed|skipped)\b', log, re.M), 'Failed or skipped test event'
    method_start = re.compile(r'^◇ Test ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) started\.$')
    method_pass = re.compile(r'^✔ Test ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) with 2 test cases passed after [0-9.]+ seconds\.$')
    case_event = re.compile(r'^(◇|✔) Test case passing 1 argument (.+) to ([A-Za-z_][A-Za-z_0-9]*)\(([^()\n]*)\) (started\.|passed after [0-9.]+ seconds\.)$')
    starts = {}; passes = {}; cases = {}; retained = []
    for offset, line in enumerate(lines):
        event = method_start.fullmatch(line)
        if event:
            name, signature = event.groups()
            assert name in METHODS and name not in starts, 'Unselected or duplicate method start'
            starts[name] = (signature, offset)
            retained.append(line)
            continue
        event = method_pass.fullmatch(line)
        if event:
            name, signature = event.groups()
            assert name in METHODS and name not in passes, 'Unselected or duplicate method PASS'
            passes[name] = (signature, offset)
            retained.append(line)
            continue
        event = case_event.fullmatch(line)
        if event:
            marker, argument, name, signature, outcome = event.groups()
            assert name in METHODS and argument.startswith('example → ') and len(argument) <= 2048
            assert (marker == '◇') == (outcome == 'started.'), 'Argument event status mismatch'
            assert name in starts and signature == starts[name][0]
            key = (name, argument)
            state = 'started' if marker == '◇' else 'passed'
            row = cases.setdefault(key, {})
            assert state not in row, 'Duplicate argument event'
            row[state] = offset
            retained.append(line)
            continue
        if re.match(r'^[◇✔✘↷] Test (?!run )', line):
            raise AssertionError('Unknown or unselected Swift Testing event: ' + line)
    assert set(starts) == set(passes) == set(METHODS), 'Require exactly the four selected actual method passes'
    assert len(cases) == 8, 'Require eight distinct actual argument cases, not declared count alone'
    actual = []
    for name in METHODS:
        assert starts[name][0] == passes[name][0]
        observed = [(argument, row) for (method, argument), row in cases.items() if method == name]
        assert len(observed) == 2, 'Each selected method must execute both distinct argument cases'
        for argument, row in observed:
            assert set(row) == {'started', 'passed'}
            assert starts[name][1] < row['started'] < row['passed'] < passes[name][1]
            actual.append({'method': name, 'actualEventSignature': name + '(' + starts[name][0] + ')',
                           'observedArgumentDescription': argument,
                           'startedLogLine': row['started'] + 1, 'passedLogLine': row['passed'] + 1})
    suite_name = 'Hierarchy rename preserves exact requested title bytes'
    suite_start = '◇ Suite "' + suite_name + '" (aka \'' + SUITE + '\') started.'
    suite_pass = re.escape('✔ Suite "' + suite_name + '" (aka \'' + SUITE + '\')') + r' passed after [0-9.]+ seconds\.'
    suite_lines = [(i, line) for i, line in enumerate(lines) if re.match(r'^[◇✔✘↷] Suite ', line)]
    assert len(suite_lines) == 2 and suite_lines[0][1] == suite_start
    assert re.fullmatch(suite_pass, suite_lines[1][1])
    assert suite_lines[0][0] < min(v[1] for v in starts.values())
    assert suite_lines[1][0] > max(v[1] for v in passes.values())
    totals = [(i, line) for i, line in enumerate(lines) if 'Test run with ' in line]
    assert len(totals) == 1 and re.fullmatch(r'✔ Test run with 4 tests in 1 suite passed after [0-9.]+ seconds\.', totals[0][1])
    assert totals[0][0] > suite_lines[1][0]
    return {'actualSwiftTestingMethods': list(METHODS), 'actualMethodCount': 4,
            'actualPassedArgumentCaseCount': 8, 'argumentCases': actual,
            'declaredSourceArgumentValues': ['latin', 'hebrew'],
            'argumentDescriptionSpellingIsObservedNotAnInventedCompiledSelector': True,
            'oldMethodsExecuted': 0, 'XCTestCases': 0, 'HTTPFixturesInvoked': 0,
            'observedTestOutcomeLines': retained + [line for _, line in suite_lines] + [totals[0][1]],
            'zeroXCTestOrSwiftTestingFooterIsNotAcceptance': True}











def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-reviewed-candidate', action='store_true')
    args = parser.parse_args()
    if not args.execute_reviewed_candidate:
        print(json.dumps({'status': 'PREPARED_NOT_ADMITTED_OR_RUN', 'productCommit': PRODUCT_COMMIT,
                          'methods': list(METHODS), 'runtimeSlotGrantedByThisScript': False}))
        return
    assert ROOT.is_dir() and ROOT.resolve(strict=True) == ROOT
    assert Path.cwd().resolve(strict=True) == ROOT and os.environ.get('PWD') == str(ROOT), 'Fixed ROOT launch cwd/PWD required'
    assert ROOT.stat().st_uid == os.geteuid() and stat.S_IMODE(ROOT.stat().st_mode) == 0o700
    assert set(p.name for p in ROOT.iterdir()) == {'inputs'}, 'Never reuse an existing attempt or output'
    assert Path(__file__).resolve(strict=True) == INPUTS / 'run_component.py'
    custody = cleanup_custody()
    source_inventory(INPUTS / 'component')
    pinned(INPUTS / 'whole-source-closure.json', SOURCE_CLOSURE_SHA)
    pinned(INPUTS / 'retained-crypto-closure.json', CRYPTO_SHA)
    initial = resource_sample(); require_budget(initial, admission=True)
    private_directory(EVIDENCE)
    receipt = {'schema': 'pinkha-hierarchy-raw-title-component/v1', 'status': 'FAIL',
               'startedAtUTC': owned_process.now(), 'productCommit': PRODUCT_COMMIT,
               'controllerSHA256': sha(Path(__file__).read_bytes()), 'sourceBodiesModifiedForComponent': 0,
               'nativeCalls': 0, 'AppleCalls': 0, 'runtimeSlotGrantedByThisScript': False,
               'noGlobalRootWriteAuditClaim': True, 'declaredControlledOutputBytesOnRoot': 0,
               'budget': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEVELOPMENT_FLOOR,
                          'ownedAllocationCapBytes': ALLOCATION_CAP, 'admissionMarginBytes': ADMISSION_MARGIN,
                          'finalEvidenceReserveWithinCapBytes': FINAL_EVIDENCE_RESERVE,
                          'memoryFloorBytes': MEMORY_FLOOR, 'commandSeconds': SECONDS, 'jobs': 2},
               'safeToReleaseRuntimeSlot': False, 'errors': []}
    samples = [initial]; process = None; state = {}; copies = []; log = ''; first = None
    started = time.monotonic()
    try:
        copies = copy_crypto(); write(EVIDENCE / 'actual-dependency-copies.json', copies)
        shutil.copytree(INPUTS / 'component', COMPONENT)
        before = source_inventory(COMPONENT); write(EVIDENCE / 'source-inputs-before.json', before)
        for name in ('tmp', 'swift-cache', 'swift-config', 'swift-security', 'clang-module-cache', 'swift-module-cache', 'xdg-cache', 'xdg-config'):
            private_directory(ROOT / name)
        env = dict(os.environ)
        env.update(TMPDIR=str(ROOT / 'tmp'), CLANG_MODULE_CACHE_PATH=str(ROOT / 'clang-module-cache'),
                   SWIFTPM_MODULECACHE_OVERRIDE=str(ROOT / 'swift-module-cache'),
                   XDG_CACHE_HOME=str(ROOT / 'xdg-cache'), XDG_CONFIG_HOME=str(ROOT / 'xdg-config'),
                   PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0', PWD=str(ROOT),
                   PATH=str(SWIFT.parent) + ':/usr/bin:/bin')
        # Keep all explicit source, module, object, cache, configuration, temporary and log paths on Development.
        argv = [str(SWIFT), 'test', '--package-path', str(COMPONENT), '--scratch-path', str(ROOT / 'build'),
                '--cache-path', str(ROOT / 'swift-cache'), '--config-path', str(ROOT / 'swift-config'),
                '--security-path', str(ROOT / 'swift-security'), '--disable-automatic-resolution',
                '--jobs', '2', '--no-parallel', '-v', '--filter', TEST_FILTER]
        receipt['command'] = {'argv': argv, 'cwd': str(COMPONENT), 'environmentOverrides': {k: env[k] for k in
            ('TMPDIR', 'CLANG_MODULE_CACHE_PATH', 'SWIFTPM_MODULECACHE_OVERRIDE', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'PYTHONDONTWRITEBYTECODE', 'GIT_TERMINAL_PROMPT', 'PWD', 'PATH')}}
        tool_binary = SWIFT.resolve(strict=True)
        receipt['actualToolchainExecutable'] = {'requestedPath': str(SWIFT), 'physicalPath': str(tool_binary),
                                               'bytes': tool_binary.stat().st_size, 'sha256': sha(tool_binary.read_bytes()),
                                               'versionAndTargetAuthority': 'Actual verbose compiler output is qualified after execution.'}
        write(EVIDENCE / 'command.json', receipt['command'])
        sample = resource_sample(); samples.append(sample); require_budget(sample)
        with (EVIDENCE / 'stdout.original.log').open('wb') as out, (EVIDENCE / 'stderr.original.log').open('wb') as err:
            process = subprocess.Popen(argv, cwd=COMPONENT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            write(EVIDENCE / 'process.json', {'pid': process.pid, 'processGroup': process.pid, 'startedAtUTC': owned_process.now()})
            deadline = time.monotonic() + SECONDS
            while process.poll() is None:
                sample = resource_sample(); samples.append(sample); require_budget(sample)
                if time.monotonic() >= deadline:
                    raise TimeoutError('Owned hierarchy rename command exceeded 300 seconds')
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        receipt['processExit'] = process.returncode
        receipt['outerGroupAtExit'] = owned_process.observe_owned_group(process, state)
        assert receipt['outerGroupAtExit']['status'] == 'ABSENT_ESRCH'
        after = source_inventory(COMPONENT)
        assert after == before == source_inventory(INPUTS / 'component')
        assert cleanup_custody() == custody
        verify_crypto(copies)
        write(EVIDENCE / 'source-inputs-after.json', after)
        log = (EVIDENCE / 'stdout.original.log').read_text(errors='replace') + '\n' + (EVIDENCE / 'stderr.original.log').read_text(errors='replace')
        assert process.returncode == 0, 'Actual Swift compiler/test command failed'
        receipt['testResult'] = swift_testing_result(log)
        receipt['compilerInputs'] = compiler_inputs(log)
        receipt['status'] = 'PASS_FOUR_SWIFT_TESTING_METHODS_EIGHT_ARGUMENT_CASES_HIERARCHY_COMPONENT_ONLY'
    except BaseException as error:
        first = error
        receipt['errors'].append({'phase': 'actual-component', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
    finally:
        if process is not None:
            try:
                owned_process.finish_owned_process(process, state, receipt)
            except BaseException as error:
                if first is None:
                    first = error
                receipt['status'] = 'FAIL'
                receipt['errors'].append({'phase': 'original-owned-cleanup', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
        try:
            write(EVIDENCE / 'source-inputs-final.json', {'inputs': source_inventory(INPUTS / 'component'),
                  'compiledCopy': source_inventory(COMPONENT) if COMPONENT.exists() else None})
            sample = resource_sample(); samples.append(sample); require_budget(sample)
            write(EVIDENCE / 'resource-samples.json', samples)
            if copies:
                verify_crypto(copies)
            receipt['safeToReleaseRuntimeSlot'] = (
                process is None or receipt.get('ownedCleanup', {}).get('status') == 'PASS_OWNED_GROUP_ABSENT')
        except BaseException as error:
            if first is None:
                first = error
            receipt['status'] = 'FAIL'
            receipt['errors'].append({'phase': 'retention-and-final-budget', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
        receipt['finishedAtUTC'] = owned_process.now()
        receipt['seconds'] = round(time.monotonic() - started, 3)
        receipt['maximumOwnedAllocatedBytes'] = max(x['ownedAllocatedBytes'] for x in samples)
        receipt['minimumRootFreeBytes'] = min(x['rootFreeBytes'] for x in samples)
        receipt['minimumDevelopmentFreeBytes'] = min(x['developmentFreeBytes'] for x in samples)
        try:
            write(EVIDENCE / 'receipt.json', receipt)
        except BaseException as error:
            if first is not None:
                first.add_note('Final receipt save also failed: ' + repr(error))
                raise first from error
            raise
        print(json.dumps({'status': receipt['status'], 'receipt': str(EVIDENCE / 'receipt.json'),
                          'receiptSHA256': sha((EVIDENCE / 'receipt.json').read_bytes()),
                          'safeToReleaseRuntimeSlot': receipt['safeToReleaseRuntimeSlot'],
                          'firstFailure': repr(first) if first else None}), flush=True)
    raise SystemExit(0 if receipt['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
