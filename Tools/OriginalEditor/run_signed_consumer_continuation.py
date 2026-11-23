#!/usr/bin/env python3
"""Run the exact retained signed consumer; never rebuild or relabel its producer."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import sys
import time
import uuid
import zipfile

from consumer_failure_capture import combine_launch_help, prepare_launch_capture, read_regular
from framework_install_names import verify_consumer_install_name
from framework_products import inventory, verify_observation
from run_runtime_continuation import require, verify_metadata, zip_members, validate_toolchain
from runtime_continuation_process import Commands, digest, write_json
from runtime_continuation_observation import runtime_environment, cleanup_owned_simulator, validate_ownership

REPOSITORY = 'davidpovarsky/anytype-swift'
BRANCH = 'codex/otzaria-sdk-runtime-20261123'
WORKFLOW = '.github/workflows/pinkha-original-editor-signed-consumer.yml'
PACKET = 'docs/pinkha/torah-integration/evidence/original-editor-signed-consumer-20261123/'
CONTROL_FILES = {WORKFLOW, *('Tools/OriginalEditor/' + name for name in (
    'run_framework_acceptance.py', 'consumer_failure_capture.py', 'run_runtime_continuation.py',
    'run_signed_consumer_continuation.py', 'signed_consumer_continuation_inputs.json',
    'test_signed_consumer_continuation.py'))}
QUALIFIED = 'ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS'


def read_original_evidence(archive, inputs):
    with zipfile.ZipFile(archive) as outer:
        members = zip_members(outer)
        require(set(members) == {'Pinkha-Native-Derived-Evidence.zip'}, 'Wrong evidence wrapper')
        raw = outer.read(members['Pinkha-Native-Derived-Evidence.zip'])
    require(len(raw) == inputs['inner_evidence_bytes']
            and hashlib.sha256(raw).hexdigest() == inputs['inner_evidence_sha256'], 'Original evidence archive differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        members = zip_members(inner)
        selected = {}
        for name, expected in inputs['original_evidence_sha256'].items():
            data = inner.read(members[name])
            require(hashlib.sha256(data).hexdigest() == expected, 'Original evidence differs: ' + name)
            selected[name] = json.loads(data)
        require(inner.read(members['source-before.json']) == inner.read(members['source-after.json']),
                'Original source changed during production')
        e, p = selected['execution.json'], inputs['producer']
        require(e['source_sha'] == p['source_sha'] and int(e['run_id']) == p['run_id']
                and int(e['run_attempt']) == p['run_attempt'] == 1 and e['status'] == 'FAIL'
                and e['phase'] == 'ACTUAL_EXTERNAL_RESOURCE_RUNTIME'
                and e['error'] == 'Actual simctl does not advertise the required output options'
                and e['original_framework_build'] == e['external_consumer_build'] == 'PASS'
                and e['verified_runtime_observations'] == [], 'Original failure boundary differs')
        for label in ['framework-build', 'external-consumer-build', 'external-consumer-signature', 'actual-simctl-launch-help']:
            record = json.loads(inner.read(members[label + '.command.json']))
            require(record['returncode'] == 0 and record['timed_out'] is False, 'Original completed command failed')
            for stream in ['stdout', 'stderr']:
                require(hashlib.sha256(inner.read(members[label + '.' + stream + '.log'])).hexdigest()
                        == record[stream + '_sha256'], 'Original completed stream differs')
        controls = selected['retained-source-controls-result.json']
        require(controls['status'] == 'RETAINED_ORIGINAL_245_AND_CURRENT_AFFECTED_8_PASS'
                and controls['current_tests_run'] == len(set(controls['current_passed_ids'])) == 8
                and sorted(controls['current_started_ids']) == sorted(controls['current_passed_ids'])
                and not any(controls[key] for key in ['current_failures', 'current_errors', 'current_skipped',
                                                     'current_expected_failures', 'current_unexpected_successes'])
                and controls['retained']['original_count'] == 245, 'Original controls incomplete')
        public = selected['actual-public-surface.json']
        require(public['reviewed_host_and_spi_requirements_observed'] == 38
                and public['public_host_scope_verified'] and public['qualification_spi_scope_verified']
                and public['public_original_editor_or_writer_declarations'] == []
                and e['actual_public_surface'] == public, 'Original public/SPI admission differs')
        return selected


def extract_inventory(zipped, members, destination, expected, prefix='', modes=None):
    require(not destination.exists(), 'Refusing existing restoration destination')
    wanted = {prefix + relative for relative in expected}
    require(set(members) == wanted and len(expected) <= 20000
            and sum(row['bytes'] for row in expected.values()) <= 2 * 1024**3, 'Retained file membership differs')
    destination.mkdir(parents=True)
    for relative, row in expected.items():
        entry = members[prefix + relative]
        require(entry.file_size == row['bytes'], 'Retained file size differs')
        mode = stat.S_IMODE(entry.external_attr >> 16) or 0o644
        if modes is not None:
            require(mode == modes[relative], 'Retained file mode differs')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipped.open(entry) as source, target.open('xb') as output:
            shutil.copyfileobj(source, output)
        target.chmod(mode)
        require(digest(target) == row['sha256'], 'Retained file content differs')
    require(inventory(destination) == expected, 'Restored inventory differs')


def restore_consumer(archive, work, original_execution):
    with zipfile.ZipFile(archive) as outer:
        members = zip_members(outer)
        require(set(members) == {'consumer-app.zip', 'consumer-app-inventory.json', 'consumer-app-retention.json'},
                'Signed consumer wrapper membership differs')
        receipt = json.loads(outer.read(members['consumer-app-retention.json']))
        require(receipt == original_execution['retained_signed_consumer']
                and receipt['runtime_qualified'] is False and receipt['restore_as_original_sdk_allowed'] is False,
                'Signed consumer retention provenance differs')
        raw_inventory = outer.read(members['consumer-app-inventory.json'])
        require(hashlib.sha256(raw_inventory).hexdigest() == receipt['consumer_inventory_sha256'],
                'Consumer inventory commitment differs')
        expected = json.loads(raw_inventory)
        raw = outer.read(members['consumer-app.zip'])
        require(len(raw) == receipt['archive_bytes'] and hashlib.sha256(raw).hexdigest() == receipt['archive_sha256'],
                'Original signed app archive differs')
    destination = work / 'OriginalEditorConsumer.app'
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        members = zip_members(inner)
        extract_inventory(inner, members, destination, expected, destination.name + '/', receipt['file_modes'])
        directories = {entry.filename.rstrip('/').removeprefix(destination.name): entry
                       for entry in inner.infolist() if entry.is_dir()}
        expected_directories = {'' if key == '.' else '/' + key: mode for key, mode in receipt['directories'].items()}
        require(set(directories) == set(expected_directories), 'Signed app directory membership differs')
        for relative, mode in expected_directories.items():
            require(stat.S_IMODE(directories[relative].external_attr >> 16) == mode, 'Signed app directory mode differs')
            (destination / relative.lstrip('/')).chmod(mode)
    require(len(expected) == receipt['consumer_files']
            and sum(row['bytes'] for row in expected.values()) == receipt['consumer_bytes'], 'Signed consumer totals differ')
    return destination, expected


def restore_distribution(archive, work, selected, inputs):
    expected = selected['framework-distribution.json']
    with zipfile.ZipFile(archive) as outer:
        members = zip_members(outer)
        require('UNQUALIFIED_PRODUCER.json' in members, 'Missing original retention receipt')
        retention = json.loads(outer.read(members.pop('UNQUALIFIED_PRODUCER.json')))
        require(retention['source_sha'] == inputs['producer']['source_sha']
                and int(retention['run_id']) == inputs['producer']['run_id']
                and int(retention['run_attempt']) == 1
                and retention['qualified_distribution'] is False and retention['restore_as_sdk_allowed'] is False
                and retention['distribution_files'] == expected['files']
                and retention['distribution_bytes'] == expected['bytes'], 'Original distribution provenance differs')
        destination = work / 'distribution'
        extract_inventory(outer, members, destination, expected['files'], 'distribution/')
    require(not (destination / 'QUALIFICATION.json').exists(), 'Historical qualification cannot be fabricated')
    return destination


def original_upload_log_argv(job_id):
    """Raw API bytes are captured by Commands into owned files, never a TTY."""
    require(type(job_id) is int and job_id > 0, 'Invalid original upload job ID')
    return ['gh', 'api', '--allow-escape-sequences',
            'repos/' + REPOSITORY + '/actions/jobs/' + str(job_id) + '/logs']


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--deadline-unix', type=int, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    work, evidence = args.work.resolve(), args.evidence.resolve()
    for path in [work, evidence]:
        require(path.is_relative_to(root / 'build') and not path.exists(), 'Fresh owned build paths required')
        path.mkdir(parents=True)
    require(not work.is_relative_to(evidence) and not evidence.is_relative_to(work), 'Owned paths overlap')
    inputs_path = root / 'Tools/OriginalEditor/signed_consumer_continuation_inputs.json'
    inputs = json.loads(inputs_path.read_bytes())
    producer = inputs['producer']
    current = {'repository': os.environ['GITHUB_REPOSITORY'], 'repository_id': int(os.environ['GITHUB_REPOSITORY_ID']),
               'control_sha': os.environ['GITHUB_SHA'], 'run_id': int(os.environ['GITHUB_RUN_ID']),
               'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']), 'workflow_path': WORKFLOW,
               'head_branch': os.environ['GITHUB_REF_NAME'], 'job_name': 'original-editor-signed-consumer'}
    environment = runtime_environment(os.environ)
    for name in ['commands', 'downloads', 'cleanup']:
        (evidence / name).mkdir()
    commands = Commands(evidence / 'commands', environment, args.deadline_unix - 180)
    github = Commands(evidence / 'downloads', {**environment, 'GH_TOKEN': os.environ['GH_TOKEN'],
                                              'GH_PROMPT_DISABLED': '1'}, args.deadline_unix - 180)
    def command(name, argv, seconds=60):
        return commands.require(name, [str(x) for x in argv], root, seconds).read_text(errors='replace').strip()
    def api(endpoint, label):
        output = github.require(label, ['gh', 'api', 'repos/' + REPOSITORY + '/' + endpoint], root, 90)
        return json.loads(output.read_bytes())
    def download(item, label):
        output = github.require(label, ['gh', 'api', 'repos/' + REPOSITORY + '/actions/artifacts/' + str(item['id']) + '/zip'], root, 600)
        require(output.stat().st_size == item['size_in_bytes'] and digest(output) == item['sha256'], 'Artifact bytes differ')
        destination = work / (label + '.zip')
        output.rename(destination)
        github.items[-1]['stdout_relocated_to_owned_work'] = destination.relative_to(work).as_posix()
        github.persist()
        return destination
    result = {'schema': 2, 'kind': 'ORIGINAL_SIGNED_CONSUMER_RUNTIME_CONTINUATION', 'status': 'FAIL',
              'phase': 'INPUT_ADMISSION', 'framework_producer': producer, 'framework_source_sha': producer['source_sha'],
              'runtime_qualification_producer': current, 'framework_builds': 0, 'consumer_builds': 0,
              'source_controls_replayed': 0, 'verified_runtime_observations': [], 'native_editor_ui_tests': 0,
              'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False, 'simulator_attempts': 0}
    owned = None
    before_ids = set()
    simulator_name = 'Pinkha-UI27-' + str(current['run_id']) + '-ipad'
    success = False
    current_request = None
    current_launch_label = None
    launch_pids = []
    capture_groups_drained = True
    write_json(evidence / 'execution.json', result)
    try:
        require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Actual Darwin arm64 required')
        require(inputs['schema'] == 1 and current['repository'] == REPOSITORY
                and current['repository_id'] == producer['repository_id'] and current['head_branch'] == BRANCH
                and current['run_attempt'] == 1 and os.environ['GITHUB_EVENT_NAME'] == 'push', 'Wrong continuation identity')
        require(time.time() < args.deadline_unix <= time.time() + 2400, 'Invalid finite deadline')
        require(command('control-head', ['git', 'rev-parse', 'HEAD']) == current['control_sha'], 'Control source differs')
        command('producer-ancestor', ['git', 'merge-base', '--is-ancestor', producer['source_sha'], 'HEAD'])
        delta = command('control-diff', ['git', 'diff', '--name-only', producer['source_sha'], 'HEAD']).splitlines()
        require(all(path in CONTROL_FILES or path.startswith(PACKET) for path in delta), 'Unowned product source changed')
        require(not command('control-status', ['git', 'status', '--porcelain', '--untracked-files=all', '--', 'Tools', '.github']),
                'Uncommitted control input')
        for path, expected in inputs['source_trees'].items():
            require(command('tree-' + path.replace('/', '-'), ['git', 'rev-parse', 'HEAD:' + path]) == expected,
                    'Original application/module tree changed')
        for path in ['Anytype.xcodeproj', 'OriginalEditorFramework']:
            require(not command('original-' + path, ['git', 'diff', '--name-only', producer['source_sha'], 'HEAD', '--', path]),
                    'Original project or facade changed')
        control_packet = root / PACKET
        controls = json.loads((control_packet / 'METADATA_CONTROLS.json').read_bytes())
        require(controls['status'] == 'PASS' and controls['tests_run'] == len(set(controls['passed_ids'])) == 6
                and controls['failed'] == controls['errors'] == controls['skipped'] == 0,
                'Exact upload metadata controls did not pass')
        for relative, expected in controls['source_sha256'].items():
            require(digest(root / relative) == expected, 'Upload proof control source differs: ' + relative)
        for relative, expected in controls['log_sha256'].items():
            require(digest(control_packet / relative) == expected, 'Upload proof control log differs: ' + relative)
        capture_controls = json.loads((control_packet / 'RAW_CAPTURE_CONTROLS.json').read_bytes())
        require(capture_controls['status'] == 'PASS'
                and capture_controls['tests_run'] == len(set(capture_controls['passed_ids'])) == 2
                and capture_controls['failed'] == capture_controls['errors'] == capture_controls['skipped'] == 0,
                'Raw original log capture controls did not pass')
        for relative, expected in capture_controls['source_sha256'].items():
            require(digest(root / relative) == expected, 'Raw capture source differs: ' + relative)
        for relative, expected in capture_controls['log_sha256'].items():
            require(digest(control_packet / relative) == expected, 'Raw capture log differs: ' + relative)
        actual = {'xcode': command('xcode', ['xcodebuild', '-version']),
                  'swift': command('swift', ['xcrun', 'swiftc', '--version']),
                  'sdk_version': command('sdk', ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'])}
        validate_toolchain(actual, inputs['toolchain'])
        run = api('actions/runs/' + str(producer['run_id']) + '/attempts/1', 'original-run')
        job = api('actions/jobs/' + str(producer['job_id']), 'original-job')
        upload_log = github.require('original-job-upload-log',
            original_upload_log_argv(producer['job_id']), root, 90)
        require(upload_log.stat().st_size <= 4 * 1024 * 1024, 'Oversized original upload proof')
        original_upload_log = upload_log.read_bytes()
        for label, item in inputs['artifacts'].items():
            proof = verify_metadata(producer, run, job,
                api('actions/artifacts/' + str(item['id']), 'metadata-' + label), item, upload_log=original_upload_log)
            write_json(evidence / ('original-upload-binding-' + label + '.json'), proof)
        selected = read_original_evidence(download(inputs['artifacts']['evidence'], 'original-evidence'), inputs)
        original = selected['execution.json']
        app, app_inventory = restore_consumer(download(inputs['artifacts']['consumer'], 'signed-consumer'), work, original)
        distribution = restore_distribution(download(inputs['artifacts']['framework'], 'original-framework'), work, selected, inputs)
        command('consumer-signature', ['codesign', '--verify', '--strict', app])
        load = verify_consumer_install_name(app)
        write_json(evidence / 'actual-consumer-install-names.json', load)
        for name in selected['framework-distribution.json']['frameworks']:
            require(inventory(app / 'Frameworks' / name) == inventory(distribution / 'Frameworks' / name),
                    'Retained signed consumer uses a different framework: ' + name)
        oracle = selected['independent-original-resource-oracles.json']
        result.update(original_framework_build='REUSED_SUCCESSFUL_ORIGINAL_PRODUCER',
                      external_consumer_build='REUSED_SUCCESSFUL_ORIGINAL_PRODUCER',
                      retained_source_controls_passed=245, retained_affected_controls_passed=8,
                      actual_public_surface=selected['actual-public-surface.json'], original_clang_declarations=original['original_clang_declarations'],
                      compiled_consumer_api_probe_sha256=inputs['consumer_probe_sha256'],
                      preflight={'xcode': actual['xcode']}, swift=actual['swift'], sdk=actual['sdk_version'],
                      phase='ACTUAL_EXTERNAL_RESOURCE_RUNTIME')
        runtimes = json.loads(command('runtimes', ['xcrun', 'simctl', 'list', 'runtimes', '-j']))['runtimes']
        matches = [item for item in runtimes if all(item.get(k) == v for k, v in inputs['runtime'].items()) and item.get('isAvailable')]
        require(len(matches) == 1 and 'arm64' in matches[0].get('supportedArchitectures', [])
                and any(t['identifier'] == inputs['device']['identifier'] for t in matches[0]['supportedDeviceTypes']),
                'Original runtime or device unavailable')
        before = json.loads(command('devices-before', ['xcrun', 'simctl', 'list', 'devices', '-j']))['devices']
        before_ids = {item['udid'] for group in before.values() for item in group}
        require(not any(item['name'] == simulator_name for group in before.values() for item in group), 'Owned name already exists')
        result['simulator_attempts'] = 1
        write_json(evidence / 'execution.json', result)
        identifier = command('create', ['xcrun', 'simctl', 'create', simulator_name, inputs['device']['identifier'], inputs['runtime']['identifier']])
        owned = {'udid': identifier, 'name': simulator_name, 'device': inputs['device'], 'runtime': inputs['runtime']}
        validate_ownership(owned, simulator_name, inputs['device'], inputs['runtime'], before_ids)
        write_json(evidence / 'owned-simulator.json', owned)
        command('boot', ['xcrun', 'simctl', 'boot', identifier], 60)
        command('boot-status', ['xcrun', 'simctl', 'bootstatus', identifier, '-b'], 180)
        command('install', ['xcrun', 'simctl', 'install', identifier, app], 300)
        bundle = 'org.otzaria.acceptance.original-editor'
        installed = Path(command('installed-app', ['xcrun', 'simctl', 'get_app_container', identifier, bundle, 'app']))
        data = Path(command('installed-data', ['xcrun', 'simctl', 'get_app_container', identifier, bundle, 'data']))
        require(installed.is_dir() and data.is_dir() and identifier in installed.parts and identifier in data.parts,
                'Wrong owned application containers')
        stdout = command('launch-help', ['xcrun', 'simctl', 'help', 'launch'], 15)
        stderr, _ = read_regular(commands.evidence / commands.items[-1]['stderr'], 65536)
        help_text = combine_launch_help(stdout, stderr.decode(errors='replace'))
        preflight = {'status': 'PREFLIGHT_PASS_UI_NOT_RUN', 'source_sha': current['control_sha'],
                     'run_id': str(current['run_id']), 'run_attempt': '1', 'selected': {'ipad': {'udid': identifier, 'name': simulator_name}}}
        result['preflight'].update(preflight)
        write_json(evidence / 'execution.json', result)
        for language in ['en', 'he']:
            nonce = str(uuid.uuid4()).upper()
            output = data / 'Documents' / ('original-editor-' + nonce + '.json')
            require(not output.exists(), 'Stale consumer observation')
            original_launch = ['xcrun', 'simctl', 'launch', '--terminate-running-process', identifier, bundle,
                               '--original-editor-nonce', nonce, '-AppleLanguages', '(' + language + ')',
                               '-AppleLocale', 'he_IL' if language == 'he' else 'en_US']
            argv, request = prepare_launch_capture(evidence, preflight, installed, original_launch, language, help_text)
            current_request = request
            current_launch_label = 'consumer-' + language + '-launch'
            pid_text = command(current_launch_label, argv, 60)
            match = re.fullmatch(re.escape(bundle) + r': ([1-9][0-9]*)', pid_text)
            require(match is not None, 'Original simulator launch returned no actual process ID')
            pid = int(match[1])
            require(pid not in launch_pids, 'Language relaunch did not create a different process')
            launch_pids.append(pid)
            write_json(evidence / ('consumer-' + language + '-launch-result.json'),
                       {'stdout': pid_text, 'pid': pid, 'nonce': nonce, 'language': language})
            deadline = min(time.monotonic() + 20, commands.monotonic_deadline)
            while not output.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 65536,
                    'No bounded original consumer runtime observation')
            raw = output.read_bytes()
            (evidence / ('consumer-' + language + '-observation.json')).write_bytes(raw)
            result['verified_runtime_observations'].append(verify_observation(json.loads(raw), nonce, language, installed, oracle))
            write_json(evidence / 'execution.json', result)
            command('consumer-' + language + '-terminate', ['xcrun', 'simctl', 'terminate', identifier, bundle], 30)
            current_request = None
            current_launch_label = None
        require(len(result['verified_runtime_observations']) == 2 and inventory(app) == app_inventory
                and inventory(distribution) == selected['framework-distribution.json']['files'], 'Retained products changed')
        result.update(distribution_unchanged=True, distribution_manifest_sha256=inputs['original_evidence_sha256']['framework-distribution.json'],
                      original_source_sha256=digest(distribution / 'SourceProvenance/OriginalSource.json'),
                      same_toolchain_only=True, device_framework_build='NOT_RUN', original_app_runtime='NOT_RUN',
                      editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN')
        success = True
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        if current_request is not None and commands.owned_groups_drained:
            try:
                launch = [item for item in commands.items if item['label'] == current_launch_label]
                require(len(launch) == 1, 'Original failed launch record is ambiguous')
                for stream in ['stdout', 'stderr']:
                    source = commands.evidence / launch[0][stream]
                    if source.exists():
                        shutil.copyfile(source, evidence / (current_launch_label + '.' + stream + '.log'))
                capture_root = evidence / 'failure-command'
                capture_root.mkdir()
                capture_env = {**environment, **{key: os.environ[key] for key in
                               ['GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']}}
                capture = Commands(capture_root, capture_env, min(args.deadline_unix - 180, time.time() + 30))
                code, _, _ = capture.run('original-consumer-failure-capture',
                    [sys.executable, str(root / 'Tools/OriginalEditor/consumer_failure_capture.py'),
                     '--capture-failure', str(current_request)], root, 20)
                result['failure_capture'] = {'returncode': code, 'owned_groups_drained': capture.owned_groups_drained}
                capture_groups_drained = capture.owned_groups_drained
                require(capture.owned_groups_drained, 'Failure capture process group did not drain')
            except BaseException as capture_error:
                result['failure_capture_error'] = {'type': type(capture_error).__name__, 'error': str(capture_error)}
    finally:
        cleanup = Commands(evidence / 'cleanup', environment, args.deadline_unix)
        try:
            require(commands.owned_groups_drained and github.owned_groups_drained and capture_groups_drained,
                    'An owned command group did not drain')
            if owned is None and result['simulator_attempts'] == 1:
                state = json.loads(cleanup.require('recover-identity', ['xcrun', 'simctl', 'list', 'devices', '-j'], root, 30).read_bytes())['devices']
                matches = [item for item in state.get(inputs['runtime']['identifier'], []) if item['name'] == simulator_name
                           and item['udid'] not in before_ids and item['deviceTypeIdentifier'] == inputs['device']['identifier']]
                require(len(matches) == 1, 'Owned creation outcome uncertain')
                owned = {'udid': matches[0]['udid'], 'name': simulator_name, 'device': inputs['device'], 'runtime': inputs['runtime']}
            if owned is not None:
                result['owned_simulator_cleanup'] = cleanup_owned_simulator(cleanup, root, owned, simulator_name,
                                                                            inputs['device'], inputs['runtime'], before_ids)
                require(result['owned_simulator_cleanup']['completed'], 'Owned simulator deletion/absence unproven')
            result['owned_simulator_cleanup_completed'] = True
        except BaseException as error:
            success = False
            result['cleanup_error'] = str(error)
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        if success:
            result.update(status=QUALIFIED, phase='COMPLETE')
            write_json(evidence / 'runtime-qualification.json', result)
        write_json(evidence / 'execution.json', result)
        write_json(evidence / 'EVIDENCE_INDEX.json', {'files': [
            {'path': path.relative_to(evidence).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}
            for path in sorted(evidence.rglob('*')) if path.is_file() and path.name != 'EVIDENCE_INDEX.json']})
    print(json.dumps({key: result.get(key) for key in ['status', 'phase', 'error', 'cleanup_error', 'verified_runtime_observations']}))
    return 0 if success else 1


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Owned continuation signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
