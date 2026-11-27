#!/usr/bin/env python3
"""Pure validation of exact public Bookmark source and retained actual evidence.

The caller supplies all bytes. This module performs no I/O, process operation,
account access or test execution. Historical process IDs are data only.
"""
import ast
from collections import Counter
import hashlib
import json
import re


FIXED = {
    'source/formatted-source.json': 'ebd4b3c7379a9d8851118d42ba25a43e08bc6939d7e1328cc8b83c67693dbe4c',
    'source/native1616-source.json': '773f0a25422b3460a375182fb6f839fd71d7246ad8b489b6c20418bfab3b2471',
    'source/composed1625-source.json': 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3',
    'source/compiled1626-inputs.json': '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0',
    'receipts/original-qualification-fail.json': '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b',
    'receipts/completion13-pass.json': 'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d',
    'receipts/bodyless-attempt1-fail.json': '6995033934f702d28af0611dab8535d6dc51d3069a32f43626182e73422ba9f3',
    'receipts/bodyless-attempt2-pass.json': '3dca1f0bc8f1d33e6392dcb3a7fab1470bb0e803e554778f8e8c23d743878877',
    'receipts/canonical-format.json': '74f095ea5ff1aa4216fc06fba5aa559afc306a3106f4d9570a09b2d42f580bf0',
    'receipts/canonical-format-worker.json': '54c8dfb8cf88b4b80a5c06958f1196eb1c99f3dbe39ac5a75e5550d98eac7db1',
    'receipts/original-os-denial-controls.json': 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab',
    'receipts/native1616-producer.json': '9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602',
    'logs/retained-go-environment.log': '865117f0fe0f842b406e0a216c4f9c249a7a2df9b66e478067066f5ef3485c1d',
    'logs/retained-sdk-eight.log': 'f6b1fdbd7308d2c3875a3465821b8ccb5dea339917d33fe314548d5d21cbdbc1',
    'logs/original-failed-server-compile.log': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'logs/current-native-compiler-environment.log': 'bdd51b9f17f07b97b2de1f0fa20a70e5e5a76d52b131ea84db7b4a98e9df6c9e',
    'logs/new-server-five.log': '725b562fae264ced5067c48aec943eba017a84676477db306c7d46223c55820f',
    'logs/native-build.log': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'logs/native-metadata.log': 'e0b3fc887d2fbfa4f81ff3f32d1a2d438aadefedd2357643fe0d1208cd1d99c1',
}
CONTROLLERS = {
    'qualification/owned_swift_commands.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    'qualification/linux_outbound_denial.py': '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1',
    'qualification/original/qualify_bookmark_native.py': 'a45b10800f1ea89530e38b1c6a5b7e34ee3e2ded5bc9d326ccc98762186ed712',
    'qualification/complete_bookmark_native.py': '193953b82d9f630006682187f9ece9169dfabd0a46d58f517e015c69139eb60c',
    'bodyless/original/run_bodyless_bookmark.py': 'c61089f42ab2f43438d89ca3798b74a3bdad3bd696eca31ffeb9d14f3566b411',
    'bodyless/before-policy-schema/run_bodyless_bookmark.py': '99b132dd1ab0436cdb3b6639831e161d7e07c5eb962c71a0021b63140a01ed4e',
    'bodyless/run_bodyless_bookmark.py': '590d1e38f67ca3f07499518199c7224a50d9aafdfad5c550c5433dba6af9b8f4',
    'bodyless/native_boundary_support.py': 'db3a44aded9c819115cc531ecf8f3682b7d8e43c25af8f64d9cbb51d13dfebfd',
    'bodyless/owned_native_commands.py': 'c2e2c23d497d334431462cd5ee530aaa3b9e9b2cf160201fe0443c27672c5145',
    'bodyless/owned_swift_commands_original.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    'bodyless/absolute_http_source_original.py': '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84',
}
NATIVE_SHA = 'b6fb8137bfce60e5af23e5c912ed133ca0e15fc10c368d2eabddc0641379b482'


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def source_archive_path(name):
    prefix = '.runtime-artifacts/sdk-source/'
    return 'overlay/sdk/'+name[len(prefix):] if name.startswith(prefix) else 'overlay/any/'+name


def clean_group(row, exit_code=0):
    require(row['exitCode'] == exit_code and row['processGroupAbsent'] is True and
            row['unreapedLeaderDuringGroupCleanup'] is True and
            row['forcedCleanup'] is False and row['cleanupErrors'] == [] and
            row['signals'] == [] and row['stopReason'] is None,
            'exact actual normal/explicit-crash group closure')


def go_events(raw, expected):
    runs, passes, packages = Counter(), Counter(), Counter()
    rows = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
    require(rows, 'nonempty actual Go JSON events')
    for row in rows:
        package, method, action = row.get('Package'), row.get('Test'), row.get('Action')
        require(package in {key[0] for key in expected}, 'declared actual test package only')
        require(action not in ('fail', 'skip', 'build-fail'), 'no failing or skipped actual event')
        if method is not None:
            require((package, method) in expected and '/' not in method, 'exact parent method; no undeclared child')
            if action == 'run':
                runs[package, method] += 1
            if action == 'pass':
                passes[package, method] += 1
        elif action == 'pass':
            packages[package] += 1
    require(runs == passes == Counter({key: 1 for key in expected}), 'exact named starts and passes once')
    require(packages == Counter({key[0]: 1 for key in expected}), 'each original package passed once')
    return [{'package': key[0], 'method': key[1]} for key in sorted(expected)]


def validate(content, code, doc):
    require(isinstance(content, dict) and all(isinstance(value, bytes) for value in content.values()), 'closed byte packet')
    for name, expected in FIXED.items():
        require(identity(content[doc+name])['sha256'] == expected, 'fixed original public evidence '+name)
    for name, expected in CONTROLLERS.items():
        raw = content[code+name]
        require(identity(raw)['sha256'] == expected, 'fixed executed/predecessor controller '+name)
        ast.parse(raw)
    parsed = {name: json.loads(content[doc+name]) for name in FIXED if name.endswith('.json')}
    manifest = parsed['source/formatted-source.json']
    base = parsed['source/native1616-source.json']
    base_files = base['files']
    source = parsed['source/composed1625-source.json']
    compiled = parsed['source/compiled1626-inputs.json']
    require(len(base_files) == 1616 and len(manifest['files']) == 17, 'full base and exact overlay')
    composed = dict(base_files)
    additions = replacements = production = tests = 0
    for name, row in manifest['files'].items():
        actual = identity(content[code+source_archive_path(name)])
        require(actual == {key: row[key] for key in actual}, 'exact compiled overlay bytes')
        before = row['beforeSHA256']
        if before is None:
            require(name not in composed, 'new source path must be absent from the actual base')
            additions += 1
        else:
            require(composed[name]['sha256'] == before, 'exact existing native source before-image')
            replacements += 1
        composed[name] = actual
        production += row['role'] == 'production'
        tests += row['role'] == 'test'
    require((additions, replacements, production, tests) == (9, 8, 13, 4), 'finite native implementation closure')
    require(composed == source['files'] and len(composed) == 1625 and
            source['baseSourceManifestSHA256'] == FIXED['source/native1616-source.json'],
            'independent full native source composition')
    config = manifest['runtimePublicConfig']
    require(config['testDestination'] == 'staging.yml' and config['outsideComposedSourceInventory'] is True,
            'separate original public test configuration')
    require(composed[config['sourceRelativePath']] == {key: config[key] for key in ('bytes', 'sha256')},
            'original runtime configuration bytes')
    composed['staging.yml'] = {key: config[key] for key in ('bytes', 'sha256')}
    require(compiled['files'] == composed and set(compiled['modes']) == set(composed) and
            len(composed) == 1626 and Counter(compiled['modes'].values()) == Counter({0o600: 1618, 0o700: 8}),
            'all physical compiler inputs and modes captured')
    selected = {'sdk': set(), 'server': set()}
    for path, methods in manifest['tests'].items():
        if path.startswith('.runtime-artifacts/sdk-source/'):
            package = 'github.com/anyproto/any-sync-sdk/'+path.removeprefix('.runtime-artifacts/sdk-source/').rsplit('/', 1)[0]
            group = 'sdk'
        else:
            package = 'github.com/anyproto/any/'+path.rsplit('/', 1)[0]
            group = 'server'
        for method in methods:
            require((package, method) not in selected[group], 'unique selected source method')
            require(re.search(rb'^func '+method.encode()+rb'\(t \*testing\.T\)', content[code+source_archive_path(path)], re.M),
                    'each selected method exists in the exact compiled test source')
            selected[group].add((package, method))
    require(tuple(map(len, (selected['sdk'], selected['server']))) == (8, 5), 'eight SDK and five server methods')
    sdk = go_events(content[doc+'logs/retained-sdk-eight.log'], selected['sdk'])
    server = go_events(content[doc+'logs/new-server-five.log'], selected['server'])
    first = parsed['receipts/original-qualification-fail.json']
    completion = parsed['receipts/completion13-pass.json']
    require(first['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and len(first['processes']) == 3,
            'original operational failure is retained unchanged')
    require(first['errors'] == [{'type': 'RuntimeError', 'message': 'RuntimeError: measured shared cache incremental cap'}] and
            first['completionErrors'] == [{'boundary': 'acceptanceAndResources',
                'message': 'measured shared cache incremental cap', 'type': 'RuntimeError'}], 'specific original cap failure')
    for row in first['processes'][:2]:
        clean_group(row)
    stopped = first['processes'][2]
    require(stopped['exitCode'] == -15 and stopped['forcedCleanup'] is True and stopped['signals'] == [15] and
            stopped['processGroupAbsent'] is True and stopped['cleanupErrors'] == [] and
            stopped['logSHA256'] == FIXED['logs/original-failed-server-compile.log'], 'interrupted compile remains failure')
    require(first['processes'][0]['logSHA256'] == FIXED['logs/retained-go-environment.log'] and
            first['processes'][1]['logSHA256'] == FIXED['logs/retained-sdk-eight.log'], 'retained normal command log binding')
    require(completion['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
            completion['errors'] == completion['completionErrors'] == [] and len(completion['processes']) == 4 and
            completion['retainedActualMethodCount'] == 8 and completion['newActualMethodCount'] == 5 and
            completion['priorTestMethodsReexecuted'] == 0, 'honest eight retained plus five new completion')
    for row, name in zip(completion['processes'], ['current-native-compiler-environment', 'new-server-five', 'native-build', 'native-metadata']):
        clean_group(row)
        require(row['logSHA256'] == FIXED['logs/'+name+'.log'], 'new actual command log binding')
    retained = completion['retainedQualification']
    require(retained['receiptSHA256'] == FIXED['receipts/original-qualification-fail.json'] and
            retained['qualifiedProcesses'] == first['processes'][:2] and retained['failedCompileProcess'] == stopped and
            retained['historicalProcessIDsNeverProbedOrSignaled'] is True and retained['originalFailureStatusUnchanged'] is True,
            'completion retains the entire original command attribution')
    require(completion['retainedCompilerEvidenceScope'] == {
        'historicalNativeCompilerExecutablesObserved': False, 'historicalPATHObserved': False,
        'originalGoDriverCompilerLinkerSourceAndRecordedEnvironmentOnly': True, 'retainedSDKMethodsReexecuted': 0},
        'historical compiler observations are not invented')
    current = completion['currentNativeCompilerObservation']
    require(current['historicalCompilerEqualityClaimed'] is False and
            current['appliesTo'] == ['five-new-server-methods', 'one-new-native-product'] and
            current['metadata'] == json.loads(content[doc+'logs/current-native-compiler-environment.log']) and
            set(current['tools']) == {'CC', 'CXX', 'AR'} and
            all(current['explicitEnvironment'][key] == row['path'] and row['mode'] == 0o755 for key, row in current['tools'].items()),
            'new native compiler evidence is separately bounded')
    product = completion['nativeBinary']
    require(product['sha256'] == NATIVE_SHA and product['bytes'] == 78262881 and product['mode'] == 0o700,
            'one exact newly built native product')
    require(completion['compiledSourceInputSHA256'] == FIXED['source/compiled1626-inputs.json'] and
            completion['sourceManifestSHA256'] == FIXED['source/composed1625-source.json'] and
            all(value is True for value in completion['finalIntegrity'].values()) and
            completion['allOwnedGroupsPositivelyAbsent'] is True and first['allOwnedGroupsPositivelyAbsent'] is True,
            'producer sources and command closures remain qualified')
    failed = parsed['receipts/bodyless-attempt1-fail.json']
    require(failed['status'] == 'FAIL_BODYLESS_BOOKMARK_PRESERVED' and failed['errors'] == [{'message': "'actual'", 'type': 'KeyError'}] and
            failed['completionErrors'] == [] and failed['commands'] == failed['requests'] == failed['mutations'] == [] and
            failed['accountInitializations'] == 0 and failed['allStartedOwnedGroupsPositivelyAbsent'] is False,
            'original no-child policy-schema failure remains explicit')
    actual = parsed['receipts/bodyless-attempt2-pass.json']
    require(actual['status'] == 'PASS_ONE_BODYLESS_BOOKMARK_ACTUAL_CRASH_AND_OFFLINE_REOPEN' and
            actual['errors'] == actual['completionErrors'] == [] and len(actual['commands']) == 3 and
            actual['allStartedOwnedGroupsPositivelyAbsent'] is True, 'actual new bodyless proof closure')
    producer = actual['qualifiedProducer']
    require(producer['sha256'] == FIXED['receipts/completion13-pass.json'] and producer['nativeBinary'] == product and
            producer['originalFailedReceiptSHA256'] == FIXED['receipts/original-qualification-fail.json'] and
            producer['compiledSourceInputSHA256'] == FIXED['source/compiled1626-inputs.json'] and
            producer['producerMethodComposition'] == {'newServer': 5, 'retainedSDK': 8} and
            producer['producerCommandComposition'] == {'newNormal': 4, 'originalFailedCompileRetained': 1, 'retainedNormal': 2} and
            producer['rerunMethods'] == 0 and producer['historicalCCompilerObservationClaimed'] is False,
            'bodyless consumer binds the exact actual thirteen-method producer chain')
    for row, code_value in zip(actual['commands'], [0, -9, 0]):
        clean_group(row, code_value)
        require(row['expectedExitCode'] == code_value, 'owned expected native termination')
    crash = actual['commands'][1]
    require(crash['callerStopSignal'] == crash['intentionalCrashSignal'] == 9 and
            crash['intentionalCrashGateValidated'] is True and actual['commands'][2]['callerStopSignal'] == 15,
            'actual warm crash is gated by validated mutation acceptance')
    require(actual['priorNoChildFailure']['receiptSHA256'] == FIXED['receipts/bodyless-attempt1-fail.json'] and
            actual['priorNoChildFailure']['historicalProcessIDsProbedOrSignaled'] is False, 'exact no-child predecessor preserved')
    phases = actual['phases']
    require(len(phases) == 2 and [p['cold'] for p in phases] == [False, True] and
            phases[0]['observation'] == phases[1]['observation'], 'exact warm/cold original body and metadata observation')
    for index, phase in enumerate(phases):
        require(phase['status'] == 'PASS_PHASE' and phase['currentOwnerAndZeroPeers'] is True and
                phase['osDenial']['noNewPrivileges'] is True and phase['osDenial']['seccompFilterMode'] == 2 and
                phase['actualPID'] == actual['commands'][index+1]['pid'], 'same owned observed native phase and OS fence')
    observation = phases[0]['observation']
    require(observation['editorRows'] == {'records': [], 'total': 0, 'hasNext': False} and
            observation['markdown']['content'] == '' and observation['markdown']['version'] and
            observation['sourceURL'] == {'bytes': 56, 'sha256': 'bd9bc3cf70057b67f6fc047326182d5eabef82b1ec6dd2e86dd766017fd93b46'},
            'true bodyless native object, exact content version and URL bytes')
    writes = actual['mutations']
    require([row['name'] for row in writes] == ['space', 'type', 'editor-part', 'property-owner', 'url-property', 'layout', 'bookmark'] and
            [row['status'] for row in writes] == [201, 201, 201, 201, 201, 204, 201] and len(writes) == 7,
            'six fresh setup mutations and one Bookmark create')
    for row in writes:
        request = actual['requests'][row['requestIndex']]
        require(row['state'] == 'validated-acknowledgement' and row['rawResponse']['completeBoundedBody'] is True and
                request['phase'] == 'native-warm-crash' and request['readOnlyOperation'] is False and
                request['method'] == row['method'] and request['path'] == row['path'] and request['status'] == row['status'] and
                request['rawResponse'] == row['rawResponse'] and request['requestBody'] == row['requestBody'],
                'every single dispatch has its own validated actual request/ACK identity')
    requests = actual['requests']
    write_indexes = {row['requestIndex'] for row in writes}
    require(len(requests) == 37 and write_indexes == {5, 7, 8, 9, 10, 11, 14}, 'exact complete actual HTTP ledger')
    space_prefix = '/v1/spaces/'+actual['scope']['spaceID']
    read_post_paths = {space_prefix+'/query', space_prefix+'/pinkha/bookmark-create-frame'}
    cold = []
    for index, request in enumerate(requests):
        require(request['phase'] in {'native-warm-crash', 'native-cold-offline'}, 'declared owned phase only')
        if index not in write_indexes:
            require(request['readOnlyOperation'] is True and
                    (request['method'] == 'GET' or request['method'] == 'POST' and request['path'] in read_post_paths),
                    'every other request is GET or an explicitly read-only native POST')
        if request['phase'] == 'native-cold-offline':
            cold.append(request)
            require(index not in write_indexes, 'cold reopen performs no native mutation')
    require(len(cold) == 13 and {r['path'] for r in cold if r['method'] == 'POST'} == read_post_paths,
            'complete cold query and descriptor-only POST scope')
    policy = parsed['receipts/original-os-denial-controls.json']['offlinePolicy']
    require(actual['offlinePolicy']['priorActualReceiptSHA256'] == FIXED['receipts/original-os-denial-controls.json'] and
            actual['offlinePolicy']['priorActualControls'] == policy and actual['offlinePolicy']['priorControlsReexecuted'] == 0 and
            policy['baselineTCPReachable'] is True and policy['baselineUDPReceived'] is True and
            all(policy['controls'][key] is True for key in ['tcpDenied', 'udpDenied', 'noNewPrivileges', 'seccompFilterActive']),
            'original OS positive/denied controls reused without a replay')
    for name in ('originalAccountInputs', 'originalAccountCopies', 'originalMigrationOperationsReplayed',
                 'controllerMutationRetries', 'priorTestMethodsReexecuted', 'compilerInvocations', 'nativeProductBuilds'):
        require(actual[name] == 0, 'no original-data, replay or second-build claim: '+name)
    for name in ('originalBuiltinTypeMigrationQualified', 'originalPlaintextHistoryReconstructed',
                 'sourceAdmissionPromoted', 'wholeMigrationComplete', 'C313SourceOrProductsAccessed', 'C3CacheAccessed'):
        require(actual[name] is False, 'narrow actual scope: '+name)
    require(actual['syntheticDefinitionOnly'] is True and actual['accountInitializations'] == 1 and
            actual['nativeBodylessCreates'] == 1 and actual['coldReadOnlyReopens'] == 1 and
            all(value is True for value in actual['finalIntegrity'].values()), 'one new fixture and exact final integrity')
    return {
        'status': 'PASS_PURE_PUBLIC_PACKET_VALIDATION_NOT_A_NEW_RUNTIME',
        'sourceComposition': {'base': 1616, 'replacements': 8, 'additions': 9, 'composed': 1625, 'compiledIncludingConfig': 1626},
        'retainedSDKMethods': sdk, 'newServerMethods': server, 'qualifiedMethodCount': 13, 'replayedMethods': 0,
        'producerCommands': {'retainedNormal': 2, 'originalFailedCompileRetained': 1, 'newNormal': 4},
        'nativeBinarySHA256': NATIVE_SHA, 'bodylessNativeGroups': 3, 'freshSetupMutations': 6, 'guardedBookmarkCreates': 1,
        'originalFailuresPreserved': [FIXED['receipts/original-qualification-fail.json'], FIXED['receipts/bodyless-attempt1-fail.json']],
        'wholeMigrationComplete': False, 'originalHistoryDecrypted': False,
        'privateAccountFilesPublished': 0, 'nativeExecutablePublished': False,
    }
