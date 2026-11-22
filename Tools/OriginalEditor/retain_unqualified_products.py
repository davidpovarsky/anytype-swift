import argparse
import json
import os
from pathlib import Path
import subprocess

from framework_profile import TARGET, sha256
from framework_products import inventory
from pbx_source import require


def retain(root, evidence, work):
    root, evidence = (Path(value).resolve(strict=True) for value in (root, evidence))
    work = Path(work)
    require(not work.is_symlink(), 'Unqualified work root is an alias')
    work = work.resolve()
    require(evidence.is_relative_to(root / 'build') and work.is_relative_to(root / 'build')
            and not evidence.is_relative_to(work) and not work.is_relative_to(evidence),
            'Unowned retention input')
    if not work.exists():
        return {'status': 'NO_WRITTEN_PRODUCER_OUTPUTS_TO_RETAIN'}
    execution_path = evidence / 'execution.json'
    if not execution_path.is_file():
        return {'status': 'NO_ACTUAL_FRAMEWORK_RECEIPT_TO_RETAIN'}
    execution = json.loads(execution_path.read_bytes())
    if execution.get('status') != 'FAIL' or execution.get('original_framework_build') != 'PASS':
        return {'status': 'NO_FAILED_CONSUMER_PRODUCER_TO_RETAIN'}
    exported = work / 'distribution'
    require(exported.is_dir() and not exported.is_symlink(), 'Missing real producer distribution')
    original_binary = exported / 'Frameworks' / (TARGET + '.framework') / TARGET
    require(original_binary.is_file() and not original_binary.is_symlink(),
            'Missing real original framework binary')
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                          capture_output=True, check=True, timeout=30).stdout.decode().strip()
    require(head == execution.get('source_sha') == os.environ.get('GITHUB_SHA')
            and execution.get('run_id') == os.environ.get('GITHUB_RUN_ID')
            and execution.get('run_attempt') == os.environ.get('GITHUB_RUN_ATTEMPT'),
            'Unqualified producer identity differs from this actual run')
    before_path, after_path = evidence / 'source-before.json', evidence / 'source-after.json'
    before, after = (json.loads(path.read_bytes()) for path in (before_path, after_path))
    require(before == after and before.get('head_sha') == head,
            'Original framework source changed during actual execution')
    command_path = evidence / 'framework-build.command.json'
    command = json.loads(command_path.read_bytes())
    require(command.get('returncode') == 0 and command.get('timed_out') is False,
            'Original framework command did not complete successfully')
    archive = evidence / 'Pinkha-Native-Derived-Evidence.zip'
    require(archive.is_file() and not archive.is_symlink(), 'Complete source evidence archive is missing')
    files = inventory(exported)
    require(files and len(files) <= 12000
            and sum(item['bytes'] for item in files.values()) <= 4 * 1024 * 1024 * 1024,
            'Unexpected unqualified producer closure size')
    record = {'schema': 1, 'status': 'UNQUALIFIED_PRODUCER_OUTPUTS_RETAINED',
              'source_sha': head, 'run_id': execution['run_id'], 'run_attempt': execution['run_attempt'],
              'failure_phase': execution.get('phase'), 'failure': execution.get('error'),
              'original_framework_build': 'PASS', 'original_public_surface': execution.get('actual_public_surface'),
              'external_consumer_build': execution.get('external_consumer_build'),
              'source_before_sha256': sha256(before_path), 'source_after_sha256': sha256(after_path),
              'successful_build_command_sha256': sha256(command_path),
              'actual_execution_sha256': sha256(execution_path),
              'source_evidence_archive': {'name': archive.name, 'bytes': archive.stat().st_size,
                                          'sha256': sha256(archive)},
              'distribution_files': files, 'distribution_bytes': sum(item['bytes'] for item in files.values()),
              'same_toolchain_only': True, 'qualified_distribution': False, 'restore_as_sdk_allowed': False,
              'consumer_continuation_admission': 'NOT_IMPLEMENTED_OR_GRANTED',
              'scope': 'Preserved actual outputs and failure evidence only; every future reuse requires its own exact source/toolchain/closure admission and all unfinished consumer/runtime gates'}
    target = work / 'UNQUALIFIED_PRODUCER.json'
    require(not os.path.lexists(target), 'Refusing to replace retained producer provenance')
    with target.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return {'status': record['status'], 'path': str(target), 'sha256': sha256(target),
            'distribution_files': len(files), 'distribution_bytes': record['distribution_bytes']}


def main():
    parser = argparse.ArgumentParser()
    for name in ('root', 'evidence', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(retain(args.root, args.evidence, args.work), sort_keys=True))


if __name__ == '__main__':
    main()
