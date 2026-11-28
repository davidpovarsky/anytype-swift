"""Pure validation of exact runtime15 source, actual18 and unrun HTTP4 packet.

No filesystem, process, network, account, compiler or historical PID access.
Current live product admission remains the separately reviewed f175 helper.
"""
import ast
import base64
from collections import Counter
import hashlib
import json

MIB = 1024**2
PINS = {
    'SOURCE_DRAFT2.json': 'f042531d9fb204aa7d92e9c73e375e839753b46b796330c7c2cce8d79a58daa4',
    'WIRE_CONTRACT.json': '3d13cb658cb45cf6b690c0d052aa6ebdae06174ec72c7e1826ff0f04019f896d',
    'runtime-state.draft2.patch': '3d6a7d1175429f2dedf4993fbaf47c91ff8cfbaf9202e2c6ef1de15efcf7c478',
    'qualification/qualify_runtime_state.py': '5b74a95e00a9a45bab0310e64b7765ebbb70b133e1482093b23cbbe9355b8656',
    'qualification/QUALIFICATION_PLAN.json': '2b8749bea0f82f4fcacabe73715ba8caf8b4c7851ccd8a6f884cfdf6d7400439',
    'qualification/COMPOSED1638.json': '12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9',
    'qualification/owned_swift_commands.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    'http/verify_runtime_state_http.py': 'a7f0fbe8067946d35865be61d3c35a1b82fe3e1b85df6f06040c758273c4a18d',
    'http/runtime_product_admission.py': 'f1755272ea4afd1a50d95ba9f085c9f61f25080b389b35359c6cc74337fcb496',
    'http/runtime_wire_validation.py': 'dde0784eeda0182bf0d0a8ff71aad5f5219fe0856223cc93e6f736e0e2d5a876',
    'http/owned_swift_commands.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    'http/HTTP_SOURCE_PLAN.json': '56241ba250b1f7d276dd2cda131ecdbc0f71e0d13d93632b72eb23da60008720',
}
RECEIPTS = {
    'format15.json': '070c6e482c923a7428ff7b6580a0acefa7ec0097844df515cc2b0a1f5d79e109',
    'runtime-source-install.json': '0439446b4d54234b78f733a003155d66393e5566abdfd2b793040cdbc567f0e0',
    'runtime18.json': 'f832753c0d365e984ed7f53ad6f4e3b20b125562b1871e0d7c5d5c54794fdfe2',
    'http4-source-install-only.json': '48f0d54609a57d2591a34b333a188d0bfff7ca39750912af50ac84518efd66cc',
    'c13-original-fail.json': '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b',
    'c13-completion.json': 'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d',
}
MAPS = {
    'runtime-compiled-source-inputs.json': '3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4',
    'runtime-source-manifest.json': '12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9',
    'c13-compiled-source-inputs.json': '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0',
    'c13-source-manifest.json': 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3',
}


def require(value, message):
    if not value:
        raise AssertionError(message)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def object_json(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate public JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'public object envelope')
    return value


def normal(row):
    return row.get('exitCode') == 0 and row.get('processGroupAbsent') is True and \
        row.get('forcedCleanup') is False and row.get('cleanupErrors') == [] and \
        row.get('signals') == [] and row.get('unreapedLeaderDuringGroupCleanup') is True


def actual_events(raw, packages, subcases):
    expected = Counter((package, method) for package, methods in packages.items() for method in methods)
    for package, methods in packages.items():
        for method in methods:
            expected.update((package, method+'/'+child) for child in subcases.get(method, ()))
    runs, passes, package_passes = Counter(), Counter(), Counter()
    for line in raw.splitlines():
        require(len(line) <= 2*MIB, 'bounded original Go event line')
        if not line:
            continue
        event = object_json(line)
        package, method, action = event.get('Package'), event.get('Test'), event.get('Action')
        require(package in packages and action not in ('skip', 'fail'), 'only successful selected original events')
        if method is not None:
            key = (package, method)
            require(key in expected, 'no old or undeclared method/subcase')
            if action == 'run':
                runs[key] += 1
            elif action == 'pass':
                passes[key] += 1
        elif action == 'pass':
            package_passes[package] += 1
    require(runs == passes == expected and package_passes == Counter({p: 1 for p in packages}),
            'one exact actual run/pass per declared method and package')
    return {'runs': sum(runs.values()), 'passes': sum(passes.values()), 'skips': 0, 'failures': 0,
            'methods': [{'package': p, 'name': n} for p, n in sorted(expected)], 'packages': sorted(packages)}


def function_nodes(raw):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(raw).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def literal(raw, name):
    values = [node.value for node in ast.parse(raw).body if isinstance(node, ast.Assign) and
              any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    require(len(values) == 1, 'one frozen top-level source declaration: '+name)
    return ast.literal_eval(values[0])


def validate(content, code, doc):
    require(code == 'Tools/AnyEngineValidation/native_runtime_state_20261127/' and
            doc == 'docs/validation/20261127-native-runtime-state/', 'only the two owned runtime source prefixes')
    require(all(isinstance(raw, bytes) and (name.startswith(code) or name.startswith(doc))
                for name, raw in content.items()), 'public finite byte packet')

    def pin(name, sha):
        raw = content[name]
        require(identity(raw)['sha256'] == sha, 'exact public byte identity: '+name)
        return raw

    for name, sha in PINS.items():
        pin(code+name, sha)
    receipts = {name: object_json(pin(doc+'receipts/'+name, sha)) for name, sha in RECEIPTS.items()}
    maps = {name: object_json(pin(doc+'maps/'+name, sha)) for name, sha in MAPS.items()}
    controller = content[code+'qualification/qualify_runtime_state.py']
    helper = content[code+'http/runtime_product_admission.py']
    public_helpers = function_nodes(content[code+'publication/validate_public_evidence.py'])
    live_helpers = function_nodes(helper)
    require(all(public_helpers[name] == live_helpers[name]
                for name in ('require', 'identity', 'object_json', 'normal', 'actual_events')),
            'unchanged exact f175 pure event and closure predicates')
    draft = object_json(content[code+'SOURCE_DRAFT2.json'])
    plan = object_json(content[code+'qualification/QUALIFICATION_PLAN.json'])
    composition = object_json(content[code+'qualification/COMPOSED1638.json'])
    require(draft['status'] == 'SOURCE_ONLY_CANONICALLY_FORMATTED_NOT_COMPILED_OR_RUN' and
            draft['newMethodsExecuted'] == draft['compilerInvocations'] == draft['accountInputsRead'] == 0,
            'original source-stage labels preserved, not rewritten to execution claims')
    require(len(draft['files']) == 15 and draft['productionPaths'] == 10 and draft['testPaths'] == 5 and
            draft['addedPaths'] == 12 and draft['replacedPaths'] == 3 and draft['wireSHA256'] == PINS['WIRE_CONTRACT.json'],
            'exact15 source and wire scope')
    require(plan['exactRunPassEvents'] == 18 and plan['newParents'] == 14 and plan['newSubcases'] == 4 and
            plan['ownedCommands'] == 6 and plan['priorMethodsRerun'] == 0 and plan['candidateSourceFiles'] == 1638 and
            plan['candidateSDKFiles'] == 750 and plan['sourceDraftSHA256'] == PINS['SOURCE_DRAFT2.json'] and
            plan['sourcePatchSHA256'] == PINS['runtime-state.draft2.patch'], 'exact frozen actual18 selection/composition')
    source_groups = literal(controller, 'GROUPS')
    require(json.loads(json.dumps(source_groups)) == {name: item['packages'] for name, item in plan['groups'].items()} and
            json.loads(json.dumps(literal(controller, 'SUBCASES'))) == plan['subcases'], 'selection plan equals executed qualifier source')
    formatted = receipts['format15.json']
    require(formatted['status'] == 'PASS_SOURCE_FORMAT15_NOT_COMPILED_NOT_TESTED' and
            formatted['errors'] == formatted['completionErrors'] == [] and formatted['allOwnedGroupsPositivelyAbsent'] is True,
            'actual canonical formatter receipt')
    formatted_rows = {row['path']: row for row in formatted['worker']['rows']}
    require(len(formatted_rows) == len(formatted['worker']['rows']) == 15 and set(formatted_rows) == set(draft['files']),
            'exact fifteen formatter outputs')
    for name, change in draft['files'].items():
        raw = content[code+'overlay/'+name]
        row = formatted_rows[name]
        require(identity(raw) == change['after'] == row['output'] and row['exitCode'] == 0 and row['stderr'] == '' and
                row['sameOwnedGroupAtStart'] is True and base64.b64decode(row['source'], validate=True) == raw,
                'each published overlay byte equals actual canonical source')
    require({name.removeprefix(code+'overlay/') for name in content if name.startswith(code+'overlay/')} == set(draft['files']),
            'no undeclared source overlay')

    c13 = receipts['c13-completion.json']
    original = receipts['c13-original-fail.json']
    require(original['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
            c13['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
            c13['retainedQualification']['receiptSHA256'] == RECEIPTS['c13-original-fail.json'] and
            c13['retainedActualMethodCount'] == 8 and c13['newActualMethodCount'] == 5 and
            c13['priorTestMethodsReexecuted'] == 0 and c13['errors'] == c13['completionErrors'] == [] and
            c13['allOwnedGroupsPositivelyAbsent'] is True and len(c13['processes']) == 4 and all(normal(row) for row in c13['processes']),
            'retain exact C13 original FAIL and accepted8+5, no historical execution or reclassification')
    base_inputs = maps['c13-compiled-source-inputs.json']
    base_map = maps['c13-source-manifest.json']['files']
    config = c13['separatelyDeclaredRuntimeConfig']
    require(config == {'path': 'staging.yml', 'bytes': 1137,
        'sha256': 'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'}, 'exact separately declared C13 configuration')
    before = dict(base_map, **{'staging.yml': {key: config[key] for key in ('bytes', 'sha256')}})
    require(len(base_map) == 1625 and len(before) == 1626 and base_inputs['files'] == before and
            c13['compiledSourceInputSHA256'] == MAPS['c13-compiled-source-inputs.json'] and
            c13['sourceManifestSHA256'] == MAPS['c13-source-manifest.json'], 'full C13 compiled-source provenance')
    expected, modes = dict(before), dict(base_inputs['modes'])
    for name, change in draft['files'].items():
        require(before.get(name) == change['before'], 'exact C13 before-image: '+name)
        expected[name], modes[name] = change['after'], 0o644
    require(composition['baseCompiledInputsSHA256'] == MAPS['c13-compiled-source-inputs.json'] and
            composition['sourceDraftSHA256'] == PINS['SOURCE_DRAFT2.json'] and composition['files'] == expected and
            len(expected) == 1638 and sum(name.startswith('.runtime-artifacts/sdk-source/') for name in expected) == 750,
            'independent full1638/SDK750 composition')
    require(maps['runtime-source-manifest.json'] == composition and
            maps['runtime-compiled-source-inputs.json'] == {'files': expected, 'modes': modes},
            'exact actual full compiled bytes and modes')

    actual = receipts['runtime18.json']
    require(actual['protocol'] == 'pinkha-native-runtime-state-qualification-v1' and
            actual['status'] == 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT' and
            actual['controller'] == identity(controller) and actual['errors'] == actual['completionErrors'] == [] and
            actual['allOwnedGroupsPositivelyAbsent'] is True and len(actual['processes']) == 6 and
            all(normal(row) for row in actual['processes']), 'actual18 and six normal closed command groups')
    require(actual['actualMethods'] == {'parents': 14, 'subcases': 4, 'runs': 18, 'passes': 18, 'skips': 0,
            'oldMethodsRerun': 0, 'freshSDKMethods': 1} and actual['nativeProductBuilds'] == 1 and
            actual['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True, 'originalC13Source': True},
            'complete original runtime qualification acceptance')
    require(actual['sourceFiles'] == 1638 and actual['sdkSourceFiles'] == 750 and
            actual['sourceDraftSHA256'] == PINS['SOURCE_DRAFT2.json'] and
            actual['sourceManifestSHA256'] == MAPS['runtime-source-manifest.json'] and
            actual['compiledSourceInputSHA256'] == MAPS['runtime-compiled-source-inputs.json'], 'actual source closure fields')
    require(actual['retainedC13']['completionSHA256'] == RECEIPTS['c13-completion.json'] and
            actual['retainedC13']['originalFailureSHA256'] == RECEIPTS['c13-original-fail.json'] and
            actual['retainedC13']['compiledSourceInputsSHA256'] == MAPS['c13-compiled-source-inputs.json'] and
            actual['retainedC13']['priorMethodReexecution'] == 0, 'historical C13 source/proof attribution')
    require(all(actual[name] == 0 for name in ('priorTestMethodsReexecuted', 'retainedPrivateAccountInputs',
            'privateRecordExports', 'nativeCLIAccountProcesses', 'C313SourceWrites', 'C3CacheWrites',
            'cloudQuotaActivationOrAccessCodeCalls')) and actual['heartSyncDateProduced'] is False and
            actual['personalProvenance'] == 'UNAVAILABLE_EXPLICIT_NULL' and
            actual['nativeHTTPRuntimeRoutes'] == 'NOT_RUN_SEPARATE_READ_ONLY_FOUR_DECISIONS_REQUIRED' and
            actual['standaloneAnySDKProducerNotEmbeddedHeart'] is True, 'unchanged actual scope and explicit unknowns')
    require(actual['OSPolicy'] == {'helperSHA256': '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1',
            'librarySHA256': '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19',
            'actualOriginalControlReceiptSHA256': 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab',
            'appliedBeforeEveryTestCommand': True, 'newFreshFixtureRequiresLiveEPERM': True} and
            actual['actualFreshSDKOSDenialVerified'] is True, 'actual original policy reuse and fresh enforced test')
    require(actual['goToolchain'] == c13['goToolchain'] and
            actual['currentNativeCompilerObservation']['tools'] == c13['currentNativeCompilerObservation']['tools'] and
            actual['currentNativeCompilerObservation']['explicitEnvironment'] == c13['currentNativeCompilerObservation']['explicitEnvironment'] and
            actual['currentNativeCompilerObservation']['PATH'] == c13['currentNativeCompilerObservation']['PATH'],
            'same recorded Go and current C compiler identity')
    parent = '/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7'
    source = parent+'/source'
    require(actual['sourceRoot'] == source, 'exact actual source location')
    phases = ('toolchain', 'sdk-units', 'server-units', 'fresh-sdk', 'native-build', 'native-metadata')
    logs = {}
    for index, phase in enumerate(phases):
        logs[phase] = pin(doc+'logs/'+phase+'.log', actual['processes'][index]['logSHA256'])
    require(object_json(logs['toolchain']) == actual['currentNativeCompilerObservation']['metadata'] and
            logs['native-build'] == b'', 'exact actual metadata and empty successful native-build log')
    events = {}
    for index, phase in enumerate(phases[1:4], start=1):
        spec = plan['groups'][phase]
        packages = spec['packages']
        selected = sorted(name for methods in packages.values() for name in methods)
        argv = [actual['OSExecPython']['path'], '-B',
            '/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py',
            '--exec', actual['goToolchain']['driver']['path'], 'test', '-json', '-count=1', '-p', '2', '-parallel=1',
            '-timeout='+spec['testTimeout'], '-run', '^('+'|'.join(selected)+')$', *packages]
        row = actual['processes'][index]
        require(row['argv'] == argv and row['cwd'] == source+('/.runtime-artifacts/sdk-source' if spec['cwd'] == 'sdk' else ''),
                'exact actual selected command and CWD')
        require(actual['rawLogs'][phase] == dict(identity(logs[phase]), path=parent+'/'+phase+'/original.log'),
                'complete retained raw event log binding')
        events[phase] = actual_events(logs[phase], packages, plan['subcases'])
        require(events[phase] == actual[phase], 'independent raw event parsing matches receipt')
    require(sum(value['runs'] for value in events.values()) == 18, 'exact eighteen new actual events')
    binary = actual['nativeBinary']
    require(binary == {'path': parent+'/any', 'bytes': 78294169, 'mode': 0o700,
            'sha256': '84a4432a0f6b330444dc35f1cf024d95fe9eea1e4e8eb3e2dfb1b99dcb24e974'} and
            actual['processes'][4]['argv'] == [actual['goToolchain']['driver']['path'], 'build', '-p', '2', '-o', parent+'/any', './cmd/any'] and
            actual['processes'][4]['cwd'] == source and
            actual['processes'][5]['argv'] == [actual['goToolchain']['driver']['path'], 'version', '-m', parent+'/any'],
            'one exact retained native product, no executable Git payload')
    base_module = pin(doc+'logs/c13-native-metadata.log', 'e0b3fc887d2fbfa4f81ff3f32d1a2d438aadefedd2357643fe0d1208cd1d99c1')
    require(identity(logs['native-metadata']) == actual['binaryModuleMetadata'] and
            logs['native-metadata'].splitlines()[1:] == base_module.splitlines()[1:], 'unchanged standalone module graph')

    installed = receipts['runtime-source-install.json']
    require(installed['status'] == 'PASS_EXACT_RUNTIME_STATE18_SOURCE_INSTALL_ONLY_NOT_RUN' and
            installed['errors'] == [] and installed['commands'] == [] and installed['newChildren'] == 0 and
            installed['sourceMembersUnchangedAtCompletion'] is True and installed['installerUnchangedAtCompletion'] is True,
            'original runtime source installation receipt')
    stage_members = {name.removeprefix(code): identity(raw) for name, raw in content.items()
        if name.startswith(code+'overlay/') or name in {code+key for key in (
            'SOURCE_DRAFT2.json', 'WIRE_CONTRACT.json', 'runtime-state.draft2.patch', 'qualification/qualify_runtime_state.py',
            'qualification/QUALIFICATION_PLAN.json', 'qualification/COMPOSED1638.json', 'qualification/owned_swift_commands.py')}}
    require(len(stage_members) == 22 and installed['installedFiles'] == stage_members, 'all22 originally installed source bytes')
    http_plan = object_json(content[code+'http/HTTP_SOURCE_PLAN.json'])
    http_installed = receipts['http4-source-install-only.json']
    require(http_plan['status'] == 'SOURCE_ONLY_NOT_INSTALLED_OR_RUN' and
            http_plan['ownerNewGET200'] == http_plan['removedMemberNewGET403'] == 2 and
            http_plan['roleInviteUploadMutation'] == http_plan['oldContentOrMetadataDecisionsReexecuted'] == 0,
            'preserved original HTTP4 source plan, no actual HTTP claim')
    require(http_installed['status'] == 'PASS_EXACT_RUNTIME_STATE_HTTP4_SOURCE_INSTALL_ONLY_NOT_RUN' and
            http_installed['dependentStageStatus'] == 'NOT_RUN' and http_installed['errors'] == [] and
            http_installed['commands'] == [] and http_installed['newChildren'] == http_installed['nativeProcesses'] ==
            http_installed['compilerInvocations'] == http_installed['testInvocations'] == http_installed['accountInputs'] == 0 and
            http_installed['sourceMembersUnchangedAtCompletion'] is True and http_installed['installerUnchangedAtCompletion'] is True,
            'actual installation only, zero HTTP/account/test processes')
    require(http_installed['installedFiles'] == http_plan['files'] == {
        name: identity(content[code+'http/'+name]) for name in http_plan['files']}, 'four exact pending HTTP sources')
    require(not any('http4-pass' in name or name.endswith('/any') for name in content), 'no fabricated HTTP receipt or native executable payload')
    return {'status': 'VALIDATED_PUBLIC_SOURCE15_ACTUAL18_HTTP4_NOT_RUN',
        'runtimeReceiptSHA256': RECEIPTS['runtime18.json'], 'sourcePaths': 15, 'sourceFiles': 1638, 'sdkSourceFiles': 750,
        'actualNewRunPassEvents': 18, 'newParents': 14, 'newSubcases': 4, 'normalClosedGroups': 6,
        'actualNewEvents': events, 'oneRetainedNativeProduct': binary,
        'currentLiveBinaryOrFilesystemAdmissionPerformed': False, 'newCompilerOrTestInvocations': 0,
        'retainedC13': {'originalFailureSHA256': RECEIPTS['c13-original-fail.json'],
            'completionSHA256': RECEIPTS['c13-completion.json'], 'historicalSDKMethods': 8,
            'historicalServerMethods': 5, 'oldMethodsReexecuted': 0},
        'http4': {'sourceInstalled': True, 'actualRuntimeStatus': 'NOT_RUN', 'newNativeProcesses': 0,
            'actualDecisions': 0, 'futureRequiredOwner200': 2, 'futureRequiredRemovedMember403': 2},
        'personalProvenanceAvailable': False, 'heartSyncDateProduced': False,
        'cloudQuotaRecovered': False, 'appleBoundRuntimeQualified': False, 'consumerAdoptionQualified': False}
