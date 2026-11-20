#!/usr/bin/env python3
"""Verify retained Apple49 evidence; does not run Swift, XCTest or controls."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

F = 'e140790e9ebf03b17ce3a241e0e3197301ea1365'
TREE = '78b918354dce380b0725e2a67fa81f1ae71c339c'
BRANCH = 'codex/otzaria-original-document-constructor49-reviewed-20261120'
RUN, JOB, ARTIFACT = 44791343024, 136479505253, 14659569956
ZIP_SHA = 'd51f5d0717c28d621e5c2a7c849967592384bc895674ad2ca9763d74d2d884d3'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(b):
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + bytes([0]) + b).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(value, message):
    if not value:
        raise ValueError(message)


def zip_record(path):
    with zipfile.ZipFile(path) as z:
        info = z.infolist()
        require(len({x.filename for x in info}) == len(info), 'Repeated ZIP member')
        require(z.testzip() is None, 'ZIP CRC failure')
        for x in info:
            p = Path(x.filename)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in x.filename,
                    'Unsafe archive member')
            require((x.external_attr >> 16) & 0o170000 != 0o120000, 'Symlink member')
        return {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes()),
                'members': len(info), 'crc_verified': True,
                'uncompressed_bytes': sum(x.file_size for x in info)}


def verify(root):
    evidence = root / 'raw/evidence'
    source = root / 'source'
    api = root / 'api'
    run, jobs, artifacts = (load(api / (x + '.json')) for x in ['RUN', 'JOBS', 'ARTIFACTS'])
    require(run['id'] == RUN and run['head_sha'] == F and run['head_branch'] == BRANCH
            and run['run_attempt'] == 1 and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'success', 'Run identity/outcome')
    require(run['path'] == '.github/workflows/pinkha-original-document-constructor.yml', 'Workflow path')
    require(run['repository']['full_name'] == 'davidpovarsky/anytype-swift'
            and run['repository']['id'] == run['head_repository']['id'] == 1289863025, 'Repository identity')
    require(jobs['total_count'] == len(jobs['jobs']) == 1, 'Job inventory')
    job = jobs['jobs'][0]
    require(job['id'] == JOB and job['head_sha'] == F and job['run_id'] == RUN
            and job['status'] == 'completed' and job['conclusion'] == 'success', 'Job identity/outcome')
    require(artifacts['total_count'] == len(artifacts['artifacts']) == 1, 'Artifact inventory')
    artifact = artifacts['artifacts'][0]
    require(artifact['id'] == ARTIFACT and artifact['expired'] is False
            and artifact['size_in_bytes'] == 797939 and artifact['digest'] == 'sha256:' + ZIP_SHA,
            'Artifact size/digest')
    require(artifact['name'] == f'Otzaria-Original-Constructors-Apple-{F}-{RUN}-1', 'Artifact name')
    wr = artifact['workflow_run']
    require(wr['id'] == RUN and wr['head_sha'] == F and wr['head_branch'] == BRANCH
            and wr['repository_id'] == wr['head_repository_id'] == 1289863025, 'Artifact source lineage')
    outer = zip_record(root / 'raw/apple49-44791343024-attempt1.zip')
    require(outer['sha256'] == ZIP_SHA and outer['bytes'] == 797939 and outer['members'] == 1, 'Retained outer ZIP')
    inner_path = root / 'extracted/Pinkha-Native-Derived-Evidence.zip'
    inner = zip_record(inner_path)
    require(inner['members'] == 157, 'Retained inner ZIP count')
    with zipfile.ZipFile(root / 'raw/apple49-44791343024-attempt1.zip') as z:
        require(z.read(z.namelist()[0]) == inner_path.read_bytes(), 'Inner archive bytes')
    with zipfile.ZipFile(inner_path) as z:
        for i in z.infolist():
            if not i.is_dir():
                require((evidence / i.filename).read_bytes() == z.read(i), 'Extracted bytes: ' + i.filename)
    require((evidence / 'OriginalConstructors.xcresult/database.sqlite3').is_file(), 'Complete xcresult missing')

    commit = load(api / 'SOURCE_COMMIT.json')
    canonical = load(api / 'CANONICAL_SOURCE_TREE.json')
    require(commit['sha'] == F and commit['tree']['sha'] == TREE
            and commit['parents'][0]['sha'] == 'b4ece8c2129124f6ec8ed00143e156b9d0e11383', 'Source commit')
    require(canonical['source_commit'] == F and canonical['source_tree'] == TREE
            and canonical['truncated'] is False and canonical['query_commit_entries_equal_actual_tree'], 'Canonical source projection')
    tree = {x['path']: x for x in canonical['entries']}
    source_records = []
    for p in sorted(source.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        relative = p.relative_to(source).as_posix()
        raw = p.read_bytes()
        require(relative in tree and tree[relative]['type'] == 'blob'
                and tree[relative]['sha'] == blob(raw) and tree[relative]['size'] == len(raw), 'Canonical Git bytes: ' + relative)
        source_records.append({'path': relative, 'bytes': len(raw), 'sha256': sha(raw), 'git_blob': blob(raw)})
    require(len(source_records) == 40, 'Reviewed result source closure count')

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / 'Tools/Hanlin'))
    import run_host_tests as host
    import original_document_constructor_profile as profile
    import run_original_document_constructor_controls as controls_driver
    manifest = profile.manifest()
    controls_manifest = load(source / 'Tools/Hanlin/original_document_constructor_controls.json')
    canonical_trees = {x['path']: x['sha'] for x in canonical['trees']}
    require(manifest['application_trees'] == canonical_trees, 'Original five product trees')
    expected_old = {suite + '/' + method for suite, item in manifest['original_suites'].items() for method in item['methods']}
    expected_new = {profile.SUITE + '/' + x for x in manifest['constructor_suite']['methods']}
    expected = expected_old | expected_new
    require(len(expected_old) == 43 and len(expected_new) == 6 and len(expected) == 49, 'Exact 43+6 inventory')
    for suite, item in manifest['original_suites'].items():
        raw = (source / item['path']).read_bytes()
        require(sha(raw) == item['sha256'], 'Original suite bytes')
        require(profile.original.validate_declarations(raw.decode(), suite, item['methods']) ==
                {suite + '/' + x for x in item['methods']}, 'Original suite declarations')
    item = manifest['constructor_suite']
    raw = (source / item['path']).read_bytes()
    require(sha(raw) == item['sha256'] and profile.validate_constructor_declarations(raw.decode(), item['methods']) == expected_new,
            'Actual six constructor declarations')
    for path, expected_sha in manifest['constructor_sources'].items():
        require(sha((source / path).read_bytes()) == expected_sha, 'Constructor production bytes')

    execution = load(evidence / 'execution.json')
    selection = load(evidence / 'original-constructors-selection.json')
    summary = load(evidence / 'original-constructors-summary.json')
    tests = load(evidence / 'original-constructors-tests.json')
    preflight = load(evidence / 'preflight/preflight.json')
    for receipt in (execution, selection, preflight):
        require(receipt['source_sha'] == F and receipt['run_id'] == str(RUN) and receipt['run_attempt'] == '1', 'Receipt identity')
    require(selection['methods'] == execution['expected_methods'] == sorted(expected), 'Selection exactly 49')
    require(selection['test_source_sha256'] == execution['test_source_hashes'], 'Actual test source hashes')
    for path, expected_sha in selection['test_source_sha256'].items():
        require(sha((source / path).read_bytes()) == expected_sha, 'Selection test source')
    require(execution['status'] == 'ORIGINAL_CONSTRUCTORS_COMPONENT_PASS' and execution['phase'] == 'COMPLETE'
            and execution['post_execution_source_verified'] is True and execution['build_succeeded'] is True
            and execution['test_command_exit_code'] == 0 and execution['release_accepted'] is False, 'Execution disposition')
    udid = preflight['selected']['ipad']['udid']
    actual = host.validate_results(summary, tests, expected, udid, host.HostTestProfile.ORIGINAL_CONSTRUCTORS)
    require(actual == execution['actual'], 'Original validator replay differs from retained result')
    require(sha((evidence / 'original-constructors-summary.json').read_bytes()) == execution['raw_summary_sha256']
            and sha((evidence / 'original-constructors-tests.json').read_bytes()) == execution['raw_tests_sha256'], 'Raw result hash')
    require(sha((source / 'Tools/Hanlin/original_document_constructor_profile.json').read_bytes()) ==
            selection['profile_manifest_sha256'] == execution['constructor_manifest_sha256'], 'Actual profile bytes')

    controls = load(evidence / 'controls/controls.json')
    require(controls['candidate_sha'] == F and controls['baseline_sha'] == controls_manifest['baseline_sha']
            and controls['candidate_inputs_unchanged'] is True and controls['original_baseline_restored'] is True,
            'Control source scope or restoration')
    for path, item in controls['before']['candidate'].items():
        raw = (source / path).read_bytes()
        require(item == {'bytes': len(raw), 'sha256': sha(raw)}, 'Actual control input: ' + path)
    control_results = {}
    for key, name, names, count in (
        ('original74', 'original74-baseline-profile', controls_manifest['original74_methods'], 74),
        ('candidate_gate_controls', 'candidate49-gate-controls', controls_manifest['candidate_control_methods'], 23),
    ):
        rec = load(evidence / 'controls' / (name + '.json'))
        raw = (evidence / 'controls' / (name + '.log')).read_bytes()
        require(controls[key] == rec and rec['status'] == 'PASS' and rec['partial_execution'] == 'NONE'
                and sha(raw) == rec['output_sha256'], 'Raw Mac control receipt')
        names_actual = controls_driver.exact_success(raw.decode(), names, rec['returncode'])
        require(names_actual == rec['verified_complete_controls'] and len(names_actual) == count, 'Exact Mac controls')
        control_results[key] = {'passed': count, 'failed': 0, 'skipped': 0, 'names': names_actual,
                                'started_at': rec['started_at'], 'finished_at': rec['finished_at'],
                                'scope': 'Original unchanged baseline-profile controls on b4, not candidate product acceptance' if count == 74 else 'Candidate49 source/outcome gate controls'}

    lock = load(source / host.LOCK)
    actual_lock = load(evidence / 'actual-package-pins.json')
    require(lock['pins'] == actual_lock['pins'] and len(lock['pins']) == 44, 'All original 44 dependency pins')
    hanlin = load(source / 'Tools/Hanlin/source.json')
    require(execution['hanlin_revision'] == hanlin['revision'] == '116cc6be0654a5d11bc56ba00e0310031107ee36', 'Hanlin pin')
    require(sha((evidence / 'hanlin-snapshot.json').read_bytes()) == execution['hanlin_snapshot_sha256'], 'Hanlin runtime snapshot')
    pins = {x['identity'].lower(): x['state'].get('revision') for x in actual_lock['pins']}
    require(all(pins[k] == v for k, v in execution['dependency_checkouts'].items()), 'Actual dependency checkouts')
    heart = load(evidence / 'heart/heart-installation.json')
    require(heart == execution['heart'] and heart['status'] == 'PASS' and heart['app_source_sha'] == F
            and heart['source_run_id'] == '44203168617', 'Original installed Heart')
    download = load(evidence / 'heart-source/original-heart-download.json')
    require(download['consumer_sha'] == F and download['artifact_id'] == 14383247626
            and download['zip_crc_verified'] is True, 'Heart download receipt')

    timing = []
    for i in range(5):
        item = load(evidence / f'command-{i:02d}.json')
        require(item['exit_code'] == 0 and item['status'] == 'SUCCEEDED', 'Command failure')
        elapsed = (datetime.fromisoformat(item['finished_at']) - datetime.fromisoformat(item['started_at'])).total_seconds()
        timing.append({'index': i, 'command': item['command'], 'started_at': item['started_at'],
                       'finished_at': item['finished_at'], 'seconds': elapsed, 'exit_code': 0})
    require(timing[2]['command'] == execution['build_command'] and timing[4]['command'] == execution['test_command'], 'Actual build/test commands')
    build_log = (evidence / 'command-02.log').read_text()
    test_log = (evidence / 'command-04.log').read_text()
    require('** TEST BUILD SUCCEEDED **' in build_log and '** TEST EXECUTE SUCCEEDED **' in test_log, 'Final command markers')
    require('Executed 6 tests, with 0 failures' in test_log and 'Test run with 43 tests in 7 suites passed' in test_log, 'Actual separate XCTest and Swift Testing summaries')
    warning_lines = [x for x in build_log.splitlines() if re.search(r'\bwarning:', x)]
    error_mentions = [x for x in build_log.splitlines() if re.search(r'\berror:', x)]
    source_context_errors = [x for x in error_mentions if re.match(r'^\s*\d+\s*\|', x)]
    diagnostic_errors = [x for x in error_mentions if x not in source_context_errors]
    # Preserve the three Internal Error messages even though the same command
    # exited zero and built the actual tested executables. They are not a failed
    # XCTest result, and this report does not claim an error-free build log.
    primary_compile_errors = [x for x in diagnostic_errors if re.match(r'^(?:/.*?:\d+(?::\d+)?:\s*)?(?:fatal )?error:', x)]
    require(not primary_compile_errors, 'Primary compile error in successful result')
    warning_messages = Counter(re.sub(r'^.*?warning:\s*', '', x) for x in warning_lines)
    warnings = {'build_log_warning_occurrences': len(warning_lines),
                'unique_exact_warning_lines': len(set(warning_lines)),
                'warning_messages': dict(warning_messages.most_common()),
                'primary_compile_error_diagnostics': len(primary_compile_errors),
                'other_build_error_messages': diagnostic_errors,
                'other_build_error_message_occurrences': len(diagnostic_errors),
                'non_diagnostic_error_parameter_source_context_lines': len(source_context_errors),
                'test_log_warning_occurrences': len([x for x in test_log.splitlines() if re.search(r'\bwarning:', x)]),
                'xcresult_runtime_warnings': summary['runtimeWarnings'],
                'interpretation': 'Raw build-log occurrences, including repeated compiler/build-tool messages, not unique defects. Source-context error: parameters are separate from three actual Internal Error messages; their cause is unqualified. Build exit0 and the actual49 XCTest results remain independently recorded.'}
    leaf_rows = [{'method': name, 'scope': 'new_constructor6' if name in expected_new else 'original43', 'result': 'Passed'} for name in actual['methods']]
    result = {'status': 'VERIFIED_APPLE49_COMPONENT_PASS', 'source_sha': F, 'source_tree': TREE,
              'run_id': RUN, 'run_attempt': 1, 'job_id': JOB, 'artifact_id': ARTIFACT,
              'job_completed_at': job['completed_at'], 'workflow_updated_at': run['updated_at'],
              'artifact': outer, 'inner_archive': inner,
              'test_results': {'passed': 49, 'failed': 0, 'skipped': 0, 'original43': 43, 'constructor6': 6,
                               'unique_methods': 49, 'leaves': leaf_rows},
              'mac_controls': control_results, 'source_inputs': source_records,
              'original_package_pins': 44, 'timing': timing, 'warnings': warnings,
              'toolchain': {k: preflight[k] for k in ['xcode', 'swift', 'host_architecture', 'developer_dir']},
              'actual_device': actual['device'],
              'validator_replay': 'Original source-bound Python validators on retained actual raw results; no test or compilation rerun',
              'native_ui_executions': 0, 'release_accepted': False,
              'limitations': execution['limitations']}
    (root / 'VERIFIED_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'source_sha', 'run_id', 'job_id', 'original_package_pins', 'native_ui_executions']}, indent=2))
    print('Apple methods: 43 original + 6 constructors = 49 PASS; Mac controls: 74 baseline + 23 candidate = 97 PASS')
    print('Warning occurrences:', len(warning_lines), 'unique exact lines:', len(set(warning_lines)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    verify(parser.parse_args().root.resolve())
