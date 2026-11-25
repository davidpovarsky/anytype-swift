"""Observe single implementation ownership in each actual Release image set."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
from framework_profile import source_observation, sha256
from pbx_source import require
from release_contract import write
from release_process import command
from release_symbols import complete_definitions
from verify_framework_ownership import (RUNTIME, EDITOR, HOST_PRODUCTS, verify_definitions,
    dependency_source_inventory)


def verify_ownership(root, evidence, work, qualification, source, before, platform_name, *, original_derived=None):
    receipt = {'schema': 1, 'status': 'FAIL', 'stageb_qualified': False}
    distribution = work / 'distribution'
    original_derived = work / 'producer-derived' if original_derived is None else Path(original_derived)
    roots = None
    if original_derived.parent != work:
        from release_continuation_roots import admit_roots
        collection = json.loads((evidence / 'compiler-symbolgraph-collection.json').read_text())
        roots = admit_roots(original_derived, distribution, collection, source, quarantined=True)
    original_bytes = (json.dumps(qualification, indent=2, sort_keys=True) + '\n').encode()
    contract_path = root / 'Tools/OriginalEditor/SharedRuntime/dependencies.json'
    contract = json.loads(contract_path.read_text())
    lock_path = distribution / 'SourceProvenance/Original-Package.resolved'
    pins = {p['identity']: p['state'] for p in json.loads(lock_path.read_text())['pins']}
    for identity, expected in contract['dependencies'].items():
        require(pins.get(identity) == {'revision': expected['revision'], 'version': expected['version']},
                'Shared runtime source differs from Host dependency contract: ' + identity)
    binaries, symbols, extractions = {}, {}, {}
    for framework in sorted((distribution / 'Frameworks').glob('*.framework')):
        info = plistlib.loads((framework / 'Info.plist').read_bytes())
        name = info['CFBundleExecutable']
        require(isinstance(name, str) and Path(name).name == name, 'Invalid framework executable')
        binary = framework / name
        header = command(['xcrun', 'otool', '-hv', str(binary)], root, evidence,
                         'shared-provider-header-' + name, 30)
        if not re.search(r'\bDYLIB\b', header):
            continue
        require(name not in binaries and binary.is_file() and not binary.is_symlink(), 'Aliased or duplicate framework')
        binaries[name] = {'path': str(binary.relative_to(distribution)), 'sha256': sha256(binary)}
        if name == 'ProtobufMessages' and 'NLIST_OUTOFSYNC_WITH_DYLDINFO' in header:
            require('NO_REEXPORTED_DYLIBS' in header, 'Unreviewed Protobuf re-export closure')
            symbols[name], extractions[name] = complete_definitions(
                binary, root, evidence, 'shared-provider-definitions-' + name)
        else:
            raw = command(['xcrun', 'nm', '-gjU', str(binary)], root, evidence,
                          'shared-provider-definitions-' + name, 600)
            symbols[name] = set(raw.splitlines())
    consumer = work / ('consumer-derived/Build/Products/Release-' + platform_name + '/OriginalEditorConsumer.app')
    require(consumer.is_dir(), 'Actual independently built original consumer is missing')
    info = plistlib.loads((consumer / 'Info.plist').read_bytes())
    main = consumer / info['CFBundleExecutable']
    consumer_images = [main, *sorted(consumer.glob('*.dylib'))]
    for number, binary in enumerate(consumer_images):
        require(binary.is_file() and not binary.is_symlink(), 'Consumer image is absent or aliased')
        key = 'external-consumer-' + str(number)
        binaries[key] = {'path': str(binary.relative_to(work)), 'sha256': sha256(binary)}
        symbols[key] = set(command(['xcrun', 'nm', '-gjU', str(binary)], root, evidence,
                                   'shared-provider-definitions-' + key, 600).splitlines())
    definitions = verify_definitions(symbols)
    loads = command(['xcrun', 'otool', '-L', str(distribution / 'Frameworks' / (EDITOR + '.framework') / EDITOR)],
                    root, evidence, 'shared-provider-original-loads', 30)
    require('@rpath/' + RUNTIME + '.framework/' + RUNTIME in loads,
            'Original framework does not load the shared runtime')
    modules = {}
    for module in HOST_PRODUCTS:
        directory = distribution / 'Modules' / (module + '.swiftmodule')
        require(directory.is_dir() and not directory.is_symlink(), 'Missing shared Host module declarations: ' + module)
        files = {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        require(files and any(p.endswith('.swiftmodule') for p in files),
                'Missing actual binary Swift module: ' + module)
        modules[module] = files
    hanlin_path = evidence / 'original-hanlin-snapshot.json'
    hanlin = json.loads(hanlin_path.read_text())
    expected_hanlin = json.loads((root / 'Tools/Hanlin/source.json').read_text())
    require(hanlin['revision'] == expected_hanlin['revision']
            and pins['swift-ai-sdk']['revision'] == expected_hanlin['swiftAISDKRevision'],
            'Compiled shared Hanlin closure does not match the current producer source contract')
    write(evidence / 'shared-provider-selected-definitions.json', definitions)
    receipt.update(
        status='PASS_OBSERVED_SINGLE_SHARED_IMPLEMENTATIONS',
        producer={'source_sha': source['head_sha'], 'run_id': source['run_id'],
                  'run_attempt': source['run_attempt']},
        original_qualification_sha256=hashlib.sha256(original_bytes).hexdigest(),
        dependency_contract_sha256=sha256(contract_path), original_package_lock_sha256=sha256(lock_path),
        root_dependency_revisions={k: pins[k] for k in contract['dependencies']},
        binary_identity=binaries, complete_symbol_extractions=extractions,
        shared_host_products=HOST_PRODUCTS, shared_module_declarations=modules,
        definition_count=definitions['selected_definition_count'],
        selected_definitions_sha256=sha256(evidence / 'shared-provider-selected-definitions.json'),
        host_module_definition_counts=definitions['host_module_definition_counts'],
        hanlin_source_revision=hanlin['revision'], hanlin_snapshot_sha256=sha256(hanlin_path),
        hanlin_package_files=hanlin['files'],
        resolved_package_states=pins,
        shared_dependency_sources=dependency_source_inventory(
            work / 'producer-derived-preserved/SourcePackages/checkouts', contract,
            original_checkouts=original_derived / 'SourcePackages/checkouts'),
        shared_swift_ai_sdk_revision=pins['swift-ai-sdk']['revision'],
        host_semantic_equality_required=True, stageb_qualified=False,
    )
    if roots is not None:
        receipt['compiler_root_continuation'] = roots
    require(source_observation(root) == before, 'Source changed during Release shared ownership verification')
    write(evidence / 'shared-runtime-ownership.json', receipt)
    return receipt
