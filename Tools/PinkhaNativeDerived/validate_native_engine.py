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
import hashlib
from build_custom_heart import NATIVE_REGRESSION_PACKAGES

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source', type=Path, required=True)
parser.add_argument('--go', required=True)
parser.add_argument('--tantivy-directory', type=Path, required=True)
parser.add_argument('--module-cache', type=Path)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--benchmarks', action='store_true')
parser.add_argument('--benchmarks-only', action='store_true')
parser.add_argument('--benchmark-pattern', default='^TestNativeBenchmarks$')
parser.add_argument('--approved-inventory', type=Path)
parser.add_argument('--only', choices=['projection-presentation','native-outbox','product-acceptance','original-regression'])
parser.add_argument('--compatibility-exports', type=Path)
parser.add_argument('--product-pattern', default='^(TestProductionEngineLifecycleAndRecovery|TestNativeMembershipAndCommittedNotifications|TestRealNativeMiddlewareDerivedProperties)$')
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
if args.compatibility_exports:
    env['PINKHA_NATIVE_COMPAT_EXPORT'] = str(args.compatibility_exports.resolve())
checks = [
    ('projection-presentation',root/'Modules/PinkhaHeart',['./...'],None),
    ('native-outbox',heart,['./pkg/lib/localstore/objectstore/spaceindex'],'^TestTorahFulltext'),
    ('product-acceptance', root/'Tools/TorahNativeDerivedSpike/integration', ['./...'],
     args.product_pattern),
    ('original-regression', heart, NATIVE_REGRESSION_PACKAGES, None),
]
if args.benchmarks_only:
    checks = []
elif args.only:
    checks = [check for check in checks if check[0] == args.only]
if args.benchmarks:
    checks.append(('native-benchmarks', root/'Tools/TorahNativeDerivedSpike/integration', ['./...'], args.benchmark_pattern))
results = []
inventory=json.loads(args.approved_inventory.read_text()) if args.approved_inventory else None

def app_revision():
    # A Windows-created worktree has a Windows absolute gitdir in its .git
    # file. Use the owning Git implementation without rewriting that metadata.
    git_file = root / '.git'
    windows_worktree = (platform.system() == 'Linux' and git_file.is_file()
                        and ':/' in git_file.read_text().replace('\\', '/'))
    if windows_worktree:
        windows_root = subprocess.check_output(['wslpath', '-w', str(root)], text=True).strip()
        command = ['git.exe', '-C', windows_root, 'rev-parse', 'HEAD']
    else:
        command = ['git', '-C', str(root), 'rev-parse', 'HEAD']
    return subprocess.check_output(command, text=True).strip()
def inputs():
    files=list((root/'Modules/PinkhaHeart').rglob('*.go'))+list((root/'Tools/TorahNativeDerivedSpike/integration').glob('*.go'))
    files+=list((root/'Tools/PinkhaNativeDerived/native_test_templates').glob('*.go'))
    data={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    if any(check[0]=='native-outbox' or check[0]=='original-regression' for check in checks):
        native_test=heart/'pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_fulltext_test.go'
        template=root/'Tools/PinkhaNativeDerived/native_test_templates/pinkha_torah_fulltext_test.go'
        if native_test.read_bytes().replace(b'\r\n',b'\n')!=template.read_bytes().replace(b'\r\n',b'\n'):
            raise RuntimeError('Applied native acceptance test differs from the recorded template')
    if inventory:
        for entry in inventory['files']:
            actual=hashlib.sha256((heart/entry['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            if actual!=entry['after_sha256']:raise RuntimeError('Native source differs: '+entry['path'])
            data['Heart/'+entry['path']]=actual
    return data
with tempfile.TemporaryDirectory(prefix='pinkha-native-validation-') as directory:
    workspace = Path(directory)/'go.work'
    modules = [heart, root/'Modules/PinkhaHeart', root/'Tools/TorahNativeDerivedSpike', root/'Tools/TorahNativeDerivedSpike/integration']
    workspace.write_text('go 1.26.5\nuse (\n' + ''.join('  ' + json.dumps(str(path)) + '\n' for path in modules) + ')\n')
    env['GOWORK'] = str(workspace)
    for name, cwd, packages, pattern in checks:
        timeout = '60m' if name == 'native-benchmarks' else '10m' if name == 'original-regression' else '5m'
        command = [args.go, 'test', '-p', '2', '-json', '-count=1', '-timeout', timeout,
                   '-tags', 'nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg']
        if pattern:
            command += ['-run', pattern]
        command += packages
        log = evidence/(name+'.log')
        source_inputs=inputs()
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
        entry['source_files']=source_inputs
        entry['app_sha']=app_revision()
        entry['heart_patch_sha256']=inventory['patch_sha256'] if inventory else None
        if inputs()!=source_inputs:entry['status']='INVALIDATED_SOURCE_CHANGED_DURING_TEST'
        results.append(entry)
        (evidence/'results.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf8')
        print(json.dumps({key:value for key,value in entry.items() if key!='source_files'}), flush=True)
        if entry['status'] != 'PASS':
            print(log.read_text(encoding='utf8', errors='replace')[-5000:])
            break
raise SystemExit(int(any(item['status'] != 'PASS' for item in results)))
