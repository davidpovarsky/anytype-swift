"""Reproducible real native-engine acceptance in an isolated pinned checkout.

Requires the verified native Tantivy archive and Go 1.26.5. Creates only a
temporary Go workspace; never changes Heart go.mod, user accounts or Spaces.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source', type=Path, required=True)
parser.add_argument('--go', required=True)
parser.add_argument('--tantivy-directory', type=Path, required=True)
parser.add_argument('--module-cache', type=Path)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--benchmarks', action='store_true')
parser.add_argument('--benchmarks-only', action='store_true')
parser.add_argument('--benchmark-pattern', default='^TestNativeBenchmarks$')
args = parser.parse_args()
if args.benchmarks_only:
    args.benchmarks = True
root = Path(__file__).resolve().parents[2]
heart = args.heart_source.resolve()
evidence = args.evidence.resolve()
evidence.mkdir(parents=True, exist_ok=True)
if subprocess.check_output(['git', '-C', str(heart), 'rev-parse', 'HEAD'], text=True).strip() != 'd98420b1113536afd08cde6de9a5816f6d27ffff':
    raise RuntimeError('Wrong native Heart source revision')
env = dict(os.environ, GOMAXPROCS='2', CGO_ENABLED='1',
           CGO_LDFLAGS='-L' + str(args.tantivy_directory.resolve()),
           PINKHA_NATIVE_WIRE_ACCEPTANCE='1', PINKHA_NATIVE_BENCH='1' if args.benchmarks else '0')
if args.module_cache:
    env['GOMODCACHE'] = str(args.module_cache.resolve())
checks = [
    ('original-regression', heart, ['./core/pinkha/...', './pkg/lib/bundle', './pkg/lib/database',
                                    './pkg/lib/localstore/objectstore/spaceindex', './core/block/object/objectcreator'], None),
    ('product-acceptance', root/'Tools/TorahNativeDerivedSpike/integration', ['./...'],
     '^(TestProductionEngineLifecycleAndRecovery|TestNativeMembershipAndCommittedNotifications|TestRealNativeMiddlewareDerivedProperties)$'),
]
if args.benchmarks_only:
    checks = []
if args.benchmarks:
    checks.append(('native-benchmarks', root/'Tools/TorahNativeDerivedSpike/integration', ['./...'], args.benchmark_pattern))
results = []
with tempfile.TemporaryDirectory(prefix='pinkha-native-validation-') as directory:
    workspace = Path(directory)/'go.work'
    modules = [heart, root/'Modules/PinkhaHeart', root/'Tools/TorahNativeDerivedSpike', root/'Tools/TorahNativeDerivedSpike/integration']
    workspace.write_text('go 1.26.5\nuse (\n' + ''.join('  ' + json.dumps(str(path)) + '\n' for path in modules) + ')\n')
    env['GOWORK'] = str(workspace)
    for name, cwd, packages, pattern in checks:
        command = [args.go, 'test', '-p', '2', '-json', '-count=1', '-timeout', '60m',
                   '-tags', 'nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg']
        if pattern:
            command += ['-run', pattern]
        command += packages
        log = evidence/(name+'.log')
        print(json.dumps(dict(starting=name)), flush=True)
        with log.open('w', encoding='utf8') as stream:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        actions = []
        for line in log.read_text(encoding='utf8', errors='replace').splitlines():
            try: actions.append(json.loads(line))
            except ValueError: pass
        passed = sum(a.get('Action') == 'pass' and bool(a.get('Test')) for a in actions)
        skipped = sum(a.get('Action') == 'skip' and bool(a.get('Test')) for a in actions)
        entry = dict(name=name, command=command, exit_code=result.returncode, passed=passed, skipped=skipped,
                     status='PASS' if result.returncode == 0 and passed > 0 and (skipped == 0 or pattern is None) else 'FAIL',
                     scope='real pinned native product engine; no physical iPad/UI inference', host=platform.platform())
        results.append(entry)
        (evidence/'results.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf8')
        print(json.dumps(entry), flush=True)
        if entry['status'] != 'PASS':
            print(log.read_text(encoding='utf8', errors='replace')[-5000:])
            break
raise SystemExit(int(any(item['status'] != 'PASS' for item in results)))
