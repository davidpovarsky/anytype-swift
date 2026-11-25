#!/usr/bin/env python3
"""Finish the actual Device292 Postbuild04 ownership gate without recompiling.

The failed postbuild and original compiler receipts remain immutable. Only an
exact admitted compiler-path move is specialized; complete original symbol,
dependency source, ABI, consumer and packaging checks remain mandatory.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_contract import (CONFIGURATION, DEVICE_PASS, admit_original_owner,
    controller_observation, digest, identity, require, timestamp,
    validate_execution, verify_original_helpers, write)
from release_process import GROUPS, group_alive

SOURCE = '8ae85a6490c4fb763fcd01d5f93345f7e071db92'
COMPILER_CONTROL = 'bd41da08b26aac66bbbee96ab753ebab624f2f2c'
POSTBUILD_CONTROL = 'fd66bc94e0ff6f0f4964fc4459b20a17bbda3c8c'
TERMINAL_SHA256 = '8648f46d56ff38d17729eb16fc4edf0d4f147a463113ff38b2dcdcf7ced70ce7'
CONTINUATION_SHA256 = '74f4605fb526f167a0f96abbbeab4f6b28de54b2d08352e2398b23b841e2f7a2'
DESCRIPTOR_SHA256 = 'bdf76198c991e74fb59623ad8448ee401269e07f64364bc89230740d53dc1865'
EVIDENCE_INVENTORY_SHA256 = '5547740e09450d2ef1a3330121b0c3e7956cafa5a8acebcd8f6c3f6aa216538f'
DRIVER_SHA256 = 'd36ec2c8e6bf949fdcd3d468632d052f8eef0a8103734dd3cb5496cbd9822eef'
PHASE = 'ACTUAL_RELEASE_SHARED_IMPLEMENTATION_OWNERSHIP'
FAILURE = 'Unreviewed producer quarantine mapping'


def admit_terminal(receipt):
    require(receipt.get('status') == 'FAIL' and receipt.get('phase') == PHASE
            and receipt.get('error_type') == 'ValueError' and receipt.get('error') == FAILURE
            and receipt.get('source_sha') == SOURCE and receipt.get('control_sha') == COMPILER_CONTROL
            and receipt.get('platform') == 'iphoneos' and receipt.get('configuration') == CONFIGURATION
            and receipt.get('owned_command_groups_drained') is True
            and not receipt.get('final_observation_error') and not receipt.get('cleanup_error')
            and receipt.get('original_framework_build') == 'PASS'
            and receipt.get('external_consumer_build') == 'PASS'
            and receipt.get('native_editor_ui_tests') == 0
            and receipt.get('device_runtime') == 'NOT_RUN'
            and receipt.get('original_app_runtime') == 'NOT_RUN'
            and receipt.get('owned_simulator_cleanup') == {'status': 'NO_OWNED_SIMULATOR_CREATED'},
            'Only the actual drained Device292 Postbuild04 mapping failure may resume')
    surface = receipt.get('actual_public_surface', {})
    require(surface.get('status') == 'ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED'
            and surface.get('reviewed_host_and_spi_requirements_observed') == 270
            and surface.get('debug_qualification_requirements_absent') == 22
            and surface.get('public_host_scope_verified') is True
            and surface.get('qualification_spi_scope_verified') is True
            and surface.get('debug_qualification_symbols_observed') == [],
            'Actual Release public API and qualification SPI acceptance is incomplete')


def inventory_digest(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()


def verify_previous_commands(evidence):
    rows = {}
    for path in sorted(evidence.glob('*.command.json')):
        row = json.loads(path.read_text())
        name = path.name.removesuffix('.command.json')
        for channel in ['stdout', 'stderr']:
            require(digest(evidence / (name + '.' + channel + '.log')) == row[channel + '_sha256'],
                    'Retained command output changed: ' + name)
        require(row.get('returncode') == 0 and row.get('timed_out') is False
                and row.get('owned_group_drained') is True
                and row.get('unexpected_children_after_parent_exit') is False,
                'Retained prerequisite did not complete cleanly: ' + name)
        rows[name] = digest(path)
    require(len(rows) == 128
            and {'framework-build', 'external-consumer-build', 'shared-provider-original-loads',
                 'shared-provider-definitions-AnytypeOriginalEditor',
                 'shared-provider-definitions-ProtobufMessages-table',
                 'shared-provider-definitions-ProtobufMessages-exports'} <= set(rows),
            'Actual original compiler, external consumer or complete symbol receipts are missing')
    return rows


def original_arguments(execution):
    raw = execution['controller_argv'][1:]
    require(len(raw) % 2 == 0 and len(set(raw[::2])) == len(raw[::2])
            and all(k.startswith('--') for k in raw[::2]),
            'Ambiguous original compiler arguments')
    values = dict(zip(raw[::2], raw[1::2]))
    required = {'--abi-execution', '--abi-execution-sha256', '--abi-source-before',
                '--abi-receipt', '--abi-sha256', '--simulator-qualification',
                '--simulator-qualification-sha256', '--signing-team-id'}
    require(required <= set(values) and values['--signing-team-id'] == 'NA6HPWARQ2',
            'Original ABI or device signing-team provenance is missing')
    return values


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ['root', 'previous-evidence', 'previous-work', 'evidence', 'control-root']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--previous-execution-sha256', required=True)
    args = parser.parse_args()
    for name, path in vars(args).items():
        if isinstance(path, Path):
            require(path.is_absolute() and '..' not in path.parts and path.resolve() == path,
                    'Aliased or nonabsolute continuation input: ' + name)
    root, old, work, evidence = args.root, args.previous_evidence, args.previous_work, args.evidence
    require(old == root / 'build/Device292-Postbuild04-Evidence'
            and work == root / 'build/Device292-Postbuild04-Work'
            and evidence.is_relative_to(root / 'build') and not evidence.exists()
            and not evidence.is_relative_to(old) and not old.is_relative_to(evidence)
            and not evidence.is_relative_to(work) and not work.is_relative_to(evidence),
            'Continuation must own fresh evidence outside exact original Postbuild04 inputs')
    sys.path[:0] = [str(root / 'Tools/OriginalEditor'),
                   str(root / 'Tools/OriginalEditor/SharedRuntime'), str(root / 'Tools/Hanlin')]
    from product_inventory import inventory
    from framework_profile import source_observation
    from import_abi_input import verify as verify_abi
    from prepare_sdk import verify as verify_hanlin
    from release_install_names import verify_consumer_install_name
    from release_continuation_roots import admit_roots
    from release_ownership import verify_ownership
    from run_release import package, preflight

    terminal = old / 'execution.json'
    require(args.previous_execution_sha256 == digest(terminal) == TERMINAL_SHA256,
            'Actual Postbuild04 terminal bytes changed')
    previous = json.loads(terminal.read_text())
    admit_terminal(previous)
    old_snapshot = inventory(old)
    require(len(old_snapshot) == 429 and inventory_digest(old_snapshot) == EVIDENCE_INVENTORY_SHA256,
            'The frozen complete 429-file Postbuild04 evidence inventory differs')
    chain_path = old / 'continuation.json'
    require(digest(chain_path) == CONTINUATION_SHA256, 'Original postbuild continuation changed')
    chain = json.loads(chain_path.read_text())
    compiler_evidence = Path(chain['previous_evidence'])
    original_derived = Path(chain['previous_work']) / 'producer-derived'
    descriptor = compiler_evidence / 'release-execution.json'
    require(digest(descriptor) == chain['previous_descriptor_sha256'] == DESCRIPTOR_SHA256,
            'Actual original compiler descriptor changed')
    execution = json.loads(descriptor.read_text())
    compiler_control = controller_observation(Path(execution['control_root']))
    validate_execution(execution, root, compiler_control, 'iphoneos')
    require(compiler_control['sha'] == COMPILER_CONTROL
            and previous['execution_identity'] == identity(execution, descriptor)
            and previous['run_id'] == execution['execution_id']
            and chain['build_run_id'] == execution['execution_id']
            and execution['evidence_root'] == str(compiler_evidence)
            and execution['work_root'] == str(original_derived.parent)
            and chain['evidence_root'] == str(old) and chain['work_root'] == str(work),
            'Original compiler or postbuild ownership identity differs')
    postbuild_control = controller_observation(Path(chain['controller']['root']))
    require(postbuild_control == chain['controller'] and postbuild_control['sha'] == POSTBUILD_CONTROL,
            'Frozen Postbuild04 controller changed')
    control = controller_observation(args.control_root)
    require(args.control_root != Path(postbuild_control['root'])
            and digest(args.control_root / 'Tools/OriginalEditor/DeviceRelease/run_release.py') == DRIVER_SHA256,
            'Ownership continuation must retain the reviewed postbuild driver in a separate controller')
    reused = verify_original_helpers(root, args.control_root)
    values = original_arguments(execution)
    before, installation, environment = admit_original_owner(
        root, Path(values['--abi-execution']), values['--abi-execution-sha256'],
        Path(values['--abi-source-before']), Path(values['--abi-receipt']),
        values['--abi-sha256'], Path(values['--simulator-qualification']),
        values['--simulator-qualification-sha256'], SOURCE)
    os.environ.update({k: environment[k] for k in ['OTZARIA_LOCAL_EXECUTION', 'OTZARIA_LOCAL_EXECUTION_SHA256']})
    require(json.loads((old / 'source-before.json').read_text()) == before
            and json.loads((old / 'source-after.json').read_text()) == before,
            'Original source closure changed')
    context = json.loads((old / 'current-build-source-context.json').read_text())
    require(context['head_sha'] == SOURCE and context['run_id'] == previous['run_id']
            and context['execution_identity'] == previous['execution_identity'],
            'Actual compiler source context changed')
    hanlin = verify_hanlin(root / 'Dependencies/Hanlin')
    require(hanlin == json.loads((old / 'original-hanlin-snapshot.json').read_text()),
            'Compiled shared Hanlin source closure changed')
    collection = json.loads((old / 'compiler-symbolgraph-collection.json').read_text())
    exported = work / 'distribution'
    roots = admit_roots(original_derived, exported, collection, context, quarantined=True)
    expected = json.loads((old / 'framework-distribution.json').read_text())['files']
    require(inventory(exported) == expected and 'QUALIFICATION.json' not in expected,
            'Retained original Release distribution differs or was already qualified')
    clang = json.loads((old / 'clang-declaration-export.json').read_text())
    require(len(clang['files']) == 1411 and len(clang['module_maps']) == 21
            and len(clang['header_search_paths']) == 21 and clang['source_sha'] == SOURCE
            and clang['local_execution_sha256'] == DESCRIPTOR_SHA256
            and previous['original_clang_declarations'] == {
                'declaration_file_count': 1411, 'header_root_count': 21, 'module_map_count': 21,
                'manifest_sha256': digest(old / 'clang-declaration-export.json')},
            'Original actual Clang product closure is incomplete')
    consumer = work / 'consumer-derived/Build/Products/Release-iphoneos/OriginalEditorConsumer.app'
    require(consumer.is_dir() and not consumer.is_symlink()
            and verify_consumer_install_name(consumer, 'iphoneos', source_root=root)
            == previous['actual_consumer_install_names'],
            'Actual device external consumer load commands changed')
    require(inventory(work / 'external-consumer')
            == json.loads((old / 'consumer-source-inputs.json').read_text()),
            'Original independently built consumer source changed')
    command_receipts = verify_previous_commands(old)
    consumer_snapshot = inventory(consumer)
    alternates = {str(p): digest(p) for p in sorted(
        (work / 'producer-derived-preserved/SourcePackages/checkouts').glob('*/.git/objects/info/alternates'))}
    require(len(alternates) == 58 and not os.path.lexists(original_derived),
            'Retained original Git closure or compiler quarantine differs')
    continuation = {
        'schema': 'otzaria.original-editor.release-quarantine-ownership-continuation/1',
        'execution_id': 'local-' + str(uuid.uuid4()), 'started_at': timestamp(),
        'source_sha': SOURCE, 'build_run_id': previous['run_id'], 'build_control_sha': COMPILER_CONTROL,
        'controller': control, 'previous_evidence': str(old), 'previous_work': str(work),
        'evidence_root': str(evidence), 'previous_execution_sha256': digest(terminal),
        'previous_continuation_sha256': digest(chain_path), 'previous_descriptor_sha256': digest(descriptor),
        'previous_inventory_sha256': inventory_digest(old_snapshot),
        'original_terminal_status': 'FAIL', 'original_failure': FAILURE,
        'reused_command_receipts': command_receipts, 'compiler_root_continuation': roots,
        'compiler_executions': 0, 'consumer_runtime_executions': 0, 'native_editor_ui_tests': 0,
        'compiled_sources_or_products_changed': False,
        'ownership_policy': 'COMPLETE_ORIGINAL_SYMBOL_AND_SOURCE_CHECKS_WITH_EXACT_ADMITTED_ROOT_MAPPING'}
    evidence.mkdir()
    write(evidence / 'continuation.json', continuation)
    write(evidence / 'retained-evidence-before.json', old_snapshot)
    write(evidence / 'retained-consumer-before.json', consumer_snapshot)
    write(evidence / 'retained-git-alternates-before.json', alternates)
    for name in ['framework-distribution.json', 'original-hanlin-snapshot.json',
                 'source-before.json', 'source-after.json', 'current-build-source-context.json',
                 'compiler-symbolgraph-collection.json', 'clang-declaration-export.json',
                 'actual-public-surface.json', 'producer-build-path-absent.json']:
        shutil.copyfile(old / name, evidence / name)
    receipt = copy.deepcopy(previous)
    receipt['ownership_resumed_from'] = continuation
    for key in ['error', 'error_type', 'finished_at']:
        receipt.pop(key, None)
    receipt.update(status='FAIL', phase=PHASE, reused_original_controls=reused)
    outcome = {'status': 'FAIL', 'started_at': timestamp(), 'build_run_id': previous['run_id'],
               'continuation_id': continuation['execution_id']}
    def interrupt(signum, frame):
        raise InterruptedError('Owned ownership continuation signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        require(preflight(root, evidence, execution, 'iphoneos') == previous['preflight'],
                'Actual toolchain differs from the original compiler')
        owner = verify_ownership(root, evidence, work, previous, context, before,
                                 'iphoneos', original_derived=original_derived)
        receipt['shared_runtime_ownership'] = owner
        require(source_observation(root) == before
                and verify_hanlin(root / 'Dependencies/Hanlin') == hanlin,
                'Original compiled source closure changed during ownership verification')
        after_abi = verify_abi(root, Path(values['--abi-receipt']), values['--abi-sha256'], before)
        require(after_abi == installation, 'Original qualified native ABI changed')
        write(evidence / 'import-abi-after.json', after_abi)
        require(inventory(exported) == expected and inventory(consumer) == consumer_snapshot
                and inventory(old) == old_snapshot,
                'Retained original distribution, consumer or evidence changed')
        require(all(digest(Path(p)) == h for p, h in alternates.items())
                and not os.path.lexists(original_derived), 'Original Git or quarantine changed')
        require(controller_observation(args.control_root) == control
                and controller_observation(Path(postbuild_control['root'])) == postbuild_control
                and all(not group_alive(g) for g in GROUPS),
                'Continuation controller/process ownership differs')
        receipt.update(status=DEVICE_PASS, phase='COMPLETE', distribution=str(exported),
            same_toolchain_only=True, original_43_component_tests='NOT_RERUN',
            native_editor_ui_tests=0, editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN',
            device_runtime='NOT_RUN', original_app_runtime='NOT_RUN',
            owned_command_groups_drained=True, finished_at=timestamp())
        write(evidence / 'execution.json', receipt)
        package_args = argparse.Namespace(root=root, evidence=evidence, platform='iphoneos',
            abi_receipt=Path(values['--abi-receipt']), abi_source_before=Path(values['--abi-source-before']),
            abi_execution=Path(values['--abi-execution']), signing_team_id=values['--signing-team-id'])
        package(package_args, receipt, descriptor)
        require(inventory(old) == old_snapshot and inventory(consumer) == consumer_snapshot
                and all(digest(Path(p)) == h for p, h in alternates.items())
                and not os.path.lexists(original_derived),
                'Historical evidence, consumer or Git changed during packaging')
        require({k:v for k,v in inventory(exported).items() if k != 'QUALIFICATION.json'} == expected,
                'Packaging changed an original distribution member')
        outcome.update(status='PASS_ACTUAL_DEVICE_OWNERSHIP_AND_EXACT_PACKAGING',
            qualification_sha256=digest(exported / 'QUALIFICATION.json'),
            production_input_sha256=digest(evidence / 'production-input.json'),
            packaging_sha256=digest(evidence / 'PACKAGING.json'),
            preserved_historical_evidence=True, preserved_consumer=True,
            preserved_original_distribution=True, preserved_git_alternates=True,
            compiler_executions=0, native_editor_ui_tests=0, device_runtime='NOT_RUN')
    except BaseException as error:
        outcome.update(error_type=type(error).__name__, error=str(error))
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        write(evidence / 'execution.json', receipt)
        if (exported / 'QUALIFICATION.json').exists():
            write(exported / 'QUALIFICATION.json', receipt)
        raise
    finally:
        outcome['owned_command_groups_drained'] = all(not group_alive(g) for g in GROUPS)
        outcome['finished_at'] = timestamp()
        write(evidence / 'RESULT.json', outcome)
        print(json.dumps(outcome, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
