"""Validate only the fixed public publication packet; perform no I/O or dispatch."""
from collections import Counter
import hashlib
import json


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def closed(value, count):
    rows = value['processes']
    require(value['errors'] == value['completionErrors'] == [], 'actual receipt errors')
    require(value['allOwnedGroupsPositivelyAbsent'] and len(rows) == count,
            'exact actual owned command count and positive absence')
    require(len({row['pid'] for row in rows}) == count and all(
        row['exitCode'] == 0 and row['processGroupAbsent'] is True and
        not row['forcedCleanup'] and row['cleanupErrors'] == [] for row in rows),
        'normal actual owned command closure')


def validate(content, code, doc, admission):
    def raw(name):
        return content[doc + 'receipts/' + name]

    def receipt(name):
        return json.loads(raw(name + '.json'))

    candidate = json.loads(content[code + 'sdk_overlay/manifest.json'])
    require(identity(content[code + 'sdk_overlay/manifest.json'])['sha256'] ==
            admission.CANDIDATE_SHA, 'immutable source candidate')
    require(identity(content[code + 'sdk_overlay/sdk-final-files-authority.patch'])['sha256'] ==
            admission.PATCH_SHA, 'immutable thirteen-path SDK patch')
    require(len(candidate['changes']) == 13, 'exact thirteen-path source overlay')
    for name, row in candidate['changes'].items():
        require(identity(content[code + 'sdk_overlay/' + name]) ==
                {key: row[key] for key in ('bytes', 'sha256')}, 'exact overlay after-image')

    unit_failure = receipt('final34-units-original-failure')
    require(identity(raw('final34-units-original-failure.json'))['sha256'] ==
            admission.PRIOR_RECEIPT_SHA, 'preserved original unit-parser FAIL')
    require(unit_failure['status'] == 'FAIL_FINAL_FILES_AUTHORITY34' and
            unit_failure['errors'] == [{'type': 'JSONDecodeError',
                                       'message': 'Expecting value: line 1 column 941 (char 940)'}],
            'original failure stays a failure with its exact cause')
    require(unit_failure['completionErrors'] == [] and
            unit_failure['allOwnedGroupsPositivelyAbsent'] and
            len(unit_failure['processes']) == 2 and
            all(row['exitCode'] == 0 and row['processGroupAbsent'] and
                not row['forcedCleanup'] and not row['cleanupErrors']
                for row in unit_failure['processes']), 'two retained completed unit-stage groups')
    early_failure = receipt('completion-attempt5-failure')
    require(early_failure['status'] == 'FAIL_FINAL_FILES_AUTHORITY34_COMPLETION' and
            early_failure['processes'] == [] and
            early_failure['errors'] == [{'type': 'KeyError', 'message': "'OSExecPython'"}] and
            early_failure['completionErrors'] == [], 'retained pre-child composition-shadow FAIL')

    qualification = receipt('final34-completion')
    admission.validate_actual34(qualification, candidate)
    require(identity(raw('final34-completion.json'))['sha256'] ==
            '4be8657cd077774edc76767195a79f5e6b97fc10704dce12dc8f05f973a2d622',
            'actual aggregate34 receipt')
    require(identity(raw('final34-units-original.log'))['sha256'] ==
            admission.PRIOR_UNIT_LOG_SHA, 'exact original32 unit log')
    units = candidate['selectedUnitParents'] + [
        parent + '/' + child for parent, children in candidate['selectedUnitSubcases'].items()
        for child in children]
    require(len(units) == 32, 'exact thirty-two unit event identities')
    original_events, measurement_chunks = admission.parse_actual_events(
        raw('final34-units-original.log'), admission.UNIT_PACKAGE, units)
    new_events, new_measurement_chunks = admission.parse_actual_events(
        raw('final34-fresh-original.log'), admission.SDK_PACKAGE,
        candidate['selectedFreshSDKParents'])
    require(identity(raw('final34-fresh-original.log'))['sha256'] ==
            qualification['processes'][0]['logSHA256'], 'actual new2 SDK log')
    require(new_measurement_chunks == [] and original_events + new_events == qualification['events'] and
            qualification['reusedEvents'] == original_events and qualification['newEvents'] == new_events,
            'aggregate is the exact retained32 plus actual new2 event stream')
    require([len(part.encode()) for part in measurement_chunks] == [57, 1024, 69, 65],
            'exact retained measurement framing')
    joined_measurement = ''.join(measurement_chunks)
    marker = 'READGUARD_CACHED_MEASUREMENT '
    require(len(joined_measurement.encode()) <= 65536 and joined_measurement.endswith('\n') and
            joined_measurement.count(marker) == 1, 'one complete same-test measurement')
    measurement_line = next(line for line in joined_measurement.splitlines() if marker in line)
    require(qualification['observedCachedMeasurements'] ==
            [json.loads(measurement_line.split(marker, 1)[1])], 'retained measured values are exact')
    require(qualification['reusedProcesses'] == unit_failure['processes'] and
            qualification['reusedAllOwnedGroupsPositivelyAbsent'] and
            qualification['historicalProcessIDsProbed'] is False and
            qualification['priorUnitMethodsReexecuted'] == 0 and
            qualification['priorMeasurementReexecuted'] is False and
            qualification['eventsRepresentAggregateOnly'] is True,
            'historical ownership and no-replay attribution remain separate')
    require(unit_failure['goToolchain'] == qualification['goToolchain'] and
            unit_failure['OSPolicy'] == qualification['OSPolicy'] and
            unit_failure['OSExecPython'] == qualification['OSExecPython'] and
            unit_failure['sourceUnchanged'] and unit_failure['qualifiedPublicSDKBaseUnchanged'] and
            unit_failure['usedPublicInputsUnchanged'] and
            qualification['originalAttempt4PublicSourceUnchanged'], 'exact retained source/toolchain/OS equality')

    base_map = json.loads(raw('base1607-source.json'))['files']
    require(len(base_map) == 1607 and identity(raw('base1607-source.json'))['sha256'] ==
            admission.BASE_MANIFEST_SHA, 'exact existing qualified base1607 map')
    expected = dict(base_map)
    for name, row in candidate['changes'].items():
        path = admission.SDK_PREFIX + name
        old = base_map.get(path)
        require((None if old is None else old['sha256']) == row['beforeSHA256'],
                'exact base source before-image')
        expected[path] = {key: row[key] for key in ('bytes', 'sha256')}
    require(len(expected) == 1616, 'exact composed full native source count')
    sdk = {name.removeprefix(admission.SDK_PREFIX): row for name, row in expected.items()
           if name.startswith(admission.SDK_PREFIX)}
    require(len(sdk) == 735 and json.loads(raw('final735-sdk-source.json')) == sdk and
            identity(raw('final735-sdk-source.json'))['sha256'] ==
            qualification['sourceManifestSHA256'], 'actual tested735 equals exact source composition')

    producer = receipt('native-producer')
    closed(producer, 3)
    require(producer['status'] == 'PASS_FINAL_NATIVE_BUILD_AND_FILES_AUTHORITY34' and
            identity(raw('native-producer.json'))['sha256'] ==
            '9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602',
            'actual single native build')
    require(producer['controller']['sha256'] ==
            identity(content[code + 'native_producer/build_final_authority_native.py'])['sha256'] and
            producer['admissionModule']['sha256'] ==
            identity(content[code + 'native_producer/final_product_admission.py'])['sha256'],
            'exact actual producer and pure source admission')
    require(producer['qualification']['sha256'] == identity(raw('final34-completion.json'))['sha256'] and
            producer['finalCandidateSHA256'] == admission.CANDIDATE_SHA and
            producer['finalPatchSHA256'] == admission.PATCH_SHA and
            producer['sourceFiles'] == 1616 and producer['sdkSourceFiles'] == 735,
            'native build joins the actual tested final source')
    require(producer['sourceUnchanged'] and producer['baseSourceUnchanged'] and
            producer['qualifiedSDKSourceUnchanged'] and producer['admittedPublicInputsUnchanged'],
            'actual producer final source checks')
    require(producer['retainedPrivateInputs'] == producer['nativeAccountProcesses'] ==
            producer['replayedTests'] == 0 and producer['nativeCLIStarted'] is False and
            producer['heartProductEmbedded'] is False and producer['appleRuntimeQualified'] is False,
            'standalone Linux build-only scope')
    native_map = json.loads(raw('native1616-source.json'))
    require(native_map['files'] == expected and identity(raw('native1616-source.json'))['sha256'] ==
            producer['sourceManifestSHA256'], 'actual complete native1616 map')

    http = receipt('metadata-http18')
    closed(http, 3)
    require(identity(raw('metadata-http18.json'))['sha256'] ==
            '8aaaf6fd04eb535bea79116ceaeac5a0dab6293d2d40bb1202616a6cef1c94ee',
            'exact actual metadata HTTP18 receipt')
    require(http['protocol'] == 'pinkha-current-metadata-authority-get-only-v1' and
            http['status'] == 'PASS_ORIGINAL_CURRENT_METADATA_AUTHORITY_HTTP18_ONLY',
            'actual current original-member metadata18 acceptance')
    require(http['controller']['sha256'] ==
            identity(content[code + 'current_metadata_http/verify_metadata_authority_http.py'])['sha256'],
            'actual reviewed GET-only controller')
    require(http['correctedNativeProducer']['receiptSHA256'] == identity(raw('native-producer.json'))['sha256'] and
            http['correctedNativeProducer']['binary'] ==
            {'bytes': producer['binaryBytes'], 'sha256': producer['binarySHA256']} and
            http['correctedNativeProducer']['sourceManifestSHA256'] == producer['sourceManifestSHA256'],
            'HTTP18 uses the one exact final native product')
    denied = [row for row in http['requests'] if row['kind'] == 'metadata-denial']
    require(http['metadataDenialCount'] == len(denied) == 18 and
            all(row['status'] == 403 and row.get('errorCode') == 'acl.forbidden' and
                row['stage'] == 'confirmed-typed-denial' for row in denied) and
            Counter(row['phase'] for row in denied) ==
            Counter({'member-online': 9, 'member-offline': 9}), 'exact eighteen typed metadata decisions')
    space = 'bafyreigwbj5ipsthay6xcrt6xcw5hpuagje2jiupq4zhidbevd4miqbrmu.qhz8hrb21y1l'
    object_id = 'bafyreicytuyyuw7nu6cklsgptni4k5xoyi3u4suijh6lp5moki2nvtpi7e'
    member = 'AAFSi1CkNvwiTLAkKWQF9K5GnLcfFaqvfYYCa1zmJWETjuyR'
    prefix = '/v1/spaces/' + space
    ids = {'E9ZfwB8Biag', 'hs6LTsotxAY', '9DSkw6W3eqv', 'SbLLxZDbq59', 'AEhbwaXwY7S'}
    routes = {prefix + '/files/' + file_id for file_id in ids} | {
        prefix + '/files?objectId=' + object_id, prefix + '/files',
        prefix + '/files/hs6LTsotxAY/status', prefix + '/files/stats'}
    require(set(http['syntheticFileBindings']) == ids and len(routes) == 9,
            'five exact known synthetic file identities')
    require([row['name'] for row in http['phases']] ==
            ['owner-observation', 'member-online', 'member-offline'], 'three exact API phases')
    for phase in http['phases'][1:]:
        require(phase['actor'] == 'member' and phase['accountId'] == member and
                phase['status'] == 'PASS_PHASE' and phase['stopRequested'] and
                phase['fileMetadata'] == [], 'removed member discloses no metadata')
        require(phase['membership'] == [
            {'step': step, 'identity': member, 'status': 'removed', 'permission': 'none'}
            for step in ('self-member', 'self-member-final')], 'current removal before and after')
        decisions = [row for row in denied if row['phase'] == phase['name']]
        require(Counter(row['path'] for row in decisions) == Counter(routes) and
                all(row['method'] == 'GET' and row['range'] is None for row in decisions),
                'each exact metadata route is denied once per phase')
    offline = http['phases'][2]
    require(offline['offline'] is True and
            offline['actualOSPolicy']['noNewPrivileges'] is True and
            offline['actualOSPolicy']['seccompFilterMode'] == 2 and
            offline['offlineSync'] == {'state': 'offline', 'networkPeers': 0,
                                      'localPeers': 0, 'globalPeers': 0},
            'fresh process uses actual unchanged OS denial with zero peers')
    require(http['publicInputsUnchanged'] and http['nativeSourceUnchanged'] and
            http['qualifiedPublicSourcesUnchanged'], 'HTTP final public/native source closure')
    for key in ('domainMutationRequests', 'accountFileReadsByController', 'accountCopies',
                'privateRecordExports', 'accountInitializations', 'roleRestorations',
                'uploadCalls', 'compilerInvocations', 'historicalPayloadRoutesRequested',
                'replayedContentDenials', 'cacheMutatorRequests'):
        require(http[key] == 0, 'no forbidden operation or old test replay: ' + key)
    for key in ('previousInsecureGETReplayed', 'freshAccountByteCustodyClaim',
                'independentSeventhRecordExportClaim', 'SSEHTTP403Claim',
                'canaryCurrentlyUncachedClaim', 'heldSDKReaderAcceptance'):
        require(http[key] is False, 'preserved narrow HTTP claim: ' + key)
    return {'finalSourceFiles': 1616, 'finalSDKFiles': 735, 'overlayPaths': 13,
            'retainedUnitEvents': 32, 'newFreshSDKEvents': 2, 'aggregateEvents': 34,
            'newMetadataHTTPDecisions': 18, 'nativeProduct': http['correctedNativeProducer'],
            'oldMethodsReexecutedDuringPublication': 0, 'retainedPrivateInputs': 0,
            'fullTierPositiveOffloadQualified': False, 'cloudQuotaBypass': False,
            'appleRuntimeQualified': False, 'heartProductEmbedded': False}
