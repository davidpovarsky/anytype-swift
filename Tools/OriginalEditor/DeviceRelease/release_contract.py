"""Separate provenance for Release builds of an already qualified SDK source.

The old source/ABI owner is retained verbatim. A new Release identity describes
only this external controller and the actual new compiler invocation.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

SOURCE = '34b8a7c5ddb34e9287acdb5c189849eeac8cff86'
REPOSITORY = 'davidpovarsky/anytype-swift'
SCHEMA = 'otzaria.original-editor.release-execution/1'
CONFIGURATION = 'Release-Anytype'
SIMULATOR_PASS = 'ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS'
DEVICE_PASS = 'ACTUAL_ORIGINAL_RELEASE_DEVICE_BUILD_LINK_API_PLATFORM_PASS'
CONTROL_PREFIX = 'Tools/OriginalEditor/DeviceRelease/'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or aliased receipt/control file')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def controller_observation(root):
    root = Path(root).resolve(strict=True)
    require(not git(root, 'diff', '--name-only', 'HEAD'), 'Controller has uncommitted changes')
    changed = git(root, 'diff', '--name-only', SOURCE, 'HEAD').splitlines()
    require(changed and all(p.startswith(CONTROL_PREFIX) for p in changed),
            'External controller must change only its isolated DeviceRelease files')
    files = git(root, 'ls-files', '--', CONTROL_PREFIX).splitlines()
    require(files and not git(root, 'ls-files', '--others', '--', CONTROL_PREFIX),
            'Untracked external controller inputs')
    observed = {}
    for name in files:
        path = root / name
        raw = path.read_bytes()
        require(path.is_file() and not path.is_symlink()
                and git(root, 'hash-object', '--', name) == git(root, 'rev-parse', 'HEAD:' + name),
                'External controller differs from its committed source')
        observed[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return {'sha': git(root, 'rev-parse', 'HEAD'), 'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
            'root': str(root), 'files': observed}


def verify_original_helpers(root, control_root):
    records = json.loads((control_root / CONTROL_PREFIX / 'REUSED_ORIGINAL_CONTROLS.json').read_text())
    for item in records.values():
        require(digest(root / item['original_path']) == item['original_sha256'],
                'A reused original helper changed after the reviewed Release adaptation: ' + item['original_path'])
    return records


def validate_execution(value, root, control, platform_name):
    require(platform_name in {'iphoneos', 'iphonesimulator'}
            and value.get('schema') == SCHEMA and value.get('repository') == REPOSITORY
            and re.fullmatch(r'[a-f0-9]{40}', value.get('source_sha', ''))
            and value.get('source_sha') == git(root, 'rev-parse', 'HEAD') and value.get('root') == str(root)
            and value.get('source_tree') == git(root, 'rev-parse', 'HEAD^{tree}')
            and value.get('control_sha') == control['sha']
            and value.get('control_tree') == control['tree']
            and value.get('control_root') == control['root']
            and value.get('control_files') == control['files']
            and value.get('platform') == platform_name
            and value.get('configuration') == CONFIGURATION
            and value.get('host', {}).get('system') == 'Darwin'
            and value.get('host', {}).get('architecture') == 'arm64'
            and value['host'].get('hostname')
            and value.get('acceptance') == 'PROVENANCE_ONLY_NOT_ACCEPTANCE',
            'Actual Release source/control/platform provenance differs')
    run = value.get('execution_id', '')
    require(run.startswith('local-') and str(uuid.UUID(run[6:])) == run[6:],
            'Release identity must be a genuine local execution UUID')


def identity(value, path):
    return {'producer_kind': 'local-mac', 'source_sha': value['source_sha'],
            'run_id': value['execution_id'], 'run_attempt': '1',
            'local_execution_sha256': digest(path), 'local_execution': value}


def admit_original_owner(root, abi_execution, abi_execution_sha256, abi_source_before,
                         abi_receipt, abi_sha256, simulator_qualification,
                         simulator_qualification_sha256, source_sha):
    from framework_profile import source_observation
    from import_abi_input import verify
    paths = list(map(Path, [abi_execution, abi_source_before, abi_receipt, simulator_qualification]))
    require(all(p.is_absolute() and p.is_relative_to(root / 'build') and not p.is_symlink()
                for p in paths), 'ABI/SDK receipts must stay in their actual original build owner')
    require(digest(abi_execution) == abi_execution_sha256,
            'Original ABI execution bytes differ')
    original = json.loads(Path(abi_execution).read_text())
    require(original.get('schema') == 'otzaria.original-editor.local-execution/1'
            and original.get('source_sha') == source_sha and original.get('root') == str(root)
            and git(root, 'rev-parse', 'HEAD') == source_sha,
            'Release must compile the same actual SDK root and commit as the ABI producer')
    environment = dict(os.environ)
    require(not any(environment.get(k) for k in ['GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']),
            'A local Release execution cannot borrow GitHub identities')
    environment.update(OTZARIA_LOCAL_EXECUTION=str(abi_execution),
                       OTZARIA_LOCAL_EXECUTION_SHA256=abi_execution_sha256)
    # Existing observation deliberately keeps the old owner. Do not substitute
    # the Release UUID into these bytes or the original ABI receipt.
    before = json.loads(Path(abi_source_before).read_text())
    require(before == source_observation(root, environment),
            'Current source closure differs from the qualified ABI owner')
    admitted = verify(root, Path(abi_receipt), abi_sha256, before)
    require(digest(simulator_qualification) == simulator_qualification_sha256,
            'Retained Debug Simulator qualification bytes differ')
    q = json.loads(Path(simulator_qualification).read_text())
    require(q.get('status') == SIMULATOR_PASS and q.get('phase') == 'COMPLETE'
            and q.get('source_sha') == source_sha
            and q.get('execution_identity') == before['execution_identity']
            and q.get('heart') == admitted
            and q.get('shared_runtime_ownership', {}).get('status') == 'PASS_OBSERVED_SINGLE_SHARED_IMPLEMENTATIONS'
            and len(q.get('verified_runtime_observations', [])) == 2
            and {v.get('language') for v in q['verified_runtime_observations']} == {'en', 'he'},
            'Release requires the actual complete original Debug SDK qualification')
    return before, admitted, environment


def current_build_context(before, execution, descriptor):
    require(before['head_sha'] == execution['source_sha'], 'Release/source closure mismatch')
    # This is explicitly a new compiler context, never a replacement source
    # observation or a claim that the old ABI belonged to this execution.
    context = dict(before)
    context.update(status='RELEASE_COMPILER_CONTEXT_SOURCE_FACTS_UNCHANGED',
                   run_id=execution['execution_id'], run_attempt='1',
                   execution_identity=identity(execution, descriptor),
                   original_source_observation_sha256=hashlib.sha256(
                       (json.dumps(before, indent=2, sort_keys=True) + '\n').encode()).hexdigest())
    return context


def create_execution(root, control, evidence, work, platform_name, argv, source_sha):
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64'
            and sys.version_info >= (3, 12), 'Actual Apple silicon/Python 3.12+ required')
    require(not evidence.exists() and not work.exists()
            and evidence.is_relative_to(root / 'build') and work.is_relative_to(root / 'build')
            and not evidence.is_relative_to(work) and not work.is_relative_to(evidence),
            'Release evidence and work must be fresh, disjoint owned build directories')
    value = {'schema': SCHEMA, 'repository': REPOSITORY,
             'execution_id': 'local-' + str(uuid.uuid4()), 'source_sha': source_sha,
             'source_tree': git(root, 'rev-parse', 'HEAD^{tree}'), 'root': str(root),
             'control_sha': control['sha'], 'control_tree': control['tree'],
             'control_root': control['root'], 'control_files': control['files'],
             'configuration': CONFIGURATION, 'platform': platform_name,
             'architectures': ['arm64'], 'host': {'system': platform.system(),
                 'architecture': platform.machine(), 'hostname': platform.node()},
             'evidence_root': str(evidence), 'work_root': str(work),
             'controller_argv': argv, 'started_at': timestamp(),
             'owner': 'ChatGPT/native_import', 'acceptance': 'PROVENANCE_ONLY_NOT_ACCEPTANCE'}
    validate_execution(value, root, control, platform_name)
    evidence.mkdir(parents=True)
    path = evidence / 'release-execution.json'
    write(path, value)
    return value, path
