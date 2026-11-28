#!/usr/bin/env python3
"""One separately admitted continuation of only the two missing Swift Testing methods.
Uses the already-qualified Integration runner; no SwiftPM/build/copy/old-test replay.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode = True

ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
INPUTS = ROOT / 'inputs'
COMPONENT = ROOT / 'component'
SWIFT = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')
PRODUCT_COMMIT = '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'
CLEANUP_SHA = '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'
PROVENANCE_SHA = '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'
CRYPTO_SHA = '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'
SOURCE_CLOSURE_SHA = '38e924728ec19aedb3eda251d7cc2f60d538c46e553ee5dcb06a607d6c4947ce'
SOURCE_PINS = {'Package.swift': 'e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be', 'Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift': 'cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1', 'Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift': '048ebd2d82e3a22265c3fea4ead6ba406b4f8d7d8f00367ec0c7779fac1b0d8f', 'Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift': '7205b72e687975bfda695bcccbcdbdd486af45c13ef7f0ddd20fcf58c9d5a312', 'Sources/PinkhaAnyEngine/AnyHTTPClient.swift': '8fce86456dfdfd7237a999fb56b6dcdf6d0917c068a797ed5d9a88c5e33d5182', 'Sources/PinkhaAnyEngine/AnyJSON.swift': 'fb8937994d7db5728a7872386670eaeb2e74dcb84abba92814316bb3d458008d', 'Sources/PinkhaAnyEngine/AnyLiveQuery.swift': '445930138f7aefe46f6d41995059acafad9363178da4bc17574d2a0e399c8cf4', 'Sources/PinkhaAnyEngine/AnyNativeFileDurability.swift': '364a1bea4e4cae6134c9bb5935c0432f257657f3ae0c889a669354de975c2dc6', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadResponse.swift': '08635cd324835923b713674c359694a380005585cadd1de3075270f41ed0f6d2', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadStaging.swift': 'd0a02b1be20973b87c9be01bbf04e40f734f9ccddc39d0c4e61b83d1212bc349', 'Sources/PinkhaAnyEngine/AnyNativeFileUploader.swift': '83e4618ee93a04ce407a62926a0bffbb1752756a59b38e6e5e5d636bad9138a6', 'Sources/PinkhaAnyEngine/AnyObjectCreationUncertain.swift': 'c4635b23304e60b1d27b546c53e8901a841160bd79bd43a066b50bc02b2b0704', 'Sources/PinkhaAnyEngine/AnySSEParser.swift': '1b5b55f99d357418d0df7ec43bc61e8bac1e1f246c613019f8c8b025c03cbdad', 'Sources/PinkhaAnyEngine/AnyTorahClaimsRepository.swift': 'cd11b4cc0e54b4593d5a9111ca37ef7556bf3bcaa71ddb1532e900dd94ac0145', 'Sources/PinkhaAnyEngine/AnyTorahLiveQuery.swift': 'd2cdada5bf2a639127e58dbbe7b422188df76cb145d32023d4b1011006fd69af', 'Sources/PinkhaAnyEngine/AnyTorahOperation.swift': 'c5cdbf04c36554a1c4a74dc164014a3cc9bd33b201479702d7c1224d3d661980', 'Sources/PinkhaAnyHost/AnyApplicationSession.swift': 'ff7480f71e2d0bdbd8de5825aca391fcbe237ca37a07dfe7e3d8f859af860acd', 'Sources/PinkhaAnyHost/AnyDestinationAnchoredText.swift': '519b06bac9334e8483895daa66e3028e51a55347c543be55d59604a083f030b5', 'Sources/PinkhaAnyHost/AnyDestinationDefinitionCoverage.swift': 'e2095c83e1fe238184db7adf0220db40a5521ee9dca31302a810af203d59fbd4', 'Sources/PinkhaAnyHost/AnyDestinationImmutableRecordChecks.swift': 'c61c901522875690a5d5178b5583cf3a5e136d1a6ba448d0f9187d6fad6a6889', 'Sources/PinkhaAnyHost/AnyDestinationMigrationPlan.swift': 'cb1f3d9be09caa0c19f1242a1c6917a6cbf6fc60d000c1d2044a85b20efba13f', 'Sources/PinkhaAnyHost/AnyDestinationNativeMigration.swift': 'bab9be2ae8767f70239386b58eed452e5ea5bfd024d6a9003bb68cc8785efdf6', 'Sources/PinkhaAnyHost/AnyDestinationSystemCoverage.swift': 'ffc3caca0ed71a6a68671f5a0f94c7722e8c78ef6ce4ed237ccea247630381a6', 'Sources/PinkhaAnyHost/AnyEditorDocumentStore.swift': '1ea82b556e9f16b7903de03bbe435a249c6c922ade9798a01d648c8394c2604d', 'Sources/PinkhaAnyHost/AnyEditorSnapshot.swift': 'd2956d5e698631a7ab90c039b2647ac518da2dea224f4e01c59dd4ca0cf9ea9f', 'Sources/PinkhaAnyHost/AnyHostCanonical.swift': 'd234b3d87ab9ec8317f159d413eb140eb94c1ae0aa0b1e20f30391b4e51c4840', 'Sources/PinkhaAnyHost/AnyInlineMarkdown.swift': 'c537820797785b9f4f3bd00533706c16145c91e5f6999936a9b97243c4d9a483', 'Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift': '6bea1d2f1108cf737d68f91cf891c901e0140212b574aaf9e42fa63b392fd652', 'Sources/PinkhaAnyHost/AnyNativeBookmarkCreationFrame.swift': '498f37384519cc638a16b23d5c1f2b615d3228abb109dd7677a8006e15a9b116', 'Sources/PinkhaAnyHost/AnyNativeFileAttachmentCreator.swift': '704a3a50613129d966729e56491bdf17349bcbb9e0f977d5666867f39bf2d010', 'Sources/PinkhaAnyHost/AnyNativeFilePropertyFormat.swift': 'd068f7dc5ca478788a3457e7114da87b154bac46efacc89fe7a81401b7d887a1', 'Sources/PinkhaAnyHost/AnyNativeFileReference.swift': '19babf809e1c6c7ec8f517f89a9eb19f6e7a67e6ec743a02a5d523ab3aa5308f', 'Sources/PinkhaAnyHost/AnyNativeImportedDefaultMetadata.swift': 'b8ac71373d973d19b8d452a6f994087f2b8aa20245ce018ca4b46d776e996adb', 'Sources/PinkhaAnyHost/AnyNativeImportedTypeOrder.swift': '4516a77ba08a02fdfb714d58629c03deb62856e8a250114bbc913d41f45be5a2', 'Sources/PinkhaAnyHost/AnyNativeImportedTypePresentation.swift': '9cc30290575197f7cc2b8f3c8fdd700b8967223b035726f314ea11b2e1991e1a', 'Sources/PinkhaAnyHost/AnyNativeObjectCreator.swift': 'ae8faf092774401c595a63e389517aa2777fa83c9b2b9ffa31cc054355ed02f6', 'Sources/PinkhaAnyHost/AnyNativePreparedDefinitionMigration.swift': '8d44ac127127a59dc1826f3716b41948ee89f846c42221e35e4f7171476af925', 'Sources/PinkhaAnyHost/AnyNativePreparedFileMigration.swift': '16b230914002ef5700397e6596671ee201852d6bb962e63a519521f3b2d15009', 'Sources/PinkhaAnyHost/AnyNativePreparedImmutableRecord.swift': '83e543085c6911be85076f097eb55f3b054e24422378c32e99e5ab7dc1693e30', 'Sources/PinkhaAnyHost/AnyNativePreparedInlineFileMigration.swift': '4c134d514014b021bfd346ca93fe11f2cbc4af12ee6c263e9b42276e0065591f', 'Sources/PinkhaAnyHost/AnyNativePreparedMigration.swift': 'e8c0e084b0a18a7c4892529054f9b9d393d8cdd72d357aef4d330ea2a4ae059d', 'Sources/PinkhaAnyHost/AnyNativePreparedPropertyUpdate.swift': 'd2265107059c571af533fe0996b29dfafc7bc0ec3d63f46e46158319b37e3c9c', 'Sources/PinkhaAnyHost/AnyNativePropertyStore.swift': 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b', 'Sources/PinkhaAnyHost/AnyProtectedCreationJournal.swift': '5f0c526fa4f88e530242198bb152c3e1840cc5396df771420bff64f4183de8d5', 'Sources/PinkhaAnyIntegration/AnyConditionalPropertyFence.swift': 'baec5f9838f1bdbf6d6aedb557998cd334b3a77bbc73ce42f0c1408e14d40129', 'Sources/PinkhaAnyIntegration/AnyGuardedHTTPHierarchyRecordStore.swift': 'e07269b03f4ed48bea10db4cc237f4017aef30eab283192d1615c7b0696861bc', 'Sources/PinkhaAnyIntegration/AnyHTTPHierarchyRecordStore.swift': '7ede044c02fffbd4c0d9c9f81b78993af2ffce12ee9816e5703264200d82e963', 'Sources/PinkhaAnyIntegration/AnyHeartInlineProjection.swift': 'ecd9e751715263ab6c592be9d2cf22129d5e295c5b7510595ff5886d630529fe', 'Sources/PinkhaAnyIntegration/AnyHeartNativeBundledDefinition.swift': '524deb8119421132b0b802c7dfc40d0718a4e01235afc3e7697aa5c09ee79a3c', 'Sources/PinkhaAnyIntegration/AnyHeartNativeCompiledRelation.swift': 'abce8533e20f169fc431bd1d851d0c56fde878974d6eadef8a42fc1035de4096', 'Sources/PinkhaAnyIntegration/AnyHeartNativeDefinitionCatalog.swift': '437131d2f7095af0a450e7c695aa9c9bed13ea290f576d49870c5224b60a3965', 'Sources/PinkhaAnyIntegration/AnyHeartNativeRecoveredDefinitions.swift': 'de4b8b0596954a3f476bfff2c3af63b15f789d6ed17d806e54a2cd221c9bd449', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSnapshotView.swift': '8128c8e00ff10f4904ea1bf1638741a0de1d68565b8a2e30f9a8b5c97ebfc0d0', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSpaceBundle.swift': '9f7aa90550b3ab54cd86928a5c254b6f4af13762e14ce80fb62199f444879977', 'Sources/PinkhaAnyIntegration/AnyHeartNativeStoreContext.swift': '42617085d07295f4eb8a67973380d6a5174ef29bba4b9b29b1e58105d99c6a81', 'Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift': 'df4bf42404eaeed6be85dfe32779683e991a392dfa39c1726d58cfbefd255f5b', 'Sources/PinkhaAnyIntegration/AnyHierarchyModels.swift': '0a594737c72b9f065cd4e70aff425f521a6d7ff86ce7b1ebd21dd1221d150700', 'Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift': '59e3404dc4553bb842ed81a9cc39b7739fab47091e480f52e753653712405135', 'Sources/PinkhaAnyIntegration/AnyLexicographicPosition.swift': '079984b4d7aabdb375ca7bb466337db3f6282e5cd3f535ad8f8ae90b4ad86c73', 'Sources/PinkhaAnyIntegration/AnyNativeDocumentPolicy.swift': 'a4fa5fc4fc1185b1778ae960b60e39a03e3d4ce487c34bd4d69401946ff7e366', 'Sources/PinkhaAnyIntegration/AnyTorahSemanticAnchorMigration.swift': 'a8968f34c5f3af00537ba9b183ce0065ff7dadd31e55ca413dddc26fbe96728d', 'Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift': 'a40e49f4d3424e5625498e1a95baad171e22391a786d16c3f3e0c4c1ea926541', 'Sources/PinkhaAnyIntegration/AnyTorahWorkspace.swift': '7a51c02baafba146fac43ab0b5737ab3db6465ebdc142bce3d1a6ea33bf36c56', 'Sources/PinkhaKit/PinkhaHierarchyBuilder.swift': '7ac6eea3d287c43afd9849e82093466987764c518d81880208dd5452c4112b97', 'Sources/PinkhaKit/PinkhaHierarchyModels.swift': '7f201585eb76b34271e49fe686770302ece2d67d3e2ba4304167637ea0ddcb0b', 'Sources/PinkhaKit/PinkhaHierarchyMutationValidator.swift': '3f5f9e21035851c171ee5c64e4789048ce2fcf78163d839ef69155499fbf0d21', 'Sources/PinkhaKit/PinkhaHierarchyOrdering.swift': '7e33fc757c7c2888a8715fa7f110503bf9dc577ea06cf5bbbcd71e0793a9adf8', 'Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift': 'bfefc94965cfe6dbdf910452eaec3a9530854a6d5b6a09a1a9b10339c6c30274', 'Sources/PinkhaKit/TorahAssociationIdentity.swift': '85738df63c9ae987c1180c20e661cd21cd4acc20afcd376592f87ca32dcdb626', 'Sources/PinkhaKit/TorahAssociationModels.swift': '0007274a78d39fd4c8e0105eb50cec106c807cf53735caa0de1f4a85cd7fbde1', 'Sources/PinkhaKit/TorahAssociationPayloadCodec.swift': '9956aa25174812c5878927b5c62cff5f5d1d16e8becb536e23dadb25a01422d1', 'Sources/PinkhaKit/TorahAssociationRepository.swift': '63c789b1e14b85fb8032f2cf8fecb4fcb7e768453c03b9304e78ac77775fb66e', 'Sources/PinkhaKit/TorahCanonicalAssociations.swift': 'e5c988ebb64572e5228592f8a833ca8e5c2638fd991d0f7fc7e9bb114e4e3f3d', 'Sources/PinkhaKit/TorahSemanticAnchorAssociation.swift': '17c469ea127bf01211c7e819c00a2e15ea07facbe2c6d86505a5f0fce82cb3f4', 'Sources/PinkhaKit/TorahSourceJSONGuard.swift': 'ad856a6ed49f645ec2d5cb6a0bc3c7b6e7566c5cd7ad2a3081ccd748849ab9f6', 'Sources/TorahInspectorCore/Models.swift': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0', 'Sources/TorahInspectorCore/ProviderProtocols.swift': '9f5f28f1d71a97831827dce5dfe2324a60460fc7760137b9527e4c3815d20273', 'Sources/TorahInspectorCore/TorahInspectorCoordinator.swift': 'fccfc25ee56e165c6559aba52a1ccec39d10db6fd6a94a91c867cd38dc693116', 'Sources/TorahInspectorCore/TorahInspectorRepository.swift': '519828f3d602811758d2698e00a06567b41d31d465b143175441f08873300040', 'Sources/TorahInspectorCore/TorahReaderScrollStateMachine.swift': '90173f3198133c6a746d00c9a6af9ad8cd854f5643f924d98e9095133da5bbdc', 'Sources/TorahInspectorCore/TorahRelatedDocumentsAccessError.swift': '0ff22bb5a56ddff0235e7b6c5188c737b110cb2848d7e17dcaefc3ca1d6df2e6', 'Sources/TorahInspectorCore/TorahSourceTransfer.swift': '994da5da2cb6b163083c7f3dea20cfe74c781211eea0f144b394a6d047affc97', 'Sources/TorahInspectorCore/TorahToolSelectorStateMachine.swift': '34dda44a571764ea98e43449422340ad7a00dbe4b0d43c0036d7d48ad8119729', 'Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift': 'b80f20ccf77b4b0bb42043d18449f2b63d8001757e389a047011e6e3b43ba3b0', 'Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift': '4274837b7e8176bc7f768149f842b31e56765716f5219c2a7e6412378c43e75c'}
SWIFT_TESTING_METHODS = ('creationOverrideRejectsAnotherWorkspaceBeforeDispatch', 'creationOverrideAndDefaultCreatorShareTheExistingMutationQueue')
ROOT_FLOOR = 2 * 1024**3
DEVELOPMENT_FLOOR = 512 * 1024**2
ALLOCATION_CAP = 256 * 1024**2
FINAL_EVIDENCE_RESERVE = 1024**2
ADMISSION_MARGIN = 32 * 1024**2
MEMORY_FLOOR = 512 * 1024**2
SECONDS = 300
EVIDENCE = ROOT / 'continuation2'
PREVIOUS_EVIDENCE = ROOT / 'continuation1'
PREVIOUS_CONTROLLER_SHA256 = '0e8fa19767222fef6f954bf4bfdb34e58a77986251e69cf461b29f7311f01627'
PREVIOUS_CONTINUATION_PINS = {
    "command.json": {
        "bytes": 1649,
        "sha256": "b870c5387a23a6d6fd34336513329cf6ea98897653c47727c07843cfa42a61eb"
    },
    "immutable-witness-after.json": {
        "bytes": 162800,
        "sha256": "ce9a153b4656baf71f3fe316e758a9fd56a9fc2607ae6cd1674f2d05ce3a05b8"
    },
    "immutable-witness-before.json": {
        "bytes": 162800,
        "sha256": "ce9a153b4656baf71f3fe316e758a9fd56a9fc2607ae6cd1674f2d05ce3a05b8"
    },
    "immutable-witness-final.json": {
        "bytes": 162800,
        "sha256": "ce9a153b4656baf71f3fe316e758a9fd56a9fc2607ae6cd1674f2d05ce3a05b8"
    },
    "process.json": {
        "bytes": 102,
        "sha256": "d9551adcd2847702726d0a03c2bee1c000ff2cc1fc8271d942d6b1543f843c99"
    },
    "receipt.json": {
        "bytes": 4021,
        "sha256": "fe4dcf305e035f38b237b198e9db956aff63aa8bd8e4f34a6ff539f2b9d5bb64"
    },
    "resource-samples.json": {
        "bytes": 1253,
        "sha256": "3ae486e39c0bf501f71cd819aac41b32b1e15575c5caac8bac1e8fbe3565f3e9"
    },
    "stderr.original.log": {
        "bytes": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "stdout.original.log": {
        "bytes": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
}
ORIGINAL_ATTEMPT = ROOT / 'attempt1'
COMPLETION = ROOT / 'completion1.json'
COMPLETION_SHA256 = 'ac38377da08aac68629d2ae04f8d4878a52eb8b28ee3e1009700c810902302d7'
COMPLETION_BYTES = 589557
ORIGINAL_FAIL_SHA256 = '4441afb94ce64ef8656dd001ec040bee2cb69201eaddba16d2fc8e7a3d4fb556'
PRODUCTS = ROOT / 'build/out/Products/Debug-linux-aarch64'
RUNNER = PRODUCTS / 'PinkhaAnyIntegrationTests-test-runner'
RUNNER_SHA256 = 'c5334175861cc165de9751240d4532e2eea73d4ac850756074f7ffb150d91b34'
RUNNER_BYTES = 10805344
TEST_LIBRARY = PRODUCTS / 'PinkhaAnyIntegrationTests.so'
TEST_LIBRARY_SHA256 = '5eac396345bc469d9712ec7a776e10671652cc1366aa6f08b4269ff49f8f70ab'
TEST_LIBRARY_BYTES = 21171736
SWIFT_RUNTIME_LIBRARIES = SWIFT.parent.parent / 'lib/swift/linux'
TEST_FILTER = r'^PinkhaAnyIntegrationTests\.AnyHierarchyTests/(?:creationOverrideRejectsAnotherWorkspaceBeforeDispatch|creationOverrideAndDefaultCreatorShareTheExistingMutationQueue)\(\)/AnyHierarchyTests\.swift:[1-9][0-9]*:[1-9][0-9]*$'
owned_process = None

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

def verify_crypto(copies):
    for item in copies:
        pinned(Path(item['source']), item['sha256'], item['bytes'])
        pinned(Path(item['original']), item['sha256'], item['bytes'])
        pinned(Path(item['target']), item['sha256'], item['bytes'])
        assert Path(item['alias']).resolve(strict=True) == Path(item['original']).resolve(strict=True)

def load_original_process_helper():
    global owned_process
    path = INPUTS / 'owned_process.py'
    pinned(path, CLEANUP_SHA, 5529)
    spec = importlib.util.spec_from_file_location('owned_process', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owned_process = module
    return cleanup_custody()


def add_pin(pins, path, expected, size=None):
    path = Path(path)
    assert path.is_relative_to(ROOT) and '..' not in path.parts
    row = {'sha256': expected, 'bytes': size}
    if str(path) in pins:
        previous = pins[str(path)]
        assert previous['sha256'] == expected
        assert previous['bytes'] is None or size is None or previous['bytes'] == size
        row['bytes'] = previous['bytes'] if size is None else size
    pins[str(path)] = row


def retained_witness():
    raw = pinned(COMPLETION, COMPLETION_SHA256, COMPLETION_BYTES)
    value = json.loads(raw)
    assert value['status'] == 'QUALIFIED_COMPILER_CUSTODY_ONLY_ORIGINAL_SIX_METHOD_RESULT_FAIL'
    assert value['originalOverallStatus'] == 'FAIL' and value['sixMethodAcceptance'] is False
    assert value['originalReceiptSHA256'] == ORIGINAL_FAIL_SHA256 and not value['errors']
    assert value['actualCompletedJob']['id'] == 'job_81ac11c248c8'
    assert value['productSourceCommit'] == PRODUCT_COMMIT
    assert value['qualifiedCompilerScope'] == {
        'driverAndProductGroups': 9, 'originalSwiftSources': 84,
        'generatedSwiftSources': 4, 'actualCompiledSwiftInputs': 88,
        'generatedBytesIncluded': 40043, 'sourceAndLinkQualificationOnly': True,
        'testDispatchRootCauseEstablished': False}
    assert value['originalArtifactsBefore'] == value['originalArtifactsAfter']
    assert value['fixedInputAndCompiledSourceBefore'] == value['fixedInputAndCompiledSourceAfter']
    fixed = value['fixedInputAndCompiledSourceBefore']
    assert fixed['compiledCopy'] == SOURCE_PINS and len(fixed['inputRows']) == 90
    assert len(value['originalArtifactsBefore']) == 10
    pins = {}
    add_pin(pins, COMPLETION, COMPLETION_SHA256, COMPLETION_BYTES)
    for relative, row in value['originalArtifactsBefore'].items():
        add_pin(pins, ORIGINAL_ATTEMPT / relative, row['sha256'], row['bytes'])
    for relative, row in fixed['inputRows'].items():
        add_pin(pins, INPUTS / relative, row['sha256'], row['bytes'])
    for relative, expected in SOURCE_PINS.items():
        row = fixed['inputRows']['component/' + relative]
        assert row['sha256'] == expected
        add_pin(pins, COMPONENT / relative, expected, row['bytes'])
    groups = value['actualCompilerInputs']
    assert len(groups) == 9
    for group in groups:
        add_pin(pins, group['sourceList'], group['sourceListSHA256'], len(group['sourceListText'].encode('utf-8')))
        add_pin(pins, group['outputFileMap'], group['outputFileMapSHA256'])
        add_pin(pins, group['emittedModule'], group['emittedModuleSHA256'])
        for obj in group['objects']:
            add_pin(pins, obj['source'], obj['sourceSHA256'], obj['sourceBytes'])
            add_pin(pins, obj['object'], obj['objectSHA256'], obj['objectBytes'])
        link = group['actualLink']
        add_pin(pins, link['product'], link['productSHA256'], link['productBytes'])
        add_pin(pins, link['moduleObject'], link['moduleObjectSHA256'])
        add_pin(pins, link['linkFileList'], link['linkFileListSHA256'], len(link['linkFileListText'].encode('utf-8')))
        for row in link['linkedFiles'] + link['extraInputs']:
            add_pin(pins, row['path'], row['sha256'], row['bytes'])
        for row in group['generatedInputs']:
            assert row['text'].encode('utf-8') and len(row['text'].encode('utf-8')) == row['bytes']
            add_pin(pins, row['path'], row['sha256'], row['bytes'])
    assert pins[str(RUNNER)] == {'sha256': RUNNER_SHA256, 'bytes': RUNNER_BYTES}
    assert pins[str(TEST_LIBRARY)] == {'sha256': TEST_LIBRARY_SHA256, 'bytes': TEST_LIBRARY_BYTES}
    original = json.loads(pinned(ORIGINAL_ATTEMPT / 'receipt.json', ORIGINAL_FAIL_SHA256, 4923))
    assert original['status'] == 'FAIL' and original['processExit'] == 0
    assert original['ownedCleanup'] == value['originalAttempt']['originalPositiveClosure']
    assert original['ownedCleanup']['status'] == 'PASS_OWNED_GROUP_ABSENT'
    # This is historical metadata only. No process helper sees the old group.
    assert original['ownedCleanup']['absenceEvidence']['processGroup'] == 2634766
    copies = json.loads(pinned(ORIGINAL_ATTEMPT / 'actual-dependency-copies.json',
                              'd27dbe22d09ed5cfc6494d62092ee2db7890de4012b0873310f6cc7881138f78', 80991))
    assert len(copies) == 102 and sum(row['bytes'] for row in copies) == 19775715
    for row in copies:
        add_pin(pins, row['target'], row['sha256'], row['bytes'])
    # The failed direct attempt is immutable input, never a reused output.
    # Its closed process is historical metadata and never reaches a helper.
    for relative, authority in PREVIOUS_CONTINUATION_PINS.items():
        add_pin(pins, PREVIOUS_EVIDENCE / relative, authority['sha256'], authority['bytes'])
    previous_pin = PREVIOUS_CONTINUATION_PINS['receipt.json']
    previous = json.loads(pinned(PREVIOUS_EVIDENCE / 'receipt.json',
                                 previous_pin['sha256'], previous_pin['bytes']))
    assert previous['controllerSHA256'] == PREVIOUS_CONTROLLER_SHA256
    assert previous['status'] == 'FAIL' and previous['processExit'] == 69
    assert 'testResult' not in previous and previous['safeToReleaseRuntimeSlot'] is True
    assert previous['completionSHA256'] == COMPLETION_SHA256
    assert previous['originalReceiptSHA256'] == ORIGINAL_FAIL_SHA256
    assert previous['productCommit'] == PRODUCT_COMMIT
    assert previous['ownedCleanup']['status'] == 'PASS_OWNED_GROUP_ABSENT'
    assert previous['ownedCleanup']['absenceEvidence']['status'] == 'ABSENT_ESRCH'
    return value, pins, copies


def snapshot_witness(pins, copies):
    actual = {}
    for name, authority in sorted(pins.items()):
        path = Path(name)
        before = path.stat()
        raw = pinned(path, authority['sha256'], authority['bytes'])
        after = path.stat()
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), name
        actual[name] = {'bytes': len(raw), 'sha256': sha(raw),
                        'device': after.st_dev, 'inode': after.st_ino,
                        'mode': stat.S_IMODE(after.st_mode), 'mtimeNS': after.st_mtime_ns}
    assert source_inventory(INPUTS / 'component') == source_inventory(COMPONENT) == SOURCE_PINS
    verify_crypto(copies)
    return actual


def continuation_environment():
    # Exact Linux TestRunner requirements: product parent on the library path,
    # and NO_COLOR for captured output. The additional runtime directory is the
    # exact -L path in the qualified original runner link command.
    env = dict(os.environ)
    assert not env.get('LD_PRELOAD'), 'A preloaded unqualified library is not admitted'
    assert not env.get('SWIFT_TESTING_XCTEST_INTEROP_MODE'), 'Package6.0 has no default interop override'
    for path in (PRODUCTS, SWIFT_RUNTIME_LIBRARIES):
        assert path.is_dir() and path.resolve(strict=True) == path
    env.update(TMPDIR=str(EVIDENCE / 'tmp'), PYTHONDONTWRITEBYTECODE='1',
               GIT_TERMINAL_PROMPT='0', PWD=str(ROOT), PATH=str(SWIFT.parent) + ':/usr/bin:/bin',
               NO_COLOR='1', LD_LIBRARY_PATH=str(PRODUCTS) + ':' + str(SWIFT_RUNTIME_LIBRARIES))
    return env


def swift_testing_two_result(log):
    assert not any(text in log for text in ('Test Case ', 'Test Suite ', 'Executed ',
        'builtin-SwiftDriver', 'builtin-generateTestEntryPoint', 'SwiftCompile', 'Build complete!')), \
        'XCTest or build output is not part of this direct continuation'
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    method_start = re.compile(r'^◇ Test ([A-Za-z_][A-Za-z_0-9]*)\(\) started\.$')
    method_pass = re.compile(r'^✔ Test ([A-Za-z_][A-Za-z_0-9]*)\(\) passed after [0-9.]+ seconds\.$')
    swift_starts = {}; swift_passes = {}; swift_events = []
    for index, line in enumerate(lines):
        start = method_start.fullmatch(line)
        passed = method_pass.fullmatch(line)
        if start or passed:
            name = (start or passed).group(1)
            assert name in SWIFT_TESTING_METHODS, 'Unselected Swift Testing method'
            target = swift_starts if start else swift_passes
            assert name not in target, 'Duplicate Swift Testing event'
            target[name] = index
            swift_events.append(line)
        elif re.match(r'^[◇✔✘↷] Test (?!run )', line):
            raise AssertionError('Unknown, failed, skipped or parameterized Swift Testing event: ' + line)
    assert set(swift_starts) == set(swift_passes) == set(SWIFT_TESTING_METHODS), 'Both selected Swift Testing cases must pass'
    assert all(swift_starts[name] < swift_passes[name] for name in SWIFT_TESTING_METHODS)
    suite_name = 'Native wiki hierarchy preserves the original tree domain'
    swift_suite_start = '◇ Suite "' + suite_name + '" (aka \'AnyHierarchyTests\') started.'
    swift_suite_pass = re.escape('✔ Suite "' + suite_name + '" (aka \'AnyHierarchyTests\')') + r' passed after [0-9.]+ seconds\.'
    suite_lines = [(i, line) for i, line in enumerate(lines) if re.match(r'^[◇✔✘↷] Suite ', line)]
    assert len(suite_lines) == 2 and suite_lines[0][1] == swift_suite_start
    assert re.fullmatch(swift_suite_pass, suite_lines[1][1])
    assert suite_lines[0][0] < min(swift_starts.values()) <= max(swift_passes.values()) < suite_lines[1][0]
    totals = [(i, line) for i, line in enumerate(lines) if 'Test run with ' in line]
    assert len(totals) == 1 and re.fullmatch(r'✔ Test run with 2 tests in 1 suite passed after [0-9.]+ seconds\.', totals[0][1])
    assert totals[0][0] > suite_lines[1][0]
    starts = [i for i, line in enumerate(lines) if line == '◇ Test run started.']
    assert len(starts) == 1 and starts[0] < suite_lines[0][0]
    return {'actualSwiftTestingMethods': list(SWIFT_TESTING_METHODS), 'actualMethods': 2, 'actualCases': 2,
            'XCTestMethodsReplayed': 0, 'old27IntegrationMethodsExecuted': 0,
            'originalFourXCTestMethodsReplayed': 0, 'originalOverallReceiptStatus': 'FAIL',
            'observedLines': swift_events + [line for _, line in suite_lines] + [line for _, line in totals],
            'combinedSixMethodAcceptanceByThisReceipt': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-reviewed-missing-two', action='store_true')
    args = parser.parse_args()
    if not args.execute_reviewed_missing_two:
        print(json.dumps({'status': 'PREPARED_NOT_ADMITTED_OR_RUN', 'methods': list(SWIFT_TESTING_METHODS),
                          'originalOverallStatus': 'FAIL', 'runtimeSlotGrantedByThisScript': False}))
        return
    assert not sys.flags.optimize
    assert ROOT.is_dir() and ROOT.resolve(strict=True) == ROOT
    assert Path.cwd().resolve(strict=True) == ROOT and os.environ.get('PWD') == str(ROOT)
    assert ROOT.stat().st_uid == os.geteuid() and stat.S_IMODE(ROOT.stat().st_mode) == 0o700
    assert not EVIDENCE.exists() and not EVIDENCE.is_symlink(), 'Never reuse a continuation attempt'
    custody = load_original_process_helper()
    completion, pins, copies = retained_witness()
    before = snapshot_witness(pins, copies)
    initial = resource_sample(); require_budget(initial, admission=True)
    private_directory(EVIDENCE)
    receipt = {'schema': 'pinkha-bookmark-missing-two-continuation/v1', 'status': 'FAIL',
               'startedAtUTC': owned_process.now(), 'productCommit': PRODUCT_COMMIT,
               'controllerSHA256': sha(Path(__file__).read_bytes()),
               'completionSHA256': COMPLETION_SHA256, 'originalReceiptSHA256': ORIGINAL_FAIL_SHA256,
               'continuationNumber': 2,
               'priorContinuation': {'path': str(PREVIOUS_EVIDENCE), 'status': 'FAIL',
                   'controllerSHA256': PREVIOUS_CONTROLLER_SHA256,
                   'receiptSHA256': PREVIOUS_CONTINUATION_PINS['receipt.json']['sha256'],
                   'immutableOriginalFiles': len(PREVIOUS_CONTINUATION_PINS)},
               'originalOverallStatus': 'FAIL', 'originalFourXCTestMethodsReplayed': 0,
               'runtimeSlotGrantedByThisScript': False, 'safeToReleaseRuntimeSlot': False,
               'sourceBodiesModified': 0, 'compilerInvocations': 0, 'SwiftPMInvocations': 0,
               'nativeCalls': 0, 'AppleCalls': 0, 'automaticRetry': False,
               'budget': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEVELOPMENT_FLOOR,
                          'ownedAllocationCapBytes': ALLOCATION_CAP, 'admissionMarginBytes': ADMISSION_MARGIN,
                          'finalEvidenceReserveWithinCapBytes': FINAL_EVIDENCE_RESERVE,
                          'memoryFloorBytes': MEMORY_FLOOR, 'commandSeconds': SECONDS},
               'errors': []}
    samples = [initial]; process = None; state = {}; first = None
    started = time.monotonic()
    try:
        private_directory(EVIDENCE / 'tmp')
        write(EVIDENCE / 'immutable-witness-before.json', before)
        env = continuation_environment()
        argv = [str(RUNNER), '--testing-library', 'swift-testing', '--no-parallel', '--verbosity', '1', '--filter', TEST_FILTER]
        receipt['command'] = {'argv': argv, 'cwd': str(COMPONENT),
            'environmentOverrides': {k: env[k] for k in ('TMPDIR','PYTHONDONTWRITEBYTECODE','GIT_TERMINAL_PROMPT','PWD','PATH','NO_COLOR','LD_LIBRARY_PATH')},
            'runtimeRunner': {'path': str(RUNNER), 'bytes': RUNNER_BYTES, 'sha256': RUNNER_SHA256},
            'runtimeTestLibrary': {'path': str(TEST_LIBRARY), 'bytes': TEST_LIBRARY_BYTES, 'sha256': TEST_LIBRARY_SHA256}}
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
                    raise TimeoutError('Owned missing-two continuation exceeded 300 seconds')
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        receipt['processExit'] = process.returncode
        receipt['outerGroupAtExit'] = owned_process.observe_owned_group(process, state)
        assert receipt['outerGroupAtExit']['status'] == 'ABSENT_ESRCH'
        assert cleanup_custody() == custody
        after = snapshot_witness(pins, copies)
        assert after == before, 'Qualified original source/product identity changed'
        write(EVIDENCE / 'immutable-witness-after.json', after)
        log = (EVIDENCE / 'stdout.original.log').read_text(errors='strict') + '\n' + (EVIDENCE / 'stderr.original.log').read_text(errors='strict')
        assert process.returncode == 0, 'Direct Integration test-runner failed'
        receipt['testResult'] = swift_testing_two_result(log)
        receipt['status'] = 'PASS_MISSING_TWO_SWIFT_TESTING_METHODS_ONLY'
    except BaseException as error:
        first = error
        receipt['errors'].append({'phase': 'missing-two-continuation', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
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
            final = snapshot_witness(pins, copies)
            assert final == before, 'Final qualified original source/product identity changed'
            write(EVIDENCE / 'immutable-witness-final.json', final)
            assert cleanup_custody() == custody
            sample = resource_sample(); samples.append(sample); require_budget(sample)
            write(EVIDENCE / 'resource-samples.json', samples)
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
