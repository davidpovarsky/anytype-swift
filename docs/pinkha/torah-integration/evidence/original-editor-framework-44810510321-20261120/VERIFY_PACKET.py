#!/usr/bin/env python3
"""Read-only replay of actual failed Mac source controls. No tools are executed."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

HEAD = '962d050eb36b2511616c771b08d92a78b64d2349'
TREE = 'a11f06d5f4fdf0ad94e4e8e1d2914c0b480d3cb6'
RUN = 44810510321
JOB = 136545541732
ARTIFACT = 14663449532
ARTIFACT_SHA = '717e082dc604f1f65834efa7997bcccf80f05afa2544720fb62d50ee59807829'
BRANCH = 'codex/otzaria-original-editor-framework-v4-reviewed-20261120'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def unzip(data, count):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == count, 'ZIP inventory differs')
        require(archive.testzip() is None, 'ZIP CRC differs')
        for name in names:
            path = PurePosixPath(name)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
                    'Unsafe ZIP path')
        return {name: archive.read(name) for name in names}


def verify(directory):
    directory = Path(directory)
    index = json.loads((directory / 'PACKET_INDEX.json').read_bytes())
    require(index['source'] == HEAD and index['run_id'] == RUN, 'Wrong packet identity')
    for name, record in index['files'].items():
        require(PurePosixPath(name).name == name, 'Unexpected packet path')
        data = (directory / name).read_bytes()
        require(len(data) == record['bytes'] and sha(data) == record['sha256']
                and blob(data) == record['git_blob'], 'Sealed file differs: ' + name)
    raw = (directory / 'artifact-14663449532.zip').read_bytes()
    require(len(raw) == 27990 and sha(raw) == ARTIFACT_SHA, 'Actual full artifact differs')
    outer = unzip(raw, 1)
    require(set(outer) == {'Pinkha-Native-Derived-Evidence.zip'}, 'Wrong nested archive')
    evidence = unzip(outer['Pinkha-Native-Derived-Evidence.zip'], 4)
    require(set(evidence) == {'source-admission.json', 'source-before.json',
                              'source-controls.stdout.log', 'source-controls.stderr.log'},
            'Unexpected actual execution stage')
    api = unzip((directory / 'canonical-api-and-log.zip').read_bytes(), 7)
    sources = unzip((directory / 'canonical-source-inputs.zip').read_bytes(), 25)
    read = lambda name: json.loads(evidence[name])
    meta = lambda name: json.loads(api[name])
    run = meta('RUN.json')
    require(run['id'] == RUN and run['head_sha'] == HEAD and run['run_attempt'] == 1
            and run['head_branch'] == BRANCH and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'failure'
            and run['repository']['id'] == 1289863025
            and run['repository']['full_name'] == 'davidpovarsky/anytype-swift', 'Actual run differs')
    jobs = meta('JOBS.json')
    require(jobs['total_count'] == len(jobs['jobs']) == 1, 'Wrong job inventory')
    job = jobs['jobs'][0]
    require(job['id'] == JOB and job['run_id'] == RUN and job['head_sha'] == HEAD
            and job['run_attempt'] == 1 and job['conclusion'] == 'failure', 'Actual job differs')
    steps = {row['name']: row['conclusion'] for row in job['steps']}
    require(steps['Bind original app sources resources packages and the additive target'] == 'failure',
            'Wrong actual failed step')
    for name in ['Checkout the immutable original canonical Hanlin source',
                 'Prepare and verify the original SDK snapshot',
                 'Verify actual Xcode27 and create original owned OS27 simulators',
                 'Verify the recorded original Heart producer and exact binary slices',
                 'Build the genuine framework and execute the separate binary consumer']:
        require(steps[name] == 'skipped', 'Unexpected later execution: ' + name)
    artifacts = meta('ARTIFACTS.json')['artifacts']
    require(len(artifacts) == 1, 'Unexpected artifact inventory')
    artifact = artifacts[0]
    require(artifact['id'] == ARTIFACT and artifact['size_in_bytes'] == len(raw)
            and artifact['digest'] == 'sha256:' + ARTIFACT_SHA
            and artifact['workflow_run']['id'] == RUN
            and artifact['workflow_run']['head_sha'] == HEAD
            and artifact['workflow_run']['head_branch'] == BRANCH, 'Artifact lineage differs')
    commit = meta('SOURCE_COMMIT.json')
    require(commit['sha'] == HEAD and commit['tree']['sha'] == TREE
            and [p['sha'] for p in commit['parents']] == ['f349d991c20a610038ea3e36be8502b4d4d82551'],
            'Source commit/tree/parent differs')
    compare = meta('ACTIVATION_COMPARISON.json')
    require(compare['total_commits'] == 1 and [p['filename'] for p in compare['files']] == [
        'docs/pinkha/torah-integration/evidence/original-editor-framework-v4-20261120-ROOT_REVIEW.json'],
        'Activation changed source')
    before = read('source-before.json')
    require(before['head_sha'] == HEAD and before['run_id'] == str(RUN)
            and before['run_attempt'] == '1' and before['original_swift_sources'] == 2237
            and before['status'] == 'SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN', 'Source observation differs')
    proof = meta('SOURCE_GIT_PROOF.json')
    rows = {row['path']: row for row in proof['inputs']}
    require(proof['source'] == HEAD and proof['tree'] == TREE and len(rows) == len(sources) == 25,
            'Canonical source inventory differs')
    require(set(sources) == set(before['source_inputs']) == set(rows), 'Wrong canonical path set')
    for path, expected in before['source_inputs'].items():
        data = sources[path]
        require(len(data) == expected['bytes'] and sha(data) == expected['sha256']
                and blob(data) == expected['git_blob'] == rows[path]['canonical_git_blob']
                and rows[path]['sha256'] == sha(data), 'Canonical source differs: ' + path)
    admission = read('source-admission.json')
    require(admission['source_sha'] == HEAD and admission['run_id'] == str(RUN)
            and admission['run_attempt'] == '1'
            and admission['status'] == 'SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN'
            and admission['original_framework_build'] == admission['external_consumer_build'] == 'NOT_RUN'
            and admission['native_editor_ui_tests'] == 0
            and admission['verified_runtime_observations'] == [], 'Wrong source-only admission scope')
    controls = evidence['source-controls.stderr.log'].decode('utf-8')
    rows = re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. (ok|FAIL|ERROR)$', controls)
    require(len(rows) == len(set((a, b) for a, b, _ in rows)) == 96, 'Actual Mac control count differs')
    failures = {name for name, _, result in rows if result == 'FAIL'}
    errors = {name for name, _, result in rows if result == 'ERROR'}
    require(failures == {'test_known_input_changed_during_copy_cannot_publish_success',
                         'test_changed_materialized_output_cannot_publish_success'}
            and errors == {'test_original_packager_retains_all_four_exact_raw_proofs_as_text'}
            and sum(result == 'ok' for _, _, result in rows) == 93
            and '\nRan 96 tests in ' in controls
            and controls.rstrip().endswith('FAILED (failures=2, errors=1)'), 'Actual Mac failures differ')
    require(controls.count('AssertionError: ValueError not raised') == 2
            and 'ValueError: Actual framework source list is not the complete original source closure' in controls,
            'Actual diagnostics differ')
    require('##[error]Process completed with exit code 1.' in api['JOB.log'].decode('utf-8'),
            'Actual nonzero job conclusion missing')
    return {'verification': 'PASS_READ_ONLY_ACTUAL_FAILURE_PACKET', 'workflow_conclusion': 'FAILURE',
            'source': HEAD, 'run_id': RUN, 'artifact_id': ARTIFACT, 'canonical_inputs': 25,
            'outer_members_crc_pass': 1, 'inner_members_crc_pass': 4,
            'actual_mac_python': {'executed': 96, 'passed': 93, 'failed': 2, 'errors': 1},
            'source_after': 'NOT_PRODUCED_BY_SOURCE_ONLY_PREBUILD_STEP',
            'swift_compile': 'NOT_RUN', 'sdk_preparation': 'NOT_RUN', 'heart_install': 'NOT_RUN',
            'framework_build': 'NOT_RUN', 'consumer_build': 'NOT_RUN', 'simulator_runtime': 'NOT_RUN',
            'editable_mount': 'NOT_EXPOSED', 'apple_or_test_reruns_by_verifier': 0}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent),
                     indent=2, sort_keys=True))
