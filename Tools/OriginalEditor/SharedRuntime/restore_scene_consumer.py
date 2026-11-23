"""Restore the exact signed UIScene consumer after native simulator boot failure.

Every native compile/link/signature result is bound to the immutable prior job.
This continuation performs no provider or consumer build and no resigning.
"""
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import zipfile

from run_probe import NAME, RUNTIME, digest, require


def restore_scene_consumer(root, work, evidence, original_app, original, receipt,
                           command, inventory, members, api, write):
    source = root / 'Tools/OriginalEditor/SharedRuntime'
    pin = json.loads((source / 'scene_runtime_continuation.json').read_text())
    run = api('/actions/runs/' + str(pin['run_id']))
    artifact = api('/actions/artifacts/' + str(pin['artifact_id']))
    jobs = api('/actions/runs/' + str(pin['run_id']) + '/attempts/1/jobs')['jobs']
    require(run['id'] == pin['run_id'] and run['head_sha'] == pin['source_sha']
            and run['head_branch'] == pin['head_branch'] and run['run_attempt'] == 1
            and run['status'] == 'completed' and run['conclusion'] == 'failure'
            and run['event'] == 'push' and run['path'] == pin['workflow_path']
            and run['repository']['id'] == pin['repository_id'],
            'Retained scene consumer run identity differs')
    selected = [j for j in jobs if j['id'] == pin['job_id']]
    require(len(selected) == 1 and selected[0]['conclusion'] == 'failure'
            and selected[0]['runner_id'] == pin['runner_id'] > 0,
            'Retained scene consumer native job differs')
    steps = {s['name']: s for s in selected[0]['steps']}
    require(steps['Restore exact signed bytes and diagnose actual runtime']['conclusion'] == 'failure'
            and steps['Preserve runtime observation and launch diagnostics']['conclusion'] == 'success',
            'Retained scene consumer job boundaries differ')
    require(artifact['id'] == pin['artifact_id'] and artifact['name'] == pin['artifact_name']
            and artifact['size_in_bytes'] == pin['artifact_bytes'] and not artifact['expired']
            and artifact['digest'] == 'sha256:' + pin['artifact_sha256']
            and artifact['workflow_run']['id'] == pin['run_id']
            and artifact['workflow_run']['head_sha'] == pin['source_sha'],
            'Retained scene consumer artifact differs')
    write(evidence / 'scene-producer-metadata.json', {'run': run, 'job': selected[0], 'artifact': artifact})
    archive = work / 'scene-evidence.zip'
    with archive.open('xb') as stream:
        subprocess.run(['gh', 'api', 'repos/' + pin['repository'] + '/actions/artifacts/'
                        + str(pin['artifact_id']) + '/zip'], cwd=root, stdout=stream,
                       check=True, timeout=120)
    require(archive.stat().st_size == pin['artifact_bytes'] and digest(archive) == pin['artifact_sha256'],
            'Retained scene artifact transport changed')
    with zipfile.ZipFile(archive) as outer:
        outer_members = members(outer)
        raw = {}
        for name, key in [('retained-scene-consumer.json', 'retention_sha256'),
                          ('RESULT.json', 'result_sha256'), ('commands.json', 'commands_sha256')]:
            require(name in outer_members and outer_members[name].file_size <= 256 * 1024,
                    'Missing bounded scene consumer receipt')
            raw[name] = outer.read(name)
            require(hashlib.sha256(raw[name]).hexdigest() == pin[key],
                    'Retained scene consumer receipt differs: ' + name)
            (evidence / ('prior-scene-' + name)).write_bytes(raw[name])
        retained, result, commands = (json.loads(raw[n]) for n in
                                      ['retained-scene-consumer.json', 'RESULT.json', 'commands.json'])
        require(retained['status'] == 'SCENE_CONSUMER_BUILT_RUNTIME_NOT_QUALIFIED'
                and retained['controller_source'] == result['controller_source'] == pin['source_sha']
                and retained['controller_run_id'] == result['controller_run_id'] == str(pin['run_id'])
                and retained['controller_run_attempt'] == result['controller_run_attempt'] == '1'
                and retained['provider_builds_executed'] == result['provider_builds_executed'] == 0
                and result['consumer_builds_executed'] == result['builds_executed'] == 1
                and result['original_editor_qualified'] is False
                and retained['stageb_qualified'] is result['stageb_qualified'] is False,
                'Retained scene consumer acceptance scope differs')
        require(retained['original_provider_source'] == original['source_sha']
                and retained['original_provider_run_id'] == original['run_id']
                and retained['original_provider_run_attempt'] == original['run_attempt'],
                'Retained scene consumer provider provenance differs')
        completed = {c['label']: c for c in commands}
        require(len(completed) == len(commands), 'Repeated scene build command identity')
        for label in ['scene-consumer-compile', 'scene-consumer-sign', 'scene-consumer-signature',
                      'scene-consumer-loads', 'scene-consumer-symbols', 'retain-scene-consumer']:
            require(completed[label].get('returncode') == 0 and not completed[label].get('timed_out'),
                    'Retained scene native prerequisite did not pass: ' + label)
        require(result['error']['type'] == 'TimeoutExpired'
                and completed['bootstatus'].get('timed_out') is True
                and completed['bootstatus']['timeout_seconds'] == 180
                and not {'install', 'launch'} & completed.keys(),
                'Retained scene consumer did not fail before install at the observed boot boundary')
        for name in ['SceneProbeApp.swift', 'build_scene_consumer.py']:
            relative = 'Tools/OriginalEditor/SharedRuntime/' + name
            require(digest(source / name) == result['controller_inputs'][relative],
                    'Retained scene consumer build source changed')
        require(digest(source / 'SceneProbeApp.swift') == retained['consumer_source_sha256']
                == pin['consumer_source_sha256'], 'Retained scene executable source differs')
        app_raw = outer.read('scene-consumer-app.zip')
        require(len(app_raw) == pin['app_archive_bytes'] == retained['archive_bytes']
                and hashlib.sha256(app_raw).hexdigest() == pin['app_archive_sha256'] == retained['archive_sha256'],
                'Retained scene app archive differs')
    current, previous = retained['app_inventory'], original['app_inventory']
    require(current.keys() == previous.keys()
            and {p for p in current if current[p] != previous[p]}
            == {NAME, 'Info.plist', '_CodeSignature/CodeResources'},
            'Scene consumer changed a retained provider or resource')
    destination = work / 'retained-scene'
    with zipfile.ZipFile(io.BytesIO(app_raw)) as inner:
        app_members = members(inner)
        expected = {NAME + '.app/' + k: v for k, v in current.items()}
        require(app_members.keys() == expected.keys(), 'Retained scene app membership differs')
        for name, item in app_members.items():
            value = inner.read(item)
            require(len(value) == expected[name]['bytes']
                    and hashlib.sha256(value).hexdigest() == expected[name]['sha256'],
                    'Retained scene app member differs')
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
            target.chmod(stat.S_IMODE((item.external_attr >> 16) & 0xffff) or 0o644)
    app = destination / (NAME + '.app')
    require(inventory(app) == current and inventory(original_app) == previous,
            'Restored scene consumer or original provider inventory differs')
    provider = app / 'Frameworks' / (RUNTIME + '.framework') / RUNTIME
    require(digest(provider) == retained['provider_binary_sha256'] == pin['provider_binary_sha256']
            and digest(app / NAME) == retained['consumer_binary_sha256'] == pin['consumer_binary_sha256'],
            'Restored exact scene consumer/provider binary differs')
    command('retained-scene-signature', ['codesign', '--verify', '--deep', '--strict', app])
    (evidence / 'scene-consumer-app.zip').write_bytes(app_raw)
    write(evidence / 'retained-scene-consumer.json', retained)
    receipt.update(retained_scene_producer=pin, original_provider_build_reused=True,
                   original_consumer_reused=False, scene_consumer_build_reused=True,
                   builds_executed=0, provider_builds_executed=0, consumer_builds_executed=0,
                   consumer_source_sha256=pin['consumer_source_sha256'],
                   binary_identity={RUNTIME: digest(provider), NAME: digest(app / NAME)},
                   build_validation='EXACT_SIGNED_BYTES_REUSE_OBSERVED_NATIVE_COMPILE_LINK_SYMBOL_PROOF')
    return app, current
