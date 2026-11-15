"""Strict component-store process pairing; never builds/downloads or proves iOS/UI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from uuid import uuid4

PIN = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
PATCHES = {'old': 'fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077',
           'new': '5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2'}
INVENTORIES = {'old': '952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14',
               'new': 'f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7'}
PROTOCOL = 'pinkha-t5-pair-store-v1'
METHOD = 'TestTorahCompatibilityPairPhase'
PHASES = [('old-create', 'old'), ('new-upgrade', 'new'), ('old-edit', 'old'), ('new-recover', 'new')]
RESERVE = 8 * 1024**3
SCOPE = 'component Go spaceindex test binaries; synthetic Details only; no packaged iOS/Swift/RPC export/UI proof'
EXECUTION_PLATFORM = os.name


def digest(path, normalize=False):
    h = hashlib.sha256()
    if normalize:
        return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def contains(path, value):
    needle = value.encode()
    previous = b''
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            if needle in previous + chunk:
                return True
            previous = chunk[-len(needle):]
    return False


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True, timeout=15).strip()


def verify_artifact(role, entry):
    require(all(Path(entry[key]).is_absolute() for key in ['binary', 'source', 'inventory', 'patch']),
            'Absolute artifact/source paths required')
    binary = Path(entry['binary']).resolve(strict=True)
    source = Path(entry['source']).resolve(strict=True)
    inventory_path = Path(entry['inventory']).resolve(strict=True)
    patch = Path(entry['patch']).resolve(strict=True)
    fixture = Path(__file__).with_name('pair_phase_test.go')
    require(digest(inventory_path, True) == INVENTORIES[role], 'Wrong immutable source inventory bytes')
    inventory = json.loads(inventory_path.read_text(encoding='utf8'))
    expected = PATCHES[role]
    require(inventory['heart_sha'] == PIN and inventory['patch_sha256'] == expected, 'Wrong revision inventory')
    require(digest(patch, True) == expected, 'Wrong patch bytes')
    require(git(source, 'rev-parse', 'HEAD') == PIN, 'Wrong source HEAD')
    require(digest(binary) == entry['binary_sha256'], 'Wrong binary bytes')
    fixture_sha = digest(fixture, True)
    require(entry['fixture_sha256'] == fixture_sha, 'Wrong pair fixture source')
    marker = 'pinkha-native-derived-v1-' + expected
    feature_marker = 'pinkha-native-t5-lookup-v1-' + PATCHES['new']
    require(contains(binary, marker) and contains(binary, fixture_sha) and contains(binary, PROTOCOL),
            'Missing hash-bound runtime/fixture markers')
    require(contains(binary, feature_marker) == (role == 'new'), 'Wrong separate runtime capability marker')
    capability = inventory.get('features', {}).get('t5_related_lookup', 0)
    require(capability == (1 if role == 'new' else 0), 'Wrong source capability')
    actual = {}
    for item in inventory['files']:
        relative = Path(item['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe inventory path')
        target = (source / relative).resolve(strict=True)
        require(target.is_relative_to(source), 'Inventory escaped checkout')
        actual[item['path']] = digest(target, True)
        require(actual[item['path']] == item['after_sha256'], 'Source inventory differs: ' + item['path'])
    changed = set(git(source, 'diff', '--name-only', 'HEAD').splitlines())
    untracked = set(git(source, 'ls-files', '--others', '--exclude-standard').splitlines())
    require((changed | untracked).issubset(actual), 'Unexpected source outside revision inventory')
    return dict(binary=str(binary), binary_sha256=entry['binary_sha256'], source=str(source),
                heart_sha=PIN, patch_sha256=expected, fixture_sha256=fixture_sha,
                inventory_sha256=digest(inventory_path, True), source_hashes=actual,
                marker=marker, runtime_capability=capability)


def validate_phase(report, phase, role, identity, nonce, database, pid, baseline, previous):
    require(report.get('protocol') == PROTOCOL and report.get('phase') == phase, 'Wrong phase/protocol')
    require(report.get('nonce') == nonce and report.get('pid') == pid, 'Stale or foreign process report')
    for key in ['heart_sha', 'patch_sha256', 'fixture_sha256', 'runtime_capability']:
        require(report.get(key) == identity[key], 'Phase runtime identity mismatch: ' + key)
    require(report.get('database_path') == str(database) and report.get('space_id') == 'test', 'Wrong database/Space')
    require(report.get('closed') is True and report.get('test_passed') is True, 'Native handles/test not closed/passed')
    require(report.get('export_status') == 'NOT_RUN_COMPONENT_NO_RPC', 'Component proof misstates export scope')
    require(report.get('swift_pairing_status') == 'NOT_RUN', 'Component proof misstates Swift scope')
    require(report.get('required_swift_fallback') == 'UNAVAILABLE_FROM_RUNTIME_CAPABILITY', 'Missing stale-capability fallback contract')
    canonical = report.get('canonical_sha256', {})
    public = report.get('public_sha256', {})
    require(set(canonical) == {'pair-manifest', 'pair-document', 'pair-block'}, 'Missing canonical sentinels')
    require(set(public) == {'pair-document', 'pair-block'}, 'Missing public sentinels')
    hashes = list(canonical.values()) + list(public.values()) + list(report.get('cache_sha256', {}).values())
    require(all(isinstance(h, str) and len(h) == 64 and set(h) <= set('0123456789abcdef') for h in hashes), 'Invalid sentinel digest')
    require(set(report.get('cache_sha256', {})) == {'pair-document', 'pair-block'}, 'Missing cache sentinels')
    if baseline:
        require(canonical == baseline['canonical_sha256'] and public == baseline['public_sha256'], 'Canonical/public data changed')
    if previous:
        require(report.get('recovery_complete') is True and report.get('recomputed', 0) >= 2, 'Revision cache recovery not observed')
        require(all(report['cache_sha256'][key] != previous['cache_sha256'][key] for key in public), 'Revision cache proof did not change')
    require(report.get('public_members') == ['pair-document'], 'Public projection widened')
    require(report.get('ready') == {'pair-document': True, 'pair-block': True}, 'Readiness lost')
    versions = report.get('private_versions')
    require(isinstance(versions, dict) and set(versions) == set(public), 'Missing observed private versions')
    if role == 'new':
        require(versions == {'pair-document': 1, 'pair-block': 1}, 'New private capability not rebuilt')
        require(all(type(value) is int for value in versions.values()), 'Private versions must be integers')
        require(report.get('private_query_status') == 'EXECUTED', 'New private query not executed')
        require(report.get('private_members') == ['pair-block', 'pair-document'] and report.get('private_index_used') is True,
                'New private membership/index not proven')
    else:
        require(report.get('private_query_status') == 'NOT_ATTEMPTED_RUNTIME_UNAVAILABLE', 'Old runtime queried expanded feature')
        require(report.get('private_members') == [] and report.get('private_index_used') is False,
                'Old runtime claimed an expanded query result')
        # Persisted version=1 may survive a downgrade. It MUST NOT establish runtime capability.
        require(report.get('runtime_capability') == 0, 'Stale row granted old runtime capability')


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_process(command, env, log, directory, deadline=180):
    require(EXECUTION_PLATFORM == 'posix', 'Execution requires POSIX process-group isolation; Windows control tests only')
    with log.open('xb') as stream:
        child = subprocess.Popen(command, env=env, cwd=directory, stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        started = time.monotonic()
        complete = False
        try:
            while child.poll() is None:
                require(time.monotonic() - started < deadline, 'Phase wall-clock deadline exceeded')
                require(shutil.disk_usage(directory).free >= RESERVE, 'Disk reserve below 8 GiB')
                time.sleep(0.25)
            require(child.wait() == 0, 'Native phase process failed')
            require(not group_exists(child.pid), 'Phase left descendant processes alive')
            complete = True
            return child.pid
        finally:
            if not complete:
                stop_group(child.pid)
            child.wait()


def execute(manifest, workspace):
    require(EXECUTION_PLATFORM == 'posix', 'Actual execution requires POSIX; no native execution on this Windows host')
    config = json.loads(manifest.read_text(encoding='utf8'))
    require(config.get('schema') == 1, 'Unknown pair manifest')
    identities = {role: verify_artifact(role, config[role]) for role in ['old', 'new']}
    require(identities['old']['binary'] != identities['new']['binary'], 'Two distinct revision binaries required')
    database = (workspace / 'database').resolve()
    database.mkdir()
    reports = []
    for phase, role in PHASES:
        require(shutil.disk_usage(workspace).free >= RESERVE, 'Disk reserve below 8 GiB')
        current = verify_artifact(role, config[role])
        require(current == identities[role], 'Artifact/source changed during pairing')
        nonce = str(uuid4())
        report_path = workspace / (phase + '.json')
        env = dict(os.environ, PINKHA_PAIR_ROOT=str(database), PINKHA_PAIR_REPORT=str(report_path),
                   PINKHA_PAIR_PHASE=phase, PINKHA_PAIR_ROLE=role, PINKHA_PAIR_NONCE=nonce,
                   PINKHA_PAIR_FIXTURE_SHA=current['fixture_sha256'], PINKHA_PAIR_PATCH_SHA=current['patch_sha256'],
                   PINKHA_PAIR_OWNER_TOKEN=(workspace / 'ownership.json').read_text(encoding='utf8'))
        command = [current['binary'], '-test.run', '^' + METHOD + '$', '-test.count=1', '-test.v', '-test.timeout=150s']
        log = workspace / (phase + '.log')
        pid = run_process(command, env, log, workspace)
        output = log.read_text(encoding='utf8', errors='replace')
        require(('--- PASS: ' + METHOD + ' ') in output and output.count('--- PASS:') == 1
                and '--- SKIP:' not in output and '--- FAIL:' not in output,
                'Missing named passing test or unexpected skip/failure')
        report = json.loads(report_path.read_text(encoding='utf8'))
        validate_phase(report, phase, role, current, nonce, database, pid,
                       reports[0] if reports else None, reports[-1] if reports else None)
        reports.append(report)
    require(all(verify_artifact(role, config[role]) == identities[role] for role in identities), 'Inputs changed after execution')
    return dict(status='COMPONENT_STORE_PAIR_PASS', scope=SCOPE, phase_reports=reports, identities=identities,
                export_status='NOT_RUN_COMPONENT_NO_RPC', swift_pairing_status='NOT_RUN',
                full_F10='NOT_PROVEN', client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF')


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path, help='Fresh nonexistent disposable directory; never reused/deleted')
    args = parser.parse_args(argv)
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=False, exist_ok=False)
    owner = dict(protocol=PROTOCOL, run_id=str(uuid4()), synthetic_only=True)
    (workspace / 'ownership.json').write_text(json.dumps(owner), encoding='utf8')
    result = workspace / 'result.json'
    receipt = dict(status='FAIL', reason='ATTEMPT_NOT_COMPLETED', scope=SCOPE, full_F10='NOT_PROVEN',
                   started_at=datetime.now(timezone.utc).isoformat(),
                   client_enablement='DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF', **owner)
    with result.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, indent=2)
    try:
        receipt.update(execute(args.manifest.resolve(strict=True), workspace))
        receipt['reason'] = 'COMPONENT_SEQUENCE_COMPLETED'
    except Exception as error:
        receipt.update(status='FAIL', reason=type(error).__name__, error=str(error))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    result.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: value for key, value in receipt.items() if key not in ['identities', 'phase_reports']}))
    return 0 if receipt['status'] == 'COMPONENT_STORE_PAIR_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
