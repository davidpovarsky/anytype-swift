#!/usr/bin/env python3
"""Root-only retirement of seven exact files after verified private offhost backup."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import time

INPUT = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs')
HELPER = Path('/Users/m1/sentinelx/uploads/pinkha-wave3-preserve-seven-archives-reference-fixed-20261127.py')
HELPER_SHA = 'f953ab341db150651c93ae46f17703459e34455cdf4015d1b5817554e0cca405'
MANIFEST = INPUT / 'seven-historical-archives-preservation2/manifest-before.json'
MANIFEST_SHA = 'd6575b864418cd7b8fdde83776a0fdb4138c70ffb252f81f855fa96c7d7e8c86'
OBSERVATION = MANIFEST.parent / 'observation.json'
OBSERVATION_SHA = '9405861bd769db68cef51fc02318756560e91bd63629e31fbf8326f623c02abd'
SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
SOURCE_SHA = '8f2c11713fb8a40ae13444104723666ffef68afe'

def require(value, why):
    if not value:
        raise ValueError(why)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def exact_json(ref):
    require(digest(ref['path']) == ref['sha256'], 'Original bound receipt bytes changed')
    return json.loads(Path(ref['path']).read_text())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-admission', type=Path, required=True)
    parser.add_argument('--root-admission-sha256', required=True)
    args = parser.parse_args()
    require(digest(args.root_admission) == args.root_admission_sha256, 'Exact root admission required')
    admission = json.loads(args.root_admission.read_text())
    require(admission['schema'] == 'pinkha-root-seven-verified-archive-files-retirement-v1'
            and admission['readyForRetirement'] is True, 'Root has not approved archive retirement')
    require(admission['controllerSHA256'] == digest(__file__) and admission['restorationOnDemandAccepted'] is True,
            'Exact controller and original-path restore disposition required')
    require(digest(HELPER) == HELPER_SHA and digest(MANIFEST) == MANIFEST_SHA
            and digest(OBSERVATION) == OBSERVATION_SHA, 'Original preservation proof changed')
    spec = importlib.util.spec_from_file_location('original_archive_preserver', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    original = json.loads(MANIFEST.read_text())
    require(admission['exactScope'] == [str(p) for p, _ in helper.SCOPE], 'Only seven exact original files are admitted')
    backup = exact_json(admission['offhostOriginalReceipt'])
    qualification = exact_json(admission['offhostVerification'])
    require(backup['status'] == 'PASS_SEVEN_ORIGINAL_ARCHIVES_OFFHOST_HASH_METADATA_PROTECTED_NOT_RETIRED'
            and backup['sourceManifestSHA256'] == MANIFEST_SHA and len(backup['files']) == 7,
            'Complete exact offhost copy required')
    require(qualification['status'] == 'PASS_FRESH_PRIVATE_OFFHOST_REHASH_NOT_RETIRED'
            and qualification['originalBackupReceiptSHA256'] == admission['offhostOriginalReceipt']['sha256'],
            'Independent complete offhost readback required')
    require(0 <= time.time() - qualification['observedAtUnix'] <= 1800,
            'Offhost readback is not fresh for this retirement')
    require(len(qualification['files']) == 7 and qualification['privateACLMatches'] is True,
            'Exact private offhost scope required')
    for index, row in enumerate(original['files']):
        b, v = backup['files'][index], qualification['files'][index]
        require(b['index'] == index and b['originalPath'] == row['path']
                and b['bytes'] == row['bytes'] and b['sha256'] == row['sha256']
                and v['path'] == b['destinationPath'] and v['bytes'] == row['bytes'] and v['sha256'] == row['sha256'],
                'Offhost archive identity differs from original')
        stream = helper.AUDIT / ('stream-' + str(index + 1) + '.json')
        require(digest(stream) == b['sourceStreamReceipt']['originalMacSHA256'], 'Original transfer receipt changed')
        sr = json.loads(stream.read_text())
        require(sr['status'] == 'PASS_EXACT_STREAM_ORIGINAL_BYTES_AND_METADATA_UNCHANGED'
                and sr['sourceAfter'] == row, 'Original post-transfer metadata differs')
    out = INPUT / 'seven-archive-files-retirement1'
    out.mkdir(mode=0o700, exist_ok=False)
    result = {'schema': 'pinkha-seven-archive-files-retirement-result-v1', 'status': 'FAIL',
              'startedAt': time.time(), 'controllerSHA256': digest(__file__), 'removedFiles': [],
              'rootAdmission': {'path': str(args.root_admission), 'sha256': args.root_admission_sha256},
              'offhostOriginalReceipt': admission['offhostOriginalReceipt'],
              'offhostVerification': admission['offhostVerification'], 'restoration': admission['restoration']}
    try:
        result['ownersBefore'] = helper.owners()
        result['referencesBefore'] = helper.references()
        require(not result['referencesBefore']['matches'], 'Current controller references an original archive')
        git = lambda arguments: helper.command(['git', '--no-replace-objects', '-C', str(SOURCE), *arguments])
        result['currentSource'] = git(['rev-parse', 'HEAD'])
        result['currentSourceStatus'] = git(['status', '--porcelain', '--untracked-files=all'])
        require(result['currentSource']['exitCode'] == 0 and result['currentSource']['stdout'].strip() == SOURCE_SHA
                and result['currentSourceStatus']['exitCode'] == 0 and not result['currentSourceStatus']['stdout'],
                'Frozen current source changed')
        siblings_before = {}
        targets = {str(p) for p, _ in helper.SCOPE}
        for parent in sorted({p.parent for p, _ in helper.SCOPE}):
            for path in sorted(parent.iterdir()):
                if str(path) not in targets and path.is_file() and not path.is_symlink():
                    siblings_before[str(path)] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        result['originalSiblingEvidenceBefore'] = helper.write(out / 'protected-sibling-evidence-before.json', siblings_before)
        for index, (path, size) in enumerate(helper.SCOPE):
            require(helper.full_row(path, size) == original['files'][index], 'Original archive changed since transfer')
        result['ownersImmediatelyBefore'] = helper.owners()
        require(digest(args.root_admission) == args.root_admission_sha256, 'Root admission changed')
        result['freeBytesBefore'] = shutil.disk_usage('/System/Volumes/Data').free
        helper.write(out / 'admitted.json', result)
        for index, (path, _) in enumerate(helper.SCOPE):
            row = original['files'][index]
            require(path.parent.resolve(strict=True) == path.parent, 'Original parent changed')
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
                with os.fdopen(fd, 'rb') as stream:
                    observed = os.fstat(stream.fileno())
                    require(stat.S_ISREG(observed.st_mode) and observed.st_dev == row['device']
                            and observed.st_ino == row['inode'] and observed.st_nlink == 1
                            and observed.st_size == row['bytes'] and observed.st_mtime_ns == row['mtimeNS']
                            and observed.st_ctime_ns == row['ctimeNS']
                            and hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'],
                            'Original open file identity changed immediately before unlink')
                    current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
                    require((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns)
                            == (observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns),
                            'Directory entry changed before unlink')
                    os.unlink(path.name, dir_fd=directory)
                require(not path.exists() and not path.is_symlink(), 'Exact original path remains')
            finally:
                os.close(directory)
            result['removedFiles'].append({'path': str(path), 'sha256': row['sha256'], 'bytes': row['bytes']})
            helper.write(out / ('removed-' + str(index + 1) + '.json'), result['removedFiles'][-1])
        siblings_after = {path: {'bytes': Path(path).stat().st_size, 'sha256': digest(path)} for path in siblings_before}
        result['originalSiblingEvidenceAfter'] = helper.write(out / 'protected-sibling-evidence-after.json', siblings_after)
        require(siblings_before == siblings_after, 'Original sibling evidence changed')
        require(git(['rev-parse', 'HEAD']) == result['currentSource']
                and git(['status', '--porcelain', '--untracked-files=all']) == result['currentSourceStatus'],
                'Frozen source changed during retirement')
        result['freeBytesAfter'] = shutil.disk_usage('/System/Volumes/Data').free
        result['observedGlobalFreeDeltaBytes'] = result['freeBytesAfter'] - result['freeBytesBefore']
        result['interpretation'] = 'Observed global delta only, not a claim about unique APFS reclamation.'
        result['status'] = 'PASS_SEVEN_EXACT_ARCHIVE_FILES_RETIRED_WITH_VERIFIED_PRIVATE_OFFHOST_ORIGINALS'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    receipt = helper.write(out / 'receipt.json', result)
    print(json.dumps({'receipt': receipt, 'result': result}))
    return 0 if result['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())
