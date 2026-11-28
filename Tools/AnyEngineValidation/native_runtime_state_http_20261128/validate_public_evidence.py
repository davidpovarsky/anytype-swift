"""Validate a new evidence append for the already completed runtime HTTP4 proof.

This module reads only supplied public bytes. It starts no process, accesses no
account, probes no historical PID and performs no live filesystem admission.
Historical Runtime18 and publication receipts retain their original scope.
"""
import ast
import hashlib
import json

PINS = json.loads(r'''{
  "D:parent-runtime18-publication.json": {
    "bytes": 75643,
    "sha256": "f87960af4e61eeb3a0cdf39cb0ad4b2d44ff942c0db71f6bdce7be8d6c0bf34e"
  },
  "D:runtime18-producer.json": {
    "bytes": 19865,
    "sha256": "f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2"
  },
  "D:runtime-http4-result.json": {
    "bytes": 22162,
    "sha256": "e33a43090d3cddf238b0a91b4641a4a354aaf2016b9d269dfcc2a6cbffeb26a9"
  },
  "D:http-source-installation.json": {
    "bytes": 2129,
    "sha256": "48f0d54609a57d2591a34b333a188d0bfff7ca39750912af50ac84518efd66cc"
  },
  "D:responses/007.json": {
    "bytes": 724,
    "sha256": "45f39842c33d7bafed4f6a858e0c1494889f2209b524a97d8921efc40a5f4f10"
  },
  "D:responses/008.json": {
    "bytes": 933,
    "sha256": "9c3889cbbe7802a0a8fe9cd173bfc3b0343a42993899b32461d701c389cabbd3"
  },
  "D:responses/015.json": {
    "bytes": 200,
    "sha256": "57bae69aceed403effbd8cd221a780c9aa309f5523e4b0619831ee5d765b2879"
  },
  "D:responses/016.json": {
    "bytes": 273,
    "sha256": "2c50097625c0a7e8100dc8dfb1796471bbe426b1f01b2ef23d0f06581593c956"
  },
  "C:runtime_wire_validation.py": {
    "bytes": 6189,
    "sha256": "dde0784eeda0182bf0d0a8ff71aad5f5219fe0856223cc93e6f736e0e2d5a876"
  }
}''')
BASE = '2a1762390e6635722b81ab04300f52dcb79dd794'
TREE = 'ea4d16fffe2597bcf58be39eec7c61179e4d0810'
BRANCH = 'codex/chatgpt-wave15-network-final-authority-20261127'
OWNER = 'A7MAdySTn1MR4Fb3gDr67ZeXEvt8fqNjtHEwB3b9kUGFZZya'
MEMBER = 'AAFSi1CkNvwiTLAkKWQF9K5GnLcfFaqvfYYCa1zmJWETjuyR'
SPACE = 'bafyreigwbj5ipsthay6xcrt6xcw5hpuagje2jiupq4zhidbevd4miqbrmu.qhz8hrb21y1l'
OBJECT = 'bafyreicytuyyuw7nu6cklsgptni4k5xoyi3u4suijh6lp5moki2nvtpi7e'
NETWORK = 'N72HQKYajADVPoyw2XXtyTScBYR7SwkudRULgED4CYyHdphU'
NATIVE = '/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/any'
NATIVE_SHA = '84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974'
HTTP_ROOT = '/mnt/development/projects/evidence/pinkha-n-runtime-state-http-20261127/attempt1'
SOURCE_ROOT = '/mnt/development/projects/evidence/pinkha-n-runtime-state-http-source-20261127-attempt1'
CONTROLS = {
    'owned_swift_commands.py': {'bytes': 9527, 'sha256': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'},
    'runtime_product_admission.py': {'bytes': 17546, 'sha256': 'f1755272ea4afd1a50d95ba9f085c9f61f25080b389b35359c6cc74337fcb496'},
    'runtime_wire_validation.py': {'bytes': 6189, 'sha256': 'dde0784eeda0182bf0d0a8ff71aad5f5219fe0856223cc93e6f736e0e2d5a876'},
    'verify_runtime_state_http.py': {'bytes': 41423, 'sha256': 'a7f0fbe8067946d35865be61d3c35a1b82fe3e1b85df6f06040c758273c4a18d'},
}


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def normal(rows, count):
    require(isinstance(rows, list) and len(rows) == count, 'exact historical process count')
    for row in rows:
        require(type(row['exitCode']) is int and row['exitCode'] == 0 and
                row['processGroupAbsent'] is True and row['forcedCleanup'] is False and
                row['cleanupErrors'] == [] and row['signals'] == [] and row['stopReason'] is None and
                row['unreapedLeaderDuringGroupCleanup'] is True and
                type(row['pid']) is int and row['pid'] > 0 and row['pgid'] == row['pid'],
                'original normal closed owner; no historical PID probe')
    require(len({row['pid'] for row in rows}) == count, 'distinct recorded owned groups')


def validate(content, code, doc):
    require(isinstance(content, dict) and all(isinstance(v, bytes) for v in content.values()),
            'public byte mapping only')
    extra = {doc+'README.md', code+'validate_public_evidence.py',
             code+'publish_runtime_http.template.py', doc+'RECOVERY_PROVENANCE.json'}
    names = {(code if key.startswith('C:') else doc)+key[2:] for key in PINS}
    require(set(content) == names | extra, 'exact nine retained inputs and four new public controls/documents')
    for key, wanted in PINS.items():
        name = (code if key.startswith('C:') else doc)+key[2:]
        require(identity(content[name]) == wanted, 'exact original public bytes: '+name)
    for name in (code+'validate_public_evidence.py', code+'publish_runtime_http.template.py'):
        ast.parse(content[name], filename=name)
    read = lambda name: json.loads(content[doc+name])
    parent = read('parent-runtime18-publication.json')
    require(parent['status'] == 'PASS_NORMAL_PUBLICATION_OF_RUNTIME_STATE15_ACTUAL18_HTTP4_PENDING' and
            parent['commit'] == BASE and parent['tree'] == TREE and parent['branch'] == BRANCH and
            parent['publicFileCount'] == 56 and parent['publicBytes'] == 2627432 and
            parent['errors'] == parent['completionErrors'] == [],
            'exact previously published Runtime15/18 parent, preserving HTTP4 pending label')
    for key in ('publicInputsUnchanged', 'publishedFilesUnchanged', 'fullUndeclaredGitTreePreserved',
                'allStartedOwnedGroupsPositivelyAbsent', 'existingOwnedWorktreeUsed'):
        require(parent[key] is True, 'accepted parent publication closure')
    for key in ('compilerInvocations', 'nativeInvocations', 'testMethodsReexecuted',
                'existingFilesReplaced', 'forcePushes', 'resetOperations'):
        require(parent[key] == 0, 'parent publication scope')
    normal(parent['commands'], 28)
    packet = parent['qualifiedPacket']
    require(packet['status'] == 'VALIDATED_PUBLIC_SOURCE15_ACTUAL18_HTTP4_NOT_RUN' and
            packet['sourcePaths'] == 15 and packet['sourceFiles'] == 1638 and packet['sdkSourceFiles'] == 750 and
            packet['actualNewRunPassEvents'] == 18 and packet['newParents'] == 14 and packet['newSubcases'] == 4 and
            packet['normalClosedGroups'] == 6 and
            packet['http4'] == {'actualDecisions': 0, 'actualRuntimeStatus': 'NOT_RUN',
                               'futureRequiredOwner200': 2, 'futureRequiredRemovedMember403': 2,
                               'newNativeProcesses': 0, 'sourceInstalled': True},
            'historical source/test proof remains separate from later HTTP4')
    producer = read('runtime18-producer.json')
    producer_sha = PINS['D:runtime18-producer.json']['sha256']
    require(producer['status'] == 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT' and
            producer['errors'] == producer['completionErrors'] == [] and
            producer['allOwnedGroupsPositivelyAbsent'] is True and
            producer['sourceFiles'] == 1638 and producer['sdkSourceFiles'] == 750 and
            producer['compiledSourceInputSHA256'] == '3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4' and
            producer['sourceManifestSHA256'] == '12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9' and
            producer['sourceRoot'] == '/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/source',
            'same already-qualified Runtime18 source producer')
    normal(producer['processes'], 6)
    require(producer['actualMethods'] == {'freshSDKMethods': 1, 'oldMethodsRerun': 0, 'parents': 14,
                                         'passes': 18, 'runs': 18, 'skips': 0, 'subcases': 4} and
            producer['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True,
                                          'originalC13Source': True},
            'historical eighteen events and full final source closure')
    for name in ('sdk-units', 'server-units', 'fresh-sdk'):
        require(producer[name] == packet['actualNewEvents'][name], 'parent retained exact original event inventory')
    require(packet['runtimeReceiptSHA256'] == producer_sha and
            producer['retainedC13']['actualMethodsRetained'] == {'sdk': 8, 'server': 5} and
            producer['retainedC13']['completionSHA256'] == packet['retainedC13']['completionSHA256'] ==
                'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d' and
            producer['retainedC13']['originalFailureSHA256'] == packet['retainedC13']['originalFailureSHA256'] ==
                '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b' and
            producer['retainedC13']['priorMethodReexecution'] == 0 and
            producer['retainedC13']['historicalProcessIDsProbedOrSignaled'] is False,
            'C13 original failure and retained eight plus five stay historical')
    binary = {'bytes': 78294169, 'mode': 0o700, 'path': NATIVE, 'sha256': NATIVE_SHA}
    require(producer['nativeBinary'] == packet['oneRetainedNativeProduct'] == binary,
            'same retained native executable; no rebuild or binary copy to Git')
    install = read('http-source-installation.json')
    require(install['status'] == 'PASS_EXACT_RUNTIME_STATE_HTTP4_SOURCE_INSTALL_ONLY_NOT_RUN' and
            install['sourceRoot'] == SOURCE_ROOT and install['installedFiles'] == CONTROLS and
            install['commands'] == install['errors'] == [] and install['dependentStageStatus'] == 'NOT_RUN' and
            install['installerUnchangedAtCompletion'] is True and install['sourceMembersUnchangedAtCompletion'] is True,
            'actual source installation retains its original not-run status')
    for key in ('accountInputs', 'compilerInvocations', 'nativeProcesses', 'newChildren',
                'oldMethodsReplayed', 'originalPathsReplaced', 'testInvocations'):
        require(install[key] == 0, 'source installation never becomes runtime evidence')
    result = read('runtime-http4-result.json')
    require(result['protocol'] == 'pinkha-native-runtime-state-http-four-v1' and
            result['status'] == 'PASS_CURRENT_AUTHORITY_RUNTIME_GET4_ONLY' and
            result['controller'] == CONTROLS['verify_runtime_state_http.py'] and
            result['ownershipHelperSHA256'] == CONTROLS['owned_swift_commands.py']['sha256'] and
            result['errors'] == result['completionErrors'] == [],
            'actual four-route result with exact installed controller and original owner')
    expected_producer = {'C13RetainedActualMethods': 13, 'binary': binary,
        'compiledSourceInputSHA256': producer['compiledSourceInputSHA256'],
        'newQualificationEvents': 18, 'oldMethodsReexecuted': 0,
        'receiptPath': '/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/result.json',
        'receiptSHA256': producer_sha, 'sdkSourceFiles': 750, 'sourceFiles': 1638,
        'sourceManifestSHA256': producer['sourceManifestSHA256']}
    require(result['runtimeNativeProducer'] == expected_producer, 'HTTP4 exact current Runtime18 native/source join')
    for key in ('allOwnedGroupsPositivelyAbsent', 'publicInputsUnchanged', 'nativeSourceUnchanged',
                'originalC13SourceUnchanged', 'productAndCompilerModesUnchanged', 'runtimeResponsesUnchanged'):
        require(result[key] is True, 'actual HTTP4 completion gate: '+key)
    for key in ('accountCopies', 'accountFileReadsByController', 'accountInitializations',
                'cloudQuotaActivationCalls', 'compilerInvocations', 'domainMutationRequests',
                'newNativeBuilds', 'oldContentOrMetadataRoutesReexecuted', 'privateRecordExports',
                'roleRestorations', 'uploadCalls'):
        require(result[key] == 0, 'exact finite HTTP4 scope: '+key)
    for key in ('PersonalSpaceProvenanceClaim', 'freshAccountByteCustodyClaim', 'heartSyncDateClaim',
                'independentSignedRecordExportClaim', 'nativeObjectExistenceClaim',
                'newRuntimeRouteOfflineHTTPAcceptance'):
        require(result[key] is False, 'unproved boundary remains explicitly unclaimed: '+key)
    require(result['nativeOperationalStoreWritesPossible'] is True and
            result['ownerObservationCount'] == result['removedMemberDenialCount'] == 2 and
            result['reusedContentHTTP14SHA256'] == '7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099' and
            result['reusedMetadataHTTP18SHA256'] == '8aaaf6fd04eb535bea79116ceaeac5a0dab6293d2d40bb1202616a6cef1c94ee' and
            result['historicalRemovalFailureSHA256'] == 'ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab',
            'existing removed-member state is retained without old route replay')
    policy = result['resourcePolicy']
    require(policy['rootFloorBytes'] == 2*1024**3 and policy['developmentFloorBytes'] == 512*1024**2 and
            policy['rootAdmissionReserveBytes'] == 128*1024**2 and
            policy['developmentAdmissionReserveBytes'] == 32*1024**2 and
            policy['maximumConcurrentNativeProcesses'] == 1 and
            policy['controllerDeadlineSeconds'] == 360 and policy['finalVerificationSeconds'] == 60 and
            policy['requiredOuterTimeoutSeconds'] == 480, 'unchanged actual HTTP4 resource/ownership limits')
    normal(result['processes'], 2)
    phases = result['phases']
    require(len(phases) == 2 and [p['name'] for p in phases] == ['owner-runtime', 'member-runtime'],
            'exact ordered owner then removed-reader phases')
    runtime_rows = [r for r in result['requests'] if r['kind'] in ('runtime-observation', 'runtime-denial')]
    require(len(runtime_rows) == 4 and
            all(r['method'] == 'GET' and r.get('range') is None for r in result['requests']),
            'only four new runtime decisions; all requests read-only')
    space_route = '/v1/spaces/'+SPACE+'/runtime-state'
    object_route = '/v1/spaces/'+SPACE+'/objects/'+OBJECT+'/runtime-state'
    expected_routes = [space_route, object_route, space_route, object_route]
    require([r['path'] for r in runtime_rows] == expected_routes and
            [r['status'] for r in runtime_rows] == [200, 200, 403, 403] and
            [r['phase'] for r in runtime_rows] == ['owner-runtime']*2+['member-runtime']*2,
            'two successful owner decisions followed by two removed-member denials')
    wire = {'__name__': 'frozen_runtime_wire_validation'}
    exec(compile(content[code+'runtime_wire_validation.py'], code+'runtime_wire_validation.py', 'exec'), wire)
    payloads = []
    for row, number in zip(runtime_rows, ('007', '008', '015', '016')):
        raw = content[doc+'responses/'+number+'.json']
        require(row['responsePath'] == HTTP_ROOT+'/responses/'+number+'.json' and
                row['response'] == identity(raw) and row['bodyReadInvocations'] == 1 and
                row['headers'] == {'Content-Length': str(len(raw)), 'Content-Range': '', 'Content-Type': 'application/json'},
                'exact original single body read and retained response bytes')
        payloads.append(json.loads(raw))
    scope0 = wire['owner_space'](payloads[0], OWNER, NETWORK, SPACE, OWNER)
    scope1 = wire['owner_object'](payloads[1], OWNER, NETWORK, SPACE, OWNER, OBJECT)
    require(scope0 == scope1, 'same exact current signed ACL head across both owner observations')
    for index, object_id in ((2, None), (3, OBJECT)):
        require(runtime_rows[index]['stage'] == 'confirmed-typed-denial' and
                runtime_rows[index]['errorCode'] == 'acl.forbidden', 'typed 403, never a successful or missing payload')
        wire['denial'](payloads[index], SPACE, object_id)
    require(all(row['stage'] == 'metadata-response' for row in runtime_rows[:2]),
            'both successful observations actually reached bounded body validation')
    expected_memberships = [
        [{'identity': OWNER, 'permission': 'owner', 'status': 'active', 'step': 'self-member'},
         {'identity': MEMBER, 'permission': 'none', 'status': 'removed', 'step': 'removed-member'},
         {'identity': MEMBER, 'permission': 'none', 'status': 'removed', 'step': 'removed-member-final'},
         {'identity': OWNER, 'permission': 'owner', 'status': 'active', 'step': 'self-member-final'}],
        [{'identity': MEMBER, 'permission': 'none', 'status': 'removed', 'step': 'self-member'},
         {'identity': MEMBER, 'permission': 'none', 'status': 'removed', 'step': 'self-member-final'}]]
    for i, (phase, process, account, actor) in enumerate(zip(phases, result['processes'],
                                                           (OWNER, MEMBER), ('owner', 'member'))):
        require(phase['status'] == 'PASS_PHASE' and phase['offline'] is False and
                phase['accountId'] == account and phase['actor'] == actor and
                phase['membership'] == expected_memberships[i] and phase['stopRequested'] is True and
                phase['gracefulStopIntent'] == {'leaderUnreaped': True, 'pid': process['pid'], 'signal': 15} and
                phase['logSHA256'] == process['logSHA256'] and process['expectedServiceShutdown'] is True,
                'current account/membership before and after read, then same unreaped owner normal stop')
        argv = process['argv']
        require(len(argv) == 8 and argv[:3] == [NATIVE, 'run', '--config'] and
                argv[3] == HTTP_ROOT+'/network.yml' and argv[4] == '--data-dir' and
                argv[5] == '/var/lib/pinkha-c-filesv2-20261126/attempt1/'+('alice' if i == 0 else 'bob') and
                argv[6] == '--addr' and argv[7].startswith('127.0.0.1:') and process['cwd'] == HTTP_ROOT,
                'same retained accounts and same current native product in separate owned processes')
    require(phases[0]['runtimeScope'] == scope0 and
            phases[0]['observations'] == [
                {'label': 'space', 'route': space_route, 'value': payloads[0]},
                {'label': 'object', 'route': object_route, 'value': payloads[1]}] and
            phases[0]['denials'] == [] and phases[1]['observations'] == [] and
            phases[1]['denials'] == ['space', 'object'], 'actual parsed observations and no denied payload')
    provenance = read('RECOVERY_PROVENANCE.json')
    require(provenance['protocol'] == 'pinkha-runtime-http4-publication-reconstruction-v1' and
            provenance['oldLocalPacketRecovered'] is False and
            provenance['newPublicationBase'] == BASE and
            provenance['exactRecoveredPublisherSHA256'] ==
                'bcb46ceca6ac77585b45c9c819559479fa0e9c726cf1abc426039bf33f61937b' and
            provenance['historicalParentHTTPStatus'] == 'NOT_RUN' and
            provenance['actualHTTPReceiptSHA256'] == PINS['D:runtime-http4-result.json']['sha256'] and
            provenance['newRuntimeOrCompilerInvocations'] == 0,
            'honest new packet reconstructed from durable originals, not recovered lost packet')
    return {'status': 'VALIDATED_EXISTING_RUNTIME_HTTP4_EVIDENCE_APPEND',
            'parentCommit': BASE, 'parentTree': TREE, 'parentHistoricalHTTPStatus': 'NOT_RUN',
            'runtime18ReceiptSHA256': producer_sha, 'historicalRuntime18Events': 18,
            'historicalC13Methods': {'sdk': 8, 'server': 5},
            'http4ReceiptSHA256': PINS['D:runtime-http4-result.json']['sha256'],
            'nativeProduct': binary, 'sourceFiles': 1638, 'sdkSourceFiles': 750,
            'actualOwner200': 2, 'actualRemovedMember403': 2, 'normalClosedNativeGroups': 2,
            'accountOrNativeProcessesStartedByValidator': 0, 'historicalPIDsProbed': False,
            'newRuntimeOrTestInvocations': 0, 'existingSourceFilesReplaced': 0,
            'newRuntimeRouteOfflineHTTPAcceptance': False, 'personalProvenanceAvailable': False,
            'nativeObjectExistenceClaim': False, 'heartSyncDateProduced': False,
            'cloudQuotaRecovered': False, 'consumerAdoptionQualified': False,
            'appleBoundRuntimeQualified': False}
