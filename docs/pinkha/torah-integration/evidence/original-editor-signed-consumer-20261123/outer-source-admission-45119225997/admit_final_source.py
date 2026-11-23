#!/usr/bin/env python3
"""Execute unchanged source admissions; never simulate Darwin or invoke native tools."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(exist_ok=False)
    packet = root / 'docs/pinkha/torah-integration/evidence/original-editor-signed-consumer-20261123'
    owned = packet / 'outer-source-admission-45119225997'
    result = {
        'schema': 1, 'status': 'FAIL', 'kind': 'UNCHANGED_SOURCE_ADMISSION_ONLY',
        'source_sha': args.expected_source, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'workflow_source_blocks_executed': 0, 'driver_source_segments_executed': 0,
        'retained_tests_reexecuted': 0, 'new_role_tests_reexecuted': 0,
        'native_tools_invoked': 0, 'ci_identity_simulated': False, 'commands': [],
    }
    def command(name, argv, seconds=60):
        assert argv[0] in ('git', sys.executable), argv
        start = datetime.now(timezone.utc).isoformat()
        proc = subprocess.run(argv, cwd=root, capture_output=True, timeout=seconds)
        ordinal = len(result['commands']) + 1
        out = output / (str(ordinal).zfill(2) + '-' + name + '.stdout')
        err = output / (str(ordinal).zfill(2) + '-' + name + '.stderr')
        out.write_bytes(proc.stdout)
        err.write_bytes(proc.stderr)
        result['commands'].append({
            'name': name, 'argv': argv, 'cwd': str(root), 'started_utc': start,
            'returncode': proc.returncode, 'stdout': out.name, 'stderr': err.name,
            'stdout_sha256': sha(out), 'stderr_sha256': sha(err),
            'stdout_bytes': len(proc.stdout), 'stderr_bytes': len(proc.stderr),
        })
        assert proc.returncode == 0, (name, proc.returncode, proc.stderr.decode(errors='replace'))
        return proc.stdout.decode().strip()
    try:
        assert __debug__, 'Python assertion optimization must be disabled'
        assert command('exact-head', ['git', 'rev-parse', 'HEAD']) == args.expected_source
        result['tree_sha'] = command('exact-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        assert not command('complete-source-status', ['git', 'status', '--porcelain', '--untracked-files=all'])
        plan = json.loads((owned / 'ADMISSION_PLAN.json').read_bytes())
        workflow = root / '.github/workflows/pinkha-original-editor-signed-consumer.yml'
        assert sha(workflow) == plan['workflow_sha256']
        text = workflow.read_text()
        start = text.index('      - name: Admit already executed focused source controls\n')
        end = text.index('      - name: Qualify exact signed consumer in English and Hebrew\n', start)
        block = text[start:end]
        workflow_source = textwrap.dedent(
            block.split("          python3 - <<'PY'\n", 1)[1].rsplit("          PY\n", 1)[0]
        )
        assert workflow_source.encode() == (owned / 'unchanged-workflow-source-admission.py').read_bytes()
        assert sha(owned / 'unchanged-workflow-source-admission.py') == plan['workflow_admission_sha256']
        command('unchanged-workflow-source-admission', [
            sys.executable, str(owned / 'unchanged-workflow-source-admission.py')
        ])
        result['workflow_source_blocks_executed'] = 1

        sys.dont_write_bytecode = True
        sys.path.insert(0, str(root / 'Tools/OriginalEditor'))
        implementation = importlib.import_module('run_signed_consumer_continuation')
        driver = root / 'Tools/OriginalEditor/run_signed_consumer_continuation.py'
        assert sha(driver) == plan['driver_sha256']
        lines = driver.read_text().splitlines(keepends=True)
        a = next(i for i, row in enumerate(lines) if "require(command('control-head'" in row)
        b = next(i for i, row in enumerate(lines) if "actual = {'xcode':" in row)
        source = textwrap.dedent(''.join(lines[a:b]))
        assert source.encode() == (owned / 'unchanged-driver-source-admissions.py').read_bytes()
        assert sha(owned / 'unchanged-driver-source-admissions.py') == plan['driver_admission_sha256']
        ast.parse(source)
        inputs = json.loads((root / 'Tools/OriginalEditor/signed_consumer_continuation_inputs.json').read_bytes())
        namespace = dict(vars(implementation))
        namespace.update(root=root, inputs=inputs, producer=inputs['producer'],
                         current={'control_sha': args.expected_source}, command=command)
        exec(compile(source, str(owned / 'unchanged-driver-source-admissions.py'), 'exec'), namespace)
        result['driver_source_segments_executed'] = 1
        result['driver_receipts_admitted'] = ['metadata-6', 'raw-capture-2', 'framework-role-6']

        focused = json.loads((packet / 'FOCUSED_CONTROLS.json').read_bytes())
        link = focused['framework_role_source_correspondence']
        assert sha(packet / link['prior_receipt_path']) == link['prior_receipt_sha256']
        assert sha(packet / link['correspondence_path']) == link['correspondence_sha256']
        prior = json.loads((packet / link['prior_receipt_path']).read_bytes())
        for key in ['tests_run', 'status', 'started_ids', 'passed_ids', 'expected_ids',
                    'errors', 'failures', 'skipped', 'log_sha256']:
            assert focused[key] == prior[key], key
        assert focused['retained_12_reexecuted'] is False and link['retained_12_reexecuted'] is False
        pointers = {
            'current_metadata_controls_sha256': 'METADATA_CONTROLS.json',
            'current_raw_capture_controls_sha256': 'RAW_CAPTURE_CONTROLS.json',
            'current_framework_role_controls_sha256': 'framework-role-admission/FRAMEWORK_ROLE_CONTROLS.json',
        }
        for key, name in pointers.items():
            assert link[key] == sha(packet / name), (key, name)
        assert focused['current_metadata_controls_sha256'] == sha(packet / 'METADATA_CONTROLS.json')
        active = []
        for name, log_root in [
            ('FOCUSED_CONTROLS.json', packet),
            ('METADATA_CONTROLS.json', packet),
            ('RAW_CAPTURE_CONTROLS.json', packet),
            ('framework-role-admission/FRAMEWORK_ROLE_CONTROLS.json', packet / 'framework-role-admission'),
        ]:
            receipt = json.loads((packet / name).read_bytes())
            for path, expected in receipt['source_sha256'].items():
                assert sha(root / path) == expected, (name, 'source', path)
            for path, expected in receipt['log_sha256'].items():
                assert sha(log_root / path) == expected, (name, 'log', path)
            active.append({'path': name, 'sha256': sha(packet / name),
                           'source_members': len(receipt['source_sha256']),
                           'log_members': len(receipt['log_sha256']),
                           'historical_case_count': receipt['tests_run']})
            if name in ('METADATA_CONTROLS.json', 'RAW_CAPTURE_CONTROLS.json'):
                correspondence = receipt['framework_role_source_correspondence']
                assert sha(packet / correspondence['prior_receipt_path']) == correspondence['prior_receipt_sha256']
                assert sha(packet / correspondence['source_correspondence_path']) == correspondence['source_correspondence_sha256']
                assert correspondence['current_new_role_controls_sha256'] == sha(packet / 'framework-role-admission/FRAMEWORK_ROLE_CONTROLS.json')
        result['active_receipts'] = active
        result['packet_indexes'] = []
        for directory in [packet / 'framework-role-admission', owned]:
            index_path = directory / 'PACKET_INDEX.json'
            index = json.loads(index_path.read_bytes())
            rows = index['files']
            names = [row['path'] for row in rows]
            assert len(names) == len(set(names))
            actual = sorted(p.relative_to(directory).as_posix() for p in directory.rglob('*')
                            if p.is_file() and p != index_path)
            assert sorted(names) == actual, str(directory)
            total = 0
            for row in rows:
                path = directory / row['path']
                assert not path.is_symlink() and path.stat().st_size == row['bytes']
                assert sha(path) == row['sha256'], str(path)
                total += row['bytes']
            assert total == index['total_bytes']
            result['packet_indexes'].append({
                'path': str(index_path.relative_to(root)), 'sha256': sha(index_path),
                'indexed_files': len(rows), 'files_including_index': len(rows) + 1,
                'indexed_bytes': total,
            })
        correspondence = json.loads((packet / 'framework-role-admission/SOURCE_CORRESPONDENCE.json').read_bytes())
        changed_driver = correspondence['changed_driver']
        assert sha(root / changed_driver['path']) == changed_driver['current_sha256']
        for path, expected in correspondence['unchanged_exact_files'].items():
            assert sha(root / path) == expected
        assert correspondence['current_new_role_controls_sha256'] == sha(packet / 'framework-role-admission/FRAMEWORK_ROLE_CONTROLS.json')
        assert not command('final-complete-source-status', ['git', 'status', '--porcelain', '--untracked-files=all'])
        result['status'] = 'PASS'
    except BaseException as error:
        result['error_type'] = type(error).__name__
        result['error'] = str(error)
        raise
    finally:
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
