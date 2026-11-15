"""Bounded T5 native proof; does not dispatch CI, build frameworks or enable clients."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone
from uuid import uuid4


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--heart-source', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--go', required=True)
    parser.add_argument('--tantivy-directory', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--component', choices=['projection-cache', 'native-index', 'native-rpc'], required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    receipt_path = evidence / (args.component + '-result.json')
    log_path = evidence / (args.component + '.log')
    if receipt_path.exists() or log_path.exists():
        print(json.dumps(dict(status='REFUSED_EVIDENCE_REUSE', component=args.component,
                              reason='Choose a fresh evidence directory; existing proof is immutable.')))
        return 1
    attempt = dict(run_id=str(uuid4()), started_at=datetime.now(timezone.utc).isoformat(),
                   component=args.component, status='FAIL', reason='ATTEMPT_NOT_COMPLETED',
                   client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF')
    try:
        with receipt_path.open('x', encoding='utf8') as stream:
            stream.write(json.dumps(attempt, indent=2) + '\n')
    except FileExistsError:
        print(json.dumps(dict(status='REFUSED_EVIDENCE_REUSE', component=args.component)))
        return 1
    try:
        receipt = execute(args, root, evidence)
    except BaseException as error:
        receipt = dict(status='FAIL', reason='PREFLIGHT_OR_EXECUTION_EXCEPTION',
                       error_type=type(error).__name__, error=str(error))
    receipt = dict(attempt, **{key: value for key, value in receipt.items() if key != 'reason'},
                   reason=receipt.get('reason', 'COMPLETED'), finished_at=datetime.now(timezone.utc).isoformat())
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: value for key, value in receipt.items() if key not in ['source_hashes', 'fixture_hashes']}))
    return 0 if receipt['status'] == 'PASS' else 1


def execute(args, root, evidence):
    heart = args.heart_source.resolve()
    inventory = json.loads(args.inventory.read_text())
    if subprocess.check_output(['git', '-C', str(heart), 'rev-parse', 'HEAD'], text=True).strip() != inventory['heart_sha']:
        raise RuntimeError('Wrong pinned native source')
    if inventory.get('features', {}).get('t5_related_lookup') != 1:
        raise RuntimeError('Exact T5 source capability is required')
    source_hashes = {}
    for entry in inventory['files']:
        actual = hashlib.sha256((heart / entry['path']).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != entry['after_sha256']:
            raise RuntimeError('Native source differs: ' + entry['path'])
        source_hashes[entry['path']] = actual
    components = {
        'projection-cache': (heart, ['-run', '^TestRelated', './core/pinkha/torah', './core/pinkha/torahindex']),
        'native-index': (heart, ['-run', '^TestTorahRelatedNativeIndexFilterCommitAndRecovery$', './pkg/lib/localstore/objectstore/spaceindex']),
        'native-rpc': (root / 'Tools/TorahNativeDerivedSpike/integration', ['-run', '^TestRealNativeMiddlewareDerivedProperties$', './...']),
    }
    cwd, selection = components[args.component]
    def fixture_hashes():
        paths = list((root / 'Modules/PinkhaHeart').rglob('*.go'))
        paths += list((root / 'Tools/TorahNativeDerivedSpike/integration').glob('*.go'))
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    before_fixtures = fixture_hashes()
    with tempfile.TemporaryDirectory(prefix='pinkha-t5-focused-') as directory:
        work = Path(directory) / 'go.work'
        work.write_text('go 1.26.5\nuse (\n' + ''.join(json.dumps(str(path)) + '\n' for path in [
            heart, root / 'Modules/PinkhaHeart', root / 'Tools/TorahNativeDerivedSpike',
            root / 'Tools/TorahNativeDerivedSpike/integration']) + ')\n')
        env = dict(os.environ, GOWORK=str(work), GOMAXPROCS='2', CGO_ENABLED='1',
                   CGO_LDFLAGS='-L' + str(args.tantivy_directory.resolve()),
                   PINKHA_NATIVE_WIRE_ACCEPTANCE='1', PINKHA_NATIVE_T5_LOOKUP_ACCEPTANCE='1')
        command = [args.go, 'test', '-p', '1', '-json', '-count=1', '-timeout', '5m',
                   '-tags', 'nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg', *selection]
        log = evidence / (args.component + '.log')
        with log.open('x', encoding='utf8') as output:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    events = []
    for line in log.read_text(encoding='utf8', errors='replace').splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    passed = [event.get('Test') for event in events if event.get('Action') == 'pass' and event.get('Test')]
    skipped = [event.get('Test') for event in events if event.get('Action') == 'skip' and event.get('Test')]
    output = ''.join(event.get('Output', '') for event in events)
    valid = result.returncode == 0 and bool(passed) and not skipped
    required = {
        'projection-cache': {'TestRelatedBindingCarriesSelectedIdentityWithoutChangingPublicGeneration',
                            'TestRelatedCacheInvalidatesR14AndSealsNewOutputs',
                            'TestRelatedInvalidPrivateTargetPreservesPublicReadiness',
                            'TestRelatedManifestCapabilityAndMalformedCleanup'},
        'native-index': {'TestTorahRelatedNativeIndexFilterCommitAndRecovery'},
        'native-rpc': {'TestRealNativeMiddlewareDerivedProperties'},
    }
    valid = valid and required[args.component].issubset(set(passed))
    expected_counts = {
        'projection-cache': dict(packages=2, top_level_tests=10, subcases=21),
        'native-index': dict(packages=1, top_level_tests=1, subcases=0),
        'native-rpc': dict(packages=1, top_level_tests=1, subcases=0),
    }[args.component]
    passed_packages = [event['Package'] for event in events if event.get('Action') == 'pass' and not event.get('Test')]
    actual_counts = dict(packages=len(passed_packages), top_level_tests=sum('/' not in name for name in passed),
                         subcases=sum('/' in name for name in passed))
    valid = valid and expected_counts == actual_counts
    valid = valid and before_fixtures == fixture_hashes()
    for path, expected in source_hashes.items():
        valid = valid and hashlib.sha256((heart / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected
    if args.component == 'native-rpc':
        valid = valid and 'PASS T5 real native ObjectCreate/BlockCreate/ObjectSetDetails/ObjectShow/private ObjectSearch' in output
        valid = valid and 'PASS T5 actual native private option/Property creation and object/Type attachment rejection' in output
    receipt = dict(component=args.component, status='PASS' if valid else 'FAIL', command=command,
        heart_sha=inventory['heart_sha'], patch_sha256=inventory['patch_sha256'], passed=passed, skipped=skipped,
        exit_code=result.returncode, source_hashes=source_hashes, fixture_hashes=before_fixtures,
        expected_counts=expected_counts, actual_counts=actual_counts, passed_packages=passed_packages,
        client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF',
        remaining=['actual old/new binary pairing', 'same-local-database downgrade/reopen/upgrade',
                   'full Swift host/query/target integration', 'true Inspector block navigation', 'physical iPad'])
    return receipt


if __name__ == '__main__':
    raise SystemExit(main())
