"""Run the exact retained signed provider probe; never build or modify its app."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import time
import traceback
import uuid
import zipfile

from run_probe import BUNDLE, CLASSES, NAME, ORIGINAL_TREES, RUNTIME, digest, git, require

BRANCH = 'codex/otzaria-shared-runtime-continuation-20261123'
WORKFLOW = '.github/workflows/pinkha-shared-runtime-continuation.yml'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Aliased retained app input')
        if path.is_dir():
            continue
        require(path.is_file(), 'Special retained app input')
        files[path.relative_to(root).as_posix()] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    return files


def members(archive):
    result, aliases = {}, set()
    for item in archive.infolist():
        path = PurePosixPath(item.filename.rstrip('/'))
        require(path.parts and not path.is_absolute() and '..' not in path.parts
                and path.as_posix() == item.filename.rstrip('/') and '\\' not in item.filename,
                'Unsafe retained ZIP input')
        key = path.as_posix().casefold()
        require(key not in aliases, 'Repeated retained ZIP member')
        aliases.add(key)
        mode = (item.external_attr >> 16) & 0xffff
        require(stat.S_IFMT(mode) in {0, stat.S_IFDIR if item.is_dir() else stat.S_IFREG},
                'Aliased or special retained ZIP member')
        if not item.is_dir():
            result[path.as_posix()] = item
    return result


def execute(args, receipt):
    root, work, evidence = args.root.resolve(), args.work.resolve(), args.evidence.resolve()
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Actual Apple silicon required')
    require(work.is_relative_to(root / 'build') and evidence.is_relative_to(root / 'build')
            and not work.exists(), 'Unowned or reused continuation paths')
    source = root / 'Tools/OriginalEditor/SharedRuntime'
    pin = json.loads((source / 'runtime_continuation.json').read_text())
    head = git(root, 'rev-parse', 'HEAD')
    require(os.environ.get('GITHUB_REPOSITORY') == pin['repository']
            and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF') == 'refs/heads/' + BRANCH
            and os.environ.get('GITHUB_SHA') == head
            and os.environ.get('GITHUB_WORKFLOW_REF') == pin['repository'] + '/' + WORKFLOW + '@refs/heads/' + BRANCH,
            'Wrong actual source-bound controller')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all', '--',
                    'Tools/OriginalEditor/SharedRuntime', WORKFLOW), 'Controller source changed')
    require({p: git(root, 'rev-parse', 'HEAD:' + p) for p in ORIGINAL_TREES} == ORIGINAL_TREES,
            'Original editor source/resource trees changed')
    controller = {p.relative_to(root).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()}
    controller[WORKFLOW] = digest(root / WORKFLOW)
    receipt.update(controller_source=head, controller_run_id=os.environ['GITHUB_RUN_ID'],
                   controller_run_attempt=os.environ['GITHUB_RUN_ATTEMPT'], controller_inputs=controller,
                   original_producer=pin, phase='AUTHENTICATE_RETAINED_SIGNED_BYTES')
    work.mkdir(parents=True)
    commands = []

    def command(label, argv, timeout=60, env=None, required=True):
        record = {'label': label, 'arguments': list(map(str, argv)), 'timeout_seconds': timeout,
                  'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        commands.append(record)
        log = evidence / (label + '.log')
        try:
            with log.open('w') as stream:
                result = subprocess.run(record['arguments'], cwd=root, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, text=True, timeout=timeout)
            record['returncode'] = result.returncode
            if required:
                require(result.returncode == 0, 'Native continuation command failed: ' + label)
            return log.read_text()
        except subprocess.TimeoutExpired:
            record['timed_out'] = True
            if required:
                raise
            return ''
        finally:
            record['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            if log.exists():
                record['log_sha256'] = digest(log)
            write(evidence / 'commands.json', commands)

    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + pin['repository'] + path], cwd=root, timeout=60))

    run = api('/actions/runs/' + str(pin['run_id']))
    artifact = api('/actions/artifacts/' + str(pin['artifact_id']))
    jobs = api('/actions/runs/' + str(pin['run_id']) + '/attempts/1/jobs')['jobs']
    require(run['id'] == pin['run_id'] and run['head_sha'] == pin['source_sha']
            and run['head_branch'] == pin['head_branch'] and run['run_attempt'] == 1
            and run['status'] == 'completed' and run['conclusion'] == 'failure'
            and run['event'] == 'push' and run['path'] == pin['workflow_path']
            and run['repository']['id'] == pin['repository_id'], 'Retained native producer identity differs')
    selected = [j for j in jobs if j['id'] == pin['job_id']]
    require(len(selected) == 1 and selected[0]['conclusion'] == 'failure'
            and selected[0]['runner_id'] > 0, 'Original native job did not execute')
    steps = {s['name']: s for s in selected[0]['steps']}
    require(steps['Build and observe the exact shared dependency implementation']['conclusion'] == 'failure'
            and steps['Preserve exact build and runtime evidence']['conclusion'] == 'success',
            'Retained native job boundaries differ')
    require(artifact['id'] == pin['artifact_id'] and artifact['name'] == pin['artifact_name']
            and artifact['size_in_bytes'] == pin['artifact_bytes'] and not artifact['expired']
            and artifact['digest'] == 'sha256:' + pin['artifact_sha256']
            and artifact['workflow_run']['id'] == pin['run_id']
            and artifact['workflow_run']['head_sha'] == pin['source_sha'], 'Retained native artifact differs')
    write(evidence / 'producer-metadata.json', {'run': run, 'job': selected[0], 'artifact': artifact})
    archive = work / 'original-evidence.zip'
    with archive.open('xb') as stream:
        subprocess.run(['gh', 'api', 'repos/' + pin['repository'] + '/actions/artifacts/'
                        + str(pin['artifact_id']) + '/zip'], cwd=root, stdout=stream, check=True, timeout=120)
    require(archive.stat().st_size == pin['artifact_bytes'] and digest(archive) == pin['artifact_sha256'],
            'Retained artifact transport changed')
    with zipfile.ZipFile(archive) as outer:
        outer_members = members(outer)
        raw = {}
        for name, key in [('retained-native-products.json', 'retention_sha256'),
                          ('RESULT.json', 'result_sha256'), ('commands.json', 'commands_sha256')]:
            require(name in outer_members and outer_members[name].file_size <= 256 * 1024,
                    'Missing bounded native source receipt')
            raw[name] = outer.read(name)
            require(hashlib.sha256(raw[name]).hexdigest() == pin[key], 'Original receipt differs: ' + name)
            (evidence / ('original-' + name)).write_bytes(raw[name])
        retained, original, original_commands = (json.loads(raw[n]) for n in
            ['retained-native-products.json', 'RESULT.json', 'commands.json'])
        require(retained['status'] == 'BUILD_LINK_EMBED_SIGNATURE_AND_DEFINITIONS_PASS_RUNTIME_NOT_RUN'
                and retained['source_sha'] == pin['source_sha'] and retained['run_id'] == str(pin['run_id'])
                and retained['run_attempt'] == '1' and retained['stageb_qualified'] is False
                and original['error']['message'] == 'Actual app did not emit runtime observation',
                'Retained producer results differ')
        completed = {c['name']: c for c in original_commands}
        for name in ['resolve', 'build', 'runtime-load-commands', 'consumer-load-commands',
                     'runtime-symbols', 'consumer-symbols', 'signature', 'retain-signed-app']:
            require(completed[name].get('returncode') == 0 and not completed[name].get('timed_out'),
                    'Original native prerequisite did not pass: ' + name)
        for name, expected in retained['source_inputs'].items():
            require(digest(root / name) == expected, 'Retained app/provider source differs: ' + name)
        app_raw = outer.read('shared-runtime-app.zip')
        require(len(app_raw) == pin['app_archive_bytes'] == retained['archive_bytes']
                and hashlib.sha256(app_raw).hexdigest() == pin['app_archive_sha256'] == retained['archive_sha256'],
                'Signed app archive identity differs')
    with zipfile.ZipFile(io.BytesIO(app_raw)) as inner:
        app_members = members(inner)
        expected = {NAME + '.app/' + k: v for k, v in retained['app_inventory'].items()}
        require(app_members.keys() == expected.keys(), 'Signed app membership differs')
        for name, item in app_members.items():
            value = inner.read(item)
            require(len(value) == expected[name]['bytes']
                    and hashlib.sha256(value).hexdigest() == expected[name]['sha256'], 'Signed member differs')
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
            target.chmod(stat.S_IMODE((item.external_attr >> 16) & 0xffff) or 0o644)
    app = work / (NAME + '.app')
    require(inventory(app) == retained['app_inventory'], 'Restored signed app differs')
    command('signature', ['codesign', '--verify', '--deep', '--strict', app])
    receipt.update(binary_identity=retained['binary_identity'], original_build_reused=True,
                   builds_executed=0, phase='ACTUAL_RETAINED_RUNTIME')
    runtimes = json.loads(command('runtimes', ['xcrun', 'simctl', 'list', 'runtimes', '--json']))['runtimes']
    matches = [r for r in runtimes if all(r.get(k) == v for k, v in pin['runtime'].items())]
    require(len(matches) == 1 and matches[0].get('isAvailable')
            and 'arm64' in matches[0]['supportedArchitectures']
            and any(d.get('identifier') == pin['device_type'] and d.get('productFamily') == 'iPad'
                    for d in matches[0]['supportedDeviceTypes']), 'Exact original iPad runtime is unavailable')
    udid = command('create', ['xcrun', 'simctl', 'create', 'OtzariaSharedResume-' + os.environ['GITHUB_RUN_ID'],
                              pin['device_type'], pin['runtime']['identifier']]).strip()
    receipt['owned_simulator'] = udid
    try:
        command('boot', ['xcrun', 'simctl', 'boot', udid], 120)
        command('bootstatus', ['xcrun', 'simctl', 'bootstatus', udid, '-b'], 180)
        command('install', ['xcrun', 'simctl', 'install', udid, app], 180)
        data = Path(command('container', ['xcrun', 'simctl', 'get_app_container', udid, BUNDLE, 'data']).strip())
        require(data.is_dir() and udid in data.parts, 'Unexpected actual probe data container')
        result_path = data / 'Documents/shared-runtime-result.json'
        require(not result_path.exists(), 'Stale app observation')
        help_text = command('launch-help', ['xcrun', 'simctl', 'help', 'launch'])
        require('--stdout' in help_text and '--stderr' in help_text, 'Native launch capture is unavailable')
        nonce = uuid.uuid4().hex
        env = dict(os.environ, SIMCTL_CHILD_SHARED_RUNTIME_PROBE_NONCE=nonce)
        launched = command('launch', ['xcrun', 'simctl', 'launch',
            '--stdout=' + str(evidence / 'app-stdout.log'), '--stderr=' + str(evidence / 'app-stderr.log'),
            udid, BUNDLE], 60, env)
        match = re.search(re.escape(BUNDLE) + r':\s*([1-9][0-9]*)', launched)
        require(match is not None, 'Actual launch returned no PID')
        receipt['launched_pid'] = int(match.group(1))
        deadline = time.monotonic() + 30
        while not result_path.is_file() and time.monotonic() < deadline:
            time.sleep(0.5)
        require(result_path.is_file() and 0 < result_path.stat().st_size <= 65536,
                'Actual retained app did not emit a bounded runtime observation')
        raw = result_path.read_bytes()
        (evidence / 'shared-runtime-result.json').write_bytes(raw)
        actual = json.loads(raw)
        require(actual['status'] == 'PASS_SINGLE_LOADED_PROVIDER' and actual['nonce'] == nonce
                and actual['process_id'] == receipt['launched_pid']
                and set(actual['providers']) == set(CLASSES)
                and all(len(paths) == 1 and paths[0].endswith('/Frameworks/' + RUNTIME + '.framework/' + RUNTIME)
                        for paths in actual['providers'].values()), 'Actual retained process lacks unique providers')
        receipt.update(runtime=actual, status='PASS_RETAINED_SHARED_FIREBASE_RUNTIME', phase='COMPLETE')
    except BaseException:
        command('processes', ['ps', '-axo', 'pid,ppid,state,comm'], 15, required=False)
        command('app-info', ['xcrun', 'simctl', 'appinfo', udid, BUNDLE], 30, required=False)
        command('runtime-log', ['xcrun', 'simctl', 'spawn', udid, 'log', 'show', '--style', 'compact',
            '--last', '5m', '--predicate',
            'process == "SharedFirebaseProbe" OR eventMessage CONTAINS "org.otzaria.acceptance.shared-firebase-runtime"'],
            30, required=False)
        command('screenshot', ['xcrun', 'simctl', 'io', udid, 'screenshot', evidence / 'runtime-screen.png'],
                20, required=False)
        crashes = []
        for directory in [Path.home() / 'Library/Logs/DiagnosticReports',
                          Path.home() / 'Library/Developer/CoreSimulator/Devices' / udid / 'data/Library/Logs/CrashReporter']:
            if directory.is_dir():
                for path in sorted(directory.rglob('SharedFirebaseProbe*'))[-8:]:
                    if path.is_file() and not path.is_symlink() and path.stat().st_size <= 5 * 1024 * 1024:
                        destination = evidence / ('crash-' + str(len(crashes)) + '-' + path.name)
                        shutil.copyfile(path, destination)
                        crashes.append({'file': destination.name, 'sha256': digest(destination)})
        receipt['crashes'] = crashes
        raise
    finally:
        for action in ['shutdown', 'delete']:
            command(action, ['xcrun', 'simctl', action, udid], 60, required=False)
        require(inventory(app) == retained['app_inventory'], 'Retained signed app changed during execution')
        require(controller == {**{p.relative_to(root).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()},
                                WORKFLOW: digest(root / WORKFLOW)}, 'Controller source changed')


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ['root', 'work', 'evidence']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 1, 'status': 'FAIL', 'builds_executed': 0,
               'original_editor_qualified': False, 'stageb_qualified': False}
    try:
        execute(args, receipt)
        return 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
        return 1
    finally:
        write(args.evidence / 'RESULT.json', receipt)


if __name__ == '__main__':
    raise SystemExit(main())
