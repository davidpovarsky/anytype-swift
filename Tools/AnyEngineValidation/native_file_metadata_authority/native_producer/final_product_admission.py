#!/usr/bin/env python3
"""Read-only PUBLIC source/receipt admission for the final standalone Any.

No account paths, account APIs, process launch, writes, or test execution live
here. Callers supply a pinned public-file reader and a bounded source inventory.
The producer and HTTP consumer independently reconstruct the same exact union.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

MIB = 1024**2
ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
BASE = ROOT/'readguard-native1'
BASE_RECEIPT_SHA = 'e26587d911cec570f9215db8bc424f9faa7fe2d09c4354f71cdb772e6fafd394'
BASE_MANIFEST_SHA = 'aa43f853a28c2cd0e125b70cdcc01b05a4748f0c25541f5ed86cea511e6b8dd1'
BASE_BINARY_SHA = '1b25764f9af1af854a928b3c445044a6906cb3477b64b4da6689b9e29997e639'
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
CANDIDATE = Path('/mnt/development/projects/evidence/pinkha-final-files-authority-source-20261127-attempt1')
CANDIDATE_SHA = '71c0b47b5aea45a9ab0a2498f56361b0b7239fab183e37af7bb365dfb9b2ee81'
PATCH_SHA = '9088b91cd098124b68d794185898aaf29d829a0e1b44ad3e8e06c914f4bb0350'
QUALIFIER_SHA = '92fd3781063138f11055631db09ec39a3e519b65a0d44bcab4284cdceae1872c'
QUALIFIER_BYTES = 32627
COMPLETION = Path('/mnt/development/projects/evidence/pinkha-final-files-authority-completion-source-20261127-attempt2/complete_final_files_authority.py')
COMPLETION_SHA = '32fb36e93ee84da31ed7df9927b76f7a52ee971d0350c3b2341a1bf8654166bc'
COMPLETION_BYTES = 38566
PRIOR_RECEIPT_SHA = '173fdab404efc5340035151022946ae2324543cb7f10889fc47257efa79f24df'
PRIOR_UNIT_LOG_SHA = '5755748de4ee2bb1477dba8f1c8ad2218202258bc53d97ca997e124a653f9313'
PRIOR_METADATA_LOG_SHA = '865117f0fe0f842b406e0a216c4f9c249a7a2df9b66e478067066f5ef3485c1d'
PRIOR_SOURCE_SHA = 'c70cea6f04851ccbbb6b312a4e760bfd3659351927439ec9632b71f81dbe3b82'
METADATA_SHA = 'd2fa0dd59b0826918631c71b6d1b5b2561599897b438077bdf53cc3b34f38af8'
CACHE_EFFECT_SHA = 'eb0b1fa3c432a56d0767ae856043aa32b39bcde694133e432b25b34087f86a22'
INVERSE_SHA = '31fc741523900913eccce7df053cfb5e4c1f22e917371ba60d7abdc229ae75bc'
FORMAT_SHA = 'b54b2e7b5c7c79a797cc41a48fbfc4ae56b6f32a199b7a42a91c4195b7d81528'
READER_PATCH_SHA = '874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f'
ORIGINAL_FRESH_SHA = 'b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b'
CURRENT_FRESH_SHA = '31759517cd3f033e0c44f53b3938af0faf6db4f75efe53c5df7fd2d67fb88409'
MEASUREMENT_SHA = 'bcbfbe42b9fabf0d63fdb852343fffa6c2e2800b8e84ec5e9e1423a290c2fcbe'
MEASUREMENT_CONTENT_SHA = '9b586ad8ac9a1e0a79d2cab4ff1f9d2671ed3d0434d8e068eebcb09330171ca9'
QUALIFICATION_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
SIGNED_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127/attempt1/result.json')
SIGNED_SHA = '68964e6db8802065ba69edad5614ec52cde3603b14f9628d65d808aa76563766'
FRESH_RECEIPT = QUALIFICATION_PARENT/'attempt2/result.json'
FRESH_SHA = '4eb696473d3cc199f935f826944a03681e0decd16047039579aba9718fc2ff35'
CONTENT_RECEIPT = ROOT/'current-authority-http-20261127/attempt1/result.json'
CONTENT_SHA = '7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099'
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
SECCOMP_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNED_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
COMMITS = {'any':'8fbd1e819fb132ac0e0a848d2ddf5c5714189b81', 'sdk':'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9'}
SYNC_MODULE = 'github.com/anyproto/any-sync@v0.13.8'
UNIT_PACKAGE = 'github.com/anyproto/any-sync-sdk/internal/files/readguard'
SDK_PACKAGE = 'github.com/anyproto/any-sync-sdk'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def object_json(raw):
    def unique(items):
        value = {}
        for key, child in items:
            require(key not in value, 'duplicate public JSON key')
            value[key] = child
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'public JSON object required')
    return value


def relative(name):
    value = PurePosixPath(name)
    require(not value.is_absolute() and '..' not in value.parts and str(value)==name, 'canonical source member')
    return value


def closed(value, count):
    require(value['allOwnedGroupsPositivelyAbsent'] is True, 'positive owned-group closure')
    require(value['errors']==[] and value['completionErrors']==[], 'retained prerequisite failure')
    rows = value['processes']
    require(len(rows)==count and len({row['pid'] for row in rows})==count, 'exact prerequisite process inventory')
    require(all(row['exitCode']==0 and row['processGroupAbsent'] is True and not row['forcedCleanup'] and row['cleanupErrors']==[] for row in rows), 'normal prerequisite completion')


def valid_qualification_path(path, digest):
    require(path.name=='result.json' and path.parent.parent==QUALIFICATION_PARENT, 'fixed final34 receipt root')
    require(re.fullmatch(r'attempt[1-9][0-9]{0,2}',path.parent.name) and int(path.parent.name[7:])>=5, 'new final34 attempt')
    require(re.fullmatch(r'[0-9a-f]{64}',digest), 'exact final34 receipt digest')


def validate_actual34(value, candidate):
    require(value['protocol']=='pinkha-final-files-authority-completion-v1', 'actual final34 completion protocol')
    require(value['status']=='PASS_FINAL_FILES_AUTHORITY34_WITH_REUSED_UNIT32_AND_NEW_FRESH2', 'actual final34 completion not qualified')
    require(value['controller']=={'bytes':COMPLETION_BYTES,'sha256':COMPLETION_SHA}, 'actual reviewed completion source')
    closed(value,1)
    require(value['baseNativeReceiptSHA256']==BASE_RECEIPT_SHA and value['baseFullSourceManifestSHA256']==BASE_MANIFEST_SHA, 'actual final34 base')
    require(value['finalCandidateSHA256']==CANDIDATE_SHA and value['finalPatchSHA256']==PATCH_SHA, 'actual final34 candidate')
    require(value['sourceOnlyMetadata16Precursor']==METADATA_SHA and value['sourceOnlyCache17Precursor']==CACHE_EFFECT_SHA, 'separate unrun precursor identities')
    require(value['reusedActualReceipts']=={'signed35':SIGNED_SHA,'freshFilesOpen2':FRESH_SHA,'contentOnlyHTTP14':CONTENT_SHA,'baseProducer':BASE_RECEIPT_SHA}, 'explicit prior source-scoped evidence reuse')
    require(value['usedPublicInputsUnchanged'] and value['sourceUnchanged'] and value['qualifiedPublicSDKBaseUnchanged'], 'actual final34 source closure')
    require(value['sdkSourceFiles']==735 and value['actualFreshSDKOSDenialVerified'] is True, 'fresh final SDK/OS proof')
    require(value['OSPolicy']=={'helperSHA256':OFFLINE_SHA,'librarySHA256':SECCOMP_SHA,'installedBeforeSDKInitialization':True,'liveTCPAndUDPRequireEPERM':True}, 'unchanged actual OS policy')
    require(value['reusedOwnershipReceiptSHA256']==OWNED_PROOF_SHA, 'actual owned lifecycle proof reuse')
    for key in ('retainedPrivateInputs','retainedAccountOpens','privateRecordExports','nativeCLIServers','originalRoleMutations','replayedPriorTestMethods'):
        require(value[key]==0, 'fresh public-only final34 scope')
    require(value['separateMetadata16OrCache17OrPerformance1Executed'] is False, 'no redundant precursor execution')
    require(value['actualMethods']=={'unitParents':14,'unitSubcases':18,'freshSDKParents':2,'totalRuns':34,'totalPasses':34,'skips':0,'oldMethodsRerun':0}, 'all exact new final34 events')
    units = candidate['selectedUnitParents']
    subcases = candidate['selectedUnitSubcases']
    fresh = candidate['selectedFreshSDKParents']
    unit_names = units+[parent+'/'+child for parent,children in subcases.items() for child in children]
    require(len(units)==14 and len(unit_names)==32 and len(fresh)==2, 'fixed distinct event inventory')
    wanted = Counter({(UNIT_PACKAGE,name):1 for name in unit_names})+Counter({(SDK_PACKAGE,name):1 for name in fresh})
    require(sum(wanted.values())==34 and all(count==1 for count in wanted.values()), 'distinct exact events')
    for action in ('run','pass'):
        observed = Counter((row['Package'],row['Test']) for row in value['events'] if row['Action']==action and 'Test' in row)
        require(observed==wanted, 'retained actual event inventory differs')
    require(not any(row['Action'] in ('fail','skip') for row in value['events']), 'no final34 fail or skip')
    require(Counter(row['Package'] for row in value['events'] if row['Action']=='pass' and 'Test' not in row)==Counter({UNIT_PACKAGE:1,SDK_PACKAGE:1}), 'two actual package completions')
    scopes = value['actualScopes']
    require(scopes['metadataAuthority']=={'runs':16,'passes':16}, 'metadata16 obligation')
    require(scopes['cacheEffectAuthority']=={'runs':17,'passes':17,'freshRemovedMemberDenials':9,'positiveFullOffloadEviction':False,'positiveInlineOffload':True,'priorQueuedJobsCancelled':False}, 'cache17 bounded effect scope')
    measurement = scopes['cachedStreamMeasurement']
    require(measurement['runs']==measurement['passes']==1 and measurement['throughputAcceptanceThreshold'] is False and measurement['nativeSDKOrStorageThroughput'] is False, 'one observational paired measurement')
    measured = measurement['measurement']
    require(value['observedCachedMeasurements']==[measured], 'one retained measurement row')
    require(measured['protocol']=='pinkha-fresh-cached-stream-measurement-v1' and measured['retainedAccountInputs']==0, 'fresh measurement identity')
    require(measured['order']==['original-unwrapped-memory-reader','current-signed-lifetime-guard'], 'exact measurement paths/order')
    require(measured['nativeSDKOrStorageThroughput'] is False and measured['throughputAcceptanceThreshold'] is False, 'no invented throughput acceptance')
    require(len(measured['measurements'])==2, 'one paired observation')
    for index,row in enumerate(measured['measurements']):
        require(row['path']==measured['order'][index] and row['bytes']==64*MIB and row['sha256']==MEASUREMENT_CONTENT_SHA and row['reads']==1024, 'complete fixed-size byte observation')
        require(row['largestInnerRequest']==row['callerBufferBytes']==64*1024, 'bounded read requests')
        require(type(row['elapsedNanoseconds']) is int and 0<row['elapsedNanoseconds']<10*10**9, 'finite measured duration')
        require(type(row['processTotalAllocatedBytes']) is int and row['processTotalAllocatedBytes']>=0 and type(row['processAllocationCount']) is int and row['processAllocationCount']>=0, 'actual allocation counters')
        require(math.isclose(row['mibPerSecond'],64*10**9/row['elapsedNanoseconds'],rel_tol=1e-12), 'observed rate formula')
    original,current = measured['measurements']
    require(math.isclose(measured['elapsedRatioGuardToOriginal'],current['elapsedNanoseconds']/original['elapsedNanoseconds'],rel_tol=1e-12), 'observed duration ratio')
    require(measured['allocationDeltaGuardMinusOriginalBytes']==current['processTotalAllocatedBytes']-original['processTotalAllocatedBytes'], 'observed allocation difference')


def parse_actual_events(raw, package, names):
    events = []; chunks = []
    for line in raw.splitlines():
        row = object_json(line)
        require(row.get('Package')==package,'exact actual package log')
        if row.get('Action')=='output' and row.get('Test')=='TestReadGuardFreshCachedStreamMeasurement64MiB':
            require(package==UNIT_PACKAGE and isinstance(row['Output'],str),'same measurement stream')
            chunks.append(row['Output'])
        if row.get('Action') in ('run','pass','fail','skip'):
            events.append({key:row[key] for key in ('Action','Package','Test','Elapsed') if key in row})
    wanted=Counter({(package,name):1 for name in names})
    for action in ('run','pass'):
        require(Counter((row['Package'],row['Test']) for row in events if row['Action']==action and 'Test' in row)==wanted,'exact actual methods')
    require(not any(row['Action'] in ('fail','skip') for row in events),'actual log no fail/skip')
    require(Counter(row['Package'] for row in events if row['Action']=='pass' and 'Test' not in row)==Counter({package:1}),'actual one package PASS')
    return events,chunks


def validate_completion_chain(pin,inventory,path,value,candidate,sdk,check):
    require(identity(pin(COMPLETION,COMPLETION_SHA))=={'bytes':COMPLETION_BYTES,'sha256':COMPLETION_SHA},'exact public completion controller')
    prior_root=QUALIFICATION_PARENT/'attempt4'
    prior=object_json(pin(prior_root/'result.json',PRIOR_RECEIPT_SHA))
    require(prior['protocol']=='pinkha-final-files-authority-synthetic-v1' and prior['status']=='FAIL_FINAL_FILES_AUTHORITY34','original overall failure retained')
    require(prior['controller']=={'bytes':QUALIFIER_BYTES,'sha256':QUALIFIER_SHA},'original reviewed source')
    require(prior['errors']==[{'type':'JSONDecodeError','message':'Expecting value: line 1 column 941 (char 940)'}] and prior['completionErrors']==[],'exact original parser-only error')
    require(prior['allOwnedGroupsPositivelyAbsent'] is True and len(prior['processes'])==2,'two historical normal groups')
    require(len({row['pid'] for row in prior['processes']})==2,'historical identity inventory')
    require(all(row['exitCode']==0 and row['processGroupAbsent'] is True and not row['forcedCleanup'] and row['cleanupErrors']==[] and row['signals']==[] for row in prior['processes']),'original normal closure')
    require(prior['sourceUnchanged'] and prior['qualifiedPublicSDKBaseUnchanged'] and prior['usedPublicInputsUnchanged'],'original source gates')
    require(prior['sourceManifestSHA256']==PRIOR_SOURCE_SHA and prior['sdkSourceFiles']==735 and prior['events']==[],'original exact source and failed parser state')
    require(prior['finalCandidateSHA256']==CANDIDATE_SHA and prior['finalPatchSHA256']==PATCH_SHA,'same final source candidate')
    require(prior['goToolchain']==value['goToolchain'] and prior['OSPolicy']==value['OSPolicy'] and prior['OSExecPython']==value['OSExecPython'],'unchanged real toolchain/OS closure')
    require(prior['reusedActualReceipts']==value['reusedActualReceipts'],'same accepted prior evidence')
    prior_source=object_json(pin(prior_root/'source-before.json',PRIOR_SOURCE_SHA))
    require(prior_source==sdk and inventory(prior_root/'sdk-source',check)==sdk,'exact source of32 actual units remains unchanged')
    require(value['originalAttempt4PublicSourceUnchanged'] is True and value['sourceManifestSHA256']==PRIOR_SOURCE_SHA,'current equality with original actual source735')
    require(value['continuationOf']=={'receipt':str(prior_root/'result.json'),'sha256':PRIOR_RECEIPT_SHA,'status':prior['status'],
        'unitLog':str(prior_root/'final-units/original.log'),'unitLogSHA256':PRIOR_UNIT_LOG_SHA,'originalControllerSHA256':QUALIFIER_SHA},'explicit immutable failure chain')
    require(value['reusedProcesses']==prior['processes'] and value['reusedAllOwnedGroupsPositivelyAbsent'] is True,'historical groups stay separate')
    require(value['historicalProcessIDsProbed'] is False and value['priorUnitMethodsReexecuted']==0 and value['priorMeasurementReexecuted'] is False,'no historical probes or replay')
    require(value['eventsRepresentAggregateOnly'] is True,'aggregate events are explicitly labeled')
    require(value['executionAccounting']=={'aggregateRequiredRuns':34,'aggregateRequiredPasses':34,'reusedUnitRuns':32,'reusedUnitPasses':32,
        'newFreshRunsRequired':2,'newFreshPassesRequired':2,'historicalClosedGroups':2,'newOwnedGroupsRequired':1,'unitOrMeasurementReruns':0},'explicit32+2 execution attribution')
    require(value['newActualMethods']=={'freshSDKParents':2,'totalRuns':2,'totalPasses':2,'skips':0},'only2 new method executions')
    unit_names=candidate['selectedUnitParents']+[a+'/'+b for a,children in candidate['selectedUnitSubcases'].items() for b in children]
    unit_raw=pin(prior_root/'final-units/original.log',PRIOR_UNIT_LOG_SHA,8*MIB)
    events,chunks=parse_actual_events(unit_raw,UNIT_PACKAGE,unit_names)
    require([len(c.encode()) for c in chunks]==[57,1024,69,65],'exact retained split log')
    joined=''.join(chunks);marker='READGUARD_CACHED_MEASUREMENT '
    require(len(joined.encode())<=65536 and joined.endswith('\n') and joined.count(marker)==1,'one complete same-test measurement')
    lines=[line for line in joined.splitlines() if marker in line]
    require(len(lines)==1,'one measurement line')
    measurement=object_json(lines[0].split(marker,1)[1])
    require(value['observedCachedMeasurements']==[measurement] and value['reusedEvents']==events,'actual reconstructed32 events and observation')
    require(value['reusedUnitLog']=={'path':str(prior_root/'final-units/original.log'),**identity(unit_raw),
        'measurementOutputChunkBytes':[57,1024,69,65],'samePackageAndTestReassembled':True},'exact original log attribution')
    metadata_raw=pin(prior_root/'toolchain/original.log',PRIOR_METADATA_LOG_SHA,65536)
    require(object_json(metadata_raw)==value['goToolchain']['metadata'],'original actual Go metadata')
    require(value['reusedToolchainMetadata']=={'path':str(prior_root/'toolchain/original.log'),**identity(metadata_raw)},'metadata reuse separate from new commands')
    require([row['logSHA256'] for row in prior['processes']]==[PRIOR_METADATA_LOG_SHA,PRIOR_UNIT_LOG_SHA],'original receipt/log joins')
    new_raw=pin(path.parent/'final-fresh/original.log',value['processes'][0]['logSHA256'],8*MIB)
    new_events,new_chunks=parse_actual_events(new_raw,SDK_PACKAGE,candidate['selectedFreshSDKParents'])
    require(new_chunks==[] and value['newEvents']==new_events and value['events']==events+new_events,'independent actual new2/aggregate34 log joins')
    require(value['rawLogs']=={'final-fresh':{'path':str(path.parent/'final-fresh/original.log'),**identity(new_raw)}},'only new fresh log')


def qualified_union(pin, inventory, qualification_path, qualification_sha, check):
    """Return the exact new source map and actual public proof, never account data."""
    valid_qualification_path(qualification_path, qualification_sha)
    check()
    base = object_json(pin(BASE/'result.json',BASE_RECEIPT_SHA))
    require(base['protocol']=='pinkha-files-readguard-native-qualified-v1' and base['status']=='PASS_NATIVE_BUILD_AND_FRESH_FILES_OPEN2', 'actual base producer')
    closed(base,3)
    require(base['sourceManifestSHA256']==BASE_MANIFEST_SHA and base['sourceFiles']==1607 and base['sourceUnchanged'], 'qualified base1607')
    require(base['binarySHA256']==BASE_BINARY_SHA and base['commits']==COMMITS and base['syncModule']==SYNC_MODULE, 'qualified base product identity')
    require(base['sdkReadguardPatchSHA256']==READER_PATCH_SHA, 'unchanged reader protection lineage')
    base_full = object_json(pin(BASE/'source-manifest.json',BASE_MANIFEST_SHA))['files']
    base_sdk = {name.removeprefix(SDK_PREFIX):row for name,row in base_full.items() if name.startswith(SDK_PREFIX)}
    require(len(base_full)==1607 and len(base_sdk)==726 and base_sdk['files_readguard_fresh_linux_test.go']['sha256']==ORIGINAL_FRESH_SHA, 'base source closure')
    require(inventory(BASE/'source',check)==base_full, 'exact retained public base source')
    signed = object_json(pin(SIGNED_RECEIPT,SIGNED_SHA,8*MIB))
    require(signed['status']=='PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE', 'actual signed35 reuse')
    closed(signed,2)
    require(signed['actualMethods']['totalRuns']==signed['actualMethods']['totalPasses']==35 and signed['actualMethods']['skips']==0, 'all prior signed35 events')
    fresh = object_json(pin(FRESH_RECEIPT,FRESH_SHA))
    require(fresh['status']=='PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2', 'actual prior Files.Open2 reuse')
    closed(fresh,2)
    require(fresh['actualMethods']['totalRuns']==fresh['actualMethods']['totalPasses']==2 and fresh['actualMethods']['skips']==0 and fresh['fixtureSource']==base_sdk['files_readguard_fresh_linux_test.go'], 'prior fresh source/event binding')
    require(fresh['goToolchain']==base['goToolchain'], 'same qualified base/fresh toolchain')
    content = object_json(pin(CONTENT_RECEIPT,CONTENT_SHA,8*MIB))
    require(content['status']=='PASS_ORIGINAL_CURRENT_AUTHORITY_HTTP14_ONLY' and content['contentDenialCount']==14, 'content-only accepted baseline retained')
    closed(content,3)
    candidate = object_json(pin(CANDIDATE/'manifest.json',CANDIDATE_SHA))
    require(candidate['protocol']=='pinkha-final-files-authority-source-v1' and candidate['baseFullSourceManifestSHA256']==BASE_MANIFEST_SHA and candidate['baseNativeReceiptSHA256']==BASE_RECEIPT_SHA and candidate['baseNativeSHA256']==BASE_BINARY_SHA, 'final candidate base')
    require(candidate['unchangedReadGuardPatchSHA256']==READER_PATCH_SHA and candidate['previousFreshFixtureSHA256']==ORIGINAL_FRESH_SHA and candidate['newFreshFixtureSHA256']==CURRENT_FRESH_SHA, 'original reader and fixture lineage')
    require(candidate['patch']==identity(pin(CANDIDATE/'sdk-final-files-authority.patch',PATCH_SHA)), 'exact final patch')
    require(identity(pin(CANDIDATE/'qualify_final_files_authority.py',QUALIFIER_SHA))=={'bytes':QUALIFIER_BYTES,'sha256':QUALIFIER_SHA}, 'reviewed actual qualifier source')
    pin(CANDIDATE/'owned_swift_commands.py',OWNED_SHA)
    require(candidate['candidateSDKFileCount']==735 and candidate['candidateSourceFileCount']==1616 and len(candidate['changes'])==13 and candidate['plannedRunPassEvents']==34, 'exact final candidate counts')
    metadata = object_json(pin(CANDIDATE/'metadata16-manifest.json',METADATA_SHA))
    effects = object_json(pin(CANDIDATE/'cache17-manifest.json',CACHE_EFFECT_SHA))
    inverse = object_json(pin(CANDIDATE/'FRESH_STARTUP_SOURCE_SUCCESSOR.json',INVERSE_SHA))
    formatting = object_json(pin(CANDIDATE/'canonical-formatting.json',FORMAT_SHA))
    require(candidate['defaultFreshFixtureInverseProofSHA256']==INVERSE_SHA and candidate['canonicalFormattingSHA256']==FORMAT_SHA, 'source-only provenance hashes')
    require(inverse['exactInverseRestoresPrevious'] is True and inverse['previousSHA256']==ORIGINAL_FRESH_SHA and inverse['currentSHA256']==CURRENT_FRESH_SHA and inverse['defaultSetupHooks']==[None,None], 'unchanged default fresh fixture')
    require(formatting['status']=='SOURCE_FORMATTED_ONLY_NOT_COMPILED_OR_TESTED', 'formatting-only provenance')
    require(len(metadata['changes'])==8 and len(effects['changes'])==6, 'two scoped source layers')
    composed = {name:{key:row[key] for key in ('bytes','sha256')} for name,row in metadata['changes'].items()}
    for name,row in effects['changes'].items():
        prior = composed.get(name,base_sdk.get(name))
        require((None if prior is None else prior['sha256'])==row['beforeSHA256'], 'metadata to cache-effect before-image')
        composed[name] = {key:row[key] for key in ('bytes','sha256')}
    measurement_name = 'internal/files/readguard/readguard_cached_stream_measurement_test.go'
    require(measurement_name not in composed and measurement_name not in base_sdk, 'one new measurement source')
    composed[measurement_name] = {'bytes':7667,'sha256':MEASUREMENT_SHA}
    require(composed=={name:{key:row[key] for key in ('bytes','sha256')} for name,row in candidate['changes'].items()}, 'independent exact source-layer composition')
    union = dict(base_full)
    for name,row in sorted(candidate['changes'].items()):
        check(); relative(name)
        previous = base_sdk.get(name)
        require((None if previous is None else previous['sha256'])==row['beforeSHA256'], 'final source before-image')
        raw = pin(CANDIDATE/'overlay'/name,row['sha256'])
        require(identity(raw)==composed[name], 'final source after-image')
        union[SDK_PREFIX+name] = identity(raw)
    sdk = {name.removeprefix(SDK_PREFIX):row for name,row in union.items() if name.startswith(SDK_PREFIX)}
    require(len(union)==1616 and len(sdk)==735, 'exact final full and SDK closure')
    changed = {name for name in set(base_full)|set(union) if base_full.get(name)!=union.get(name)}
    require(changed=={SDK_PREFIX+name for name in candidate['changes']}, 'only thirteen declared source paths')
    qualified = object_json(pin(qualification_path,qualification_sha,8*MIB))
    validate_actual34(qualified,candidate)
    validate_completion_chain(pin,inventory,qualification_path,qualified,candidate,sdk,check)
    require(qualified['goToolchain']==base['goToolchain'], 'same actual final/base compiler closure')
    source_map = object_json(pin(qualification_path.parent/'source-before.json',qualified['sourceManifestSHA256']))
    require(source_map==sdk, 'actual tested SDK equals reconstructed candidate')
    require(inventory(qualification_path.parent/'sdk-source',check)==sdk, 'actual qualified public SDK bytes')
    return {'baseProducer':base,'candidate':candidate,'qualification':qualified,
            'qualificationReference':{'path':str(qualification_path),'sha256':qualification_sha},
            'baseFiles':base_full,'sdkFiles':sdk,'files':union,'changedPaths':sorted(changed),
            'qualifiedSDKSource':qualification_path.parent/'sdk-source'}


def admit_product(pin, inventory, receipt_path, receipt_sha, check, expected_controller_sha, expected_admission_sha):
    """Require one real final native build and its complete independently joined source."""
    require(receipt_path.name=='result.json' and receipt_path.parent.parent==ROOT, 'fixed final native producer parent')
    require(re.fullmatch(r'final-authority-native[1-9][0-9]{0,2}',receipt_path.parent.name), 'new exclusive final native output')
    require(re.fullmatch(r'[0-9a-f]{64}',receipt_sha), 'exact final product receipt')
    producer = object_json(pin(receipt_path,receipt_sha,8*MIB))
    require(producer['protocol']=='pinkha-final-files-authority-native-qualified-v1' and producer['status']=='PASS_FINAL_NATIVE_BUILD_AND_FILES_AUTHORITY34', 'final native product not qualified')
    closed(producer,3)
    require(producer['controller']['sha256']==expected_controller_sha and producer['admissionModule']['sha256']==expected_admission_sha, 'reviewed producer/admission bytes')
    require(producer['baseNativeReceiptSHA256']==BASE_RECEIPT_SHA and producer['baseSourceManifestSHA256']==BASE_MANIFEST_SHA and producer['finalCandidateSHA256']==CANDIDATE_SHA and producer['finalPatchSHA256']==PATCH_SHA, 'exact final producer composition')
    require(producer['commits']==COMMITS and producer['syncModule']==SYNC_MODULE and producer['buildExitCode']==0, 'standalone Any/SDK actual build')
    require(producer['productionOverlayApplications']==1 and producer['sourceFiles']==1616 and producer['sdkSourceFiles']==735, 'one complete final source application')
    for key in ('nativeAccountProcesses','retainedPrivateInputs','replayedTests'):
        require(producer[key]==0, 'source/build-only producer')
    require(producer['nativeCLIStarted'] is False and producer['appleRuntimeQualified'] is False and producer['heartProductEmbedded'] is False, 'producer scope remains standalone Linux')
    require(producer['sourceUnchanged'] and producer['baseSourceUnchanged'] and producer['qualifiedSDKSourceUnchanged'] and producer['admittedPublicInputsUnchanged'], 'producer final source checks')
    reference = producer['qualification']
    joined = qualified_union(pin,inventory,Path(reference['path']),reference['sha256'],check)
    require(producer['goToolchain']==joined['baseProducer']['goToolchain'] and producer['sourceChanges']==joined['changedPaths'], 'same tested toolchain and declared delta')
    manifest = object_json(pin(receipt_path.parent/'source-manifest.json',producer['sourceManifestSHA256']))
    require(manifest['protocol']=='pinkha-final-files-authority-native-source-v1' and manifest['baseSourceManifestSHA256']==BASE_MANIFEST_SHA and manifest['finalCandidateSHA256']==CANDIDATE_SHA and manifest['finalPatchSHA256']==PATCH_SHA, 'final source manifest provenance')
    require(manifest['files']==joined['files'], 'producer source map equals independent complete union')
    require(inventory(receipt_path.parent/'source',check)==joined['files'], 'complete physical final producer source')
    binary = receipt_path.parent/'any'
    raw = pin(binary,producer['binarySHA256'],128*MIB)
    require(len(raw)==producer['binaryBytes'] and raw.startswith(b'\x7fELF'), 'exact final native ELF bytes')
    return {**joined,'producer':producer,'binary':binary,'binaryIdentity':identity(raw),'source':receipt_path.parent/'source'}
