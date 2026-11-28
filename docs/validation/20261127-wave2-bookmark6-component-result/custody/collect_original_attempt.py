"""NEW read-only collector; definitions are inert until root supplies a completed job.

This is not a reconstruction/inverse of the unavailable Property4 collector.
Only the ten named originals are opened. No runner import, writes, subprocess,
process queries, signals, filesystem walk, result qualification or slot release.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import os
import stat

ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
ATTEMPT = ROOT / 'attempt1'
FILES = ('actual-dependency-copies.json', 'command.json', 'process.json', 'receipt.json',
         'resource-samples.json', 'source-inputs-after.json', 'source-inputs-before.json',
         'source-inputs-final.json', 'stderr.original.log', 'stdout.original.log')
CONTROLLER = '3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c'
PACKET = '2341bdb226521d368b37f37c402c83b6bb20ae1db6efe4d7f65938198f5f1353'
PRODUCT = '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'
MAX_FILE_BYTES = 2 * 1024**2
MAX_TOTAL_BYTES = 8 * 1024**2
MAX_COMPLETION_BYTES = 256 * 1024
CHUNK_CHARACTERS = 48000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return {name: getattr(value, 'st_' + name) for name in
            ('dev', 'ino', 'mode', 'uid', 'gid', 'nlink', 'size', 'mtime_ns', 'ctime_ns')}


def completed_job(raw):
    # Root supplies exact notifications_get JSON only after the actual job ended.
    # This validates custody input; it neither contacts Sentinel nor grants runtime.
    assert isinstance(raw, bytes) and 0 < len(raw) <= MAX_COMPLETION_BYTES
    value = json.loads(raw)
    assert value.get('ok') is True and isinstance(value.get('job'), dict)
    job = value['job']
    assert job['tool'] == 'script_run' and job['host'] == 'host_299cf75f6b338ecd'
    assert isinstance(job['id'], str) and job['id'].startswith('job_')
    assert job['status'] in ('succeeded', 'failed'), 'Only actual completed success/failure envelopes are admitted'
    assert isinstance(job.get('finished_at'), str) and job['finished_at']
    assert type(job.get('exit_code')) is int and job['timeout_s'] == 360
    assert job.get('output_truncated') is False and isinstance(job.get('output'), str)
    records = []
    for line in job['output'].splitlines():
        try:
            item = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict):
            records.append(item)
    stages = [r for r in records if r.get('root') == str(ROOT) and r.get('packetSHA256') == PACKET]
    summaries = [r for r in records if r.get('receipt') == str(ATTEMPT / 'receipt.json')]
    assert len(stages) <= 1 and len(summaries) <= 1 and (stages or summaries), 'Completed job does not bind this fixed attempt'
    if summaries:
        digest = summaries[0].get('receiptSHA256')
        assert isinstance(digest, str) and len(digest) == 64 and set(digest) <= set('0123456789abcdef')
    return job, summaries[0] if summaries else None


def read_original(name, remaining):
    path = ATTEMPT / name
    row = {'path': name, 'status': 'INCOMPLETE', 'errors': []}
    raw = bytearray()
    fd = None
    try:
        before = path.lstat()
        row['statBefore'] = identity(before)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'Original is not a singly linked regular file'
        assert path.resolve(strict=True) == path, 'Original path is not physical'
        assert before.st_size <= MAX_FILE_BYTES and before.st_size <= remaining, 'Read-size bound exceeded'
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        assert identity(os.fstat(fd)) == row['statBefore'], 'Original changed during open'
        while len(raw) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        row['statAfterFD'] = identity(os.fstat(fd))
        row['statAfterPath'] = identity(path.lstat())
        assert row['statBefore'] == row['statAfterFD'] == row['statAfterPath'], 'Original stat identity changed during read'
        assert len(raw) == before.st_size, 'Original length changed during read'
        row['status'] = 'EXACT_BYTES_READ'
    except Exception as error:
        row['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as error:
                row['status'] = 'INCOMPLETE'
                row['errors'].append({'type': type(error).__name__, 'message': str(error)})
    if fd is not None:
        row.update(bytes=len(raw), sha256=sha(raw), contentBase64=base64.b64encode(raw).decode('ascii'))
        row['contentIsCompleteOriginal'] = row['status'] == 'EXACT_BYTES_READ'
    return row, bytes(raw)


def collect(completed_job_raw, offset=0, expected_gzip_sha256=None):
    """Return one transport chunk; root must explicitly supply actual terminal JSON.

    Later chunks re-read only these same ten paths and require the first chunk's
    gzip hash. Any changed byte/stat identity stops reassembly. No automatic loop.
    """
    job, summary = completed_job(completed_job_raw)  # Before any filesystem read.
    assert type(offset) is int and offset >= 0 and offset % CHUNK_CHARACTERS == 0
    assert offset == 0 or expected_gzip_sha256 is not None
    directories = []
    issues = []
    for path in (ROOT, ATTEMPT):
        try:
            value = path.lstat()
            assert stat.S_ISDIR(value.st_mode) and path.resolve(strict=True) == path, 'Attempt directory is not physical'
            directories.append({'path': str(path), 'before': identity(value)})
        except Exception as error:
            issues.append({'path': str(path), 'type': type(error).__name__, 'message': str(error)})
    rows = []
    contents = {}
    total = 0
    for name in FILES:
        if len(directories) != 2:
            rows.append({'path': name, 'status': 'NOT_READ_DIRECTORY_CUSTODY_FAILED'})
            continue
        row, raw = read_original(name, max(0, MAX_TOTAL_BYTES - total))
        rows.append(row)
        total += len(raw)
        if row['status'] == 'EXACT_BYTES_READ':
            contents[name] = raw
    for row in directories:
        try:
            row['after'] = identity(Path(row['path']).lstat())
            assert row['after'] == row['before'], 'Directory changed during fixed-file collection'
        except Exception as error:
            issues.append({'path': row['path'], 'type': type(error).__name__, 'message': str(error)})
    observation = {'receiptPresentAndComplete': 'receipt.json' in contents,
                   'runnerQualification': 'UNQUALIFIED_BY_COLLECTOR', 'safeToReleaseRuntimeSlotObserved': None}
    if 'receipt.json' in contents:
        try:
            receipt = json.loads(contents['receipt.json'])
            assert receipt['schema'] == 'pinkha-bookmark-six-component/v1'
            assert receipt['controllerSHA256'] == CONTROLLER and receipt['productCommit'] == PRODUCT
            if summary is not None:
                assert sha(contents['receipt.json']) == summary['receiptSHA256'], 'Actual receipt differs from completed-job hash'
            observation.update(receiptSHA256=sha(contents['receipt.json']),
                sourcePinsMatched=True, completedJobReceiptHashMatched=summary is not None,
                runnerReportedStatus=receipt.get('status'), commandExitObserved=receipt.get('processExit'),
                testResultRecorded=receipt.get('testResult'), compilerProofRecorded='compilerInputs' in receipt,
                originalRunnerErrors=receipt.get('errors'),
                safeToReleaseRuntimeSlotObserved=receipt.get('safeToReleaseRuntimeSlot'))
        except Exception as error:
            issues.append({'path': 'receipt.json', 'type': type(error).__name__, 'message': str(error)})
    complete = len(contents) == len(FILES) == 10 and not issues
    bundle = {'schema': 'pinkha-bookmark6-exact-original-attempt-export/v1',
        'collectorIsNewSource': True, 'originalRoot': str(ATTEMPT), 'directories': directories,
        'completedJob': {'sha256': sha(completed_job_raw), 'bytes': len(completed_job_raw),
                         'contentBase64': base64.b64encode(completed_job_raw).decode('ascii'),
                         'id': job['id'], 'status': job['status'], 'exitCode': job['exit_code']},
        'entries': rows, 'collectionIssues': issues, 'outcomeObservation': observation,
        'status': 'ALL_TEN_ORIGINALS_COLLECTED' if complete else 'INCOMPLETE_OR_UNQUALIFIED_CUSTODY',
        'outcomeBoundary': 'File collection is independent of compiler/test outcome and runner qualification; no release decision is made.',
        'mutations': 0, 'processQueries': 0, 'signals': 0, 'atimePreservationClaim': False}
    raw = (json.dumps(bundle, sort_keys=True, separators=(',', ':')) + '\n').encode()
    assert len(raw) <= 13 * 1024**2, 'Bounded transport exceeded'
    compressed = gzip.compress(raw, mtime=0)
    digest = sha(compressed)
    assert expected_gzip_sha256 is None or digest == expected_gzip_sha256, 'Original collection changed between chunks'
    encoded = base64.b64encode(compressed).decode('ascii')
    assert offset < len(encoded)
    return {'schema': 'pinkha-bookmark6-original-export-transfer/v1', 'status': bundle['status'],
        'originalFiles': len(contents), 'expectedFiles': 10, 'observedContentBytes': total,
        'rawBytes': len(raw), 'rawSHA256': sha(raw), 'gzipBytes': len(compressed), 'gzipSHA256': digest,
        'base64Characters': len(encoded), 'offset': offset, 'chunkCharacters': CHUNK_CHARACTERS,
        'data': encoded[offset:offset + CHUNK_CHARACTERS], 'mutations': 0,
        'processQueries': 0, 'signals': 0, 'runtimeQualification': 'NOT_PERFORMED_BY_COLLECTOR'}
