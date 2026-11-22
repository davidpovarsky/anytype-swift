import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
E = ROOT / 'evidence'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


archive = ROOT / 'runtime-continuation-evidence.zip'
assert archive.stat().st_size == 442628
assert sha(archive) == '37ccba5016d8457da54945338e19e88b47f40909b2940cfbbf09f6c7ed6377b5'
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None and len(zipped.namelist()) == len(set(zipped.namelist())) == 210
    for row in zipped.infolist():
        p = PurePosixPath(row.filename)
        assert not p.is_absolute() and '..' not in p.parts and not row.is_dir()
        assert (E / row.filename).read_bytes() == zipped.read(row)
upload, inner = read(E / 'UPLOAD_INDEX.json'), read(E / 'EVIDENCE_INDEX.json')
assert len(upload['files']) == 209 and not upload['omitted_binary_artifact_streams']
assert len(inner['files']) == 206
for index in (upload, inner):
    for row in index['files']:
        p = E / row['path']
        assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
assert {p.relative_to(E).as_posix() for p in E.rglob('*') if p.is_file()} == {r['path'] for r in upload['files']} | {'UPLOAD_INDEX.json'}
producer = read(ROOT.parent / 'sdk_runtime_continuation/FRAMEWORK_PRODUCER.json')
roles = {'original-evidence-outer-download': 'evidence_artifact', 'original-framework-download': 'framework_artifact'}
relocated, ledgers = [], {}
for ledger in E.rglob('COMMANDS.json'):
    directory = ledger.parent
    name = directory.relative_to(E).as_posix()
    rows = read(ledger)
    ledgers[name] = rows
    for row in rows:
        assert row['status'] == 'TERMINAL' and row['start_new_session'] is True and row['cleanup'][-1]['drained'] is True
        for stream in ('stdout', 'stderr'):
            path = directory / row[stream]
            if path.exists():
                assert sha(path) == row[stream + '_sha256']
            else:
                assert name == 'github-commands' and stream == 'stdout' and row['label'] in roles
                artifact = producer[roles[row['label']]]
                assert row['argv'] == ['gh', 'api', 'repos/davidpovarsky/anytype-swift/actions/artifacts/' + str(artifact['id']) + '/zip']
                assert row['stdout_relocated_to_owned_work'] == row['label'].removesuffix('-download') + '.zip'
                assert row['stdout_bytes'] == artifact['size_in_bytes'] and row['stdout_sha256'] == artifact['sha256']
                relocated.append({'label': row['label'], 'artifact_id': artifact['id'], 'bytes': row['stdout_bytes'], 'sha256': row['stdout_sha256']})
assert len(relocated) == 2 and sum(len(v) for v in ledgers.values()) == 85
commands, cleanup = ledgers['commands'], ledgers['cleanup']
assert len(commands) == 54 and len(cleanup) == 3 and len(ledgers['github-commands']) == 8
assert all(r['effective_returncode'] == 0 and not r['timed_out'] for r in commands[:-1])
assert all(r['effective_returncode'] == 0 and not r['timed_out'] for r in cleanup + ledgers['github-commands'])
labels = {r['label']: r for r in commands}
assert len(labels) == len(commands)
launch = commands[-1]
assert launch['label'] == 'consumer-en-launch' and launch['returncode'] == launch['effective_returncode'] == 3 and not launch['timed_out']
assert launch['duration_seconds'] == 4.88
assert (E / 'commands' / launch['stdout']).stat().st_size == 0
error = (E / 'commands' / launch['stderr']).read_text()
assert 'NSPOSIXErrorDomain, code=3' in error and 'did not return a process handle nor launch error' in error
result, owned = read(E / 'execution.json'), read(E / 'owned-simulator.json')
assert result['status'] == 'FAIL' and result['error'] == 'owned command failed: consumer-en-launch'
assert result['phase'] == 'ACTUAL_EXTERNAL_RESOURCE_RUNTIME' and not result.get('cleanup_error')
assert result['runtime_qualification_producer']['control_sha'] == '0b792c7f2906f375e34b30a0cb42b85d98c0ba56'
assert int(result['runtime_qualification_producer']['run_id']) == 45054111060
assert result['original_framework_build'] == 'REUSED_SUCCESSFUL_ORIGINAL_PRODUCER'
assert result['framework_source_sha'] == 'edce5b975b173059522f90adb71271fb95adf963' and result['framework_producer'] == producer
assert result['retained_source_controls_passed'] == 245 and result['source_controls_replayed'] == 0
assert result['external_consumer_build'] == 'PASS' and result['install_attempts'] == result['simulator_attempts'] == 1
assert result['verified_runtime_observations'] == [] and result['owned_simulator_cleanup_completed'] is True
assert not (E / 'runtime-qualification.json').exists()
assert owned['udid'] == 'DF31D8F2-1736-4A99-88BB-3D14D94B3588'
assert labels['boot-status']['argv'] == ['xcrun', 'simctl', 'bootstatus', owned['udid'], '-b']
assert labels['boot-status']['requested_timeout_seconds'] == 180 and labels['boot-status']['duration_seconds'] == 127.237
assert labels['install-external-consumer']['requested_timeout_seconds'] == 300 and labels['install-external-consumer']['duration_seconds'] == 40.694
assert [r['label'] for r in cleanup] == ['shutdown-owned-simulator', 'delete-owned-simulator', 'devices-after-cleanup']
assert cleanup[0]['argv'] == ['xcrun', 'simctl', 'shutdown', owned['udid']]
assert cleanup[1]['argv'] == ['xcrun', 'simctl', 'delete', owned['udid']]
after = read(E / 'cleanup' / cleanup[2]['stdout'])['devices']
assert not any(d['udid'].upper() == owned['udid'].upper() for rows in after.values() for d in rows)
cleanup_result = read(E / 'cleanup/OWNED_SIMULATOR_CLEANUP.json')
assert cleanup_result == result['owned_simulator_cleanup']
assert cleanup_result['completed'] and cleanup_result['owned_groups_drained'] and cleanup_result['owned_device_proven_absent']
app = read(E / 'consumer-app-inventory.json')
assert len(app) == result['consumer_app_files'] == 642
assert sum(x['bytes'] for x in app.values()) == result['consumer_app_bytes'] == 500498107
assert sha(E / 'consumer-app-inventory.json') == result['consumer_app_inventory_sha256']
retained = read(E / 'retained-consumer.json')
assert retained == result['retained_signed_consumer']
assert retained['consumer_inventory_sha256'] == sha(E / 'consumer-app-inventory.json')
assert retained['signature_command'] == labels['external-consumer-signature']
assert retained['consumer_producer'] == result['runtime_qualification_producer'] and retained['framework_producer'] == producer
assert retained['runtime_qualified'] is retained['restore_as_original_sdk_allowed'] is False
assert retained['archive_bytes'] == 141705455 and retained['archive_sha256'] == 'ef49025e85cc27723738c0cb96cc91084412a952462627d9416bc7b3207068a1'
controls = read(E / 'runtime-continuation-control-admission.json')
assert controls['retained_new_control_count'] == 24 and controls['retained_instrumented_control_count'] == 14
assert controls['new_control_bodies_replayed'] == controls['prior_source_controls_replayed'] == 0
run, jobs, artifacts = read(ROOT / 'RUN_TERMINAL_OR_LAST.json'), read(ROOT / 'JOBS.json')['jobs'], read(ROOT / 'ARTIFACTS.json')['artifacts']
assert run['id'] == 45054111060 and run['run_attempt'] == 1 and run['head_sha'] == result['runtime_qualification_producer']['control_sha']
assert run['status'] == 'completed' and run['conclusion'] == 'failure'
assert len(jobs) == 1 and jobs[0]['id'] == 137305434669 and jobs[0]['conclusion'] == 'failure'
by_id = {a['id']: a for a in artifacts}
assert set(by_id) == {14767271445, 14766857451}
assert by_id[14767271445]['size_in_bytes'] == 442808 and by_id[14767271445]['digest'] == 'sha256:6c153f074318446a2a78cbf1807e177a113e0c7163c74a2ebe69e1c90be96967'
assert by_id[14766857451]['size_in_bytes'] == 141885343 and by_id[14766857451]['digest'] == 'sha256:54e2a4b191d1248ab446273628f397bb2763c26efcf1c9648c208c3ae0469302'
for artifact in artifacts:
    assert artifact['workflow_run']['id'] == run['id'] and artifact['workflow_run']['head_sha'] == run['head_sha']
receipt = {
    'schema': 'otzaria.root-sdk-launch-failure-review/1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'run_id': run['id'], 'attempt': 1, 'head': run['head_sha'], 'job_id': jobs[0]['id'],
    'status': 'VERIFIED_LAUNCH_FAILURE_WITH_SUCCESSFUL_OWNED_DEVICE_CLEANUP',
    'archive_members_crc_and_bytes_verified': 210, 'upload_index': 209, 'execution_index': 206,
    'command_ledger_counts': {k: len(v) for k, v in ledgers.items()}, 'command_groups_drained': 85,
    'original_binary_stream_relocations': relocated,
    'retained_source_controls': 245, 'retained_continuation_controls': 24, 'retained_instrumented_controls': 14,
    'consumer_build_and_signature': 'PASS', 'boot_status': 'PASS', 'boot_status_seconds': 127.237,
    'install_attempts': 1, 'install_seconds': 40.694, 'install': 'PASS',
    'first_failed_command': launch, 'runtime_observations': 0, 'runtime_qualified': False,
    'owned_udid': owned['udid'], 'cleanup': cleanup_result,
    'signed_app_retention_metadata': {'outer_artifact_id': 14766857451, 'outer_bytes': 141885343, 'outer_sha256': by_id[14766857451]['digest'][7:], 'inner_bytes': retained['archive_bytes'], 'inner_sha256': retained['archive_sha256'], 'files': 642, 'bytes': 500498107, 'actual_app_archive_not_downloaded_by_this_review': True},
    'diagnostic_limits': 'Two bounded simctl list reads timed out; process and plist observations do not establish the launch failure cause. No app crash report is present.',
    'cause': 'NOT_ESTABLISHED', 'new_tests_or_Actions_downloads_by_review': 0,
    'next': 'Inspect the once-retained signed application bytes and exact dependencies; require an evidence-driven change or scoped diagnostic before a further simulator attempt.',
}
(ROOT / 'ROOT_LAUNCH_FAILURE_REVIEW.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('status', 'archive_members_crc_and_bytes_verified', 'command_groups_drained', 'consumer_build_and_signature', 'boot_status', 'install', 'runtime_observations', 'runtime_qualified', 'cause')}))
