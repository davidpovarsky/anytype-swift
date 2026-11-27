from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import time

CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
OUT = Path('/var/lib/pinkha-w1-functional-migration-20261127/dependency-locator-repair1')
OLD = Path('/tmp/pinkha-d-bookmark-swift-20261126')
PINS = {
    'swift-asn1': ('swift-asn1-7065ad2c', '917b472dbe53ba699cbb0495f9a95a084bc6364d'),
    'swift-crypto': ('swift-crypto-7e0614ea', 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed'),
    'TorahInspectorKit': ('TorahInspectorKit-776a6c0e', '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

def sources():
    result = {}
    for name in PINS:
        folder = CACHE / 'checkouts' / name
        for base, directories, files in os.walk(folder, followlinks=False):
            directories[:] = [d for d in directories if d != '.git']
            for name in sorted(files):
                path = Path(base) / name
                info = path.lstat()
                row = {'mode': stat.S_IMODE(info.st_mode)}
                if path.is_symlink():
                    row['link'] = os.readlink(path)
                else:
                    assert path.is_file()
                    row.update(bytes=info.st_size, sha256=sha(path))
                result[path.relative_to(CACHE).as_posix()] = row
    return result

def products():
    result = {str(p.relative_to(CACHE)): sha(p) for p in sorted(CACHE.rglob('*'))
              if p.is_file() and p.name in ['PinkhaAnyHostTests-test-runner', 'PinkhaAnyHostTests.so']}
    assert len(result) == 2
    return result

def run(command, env=None):
    output = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    row = {'command': command, 'exitCode': output.returncode, 'stdout': output.stdout, 'stderr': output.stderr}
    result['checks'].append(row)
    write(OUT / 'result.json', result)
    assert output.returncode == 0, row
    return output.stdout

os.umask(0o077)
OUT.mkdir(parents=True, exist_ok=False)
started = time.monotonic()
result = {'status': 'RUNNING', 'scope': 'Relocate only three owned Git alternate locators to their existing exact pinned mirrors',
          'sourceCheckoutOrResetPerformed': False, 'networkFetchPerformed': False, 'compilerStarted': False,
          'checks': [], 'locators': [], 'errors': []}
before_sources = before_products = None
try:
    assert CACHE.is_dir() and not CACHE.is_symlink() and not OLD.exists()
    before_sources = sources()
    before_products = products()
    write(OUT / 'source-before.json', before_sources)
    write(OUT / 'products-before.json', before_products)
    qualified = []
    for name, (repository, pin) in PINS.items():
        checkout = CACHE / 'checkouts' / name
        mirror = CACHE / 'repositories' / repository
        object_dir = mirror / 'objects'
        locator = checkout / '.git/objects/info/alternates'
        old = str(OLD / 'repositories' / repository / 'objects') + '\n'
        new = str(object_dir) + '\n'
        assert not locator.is_symlink() and locator.read_text() == old
        assert object_dir.is_dir() and not object_dir.is_symlink()
        assert not (object_dir / 'info/alternates').exists()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env['GIT_OPTIONAL_LOCKS'] = '0'
        prefix = ['git', '-c', 'safe.directory=' + str(mirror), '--git-dir=' + str(mirror)]
        assert run(prefix + ['cat-file', '-t', pin], env).strip() == 'commit'
        run(prefix + ['fsck', '--full', '--no-dangling'], env)
        env['GIT_ALTERNATE_OBJECT_DIRECTORIES'] = str(object_dir)
        prefix = ['git', '-c', 'safe.directory=' + str(checkout), '-C', str(checkout)]
        assert run(prefix + ['rev-parse', 'HEAD'], env).strip() == pin
        assert not run(prefix + ['status', '--porcelain', '--untracked-files=all'], env)
        mode = stat.S_IMODE(locator.stat().st_mode)
        result['locators'].append({'checkout': str(checkout), 'pin': pin, 'old': old, 'new': new,
                                   'oldSHA256': sha(locator), 'mode': mode, 'changed': False})
        qualified.append((locator, old, new, mode, checkout, pin))
    write(OUT / 'qualified-locators.json', result['locators'])
    for i, (locator, old, new, mode, checkout, pin) in enumerate(qualified):
        assert locator.read_text() == old
        replacement = locator.with_name('alternates.pinkha-w1-relocated')
        with replacement.open('x') as stream:
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        replacement.chmod(mode)
        os.replace(replacement, locator)
        assert locator.read_text() == new and stat.S_IMODE(locator.stat().st_mode) == mode
        result['locators'][i].update(changed=True, newSHA256=sha(locator))
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env['GIT_OPTIONAL_LOCKS'] = '0'
        prefix = ['git', '-c', 'safe.directory=' + str(checkout), '-C', str(checkout)]
        assert run(prefix + ['rev-parse', 'HEAD'], env).strip() == pin
        assert not run(prefix + ['status', '--porcelain', '--untracked-files=all'], env)
        assert result['checks'][-1]['stderr'] == ''
    result['status'] = 'PASS_OWNED_DEPENDENCY_LOCATORS_REPAIRED'
except BaseException as error:
    result['status'] = 'FAIL'
    result['errors'].append({'type': type(error).__name__, 'message': str(error)})
finally:
    try:
        after_sources = sources()
        after_products = products()
        write(OUT / 'source-after.json', after_sources)
        write(OUT / 'products-after.json', after_products)
        if before_sources is not None:
            result['allDependencySourceFilesAndModesUnchanged'] = after_sources == before_sources
            assert result['allDependencySourceFilesAndModesUnchanged']
        if before_products is not None:
            result['acceptedCompiledProductsUnchanged'] = after_products == before_products
            assert result['acceptedCompiledProductsUnchanged']
        result['controllerSHA256'] = sha(Path(__file__))
        result['sourceManifestSHA256'] = sha(OUT / 'source-after.json')
        result['productsManifestSHA256'] = sha(OUT / 'products-after.json')
        result['sourceFiles'] = len(after_sources)
    except BaseException as error:
        result['status'] = 'FAIL'
        result['errors'].append({'type': type(error).__name__, 'message': 'final integrity: ' + str(error)})
    result['seconds'] = round(time.monotonic() - started, 3)
    write(OUT / 'result.json', result)
print(json.dumps({key: result.get(key) for key in ['status', 'seconds', 'sourceFiles', 'acceptedCompiledProductsUnchanged', 'errors']}))
raise SystemExit(0 if result['status'] == 'PASS_OWNED_DEPENDENCY_LOCATORS_REPAIRED' else 1)
