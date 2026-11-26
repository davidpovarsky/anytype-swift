#!/usr/bin/env python3
"""Resume the uninvoked App15 T5 core/R08 tests on their original native account.

The original failed run, producer products, fixture, credentials and preparation
receipt remain immutable. This controller builds nothing and never prepares,
reinstalls, copies, renews, or substitutes an account. Its result is Debug-only.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import combined_host_acceptance_app15 as controller

shared = controller.shared
require, raw, decode = shared.require, shared.raw, shared.decode
write, write_bytes, digest, sha = shared.write, shared.write_bytes, shared.digest, shared.sha

PREVIOUS = Path('/Users/m1/development/anytype-root-active-20261125/app15-t5-pending-ipad-he-light-01')
SOURCE = '379ca3568f247d2fc218ed63df24796d461713c0'
ADMISSION_SHA = '29bb770a661d4843f2a1105749969def68aafa86204619d0121d8377f7afb3fa'
CHECKPOINT_SHA = '1a1f93f197e901179d1cd519018bb4e3abfed330f68a2a8813882ee6d9b33d99'
UDID = 'AE150CEF-CF35-4029-87F8-0CEF8E8E6F87'
IDENTITY = {
    'fixture_sha256': 'bb6f01e792c81e588368f4916ca93835b8a5e498ec0af57e378b27b5d028755d',
    'credentials_sha256': 'ecdb398e3cd7b694a87d9ac2f562a9e2722ed76d03200b26041512691c8b753f',
    'native_mutations_sha256': '137f1b9fdee9fcdb368befba57ce6a26422712d0f0ead1373042592749967743',
}


def admit_previous():
    previous_evidence = PREVIOUS / 'evidence'
    require(digest(previous_evidence / 'admission.json') == ADMISSION_SHA,
            'Original admission changed')
    require(digest(previous_evidence / 'checkpoint-t5-native-ui.json') == CHECKPOINT_SHA,
            'Original failed checkpoint changed')
    admission = decode(raw(previous_evidence / 'admission.json'))
    checkpoint = decode(raw(previous_evidence / 'checkpoint-t5-native-ui.json'))
    require(admission['sourceCommit'] == checkpoint['binding']['sourceSHA'] == SOURCE,
            'Original compiled App/UI source differs')
    lane = previous_evidence / 'lanes/t5-native-ui'
    failed = decode(raw(lane / 'core-ui/result.json'))
    require(failed['status'] == 'FAIL' and failed['testInvoked'] is False
            and failed['errors'] == []
            and failed['firstFailure']['message'] ==
            'Enumeration must contain every exact original selected method and no extra method',
            'Only the original never-invoked enumeration failure may resume')
    execution = decode(raw(lane / 'execution.json'))
    require(execution['ownedSimulator'] == {'deleted': False,
            'status': 'SHUTDOWN_ACCOUNT_RETAINED', 'udid': UDID},
            'Original retained simulator identity differs')
    require(decode(raw(lane / 'preparation/result.json'))['status'] == 'PASS',
            'Original real native preparation did not pass')
    return admission, checkpoint['binding'], lane


def check_original_identity(helpers, container):
    identity, _ = helpers['run_t5_native_ui'].native_ui_identity(container)
    require(identity == IDENTITY, 'Original live fixture, credentials or mutation receipt changed')
    return identity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--control-manifest', type=Path, required=True)
    parser.add_argument('--control-manifest-sha256', required=True)
    parser.add_argument('--admission-only', action='store_true')
    args = parser.parse_args()
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64',
            'Actual Apple Silicon Mac required')
    require(digest(args.control_manifest) == args.control_manifest_sha256,
            'Exact reviewed continuation controls required')
    control_manifest = decode(raw(args.control_manifest))
    require(control_manifest['schema'] == 'pinkha-app15-t5-retained-continuation-controls-v1'
            and len(control_manifest['controlSourceCommit']) == 40,
            'Exact original Git source of continuation controls required')
    control_root = Path(__file__).resolve().parent
    for name, expected in control_manifest['files'].items():
        require(Path(name).name == name and digest(control_root / name) == expected,
                'Continuation control changed: ' + name)
    require({'resume_app15_t5_native_ui.py', 'combined_host_acceptance_app15.py',
             'combined_heart_semantics_current.py', 'combined_host_helper_pins_gateway.json'}
            <= set(control_manifest['files']), 'Incomplete continuation control closure')
    admission, binding, original_lane = admit_previous()
    for name, expected in admission['controlFiles'].items():
        if name != 'combined_host_acceptance_app15.py':
            require(control_manifest['files'].get(name) == expected,
                    'Unchanged original non-UI controller closure required: ' + name)
    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent
            and not args.root.exists(), 'Fresh separate private continuation root required')
    args.root.mkdir(mode=0o700)
    evidence_root = args.root / 'evidence'
    evidence_root.mkdir(mode=0o700)
    commands = shared.Commands(args.root / 'commands', args.root)
    result = {'schema': 'pinkha-app15-t5-retained-continuation-v1', 'status': 'FAIL',
        'startedAt': time.time(), 'sourceCommit': SOURCE,
        'controlSourceCommit': control_manifest['controlSourceCommit'],
        'controlManifestSHA256': args.control_manifest_sha256,
        'controllerSHA256': digest(control_root / 'combined_host_acceptance_app15.py'),
        'wrapperSHA256': digest(Path(__file__)), 'originalRoot': str(PREVIOUS),
        'originalAdmissionSHA256': ADMISSION_SHA, 'originalCheckpointSHA256': CHECKPOINT_SHA,
        'fixtureBinding': binding, 'simulatorUDID': UDID, 'appBuilds': 0, 'uiBuilds': 0,
        'nativeBuilds': 0, 'newAccounts': 0, 'preparationInvocations': 0,
        'pendingNineInvocations': 0, 'releaseAccepted': False, 'fullFAcceptance': False,
        'fullT5Acceptance': False, 'newFocusSourceAccepted': False,
        'visualReview': 'PENDING', 'voiceOver': 'NOT_RUN', 'physicalDevice': 'NOT_RUN',
        'dynamicTypeScope': 'fixed-large-only', 'errors': []}
    built = {}
    consumer = None
    booted = False
    lease_file = None
    lane = evidence_root / 'lanes/t5-native-ui-continuation'
    lane.mkdir(parents=True, mode=0o700)
    try:
        write_bytes(evidence_root / 'original-admission.json', raw(PREVIOUS / 'evidence/admission.json'))
        write_bytes(evidence_root / 'control-manifest.json', raw(args.control_manifest))
        result['sourceAdmission'], built, app = shared.admit_and_clone_products(
            admission, args.root, evidence_root, commands)
        result['originalHelpers'] = controller.freeze_helpers(
            Path(admission['sourceRoot']), SOURCE, args.root / 'helpers',
            control_root / 'combined_host_helper_pins_gateway.json')
        helpers = controller.load_helpers(args.root / 'helpers')
        original = helpers['run_t5_native_ui']
        t5 = helpers['t5_native_ui_evidence']
        mutations = helpers['t5_native_ui_mutations']
        r08 = helpers['t5_native_ui_r08']
        fixture_raw = raw(original_lane / 'private/pinkha-t5-native-ui-fixture.json', 65536)
        fixture = decode(fixture_raw)
        require(sha(fixture_raw) == IDENTITY['fixture_sha256'], 'Original fixture pin changed')
        t5.validate_standalone_fixture(fixture, source=SOURCE, run_id=binding['runID'],
            token=fixture['token'], runtime=shared.VERSION)
        result['nativeMutations'] = mutations.validate(decode(raw(
            original_lane / 'private/pinkha-t5-native-ui-mutations.json', 65536)), fixture)
        selectors = [controller.UI + '/' + method for method in t5.METHODS.values()]
        result['originalEnumerationRequalified'] = controller.exact_enumeration(
            decode(raw(original_lane / 'core-ui/enumeration.json')), selectors)
        simulator_home = Path.home() / 'Library/Developer/CoreSimulator/Devices' / UDID
        candidates = []
        for candidate in (simulator_home / 'data/Containers/Data/Application').iterdir():
            path = candidate / original.UI_FIXTURE
            if path.is_file() and digest(path) == IDENTITY['fixture_sha256']:
                candidates.append(candidate)
        require(len(candidates) == 1, 'One original simulator account container required')
        result['fixtureIdentityBefore'] = check_original_identity(helpers, candidates[0])
        inventory_log, _ = commands.run(['xcrun', 'simctl', 'list', '--json'], 'retained-device-inventory', 60)
        inventory = decode(raw(inventory_log))
        devices = [d for d in inventory['devices'][shared.RUNTIME] if d.get('udid') == UDID]
        runtimes = [r for r in inventory['runtimes'] if r.get('identifier') == shared.RUNTIME]
        require(len(devices) == len(runtimes) == 1 and devices[0]['state'] == 'Shutdown'
                and devices[0]['isAvailable'] is True and runtimes[0]['isAvailable'] is True
                and devices[0]['deviceTypeIdentifier'] == admission['deviceType']
                and runtimes[0]['version'] == shared.OS_VERSION
                and runtimes[0]['buildversion'] == shared.OS_BUILD,
                'Exact original shutdown simulator and runtime required')
        result['actualDevice'] = devices[0]
        result['accountLease'] = {'status': 'NO_EXPIRY_FIELD_IN_ORIGINAL_T5_ACCOUNT_CONTRACT',
            'validation': 'Original fixture, credentials, mutation and native account hashes retained',
            'renewed': False, 'bypassed': False}
        write(evidence_root / 'preflight.json', result)
        if args.admission_only:
            result['status'] = 'PASS_ORIGINAL_ACCOUNT_PRODUCTS_AND_ENUMERATION_ONLY'
        else:
            lease_path = PREVIOUS.parent / ('.pinkha-t5-continuation-' + UDID + '.lock')
            lease_file = lease_path.open('a')
            fcntl.flock(lease_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            consumer = controller.Consumer(args.root, admission, commands, built, app, helpers, binding)
            consumer.devices = [UDID]
            consumer.current = UDID
            commands.run(['xcrun', 'simctl', 'boot', UDID], 'retained-t5-boot', 60)
            booted = True
            commands.run(['xcrun', 'simctl', 'bootstatus', UDID, '-b'], 'retained-t5-boot-ready', 180)
            result['installedOriginalCode'] = consumer.installed(UDID, 'retained-t5-original')
            container = consumer.container(UDID, 'data', 'retained-t5-original-account')
            check_original_identity(helpers, container)
            consumer.appearance(UDID, 'retained-core', 'light', 'large')
            ui_environment = {'PINKHA_NATIVE_UI_DISPOSABLE': '1',
                'PINKHA_T5_NATIVE_UI_FIXTURE_JSON': fixture_raw.decode(),
                'PINKHA_T5_UI_TOKEN': fixture['token'], 'PINKHA_T5_UI_APP_SHA': SOURCE,
                'PINKHA_T5_UI_RUN_ID': binding['runID'], 'PINKHA_UI27_APP_LANGUAGE': 'en',
                'PINKHA_UI27_SELECTION_SCOPE': 'WAVE15_ACCEPTANCE'}
            result['coreUI'], path = consumer.stage(lane, 'core-ui', UDID,
                list(t5.METHODS.values()), ui_environment, target=controller.UI)
            observed, _ = t5.read_ui_receipts(path / 'private-attachments', fixture)
            result['originalCoreReceipts'] = observed
            check_original_identity(helpers, consumer.container(UDID, 'data', 'retained-core-after'))
            note = observed['receipts']['note-lifecycle']['observations'][-1]
            retained = {key: note[key] for key in ('objectID', 'blockID', 'actualText')}
            used = controller.native_ui_prior_processes(fixture, observed)
            result['coreProcessIDs'] = sorted(used)
            result['r08'] = {}
            for appearance in r08.APPEARANCES:
                name = 'r08-he-' + appearance
                consumer.appearance(UDID, 'retained-' + name, appearance, 'large')
                environment = dict(ui_environment, PINKHA_UI27_APP_LANGUAGE='he',
                    PINKHA_T5_UI_PRESENTATION_MODE='R08', PINKHA_T5_UI_APPEARANCE=appearance,
                    PINKHA_T5_R08_RETAINED_NOTE_JSON=json.dumps(retained))
                selected, stage = consumer.stage(lane, name, UDID, [r08.METHOD],
                                                environment, target=controller.UI)
                report, _ = r08.read_receipt(stage / 'private-attachments', appearance, fixture, retained, used)
                used.add(report['process_id'])
                check_original_identity(helpers, consumer.container(UDID, 'data', 'retained-' + name + '-after'))
                for key, expected in (('appearance', appearance), ('content_size', 'large')):
                    output, _ = commands.run(['xcrun', 'simctl', 'ui', UDID, key],
                        'retained-' + name + '-after-' + key.replace('_', '-'), 30)
                    r08.actual_setting(raw(output).decode(), expected, key)
                result['r08'][appearance] = {'selected': selected, 'originalObservations': report}
            result['status'] = 'PASS_RETAINED_T5_CORE2_R08_HE_LIGHT_DARK_VISUAL_REVIEW_PENDING'
    except BaseException as exc:
        result['firstFailure'] = shared.error(exc)
    finally:
        if consumer is not None and booted:
            try:
                result['privateEvidence'] = consumer.preserve(UDID, lane, 'retained-t5')
                result['fixtureIdentityAfter'] = check_original_identity(
                    consumer.helpers, consumer.container(UDID, 'data', 'retained-t5-final-identity'))
            except BaseException as exc:
                result['errors'].append({'phase': 'preserve', **shared.error(exc)})
            try:
                commands.run(['xcrun', 'simctl', 'shutdown', UDID], 'retained-t5-shutdown', 60, capacity=False)
                result['ownedSimulator'] = {'udid': UDID, 'deleted': False,
                                          'status': 'SHUTDOWN_ACCOUNT_RETAINED'}
            except BaseException as exc:
                result['errors'].append({'phase': 'shutdown', **shared.error(exc)})
        try:
            result['finalProducts'] = {name: shared.product_integrity(value) for name, value in built.items()}
            result['ownedProcessGroups'] = controller.observe_owned_groups(commands)
            require(result['ownedProcessGroups']['status'] == 'PASS',
                    'Every owned command process group must have a positive absence proof')
            admit_previous()
        except BaseException as exc:
            result['errors'].append({'phase': 'final-invariants', **shared.error(exc)})
        if lease_file is not None:
            lease_file.close()
        if result['errors']:
            result['status'] = 'FAIL'
        result['finishedAt'] = time.time()
        result['rawXCResultRetainedPrivately'] = True
        result['accountDataUploaded'] = False
        write(evidence_root / 'execution.json', result)
    print(json.dumps({'status': result['status'], 'receipt': str(evidence_root / 'execution.json'),
        'firstFailure': result.get('firstFailure'), 'errors': result['errors']}, sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
