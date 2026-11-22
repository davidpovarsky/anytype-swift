"""Adapt this genuine producer's signature receipt to the unchanged archiver.

The framework and consumer are both built by this producer. Retaining their
signed app bytes before boot does not grant runtime qualification or assert
the original command runner's process-group drain beyond its recorded result.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time

from framework_profile import BRANCH, REPOSITORY, sha256
from product_inventory import inventory
from runtime_continuation_observation import retain_signed_consumer


def require(condition, message):
    if not condition:
        raise ValueError(message)


def current_producers(source, environment):
    require(source.get('head_sha') == environment.get('GITHUB_SHA')
            and re.fullmatch(r'[0-9a-f]{40}', source.get('head_sha', ''))
            and source.get('run_id') == environment.get('GITHUB_RUN_ID')
            and re.fullmatch(r'[1-9][0-9]*', source.get('run_id', ''))
            and source.get('run_attempt') == environment.get('GITHUB_RUN_ATTEMPT') == '1'
            and environment.get('GITHUB_REPOSITORY') == REPOSITORY
            and re.fullmatch(r'[1-9][0-9]*', environment.get('GITHUB_REPOSITORY_ID', ''))
            and environment.get('GITHUB_REF') == 'refs/heads/' + BRANCH,
            'Signed consumer retention is not bound to this original producer')
    consumer = {'repository': REPOSITORY, 'repository_id': int(environment['GITHUB_REPOSITORY_ID']),
                'control_sha': source['head_sha'], 'run_id': int(source['run_id']), 'run_attempt': 1,
                'workflow_path': '.github/workflows/pinkha-original-editor-framework.yml',
                'head_branch': BRANCH, 'job_name': 'original-editor-framework'}
    framework = dict(consumer)
    framework['source_sha'] = framework.pop('control_sha')
    return consumer, framework


def adapt_signature(app, root, evidence):
    app, root, evidence = map(Path, (app, root, evidence))
    path = evidence / 'external-consumer-signature.command.json'
    require(path.is_file() and not path.is_symlink(), 'Actual consumer signature receipt is absent/aliased')
    raw = path.read_bytes()
    observed = json.loads(raw)
    expected = ['codesign', '--verify', '--strict', str(app)]
    require(observed.get('command') == expected and observed.get('cwd') == str(root)
            and type(observed.get('returncode')) is int and observed['returncode'] == 0
            and observed.get('timed_out') is False, 'Actual consumer signature command did not succeed')
    for stream in ['stdout', 'stderr']:
        output = evidence / ('external-consumer-signature.' + stream + '.log')
        require(output.is_file() and not output.is_symlink() and sha256(output) == observed.get(stream + '_sha256'),
                'Actual consumer signature output differs')
    return {'label': 'external-consumer-signature', 'argv': expected, 'status': 'TERMINAL',
            'returncode': observed['returncode'], 'effective_returncode': observed['returncode'],
            'timed_out': False, 'original_command_sha256': hashlib.sha256(raw).hexdigest(),
            'original_command_receipt': str(path),
            'scope': 'Exact successful original command receipt; no additional process-group drain claim.'}


def retain_built_consumer(app, root, evidence, work, source):
    root, evidence, work, app = map(Path, (root, evidence, work, app))
    consumer, framework = current_producers(source, os.environ)
    signature = adapt_signature(app, root, evidence)
    actual_inventory = inventory(app)
    return retain_signed_consumer(app, actual_inventory, signature, work / 'retained-consumer',
                                  consumer, framework,
                                  sha256(root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift'),
                                  sha256(evidence / 'consumer-source-inputs.json'), time.time() + 180)
