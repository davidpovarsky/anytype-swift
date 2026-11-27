#!/usr/bin/env python3
"""Offhost synthetic boundaries for compiler_inputs only; no driver import/run."""
from pathlib import Path
import ast
import hashlib
import json
import shlex
import shutil
import time

BASE = Path(__file__).resolve().parent
OUT = BASE / 'compiler-format-controls1'
PRIOR = BASE.parents[2] / 'wave2-properties-related-component/macro-repair1/actual-source2'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepared():
    source = (BASE / 'inputs/run_component.py').read_text()
    tree = ast.parse(source)
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('SOURCE_PINS', 'METHODS'):
                constants[node.targets[0].id] = ast.literal_eval(node.value)
    selected = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'compiler_inputs')
    namespace = {'Path': Path, 'json': json, 'shlex': shlex, 'sha': sha, **constants}
    exec(compile(ast.Module(body=[selected], type_ignores=[]), 'compiler_inputs-source-only', 'exec'), namespace)
    return source, namespace


def fixture(name, namespace):
    root = OUT / name
    component = root / 'component'
    shutil.copytree(BASE / 'inputs/component', component)
    namespace.update(ROOT=root, COMPONENT=component,
                     SWIFT=Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift'))
    project = root / 'build/out/Intermediates.noindex/HostTextReadbackProof.build/Debug-linux-aarch64'
    old = json.loads((PRIOR / 'root-actual-qualification.json').read_text())
    prototypes = {row['module']: shlex.split(row['commandWitnesses'][0]) for row in old['actualCompilerInvocations']}
    oldroot = '/var/lib/pinkha-wave2-properties-related-lifetime-source2-20261127'
    groups = {}
    for path in namespace['SOURCE_PINS']:
        parts = Path(path).parts
        if len(parts) == 3 and parts[0] in ('Sources', 'Tests') and path.endswith('.swift'):
            groups.setdefault(parts[1], set()).add(str(component / path))
    test = 'PinkhaAnyHostTests'
    runner = test + '_test_runner'
    anchor = project / (test + '-p.build/DerivedSources/test_anchor.swift')
    entry = project / (test + '-test-runner.build/DerivedSources/test_entry_point.swift')
    for path in (anchor, entry):
        path.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text('public func __test_anchor_PinkhaAnyHostTests() {}')
    # Real retained generator template, target-name replacement and clearly
    # synthetic identity comments. This is not a compiled/generated acceptance.
    entry.write_text((PRIOR / 'compiler/test_entry_point.swift').read_text().replace('PinkhaAnyUITests', test)
                     + '\n' + '\n'.join('// SYNTHETIC CONTROL ONLY: ' + method for method in namespace['METHODS']) + '\n')
    groups[test].add(str(anchor))
    groups[runner] = {str(entry)}
    log = ['Swift version 6.4.3 (swift-6.4.3-RELEASE)', 'Target: aarch64-unknown-linux-gnu']
    lists = {}
    for module, sources in sorted(groups.items()):
        if module == runner:
            prototype, stem, target = 'PinkhaAnyUITests_test_runner', test + '-test-runner', test + '-test-runner.build'
            old_name = 'PinkhaAnyUITests'
        elif module == test:
            prototype, stem, target = 'PinkhaAnyUITests', module, module + '-p.build'
            old_name = 'PinkhaAnyUITests'
        else:
            prototype, stem, target = 'TorahInspectorCore', module, module + '-t.build'
            old_name = 'TorahInspectorCore'
        object_root = project / target / 'Objects-normal/aarch64'
        object_root.mkdir(parents=True)
        source_list = object_root / (stem + '.SwiftFileList')
        source_list.write_text('\n'.join(shlex.quote(x) for x in sorted(sources)) + '\n')
        lists[module] = source_list
        output = {'': {'swift-dependencies': str(object_root / 'master.swiftdeps')}}
        for source in sorted(sources):
            obj = object_root / (Path(source).stem + '.o')
            obj.write_bytes(b'SYNTHETIC OBJECT, NOT A COMPILER OUTPUT\n' + source.encode())
            output[source] = {'object': str(obj)}
        (object_root / (stem + '-OutputFileMap.json')).write_text(json.dumps(output))
        modules = object_root / 'Modules'
        modules.mkdir()
        (modules / (module + '.swiftmodule')).write_bytes(b'SYNTHETIC MODULE, NOT A COMPILER OUTPUT')
        argv = [part.replace(oldroot, str(root)).replace('PropertiesSourceDocumentsComponent.build', 'HostTextReadbackProof.build')
                .replace(old_name, test if module == runner else module) for part in prototypes[prototype]]
        argv[argv.index('-working-directory') + 1] = str(component)
        log.append('    ' + shlex.join(argv))
    linklist = project / (test + '-p.build/Objects-normal/aarch64/' + test + '.LinkFileList')
    linklist.write_text(str(project / (test + '-p.build/Objects-normal/aarch64/NativeHostTests.o')) + '\n')
    log += ['    write-file ' + str(anchor), '    ' + shlex.join([
        'builtin-generateTestEntryPoint', '--output', str(entry), '--discover-tests',
        '--linker-file-list-format', 'unixShellQuotedNewlineSeparated', '--index-store-library-path',
        '/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/libIndexStore.so', '--linker-filelist', str(linklist),
        '--index-store', str(root / 'build/out'), '--index-unit-base-path', str(root / 'build/out/Intermediates.noindex'),
        '--test-anchor-module', test])]
    return root, '\n'.join(log), lists


def main():
    assert not OUT.exists(), 'Keep earlier controls; choose a separate successor attempt'
    OUT.mkdir()
    source, namespace = prepared()
    started = time.monotonic()
    results = []
    for name, mutation in [('actual-format-synthetic', None), ('unlisted-generated-source', 'extra'),
                           ('wrong-original-source-map', 'map'), ('wrong-actual-driver-target', 'target')]:
        root, log, lists = fixture(name, namespace)
        if mutation == 'extra':
            (root / 'build/unlisted.swift').write_text('// synthetic unexpected generated file\n')
        elif mutation == 'map':
            p = lists['PinkhaAnyHost'].with_name('PinkhaAnyHost-OutputFileMap.json')
            data = json.loads(p.read_text())
            key = next(key for key in data if key)
            data[str(root / 'foreign.swift')] = data.pop(key)
            p.write_text(json.dumps(data))
        elif mutation == 'target':
            log = log.replace('-target aarch64-unknown-linux-gnu', '-target x86_64-unknown-linux-gnu', 1)
        (root / 'synthetic-compiler.log').write_text(log)
        try:
            proof = namespace['compiler_inputs'](log)
        except AssertionError as error:
            if mutation is None:
                raise
            results.append({'name': name, 'status': 'PASS_EXPECTED_REJECTION', 'reason': str(error)})
        else:
            assert mutation is None, 'Invalid witness was accepted'
            assert len(proof) == 7 and sum(len(row['objects']) for row in proof) == 30
            assert sum(len(row['generatedInputs']) for row in proof) == 2
            (root / 'synthetic-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
            results.append({'name': name, 'status': 'PASS_SYNTHETIC_FORMAT_CONTROL'})
    receipt = {'schema': 'host2-compiler-format-portable-controls/v1', 'status': 'PASS_SYNTHETIC_CONTROLS_ONLY',
               'controllerSHA256': sha(source.encode()), 'controls': results, 'seconds': time.monotonic() - started,
               'originalObservedCompilerProofSHA256': '4d4aaa998116af4ea4a31ba0ad9714a3dd4f56bc195632314f0fe2cd9ad9673d',
               'selectedFunctionOnly': 'compiler_inputs', 'driverImported': False, 'driverExecuted': False,
               'SwiftCompilerCalls': 0, 'XCTestCalls': 0, 'HTTPServerCalls': 0, 'NativeCalls': 0, 'OracleCalls': 0,
               'syntheticObjectsAndModules': True, 'runtimeAdmission': False}
    (OUT / 'result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
