"""Create exact test-only source overlays without modifying the frozen control snapshot."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
CONTROL = ROOT.parent / 't2-resume-source'
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'source-baseline'
OVERLAY = HERE / 'overlay'
sha = lambda data: hashlib.sha256(data).hexdigest()
IMPORT = '\n\t"github.com/anyproto/anytype-heart/util/pinkhat2test"'

def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)

def instrument(path, source, transform):
    before = source.read_bytes()
    if source.is_relative_to(CONTROL):
        inventory = json.loads((CONTROL / 'Tools/TorahNativeOperations/heart-registration.json').read_text())
        assert sha(before) == inventory['overlay'][path], 'Published product source changed: ' + path
    else:
        assert sha(before) == {
            'core/block/cache/cache.go': '4577909a70a480c2bde63985ee3f800e86d4dfa4121d004f15b676544778b3f7',
            'core/application/account_stop.go': '5675f1211e5fcb3d95d54ea1d9894a5834df27b8ab3af75d0e7d075b55f1069a',
        }[path], 'Pinned upstream source changed: ' + path
    text = transform(before.decode())
    import_end = text.index('\n)\n', text.index('import (\n'))
    text = text[:import_end] + IMPORT + text[import_end:]
    after = text.encode()
    target = OVERLAY / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(after)
    return {'path': path, 'before_sha256': sha(before), 'after_sha256': sha(after),
            'diff': ''.join(difflib.unified_diff(before.decode().splitlines(True), text.splitlines(True),
                                               fromfile='a/' + path, tofile='b/' + path))}

def operations(text):
    text = replace_once(text,
        '\tleaseCtx, release, err := torahopsobject.AcquireNativeTargetLease(ctx, spc, root.Id, target)',
        '\tif write {\n\t\tpinkhat2test.Point(ctx, "prelease", target.ObjectID, "write", s.application)\n\t}\n'
        '\tleaseCtx, release, err := torahopsobject.AcquireNativeTargetLease(ctx, spc, root.Id, target)')
    return replace_once(text,
        '\tresult, appendErr := host.AppendTorahOperation(hostCtx, op)\n',
        '\tresult, appendErr := host.AppendTorahOperation(hostCtx, op)\n'
        '\tpinkhat2test.Point(ctx, "append-native-return", req.Target.ObjectID, "write", scope.application)\n')

def commit(text):
    return replace_once(text,
        '\t\treturn s.Storage.AddAll(ctx, changes, heads, snapshot)\n\t}()',
        '\t\tpinkhat2test.Point(ctx, "commit-before-storage", s.header.Id, "", s)\n'
        '\t\terr := s.Storage.AddAll(ctx, changes, heads, snapshot)\n'
        '\t\tpinkhat2test.Point(ctx, "commit-after-storage", s.header.Id, "", s)\n'
        '\t\treturn err\n\t}()')

def cache(text):
    start = text.index('func Do[t any](')
    end = text.index('\nfunc DoWait[', start)
    body = replace_once(text[start:end], '\tsb.Lock()\n',
        '\tpinkhat2test.Point(ctx, "delete-lock-attempt", objectID, pinkhat2test.TypeName[t](), sb)\n'
        '\tsb.Lock()\n'
        '\tpinkhat2test.Point(ctx, "delete-lock-acquired", objectID, pinkhat2test.TypeName[t](), sb)\n')
    return text[:start] + body + text[end:]

def stop(text):
    start = text.index('func (s *Service) AccountStop(')
    end = text.index('\nfunc (s *Service) AccountChangeNetworkConfigAndRestart', start)
    body = replace_once(text[start:end], '\ts.lock.Lock()\n',
        '\tpinkhat2test.Point(context.Background(), "stop-lock-attempt", "", "", s)\n'
        '\ts.lock.Lock()\n'
        '\tpinkhat2test.Point(context.Background(), "stop-lock-acquired", "", "", s)\n')
    return text[:start] + body + text[end:]

def application_lease(text):
    return replace_once(text, '\tvar once sync.Once\n',
        '\tpinkhat2test.Point(ctx, "app-lease-held", "", "", s)\n\tvar once sync.Once\n')

product = CONTROL / 'Tools/TorahNativeOperations/overlay'
specs = [('core/pinkha_torah_operations.go', product, operations),
         ('core/block/editor/torahops/native_commit_guard.go', product, commit),
         ('core/application/pinkha_torah_lifecycle.go', product, application_lease),
         ('core/block/cache/cache.go', BASE, cache),
         ('core/application/account_stop.go', BASE, stop)]
entries = [instrument(path, source / path, edit) for path, source, edit in specs]
patch = ''.join(e.pop('diff') for e in entries)
(HERE / 'test-composition.patch').write_text(patch)
manifest = {'status': 'LOCAL_CANDIDATE_NOT_COMPILED_NOT_DISPATCHED',
    'app_sha': '16b7493fa05bdc3abbae190c6e6c364c81874eea',
    'heart_sha': 'd98420b1113536afd08cde6de9a5816f6d27ffff',
    'scope': 'TEST_COMPILE_OVERLAYS_ONLY_NOT_SHIPPED_PRODUCT',
    'instrumented': entries,
    'patch_sha256': sha((HERE / 'test-composition.patch').read_bytes()),
    'added': {
        'util/pinkhat2test/lifecycle.go': {'fixture': 'lifecycle_observer.go', 'sha256': sha((HERE / 'lifecycle_observer.go').read_bytes())},
        'clientlibrary/service/pinkha_t2_native_rpc_lifecycle_test.go': {
            'fixture': 'native_rpc_lifecycle_test.go', 'sha256': sha((HERE / 'native_rpc_lifecycle_test.go').read_bytes())},
    },
    'app_capability': 'OFF'}
(HERE / 'candidate.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': manifest['status'], 'instrumented_files': len(entries),
                  'manifest_sha256': sha((HERE / 'candidate.json').read_bytes())}))
