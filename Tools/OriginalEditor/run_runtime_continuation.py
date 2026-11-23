#!/usr/bin/env python3
"""Qualify one actual consumer runtime using one exact retained framework.

The framework remains attributed to its original producer. This continuation
never rebuilds it, replays its source suites, or rewrites its retained products.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import re
import shutil
import signal
import stat
import sys
import time
import uuid
import zipfile

from clang_product_closure import read_clang_imports
from framework_products import consumer_project, inventory, original_oracles, verify_observation
from runtime_continuation_process import Commands, digest, write_json
from runtime_continuation_observation import (runtime_environment, validate_ownership, observe_runtime,
                                               retain_signed_consumer, cleanup_owned_simulator)

REPOSITORY = 'davidpovarsky/anytype-swift'
QUALIFIED = 'ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS'
WORKFLOW = '.github/workflows/pinkha-original-editor-runtime-continuation.yml'
CONTROL_FILES = {
    WORKFLOW, 'Tools/OriginalEditor/run_runtime_continuation.py',
    'Tools/OriginalEditor/runtime_continuation_process.py',
    'Tools/OriginalEditor/runtime_continuation_inputs.json',
    'Tools/OriginalEditor/runtime_continuation_controls.py',
    'Tools/OriginalEditor/runtime_continuation_observation.py',
}
EVIDENCE_PREFIX = 'docs/pinkha/torah-integration/evidence/original-editor-runtime-continuation-20261122/'
ORIGINAL_DOTFILE_PATHS = {
    'Frameworks/AnytypeOriginalEditor.framework/.gitattributes',
    'Bundles/HanlinPresentationSDK_HanlinRichUI.bundle/OpenUI/.gitattributes',
}

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def read_json(path, maximum=16 * 1024 * 1024):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= maximum,
            'Missing, aliased or oversized evidence: ' + str(path))
    return json.loads(path.read_bytes())

def zip_members(zipped):
    result, aliases = {}, set()
    for entry in zipped.infolist():
        path = PurePosixPath(entry.filename.rstrip('/'))
        require(path.parts and path.as_posix() != '.' and not path.is_absolute() and '..' not in path.parts
                and path.as_posix() == entry.filename.rstrip('/') and '\\' not in entry.filename
                and ':' not in entry.filename and not (entry.flag_bits & 1), 'Unsafe retained ZIP member')
        folded = path.as_posix().casefold()
        require(folded not in aliases, 'Aliased or repeated retained ZIP member')
        aliases.add(folded)
        mode = (entry.external_attr >> 16) & 0xFFFF
        require(stat.S_IFMT(mode) in {0, stat.S_IFDIR if entry.is_dir() else stat.S_IFREG}
                and not stat.S_IMODE(mode) & ~0o777, 'Nonregular retained ZIP member')
        if not entry.is_dir():
            result[path.as_posix()] = entry
    return result

def verify_exact_upload_log(producer, upload, artifact, expected_artifact, raw):
    """Bind the artifact to its exact successful action, without clock tolerance."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= 4 * 1024 * 1024,
            'Missing bounded authenticated original upload log')
    lines = raw.decode('utf-8-sig').splitlines()
    starts = [i for i, line in enumerate(lines) if '##[group]Run ' in line]
    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        if lines[start].endswith('##[group]Run actions/upload-artifact@v4'):
            block = lines[start:end]
            if any(line.partition(' ')[2].strip() == 'name: ' + expected_artifact['name'] for line in block):
                blocks.append(block)
    require(len(blocks) == 1, 'Original artifact has no unique matching upload action')
    block = blocks[0]
    expected = [
        'name: ' + expected_artifact['name'],
        'SHA256 digest of uploaded artifact zip is ' + expected_artifact['sha256'],
        'Artifact ' + expected_artifact['name'] + '.zip successfully finalized. Artifact ID ' + str(expected_artifact['id']),
        'Artifact ' + expected_artifact['name'] + ' has been successfully uploaded! Final size is '
            + str(expected_artifact['size_in_bytes']) + ' bytes. Artifact ID is ' + str(expected_artifact['id']),
        'Artifact download URL: https://github.com/' + REPOSITORY + '/actions/runs/'
            + str(producer['run_id']) + '/artifacts/' + str(expected_artifact['id']),
    ]
    instant = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00'))
    statements, positions = [], []
    for message in expected:
        found = [(i, line) for i, line in enumerate(block) if line.partition(' ')[2].strip() == message]
        require(len(found) == 1, 'Original upload log does not bind exact artifact ID, size and digest')
        index, line = found[0]
        timestamp = line.partition(' ')[0]
        # Job step metadata has whole-second precision. Compare the log's
        # corresponding whole second, not the artifact service creation clock.
        second = instant(timestamp).replace(microsecond=0)
        require(instant(upload['started_at']) <= second <= instant(upload['completed_at']),
                'Artifact finalization statement is outside the exact successful upload step')
        positions.append(index)
        statements.append({'timestamp': timestamp, 'message': message})
    require(positions == sorted(set(positions)), 'Original upload finalization statements are out of order')
    return {'status': 'EXACT_SUCCESSFUL_UPLOAD_LOG_ARTIFACT_BINDING',
            'source_sha': producer['source_sha'], 'run_id': producer['run_id'], 'job_id': producer['job_id'],
            'upload_step': expected_artifact['upload_step'], 'artifact_id': expected_artifact['id'],
            'artifact_sha256': expected_artifact['sha256'], 'artifact_bytes': expected_artifact['size_in_bytes'],
            'artifact_created_at': artifact['created_at'], 'step_started_at': upload['started_at'],
            'step_completed_at': upload['completed_at'], 'authenticated_job_log_sha256': hashlib.sha256(raw).hexdigest(),
            'statements': statements, 'timestamp_tolerance_applied': False}


def verify_metadata(producer, run, job, artifact, expected_artifact, *, upload_log=None):
    require(run.get('id') == producer['run_id'] and run.get('run_attempt') == producer['run_attempt']
            and run.get('head_sha') == run.get('head_commit', {}).get('id') == producer['source_sha']
            and run.get('status') == 'completed' and run.get('conclusion') == 'failure'
            and run.get('path') == producer['workflow_path'] and run.get('head_branch') == producer['head_branch'],
            'Original producer run differs from the exact retained failure')
    for key in ['repository', 'head_repository']:
        require(run.get(key, {}).get('id') == producer['repository_id']
                and run[key].get('full_name') == REPOSITORY, 'Original producer repository differs')
    require(job.get('id') == producer['job_id'] and job.get('name') == producer['job_name']
            and job.get('run_id') == producer['run_id'] and job.get('run_attempt') == producer['run_attempt']
            and job.get('head_sha') == producer['source_sha'] and job.get('head_branch') == producer['head_branch']
            and job.get('status') == 'completed' and job.get('conclusion') == 'failure', 'Original failed job differs')
    def step(name, conclusion):
        found = [s for s in job.get('steps', []) if s.get('name') == name]
        require(len(found) == 1 and found[0].get('status') == 'completed'
                and found[0].get('conclusion') == conclusion, 'Original step differs: ' + name)
        return found[0]
    for name in producer['required_steps']:
        step(name, 'success')
    step(producer['failed_step'], 'failure')
    upload = step(expected_artifact['upload_step'], 'success')
    require(all(artifact.get(k) == expected_artifact[k] for k in ['id', 'name', 'size_in_bytes'])
            and artifact.get('expired') is False and artifact.get('digest') == 'sha256:' + expected_artifact['sha256'],
            'Original artifact identity/digest differs')
    origin = artifact.get('workflow_run', {})
    require(origin.get('id') == producer['run_id'] and origin.get('head_sha') == producer['source_sha']
            and origin.get('repository_id') == origin.get('head_repository_id') == producer['repository_id']
            and origin.get('head_branch') == producer['head_branch'], 'Original artifact belongs to another producer')
    instant = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
    created = instant(artifact['created_at'])
    require(instant(job['started_at']) <= created <= instant(job['completed_at']),
            'Original artifact was not created by its exact successful upload')
    if upload_log is None:
        require(instant(upload['started_at']) <= created <= instant(upload['completed_at']),
                'Original artifact was not created by its exact successful upload')
        return None
    return verify_exact_upload_log(producer, upload, artifact, expected_artifact, upload_log)

def verify_retained_phase(producer, evidence):
    for name, expected in producer['retained_input_sha256'].items():
        require(digest(evidence / name) == expected, 'Original evidence digest differs: ' + name)
    execution = read_json(evidence / 'execution.json')
    require(execution['source_sha'] == producer['source_sha']
            and str(execution['run_id']) == str(producer['run_id'])
            and str(execution['run_attempt']) == str(producer['run_attempt'])
            and execution['status'] == 'FAIL' and execution['phase'] == 'ACTUAL_EXTERNAL_RESOURCE_RUNTIME'
            and execution['error_type'] == 'TimeoutExpired'
            and execution['original_framework_build'] == execution['external_consumer_build'] == 'PASS'
            and execution['verified_runtime_observations'] == [], 'Original failure is not the admitted install boundary')
    install = read_json(evidence / 'install-external-consumer.command.json')
    require(install['command'][:3] == ['xcrun', 'simctl', 'install']
            and install['timed_out'] is True and install['timeout_seconds'] == 60 and install['returncode'] == -15,
            'Original install did not fail at the reviewed finite timeout')
    for name in ['framework-build', 'external-consumer-build', 'external-consumer-signature']:
        command = read_json(evidence / (name + '.command.json'))
        require(command['returncode'] == 0 and command['timed_out'] is False, 'Original completed command differs: ' + name)
    controls = read_json(evidence / 'source-controls-result.json')
    expected = controls['expected_ids']
    require(controls['status'] == 'PASS_SOURCE_CONTROLS_245' and controls['tests_run'] == 245,
            'Original required source suite did not pass')
    for key in ['expected_ids', 'discovered_ids', 'started_ids', 'passed_ids']:
        require(len(controls[key]) == len(set(controls[key])) == 245 and sorted(controls[key]) == sorted(expected),
                'Original source control identity set differs')
    require(all(controls[k] == [] for k in ['errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes']),
            'Original source controls were incomplete')
    require((evidence / 'source-before.json').read_bytes() == (evidence / 'source-after.json').read_bytes(),
            'Original product source changed')
    surface = read_json(evidence / 'actual-public-surface.json')
    require(surface['reviewed_host_and_spi_requirements_observed'] == 38
            and surface['public_host_scope_verified'] and surface['qualification_spi_scope_verified']
            and surface['public_original_editor_or_writer_declarations'] == []
            and surface == execution['actual_public_surface'], 'Original public/SPI closure differs')
    require(execution['compiled_consumer_api_probe_sha256'] == producer['consumer_source_sha256'],
            'Original compiled consumer probe differs')
    return execution

def extract_original_evidence(outer_path, work, producer):
    with zipfile.ZipFile(outer_path) as outer:
        members = zip_members(outer)
        require(set(members) == {'Pinkha-Native-Derived-Evidence.zip'}, 'Unexpected original evidence wrapper')
        payload = outer.read(members['Pinkha-Native-Derived-Evidence.zip'])
    require(len(payload) == producer['evidence_inner_bytes']
            and hashlib.sha256(payload).hexdigest() == producer['evidence_inner_sha256'], 'Original evidence payload differs')
    inner_path = work / 'original-evidence.zip'
    inner_path.write_bytes(payload)
    destination = work / 'original-evidence'
    destination.mkdir()
    with zipfile.ZipFile(io.BytesIO(payload)) as inner:
        members = zip_members(inner)
        for name in producer['retained_input_sha256']:
            require(name in members and members[name].file_size <= 16 * 1024 * 1024, 'Missing bounded original evidence member')
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(inner.read(members[name]))
    verify_retained_phase(producer, destination)
    return destination

def validate_original_dotfile(item, response, exported, original_evidence):
    """Admit only an exact immutable source blob already hashed by the producer."""
    require(item['distribution_path'] in ORIGINAL_DOTFILE_PATHS
            and exported['files'][item['distribution_path']] == {k: item[k] for k in ['bytes', 'sha256']},
            'Supplement does not match an original exported dotfile')
    require(response.get('type') == 'file' and response.get('path') == item['source_path']
            and response.get('sha') == item['git_blob'] and response.get('encoding') == 'base64',
            'Immutable original source blob metadata differs')
    raw = base64.b64decode(response['content'])
    require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
            and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob'],
            'Original dotfile bytes differ from both Git and the original product inventory')
    if item['repository'] == 'davidpovarsky/hanlin-ai':
        hanlin = read_json(original_evidence / 'original-hanlin-snapshot.json')
        require(hanlin['revision'] == item['source_sha']
                and hanlin['files'][item['source_path']] == item['sha256'], 'Original Hanlin source binding differs')
    else:
        require(item['repository'] == REPOSITORY
                and read_json(original_evidence / 'source-before.json')['head_sha'] == item['source_sha'],
                'Original application source binding differs')
    return raw

def restore_original_distribution(archive, destination, evidence, producer, exported, supplements):
    require(not destination.exists(), 'Refusing existing distribution')
    with zipfile.ZipFile(archive) as zipped:
        members = zip_members(zipped)
        expected = {'distribution/' + k: v for k, v in exported['files'].items()}
        omissions = {item['distribution_path']: item for item in producer['archive_omissions']}
        require(len(producer['archive_omissions']) == 2 and set(omissions) == set(supplements) == ORIGINAL_DOTFILE_PATHS,
                'Only the two observed original artifact omissions may be restored')
        absent = {'distribution/' + name for name in omissions}
        require(set(members) == (set(expected) - absent) | {'UNQUALIFIED_PRODUCER.json'},
                'Retained distribution membership differs beyond the exact two observed dotfiles')
        require(sum(v['bytes'] for v in expected.values()) == exported['bytes'] <= 4 * 1024**3,
                'Retained distribution size differs')
        record_raw = zipped.read(members['UNQUALIFIED_PRODUCER.json'])
        require(hashlib.sha256(record_raw).hexdigest() == producer['retention_receipt_sha256'], 'Retention receipt differs')
        record = json.loads(record_raw)
        require(record['source_sha'] == producer['source_sha'] and str(record['run_id']) == str(producer['run_id'])
                and str(record['run_attempt']) == str(producer['run_attempt'])
                and record['qualified_distribution'] is False and record['restore_as_sdk_allowed'] is False
                and record['consumer_continuation_admission'] == 'NOT_IMPLEMENTED_OR_GRANTED'
                and record['distribution_files'] == exported['files'] and record['distribution_bytes'] == exported['bytes']
                and record['actual_execution_sha256'] == producer['retained_input_sha256']['execution.json']
                and record['source_before_sha256'] == producer['retained_input_sha256']['source-before.json']
                and record['source_after_sha256'] == producer['retained_input_sha256']['source-after.json']
                and record['successful_build_command_sha256'] == producer['retained_input_sha256']['framework-build.command.json']
                and record['source_evidence_archive']['sha256'] == producer['evidence_inner_sha256']
                and record['source_evidence_archive']['bytes'] == producer['evidence_inner_bytes'], 'Retention provenance differs')
        (evidence / 'UNQUALIFIED_PRODUCER.json').write_bytes(record_raw)
        destination.mkdir()
        for name, commitment in expected.items():
            relative = name.removeprefix('distribution/')
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if name in absent:
                raw = supplements[relative]
                require(len(raw) == commitment['bytes'] and hashlib.sha256(raw).hexdigest() == commitment['sha256'],
                        'Original source supplement differs from the complete product inventory')
                with target.open('xb') as output:
                    output.write(raw)
                target.chmod(0o644)
            else:
                entry = members[name]
                require(entry.file_size == commitment['bytes'], 'Retained file size differs: ' + name)
                with zipped.open(entry) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(stat.S_IMODE((entry.external_attr >> 16) & 0xFFFF) or 0o644)
            require(digest(target) == commitment['sha256'], 'Retained file bytes differ: ' + name)
    require('QUALIFICATION.json' not in exported['files'] and inventory(destination) == exported['files'],
            'Restored product changed or acquired a synthetic qualification')
    original_source = read_json(destination / 'SourceProvenance/OriginalSource.json')
    require(digest(destination / 'SourceProvenance/OriginalSource.json') == producer['original_source_sha256']
            and original_source['application_source'] == producer['source_sha']
            and original_source['original_trees'] == producer['source_trees'], 'Original source provenance differs')
    clang = read_json(destination / 'SourceProvenance/ClangImportContext.json')
    identity = {k: clang[k] for k in ['source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256']}
    require(identity['source_sha'] == producer['source_sha']
            and str(identity['run_id']) == str(producer['run_id'])
            and str(identity['run_attempt']) == str(producer['run_attempt']), 'Clang origin differs')
    identity['manifest_sha256'] = producer['clang_manifest_sha256']
    read_clang_imports(destination, identity)
    write_json(evidence / 'RESTORATION.json', {
        'status': 'EXACT_ORIGINAL_FULL_DISTRIBUTION_RESTORED_WITH_TWO_SOURCE_BOUND_DOTFILES',
        'historical_archive_sha256': producer['framework_artifact']['sha256'],
        'historical_archive_unchanged': True, 'archive_product_members': len(expected) - len(omissions),
        'restored_product_members': len(expected), 'restored_product_bytes': exported['bytes'],
        'omissions': producer['archive_omissions'], 'original_qualification_synthesized': False,
    })
    return identity

def validate_toolchain(actual, expected):
    require(actual == expected, 'Continuation Xcode/Swift/SDK differs from the original framework toolchain')

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--deadline-unix', required=True, type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    inputs_path = args.inputs.resolve()
    work, evidence = args.work.resolve(), args.evidence.resolve()
    require(inputs_path == root / 'Tools/OriginalEditor/runtime_continuation_inputs.json', 'Unexpected input contract path')
    require(digest(inputs_path) == args.inputs_sha256, 'Input contract differs from the reviewed workflow')
    for path in [work, evidence]:
        require(path.is_relative_to(root / 'build') and not path.exists(), 'Fresh owned continuation paths required')
    require(not work.is_relative_to(evidence) and not evidence.is_relative_to(work), 'Owned paths must be disjoint')
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    inputs = read_json(inputs_path)
    producer = inputs['framework_producer']
    current = {'repository': os.environ['GITHUB_REPOSITORY'], 'repository_id': int(os.environ['GITHUB_REPOSITORY_ID']),
        'control_sha': os.environ['GITHUB_SHA'], 'run_id': int(os.environ['GITHUB_RUN_ID']),
        'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']), 'workflow_path': WORKFLOW,
        'head_branch': os.environ['GITHUB_REF_NAME'], 'job_name': 'original-editor-runtime-continuation'}
    env = runtime_environment(os.environ)
    write_json(evidence / 'runtime-environment.json', env)
    for name in ['commands', 'github-commands', 'cleanup']:
        (evidence / name).mkdir()
    commands = Commands(evidence / 'commands', env, args.deadline_unix - 180)
    github_env = {**env, 'GH_TOKEN': os.environ['GH_TOKEN'], 'GH_PROMPT_DISABLED': '1', 'GH_PAGER': 'cat'}
    github = Commands(evidence / 'github-commands', github_env, args.deadline_unix - 180)
    def command(label, argv, cwd=root, seconds=60):
        return commands.require(label, [str(x) for x in argv], cwd, seconds).read_text(errors='replace').strip()
    def api(endpoint, label, repository=REPOSITORY):
        path = evidence / (label + '.json')
        output = github.require(label, ['gh', 'api', 'repos/' + repository + '/' + endpoint], root, 90)
        shutil.copyfile(output, path)
        return read_json(path)
    def download(item, label):
        target = work / (label + '.zip')
        code, output, error = github.run(label + '-download', ['gh', 'api', 'repos/' + REPOSITORY + '/actions/artifacts/' + str(item['id']) + '/zip'], root, 900)
        partial = target.with_suffix('.zip.partial')
        output.rename(partial)
        github.items[-1]['stdout_relocated_to_owned_work'] = partial.relative_to(work).as_posix()
        github.items[-1]['stdout_bytes'] = partial.stat().st_size
        github.persist()
        require(code == 0 and not github.items[-1]['timed_out'], 'One artifact download did not complete: ' + label)
        require(partial.stat().st_size == item['size_in_bytes'] and digest(partial) == item['sha256'], 'Downloaded artifact differs')
        partial.rename(target)
        github.items[-1]['stdout_relocated_to_owned_work'] = target.relative_to(work).as_posix()
        github.persist()
        require(target.stat().st_size == item['size_in_bytes'] and digest(target) == item['sha256'], 'Downloaded artifact differs')
        return target
    result = {'schema': 2, 'kind': 'ORIGINAL_FRAMEWORK_RUNTIME_CONTINUATION', 'status': 'FAIL', 'phase': 'INPUT_ADMISSION',
        'started_at': timestamp(), 'framework_source_sha': producer['source_sha'], 'framework_producer': producer,
        'runtime_qualification_producer': current, 'original_framework_build': 'ORIGINAL_PRODUCER_NOT_YET_ADMITTED',
        'source_controls_replayed': 0, 'retained_source_controls_passed': 0, 'external_consumer_build': 'NOT_RUN',
        'verified_runtime_observations': [], 'native_editor_ui_tests': 0, 'simulator_attempts': 0, 'install_attempts': 0,
        'automatic_retry': False}
    write_json(evidence / 'execution.json', result)
    owned_id = None
    owned_record = None
    simulator_name = None
    original_device_ids = set()
    diagnostic_groups_drained = True
    def observe(stage, reserve=180):
        nonlocal diagnostic_groups_drained
        try:
            observed = observe_runtime(evidence, stage, root, env, args.deadline_unix - reserve, owned_record)
        except BaseException:
            diagnostic_groups_drained = False
            raise
        diagnostic_groups_drained = diagnostic_groups_drained and observed['owned_groups_drained']
        result.setdefault('runtime_diagnostics', []).append(observed)
        write_json(evidence / 'execution.json', result)
        if observed.get('interrupted'):
            raise KeyboardInterrupt('Runtime diagnostics were interrupted')
    success = False
    try:
        require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Actual Darwin arm64 toolchain required')
        require(current['repository'] == REPOSITORY and current['repository_id'] == producer['repository_id']
                and current['head_branch'] == inputs['continuation_branch']
                and current['run_attempt'] == 1 and os.environ['GITHUB_EVENT_NAME'] == 'push', 'Unexpected continuation identity')
        require(inputs['schema'] == 'otzaria.original-editor.runtime-continuation-input/1'
                and inputs['continuation_workflow'] == WORKFLOW and inputs['install_timeout_seconds'] == 300
                and inputs['one_simulator_attempt'] is True and inputs['automatic_retry'] is False
                and inputs['framework_builds'] == inputs['prior_source_controls_replayed'] == 0, 'Unexpected continuation scope')
        require(args.deadline_unix <= time.time() + 2800 and commands.deadline > time.time(), 'Invalid absolute workflow budget')
        require(command('control-head', ['git', 'rev-parse', 'HEAD']) == current['control_sha'], 'Actual control checkout differs')
        command('original-ancestor', ['git', 'merge-base', '--is-ancestor', producer['source_sha'], 'HEAD'])
        delta = command('control-source-delta', ['git', 'diff', '--name-only', producer['source_sha'], 'HEAD']).splitlines()
        require(all(p in CONTROL_FILES or p.startswith(EVIDENCE_PREFIX) for p in delta), 'An original SDK product/control source changed')
        require(not command('tracked-source-status', ['git', 'status', '--porcelain', '--untracked-files=all', '--',
                'Tools', 'Anytype', 'Modules', 'OriginalEditorFramework', '.github']), 'Original or control input differs')
        require(command('committed-inputs', ['git', 'show', 'HEAD:Tools/OriginalEditor/runtime_continuation_inputs.json']) == inputs_path.read_text().strip(),
                'Input contract is not the committed control input')
        for path, tree in producer['source_trees'].items():
            require(command('source-tree-' + path.replace('/', '-'), ['git', 'rev-parse', 'HEAD:' + path]) == tree,
                    'Original compiled product source tree differs')
        run = api(f"actions/runs/{producer['run_id']}/attempts/{producer['run_attempt']}", 'original-run')
        job = api('actions/jobs/' + str(producer['job_id']), 'original-job')
        for key in ['framework_artifact', 'evidence_artifact']:
            item = producer[key]
            artifact = api('actions/artifacts/' + str(item['id']), 'original-' + key)
            verify_metadata(producer, run, job, artifact, item)
        original_evidence = extract_original_evidence(download(producer['evidence_artifact'], 'original-evidence-outer'), work, producer)
        original_execution = verify_retained_phase(producer, original_evidence)
        exported = read_json(original_evidence / 'framework-distribution.json')
        supplements = {}
        for index, item in enumerate(producer['archive_omissions']):
            response = api('contents/' + item['source_path'] + '?ref=' + item['source_sha'],
                           'original-dotfile-source-' + str(index), item['repository'])
            raw = validate_original_dotfile(item, response, exported, original_evidence)
            target = evidence / item['evidence_path']
            require(target.parent == evidence / 'original-dotfiles' and not target.exists(), 'Unexpected original dotfile receipt path')
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
            supplements[item['distribution_path']] = raw
        distribution = work / 'distribution'
        clang_identity = restore_original_distribution(download(producer['framework_artifact'], 'original-framework'),
                                                       distribution, evidence, producer, exported, supplements)
        result.update(original_framework_build='REUSED_SUCCESSFUL_ORIGINAL_PRODUCER', retained_source_controls_passed=245,
                      restoration=read_json(evidence / 'RESTORATION.json'))
        actual_toolchain = {'xcode': command('actual-xcode', ['xcodebuild', '-version']),
            'swift': command('actual-swift', ['xcrun', 'swiftc', '--version']),
            'sdk_version': command('actual-sdk', ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'])}
        validate_toolchain(actual_toolchain, producer['toolchain'])
        result.update(preflight={'xcode': actual_toolchain['xcode']}, swift=actual_toolchain['swift'], sdk=actual_toolchain['sdk_version'],
            actual_public_surface=original_execution['actual_public_surface'],
            public_surface_producer={'source_sha': producer['source_sha'], 'run_id': producer['run_id'], 'run_attempt': producer['run_attempt']},
            original_clang_declarations=original_execution['original_clang_declarations'])
        require(not Path(read_json(original_evidence / 'producer-build-path-absent.json')['original']).exists(),
                'An original producer build-path fallback is present')
        source = root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift'
        require(digest(source) == producer['consumer_source_sha256'], 'Consumer probe changed')
        profile = read_json(root / 'Tools/OriginalEditor/framework_profile.json')
        oracle = original_oracles(root, profile)
        require(oracle == read_json(original_evidence / 'independent-original-resource-oracles.json'), 'Original resource oracles differ')
        dynamic = []
        for index, name in enumerate(exported['frameworks']):
            framework = distribution / 'Frameworks' / name
            info = plistlib.loads((framework / 'Info.plist').read_bytes())
            executable = info.get('CFBundleExecutable')
            require(isinstance(executable, str) and Path(executable).name == executable,
                    'Malformed original framework executable')
            binary = framework / executable
            header = command('framework-header-' + str(index), ['otool', '-hv', binary])
            if re.search(r'\bDYLIB\b', header):
                command('framework-signature-' + str(index), ['codesign', '--verify', '--strict', distribution / 'Frameworks' / name])
                dynamic.append(name)
        require('AnytypeOriginalEditor.framework' in dynamic, 'Original dynamic editor framework is absent')
        consumer = work / 'external-consumer'
        project = consumer_project(consumer, distribution, source, dynamic, clang_identity)
        require(inventory(consumer) == read_json(original_evidence / 'consumer-source-inputs.json'), 'Recreated consumer source/project differs')
        write_json(evidence / 'consumer-source-inputs.json', inventory(consumer))
        runtimes = json.loads(command('available-runtimes', ['xcrun', 'simctl', 'list', 'runtimes', '-j']))['runtimes']
        matches = [r for r in runtimes if all(r.get(k) == v for k,v in inputs['runtime'].items()) and r.get('isAvailable')]
        require(len(matches) == 1 and 'arm64' in matches[0].get('supportedArchitectures', []), 'Original OS27 runtime is unavailable')
        require(any(t.get('identifier') == inputs['device']['identifier'] for t in matches[0]['supportedDeviceTypes']), 'Original iPad type is unsupported')
        simulator_name = 'Otzaria-Original-Editor-Continuation-' + str(current['run_id']) + '-' + str(current['run_attempt'])
        existing = json.loads(command('devices-before', ['xcrun', 'simctl', 'list', 'devices', '-j']))['devices']
        original_device_ids = {d['udid'] for devices in existing.values() for d in devices}
        require(not any(d.get('name') == simulator_name for devices in existing.values() for d in devices), 'Owned simulator name already exists')
        result['simulator_attempts'] = 1
        write_json(evidence / 'execution.json', result)
        created = command('create-owned-simulator', ['xcrun', 'simctl', 'create', simulator_name, inputs['device']['identifier'], inputs['runtime']['identifier']])
        require(str(uuid.UUID(created)).upper() == created.upper() and created not in original_device_ids,
                'Simulator creation returned no new exact identity')
        owned_id = created
        owned_record = {'udid': owned_id, 'name': simulator_name, 'device': inputs['device'], 'runtime': inputs['runtime']}
        validate_ownership(owned_record, simulator_name, inputs['device'], inputs['runtime'], original_device_ids)
        write_json(evidence / 'owned-simulator.json', owned_record)
        result['preflight']['selected'] = {'ipad': {'udid': owned_id, 'name': simulator_name, 'device': inputs['device'], 'runtime': inputs['runtime']}}
        derived = work / 'consumer-derived'
        result['phase'] = 'EXTERNAL_BINARY_CONSUMER_BUILD'
        write_json(evidence / 'execution.json', result)
        command('external-consumer-build', ['xcodebuild', 'build', '-project', project, '-scheme', 'OriginalEditorConsumer',
            '-configuration', 'Debug', '-destination', 'platform=iOS Simulator,id=' + owned_id, '-derivedDataPath', derived,
            '-resultBundlePath', evidence / 'consumer-build.xcresult', 'ONLY_ACTIVE_ARCH=YES', 'ARCHS=arm64'], consumer, 600)
        app = derived / 'Build/Products/Debug-iphonesimulator/OriginalEditorConsumer.app'
        command('external-consumer-signature', ['codesign', '--verify', '--strict', app])
        consumer_signature = commands.items[-1]
        for name in dynamic:
            require(inventory(app / 'Frameworks' / name) == inventory(distribution / 'Frameworks' / name), 'Embedded original framework differs: ' + name)
        app_inventory = inventory(app)
        write_json(evidence / 'consumer-app-inventory.json', app_inventory)
        result.update(external_consumer_build='PASS', compiled_consumer_api_probe_sha256=digest(source),
            public_host_api='EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN', editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN',
            consumer_app_bytes=sum(v['bytes'] for v in app_inventory.values()), consumer_app_files=len(app_inventory),
            consumer_app_inventory_sha256=digest(evidence / 'consumer-app-inventory.json'), phase='ACTUAL_EXTERNAL_RESOURCE_RUNTIME')
        require(inventory(distribution) == exported['files'], 'Consumer build changed the retained original SDK')
        result['phase'] = 'RETAIN_SIGNED_CONSUMER'
        write_json(evidence / 'execution.json', result)
        result['retained_signed_consumer'] = retain_signed_consumer(app, app_inventory, consumer_signature,
            work / 'retained-consumer', current, producer, digest(source),
            digest(evidence / 'consumer-source-inputs.json'), args.deadline_unix - 180)
        write_json(evidence / 'retained-consumer.json', result['retained_signed_consumer'])
        result['phase'] = 'ACTUAL_EXTERNAL_RESOURCE_RUNTIME'
        write_json(evidence / 'execution.json', result)
        observe('before-boot')
        require(diagnostic_groups_drained, 'A diagnostic command group did not drain before boot')
        command('boot-owned-simulator', ['xcrun', 'simctl', 'boot', owned_id], seconds=60)
        command('boot-status', ['xcrun', 'simctl', 'bootstatus', owned_id, '-b'], seconds=180)
        observe('after-boot')
        require(diagnostic_groups_drained, 'A diagnostic command group did not drain before install')
        result['install_attempts'] = 1
        write_json(evidence / 'execution.json', result)
        command('install-external-consumer', ['xcrun', 'simctl', 'install', owned_id, app], seconds=inputs['install_timeout_seconds'])
        bundle = 'org.otzaria.acceptance.original-editor'
        installed = Path(command('installed-app-container', ['xcrun', 'simctl', 'get_app_container', owned_id, bundle, 'app']))
        data = Path(command('installed-data-container', ['xcrun', 'simctl', 'get_app_container', owned_id, bundle, 'data']))
        require(installed.is_dir() and data.is_dir() and owned_id in installed.parts and owned_id in data.parts, 'Wrong owned runtime containers')
        for language in ['en', 'he']:
            nonce = str(uuid.uuid4()).upper()
            output = data / 'Documents' / ('original-editor-' + nonce + '.json')
            require(not output.exists(), 'Stale consumer observation')
            command('consumer-' + language + '-launch', ['xcrun', 'simctl', 'launch', '--terminate-running-process', owned_id, bundle,
                '--original-editor-nonce', nonce, '-AppleLanguages', '(' + language + ')', '-AppleLocale', 'he_IL' if language == 'he' else 'en_US'])
            deadline = min(time.monotonic() + 20, commands.monotonic_deadline)
            while not output.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 65536, 'No bounded actual consumer observation')
            raw = output.read_bytes()
            (evidence / ('consumer-' + language + '-observation.json')).write_bytes(raw)
            result['verified_runtime_observations'].append(verify_observation(json.loads(raw), nonce, language, installed, oracle))
            write_json(evidence / 'execution.json', result)
            command('consumer-' + language + '-terminate', ['xcrun', 'simctl', 'terminate', owned_id, bundle])
        require(len(result['verified_runtime_observations']) == 2 and inventory(app) == app_inventory
                and inventory(distribution) == exported['files'], 'Consumer or SDK changed during qualification')
        require(not command('source-after', ['git', 'status', '--porcelain', '--untracked-files=all', '--',
                'Tools', 'Anytype', 'Modules', 'OriginalEditorFramework', '.github']), 'Original or control input changed')
        require(not Path(read_json(original_evidence / 'producer-build-path-absent.json')['original']).exists(),
                'Original producer fallback appeared during qualification')
        result.update(distribution_unchanged=True, distribution_manifest_sha256=producer['retained_input_sha256']['framework-distribution.json'],
            original_source_sha256=digest(distribution / 'SourceProvenance/OriginalSource.json'),
            hanlin_source_sha256=producer['retained_input_sha256']['original-hanlin-snapshot.json'],
            same_toolchain_only=True, device_framework_build='NOT_RUN', original_app_runtime='NOT_RUN')
        success = True
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        if (owned_record and commands.owned_groups_drained and github.owned_groups_drained
                and diagnostic_groups_drained and not isinstance(error, KeyboardInterrupt)):
            try:
                observe('after-runtime-failure')
            except BaseException as diagnostic_error:
                result['failure_diagnostic_error'] = {'type': type(diagnostic_error).__name__, 'error': str(diagnostic_error)}
    finally:
        cleanup = Commands(evidence / 'cleanup', env, args.deadline_unix)
        try:
            require(commands.owned_groups_drained and github.owned_groups_drained and diagnostic_groups_drained,
                    'A continuation-owned command group has not drained')
            if owned_id is None and result['simulator_attempts'] == 1:
                out = cleanup.require('recover-create-identity', ['xcrun', 'simctl', 'list', 'devices', '-j'], root, 30)
                actual = json.loads(out.read_bytes())['devices']
                matches = [d for d in actual.get(inputs['runtime']['identifier'], [])
                           if d.get('name') == simulator_name and d.get('udid') not in original_device_ids
                           and d.get('deviceTypeIdentifier') == inputs['device']['identifier']]
                require(len(matches) == 1, 'Creation outcome is uncertain; no broad simulator cleanup is permitted')
                owned_id = matches[0]['udid']
                owned_record = {'udid': owned_id, 'name': simulator_name, 'device': inputs['device'], 'runtime': inputs['runtime']}
                write_json(evidence / 'owned-simulator-recovered-for-cleanup.json', matches[0])
            if owned_id is not None:
                if success:
                    observe('before-cleanup', reserve=150)
                require(diagnostic_groups_drained, 'A diagnostic command group did not drain before cleanup')
                result['owned_simulator_cleanup'] = cleanup_owned_simulator(cleanup, root, owned_record,
                    simulator_name, inputs['device'], inputs['runtime'], original_device_ids)
                # Preserve every cleanup outcome before diagnostics or admission.
                write_json(evidence / 'execution.json', result)
                if cleanup.owned_groups_drained:
                    observe('after-cleanup', reserve=0)
                require(result['owned_simulator_cleanup']['completed'], 'Owned simulator deletion and absence were not proven')
            require(cleanup.owned_groups_drained and diagnostic_groups_drained, 'An owned cleanup or diagnostic group did not drain')
            result['owned_simulator_cleanup_completed'] = True
        except BaseException as error:
            success = False
            result.update(cleanup_error_type=type(error).__name__, cleanup_error=str(error))
        result['finished_at'] = timestamp()
        if success:
            result.update(status=QUALIFIED, phase='COMPLETE')
        write_json(evidence / 'execution.json', result)
        if success:
            write_json(evidence / 'runtime-qualification.json', result)
        write_json(evidence / 'EVIDENCE_INDEX.json', {'files': [
            {'path': p.relative_to(evidence).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
            for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'EVIDENCE_INDEX.json']})
    print(json.dumps({k: result.get(k) for k in ['status', 'phase', 'error', 'cleanup_error', 'framework_source_sha',
        'runtime_qualification_producer', 'external_consumer_build', 'consumer_app_bytes', 'verified_runtime_observations']}))
    return 0 if success else 1

if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Continuation interruption signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
