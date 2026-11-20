#!/usr/bin/env python3
"""Read-only verification of the complete failed v3 artifact; executes no Apple tools."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

HEAD = 'a75443e4244762051cb0a99367188dc35645bfbf'
TREE = '9498cf1474244ae2a30d22117482e100d9e10118'
RUN = 44797902550
JOB = 136502155185
ARTIFACT = 14661426349
ARTIFACT_SHA = '508d94841af15124cb87580ac87829973e7d8aceae75e3ffb1948db74e761cdf'
BRANCH = 'codex/otzaria-original-editor-framework-v3-reviewed-20261120'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def unzip(raw, count):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == count, 'ZIP member inventory differs')
        require(archive.testzip() is None, 'ZIP CRC failure')
        for name in names:
            p = PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,
                    'Unsafe raw ZIP member')
        return {name: archive.read(name) for name in names}


def verify(directory):
    directory = Path(directory)
    index = json.loads((directory / 'PACKET_INDEX.json').read_bytes())
    require(index['source'] == HEAD and index['run_id'] == RUN, 'Wrong packet authority')
    for name, record in index['files'].items():
        require(PurePosixPath(name).name == name, 'Unexpected packet path')
        raw = (directory / name).read_bytes()
        require(len(raw) == record['bytes'] and sha(raw) == record['sha256']
                and blob(raw) == record['git_blob'], 'Sealed packet file differs: ' + name)
    raw = (directory / 'artifact-14661426349.zip').read_bytes()
    require(len(raw) == 1620390 and sha(raw) == ARTIFACT_SHA, 'Original artifact differs')
    outer = unzip(raw, 1)
    require(set(outer) == {'Pinkha-Native-Derived-Evidence.zip'}, 'Wrong original archive')
    nested = outer['Pinkha-Native-Derived-Evidence.zip']
    require(len(nested) == 1656805 and sha(nested) ==
            '5ef9c71bea030f6c9dbe06f8e1b787966a54af5dbdb954f82fcfbf96324390f5',
            'Original nested archive differs')
    evidence = unzip(nested, 34)
    metadata = unzip((directory / 'canonical-api-and-log.zip').read_bytes(), 10)
    sources = unzip((directory / 'canonical-source-inputs.zip').read_bytes(), 24)
    read = lambda name: json.loads(evidence[name])
    meta = lambda name: json.loads(metadata[name])
    run, jobs, artifacts = meta('RUN.json'), meta('JOBS.json'), meta('ARTIFACTS.json')
    require(run['id'] == RUN and run['run_attempt'] == 1 and run['head_sha'] == HEAD
            and run['head_branch'] == BRANCH and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'failure'
            and run['repository']['id'] == 1289863025
            and run['repository']['full_name'] == 'davidpovarsky/anytype-swift', 'Wrong actual run')
    require(jobs['total_count'] == len(jobs['jobs']) == 1, 'Unexpected job inventory')
    job = jobs['jobs'][0]
    require(job['id'] == JOB and job['run_id'] == RUN and job['head_sha'] == HEAD
            and job['conclusion'] == 'failure', 'Wrong actual failed job')
    step = [s for s in job['steps'] if s['name'] ==
            'Build the genuine framework and execute the separate binary consumer']
    require(len(step) == 1 and step[0]['conclusion'] == 'failure', 'Wrong failed step')
    require(len(artifacts) == 1, 'Unexpected published artifact inventory')
    artifact = artifacts[0]
    require(artifact['id'] == ARTIFACT and artifact['size_in_bytes'] == len(raw)
            and artifact['digest'] == 'sha256:' + ARTIFACT_SHA
            and artifact['workflow_run']['id'] == RUN
            and artifact['workflow_run']['head_sha'] == HEAD
            and artifact['workflow_run']['head_branch'] == BRANCH, 'Artifact provenance differs')
    commit = meta('SOURCE_COMMIT.json')
    require(commit['sha'] == HEAD and commit['tree']['sha'] == TREE, 'Wrong canonical source')
    require(evidence['source-before.json'] == evidence['source-after.json'], 'Source changed during execution')
    before = read('source-before.json')
    require(before['head_sha'] == HEAD and before['run_id'] == str(RUN)
            and before['run_attempt'] == '1' and before['original_swift_sources'] == 2237,
            'Source observation identity differs')
    proof = meta('SOURCE_GIT_PROOF.json')
    rows = {r['path']: r for r in proof['source_inputs']}
    require(len(rows) == len(before['source_inputs']) == 23, 'Source input inventory differs')
    for path, record in before['source_inputs'].items():
        source = sources[path]
        require(len(source) == record['bytes'] and sha(source) == record['sha256']
                and blob(source) == record['git_blob'] == rows[path]['canonical_git_entry']['sha']
                and rows[path]['sha256'] == record['sha256'], 'Canonical input differs: ' + path)
    canonical = meta('CANONICAL_TREE_SUBSET.json')
    require(canonical['sha'] == TREE and canonical['truncated'] is False
            and canonical['full_entry_count'] == 12483, 'Canonical Git tree differs')
    entries = {e['path']: e for e in canonical['entries']}
    swift = sorted(p for p, e in entries.items() if p.startswith('Anytype/Sources/')
                   and p.endswith('.swift') and e['type'] == 'blob')
    require(len(swift) == 2237 and swift == sorted(before['source_files']), 'Original compiler path closure differs')
    for path, expected in before['original_trees'].items():
        require(entries[path]['sha'] == expected == proof['original_trees'][path], 'Original tree differs')
    pins_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    pins_raw = sources[pins_path]
    require(blob(pins_raw) == entries[pins_path]['sha'] ==
            '2ee4435d9563f3e8b8691fbb36600bf63ec35a36', 'Original package pins differ')
    pins = {p['identity'].lower(): p['state']['revision'] for p in json.loads(pins_raw)['pins']}
    dependencies = read('dependency-checkouts.json')
    require(len(pins) == 44 and dependencies['original_pin_count'] == 44
            and dependencies['actual_checkout_revisions'] == pins
            and dependencies['locked_but_not_materialized'] == [], 'Original dependency closure differs')
    require(len(read('original-hanlin-snapshot.json')['files']) == 407, 'Original SDK snapshot differs')
    command = read('framework-build.command.json')
    require(command['returncode'] == 0 and command['timed_out'] is False
            and command['timeout_seconds'] == 6000, 'Actual framework build did not pass')
    for stream in ['stdout', 'stderr']:
        require(sha(evidence['framework-build.' + stream + '.log']) == command[stream + '_sha256'],
                'Framework build log differs')
    stdout = evidence['framework-build.stdout.log'].decode()
    stderr = evidence['framework-build.stderr.log'].decode()
    require('** BUILD SUCCEEDED **' in stdout, 'Original build success footer missing')
    require(not re.search(r':\d+:\d+: error:', stdout + stderr), 'Unexpected Swift error diagnostic')
    warnings = [line for line in stdout.splitlines() if 'warning:' in line]
    internal = [line for line in stdout.splitlines() if 'Internal Error:' in line]
    require(len(warnings) == 1298 and len(internal) == 5, 'Retained warning/error diagnostic inventory differs')
    lib_lines = [line for line in stdout.splitlines() if line.startswith('ProcessXCFramework ')
                 and 'Dependencies/Middleware/Lib.xcframework ' in line]
    require(len(lib_lines) == 2
            and any('/PackageFrameworks/Lib.framework ios simulator' in line for line in lib_lines)
            and any('/Debug-Anytype-iphonesimulator/Lib.framework ios simulator' in line for line in lib_lines),
            'Observed two Lib destinations differ')
    execution = read('execution.json')
    require(execution['status'] == 'FAIL' and execution['error_type'] == 'ValueError'
            and execution['error'] == 'Missing or ambiguous genuine framework products'
            and execution['original_framework_build'] == 'PASS'
            and execution['external_consumer_build'] == 'NOT_RUN'
            and execution['original_app_runtime'] == 'NOT_RUN'
            and execution['editable_mount'] == 'NOT_EXPOSED'
            and execution['native_editor_ui_tests'] == 0
            and execution['verified_runtime_observations'] == [], 'Failure scope differs')
    closure = read('actual-framework-source-inputs.json')
    require(closure == execution['actual_source_closure']
            and closure['complete_original_swift_input_count'] == 2238
            and closure['generated_swift_input_count'] == 1
            and len(closure['lists']) == 1
            and {r['module'] for r in closure['generated_bundle_accessors']} == {'Assets', 'DesignKit', 'Loc'},
            'Runtime-reported compiler closure differs')
    require(not any(n.endswith(('.SwiftFileList', '.swift')) for n in evidence),
            'Unexpected raw compiler-list retention; update precise packet scope')
    require(not any(n.startswith(('consumer-', 'actual-public-symbol-', 'consumer-owned-boot')) for n in evidence),
            'Unexpected later-stage execution evidence')
    controls = evidence['source-controls.stderr.log'].decode()
    actual_cases = re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. ok$', controls)
    require(len(actual_cases) == 54 and len(set(actual_cases)) == 54
            and '\nRan 54 tests in ' in controls and controls.rstrip().endswith('OK'), 'Actual Mac controls differ')
    heart = read('heart/heart-installation.json')
    require(heart['status'] == 'PASS' and heart['app_source_sha'] == HEAD
            and heart['source_run_id'] == '44203168617', 'Original verified Heart installation differs')
    cleanup = read('owned-simulator-cleanup.json')
    owned = {r['udid'] for r in cleanup}
    require(len(cleanup) == 4 and len(owned) == 2
            and all(r['returncode'] == (0 if r['operation'] == 'delete' else 149) for r in cleanup)
            and all('Shutdown' in r['stderr'] for r in cleanup if r['operation'] == 'shutdown'),
            'Owned simulator cleanup differs')
    require(all({'delete', 'shutdown'} == {r['operation'] for r in cleanup if r['udid'] == u} for u in owned),
            'Owned simulator deletion incomplete')
    return {'verification': 'PASS_READ_ONLY_ACTUAL_FAILURE_PACKET', 'workflow_conclusion': 'FAILURE',
            'source': HEAD, 'run_id': RUN, 'artifact_id': ARTIFACT,
            'outer_members_crc_pass': 1, 'inner_members_crc_pass': 34, 'canonical_inputs': 23,
            'original_swift_paths': 2237, 'original_package_pins': 44, 'sdk_snapshot_files': 407,
            'actual_mac_python_controls_pass': 54, 'actual_framework_build': 'PASS_EXIT_0',
            'compiler_warning_lines': 1298, 'nonfatal_internal_decoding_error_lines': 5,
            'raw_compiler_file_list_and_three_accessors': 'NOT_RETAINED_DIGEST_ONLY',
            'duplicate_lib_payload_equivalence': 'NOT_MEASURED_IN_FAILED_RUN',
            'external_consumer_build': 'NOT_RUN', 'symbol_graph': 'NOT_RUN',
            'native_runtime': 'NOT_RUN', 'editable_mount': 'NOT_EXPOSED',
            'swift_or_apple_reruns_by_verifier': 0}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent),
                     indent=2, sort_keys=True))
