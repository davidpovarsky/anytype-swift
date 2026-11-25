#!/usr/bin/env python3
"""Create a genuine Mac producer identity and disposable native preflight.

This does not build a framework or install a Heart binary. Those remain separate
qualified inputs to run_framework_acceptance.py.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

from local_execution import (LOCAL_BRANCHES, REPOSITORY, SCHEMA, git,
                             machine_identity, require, sha)


def write(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare(root, evidence, work):
    root, evidence, work = map(lambda value: Path(value).resolve(), (root, evidence, work))
    require(evidence.is_relative_to(root / 'build') and work.is_relative_to(root / 'build')
            and evidence != work and not evidence.is_relative_to(work)
            and not work.is_relative_to(evidence) and not evidence.exists() and not work.exists(),
            'Local evidence and build roots must be fresh, owned and disjoint')
    host = machine_identity()
    require(host['system'] == 'Darwin' and host['architecture'] == 'arm64'
            and sys.version_info >= (3, 12), 'Actual Apple silicon and Python 3.12+ are required')
    require(not any(os.environ.get(k) for k in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')),
            'Do not use synthetic Actions metadata for local execution')
    branch = git(root, 'branch', '--show-current')
    require(branch in LOCAL_BRANCHES
            and not git(root, 'diff', '--name-only', 'HEAD'), 'Exact clean owned branch required')
    head, tree = git(root, 'rev-parse', 'HEAD'), git(root, 'rev-parse', 'HEAD^{tree}')
    xcode = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
    require(xcode == 'Xcode 27.0\nBuild version 27A266a', 'The qualified Xcode 27 toolchain is required')
    execution_id = 'local-' + str(uuid.uuid4())
    evidence.mkdir(parents=True)
    record = {'schema': SCHEMA, 'repository': REPOSITORY, 'execution_id': execution_id,
              'source_sha': head, 'source_tree': tree, 'head_branch': branch,
              'root': str(root), 'host': host, 'owner': ('ChatGPT/anytype_resume' if branch in {'codex/anytype-original-miniapps-facade-20261125',
                                                                                     'codex/anytype-original-sdk-collections13-20261125'}
                                                  else 'ChatGPT/native_import'),
              'started_at': datetime.now(timezone.utc).isoformat(),
              'evidence_root': str(evidence), 'work_root': str(work),
              'runner_sha256': sha(root / 'Tools/OriginalEditor/run_framework_acceptance.py'),
              'acceptance': 'PROVENANCE_ONLY_NOT_ACCEPTANCE'}
    descriptor = evidence / 'local-execution.json'
    write(descriptor, record)
    environment = {'OTZARIA_LOCAL_EXECUTION': str(descriptor),
                   'OTZARIA_LOCAL_EXECUTION_SHA256': sha(descriptor)}
    with (evidence / 'local-execution.env').open('x') as stream:
        for key, value in environment.items():
            stream.write('export ' + key + '=' + shlex.quote(value) + '\n')
    preflight_dir = evidence / 'preflight'
    preflight_dir.mkdir()
    preflight = {'status': 'FAIL', 'phase': 'PREFLIGHT', 'ui_tests_executed': 0,
                 'source_sha': head, 'run_id': execution_id, 'run_attempt': '1',
                 'producer_kind': 'local-mac', 'local_execution_sha256': sha(descriptor),
                 'selected': {}, 'xcode': xcode, 'host_architecture': host['architecture'],
                 'python': sys.version, 'started_at': record['started_at']}
    try:
        sys.path.insert(0, str(root / 'Tools/PinkhaSimulatorGate'))
        from preflight import select_pairs
        inventory = json.loads(subprocess.check_output(['xcrun', 'simctl', 'list', '--json']))
        write(preflight_dir / 'simulator-inventory.json', inventory)
        runtime, devices = select_pairs(inventory)
        for kind, device in devices.items():
            name = 'Pinkha-UI27-' + execution_id + '-' + kind
            udid = subprocess.check_output(['xcrun', 'simctl', 'create', name,
                                            device['identifier'], runtime['identifier']], text=True).strip()
            require(re.fullmatch(r'[A-Fa-f0-9-]{36}', udid), 'Invalid disposable simulator identity')
            preflight['selected'][kind] = {'udid': udid, 'device': device,
                                           'runtime': runtime, 'name': name}
        preflight.update(status='PREFLIGHT_PASS_UI_NOT_RUN',
                         swift=subprocess.check_output(['xcrun', 'swiftc', '--version'], text=True).strip(),
                         sdks=subprocess.check_output(['xcodebuild', '-showsdks'], text=True).strip(),
                         developer_dir=subprocess.check_output(['xcode-select', '-p'], text=True).strip())
    except BaseException as error:
        preflight.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        preflight['finished_at'] = datetime.now(timezone.utc).isoformat()
        write(preflight_dir / 'preflight.json', preflight)
    return {'environment': environment, 'preflight': preflight,
            'source_acceptance': 'NOT_RUN', 'build_acceptance': 'NOT_RUN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('root', 'evidence', 'work'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.evidence, args.work), indent=2))
