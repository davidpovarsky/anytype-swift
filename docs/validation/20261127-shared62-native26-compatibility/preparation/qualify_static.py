#!/usr/bin/env python3
"""Byte/AST qualification only. Never imports or executes candidate controls."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path('/workspace/scratch/ae335eba85e3')
PACK = ROOT / 'shared62-native26-compatibility-source/prepared2'
OUT = ROOT / 'shared62-native26-compatibility-source/qualification1'
BASE = '5a45fe4af2c4601faad181f81d391057c1237654'
TREE = '13578db08a5e215fd70e88209e6ec409135440e2'
PREFIX = 'Tools/PinkhaDualEngineRuntime/'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
            'gitMode': '100644'}


def reference(path):
    return {'path': str(path), **identity(path.read_bytes())}


def require_identity(raw, expected):
    got = identity(raw)
    assert all(got[k] == expected[k] for k in expected if k in got), (got, expected)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def declarations(raw):
    text = raw.decode()
    result = {}
    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = '.'.join(prefix + (child.name,))
                assert key not in result, key
                signature = {'kind': type(child).__name__, 'name': child.name,
                             'decorators': [ast.dump(n) for n in child.decorator_list]}
                if isinstance(child, ast.ClassDef):
                    signature['bases'] = [ast.dump(n) for n in child.bases]
                    signature['keywords'] = [ast.dump(n) for n in child.keywords]
                else:
                    signature['arguments'] = ast.dump(child.args)
                    signature['returns'] = ast.dump(child.returns) if child.returns else None
                result[key] = {'raw': ast.get_source_segment(text, child).encode(), 'signature': signature}
                visit(child, prefix + (child.name,))
            else:
                visit(child, prefix)
    visit(ast.parse(raw), ())
    return result


def constants(raw):
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'frozenset':
                result[node.targets[0].id] = frozenset(ast.literal_eval(value.args[0]))
            else:
                try:
                    result[node.targets[0].id] = ast.literal_eval(value)
                except (ValueError, TypeError):
                    pass
    return result


assert not OUT.exists()
handoff = json.loads((PACK / 'handoff.json').read_text())
assert identity((PACK / 'handoff.json').read_bytes())['sha256'] == '4809941a3f8d4e50ea29e1eee4920177c3e5e0eed0eb60e55a8548240248a5ce'
index = json.loads((PACK / 'source-index.json').read_text())['files']
for path, expected in index.items():
    require_identity((PACK / path).read_bytes(), expected)
source = json.loads((PACK / 'source-inputs.json').read_text())
assert source['actualBase'] == BASE and source['actualTree'] == TREE
rows = source['files']
assert len(rows) == 38
context = json.loads((PACK / 'evidence/source-context.json').read_text())
current = context['current113']
assert len(current) == 113
before, after = {}, {}
for path, item in current.items():
    raw = Path(item['localPath']).read_bytes()
    require_identity(raw, item)
    before[path] = raw
    after[path] = raw
for path, row in rows.items():
    raw = base64.b64decode(row['base64'], validate=True)
    old = base64.b64decode(row['beforeBase64'], validate=True)
    require_identity(raw, row['after']); require_identity(old, row['before'])
    assert old == before[path] == (PACK / 'before' / path).read_bytes()
    assert raw == (PACK / 'after' / path).read_bytes() and raw != old
    assert row['status'] == 'M'
    after[path] = raw

# Exact actual complete Git tree, without any Git subprocess or checkout.
leaf_path = ROOT / 'wave3-bookmark-mounted-result-source-integration-prepared/prepared1/expected-final-complete-leaves.stdout'
leaves = {}
root = {}
for record in leaf_path.read_bytes().split(b'\0'):
    if not record:
        continue
    left, name = record.split(b'\t', 1)
    mode, kind, oid = left.decode().split(' ')
    path = name.decode()
    assert path not in leaves
    leaves[path] = {'mode': mode, 'type': kind, 'sha': oid}
    target = root
    parts = path.split('/')
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = (mode, oid)


def tree_hash(node):
    members = []
    for name, value in node.items():
        is_dir = isinstance(value, dict)
        mode, oid = ('40000', tree_hash(value)) if is_dir else value
        members.append((name.encode() + (b'/' if is_dir else b''),
                        mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(oid)))
    content = b''.join(row[1] for row in sorted(members))
    return hashlib.sha1(b'tree ' + str(len(content)).encode() + b'\0' + content).hexdigest()


assert len(leaves) == 23217 and tree_hash(root) == TREE
for path, raw in before.items():
    assert leaves[path] == {'mode': '100644', 'type': 'blob', 'sha': identity(raw)['gitBlob']}
actual_control_paths = {p for p in leaves if p.startswith(PREFIX + 'hosted_') or p.startswith(PREFIX + 'warm_')}
actual_control_paths = {p for p in actual_control_paths if p.endswith(('.py', '.json'))}
assert actual_control_paths == set(current)

# Every full literal inverse independently restores the actual published preimage.
inverse = json.loads((PACK / 'evidence/full-literal-inverses.json').read_text())
assert {r['path'] for r in inverse['files']} == set(rows)
for row in inverse['files']:
    text = after[row['path']].decode().splitlines(keepends=True)
    for op in reversed(row['operations']):
        at = op['afterLine'] - 1
        old = op['afterUTF8'].splitlines(keepends=True)
        assert text[at:at + len(old)] == old
        text[at:at + len(old)] = op['beforeUTF8'].splitlines(keepends=True)
    assert ''.join(text).encode() == before[row['path']]

# Complete recursive declaration/API census, not just top-level function counts.
declaration_rows = []
critical = {'Commands', 'FirstFailure', 'PhaseCustody', 'StageResultWrites', 'CommandBarrier',
            'execute_lane', 'main', 'run_phase', 'stage_and_build', 'preserve', 'cleanup',
            'observe_owned_groups', 'require_closed', 'final_inputs', 'file_only_postflight',
            'final_input_boundary', 'retain_native23_failure', 'retain_native23_receipt'}
critical_rows = []
for path in sorted(current):
    if not path.endswith('.py'):
        continue
    a, b = declarations(before[path]), declarations(after[path])
    assert a.keys() == b.keys()
    for name in a:
        assert a[name]['signature'] == b[name]['signature'], (path, name)
        exact = a[name]['raw'] == b[name]['raw']
        declaration_rows.append({'path': path, 'declaration': name, 'byteExact': exact,
                                 'before': identity(a[name]['raw']), 'after': identity(b[name]['raw'])})
        if any(part in critical for part in name.split('.')):
            assert exact, (path, name)
            critical_rows.append({'path': path, 'declaration': name, **identity(a[name]['raw'])})

# Explicit semantic replay plus qualified identity substitutions reconstructs every Python file.
semantic = dict(before)
proof = json.loads((PACK / 'evidence/declaration-preservation.json').read_text())
for row in proof['files']:
    for op in row['semanticLiteralOperations']:
        old, new = op['beforeUTF8'].encode(), op['afterUTF8'].encode()
        assert semantic[row['path']].count(old) == op['occurrences']
        semantic[row['path']] = semantic[row['path']].replace(old, new)
graph = json.loads((PACK / 'evidence/current-identity-cascade.json').read_text())
replacement_pairs = {}
for path in rows:
    old_sha, new_sha = identity(before[path])['sha256'], identity(after[path])['sha256']
    assert old_sha not in replacement_pairs or replacement_pairs[old_sha] == new_sha
    replacement_pairs[old_sha] = new_sha
for path in current:
    if not path.endswith('.py'):
        continue
    raw = semantic[path]
    for old_sha, new_sha in replacement_pairs.items():
        if old_sha == identity(before[path])['sha256']:
            continue
        if old_sha.encode() in before[path]:
            assert raw.count(old_sha.encode()) == before[path].count(old_sha.encode())
            raw = raw.replace(old_sha.encode(), new_sha.encode())
    assert raw == after[path], path
for edge in graph['edges']:
    assert identity(before[edge['producer']])['sha256'] == edge['beforeSHA256']
    assert identity(after[edge['producer']])['sha256'] == edge['afterSHA256']
    assert edge['beforeSHA256'].encode() not in after[edge['consumer']]
    assert after[edge['consumer']].count(edge['afterSHA256'].encode()) >= edge['occurrences']
for edge in graph['fullIdentityRows']:
    value = json.loads(after[edge['consumer']])
    for key in edge['keys']:
        value = value[key]
    expected = identity(after[edge['producers'][0]])
    assert all(value[k] == expected[k] for k in edge['identityFields'])

# Current 62 + 10 + 27 source identities and original two Native UI sources.
inventory = json.loads((PACK / 'evidence/complete99-source-inputs.json').read_text())
assert inventory['counts'] == {'selectedAppTestSwift': 62, 'selectedStage1UISwift': 10, 'support': 27, 'total': 99}
assert len(inventory['sources']) == 99
for row in inventory['sources']:
    raw = Path(row['localPath']).read_bytes()
    require_identity(raw, row)
    assert leaves[row['path']]['sha'] == identity(raw)['gitBlob']
    assert leaves[row['path']]['mode'] == row['gitMode']
selected = json.loads((PACK / 'evidence/shared-build-test-source-inventory.json').read_text())
owner = constants(after[PREFIX + 'hosted_shared_build/run.py'])
old_owner = constants(before[PREFIX + 'hosted_shared_build/run.py'])
assert owner['COMPOSED_NATIVE_SOURCE_PATHS'] == frozenset(selected['selectedAppNative'])
assert owner['COMPOSED_NATIVE_SOURCE_PATHS'] - old_owner['COMPOSED_NATIVE_SOURCE_PATHS'] == {'AnyTypeTests/Pinkha/AnyNativeAttachmentMountedRecoveryTests.swift'}
assert owner['COMPOSED_STAGE1_SOURCE_PATHS'] == old_owner['COMPOSED_STAGE1_SOURCE_PATHS']
assert owner['ORIGINAL_UIKIT23_PROJECTED_SOURCES'] == old_owner['ORIGINAL_UIKIT23_PROJECTED_SOURCES']
contract_path = PREFIX + 'hosted_shared_build/native23_build_contract.json'
old_contract, contract = json.loads(before[contract_path]), json.loads(after[contract_path])
assert {p for p in contract['sourcePathPins'] if contract['sourcePathPins'][p] != old_contract['sourcePathPins'][p]} == {'Modules/PinkhaAnyUI/Package.swift'}
assert contract['sourceCompatibilitySuccessor']['previousNative26Compatibility'] == old_contract['sourceCompatibilitySuccessor']
assert {k: v for k, v in contract.items() if k not in ('sourcePathPins', 'sourceCompatibilitySuccessor')} == {k: v for k, v in old_contract.items() if k not in ('sourcePathPins', 'sourceCompatibilitySuccessor')}

json_allowed_top = {
    'hosted_account_runtime/profile-dependency.json': {'files'},
    'hosted_account_runtime/profile.json': {'compilerScope'},
    'hosted_native23/activation.json': {'producerOwnerSHA256', 'reason'},
    'hosted_native25/activation.json': {'producerOwnerSHA256'},
    'hosted_native26_properties/activation.json': {'producerOwnerSHA256'},
    'hosted_native26_properties/source_witnesses.json': {'appFixtureSources'},
    'hosted_shared_build/native23_build_contract.json': {'sourcePathPins', 'sourceCompatibilitySuccessor'},
    'hosted_t5/activation.json': {'compiledSourceCounts'},
    'warm_focus_editor/activation.json': {'requiredAppCompilerSources'},
    'warm_focus_editor/source-membership.json': {'native'},
}
assert {PREFIX + p for p in json_allowed_top} == {p for p in rows if p.endswith('.json')}
for suffix, allowed in json_allowed_top.items():
    a, b = json.loads(before[PREFIX + suffix]), json.loads(after[PREFIX + suffix])
    assert a.keys() == b.keys()
    assert {k for k in a if a[k] != b[k]} == allowed
assert json.loads(after[PREFIX + 'hosted_account_runtime/profile.json'])['compilerScope'] == {
    **json.loads(before[PREFIX + 'hosted_account_runtime/profile.json'])['compilerScope'],
    'currentNativeSourcePaths': 62,
}
old_store = json.loads(before[PREFIX + 'hosted_native26_properties/source_witnesses.json'])
new_store = json.loads(after[PREFIX + 'hosted_native26_properties/source_witnesses.json'])
store_path = 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift'
assert {p for p in old_store['appFixtureSources'] if old_store['appFixtureSources'][p] != new_store['appFixtureSources'][p]} == {store_path}
assert new_store['appFixtureSources'][store_path] == {'bytes': 53698, 'sha256': 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b'}

# Existing 52 witness guards: only ten reviewed full file identities advance.
prior = json.loads((ROOT / 'wave3-bookmark-mounted-result-source-integration-prepared/prepared1/payload.json').read_text())['guardInputs']
guard_before = prior['filesAfter']
guard_after = copy.deepcopy(guard_before)
guard_updates = {}
for path in set(guard_before) & set(rows):
    assert guard_before[path] == rows[path]['before']
    guard_after[path] = rows[path]['after']
    guard_updates[path] = {'before': guard_before[path], 'after': guard_after[path]}
assert len(guard_before) == len(guard_after) == 52 and len(guard_updates) == 10
protected = copy.deepcopy(prior['protectedLeaves'])
for path, row in prior['protectedUpdates'].items():
    assert protected[path] == row['before']
    protected[path] = row['after']
assert not (set(protected) & set(prior['addedProtectedLeaves']))
protected.update(prior['addedProtectedLeaves'])
assert len(protected) == 82 and not (set(protected) & set(rows))
for path, row in protected.items():
    assert leaves[path] == row
for row in prior['closedActivation']:
    value = json.loads(after[row['path']])
    assert all(value[key] == expected for key, expected in row['fields'].items())
assert len(prior['closedActivation']) == 45
receipt = json.loads(Path(context['actualReceipt']['localPath']).read_text())
assert len(receipt['outputPins']['allPackagePins']) == 56 and receipt['outputPins']['reviewedRefactors'] == 145
map_path = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
assert map_path not in rows and leaves[map_path]['sha'] == guard_before[map_path]['gitBlob']

# No old group lifecycle, native tuple, private crypto, or historical profile is admitted by a count change.
same = ['hosted_core13/run.py', 'hosted_core13/originals.py', 'hosted_core13/original_sources.json',
        'hosted_core24/run.py', 'hosted_t5/run.py', 'hosted_t5/custody_crypto.mjs',
        'warm_focus_editor/originals.py', 'warm_focus_editor/priority-runtime-selection.closed.json',
        'warm_forward/priority-runtime-selection.closed.json']
for suffix in same:
    path = PREFIX + suffix
    if path in before:
        assert before[path] == after[path]
selection = json.loads(after[PREFIX + 'warm_focus_editor/priority-runtime-selection.closed.json'])
warm_run = PREFIX + 'warm_focus_editor/run.py'
assert {n: v['raw'] for n, v in declarations(before[warm_run]).items()} == {n: v['raw'] for n, v in declarations(after[warm_run]).items()}

OUT.mkdir(parents=True)
def write(name, value):
    path = OUT / name
    with path.open('xb') as f:
        f.write(dump(value))
    return reference(path)

details = write('recursive-declaration-and-api-proof.json', {
    'files': declaration_rows, 'criticalUnchangedDeclarations': critical_rows,
    'allDeclarationNamesAndSignaturesUnchanged': True,
    'candidateImports': 0, 'testsExecuted': 0, 'compilerInvocations': 0,
})
guards = write('exact-guard-successor.json', {
    'actualBase': BASE, 'actualTree': TREE, 'before52': guard_before, 'after52': guard_after,
    'explicit10IdentityUpdates': guard_updates, 'unchanged82ProtectedLeaves': protected,
    'unchanged45ClosedFieldTuples': prior['closedActivation'],
    'unchangedMap145': guard_before[map_path], 'unchanged56PackagePins': receipt['outputPins']['allPackagePins'],
    'bindingReady': False, 'finalReleaseSHA': None, 'finalControlSHA': None,
})
seal = write('independent-static-seal.json', {
    'schema': 'pinkha-shared62-native26-static-source-qualification/v1',
    'status': 'PASS_STATIC_SOURCE_ONLY_NOT_RUNTIME', 'actualBase': BASE, 'actualTree': TREE,
    'frozenHandoff': reference(PACK / 'handoff.json'), 'sourceIndex': reference(PACK / 'source-index.json'),
    'fullIndexFileCount': len(index), 'sourceInputs': reference(PACK / 'source-inputs.json'),
    'wholeActualTree': reference(leaf_path), 'actualCompleteLeaves': len(leaves),
    'actualTreeMerkleVerified': True, 'currentControls': 113, 'modifiedControls': 38, 'unchangedControls': 75,
    'fullInverseOperations': sum(len(r['operations']) for r in inverse['files']),
    'recursiveDeclarations': len(declaration_rows),
    'byteExactRecursiveDeclarations': sum(r['byteExact'] for r in declaration_rows),
    'criticalCustodyAndFailureDeclarationsUnchanged': len(critical_rows),
    'fullAPIAndDeclarationProof': details, 'exactGuardSuccessor': guards,
    'identityEdges': len(graph['edges']), 'fullIdentityRows': len(graph['fullIdentityRows']),
    'sourceCounts': {'app': 62, 'stage1UI': 10, 'separateNativeUI': 2, 'stagingWithSupport': 99},
    'oneNewMembershipOnly': 'AnyTypeTests/Pinkha/AnyNativeAttachmentMountedRecoveryTests.swift',
    'sourcePinPromotionOnly': 'Modules/PinkhaAnyUI/Package.swift',
    'noSwiftPBXOrNewTestImplementationInThisPacket': True,
    'historicalContractAndReceiptsPreserved': True, 'warmOriginalSelectionAndOrderPreserved': True,
    'all45ClosedTuplesPreserved': True, 'finalReleaseSHA': None, 'finalControlSHA': None,
    'bindingReady': False, 'candidateImports': 0, 'testsExecuted': 0, 'compilerInvocations': 0,
    'hostActions': 0, 'runtimeAcceptance': False,
})
print(json.dumps(seal))
