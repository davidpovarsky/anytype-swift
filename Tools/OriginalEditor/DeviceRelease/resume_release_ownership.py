#!/usr/bin/env python3
"""Resume only an observed Release ownership timeout, retaining the build owner.

No compiler, consumer launch, source mutation or prior evidence rewrite occurs.
The original producer UUID remains the compiler identity. A distinct continuation
UUID and controller hash identify the actual ownership check and packaging.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_contract import (SOURCE, CONFIGURATION, SIMULATOR_PASS, DEVICE_PASS,
    admit_original_owner, controller_observation, digest, require, timestamp,
    validate_execution, verify_original_helpers, write)
from release_process import GROUPS, group_alive

TIMEOUT_COMMAND = 'shared-provider-definitions-ProtobufMessages'
RESUME_PHASE = 'ACTUAL_RELEASE_SHARED_IMPLEMENTATION_OWNERSHIP'


def admit_terminal(receipt):
    require(receipt.get('status') == 'FAIL' and receipt.get('phase') == RESUME_PHASE
            and receipt.get('error_type') == 'TimeoutExpired'
            and receipt.get('owned_command_groups_drained') is True
            and not receipt.get('final_observation_error') and not receipt.get('cleanup_error')
            and receipt.get('source_sha') == SOURCE
            and receipt.get('configuration') == CONFIGURATION
            and receipt.get('original_framework_build') == 'PASS'
            and receipt.get('external_consumer_build') == 'PASS'
            and receipt.get('owned_simulator_cleanup', {}).get('status') in {'PASS', 'NOT_REQUIRED'},
            'Only a drained ownership timeout after actual Release prerequisites may resume')
    surface = receipt.get('actual_public_surface', {})
    require(surface.get('status') == 'ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED'
            and surface.get('reviewed_host_and_spi_requirements_observed') == 89
            and surface.get('debug_qualification_requirements_absent') == 22
            and surface.get('public_host_scope_verified') is True
            and surface.get('qualification_spi_scope_verified') is True
            and not surface.get('debug_qualification_symbols_observed'),
            'Original Release API/SPI acceptance is incomplete')
    if receipt.get('platform') == 'iphonesimulator':
        observations = receipt.get('verified_runtime_observations', [])
        require(len(observations) == 2 and {r.get('language') for r in observations} == {'en', 'he'}
                and all(r.get('status') == 'ACTUAL_IMPORT_LINK_RESOURCE_RUNTIME_PASS' for r in observations),
                'Original Release EN/HE executions are incomplete')
    else:
        require(receipt.get('platform') == 'iphoneos', 'Unknown Release platform')


def verify_previous_commands(evidence, work):
    rows = {}
    for path in sorted(evidence.glob('*.command.json')):
        row = json.loads(path.read_text())
        name = path.name.removesuffix('.command.json')
        for channel in ['stdout', 'stderr']:
            require(digest(evidence / (name + '.' + channel + '.log')) == row[channel + '_sha256'],
                    'Prior terminal output differs: ' + name)
        require(row.get('owned_group_drained') is True
                and row.get('unexpected_children_after_parent_exit') is False,
                'Prior command group did not terminate cleanly: ' + name)
        if name == TIMEOUT_COMMAND:
            binary = work / 'distribution/Frameworks/ProtobufMessages.framework/ProtobufMessages'
            require(row.get('timed_out') is True and row.get('timeout_seconds') == 60
                    and row.get('returncode') in {-15, -9}
                    and row.get('command') == ['xcrun', 'nm', '-gjU', str(binary)],
                    'The retained failure is not the reviewed exact symbol timeout')
        else:
            require(row.get('returncode') == 0 and row.get('timed_out') is False,
                    'Another original prerequisite failed: ' + name)
        rows[name] = digest(path)
    require(TIMEOUT_COMMAND in rows and {'framework-build', 'external-consumer-build'} <= set(rows),
            'Original actual command receipts are missing')
    return rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ['root', 'previous-evidence', 'previous-work', 'evidence', 'control-root']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--previous-execution-sha256', required=True)
    args = parser.parse_args()
    for name, path in vars(args).items():
        if isinstance(path, Path):
            require(path.is_absolute() and path.resolve() == path, 'Aliased continuation input: ' + name)
    root, old, work, evidence = args.root, args.previous_evidence, args.previous_work, args.evidence
    require(all(p.is_relative_to(root / 'build') for p in [old, work, evidence])
            and not evidence.exists() and not evidence.is_relative_to(old)
            and not old.is_relative_to(evidence) and not evidence.is_relative_to(work),
            'Continuation must own a fresh evidence directory outside original inputs')
    sys.path.insert(0, str(root / 'Tools/OriginalEditor'))
    sys.path.insert(0, str(root / 'Tools/OriginalEditor/SharedRuntime'))
    from product_inventory import inventory
    from framework_profile import source_observation
    from framework_install_names import verify_consumer_install_name
    from import_abi_input import verify as verify_abi
    from release_ownership import verify_ownership
    from run_release import package
    original_receipt_path = old / 'execution.json'
    require(digest(original_receipt_path) == args.previous_execution_sha256,
            'Pinned original terminal receipt changed')
    previous = json.loads(original_receipt_path.read_text())
    admit_terminal(previous)
    descriptor = old / 'release-execution.json'
    execution = json.loads(descriptor.read_text())
    original_control = controller_observation(Path(execution['control_root']))
    validate_execution(execution, root, original_control, previous['platform'])
    require(previous['execution_identity']['local_execution_sha256'] == digest(descriptor)
            and previous['run_id'] == execution['execution_id']
            and previous['control_sha'] == execution['control_sha']
            and execution['evidence_root'] == str(old) and execution['work_root'] == str(work),
            'Original compiler identity or paths differ')
    control = controller_observation(args.control_root)
    verify_original_helpers(root, args.control_root)
    argv = execution['controller_argv'][1:]
    require(len(argv) % 2 == 0 and len(set(argv[::2])) == len(argv[::2]),
            'Ambiguous original controller arguments')
    original_args = dict(zip(argv[::2], argv[1::2]))
    before, installation, environment = admit_original_owner(
        root, Path(original_args['--abi-execution']), original_args['--abi-execution-sha256'],
        Path(original_args['--abi-source-before']), Path(original_args['--abi-receipt']),
        original_args['--abi-sha256'], Path(original_args['--simulator-qualification']),
        original_args['--simulator-qualification-sha256'], SOURCE)
    os.environ.update({k: environment[k] for k in ['OTZARIA_LOCAL_EXECUTION', 'OTZARIA_LOCAL_EXECUTION_SHA256']})
    require(json.loads((old / 'source-before.json').read_text()) == before
            and json.loads((old / 'source-after.json').read_text()) == before,
            'Original Release source changed')
    context = json.loads((old / 'current-build-source-context.json').read_text())
    require(context['run_id'] == previous['run_id'] and context['head_sha'] == SOURCE,
            'Original compiler source context differs')
    exported = work / 'distribution'
    expected = json.loads((old / 'framework-distribution.json').read_text())['files']
    require(inventory(exported) == expected, 'Retained Release distribution bytes differ')
    require(not os.path.lexists(work / 'producer-derived'), 'Producer resource fallback was recreated')
    consumer = work / ('consumer-derived/Build/Products/Release-' + previous['platform'] + '/OriginalEditorConsumer.app')
    require(verify_consumer_install_name(consumer) == previous['actual_consumer_install_names'],
            'Retained external consumer load commands differ')
    require(inventory(work / 'external-consumer') == json.loads((old / 'consumer-source-inputs.json').read_text()),
            'Original external consumer source differs')
    command_receipts = verify_previous_commands(old, work)
    old_snapshot = inventory(old)
    consumer_snapshot = inventory(consumer)
    alternates = {str(p): digest(p) for p in sorted((work / 'producer-derived-preserved/SourcePackages/checkouts').glob('*/.git/objects/info/alternates'))}
    continuation = {'schema': 'otzaria.original-editor.release-ownership-continuation/1',
        'execution_id': 'local-' + str(uuid.uuid4()), 'started_at': timestamp(),
        'source_sha': SOURCE, 'build_run_id': previous['run_id'], 'build_control_sha': previous['control_sha'],
        'controller': control, 'previous_evidence': str(old),
        'previous_execution_sha256': digest(original_receipt_path),
        'previous_descriptor_sha256': digest(descriptor), 'original_terminal_status': 'FAIL',
        'reused_command_receipts': command_receipts, 'compiled_sources_or_products_changed': False,
        'compiler_executions': 0, 'consumer_runtime_executions': 0,
        'ownership_policy': 'UNCHANGED_COMPLETE_SYMBOL_SETS_AND_SOURCE_CLOSURES'}
    evidence.mkdir()
    write(evidence / 'continuation.json', continuation)
    write(evidence / 'retained-evidence-before.json', old_snapshot)
    for name in ['framework-distribution.json', 'original-hanlin-snapshot.json', 'source-before.json', 'source-after.json']:
        shutil.copyfile(old / name, evidence / name)
    receipt = copy.deepcopy(previous)
    receipt['resumed_from'] = continuation
    receipt.pop('error', None)
    receipt.pop('error_type', None)
    receipt['status'] = 'FAIL'
    outcome = {'status': 'FAIL', 'started_at': timestamp(), 'build_run_id': previous['run_id'],
               'continuation_id': continuation['execution_id']}
    try:
        owner = verify_ownership(root, evidence, work, previous, context, before, previous['platform'])
        receipt['shared_runtime_ownership'] = owner
        require(source_observation(root) == before, 'Original source changed during continuation')
        after_abi = verify_abi(root, Path(original_args['--abi-receipt']), original_args['--abi-sha256'], before)
        require(after_abi == installation, 'Original qualified ABI changed')
        write(evidence / 'import-abi-after.json', after_abi)
        require(inventory(exported) == expected and inventory(consumer) == consumer_snapshot
                and inventory(old) == old_snapshot,
                'Original products, consumer or prior evidence changed during continuation')
        require(all(digest(Path(p)) == h for p, h in alternates.items())
                and not os.path.lexists(work / 'producer-derived'),
                'Original Git alternates or resource quarantine changed')
        require(controller_observation(args.control_root) == control
                and all(not group_alive(g) for g in GROUPS), 'Continuation controller/process ownership differs')
        receipt.update(status=SIMULATOR_PASS if previous['platform'] == 'iphonesimulator' else DEVICE_PASS,
            phase='COMPLETE', distribution=str(exported), same_toolchain_only=True,
            original_43_component_tests='NOT_RERUN', native_editor_ui_tests=0,
            editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN', device_runtime='NOT_RUN',
            owned_command_groups_drained=True, finished_at=timestamp())
        write(evidence / 'execution.json', receipt)
        package_args = argparse.Namespace(root=root, evidence=evidence, platform=previous['platform'],
            abi_receipt=Path(original_args['--abi-receipt']), abi_source_before=Path(original_args['--abi-source-before']),
            abi_execution=Path(original_args['--abi-execution']),
            signing_team_id=original_args.get('--signing-team-id'))
        package(package_args, receipt, descriptor)
        require(inventory(old) == old_snapshot and inventory(consumer) == consumer_snapshot,
                'Historical evidence or original consumer changed during packaging')
        require({k:v for k,v in inventory(exported).items() if k != 'QUALIFICATION.json'} == expected,
                'Packaging changed a pre-existing distribution member')
        outcome.update(status='PASS_RELEASE_OWNERSHIP_AND_EXACT_PACKAGING',
            qualification_sha256=digest(exported / 'QUALIFICATION.json'),
            production_input_sha256=digest(evidence / 'production-input.json'),
            packaging_sha256=digest(evidence / 'PACKAGING.json'),
            preserved_historical_evidence=True, preserved_consumer=True,
            preserved_original_distribution=True, owned_groups_drained=True)
    except BaseException as error:
        outcome.update(error_type=type(error).__name__, error=str(error))
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        write(evidence / 'execution.json', receipt)
        # Packaging is part of acceptance: an incomplete archive cannot leave
        # a successful qualification for a later Host to consume.
        if (exported / 'QUALIFICATION.json').exists():
            write(exported / 'QUALIFICATION.json', receipt)
        raise
    finally:
        outcome['finished_at'] = timestamp()
        write(evidence / 'RESULT.json', outcome)
        print(json.dumps(outcome, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
