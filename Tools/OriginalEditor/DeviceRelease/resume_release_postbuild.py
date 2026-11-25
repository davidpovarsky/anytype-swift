#!/usr/bin/env python3
"""Finish a source-identical device Release after the exact legacy-seal refusal.

The successful original compiler interval keeps its UUID, source and receipts.
A separate continuation records the actual export, API, link and ownership work.
The complete reviewed original postbuild body executes unchanged.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_contract import (CONFIGURATION, DEVICE_PASS, admit_original_owner,
    controller_observation, digest, require, timestamp, validate_execution,
    verify_original_helpers, write)
from release_process import GROUPS, group_alive

SOURCE = '8ae85a6490c4fb763fcd01d5f93345f7e071db92'
ORIGINAL_CONTROL = 'bd41da08b26aac66bbbee96ab753ebab624f2f2c'
ORIGINAL_DRIVER_SHA256 = '4c15b5e8c8bfb2a32540fd3bb2166bbc3388bc3096dcef693a96bb916eae435b'
FAILURE = 'Unreviewed Release build platform command'
REQUIRED_COMMANDS = {'actual-sdk', 'actual-sdk-path', 'actual-swift', 'actual-xcode',
    'exact-package-resolution', 'framework-build', 'framework-header-0',
    'release-seal-AmplitudeCore', 'release-seal-AmplitudeCore-verify',
    'release-seal-AmplitudeCore-identity'}


def admit_terminal(receipt):
    require(receipt.get('status') == 'FAIL'
            and receipt.get('phase') == 'ORIGINAL_RELEASE_FRAMEWORK_BUILD'
            and receipt.get('error_type') == 'RuntimeError' and receipt.get('error') == FAILURE
            and receipt.get('source_sha') == SOURCE and receipt.get('control_sha') == ORIGINAL_CONTROL
            and receipt.get('platform') == 'iphoneos' and receipt.get('configuration') == CONFIGURATION
            and receipt.get('original_framework_build') == 'PASS'
            and receipt.get('external_consumer_build') == 'NOT_RUN'
            and receipt.get('strict_dependency_resolution') == 'PASS_EXACT_COMMITTED_LOCK_UNCHANGED'
            and receipt.get('owned_command_groups_drained') is True
            and receipt.get('owned_simulator_cleanup', {}).get('status') == 'NO_OWNED_SIMULATOR_CREATED'
            and not receipt.get('final_observation_error') and not receipt.get('cleanup_error'),
            'Only the exact drained original device legacy-seal refusal may continue')


def verify_commands(evidence, root, work):
    rows = {}
    for path in sorted(evidence.glob('*.command.json')):
        row = json.loads(path.read_text())
        label = path.name.removesuffix('.command.json')
        require(row.get('returncode') == 0 and row.get('timed_out') is False
                and row.get('owned_group_drained') is True
                and row.get('unexpected_children_after_parent_exit') is False,
                'Original command did not succeed and drain: ' + label)
        for stream in ['stdout', 'stderr']:
            require(digest(evidence / (label + '.' + stream + '.log')) == row[stream + '_sha256'],
                    'Original command output changed: ' + label)
        rows[label] = digest(path)
    require(set(rows) == REQUIRED_COMMANDS, 'Original executed command membership differs')
    build = json.loads((evidence / 'framework-build.command.json').read_text())
    expected = ['xcodebuild', 'build', '-jobs', '2', '-project', str(root / 'Anytype.xcodeproj'),
        '-scheme', 'AnytypeOriginalEditor', '-configuration', CONFIGURATION,
        '-destination', 'generic/platform=iOS', '-derivedDataPath', str(work / 'producer-derived'),
        '-resultBundlePath', str(evidence / 'framework-build.xcresult'),
        '-onlyUsePackageVersionsFromResolvedFile',
        'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED $(ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS)',
        'ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS=-emit-symbol-graph -emit-symbol-graph-dir $(DERIVED_FILE_DIR)/OriginalEditorSymbolGraphs -symbol-graph-minimum-access-level public -include-spi-symbols',
        'ONLY_ACTIVE_ARCH=YES', 'ARCHS=arm64', 'CODE_SIGNING_ALLOWED=NO',
        'CODE_SIGNING_REQUIRED=NO', 'CODE_SIGN_IDENTITY=', 'PROVISIONING_PROFILE_SPECIFIER=']
    require(build['command'] == expected and build['cwd'] == str(root)
            and build['timeout_seconds'] == 6000, 'Original actual Release compiler flags differ')
    return rows


def original_postbuild(driver_path):
    require(digest(driver_path) == ORIGINAL_DRIVER_SHA256,
            'The complete reviewed original Release driver changed')
    tree = ast.parse(driver_path.read_text(), filename=str(driver_path))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'execute']
    require(len(functions) == 1, 'Ambiguous original execute body')
    body = functions[0].body
    starts = [i for i, n in enumerate(body) if isinstance(n, ast.Assign)
              and ast.unparse(n.targets[0]) == "receipt['actual_source_closure']"]
    require(len(starts) == 1, 'Original postbuild boundary differs')
    imports = [n for n in body[:starts[0]] if isinstance(n, (ast.Import, ast.ImportFrom))]
    selected = ast.Module(body=imports + body[starts[0]:], type_ignores=[])
    return compile(ast.fix_missing_locations(selected), str(driver_path), 'exec'), hashlib.sha256(
        ast.dump(selected, include_attributes=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ['root', 'previous-evidence', 'previous-work', 'evidence', 'work', 'control-root']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--previous-execution-sha256', required=True)
    options = parser.parse_args()
    for name, path in vars(options).items():
        if isinstance(path, Path):
            require(path.is_absolute() and path.resolve() == path,
                    'Continuation requires unaliased absolute paths: ' + name)
    root, old, old_work = options.root, options.previous_evidence, options.previous_work
    evidence, work = options.evidence, options.work
    require(all(p.is_relative_to(root / 'build') for p in [old, old_work, evidence, work])
            and not evidence.exists() and not work.exists()
            and len({str(p) for p in [old, old_work, evidence, work]}) == 4
            and all(not a.is_relative_to(b) for a in [evidence, work] for b in [old, old_work])
            and not evidence.is_relative_to(work) and not work.is_relative_to(evidence),
            'New continuation paths must be fresh and disjoint from retained inputs')
    sys.path[:0] = [str(root / 'Tools/OriginalEditor'), str(root / 'Tools/OriginalEditor/SharedRuntime'),
                   str(root / 'Tools/Hanlin')]
    from product_inventory import inventory
    from framework_profile import source_observation, read_manifest
    from import_abi_input import verify as verify_abi
    from prepare_sdk import verify as verify_hanlin
    receipt_path = old / 'execution.json'
    require(digest(receipt_path) == options.previous_execution_sha256,
            'Pinned original failure receipt changed')
    previous = json.loads(receipt_path.read_text())
    admit_terminal(previous)
    descriptor = old / 'release-execution.json'
    execution = json.loads(descriptor.read_text())
    original_control = controller_observation(Path(execution['control_root']))
    validate_execution(execution, root, original_control, 'iphoneos')
    require(original_control['sha'] == ORIGINAL_CONTROL
            and previous['execution_identity']['local_execution_sha256'] == digest(descriptor)
            and previous['run_id'] == execution['execution_id']
            and execution['evidence_root'] == str(old) and execution['work_root'] == str(old_work),
            'Original compiler identity or paths differ')
    control = controller_observation(options.control_root)
    reused = verify_original_helpers(root, options.control_root)
    driver_path = options.control_root / 'Tools/OriginalEditor/DeviceRelease/run_release.py'
    code, ast_sha = original_postbuild(driver_path)
    command_receipts = verify_commands(old, root, old_work)
    raw_args = execution['controller_argv'][1:]
    require(len(raw_args) % 2 == 0 and len(set(raw_args[::2])) == len(raw_args[::2]),
            'Ambiguous original controller argv')
    values = dict(zip(raw_args[::2], raw_args[1::2]))
    before, installation, environment = admit_original_owner(
        root, Path(values['--abi-execution']), values['--abi-execution-sha256'],
        Path(values['--abi-source-before']), Path(values['--abi-receipt']),
        values['--abi-sha256'], Path(values['--simulator-qualification']),
        values['--simulator-qualification-sha256'], SOURCE)
    os.environ.update({k: environment[k] for k in ['OTZARIA_LOCAL_EXECUTION', 'OTZARIA_LOCAL_EXECUTION_SHA256']})
    require(json.loads((old / 'source-before.json').read_text()) == before
            and json.loads((old / 'source-after.json').read_text()) == before,
            'Original source changed before or after the real Release build')
    context = json.loads((old / 'current-build-source-context.json').read_text())
    require(context['run_id'] == previous['run_id'] and context['head_sha'] == SOURCE
            and context['execution_identity'] == previous['execution_identity'],
            'Original actual compiler context differs')
    hanlin = verify_hanlin(root / 'Dependencies/Hanlin')
    require(hanlin == json.loads((old / 'original-hanlin-snapshot.json').read_text()),
            'Original shared Hanlin source changed')
    derived = old_work / 'producer-derived'
    products = derived / ('Build/Products/' + CONFIGURATION + '-iphoneos')
    require(products.is_dir() and not derived.is_symlink(), 'Original compiled Release products are absent')
    old_evidence = inventory(old)
    old_export = inventory(old_work / 'distribution')
    compiled_products = inventory(products)
    continuation = {'schema': 'otzaria.original-editor.release-postbuild-continuation/1',
        'execution_id': 'local-' + str(uuid.uuid4()), 'started_at': timestamp(),
        'source_sha': SOURCE, 'build_run_id': previous['run_id'], 'build_control_sha': ORIGINAL_CONTROL,
        'controller': control, 'previous_evidence': str(old), 'previous_work': str(old_work),
        'evidence_root': str(evidence), 'work_root': str(work),
        'previous_execution_sha256': digest(receipt_path), 'previous_descriptor_sha256': digest(descriptor),
        'original_terminal_status': 'FAIL', 'original_failure': FAILURE,
        'reused_command_receipts': command_receipts, 'original_postbuild_ast_sha256': ast_sha,
        'compiler_executions': 0, 'native_editor_ui_tests': 0, 'physical_device_tests': 0,
        'compiled_inputs_unchanged': True}
    evidence.mkdir(); work.mkdir()
    write(evidence / 'continuation.json', continuation)
    write(evidence / 'retained-evidence-before.json', old_evidence)
    write(evidence / 'retained-partial-export-before.json', old_export)
    write(evidence / 'retained-compiled-products-before.json', compiled_products)
    for name in ['source-before.json', 'source-after.json', 'current-build-source-context.json',
                 'original-hanlin-snapshot.json', 'framework-build.command.json',
                 'framework-build.stdout.log', 'framework-build.stderr.log']:
        shutil.copyfile(old / name, evidence / name)
    spec = importlib.util.spec_from_file_location('original_release_postbuild_driver', driver_path)
    driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
    original_command = driver.command
    def scheduled_command(argv, *args, **kwargs):
        if argv[:2] == ['xcodebuild', 'build']:
            require('-jobs' not in argv, 'Unexpected duplicate scheduler option')
            argv = [*argv[:2], '-jobs', '2', *argv[2:]]
        return original_command(argv, *args, **kwargs)
    driver.command = scheduled_command
    args = argparse.Namespace(root=root, evidence=evidence, work=work, platform='iphoneos',
        control_root=options.control_root, sdk_source=SOURCE,
        abi_execution=Path(values['--abi-execution']), abi_execution_sha256=values['--abi-execution-sha256'],
        abi_source_before=Path(values['--abi-source-before']), abi_receipt=Path(values['--abi-receipt']),
        abi_sha256=values['--abi-sha256'], simulator_qualification=Path(values['--simulator-qualification']),
        simulator_qualification_sha256=values['--simulator-qualification-sha256'],
        signing_team_id=values.get('--signing-team-id'))
    receipt = copy.deepcopy(previous)
    for key in ['error', 'error_type', 'finished_at']:
        receipt.pop(key, None)
    receipt.update(status='FAIL', resumed_from=continuation,
                   phase='ACTUAL_RELEASE_POSTBUILD_CONTINUATION', reused_original_controls=reused)
    result = {'status': 'FAIL', 'started_at': timestamp(), 'build_run_id': previous['run_id'],
              'continuation_id': continuation['execution_id']}
    try:
        checked = driver.preflight(root, evidence, execution, 'iphoneos')
        require(checked == previous['preflight'], 'Actual Release toolchain changed after compilation')
        scope = dict(driver.__dict__)
        scope.update(args=args, receipt=receipt, execution=execution, descriptor=descriptor, control=control,
            root=root, work=work, evidence=evidence, before=before, installation=installation,
            hanlin=hanlin, profile=read_manifest(), checked=checked, context=context,
            derived=derived, destination='generic/platform=iOS')
        exec(code, scope)
        require(receipt['status'] == DEVICE_PASS and receipt['phase'] == 'COMPLETE',
                'The original device postbuild gates did not complete')
        require(inventory(old) == old_evidence and inventory(old_work / 'distribution') == old_export,
                'Historical failure evidence or partial export changed')
        require(not derived.exists()
                and inventory(work / 'producer-derived-preserved' / 'Build/Products' /
                              (CONFIGURATION + '-iphoneos')) == compiled_products,
                'Original compiled products changed during their retained-path move')
        require(source_observation(root) == before and verify_hanlin(root / 'Dependencies/Hanlin') == hanlin,
                'Actual source closure changed during continuation')
        require(verify_abi(root, args.abi_receipt, args.abi_sha256, before) == installation,
                'Actual native input changed during continuation')
        require(controller_observation(options.control_root) == control
                and all(not group_alive(group) for group in GROUPS),
                'Postbuild controller changed or owned commands remain')
        receipt.update(owned_command_groups_drained=True, finished_at=timestamp())
        write(evidence / 'source-after.json', source_observation(root))
        write(evidence / 'execution.json', receipt)
        driver.package(args, receipt, descriptor)
        require(inventory(old) == old_evidence and inventory(old_work / 'distribution') == old_export,
                'Packaging changed historical evidence or partial export')
        result.update(status='PASS_ACTUAL_DEVICE_POSTBUILD_AND_PACKAGING',
            qualification_sha256=digest(work / 'distribution/QUALIFICATION.json'),
            production_input_sha256=digest(evidence / 'production-input.json'),
            packaging_sha256=digest(evidence / 'PACKAGING.json'),
            original_compiler_interval_preserved=True, original_failure_preserved=True,
            new_compiler_executions=0, new_device_runtime_tests=0)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        write(evidence / 'execution.json', receipt)
        if (work / 'distribution/QUALIFICATION.json').exists():
            write(work / 'distribution/QUALIFICATION.json', receipt)
        raise
    finally:
        result['finished_at'] = timestamp()
        write(evidence / 'RESULT.json', result)
        print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
