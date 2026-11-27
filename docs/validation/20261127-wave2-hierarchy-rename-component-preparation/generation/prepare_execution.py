#!/usr/bin/env python3
"""Assemble a source-only finite derivative; never import or execute a runner."""
from pathlib import Path
import ast
import base64
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
OLD = WORK / 'wave2-property-unicode-audit/component-preparation/execution-preparation'
OUT = HERE / 'execution-preparation'
INPUTS = OUT / 'inputs'
ROOT = '/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127'
OLD_ROOT = '/mnt/development/projects/evidence/pinkha-wave2-property-text-readback-20261127'
PRODUCT = '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'
METHODS = (
    'canonicallyEquivalentRequestedRenameReachesTheOriginalStore',
    'canonicallyEquivalentStaleExpectedTitleRefusesBeforeDispatch',
    'canonicallyEquivalentSuccessfulReadbackCannotCertifyRename',
    'canonicallyEquivalentReadbackPreservesTheOriginalWriteError',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Frozen output differs: ' + str(path)
    else:
        path.write_bytes(raw)


def emit(path, value):
    save(path, (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode())


def span(text, node):
    lines = text.splitlines(keepends=True)
    return ''.join(lines[node.lineno-1:node.end_lineno])


def inverse(old, new):
    old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
    edits = []
    for tag, a, b, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        edits.append({'originalByteOffset': sum(map(len, old_lines[:a])),
                      'candidateByteOffset': sum(map(len, new_lines[:c])),
                      'oldBase64': base64.b64encode(b''.join(old_lines[a:b])).decode(),
                      'newBase64': base64.b64encode(b''.join(new_lines[c:d])).decode()})
    restored = new
    for row in reversed(edits):
        start = row['candidateByteOffset']; replacement = base64.b64decode(row['newBase64'])
        assert restored[start:start+len(replacement)] == replacement
        restored = restored[:start] + base64.b64decode(row['oldBase64']) + restored[start+len(replacement):]
    assert restored == old
    forward = old
    for row in reversed(edits):
        start = row['originalByteOffset']; original = base64.b64decode(row['oldBase64'])
        assert forward[start:start+len(original)] == original
        forward = forward[:start] + base64.b64decode(row['newBase64']) + forward[start+len(original):]
    assert forward == new
    return {'originalBytes': len(old), 'originalSHA256': sha(old),
            'candidateBytes': len(new), 'candidateSHA256': sha(new),
            'bidirectionalExactBytes': True, 'hunks': edits}


intake = json.loads((HERE / 'whole-source-intake.json').read_text())
assert intake['publishedProductCommit'] == PRODUCT and len(intake['files']) == 55
source_pins = {}
for row in intake['files']:
    raw = Path(row['localSource']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    save(INPUTS / 'component' / row['path'], raw)
    source_pins[row['path']] = row['sha256']

old_package = (OLD / 'inputs/component/Package.swift').read_bytes()
assert sha(old_package) == '25f975e6448feb61044163468c676b0d2fa686e02af3481261a53e11fd905f1b'
package = old_package.decode().replace(OLD_ROOT, ROOT).replace('PropertyTextReadbackProof', 'HierarchyRawTitleProof')
host_target = [line for line in package.splitlines(keepends=True) if '.target(name: "PinkhaAnyHost",' in line]
assert len(host_target) == 1
package = package.replace(host_target[0], '').replace('.testTarget(name: "PinkhaAnyHostTests", dependencies: ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost"]',
                                                     '.testTarget(name: "PinkhaAnyIntegrationTests", dependencies: ["PinkhaAnyIntegration"]')
assert package.count('.target(name:') == 4 and package.count('.testTarget(name:') == 1
assert 'PinkhaAnyHost' not in package
package_raw = package.encode()
save(INPUTS / 'component/Package.swift', package_raw)
source_pins['Package.swift'] = sha(package_raw)
source_pins = dict(sorted(source_pins.items()))

for name, expected in (
    ('owned_process.py', '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'),
    ('owned-process-provenance.json', '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'),
    ('retained-crypto-closure.json', '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'),
):
    raw = (OLD / 'inputs' / name).read_bytes()
    assert sha(raw) == expected
    save(INPUTS / name, raw)

closure = dict(intake)
closure.update(schema='pinkha-hierarchy-rename-component-source-closure/v1',
               sourceIntake=pin(HERE / 'whole-source-intake.json'),
               package={'path': 'component/Package.swift', 'bytes': len(package_raw), 'sha256': sha(package_raw)},
               newDeclaredMethods=4, newDeclaredArgumentCases=8,
               sourceMethodNames=list(METHODS), selectedSuiteFilter='AnyHierarchyRawTitleTests',
               sourceMethodNamesAreNotClaimedCompiledEnumeration=True)
emit(INPUTS / 'whole-source-closure.json', closure)
closure_sha = sha((INPUTS / 'whole-source-closure.json').read_bytes())

g04 = WORK / 'wave2-reader-audit/component/actual-run/attempt1'
entry_original = (g04 / 'compiler-filelists/test_entry_point.swift').read_bytes()
assert sha(entry_original) == '2bd3ed107dee6b78c0927cc9602bd81533bc11a1c1b03c36ba827a3d9b669c65'
assert entry_original.count(b'TorahInspectorUITests') == 2
entry_expected = entry_original.replace(b'TorahInspectorUITests', b'PinkhaAnyIntegrationTests')
assert sha(entry_expected) == 'ef1ea588c48abfb9df451d79abb95237c2380da8b15cc97422bbfcccd532993b'
save(OUT / 'expected-generated-test-entry-point.swift', entry_expected)
emit(OUT / 'generated-source-format-proof.json', {
    'schema': 'pinkha-hierarchy-rename-generated-source-expectation/v1',
    'actualOriginalEntryPoint': pin(g04 / 'compiler-filelists/test_entry_point.swift'),
    'actualOriginalStdout': pin(g04 / 'stdout.original.log'),
    'actualOriginalReceipt': pin(g04 / 'receipt.json'),
    'sourceOnlyExpectedEntryPoint': pin(OUT / 'expected-generated-test-entry-point.swift'),
    'exactInverse': inverse(entry_original, entry_expected),
    'onlyChange': 'Two original test-module spellings. Exact empty XCTest discovery and public Testing.__swiftPMEntryPoint remain unchanged.',
    'newGeneratedSourceObserved': False, 'actualCompilerWitnessRequired': True,
    'unknownActualFormat': 'Fail and retain actual evidence; no fallback or automatic qualifier widening.'})

old_raw = (OLD / 'inputs/run_component.py').read_bytes()
assert sha(old_raw) == '66f09e18e07cca8a2056d0c8b51ffa318433f28bf9cb7f255f7a0c9bd9db9ea8'
old = old_raw.decode()
candidate = old
doc = ast.get_docstring(ast.parse(old), clean=False)
new_doc = '''One source-bound hierarchy rename component, four methods/eight argument cases.

Preparation is inert by default and does not grant a coordinated runtime slot.
All54 production bodies and the full27-method Integration test file are exact.
Only AnyHierarchyRawTitleTests is selected; old23 tests and Host2 are not replayed.
This is controlled-store Integration coverage, not HTTP/Native/Apple/account UI.
'''
assert candidate.count(doc) == 1
candidate = candidate.replace(doc, new_doc)
candidate = candidate.replace(OLD_ROOT, ROOT)
candidate = candidate.replace("PRODUCT_COMMIT = '937a8167700481b71c3c2eeb8771634d2c6bbc4f'", "PRODUCT_COMMIT = '" + PRODUCT + "'")
candidate = candidate.replace("SOURCE_CLOSURE_SHA = 'd70f949ee299e2b06d0120056cadae2b86e9e8aa84f23c564ed291140407bba4'", "SOURCE_CLOSURE_SHA = '" + closure_sha + "'")
candidate, count = re.subn(r'^SOURCE_PINS = .*$', 'SOURCE_PINS = ' + repr(source_pins), candidate, flags=re.M)
assert count == 1
candidate, count = re.subn(r'^METHODS = .*$', 'METHODS = ' + repr(METHODS), candidate, flags=re.M)
assert count == 1
candidate = candidate.replace("SUITE = 'NativePropertyStoreTests'", "SUITE = 'AnyHierarchyRawTitleTests'")
candidate = candidate.replace("TEST_FILTER = '(' + '|'.join(METHODS) + ')'", "TEST_FILTER = SUITE")

functions = {node.name: node for node in ast.parse(old).body if isinstance(node, ast.FunctionDef)}
compiler = span(old, functions['compiler_inputs'])
new_compiler = compiler.replace('PropertyTextReadbackProof.build', 'HierarchyRawTitleProof.build')
new_compiler = new_compiler.replace("test_module = 'PinkhaAnyHostTests'", "test_module = 'PinkhaAnyIntegrationTests'")
new_compiler = new_compiler.replace('== 78 and len(groups) == 6', '== 55 and len(groups) == 5')
new_compiler = new_compiler.replace('PinkhaAnyHostTests', 'PinkhaAnyIntegrationTests')
old_discovery = "    assert all(method in entry_text for method in METHODS), 'Actual generated XCTest discovery omits selected method'\n"
new_discovery = """    # The retained actual G04 run uses the same Swift6.4.3 Swift Testing entry
    # point with empty XCTest discovery. Only its two module-name literals vary.
    assert sha(entry_raw) == 'ef1ea588c48abfb9df451d79abb95237c2380da8b15cc97422bbfcccd532993b'
    assert 'await Testing.__swiftPMEntryPoint() as Never' in entry_text
"""
assert new_compiler.count(old_discovery) == 1
new_compiler = new_compiler.replace(old_discovery, new_discovery)
assert candidate.count(compiler) == 1
candidate = candidate.replace(compiler, new_compiler)

old_result = span(old, functions['xctest_result'])
new_result = (HERE / 'swift_testing_result.fragment.py').read_text().rstrip('\n') + '\n'
assert candidate.count(old_result) == 1
candidate = candidate.replace(old_result, new_result)

candidate = candidate.replace("    assert ROOT.is_dir() and ROOT.resolve(strict=True) == ROOT\n", "    assert ROOT.is_dir() and ROOT.resolve(strict=True) == ROOT\n    assert Path.cwd().resolve(strict=True) == ROOT and os.environ.get('PWD') == str(ROOT), 'Fixed ROOT launch cwd/PWD required'\n")
candidate = candidate.replace("'pinkha-property-text-readback-component/v1'", "'pinkha-hierarchy-raw-title-component/v1'")
candidate = candidate.replace("PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0',\n", "PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0', PWD=str(ROOT),\n")
candidate = candidate.replace("'PYTHONDONTWRITEBYTECODE', 'GIT_TERMINAL_PROMPT', 'PATH')", "'PYTHONDONTWRITEBYTECODE', 'GIT_TERMINAL_PROMPT', 'PWD', 'PATH')")
candidate = candidate.replace('Owned Property command exceeded 300 seconds', 'Owned hierarchy rename command exceeded 300 seconds')
candidate = candidate.replace("receipt['testResult'] = xctest_result(log)", "receipt['testResult'] = swift_testing_result(log)")
candidate = candidate.replace("'PASS_FOUR_XCTEST_METHODS_PROPERTY_COMPONENT_ONLY'", "'PASS_FOUR_SWIFT_TESTING_METHODS_EIGHT_ARGUMENT_CASES_HIERARCHY_COMPONENT_ONLY'")
assert 'NativePropertyStoreTests' not in candidate and 'PinkhaAnyHost' not in candidate
assert 'testStringReadback' not in candidate and OLD_ROOT not in candidate
ast.parse(candidate)
new_raw = candidate.encode()
save(INPUTS / 'run_component.py', new_raw)

new_functions = {node.name: span(candidate, node) for node in ast.parse(candidate).body if isinstance(node, ast.FunctionDef)}
unchanged = [name for name, node in functions.items() if name in new_functions and span(old, node) == new_functions[name]]
assert unchanged == ['sha', 'write', 'pinned', 'source_inventory', 'cleanup_custody', 'allocated_bytes',
                     'resource_sample', 'require_budget', 'private_directory', 'copy_crypto', 'verify_crypto']
proof = {'schema': 'pinkha-hierarchy-rename-component-controller-derivative/v1',
         'status': 'LOCAL_BYTE_INVERSE_AND_PYTHON_AST_ONLY', 'runtimeInvocations': 0,
         'originalRunner': pin(OLD / 'inputs/run_component.py'),
         'candidateRunner': pin(INPUTS / 'run_component.py'),
         'runnerInverse': inverse(old_raw, new_raw),
         'originalPackage': pin(OLD / 'inputs/component/Package.swift'),
         'candidatePackage': pin(INPUTS / 'component/Package.swift'),
         'packageInverse': inverse(old_package, package_raw),
         'unchangedFunctionBodies': [{'name': name, 'sha256': sha(new_functions[name].encode())} for name in unchanged],
         'changedFunctionScopes': {'compiler_inputs': '55 whole originals + two named actual generated inputs, six modules/FileLists; same complete original physical/maps/driver/object checks; exact G04 Swift Testing generator spelling.',
                                   'xctest_result -> swift_testing_result': 'Only four selected methods, eight unique paired argument events, one suite/summary. Zero/old/unrecognized execution refuses.',
                                   'main': 'Fixed source/suite/receipt namespace, exact ROOT cwd/PWD precondition and logged PWD; unchanged one-child/lifecycle/budget/first-error/finalization bodies.'},
         'originalG04Runner': pin(WORK / 'wave2-reader-audit/component/run_component.py'),
         'actualG04EventFormat': pin(g04 / 'stdout.original.log'),
         'declaredMethods': list(METHODS), 'declaredArgumentValues': ['latin', 'hebrew'],
         'old23MethodsSelected': 0, 'actualNewCompilerOrTestEvidence': None}
emit(OUT / 'controller-derivative.json', proof)
save(OUT / 'controller-derivative.patch', ''.join(difflib.unified_diff(old.splitlines(keepends=True), candidate.splitlines(keepends=True),
      fromfile='Property4/run_component.py', tofile='HierarchyRename/run_component.py')).encode())
save(OUT / 'package-derivative.patch', ''.join(difflib.unified_diff(old_package.decode().splitlines(keepends=True), package.splitlines(keepends=True),
      fromfile='Property4/Package.swift', tofile='HierarchyRename/Package.swift')).encode())

files = [{**pin(path), 'path': path.relative_to(INPUTS).as_posix()} for path in sorted(INPUTS.rglob('*')) if path.is_file()]
assert len(files) == 61
packet = {'schema': 'pinkha-hierarchy-rename-component-input-packet/v1',
          'status': 'PREPARED_NOT_ADMITTED_OR_RUN', 'productCommit': PRODUCT,
          'futureFixedRoot': ROOT, 'futureLaunch': {'cwd': ROOT, 'environment': {'PWD': ROOT, 'PYTHONDONTWRITEBYTECODE': '1'},
              'argv': ['/usr/bin/python3', '-B', ROOT + '/inputs/run_component.py', '--execute-reviewed-candidate'],
              'requiresSeparateReviewedStagingAndOwnerSlot': True},
          'fileCount': len(files), 'bytes': sum(x['bytes'] for x in files), 'files': files,
          'wholeProductionFiles': 54, 'wholeTestFiles': 1, 'fullSourceTestMethods': 27,
          'sourceBodiesChangedForComponent': 0, 'selectedSuiteFilter': 'AnyHierarchyRawTitleTests',
          'selectedSourceMethodNames': list(METHODS), 'declaredArgumentCases': 8,
          'compiledEnumeration': None, 'actualResult': None, 'runtimeReady': False, 'runtimeSlotGranted': False,
          'old23MethodsSelected': 0, 'oldProperty4MethodsSelected': 0, 'oldHost2MethodsSelected': 0,
          'proposedResourceBound': {'rootFloorBytes': 2 * 1024**3, 'developmentFloorBytes': 512 * 1024**2,
              'ownedAllocationCapBytes': 256 * 1024**2, 'finalEvidenceReserveWithinCapBytes': 1024**2,
              'admissionMarginBytes': 32 * 1024**2, 'memoryFloorBytes': 512 * 1024**2, 'seconds': 300, 'jobs': 2},
          'strictContainmentIsNotAForecastOrWarmCacheCredit': True,
          'cryptoArtifacts': 102, 'cryptoPayloadBytes': 19775715,
          'cryptoAndHistoricalAliasCurrentReadiness': 'UNOBSERVED; exact physical/hash/copy checks required within a separately owned runtime window.',
          'automaticRetries': 0, 'uploadPerformed': False, 'runtimeCalls': 0, 'compilerInvocations': 0}
emit(OUT / 'input-packet.json', packet)
print(json.dumps({'packet': pin(OUT / 'input-packet.json'), 'inputs': len(files), 'inputBytes': packet['bytes'],
                  'runner': pin(INPUTS / 'run_component.py'), 'package': pin(INPUTS / 'component/Package.swift'),
                  'closure': pin(INPUTS / 'whole-source-closure.json'), 'inverse': pin(OUT / 'controller-derivative.json'),
                  'unchangedFunctions': unchanged}, indent=2))
