"""Run downstream tests against an unmodified, pinned Heart checkout.

Requires the pinned Heart's Go version, CGO compiler and verified Tantivy
library. No dependency pins, original source or global Go settings are edited.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--heart-source', required=True, type=Path)
parser.add_argument('--go', default='go')
parser.add_argument('--native-library', type=Path)
parser.add_argument('--module-cache', type=Path)
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--bench', action='store_true')
args = parser.parse_args()
heart = args.heart_source.resolve()
module = Path(__file__).resolve().parent
head = subprocess.check_output(['git', '-C', str(heart), 'rev-parse', 'HEAD'], text=True).strip()
if head != 'd98420b1113536afd08cde6de9a5816f6d27ffff':
    raise SystemExit('Heart checkout is not the verified pinned commit')
subprocess.run(['git', '-C', str(heart), 'diff', '--exit-code', '--quiet'], check=True)
subprocess.run(['git', '-C', str(heart), 'diff', '--cached', '--exit-code', '--quiet'], check=True)
args.evidence.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='pinkha-heart-probe-') as temporary:
    work = Path(temporary) / 'go.work'
    product = module.parents[1] / 'Modules' / 'PinkhaHeart'
    work.write_text('go 1.26.5\nuse (\n' + '\n'.join(json.dumps(str(path)) for path in [heart, product, module, module/'integration']) + '\n)\n', encoding='utf-8')
    env = dict(os.environ, GOWORK=str(work), CGO_ENABLED='1', GOMAXPROCS='2')
    if args.module_cache:
        env['GOMODCACHE'] = str(args.module_cache.resolve())
    if args.native_library:
        env['CGO_LDFLAGS'] = '-L' + str(args.native_library.resolve())
    if args.bench:
        env['PINKHA_NATIVE_BENCH'] = '1'
    command = [args.go, 'test', '-p', '2', '-json', '-count=1', './...']
    log = args.evidence / 'heart-native-probe.log'
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, cwd=module/'integration', env=env, stdout=stream, stderr=subprocess.STDOUT)
    metadata = dict(heart_sha=head, command=command, exit_code=result.returncode, scope='ObjectStore probe; no app/native Set/production indexer integration', bench=args.bench)
    (args.evidence/'heart-native-probe-result.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata))
    print(log.read_text(encoding='utf-8')[-5000:])
    raise SystemExit(result.returncode)
