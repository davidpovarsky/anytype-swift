"""Owned same-binary fixture with narrowly enabled native HTTP access logging."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119')
APP = Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
TOOLS = APP / 'Tools/AnyEngineValidation'
OUTPUT = APP / 'build/any-engine-port/guarded-hierarchy-native-v7-watchdog-v1'
sys.path.insert(0, str(TOOLS))
from run_runtime_validation import Peer, require

NATIVE_SHA = '12c7fb62164c830410331aabf616194edb0711a083250f8e8dd34c3cba52078b'
MANIFEST_SHA = '62a13310a474d93d728258d0631618b09056a20c4454bd7be303f3ec071fb77c'
binary = ROOT / '.runtime-artifacts/any-native-metadata-v7.exe'
manifest = TOOLS / 'evidence/native-document-metadata-v7-source.json'
folder = ROOT / '.runtime-artifacts/peer-native-v7-watchdog-hierarchy-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_http_records(paths):
    result = []
    for path in paths:
        with path.open('rb') as stream:
            data = stream.read(2 * 1024 * 1024 + 1)
        require(len(data) <= 2 * 1024 * 1024, 'startup private log exceeds the read bound')
        for line in data.decode('utf8', errors='replace').splitlines():
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue  # Includes the private handshake; never copied or printed.
            if not isinstance(value, dict) or value.get('logger') != 'http' or value.get('msg') != 'http':
                continue
            if value.get('method') not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
                continue
            path_value = value.get('path')
            if not isinstance(path_value, str) or not path_value.startswith('/') or len(path_value.encode()) > 8192:
                continue
            status = value.get('status')
            if not isinstance(status, int) or not 100 <= status <= 599:
                continue
            result.append({'method': value['method'], 'path': path_value, 'status': status,
                           'duration': value.get('duration'), 'time': value.get('ts')})
    return result


require(sha(binary) == NATIVE_SHA, 'native v7 binary changed')
require(sha(manifest) == MANIFEST_SHA, 'native v7 manifest changed')
require(not folder.exists(), 'owned watchdog fixture already exists; inspect before any relaunch')
require(not OUTPUT.exists(), 'watchdog evidence prefix already exists; preserve it')
folder.mkdir()
OUTPUT.mkdir(parents=True)
shutil.copyfile(__file__, OUTPUT / 'executed-launcher.py')
config = {
    'mode': 'managed', 'webUI': {'enabled': False},
    'p2p': {'enabled': False, 'localDiscovery': False, 'global': {'enabled': False}},
    'push': {'enabled': False}, 'index': {'embedder': 'none'},
    'log': {'defaultLevel': 'error', 'format': 2,
            'levels': [{'name': 'http', 'level': 'info'}, {'name': '*', 'level': 'error'}]},
}
(folder / 'config.json').write_text(json.dumps(config), encoding='utf8')
out, err = folder / 'stdout.private.log', folder / 'stderr.private.log'
with out.open('wb') as stdout, err.open('wb') as stderr:
    process = subprocess.Popen(
        [str(binary), 'run', '--mode', 'managed', '--config', str(folder / 'config.json'),
         '--data-dir', str(folder / 'data'), '--addr', '127.0.0.1:0'],
        cwd=folder, env={k: v for k, v in os.environ.items() if not k.startswith('ANY_')},
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
(folder / 'pid.txt').write_text(str(process.pid), encoding='ascii')
peer = object.__new__(Peer)
peer.process = process
try:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        require(process.poll() is None, 'owned watchdog fixture exited before readiness')
        text = out.read_text(encoding='utf8', errors='replace')
        addr = re.search(r'(?m)^LISTENING (127\.0\.0\.1:\d+)\s*$', text)
        token = re.search(r'(?m)^CONTROL_TOKEN ([0-9a-f]+)\s*$', text)
        if addr and token:
            peer.endpoint, peer.token = 'http://' + addr.group(1), token.group(1)
            if peer.request('GET', '/v1/health', timeout=2).get('status') == 'ok':
                break
        time.sleep(.1)
    else:
        raise RuntimeError('owned watchdog fixture readiness exceeded40seconds')
    startup = allowed_http_records((out, err))
    require(any(v['method'] == 'GET' and v['path'] == '/v1/health' and v['status'] == 200 for v in startup),
            'native HTTP access logging not observed; do not proceed without correlation data')
    auth = peer.request('POST', '/v1/auth', {}, timeout=60, control=True)
    account = auth['accountId']
    del auth
    space = peer.request('POST', '/v1/spaces', {
        'name': 'Disposable watchdog native hierarchy launcher Space'
    }, timeout=60)['id']
    proof = peer.request('GET', '/v1/spaces/' + space + '/pinkha/document-types/page', timeout=20)
    require(proof.get('eligible') is True, 'fresh Page policy failed')
    public = {
        'status': 'READY_OWNED_NATIVE_V7_CORRELATED_FIXTURE', 'endpoint': peer.endpoint,
        'pid': process.pid, 'accountId': account, 'spaceId': space,
        'claimsInstalledByLauncher': False, 'userObjectsCreatedByLauncher': 0,
        'binarySHA256': NATIVE_SHA, 'nativeSourceManifestSHA256': MANIFEST_SHA,
        'launcherSHA256': sha(Path(__file__)), 'configurationSHA256': sha(folder / 'config.json'),
        'nativeHTTPAccessLoggingObserved': True,
        'accessLogFields': ['method', 'path', 'status', 'duration', 'time'],
        'networkAndTransportSettingsUnchanged': True,
        'readyAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'syntheticAccountScope': 'New disposable official-network account and Space; no existing accounts selected.',
    }
    (folder / 'session.public.json').write_text(json.dumps(public, indent=2) + '\n', encoding='utf8')
    (OUTPUT / 'fixture.json').write_text(json.dumps(public, indent=2) + '\n', encoding='utf8')
    records = allowed_http_records((out, err))
    (OUTPUT / 'native-http-startup.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf8')
    print(json.dumps(public), flush=True)
except BaseException as error:
    failure = {'status': 'FAILED_OWNED_CORRELATED_FIXTURE', 'errorType': type(error).__name__,
               'pid': process.pid, 'privateLogsRetained': True, 'binarySHA256': NATIVE_SHA}
    (OUTPUT / 'launcher-failure.json').write_text(json.dumps(failure, indent=2) + '\n', encoding='utf8')
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)
    print(json.dumps(failure), flush=True)
    raise SystemExit(1)
