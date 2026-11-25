#!/usr/bin/env python3
"""Build only the shared production Host probe; no native account or tests."""
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
import traceback
import shutil

ROOT = Path('/Users/m1/builds/e-semantic-peer-native-20261125')
PRODUCER = Path('/Users/m1/builds/e-combined-current-20261125/frozen-current5c05/source')
SOURCE = '5c05a612e4054a4adfa7f812343be6a15871cc89'
CANDIDATE = 'daa14bed739503cc7dc65f838a1adf4fb133a01c'
MODULES = ['PinkhaAnyEngine', 'PinkhaAnyIntegration', 'PinkhaAnyHost', 'PinkhaKit']
PROBE = 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/'
ADDED = 'SemanticAnchorPeerProbe.swift'
EXPECTED_ADDED = 'd49b7d0c6e5bd75d69c029e1d217c58168d7ab09054d088581eef92282795fda'
DISPATCH = '''        if arguments.contains("--semantic-peer") {
            try await runSemanticAnchorPeerProbe(client: client, workspace: workspace, owner: owner, arguments: arguments)
            return
        }
'''

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise ValueError('not a regular file: ' + str(path))
    return path.read_bytes()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write('\n')

def git(*args):
    return subprocess.check_output(['git', '-C', str(PRODUCER), *args])

def inventory(path):
    result = {}
    for p in sorted(path.rglob('*')):
        if p.is_file() or p.is_symlink():
            b = read(p)
            result[str(p.relative_to(path))] = {'bytes': len(b), 'sha256': sha(b)}
    return result

def main():
    os.umask(0o077)
    attempt = ROOT / 'probe-build1'
    attempt.mkdir(exist_ok=False)
    result = {'protocol': 'pinkha-semantic-peer-probe-build-v1',
              'status': 'FAIL', 'sourceCommit': SOURCE, 'probeCandidate': CANDIDATE,
              'nativeBuilds': 0, 'appBuilds': 0, 'testsExecuted': 0, 'accountsCreated': 0,
              'startedAt': time.time()}
    process = None
    try:
        if shutil.disk_usage(ROOT).free < 6 * 1024**3:
            raise ValueError('measured 4 GiB phase allowance plus 2 GiB emergency floor unavailable')
        if git('rev-parse', 'HEAD').decode().strip() != SOURCE:
            raise ValueError('immutable producer checkout identity changed')
        source = ROOT / 'source'
        source.mkdir(exist_ok=False)
        names = git('ls-tree', '-r', '--name-only', '-z', SOURCE, '--',
                    *['Modules/' + n for n in MODULES]).decode().split('\0')
        originals = {}
        for name in filter(None, names):
            b = git('show', SOURCE + ':' + name)
            if read(PRODUCER / name) != b:
                raise ValueError('producer worktree differs from exact Git bytes: ' + name)
            p = source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
            originals[name] = {'bytes': len(b), 'sha256': sha(b)}
        new = read(ROOT / 'candidate' / ADDED)
        if sha(new) != EXPECTED_ADDED:
            raise ValueError('peer candidate changed')
        original = read(source / PROBE / 'Probe.swift')
        candidate = read(ROOT / 'candidate/Probe.swift')
        if candidate.count(DISPATCH.encode()) != 1 or candidate.replace(DISPATCH.encode(), b'', 1) != original:
            raise ValueError('Probe.swift is not the single reviewed dispatch addition')
        (source / PROBE / ADDED).write_bytes(new)
        (source / PROBE / 'Probe.swift').write_bytes(candidate)
        before = inventory(source)
        save(attempt / 'original-production-sources.json', originals)
        save(attempt / 'source-before.json', before)
        package = source / 'Modules/PinkhaAnyHost'
        lock = json.loads(read(package / 'Package.resolved'))
        expected = {'swift-asn1': '917b472dbe53ba699cbb0495f9a95a084bc6364d',
                    'swift-crypto': 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed',
                    'torahinspectorkit': '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'}
        if {p['identity']: p['state']['revision'] for p in lock['pins']} != expected:
            raise ValueError('production dependency lock mismatch')
        result['packageResolvedSHA256'] = sha(read(package / 'Package.resolved'))
        result['sourceManifestSHA256'] = sha(read(attempt / 'source-before.json'))
        result['sourceFileCount'] = len(before)
        cmd = ['xcrun', 'swift', 'build', '--package-path', str(package), '--scratch-path', str(ROOT / 'scratch'),
               '--cache-path', str(ROOT / 'cache'), '--config-path', str(ROOT / 'config'),
               '--security-path', str(ROOT / 'security'), '--build-system', 'native',
               '--disable-automatic-resolution', '--disable-index-store', '-j', '4',
               '--product', 'pinkha-any-host-probe']
        result['command'] = cmd
        with (attempt / 'original.log').open('xb') as log:
            process = subprocess.Popen(cmd, cwd=source, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            result['pid'] = process.pid
            result['pgid'] = process.pid
            save(attempt / 'started.json', result)
            start = time.monotonic()
            minimum = shutil.disk_usage(ROOT).free
            while process.poll() is None:
                free = shutil.disk_usage(ROOT).free
                minimum = min(minimum, free)
                if free < 2 * 1024**3 or time.monotonic() - start > 900:
                    result['interruption'] = 'emergency capacity floor or 900s deadline'
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                    break
                time.sleep(0.5)
            result['exitCode'] = process.wait(timeout=15)
            result['durationSeconds'] = round(time.monotonic() - start, 3)
            result['minimumFreeBytes'] = minimum
        after = inventory(source)
        save(attempt / 'source-after.json', after)
        if after != before:
            raise ValueError('source changed during build')
        if result['exitCode'] != 0:
            raise ValueError('actual Swift build failed; original log retained')
        dependencies = {}
        for p in (ROOT / 'scratch/checkouts').iterdir():
            revision = subprocess.check_output(['git', '-C', str(p), 'rev-parse', 'HEAD']).decode().strip()
            identity = p.name.lower()
            if expected.get(identity) != revision:
                raise ValueError('actual dependency checkout differs: ' + p.name)
            if subprocess.check_output(['git', '-C', str(p), 'status', '--porcelain', '--untracked-files=no']).strip():
                raise ValueError('dependency checkout is dirty: ' + p.name)
            dependencies[identity] = revision
        if dependencies != expected:
            raise ValueError('actual dependency checkout closure mismatch')
        product = ROOT / 'scratch/arm64-apple-macosx/debug/pinkha-any-host-probe'
        b = read(product)
        result['product'] = {'path': str(product), 'bytes': len(b), 'sha256': sha(b)}
        result['actualDependencies'] = dependencies
        result['status'] = 'PASS_BUILD_NOT_PEER_ACCEPTANCE'
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
        (attempt / 'traceback.txt').write_text(traceback.format_exc())
    finally:
        result['finishedAt'] = time.time()
        p = attempt / 'original.log'
        if p.exists():
            b = read(p)
            result['originalLog'] = {'bytes': len(b), 'sha256': sha(b)}
        if process is not None:
            ps = subprocess.run(['ps', '-axo', 'pid,pgid,command'], capture_output=True, text=True).stdout
            rows = [line for line in ps.splitlines() if len(line.split()) > 1 and line.split()[1] == str(process.pid)]
            result['ownedProcessGroupAbsent'] = not rows
            if rows:
                result['status'] = 'FAIL'
        save(attempt / 'receipt.json', result)
        print(json.dumps({k: result.get(k) for k in ['status', 'error', 'durationSeconds', 'product']}), flush=True)
    return 0 if result['status'] == 'PASS_BUILD_NOT_PEER_ACCEPTANCE' else 1

if __name__ == '__main__':
    raise SystemExit(main())
