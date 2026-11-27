#!/usr/bin/env python3
"""Local source-only derivation. Does not import or execute either component runner."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re
import shutil

BASE = Path(__file__).resolve().parent
WORK = BASE.parents[1]
SOURCE = BASE.parent / 'source-preparation'
HIERARCHY = WORK / 'wave2-hierarchy-rename-component/execution-preparation'
PROPERTY = WORK / 'wave2-property-unicode-audit/component-preparation/execution-preparation'
FUTURE_ROOT = '/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127'
OLD_ROOT = '/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127'
PRODUCT = '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if isinstance(raw, bytes) else raw.encode('utf-8'))


def json_write(path, value):
    write(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def record(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(WORK)), 'bytes': len(raw), 'sha256': sha(raw),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def inverse(old, new):
    old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
    changes = []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
        if tag != 'equal':
            changes.append({'oldStartLine': a, 'oldEndLine': b, 'newStartLine': c, 'newEndLine': d,
                            'oldText': ''.join(old_lines[a:b]), 'newText': ''.join(new_lines[c:d])})
    restored = new_lines[:]
    for row in reversed(changes):
        assert ''.join(restored[row['newStartLine']:row['newEndLine']]) == row['newText']
        restored[row['newStartLine']:row['newEndLine']] = row['oldText'].splitlines(keepends=True)
    assert ''.join(restored) == old
    return changes


closure_path = SOURCE / 'whole-source-closure.json'
closure_raw = closure_path.read_bytes()
assert sha(closure_raw) == '38e924728ec19aedb3eda251d7cc2f60d538c46e553ee5dcb06a607d6c4947ce'
closure = json.loads(closure_raw)
assert closure['publishedProductCommit'] == PRODUCT and len(closure['files']) == 84
assert closure['wholeSwiftBytes'] == 980531 and closure['productionWholeSwiftFiles'] == 82
inputs = BASE / 'inputs'
component = inputs / 'component'
for row in closure['files']:
    raw = (SOURCE / 'source' / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['gitBlob']
    write(component / row['path'], raw)
write(inputs / 'whole-source-closure.json', closure_raw)
for name, expected in [
    ('owned_process.py', '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'),
    ('owned-process-provenance.json', '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'),
    ('retained-crypto-closure.json', '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c')]:
    raw = (HIERARCHY / 'inputs' / name).read_bytes()
    assert sha(raw) == expected
    write(inputs / name, raw)

old_package_path = HIERARCHY / 'inputs/component/Package.swift'
old_package = old_package_path.read_text()
assert sha(old_package.encode()) == 'bf6b4e867ea96c9fe8a51fb148867c33885b2c5ee335c07070cacb53d3ac305c'
property_package = (PROPERTY / 'inputs/component/Package.swift').read_text()
property_root = '/mnt/development/projects/evidence/pinkha-wave2-property-text-readback-20261127'
host_lines = [line for line in property_package.splitlines(keepends=True)
              if '.target(name: "PinkhaAnyHost"' in line or '.testTarget(name: "PinkhaAnyHostTests"' in line]
assert len(host_lines) == 2 and all(property_root in line for line in host_lines)
package = old_package.replace('HierarchyRawTitleProof', 'BookmarkCreationProof').replace(OLD_ROOT, FUTURE_ROOT)
integration_test_line = next(line for line in package.splitlines(keepends=True) if '.testTarget(name:' in line)
host_production, host_tests = [line.replace(property_root, FUTURE_ROOT) for line in host_lines]
assert integration_test_line.rstrip().endswith(')])') and host_tests.rstrip().endswith(')])')
replacement = host_production + integration_test_line.rstrip('\n') + ',\n' + host_tests
package = package.replace(integration_test_line, replacement)
write(component / 'Package.swift', package)

xctest_methods = tuple(closure['testPrefixAndSelection'][0]['newSourceNames'])
swift_methods = tuple(closure['testPrefixAndSelection'][1]['newSourceNames'])
assert len(xctest_methods) == 4 and len(swift_methods) == 2
host_source = (component / 'Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift').read_text()
all_host_methods = sorted(re.findall(r'^\s+func (test\w+)\(\) throws \{', host_source, re.M))
assert len(all_host_methods) == 11 and set(xctest_methods).issubset(all_host_methods)

hierarchy_receipt_path = WORK / 'wave2-hierarchy-rename-component/runtime-attempt1-root-custody/original-attempt/receipt.json'
property_receipt_path = WORK / 'wave2-property-unicode-audit/runtime-attempt1-root-custody/original-attempt/receipt.json'
hierarchy_receipt = json.loads(hierarchy_receipt_path.read_bytes())
property_receipt = json.loads(property_receipt_path.read_bytes())
assert sha(hierarchy_receipt_path.read_bytes()) == '42d6a0b7b5bd09bf253fcabb814120397da615fc6db8647b633c4ba677cf8266'
assert sha(property_receipt_path.read_bytes()) == 'e025fbaf18eb23442d5bceba216874422795fabd34d9eb1eb0a0f28cac830d28'


def generated_entry(receipt, module):
    rows = [g for group in receipt['compilerInputs'] if group['module'] == module + '_test_runner'
            for g in group['generatedInputs'] if g['path'].endswith('test_entry_point.swift')]
    assert len(rows) == 1
    raw = rows[0]['text'].encode()
    assert sha(raw) == rows[0]['sha256'] and len(raw) == rows[0]['bytes']
    return raw


integration_entry = generated_entry(hierarchy_receipt, 'PinkhaAnyIntegrationTests')
property_entry = generated_entry(property_receipt, 'PinkhaAnyHostTests').decode()
start = property_entry.index('        testCase([')
end = property_entry.index(']),', start) + len(']),')
old_discovery = property_entry[start:end]
new_discovery = '        testCase([' + ',\n'.join('            ("' + name + '", NativeBookmarkPresentationTests.' + name + ')' for name in all_host_methods) + ']),'
host_entry = (property_entry[:start] + new_discovery + property_entry[end:]).encode()
assert 'NativePropertyStoreTests' not in host_entry.decode()
assert (host_entry.decode()[:start] + old_discovery + host_entry.decode()[start + len(new_discovery):]) == property_entry
entry_pins = {'PinkhaAnyHostTests': sha(host_entry), 'PinkhaAnyIntegrationTests': sha(integration_entry)}
write(BASE / 'expected-generated/PinkhaAnyHostTests-test_entry_point.swift', host_entry)
write(BASE / 'expected-generated/PinkhaAnyIntegrationTests-test_entry_point.swift', integration_entry)
json_write(BASE / 'expected-generated/derivation.json', {
    'schema': 'pinkha-bookmark6-generated-input-expectation/v1',
    'status': 'PREDICTED_BYTES_FROM_RETAINED_ACTUAL_TEMPLATE_NOT_NEW_COMPILER_EVIDENCE',
    'inputsNotStagedAsCompilerSources': True, 'actualBookmarkCompilerGeneratedSources': None,
    'originalHierarchyReceipt': record(hierarchy_receipt_path), 'originalPropertyReceipt': record(property_receipt_path),
    'IntegrationGeneratedEntryUnchangedSHA256': sha(integration_entry),
    'hostOriginalGeneratedEntrySHA256': sha(property_entry.encode()), 'hostSuccessorGeneratedEntrySHA256': sha(host_entry),
    'hostFullDiscoveredSourceMethods': all_host_methods, 'hostOriginalDiscoveryText': old_discovery,
    'hostSuccessorDiscoveryText': new_discovery, 'fullInverseVerified': True})

old_runner_path = HIERARCHY / 'inputs/run_component.py'
old_runner = old_runner_path.read_text()
assert sha(old_runner.encode()) == 'f63adbdfde8bfa5d1779371e1c046f196e617f2f286181dc6c8c7768414e3628'
tree = ast.parse(old_runner)
functions = {node.name: ast.get_source_segment(old_runner, node) for node in tree.body if isinstance(node, ast.FunctionDef)}
runner = old_runner.replace(OLD_ROOT, FUTURE_ROOT)
runner = runner.replace('9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce', PRODUCT)
runner = runner.replace('510a00d5fb0065bcc5292d83443b9e4b6774f9dda4a7fd1d1d0ef4cfddeb8ca0', sha(closure_raw))
old_doc = ast.get_source_segment(old_runner, tree.body[0])
new_doc = '"""One source-bound Bookmark component: four XCTest and two Swift Testing cases.\n\nPreparation is inert and never grants a coordinated runtime slot. All82 production\nbodies and both complete original test files are exact. Old7/27 methods are not\nselected. Typed fixtures and the original controlled repository are not Native,\nHTTP, account, hosted UI, or Apple acceptance. There is one owned Swift command.\n"""'
runner = runner.replace(old_doc, new_doc, 1)
pins = {p.relative_to(component).as_posix(): sha(p.read_bytes()) for p in sorted(component.rglob('*')) if p.is_file()}
assert len(pins) == 85
assignments = {node.targets[0].id: ast.get_source_segment(old_runner, node) for node in tree.body
               if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
runner = runner.replace(assignments['SOURCE_PINS'], 'SOURCE_PINS = ' + repr(pins), 1)
runner = runner.replace(assignments['METHODS'], 'XCTEST_METHODS = ' + repr(xctest_methods) + '\nSWIFT_TESTING_METHODS = ' + repr(swift_methods) + '\nMETHODS = XCTEST_METHODS + SWIFT_TESTING_METHODS', 1)
runner = runner.replace(assignments['SUITE'], 'GENERATED_ENTRY_SHA256 = ' + repr(entry_pins), 1)
runner = runner.replace(assignments['TEST_FILTER'], "TEST_FILTER = '(?:' + '|'.join(re.escape(name) for name in METHODS) + r')(?:\\(\\))?$'", 1)
runner = runner.replace(functions['compiler_inputs'], (BASE / 'compiler_inputs.fragment.py').read_text().rstrip(), 1)
runner = runner.replace(functions['swift_testing_result'], (BASE / 'mixed_test_result.fragment.py').read_text().rstrip(), 1)
runner = runner.replace("'pinkha-hierarchy-raw-title-component/v1'", "'pinkha-bookmark-six-component/v1'")
runner = runner.replace('Owned hierarchy rename command exceeded 300 seconds', 'Owned Bookmark six-method command exceeded 300 seconds')
runner = runner.replace("receipt['testResult'] = swift_testing_result(log)", "receipt['testResult'] = mixed_test_result(log)")
runner = runner.replace('PASS_FOUR_SWIFT_TESTING_METHODS_EIGHT_ARGUMENT_CASES_HIERARCHY_COMPONENT_ONLY', 'PASS_FOUR_XCTEST_AND_TWO_SWIFT_TESTING_CASES_BOOKMARK_COMPONENT_ONLY')
ast.parse(runner)
write(inputs / 'run_component.py', runner)

new_functions = {node.name: ast.get_source_segment(runner, node) for node in ast.parse(runner).body if isinstance(node, ast.FunctionDef)}
unchanged = [name for name in functions if name in new_functions and functions[name] == new_functions[name]]
assert len(unchanged) == 11 and set(functions) - set(unchanged) == {'compiler_inputs', 'swift_testing_result', 'main'}
runner_changes = inverse(old_runner, runner)
package_changes = inverse(old_package, package)
write(BASE / 'runner-source.patch', ''.join(difflib.unified_diff(old_runner.splitlines(True), runner.splitlines(True), fromfile='actual-hierarchy/run_component.py', tofile='bookmark6/run_component.py')))
write(BASE / 'package-source.patch', ''.join(difflib.unified_diff(old_package.splitlines(True), package.splitlines(True), fromfile='actual-hierarchy/Package.swift', tofile='bookmark6/Package.swift')))
json_write(BASE / 'source-inverse.json', {
    'schema': 'pinkha-bookmark6-execution-full-source-inverse/v1',
    'originalRunner': record(old_runner_path), 'candidateRunner': record(inputs / 'run_component.py'),
    'originalPackage': record(old_package_path), 'candidatePackage': record(component / 'Package.swift'),
    'hostTargetDonorPackage': record(PROPERTY / 'inputs/component/Package.swift'),
    'runnerReverseEdits': runner_changes, 'packageReverseEdits': package_changes,
    'completeOldRunnerAndPackageRestored': True, 'unchangedFunctionNames': unchanged,
    'unchangedFunctionSHA256': {name: sha(functions[name].encode()) for name in unchanged},
    'changedFunctions': ['compiler_inputs', 'main'],
    'replacedResultFunction': {'old': 'swift_testing_result', 'new': 'mixed_test_result'},
    'productionBodiesChanged': 0, 'testBodiesChanged': 0, 'runtimeInvocations': 0})

files = []
for path in sorted(inputs.rglob('*')):
    if path.is_file():
        r = record(path);r['path'] = path.relative_to(inputs).as_posix();r['mode'] = '100644';files.append(r)
assert len(files) == 90 and {r['path'] for r in files} == {'component/' + p for p in pins} | {
    'run_component.py', 'owned_process.py', 'owned-process-provenance.json', 'retained-crypto-closure.json', 'whole-source-closure.json'}
packet = {'schema': 'pinkha-bookmark6-component-input-packet/v1', 'status': 'PREPARED_NOT_ADMITTED_OR_RUN',
    'productCommit': PRODUCT, 'coreDependencyCommit': closure['coreDependencyCommit'],
    'runtimeReady': False, 'runtimeSlotGranted': False, 'actualResult': None, 'compiledEnumeration': None,
    'compilerInvocations': 0, 'runtimeCalls': 0, 'uploadPerformed': False, 'automaticRetries': 0,
    'wholeProductionFiles': 82, 'wholeTestFiles': 2, 'sourceBodiesChangedForComponent': 0,
    'fullSourceTestMethods': {'PinkhaAnyHostTests': 11, 'PinkhaAnyIntegrationTests': 29},
    'selectedSourceMethodNames': {'XCTest': list(xctest_methods), 'SwiftTesting': list(swift_methods)},
    'declaredNewCaseEvents': {'XCTest': 4, 'SwiftTesting': 2}, 'hostLiteralScenarios': 17,
    'literalScenariosAreEnumeratedCases': False, 'old7HostMethodsSelected': 0, 'old27IntegrationMethodsSelected': 0,
    'testFilter': '(?:' + '|'.join(re.escape(name) for name in xctest_methods + swift_methods) + r')(?:\(\))?$',
    'expectedCompilerClosure': {'originalSwiftFiles': 84, 'generatedSwiftFiles': 4, 'driverModules': 9,
                                'SwiftFileLists': 9, 'LinkFileLists': 9, 'testProducts': 2, 'testRunners': 2,
                                'actualCompilerOrLinkEvidence': None},
    'cryptoArtifacts': 102, 'cryptoPayloadBytes': 19775715,
    'cryptoAndHistoricalAliasCurrentReadiness': 'UNOBSERVED; fresh physical/hash/copy checks remain required within an owned runtime window.',
    'futureFixedRoot': FUTURE_ROOT, 'futureLaunch': {'argv': ['/usr/bin/python3', '-B', FUTURE_ROOT + '/inputs/run_component.py', '--execute-reviewed-candidate'],
        'cwd': FUTURE_ROOT, 'environment': {'PWD': FUTURE_ROOT, 'PYTHONDONTWRITEBYTECODE': '1'}, 'requiresSeparateReviewedStagingAndOwnerSlot': True},
    'proposedResourceBound': {'rootFloorBytes': 2147483648, 'developmentFloorBytes': 536870912,
        'ownedAllocationCapBytes': 268435456, 'finalEvidenceReserveWithinCapBytes': 1048576,
        'admissionMarginBytes': 33554432, 'memoryFloorBytes': 536870912, 'jobs': 2, 'seconds': 300},
    'strictContainmentIsNotAForecastOrWarmCacheCredit': True, 'fileCount': len(files),
    'bytes': sum(r['bytes'] for r in files), 'files': files}
json_write(BASE / 'input-packet.json', packet)
json_write(BASE / 'preparation-proof.json', {
    'schema': 'pinkha-bookmark6-source-preparation-proof/v1', 'status': 'SOURCE_ONLY_NOT_EXECUTED',
    'packet': record(BASE / 'input-packet.json'), 'sourceClosure': record(closure_path),
    'sourceInventory': record(SOURCE / 'source-inventory.json'), 'sourceEvidence': record(SOURCE / 'source-evidence.json'),
    'runner': record(inputs / 'run_component.py'), 'package': record(component / 'Package.swift'),
    'inverse': record(BASE / 'source-inverse.json'), 'generator': record(Path(__file__)),
    'unchangedFunctions': unchanged, 'all84WholeSourceCopiesExact': True,
    'sourceDeclarationCountsAreNotCompiledEnumeration': True, 'noHistoricalTestReplay': True,
    'noHostOrCompilerOrNetworkProcess': True, 'noStagerCreated': True, 'runtimeGrant': None})
print(json.dumps({'runner': record(inputs / 'run_component.py'), 'package': record(component / 'Package.swift'),
                  'packet': record(BASE / 'input-packet.json'), 'files': len(files), 'bytes': packet['bytes'],
                  'unchangedFunctions': len(unchanged), 'runtimeInvocations': 0}, indent=2))
