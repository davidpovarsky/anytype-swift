#!/usr/bin/env python3
"""Source-only embedded boot/lifecycle extension for the N-owned qualifier.

There is no entry point, source installer, cache-release path or process owner.
Only a separately reviewed N controller may call these functions, after its
actual E Native117/Swift23 receipts and explicit Root cache/runtime grant.
The exact preserved N24 attempt1 donor is c83aa7aa, not the unavailable current
attempt2. This extension does not make that donor executable or current.

Three additional existing-owner commands select 17 parents and 16 children.
The four affected original embedded parents run once; no untouched migration,
Files, ACL or networking cohort is selected. Linux Go wrappers/core are not
generated gomobile bindings, an Apple C ABI, a framework or an app acceptance.
"""
import json
from pathlib import Path, PurePosixPath

PROTOCOL = 'pinkha-embedded-boot-lifecycle-extension-v1'
MIB = 1024**2
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
OFFLINE_PATH = '/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py'
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
LIFECYCLE_SOURCE_COMMIT = '584d8eb7423e61823aa67c173312b742d540a27f'
N24_SOURCE_COMMIT = '94fd763d459210b496557894628333d466abae73'
PRESERVED_DONOR_SHA = 'c83aa7aaeeee3c40f488b93573c162f253cae8f18856594187cbd301b0c3acb6'

ASSET_ROWS = json.loads("{\"selection.json\":{\"bytes\":6893,\"sha256\":\"dde922871f07cb3f124d53999ee950fd9f1d04ed5784bf28c2fe90c1b6b9c8c0\",\"mode\":384},\"composition.json\":{\"bytes\":9025,\"sha256\":\"7822a8c641331259b23f2569adaddb34095ec4b86b0f44fd11bd1932ed571e1f\",\"mode\":384},\"native-production-source.json\":{\"bytes\":372320,\"sha256\":\"5206276e3071eeac65784c08a6981b5300eb9017b084c0052db0b2afe46dc74e\",\"mode\":384},\"native-qualification-source.json\":{\"bytes\":374143,\"sha256\":\"8c263f483b327c76d511b6b5786654f64743df9a300741f0ef8760f25b216c3c\",\"mode\":384},\"payloads/boot-binding/internal/embedded/embedded.go\":{\"bytes\":15885,\"sha256\":\"3b734dd4b3d05c51c4afec4e914d3c637d41e34c9545fd7749bc1aba8b09ae82\",\"mode\":384},\"payloads/boot-binding/internal/embedded/network_binding.go\":{\"bytes\":2162,\"sha256\":\"df3e4bdd15dfedbda827cf53f6b65c1179a6b63a3c74617302b8ae91432992a6\",\"mode\":384},\"payloads/boot-binding/internal/embedded/network_binding_test.go\":{\"bytes\":6426,\"sha256\":\"9346d49093706e152fd0da02b571fd037974c9ecbbc41871c2193df50c425740\",\"mode\":384},\"payloads/boot-binding/mobile/android/network_binding.go\":{\"bytes\":1137,\"sha256\":\"6850eb04ff0ae46c7a14da7495047d1f58aa399964d8baf97aa74ec4ef7c3e21\",\"mode\":384},\"payloads/boot-binding/mobile/android/network_binding_test.go\":{\"bytes\":1106,\"sha256\":\"3eee3e3661d30c483f5952036ab9737e81186da8862d4a7eb896b5ce564117e5\",\"mode\":384},\"payloads/boot-binding/mobile/ios/anylib_binding.go\":{\"bytes\":1966,\"sha256\":\"9ec543d57dfd550aedff75c561f55e1297d37d4d43f8a177a6e12e53d3442ec5\",\"mode\":384},\"payloads/boot-binding/mobile/ios/anylib_binding_test.go\":{\"bytes\":1007,\"sha256\":\"ce1c00f8bcd2746c6d5f13775004fa9352a6340c7d3e69880d7a00924a301b21\",\"mode\":384},\"payloads/embedded-lifecycle/internal/embedded/embedded.go\":{\"bytes\":16440,\"sha256\":\"7e04af3c356e2b7596540e69b54b7b1e390d00610e2cf2202e8356b1e17a9154\",\"mode\":384},\"payloads/embedded-lifecycle/internal/embedded/lifecycle_reservation_test.go\":{\"bytes\":19960,\"sha256\":\"e92092ec1469323c9a0631dfd01cbad1973a6f1a54ab0deabb9c4ed8768ad026\",\"mode\":384}}")
PHASES = json.loads("[{\"label\":\"embedded-boot-lifecycle\",\"package\":\"github.com/anyproto/any/internal/embedded\",\"parents\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts\",\"TestLifecycleCancelledPendingStartCannotSkipPreviousDrain\",\"TestLifecycleGracefulStopFencesNextGeneration\",\"TestLifecycleGracefulStopWaitsAfterStopNow\",\"TestLifecycleLateReadyCannotRepublishStoppedGeneration\",\"TestLifecycleFailedStartReleasesReservation\",\"TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime\",\"TestBoundNetworkOfficialUsesNativeParserAndPreservesDefaults\",\"TestBoundNetworkCustomPreservesExactIdentityAndConfiguration\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem\",\"TestBoundStartCapturesExactBootAndCannotBorrowRunningIdentity\",\"TestStartAddressStop\",\"TestDoubleStartIsAlreadyRunning\",\"TestBadDataDirIsBadDirError\",\"TestStartStopRestartNoLeak\"],\"tags\":[],\"testTimeout\":\"120s\",\"commandSeconds\":240,\"expectedEvents\":31},{\"label\":\"android-bound-core\",\"package\":\"github.com/anyproto/any/mobile/android\",\"parents\":[\"TestBoundMobileResultCarriesExactIdentityAndClearsFailure\"],\"tags\":[\"gomobile\"],\"testTimeout\":\"60s\",\"commandSeconds\":180,\"expectedEvents\":1},{\"label\":\"ios-bound-core\",\"package\":\"github.com/anyproto/any/mobile/ios\",\"parents\":[\"TestBoundCArchiveCoreCarriesExactIdentityAndClearsFailure\"],\"tags\":[],\"testTimeout\":\"60s\",\"commandSeconds\":180,\"expectedEvents\":1}]")
SUBCASES = json.loads("{\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts\":[\"legacy-core\",\"bound-core\"],\"TestLifecycleFailedStartReleasesReservation\":[\"empty-directory\",\"invalid-mode\",\"bound-network\",\"runner-failure\"],\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem\":[\"missing\",\"malformed\",\"duplicate\",\"empty\",\"space\",\"tab\",\"nul\",\"del\",\"long_ascii\",\"long_utf8\"]}")
EXPECTED_SELECTION = json.loads("{\"admission\":\"The qualification owner must bind the exact full physical source, toolchain, selected runner identifiers, resources, deadlines, child custody and final source witness before execution. This file authorizes no execution and relaxes no resource gate.\",\"affectedExistingParents\":[\"TestStartAddressStop\",\"TestDoubleStartIsAlreadyRunning\",\"TestBadDataDirIsBadDirError\",\"TestStartStopRestartNoLeak\"],\"affectedExistingSource\":{\"bytes\":10883,\"sha256\":\"44270ad3062652ef091a0808eb1d247202e7b55dc4c935099293e7dfe9796b32\",\"sourceRelativePath\":\"internal/embedded/embedded_test.go\"},\"apple\":\"NOT_RUN\",\"bootParentsByPackage\":{\"internal/embedded\":[\"TestBoundNetworkOfficialUsesNativeParserAndPreservesDefaults\",\"TestBoundNetworkCustomPreservesExactIdentityAndConfiguration\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem\",\"TestBoundStartCapturesExactBootAndCannotBorrowRunningIdentity\"],\"mobile/android\":[\"TestBoundMobileResultCarriesExactIdentityAndClearsFailure\"],\"mobile/ios\":[\"TestBoundCArchiveCoreCarriesExactIdentityAndClearsFailure\"]},\"bootSourceCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"combinedWithExactN24\":{\"childEvents\":31,\"executedEvents\":0,\"notAnExecutionPlan\":true,\"parentEvents\":26,\"selectionPath\":\"Tools/AnyEngineValidation/native_bound_http_source_20261128/test-selection.json\",\"selectionSHA256\":\"87d1ca5bf68563f50d7557b350ffd15e0ffcd496db62d67ac3eba07111fb0590\",\"sourceCommit\":\"94fd763d459210b496557894628333d466abae73\",\"totalEvents\":57},\"compilation\":\"NOT_RUN\",\"exactParentMethods\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts\",\"TestLifecycleCancelledPendingStartCannotSkipPreviousDrain\",\"TestLifecycleGracefulStopFencesNextGeneration\",\"TestLifecycleGracefulStopWaitsAfterStopNow\",\"TestLifecycleLateReadyCannotRepublishStoppedGeneration\",\"TestLifecycleFailedStartReleasesReservation\",\"TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime\",\"TestBoundNetworkOfficialUsesNativeParserAndPreservesDefaults\",\"TestBoundNetworkCustomPreservesExactIdentityAndConfiguration\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem\",\"TestBoundStartCapturesExactBootAndCannotBorrowRunningIdentity\",\"TestBoundMobileResultCarriesExactIdentityAndClearsFailure\",\"TestBoundCArchiveCoreCarriesExactIdentityAndClearsFailure\",\"TestStartAddressStop\",\"TestDoubleStartIsAlreadyRunning\",\"TestBadDataDirIsBadDirError\",\"TestStartStopRestartNoLeak\"],\"expectedChildEvents\":16,\"expectedChildren\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts/legacy-core\",\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts/bound-core\",\"TestLifecycleFailedStartReleasesReservation/empty-directory\",\"TestLifecycleFailedStartReleasesReservation/invalid-mode\",\"TestLifecycleFailedStartReleasesReservation/bound-network\",\"TestLifecycleFailedStartReleasesReservation/runner-failure\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/missing\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/malformed\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/duplicate\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/empty\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/space\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/tab\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/nul\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/del\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/long_ascii\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem/long_utf8\"],\"expectedParentEvents\":17,\"expectedTotalRunAndPassEvents\":33,\"generatedABI\":\"NOT_PRODUCED\",\"newLifecycle\":{\"explicitChildren\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts/legacy-core\",\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts/bound-core\",\"TestLifecycleFailedStartReleasesReservation/empty-directory\",\"TestLifecycleFailedStartReleasesReservation/invalid-mode\",\"TestLifecycleFailedStartReleasesReservation/bound-network\",\"TestLifecycleFailedStartReleasesReservation/runner-failure\"],\"parents\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts\",\"TestLifecycleCancelledPendingStartCannotSkipPreviousDrain\",\"TestLifecycleGracefulStopFencesNextGeneration\",\"TestLifecycleGracefulStopWaitsAfterStopNow\",\"TestLifecycleLateReadyCannotRepublishStoppedGeneration\",\"TestLifecycleFailedStartReleasesReservation\",\"TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime\"],\"privateControlledRunnerParentCount\":6,\"realExportManagedAccountFreeParentCount\":1},\"noUntouchedMigrationNetworkOrFilesReplay\":true,\"originalStartAddressStopDeduplicatedAcrossBootAndLifecycle\":true,\"packages\":[{\"parents\":[\"TestLifecycleReservationCoversPendingLegacyAndBoundStarts\",\"TestLifecycleCancelledPendingStartCannotSkipPreviousDrain\",\"TestLifecycleGracefulStopFencesNextGeneration\",\"TestLifecycleGracefulStopWaitsAfterStopNow\",\"TestLifecycleLateReadyCannotRepublishStoppedGeneration\",\"TestLifecycleFailedStartReleasesReservation\",\"TestConcurrentLegacyAndBoundStartsShareOneManagedRuntime\",\"TestBoundNetworkOfficialUsesNativeParserAndPreservesDefaults\",\"TestBoundNetworkCustomPreservesExactIdentityAndConfiguration\",\"TestBoundNetworkRejectsUnrepresentableIdentityBeforeFilesystem\",\"TestBoundStartCapturesExactBootAndCannotBorrowRunningIdentity\",\"TestStartAddressStop\",\"TestDoubleStartIsAlreadyRunning\",\"TestBadDataDirIsBadDirError\",\"TestStartStopRestartNoLeak\"],\"path\":\"./internal/embedded\",\"tags\":[]},{\"parents\":[\"TestBoundMobileResultCarriesExactIdentityAndClearsFailure\"],\"path\":\"./mobile/android\",\"tags\":[\"gomobile\"]},{\"limitation\":\"Linux core/shim test does not qualify generated Apple C ABI or a framework.\",\"parents\":[\"TestBoundCArchiveCoreCarriesExactIdentityAndClearsFailure\"],\"path\":\"./mobile/ios\",\"requiresCGO\":true,\"tags\":[]}],\"protocol\":\"pinkha-embedded-lifecycle-and-boot-source-selection-v1\",\"sourceOnly\":true,\"status\":\"NOT_RUN\",\"swiftAffectedMethod\":\"AnyEmbeddedRuntimeTests.testRealManagedRuntimeLifecycleAndControlBoundary\",\"swiftTestsRun\":0}")
EXPECTED_ACTIONS = json.loads("[{\"action\":\"replace\",\"after\":{\"bytes\":15885,\"nativeMode\":384,\"sha256\":\"3b734dd4b3d05c51c4afec4e914d3c637d41e34c9545fd7749bc1aba8b09ae82\"},\"before\":{\"bytes\":15460,\"nativeMode\":384,\"sha256\":\"a1b52dda8a4232d544242f27bf13bc8a6f4b4832be5d90be2baf0ffa222c2088\"},\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/internal/embedded/embedded.go\",\"kind\":\"production\",\"sourceRelativePath\":\"internal/embedded/embedded.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":2162,\"nativeMode\":420,\"sha256\":\"df3e4bdd15dfedbda827cf53f6b65c1179a6b63a3c74617302b8ae91432992a6\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/internal/embedded/network_binding.go\",\"kind\":\"production\",\"sourceRelativePath\":\"internal/embedded/network_binding.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":6426,\"nativeMode\":420,\"sha256\":\"9346d49093706e152fd0da02b571fd037974c9ecbbc41871c2193df50c425740\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/internal/embedded/network_binding_test.go\",\"kind\":\"test\",\"sourceRelativePath\":\"internal/embedded/network_binding_test.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":1137,\"nativeMode\":420,\"sha256\":\"6850eb04ff0ae46c7a14da7495047d1f58aa399964d8baf97aa74ec4ef7c3e21\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/mobile/android/network_binding.go\",\"kind\":\"production\",\"sourceRelativePath\":\"mobile/android/network_binding.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":1106,\"nativeMode\":420,\"sha256\":\"3eee3e3661d30c483f5952036ab9737e81186da8862d4a7eb896b5ce564117e5\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/mobile/android/network_binding_test.go\",\"kind\":\"test\",\"sourceRelativePath\":\"mobile/android/network_binding_test.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":1966,\"nativeMode\":420,\"sha256\":\"9ec543d57dfd550aedff75c561f55e1297d37d4d43f8a177a6e12e53d3442ec5\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/mobile/ios/anylib_binding.go\",\"kind\":\"production\",\"sourceRelativePath\":\"mobile/ios/anylib_binding.go\",\"stage\":\"boot-binding\"},{\"action\":\"add\",\"after\":{\"bytes\":1007,\"nativeMode\":420,\"sha256\":\"ce1c00f8bcd2746c6d5f13775004fa9352a6340c7d3e69880d7a00924a301b21\"},\"before\":null,\"carrierCommit\":\"f372f5e243427822df27bf8bd2ba51bf8206c644\",\"carrierPath\":\"Tools/AnyEngineValidation/native_boot_network_binding_20261128/overlay/any/mobile/ios/anylib_binding_test.go\",\"kind\":\"test\",\"sourceRelativePath\":\"mobile/ios/anylib_binding_test.go\",\"stage\":\"boot-binding\"},{\"action\":\"replace\",\"after\":{\"bytes\":16440,\"nativeMode\":384,\"sha256\":\"7e04af3c356e2b7596540e69b54b7b1e390d00610e2cf2202e8356b1e17a9154\"},\"before\":{\"bytes\":15885,\"nativeMode\":384,\"sha256\":\"3b734dd4b3d05c51c4afec4e914d3c637d41e34c9545fd7749bc1aba8b09ae82\"},\"carrierCommit\":\"THIS_COMMIT\",\"carrierPath\":\"Tools/AnyEngineValidation/native_embedded_lifecycle_20261128/overlay/any/internal/embedded/embedded.go\",\"kind\":\"production\",\"sourceRelativePath\":\"internal/embedded/embedded.go\",\"stage\":\"embedded-lifecycle\"},{\"action\":\"add\",\"after\":{\"bytes\":19960,\"nativeMode\":420,\"sha256\":\"e92092ec1469323c9a0631dfd01cbad1973a6f1a54ab0deabb9c4ed8768ad026\"},\"before\":null,\"carrierCommit\":\"THIS_COMMIT\",\"carrierPath\":\"Tools/AnyEngineValidation/native_embedded_lifecycle_20261128/overlay/any/internal/embedded/lifecycle_reservation_test.go\",\"kind\":\"test\",\"sourceRelativePath\":\"internal/embedded/lifecycle_reservation_test.go\",\"stage\":\"embedded-lifecycle\"}]")
N24_MAP_PINS = json.loads("{\"production\":{\"bytes\":371724,\"sha256\":\"f5cee416ebf393079a3eedc7cf9890df64548628a90291803201ed0c6fdef645\"},\"qualification\":{\"bytes\":372692,\"sha256\":\"b757e6f81d7fadd76abfb0f6e96974896eee59c7dc62a6b984c021003bce7e47\"},\"sdkProduction\":{\"bytes\":148000,\"sha256\":\"4a756afeda551334ae012fd9256c0f7bec83321ab83bd5595b7ee99c90ef8f40\"}}")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode('utf-8')


def closed_relative(name):
    require(isinstance(name, str) and bool(name), 'public relative path string')
    path = PurePosixPath(name)
    require(bool(path.parts) and not path.is_absolute() and
            str(path) == name and '..' not in path.parts and '\\' not in name,
            'closed public extension path')
    return path


def projected_sdk(source_map):
    return {
        'files': {name[len(SDK_PREFIX):]: row for name, row in source_map['files'].items()
                  if name.startswith(SDK_PREFIX)},
        'modes': {name[len(SDK_PREFIX):]: mode for name, mode in source_map['modes'].items()
                  if name.startswith(SDK_PREFIX)}
    }


def validate_map(source_map, count):
    require(set(source_map) == {'files', 'modes'} and
            len(source_map['files']) == len(source_map['modes']) == count and
            set(source_map['files']) == set(source_map['modes']),
            'complete exact source and mode membership')
    for name, row in source_map['files'].items():
        closed_relative(name)
        require(set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int and
                0 <= row['bytes'] <= 32*MIB and isinstance(row['sha256'], str) and
                len(row['sha256']) == 64 and
                all(c in '0123456789abcdef' for c in row['sha256']) and
                type(source_map['modes'][name]) is int and
                0 <= source_map['modes'][name] <= 0o777,
                'bounded exact source identity and original mode')


def apply_actions(source_map, actions, include_tests, inverse=False):
    result = {'files': dict(source_map['files']), 'modes': dict(source_map['modes'])}
    sequence = reversed(actions) if inverse else actions
    for row in sequence:
        if row['kind'] == 'test' and not include_tests:
            continue
        name = row['sourceRelativePath']
        closed_relative(name)
        require(row['kind'] in ('production', 'test') and
                (name.endswith('_test.go') == (row['kind'] == 'test')),
                'explicit production versus test overlay')
        wanted = row['after'] if inverse else row['before']
        if wanted is None:
            require(row['action'] == 'add' and name not in result['files'] and
                    name not in result['modes'], 'addition requires genuine absence')
        else:
            require(result['files'].get(name) == {k: wanted[k] for k in ('bytes', 'sha256')} and
                    result['modes'].get(name) == wanted['nativeMode'],
                    'full ordered source preimage or postimage')
        replacement = row['before'] if inverse else row['after']
        if replacement is None:
            require(inverse and row['action'] == 'add', 'inverse removes only an exact addition')
            del result['files'][name]
            del result['modes'][name]
        else:
            result['files'][name] = {k: replacement[k] for k in ('bytes', 'sha256')}
            result['modes'][name] = replacement['nativeMode']
    return result


def admit_composition(admitted, asset_root, pin, identity, result):
    """Read only13 fixed public assets through the N owner's immutable reader.

    This never admits or reads the cache, a user account, a fixture, or a prior
    executable. The current N admission must already have completed its real
    release and full Runtime18/N24 source proof. Both N input maps are exact.
    """
    release = result.get('ECacheRelease', {})
    require(result.get('RootCacheReleaseAcknowledgedByCaller') is True and
            release.get('actualNativeEvents') == 117 and
            release.get('actualSwiftMethods') == 23 and
            release.get('allRecordedGroupsNormallyClosed') is True and
            result.get('archivedNGoCacheUsedOrRestored') is False and
            isinstance(result.get('cacheRootStableIdentity'), list) and
            len(result['cacheRootStableIdentity']) == 5 and
            type(result.get('cacheAllocationBefore')) is int,
            'upstream actual E release and separately admitted physical cache are mandatory')
    asset_root = Path(asset_root)
    require(asset_root.is_absolute() and asset_root.resolve() == asset_root and
            asset_root.name == 'embedded-boot-lifecycle', 'fixed physical prepared asset subdirectory')
    public_raw, observed = {}, {}
    for name, row in ASSET_ROWS.items():
        path = asset_root/closed_relative(name)
        raw = pin(path, row['sha256'], max(1, row['bytes']), mode=row['mode'])
        require(identity(raw) == {k: row[k] for k in ('bytes', 'sha256')},
                'complete pinned extension asset')
        public_raw[name] = raw
        observed[name] = dict(path=str(path), **row)
    selection = json.loads(public_raw['selection.json'])
    composition = json.loads(public_raw['composition.json'])
    production = json.loads(public_raw['native-production-source.json'])
    qualification = json.loads(public_raw['native-qualification-source.json'])
    require(selection == EXPECTED_SELECTION and selection['sourceOnly'] is True and
            selection['status'] == selection['compilation'] == 'NOT_RUN' and
            selection['expectedParentEvents'] == 17 and selection['expectedChildEvents'] == 16 and
            selection['expectedTotalRunAndPassEvents'] == 33,
            'exact source-only17-parent/33-event selection')
    require(composition['protocol'] == 'pinkha-n24-boot-lifecycle-composition-v1' and
            composition['status'] == 'PROSPECTIVE_SOURCE_MAPS_NOT_MATERIALIZED_NOT_COMPILED' and
            composition['orderedOverlayActions'] == EXPECTED_ACTIONS and
            composition['actualCompiles'] == composition['actualMaterializations'] ==
            composition['actualTests'] == 0 and composition['modesAreProspective'] is True,
            'exact prospective ordered source composition; no historical compile promotion')
    n_production, n_qualification = admitted['production'], admitted['candidate']
    validate_map(n_production, 1645)
    validate_map(n_qualification, 1649)
    validate_map(production, 1648)
    validate_map(qualification, 1656)
    require(identity(canonical(n_production)) == N24_MAP_PINS['production'] and
            identity(canonical(n_qualification)) == N24_MAP_PINS['qualification'] and
            identity(canonical(projected_sdk(n_production))) == N24_MAP_PINS['sdkProduction'],
            'whole original N24 maps and exact SDK755 projection')
    actions = composition['orderedOverlayActions']
    require(len(actions) == 9 and len({r['sourceRelativePath'] for r in actions}) == 8 and
            apply_actions(n_production, actions, False) == production and
            apply_actions(n_qualification, actions, True) == qualification and
            apply_actions(production, actions, False, inverse=True) == n_production and
            apply_actions(qualification, actions, True, inverse=True) == n_qualification,
            'complete forward and inverse of both source maps')
    require(projected_sdk(production) == projected_sdk(n_production) and
            projected_sdk(qualification) == projected_sdk(n_qualification) and
            len(projected_sdk(production)['files']) == 755 and
            len(projected_sdk(qualification)['files']) == 756,
            'all SDK production and qualification bytes/modes remain exact')
    overlay = dict(admitted['overlay'])
    original_overlay = dict(overlay)
    extension_names = {r['sourceRelativePath'] for r in actions}
    require(not extension_names.intersection(original_overlay),
            'boot/lifecycle paths are disjoint from N24 overlay')
    for row in actions:
        name = 'payloads/'+row['stage']+'/'+row['sourceRelativePath']
        raw = public_raw[name]
        require(identity(raw) == {k: row['after'][k] for k in ('bytes', 'sha256')},
                'each full boot and lifecycle stage body is pinned')
        overlay[row['sourceRelativePath']] = raw
    require({k: v for k, v in overlay.items() if k not in extension_names} == original_overlay and
            len(original_overlay) == 20 and len(overlay) == 28,
            'all20 N24 source payloads retained with only eight explicit additions/replacements')
    for name, raw in overlay.items():
        require(identity(raw) == qualification['files'][name],
                'effective overlay bytes equal complete qualification map')
    proof = {
        'protocol': PROTOCOL, 'assets': observed,
        'lifecycleSourceCommit': LIFECYCLE_SOURCE_COMMIT, 'n24SourceCommit': N24_SOURCE_COMMIT,
        'originalN24Production': N24_MAP_PINS['production'],
        'originalN24Qualification': N24_MAP_PINS['qualification'],
        'productionMap': ASSET_ROWS['native-production-source.json'],
        'qualificationMap': ASSET_ROWS['native-qualification-source.json'],
        'sourceOnlyInputWasNotAnExecution': True, 'completeForwardAndInverse': True,
        'baseFiles': 1638, 'n24ProductionFiles': 1645, 'n24QualificationFiles': 1649,
        'productionFiles': 1648, 'qualificationFiles': 1656,
        'sdkProductionFiles': 755, 'sdkQualificationFiles': 756,
        'newNativeAccountOrNetworkAcceptanceClaim': False,
        'noUntouchedMigrationNetworkOrFilesReplay': True
    }
    original_manifest = admitted['manifest']
    combined_manifest = {
        'protocol': 'pinkha-native-n24-plus-boot-lifecycle-source-manifest-v1',
        'status': 'SOURCE_COMPOSED_REQUIRES_ACTUAL_QUALIFICATION',
        'originalN24Manifest': original_manifest,
        'embeddedBootLifecycle': proof,
        'fullSourceCounts': {'base': 1638, 'production': 1648, 'qualification': 1656,
                             'sdkProduction': 755, 'sdkQualification': 756}
    }
    result['embeddedBootLifecycleSourceAdmission'] = proof
    return dict(admitted, production=production, candidate=qualification, overlay=overlay,
                manifest=combined_manifest, originalN24Manifest=original_manifest)


def run_selected(source, source_before, driver, python, offline, environment, *,
                 command, source_inventory, checkpoint, frozen, identity,
                 parse_events, normal, result, save):
    """Use only the caller's f9de command owner, deadlines and original budgets."""
    proof = result.get('embeddedBootLifecycleSourceAdmission', {})
    require(proof.get('completeForwardAndInverse') is True and
            proof.get('qualificationFiles') == 1656 and
            result.get('RootCacheReleaseAcknowledgedByCaller') is True and
            identity(canonical(source_before)) == {
                key: ASSET_ROWS['native-qualification-source.json'][key]
                for key in ('bytes', 'sha256')},
            'complete extension source and upstream ownership admission')
    require(str(offline) == OFFLINE_PATH and
            result['OSPolicy']['helperSHA256'] == OFFLINE_SHA and
            result['OSPolicy']['appliedBeforeEveryTestCommand'] is True and
            result['OSExecPython']['path'] == str(python) and
            result['goToolchain']['driver']['path'] == str(driver) and
            environment['CGO_ENABLED'] == '1' and environment['GOTOOLCHAIN'] == 'local',
            'same admitted OS denial, Python and physical Go/native toolchain')
    selected_result = {
        'protocol': PROTOCOL, 'status': 'RUNNING_SELECTED_COMPONENTS',
        'sourceSelection': ASSET_ROWS['selection.json'], 'phases': {},
        'privateControlledRunnerParents': 6, 'realMixedExportManagedParents': 1,
        'affectedExistingStandaloneParents': 4, 'additionalNativeProductBuilds': 0,
        'generatedAppleABIQualified': False, 'gomobileGeneratedBindingQualified': False,
        'newOSDenialProbeEvents': 0, 'inheritedActualOSDenialAndCurrentN24ProofRequired': True
    }
    result['embeddedBootLifecycle'] = selected_result
    for phase in PHASES:
        require(source_inventory(source, checkpoint) == source_before,
                'complete physical1656-source map before each extension selection')
        package = phase['package']
        methods = phase['parents']
        require(len(methods) == len(set(methods)), 'unique exact parent names')
        argv = [str(python), '-B', str(offline), '--exec', str(driver),
                'test', '-json', '-count=1', '-p', '2', '-parallel=1',
                '-timeout='+phase['testTimeout']]
        if phase['tags']:
            argv.append('-tags='+','.join(phase['tags']))
        argv.extend(['-run', '^('+'|'.join(methods)+')$', package])
        before = len(result['processes'])
        log, row = command(phase['label'], argv, source, environment, phase['commandSeconds'])
        require(normal(row) and len(result['processes']) == before+1 and
                result['processes'][-1] == row and row['argv'] == argv and
                row['cwd'] == str(source), 'one exact normally closed current owned command')
        require(Path(log) == Path(source).parent/phase['label']/'original.log',
                'selected log stays in its caller-owned label directory')
        raw = frozen(log, 16*MIB)
        require(row['logSHA256'] == identity(raw)['sha256'],
                'exact selected Go event log bound to the owned command row')
        events = parse_events(raw, {package: methods}, subcases=SUBCASES)
        require(events['runs'] == events['passes'] == phase['expectedEvents'] and
                events['skips'] == events['failures'] == 0,
                'complete exact phase run/pass set')
        selected_result['phases'][phase['label']] = {
            'processIndex': before, 'argv': argv, 'log': dict(path=str(log), **identity(raw)),
            'events': events
        }
        save()
    expected = {(phase['package'], parent) for phase in PHASES for parent in phase['parents']}
    for phase in PHASES:
        for parent in phase['parents']:
            expected.update((phase['package'], parent+'/'+child) for child in SUBCASES.get(parent, ()))
    actual = [(event['package'], event['name']) for phase in selected_result['phases'].values()
              for event in phase['events']['methods']]
    require(len(expected) == len(actual) == len(set(actual)) == 33 and set(actual) == expected,
            'one exact event for17 parents and16 children, with no duplicate legacy selection')
    require(source_inventory(source, checkpoint) == source_before,
            'complete physical source remains unchanged after all three extension commands')
    selected_result.update(status='PASS_SELECTED33_REQUIRES_OUTER_FINALIZATION',
        actualParents=17, actualSubcases=16, actualRuns=33, actualPasses=33, skips=0,
        affectedExistingParentNames=EXPECTED_SELECTION['affectedExistingParents'],
        actualMethods=[{'package': p, 'name': n} for p, n in sorted(actual)],
        oldStartAddressStopSelectedOnce=True, untouchedC13Runtime18MigrationFilesMethodsSelected=0)
    save()
    return selected_result


def finalize_combined(result, normal):
    """Called only after the N owner's one product build and module check."""
    extension = result['embeddedBootLifecycle']
    original = result['actualMethods']
    require(extension['status'] == 'PASS_SELECTED33_REQUIRES_OUTER_FINALIZATION' and
            extension['actualRuns'] == extension['actualPasses'] == 33 and
            extension['actualParents'] == 17 and extension['actualSubcases'] == 16 and
            extension['skips'] == 0 and
            original['parents'] == 9 and original['subcases'] == 15 and
            original['runs'] == original['passes'] == 24 and original['skips'] == 0,
            'separate complete N24 and embedded33 evidence')
    original_events = []
    for label in ('server-units', 'fresh-sdk', 'fresh-http'):
        original_events.extend((x['package'], x['name']) for x in result[label]['methods'])
    additional = [(x['package'], x['name']) for x in extension['actualMethods']]
    require(len(original_events) == len(set(original_events)) == 24 and
            len(additional) == len(set(additional)) == 33 and
            not set(original_events).intersection(additional),
            'disjoint original24 and new selected33 event sets')
    require(len(result['processes']) == 9 and all(normal(row) for row in result['processes']) and
            result['nativeProductBuilds'] == 1 and result['sourceFiles'] == 1656 and
            result['productionFiles'] == 1648 and
            result['sdkSourceFiles'] == 756 and result['sdkProductionFiles'] == 755,
            'nine normal owned commands and one coherent complete-source product')
    require(set(extension['phases']) == {phase['label'] for phase in PHASES} and
            [extension['phases'][phase['label']]['processIndex'] for phase in PHASES] == [4, 5, 6],
            'three extension commands remain between N24 tests and the sole native product build')
    for phase in PHASES:
        evidence = extension['phases'][phase['label']]
        row = result['processes'][evidence['processIndex']]
        require(row['argv'] == evidence['argv'] and row['cwd'] == result['sourceRoot'] and
                row['logSHA256'] == evidence['log']['sha256'],
                'each selected phase remains joined to its exact owned command and raw log')
    driver = result['goToolchain']['driver']['path']
    binary = result['nativeBinary']['path']
    require(result['processes'][7]['argv'] == [driver, 'build', '-p', '2', '-o', binary, './cmd/any'] and
            result['processes'][8]['argv'] == [driver, 'version', '-m', binary] and
            result['processes'][7]['cwd'] == result['processes'][8]['cwd'] == result['sourceRoot'],
            'one original native build and its exact module observation remain last')
    for index, label in enumerate(('server-units', 'fresh-sdk', 'fresh-http'), 1):
        require(result['processes'][index]['logSHA256'] == result['rawLogs'][label]['sha256'],
                'all original N24 parsed event streams remain joined to their owned rows')
    aggregate = {
        'parents': 26, 'subcases': 31, 'runs': 57, 'passes': 57, 'skips': 0,
        'n24Events': 24, 'embeddedBootLifecycleEvents': 33,
        'affectedExistingEmbeddedParents': 4,
        'untouchedC13Runtime18MigrationFilesMethodsSelected': 0,
        'methods': [{'package': p, 'name': n} for p, n in sorted(original_events+additional)],
        'nativeCLIAccountProof': False, 'generatedAppleABIQualified': False
    }
    result['combinedActualMethods'] = aggregate
    return aggregate
