#!/usr/bin/env python3
"""Pure validation of the exact, already produced public Offload evidence.

No filesystem, process, HTTP, account or key access. The caller supplies the
bounded byte dictionary and independently admits each original public source.
This module does not execute a controller or reuse a historical PID.
"""
import ast
import hashlib
import json

PASS_SHA = '75cfb31e711b2653905a76cf6faf3573976d3c88fa0548238b85c1ae916b85fd'
FAIL_SHA = '875ed86695e1cf5acc8ef38f5b6e553cb8d2fb2ef4cb885e52727d61a0e162da'
SOURCE_SHA = '2079f987b6735cfbcb779066ac6d4f34c7f0cf0732a9aa67ddefeef3b7d50553'
ORIGINAL_SOURCE_SHA = '58df056c9b02b88f3196d77114fb47100380183ae1fb2fd81be3a182b0633609'
INSTALL_SHA = '63285b0cb6b6436ff7a6a8eaba22ca5ed07426c658be5be3739d01b92a7e21ce'
PRODUCER_SHA = '9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602'
CLOUD_SHA = 'e6446c4ff820e0dcdf80ba298a977368a7a5c19ada0eea9dab1280998a6937ba'
VARIANT_SHA = 'c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692'
QUOTA_SHA = 'aa61aadca348b2c89bc0321f6239a299c4d2fb3d62014366e1c4b707defef100'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'
SOURCE_MANIFEST_SHA = '773f0a25422b3460a375182fb6f839fd71d7246ad8b489b6c20418bfab3b2471'
BINARY = {'bytes': 78107649, 'sha256': 'cac96a8ab3edb6a2e908f423c45726818bcf3cc223d57aa4018869702be0ee21'}
MEMBER = 'A7zf8i42qUR8rZJwHrztRqFPifD3upr1fkyN9V3pF72AAaGi'
OBJECT = 'bafyreid5n5gg366h3lsqdolu5wi6hffwtqfyhzb53ylneh626bnapnzj6q'
SPACE = 'bafyreiet62u77nehvmtgn45ltxrk6itepoighks3u4y2f3pjjotaczcsfi.361psf76ieku2'
FILE = 'BEaHYwGfZiM'
PROTECTED = 'ahKeFKn7uta'
PAYLOAD = {'bytes': 8192, 'sha256': '5b3ad191f3c210b61bd5d1ef5ffc838b7fbabe38e8b42207fa04bf2388831313', 'status': 200}
FILE_ROW = {'fileId': FILE, 'objectId': OBJECT, 'name': 'cloud-binary.bin', 'size': 8192,
            'rootCid': 'bafybeibfvxnwxvg6mufc4lksm4t544hwm3233ph3asn4lgdhjjifmj567i', 'inline': False, 'durable': True}
PROTECTED_ROW = {'fileId': PROTECTED, 'objectId': OBJECT, 'name': 'cloud-thumb.png', 'size': 12420,
                 'rootCid': 'bafybeighhcuudwqvbo36hmty4mrfdkp4cuuvzn3ddzspi7vjt7klnugg7e',
                 'inline': False, 'durable': True, 'cached': True, 'mime': 'image/png',
                 'variant': 'thumb', 'variantOf': 'YhnuHkqoHza'}


def require(value, message):
    if not value:
        raise AssertionError(message)


def validate(content, code, doc):
    def raw(relative, wanted):
        data = content[relative]
        require(isinstance(data, bytes) and hashlib.sha256(data).hexdigest() == wanted,
                'exact immutable public input: ' + relative)
        return data

    def record(relative, wanted):
        value = json.loads(raw(relative, wanted))
        require(isinstance(value, dict), 'public receipt is an object')
        return value

    original_source = raw(code + 'original/run_positive_full_tier_offload.py', ORIGINAL_SOURCE_SHA)
    source = raw(code + 'run_positive_full_tier_offload.py', SOURCE_SHA)
    raw(code + 'final_product_admission.py', ADMISSION_SHA)
    raw(code + 'owned_swift_commands.py', HELPER_SHA)
    for data in (original_source, source):
        ast.parse(data)
    manifest = record(code + 'variant-source-manifest.json',
                      '390287cfb93a77e85562812221aac8931cf6829c9209bf1b2d4e090ce7ae2b19')
    raw(code + 'variant-identity.review.patch',
        '126d42034f1c68bf0562d3e78fe160af683f0795f494b9373beb52b054eeec19')
    require(manifest['literalReplacementCount'] == 5 and manifest['inverseRestoresExactOriginal'] is True,
            'reviewed five-change controller successor')
    inverse = source.decode()
    for change in reversed(manifest['changes']):
        require(inverse.count(change['after']) == 1, 'unique exact successor replacement')
        inverse = inverse.replace(change['after'], change['before'])
    require(inverse.encode() == original_source, 'inverse preserves every other original controller byte')

    before = record(doc + 'receipts/original-attempt1-fail.json', FAIL_SHA)
    result = record(doc + 'receipts/attempt2-pass.json', PASS_SHA)
    install = record(doc + 'receipts/attempt2-source-install.json', INSTALL_SHA)
    producer = record(doc + 'receipts/native1616-producer.json', PRODUCER_SHA)
    cloud = record(doc + 'receipts/original-two-file-cloud.json', CLOUD_SHA)
    variant = record(doc + 'receipts/original-protected-variant.json', VARIANT_SHA)
    record(doc + 'receipts/historical-account-limits-read1.json', QUOTA_SHA)

    require(before['status'] == 'FAIL_BACKED_FULL_TIER_OFFLOAD_RETAINED' and
            before['errors'] == [{'type': 'RuntimeError', 'message': 'AssertionError: original file, not a variant redirection'}] and
            before['completionErrors'] == [] and before['offloadDispatches'] == [] and
            before['allOwnedGroupsPositivelyAbsent'] is True and len(before['processes']) == 1,
            'actual original zero-dispatch failure retained')
    old = before['processes'][0]
    require(old['exitCode'] == 0 and old['processGroupAbsent'] is True and old['forcedCleanup'] is True and
            old['signals'] == [15] and old['cleanupErrors'] == [], 'original forced cleanup remains explicit')
    require(all(row['method'] == 'GET' for row in before['requests']), 'no historical mutation to replay')
    require(result['retainedPreDispatchFailure'] == {
        'controllerSHA256': ORIGINAL_SOURCE_SHA, 'failureReclassified': False, 'forcedCleanup': True,
        'historicalProcessIDsProbed': False, 'offloadDispatches': 0, 'priorAcceptanceEventsReused': 0,
        'receiptSHA256': FAIL_SHA}, 'truthful original failure attribution')

    require(install['status'] == 'PASS_EXACT_POSITIVE_FULL_TIER_OFFLOAD_SOURCE_INSTALL_ONLY_NOT_RUN' and
            install['commands'] == [] and install['newChildren'] == 0 and install['errors'] == [] and
            install['sourceMembersUnchangedAtCompletion'] is True and install['installerUnchangedAtCompletion'] is True and
            install['installedFiles'] == {
                'run_positive_full_tier_offload.py': {'bytes': 51421, 'sha256': SOURCE_SHA},
                'final_product_admission.py': {'bytes': 28708, 'sha256': ADMISSION_SHA},
                'owned_swift_commands.py': {'bytes': 9527, 'sha256': HELPER_SHA}},
            'exact installed three-source closure without runtime claim')
    require(producer['status'] == 'PASS_FINAL_NATIVE_BUILD_AND_FILES_AUTHORITY34' and
            producer['sourceFiles'] == 1616 and producer['sdkSourceFiles'] == 735 and
            producer['sourceManifestSHA256'] == SOURCE_MANIFEST_SHA and
            {'bytes': producer['binaryBytes'], 'sha256': producer['binarySHA256']} == BINARY and
            producer['sourceUnchanged'] is True and producer['allOwnedGroupsPositivelyAbsent'] is True and
            producer['heartProductEmbedded'] is False and producer['appleRuntimeQualified'] is False,
            'same previously published standalone native1616 product')
    admission = result['correctedNativeProducer']
    require(admission['receiptSHA256'] == PRODUCER_SHA and admission['sourceFiles'] == 1616 and
            admission['sourceManifestSHA256'] == SOURCE_MANIFEST_SHA and admission['binary'] == BINARY and
            admission['finalAuthorityQualification']['sha256'] == '4be8657cd077774edc76767195a79f5e6b97fc10704dce12dc8f05f973a2d622',
            'runtime uses exact final-authority product and existing34 proof')
    require(cloud['status'] == 'PASS_TWO_DURABLE_CLOUD_FILES_AND_RECIPIENT_OFFLINE_ONLY' and
            cloud['selectedFilesCloudCustodyAccepted'] is True and cloud['allFourFilesAccepted'] is False and
            cloud['spaceID'] == SPACE and cloud['objectID'] == OBJECT,
            'only original two backed cloud files, no quota recovery inference')
    require(result['originalCloudProof']['receiptSHA256'] == CLOUD_SHA and
            result['originalCloudProof']['originalGroupsReexecuted'] == 0 and
            result['originalCloudProof']['historicalProcessIDsProbed'] is False,
            'no historical cloud replay or PID action')
    require(variant['status'] == 'PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES' and
            variant['ownerMetadataObserved'][PROTECTED] == PROTECTED_ROW and
            result['protectedVariantBinding'] == {
                'fileId': PROTECTED, 'historicalMethodsReplayed': 0, 'historicalReceiptSHA256': VARIANT_SHA,
                'rejectedAttemptFreshVariantBodyRecovered': False, 'variant': 'thumb', 'variantOf': 'YhnuHkqoHza'},
            'exact accepted protected thumbnail and original variant owner')

    require(result['protocol'] == 'pinkha-backed-full-tier-offload-cloud-refetch-v1' and
            result['status'] == 'PASS_ONE_BACKED_FULL_TIER_OFFLOAD_CLOUD_REFETCH_AND_COLD_READ_ONLY' and
            result['controller'] == {'bytes': 51421, 'sha256': SOURCE_SHA} and
            result['ownershipHelperSHA256'] == HELPER_SHA and
            result['errors'] == result['completionErrors'] == [], 'exact actual accepted runtime')
    for name in ['allOwnedGroupsPositivelyAbsent', 'positiveFullTierOffloadAccepted', 'coldUncachedNoContentAccepted',
                 'sameCloudCIDRedownloadAccepted', 'coldRestoredExactBytesAccepted', 'nativeSourceUnchanged',
                 'publicInputsUnchanged', 'qualifiedPublicSourcesUnchanged', 'protectedOtherFileMetadataUnchanged']:
        require(result[name] is True, 'actual accepted boundary: ' + name)
    for name in ['accountCopies', 'accountFileReadsByController', 'accountInitializations', 'callerPlaintextFilesWritten',
                 'compilerInvocations', 'inviteMutations', 'oldMethodsReexecuted', 'pinCalls', 'privateRecordExports',
                 'retainedCARFilesReadByController', 'retryCalls', 'roleMutations', 'uploadCalls']:
        require(result[name] == 0, 'unchanged zero-operation scope: ' + name)
    for name in ['allFourCloudFilesDurableClaim', 'quotaBypass', 'privateAccountByteCustodyClaim', 'cloudProviderInternalTraceClaim']:
        require(result[name] is False, 'no broader claim: ' + name)
    network = result['networkPolicy']
    require(network['P2PEnabled'] is False and network['globalP2PEnabled'] is False and
            network['localDiscoveryEnabled'] is False and network['senderNativeProcessStarted'] is False and
            network['currentSenderAbsenceCheckedBeforeEveryPhaseAndContent'] is True,
            'actual sender-absent and P2P-disabled cloud path')
    commands = result['processes']
    names = ['member-offload', 'member-offline-miss', 'member-cloud-refetch', 'member-offline-restored']
    require(len(commands) == len(result['phases']) == 4 and len({row['pid'] for row in commands}) == 4,
            'four fresh, separately closed native processes')
    require([row['name'] for row in result['phases']] == names, 'fixed ordered four phases')
    cached_pairs = [(True, False), (False, False), (False, True), (True, True)]
    for index, (phase, command) in enumerate(zip(result['phases'], commands)):
        require(command['exitCode'] == 0 and command['processGroupAbsent'] is True and
                command['forcedCleanup'] is False and command['cleanupErrors'] == command['signals'] == [] and
                command['unreapedLeaderDuringGroupCleanup'] is True, 'original owned normal group closure')
        require(phase['gracefulStopIntent'] == {'leaderUnreaped': True, 'pid': command['pid'], 'signal': 15} and
                phase['status'] == 'PASS_PHASE' and phase['accountId'] == MEMBER and phase['actor'] == 'member' and
                phase['stopRequested'] is True, 'same current-member phase and intentional graceful stop')
        require(phase['membership'] == [dict(identity=MEMBER, permission='reader', status='active', step=step)
                for step in ['self-member', 'self-member-final']], 'active Reader before and after every phase')
        rows = {row['step']: {key: value for key, value in row.items() if key != 'step'} for row in phase['fileMetadata']}
        require(len(rows) == 4 and rows['file-before'] == dict(FILE_ROW, cached=cached_pairs[index][0]) and
                rows['file-after'] == dict(FILE_ROW, cached=cached_pairs[index][1]) and
                rows['protected-before'] == rows['protected-after'] == PROTECTED_ROW,
                'exact full-tier CID/variant/bytes and cache transition')
        require(phase['closedPairObservation']['matchingProcesses'] == 0 and
                phase['closedPairObservation']['accountContentsRead'] is False and
                all(value['matchingProcesses'] == 0 and value['accountContentsRead'] is False
                    for value in phase['senderAbsence']), 'current sender absence with no account reads')
        offline = index in (1, 3)
        require(phase['offline'] is offline and all(value['localPeers'] == value['globalPeers'] == 0
                for value in phase['syncObservations']), 'no peer transfer')
        if offline:
            require(phase['actualOSPolicy']['noNewPrivileges'] is True and phase['actualOSPolicy']['seccompFilterMode'] == 2 and
                    all(value['networkPeers'] == 0 for value in phase['syncObservations']), 'fresh OS-offline process')
        if index == 0:
            require(phase['content'] == [], 'no content read needed for eviction phase')
        elif index == 1:
            require(len(phase['content']) == 1 and phase['content'][0]['status'] == 500 and
                    phase['content'][0]['errorCode'] == 'internal' and phase['content'][0]['filePlaintextBytesDelivered'] == 0,
                    'original native offline error, zero plaintext, no invented typed UX')
        else:
            require(phase['content'] == [PAYLOAD], 'same exact bytes/hash online and fresh offline')
    writes = [row for row in result['requests'] if row['method'] != 'GET']
    dispatches = result['offloadDispatches']
    require(len(writes) == len(dispatches) == 1 and writes[0] == dispatches[0], 'exactly one ledgered mutating request')
    write = dispatches[0]
    require(write['method'] == 'POST' and write['path'] == '/v1/spaces/' + SPACE + '/files/' + FILE + '/offload' and
            write['phase'] == 'member-offload' and write['status'] == 204 and
            write['stage'] == '204-and-full-tier-cache-eviction-confirmed' and
            write['effectOutcome'] == 'confirmed-cached-true-to-false' and write['response']['bytes'] == 0 and
            write['retainedResponse']['sha256'] == write['response']['sha256'] and
            write['callerFilePlaintextBytesRetained'] == 0, 'one original ACK and observed eviction, no retry')
    return {'actualOffloadReceiptSHA256': PASS_SHA, 'originalFailureSHA256': FAIL_SHA,
            'originalFailureRemainsFailed': True, 'originalFailureForcedCleanupRetained': True,
            'nativeProductReceiptSHA256': PRODUCER_SHA, 'nativeSourceFiles': 1616, 'sdkSourceFiles': 735,
            'actualPhases': names, 'actualNormalClosedGroups': 4, 'historicalGroupsProbedOrReexecuted': 0,
            'newRuntimeOrTestCommandsDuringPublication': 0, 'originalCurrentActiveReader': True,
            'fullTierPositiveOffloadQualified': True, 'sameCIDCloudRefetchQualified': True,
            'freshOfflineMissAndRestoredBytesQualified': True, 'originalOfflineStatus': 500,
            'originalOfflineErrorCode': 'internal', 'typedOfflineUXQualified': False,
            'quotaRecoveryQualified': False, 'allFourCloudFilesDurableQualified': False,
            'appleRuntimeQualified': False, 'consumerAdoptionQualified': False,
            'retainedPrivateInputReads': 0, 'historicalQuotaReceiptSHA256': QUOTA_SHA}
