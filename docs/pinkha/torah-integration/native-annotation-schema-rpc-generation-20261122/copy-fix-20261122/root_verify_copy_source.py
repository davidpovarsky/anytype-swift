from pathlib import Path
import ast
import datetime
import hashlib
import json

BASE = Path(__file__).resolve().parent
NEW = BASE / 'packet'
OLD = BASE.parent / 'schema_rpc_generation_candidate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


manifest = json.loads((NEW / 'EXECUTION_INPUTS.json').read_text())
previous = json.loads((OLD / 'EXECUTION_INPUTS.json').read_text())
request = json.loads((BASE / 'SOURCE_REVIEW_REQUEST.json').read_text())
publication = json.loads((BASE / 'PUBLICATION_INDEX.json').read_text())
for name, row in request['executables'].items():
    path = NEW / name
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'] and blob(path) == row['git_blob']
for row in manifest['control_inputs']:
    path = NEW / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
old_controls = {x['path']: x for x in previous['control_inputs']}
new_controls = {x['path']: x for x in manifest['control_inputs']}
assert len(old_controls) == 11 and len(new_controls) == 12
for path, entry in old_controls.items():
    if path != 'generate_original_schema_rpc.py':
        assert entry == new_controls[path] and (NEW / path).read_bytes() == (OLD / path).read_bytes()
assert previous['repository_base'] == 'c21b9ebcbf255e6f4c02611069d8f40b75436a05'
assert manifest['repository_base'] == publication['parent'] == '2e4a004778d5cc29afebaa4c278a2f1a8bf5c74d'
for key, value in previous.items():
    if key not in ('control_inputs', 'repository_base'):
        assert manifest[key] == value, key
assert set(manifest) - set(previous) == {'source_copy_correction'}
assert len(manifest['original_inputs']) == 42
original_payloads_locally_present = 0
for row in manifest['original_inputs']:
    path = NEW / 'original-source' / row['repository'].split('/')[-1] / row['path']
    # The packet intentionally preserves reference copies of only some original
    # inputs. The actual driver checks all42 in the immutable original checkouts.
    # All42 descriptor rows were compared verbatim above; do not manufacture a
    # local payload verification for a reference-only row.
    old_path = OLD / 'original-source' / row['repository'].split('/')[-1] / row['path']
    assert path.exists() == old_path.exists()
    if path.exists():
        assert path.read_bytes() == old_path.read_bytes()
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'] and blob(path) == row['git_blob']
        original_payloads_locally_present += 1
old_text = (OLD / 'generate_original_schema_rpc.py').read_text()
new_text = (NEW / 'generate_original_schema_rpc.py').read_text()
start = '                target = work / (lane + "-" + kind)\n'
end = '                lanes[lane][kind] = target\n'
old_span = old_text[old_text.index(start):old_text.index(end) + len(end)]
new_span = new_text[new_text.index(start):new_text.index(end) + len(end)]
assert new_text.count(new_span) == 1 and new_text.replace(new_span, old_span) == old_text


def helpers(source):
    return {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != 'main'}


assert helpers(old_text) == helpers(new_text) and len(helpers(old_text)) == 7
controls = json.loads((BASE / 'LOCAL_PARTIAL_GIT_COPY_CONTROLS.json').read_text())
assert controls['status'] == 'LOCAL_GIT_PREPARATION_CONTROLS_PASS'
assert controls['helper_sha256'] == sha(NEW / 'copy_materialized_checkout.py')
assert controls['old_failure_reproduced'] is False
assert all(controls[k] for k in ('unfetched_blob_remained_unfetched', 'candidate_mutation_isolated', 'shared_storage_rejected_before_target_creation', 'owned_fixture_removed'))
commands = {x['label']: x for x in controls['commands']}
assert len(commands) == len(controls['commands'])
for lane in ('baseline', 'candidate'):
    command = commands[lane + '-copy']
    assert command['returncode'] == 0 and not command['stderr']
    assert json.loads(command['stdout']) == controls['copies'][lane]
assert commands['missing-before']['stdout'] == commands['missing-after']['stdout']
assert '?' in commands['missing-before']['stdout']
assert commands['reject-alternates']['returncode'] == 1
assert 'shared or alternate Git storage is refused' in commands['reject-alternates']['stderr']
assert all(c['returncode'] == 0 for k, c in commands.items() if k != 'reject-alternates')
assert '    paths:' not in (NEW / 'otzaria-schema-rpc-generation.yml').read_text()
for row in publication['files']:
    path = Path(row['local_path'])
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'] and blob(path) == row['git_blob']
receipt = {
    'schema': 'otzaria.root-rpc-materialized-copy-source-review/1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'SOURCE_AND_RETAINED_LOCAL_PREPARATION_RESULTS_REVIEW_CLEAR',
    'reviewed_executables': request['executables'],
    'complete_driver_inverse_to_actual_failed_source': sha(OLD / 'generate_original_schema_rpc.py'),
    'unchanged_original_driver_helpers': 7,
    'unchanged_original_control_files': 10,
    'control_inputs_verified': 12,
    'original_input_commitments_preserved': 42,
    'original_payloads_locally_rehashed': original_payloads_locally_present,
    'local_publication_paths_verified': len(publication['files']),
    'retained_local_fixture_commands': len(commands),
    'actual_private_copy_successes': 2,
    'original_failed_actions_environment_reproduced': False,
    'original_fixture_failure_evidence_preserved': True,
    'source_review': [
        'Full helper and one-hunk driver change reviewed; only sparse SDK lane preparation replaced.',
        'Private Git metadata/files copied with complete membership/mode/hash equality, disjoint inodes, explicit local no-lazy-fetch reads, no shared storage and no remote hydration.',
        'Both original lanes retain exact SDK HEAD and six sparse scopes; original tool recipes, proto afterimages and compile gates preserved.',
        'One bounded180-second owned process per copy; any failure remains original failure evidence and parent cleanup ownership.',
        'Final dedicated-branch workflow removes routing path filters and binds exact helper/manifest inputs. No cause is asserted for earlier zero-run routing.',
        'Updated artifact verifier requires both genuine copy receipts plus37 terminal successful commands and unchanged original generated-source/compile acceptance.',
    ],
    'review_scope_correction': 'The initial root comparison also required old control repository_base c21b to remain unchanged; the sole other previous field change is the explicit neutral failure-evidence parent2e4, now required exactly. A subsequent local-path check incorrectly assumed all42 original input reference rows had packet copies. The packet preserves only selected reference copies; this review rehashes only those present and verifies all42 immutable input commitments remain byte-identical. Actual original checkout validation stays in the unchanged driver. No product, test result, generator or workflow source was altered by this review.',
    'limitations': 'Local Git2.56.1 partial repository preparation only; actual Actions Git2.56.0 failure remains separate. No generator, protocol compile, full SDK, native or application result granted.',
    'new_tests_or_generators_by_review': 0,
    'pending': 'Neutral exact source publication/readback then one actual generation attempt.',
}
(BASE / 'ROOT_COPY_SOURCE_REVIEW.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('status', 'unchanged_original_driver_helpers', 'unchanged_original_control_files', 'control_inputs_verified', 'original_input_commitments_preserved', 'original_payloads_locally_rehashed', 'local_publication_paths_verified', 'retained_local_fixture_commands', 'actual_private_copy_successes')}))
