#!/usr/bin/env python3
"""Finite source-only compatibility composition; no candidate module is imported."""
import ast
import base64
import copy
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path('/workspace/scratch/ae335eba85e3')
OUT = ROOT / 'shared62-native26-compatibility-source/prepared2'
STORE_PACKET = ROOT / 'native26-store-bookmark-compatibility-source/prepared3'
PREFIX = 'Tools/PinkhaDualEngineRuntime/'
BASE = '5a45fe4af2c4601faad181f81d391057c1237654'
BASE_TREE = '13578db08a5e215fd70e88209e6ec409135440e2'
MOUNTED = 'AnyTypeTests/Pinkha/AnyNativeAttachmentMountedRecoveryTests.swift'
PACKAGE = 'Modules/PinkhaAnyUI/Package.swift'
CONTRACT = PREFIX + 'hosted_shared_build/native23_build_contract.json'
OWNER = PREFIX + 'hosted_shared_build/run.py'
WITNESS = PREFIX + 'hosted_native26_properties/source_witnesses.json'


def ident(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
            'gitMode': '100644'}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def ref(path):
    return {'localPath': str(path), **ident(path.read_bytes())}


def constants(raw):
    result = {}
    for node in ast.parse(raw.decode()).body:
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


def assignment(raw, name):
    text = raw.decode()
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    assert len(nodes) == 1, name
    return ast.get_source_segment(text, nodes[0])


def declarations(raw):
    text = raw.decode()
    return {n.name: ast.get_source_segment(text, n).encode() for n in ast.parse(text).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def inverse_operations(before, after):
    a, b = before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True)
    operations = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != 'equal':
            operations.append({'beforeLine': i + 1, 'afterLine': k + 1,
                               'beforeUTF8': ''.join(a[i:j]), 'afterUTF8': ''.join(b[k:l])})
    restored = list(b)
    for op in reversed(operations):
        pos = op['afterLine'] - 1
        fragment = op['afterUTF8'].splitlines(keepends=True)
        assert restored[pos:pos + len(fragment)] == fragment
        restored[pos:pos + len(fragment)] = op['beforeUTF8'].splitlines(keepends=True)
    assert ''.join(restored).encode() == before
    forward = list(a)
    for op in reversed(operations):
        pos = op['beforeLine'] - 1
        fragment = op['beforeUTF8'].splitlines(keepends=True)
        assert forward[pos:pos + len(fragment)] == fragment
        forward[pos:pos + len(fragment)] = op['afterUTF8'].splitlines(keepends=True)
    assert ''.join(forward).encode() == after
    return operations


assert not OUT.exists(), 'Do not overwrite a frozen source proposal'
census_path = STORE_PACKET / 'current-control-reference-census.json'
census = json.loads(census_path.read_text())
assert census['actualPublishedBase'] == BASE and census['actualPublishedBaseTree'] == BASE_TREE
original = {}
for path, row in census['current113'].items():
    raw = Path(row['localPath']).read_bytes()
    assert all(ident(raw)[k] == row[k] for k in ('bytes', 'sha256', 'gitBlob', 'gitMode')), path
    original[path] = raw
assert len(original) == 113
semantic = dict(original)
seeds, edits = set(), []


def edit(path, old, new, reason, count=1):
    old = old.encode() if isinstance(old, str) else old
    new = new.encode() if isinstance(new, str) else new
    raw = semantic[path]
    assert old != new and raw.count(old) == count, (path, old[:120], raw.count(old), count)
    semantic[path] = raw.replace(old, new)
    seeds.add(path)
    edits.append({'path': path, 'reason': reason, 'beforeUTF8': old.decode(),
                  'afterUTF8': new.decode(), 'occurrences': count})


def edit_json(path, value, reason):
    assert encoded(json.loads(semantic[path])) == semantic[path], path
    edit(path, semantic[path], encoded(value), reason)


# Store successor is the exact already sealed two-scalar change, with all history retained.
new_witness = (STORE_PACKET / 'after' / WITNESS).read_bytes()
assert ident(new_witness)['sha256'] == '5a7d243716c5189c169424a8798e1d31145034f5caf032a9be46c529d1a0a3ac'
edit(WITNESS, original[WITNESS], new_witness, 'Exact sealed live Store c653 to b91e witness only')

# Derive the same historical profile through its existing finite mechanism.
profile_path = ROOT / 'hosted-inspector14-native26-source/prepared2/originals/original-native23-profile.py'
profile_original = profile_path.read_bytes()
assert ident(profile_original)['sha256'] == '3fd3049737f4be72f4257a04e5ca94085e6d9e11cd3916257ced4bf2e8943aa6'
package_before = (ROOT / 'w2-bookmark-ui7-3d2-intake/before' / PACKAGE).read_bytes()
package_after = (ROOT / 'w2-bookmark-ui7-3d2-intake/source' / PACKAGE).read_bytes()
assert ident(package_before)['sha256'] == '33a710dfb7793f943c85432b28cafa1fef0fa081da35ba295e092937a7c91b35'
assert ident(package_after)['sha256'] == '173395dde0549705a14b51a7d36fb2799e80f659cc7211d13798710e1f0b1096'


def project_profile(values):
    text = profile_original.decode()
    for key in ('PROFILE_SOURCE_COMPATIBILITY', 'PROFILE_DECLARATION_COMPATIBILITY'):
        for row in values[key]:
            assert text.count(row['beforeUTF8']) == 1
            text = text.replace(row['beforeUTF8'], row['afterUTF8'], 1)
    result = text.encode()
    assert len(result) == values['PROFILE_COMPATIBLE_BYTES']
    assert ident(result)['sha256'] == values['PROFILE_COMPATIBLE_SHA256']
    for key in ('PROFILE_DECLARATION_COMPATIBILITY', 'PROFILE_SOURCE_COMPATIBILITY'):
        for row in reversed(values[key]):
            assert text.count(row['afterUTF8']) == 1
            text = text.replace(row['afterUTF8'], row['beforeUTF8'], 1)
    assert text.encode() == profile_original
    return result


profiles = []
profile_proofs = []
for lane in ('hosted_native23', 'hosted_native25', 'hosted_native26_properties'):
    path = PREFIX + lane + '/control.py'
    prior_constants = constants(original[path])
    previous = project_profile(prior_constants)
    updated_rows = copy.deepcopy(prior_constants['PROFILE_SOURCE_COMPATIBILITY'])
    rows = [row for row in updated_rows if row['path'] == PACKAGE]
    assert len(rows) == 1
    row = rows[0]
    old_line = row['afterUTF8']
    assert old_line.count(ident(package_before)['sha256']) == 1
    row['afterUTF8'] = old_line.replace(ident(package_before)['sha256'], ident(package_after)['sha256'])
    assert row['sourceAfterSHA256'] == ident(package_before)['sha256'] and row['sourceAfterBytes'] == 2051
    row['sourceAfterSHA256'], row['sourceAfterBytes'] = ident(package_after)['sha256'], len(package_after)
    projected = previous.replace(old_line.encode(), row['afterUTF8'].encode(), 1)
    assert previous.count(old_line.encode()) == 1 and len(projected) == len(previous) == 57360
    edit(path, assignment(semantic[path], 'PROFILE_SOURCE_COMPATIBILITY'),
         'PROFILE_SOURCE_COMPATIBILITY = ' + repr(updated_rows), 'Only final UI Package pin/identity changes in the original seven-row transformation')
    edit(path, assignment(semantic[path], 'PROFILE_COMPATIBLE_SHA256'),
         'PROFILE_COMPATIBLE_SHA256 = ' + repr(ident(projected)['sha256']), 'Bind complete same-size derived profile')
    assert project_profile(constants(semantic[path])) == projected
    assert declarations(original[path]) == declarations(semantic[path])
    assert prior_constants['PROFILE_DECLARATION_COMPATIBILITY'] == constants(semantic[path])['PROFILE_DECLARATION_COMPATIBILITY']
    a, b = ast.parse(previous), ast.parse(projected)
    assert len(a.body) == len(b.body)
    changed_top = []
    for x, y in zip(a.body, b.body):
        if ast.get_source_segment(previous.decode(), x) != ast.get_source_segment(projected.decode(), y):
            assert isinstance(x, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SOURCE_FILES' for t in x.targets)
            old, new = ast.literal_eval(x.value), ast.literal_eval(y.value)
            assert len(old) == len(new) == 28 and {p for p in old if old[p] != new[p]} == {PACKAGE}
            changed_top.append('SOURCE_FILES')
    assert changed_top == ['SOURCE_FILES']
    profiles.append(projected)
    profile_proofs.append({'path': path, 'beforeProjection': ident(previous), 'afterProjection': ident(projected),
                           'onlySourceMapEntryChanged': PACKAGE, 'everyProfileDeclarationByteExact': True,
                           'everyControlDeclarationByteExact': True, 'originalProfileFullInverseExact': True})
assert len(set(profiles)) == 1
profile_new = profiles[0]

old_contract = json.loads(original[CONTRACT])
new_contract = copy.deepcopy(old_contract)
assert new_contract['sourcePathPins'][PACKAGE] == ident(package_before)['sha256']
new_contract['sourcePathPins'][PACKAGE] = ident(package_after)['sha256']
new_contract['sourceCompatibilitySuccessor'] = {
    'status': 'EXACT_BOOKMARK_UI_MANIFEST_SOURCE_ONLY_RUNTIME_CLOSED',
    'previousNative26Contract': ident(original[CONTRACT]),
    'previousNative26Compatibility': old_contract['sourceCompatibilitySuccessor'],
    'currentSourcePinCount': 28, 'currentSourceProjectionBytes': len(profile_new),
    'currentSourceProjectionSHA256': ident(profile_new)['sha256'],
    'exactNewSourcePins': {PACKAGE: {'before': ident(package_before), 'after': ident(package_after)}},
    'unchangedPreviousNative26PinCount': 27,
    'allOriginalNative26AndHistorySwiftUnchanged': True,
    'allOriginalCompilerFunctionBodiesUnchanged': True,
    'allPreviousCompilerReceiptsRequireNewExactContractAndInputs': True,
    'actualSourceCommit': BASE, 'finalSourceSDKNativeTuple': None, 'runtimeReady': False,
}
assert {k: v for k, v in new_contract.items() if k not in ('sourcePathPins', 'sourceCompatibilitySuccessor')} == {
       k: v for k, v in old_contract.items() if k not in ('sourcePathPins', 'sourceCompatibilitySuccessor')}
edit_json(CONTRACT, new_contract, 'Only current UI Package pin plus append-preserved contract provenance; original compiler budget and Swift inputs exact')

# One additional already-published synchronized test file, never a synthetic source.
inventory = json.loads((STORE_PACKET / 'shared-build-test-source-inventory.json').read_text())
native62 = set(inventory['selectedAppNative'])
owner_values = constants(original[OWNER])
assert native62 - set(owner_values['COMPOSED_NATIVE_SOURCE_PATHS']) == {MOUNTED}
assert len(native62) == 62 and len(owner_values['COMPOSED_NATIVE_SOURCE_PATHS']) == 61
assert set(inventory['selectedStage1UI']) == set(owner_values['COMPOSED_STAGE1_SOURCE_PATHS'])
edit(OWNER, assignment(semantic[OWNER], 'COMPOSED_NATIVE_SOURCE_PATHS'),
     'COMPOSED_NATIVE_SOURCE_PATHS = frozenset(' + repr(tuple(sorted(native62))) + ')',
     'Add only original mounted attachment recovery source to the literal existing61 set')
edit(OWNER, '# Exact reviewed composition: published50 synchronized + UIKit2 + published9 external.',
     '# Exact reviewed composition: published50 synchronized + UIKit2 + mounted1 + published9 external.',
     'Explain the sole additional original mounted source accurately')
edit(OWNER, 'reviewed61/10 composition', 'reviewed62/10 composition', 'Accurate finite source-membership diagnostic')
edit(OWNER, '{"native": 61, "stage1UI": 10, "native23UI": 2}',
     '{"native": 62, "stage1UI": 10, "native23UI": 2}', 'Exact same producer membership count; Stage1 and UI-runner inputs unchanged')

# Existing identical reader contracts, same APIs and guards; only their exact source count changes.
count_paths = []
for path in original:
    if path.endswith(('/admission.py', '/native23_inputs.py', '/native23_receipts.py')):
        old = '{"native": 61, "stage1UI": 10, "native23UI": 2}'
        count = semantic[path].count(old.encode())
        if count:
            assert count == 1
            edit(path, old, '{"native": 62, "stage1UI": 10, "native23UI": 2}', 'Propagate exact62/10/2 admission through existing reader', count)
            count_paths.append(path)
        for old, new in [('reviewed61-native/10-Stage1', 'reviewed62-native/10-Stage1'),
                         ('Actual61 App, 10 Stage1', 'Actual62 App, 10 Stage1')]:
            if old.encode() in semantic[path]:
                edit(path, old, new, 'Keep original refusal diagnostic accurate')
assert len(count_paths) == 14, count_paths
edit(PREFIX + 'hosted_native23/activation.json', 'successful actual 61/10/2 producer',
     'successful actual 62/10/2 producer', 'Closed reason names the exact new source membership')
t5_activation = PREFIX + 'hosted_t5/activation.json'
value = json.loads(semantic[t5_activation]); assert value['compiledSourceCounts'] == [61, 10, 2]
value['compiledSourceCounts'] = [62, 10, 2]
edit_json(t5_activation, value, 'Closed T5 consumes the same reviewed62/10/2 products; fixture/crypto/120s and plans unchanged')
edit(PREFIX + 'hosted_t5/profile.py', 'value["compiledSourceCounts"] == [61, 10, 2]',
     'value["compiledSourceCounts"] == [62, 10, 2]', 'Same closed T5 activation schema with exact new compiler membership')
account_profile = PREFIX + 'hosted_account_runtime/profile.json'
value = json.loads(semantic[account_profile]); assert value['compilerScope']['currentNativeSourcePaths'] == 61
value['compilerScope']['currentNativeSourcePaths'] = 62
edit_json(account_profile, value, 'Account four methods/five cases unchanged; update current enclosing compiler path count only')

# Warm App product admission remains genuine Mac admission, without a Native26 dependency.
warm = PREFIX + 'warm_focus_editor/'
value = json.loads(semantic[warm + 'source-membership.json'])
assert set(value['native']) == set(owner_values['COMPOSED_NATIVE_SOURCE_PATHS'])
value['native'] = sorted(native62)
edit_json(warm + 'source-membership.json', value, 'Add only the original mounted source to warm App membership; original nine external paths/ten UI paths remain')
value = json.loads(semantic[warm + 'activation.json'])
assert value['requiredAppCompilerSources'] == 61
value['requiredAppCompilerSources'] = 62
edit_json(warm + 'activation.json', value, 'Closed warm tuple expects62 App paths; original focus22/34, preparation and four UI retained')
for old, new, count in [
    ('App61/Stage1UI10', 'App62/Stage1UI10', 1),
    ('len(native) == 61 and len(ui) == 10', 'len(native) == 62 and len(ui) == 10', 1),
    ('original61/10 tracked', 'original62/10 tracked', 1),
    ('every61/10 input', 'every62/10 input', 1),
    ('len(inventory["sources"]) == 71', 'len(inventory["sources"]) == 72', 1),
    ('== (61, 10)', '== (62, 10)', 1),
    ('"native": 61, "stage1UI": 10', '"native": 62, "stage1UI": 10', 1),
]:
    edit(warm + 'admission.py', old, new, 'Finite warm source count follows exact membership while all physical/compiler/custody guards remain', count)
for old, new, count in [
    ('== (61, 10)', '== (62, 10)', 1),
    ('len(set(value["native"])) == 61', 'len(set(value["native"])) == 62', 1),
    ('App61/Stage1UI10 source', 'App62/Stage1UI10 source', 1),
    ('"app": 61, "stage1UI": 10', '"app": 62, "stage1UI": 10', 1),
]:
    edit(warm + 'profile_binding.py', old, new, 'Same warm lane/order/validators; report exact new enclosing App source count', count)
edit(warm + 'run.py', 'Closed current warm App61/Stage1UI10 consumer',
     'Closed current warm App62/Stage1UI10 consumer', 'Accurate module docstring; every runtime declaration remains original')

# Exact current-file dependency graph. Do not change historical external originals or self-provenance.
by_sha = {}
for path, raw in original.items():
    by_sha.setdefault(ident(raw)['sha256'], []).append(path)
reachable, queue, edges = set(seeds), sorted(seeds), []
while queue:
    producer = queue.pop(0)
    digest = ident(original[producer])['sha256']
    for consumer, raw in sorted(original.items()):
        if consumer != producer and digest.encode() in raw:
            edge = {'producer': producer, 'consumer': consumer, 'beforeSHA256': digest,
                    'occurrences': raw.count(digest.encode())}
            if edge not in edges:
                edges.append(edge)
            if consumer not in reachable:
                reachable.add(consumer); queue.append(consumer)

identity_edges = []
for consumer in sorted(reachable):
    if not consumer.endswith('.json'):
        continue
    def walk(value, keys=()):
        if isinstance(value, dict):
            old_sha = value.get('sha256')
            producers = by_sha.get(old_sha, []) if isinstance(old_sha, str) else []
            current = [p for p in producers if p in reachable and p != consumer]
            if current:
                primary = ident(original[current[0]])
                for field in ('bytes', 'gitBlob', 'gitMode'):
                    if field in value:
                        assert value[field] == primary[field], (consumer, keys, field, value[field], primary[field])
                identity_edges.append({'consumer': consumer, 'keys': list(keys), 'producers': current,
                                       'before': primary, 'identityFields': [k for k in primary if k in value]})
            for key, item in value.items():
                walk(item, keys + (key,))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, keys + (i,))
    walk(json.loads(original[consumer]))

projected = dict(semantic)
iterations = 0
for _ in range(32):
    replacements = {}
    for path in reachable:
        old_sha, new_sha = ident(original[path])['sha256'], ident(projected[path])['sha256']
        if old_sha in replacements:
            assert replacements[old_sha] == new_sha, 'Identical source copies must remain identical'
        replacements[old_sha] = new_sha
    updated = {}
    for consumer, seed in semantic.items():
        raw = seed
        for old_sha, new_sha in sorted(replacements.items()):
            if old_sha == ident(original[consumer])['sha256']:
                continue
            if old_sha.encode() in original[consumer] and old_sha != new_sha:
                assert raw.count(old_sha.encode()) == original[consumer].count(old_sha.encode()), consumer
                raw = raw.replace(old_sha.encode(), new_sha.encode())
        identities = [e for e in identity_edges if e['consumer'] == consumer]
        if identities:
            value = json.loads(raw)
            for edge in identities:
                row = value
                for key in edge['keys']:
                    row = row[key]
                values = {tuple(sorted(ident(projected[p]).items())) for p in edge['producers']}
                assert len(values) == 1
                new_identity = dict(next(iter(values)))
                for field in edge['identityFields']:
                    row[field] = new_identity[field]
            raw = encoded(value)
        updated[consumer] = raw
    iterations += 1
    if updated == projected:
        break
    projected = updated
else:
    raise AssertionError('Exact dependency graph did not converge')
changed = {p for p in original if original[p] != projected[p]}
assert changed == reachable
for edge in edges:
    edge['afterSHA256'] = ident(projected[edge['producer']])['sha256']
    assert edge['beforeSHA256'].encode() not in projected[edge['consumer']]
    assert projected[edge['consumer']].count(edge['afterSHA256'].encode()) >= edge['occurrences']
for edge in identity_edges:
    value = json.loads(projected[edge['consumer']])
    for key in edge['keys']:
        value = value[key]
    edge['after'] = ident(projected[edge['producers'][0]])
    assert all(value[field] == edge['after'][field] for field in edge['identityFields'])

# Semantic declaration deltas are exactly source counts; all original process/lifetime code stays.
function_proof = []
for path in sorted(changed):
    if not path.endswith('.py'):
        continue
    a, b, seed = declarations(original[path]), declarations(projected[path]), declarations(semantic[path])
    assert a.keys() == b.keys() == seed.keys(), path
    semantic_changed = [name for name in a if a[name] != seed[name]]
    changed_names = [name for name in a if a[name] != b[name]]
    function_proof.append({'path': path, 'originalDeclarationCount': len(a),
                           'changedDeclarationNames': changed_names,
                           'semanticCountOrDiagnosticDeclarations': semantic_changed,
                           'hashOnlyDeclarations': [n for n in changed_names if n not in semantic_changed],
                           'unchangedDeclarations': {n: ident(a[n]) for n in a if n not in changed_names},
                           'semanticLiteralOperations': [e for e in edits if e['path'] == path]})
    forbidden = {'Commands', 'FirstFailure', 'PhaseCustody', 'StageResultWrites', 'execute_lane', 'final_inputs',
                 'file_only_postflight', 'final_input_boundary', 'retain_native23_failure', 'retain_native23_receipt',
                 'run_phase', 'stage_and_build', 'build', 'producer_context', 'receipt_contract', 'main'}
    # Existing producer_context changes only exact membership literals in the hosted readers.
    if path.endswith('/admission.py') and path != warm + 'admission.py':
        forbidden.remove('producer_context')
    assert not (set(semantic_changed) & forbidden), (path, semantic_changed)
assert declarations(original[warm + 'run.py']) == declarations(projected[warm + 'run.py'])
assert original[warm + 'priority-runtime-selection.closed.json'] == projected[warm + 'priority-runtime-selection.closed.json']
assert original[PREFIX + 'warm_forward/priority-runtime-selection.closed.json'] == projected[PREFIX + 'warm_forward/priority-runtime-selection.closed.json']
assert json.loads(original[PREFIX + 'hosted_core24/profile.json'])['originalCompilerPathCount'] == 61
assert original[PREFIX + 'hosted_core24/profile.json'] == projected[PREFIX + 'hosted_core24/profile.json']
actual_receipt_path = ROOT / 'wave3-bookmark-mounted-result-source-integration-prepared/actual1/receipt.original.json'
assert ident(actual_receipt_path.read_bytes())['sha256'] == '58c035a658e6264d55284bae538a175f00fb5bb16990e1c3863186f66357a1c8'
receipt = json.loads(actual_receipt_path.read_text())
assert receipt['head'] == receipt['normalPushReadback'] == BASE and receipt['tree'] == BASE_TREE
closed_rows = receipt['outputPins']['closedActivation']
assert len(closed_rows) == 45
for row in closed_rows:
    value = json.loads(projected[row['path']])
    for key, expected in row['fields'].items():
        assert value[key] == expected, (row['path'], key)

# Write only owned reviewable outputs after all source checks succeeded.
OUT.mkdir(parents=True)
def output(relative, raw):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw)
    return ref(path)
def json_output(relative, value):
    return output(relative, encoded(value))

source_rows, inverses, patches = {}, [], []
for path in sorted(changed):
    a, b = original[path], projected[path]
    output('before/' + path, a); output('after/' + path, b)
    source_rows[path] = {'status': 'M', 'before': ident(a), 'after': ident(b),
                         'beforeBase64': base64.b64encode(a).decode(), 'base64': base64.b64encode(b).decode()}
    inverses.append({'path': path, 'before': ident(a), 'after': ident(b), 'operations': inverse_operations(a, b)})
    patches.append(''.join(difflib.unified_diff(a.decode().splitlines(keepends=True), b.decode().splitlines(keepends=True),
                  fromfile='a/' + path, tofile='b/' + path)))
output('evidence/original-native23-profile.py', profile_original)
output('evidence/bookmark-compatible-native26-profile.py', profile_new)
json_output('evidence/source-diff.json', {'originalUTF8': ''.join(patches), 'sha256': hashlib.sha256(''.join(patches).encode()).hexdigest()})
json_output('evidence/full-literal-inverses.json', {'files': inverses, 'modifiedPaths': len(changed),
                                                  'literalOperationCount': sum(len(r['operations']) for r in inverses)})
json_output('evidence/declaration-preservation.json', {'files': function_proof, 'candidateImports': 0,
                                                     'everyOriginalCustodyAndFirstFailureDeclarationUnchanged': True})
json_output('evidence/current-identity-cascade.json', {'seeds': sorted(seeds), 'changedPaths': sorted(changed),
                                                    'unchangedPaths': sorted(set(original) - changed),
                                                    'iterations': iterations, 'edges': edges,
                                                    'fullIdentityRows': identity_edges})
json_output('evidence/native-profile-source-proof.json', {'original': ref(profile_path), 'lanes': profile_proofs,
                                                        'originalHistoricalSourcePreserved': True,
                                                        'NativeLaunch26AndHistory1WholeSourceUnchanged': True,
                                                        'runtimeReady': False})
json_output('evidence/source-context.json', {'actualBase': BASE, 'actualTree': BASE_TREE,
                                          'actualReceipt': ref(actual_receipt_path), 'current113': census['current113'],
                                          'unchanged45ClosedFieldTuples': closed_rows,
                                          'retainedHistoricalCore24CompilerCount61': True,
                                          'readyForBuild': False, 'bindingReady': False,
                                          'finalReleaseSHA': None, 'finalControlSHA': None,
                                          'actualCompilerReceipts': None, 'runtimeExecuted': False})
for name in ['complete99-source-inputs.json', 'shared-build-test-source-inventory.json', 'prospective-runtime-selection.json',
             'store-method-preservation.json', 'full-source-witness-inverse.json']:
    output('evidence/' + name, (STORE_PACKET / name).read_bytes())
json_output('source-inputs.json', {'schema': 'pinkha-shared62-native26-compatibility-source-inputs/v1',
                                 'actualBase': BASE, 'actualTree': BASE_TREE, 'files': source_rows,
                                 'modifiedControlPaths': len(changed), 'newProductSources': 0,
                                 'newTestImplementations': 0, 'bindingReady': False,
                                 'finalReleaseSHA': None, 'finalControlSHA': None,
                                 'testsExecuted': 0, 'compilerInvocations': 0, 'hostActions': 0})
index = {p.relative_to(OUT).as_posix(): ident(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file()}
json_output('source-index.json', {'schema': 'pinkha-shared62-native26-source-index/v1', 'files': index})
handoff = {'schema': 'pinkha-shared62-native26-source-handoff/v1', 'status': 'SOURCE_ONLY_FOR_REVIEW',
           'actualBase': BASE, 'actualTree': BASE_TREE, 'modifiedControlPaths': len(changed),
           'sourceInputs': ref(OUT / 'source-inputs.json'), 'sourceIndex': ref(OUT / 'source-index.json'),
           'inverse': ref(OUT / 'evidence/full-literal-inverses.json'),
           'declarations': ref(OUT / 'evidence/declaration-preservation.json'),
           'currentSourceCounts': {'native': 62, 'stage1UI': 10, 'native26UI': 2, 'sourceAndSupport': 99},
           'current45ClosedFieldTuplesPreserved': True, 'warm22_34PreparationFourUIOrderUnchanged': True,
           'historicalNative23ProfileUnchanged': True, 'Native26TwoSwiftAnd900_1200BoundsUnchanged': True,
           'bindingReady': False, 'finalReleaseSHA': None, 'finalControlSHA': None,
           'testsExecuted': 0, 'compilerInvocations': 0, 'hostActions': 0,
           'authoringSource': ref(Path(__file__))}
json_output('handoff.json', handoff)
print(json.dumps({'status': 'SOURCE_ONLY_PREPARED', 'handoff': ref(OUT / 'handoff.json'),
                  'changedControls': len(changed), 'unchangedControls': len(original) - len(changed),
                  'sourceCounts': handoff['currentSourceCounts']}))
