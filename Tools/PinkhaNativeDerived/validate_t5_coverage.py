"""Bounded T5 native proof; does not dispatch CI, build frameworks or enable clients."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--heart-source', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--go', required=True)
    parser.add_argument('--tantivy-directory', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--component', choices=['projection-cache', 'native-index', 'native-rpc'], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
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
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
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
        with log.open('w', encoding='utf8') as output:
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
    valid = valid and before_fixtures == fixture_hashes()
    for path, expected in source_hashes.items():
        valid = valid and hashlib.sha256((heart / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected
    if args.component == 'native-rpc':
        valid = valid and 'PASS T5 real native ObjectCreate/BlockCreate/ObjectSetDetails/ObjectShow/private ObjectSearch' in output
        valid = valid and 'PASS T5 actual native private option/Property creation and object/Type attachment rejection' in output
    receipt = dict(component=args.component, status='PASS' if valid else 'FAIL', command=command,
        heart_sha=inventory['heart_sha'], patch_sha256=inventory['patch_sha256'], passed=passed, skipped=skipped,
        exit_code=result.returncode, source_hashes=source_hashes, fixture_hashes=before_fixtures,
        client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF',
        remaining=['actual old/new binary pairing', 'same-local-database downgrade/reopen/upgrade',
                   'full Swift host/query/target integration', 'true Inspector block navigation', 'physical iPad'])
    (evidence / (args.component + '-result.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({key: value for key, value in receipt.items() if key != 'source_hashes'}))
    raise SystemExit(0 if valid else 1)


if __name__ == '__main__':
    main()
