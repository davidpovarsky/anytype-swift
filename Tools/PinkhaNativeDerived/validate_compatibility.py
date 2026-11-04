"""Run actual export/import RPCs against the original or modified pinned Heart.

Consumes exports from the native middleware acceptance fixture. Never edits
Heart, its dependencies, existing accounts or personal Spaces.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source', required=True, type=Path)
parser.add_argument('--go', required=True)
parser.add_argument('--tantivy-directory', required=True, type=Path)
parser.add_argument('--module-cache', type=Path)
parser.add_argument('--input', required=True, type=Path)
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--expect-native', action='store_true')
parser.add_argument('--inventory', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
heart = args.heart_source.resolve()
module = root / 'Tools/PinkhaNativeDerived/compatibility'
fixture = args.input.resolve()
evidence = args.evidence.resolve()
evidence.mkdir(parents=True, exist_ok=True)
pin = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
if subprocess.check_output(['git', '-C', str(heart), 'rev-parse', 'HEAD'], text=True).strip() != pin:
    raise RuntimeError('Wrong original Heart revision')
if not (fixture / 'contract.json').is_file():
    raise RuntimeError('Actual native exports and their contract are required')
if args.expect_native:
    if not args.inventory:
        raise RuntimeError('Exact modified Heart inventory required')
    inventory = json.loads(args.inventory.read_text())
    for item in inventory['files']:
        actual = hashlib.sha256((heart/item['path']).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != item['after_sha256']:
            raise RuntimeError('Modified Heart source differs: ' + item['path'])
else:
    if subprocess.check_output(['git', '-C', str(heart), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('Original compatibility engine must be completely unmodified')
    inventory = None
inputs = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in fixture.rglob('*') if p.is_file()}
source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in module.glob('*.go')}
env = dict(os.environ, CGO_ENABLED='1', GOMAXPROCS='2',
           CGO_LDFLAGS='-L' + str(args.tantivy_directory.resolve()),
           PINKHA_COMPATIBILITY_INPUT=str(fixture),
           PINKHA_COMPATIBILITY_EXPECT_NATIVE='1' if args.expect_native else '0')
if args.module_cache:
    env['GOMODCACHE'] = str(args.module_cache.resolve())
with tempfile.TemporaryDirectory(prefix='pinkha-native-compatibility-') as directory:
    workspace = Path(directory) / 'go.work'
    workspace.write_text('go 1.26.5\nuse (\n' + ''.join(json.dumps(str(p))+'\n' for p in [heart, module]) + ')\n')
    env['GOWORK'] = str(workspace)
    command = [args.go, 'test', '-p', '2', '-json', '-count=1', '-timeout', '5m',
               '-tags', 'nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg',
               '-run', '^TestActualExportImportRoundTrip$', './...']
    log = evidence / 'native-compatibility.log'
    with log.open('w', encoding='utf8') as stream:
        result = subprocess.run(command, cwd=module, env=env, stdout=stream, stderr=subprocess.STDOUT)
events = []
for line in log.read_text(encoding='utf8', errors='replace').splitlines():
    try:
        events.append(json.loads(line))
    except ValueError:
        pass
passed = [x.get('Test') for x in events if x.get('Action') == 'pass' and x.get('Test')]
skipped = [x.get('Test') for x in events if x.get('Action') == 'skip' and x.get('Test')]
receipt = dict(status='PASS' if result.returncode == 0 and len(passed) == 3 and not skipped else 'FAIL',
               heart_sha=pin, modified_engine=args.expect_native,
               heart_patch_sha256=inventory['patch_sha256'] if inventory else None,
               command=command, passed=passed, skipped=skipped, exit_code=result.returncode,
               fixture_hashes=inputs, test_source_hashes=source,
               scope='actual original RPC import/edit/export of native snapshots in disposable accounts/Spaces; no device/UI inference')
(evidence / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
print(json.dumps({key: value for key, value in receipt.items() if not key.endswith('_hashes')}))
if receipt['status'] != 'PASS':
    print(log.read_text(encoding='utf8', errors='replace')[-6000:])
raise SystemExit(int(receipt['status'] != 'PASS'))
