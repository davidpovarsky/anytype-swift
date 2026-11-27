"""Read-only provenance for the retained canonical Swift dependency products.

No dependency target is rebuilt. The isolated caller still compiles the exact
production client/generated source and runs every actual XCTest method.
"""
import hashlib, json, os, re, shlex, stat
from pathlib import Path

CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
PRODUCTS = CACHE/'out/Products/Debug-linux-aarch64'
BUILD_DATA = CACHE/'out/Intermediates.noindex/XCBuildData/4b41a04d4a068c57706250bbd949e24269e854d2b81b89d3c14e357f5c995433.xcbuilddata'
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
COMPONENT_RECEIPT = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-components-attempt3/result.json')
CUSTODY_RECEIPT = Path('/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1/result.json')
PINS = {
    COMPONENT_RECEIPT: 'd9bf1c3911219e2227c17db48726a8508030a20f7557f19934504f599b76c69b',
    CUSTODY_RECEIPT: 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8',
    BUILD_DATA/'manifest.json': 'a6123b8f24b7edcd2cd922f77f6af5a662a520854b2926d0830533415966c590',
    BUILD_DATA/'task-store.msgpack': 'dfa181d27e89fe3fade98b02a259beda99c44b82753c34250f6ee6231a6e7e4e',
}
MODULES = ('Crypto', 'CryptoBoringWrapper')
OBJECTS = ('Crypto', 'CryptoBoringWrapper', 'CCryptoBoringSSL', 'CCryptoBoringSSLShims')
PRODUCER_OUTPUT_PINS = {
    "Crypto.o": "58850f407216c5b185f757b090e2bba60128b18404c3bd8c807676433f21a332",
    "CryptoBoringWrapper.o": "07401e221fbdc883d1e049e4ae9dfa74d50b2822707d4edfe8cdcc8aab6adc3b",
    "CCryptoBoringSSL.o": "d19eb6212430b4f14b0877fe096f4a41228c214bde075e4fdf5183e598cd7d35",
    "CCryptoBoringSSLShims.o": "e8629121172d39d210b77dcfcf2db64a1dad6847ead746265575834881e63d3d",
    "Crypto.swiftmodule/aarch64-unknown-linux-gnu.swiftdoc": "6c3caa5098d87cf62f6a80efa31cb45ff79569a7351e9d7e1775eb95bb78f851",
    "Crypto.swiftmodule/aarch64-unknown-linux-gnu.swiftmodule": "2bc5921142a33b7530155f81903cfabd0a4a7f0bc1d1436d55ccee008114b886",
    "CryptoBoringWrapper.swiftmodule/aarch64-unknown-linux-gnu.swiftdoc": "e92a1b7ab635241b80dc237e1668425471cf8e698091fb2b0781c712aaf515ea",
    "CryptoBoringWrapper.swiftmodule/aarch64-unknown-linux-gnu.swiftmodule": "ee377d02fe9702342f72974077fd6cd5657a9e72c2d5d4913f847423db69c40a"
}

def original_driver_commands(data):
    """Decode only the bounded original MessagePack string-array argv values.

    The full task store is pinned above. This is provenance extraction, never an
    execution of untrusted build instructions or a general-purpose RPC decoder.
    """
    needle = b'\xb3builtin-SwiftDriver'; offset = 0; found = {}
    while (start := data.find(needle, offset)) >= 0:
        offset = start+len(needle)
        assert data[start-3] == 0xdc, 'expected original argv array16'
        count = int.from_bytes(data[start-2:start], 'big')
        assert 1 <= count <= 256
        pos = start; args = []
        for _ in range(count):
            tag = data[pos]; pos += 1
            if 0xa0 <= tag <= 0xbf: length = tag & 31
            elif tag in (0xd9, 0xda, 0xdb):
                width = {0xd9:1, 0xda:2, 0xdb:4}[tag]
                length = int.from_bytes(data[pos:pos+width], 'big'); pos += width
            else: raise AssertionError('original argv contains non-string')
            assert length <= 8192 and pos+length <= len(data)
            args.append(data[pos:pos+length].decode()); pos += length
        if '-module-name' not in args: continue
        name = args[args.index('-module-name')+1]
        if name not in MODULES: continue
        assert args[:3] == ['builtin-SwiftDriver', '--', str(TOOLCHAIN/'swiftc')]
        assert args[args.index('-target')+1] == 'aarch64-unknown-linux-gnu'
        assert args[args.index('-swift-version')+1] == '5'
        assert '-Onone' in args and '-enable-testing' in args
        if name == 'Crypto':
            assert '-DCRYPTO_IN_SWIFTPM' in args and '-DCRYPTO_IN_SWIFTPM_FORCE_BUILD_API' in args
        row = {'argv': args, 'rawArraySHA256': hashlib.sha256(data[start-3:pos]).hexdigest()}
        if name in found:
            # SwiftBuild records the same driver invocation for compilation and
            # its requirements task. Only byte-identical repeats are reusable.
            assert found[name]['argv'] == row['argv'] and found[name]['rawArraySHA256'] == row['rawArraySHA256'], name+' has different original driver invocations'
            found[name]['identicalOccurrences'] += 1
        else:
            found[name] = row | {'identicalOccurrences': 1}
    assert set(found) == set(MODULES)
    return found

def qualify(generated, protobuf, crypto, asn1, root, base):
    immutable = {}; modes = {}
    def admitted_path(path):
        if path.is_relative_to(CACHE):
            assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
            candidate = PHYSICAL_CACHE/path.relative_to(CACHE)
            assert candidate.resolve() == candidate and path.resolve() == candidate and not candidate.is_symlink()
            return candidate
        assert path.resolve() == path and not path.is_symlink()
        return path
    def keep(path):
        assert path.is_file(), str(path)
        admitted_path(path)
        immutable[str(path)] = base.row(path)
        modes[str(path)] = stat.S_IMODE(path.stat().st_mode)
        return immutable[str(path)]

    # The producer's relocation is a separate fixed, caller-independent
    # custody boundary. Authenticate it before admitting an original stable
    # alias for any retained compiler input. Never relax base.pinned globally.
    for path in (COMPONENT_RECEIPT, CUSTODY_RECEIPT):
        base.pinned(path, PINS[path]); keep(path)
    component = json.loads(COMPONENT_RECEIPT.read_text())
    custody = json.loads(CUSTODY_RECEIPT.read_text())
    assert component['status'] == 'PASS' and component['compiled'] and component['sourceUnchanged']
    assert component['exitCode'] == 0 and component['ownedGroupAbsent']
    assert not component['cleanupRequired'] and not component['cleanupForcedKill']
    assert component['qualification']['newlyExecutedMethods'] == 1
    assert component['qualification']['retainedUnchangedMethods'] == 2
    assert component['dependencies']['swift-crypto'] == 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed'
    assert component['dependencies']['swift-asn1'] == '917b472dbe53ba699cbb0495f9a95a084bc6364d'
    assert custody['status'] == 'PASS_EXACT_OWNED_SWIFT_CACHE_RELOCATED_STABLE_PATH_RETAINED'
    assert custody['productsAndDependencyClosureUnchanged'] and custody['allExactPortableMetadataAndBytesRetained']
    assert custody['stableSymlinkInstalled'] and custody['source'] == str(CACHE)
    assert Path(custody['destination']) == PHYSICAL_CACHE
    assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
    assert CACHE.resolve() == PHYSICAL_CACHE and PHYSICAL_CACHE.resolve() == PHYSICAL_CACHE
    for path, pin in PINS.items():
        base.pinned(admitted_path(path), pin); keep(path)
    # These are exact retained dependency bytes, independently pinned during
    # the source-only producer review. A later Host-only relink is not claimed
    # as the original accepted Host product; dependency replacement must fail.
    for relative,pin in PRODUCER_OUTPUT_PINS.items():
        base.pinned(admitted_path(PRODUCTS/relative),pin);keep(PRODUCTS/relative)
    resolved = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Modules/PinkhaAnyHost/Package.resolved')
    base.pinned(resolved, 'db45ce18907a30d9b3c400463e7667190e16ac9e3e420d76e73b79ab8bc07337'); keep(resolved)
    assert crypto == CACHE/'checkouts/swift-crypto' and asn1 == CACHE/'checkouts/swift-asn1'
    assert protobuf == Path(generated['generatorCheckout'])

    # Both product closures must have used the same original compiler driver.
    assert (TOOLCHAIN/'swift').resolve() == (TOOLCHAIN/'swiftc').resolve()
    assert base.sha(TOOLCHAIN/'swift') == generated['swift']['sha256']
    assert re.search(r'Swift version 6\.4\.3\b', generated['swift']['version'])
    for name in ('swift', 'swiftc', 'swift-frontend', 'clang', 'clang++'):
        # These are the original compiler's explicitly observed driver links,
        # not aliases admitted for native source or dependency products.
        compiler = TOOLCHAIN/name
        immutable[str(compiler)] = base.row(compiler)
        modes[str(compiler)] = stat.S_IMODE(compiler.stat().st_mode)
    commands = original_driver_commands((BUILD_DATA/'task-store.msgpack').read_bytes())
    build_manifest = json.loads((BUILD_DATA/'manifest.json').read_text())
    selected_commands = {}; object_inputs = {}
    for name in OBJECTS:
        output = PRODUCTS/(name+'.o'); keep(output)
        matches = [(key, value) for key, value in build_manifest['commands'].items()
                   if value.get('tool') == 'shell' and value.get('outputs') == [str(output), '<Linked Binary '+str(output)+'>']]
        assert len(matches) == 1, (name, len(matches))
        key, command = matches[0]
        linker = 'clang++' if name == 'CCryptoBoringSSL' else 'clang'
        assert command['args'][0] == str(TOOLCHAIN/linker) and '-r' in command['args']
        assert command['args'][command['args'].index('-target')+1] == 'aarch64-unknown-linux-gnu'
        lists = [Path(arg[1:]) for arg in command['args'] if arg.startswith('@')]
        assert len(lists) == 1 and lists[0].is_relative_to(CACHE/'out/Intermediates.noindex/swift-crypto.build')
        keep(lists[0]); inputs = []
        for token in shlex.split(lists[0].read_text()):
            path = Path(token)
            assert path.is_absolute() and path.is_relative_to(CACHE/'out/Intermediates.noindex/swift-crypto.build')
            keep(path); inputs.append(str(path))
        assert 1 <= len(inputs) <= 1000
        selected_commands[key] = command; object_inputs[name] = inputs
    for name in MODULES:
        module = PRODUCTS/(name+'.swiftmodule')
        assert module.is_dir() and not module.is_symlink()
        for path in sorted(module.rglob('*')):
            if path.is_file(): keep(path)
        assert (module/'aarch64-unknown-linux-gnu.swiftmodule').is_file()
        for argument in commands[name]['argv']:
            if argument.startswith('@'):
                source_list = Path(argument[1:]); keep(source_list)
                sources = shlex.split(source_list.read_text())
                assert sources and all(Path(p).is_relative_to(crypto/'Sources'/name) for p in sources)
                for path in sources: keep(Path(path))
    module_maps = [crypto/'Sources'/name/'include/module.modulemap' for name in ('CCryptoBoringSSL', 'CCryptoBoringSSLShims')]
    for path in module_maps: keep(path)

    # The exact generator compile produced SwiftProtobuf once already. Reusing
    # that runtime module does not turn generated-message replay into native proof.
    products = Path(generated['generatorProductDirectory'])
    assert products.resolve().is_relative_to(Path(generated['buildRoot']).resolve())
    assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and row['stopReason'] is None for row in generated['commands'])
    protobuf_object = products/'SwiftProtobuf.o'
    protobuf_module = products/'SwiftProtobuf.swiftmodule'
    assert protobuf_module.is_dir() and not protobuf_module.is_symlink()
    keep(protobuf_object)
    for path in sorted(protobuf_module.rglob('*')):
        if path.is_file(): keep(path)
    assert (protobuf_module/'aarch64-unknown-linux-gnu.swiftmodule').is_file()
    for rel, want in generated['originalGeneratorSource'].items():
        assert base.row(protobuf/rel) == want, 'canonical generator source changed'
    generator_metadata = Path(generated['buildRoot'])/'swift-build/out/Intermediates.noindex/XCBuildData'
    manifests = sorted(generator_metadata.glob('*.xcbuilddata/manifest.json'))
    assert manifests, 'canonical SwiftBuild provenance missing'
    for path in manifests:
        keep(path)
        task_store = path.parent/'task-store.msgpack'
        assert task_store.is_file(); keep(task_store)

    compiler = ['-I', str(PRODUCTS), '-I', str(products)]
    for path in module_maps:
        compiler += ['-Xcc', '-fmodule-map-file='+str(path), '-Xcc', '-I'+str(path.parent)]
    links = [str(PRODUCTS/(name+'.o')) for name in OBJECTS]+[str(protobuf_object)]
    receipt = {'status': 'RETAINED_CANONICAL_DEPENDENCY_PRODUCTS_QUALIFIED_FOR_REUSE_ONLY',
               'componentProducerReceipt': str(COMPONENT_RECEIPT), 'componentProducerSHA256': PINS[COMPONENT_RECEIPT],
               'producerCustodyReceipt': str(CUSTODY_RECEIPT), 'producerCustodySHA256': PINS[CUSTODY_RECEIPT],
               'producerExactStableToPhysicalMapping': {str(CACHE):str(PHYSICAL_CACHE)},
               'originalProducerCompiledProducts': component['compiledProducts'],
               'originalProducerNewlyExecutedMethods': 1, 'originalProducerRetainedMethods': 2,
               'sourceOnlyASN1PinNoASN1CompiledProductClaim': True,
               'exactRetainedDependencyOutputPins': PRODUCER_OUTPUT_PINS,
               'toolchain': str(TOOLCHAIN), 'target': 'aarch64-unknown-linux-gnu',
               'cryptoSourceCommit': 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed',
               'asn1SourceCommit': '917b472dbe53ba699cbb0495f9a95a084bc6364d',
               'protobufSourceCommit': generated['generatorCommit'],
               'originalCompilerCommands': commands, 'originalLinkCommands': selected_commands,
               'originalLinkInputs': object_inputs, 'immutableFiles': immutable, 'modes': modes,
               'compilerImportFlags': compiler, 'linkObjects': links, 'additionalOriginalSystemLinkLibrary': 'stdc++',
               'dependencyCompilerInvocations': 0, 'acceptance': 'none; client XCTest remains mandatory'}
    base.save(root/'retained-dependency-products.json', receipt)
    return {'receipt': {'path': str(root/'retained-dependency-products.json'), **base.row(root/'retained-dependency-products.json')},
            'immutableInputs': immutable, 'inputModes': modes, 'compilerFlags': compiler,
            'linkObjects': links, 'swiftDriver': str(TOOLCHAIN/'swift'),
            'producerExactStableToPhysicalMapping': {str(CACHE):str(PHYSICAL_CACHE)}}

def validate_modes(reused):
    assert reused['producerExactStableToPhysicalMapping'] == {str(CACHE):str(PHYSICAL_CACHE)}
    assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
    assert CACHE.resolve() == PHYSICAL_CACHE and PHYSICAL_CACHE.resolve() == PHYSICAL_CACHE
    for path, mode in reused['inputModes'].items():
        assert stat.S_IMODE(Path(path).stat().st_mode) == mode, path+' original product mode changed'
