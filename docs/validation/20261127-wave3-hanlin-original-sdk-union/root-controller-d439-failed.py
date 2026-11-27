#!/usr/bin/env python3
"""Create only the reviewed, pure Hanlin source union in a new owned worktree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

MIRROR = '/mnt/development/projects/git-mirrors/hanlin-ai.git'
ROOT = '/mnt/development/projects/worktrees/hanlin-pinkha-original-sdk-union-20261127'
BRANCH = 'codex/pinkha-original-sdk-union-20261127'
FOREIGN = '/mnt/development/projects/worktrees/hanlin-miniapps-widget-recovery-os-20261127'
BASE = '6a6638c314fe04c481eb0a2e29fbeaaafcbb0908'
LEFT = '45d5d90512c304d3457774b185741b7ef7d801db'
RIGHT = '866d2d3c60525e32eae27564869e6dba024e625c'
EXPECTED_TREE = '14e860ce3f7d2b8623085f16d99d34b8b347a48c'
REVIEW_SHA256 = '41bc26ccbea8ad4f6ac504cec19357cd9f8b5894f4bdb3c7921dcf30360d793d'
EXPECTED_PACKAGE_TREES = {
    'HanlinAgentSDK': 'bbe6a0e4387f3f33d6592e24c1927182a1aceb22',
    'HanlinPlatform': 'db6e9533242f08bb1bb7accdf6970a436aa953d1',
    'HanlinPresentationSDK': '3096459e793e32293ba145cb1f595181ad0d38a5',
    'HanlinAppExtensionsSDK': '686aad16f099b5c75b6ef84073a0a10557281628',
    'HanlinNativeScriptRuntime': '14373dc81171600079e458087872d4e8ea7bbc1c',
    'HanlinMiniAppsBridge': '98ef5d2b47c03f4ea98319a851abae183f500a40',
}
SELECTED = [
    'AGENTS.md', 'PROJECT_AGENT_GUIDANCE.md', 'PROJECT_BOARD.md',
    'docs/ai-team/', 'docs/continuation-20261117/OWNER_AUTHORIZATION_20261118.md',
    '.agents/roles/', 'Packages/HanlinAgentSDK/', 'Packages/HanlinPlatform/',
    'Packages/HanlinPresentationSDK/', 'Packages/HanlinAppExtensionsSDK/',
]
RECEIPT = Path('/tmp/pinkha-root-hanlin-original-sdk-union-20261127.json')
PRE = ['sudo', '-n', '-u', 'chatgpt-agent']
GIT_OPTIONS = ['-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com']
state = {'schema': 'pinkha-original-hanlin-pure-union-v1', 'startedAt': time.time(),
         'sourceOnly': True, 'runtimeAcceptance': 'NOT_RUN', 'worktree': ROOT,
         'branch': BRANCH, 'base': BASE, 'parents': [LEFT, RIGHT],
         'expectedTree': EXPECTED_TREE, 'independentReviewSHA256': REVIEW_SHA256,
         'steps': [], 'status': 'STARTING'}
receipt_claimed = False

def digest(data):
    return hashlib.sha256(data).hexdigest()

def persist():
    fd, name = tempfile.mkstemp(prefix=RECEIPT.name + '.', suffix='.tmp', dir=RECEIPT.parent)
    temp = Path(name)
    with os.fdopen(fd, 'wb') as f:
        f.write((json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode())
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, RECEIPT)

def run(args, *, data=None, allowed=(0,), record=True, timeout=90):
    start = time.monotonic()
    p = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if record:
        state['steps'].append({'argv': args, 'returncode': p.returncode,
                               'elapsedSeconds': round(time.monotonic() - start, 6),
                               'stdout': p.stdout.decode('utf-8', 'replace'),
                               'stderr': p.stderr.decode('utf-8', 'replace')})
        persist()
    if p.returncode not in allowed:
        raise RuntimeError(f'command exit {p.returncode}: {args}')
    return p

def git(path, *args, **kw):
    return run(PRE + ['git'] + GIT_OPTIONS + ['-C', path] + list(args), **kw)

def text(path, *args):
    return git(path, *args, record=False).stdout.decode().strip()

def leaves(ref):
    raw = git(MIRROR, 'ls-tree', '-r', '-z', ref, record=False).stdout
    entries = {}
    for row in raw.split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            entries[path.decode()] = meta.decode()
    return entries

def status(path):
    return {'head': text(path, 'rev-parse', 'HEAD'),
            'status': git(path, '--no-optional-locks', 'status', '--porcelain=v1', '--untracked-files=all', record=False).stdout.decode()}

def selected(path):
    return any(path == x or (x.endswith('/') and path.startswith(x)) for x in SELECTED)

def main():
    global receipt_claimed
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-sha256', required=True)
    args = parser.parse_args()
    actual = digest(Path(__file__).read_bytes())
    assert actual == args.self_sha256, 'controller bytes differ'
    state['controllerSHA256'] = actual
    fd = os.open(RECEIPT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    receipt_claimed = True
    os.close(fd)
    persist()
    assert not Path(ROOT).exists(), 'new worktree already exists; inspect, never overwrite'
    assert git(MIRROR, 'show-ref', '--verify', '--quiet', 'refs/heads/' + BRANCH, allowed=(0, 1)).returncode == 1
    remote = git(MIRROR, '-c', 'credential.helper=!gh auth git-credential', 'ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH)
    assert not remote.stdout.strip(), 'remote branch already exists; inspect'
    assert text(MIRROR, 'merge-base', LEFT, RIGHT) == BASE
    source = {ref: leaves(ref) for ref in [BASE, LEFT, RIGHT]}
    all_paths = set().union(*[set(x) for x in source.values()])
    changed_left = {p for p in all_paths if source[BASE].get(p) != source[LEFT].get(p)}
    changed_right = {p for p in all_paths if source[BASE].get(p) != source[RIGHT].get(p)}
    assert not changed_left.intersection(changed_right), 'reviewed branches now overlap'
    assert (len(changed_left), len(changed_right)) == (12, 221)
    union = dict(source[LEFT])
    for path in changed_right:
        if path in source[RIGHT]:
            union[path] = source[RIGHT][path]
        else:
            union.pop(path, None)
    assert len(union) == 17827
    state['changedLeft'] = sorted(changed_left)
    state['changedRight'] = sorted(changed_right)
    state['expectedLeafCount'] = len(union)
    blobs = [(path, meta.split()[2]) for path, meta in union.items() if selected(path)]
    sizes = git(MIRROR, 'cat-file', '--batch-check=%(objectname) %(objectsize)',
                data=('\n'.join(sha for _, sha in blobs) + '\n').encode(), record=False).stdout.decode().splitlines()
    assert len(sizes) == len(blobs)
    logical = rounded = 0
    for (_, sha), line in zip(blobs, sizes):
        got, count = line.split()
        assert sha == got
        n = int(count)
        logical += n
        rounded += ((n + 4095) // 4096) * 4096
    state['sparseBudget'] = {'fileCount': len(blobs), 'logicalBytes': logical,
                            'rounded4KiBBytes': rounded, 'metadataAllowanceBytes': 64 * 1024**2,
                            'remainingFloorBytes': 512 * 1024**2, 'patterns': SELECTED}
    state['freeBefore'] = {'root': shutil.disk_usage('/').free,
                           'development': shutil.disk_usage('/mnt/development').free}
    assert state['freeBefore']['development'] >= rounded + 64 * 1024**2 + 512 * 1024**2, 'measured sparse checkout budget unavailable'
    assert state['freeBefore']['root'] >= 128 * 1024**2, 'receipt/temporary space unavailable'
    state['foreignObservedBefore'] = status(FOREIGN)
    state['status'] = 'PREFLIGHT_PASS'
    persist()
    print(json.dumps({k: state[k] for k in ['status', 'sparseBudget', 'freeBefore']}), flush=True)
    git(MIRROR, 'worktree', 'add', '--no-checkout', '-b', BRANCH, ROOT, LEFT)
    patterns = ''.join('/' + x + ('**' if x.endswith('/') else '') + '\n' for x in SELECTED)
    git(ROOT, 'sparse-checkout', 'set', '--no-cone', '--stdin', data=patterns.encode())
    # --no-checkout leaves an unborn index; materialize only this new owned tree.
    git(ROOT, 'read-tree', '-m', '-u', LEFT)
    assert text(ROOT, 'rev-parse', 'HEAD') == LEFT
    assert not git(ROOT, 'status', '--porcelain=v1', '--untracked-files=all', record=False).stdout
    state['sparseFreeAfterCheckout'] = shutil.disk_usage('/mnt/development').free
    assert state['sparseFreeAfterCheckout'] >= 512 * 1024**2
    git(ROOT, 'merge', '--no-ff', '--no-commit', RIGHT)
    assert not git(ROOT, 'ls-files', '-u', record=False).stdout, 'merge conflict: leave intact for review'
    tree = text(ROOT, 'write-tree')
    assert tree == EXPECTED_TREE, f'unexpected merged tree {tree}'
    assert leaves(tree) == union, 'full union differs from independent per-path projection'
    state['actualTree'] = tree
    state['packageTrees'] = {}
    for package, expected in EXPECTED_PACKAGE_TREES.items():
        got = text(ROOT, 'rev-parse', tree + ':Packages/' + package)
        assert got == expected, f'package source drift: {package}'
        state['packageTrees'][package] = got
    state['unionEntriesSHA256'] = digest(git(ROOT, 'ls-tree', '-r', '-z', tree, record=False).stdout)
    state['sparseFilesAfterMerge'] = len([p for p in Path(ROOT).rglob('*') if p.is_file()])
    state['sourceValidation'] = 'PASS: all 17827 leaf entries and all six package trees equal reviewed union'
    state['status'] = 'REVIEWED_MERGE_STAGED'
    persist()
    message = ('Merge published MiniApps fixes with original SDK cancellation and presentation retention\n\n'
               'Pure source union of 45d5d905 and 866d2d3c; preserve all 12 and 221 disjoint changed paths.\n'
               'Independent review SHA256: ' + REVIEW_SHA256 + '\n'
               'Exact full tree: ' + EXPECTED_TREE + '\n'
               'This source checkpoint does not assert fresh SDK, paired Host, consumer, or TestFlight acceptance.\n')
    git(ROOT, 'commit', '-F', '-', data=message.encode())
    commit = text(ROOT, 'rev-parse', 'HEAD')
    assert text(ROOT, 'show', '-s', '--format=%P', commit).split() == [LEFT, RIGHT]
    assert text(ROOT, 'rev-parse', commit + '^{tree}') == EXPECTED_TREE
    assert not git(ROOT, 'status', '--porcelain=v1', '--untracked-files=all', record=False).stdout
    state['commit'] = commit
    state['status'] = 'COMMITTED_NOT_YET_PUBLISHED'
    persist()
    git(ROOT, '-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential',
        'push', 'origin', commit + ':refs/heads/' + BRANCH)
    readback = git(ROOT, '-c', 'credential.helper=!gh auth git-credential', 'ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH).stdout.decode().split()
    assert readback == [commit, 'refs/heads/' + BRANCH], 'remote readback mismatch'
    state['remoteReadback'] = readback
    state['foreignObservedAfter'] = status(FOREIGN)
    state['foreignObservationUnchanged'] = state['foreignObservedBefore'] == state['foreignObservedAfter']
    state['foreignWritesPerformed'] = False
    state['freeAfter'] = {'root': shutil.disk_usage('/').free,
                          'development': shutil.disk_usage('/mnt/development').free}
    state['completedAt'] = time.time()
    state['status'] = 'PASS_SOURCE_UNION_PUBLISHED'
    persist()
    print(json.dumps({'status': state['status'], 'commit': commit, 'tree': EXPECTED_TREE,
                      'branch': BRANCH, 'receipt': str(RECEIPT),
                      'receiptSHA256': digest(RECEIPT.read_bytes()),
                      'freeAfter': state['freeAfter'], 'runtimeAcceptance': state['runtimeAcceptance']}), flush=True)

if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        state['status'] = 'FAILED_PRESERVED_FOR_INSPECTION'
        state['failure'] = str(exc)
        if receipt_claimed:
            persist()
        print(json.dumps({'status': state['status'], 'failure': str(exc), 'receipt': str(RECEIPT)}), flush=True)
        raise
