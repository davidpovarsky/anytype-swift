"""Fail closed on actual case/configuration evidence before any TestFlight job."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import zipfile

SHA = re.compile(r'[0-9a-f]{64}')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def safe_path(path):
    value = PurePosixPath(path)
    require(bool(path) and not value.is_absolute() and '..' not in value.parts and '\\' not in path,
            'Unsafe evidence path')
    return value.as_posix()


def method_results(value):
    found = {}
    if isinstance(value, dict):
        if value.get('nodeType') == 'Test Case':
            name = value.get('nodeIdentifier')
            require(name and name not in found, 'Unnamed actual test method')
            found[name] = value.get('result')
        for child in value.values():
            for name, result in method_results(child).items():
                require(name not in found, 'Duplicate actual test method')
                found[name] = result
    elif isinstance(value, list):
        for child in value:
            for name, result in method_results(child).items():
                require(name not in found, 'Duplicate actual test method')
                found[name] = result
    return found


def validate_record(required, configuration, record, files, candidate_inputs, reviews):
    require(record.get('status') in ['EXECUTED_PASS', 'REUSED_VERIFIED_PASS'], 'Case is not an actual verified pass')
    require(record.get('case_id') == required['id'] and record.get('configuration_id') == configuration,
            'Case/configuration identity differs')
    criteria = set(record.get('criteria', []))
    require(bool(criteria) and criteria.issubset(set(required['criteria'])), 'Unknown or empty behavior coverage')
    require(record.get('source_sha') and re.fullmatch('[0-9a-f]{40}', record['source_sha']), 'Missing actual source SHA')
    require(record.get('run_id', '').isdigit() and record.get('run_attempt', '').isdigit(), 'Missing actual run attempt')
    require(record.get('ui_command_exit_code') == 0, 'UI command did not succeed')
    identity = record.get('identity', {})
    require(identity.get('kit_checkout_sha') == candidate_inputs['kit_sha']
            and identity.get('kit_lock_sha') == candidate_inputs['kit_sha'], 'Kit checkout/lock mismatch')
    require(identity.get('native_patch_sha256') == candidate_inputs['native_patch_sha256'], 'Native source capability differs')
    require(identity.get('os_version', '').split('.')[0] == '27' and identity.get('os_build'), 'Actual OS27 identity missing')
    require(identity.get('device_family') == configuration.split('-')[0]
            and identity.get('device_model') and identity.get('simulator_udid'), 'Actual device class/model/UDID missing')
    require(identity.get('xcode_version', '').startswith('Xcode 27') and identity.get('architecture') == 'arm64',
            'Actual compatible Xcode/architecture missing')
    require(identity.get('app_language') == configuration.split('-')[1], 'Actual app language differs')
    expected_orientation = 'landscape' if '-landscape-' in configuration else 'portrait'
    if '-compact-' not in configuration:
        require(identity.get('orientation') == expected_orientation, 'Actual orientation differs')
    require(identity.get('appearance') == ('dark' if '-dark-' in configuration else 'light'), 'Actual appearance differs')
    if '-large-' in configuration:
        require(identity.get('accessibility_text_size_observed') is True, 'Actual enlarged Dynamic Type not observed')
    if '-compact-' in configuration:
        require(identity.get('window_mode') == 'compact' and identity.get('window_transition_observed') is True,
                'Actual compact window transition missing')
    require(identity.get('app_launched') is True and identity.get('live_pid', 0) > 0, 'Real live app launch not evidenced')
    embedded, live = identity.get('embedded_runtime_sha256', ''), identity.get('live_runtime_sha256', '')
    require(SHA.fullmatch(embedded) and embedded == live and identity.get('native_marker_present') is True
            and identity.get('live_runtime_loaded') is True, 'Embedded/live runtime proof missing or mismatched')
    require(SHA.fullmatch(identity.get('app_executable_sha256', '')), 'Actual application executable hash missing')
    require(record.get('candidate_input_hashes') == candidate_inputs['hashes'], 'Relevant compiled/test inputs are stale')
    methods = record.get('methods', [])
    require(bool(methods) and len(methods) == len(set(methods)), 'No nonzero unique named methods')
    coverage = record.get('coverage_review', {})
    require(coverage.get('reviewer') and coverage.get('criteria') == record['criteria']
            and coverage.get('methods') == methods, 'Named method-to-behavior source review missing')
    summary = json.loads(files[safe_path(record['summary_path'])])
    actual_devices = [row['device'] for row in summary.get('devicesAndConfigurations', [])]
    require(bool(actual_devices) and all(d.get('osVersion') == identity['os_version']
        and d.get('osBuildNumber') == identity['os_build'] and d.get('deviceId') == identity['simulator_udid']
        and d.get('modelName') == identity['device_model'] and d.get('architecture') == identity['architecture']
        for d in actual_devices), 'Raw xcresult device/OS identity differs from the case receipt')
    tests = method_results(json.loads(files[safe_path(record['tests_path'])]))
    require(summary.get('totalTestCount', 0) > 0, 'Zero-test selection')
    require(summary.get('passedTests', 0) >= len(methods), 'Named pass count not supported by raw xcresult')
    # A failed batch may retain an independently passed method, but the case's own methods cannot fail/skip.
    require(all(tests.get(name) == 'Passed' for name in methods), 'Required actual method is absent, failed or skipped')
    require(record.get('counts') == dict(passed=len(methods), failed=0, skipped=0), 'Required case counts differ')
    shots = record.get('screenshots', [])
    require(bool(shots), 'Per-case screenshots missing')
    for shot in shots:
        data = files[safe_path(shot['path'])]
        require(data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24, 'Screenshot is not an actual PNG')
        require(digest(data) == shot.get('sha256'), 'Screenshot content hash differs')
        width, height = struct.unpack('>II', data[16:24])
        require(min(width, height) >= 640, 'Full-resolution screenshot evidence required')
        if required['visual']:
            matches = [r for r in reviews if r.get('case_id') == required['id']
                       and r.get('configuration_id') == configuration and r.get('run_id') == record['run_id']
                       and r.get('screenshot_sha256') == shot['sha256']]
            require(any(r.get('verdict') == 'PASS' and r.get('reviewer') and r.get('reviewer_thread_id')
                        and set(r.get('criteria', [])) == criteria for r in matches),
                    'Actual screenshot visual review missing, stale or failed')
    return dict(case_id=required['id'], configuration_id=configuration, methods=methods,
                source_sha=record['source_sha'], run_id=record['run_id'], status=record['status'], criteria=record['criteria'])


def require_complete_case(required, records):
    covered = {criterion for record in records for criterion in record['criteria']}
    require(covered == set(required['criteria']), 'Required behavior coverage is incomplete: ' +
            ', '.join(sorted(set(required['criteria']) - covered)))


def configuration_requirements(case, configuration):
    required = dict(case)
    required['criteria'] = case.get('criteria_by_configuration', {}).get(configuration, case['criteria'])
    require(bool(required['criteria']), 'A required configuration cannot waive all behavior')
    return required


def source_inputs(root):
    tree = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '-z', 'HEAD']).decode().split('\0')
    # Shared compiled inputs are conservative. A future reviewed per-case scope can narrow this set;
    # documentation-only commits already reuse evidence without rerunning an app case.
    prefixes = ('Anytype/', 'Modules/', 'Dependencies/ProtobufMessages/', 'Anytype.xcodeproj/',
                'PinkhaStage1Acceptance/', 'Tools/PinkhaSimulatorAcceptance/')
    fixtures = {'AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift',
                'AnyTypeTests/Pinkha/SimulatorAcceptancePreparationTests.swift',
                'AnyTypeTests/Pinkha/TorahWave1IntegrationTests.swift'}
    proof_inputs = {'Tools/PinkhaSimulatorGate/run_ui27.py', 'Tools/PinkhaSimulatorGate/preflight.py',
                    'Tools/PinkhaSimulatorGate/validate_release.py', 'Tools/PinkhaSimulatorGate/required-coverage.json',
                    '.github/workflows/pinkha-simulator-ui27.yml',
                    *('Tools/PinkhaNativeDerived/' + name for name in [
                        'build_native_ipa.py', 'rerun_original_ui.py', 'install_verified_heart.py',
                        'build_custom_heart.py', 'validate_wave1.py', 'package_evidence.py'])}
    inputs = {}
    for entry in filter(None, tree):
        identity, path = entry.split('\t', 1)
        mode, kind, object_id = identity.split()
        if kind == 'blob' and mode != '120000' and (path.startswith(prefixes) or path in fixtures or path in proof_inputs):
            # Git's immutable canonical blob identity avoids rereading gigabytes of resources,
            # and remains stable across checkout line endings and documentation-only commits.
            inputs[path] = digest((mode + ' ' + object_id).encode())
    return inputs


def candidate_identity(root, matrix):
    package = (root / 'Modules/PinkhaKit/Package.swift').read_text(encoding='utf8')
    project = (root / 'Anytype.xcodeproj/project.pbxproj').read_text(encoding='utf8')
    lock = json.loads((root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_text())
    kit = next(p['state']['revision'] for p in lock['pins'] if p['identity'] == 'torahinspectorkit')
    require(re.fullmatch('[0-9a-f]{40}', kit) and f'revision: "{kit}"' in package
            and f'revision = {kit};' in project and kit == matrix['kit_sha'], 'Candidate actual Kit pins disagree')
    approval = root / 'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14'
    inventory = json.loads((approval / 'native-heart-integration.json').read_text())
    patch = digest((approval / 'native-heart-integration.patch').read_bytes().replace(b'\r\n', b'\n'))
    require(patch == inventory['patch_sha256'] == matrix['native_patch_sha256'], 'Candidate actual native inventory differs')
    return dict(kit_sha=kit, native_patch_sha256=patch, hashes=source_inputs(root))


def fetch_artifact(repo, entry):
    artifact_id = str(entry['artifact_id'])
    require(artifact_id.isdigit() and str(entry['run_id']).isdigit(), 'Invalid immutable artifact/run ID')
    metadata = json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/actions/artifacts/{artifact_id}']))
    require(not metadata.get('expired') and str(metadata['workflow_run']['id']) == str(entry['run_id']),
            'Artifact expired or belongs to another run')
    require(metadata['workflow_run']['head_sha'] == entry['source_sha'], 'Artifact source identity differs')
    require(0 < metadata['size_in_bytes'] < 512 * 1024 ** 2, 'Artifact exceeds bounded evidence size')
    data = subprocess.check_output(['gh', 'api', f'repos/{repo}/actions/artifacts/{artifact_id}/zip'])
    require(digest(data) == entry['archive_sha256'], 'Immutable artifact ZIP hash differs')
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = archive.namelist()
    if len(names) == 1 and names[0].endswith('.zip'):
        require(archive.getinfo(names[0]).file_size < 512 * 1024 ** 2, 'Inner evidence ZIP too large')
        archive = zipfile.ZipFile(io.BytesIO(archive.read(names[0])))
    require(sum(i.file_size for i in archive.infolist()) < 1024 ** 3, 'Expanded evidence too large')
    return {safe_path(i.filename): archive.read(i) for i in archive.infolist()
            if not i.is_dir() and i.filename.endswith(('.json', '.png', '.txt', '.log'))}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status='FAIL', started_at=datetime.now(timezone.utc).isoformat(), accepted=[],
                  verified_partial_records=[], failures=[])
    try:
        root = args.root.resolve()
        matrix = json.loads((root / 'Tools/PinkhaSimulatorGate/required-coverage.json').read_text())
        ledger = json.loads(args.ledger.read_text())
        require(ledger.get('schema_version') == 1 and matrix.get('schema_version') == 1, 'Unknown gate schema')
        candidate = candidate_identity(root, matrix)
        require(bool(candidate['hashes']), 'No actual candidate compiled inputs')
        result['candidate_sha'] = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        if os.environ.get('GITHUB_SHA'):
            require(result['candidate_sha'] == os.environ['GITHUB_SHA'], 'Distribution checkout differs from the actual run source')
        result['candidate_inputs_sha256'] = digest(json.dumps(candidate, sort_keys=True).encode())
        cache = {}
        for required in matrix['cases']:
            for configuration in required['configurations']:
                required_configuration = configuration_requirements(required, configuration)
                key = required['id'] + '/' + configuration
                try:
                    entries = [e for e in ledger['records'] if e.get('case_id') == required['id']
                               and e.get('configuration_id') == configuration]
                    require(bool(entries), 'At least one accepted immutable case receipt is required')
                    records = []
                    for entry in entries:
                        artifact = (str(entry['artifact_id']), str(entry['run_id']), entry['source_sha'])
                        if artifact not in cache:
                            cache[artifact] = fetch_artifact(os.environ['GITHUB_REPOSITORY'], entry)
                        files = cache[artifact]
                        receipt_bytes = files[safe_path(entry['receipt_path'])]
                        require(digest(receipt_bytes) == entry['receipt_sha256'], 'Case receipt hash differs')
                        record = json.loads(receipt_bytes)
                        require(record['source_sha'] == entry['source_sha'] and record['run_id'] == str(entry['run_id']),
                                'Receipt/artifact source or run differs')
                        verified = validate_record(required_configuration, configuration, record, files,
                                                   candidate, ledger.get('visual_reviews', []))
                        records.append(verified)
                        result['verified_partial_records'].append(verified)
                    require_complete_case(required_configuration, records)
                    result['accepted'].append(dict(case_id=required['id'], configuration_id=configuration,
                                                   supporting_records=records))
                except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
                    result['failures'].append(dict(case=key, error=str(error)))
        if not result['failures'] and result['accepted']:
            result['status'] = 'PASS'
    except BaseException as error:
        result['failures'].append(dict(error_type=type(error).__name__, error=str(error)))
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    (args.evidence / 'release-gate.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
