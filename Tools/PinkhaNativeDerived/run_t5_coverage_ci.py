"""Run one pinned native source fixture; never build an Apple SDK or enable clients."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SOURCE = '947fbde24d5657d0e1229f45bb3993648884a8a1'
HEART = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
PATCH = '5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2'
APPROVAL = 'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-15/'
HASHES = {
    'Tools/PinkhaNativeDerived/build_custom_heart.py': '8534f5a3ecc1df8321dc3820409f1c8812d876bfe7989877bf121681d04955fd',
    'Tools/PinkhaNativeDerived/validate_t5_coverage.py': '6d7e21402f381bc613663f90ab669253e276cc9608c9c66de900ae371896edf1',
    'Tools/PinkhaNativeDerived/native_test_templates/pinkha_torah_reopen_test.go': '89f6096355cefdd342ec44ba0bef21b87e832566d85172b25a92d33f51b5fa79',
    'Tools/PinkhaNativeDerived/test_t5_validation_receipts.py': 'a1bbe2842f9572ba9789f2b01a7af7e660928eb5396a2aa8ee6139e791468d05',
    APPROVAL + 'native-heart-integration.json': 'f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7',
    APPROVAL + 'native-heart-integration.patch': PATCH,
}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def write_receipt(path, receipt):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)


def require_identity(control):
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '')
    sha = os.environ.get('GITHUB_SHA', '')
    if not run_id.isdigit() or not attempt.isdigit() or not re.fullmatch('[0-9a-f]{40}', sha):
        raise RuntimeError('A real GitHub run/attempt/full source identity is required')
    if git(control, 'rev-parse', 'HEAD') != sha:
        raise RuntimeError('Integration checkout differs from this GitHub run')
    return dict(github_run_id=run_id, github_run_attempt=attempt, integration_sha=sha)


def execute(args, control, evidence):
    identity = require_identity(control)
    source, heart = args.source.resolve(), args.heart.resolve()
    if git(source, 'rev-parse', 'HEAD') != SOURCE or git(heart, 'rev-parse', 'HEAD') != HEART:
        raise RuntimeError('Reviewed source/native pin mismatch')
    if git(source, 'status', '--porcelain') or git(heart, 'status', '--porcelain'):
        raise RuntimeError('Proof requires clean fresh source and native checkouts')
    for path, expected in HASHES.items():
        if digest(source / path) != expected:
            raise RuntimeError('Reviewed input differs: ' + path)
    version = subprocess.check_output(['go', 'version'], text=True).strip()
    if not version.startswith('go version go1.26.5 linux/amd64'):
        raise RuntimeError('Expected pinned Linux Go 1.26.5, got ' + version)
    def run(command, name, cwd=source):
        with (evidence / (name + '.log')).open('x', encoding='utf8') as output:
            result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(name + ' failed; see its retained log')
    helper = source / 'Tools/PinkhaNativeDerived'
    inventory = source / (APPROVAL + 'native-heart-integration.json')
    run([sys.executable, str(helper / 'build_custom_heart.py'), '--heart-source', str(heart),
         '--patch', str(source / (APPROVAL + 'native-heart-integration.patch')),
         '--inventory', str(inventory), '--approved-patch-sha256', PATCH,
         '--apply-approved-patch', '--target', 'verify', '--evidence', str(evidence / 'source-preflight')], 'source-preflight')
    spec = importlib.util.spec_from_file_location('pinned_heart_helper', helper / 'build_custom_heart.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tantivy = module.fetch_tantivy(heart, 'linux-amd64-musl')
    (evidence / 'tantivy.json').write_text(json.dumps(tantivy, indent=2) + '\n', encoding='utf8')
    run([sys.executable, str(helper / 'test_t5_validation_receipts.py')], 'driver-controls')
    run([sys.executable, str(helper / 'validate_t5_coverage.py'), '--heart-source', str(heart),
         '--inventory', str(inventory), '--go', 'go', '--tantivy-directory', str(heart / 'deps/libs/linux-amd64-musl'),
         '--component', args.component, '--evidence', str(evidence)], 'native-component')
    component = json.loads((evidence / (args.component + '-result.json')).read_text())
    expected = {'projection-cache': dict(packages=2, top_level_tests=10, subcases=21),
                'native-index': dict(packages=1, top_level_tests=2, subcases=0),
                'native-rpc': dict(packages=1, top_level_tests=1, subcases=0)}[args.component]
    if (component.get('status') != 'PASS' or component.get('exit_code') != 0
            or component.get('actual_counts') != expected or component.get('skipped') != []
            or component.get('heart_sha') != HEART or component.get('patch_sha256') != PATCH
            or component.get('component') != args.component
            or component.get('client_enablement') != 'DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF'):
        raise RuntimeError('Native component receipt failed independent CI outcome checks')
    if require_identity(control) != identity or git(source, 'diff', 'HEAD'):
        raise RuntimeError('Source/run identity changed during proof')
    for path, expected_hash in HASHES.items():
        if digest(source / path) != expected_hash:
            raise RuntimeError('Reviewed source changed during proof: ' + path)
    return dict(status='PASS', **identity, source_sha=SOURCE, heart_sha=HEART, patch_sha256=PATCH,
                driver_hashes=HASHES, go_version=version, tantivy=tantivy,
                actual_counts=component['actual_counts'], passed=component['passed'],
                component_receipt_sha256=digest(evidence / (args.component + '-result.json')))


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--heart', type=Path, required=True)
    parser.add_argument('--component', choices=['projection-cache', 'native-index', 'native-rpc'], required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    receipt_path = evidence / 'ci-result.json'
    receipt = dict(status='RUNNING', component=args.component, started_at=datetime.now(timezone.utc).isoformat(),
                   client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF',
                   limits=['native source fixtures only', 'no packaged old/new binaries', 'no Swift/UI/physical acceptance'])
    write_receipt(receipt_path, receipt)
    try:
        receipt.update(execute(args, Path(__file__).resolve().parents[2], evidence))
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    write_receipt(receipt_path, receipt)
    print(json.dumps(receipt))
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
