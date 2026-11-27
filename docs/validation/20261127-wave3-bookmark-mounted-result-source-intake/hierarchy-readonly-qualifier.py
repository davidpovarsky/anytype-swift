"""Read only original published evidence; no candidate imports, processes or tests."""
from pathlib import Path
import hashlib
import json
import re
import shlex

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREFIX = 'docs/validation/20261127-wave2-hierarchy-rename-component-'
RESULT = HERE / 'source' / (PREFIX + 'result')
PREP = HERE / 'source' / (PREFIX + 'preparation')
ATTEMPT = RESULT / 'original-attempt'
SOURCE_ROOT = PREP / 'execution/inputs/component'
PHYSICAL = '/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def identity(p):
    p = Path(p); raw = p.read_bytes()
    return {'path': str(p), 'bytes': len(raw), 'sha256': digest(raw),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}

def load(p):
    return json.loads(Path(p).read_text())

inventory = load(RESULT / 'original-inventory.json')
assert len(inventory['files']) == inventory['exactOriginalCount'] == 10
assert sum(x['bytes'] for x in inventory['files']) == inventory['exactOriginalBytes'] == 561482
originals = []
for entry in inventory['files']:
    observed = identity(ATTEMPT / entry['path'])
    assert all(observed[k] == entry[k] for k in ['bytes', 'sha256', 'gitBlob'])
    originals.append(observed)
receipt_raw = (ATTEMPT / 'receipt.json').read_bytes()
assert len(receipt_raw) == 283810 and digest(receipt_raw) == '42d6a0b7b5bd09bf253fcabb814120397da615fc6db8647b633c4ba677cf8266'
r = json.loads(receipt_raw)
assert r['schema'] == 'pinkha-hierarchy-raw-title-component/v1'
assert r['status'] == 'PASS_FOUR_SWIFT_TESTING_METHODS_EIGHT_ARGUMENT_CASES_HIERARCHY_COMPONENT_ONLY'
assert r['processExit'] == 0 and r['errors'] == []
assert r['nativeCalls'] == r['AppleCalls'] == r['sourceBodiesModifiedForComponent'] == 0
assert r['productCommit'] == '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'
assert r['controllerSHA256'] == digest((PREP / 'execution/inputs/run_component.py').read_bytes())
assert r['command'] == load(ATTEMPT / 'command.json')
argv = r['command']['argv']
assert argv[-2:] == ['--filter', 'AnyHierarchyRawTitleTests']
assert argv[argv.index('--jobs') + 1] == '2' and '--no-parallel' in argv
assert '--disable-automatic-resolution' in argv
assert r['outerGroupAtExit']['status'] == 'ABSENT_ESRCH' and r['outerGroupAtExit']['errno'] == 3
assert r['ownedCleanup']['absenceEvidence'] == r['outerGroupAtExit']
assert r['ownedCleanup']['historicalGroupReprobed'] is False
assert r['ownedCleanup']['status'] == 'PASS_OWNED_GROUP_ABSENT'
assert load(ATTEMPT / 'process.json')['processGroup'] == r['outerGroupAtExit']['processGroup']

before = load(ATTEMPT / 'source-inputs-before.json')
assert len(before) == 56 and before == load(ATTEMPT / 'source-inputs-after.json')
final = load(ATTEMPT / 'source-inputs-final.json')
assert final['inputs'] == final['compiledCopy'] == before
for path, sha in before.items():
    assert digest((SOURCE_ROOT / path).read_bytes()) == sha
closure = load(PREP / 'execution/inputs/whole-source-closure.json')
assert len(closure['files']) == 55 and closure['sourceBodiesChangedForComponent'] == 0
assert closure['coreDependencyCommit'] == '26beca175d64a4d34e3567f2bbb4bf308d714478'
current_tree_path = ROOT / 'wave3-heart-note-empty-warm-source-integration-prepared/map110-continuation/prepared2/expected-final-complete-leaves.stdout'
current = {}
for entry in current_tree_path.read_bytes().split(b'\0'):
    if entry:
        h, p = entry.split(b'\t', 1); mode, kind, sha = h.decode().split()
        current[p.decode()] = {'mode': mode, 'type': kind, 'sha': sha}
current_matches = []; external = []
for entry in closure['files']:
    actual = identity(SOURCE_ROOT / entry['path'])
    assert all(actual[k] == entry[k] for k in ['bytes', 'sha256', 'gitBlob'])
    assert entry['wholeOriginalFile'] is True
    if entry['repository'] == 'davidpovarsky/anytype-swift':
        assert current[entry['repositoryPath']] == {'mode': '100644', 'type': 'blob', 'sha': actual['gitBlob']}
        current_matches.append({'path': entry['repositoryPath'], 'identity': actual})
    else:
        assert entry['repository'] == 'davidpovarsky/TorahInspectorKit'
        assert entry['sourceCommit'] == '26beca175d64a4d34e3567f2bbb4bf308d714478'
        external.append({'path': entry['repositoryPath'], 'commit': entry['sourceCommit'], 'identity': actual})
assert len(current_matches) == 47 and len(external) == 8

stderr = (ATTEMPT / 'stderr.original.log').read_text()
compiled = {}; generated = {}; modules = []
for item in r['compilerInputs']:
    args = item['actualCompilerArgv']
    assert args[args.index('-target') + 1] == 'aarch64-unknown-linux-gnu'
    assert args[args.index('-working-directory') + 1] == PHYSICAL
    assert '-j2' in args and '-enable-testing' in args
    for line in item['actualCompilerLines']:
        assert line in stderr.splitlines()
        assert shlex.split(line) == args
    assert digest(item['sourceListText'].encode()) == item['sourceListSHA256']
    listed = []
    for line in item['sourceListText'].splitlines():
        parts = shlex.split(line); assert len(parts) == 1; listed.append(parts[0])
    assert set(listed) == {x['source'] for x in item['objects']}
    for obj in item['objects']:
        assert obj['objectBytes'] > 0 and re.fullmatch('[0-9a-f]{64}', obj['objectSHA256'])
        assert item['outputFileMapValue'][obj['source']]['object'] == obj['object']
        if obj['generatedSource']:
            evidence = next(x for x in item['generatedInputs'] if x['path'] == obj['source'])
            raw = evidence['text'].encode()
            assert len(raw) == evidence['bytes'] == obj['sourceBytes']
            assert digest(raw) == evidence['sha256'] == obj['sourceSHA256']
            generated[obj['source']] = evidence['sha256']
        else:
            assert obj['source'].startswith(PHYSICAL + '/component/')
            path = obj['source'].removeprefix(PHYSICAL + '/component/')
            assert obj['sourceSHA256'] == before[path]
            assert obj['sourceBytes'] == (SOURCE_ROOT / path).stat().st_size
            compiled[path] = obj['sourceSHA256']
    modules.append({'module': item['module'], 'objects': len(item['objects']),
                    'sourceListSHA256': item['sourceListSHA256'],
                    'actualDriverLineFoundInOriginalLog': True})
assert len(modules) == 6 and len(compiled) == 55 and len(generated) == 2
assert set(compiled) == set(before) - {'Package.swift'}

dep_expected = load(PREP / 'execution/inputs/retained-crypto-closure.json')['files']
dep_actual = load(ATTEMPT / 'actual-dependency-copies.json')
assert len(dep_expected) == len(dep_actual) == 102
by_source = {x['freshCopySourcePath']: x for x in dep_expected}
assert len(by_source) == 102
for entry in dep_actual:
    expected = by_source[entry['source']]
    assert all(entry[k] == expected[k] for k in ['kind', 'bytes', 'sha256'])
    assert entry['original'] == expected['originalManifestPath']
    alias_key = 'actualOriginalPackageLinkerPath' if expected['kind'] == 'aggregated-link-object' else 'recordedHistoricalAliasPath'
    assert entry['alias'] == expected[alias_key]
    assert entry['target'].startswith(PHYSICAL + '/retained-crypto-')
assert sum(x['bytes'] for x in dep_actual) == 19775715

stdout = (ATTEMPT / 'stdout.original.log').read_text()
lines = stdout.splitlines()
expected_methods = [
    'canonicallyEquivalentRequestedRenameReachesTheOriginalStore',
    'canonicallyEquivalentStaleExpectedTitleRefusesBeforeDispatch',
    'canonicallyEquivalentSuccessfulReadbackCannotCertifyRename',
    'canonicallyEquivalentReadbackPreservesTheOriginalWriteError']
assert r['testResult']['actualSwiftTestingMethods'] == expected_methods
assert r['testResult']['actualMethodCount'] == 4
assert r['testResult']['actualPassedArgumentCaseCount'] == 8
assert r['testResult']['oldMethodsExecuted'] == r['testResult']['XCTestCases'] == r['testResult']['HTTPFixturesInvoked'] == 0
assert '✔ Test run with 4 tests in 1 suite passed after 0.012 seconds.' in lines
assert not any(re.search(r'\b(failed|skipped|cancelled)\b', x, re.I) for x in lines)
assert len([x for x in lines if x.startswith('✔ Test case passing ')]) == 8
assert len([x for x in lines if x.startswith('◇ Test case passing ')]) == 8
assert len([x for x in lines if x.startswith('✔ Test ') and 'with 2 test cases passed' in x]) == 4
cases = []
for event in r['testResult']['argumentCases']:
    started = lines[event['startedLogLine'] - 1]; passed = lines[event['passedLogLine'] - 1]
    assert event['method'] in expected_methods
    assert started.startswith('◇ Test case passing ') and started.endswith(' started.')
    assert passed.startswith('✔ Test case passing ') and ' passed after ' in passed
    assert event['actualEventSignature'] in started and event['actualEventSignature'] in passed
    assert event['observedArgumentDescription'] in started and event['observedArgumentDescription'] in passed
    cases.append((event['method'], event['observedArgumentDescription']))
assert len(set(cases)) == 8
for method in expected_methods:
    descriptions = [d for m, d in cases if m == method]
    assert len(descriptions) == 2 and sum('.latin ' in d for d in descriptions) == sum('.hebrew ' in d for d in descriptions) == 1

samples = load(ATTEMPT / 'resource-samples.json')
assert len(samples) == 45
budget = r['budget']
for sample in samples:
    assert sample['rootFreeBytes'] >= budget['rootFloorBytes']
    assert sample['developmentFreeBytes'] >= budget['developmentFloorBytes']
    assert sample['memAvailableBytes'] >= budget['memoryFloorBytes']
    assert sample['ownedAllocatedBytes'] <= budget['ownedAllocationCapBytes']
assert max(x['ownedAllocatedBytes'] for x in samples) == r['maximumOwnedAllocatedBytes']
assert min(x['rootFreeBytes'] for x in samples) == r['minimumRootFreeBytes']
assert min(x['developmentFreeBytes'] for x in samples) == r['minimumDevelopmentFreeBytes']
out = {'schema': 'pinkha-independent-original-hierarchy-result-qualification/v1',
       'status': 'PASS_ORIGINAL_LINUX_FOUR_METHODS_EIGHT_CASES_ONLY',
       'receipt': identity(ATTEMPT / 'receipt.json'), 'originalFiles': originals,
       'input56BeforeAfterFinalAndCompiledCopyExact': True,
       'actualCurrentBase': '3208bdb32e043d9a9b333ec45e017bc5a966ce0b',
       'actualCurrentTree': '1bbf243c96eef7bd1c19b8f9b4ad73e59af8925e',
       'currentAppSource47Exact': current_matches, 'externalOriginalKit26Whole8': external,
       'compilerModules': modules, 'wholeCompiledSources': 55, 'generatedCompilerInputs': 2,
       'actualDependencyCopies102MatchOriginalClosure': True, 'dependencyPayloadBytes': 19775715,
       'actualMethods': expected_methods, 'actualArgumentCases': [list(x) for x in cases],
       'originalResourceSamples': 45, 'originalGroupClosure': r['ownedCleanup'],
       'stderrOriginal': identity(ATTEMPT / 'stderr.original.log'),
       'warningFreeClaim': False,
       'scope': 'Original9e4 controlled-store hierarchy rename component. Later3d2 creator override and new tests are outside this compiled whole-file envelope. No App/UI/native/account/SDK/physical-device qualification.',
       'newTestsExecuted': 0, 'candidateImports': 0, 'newHostCalls': 0,
       'historicalPIDsReprobed': False}
destination = HERE / 'independent-original-result-proof.json'
assert not destination.exists()
destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(identity(destination), indent=2))
