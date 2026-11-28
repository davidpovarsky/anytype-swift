#!/usr/bin/env python3
"""Pure validation of the exact public Type25 source/evidence packet.

This module reads only byte values supplied by its caller. It performs no I/O,
process operation, account access, compiler invocation, or test replay.
"""
import ast
import difflib
import hashlib
import json
import re

CODE = 'Tools/AnyEngineValidation/original_type_runtime_provider25_20261128/'
DOC = 'docs/validation/20261128-original-type-runtime-provider25/'
HOST = 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/'
ORIGINAL = '/mnt/development/projects/evidence/pinkha-original-type-runtime-provider25-20261127'
SOURCE_ROOT = '/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127'
BASE = 'e8331a3943db99cc8c73b9c61c6120b4ecf5ee7d'
BASE_TREE = 'c78246b891799d5583b204c1bef6337e5fc0b19a'
METHODS = {"NativeRuntimeRelationBindingTests":["testOriginalEightRuntimeDefinitionsPreserveExactIdentityAndWritability","testOriginalRuntimeDefinitionOverridesCannotSelectBuiltinProviders","testDecodeRevalidatesRuntimeRoleVersionAndOriginalEvidence"],"NativeRuntimeStateHTTPTests":["testBothScopedReadRoutesUseTheExistingClientAndRetainTheDeliveryLease","testAccountSwitchWithholdsEachAlreadyReceivedRuntimeResponse","testEngineRestartAndSessionRetirementWithholdBothReceivedResponseTypes","testForeignLeaseAndCurrentTaskCancellationRefuseBeforeAnyHTTPDispatch","testUnsupportedOversizedAndForeignNetworkAnswersFailWithoutRetry"],"NativeRuntimeStateTests":["testGuestScopeAndObservedZeroRemainDistinctFromMissingCoordinatorData","testAccessKeepsOriginalPersonalFirstClassificationAndRequiresItsProvenance","testExactAccountNetworkSpaceAndLeaseBytesCannotCrossCanonicalUnicodeAliases","testHistoricalObjectConfirmationDoesNotInventCurrentConnectivityOrObjectExistence","testMalformedDomainsAndContradictoryNativeProvenanceFailClosed","testClosedVersionedSchemasDoNotSilentlyEraseMalformedOrMissingData"],"NativeSharedSpacesLimitTests":["testActualRetainedNativeAnswerPreservesQuotaAndNanosecondTimestamp","testUnansweredPartAndObservedZeroRemainDistinct","testMalformedPresentPartCannotBecomeUnknownOrRoundedLimit","testTimestampKeepsNativePrecisionAndRejectsInvalidDatesAndOffsets","testDestinationAccountIdentityUsesExactBytesBeforeAnyRequest"],"NativeTypeReferenceTests":["testAllOriginalTypesKeepCompleteOrderedRecommendationEvidence","testExistingPropertyAndComputedReferencesKeepDifferentNativeContracts","testPartialForeignAndChangedCatalogsCannotSelectOriginalBindings","testClosedDescriptorRejectsOmittedComputedRefsAliasAndReorderedSource","testAbsentEmptyRepeatedAndUnresolvedRecommendationsRemainDistinct","testCapturedProviderOverrideAndExactUTF8NeverSelectAnAlias"]}
PINS = {
 'qualification/run_provider_components.py':'b9d7e0748231ba9f34362f68508f27958abd6922eb5ea5e68cb01d093ca8d5e7',
 'qualification/provider-component-inputs.json':'4cabf3c455886e224e9df83aa0cc00f05eb487665306e891a67a53e9ede6bc98',
 'qualification/previous-attempt1/run_provider_components.py':'6e2690f9693a00c5fbf6876274156e823426b0c4082cd7b23c00b23bf11cef91',
 'qualification/previous-attempt1/provider-component-inputs.json':'40d4d54cf15c1f239b4a181fa0aed627416fa74bc862dab87b99e126b9b8cec5',
 'qualification/previous-attempt2/run_provider_components.py':'65db477bdc8ac9d812bb5719c361e1815cf76672d8d9030e2b4b48305e517f4b',
 'qualification/previous-attempt2/provider-component-inputs.json':'47f4a1fc14b27c541d656ff707a22c6a45efb666566afa4bddaee3060b4c6d87',
 'Tests/before-two-try/NativeTypeReferenceTests.swift':'265ac60331fc53b65bf91392e03feb353e70a7423de416edc16ac437e28fe1f6',
 'qualification/compiled-source-313.json':'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa',
 'qualification/qualify_current_c3_crypto.py':'206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0',
}
ACTUAL = {
 'components-attempt1-result.json':'82998f003873e5c3ba44f230003af78a6015d5b9f34f7ab6ce858b3e9466c18c',
 'components-attempt2-result.json':'ef9cd141fc26457463abd4beecab8399e6d5e2bef7a589c2a3b59fad5152b52f',
 'components-attempt3-result.json':'f48358e0a4ac12cab0f354638c9f1fe15479378dcb0b3a7edd6dd4df2b6907e7',
 'components-attempt1-swift.log':'764276f2f20a858f9b8f1e9328d1a758d4359549df750efcb00bc1483f447a10',
 'components-attempt2-swift.log':'f91c2df2cab225e44e223bbb1d6e4e8d96d726091353eb7c0376dbc2f7502542',
 'components-attempt3-swift.log':'2ef962efc46ed33da091e181e02b664ba029b9f5cb475935ff7638d08fe16f29',
 'components-attempt3-compiled-source-inputs.json':'e5a934fbe384adcb06d636766548fdd4332d6d2f11ea9b69d90624162a7d56e3',
 'source-installation3-result.json':'71a82ef1d1f267a2efec6f73f9e65c6bcb71887f1dd000dcb1ba523a803af723',
 'parent-c13-publication-result.json':'2659913753f6f812282cadd709056b59ed2e81bbc2d0f293c388daee7f59149c',
}


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(raw):
    require(type(raw) is bytes, 'public member must be supplied as exact bytes')
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def definitions(source):
    return {node.name:ast.dump(node,include_attributes=False)
            for node in ast.parse(source).body
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.name!='main'}


def closed_groups(rows, exits):
    require(type(rows) is list and len(rows)==len(exits), 'exact historical group count')
    for row,exit_code in zip(rows,exits):
        require(row['exitCode']==exit_code and row['processGroupAbsent'] is True and
                row['unreapedLeaderDuringGroupCleanup'] is True and
                row['forcedCleanup'] is False and row['signals']==[] and row['cleanupErrors']==[],
                'actual retained group exit and positive owned closure')


def test_events(raw):
    text=raw.decode('utf-8')
    events={kind:re.findall(r"^Test Case '([^']+)' "+kind+r"\b",text,re.M)
            for kind in ('started','passed','failed','skipped')}
    return text,events


def validate(content, code, doc):
    require(code==CODE and doc==DOC, 'fixed public publication prefixes')
    require(type(content) is dict and all(type(k) is str for k in content), 'closed supplied byte packet')
    for relative,digest in PINS.items():
        require(identity(content[CODE+relative])['sha256']==digest, 'exact qualified or failed source')
    for name,digest in ACTUAL.items():
        require(identity(content[DOC+'actual/'+name])['sha256']==digest, 'exact original raw receipt or log')
    manifest=json.loads(content[CODE+'qualification/provider-component-inputs.json'])
    receipt=json.loads(content[DOC+'actual/components-attempt3-result.json'])
    ledger=json.loads(content[DOC+'actual/components-attempt3-compiled-source-inputs.json'])
    old_manifests=[json.loads(content[CODE+'qualification/previous-attempt%d/provider-component-inputs.json'%n]) for n in (1,2)]
    require(manifest['methods']==METHODS and all(m['methods']==METHODS for m in old_manifests),
            'same five classes and twenty-five named methods in all three source plans')
    selected=sorted(owner+'.'+method for owner,names in METHODS.items() for method in names)
    require(len(selected)==len(set(selected))==25, 'finite exact twenty-five-method inventory')
    require(manifest['expectedCounts']==ledger['counts'], 'actual compiled source-count ledger')
    counts=manifest['expectedCounts']
    require((counts['methods'],counts['typeMethods'],counts['runtimeBindingMethods'],counts['quotaMethods'],
             counts['runtimeWireMethods'],counts['runtimeHTTPMethods'])==(25,6,3,5,6,5),
            'six Type plus nineteen runtime/quota methods')
    require((counts['productionCompiledFiles'],counts['compiledTestFiles'],counts['originalProjectReadFiles'],
             counts['originalCoreCompiledFiles'])==(87,6,75,8), 'ninety-three complete source files')
    require(receipt['status']=='PASS' and receipt['errors']==[] and 'completionErrors' not in receipt,
            'actual successful attempt3 remains separately attributed')
    require(receipt['controllerSHA256']==PINS['qualification/run_provider_components.py'] and
            receipt['inputManifestSHA256']==PINS['qualification/provider-component-inputs.json'],
            'exact producer controller and source plan')
    for field in ('admittedInputsUnchanged','sourceUnchanged','compiledSourceInputsUnchanged',
                  'compiledProductsAndModesUnchanged','originalSourceFixtureInputsAndCopiesUnchanged',
                  'allStartedOwnedGroupsPositivelyAbsent'):
        require(receipt[field] is True,'actual final integrity '+field)
    require(receipt['nativeAccountsOpened'] is False and receipt['nativeStorageQualified'] is False and
            receipt['cloudDurabilityQualified'] is False and receipt['earlierTestReplayRequested'] is False and
            receipt['earlierTestReplayStatus']=='NOT_RUN' and
            receipt['priorMigrationOrFilesV2MethodsReplayed']==receipt['priorUpload35MethodsReplayed']==0,
            'component/loopback scope with no native or prior-method replay claim')
    closed_groups(receipt['commands'],[0]*7)
    require(len(receipt['compiledProducts'])==28 and
            set(receipt['compiledProducts'])==set(receipt['compiledProductModes']) and
            len(receipt['compiledProductDirectories'])==17 and len(receipt['compiledExecutables'])==2,
            'complete historical Products maps remain in actual receipt')
    require(receipt['compiledSourceInputs']['sha256']==ACTUAL['components-attempt3-compiled-source-inputs.json'] and
            receipt['compiledSourceInputs']['bytes']==len(content[DOC+'actual/components-attempt3-compiled-source-inputs.json']),
            'full actual compiled-source ledger hash and length')
    text,events=test_events(content[DOC+'actual/components-attempt3-swift.log'])
    require(sorted(events['started'])==sorted(events['passed'])==selected and
            len(events['started'])==len(events['passed'])==25 and not events['failed'] and not events['skipped'],
            'independent raw XCTest exact starts and passes, no skipped or failed case')
    require(len(re.findall(r'Executed 25 tests, with 0 failures \(0 unexpected\)',text))==1,
            'one complete aggregate XCTest result')
    require(receipt['actualMethods']['started']==receipt['actualMethods']['passed']==selected and
            receipt['actualMethods']['total']==25 and receipt['actualMethods']['skipped']==0,
            'actual named method receipt matches raw log')
    require({k:receipt['actualMethods'][k] for k in ('type','runtimeBinding','quota','runtimeWire','runtimeHTTP')}==
            {'type':6,'runtimeBinding':3,'quota':5,'runtimeWire':6,'runtimeHTTP':5},
            'separate component cohort totals')
    require(receipt['commands'][3]['logSHA256']==ACTUAL['components-attempt3-swift.log'] and
            receipt['commands'][3]['argv'][-2:]==['--filter','|'.join(sorted(METHODS))],
            'actual single selected compiler/test invocation')
    excluded={owner+'.'+name for owner,names in manifest['excludedEarlierMethods'].items() for name in names}
    require(len(excluded)==3 and not excluded.intersection(events['started']),
            'three canonical fixture methods compiled but not replayed')
    for n,old_manifest in enumerate(old_manifests,1):
        old=json.loads(content[DOC+'actual/components-attempt%d-result.json'%n])
        require(old['status']=='FAIL' and 'completionErrors' not in old and old['errors']==[
                {'message':'owned command did not finish normally: swift-components','type':'RuntimeError'},
                {'message':'','phase':'final-lifecycle-and-budget','type':'AssertionError'}],
                'earlier compile failure retains its exact main and final errors in the original errors array')
        closed_groups(old['commands'],[0,0,0,1])
        _,old_events=test_events(content[DOC+'actual/components-attempt%d-swift.log'%n])
        require(not any(old_events.values()), 'no historical XCTest event relabelled as success')
        require(old['commands'][3]['logSHA256']==ACTUAL['components-attempt%d-swift.log'%n] and
                old['controllerSHA256']==PINS['qualification/previous-attempt%d/run_provider_components.py'%n] and
                old['inputManifestSHA256']==PINS['qualification/previous-attempt%d/provider-component-inputs.json'%n],
                'original failed compiler source/log correlation')
    require(receipt['previousClosureFailure']['sha256']==ACTUAL['components-attempt1-result.json'] and
            receipt['previousTestSyntaxFailure']['sha256']==ACTUAL['components-attempt2-result.json'] and
            receipt['previousClosureFailure']['actualTestStarts']==receipt['previousTestSyntaxFailure']['actualTestStarts']==0 and
            receipt['previousClosureFailure']['oldGroupsReprobedOrReplayed'] is False and
            receipt['previousTestSyntaxFailure']['oldGroupsReprobedOrReplayed'] is False,
            'explicit two-failure chain and no historical PID or test replay')
    original_sets=[{row['path']:row for row in m['originalProjectFiles']} for m in old_manifests+[manifest]]
    require(len(original_sets[0])==72 and len(original_sets[1])==len(original_sets[2])==75 and
            original_sets[1]==original_sets[2] and
            all(original_sets[1][key]==row for key,row in original_sets[0].items()),
            'three whole original extension dependencies were additive')
    require(set(original_sets[1])-set(original_sets[0])==set(manifest['sourceClosureRepair']['addedOriginalWholeSources']),
            'exact closure repair identity, no test-body substitution')
    require(old_manifests[0]['preparedSources']==old_manifests[1]['preparedSources'],
            'first closure repair retained all ten prepared source files')
    before=content[CODE+'Tests/before-two-try/NativeTypeReferenceTests.swift']
    after=content[CODE+'Tests/NativeTypeReferenceTests.swift']
    before_lines=before.splitlines(keepends=True);after_lines=after.splitlines(keepends=True)
    require(len(before_lines)==len(after_lines) and len(after)-len(before)==8,
            'same complete test file with exactly eight added bytes')
    changed=[i for i,(left,right) in enumerate(zip(before_lines,after_lines)) if left!=right]
    require(changed==[24,174], 'exact two retained throwing-argument source lines')
    for index,assertion in zip(changed,(b'XCTAssertEqual',b'XCTAssertNotEqual')):
        left=before_lines[index];right=after_lines[index]
        indent=left[:len(left)-len(left.lstrip(b' '))]
        require(right==indent+b'try '+left[len(indent):] and
                before_lines[index-1].lstrip().startswith(assertion),
                'only try is inserted in the original comparison argument; assertions remain exact')
    new_sources={r['path']:r for r in manifest['preparedSources']}
    for row in old_manifests[1]['preparedSources']:
        now=new_sources[row['path']]
        if row['path']=='Tests/NativeTypeReferenceTests.swift':
            require(row['sha256']==identity(before)['sha256'] and now['sha256']==identity(after)['sha256'],
                    'precise before/after syntax correction identity')
        else:
            require(row==now,'all production and other tests unchanged')
    baseline_definitions=definitions(content[CODE+'qualification/previous-attempt1/run_provider_components.py'])
    for relative in ('qualification/previous-attempt2/run_provider_components.py','qualification/run_provider_components.py'):
        require(definitions(content[CODE+relative])==baseline_definitions,'unchanged qualifier non-main helpers')
    installed=json.loads(content[DOC+'actual/source-installation3-result.json'])
    require(installed['status']=='PASS_EXACT_PROVIDER25_SOURCE_INSTALLATION_ONLY' and
            installed['errors']==installed['completionErrors']==installed['commands']==[] and
            len(installed['installedSources'])==19,'exact source-only installation3')
    expected_files=set()
    production_names=[]
    for relative,row in installed['installedSources'].items():
        if relative.startswith('Sources/'):
            destination=HOST+relative.split('/')[-1];production_names.append(destination)
        elif relative.startswith('Tests/'):
            destination=CODE+relative
        else:
            destination=CODE+'qualification/'+relative
        require(identity(content[destination])==row,'all nineteen actual installed source bytes preserved')
        expected_files.add(destination)
    require(len(production_names)==5 and len(set(production_names))==5,'exact five additive Host production files')
    originals=ledger['originalInputs'];copies=ledger['isolatedCopies'];package=ORIGINAL+'/components-attempt3/package/'
    package_expected={package+'Package.swift'}
    require(len(originals)==2129 and len(copies)==511 and ledger['noExistingProjectModuleImportDirectories'] is True,
            'actual whole producer input and isolated-copy cardinalities')
    for row in manifest['originalProjectFiles']:
        wanted={k:row[k] for k in ('bytes','sha256')}
        require(originals[manifest['originalProjectRoot']+'/'+row['path']]==wanted,'original project source identity')
        destination=package+('Tests/' if row['kind']=='test-helper' else 'Sources/')+row['target']+'/'+row['path'].split('/')[-1]
        require(copies[destination]==wanted,'complete original project file compiled as an isolated copy')
        package_expected.add(destination)
    for row in manifest['originalCoreFiles']:
        wanted={k:row[k] for k in ('bytes','sha256')}
        require(originals[manifest['originalCoreRoot']+'/'+row['path']]==wanted,'original Core source identity')
        destination=package+row['path'];require(copies[destination]==wanted,'complete original Core isolated copy')
        package_expected.add(destination)
    for row in manifest['preparedSources']:
        wanted={k:row[k] for k in ('bytes','sha256')}
        require(originals[ORIGINAL+'/prepared3/'+row['path']]==wanted,'new source was an actual producer input')
        destination=package+('Tests/' if row['kind']=='test' else 'Sources/')+row['target']+'/'+row['path'].split('/')[-1]
        require(copies[destination]==wanted,'new complete source compiled as exact isolated copy')
        package_expected.add(destination)
    require(len(package_expected)==94 and {p for p in copies if p.startswith(package)}==package_expected,
            'complete package is Package.swift plus exactly ninety-three source files')
    fixture=receipt['httpFixtureQualification']
    require({k:fixture[k] for k in ('instances','requestCount','GETCount','POSTCount','authGETCount','runtimeGETCount')}==
            {'instances':14,'requestCount':38,'GETCount':38,'POSTCount':0,'authGETCount':24,'runtimeGETCount':14} and
            fixture['allCleanEOF'] is True and fixture['allOwnedOriginalGroup'] is True,
            'actual fourteen owned loopback fixtures and thirty-eight GETs')
    rows=fixture['fixtureRows']
    require(len(rows)==14 and len({r['directory'] for r in rows})==14 and len({r['fixturePID'] for r in rows})==14 and
            sum(r['requestCount'] for r in rows)==38 and sum(r['runtimeGETCount'] for r in rows)==14,
            'independent fixture aggregate from all actual receipt rows')
    for row in rows:
        require(row['ownedGroup']==receipt['commands'][3]['pgid'] and row['stdinEOFExit'] is True and
                row['artifacts']['server.py']==manifest['fixtureScript'],
                'historical fixture source and owned EOF closure; no PID probe')
    parent=json.loads(content[DOC+'actual/parent-c13-publication-result.json'])
    require(parent['status']=='PASS_NORMAL_PUBLICATION_OF_BOOKMARK_NATIVE_13_AND_BODYLESS_PROOF' and
            parent['commit']==BASE and parent['tree']==BASE_TREE and parent['errors']==parent['completionErrors']==[] and
            parent['publicInputsUnchanged'] is True and parent['publishedFilesUnchanged'] is True and
            parent['fullUndeclaredGitTreePreserved'] is True,'actual ordinary C13 parent publication')
    closed_groups(parent['commands'],[0]*len(parent['commands']))
    parent_rows=json.loads(content[DOC+'parent-source-correspondence.json'])
    require(parent_rows['status']=='EXACT_SOURCE_BYTES_PREPARED_FOR_PARENT_GIT_TREE_ADMISSION' and
            parent_rows['parentCommit']==BASE and parent_rows['parentTree']==BASE_TREE and
            parent_rows['sourceRoot']==SOURCE_ROOT==manifest['originalProjectRoot'] and
            parent_rows['actualGitTreeReadByPreparation'] is False,
            'source correspondence is not mislabeled as an executed Git check')
    require(set(parent_rows['files'])==set(original_sets[2]),'all seventy-five project dependencies in future parent gate')
    for path,row in parent_rows['files'].items():
        require({k:row[k] for k in ('bytes','sha256')}==
                {k:original_sets[2][path][k] for k in ('bytes','sha256')} and
                re.fullmatch('[0-9a-f]{40}',row['gitBlobSHA1']) is not None,
                'exact original source rows; publisher must join each actual Git blob before mutation')
    scope=json.loads(content[DOC+'recovery-scope.json'])
    require(scope['previousScratchPacketRecovered'] is False and scope['newPacketDerivedFromActualOracleInputs'] is True and
            scope['testReexecutionForPublication']==0 and scope['nativeRuntimeAcceptance']==False and
            scope['wholeMigrationComplete']==False and scope['originalEncrypted158HistoryDecrypted']==False,
            'honest new packet identity and bounded acceptance claims')
    expected_files.update(CODE+p for p in PINS if p not in ('qualification/run_provider_components.py',
        'qualification/provider-component-inputs.json','qualification/compiled-source-313.json','qualification/qualify_current_c3_crypto.py'))
    expected_files.update(DOC+'actual/'+name for name in ACTUAL)
    expected_files.update({DOC+'README.md',DOC+'PROVIDER_CONTRACT.md',DOC+'parent-source-correspondence.json',
                           DOC+'recovery-scope.json',CODE+'publication/validate_public_evidence.py'})
    require(set(content)==expected_files and len(content)==38,'closed thirty-eight-member public packet before plan and FILES')
    for name,raw in content.items():
        if name.endswith('.py'):ast.parse(raw,filename=name)
        elif name.endswith('.json'):json.loads(raw)
        if name.endswith(('.py','.swift','.md','.json')):
            require(not raw.endswith(b'\n\n') and not any(re.search(br'[ \t]+$',line) for line in raw.splitlines()),
                    'exact new text files satisfy the ordinary whitespace gate')
    return {'status':'PASS_PURE_PUBLIC_PACKET_VALIDATION_NOT_A_NEW_TEST_RUN','actualNewMethods':25,
            'methodGroups':{'type':6,'runtimeBinding':3,'quota':5,'runtimeWire':6,'runtimeHTTP':5},
            'compiledFullSources':93,'productionSources':87,'testSources':6,'newProductionFiles':5,
            'compiledCanonicalMethodsExcluded':3,'httpFixtures':14,'httpGETs':38,'httpPOSTs':0,
            'retainedFailedAttempts':[ACTUAL['components-attempt1-result.json'],ACTUAL['components-attempt2-result.json']],
            'historicalFailedTestStarts':0,'acceptedMethodsReplayed':0,'nativeAccountsOpened':0,
            'nativeStorageQualified':False,'cloudDurabilityQualified':False,
            'wholeMigrationComplete':False,'originalEncrypted158HistoryDecrypted':False,
            'publicPacketFilesBeforePlanAndDescriptor':38,'fullParentSourceAdmissionFiles':75,
            'preparedHostProductionPaths':sorted(production_names)}
