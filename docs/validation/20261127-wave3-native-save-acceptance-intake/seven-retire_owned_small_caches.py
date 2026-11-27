#!/usr/bin/env python3
"""Root-authorized removal of three inactive, regenerable compiler cache leaves."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

INPUT = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs')
MINI = Path('/Users/m1/development/anytype-root-active-20261125/miniapps-producer86-restore3')
SDK = Path('/Users/m1/development/anytype-d-active-20261125/sdk9565-notification')
TARGETS = [MINI / 'derived-producer1/SDKExplicitPrecompiledModules',
           SDK / 'original-suite-attempt1/module-cache', SDK / 'original-suite-attempt1/build/out/v5']
PROOF = INPUT / 'owned-small-caches-readonly1/receipt.json'
PROOF_SHA = 'f84721bd6abc6255435f6bee69c73f99c0ec292c199c2fce125ecb0bce7eec98'
QUALIFIER = INPUT / 'retirement-control1/qualify_archived_products.py'
QUALIFIER_SHA = '4fb4dde0ecadb8bc75437b164e93d36b7f732a4689f7dbd8fd1de177208b59bf'


def require(value, why):
    if not value:
        raise ValueError(why)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return {'path': str(path), 'sha256': digest(path), 'bytes': Path(path).stat().st_size}


def cache_inventory(target, index):
    require(target.is_dir() and not target.is_symlink() and target.resolve() == target,
            'Exact canonical cache directory required')
    files = []
    for path in sorted(target.rglob('*')):
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode), 'Cache symlink is not admitted')
        if stat.S_ISDIR(info.st_mode):
            continue
        require(stat.S_ISREG(info.st_mode), 'Unexpected cache node type')
        if index < 2:
            require(path.suffix in {'.pcm', '.swiftmodule', '.timestamp'}, 'Unexpected compiler cache file type')
        else:
            require(path.relative_to(target).parts[0] in {'records', 'units'}, 'Only compiler index records/units admitted')
        files.append({'path': str(path.relative_to(target)), 'bytes': info.st_size,
                      'mode': stat.S_IMODE(info.st_mode), 'mtimeNS': info.st_mtime_ns, 'links': info.st_nlink})
    return {'root': str(target), 'files': files, 'symlinks': []}


def no_writer(q):
    observed = q.command(['ps', '-axo', 'pid=,ppid=,etime=,command='])
    matches = []
    for line in observed['stdout'].splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) >= 4 and int(fields[0]) != os.getpid() and any(str(p) in line for p in
                [*TARGETS, MINI / 'derived-producer1', SDK / 'original-suite-attempt1']):
            matches.append(line)
    require(observed['exitCode'] == 0 and not matches, 'A process uses an admitted cache leaf')
    handles = [q.command(['lsof', '-nP', '+D', str(p)]) for p in TARGETS]
    require(all(r['exitCode'] == 1 and r['stdout'] == r['stderr'] == '' for r in handles),
            'An admitted cache has an open handle')
    return {'observedAt': time.time(), 'processMatches': matches, 'openHandles': handles}


def protected(q):
    module = q.archiver()
    result = {}
    for name, root in [('original86Products', MINI / 'derived-producer1/Build/Products'),
                       ('original9565Products', SDK / 'original-suite-attempt1/build/out/Products'),
                       ('original9565Source', SDK / 'source')]:
        module.ROOT = root
        inventory = module.manifest()
        result[name] = {'root': str(root), 'nodes': len(inventory['entries']),
                        'fullTypeModeLinkTimeXattrContentSHA256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()}
    git = lambda args: q.command(['git', '--no-replace-objects', '-C', str(MINI / 'source'), *args])
    result['source86HEAD'] = git(['rev-parse', 'HEAD'])
    require(result['source86HEAD']['exitCode'] == 0 and
            result['source86HEAD']['stdout'].strip() == '86a6dde354947be9329fe1e8f4d45a433fe488c4', 'Original86 source differs')
    for label, args in [('source86Status', ['status', '--porcelain', '--untracked-files=all']),
                        ('source86TrackedDiff', ['diff', 'HEAD', '--'])]:
        raw = git(args)
        require(raw['exitCode'] == 0, 'Original86 source observation failed')
        result[label] = {'exitCode': 0, 'stdoutSHA256': hashlib.sha256(raw['stdout'].encode()).hexdigest()}
    for p in [MINI / 'producer2/build.command.json', SDK / 'materialization.json',
              SDK / 'original-suite-attempt1/qualified-original-with-xml.json',
              SDK / 'original-suite-attempt1/result.json']:
        result[str(p)] = q.file(p)
    result['frozenCurrentApp'] = q.source_identity()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-admission', type=Path, required=True)
    parser.add_argument('--root-admission-sha256', required=True)
    args = parser.parse_args()
    require(digest(args.root_admission) == args.root_admission_sha256, 'Exact root admission required')
    admission = json.loads(args.root_admission.read_text())
    require(admission['schema'] == 'pinkha-root-three-owned-cache-leaves-retirement-v1'
            and admission['readyForRetirement'] is True, 'Root has not admitted this cleanup')
    require(admission['controllerSHA256'] == digest(__file__) and admission['exactScope'] == list(map(str, TARGETS)),
            'Exact controller and three-cache scope required')
    require(admission['originalReadOnlyReceiptSHA256'] == digest(PROOF) == PROOF_SHA, 'Original cache observation changed')
    require(admission['SDKOwnerNoCurrentOrPlannedReuseConfirmed'] is True, 'SDK owner reuse disposition required')
    require(digest(QUALIFIER) == QUALIFIER_SHA and shutil.rmtree.avoids_symlink_attacks, 'Original helper/FD-safe deletion required')
    spec = importlib.util.spec_from_file_location('original_product_manifest_helper', QUALIFIER)
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)
    proof = json.loads(PROOF.read_text())
    require([x['path'] for x in proof['caches']] == list(map(str, TARGETS)), 'Recorded cache scope changed')
    out = INPUT / 'owned-small-caches-retirement1'
    out.mkdir(exist_ok=False)
    result = {'schema': 'pinkha-three-owned-cache-leaves-retirement-result-v1', 'status': 'FAIL',
              'startedAt': time.time(), 'controllerSHA256': digest(__file__),
              'rootAdmission': {'path': str(args.root_admission), 'sha256': args.root_admission_sha256},
              'exactScope': list(map(str, TARGETS)), 'removedPaths': [], 'builds': 0, 'tests': 0}
    try:
        result['ownersBefore'] = write(out / 'owners-before.json', no_writer(q))
        for index, row in enumerate(proof['caches']):
            inventory = row['inventory']
            require(digest(inventory['path']) == inventory['sha256'], 'Original cache file inventory changed')
            require(cache_inventory(TARGETS[index], index) == json.loads(Path(inventory['path']).read_text()),
                    'Cache nodes changed since scoped qualification')
        before = protected(q)
        result['protectedBefore'] = write(out / 'protected-before.json', before)
        result['ownersImmediatelyBefore'] = no_writer(q)
        require(digest(args.root_admission) == args.root_admission_sha256, 'Admission changed during qualification')
        result['freeBytesBefore'] = shutil.disk_usage('/System/Volumes/Data').free
        write(out / 'retirement-admitted.json', result)
        for index, root in enumerate(TARGETS):
            require(root.resolve(strict=True) == root and root.is_dir() and not root.is_symlink(), 'Cache root changed')
            shutil.rmtree(root)
            require(not root.exists() and not root.is_symlink(), 'Cache root remains')
            result['removedPaths'].append(str(root))
            write(out / ('removed-' + str(index + 1) + '.json'), {'path': str(root), 'observedAt': time.time()})
        after = protected(q)
        result['protectedAfter'] = write(out / 'protected-after.json', after)
        require(before == after, 'Protected source/Products/original evidence changed')
        result['freeBytesAfter'] = shutil.disk_usage('/System/Volumes/Data').free
        result['observedGlobalFreeDeltaBytes'] = result['freeBytesAfter'] - result['freeBytesBefore']
        result['interpretation'] = 'Global observed free-space delta only; no COW or unique-physical-reclamation claim.'
        result['status'] = 'PASS_THREE_OWNED_COMPILER_CACHE_LEAVES_REMOVED_ORIGINALS_PRESERVED'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    ref = write(out / 'receipt.json', result)
    print(json.dumps({'receipt': ref, 'result': result}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
