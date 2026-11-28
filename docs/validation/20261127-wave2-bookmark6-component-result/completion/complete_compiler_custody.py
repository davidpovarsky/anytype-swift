#!/usr/bin/env python3
"""Single read-only qualification of the already-closed Bookmark6 attempt.

No runner import, compiler/test invocation, process observation, Crypto copy or
runtime replay. The original six-method FAIL is immutable. The sole permitted
new file is ROOT/completion1.json. Run only after separate owner authorization.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import stat
import time
from datetime import datetime, timezone

ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')

INPUTS = ROOT / 'inputs'

COMPONENT = ROOT / 'component'

EVIDENCE = ROOT / 'attempt1'

SWIFT = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')

PRODUCT_COMMIT = '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'

CRYPTO_SHA = '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'

SOURCE_PINS = {'Package.swift': 'e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be', 'Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift': 'cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1', 'Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift': '048ebd2d82e3a22265c3fea4ead6ba406b4f8d7d8f00367ec0c7779fac1b0d8f', 'Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift': '7205b72e687975bfda695bcccbcdbdd486af45c13ef7f0ddd20fcf58c9d5a312', 'Sources/PinkhaAnyEngine/AnyHTTPClient.swift': '8fce86456dfdfd7237a999fb56b6dcdf6d0917c068a797ed5d9a88c5e33d5182', 'Sources/PinkhaAnyEngine/AnyJSON.swift': 'fb8937994d7db5728a7872386670eaeb2e74dcb84abba92814316bb3d458008d', 'Sources/PinkhaAnyEngine/AnyLiveQuery.swift': '445930138f7aefe46f6d41995059acafad9363178da4bc17574d2a0e399c8cf4', 'Sources/PinkhaAnyEngine/AnyNativeFileDurability.swift': '364a1bea4e4cae6134c9bb5935c0432f257657f3ae0c889a669354de975c2dc6', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadResponse.swift': '08635cd324835923b713674c359694a380005585cadd1de3075270f41ed0f6d2', 'Sources/PinkhaAnyEngine/AnyNativeFileUploadStaging.swift': 'd0a02b1be20973b87c9be01bbf04e40f734f9ccddc39d0c4e61b83d1212bc349', 'Sources/PinkhaAnyEngine/AnyNativeFileUploader.swift': '83e4618ee93a04ce407a62926a0bffbb1752756a59b38e6e5e5d636bad9138a6', 'Sources/PinkhaAnyEngine/AnyObjectCreationUncertain.swift': 'c4635b23304e60b1d27b546c53e8901a841160bd79bd43a066b50bc02b2b0704', 'Sources/PinkhaAnyEngine/AnySSEParser.swift': '1b5b55f99d357418d0df7ec43bc61e8bac1e1f246c613019f8c8b025c03cbdad', 'Sources/PinkhaAnyEngine/AnyTorahClaimsRepository.swift': 'cd11b4cc0e54b4593d5a9111ca37ef7556bf3bcaa71ddb1532e900dd94ac0145', 'Sources/PinkhaAnyEngine/AnyTorahLiveQuery.swift': 'd2cdada5bf2a639127e58dbbe7b422188df76cb145d32023d4b1011006fd69af', 'Sources/PinkhaAnyEngine/AnyTorahOperation.swift': 'c5cdbf04c36554a1c4a74dc164014a3cc9bd33b201479702d7c1224d3d661980', 'Sources/PinkhaAnyHost/AnyApplicationSession.swift': 'ff7480f71e2d0bdbd8de5825aca391fcbe237ca37a07dfe7e3d8f859af860acd', 'Sources/PinkhaAnyHost/AnyDestinationAnchoredText.swift': '519b06bac9334e8483895daa66e3028e51a55347c543be55d59604a083f030b5', 'Sources/PinkhaAnyHost/AnyDestinationDefinitionCoverage.swift': 'e2095c83e1fe238184db7adf0220db40a5521ee9dca31302a810af203d59fbd4', 'Sources/PinkhaAnyHost/AnyDestinationImmutableRecordChecks.swift': 'c61c901522875690a5d5178b5583cf3a5e136d1a6ba448d0f9187d6fad6a6889', 'Sources/PinkhaAnyHost/AnyDestinationMigrationPlan.swift': 'cb1f3d9be09caa0c19f1242a1c6917a6cbf6fc60d000c1d2044a85b20efba13f', 'Sources/PinkhaAnyHost/AnyDestinationNativeMigration.swift': 'bab9be2ae8767f70239386b58eed452e5ea5bfd024d6a9003bb68cc8785efdf6', 'Sources/PinkhaAnyHost/AnyDestinationSystemCoverage.swift': 'ffc3caca0ed71a6a68671f5a0f94c7722e8c78ef6ce4ed237ccea247630381a6', 'Sources/PinkhaAnyHost/AnyEditorDocumentStore.swift': '1ea82b556e9f16b7903de03bbe435a249c6c922ade9798a01d648c8394c2604d', 'Sources/PinkhaAnyHost/AnyEditorSnapshot.swift': 'd2956d5e698631a7ab90c039b2647ac518da2dea224f4e01c59dd4ca0cf9ea9f', 'Sources/PinkhaAnyHost/AnyHostCanonical.swift': 'd234b3d87ab9ec8317f159d413eb140eb94c1ae0aa0b1e20f30391b4e51c4840', 'Sources/PinkhaAnyHost/AnyInlineMarkdown.swift': 'c537820797785b9f4f3bd00533706c16145c91e5f6999936a9b97243c4d9a483', 'Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift': '6bea1d2f1108cf737d68f91cf891c901e0140212b574aaf9e42fa63b392fd652', 'Sources/PinkhaAnyHost/AnyNativeBookmarkCreationFrame.swift': '498f37384519cc638a16b23d5c1f2b615d3228abb109dd7677a8006e15a9b116', 'Sources/PinkhaAnyHost/AnyNativeFileAttachmentCreator.swift': '704a3a50613129d966729e56491bdf17349bcbb9e0f977d5666867f39bf2d010', 'Sources/PinkhaAnyHost/AnyNativeFilePropertyFormat.swift': 'd068f7dc5ca478788a3457e7114da87b154bac46efacc89fe7a81401b7d887a1', 'Sources/PinkhaAnyHost/AnyNativeFileReference.swift': '19babf809e1c6c7ec8f517f89a9eb19f6e7a67e6ec743a02a5d523ab3aa5308f', 'Sources/PinkhaAnyHost/AnyNativeImportedDefaultMetadata.swift': 'b8ac71373d973d19b8d452a6f994087f2b8aa20245ce018ca4b46d776e996adb', 'Sources/PinkhaAnyHost/AnyNativeImportedTypeOrder.swift': '4516a77ba08a02fdfb714d58629c03deb62856e8a250114bbc913d41f45be5a2', 'Sources/PinkhaAnyHost/AnyNativeImportedTypePresentation.swift': '9cc30290575197f7cc2b8f3c8fdd700b8967223b035726f314ea11b2e1991e1a', 'Sources/PinkhaAnyHost/AnyNativeObjectCreator.swift': 'ae8faf092774401c595a63e389517aa2777fa83c9b2b9ffa31cc054355ed02f6', 'Sources/PinkhaAnyHost/AnyNativePreparedDefinitionMigration.swift': '8d44ac127127a59dc1826f3716b41948ee89f846c42221e35e4f7171476af925', 'Sources/PinkhaAnyHost/AnyNativePreparedFileMigration.swift': '16b230914002ef5700397e6596671ee201852d6bb962e63a519521f3b2d15009', 'Sources/PinkhaAnyHost/AnyNativePreparedImmutableRecord.swift': '83e543085c6911be85076f097eb55f3b054e24422378c32e99e5ab7dc1693e30', 'Sources/PinkhaAnyHost/AnyNativePreparedInlineFileMigration.swift': '4c134d514014b021bfd346ca93fe11f2cbc4af12ee6c263e9b42276e0065591f', 'Sources/PinkhaAnyHost/AnyNativePreparedMigration.swift': 'e8c0e084b0a18a7c4892529054f9b9d393d8cdd72d357aef4d330ea2a4ae059d', 'Sources/PinkhaAnyHost/AnyNativePreparedPropertyUpdate.swift': 'd2265107059c571af533fe0996b29dfafc7bc0ec3d63f46e46158319b37e3c9c', 'Sources/PinkhaAnyHost/AnyNativePropertyStore.swift': 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b', 'Sources/PinkhaAnyHost/AnyProtectedCreationJournal.swift': '5f0c526fa4f88e530242198bb152c3e1840cc5396df771420bff64f4183de8d5', 'Sources/PinkhaAnyIntegration/AnyConditionalPropertyFence.swift': 'baec5f9838f1bdbf6d6aedb557998cd334b3a77bbc73ce42f0c1408e14d40129', 'Sources/PinkhaAnyIntegration/AnyGuardedHTTPHierarchyRecordStore.swift': 'e07269b03f4ed48bea10db4cc237f4017aef30eab283192d1615c7b0696861bc', 'Sources/PinkhaAnyIntegration/AnyHTTPHierarchyRecordStore.swift': '7ede044c02fffbd4c0d9c9f81b78993af2ffce12ee9816e5703264200d82e963', 'Sources/PinkhaAnyIntegration/AnyHeartInlineProjection.swift': 'ecd9e751715263ab6c592be9d2cf22129d5e295c5b7510595ff5886d630529fe', 'Sources/PinkhaAnyIntegration/AnyHeartNativeBundledDefinition.swift': '524deb8119421132b0b802c7dfc40d0718a4e01235afc3e7697aa5c09ee79a3c', 'Sources/PinkhaAnyIntegration/AnyHeartNativeCompiledRelation.swift': 'abce8533e20f169fc431bd1d851d0c56fde878974d6eadef8a42fc1035de4096', 'Sources/PinkhaAnyIntegration/AnyHeartNativeDefinitionCatalog.swift': '437131d2f7095af0a450e7c695aa9c9bed13ea290f576d49870c5224b60a3965', 'Sources/PinkhaAnyIntegration/AnyHeartNativeRecoveredDefinitions.swift': 'de4b8b0596954a3f476bfff2c3af63b15f789d6ed17d806e54a2cd221c9bd449', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSnapshotView.swift': '8128c8e00ff10f4904ea1bf1638741a0de1d68565b8a2e30f9a8b5c97ebfc0d0', 'Sources/PinkhaAnyIntegration/AnyHeartNativeSpaceBundle.swift': '9f7aa90550b3ab54cd86928a5c254b6f4af13762e14ce80fb62199f444879977', 'Sources/PinkhaAnyIntegration/AnyHeartNativeStoreContext.swift': '42617085d07295f4eb8a67973380d6a5174ef29bba4b9b29b1e58105d99c6a81', 'Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift': 'df4bf42404eaeed6be85dfe32779683e991a392dfa39c1726d58cfbefd255f5b', 'Sources/PinkhaAnyIntegration/AnyHierarchyModels.swift': '0a594737c72b9f065cd4e70aff425f521a6d7ff86ce7b1ebd21dd1221d150700', 'Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift': '59e3404dc4553bb842ed81a9cc39b7739fab47091e480f52e753653712405135', 'Sources/PinkhaAnyIntegration/AnyLexicographicPosition.swift': '079984b4d7aabdb375ca7bb466337db3f6282e5cd3f535ad8f8ae90b4ad86c73', 'Sources/PinkhaAnyIntegration/AnyNativeDocumentPolicy.swift': 'a4fa5fc4fc1185b1778ae960b60e39a03e3d4ce487c34bd4d69401946ff7e366', 'Sources/PinkhaAnyIntegration/AnyTorahSemanticAnchorMigration.swift': 'a8968f34c5f3af00537ba9b183ce0065ff7dadd31e55ca413dddc26fbe96728d', 'Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift': 'a40e49f4d3424e5625498e1a95baad171e22391a786d16c3f3e0c4c1ea926541', 'Sources/PinkhaAnyIntegration/AnyTorahWorkspace.swift': '7a51c02baafba146fac43ab0b5737ab3db6465ebdc142bce3d1a6ea33bf36c56', 'Sources/PinkhaKit/PinkhaHierarchyBuilder.swift': '7ac6eea3d287c43afd9849e82093466987764c518d81880208dd5452c4112b97', 'Sources/PinkhaKit/PinkhaHierarchyModels.swift': '7f201585eb76b34271e49fe686770302ece2d67d3e2ba4304167637ea0ddcb0b', 'Sources/PinkhaKit/PinkhaHierarchyMutationValidator.swift': '3f5f9e21035851c171ee5c64e4789048ce2fcf78163d839ef69155499fbf0d21', 'Sources/PinkhaKit/PinkhaHierarchyOrdering.swift': '7e33fc757c7c2888a8715fa7f110503bf9dc577ea06cf5bbbcd71e0793a9adf8', 'Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift': 'bfefc94965cfe6dbdf910452eaec3a9530854a6d5b6a09a1a9b10339c6c30274', 'Sources/PinkhaKit/TorahAssociationIdentity.swift': '85738df63c9ae987c1180c20e661cd21cd4acc20afcd376592f87ca32dcdb626', 'Sources/PinkhaKit/TorahAssociationModels.swift': '0007274a78d39fd4c8e0105eb50cec106c807cf53735caa0de1f4a85cd7fbde1', 'Sources/PinkhaKit/TorahAssociationPayloadCodec.swift': '9956aa25174812c5878927b5c62cff5f5d1d16e8becb536e23dadb25a01422d1', 'Sources/PinkhaKit/TorahAssociationRepository.swift': '63c789b1e14b85fb8032f2cf8fecb4fcb7e768453c03b9304e78ac77775fb66e', 'Sources/PinkhaKit/TorahCanonicalAssociations.swift': 'e5c988ebb64572e5228592f8a833ca8e5c2638fd991d0f7fc7e9bb114e4e3f3d', 'Sources/PinkhaKit/TorahSemanticAnchorAssociation.swift': '17c469ea127bf01211c7e819c00a2e15ea07facbe2c6d86505a5f0fce82cb3f4', 'Sources/PinkhaKit/TorahSourceJSONGuard.swift': 'ad856a6ed49f645ec2d5cb6a0bc3c7b6e7566c5cd7ad2a3081ccd748849ab9f6', 'Sources/TorahInspectorCore/Models.swift': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0', 'Sources/TorahInspectorCore/ProviderProtocols.swift': '9f5f28f1d71a97831827dce5dfe2324a60460fc7760137b9527e4c3815d20273', 'Sources/TorahInspectorCore/TorahInspectorCoordinator.swift': 'fccfc25ee56e165c6559aba52a1ccec39d10db6fd6a94a91c867cd38dc693116', 'Sources/TorahInspectorCore/TorahInspectorRepository.swift': '519828f3d602811758d2698e00a06567b41d31d465b143175441f08873300040', 'Sources/TorahInspectorCore/TorahReaderScrollStateMachine.swift': '90173f3198133c6a746d00c9a6af9ad8cd854f5643f924d98e9095133da5bbdc', 'Sources/TorahInspectorCore/TorahRelatedDocumentsAccessError.swift': '0ff22bb5a56ddff0235e7b6c5188c737b110cb2848d7e17dcaefc3ca1d6df2e6', 'Sources/TorahInspectorCore/TorahSourceTransfer.swift': '994da5da2cb6b163083c7f3dea20cfe74c781211eea0f144b394a6d047affc97', 'Sources/TorahInspectorCore/TorahToolSelectorStateMachine.swift': '34dda44a571764ea98e43449422340ad7a00dbe4b0d43c0036d7d48ad8119729', 'Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift': 'b80f20ccf77b4b0bb42043d18449f2b63d8001757e389a047011e6e3b43ba3b0', 'Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift': '4274837b7e8176bc7f768149f842b31e56765716f5219c2a7e6412378c43e75c'}

GENERATED_ENTRY_SHA256 = {'PinkhaAnyHostTests': '3ba4486f07a26bb0c71f7003aaa14f49954be57f5a3cd988ecb1c082e8487904', 'PinkhaAnyIntegrationTests': 'ef1ea588c48abfb9df451d79abb95237c2380da8b15cc97422bbfcccd532993b'}

ALLOCATION_CAP = 256 * 1024**2

ORIGINAL_CONTROLLER_SHA256 = '3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c'
ORIGINAL_CONTROLLER_BYTES = 48105
ORIGINAL_PACKET_SHA256 = '2341bdb226521d368b37f37c402c83b6bb20ae1db6efe4d7f65938198f5f1353'
ORIGINAL_CUSTODY_MANIFEST_SHA256 = '361e4a42407d65206945ab5732b83bdf35df9625c8ac01b96e08776353f6e1a9'
ORIGINAL_JOB = {'id': 'job_81ac11c248c8', 'host': 'host_299cf75f6b338ecd', 'status': 'failed', 'exit_code': 1, 'started_at': '2026-11-27T22:36:24.281237+00:00', 'finished_at': '2026-11-27T22:37:21.705140+00:00', 'duration_s': 57.42, 'retainedNotificationSHA256': '63ac4734b52c43d0aff38bc77b3d6d9fc553ad254b816f08665c306b2712e068'}
ORIGINAL_ARTIFACTS = {'actual-dependency-copies.json': {'bytes': 80991, 'sha256': 'd27dbe22d09ed5cfc6494d62092ee2db7890de4012b0873310f6cc7881138f78'}, 'command.json': {'bytes': 2022, 'sha256': '35f2b31ba614562563f8fd9379a4a744f1d8adf65bb5e57dc4df4fc1a94da9c7'}, 'process.json': {'bytes': 102, 'sha256': '42b16d9d635765b9f68b6d80eca3ef157f7e02ccf6c0c98d9223a621a7ba5109'}, 'receipt.json': {'bytes': 4923, 'sha256': '4441afb94ce64ef8656dd001ec040bee2cb69201eaddba16d2fc8e7a3d4fb556'}, 'resource-samples.json': {'bytes': 17603, 'sha256': '8adb251daf9c6e94f9dff72d9854c88df0b8e4e4ddfa382aef2d5c8b9d1e7a55'}, 'source-inputs-after.json': {'bytes': 10912, 'sha256': 'e1746b0ec408edf61f7cd7b2a6a035cbc44018167f7cc5a02d7520edc6a3f597'}, 'source-inputs-before.json': {'bytes': 10912, 'sha256': 'e1746b0ec408edf61f7cd7b2a6a035cbc44018167f7cc5a02d7520edc6a3f597'}, 'source-inputs-final.json': {'bytes': 22203, 'sha256': 'a26463168ecc3a9c990daf55fbdd7682f62d49bd90dc99ff0f6f4c39959f873f'}, 'stderr.original.log': {'bytes': 210554, 'sha256': '3129a86a2eba944743567e25b4e317182133cb8e37970d640088067008ca5ed0'}, 'stdout.original.log': {'bytes': 1701, 'sha256': 'bdd491647284cb881775720437223dc5d39c9314fcc1f1249c596646a1db7bdf'}}
INPUT_ENTRIES = {'component/Package.swift': {'bytes': 6987, 'sha256': 'e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be'}, 'component/Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift': {'bytes': 9870, 'sha256': 'cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1'}, 'component/Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift': {'bytes': 11996, 'sha256': '048ebd2d82e3a22265c3fea4ead6ba406b4f8d7d8f00367ec0c7779fac1b0d8f'}, 'component/Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift': {'bytes': 6644, 'sha256': '7205b72e687975bfda695bcccbcdbdd486af45c13ef7f0ddd20fcf58c9d5a312'}, 'component/Sources/PinkhaAnyEngine/AnyHTTPClient.swift': {'bytes': 27831, 'sha256': '8fce86456dfdfd7237a999fb56b6dcdf6d0917c068a797ed5d9a88c5e33d5182'}, 'component/Sources/PinkhaAnyEngine/AnyJSON.swift': {'bytes': 2600, 'sha256': 'fb8937994d7db5728a7872386670eaeb2e74dcb84abba92814316bb3d458008d'}, 'component/Sources/PinkhaAnyEngine/AnyLiveQuery.swift': {'bytes': 12640, 'sha256': '445930138f7aefe46f6d41995059acafad9363178da4bc17574d2a0e399c8cf4'}, 'component/Sources/PinkhaAnyEngine/AnyNativeFileDurability.swift': {'bytes': 6439, 'sha256': '364a1bea4e4cae6134c9bb5935c0432f257657f3ae0c889a669354de975c2dc6'}, 'component/Sources/PinkhaAnyEngine/AnyNativeFileUploadResponse.swift': {'bytes': 9648, 'sha256': '08635cd324835923b713674c359694a380005585cadd1de3075270f41ed0f6d2'}, 'component/Sources/PinkhaAnyEngine/AnyNativeFileUploadStaging.swift': {'bytes': 15355, 'sha256': 'd0a02b1be20973b87c9be01bbf04e40f734f9ccddc39d0c4e61b83d1212bc349'}, 'component/Sources/PinkhaAnyEngine/AnyNativeFileUploader.swift': {'bytes': 14691, 'sha256': '83e4618ee93a04ce407a62926a0bffbb1752756a59b38e6e5e5d636bad9138a6'}, 'component/Sources/PinkhaAnyEngine/AnyObjectCreationUncertain.swift': {'bytes': 2695, 'sha256': 'c4635b23304e60b1d27b546c53e8901a841160bd79bd43a066b50bc02b2b0704'}, 'component/Sources/PinkhaAnyEngine/AnySSEParser.swift': {'bytes': 10163, 'sha256': '1b5b55f99d357418d0df7ec43bc61e8bac1e1f246c613019f8c8b025c03cbdad'}, 'component/Sources/PinkhaAnyEngine/AnyTorahClaimsRepository.swift': {'bytes': 13237, 'sha256': 'cd11b4cc0e54b4593d5a9111ca37ef7556bf3bcaa71ddb1532e900dd94ac0145'}, 'component/Sources/PinkhaAnyEngine/AnyTorahLiveQuery.swift': {'bytes': 3828, 'sha256': 'd2cdada5bf2a639127e58dbbe7b422188df76cb145d32023d4b1011006fd69af'}, 'component/Sources/PinkhaAnyEngine/AnyTorahOperation.swift': {'bytes': 12417, 'sha256': 'c5cdbf04c36554a1c4a74dc164014a3cc9bd33b201479702d7c1224d3d661980'}, 'component/Sources/PinkhaAnyHost/AnyApplicationSession.swift': {'bytes': 5633, 'sha256': 'ff7480f71e2d0bdbd8de5825aca391fcbe237ca37a07dfe7e3d8f859af860acd'}, 'component/Sources/PinkhaAnyHost/AnyDestinationAnchoredText.swift': {'bytes': 2574, 'sha256': '519b06bac9334e8483895daa66e3028e51a55347c543be55d59604a083f030b5'}, 'component/Sources/PinkhaAnyHost/AnyDestinationDefinitionCoverage.swift': {'bytes': 27878, 'sha256': 'e2095c83e1fe238184db7adf0220db40a5521ee9dca31302a810af203d59fbd4'}, 'component/Sources/PinkhaAnyHost/AnyDestinationImmutableRecordChecks.swift': {'bytes': 3645, 'sha256': 'c61c901522875690a5d5178b5583cf3a5e136d1a6ba448d0f9187d6fad6a6889'}, 'component/Sources/PinkhaAnyHost/AnyDestinationMigrationPlan.swift': {'bytes': 40052, 'sha256': 'cb1f3d9be09caa0c19f1242a1c6917a6cbf6fc60d000c1d2044a85b20efba13f'}, 'component/Sources/PinkhaAnyHost/AnyDestinationNativeMigration.swift': {'bytes': 23299, 'sha256': 'bab9be2ae8767f70239386b58eed452e5ea5bfd024d6a9003bb68cc8785efdf6'}, 'component/Sources/PinkhaAnyHost/AnyDestinationSystemCoverage.swift': {'bytes': 4116, 'sha256': 'ffc3caca0ed71a6a68671f5a0f94c7722e8c78ef6ce4ed237ccea247630381a6'}, 'component/Sources/PinkhaAnyHost/AnyEditorDocumentStore.swift': {'bytes': 11711, 'sha256': '1ea82b556e9f16b7903de03bbe435a249c6c922ade9798a01d648c8394c2604d'}, 'component/Sources/PinkhaAnyHost/AnyEditorSnapshot.swift': {'bytes': 8318, 'sha256': 'd2956d5e698631a7ab90c039b2647ac518da2dea224f4e01c59dd4ca0cf9ea9f'}, 'component/Sources/PinkhaAnyHost/AnyHostCanonical.swift': {'bytes': 2773, 'sha256': 'd234b3d87ab9ec8317f159d413eb140eb94c1ae0aa0b1e20f30391b4e51c4840'}, 'component/Sources/PinkhaAnyHost/AnyInlineMarkdown.swift': {'bytes': 41061, 'sha256': 'c537820797785b9f4f3bd00533706c16145c91e5f6999936a9b97243c4d9a483'}, 'component/Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift': {'bytes': 12014, 'sha256': '6bea1d2f1108cf737d68f91cf891c901e0140212b574aaf9e42fa63b392fd652'}, 'component/Sources/PinkhaAnyHost/AnyNativeBookmarkCreationFrame.swift': {'bytes': 10591, 'sha256': '498f37384519cc638a16b23d5c1f2b615d3228abb109dd7677a8006e15a9b116'}, 'component/Sources/PinkhaAnyHost/AnyNativeFileAttachmentCreator.swift': {'bytes': 23257, 'sha256': '704a3a50613129d966729e56491bdf17349bcbb9e0f977d5666867f39bf2d010'}, 'component/Sources/PinkhaAnyHost/AnyNativeFilePropertyFormat.swift': {'bytes': 1927, 'sha256': 'd068f7dc5ca478788a3457e7114da87b154bac46efacc89fe7a81401b7d887a1'}, 'component/Sources/PinkhaAnyHost/AnyNativeFileReference.swift': {'bytes': 2019, 'sha256': '19babf809e1c6c7ec8f517f89a9eb19f6e7a67e6ec743a02a5d523ab3aa5308f'}, 'component/Sources/PinkhaAnyHost/AnyNativeImportedDefaultMetadata.swift': {'bytes': 4547, 'sha256': 'b8ac71373d973d19b8d452a6f994087f2b8aa20245ce018ca4b46d776e996adb'}, 'component/Sources/PinkhaAnyHost/AnyNativeImportedTypeOrder.swift': {'bytes': 3865, 'sha256': '4516a77ba08a02fdfb714d58629c03deb62856e8a250114bbc913d41f45be5a2'}, 'component/Sources/PinkhaAnyHost/AnyNativeImportedTypePresentation.swift': {'bytes': 8198, 'sha256': '9cc30290575197f7cc2b8f3c8fdd700b8967223b035726f314ea11b2e1991e1a'}, 'component/Sources/PinkhaAnyHost/AnyNativeObjectCreator.swift': {'bytes': 19634, 'sha256': 'ae8faf092774401c595a63e389517aa2777fa83c9b2b9ffa31cc054355ed02f6'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedDefinitionMigration.swift': {'bytes': 19838, 'sha256': '8d44ac127127a59dc1826f3716b41948ee89f846c42221e35e4f7171476af925'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedFileMigration.swift': {'bytes': 15234, 'sha256': '16b230914002ef5700397e6596671ee201852d6bb962e63a519521f3b2d15009'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedImmutableRecord.swift': {'bytes': 18393, 'sha256': '83e543085c6911be85076f097eb55f3b054e24422378c32e99e5ab7dc1693e30'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedInlineFileMigration.swift': {'bytes': 13543, 'sha256': '4c134d514014b021bfd346ca93fe11f2cbc4af12ee6c263e9b42276e0065591f'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedMigration.swift': {'bytes': 18794, 'sha256': 'e8c0e084b0a18a7c4892529054f9b9d393d8cdd72d357aef4d330ea2a4ae059d'}, 'component/Sources/PinkhaAnyHost/AnyNativePreparedPropertyUpdate.swift': {'bytes': 12743, 'sha256': 'd2265107059c571af533fe0996b29dfafc7bc0ec3d63f46e46158319b37e3c9c'}, 'component/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift': {'bytes': 53698, 'sha256': 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b'}, 'component/Sources/PinkhaAnyHost/AnyProtectedCreationJournal.swift': {'bytes': 17368, 'sha256': '5f0c526fa4f88e530242198bb152c3e1840cc5396df771420bff64f4183de8d5'}, 'component/Sources/PinkhaAnyIntegration/AnyConditionalPropertyFence.swift': {'bytes': 2695, 'sha256': 'baec5f9838f1bdbf6d6aedb557998cd334b3a77bbc73ce42f0c1408e14d40129'}, 'component/Sources/PinkhaAnyIntegration/AnyGuardedHTTPHierarchyRecordStore.swift': {'bytes': 7638, 'sha256': 'e07269b03f4ed48bea10db4cc237f4017aef30eab283192d1615c7b0696861bc'}, 'component/Sources/PinkhaAnyIntegration/AnyHTTPHierarchyRecordStore.swift': {'bytes': 11318, 'sha256': '7ede044c02fffbd4c0d9c9f81b78993af2ffce12ee9816e5703264200d82e963'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartInlineProjection.swift': {'bytes': 2949, 'sha256': 'ecd9e751715263ab6c592be9d2cf22129d5e295c5b7510595ff5886d630529fe'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeBundledDefinition.swift': {'bytes': 3335, 'sha256': '524deb8119421132b0b802c7dfc40d0718a4e01235afc3e7697aa5c09ee79a3c'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeCompiledRelation.swift': {'bytes': 5012, 'sha256': 'abce8533e20f169fc431bd1d851d0c56fde878974d6eadef8a42fc1035de4096'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeDefinitionCatalog.swift': {'bytes': 23399, 'sha256': '437131d2f7095af0a450e7c695aa9c9bed13ea290f576d49870c5224b60a3965'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeRecoveredDefinitions.swift': {'bytes': 13436, 'sha256': 'de4b8b0596954a3f476bfff2c3af63b15f789d6ed17d806e54a2cd221c9bd449'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeSnapshotView.swift': {'bytes': 12396, 'sha256': '8128c8e00ff10f4904ea1bf1638741a0de1d68565b8a2e30f9a8b5c97ebfc0d0'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeSpaceBundle.swift': {'bytes': 23124, 'sha256': '9f7aa90550b3ab54cd86928a5c254b6f4af13762e14ce80fb62199f444879977'}, 'component/Sources/PinkhaAnyIntegration/AnyHeartNativeStoreContext.swift': {'bytes': 18654, 'sha256': '42617085d07295f4eb8a67973380d6a5174ef29bba4b9b29b1e58105d99c6a81'}, 'component/Sources/PinkhaAnyIntegration/AnyHierarchyArchiveRequest.swift': {'bytes': 2424, 'sha256': 'df4bf42404eaeed6be85dfe32779683e991a392dfa39c1726d58cfbefd255f5b'}, 'component/Sources/PinkhaAnyIntegration/AnyHierarchyModels.swift': {'bytes': 16048, 'sha256': '0a594737c72b9f065cd4e70aff425f521a6d7ff86ce7b1ebd21dd1221d150700'}, 'component/Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift': {'bytes': 22719, 'sha256': '59e3404dc4553bb842ed81a9cc39b7739fab47091e480f52e753653712405135'}, 'component/Sources/PinkhaAnyIntegration/AnyLexicographicPosition.swift': {'bytes': 8273, 'sha256': '079984b4d7aabdb375ca7bb466337db3f6282e5cd3f535ad8f8ae90b4ad86c73'}, 'component/Sources/PinkhaAnyIntegration/AnyNativeDocumentPolicy.swift': {'bytes': 6882, 'sha256': 'a4fa5fc4fc1185b1778ae960b60e39a03e3d4ce487c34bd4d69401946ff7e366'}, 'component/Sources/PinkhaAnyIntegration/AnyTorahSemanticAnchorMigration.swift': {'bytes': 1870, 'sha256': 'a8968f34c5f3af00537ba9b183ce0065ff7dadd31e55ca413dddc26fbe96728d'}, 'component/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift': {'bytes': 1537, 'sha256': 'a40e49f4d3424e5625498e1a95baad171e22391a786d16c3f3e0c4c1ea926541'}, 'component/Sources/PinkhaAnyIntegration/AnyTorahWorkspace.swift': {'bytes': 10327, 'sha256': '7a51c02baafba146fac43ab0b5737ab3db6465ebdc142bce3d1a6ea33bf36c56'}, 'component/Sources/PinkhaKit/PinkhaHierarchyBuilder.swift': {'bytes': 3339, 'sha256': '7ac6eea3d287c43afd9849e82093466987764c518d81880208dd5452c4112b97'}, 'component/Sources/PinkhaKit/PinkhaHierarchyModels.swift': {'bytes': 5447, 'sha256': '7f201585eb76b34271e49fe686770302ece2d67d3e2ba4304167637ea0ddcb0b'}, 'component/Sources/PinkhaKit/PinkhaHierarchyMutationValidator.swift': {'bytes': 1804, 'sha256': '3f5f9e21035851c171ee5c64e4789048ce2fcf78163d839ef69155499fbf0d21'}, 'component/Sources/PinkhaKit/PinkhaHierarchyOrdering.swift': {'bytes': 6164, 'sha256': '7e33fc757c7c2888a8715fa7f110503bf9dc577ea06cf5bbbcd71e0793a9adf8'}, 'component/Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift': {'bytes': 16150, 'sha256': 'bfefc94965cfe6dbdf910452eaec3a9530854a6d5b6a09a1a9b10339c6c30274'}, 'component/Sources/PinkhaKit/TorahAssociationIdentity.swift': {'bytes': 5165, 'sha256': '85738df63c9ae987c1180c20e661cd21cd4acc20afcd376592f87ca32dcdb626'}, 'component/Sources/PinkhaKit/TorahAssociationModels.swift': {'bytes': 15128, 'sha256': '0007274a78d39fd4c8e0105eb50cec106c807cf53735caa0de1f4a85cd7fbde1'}, 'component/Sources/PinkhaKit/TorahAssociationPayloadCodec.swift': {'bytes': 6237, 'sha256': '9956aa25174812c5878927b5c62cff5f5d1d16e8becb536e23dadb25a01422d1'}, 'component/Sources/PinkhaKit/TorahAssociationRepository.swift': {'bytes': 2445, 'sha256': '63c789b1e14b85fb8032f2cf8fecb4fcb7e768453c03b9304e78ac77775fb66e'}, 'component/Sources/PinkhaKit/TorahCanonicalAssociations.swift': {'bytes': 8403, 'sha256': 'e5c988ebb64572e5228592f8a833ca8e5c2638fd991d0f7fc7e9bb114e4e3f3d'}, 'component/Sources/PinkhaKit/TorahSemanticAnchorAssociation.swift': {'bytes': 3789, 'sha256': '17c469ea127bf01211c7e819c00a2e15ea07facbe2c6d86505a5f0fce82cb3f4'}, 'component/Sources/PinkhaKit/TorahSourceJSONGuard.swift': {'bytes': 7503, 'sha256': 'ad856a6ed49f645ec2d5cb6a0bc3c7b6e7566c5cd7ad2a3081ccd748849ab9f6'}, 'component/Sources/TorahInspectorCore/Models.swift': {'bytes': 24592, 'sha256': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0'}, 'component/Sources/TorahInspectorCore/ProviderProtocols.swift': {'bytes': 510, 'sha256': '9f5f28f1d71a97831827dce5dfe2324a60460fc7760137b9527e4c3815d20273'}, 'component/Sources/TorahInspectorCore/TorahInspectorCoordinator.swift': {'bytes': 461, 'sha256': 'fccfc25ee56e165c6559aba52a1ccec39d10db6fd6a94a91c867cd38dc693116'}, 'component/Sources/TorahInspectorCore/TorahInspectorRepository.swift': {'bytes': 17499, 'sha256': '519828f3d602811758d2698e00a06567b41d31d465b143175441f08873300040'}, 'component/Sources/TorahInspectorCore/TorahReaderScrollStateMachine.swift': {'bytes': 3444, 'sha256': '90173f3198133c6a746d00c9a6af9ad8cd854f5643f924d98e9095133da5bbdc'}, 'component/Sources/TorahInspectorCore/TorahRelatedDocumentsAccessError.swift': {'bytes': 355, 'sha256': '0ff22bb5a56ddff0235e7b6c5188c737b110cb2848d7e17dcaefc3ca1d6df2e6'}, 'component/Sources/TorahInspectorCore/TorahSourceTransfer.swift': {'bytes': 3410, 'sha256': '994da5da2cb6b163083c7f3dea20cfe74c781211eea0f144b394a6d047affc97'}, 'component/Sources/TorahInspectorCore/TorahToolSelectorStateMachine.swift': {'bytes': 2005, 'sha256': '34dda44a571764ea98e43449422340ad7a00dbe4b0d43c0036d7d48ad8119729'}, 'component/Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift': {'bytes': 20663, 'sha256': 'b80f20ccf77b4b0bb42043d18449f2b63d8001757e389a047011e6e3b43ba3b0'}, 'component/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift': {'bytes': 45205, 'sha256': '4274837b7e8176bc7f768149f842b31e56765716f5219c2a7e6412378c43e75c'}, 'owned-process-provenance.json': {'bytes': 1010, 'sha256': '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'}, 'owned_process.py': {'bytes': 5529, 'sha256': '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'}, 'retained-crypto-closure.json': {'bytes': 122971, 'sha256': '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'}, 'run_component.py': {'bytes': 48105, 'sha256': '3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c'}, 'whole-source-closure.json': {'bytes': 179044, 'sha256': '38e924728ec19aedb3eda251d7cc2f60d538c46e553ee5dcb06a607d6c4947ce'}}
EXTRACTED_FUNCTIONS = {'sha': {'bytes': 56, 'sha256': '166ad903d6d1b4f98706f40c535e6a84f4a6268f81640d32bb1d0f02c6857de1'}, 'pinned': {'bytes': 310, 'sha256': '6cdc427d4660b21b4046aef1f106c2834a0504e25c1cfa17124140f7d590e767'}, 'verify_crypto': {'bytes': 359, 'sha256': 'bedf311323a1a87a8433d694da2db5337aa31d8ded1df230252e448e137f9f09'}, 'compiler_inputs': {'bytes': 14394, 'sha256': '1a124b4897e005f44e3ed8fa18185fe04c12a9ce46b7fdf48e683d9dd76c0df0'}}
EXTRACTED_CONSTANTS = {'ROOT': {'bytes': 81, 'sha256': 'e7a7b3286a81483c154b2ef1831a6bcaaff8ffd9094063f54d3692bb6e61f6f5'}, 'INPUTS': {'bytes': 24, 'sha256': '3ef5ae33550717f9b6828c5bec6f72daffc5c311e20f7da0564e12366b1153bf'}, 'COMPONENT': {'bytes': 30, 'sha256': '8f96eac8b89447da3f36d1c6f09f9b5891d3db0ad47a3c3f772ec743597998da'}, 'EVIDENCE': {'bytes': 28, 'sha256': '768cf41d765c51b340900cf1e848bbe2221be94379e22347410930cd461e3af3'}, 'SWIFT': {'bytes': 79, 'sha256': '2438cf15997ae10dca6669c06be4c324b6a80d93919ce7958e01aa0801ca80fe'}, 'PRODUCT_COMMIT': {'bytes': 59, 'sha256': '0e43f3d0bfeed769e6c30126d594b7aeb204b73f3bf1357dfefc188f60906ff3'}, 'CRYPTO_SHA': {'bytes': 79, 'sha256': 'fec96f932f7cf2127c4e595a524fb0be80f5b5e7481808fe28998f73f8d6e84f'}, 'SOURCE_PINS': {'bytes': 10753, 'sha256': 'b5963c92b36651a799dd1826d4af4afbab3e4fc3d676c4db7258a0d8a799f8c5'}, 'GENERATED_ENTRY_SHA256': {'bytes': 212, 'sha256': 'de1302c710b7c4ce38cfe73cc6f491d2ce54f3522d0855a59ee54136a53d1f20'}, 'ALLOCATION_CAP': {'bytes': 30, 'sha256': '16550de2ad8ee662ae0b4aecaa06b9d2283c1bf09b42cacb777dd1826dbf40c5'}}
MAX_RECEIPT_BYTES = 2 * 1024**2
ADDRESS_SPACE_BYTES = 512 * 1024**2
WALL_SECONDS = 60
OUTPUT = ROOT / 'completion1.json'
STARTED = None
WRITING_RECEIPT = False
FORBIDDEN_ATTEMPTS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pinned(path, expected, size=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.resolve(strict=True) == path, 'Physical path changed: ' + str(path)
    raw = path.read_bytes()
    assert sha(raw) == expected and (size is None or len(raw) == size), str(path)
    return raw

def verify_crypto(copies):
    for item in copies:
        pinned(Path(item['source']), item['sha256'], item['bytes'])
        pinned(Path(item['original']), item['sha256'], item['bytes'])
        pinned(Path(item['target']), item['sha256'], item['bytes'])
        assert Path(item['alias']).resolve(strict=True) == Path(item['original']).resolve(strict=True)

def compiler_inputs(log):
    assert 'Swift version 6.4.3 (swift-6.4.3-RELEASE)' in log
    assert 'aarch64-unknown-linux-gnu' in log
    # The retained single-target runs establish this backend's actual format.
    # Exact 6.4.3 SwiftPM source establishes one product/runner per test target.
    # Both must produce the fixed layout below; another backend is not admitted.
    build = ROOT / 'build'
    project = build / 'out/Intermediates.noindex/BookmarkCreationProof.build/Debug-linux-aarch64'
    products = build / 'out/Products/Debug-linux-aarch64'
    swiftc = str(SWIFT.with_name('swiftc'))
    clang = str(SWIFT.with_name('clang'))
    test_modules = ('PinkhaAnyHostTests', 'PinkhaAnyIntegrationTests')
    production_modules = ('TorahInspectorCore', 'PinkhaKit', 'PinkhaAnyEngine', 'PinkhaAnyIntegration', 'PinkhaAnyHost')
    runner_modules = {module + '_test_runner': module for module in test_modules}
    anchors = {module: project / (module + '-p.build/DerivedSources/test_anchor.swift') for module in test_modules}
    entries = {module: project / (module + '-test-runner.build/DerivedSources/test_entry_point.swift') for module in test_modules}

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
    assert sum(len(x) for x in groups.values()) == 84 and set(groups) == set(production_modules + test_modules)
    generated = {}
    for module in test_modules:
        groups[module].add(str(anchors[module]))
        groups[module + '_test_runner'] = {str(entries[module])}
        anchor_raw = physical(anchors[module])
        assert anchor_raw == ('public func __test_anchor_' + module + '() {}').encode('utf-8')
        entry_raw = physical(entries[module])
        entry_text = entry_raw.decode('utf-8')
        assert 'import ' + module in entry_text and '__test_anchor_' + module + '()' in entry_text
        assert 'struct __SwiftPMGeneratedTestRunner' in entry_text and 'XCTMain(__allDiscoveredTests())' in entry_text
        assert 'await Testing.__swiftPMEntryPoint() as Never' in entry_text
        # These are fixed byte expectations derived from retained actual generated
        # source. They are not compiled inputs or evidence of future execution.
        assert sha(entry_raw) == GENERATED_ENTRY_SHA256[module], module
        generated[str(anchors[module])] = anchor_raw
        generated[str(entries[module])] = entry_raw
    assert {str(p) for p in build.rglob('*.swift')} == set(generated), 'Unexpected generated Swift input'

    driver_lines = {}
    anchor_writes = {module: [] for module in test_modules}
    entry_generators = {module: [] for module in test_modules}
    link_commands = {}
    expected_products = {module: products / (module + '.o') for module in production_modules}
    expected_products.update({module: products / (module + '.so') for module in test_modules})
    expected_products.update({runner: products / (module + '-test-runner') for runner, module in runner_modules.items()})
    product_modules = {str(path): module for module, path in expected_products.items()}
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.startswith('builtin-SwiftDriver -- '):
            argv = shlex.split(stripped)
            assert argv[:3] == ['builtin-SwiftDriver', '--', swiftc]
            module = value(argv, '-module-name')
            assert module in groups and module not in driver_lines, 'Unexpected or duplicate Swift driver'
            driver_lines[module] = (line, argv)
        elif stripped.startswith('write-file '):
            argv = shlex.split(stripped)
            for module, anchor in anchors.items():
                if argv == ['write-file', str(anchor)]:
                    anchor_writes[module].append(line)
        elif stripped.startswith('builtin-generateTestEntryPoint '):
            argv = shlex.split(stripped)
            module = value(argv, '--test-anchor-module')
            assert module in test_modules
            assert value(argv, '--output') == str(entries[module])
            assert argv.count('--discover-tests') == 1
            assert value(argv, '--linker-file-list-format') == 'unixShellQuotedNewlineSeparated'
            assert value(argv, '--index-store-library-path') == str(SWIFT.parent.parent / 'lib/libIndexStore.so')
            assert value(argv, '--index-store') == str(build / 'out')
            assert value(argv, '--index-unit-base-path') == str(build / 'out/Intermediates.noindex')
            link_list = Path(value(argv, '--linker-filelist'))
            assert link_list == project / (module + '-p.build/Objects-normal/aarch64/' + module + '.LinkFileList')
            raw = physical(link_list)
            entry_generators[module].append({'actualCommandLine': line, 'linkerFileList': str(link_list),
                                            'linkerFileListSHA256': sha(raw), 'linkerFileListText': raw.decode('utf-8')})
        elif stripped.startswith((swiftc + ' ', clang + ' ')):
            argv = shlex.split(stripped)
            if '-o' not in argv:
                continue
            output = value(argv, '-o')
            if Path(output).is_relative_to(products):
                assert output in product_modules, 'Unexpected linked component product'
                module = product_modules[output]
                assert module not in link_commands, 'Duplicate product link command'
                link_commands[module] = (line, argv)
    assert set(driver_lines) == set(groups) == set(link_commands) and len(groups) == 9
    assert all(len(anchor_writes[module]) == len(entry_generators[module]) == 1 for module in test_modules)

    proof = []
    qualified_lists = set()
    qualified_link_lists = set()
    crypto_objects = [str(ROOT / 'retained-crypto-objects' / (name + '.o')) for name in
                      ('Crypto', 'CryptoBoringWrapper', 'CCryptoBoringSSL', 'CCryptoBoringSSLShims')]
    for module, expected in sorted(groups.items()):
        if module in runner_modules:
            stem = runner_modules[module] + '-test-runner'
            target = stem + '.build'
        else:
            stem, target = module, module + ('-p.build' if module in test_modules else '-t.build')
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
        assert value(argv, '-swift-version') == ('5' if module in runner_modules else '6')
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

        # Actual link closure is separate from compiler source-list custody.
        # Each of the two products/runners links its own fixed dependency tuple.
        module_object = object_root / 'Modules' / (module + '.o')
        module_object_raw = physical(module_object)
        expected_link = {row['object'] for row in objects} | {str(module_object)}
        if module in test_modules:
            linked_modules = production_modules if module == 'PinkhaAnyHostTests' else production_modules[:-1]
            expected_link |= {str(expected_products[name]) for name in linked_modules}
        link_list = object_root / (stem + '.LinkFileList')
        link_raw = physical(link_list)
        linked = shlex.split(link_raw.decode('utf-8'))
        assert len(linked) == len(set(linked)) and set(linked) == expected_link, module
        qualified_link_lists.add(link_list)
        linked_files = []
        for path in linked:
            raw = physical(Path(path), maximum=ALLOCATION_CAP if path in product_modules else 16 * 1024**2)
            linked_files.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
        link_line, link_argv = link_commands[module]
        assert value(link_argv, '-o') == str(expected_products[module])
        assert value(link_argv, '-target') == 'aarch64-unknown-linux-gnu'
        at_files = [arg for arg in link_argv if arg.startswith('@')]
        link_extras = []
        if module in production_modules:
            assert link_argv[0] == clang and '-r' in link_argv and '-nostdlib' in link_argv
            assert at_files == ['@' + str(link_list)]
            assert not [arg for arg in link_argv if arg.endswith(('.o', '.so')) and arg != str(expected_products[module])]
        else:
            autolink = object_root / (module + '-swiftbuild.autolink')
            autolink_raw = physical(autolink)
            assert link_argv[0] == swiftc
            assert at_files == ['@' + str(link_list), '@' + str(autolink)]
            assert link_argv.count('-lstdc++') == 1
            assert all(link_argv.count(path) == 1 for path in crypto_objects)
            object_tokens = [arg for arg in link_argv if arg.endswith(('.o', '.so')) and arg != str(expected_products[module])]
            relative_tokens = [arg for arg in object_tokens if not Path(arg).is_absolute()]
            if module in test_modules:
                assert relative_tokens == [module + '.so']
                soname = link_argv.index(module + '.so')
                assert link_argv[soname - 3:soname] == ['-Xlinker', '-soname', '-Xlinker']
            else:
                assert not relative_tokens
            explicit_objects = [arg for arg in object_tokens if Path(arg).is_absolute()]
            expected_explicit = crypto_objects[:]
            if module in runner_modules:
                assert '-emit-executable' in link_argv and '-emit-library' not in link_argv
                expected_explicit.append(str(expected_products[runner_modules[module]]))
            else:
                assert '-emit-library' in link_argv and '-emit-executable' not in link_argv
            assert len(explicit_objects) == len(expected_explicit) and set(explicit_objects) == set(expected_explicit)
            for path in expected_explicit:
                raw = physical(Path(path), maximum=ALLOCATION_CAP if path in product_modules else 16 * 1024**2)
                link_extras.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
            link_extras.append({'path': str(autolink), 'bytes': len(autolink_raw),
                                'sha256': sha(autolink_raw), 'text': autolink_raw.decode('utf-8')})
        product_raw = physical(expected_products[module], maximum=ALLOCATION_CAP)
        proof.append({'module': module, 'sourceList': str(source_list),
                      'sourceListSHA256': sha(source_list_raw), 'sourceListText': source_list_raw.decode('utf-8'),
                      'outputFileMap': str(map_path), 'outputFileMapSHA256': sha(map_raw), 'outputFileMapValue': output_map,
                      'actualCompilerLines': [line], 'actualCompilerArgv': argv,
                      'emittedModule': str(module_path), 'emittedModuleSHA256': sha(module_raw), 'objects': objects,
                      'actualLink': {'commandLine': link_line, 'argv': link_argv,
                                     'linkFileList': str(link_list), 'linkFileListSHA256': sha(link_raw),
                                     'linkFileListText': link_raw.decode('utf-8'), 'linkedFiles': linked_files,
                                     'moduleObject': str(module_object), 'moduleObjectSHA256': sha(module_object_raw),
                                     'extraInputs': link_extras, 'product': str(expected_products[module]),
                                     'productBytes': len(product_raw), 'productSHA256': sha(product_raw)},
                      'generatedInputs': [{'path': source, 'bytes': len(raw), 'sha256': sha(raw), 'text': raw.decode('utf-8'),
                                           'actualGeneration': anchor_writes[module] if source == str(anchors.get(module))
                                           else entry_generators[runner_modules[module]]}
                                          for source, raw in generated.items() if source in expected]})
    assert set(build.rglob('*.SwiftFileList')) == qualified_lists, 'Unexpected compiler source list'
    assert set(build.rglob('*.LinkFileList')) == qualified_link_lists, 'Unexpected product linker list'
    return proof

def now():
    return datetime.now(timezone.utc).isoformat()


def deadline():
    if STARTED is not None and time.monotonic() - STARTED >= WALL_SECONDS:
        raise TimeoutError('Read-only completion exceeded its 60-second wall budget')


def audit_guard(event, arguments):
    # Finite operation enforcement; this is not an owned-process manager.
    forbidden = ('subprocess.Popen', 'os.fork', 'os.forkpty', 'os.posix_spawn',
                 'os.exec', 'os.spawn', 'os.system', 'os.kill', 'os.killpg',
                 'socket.__new__', 'socket.connect', 'socket.bind')
    if event in forbidden or event.startswith(('subprocess.', 'os.exec', 'os.spawn')):
        FORBIDDEN_ATTEMPTS.append(event)
        raise RuntimeError('Forbidden operation in read-only completion: ' + event)
    if event == 'open':
        path, mode, flags = arguments
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        if writing:
            assert WRITING_RECEIPT and path == 'completion1.json', 'Only the fixed receipt may be created'
            assert flags & os.O_EXCL and flags & os.O_NOFOLLOW and not flags & (os.O_TRUNC | os.O_APPEND)
        elif not WRITING_RECEIPT:
            deadline()
    if event in ('os.listdir', 'os.scandir'):
        # Only the three original compiler_inputs glob assertions are retained.
        path = Path(arguments[0])
        assert path == ROOT / 'build' or path.is_relative_to(ROOT / 'build'), str(path)
        deadline()
    if event in ('os.remove', 'os.rmdir', 'os.rename', 'os.link', 'os.symlink',
                 'os.mkdir', 'os.chmod', 'os.chown', 'os.truncate', 'os.utime'):
        raise RuntimeError('Filesystem mutation outside the sole receipt is forbidden: ' + event)


def read_originals():
    actual = {}
    parsed = {}
    for name, authority in sorted(ORIGINAL_ARTIFACTS.items()):
        deadline()
        path = EVIDENCE / name
        raw = pinned(path, authority['sha256'], authority['bytes'])
        actual[name] = {'bytes': len(raw), 'sha256': sha(raw)}
        parsed[name] = json.loads(raw) if name.endswith('.json') else raw.decode('utf-8')
    assert len(actual) == 10 and sum(v['bytes'] for v in actual.values()) == 361923
    return actual, parsed


def verify_fixed_inputs():
    # Exactly the immutable 90 rows; no directory or PIF search is added.
    actual = {}
    for relative, authority in sorted(INPUT_ENTRIES.items()):
        deadline()
        path = Path(relative)
        assert not path.is_absolute() and '..' not in path.parts
        raw = pinned(INPUTS / path, authority['sha256'], authority['bytes'])
        actual[relative] = {'bytes': len(raw), 'sha256': sha(raw)}
    assert len(actual) == 90 and sum(x['bytes'] for x in actual.values()) == 1344177
    assert len(SOURCE_PINS) == 85
    compiled = {}
    for relative, expected in sorted(SOURCE_PINS.items()):
        deadline()
        authority = INPUT_ENTRIES['component/' + relative]
        assert authority['sha256'] == expected
        raw = pinned(COMPONENT / relative, expected, authority['bytes'])
        compiled[relative] = sha(raw)
    assert compiled == SOURCE_PINS
    return {'inputRows': actual, 'compiledCopy': compiled}


def check_extracted_source():
    raw = pinned(INPUTS / 'run_component.py', ORIGINAL_CONTROLLER_SHA256, ORIGINAL_CONTROLLER_BYTES)
    original = raw.decode('utf-8')
    current = Path(__file__).read_text(encoding='utf-8')
    result = {}
    for description, text in (('original', original), ('completion', current)):
        tree = ast.parse(text)
        found = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in EXTRACTED_FUNCTIONS:
                segment = ast.get_source_segment(text, node).encode('utf-8')
                assert node.name not in found
                found[node.name] = {'bytes': len(segment), 'sha256': sha(segment)}
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in EXTRACTED_CONSTANTS:
                    segment = ast.get_source_segment(text, node).encode('utf-8')
                    assert name not in found
                    found[name] = {'bytes': len(segment), 'sha256': sha(segment)}
        assert found == {**EXTRACTED_FUNCTIONS, **EXTRACTED_CONSTANTS}, description
        result[description] = found
    return {'originalControllerSHA256': sha(raw), 'completionSourceSHA256': sha(current.encode('utf-8')),
            'exactOriginalDeclarations': result['completion'], 'originalModuleImported': False,
            'originalMainOrMixedParserCalled': False, 'originalCopierOrProcessHelperCalled': False}


def bind_original_attempt(parsed):
    original = parsed['receipt.json']
    assert original['schema'] == 'pinkha-bookmark-six-component/v1'
    assert original['status'] == 'FAIL' and original['processExit'] == 0
    assert original['controllerSHA256'] == ORIGINAL_CONTROLLER_SHA256
    assert original['productCommit'] == PRODUCT_COMMIT
    assert original['command'] == parsed['command.json']
    command = original['command']
    assert command['cwd'] == str(COMPONENT) and command['environmentOverrides']['PWD'] == str(ROOT)
    assert command['argv'][0:2] == [str(SWIFT), 'test']
    assert command['argv'][command['argv'].index('--scratch-path') + 1] == str(ROOT / 'build')
    assert original['startedAtUTC'] == '2026-11-27T22:36:25.026796+00:00'
    assert original['finishedAtUTC'] == '2026-11-27T22:37:21.691441+00:00'
    assert original['ownedCleanup']['status'] == 'PASS_OWNED_GROUP_ABSENT'
    absence = original['ownedCleanup']['absenceEvidence']
    assert absence == original['outerGroupAtExit']
    assert absence['status'] == 'ABSENT_ESRCH' and absence['errno'] == 3
    assert absence['processGroup'] == 2634766 and absence['atUTC'] == '2026-11-27T22:37:21.190723+00:00'
    assert original['ownedCleanup']['historicalGroupReprobed'] is False
    assert parsed['process.json']['pid'] == parsed['process.json']['processGroup'] == 2634766
    assert original['safeToReleaseRuntimeSlot'] is True
    assert len(original['errors']) == 1 and original['errors'][0]['type'] == 'AssertionError'
    assert 'Both selected Swift Testing cases must pass' in original['errors'][0]['traceback']
    assert parsed['source-inputs-before.json'] == parsed['source-inputs-after.json'] == SOURCE_PINS
    assert parsed['source-inputs-final.json'] == {'compiledCopy': SOURCE_PINS, 'inputs': SOURCE_PINS}
    return {'originalStatus': 'FAIL', 'originalChildExit': 0,
            'originalError': original['errors'], 'originalPositiveClosure': original['ownedCleanup'],
            'closureReusedFromPinnedReceiptOnly': True, 'historicalGroupReprobed': False,
            'actualCompletedJob': ORIGINAL_JOB,
            'jobBindingAuthority': 'Pinned retained job notification; no server query performed by completion.'}


def bind_crypto_copies(copies):
    closure = json.loads(pinned(INPUTS / 'retained-crypto-closure.json', CRYPTO_SHA, 122971))
    assert len(closure['files']) == len(copies) == 102
    destinations = {'swift-import': 'retained-crypto-imports',
                    'c-header-or-module-map': 'retained-crypto-headers',
                    'aggregated-link-object': 'retained-crypto-objects'}
    expected = []
    for row in closure['files']:
        relative = Path(row['relativePath'])
        assert not relative.is_absolute() and '..' not in relative.parts
        alias = row['actualOriginalPackageLinkerPath'] if row['kind'] == 'aggregated-link-object' else row['recordedHistoricalAliasPath']
        expected.append({'kind': row['kind'], 'source': row['freshCopySourcePath'],
                         'original': row['originalManifestPath'], 'alias': alias,
                         'target': str(ROOT / destinations[row['kind']] / relative),
                         'sha256': row['sha256'], 'bytes': row['bytes']})
    assert copies == expected and sum(x['bytes'] for x in copies) == 19775715
    verify_crypto(copies)
    return {'files': 102, 'logicalBytes': 19775715, 'originalAliasSourceAndActualCopyVerified': True,
            'copierCalled': False, 'atimePreservationClaim': False}


def fixed_observed_test_boundary(stdout):
    # This is an immutable observation, not a substitute result validator.
    # Exact original stdout has already been pinned; no mixed parser is invoked.
    names = ('testBookmarkCreationReadbackRequiresExactSourceAndOriginalIdentity',
             'testBookmarkCreationRefusesFramesOutsideTheSelectedBinding',
             'testBookmarkCreationRefusesHiddenManagedAndChangedBindings',
             'testBookmarkCreationRetainsEmptyNameAndOneExactMappedURL')
    for name in names:
        marker = "Test Case 'NativeBookmarkPresentationTests." + name + "' passed ("
        assert stdout.count(marker) == 1
    assert 'Executed 4 tests, with 0 failures (0 unexpected) in 0.029 (0.029) seconds' in stdout
    assert 'Executed 0 tests, with 0 failures' in stdout
    return {'observedXCTestMethodNames': list(names), 'observedXCTestMethods': 4,
            'observedXCTestSummarySeconds': 0.029, 'observedOtherXCTestProductTests': 0,
            'observedSwiftTestingEvents': 0, 'missingSwiftTestingMethods': [
                'creationOverrideRejectsAnotherWorkspaceBeforeDispatch',
                'creationOverrideAndDefaultCreatorShareTheExistingMutationQueue'],
            'sixMethodAcceptance': False, 'originalOverallStatus': 'FAIL',
            'testsExecutedByCompletion': 0,
            'meaning': 'Pinned original observations retained; generated/linked products do not prove either missing test executed.'}


def failure_record(phase, error):
    # Never ask linecache to open source while retaining a timeout/I/O failure.
    frames = []
    cursor = error.__traceback__
    while cursor is not None and len(frames) < 32:
        code = cursor.tb_frame.f_code
        frames.append({'file': code.co_filename, 'function': code.co_name, 'line': cursor.tb_lineno})
        cursor = cursor.tb_next
    return {'phase': phase, 'type': type(error).__name__, 'message': str(error)[:8192],
            'tracebackFrames': frames, 'additionalFramesOmitted': cursor is not None}


def write_receipt(receipt, root_fd):
    global WRITING_RECEIPT
    raw = (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode('utf-8')
    assert 0 < len(raw) <= MAX_RECEIPT_BYTES, 'Completion receipt exceeds its fixed 2 MiB bound'
    WRITING_RECEIPT = True
    try:
        fd = os.open('completion1.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
        try:
            metadata = os.fstat(fd)
            assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            assert metadata.st_uid == os.geteuid() and stat.S_IMODE(metadata.st_mode) == 0o600
            remaining = memoryview(raw)
            while remaining:
                written = os.write(fd, remaining)
                assert written > 0, 'Receipt write made no progress'
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(root_fd)
        # Full byte readback; a partial/failed output is retained, never replaced.
        assert OUTPUT.read_bytes() == raw
        return {'path': str(OUTPUT), 'bytes': len(raw), 'sha256': sha(raw)}
    finally:
        WRITING_RECEIPT = False


def complete_read_only():
    global STARTED
    assert sys.argv[1:] == ['--qualify-original-attempt1'], 'Explicit reviewed completion invocation required'
    assert not sys.flags.optimize, 'Assertions are part of the reviewed qualification'
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE_BYTES, ADDRESS_SPACE_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (WALL_SECONDS, WALL_SECONDS))
    STARTED = time.monotonic()
    sys.addaudithook(audit_guard)
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve(strict=True) == ROOT
    root_info = ROOT.stat()
    assert root_info.st_uid == os.geteuid() and stat.S_IMODE(root_info.st_mode) == 0o700
    root_fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    first = None
    receipt = {'schema': 'bookmark6-read-only-compiler-custody-completion/v1',
               'status': 'FAIL_READ_ONLY_COMPLETION_ORIGINAL_FAIL_RETAINED',
               'originalOverallStatus': 'FAIL', 'originalReceiptSHA256': ORIGINAL_ARTIFACTS['receipt.json']['sha256'],
               'originalCustodyManifestSHA256': ORIGINAL_CUSTODY_MANIFEST_SHA256,
               'originalInputPacketSHA256': ORIGINAL_PACKET_SHA256, 'productSourceCommit': PRODUCT_COMMIT,
               'root': str(ROOT), 'output': str(OUTPUT), 'actualCompletedJob': ORIGINAL_JOB,
               'startedAtUTC': now(), 'limits': {'addressSpaceBytes': ADDRESS_SPACE_BYTES,
                   'cpuSeconds': WALL_SECONDS, 'wallSeconds': WALL_SECONDS, 'externalDispatchTimeoutRequiredSeconds': WALL_SECONDS,
                   'receiptBytes': MAX_RECEIPT_BYTES},
               'children': 0, 'compilerCommands': 0, 'SwiftInvocations': 0, 'testsExecuted': 0,
               'processQueries': 0, 'signals': 0, 'NativeCalls': 0, 'AppleCalls': 0,
               'runtimeSlotGranted': False, 'originalFilesModified': False, 'sixMethodAcceptance': False,
               'historicalProcessClosureIsRecordOnly': True, 'atimePreservationClaim': False, 'errors': []}
    original_before = None
    inputs_before = None
    copies = None
    try:
        try:
            os.stat('completion1.json', dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('completion1.json already exists; never reuse or replace a completion')
        receipt['sourceDeclarationProof'] = check_extracted_source()
        original_before, original = read_originals()
        receipt['originalAttempt'] = bind_original_attempt(original)
        receipt['originalArtifactsBefore'] = original_before
        inputs_before = verify_fixed_inputs()
        receipt['fixedInputAndCompiledSourceBefore'] = inputs_before
        copies = original['actual-dependency-copies.json']
        receipt['cryptoBefore'] = bind_crypto_copies(copies)
        receipt['observedTestBoundary'] = fixed_observed_test_boundary(original['stdout.original.log'])
        # EXACT original qualifier. Its fixed build subtree glob assertions remain
        # unchanged; no generic filesystem/PIF search or test dispatch is added.
        deadline()
        log = original['stdout.original.log'] + '\n' + original['stderr.original.log']
        receipt['actualCompilerInputs'] = compiler_inputs(log)
        deadline()
        groups = receipt['actualCompilerInputs']
        objects = [item for group in groups for item in group['objects']]
        generated = [item for group in groups for item in group['generatedInputs']]
        assert len(groups) == 9 and len(objects) == 88 and len(generated) == 4
        assert sum(bool(item['generatedSource']) for item in objects) == 4
        assert sum(item['bytes'] for item in generated) <= 64 * 1024
        receipt['qualifiedCompilerScope'] = {'driverAndProductGroups': 9, 'originalSwiftSources': 84,
            'generatedSwiftSources': 4, 'actualCompiledSwiftInputs': 88,
            'generatedBytesIncluded': sum(item['bytes'] for item in generated),
            'sourceAndLinkQualificationOnly': True, 'testDispatchRootCauseEstablished': False}
    except BaseException as error:
        first = error
        receipt['errors'].append(failure_record('read-only-qualification', error))
    finally:
        # Read-only after checks retain their own errors without replacing the first.
        for phase, operation in (
            ('original-artifact-after', read_originals),
            ('fixed-input-and-source-after', verify_fixed_inputs),
            ('crypto-after', (lambda: bind_crypto_copies(copies)) if copies is not None else None),
        ):
            if operation is None:
                continue
            try:
                deadline()
                result = operation()
                if phase == 'original-artifact-after':
                    actual, _ = result
                    assert original_before is None or actual == original_before
                    receipt['originalArtifactsAfter'] = actual
                elif phase == 'fixed-input-and-source-after':
                    assert inputs_before is None or result == inputs_before
                    receipt['fixedInputAndCompiledSourceAfter'] = result
                else:
                    receipt['cryptoAfter'] = result
                    assert result == receipt['cryptoBefore']
            except BaseException as error:
                if first is None:
                    first = error
                receipt['errors'].append(failure_record(phase, error))
        if first is None:
            receipt['status'] = 'QUALIFIED_COMPILER_CUSTODY_ONLY_ORIGINAL_SIX_METHOD_RESULT_FAIL'
        receipt['forbiddenOperationAttempts'] = FORBIDDEN_ATTEMPTS[:]
        receipt['finishedAtUTC'] = now()
        receipt['seconds'] = round(time.monotonic() - STARTED, 3)
        try:
            if first is None:
                deadline()
            result = write_receipt(receipt, root_fd)
            print(json.dumps({'status': receipt['status'], 'receipt': result,
                              'originalOverallStatus': 'FAIL', 'sixMethodAcceptance': False}, sort_keys=True), flush=True)
        except BaseException as save_error:
            if first is not None:
                if hasattr(first, 'add_note'):
                    first.add_note('Secondary completion receipt failure: ' + repr(save_error))
                print(json.dumps({'status': 'FAIL_RECEIPT_WRITE_ORIGINAL_FAIL_RETAINED',
                                  'firstError': repr(first), 'secondarySaveError': repr(save_error)}, sort_keys=True), file=sys.stderr, flush=True)
            else:
                first = save_error
        finally:
            os.close(root_fd)
    if first is not None:
        raise first


if __name__ == '__main__':
    complete_read_only()
