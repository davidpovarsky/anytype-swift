def compiler_inputs(log):
    assert 'Swift version 6.4.3 (swift-6.4.3-RELEASE)' in log
    assert 'aarch64-unknown-linux-gnu' in log
    # The retained single-target runs establish this backend's actual format.
    # Exact 6.4.3 SwiftPM source establishes one product/runner per test target.
    # Both must produce the fixed layout below; another backend is not admitted.
    build = ROOT / 'build'
    project = build / 'out/Intermediates.noindex/BookmarkCreationProof.build/Debug-linux-aarch64'
    products = build / 'out/Products/Debug-linux-aarch64'
    swiftc = str(SWIFT.with_name('swiftc'))
    clang = str(SWIFT.with_name('clang'))
    test_modules = ('PinkhaAnyHostTests', 'PinkhaAnyIntegrationTests')
    production_modules = ('TorahInspectorCore', 'PinkhaKit', 'PinkhaAnyEngine', 'PinkhaAnyIntegration', 'PinkhaAnyHost')
    runner_modules = {module + '_test_runner': module for module in test_modules}
    anchors = {module: project / (module + '-p.build/DerivedSources/test_anchor.swift') for module in test_modules}
    entries = {module: project / (module + '-test-runner.build/DerivedSources/test_entry_point.swift') for module in test_modules}

    def physical(path, maximum=16 * 1024**2):
        assert path.is_relative_to(ROOT) and path.resolve(strict=True) == path, str(path)
        assert path.is_file() and not path.is_symlink(), str(path)
        raw = path.read_bytes()
        assert 0 < len(raw) <= maximum, str(path)
        return raw

    def value(argv, flag):
        assert argv.count(flag) == 1, (flag, argv)
        return argv[argv.index(flag) + 1]

    groups = {}
    for relative in SOURCE_PINS:
        parts = Path(relative).parts
        if len(parts) == 3 and parts[0] in ('Sources', 'Tests') and relative.endswith('.swift'):
            groups.setdefault(parts[1], set()).add(str(COMPONENT / relative))
    assert sum(len(x) for x in groups.values()) == 84 and set(groups) == set(production_modules + test_modules)
    generated = {}
    for module in test_modules:
        groups[module].add(str(anchors[module]))
        groups[module + '_test_runner'] = {str(entries[module])}
        anchor_raw = physical(anchors[module])
        assert anchor_raw == ('public func __test_anchor_' + module + '() {}').encode('utf-8')
        entry_raw = physical(entries[module])
        entry_text = entry_raw.decode('utf-8')
        assert 'import ' + module in entry_text and '__test_anchor_' + module + '()' in entry_text
        assert 'struct __SwiftPMGeneratedTestRunner' in entry_text and 'XCTMain(__allDiscoveredTests())' in entry_text
        assert 'await Testing.__swiftPMEntryPoint() as Never' in entry_text
        # These are fixed byte expectations derived from retained actual generated
        # source. They are not compiled inputs or evidence of future execution.
        assert sha(entry_raw) == GENERATED_ENTRY_SHA256[module], module
        generated[str(anchors[module])] = anchor_raw
        generated[str(entries[module])] = entry_raw
    assert {str(p) for p in build.rglob('*.swift')} == set(generated), 'Unexpected generated Swift input'

    driver_lines = {}
    anchor_writes = {module: [] for module in test_modules}
    entry_generators = {module: [] for module in test_modules}
    link_commands = {}
    expected_products = {module: products / (module + '.o') for module in production_modules}
    expected_products.update({module: products / (module + '.so') for module in test_modules})
    expected_products.update({runner: products / (module + '-test-runner') for runner, module in runner_modules.items()})
    product_modules = {str(path): module for module, path in expected_products.items()}
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.startswith('builtin-SwiftDriver -- '):
            argv = shlex.split(stripped)
            assert argv[:3] == ['builtin-SwiftDriver', '--', swiftc]
            module = value(argv, '-module-name')
            assert module in groups and module not in driver_lines, 'Unexpected or duplicate Swift driver'
            driver_lines[module] = (line, argv)
        elif stripped.startswith('write-file '):
            argv = shlex.split(stripped)
            for module, anchor in anchors.items():
                if argv == ['write-file', str(anchor)]:
                    anchor_writes[module].append(line)
        elif stripped.startswith('builtin-generateTestEntryPoint '):
            argv = shlex.split(stripped)
            module = value(argv, '--test-anchor-module')
            assert module in test_modules
            assert value(argv, '--output') == str(entries[module])
            assert argv.count('--discover-tests') == 1
            assert value(argv, '--linker-file-list-format') == 'unixShellQuotedNewlineSeparated'
            assert value(argv, '--index-store-library-path') == str(SWIFT.parent.parent / 'lib/libIndexStore.so')
            assert value(argv, '--index-store') == str(build / 'out')
            assert value(argv, '--index-unit-base-path') == str(build / 'out/Intermediates.noindex')
            link_list = Path(value(argv, '--linker-filelist'))
            assert link_list == project / (module + '-p.build/Objects-normal/aarch64/' + module + '.LinkFileList')
            raw = physical(link_list)
            entry_generators[module].append({'actualCommandLine': line, 'linkerFileList': str(link_list),
                                            'linkerFileListSHA256': sha(raw), 'linkerFileListText': raw.decode('utf-8')})
        elif stripped.startswith((swiftc + ' ', clang + ' ')):
            argv = shlex.split(stripped)
            if '-o' not in argv:
                continue
            output = value(argv, '-o')
            if Path(output).is_relative_to(products):
                assert output in product_modules, 'Unexpected linked component product'
                module = product_modules[output]
                assert module not in link_commands, 'Duplicate product link command'
                link_commands[module] = (line, argv)
    assert set(driver_lines) == set(groups) == set(link_commands) and len(groups) == 9
    assert all(len(anchor_writes[module]) == len(entry_generators[module]) == 1 for module in test_modules)

    proof = []
    qualified_lists = set()
    qualified_link_lists = set()
    crypto_objects = [str(ROOT / 'retained-crypto-objects' / (name + '.o')) for name in
                      ('Crypto', 'CryptoBoringWrapper', 'CCryptoBoringSSL', 'CCryptoBoringSSLShims')]
    for module, expected in sorted(groups.items()):
        if module in runner_modules:
            stem = runner_modules[module] + '-test-runner'
            target = stem + '.build'
        else:
            stem, target = module, module + ('-p.build' if module in test_modules else '-t.build')
        object_root = project / target / 'Objects-normal/aarch64'
        source_list = object_root / (stem + '.SwiftFileList')
        source_list_raw = physical(source_list)
        sources = shlex.split(source_list_raw.decode('utf-8'))
        assert len(sources) == len(set(sources)) and set(sources) == expected, module
        qualified_lists.add(source_list)
        map_path = object_root / (stem + '-OutputFileMap.json')
        map_raw = physical(map_path)
        output_map = json.loads(map_raw)
        assert set(output_map) - {''} == expected, module
        line, argv = driver_lines[module]
        assert [arg for arg in argv if arg.startswith('@')] == ['@' + str(source_list)]
        assert value(argv, '-output-file-map') == str(map_path)
        assert value(argv, '-target') == 'aarch64-unknown-linux-gnu'
        assert value(argv, '-swift-version') == ('5' if module in runner_modules else '6')
        assert value(argv, '-working-directory') == str(ROOT)
        assert '-j2' in argv and '-c' in argv and '-enable-testing' in argv
        module_path = object_root / 'Modules' / (module + '.swiftmodule')
        assert value(argv, '-emit-module-path') == str(module_path)
        module_raw = physical(module_path)
        objects = []
        for source in sorted(expected):
            source_raw = physical(Path(source))
            if source in generated:
                assert source_raw == generated[source]
            else:
                assert sha(source_raw) == SOURCE_PINS[Path(source).relative_to(COMPONENT).as_posix()]
            object_path = Path(output_map[source]['object'])
            assert object_path.is_relative_to(object_root) and object_path.suffix == '.o'
            raw = physical(object_path)
            objects.append({'source': source, 'sourceSHA256': sha(source_raw), 'sourceBytes': len(source_raw),
                            'generatedSource': source in generated,
                            'object': str(object_path), 'objectSHA256': sha(raw), 'objectBytes': len(raw)})

        # Actual link closure is separate from compiler source-list custody.
        # Each of the two products/runners links its own fixed dependency tuple.
        module_object = object_root / 'Modules' / (module + '.o')
        module_object_raw = physical(module_object)
        expected_link = {row['object'] for row in objects} | {str(module_object)}
        if module in test_modules:
            linked_modules = production_modules if module == 'PinkhaAnyHostTests' else production_modules[:-1]
            expected_link |= {str(expected_products[name]) for name in linked_modules}
        link_list = object_root / (stem + '.LinkFileList')
        link_raw = physical(link_list)
        linked = shlex.split(link_raw.decode('utf-8'))
        assert len(linked) == len(set(linked)) and set(linked) == expected_link, module
        qualified_link_lists.add(link_list)
        linked_files = []
        for path in linked:
            raw = physical(Path(path), maximum=ALLOCATION_CAP if path in product_modules else 16 * 1024**2)
            linked_files.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
        link_line, link_argv = link_commands[module]
        assert value(link_argv, '-o') == str(expected_products[module])
        assert value(link_argv, '-target') == 'aarch64-unknown-linux-gnu'
        at_files = [arg for arg in link_argv if arg.startswith('@')]
        link_extras = []
        if module in production_modules:
            assert link_argv[0] == clang and '-r' in link_argv and '-nostdlib' in link_argv
            assert at_files == ['@' + str(link_list)]
            assert not [arg for arg in link_argv if arg.endswith(('.o', '.so')) and arg != str(expected_products[module])]
        else:
            autolink = object_root / (module + '-swiftbuild.autolink')
            autolink_raw = physical(autolink)
            assert link_argv[0] == swiftc
            assert at_files == ['@' + str(link_list), '@' + str(autolink)]
            assert link_argv.count('-lstdc++') == 1
            assert all(link_argv.count(path) == 1 for path in crypto_objects)
            object_tokens = [arg for arg in link_argv if arg.endswith(('.o', '.so')) and arg != str(expected_products[module])]
            relative_tokens = [arg for arg in object_tokens if not Path(arg).is_absolute()]
            if module in test_modules:
                assert relative_tokens == [module + '.so']
                soname = link_argv.index(module + '.so')
                assert link_argv[soname - 3:soname] == ['-Xlinker', '-soname', '-Xlinker']
            else:
                assert not relative_tokens
            explicit_objects = [arg for arg in object_tokens if Path(arg).is_absolute()]
            expected_explicit = crypto_objects[:]
            if module in runner_modules:
                assert '-emit-executable' in link_argv and '-emit-library' not in link_argv
                expected_explicit.append(str(expected_products[runner_modules[module]]))
            else:
                assert '-emit-library' in link_argv and '-emit-executable' not in link_argv
            assert len(explicit_objects) == len(expected_explicit) and set(explicit_objects) == set(expected_explicit)
            for path in expected_explicit:
                raw = physical(Path(path), maximum=ALLOCATION_CAP if path in product_modules else 16 * 1024**2)
                link_extras.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw)})
            link_extras.append({'path': str(autolink), 'bytes': len(autolink_raw),
                                'sha256': sha(autolink_raw), 'text': autolink_raw.decode('utf-8')})
        product_raw = physical(expected_products[module], maximum=ALLOCATION_CAP)
        proof.append({'module': module, 'sourceList': str(source_list),
                      'sourceListSHA256': sha(source_list_raw), 'sourceListText': source_list_raw.decode('utf-8'),
                      'outputFileMap': str(map_path), 'outputFileMapSHA256': sha(map_raw), 'outputFileMapValue': output_map,
                      'actualCompilerLines': [line], 'actualCompilerArgv': argv,
                      'emittedModule': str(module_path), 'emittedModuleSHA256': sha(module_raw), 'objects': objects,
                      'actualLink': {'commandLine': link_line, 'argv': link_argv,
                                     'linkFileList': str(link_list), 'linkFileListSHA256': sha(link_raw),
                                     'linkFileListText': link_raw.decode('utf-8'), 'linkedFiles': linked_files,
                                     'moduleObject': str(module_object), 'moduleObjectSHA256': sha(module_object_raw),
                                     'extraInputs': link_extras, 'product': str(expected_products[module]),
                                     'productBytes': len(product_raw), 'productSHA256': sha(product_raw)},
                      'generatedInputs': [{'path': source, 'bytes': len(raw), 'sha256': sha(raw), 'text': raw.decode('utf-8'),
                                           'actualGeneration': anchor_writes[module] if source == str(anchors.get(module))
                                           else entry_generators[runner_modules[module]]}
                                          for source, raw in generated.items() if source in expected]})
    assert set(build.rglob('*.SwiftFileList')) == qualified_lists, 'Unexpected compiler source list'
    assert set(build.rglob('*.LinkFileList')) == qualified_link_lists, 'Unexpected product linker list'
    return proof
