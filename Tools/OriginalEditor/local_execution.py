"""An explicit identity for the owner's Mac, separate from GitHub Actions.

This binds an execution to the current clean Git source and actual machine.
It grants no build, ABI, editor or runtime acceptance by itself.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import uuid

SCHEMA = 'otzaria.original-editor.local-execution/1'
REPOSITORY = 'davidpovarsky/anytype-swift'
LOCAL_BRANCH = 'codex/otzaria-sdk-mac-20261124'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def machine_identity():
    return {'system': platform.system(), 'architecture': platform.machine(),
            'hostname': platform.node()}


def validate_record(record, root, head, tree, branch, machine):
    require(record.get('schema') == SCHEMA and record.get('repository') == REPOSITORY,
            'Unknown local producer identity')
    execution_id = record.get('execution_id', '')
    require(execution_id.startswith('local-') and
            str(uuid.UUID(execution_id[6:])) == execution_id[6:],
            'Local execution must have its own UUID, not a GitHub run ID')
    require(re.fullmatch(r'[0-9a-f]{40}', head) and re.fullmatch(r'[0-9a-f]{40}', tree)
            and record.get('source_sha') == head and record.get('source_tree') == tree
            and record.get('head_branch') == branch == LOCAL_BRANCH,
            'Local producer source or branch differs')
    require(record.get('root') == str(Path(root).resolve())
            and record.get('host') == machine
            and machine.get('system') == 'Darwin' and machine.get('architecture') == 'arm64'
            and bool(machine.get('hostname')),
            'Local producer root or actual Apple silicon host differs')
    require(record.get('acceptance') == 'PROVENANCE_ONLY_NOT_ACCEPTANCE',
            'Execution identity must not assert product acceptance')
    return record


def read_identity(environment=None):
    env = os.environ if environment is None else environment
    require(env.get('OTZARIA_LOCAL_EXECUTION') and env.get('OTZARIA_LOCAL_EXECUTION_SHA256'),
            'Both local execution descriptor and exact digest are required')
    require(not any(env.get(k) for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA')),
            'Local and GitHub producer identities cannot be mixed')
    path = Path(env['OTZARIA_LOCAL_EXECUTION'])
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16384
            and sha(path) == env['OTZARIA_LOCAL_EXECUTION_SHA256'],
            'Local execution descriptor bytes differ')
    record = json.loads(path.read_bytes())
    root = Path(record['root'])
    require(root.is_absolute() and root.resolve() == root
            and path.resolve().is_relative_to(root / 'build'),
            'Local execution descriptor is outside its owned build root')
    validate_record(record, root, git(root, 'rev-parse', 'HEAD'),
                    git(root, 'rev-parse', 'HEAD^{tree}'),
                    git(root, 'branch', '--show-current'), machine_identity())
    runner = root / 'Tools/OriginalEditor/run_framework_acceptance.py'
    require(record.get('runner_sha256') == sha(runner), 'Local producer runner changed')
    return record


def current_identity(environment=None):
    env = os.environ if environment is None else environment
    if env.get('OTZARIA_LOCAL_EXECUTION'):
        value = read_identity(env)
        return {'source_sha': value['source_sha'], 'run_id': value['execution_id'],
                'run_attempt': '1', 'producer_kind': 'local-mac',
                'local_execution': value,
                'local_execution_sha256': env['OTZARIA_LOCAL_EXECUTION_SHA256']}
    return {'source_sha': env.get('GITHUB_SHA'), 'run_id': env.get('GITHUB_RUN_ID'),
            'run_attempt': env.get('GITHUB_RUN_ATTEMPT'), 'producer_kind': 'github-actions'}
