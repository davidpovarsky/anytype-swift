#!/usr/bin/env python3
"""Independently verify the native bundle retained after an actual UI failure.

No simulator or engine call is made. This does not grant the failed UI method,
its second capture/close, destination admission or whole-space migration.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = Path('/Users/m1/development/anytype-c-active-20261125/app13-fresh-source-capture/prepared-resume-attempt1')
CONTROL = ROOT.parent / 'control-resume2e266'
COMMON = Path('/Users/m1/development/anytype-e-active-20261125/main13/control-643c7d8/combined_heart_semantics_current.py')
PINS = {
    'evidence/execution.json': '6b3cc3807176e803e4b2e2aa4124c52b9e30684fa30350035834d40d7bb793cb',
    'evidence/final-outcome.json': '5f116429be99ef72324c9199a489cd25e54f7c564c4ab060d41b1da5205e1029',
    'evidence/source-review/result.json': '680bdb1749e34219fa3641fca647399105c3f0d94acd93fc67c694d9a9ba0afe',
    'private/pinkha-semantic-page154-mounted-fixture.json': '1fcf19934d5ab77669339a71cee62f771f5610099117ca418a866d14876229e2',
    'private/owned-account-originals/retention.json': '00d6c3342a7d7bed788e08f412df82f5f9e82d82f3f5f1aaea3538c8c7bcc59d',
    'private/owned-account-originals/device.plist': '97d9ecd8995c36a80b0c982c71a36996d88b229678804d98049be5bc55cd8fed',
}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def load(name, path, expected):
    assert path.is_file() and not path.is_symlink() and digest(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    proof = {'protocol': 'pinkha-retained-native-capture-only-v1', 'status': 'FAIL',
        'actualSourceUI': {'passed': 0, 'failed': 1, 'skipped': 0},
        'twoCapturesTwoClosesQualified': False, 'destinationAdmission': False,
        'wholeSpaceMigration': False, 'extraEngineCalls': 0, 'extraSimulatorCalls': 0,
        'sourceAppCommit': 'e540cd7e01b497f1b3173ae2e68b43ade0b00b6f',
        'nativeClosure': '410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9',
        'originalPins': PINS}
    try:
        assert all(digest(ROOT / name) == expected for name, expected in PINS.items())
        core = load('c_retained_core', COMMON, '73ee947386ac6115ec7b1d75d74b1590a68a033000b311329fb8824c15691239')
        capture = load('c_retained_capture', CONTROL / 'run_app13_observed_heart_source_capture.py',
            '5330c499dcac6a57d7242256a9daaf8702dc5e2d826327a14bfd10fbb1f572ec')
        retainer = load('c_retained_copier', CONTROL / 'retain_fresh_c_source_account.py',
            '24b3d4739fb4a3404263832f0a710365bb314c3249c3c392a2db53a731eb3ee9')
        execution = core.decode(core.raw(ROOT / 'evidence/execution.json'))
        final = core.decode(core.raw(ROOT / 'evidence/final-outcome.json'))
        assert final['status'] == 'FAIL' and execution['cleanup']['status'] == 'PASS'
        private = ROOT / 'private/owned-account-originals'
        backup = core.decode(core.raw(private / 'retention.json'))
        assert backup['status'] == 'PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE'
        assert backup['executionSHA256'] == PINS['evidence/execution.json']
        scopes = {}
        for name in ['application-data', 'shared-app-groups', 'keychains', 'device-preferences']:
            before = core.decode(core.raw(private / (name + '-before.json')))
            copied = core.decode(core.raw(private / (name + '-copied.json')))
            after = core.decode(core.raw(private / (name + '-after.json')))
            assert retainer.inventory(private / name) == before == copied == after
            scopes[name] = {'entries': len(before), 'manifestSHA256': digest(private / (name + '-copied.json'))}
        fixture = core.decode(core.raw(ROOT / 'private/pinkha-semantic-page154-mounted-fixture.json'))
        parent, captures = capture.captures_inventory(core, private / 'application-data')
        assert len(captures) == 1
        verified = [capture.verify_bundle(core, parent / name, fixture) for name in sorted(captures)]
        observations = []
        for path in sorted(parent.glob('source-observation-*.json')):
            raw = capture.diagnostic_bytes(core, path)
            observations.append({'fileSHA256': digest(path), 'bytes': path.stat().st_size})
        assert all(digest(ROOT / name) == expected for name, expected in PINS.items())
        assert capture.captures_inventory(core, private / 'application-data')[1] == captures
        proof.update(status='PASS_ONE_ORIGINAL_NATIVE_BUNDLE_NOT_UI_ACCEPTANCE',
            verifiedCaptures=verified, retainedScopes=scopes, diagnosticFiles=observations)
    except BaseException as error:
        proof.update(status='FAIL', error={'type': type(error).__name__, 'message': str(error)})
    finally:
        (args.output / 'receipt.json').write_text(json.dumps(proof, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': proof['status'], 'receiptSHA256': digest(args.output / 'receipt.json'),
        'extraEngineCalls': 0, 'wholeSpaceMigration': False}))
    return 0 if proof['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())
