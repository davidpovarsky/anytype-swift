#!/usr/bin/env python3
"""Pure receipt/source admission for the new bound HTTP and typed ACL-error qualifier.

This module has no process, account, mutation, or cache access of its own. The
caller supplies pinned reads and a bounded source census. Historical acceptance
is attributed to its original receipts; it never makes an overall FAIL a PASS.
The planned E cache release is currently unsatisfied and must receive a separate
source review when the actual successor and Swift closure exist.
"""
import json
from pathlib import Path

MIB = 1024**2
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
EXPECTED_BASE = json.loads("{\"compiled\":{\"bytes\":369957,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/compiled-source-inputs.json\",\"sha256\":\"3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4\"},\"fullSourceFiles\":1638,\"receipt\":{\"bytes\":19865,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/result.json\",\"sha256\":\"f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2\"},\"sdkFiles\":750,\"source\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/source\"}")
EXPECTED_FORMATTED = json.loads("{\"root\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7\",\"receipt\":{\"path\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7/result.json\",\"bytes\":9508,\"sha256\":\"d4669b849169f0e802bc02d5cfccc72ea5abed51d8401d7eed0bac93b3f52d14\"},\"manifest\":{\"bytes\":16997,\"mode\":384,\"path\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7/SOURCE_MANIFEST.json\",\"sha256\":\"48f16026321d8209a371b9be850c51a5ae25033168724a558c64c7e6f6bebb20\"},\"productionMap\":{\"bytes\":371724,\"mode\":384,\"path\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7/PRODUCTION_SOURCE_MAP.json\",\"sha256\":\"f5cee416ebf393079a3eedc7cf9890df64548628a90291803201ed0c6fdef645\"},\"sdkProductionMap\":{\"bytes\":148000,\"mode\":384,\"path\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7/SDK_PRODUCTION_SOURCE_MAP.json\",\"sha256\":\"4a756afeda551334ae012fd9256c0f7bec83321ab83bd5595b7ee99c90ef8f40\"},\"qualificationMap\":{\"bytes\":372692,\"mode\":384,\"path\":\"/mnt/development/projects/evidence/pinkha-n-bound-http-engine-formatted-20261128-draft7/QUALIFICATION_SOURCE_MAP.json\",\"sha256\":\"b757e6f81d7fadd76abfb0f6e96974896eee59c7dc62a6b984c021003bce7e47\"}}")
EXPECTED_COUNTS = json.loads("{\"fullWithNewTests\":1649,\"fullWithProductionChanges\":1645,\"newTestFiles\":4,\"originalFull\":1638,\"originalSDK\":750,\"productionAdditions\":7,\"productionChanges\":16,\"productionReplacements\":9,\"sdkWithNewTests\":756,\"sdkWithProductionChanges\":755}")
EXPECTED_RETAINED_C13 = json.loads("{\"actualMethodsRetained\":{\"sdk\":8,\"server\":5},\"binary\":{\"bytes\":78262881,\"mode\":448,\"path\":\"/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127/qualification-completion-attempt1/any\",\"sha256\":\"b6fb8137bfce60e5af23e5c912ed133ca0e15fc10c368d2eabddc0641379b482\"},\"compiledSourceInputsSHA256\":\"1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0\",\"completionSHA256\":\"a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d\",\"historicalProcessIDsProbedOrSignaled\":false,\"originalFailureSHA256\":\"2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b\",\"priorMethodReexecution\":0,\"sourceManifestSHA256\":\"f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3\"}")
EXPECTED_RUNTIME18 = json.loads("{\"receipt\":{\"bytes\":19865,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/result.json\",\"sha256\":\"f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2\"},\"actualMethods\":{\"freshSDKMethods\":1,\"oldMethodsRerun\":0,\"parents\":14,\"passes\":18,\"runs\":18,\"skips\":0,\"subcases\":4},\"rawLogs\":{\"fresh-sdk\":{\"bytes\":42097,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/fresh-sdk/original.log\",\"sha256\":\"26158576c5eff03c0d4a39837c3a5f7064a8d737069dabf22e07e11ba3720c19\"},\"sdk-units\":{\"bytes\":16478,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/sdk-units/original.log\",\"sha256\":\"c59f935902e3d987fb2aaee9f49412d300f05191f9eb80712de4826b82de4cae\"},\"server-units\":{\"bytes\":3388,\"path\":\"/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/server-units/original.log\",\"sha256\":\"430177af447db6e741fcc8f2c1e7e2145053c506c2e8a694fc91bfe6c4c4ea06\"}},\"sourceManifestSHA256\":\"12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9\",\"priorMethodsSelected\":0,\"priorProcessIDsProbed\":false}")
EXPECTED_E_CACHE = json.loads("{\"path\":\"/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1/cache\",\"physicalNotAlias\":true,\"archivedNCacheUsedOrRestored\":false,\"requiresRootExplicitOwnershipRelease\":true,\"requiresActualNative117ThenSwift23\":true,\"nativeReceiptPath\":\"/mnt/development/projects/evidence/pinkha-e-final-engine-20261127/runtime-attempt7/receipt.json\",\"swiftReceiptPath\":\"/mnt/development/projects/evidence/pinkha-e-final-engine-20261127/swift-attempt1/receipt.json\",\"nativeSource\":{\"path\":\"/mnt/development/projects/evidence/pinkha-e-historical-native-binary-full-custody-preparation-20261128-attempt2/qualify_final_engine_native_historical_custody.py\",\"bytes\":163688,\"sha256\":\"8033fbb2f4949a9992a23f4f07748402f50be215e7f179cb239f543e5ed60468\"},\"swiftSource\":{\"path\":\"/mnt/development/projects/evidence/pinkha-e-historical-native-binary-full-custody-preparation-20261128-attempt2/qualify_final_engine_swift_historical_custody.py\",\"bytes\":90775,\"sha256\":\"571c486ea77e716ccca89c24c418ab93c849e4690eec1811463b00dc2c7a2035\"},\"futureActualReceiptSHA256MustBeSuppliedByCaller\":true,\"newPhysicalMetadataAndAllocationBaselineRequired\":true,\"releaseCandidateState\":\"NATIVE117_ATTEMPT7_FAILED_NO_SWIFT23_NO_ROOT_RELEASE\",\"executionAdmissionCurrentlySatisfiable\":false,\"futureSuccessorRequiresSeparateExactSourceAndReceiptReview\":true}")
EXPECTED_WIRE = json.loads("{\"acceptedWireSHA256\":\"81029040a074debe3ad551ea1af2ce05680bb62c674624665f07e2e8661328cb\",\"bindingGET\":\"/v1/auth/engine-binding\",\"contract\":\"pinkha-any-http-engine-binding-v1\",\"localPropertyPOST\":\"/v1/pinkha/bound/spaces/:spaceId/properties/:objectId/set/:typeId\",\"nonAnyOwnerHTTP\":{\"code\":\"auth.binding_unsupported\",\"status\":501},\"requestHeaders\":[\"X-Any-Expected-Account-Id\",\"X-Any-Expected-Run-Id\"],\"responseHeaders\":[\"X-Any-Binding-Contract\",\"X-Any-Bound-Account-Id\",\"X-Any-Bound-Run-Id\"],\"settingsPATCH\":\"/v1/pinkha/bound/spaces/:spaceId/settings\",\"supportedBoundLocalOwner\":\"any\"}")
EXPECTED_LOCAL_BUILTIN = json.loads("{\"catalogGET\":\"/v1/spaces/:spaceId/types/any/properties\",\"kind\":\"datetime\",\"nativeStorage\":\"Unix milliseconds (TypeDateTime)\",\"owner\":\"any\",\"precisionEnforcedBy\":\"caller contract, no native rounding\",\"propertyId\":\"pinkhaLastOpenedV1\",\"scope\":\"local\",\"sourceSystemRoleEvidence\":\"separately required by consumer, not inferred by this builtin\",\"storedPath\":\"any.pinkhaLastOpenedV1\",\"xFormat\":{\"contract\":\"pinkha-last-opened-local-v1\",\"precision\":\"seconds\",\"type\":\"datetime\"}}")
EXPECTED_TYPED_ACL = json.loads("{\"cancellationAndDeadlinePrecedence\":503,\"code\":\"acl.record_not_found\",\"declineExpectedRequestRecordId\":false,\"status\":404,\"typedNativeErrors\":[\"ErrNoSuchRequest\",\"ErrNoSuchRecord\"],\"untypedLookalikeStatus\":500}")


def admit_sources(plan, pin, require, normal, identity, source_inventory, checkpoint, parse_events, result):
    """Return only the exact source composition admitted by the public receipts."""
    require(plan['base'] == EXPECTED_BASE and plan['formatted'] == EXPECTED_FORMATTED and
            plan['counts'] == EXPECTED_COUNTS and plan['retainedC13'] == EXPECTED_RETAINED_C13 and
            plan['retainedRuntime18'] == EXPECTED_RUNTIME18, 'fixed original/current composition inputs')

    def read_row(row, maximum=4*MIB):
        raw = pin(Path(row['path']), row['sha256'], maximum, row.get('mode'))
        require(identity(raw) == {key: row[key] for key in ('bytes', 'sha256')}, 'complete declared public bytes')
        return raw

    prior = json.loads(read_row(EXPECTED_BASE['receipt']))
    base_input = json.loads(read_row(EXPECTED_BASE['compiled']))
    base = Path(EXPECTED_BASE['source'])
    require(prior['status'] == 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT' and
            prior['errors'] == prior['completionErrors'] == [] and
            prior['allOwnedGroupsPositivelyAbsent'] is True and len(prior['processes']) == 6 and
            all(normal(row) for row in prior['processes']) and
            prior['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True,
                                       'originalC13Source': True}, 'actual Runtime18 source/product and six closed groups')
    require(prior['controller'] == {'bytes': 39818,
            'sha256': '5b74a95e00a9a45bab0310e64b7765ebbb70b133e1482093b23cbbe9355b8656'} and
            prior['compiledSourceInputSHA256'] == EXPECTED_BASE['compiled']['sha256'] and
            prior['sourceManifestSHA256'] == EXPECTED_RUNTIME18['sourceManifestSHA256'] and
            prior['sourceRoot'] == str(base) and prior['sourceFiles'] == 1638 and prior['sdkSourceFiles'] == 750 and
            prior['actualMethods'] == EXPECTED_RUNTIME18['actualMethods'] and
            prior['retainedC13'] == EXPECTED_RETAINED_C13 and prior['priorTestMethodsReexecuted'] == 0,
            'historical Runtime18 attribution, not a replay')
    require(prior['nativeBinary'] == plan['baseNative'] and prior['nativeProductBuilds'] == 1 and
            prior['standaloneAnySDKProducerNotEmbeddedHeart'] is True and
            prior['retainedPrivateAccountInputs'] == prior['nativeCLIAccountProcesses'] == 0,
            'the admitted original standalone native product')
    read_row(plan['baseNative'], 128*MIB)
    base_metadata = read_row(plan['baseNativeModule'], 65536)
    require(prior['binaryModuleMetadata'] == identity(base_metadata), 'actual Runtime18 original native module graph')

    historical_groups = {
        'sdk-units': {
            'github.com/anyproto/any-sync-sdk/internal/files/readguard': [
                'TestRuntimeObservationBindsActualReaderAndGuestHead',
                'TestRuntimeObservationWithholdsAfterCurrentAuthorityChanges',
                'TestRuntimeObservationUsesOriginalACLIsEmptyIncludingInvites'],
            'github.com/anyproto/any-sync-sdk/internal/spaceimpl': [
                'TestRuntimeCoordinatorMissingLimitsAndExplicitZeroStayDistinct',
                'TestRuntimeCoordinatorRejectsMalformedAndForeignCachedAnswers',
                'TestRuntimeCoordinatorPersistsSuccessfulAnswerAcrossOfflineReopen',
                'TestRuntimeCoordinatorCoalescesFetchAndDrainsOwnerCancellation',
                'TestRuntimeAccessNeedsPositiveOriginalPersonalProvenance'],
            'github.com/anyproto/any-sync-sdk/internal/syncstatus': [
                'TestRuntimeSyncObservationPreservesOriginalDomainsAndPrecedence',
                'TestRuntimeSyncObservationDistinguishesInheritedAndUnobserved']},
        'server-units': {'github.com/anyproto/any/internal/server': [
            'TestRuntimeStateWirePreservesAbsenceZeroAndOriginalAccessDomain',
            'TestRuntimeObjectWireDoesNotCastSDKSyncIntoHeartDomain',
            'TestRuntimeStateRoutesAdvertiseOnlyVersionedOptionalReads']},
        'fresh-sdk': {'github.com/anyproto/any-sync-sdk': [
            'TestRuntimeStateFreshScopeAndSyncStopAtSignedRemoval']}}
    historical_children = {'TestRuntimeObservationWithholdsAfterCurrentAuthorityChanges':
                           ['signed-removal', 'signed-head', 'account-retirement', 'space-retirement']}
    historical_events = {}
    require(prior['rawLogs'] == EXPECTED_RUNTIME18['rawLogs'], 'exact original three public event streams')
    for label, groups in historical_groups.items():
        checkpoint()
        raw = read_row(EXPECTED_RUNTIME18['rawLogs'][label], 16*MIB)
        events = parse_events(raw, groups, historical_children)
        require(events == prior[label], 'retained Runtime18 events independently reconstructed')
        historical_events[label] = events
    require(sum(row['passes'] for row in historical_events.values()) == 18, 'eighteen retained original events')
    result['retainedRuntime18'] = dict(EXPECTED_RUNTIME18, events=historical_events,
                                      originalOverallStatus=prior['status'])

    c13_root = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127')
    c13_original = json.loads(pin(c13_root/'qualification-attempt1/result.json',
                                 EXPECTED_RETAINED_C13['originalFailureSHA256']))
    c13_complete = json.loads(pin(c13_root/'qualification-completion-attempt1/result.json',
                                 EXPECTED_RETAINED_C13['completionSHA256']))
    require(c13_original['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
            c13_complete['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
            c13_complete['errors'] == c13_complete['completionErrors'] == [] and
            c13_complete['allOwnedGroupsPositivelyAbsent'] is True and
            len(c13_complete['processes']) == 4 and all(normal(row) for row in c13_complete['processes']) and
            c13_complete['retainedQualification']['receiptSHA256'] == EXPECTED_RETAINED_C13['originalFailureSHA256'] and
            c13_complete['retainedActualMethodCount'] == 8 and c13_complete['newActualMethodCount'] == 5 and
            c13_complete['sdk-eight']['runs'] == c13_complete['sdk-eight']['passes'] == 8 and
            c13_complete['server-five']['runs'] == c13_complete['server-five']['passes'] == 5 and
            c13_complete['priorTestMethodsReexecuted'] == 0 and
            c13_complete['compiledSourceInputSHA256'] == EXPECTED_RETAINED_C13['compiledSourceInputsSHA256'] and
            c13_complete['sourceManifestSHA256'] == EXPECTED_RETAINED_C13['sourceManifestSHA256'] and
            c13_complete['nativeBinary'] == EXPECTED_RETAINED_C13['binary'],
            'original C13 FAIL plus actual retained8/new5 remains separately attributed')
    result['retainedC13'] = EXPECTED_RETAINED_C13
    result['historicalProcessIDsProbedOrSignaled'] = False

    require(set(base_input) == {'files', 'modes'} and len(base_input['files']) == 1638 and
            set(base_input['files']) == set(base_input['modes']) and
            sum(name.startswith(SDK_PREFIX) for name in base_input['files']) == 750,
            'complete actual 1638-file/SDK750 source input map')
    base_before = source_inventory(base, checkpoint)
    require(base_before == base_input, 'full immutable Runtime18 bytes and modes before composition')

    formatted = json.loads(read_row(EXPECTED_FORMATTED['receipt']))
    manifest = json.loads(read_row(EXPECTED_FORMATTED['manifest']))
    production = json.loads(read_row(EXPECTED_FORMATTED['productionMap']))
    qualification = json.loads(read_row(EXPECTED_FORMATTED['qualificationMap']))
    sdk_production = json.loads(read_row(EXPECTED_FORMATTED['sdkProductionMap']))
    require(formatted['status'] == 'PASS_FORMAT2_RETAINED18_EXACT24_OBLIGATION_SOURCE_NOT_COMPILED_NOT_TESTED' and
            formatted['errors'] == formatted['completionErrors'] == [] and
            formatted['allOwnedGroupsPositivelyAbsent'] is True and len(formatted['commands']) == 1 and
            all(normal(row) for row in formatted['commands']) and
            formatted['compilerInvocations'] == formatted['nativeInvocations'] ==
            formatted['accountInputs'] == formatted['testsExecuted'] == formatted['originalSourceWrites'] == 0 and
            formatted['historicalGroupsProbed'] == 0 and formatted['formatterChildren'] == 2 and
            formatted['retainedFormattedSourceFiles'] == 18 and formatted['expectedTestEvents'] == 24 and
            formatted['sourceCounts'] == EXPECTED_COUNTS and
            all(formatted[key] is True for key in ('allFormattedOutputsAndMapsUnchanged',
                'allOriginalSourceInputsUnchanged', 'formatterBytesAndNonAccessMetadataUnchanged')),
            'actual two-file formatting with exact retained18; no native test acceptance')
    require(formatted['sourceManifest'] == EXPECTED_FORMATTED['manifest'] and
            formatted['productionSourceMap'] == EXPECTED_FORMATTED['productionMap'] and
            formatted['sdkProductionSourceMap'] == EXPECTED_FORMATTED['sdkProductionMap'] and
            formatted['qualificationSourceMap'] == EXPECTED_FORMATTED['qualificationMap'] and
            formatted['formatter'] == {'bytes': 3027672,
                'sha256': '3ca5e23c92e957338205edb7c8a19a0c4f211b2cf606e21171925f3001d12825'} and
            formatted['formatterWorker'] == {'bytes': 4861,
                'sha256': '17aa3f7e6e50a7b9d4cca8c436cb25ae3233e4be60a98835dc82f16e98c343d7'},
            'exact actual formatter and all final source-map identities')
    require(manifest['sourceState'] == 'FORMAT2_PLUS_EXACT_RETAINED18_NOT_COMPILED_NOT_TESTED' and
            manifest['actualTestEvents'] == 0 and manifest['expectedEvents'] == 24 and
            manifest['retainedOriginalRequiredEvents'] == 17 and manifest['addedRequiredEvents'] == 7 and
            manifest['parentMethods'] == plan['exactParentMethods'] and
            manifest['expectedChildren'] == plan['expectedChildren'] and
            manifest['wire'] == EXPECTED_WIRE and manifest['localBuiltin'] == EXPECTED_LOCAL_BUILTIN and
            manifest['aclConsumedRecordContract'] == EXPECTED_TYPED_ACL and
            manifest['counts'] == EXPECTED_COUNTS and manifest['base'] == EXPECTED_BASE,
            'exact compiled-boundary source scope and explicit24 unrun obligations')

    predecessor_rows = manifest['formattedPredecessor']
    old_completion = json.loads(read_row(predecessor_rows['receipt']))
    old_failure = json.loads(read_row(predecessor_rows['originalFailure']))
    old_manifest = json.loads(read_row(predecessor_rows['manifest']))
    read_row(predecessor_rows['formatterLog'], 2*MIB)
    require(old_failure['status'] == 'FAIL' and
            old_completion['status'] == 'PASS_RETAINED_FORMAT18_SOURCE_COMPOSITION_COMPLETION_ONLY' and
            old_completion['originalFailureReceipt'] == predecessor_rows['originalFailure'] and
            old_completion['originalOverallStatus'] == 'FAIL' and
            old_completion['commands'] == [] and old_completion['newChildInvocations'] ==
            old_completion['newFormatterInvocations'] == old_completion['compilerInvocations'] ==
            old_completion['nativeInvocations'] == old_completion['accountInputs'] == old_completion['testsExecuted'] == 0 and
            old_completion['retainedFormatterChildren'] == 18 and
            old_completion['allHistoricalFormatterGroupsWerePositivelyAbsent'] is True and
            old_completion['allOriginalSourceInputsUnchanged'] is True and
            old_completion['allFormattedOutputsAndMapsUnchanged'] is True and
            old_completion['errors'] == old_completion['completionErrors'] == [] and
            formatted['retainedCompletion'] == predecessor_rows['receipt'] and
            formatted['originalFormatterFailurePreserved'] == predecessor_rows['originalFailure'],
            'original formatter FAIL retained; exact completion is source-only and zero-child')
    overlay = {}
    combined = dict(manifest['productionFiles'])
    require(len(combined) == 16 and len(manifest['testFiles']) == 4 and
            not (set(combined) & set(manifest['testFiles'])), 'sixteen production plus four disjoint test paths')
    combined.update(manifest['testFiles'])
    for name, row in sorted(combined.items()):
        checkpoint()
        require(Path(row['path']) == Path(EXPECTED_FORMATTED['root'])/'overlay'/name and
                name and not name.startswith('/') and '..' not in Path(name).parts and
                row['mode'] in (0o600, 0o644), 'closed formatted source path and exact original mode')
        overlay[name] = read_row(row, 2*MIB)
    for old_group, new_group in [('productionFiles', 'productionFiles'), ('testFiles', 'testFiles')]:
        for name, old_row in old_manifest[old_group].items():
            current = manifest[new_group][name]
            require({k: current[k] for k in ('bytes', 'sha256', 'mode')} ==
                    {k: old_row[k] for k in ('bytes', 'sha256', 'mode')},
                    'all original18 formatted source bytes and modes remain exact')
    require(sum(len(old_manifest[key]) for key in ('productionFiles', 'testFiles')) == 18,
            'exact original formatted18 closure')

    worker_row = formatted['commands'][0]
    worker_argv = worker_row['argv']
    require(len(worker_argv) == 6 and worker_argv[1:3] == ['-B', '-c'] and
            identity(worker_argv[3].encode()) == formatted['formatterWorker'],
            'actual two-file worker source bound to original argv')
    worker_log = pin(Path(EXPECTED_FORMATTED['root'])/'formatter/original.log',
                     worker_row['logSHA256'], 2*MIB)
    worker = json.loads(worker_log)
    require(worker['status'] == 'PASS_SOURCE_FORMATTING_REQUIRES_OUTER_CLOSURE' and
            worker['compilerInvocations'] == worker['nativeSDKInvocations'] ==
            worker['accountInputs'] == worker['sourceFileWrites'] == 0 and len(worker['rows']) == 2,
            'actual formatter worker produced only two declared public sources')
    expected_two = {'internal/server/handlers_acl_common.go',
                    'internal/server/handlers_acl_consumed_request_test.go'}
    seen_two = set()
    import base64
    for row in worker['rows']:
        name = row['path']
        require(name in expected_two and name not in seen_two and row['exitCode'] == 0 and
                row['sameOwnedGroupAtStart'] is True and row['stderr'] == '' and
                row['output'] == identity(overlay[name]) and
                base64.b64decode(row['source'], validate=True) == overlay[name],
                'each new source equals its actual canonical formatter stdout')
        seen_two.add(name)
    require(seen_two == expected_two, 'exact two new formatted paths')

    expected_files, expected_modes = dict(base_input['files']), dict(base_input['modes'])
    require(set(manifest['productionBeforeImages']) == set(manifest['productionFiles']),
            'complete production before-image map')
    for name, row in manifest['productionFiles'].items():
        require(expected_files.get(name) == manifest['productionBeforeImages'][name],
                'exact Runtime18 production preimage')
        expected_files[name] = {k: row[k] for k in ('bytes', 'sha256')}
        expected_modes[name] = row['mode']
    require(production == {'files': expected_files, 'modes': expected_modes} and
            len(expected_files) == 1645 and sum(name.startswith(SDK_PREFIX) for name in expected_files) == 755,
            'complete production1645/SDK755 source census')
    require(sdk_production == {
                'files': {name[len(SDK_PREFIX):]: row for name, row in expected_files.items() if name.startswith(SDK_PREFIX)},
                'modes': {name[len(SDK_PREFIX):]: mode for name, mode in expected_modes.items() if name.startswith(SDK_PREFIX)}},
            'exact SDK-only production census')
    for name, row in manifest['testFiles'].items():
        require(name not in expected_files, 'new tests are additions, not replacements of old cohorts')
        expected_files[name] = {k: row[k] for k in ('bytes', 'sha256')}
        expected_modes[name] = row['mode']
    require(qualification == {'files': expected_files, 'modes': expected_modes} and
            len(expected_files) == 1649 and sum(name.startswith(SDK_PREFIX) for name in expected_files) == 756,
            'complete qualification1649/SDK756 source census')
    result['sourceFormatting'] = {'actualTwoFileReceipt': EXPECTED_FORMATTED['receipt'],
        'retained18Completion': predecessor_rows['receipt'],
        'original18FormatterFailure': predecessor_rows['originalFailure'],
        'actualFormatterChildrenReexecuted': 0, 'sourceOnlyDoesNotEstablishTests': True}
    return {'prior': prior, 'baseBefore': base_before, 'baseModule': base_metadata,
            'manifest': manifest, 'production': production, 'candidate': qualification, 'overlay': overlay}


def admit_e_cache_release(plan, native_sha, swift_sha, pin, require, normal, identity, result):
    """No cache access: require exact separately released E receipts and controls.

    The current fixed Native attempt7 receipt is an actual FAIL. Therefore this
    candidate cannot authorize cache use. An eventual E successor must receive
    its own exact path/hash/schema review before these constants are updated.
    Root's ownership grant is still a separate caller prerequisite.
    """
    require(plan['ECache'] == EXPECTED_E_CACHE, 'fixed planned E release boundary')
    native_path = Path(EXPECTED_E_CACHE['nativeReceiptPath'])
    swift_path = Path(EXPECTED_E_CACHE['swiftReceiptPath'])
    for source in (EXPECTED_E_CACHE['nativeSource'], EXPECTED_E_CACHE['swiftSource']):
        raw = pin(Path(source['path']), source['sha256'], 512*1024)
        require(identity(raw) == {key: source[key] for key in ('bytes', 'sha256')},
                'exact reviewed E release-controller bytes')
    native = json.loads(pin(native_path, native_sha, 8*MIB))
    require(native['status'] == 'PASS_ACTUAL_NATIVE117_POSITIVE_EMPTY_KV_FULLSPACE_ACCOUNT_RUN_CLIPBOARD_NOT_SWIFT_OR_APPLE' and
            native['errors'] == native['completionErrors'] == [] and
            native['allOwnedGroupsPositivelyAbsent'] is True and len(native['commands']) == 17 and
            all(normal(row) for row in native['commands']) and
            native['actualNewTestEventCount'] == 113 and native['retainedPassingTestEventCount'] == 4 and
            native['actualTopLevelMethods'] == 56 and native['actualSubcases'] == 61 and
            native['historicalBinaryCustodyInputsUnchanged'] is True and
            native['allRecordedInputsUnchanged'] is True, 'actual Native117 acceptance and full positive closure required')
    native_source = EXPECTED_E_CACHE['nativeSource']
    require(native['immutableInputManifest'][native_source['path']] ==
            {key: native_source[key] for key in ('bytes', 'sha256')} and
            native['environment']['GOCACHE'] == EXPECTED_E_CACHE['path'] and
            native['goToolchain']['actualEnvironment']['GOCACHE'] == EXPECTED_E_CACHE['path'] and
            native['resourcePolicy']['sharedCacheGrowthCapBytes'] == 512*MIB and
            type(native['sharedCacheAllocatedBefore']) is int and native['sharedCacheAllocatedBefore'] >= 0 and
            type(native['sampledSharedCacheGrowthPeakBytes']) is int and
            0 <= native['sampledSharedCacheGrowthPeakBytes'] <= 512*MIB,
            'actual E compiler cache path and bounded growth provenance')
    swift = json.loads(pin(swift_path, swift_sha, 8*MIB))
    require(swift['status'] == 'PASS_TWENTYTHREE_ACTUAL_FINAL_SWIFT_OWNER_PROTOCOL_AND_NATIVE_FRAME_METHODS_NOT_APPLE' and
            swift['errors'] == swift['completionErrors'] == [] and
            swift['allOwnedGroupsPositivelyAbsent'] is True and len(swift['commands']) == 1 and
            all(normal(row) for row in swift['commands']) and len(swift['methods']) == 23 and swift['skips'] == 0 and
            swift['allActualDependencyInputsUnchanged'] is True and
            swift['allRecordedInputsUnchanged'] is True and swift['historicalBinaryCustodyInputsUnchanged'] is True and
            swift['canonicalNativeQualificationSHA256'] == native_sha,
            'actual subsequent Swift23 acceptance and exact Native117 receipt binding')
    swift_source = EXPECTED_E_CACHE['swiftSource']
    require(swift['immutableInputManifest'][swift_source['path']] ==
            {key: swift_source[key] for key in ('bytes', 'sha256')},
            'actual executing Swift release-controller identity')
    result['ECacheRelease'] = {'nativeReceipt': {'path': str(native_path), 'sha256': native_sha},
        'swiftReceipt': {'path': str(swift_path), 'sha256': swift_sha},
        'nativeController': native_source, 'swiftController': swift_source,
        'actualNativeEvents': 117, 'actualSwiftMethods': 23,
        'allRecordedGroupsNormallyClosed': True, 'historicalProcessIDsProbedOrSignaled': False,
        'physicalCache': EXPECTED_E_CACHE['path'], 'newNBaselineRequired': True,
        'rootOwnershipReleaseIsSeparateCallerPrerequisite': True}
