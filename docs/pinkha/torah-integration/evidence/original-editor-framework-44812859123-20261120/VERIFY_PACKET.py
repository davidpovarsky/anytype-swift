#!/usr/bin/env python3
"""Read-only verification of actual v5 build success / signature failure. No tools rerun."""
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import shlex
import stat
import sys
import zipfile

HEAD = '196459fc9fa943f90e5c7f256545f94083e373e3'
TREE = 'bd3afe1eb84ec2285d52856b10860a7bae70df9d'
RUN = 44812859123
JOB = 136553572930
ARTIFACT = 14668938238
ARTIFACT_SHA = 'fda87acf19d28cf2b465b3c081874e1b215a3d49cc2c7c739c2de0d214ccebec'
BRANCH = 'codex/otzaria-original-editor-framework-v5-reviewed-20261120'
UPSTREAM_SHA = '2c0fbe60170efdf0b634ae73298803880098e1d352c9afef2baface15b45070c'
UPSTREAM_REF = '13fd0eb0aa080816ffa409669758b2e8787322b2'

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def unzip(data, count):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == count, 'ZIP inventory differs')
        require(archive.testzip() is None, 'ZIP CRC differs')
        for name in names:
            path = PurePosixPath(name)
            require(not path.is_absolute() and '..' not in path.parts and chr(92) not in name,
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
    raw = (directory / 'artifact-14668938238.zip').read_bytes()
    require(len(raw) == 1686079 and sha(raw) == ARTIFACT_SHA, 'Actual full artifact differs')
    outer = unzip(raw, 1)
    require(set(outer) == {'Pinkha-Native-Derived-Evidence.zip'}, 'Wrong nested archive')
    evidence = unzip(outer['Pinkha-Native-Derived-Evidence.zip'], 45)
    api = unzip((directory / 'canonical-api-and-log.zip').read_bytes(), 10)
    sources = unzip((directory / 'canonical-source-inputs.zip').read_bytes(), 27)
    read = lambda name: json.loads(evidence[name])
    meta = lambda name: json.loads(api[name])
    run = meta('RUN.json')
    require(run['id'] == RUN and run['head_sha'] == HEAD and run['run_attempt'] == 1
            and run['head_branch'] == BRANCH and run['event'] == 'push'
            and run['status'] == 'completed' and run['conclusion'] == 'failure'
            and run['repository']['id'] == run['head_repository']['id'] == 1289863025
            and run['repository']['full_name'] == 'davidpovarsky/anytype-swift', 'Actual run differs')
    jobs = meta('JOBS.json')
    require(jobs['total_count'] == len(jobs['jobs']) == 1, 'Wrong job inventory')
    job = jobs['jobs'][0]
    require(job['id'] == JOB and job['run_id'] == RUN and job['head_sha'] == HEAD
            and job['run_attempt'] == 1 and job['conclusion'] == 'failure', 'Actual job differs')
    steps = {row['name']: row['conclusion'] for row in job['steps']}
    require(steps['Build the genuine framework and execute the separate binary consumer'] == 'failure',
            'Wrong failed step')
    require(steps['Bind original app sources resources packages and the additive target'] == 'success',
            'Actual source admission did not pass')
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
            and [p['sha'] for p in commit['parents']] == ['e27a73ebbcafd883a91f83116f03cc40ab9d19db'],
            'Source commit/tree/parent differs')
    compare = meta('ACTIVATION_COMPARISON.json')
    require(compare['total_commits'] == 1 and [p['filename'] for p in compare['files']] == [
        'docs/pinkha/torah-integration/evidence/original-editor-framework-v5-root-review-20261120/ROOT_REVIEW.json'],
        'Activation changed source')
    before, after = read('source-before.json'), read('source-after.json')
    require(before == after and before['head_sha'] == HEAD and before['run_id'] == str(RUN)
            and before['run_attempt'] == '1' and before['original_swift_sources'] == 2237,
            'Actual source before/after differs')
    tree = meta('SOURCE_TREE.json')
    require(tree['sha'] == TREE and tree['truncated'] is False, 'Canonical Git tree differs')
    entries = {row['path']: row for row in tree['tree']}
    require(len(entries) == len(tree['tree']) == 12530, 'Canonical Git path inventory differs')
    original_files = sorted(path for path, row in entries.items()
                            if row['type'] == 'blob' and path.startswith('Anytype/Sources/')
                            and path.endswith('.swift'))
    require(original_files == before['source_files'], 'Actual original input paths differ from Git')
    for path, expected in before['original_trees'].items():
        require(entries[path]['type'] == 'tree' and entries[path]['sha'] == expected,
                'Original application/resource/module tree differs')
    proof = meta('SOURCE_GIT_PROOF.json')
    rows = {row['path']: row for row in proof['inputs']}
    require(len(rows) == len(before['source_inputs']) == 26, 'Canonical source count differs')
    require(set(rows) == set(before['source_inputs']), 'Canonical source paths differ')
    for path, expected in before['source_inputs'].items():
        data = sources[path]
        require(len(data) == expected['bytes'] and sha(data) == expected['sha256']
                and blob(data) == expected['git_blob'] == entries[path]['sha']
                == rows[path]['canonical_git_blob'], 'Canonical source bytes differ: ' + path)
    package_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    require(set(sources) == set(rows) | {package_path}, 'Unexpected canonical source')
    require(blob(sources[package_path]) == entries[package_path]['sha']
            == meta('PACKAGE_RESOLVED_API.json')['sha'], 'Original package lock differs')
    pins = json.loads(sources[package_path])['pins']
    required_pins = {pin['identity']: pin['state']['revision'] for pin in pins}
    dependencies = read('dependency-checkouts.json')
    require(len(required_pins) == dependencies['original_pin_count'] == 44
            and dependencies['actual_checkout_revisions'] == required_pins
            and dependencies['locked_but_not_materialized'] == [], 'Original 44 package checkouts differ')
    execution = read('execution.json')
    require(execution['source_sha'] == HEAD and execution['run_id'] == str(RUN)
            and execution['run_attempt'] == '1' and execution['status'] == 'FAIL'
            and execution['error_type'] == 'ValueError'
            and execution['error'] == 'Actual command failed: framework-signature-0'
            and execution['original_framework_build'] == 'PASS'
            and execution['external_consumer_build'] == 'NOT_RUN'
            and execution['native_editor_ui_tests'] == 0
            and execution['editable_mount'] == 'NOT_EXPOSED'
            and execution['verified_runtime_observations'] == [], 'Actual execution scope differs')
    commands = {name: json.loads(data) for name, data in evidence.items()
                if name.endswith('.command.json')}
    require(len(commands) == 5, 'Unexpected actual command inventory')
    for name, command in commands.items():
        stem = name.removesuffix('.command.json')
        require(command['stdout_sha256'] == sha(evidence[stem + '.stdout.log'])
                and command['stderr_sha256'] == sha(evidence[stem + '.stderr.log'])
                and command['timed_out'] is False, 'Actual command log hash/timeout differs')
    build = commands['framework-build.command.json']
    require(build['returncode'] == 0 and build['timeout_seconds'] == 6000
            and build['command'][0:2] == ['xcodebuild', 'build']
            and '-onlyUsePackageVersionsFromResolvedFile' in build['command']
            and 'CODE_SIGNING_ALLOWED=YES' in build['command']
            and 'CODE_SIGNING_REQUIRED=YES' in build['command']
            and 'CODE_SIGN_IDENTITY=-' in build['command']
            and '** BUILD SUCCEEDED **' in evidence['framework-build.stdout.log'].decode(),
            'Original framework build differs')
    signature = commands['framework-signature-0.command.json']
    require(signature['returncode'] == 1 and signature['timeout_seconds'] == 30
            and signature['command'][:3] == ['codesign', '--verify', '--strict']
            and signature['command'][-1].endswith('/distribution/Frameworks/AmplitudeCore.framework')
            and b'a sealed resource is missing or invalid' in evidence['framework-signature-0.stderr.log'],
            'Actual first signature failure differs')
    require(not any(name.startswith(('external-consumer', 'simulator-boot', 'public-surface'))
                    for name in evidence), 'Later gates unexpectedly executed')
    compiler = read('actual-framework-source-inputs.json')
    require(compiler['complete_original_swift_input_count'] == 2238
            and compiler['generated_swift_input_count'] == 1
            and compiler['source_is_original'] is True
            and compiler['app_or_test_binary_repackaged'] is False, 'Actual compiler closure differs')
    root = PurePosixPath(build['cwd'])
    derived = PurePosixPath(build['command'][build['command'].index('-derivedDataPath') + 1])
    expected_sources = {str(root / path) for path in before['source_files']
                        if path != 'Anytype/Sources/ApplicationLayer/AppScene.swift'}
    expected_sources |= {str(root / 'Anytype/Resources/AssetConstants.swift'),
                         str(root / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift')}
    observed = set()
    for item in compiler['lists']:
        data = evidence[item['evidence_path']]
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'Raw Swift input list differs')
        for line in data.decode().splitlines():
            values = shlex.split(line)
            require(len(values) == 1, 'Malformed raw Swift input')
            observed.add(values[0])
    original_observed = {path for path in observed if PurePosixPath(path).is_relative_to(root)
                         and not PurePosixPath(path).is_relative_to(derived)}
    require(original_observed == expected_sources and len(observed - expected_sources) == 1
            and all(PurePosixPath(path).is_relative_to(derived) for path in observed - expected_sources),
            'Original full compiler list differs')
    require({item['module'] for item in compiler['generated_bundle_accessors']} == {'Assets', 'DesignKit', 'Loc'},
            'Original generated resource accessor set differs')
    for item in compiler['generated_bundle_accessors']:
        data = evidence[item['evidence_path']]
        require(len(data) == item['bytes'] and sha(data) == item['sha256'],
                'Actual raw generated resource accessor differs')
    sdk = read('original-hanlin-snapshot.json')
    require(sdk['revision'] == '116cc6be0654a5d11bc56ba00e0310031107ee36'
            and len(sdk['files']) == 407, 'Original initial SDK snapshot differs')
    heart = read('heart/heart-installation.json')
    require(heart['status'] == 'PASS' and heart['source_run_id'] == '44203168617'
            and heart['app_source_sha'] == HEAD and execution['heart'] == heart,
            'Original Heart installation proof differs')
    controls = evidence['source-controls.stderr.log'].decode()
    actual = re.findall(r'(?m)^(test_\S+) \(([^\n]+)\) \.\.\. (ok|FAIL|ERROR)$', controls)
    declarations = set()
    for path, data in sources.items():
        if path.startswith('Tools/OriginalEditor/test_framework') and path.endswith('.py'):
            parsed = ast.parse(data)
            for cls in (node for node in parsed.body if isinstance(node, ast.ClassDef)):
                for method in (node for node in cls.body if isinstance(node, ast.FunctionDef)
                               and node.name.startswith('test_')):
                    declarations.add(PurePosixPath(path).stem + '.' + cls.name + '.' + method.name)
    require(len(declarations) == len(actual) == len({full for _, full, _ in actual}) == 99
            and {full for _, full, _ in actual} == declarations
            and all(outcome == 'ok' for _, _, outcome in actual)
            and '\nRan 99 tests in ' in controls and controls.rstrip().endswith('OK'),
            'Actual 99 Mac controls differ')
    distribution = read('framework-distribution.json')
    require(len(distribution['frameworks']) == 17 and len(distribution['resource_bundles']) == 34
            and len(distribution['verified_known_duplicates']) == 1
            and distribution['verified_known_duplicates'][0]['equivalence'] == 'COMPLETE_CLOSURE_EQUAL',
            'Actual export boundary differs')
    # This proof is byte evidence; it does not run codesign or emulate its policy.
    upstream = (directory / 'pinned-upstream-AmplitudeCore.zip').read_bytes()
    require(len(upstream) == 1964793 and sha(upstream) == UPSTREAM_SHA, 'Pinned upstream archive differs')
    upstream_files = unzip(upstream, 194)
    upstream_api = unzip((directory / 'upstream-provenance.zip').read_bytes(), 6)
    package_api = json.loads(upstream_api['AMPLITUDE_PACKAGE_API.json'])
    require(package_api['sha'] == blob(package_api['content'].encode())
            == 'b8720d5b79c8cad6b13564bc5fa959be2fbf3c26'
            and UPSTREAM_SHA in package_api['content'], 'Pinned original binary declaration differs')
    require(required_pins['amplitudecore-swift'] == UPSTREAM_REF, 'Different upstream package revision')
    release = json.loads(upstream_api['AMPLITUDE_RELEASE_API.json'])
    asset = next(item for item in release['assets'] if item['id'] == 267652144)
    require(release['id'] == 228171623 and asset['size'] == len(upstream)
            and asset['digest'] == 'sha256:' + UPSTREAM_SHA, 'Upstream release metadata differs')
    prefix = 'AmplitudeCore.xcframework/ios-arm64_x86_64-simulator/AmplitudeCore.framework/'
    actual_files = {name[len(prefix):]: data for name, data in upstream_files.items()
                    if name.startswith(prefix) and not name.endswith('/')}
    exported = {name.removeprefix('Frameworks/AmplitudeCore.framework/'): value
                for name, value in distribution['files'].items()
                if name.startswith('Frameworks/AmplitudeCore.framework/')}
    require(len(actual_files) == 13 and set(actual_files) == set(exported), 'Upstream/export membership differs')
    with zipfile.ZipFile(io.BytesIO(upstream)) as archive:
        for name, data in actual_files.items():
            item = archive.getinfo(prefix + name)
            require(stat.S_ISREG(item.external_attr >> 16)
                    and exported[name] == {'bytes': len(data), 'sha256': sha(data)}, 'Upstream/export bytes differ')
    seal = plistlib.loads(actual_files['_CodeSignature/CodeResources'])
    missing = set()
    for table in ('files', 'files2'):
        for name, item in seal[table].items():
            item = item if isinstance(item, dict) else {'hash': item}
            if name not in actual_files:
                require(item.get('optional') is not True, 'Missing member was optional')
                missing.add(name)
                continue
            for field, algorithm in [('hash', 'sha1'), ('hash2', 'sha256')]:
                if field in item:
                    require(hashlib.new(algorithm, actual_files[name]).digest() == item[field],
                            'Present upstream resource seal differs: ' + name)
    require(missing == {
        'Modules/AmplitudeCore.swiftmodule/arm64-apple-ios-simulator.swiftmodule',
        'Modules/AmplitudeCore.swiftmodule/x86_64-apple-ios-simulator.swiftmodule'},
        'Different upstream missing sealed members')
    cleanup = read('owned-simulator-cleanup.json')
    require(len(cleanup) == 4 and [item['returncode'] for item in cleanup] == [149, 0, 149, 0]
            and [item['operation'] for item in cleanup] == ['shutdown', 'delete', 'shutdown', 'delete'],
            'Owned cleanup result differs')
    warnings = meta('BUILD_WARNINGS.json')
    lines = [line for line in evidence['framework-build.stdout.log'].decode().splitlines()
             if 'warning:' in line]
    require(warnings['lines'] == lines and warnings['occurrences'] == len(lines) == 1300,
            'Full original compiler warning lines differ')
    return {'verification': 'PASS_READ_ONLY_ACTUAL_V5_FAILURE_PACKET',
            'workflow_conclusion': 'FAILURE', 'source': HEAD, 'run_id': RUN, 'artifact_id': ARTIFACT,
            'canonical_inputs': 26, 'additional_original_package_lock': 1,
            'source_before_after': 'EQUAL', 'original_source_files': 2237,
            'outer_members_crc_pass': 1, 'inner_members_crc_pass': 45,
            'actual_mac_python': {'executed': 99, 'passed': 99, 'failed': 0, 'errors': 0},
            'framework_build': 'PASS_ACTUAL_ORIGINAL_DEBUG_FRAMEWORK_BUILD',
            'compiler_original_inputs': 2238, 'compiler_generated_inputs': 1,
            'package_checkouts': 44, 'frameworks_exported': 17, 'resource_bundles_exported': 34,
            'initial_sdk_snapshot_files': 407, 'final_sdk_preservation_comparison': 'NOT_REACHED',
            'signature': 'FAILED_AMPLITUDECORE_STRICT_VERIFICATION_EXIT1',
            'upstream_matching_regular_files': 13, 'upstream_missing_required_seal_members': sorted(missing),
            'original_producer_codesign': 'NOT_OBSERVED', 'local_codesign_reruns': 0,
            'consumer_build': 'NOT_RUN', 'public_symbol_graph': 'NOT_RUN', 'simulator_runtime': 'NOT_RUN',
            'editable_mount': 'NOT_EXPOSED', 'native_editor_ui_tests': 0,
            'warning_lines_in_complete_build_stdout': 1300,
            'apple_or_test_reruns_by_verifier': 0}

if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent),
                     indent=2, sort_keys=True))
