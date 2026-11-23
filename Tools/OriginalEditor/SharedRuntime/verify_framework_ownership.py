"""Verify real shared implementations after the unchanged original native acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import sys
import subprocess
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from framework_profile import source_observation, sha256, blob
from pbx_source import require
from run_framework_acceptance import command, write

RUNTIME = 'OriginalEditorSharedFirebase'
EDITOR = 'AnytypeOriginalEditor'
FIREBASE_CLASSES = ['FIRApp', 'FIRInstallations', 'FIRMessaging', 'FBLPromise', 'GDTCORTransport']
HOST_PRODUCTS = [
    'HanlinHostContracts', 'HanlinAgentCore', 'HanlinChatCore', 'HanlinScriptUI',
    'HanlinChatUI', 'HanlinPresentationKit', 'HanlinRichUI', 'HanlinPlatformContracts',
    'FloatingPanel', 'TorahInspectorCore', 'TorahInspectorUI', 'ZIPFoundation',
]
FIREBASE = re.compile(
    r'^_(?:(?:OBJC_(?:META)?CLASS_\$_)?(?:FIR|Firebase|FBL|GUL|GDT)|pb_|'
    r'\$s20FirebaseCoreInternal|\$s8Promises)'
)
EDITOR_C = re.compile(r'^_(?:OBJC_(?:META)?CLASS_\$_MT|cmark_)')


def verify_definitions(symbols):
    """A decision over observed nm -gUj output; this alone gives no native credit."""
    require(RUNTIME in symbols and EDITOR in symbols, 'Missing actual shared or original editor image')
    owners = {}
    module_symbols = {}
    for module in HOST_PRODUCTS:
        prefix = '_$s' + str(len(module)) + module
        module_symbols[module] = {s for values in symbols.values() for s in values if s.startswith(prefix)}
        require(module_symbols[module], 'Shared Host module has no exported implementation: ' + module)
    selected = {s for values in symbols.values() for s in values if FIREBASE.match(s) or EDITOR_C.match(s)}
    selected |= set().union(*module_symbols.values())
    for symbol in sorted(selected):
        images = sorted(image for image, values in symbols.items() if symbol in values)
        expected = RUNTIME if FIREBASE.match(symbol) else EDITOR
        require(images == [expected], 'Shared definition has the wrong/multiple providers: ' + symbol + ': ' + repr(images))
        owners[symbol] = images[0]
    required = {'_OBJC_CLASS_$_' + c for c in FIREBASE_CLASSES}
    require(required <= set(owners), 'Shared Firebase implementation classes are missing')
    require({'_OBJC_CLASS_$_MTMathUILabel', '_cmark_parse_document'} <= set(owners),
            'Original iosMath/cmark implementations are missing')
    return {'selected_definition_count': len(owners), 'owners': owners,
            'host_module_definition_counts': {k: len(v) for k, v in module_symbols.items()}}


# Full source/resource closures for the precise CocoaPods libraries that the Host
# will route to this provider. The native Host checks its actual Pod compile
# memberships against these exact Git-bound bytes before removing a link input.
DEPENDENCY_SOURCE_ROOTS = {
    'firebase-ios-sdk': ['FirebaseCore', 'FirebaseCoreInternal', 'FirebaseInstallations'],
    'googleutilities': ['GoogleUtilities', 'third_party'],
    'googledatatransport': ['GoogleDataTransport'],
    'promises': ['Sources'],
    'nanopb': ['pb.h', 'pb_common.c', 'pb_common.h', 'pb_decode.c', 'pb_decode.h',
               'pb_encode.c', 'pb_encode.h', 'spm_resources'],
}


def dependency_source_inventory(checkouts, contract):
    observed = {}
    for directory in sorted(checkouts.iterdir()):
        if not directory.is_dir() or not (directory / '.git').exists():
            continue
        revision = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'],
                                           text=True).strip()
        identities = [k for k, v in contract['dependencies'].items() if v['revision'] == revision]
        if not identities:
            continue
        require(len(identities) == 1 and identities[0] not in observed,
                'Ambiguous exact shared dependency checkout')
        identity = identities[0]
        rows = subprocess.check_output(['git', '-C', str(directory), 'ls-tree', '-rz',
                                        '--full-tree', revision, '--', *DEPENDENCY_SOURCE_ROOTS[identity]])
        files = {}
        for row in rows.split(b'\0'):
            if not row:
                continue
            metadata, path_bytes = row.split(b'\t', 1)
            mode, kind, object_id = metadata.decode().split()
            name = path_bytes.decode()
            require(kind == 'blob' and mode in {'100644', '100755', '120000'}
                    and name not in files, 'Unexpected shared source entry')
            path = directory / name
            require(path.resolve(strict=True).is_relative_to(directory), 'Escaping shared source input')
            if mode == '120000':
                require(path.is_symlink() and blob(os.fsencode(os.readlink(path))) == object_id,
                        'Original shared source alias differs')
                resolved = path.resolve(strict=True).relative_to(directory).as_posix()
                target_blob = subprocess.check_output(['git', '-C', str(directory), 'rev-parse',
                                                       revision + ':' + resolved], text=True).strip()
                raw = path.read_bytes()
                require(blob(raw) == target_blob, 'Original shared alias target bytes differ')
                alias = {'literal_alias': os.readlink(path), 'target': resolved, 'target_blob': target_blob}
            else:
                require(path.is_file() and not path.is_symlink(), 'Missing shared source input')
                raw = path.read_bytes()
                require(blob(raw) == object_id, 'Original shared source bytes differ')
                alias = {}
            files[name] = {'git_blob': object_id, 'git_mode': mode, 'bytes': len(raw),
                           'sha256': hashlib.sha256(raw).hexdigest(), **alias}
        require(files and len(files) < 10000, 'Missing or excessive shared source closure')
        observed[identity] = {'revision': revision, 'roots': DEPENDENCY_SOURCE_ROOTS[identity], 'files': files}
    require(set(observed) == set(contract['dependencies']), 'Incomplete shared dependency source closure')
    return observed


def execute(args, receipt):
    root, evidence, work = args.root.resolve(), args.evidence.resolve(), args.work.resolve()
    require(evidence.is_relative_to(root / 'build') and work.is_relative_to(root / 'build'),
            'Unowned producer paths')
    source = source_observation(root)
    distribution = work / 'distribution'
    qualification_path = distribution / 'QUALIFICATION.json'
    original_bytes = qualification_path.read_bytes()
    qualification = json.loads(original_bytes)
    require(qualification.get('status') == 'ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS'
            and qualification.get('phase') == 'COMPLETE'
            and qualification.get('original_framework_build') == 'PASS'
            and qualification.get('external_consumer_build') == 'PASS'
            and qualification.get('source_sha') == source['head_sha']
            and str(qualification.get('run_id')) == source['run_id']
            and str(qualification.get('run_attempt')) == source['run_attempt']
            and len(qualification.get('verified_runtime_observations', [])) == 2,
            'Original native producer/consumer/resources have not qualified this source')
    require('shared_runtime_ownership' not in qualification, 'Refusing a prior ownership receipt')
    contract_path = root / 'Tools/OriginalEditor/SharedRuntime/dependencies.json'
    contract = json.loads(contract_path.read_text())
    lock_path = distribution / 'SourceProvenance/Original-Package.resolved'
    pins = {p['identity']: p['state'] for p in json.loads(lock_path.read_text())['pins']}
    for identity, expected in contract['dependencies'].items():
        require(pins.get(identity) == {'revision': expected['revision'], 'version': expected['version']},
                'Shared runtime source differs from Host dependency contract: ' + identity)
    binaries, symbols = {}, {}
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
        raw = command(['xcrun', 'nm', '-gjU', str(binary)], root, evidence,
                      'shared-provider-definitions-' + name, 60)
        symbols[name] = set(raw.splitlines())
    consumer = work / 'consumer-derived/Build/Products/Debug-iphonesimulator/OriginalEditorConsumer.app'
    require(consumer.is_dir(), 'Actual independently built original consumer is missing')
    info = plistlib.loads((consumer / 'Info.plist').read_bytes())
    main = consumer / info['CFBundleExecutable']
    consumer_images = [main, *sorted(consumer.glob('*.dylib'))]
    for number, binary in enumerate(consumer_images):
        require(binary.is_file() and not binary.is_symlink(), 'Consumer image is absent or aliased')
        key = 'external-consumer-' + str(number)
        binaries[key] = {'path': str(binary.relative_to(work)), 'sha256': sha256(binary)}
        symbols[key] = set(command(['xcrun', 'nm', '-gjU', str(binary)], root, evidence,
                                   'shared-provider-definitions-' + key, 60).splitlines())
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
        binary_identity=binaries, shared_host_products=HOST_PRODUCTS, shared_module_declarations=modules,
        definition_count=definitions['selected_definition_count'],
        selected_definitions_sha256=sha256(evidence / 'shared-provider-selected-definitions.json'),
        host_module_definition_counts=definitions['host_module_definition_counts'],
        hanlin_source_revision=hanlin['revision'], hanlin_snapshot_sha256=sha256(hanlin_path),
        hanlin_package_files=hanlin['files'],
        resolved_package_states=pins,
        shared_dependency_sources=dependency_source_inventory(
            work / 'producer-derived-preserved/SourcePackages/checkouts', contract),
        shared_swift_ai_sdk_revision=pins['swift-ai-sdk']['revision'],
        host_semantic_equality_required=True, stageb_qualified=False,
    )
    require(source_observation(root) == source, 'Source changed during shared ownership verification')
    write(evidence / 'shared-runtime-ownership.json', receipt)
    qualification['shared_runtime_ownership'] = receipt
    write(qualification_path, qualification)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    receipt = {'schema': 1, 'status': 'FAIL', 'stageb_qualified': False}
    try:
        execute(args, receipt)
        return 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
        return 1
    finally:
        write(args.evidence / 'shared-runtime-ownership.json', receipt)


if __name__ == '__main__':
    raise SystemExit(main())
