"""Read-only admission of the C3-produced Crypto subset for isolated consumers.

The original E5/17 producer record remains immutable historical evidence. C3
rebuilt four aggregate objects and their intermediate closure; this module
admits that separately observed producer, never four substituted output hashes.
No compiler, test, resolver, native account or build instruction is executed.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys

CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
PRODUCTS = CACHE/'out/Products/Debug-linux-aarch64'
APPLICATION = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127')
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
E5 = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/successor-runs/swift-client-physical5')
OBSERVATION = Path('/mnt/development/projects/evidence/pinkha-c-crypto-producer-20261127/observation3/result.json')
OBSERVATION_SHA = 'd93433b85ab53b941cde27af52d3612d21b2a93af3d5e838cff2126607f3af17'
PRODUCER = Path('/var/lib/pinkha-w1-functional-migration-20261127/source-facts-components-attempt2')
PRODUCER_SHA = '437fab26265b371180016caae6fc87c72a9b471deecc70d6d99b92309d51959f'
SOURCE_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
OLD_REUSE_SHA = 'da72939a5b20da7b417f85d00a689c245f59516d3ae94ddaef31c2c7a50f65f0'
DEPENDENCY_SHA = 'de8b4f95209e29366c7a59995d622f4c6f34288a575e4b4b13a48324890533b6'
CUSTODY = Path('/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1/result.json')
CUSTODY_SHA = 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
BUILD_DATA = PHYSICAL/'out/Intermediates.noindex/XCBuildData/5f7ca1648219fca76b90928b9f530d1c2abba148c97b5a0410cbc00a30066ae3.xcbuilddata'
BUILD_MANIFEST_SHA = '849e41c676460c874e4fc6cc9e9359fbff8066f9850e93da06d68921e15442e3'
TASK_STORE_SHA = '81dd4476f78ae077df1198d266910c2e570a7d364e5eb9ed965dbfb638e1257d'
MODULES = ('Crypto', 'CryptoBoringWrapper')
OBJECTS = ('Crypto', 'CryptoBoringWrapper', 'CCryptoBoringSSL', 'CCryptoBoringSSLShims')
TOOL_LINKS = {'swift': 'swift-driver', 'swiftc': 'swift-driver', 'clang': 'clang-21', 'clang++': 'clang'}
DEPENDENCIES = {
    'swift-crypto': ('e8d6eba1fef23ae5b359c46b03f7d94be2f41fed', 919),
    'swift-asn1': ('917b472dbe53ba699cbb0495f9a95a084bc6364d', 211),
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def admitted(path):
    path = Path(path)
    require(path.is_absolute(), 'absolute producer input')
    if path.is_relative_to(CACHE):
        require(CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL) and CACHE.resolve() == PHYSICAL,
                'exact retained C producer alias')
        target = PHYSICAL/path.relative_to(CACHE)
        require(target.resolve() == target and path.resolve() == target and not target.is_symlink(),
                'no additional producer alias')
        return target
    if path.parent == TOOLCHAIN and path.name in TOOL_LINKS:
        require(path.is_symlink() and os.readlink(path) == TOOL_LINKS[path.name], 'exact original driver alias')
        if path.name == 'clang++':
            require((TOOLCHAIN/'clang').is_symlink() and os.readlink(TOOLCHAIN/'clang') == 'clang-21',
                    'exact original clang chain')
        target = TOOLCHAIN/('clang-21' if path.name.startswith('clang') else 'swift-driver')
        require(path.resolve() == target and target.resolve() == target and not target.is_symlink(),
                'fixed physical compiler driver')
        return target
    require(path.resolve() == path and not path.is_symlink(), 'physical non-producer input')
    return path


def identity(path, collect=False, maximum=512*1024**2):
    target = admitted(path)
    descriptor = os.open(target, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, 'bounded regular producer input')
        digest, chunks, size = hashlib.sha256(), [], 0
        while True:
            chunk = os.read(descriptor, 1024**2)
            if not chunk:
                break
            digest.update(chunk); size += len(chunk)
            require(size <= maximum, 'bounded producer stream')
            if collect:
                chunks.append(chunk)
        require(before == os.fstat(descriptor) == target.lstat() and size == before.st_size,
                'producer input changed during noatime read')
    finally:
        os.close(descriptor)
    row = {'bytes': size, 'sha256': digest.hexdigest(), 'mode': stat.S_IMODE(before.st_mode)}
    return row, b''.join(chunks) if collect else None


def read_json(path, digest, keep, maximum=4*1024**2):
    row, raw = identity(path, True, maximum)
    require(row['sha256'] == digest, 'pinned producer record: '+str(path))
    keep[str(admitted(path))] = row
    return json.loads(raw)


def original_driver_commands(data):
    """The retained decoder, restricted to pinned MessagePack argv arrays."""
    needle = b'\xb3builtin-SwiftDriver'; offset = 0; found = {}
    while (start := data.find(needle, offset)) >= 0:
        offset = start+len(needle)
        require(start >= 3 and data[start-3] == 0xdc, 'expected original argv array16')
        count = int.from_bytes(data[start-2:start], 'big')
        require(1 <= count <= 256, 'bounded original driver argv')
        pos = start; args = []
        for _ in range(count):
            require(pos < len(data), 'complete original driver string')
            tag = data[pos]; pos += 1
            if 0xa0 <= tag <= 0xbf:
                length = tag & 31
            elif tag in (0xd9, 0xda, 0xdb):
                width = {0xd9: 1, 0xda: 2, 0xdb: 4}[tag]
                require(pos+width <= len(data), 'complete original string length')
                length = int.from_bytes(data[pos:pos+width], 'big'); pos += width
            else:
                raise RuntimeError('original driver argv contains non-string')
            require(length <= 8192 and pos+length <= len(data), 'bounded complete original string')
            args.append(data[pos:pos+length].decode()); pos += length
        if '-module-name' not in args:
            continue
        name = args[args.index('-module-name')+1]
        if name not in MODULES:
            continue
        require(args[:3] == ['builtin-SwiftDriver', '--', str(TOOLCHAIN/'swiftc')], 'original Swift driver')
        require(args[args.index('-target')+1] == 'aarch64-unknown-linux-gnu' and
                args[args.index('-swift-version')+1] == '5' and '-Onone' in args and '-enable-testing' in args,
                'original target and compiler flags')
        if name == 'Crypto':
            require('-DCRYPTO_IN_SWIFTPM' in args and '-DCRYPTO_IN_SWIFTPM_FORCE_BUILD_API' in args,
                    'original native Crypto implementation flags')
        row = {'argv': args, 'rawArraySHA256': hashlib.sha256(data[start-3:pos]).hexdigest()}
        if name in found:
            require(found[name]['argv'] == row['argv'] and found[name]['rawArraySHA256'] == row['rawArraySHA256'],
                    'different duplicate original driver invocations')
            found[name]['identicalOccurrences'] += 1
        else:
            found[name] = row | {'identicalOccurrences': 1}
    require(set(found) == set(MODULES), 'exact two Crypto module driver commands')
    return found


def source_membership(checkout, expected):
    root = admitted(checkout/'Sources')
    require(root.is_dir(), 'physical original dependency Sources')
    found = set()
    for directory, directories, files in os.walk(root, followlinks=False):
        require(not any((Path(directory)/name).is_symlink() for name in directories), 'no source directory alias')
        for name in files:
            path = Path(directory)/name
            require(path.is_file() and not path.is_symlink(), 'regular dependency source')
            found.add('Sources/'+path.relative_to(root).as_posix())
    require(found == {name for name in expected if name.startswith('Sources/')},
            'complete exact dependency Sources and include membership')


def qualify(guard=lambda: None):
    if sys.flags.optimize:
        raise RuntimeError('producer qualification guards must remain enabled')
    guard()
    retained = {}
    observation = read_json(OBSERVATION, OBSERVATION_SHA, retained)
    require(observation['protocol'] == 'pinkha-c3-current-crypto-producer-observation-v1' and
            observation['status'] == 'PASS_CURRENT_C3_CRYPTO_SUBSET_OBSERVED_NO_TEST_REPLAY' and
            observation['allObservedInputsStableThroughCompletion'] is True and observation['errors'] == [] and
            observation['compilerInvocations'] == observation['testInvocations'] == observation['accountOpens'] == 0,
            'exact read-only C3 producer observation')
    require(observation['controllerSHA256'] == '1454170720d38f6b1dc573e168a615b1125c311166d8011856a55abe9264473b',
            'reviewed C3 provenance observer')
    require(len(observation['immutableCurrentInputs']) == 1915, 'complete observed C3 source/input closure')
    component = read_json(PRODUCER/'result.json', PRODUCER_SHA, retained)
    require(component == observation['currentProducer'] and observation['currentProducerSHA256'] == PRODUCER_SHA and
            observation['currentProducerPath'] == str(PRODUCER/'result.json'), 'actual producer identity')
    require(component['status'] == 'PASS' and component['compiled'] is True and component['sourceUnchanged'] is True and
            component['exitCode'] == 0 and component['ownedGroupAbsent'] is True and component['errors'] == [] and
            not component['cleanupForcedKill'] and not component['cleanupRequired'] and
            len(component['passLines']) == len(component['startLines']) == 3 and component['failLines'] == [],
            'actual completed C3 compilation and three-method proof')
    require(component['sourceBeforeSHA256'] == component['sourceAfterSHA256'] == SOURCE_SHA and
            component['preparedSwiftSourceClosureSHA256'] == SOURCE_SHA, 'original C3 source closure binding')
    source_before = read_json(PRODUCER/'source-before.json', SOURCE_SHA, retained)
    require(read_json(PRODUCER/'source-after.json', SOURCE_SHA, retained) == source_before ==
            observation['current313SourceClosure'] and len(source_before) == 313, 'captured complete C3 application source')
    # Today's application checkout is not a compiler input of a Crypto-only
    # consumer. Preserve its original captured closure; never relabel it current.
    historical_application = {str(APPLICATION/name): digest for name, digest in source_before.items()}
    captured_application = {path: value for path, value in observation['immutableCurrentInputs'].items()
                            if Path(path).is_relative_to(APPLICATION)}
    require(set(captured_application) == set(historical_application) and
            all(value['sha256'] == historical_application[path] for path, value in captured_application.items()),
            'all historical application inputs exactly accounted for')
    custody = read_json(CUSTODY, CUSTODY_SHA, retained)
    require(component['cacheCustodyReceiptSHA256'] == CUSTODY_SHA and
            custody['status'] == 'PASS_EXACT_OWNED_SWIFT_CACHE_RELOCATED_STABLE_PATH_RETAINED' and
            custody['productsAndDependencyClosureUnchanged'] is True and custody['allExactPortableMetadataAndBytesRetained'] is True and
            custody['stableSymlinkInstalled'] is True and custody['source'] == str(CACHE) and
            custody['destination'] == str(PHYSICAL), 'original exact cache custody')
    admitted(PRODUCTS)
    original = read_json(E5/'retained-dependency-products.json', OLD_REUSE_SHA, retained)
    dependencies = read_json(E5/'dependency-before.json', DEPENDENCY_SHA, retained)
    require(observation['oldE5ReuseSHA256'] == OLD_REUSE_SHA and
            observation['exactOriginalDependencyManifestSHA256'] == DEPENDENCY_SHA, 'unchanged E5 provenance')
    live = {path: value for path, value in observation['immutableCurrentInputs'].items()
            if path not in historical_application}
    require(len(live) == 1602, 'all non-application producer inputs remain live requirements')
    for path, expected in live.items():
        guard()
        require(identity(Path(path))[0] == expected, 'exact current producer input: '+path)
        retained[path] = expected
    for name, (commit, count) in DEPENDENCIES.items():
        checkout = CACHE/'checkouts'/name
        record = dependencies[str(checkout)]
        require(component['dependencies'][name] == record['commit'] == commit and len(record['trackedFiles']) == count and
                observation['unchangedDependencySources'][str(checkout)] == record, 'original unchanged dependency source pin')
        for relative, expected in record['trackedFiles'].items():
            physical = str(admitted(checkout/relative))
            value = live[physical]
            require({key: value[key] for key in ['bytes', 'sha256']} == expected,
                    'exact dependency source linked to original version')
        source_membership(checkout, record['trackedFiles'])
    for name, alias in observation['toolchainExactAliases'].items():
        require(name in TOOL_LINKS and alias == {'target': TOOL_LINKS[name], 'physical': str(admitted(TOOLCHAIN/name))},
                'exact qualified compiler aliases')
    require(set(observation['toolchainExactAliases']) == set(TOOL_LINKS), 'all four compiler aliases')
    require(set(observation['toolchainPhysicalFiles']) == {'swift-driver', 'swift-frontend', 'clang-21'}, 'exact compiler executables')
    for name, expected in observation['toolchainPhysicalFiles'].items():
        require(live[str(TOOLCHAIN/name)] == expected, 'original compiler byte/mode identity')
    require(observation['currentBuildDataPath'] == str(BUILD_DATA), 'fixed actual C3 build plan')
    manifest = read_json(BUILD_DATA/'manifest.json', BUILD_MANIFEST_SHA, retained)
    task_row, task = identity(BUILD_DATA/'task-store.msgpack', True, 4*1024**2)
    require(task_row['sha256'] == TASK_STORE_SHA and original_driver_commands(task) == observation['currentCompilerCommands'],
            'actual current C3 module compilation commands')
    retained[str(BUILD_DATA/'task-store.msgpack')] = task_row
    source_lists, compiled = {}, {}
    for name, command in observation['currentCompilerCommands'].items():
        paths = [Path(value[1:]) for value in command['argv'] if value.startswith('@')]
        require(len(paths) == 1, 'one original Swift file list')
        value, raw = identity(paths[0], True, 1024**2)
        members = shlex.split(raw.decode())
        require(len(members) == (79 if name == 'Crypto' else 7) and len(set(members)) == len(members) and
                all(Path(path).is_relative_to(PHYSICAL/'checkouts/swift-crypto/Sources'/name) for path in members),
                'exact current physical compiler source list')
        source_lists[str(paths[0])] = {'file': value, 'members': members}
        for path in members:
            compiled[path] = live[path]
    require(source_lists == observation['compilerSourceLists'] and compiled == observation['compilerSources'] and
            len(compiled) == 86, 'all native Swift compiler source inputs')
    link_commands, linked, link_lists = {}, {}, {}
    for name in OBJECTS:
        output = PRODUCTS/(name+'.o')
        matches = [(key, value) for key, value in manifest['commands'].items() if value.get('tool') == 'shell' and
                   value.get('outputs') == [str(output), '<Linked Binary '+str(output)+'>']]
        require(len(matches) == 1, 'one original aggregate-object link command')
        key, command = matches[0]
        require(command['args'][0] == str(TOOLCHAIN/('clang++' if name == 'CCryptoBoringSSL' else 'clang')) and
                '-r' in command['args'] and command['args'][command['args'].index('-target')+1] == 'aarch64-unknown-linux-gnu',
                'original native linker and target')
        paths = [Path(value[1:]) for value in command['args'] if value.startswith('@')]
        require(len(paths) == 1 and paths[0].is_relative_to(CACHE/'out/Intermediates.noindex/swift-crypto.build'),
                'one fixed original native link list')
        value, raw = identity(paths[0], True, 1024**2)
        members = shlex.split(raw.decode())
        require(1 <= len(members) <= 1000 and len(set(members)) == len(members), 'bounded original native object membership')
        link_lists[name] = {'path': str(paths[0]), 'file': value, 'members': members}
        for path in members:
            require(Path(path).is_relative_to(CACHE/'out/Intermediates.noindex/swift-crypto.build'), 'fixed native object closure')
            linked[path] = live[str(admitted(Path(path)))]
        link_commands[key] = command
    require(link_commands == observation['currentLinkCommands'] and link_lists == observation['currentLinkLists'] and
            linked == observation['currentLinkedInputs'] and len(linked) == 448, 'complete actual C3 native link closure')
    outputs = observation['currentOutputProducts']
    modules = {name+'.swiftmodule/aarch64-unknown-linux-gnu.'+suffix for name in MODULES for suffix in ['swiftmodule', 'swiftdoc']}
    require(set(outputs) == {name+'.o' for name in OBJECTS} | modules, 'exact eight admitted dependency output files')
    for relative, expected in outputs.items():
        path = str(PRODUCTS/relative)
        require(live[str(admitted(Path(path)))] == expected, 'actual C3 consumer output identity')
        if relative in modules:
            require({key: expected[key] for key in ['bytes', 'sha256']} == original['immutableFiles'][path] and
                    expected['mode'] == original['modes'][path], 'original module and documentation ABI bytes remain exact')
    comparison = observation['oldE5CryptoInputComparison']
    require(len(comparison) == 550 and sum(not row['bytesEqualOld'] for row in comparison.values()) == 451 and
            all(row['modeEqualOld'] for row in comparison.values()), 'explicit full old-versus-current product delta')
    for path, value in comparison.items():
        require(value['old'] == original['immutableFiles'][path] and value['oldMode'] == original['modes'][path] and
                value['current'] == live[str(admitted(Path(path)))], 'complete original E5 comparison retained')
    crypto_source = dependencies[str(CACHE/'checkouts/swift-crypto')]['trackedFiles']
    headers = {relative: live[str(admitted(CACHE/'checkouts/swift-crypto'/relative))] for relative in crypto_source
               if any(relative.startswith('Sources/'+name+'/include/') for name in ['CCryptoBoringSSL', 'CCryptoBoringSSLShims'])}
    require(len(headers) == 94 and sum(value['bytes'] for value in headers.values()) == 2571399,
            'exact complete C header/modulemap subset for isolated imports')
    guard()
    return {
        'status': 'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_REUSE_ONLY',
        'observation': {'path': str(OBSERVATION), 'sha256': OBSERVATION_SHA},
        'producer': {'path': str(PRODUCER/'result.json'), 'sha256': PRODUCER_SHA},
        'producerApplicationSourceManifestSHA256': SOURCE_SHA,
        'producerApplicationSourceClosure': source_before,
        'currentApplicationWorktreeClaimedUnchanged': False,
        'historicalApplicationSourceRowsNotNewConsumerInputs': 313,
        'originalE5ProducerManifestSHA256': OLD_REUSE_SHA,
        'originalDependencySourceManifestSHA256': DEPENDENCY_SHA,
        'originalE5InputComparison': comparison,
        'producerExactStableToPhysicalMapping': {str(CACHE): str(PHYSICAL)},
        'liveInputs': retained,
        'currentCompilerCommands': observation['currentCompilerCommands'],
        'currentCompilerSourceLists': source_lists,
        'currentLinkCommands': link_commands,
        'currentLinkLists': link_lists,
        'currentLinkedInputs': linked,
        'currentOutputProducts': outputs,
        'dependencySources': observation['unchangedDependencySources'],
        'moduleFiles': {relative: outputs[relative] for relative in sorted(modules)},
        'headerFiles': headers,
        'headerSourceRoot': str(CACHE/'checkouts/swift-crypto'),
        'productDirectory': str(PRODUCTS),
        'linkObjects': [str(PRODUCTS/(name+'.o')) for name in OBJECTS],
        'swiftDriver': str(TOOLCHAIN/'swift'),
        'toolchainExactAliases': observation['toolchainExactAliases'],
        'additionalOriginalSystemLinkLibrary': 'stdc++',
        'sourceOnlyASN1PinNoASN1CompiledProductClaim': True,
        'dependencyCompilerInvocations': 0,
        'producerTestsReplayed': False,
        'originalSeventeenMethodsReplayed': False,
    }


def validate_after(admission, guard=lambda: None):
    """No dependency input can be replaced while the new consumer uses it."""
    after = qualify(guard)
    require(after == admission, 'C3 dependency admission changed during consumer qualification')
    return after
