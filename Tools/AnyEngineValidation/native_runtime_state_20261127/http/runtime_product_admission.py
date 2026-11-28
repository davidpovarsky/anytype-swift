"""Read-only admission for the one future C13 + runtime-state native product.

This module does not launch a process, access an account or write a file. Its
caller supplies bounded public-source reads, complete inventory and checkpoints.
No historical test is executed to establish this receipt/source join.
"""
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import stat

MIB = 1024**2
SOURCE_INPUT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-source-20261127-attempt1')
QUALIFIER = SOURCE_INPUT/'qualification/qualify_runtime_state.py'
QUALIFIER_SHA = '5b74a95e00a9a45bab0310e64b7765ebbb70b133e1482093b23cbbe9355b8656'
QUALIFIER_BYTES = 39818
PLAN_SHA = '2b8749bea0f82f4fcacabe73715ba8caf8b4c7851ccd8a6f884cfdf6d7400439'
COMPOSED_SHA = '12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9'
DRAFT_SHA = 'f042531d9fb204aa7d92e9c73e375e839753b46b796330c7c2cce8d79a58daa4'
PATCH_SHA = '3d6a7d1175429f2dedf4993fbaf47c91ff8cfbaf9202e2c6ef1de15efcf7c478'
WIRE_SHA = '3d13cb658cb45cf6b690c0d052aa6ebdae06174ec72c7e1826ff0f04019f896d'
FORMAT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-gofmt-20261127-attempt1/result.json')
FORMAT_SHA = '070c6e482c923a7428ff7b6580a0acefa7ec0097844df515cc2b0a1f5d79e109'
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
LIBRARY = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
LIBRARY_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OS_PROOF_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
PRODUCER_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
C13 = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127')
C13_COMPLETION = C13/'qualification-completion-attempt1'
C13_SOURCE = C13/'qualification-attempt1/source'
C13_RECEIPT_SHA = 'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d'
C13_FAILURE_SHA = '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b'
C13_INPUTS_SHA = '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0'
C13_MANIFEST_SHA = 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3'
C13_MODULE_SHA = 'e0b3fc887d2fbfa4f81ff3f32d1a2d438aadefedd2357643fe0d1208cd1d99c1'


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


def admit_product(pin, inventory, receipt_path, receipt_sha, check):
    """Return only a fully joined actual product; every read is public/allowlisted."""
    check()
    parent = receipt_path.parent
    require(parent.parent == PRODUCER_PARENT and receipt_path.name == 'result.json' and
            re.fullmatch(r'attempt[1-9][0-9]{0,2}', parent.name) and
            int(parent.name.removeprefix('attempt')) >= 7 and re.fullmatch(r'[0-9a-f]{64}', receipt_sha),
            'future actual runtime18 producer namespace and exact receipt')
    raw_controller = pin(QUALIFIER, QUALIFIER_SHA)
    require(len(raw_controller) == QUALIFIER_BYTES, 'reviewed exact runtime18 qualifier')
    pin(SOURCE_INPUT/'qualification/owned_swift_commands.py', OWNED_SHA)
    plan = object_json(pin(SOURCE_INPUT/'qualification/QUALIFICATION_PLAN.json', PLAN_SHA))
    composition = object_json(pin(SOURCE_INPUT/'qualification/COMPOSED1638.json', COMPOSED_SHA))
    draft = object_json(pin(SOURCE_INPUT/'SOURCE_DRAFT2.json', DRAFT_SHA))
    pin(SOURCE_INPUT/'runtime-state.draft2.patch', PATCH_SHA)
    pin(SOURCE_INPUT/'WIRE_CONTRACT.json', WIRE_SHA)
    require(plan['sourceDraftSHA256'] == DRAFT_SHA and
            plan['baseC13CompiledInputsSHA256'] == C13_INPUTS_SHA and plan['baseC13CompletionSHA256'] == C13_RECEIPT_SHA and
            plan['exactRunPassEvents'] == 18 and plan['ownedCommands'] == 6 and plan['priorMethodsRerun'] == 0 and
            draft['wireSHA256'] == WIRE_SHA and len(draft['files']) == 15,
            'reviewed coherent source/selection plan')
    formatted = object_json(pin(FORMAT, FORMAT_SHA))
    require(formatted['status'] == 'PASS_SOURCE_FORMAT15_NOT_COMPILED_NOT_TESTED' and
            formatted['errors'] == formatted['completionErrors'] == [] and
            formatted['allOwnedGroupsPositivelyAbsent'] is True and len(formatted['worker']['rows']) == 15,
            'actual canonical source formatting')
    formatted_rows = {row['path']: row for row in formatted['worker']['rows']}
    require(len(formatted_rows) == 15 and set(formatted_rows) == set(draft['files']), 'exact canonical output paths')
    for name, change in draft['files'].items():
        check()
        row = formatted_rows[name]
        raw = pin(SOURCE_INPUT/'overlay'/name, change['after']['sha256'])
        require(identity(raw) == change['after'] == row['output'] and row['exitCode'] == 0 and
                row['stderr'] == '' and row['sameOwnedGroupAtStart'] is True and
                base64.b64decode(row['source'], validate=True) == raw, 'current overlay equals actual formatter bytes')

    original = object_json(pin(C13/'qualification-attempt1/result.json', C13_FAILURE_SHA))
    base = object_json(pin(C13_COMPLETION/'result.json', C13_RECEIPT_SHA))
    base_input = object_json(pin(C13_COMPLETION/'compiled-source-inputs.json', C13_INPUTS_SHA))
    base_map = object_json(pin(C13_COMPLETION/'source-manifest.json', C13_MANIFEST_SHA))['files']
    require(original['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
            base['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
            base['retainedQualification']['receiptSHA256'] == C13_FAILURE_SHA and
            base['retainedActualMethodCount'] == 8 and base['newActualMethodCount'] == 5 and
            base['priorTestMethodsReexecuted'] == 0 and base['errors'] == base['completionErrors'] == [] and
            len(base['processes']) == 4 and all(normal(row) for row in base['processes']) and
            base['allOwnedGroupsPositivelyAbsent'] is True, 'actual C13 retained8/new5 with original failure unchanged')
    config = base['separatelyDeclaredRuntimeConfig']
    require(config == {'path': 'staging.yml', 'bytes': 1137,
            'sha256': 'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'}, 'actual separately declared C13 config')
    expected_base = dict(base_map, **{'staging.yml': {k: config[k] for k in ('bytes', 'sha256')}})
    require(base['compiledSourceInputSHA256'] == C13_INPUTS_SHA and base['sourceManifestSHA256'] == C13_MANIFEST_SHA and
            len(base_map) == 1625 and base_input['files'] == expected_base and len(expected_base) == 1626 and
            inventory(C13_SOURCE, check) == base_input, 'complete immutable actual C13 source and modes')
    expected, modes = dict(expected_base), dict(base_input['modes'])
    for name, change in draft['files'].items():
        require(expected_base.get(name) == change['before'], 'exact runtime before-image on actual C13')
        expected[name], modes[name] = change['after'], 0o644
    require(composition['baseCompiledInputsSHA256'] == C13_INPUTS_SHA and composition['sourceDraftSHA256'] == DRAFT_SHA and
            composition['files'] == expected and len(expected) == 1638 and
            sum(name.startswith('.runtime-artifacts/sdk-source/') for name in expected) == 750,
            'independent full1638/SDK750 source composition')

    producer = object_json(pin(receipt_path, receipt_sha))
    require(producer['protocol'] == 'pinkha-native-runtime-state-qualification-v1' and
            producer['status'] == 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT' and
            producer['controller'] == identity(raw_controller) and producer['errors'] == producer['completionErrors'] == [] and
            producer['allOwnedGroupsPositivelyAbsent'] is True and len(producer['processes']) == 6 and
            all(normal(row) for row in producer['processes']) and
            producer['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True, 'originalC13Source': True},
            'actual exact runtime18 native producer and six normal closed groups')
    require(producer['actualMethods'] == {'parents': 14, 'subcases': 4, 'runs': 18, 'passes': 18, 'skips': 0,
            'oldMethodsRerun': 0, 'freshSDKMethods': 1} and producer['nativeProductBuilds'] == 1 and
            producer['priorTestMethodsReexecuted'] == producer['retainedPrivateAccountInputs'] ==
            producer['privateRecordExports'] == producer['nativeCLIAccountProcesses'] ==
            producer['C313SourceWrites'] == producer['C3CacheWrites'] ==
            producer['cloudQuotaActivationOrAccessCodeCalls'] == 0 and
            producer['personalProvenance'] == 'UNAVAILABLE_EXPLICIT_NULL' and producer['heartSyncDateProduced'] is False,
            'eighteen new actual events and no substituted historical/private scope')
    require(producer['retainedC13']['completionSHA256'] == C13_RECEIPT_SHA and
            producer['retainedC13']['originalFailureSHA256'] == C13_FAILURE_SHA and
            producer['retainedC13']['compiledSourceInputsSHA256'] == C13_INPUTS_SHA and
            producer['retainedC13']['priorMethodReexecution'] == 0, 'retained C13 attribution')
    source = parent/'source'
    current_input = object_json(pin(parent/'compiled-source-inputs.json', producer['compiledSourceInputSHA256']))
    current_map = object_json(pin(parent/'source-manifest.json', producer['sourceManifestSHA256']))
    require(producer['sourceRoot'] == str(source) and producer['sourceFiles'] == 1638 and producer['sdkSourceFiles'] == 750 and
            producer['sourceDraftSHA256'] == DRAFT_SHA and current_input == {'files': expected, 'modes': modes} and
            current_map == composition and inventory(source, check) == current_input,
            'actual full native source and complete file modes remain exact')
    require(producer['OSPolicy'] == {'helperSHA256': OFFLINE_SHA, 'librarySHA256': LIBRARY_SHA,
            'actualOriginalControlReceiptSHA256': OS_PROOF_SHA, 'appliedBeforeEveryTestCommand': True,
            'newFreshFixtureRequiresLiveEPERM': True} and producer['actualFreshSDKOSDenialVerified'] is True,
            'exact test isolation and actual fresh SDK enforcement')
    pin(OFFLINE, OFFLINE_SHA, 65536)
    pin(LIBRARY, LIBRARY_SHA, 4*MIB)
    python = producer['OSExecPython']
    require(identity(pin(Path(python['path']), python['sha256'], 32*MIB)) ==
            {k: python[k] for k in ('bytes', 'sha256')}, 'same admitted OS-wrapper Python')
    go = producer['goToolchain']
    native = producer['currentNativeCompilerObservation']
    require(go == base['goToolchain'] and native['tools'] == base['currentNativeCompilerObservation']['tools'] and
            native['explicitEnvironment'] == base['currentNativeCompilerObservation']['explicitEnvironment'] and
            native['PATH'] == base['currentNativeCompilerObservation']['PATH'], 'same actual C13 producer toolchain')
    for tool in [go['driver'], *go['tools'].values(), *native['tools'].values()]:
        check()
        require(identity(pin(Path(tool['path']), tool['sha256'], 128*MIB)) ==
                {k: tool[k] for k in ('bytes', 'sha256')}, 'current exact admitted compiler/tool bytes')
        if 'mode' in tool:
            require(stat.S_IMODE(Path(tool['path']).lstat().st_mode) == tool['mode'], 'current compiler mode')
    environment = producer['environment']
    require(all(environment[name] == value for name, value in {
        'GOTOOLCHAIN': 'local', 'GOMAXPROCS': '2', 'GOMEMLIMIT': '1GiB', 'CGO_ENABLED': '1',
        'GOWORK': 'off', 'GOFLAGS': '-mod=readonly', 'GOPROXY': 'off', 'GOSUMDB': 'off',
        'GOTMPDIR': str(parent/'temporary'), 'TMPDIR': str(parent/'temporary'),
        'PINKHA_FRESH_FILES_FIXTURE_ROOT': str(parent/'fixtures'),
        **native['explicitEnvironment'], 'PATH': native['PATH']}.items()), 'closed original build/test environment')
    actual = {}
    for ordinal, label in enumerate(('sdk-units', 'server-units', 'fresh-sdk'), start=1):
        check()
        spec, row = plan['groups'][label], producer['processes'][ordinal]
        packages = spec['packages']
        methods = sorted(method for group in packages.values() for method in group)
        argv = [python['path'], '-B', str(OFFLINE), '--exec', go['driver']['path'], 'test', '-json', '-count=1',
            '-p', '2', '-parallel=1', '-timeout='+spec['testTimeout'], '-run', '^('+'|'.join(methods)+')$', *packages]
        cwd = source/'.runtime-artifacts/sdk-source' if spec['cwd'] == 'sdk' else source
        require(row['argv'] == argv and row['cwd'] == str(cwd), 'actual exact new test selection/source')
        log_row = producer['rawLogs'][label]
        require(log_row['path'] == str(parent/label/'original.log') and log_row['sha256'] == row['logSHA256'],
                'actual command/log attribution')
        raw = pin(parent/label/'original.log', row['logSHA256'], 16*MIB)
        require(identity(raw) == {k: log_row[k] for k in ('bytes', 'sha256')}, 'complete original event stream')
        actual[label] = actual_events(raw, packages, plan['subcases'])
        require(actual[label] == producer[label], 'independently reconstructed eighteen events')
    require(sum(row['runs'] for row in actual.values()) == 18, 'exact new event total')
    binary = parent/'any'
    description = producer['nativeBinary']
    require(description['path'] == str(binary) and 0 < description['bytes'] <= 128*MIB and description['mode'] & 0o111,
            'same single qualified executable')
    require(identity(pin(binary, description['sha256'], 128*MIB)) == {k: description[k] for k in ('bytes', 'sha256')} and
            stat.S_IMODE(binary.lstat().st_mode) == description['mode'], 'current native executable bytes/mode')
    require(producer['processes'][4]['argv'] == [go['driver']['path'], 'build', '-p', '2', '-o', str(binary), './cmd/any'] and
            producer['processes'][4]['cwd'] == str(source) and
            producer['processes'][5]['argv'] == [go['driver']['path'], 'version', '-m', str(binary)],
            'one build and its original module inspection')
    module = pin(parent/'native-metadata/original.log', producer['processes'][5]['logSHA256'], 65536)
    base_module = pin(C13_COMPLETION/'native-metadata/original.log', C13_MODULE_SHA, 65536)
    require(identity(module) == producer['binaryModuleMetadata'] and module.splitlines()[1:] == base_module.splitlines()[1:] and
            go['metadata']['GOVERSION'].encode() in module.splitlines()[0] and
            producer['standaloneAnySDKProducerNotEmbeddedHeart'] is True, 'original standalone native module graph')
    return {'producer': producer, 'source': source, 'sourceInventory': current_input, 'binary': binary,
            'binaryIdentity': description, 'baseSource': C13_SOURCE, 'baseInventory': base_input,
            'actualNewEvents': actual, 'originalC13FailureSHA256': C13_FAILURE_SHA,
            'actualC13CompletionSHA256': C13_RECEIPT_SHA, 'personalProvenanceAvailable': False}
