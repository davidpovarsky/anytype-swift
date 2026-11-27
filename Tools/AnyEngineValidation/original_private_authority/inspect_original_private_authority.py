#!/usr/bin/env python3
"""Read the exact original archive without extracting or opening an account.

Only lengths, hashes, format categories, public source joins and bounded
producer path/cleanup observations may enter the receipt. No credential,
account-file payload or raw command output is written to disk or stdout.
This independent read-only budget is not a native/build controller budget.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import traceback

HELPER_SHA = '03625d7770c10fd072034bc9ab0d84483a537bf1a5ea03e2d473b4147bf5ec82'
PINS_SHA = '3acbd1188e4cd7ca539b07e728397504f54ef6e18edcda2c574b7c14945f661d'
PUBLIC_PINS_SHA = 'c004d620661df3da00168cbe07fd1c2fdcc059fc1d104cc94ad24f67f252aa50'
PRODUCER_COMMIT = 'bfd73d7d2d05a3dc115f6fddf2fb938844b17280'
CUSTOM_SOURCE_SHA = '699fe5e97942360e53b0ac364105dbf11350e81b33f042337b49995e32edac79'
CUSTOM_DELTA_SHA = '315b63e0496cf260691c6fae367a555f143209cf3e35f45da9302836ce5ba8cb'
PRIOR = Path('/var/lib/pinkha-w1-functional-migration-20261127/original156-source-history-authority1/result.json')
PRIOR_SHA = '19c454ee9feed8bc98697eb6db316ca4e0b19bdeeb0b759a6f37ddfb83ce2d9d'
INDEX = Path('/var/lib/pinkha-w1-functional-migration-20261127/original156-source-custody2/private-original-index.json')
INDEX_SHA = '9e4fc63d587d194cf13fff4002329c25404490c166dd9ffc4fac9778767167b1'
RETIREMENT = Path('/var/lib/pinkha-w1-original156-retirement-20261127/attempt2/result.json')
RETIREMENT_SHA = '5d0dc7beab578f61d40eab4e9f466e936ca7f97903d5062fcb2844432d55303b'
RESTORE_SHA = 'f18df0bf23d585e31941d62910ee55ea673d51882c290260ad9f3d55832e82b5'
E_PARENT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127')
SOURCE = E_PARENT/'retained/current8ac/attempt2/source'
E_CUSTODY_SHA = '331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772'
E_CONTROLLER_SHA = '4ddaa92aaa5fe2d13d39bab699dbe6c409a2900eb9713da48af2470435c635fd'
SOURCE_INVENTORY_SHA = 'ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28'
SOURCE_METADATA_SHA = '2a0a8807ffaae25b3596a387e47f42e5893d9a83ee64d161d029712d0acaced9'
ARCHIVE_BYTES = 106036361
ARCHIVE_SHA = 'f85036744b0cb76ffecb4e29f752dd293a74a1f76c2d13c273df57691a4a8c64'
ACCOUNT_SHA = '6403e2a6ff63f62dc5be07a393751f70507ba50863d9dc9758807bb7b635354a'
SPACE_SHA = 'b8a6fd56b502aca4a9f28783974fe33a4dc9313320f8fdffe2041ab8e95c19df'
FIXTURE = 'private/fixtures/TestLoadedAccountCustomSchemaSource/'
ACCOUNT = 'AAZDAU4v7NMed5j3SkFbBLMVHK6Tv2EvzStaKv2mJ5ZmbBg8'
ACCOUNT_PREFIX = FIXTURE+ACCOUNT+'/'
DEVICE_SHA = '554bbf9e65173448fdbd77207be2c1bbeaf6c574828508c50fa75ef689e71ec7'
MANIFEST_NAME = FIXTURE+'native-source-2179973240/manifest.json'
MANIFEST_SHA = 'cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4'
METADATA_MEMBERS = {
    'private/source-metadata/manifest.json', 'private/result.json', 'private/commands.json',
    'private/generated-test-main.go', 'private/commands/native-custom-schema.stdout',
    'private/commands/native-custom-schema-inspect.stdout',
    FIXTURE+'.anytype-locks/'+ACCOUNT+'.owner.json',
    FIXTURE+'native-custom-schema-capture-attempt-1.json', MANIFEST_NAME,
}
DELTAS = ['derived-source-v2.json', 'native-whole-source-delta-v1.json', 'native-file-peer-source-delta-v1.json',
          'native-type-namespace-peer-continuation-v1.json', 'native-custom-schema-checkpoint-delta-v1.json']
METADATA_MEMBERS.update('private/source-metadata/'+name for name in DELTAS)
CONFIG_KEYS = {'HostAddr', 'GatewayAddr', 'CustomFileStorePath', 'LegacyFileStorePath', 'NetworkId',
               'AutoDownloadFiles', 'AutoDownloadOnWifiOnly', 'AutoDownloadSizeLimitMb'}
CREDENTIAL_KEYS = {'mnemonic', 'accountkey', 'accountmasternode', 'masterkey', 'sessionsigningkey', 'privatekey', 'seed'}
MIB = 1024**2
ROOT_READ_ONLY_FLOOR = 64*MIB
DEV_FLOOR = 512*MIB
DEV_ADMISSION = DEV_FLOOR+8*MIB
MEMORY_FLOOR = 256*MIB
OUTPUT_CAP = 256*1024
DEADLINE = 120
OUT_PARENT = Path('/mnt/development/projects/evidence/pinkha-c-original156-private-authority-20261127')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(path):
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    return path


def load_helper():
    path = physical(Path(__file__).with_name('reviewed_stream_lifecycle.py'))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(64*1024)
    assert sha(raw) == HELPER_SHA
    spec = importlib.util.spec_from_loader('read_only_stream_lifecycle', loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    # Only fixed nonmux SSH, immutable reads and process-group ownership are
    # reused. Its main, process_guard and HashStream are never called or patched.
    return module, raw


def available_memory():
    with open('/proc/meminfo') as stream:
        rows = dict(line.split(':', 1) for line in stream)
    return int(rows['MemAvailable'].split()[0])*1024


def guard(out, began, result):
    root = shutil.disk_usage('/').free
    dev = shutil.disk_usage(out).free
    memory = available_memory()
    result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes', root), root)
    result['minimumDevelopmentFreeBytes'] = min(result.get('minimumDevelopmentFreeBytes', dev), dev)
    result['minimumMemAvailableBytes'] = min(result.get('minimumMemAvailableBytes', memory), memory)
    assert root >= ROOT_READ_ONLY_FLOOR and dev >= DEV_FLOOR and memory >= MEMORY_FLOOR
    assert time.monotonic()-began < DEADLINE
    assert sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= OUTPUT_CAP


class ArchiveStream(io.RawIOBase):
    def __init__(self, pipe, out, began, result):
        self.pipe, self.out, self.began, self.result = pipe, out, began, result
        self.count, self.eof, self.hasher = 0, False, hashlib.sha256()

    def readable(self):
        return True

    def read(self, count=-1):
        if self.eof:
            return b''
        count = min(count if count >= 0 else MIB, MIB)
        if count == 0:
            return b''
        while True:
            guard(self.out, self.began, self.result)
            ready, _, _ = select.select([self.pipe], [], [], .25)
            if ready:
                raw = os.read(self.pipe.fileno(), count)
                self.count += len(raw)
                assert self.count <= ARCHIVE_BYTES
                self.hasher.update(raw)
                if not raw:
                    self.eof = True
                return raw


def json_candidates(value):
    hits = []
    def visit(node):
        if isinstance(node, dict):
            for key, item in node.items():
                normalized = re.sub('[^a-z]', '', key.lower())
                if normalized in CREDENTIAL_KEYS and item is not None and item != '' and item != [] and item != {}:
                    hits.append({'fieldKind': normalized, 'valuePresent': True,
                                 'valueType': type(item).__name__, 'valueExposed': False})
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)
    visit(value)
    return hits


def classify_account(relative, raw):
    row = {'relativePath': relative, 'bytes': len(raw), 'sha256': sha(raw),
           'accountOrDatabaseOpened': False, 'payloadExposed': False}
    candidates = []
    if relative == 'device.key':
        assert len(raw) == 116 and sha(raw) == DEVICE_SHA
        row.update(format='opaque native encrypted device-key candidate',
                   expectedPlaintextType='cryptoproto.Key(Ed25519Private)',
                   expectedSerializedPlaintextBytes=68, ephemeralPublicPrefixBytes=32,
                   authenticatedBoxOverheadBytes=16, ciphertextAuthenticationPerformed=False,
                   decryptionAttempted=False, accountAuthorityRecovered=False)
    elif relative == 'config.json':
        obj = json.loads(raw)
        assert isinstance(obj, dict)
        row.update(format='native persisted configuration JSON', fieldNames=sorted(obj),
                   allFieldsInOriginalConfigurationSchema=set(obj).issubset(CONFIG_KEYS))
        candidates = json_candidates(obj)
    elif relative.endswith('.db'):
        assert raw.startswith(b'SQLite format 3\x00')
        row.update(format='SQLite database header; no SQL connection or row query')
    elif relative.startswith('fts_tantivy/16/'):
        row.update(format='Tantivy index/bookkeeping member; exact bytes hashed only')
        if relative.endswith('.json'):
            obj = json.loads(raw)
            row['jsonTopLevelType'] = type(obj).__name__
            candidates = json_candidates(obj)
    elif relative in {'flatfs/SHARDING', 'flatfs/_README', 'flatfs/diskUsage.cache'}:
        row.update(format='flatfs bookkeeping member; exact bytes hashed only')
    else:
        raise AssertionError('unclassified original account member')
    return row, candidates


def producer_location(commands, producer, inspection):
    # The original public helper records an explicit argv array per label.
    # Inspect that fixed schema; do not infer a wallet path from arbitrary text.
    assert isinstance(commands, list) and all(isinstance(row, dict) for row in commands)
    selected = [row for row in commands if row.get('label') == 'native-custom-schema']
    assert len(selected) == 1
    run = selected[0]; argv = run['argv']
    assert isinstance(argv, list) and all(isinstance(x, str) for x in argv)
    assert argv[:4] == ['sudo', '-n', 'docker', 'run']
    def values(flag):
        indices = [i for i, token in enumerate(argv) if token == flag]
        assert all(i+1 < len(argv) for i in indices)
        return [argv[i+1] for i in indices]
    names = values('--name')
    assert names == ['pinkha-loaded-native-45492064232-1-native-custom-schema']
    name = names[0]
    roots = [item.split('=', 1)[1] for item in values('--env')
             if item.startswith('PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT=')]
    assert len(roots) == 1
    root = roots[0]; path = PurePosixPath(root)
    assert path.is_absolute() and str(path) == root and '..' not in path.parts
    assert root.endswith('/pinkha-native-file-peer/private/fixtures')
    mounts = []
    for specification in values('--mount'):
        fields = specification.split(',')
        keyed = [field.split('=', 1) for field in fields if '=' in field]
        assert len(keyed) == len({key for key, _ in keyed})
        row = dict(keyed)
        assert row.get('type') == 'bind'
        if row.get('target') == root:
            assert 'readonly' not in fields
            src = PurePosixPath(row['source'])
            assert src.is_absolute() and str(src) == row['source'] and '..' not in src.parts
            mounts.append(row)
    assert len(mounts) == 1 and mounts[0]['source'] == root
    inspect_commands = [row for row in commands if row.get('label') == 'native-custom-schema-inspect']
    assert len(inspect_commands) == 1
    inspect_command = inspect_commands[0]
    assert inspect_command['argv'] == ['sudo', '-n', 'docker', 'inspect', name]
    assert inspect_command['returncode'] == 0
    assert isinstance(inspection, list) and len(inspection) == 1
    inspected = inspection[0]
    assert inspected['Name'] == '/'+name and inspected['State']['Running'] is False
    assert inspected['State']['ExitCode'] == run['returncode']
    assert inspected['HostConfig']['ReadonlyRootfs'] is True
    assert inspected['HostConfig']['NetworkMode'] == 'none'
    inspected_roots = [item.split('=', 1)[1] for item in inspected['Config']['Env']
                       if item.startswith('PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT=')]
    assert inspected_roots == roots
    inspected_mounts = [row for row in inspected['Mounts'] if row['Destination'] == root]
    assert len(inspected_mounts) == 1 and inspected_mounts[0]['Source'] == root
    assert inspected_mounts[0]['RW'] is True
    cleanup = producer['container_cleanup']
    assert isinstance(cleanup, list) and cleanup and all(row.get('returncode') == 0 for row in cleanup)
    matched = [row for row in cleanup if row.get('name') == name]
    assert len(matched) == 1
    cleanup_commands = [row for row in commands if row.get('argv') ==
                        ['sudo', '-n', 'docker', 'rm', '--force', name]]
    assert len(cleanup_commands) == 1 and cleanup_commands[0]['returncode'] == 0
    return {'privateRootEnvironmentValues': roots, 'sourceContainerCount': 1,
            'sourceContainersMatchedSuccessfulCleanup': 1, 'cleanupEntries': len(cleanup),
            'allReportedContainerCleanupReturnedZero': True,
            'sourceContainerCleanupExplicitlyBound': True,
            'containerStoppedBeforeCleanup': True,
            'originalCustomFixtureExitCode': run['returncode'],
            'privateRootMounts': [{'containerMount': root, 'hostMount': root,
                'fixtureRootInContainer': root, 'fixtureRootOnProducerHost': root,
                'walletRootInContainer': str(path/'TestLoadedAccountCustomSchemaSource'),
                'walletRootOnProducerHost': str(path/'TestLoadedAccountCustomSchemaSource')}],
            'walletRootPathExplicitlyBound': True,
            'archiverIncludesEntireFixturesRoot': True,
            'archiverExcludesSiblingDirectories': ['go-build', 'work'],
            'producerMetadataFieldNames': sorted(producer),
            'rawCommandsOrSecretsExposed': False,
            'unarchivedProducerHostDirectoryCurrentlyInspected': False}


def main():
    if sys.flags.optimize:
        raise RuntimeError('Forensic guards require assertions; optimized execution is refused.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    assert out.parent == OUT_PARENT and re.fullmatch(r'attempt[1-9][0-9]?', out.name)
    physical(OUT_PARENT.parent)
    if not OUT_PARENT.exists():
        OUT_PARENT.mkdir(mode=0o700)
    physical(OUT_PARENT)
    assert not os.path.lexists(out)
    os.umask(0o077); out.mkdir(mode=0o700)
    result = {'status': 'FAIL', 'protocol': 'pinkha-original156-private-material-inventory-v1', 'errors': [], 'commands': [],
              'accountExtracted': False, 'accountOpened': False, 'SQLiteConnections': 0, 'decryptionAttempts': 0,
              'privateCredentialValuesExposed': False, 'peerWalletsRead': False, 'nativeBuilds': 0, 'nativeTests': 0,
              'original182Replayed': False, 'originalHistoryReconstructed': False, 'sourceAdmissionPromoted': False,
              'resourcePolicy': {'purpose': 'independent bounded read-only archive inventory',
                  'nativeBuildEmergencyFloorUnchanged': 2*1024**3, 'nativeControllerGuardReusedOrRelaxed': False,
                  'rootReadOnlyFloorBytes': ROOT_READ_ONLY_FLOOR, 'rootBulkWrites': 0,
                  'developmentRuntimeFloorBytes': DEV_FLOOR, 'developmentAdmissionBytes': DEV_ADMISSION,
                  'outputCapBytes': OUTPUT_CAP, 'maximumSeconds': DEADLINE,
                  'initialMemAvailableBytes': 512*MIB, 'minimumMemAvailableBytes': MEMORY_FLOOR}}
    began = time.monotonic(); process = stream = helper = None
    observed_absent = False; frozen = []; source_files = {}; controller = None
    try:
        result['phase'] = 'read-only-control-and-source-admission'
        helper, helper_bytes = load_helper()
        controller = helper.read_frozen(physical(Path(__file__)))
        result['controllerSHA256'] = sha(controller)
        signal.signal(signal.SIGTERM, helper.interrupted); signal.signal(signal.SIGINT, helper.interrupted)
        mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
        result['inheritedBlockedSignals'] = sorted(int(x) for x in mask)
        assert shutil.disk_usage(out).free >= DEV_ADMISSION and available_memory() >= 512*MIB
        guard(out, began, result)
        def read_control(path, pin):
            value = helper.read_frozen(physical(path)); assert sha(value) == pin
            frozen.append((path, pin)); return value
        public_pins = json.loads(read_control(Path(__file__).with_name('public-producer-pins.json'), PUBLIC_PINS_SHA))
        assert public_pins['producerCommit'] == PRODUCER_COMMIT and public_pins['runID'] == 45492064232
        assert public_pins['jobID'] == 138792712711 and len(public_pins['files']) == 8
        public = {}
        for row in public_pins['files']:
            assert row['name'] == Path(row['name']).name and row['name'] not in public
            value = read_control(Path(__file__).parent/'public-producer'/row['name'], row['sha256'])
            assert len(value) == row['bytes']; public[row['name']] = value
        workflow_run = json.loads(public['producer-run.json'])
        assert workflow_run['id'] == 45492064232 and workflow_run['head_sha'] == PRODUCER_COMMIT
        assert workflow_run['status'] == 'completed' and workflow_run['conclusion'] == 'failure'
        workflow_jobs = json.loads(public['producer-jobs.json'])
        jobs = [row for row in workflow_jobs['jobs'] if row['id'] == 138792712711]
        assert len(jobs) == 1
        job = jobs[0]
        assert job['name'] == 'native-source-file-peers' and job['labels'] == ['ubuntu-24.04-arm']
        assert job['runner_group_name'] == 'GitHub Actions' and job['runner_name'] == 'GitHub Actions 1000025729'
        assert job['status'] == 'completed' and job['conclusion'] == 'failure'
        schema_delta = json.loads(public['original-custom-schema-delta.json'])
        assert sha(public['original-custom-schema-delta.json']) == CUSTOM_DELTA_SHA
        custom_rows = [row for row in schema_delta['files']
                       if row['path'] == 'core/application/loaded_custom_schema_source_test.go']
        assert len(custom_rows) == 1
        custom_row = custom_rows[0]; custom_source = public['original-custom-schema.go']
        assert custom_row['operation'] == 'A' and custom_row['bytes'] == len(custom_source) == 15728
        assert custom_row['sha256'] == sha(custom_source) == CUSTOM_SOURCE_SHA
        assert custom_row['git_blob_sha1'] == hashlib.sha1(b'blob '+str(len(custom_source)).encode()+b'\0'+custom_source).hexdigest()
        assert b'f := newLoadedAccountFixture(t)' in custom_source
        assert b'rawObject(id, model.SmartBlockType_Page, "")' in custom_source
        assert b'ordinaryPageKey' not in custom_source
        assert b'if path.name not in ("go-build", "work"):' in public['producer-portable.py']
        assert b'archive.add(path, arcname="private/" + path.name, recursive=True)' in public['producer-portable.py']
        assert b'"PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT": str(self.private / "fixtures")' in public['producer-portable.py']
        assert b'self.base = Path(os.environ["RUNNER_TEMP"]) / "pinkha-native-file-peer"' in public['producer-native-file-peer.py']
        assert b'run: python3 Tools/AnyEngineValidation/native_file_peer/run_native.py' in public['producer-workflow.yml']
        index = json.loads(read_control(INDEX, INDEX_SHA))
        original = {row['path']: row for row in index['members']}
        assert len(original) == len(index['members']) == 1039
        prior = json.loads(read_control(PRIOR, PRIOR_SHA))
        assert prior['originalAccountSHA256'] == ACCOUNT_SHA and prior['originalSpaceSHA256'] == SPACE_SHA
        read_control(RETIREMENT, RETIREMENT_SHA)
        read_control(RETIREMENT.parent/'restoration-map.json', RESTORE_SHA)
        custody = json.loads(read_control(E_PARENT/'attempt1/result.json', E_CUSTODY_SHA))
        assert custody['status'] == 'PASS_THREE_E_ROOTS_EXACT_PHYSICAL_CUSTODY_STABLE_ORIGINAL_ALIASES'
        assert custody['controllerSHA256'] == E_CONTROLLER_SHA and custody['controllerSourceUnchanged']
        inventory = json.loads(read_control(SOURCE.parent/'source-before.json', SOURCE_INVENTORY_SHA))
        pins_path = physical(Path(__file__).with_name('source-pins.json'))
        pins = json.loads(read_control(pins_path, PINS_SHA))
        assert len(pins['files']) == 12 and pins['originalAuthorityReceiptSHA256'] == PRIOR_SHA
        for row in pins['files']:
            name = row['scope']+'/'+row['path']
            assert row['scope'] in ('heart', 'sync') and '..' not in PurePosixPath(name).parts
            assert inventory[name] == {'bytes': row['bytes'], 'sha256': row['sha256']}
            data = read_control(SOURCE/name, row['sha256'])
            assert len(data) == row['bytes']; source_files[name] = data
        assert sha(ACCOUNT.encode()) == ACCOUNT_SHA
        account_names = {name for name in original if name.startswith(ACCOUNT_PREFIX)}
        assert len(account_names) == 28 and sum(original[name]['bytes'] for name in account_names) == 3225222
        selected_names = account_names | METADATA_MEMBERS
        assert selected_names.issubset(original)
        result['selectedMemberCount'] = len(selected_names)
        selected, classifications, candidates, source_matches = {}, [], [], []
        source_metadata_custom_rows = []
        result['phase'] = 'full-compressed-stream-and-selected-original-members'
        with (out/'source-stream-stderr.log').open('xb') as stderr:
            process = subprocess.Popen(helper.remote_command(), stdout=subprocess.PIPE, stderr=stderr, start_new_session=True)
            stream = ArchiveStream(process.stdout, out, began, result)
            with tarfile.open(fileobj=stream, mode='r|gz') as archive:
                for member in archive:
                    guard(out, began, result)
                    if member.name not in selected_names:
                        continue
                    assert member.name not in selected and member.isfile() and not member.issym() and not member.islnk()
                    expected = original[member.name]
                    maximum = 24*MIB if member.name == 'private/source-metadata/manifest.json' else MIB
                    assert member.size == expected['bytes'] and member.size <= maximum
                    data = archive.extractfile(member).read(member.size+1)
                    assert len(data) == member.size and sha(data) == expected['sha256']
                    row = {'path': member.name, 'bytes': len(data), 'sha256': sha(data)}
                    if member.name in account_names:
                        classified, found = classify_account(member.name[len(ACCOUNT_PREFIX):], data)
                        classifications.append(classified)
                        candidates.extend({'member': member.name, **hit} for hit in found)
                    elif member.name == 'private/source-metadata/manifest.json':
                        assert sha(data) == SOURCE_METADATA_SHA
                        metadata = json.loads(data)
                        assert metadata['file_columns_schema'] == 'loaded-account-source-file-columns-v1'
                        rows = metadata['files']['rows']
                        assert len(rows) == 59826
                        for pin in pins['files']:
                            commit = 'c005bd6cde8d8f8a6007c35f06894f3d89f9f07c' if pin['scope'] == 'sync' else '24dc6393b30e6d1d80ec28ff624060af9bb4327a'
                            found = [value for value in rows if value[0].endswith('/'+pin['path']) and
                                     isinstance(value[6], dict) and value[6].get('commit') == commit]
                            assert len(found) == 1 and found[0][4] == pin['sha256']
                            source_matches.append({'scope': pin['scope'], 'path': pin['path'], 'bytes': pin['bytes'],
                                                   'sha256': pin['sha256'], 'originalCommit': commit})
                        source_metadata_custom_rows = [{'sourcePath': value[0], 'sha256': value[4],
                            'originalCommit': value[6].get('commit') if isinstance(value[6], dict) else None,
                            'gitBlobSHA1': value[6].get('git_blob_sha1') if isinstance(value[6], dict) else None}
                            for value in rows if value[0].endswith('/core/application/loaded_custom_schema_source_test.go')]
                        del rows, metadata
                    else:
                        # Only bounded producer/source metadata is retained in
                        # memory. Account-file bytes are never retained here.
                        row['privateInMemoryValue'] = data
                    selected[member.name] = row
                    del data
            while stream.read(MIB):
                pass
            process.wait(timeout=max(1, DEADLINE-int(time.monotonic()-began)))
        assert process.returncode == 0 and helper.absent(process.pid)
        observed_absent = True
        assert stream.eof and stream.count == ARCHIVE_BYTES and stream.hasher.hexdigest() == ARCHIVE_SHA
        assert set(selected) == selected_names
        result['phase'] = 'exact-original-producer-account-and-source-joins'
        remote_bytes = (out/'source-stream-stderr.log').read_bytes(); assert len(remote_bytes) < 16*1024
        remote = json.loads(remote_bytes)
        assert remote['source']['host'] == 'DAVID_AND_GOLDY' and remote['streamedBytes'] == ARCHIVE_BYTES
        assert remote['readOnlySharedHandle'] is True
        result['originalArchiveSHA256'] = ARCHIVE_SHA; result['streamedCompressedBytes'] = ARCHIVE_BYTES
        def meta(name):
            return json.loads(selected[name]['privateInMemoryValue'])
        manifest = meta(MANIFEST_NAME)
        assert selected[MANIFEST_NAME]['sha256'] == MANIFEST_SHA
        assert manifest['Receipt']['Source']['accountSHA256'] == ACCOUNT_SHA
        assert manifest['Receipt']['Source']['source']['spaceSHA256'] == SPACE_SHA
        assert any(sha(row['relativePath'].split('/')[1].encode()) == SPACE_SHA for row in classifications
                   if row['relativePath'].startswith('spaceStoreNew/') and row['relativePath'].endswith('/store.db'))
        expected_commit = '24dc6393b30e6d1d80ec28ff624060af9bb4327a'
        custom_deltas = []
        for name in DELTAS:
            delta = meta('private/source-metadata/'+name)
            assert delta['base_heart_commit'] == expected_commit
            changed = [row['path'] for row in delta.get('files', [])]
            if 'path' in delta:
                changed.append(delta['path'])
            assert not set(changed).intersection(row['path'] for row in pins['files'] if row['scope'] == 'heart')
            expected_commit = delta['derived_heart_commit']
            custom_deltas.append({'name': name, 'sha256': selected['private/source-metadata/'+name]['sha256'],
                                 'customFixtureRows': [{key: row[key] for key in ('path', 'sha256', 'bytes', 'git_blob_sha1') if key in row}
                                     for row in delta.get('files', [])
                                     if row.get('path') == 'core/application/loaded_custom_schema_source_test.go']})
        producer = meta('private/result.json')
        assert producer['heart_sha'] == expected_commit == '65caee9bfc386c2f9182564d6ad1eb2f02cfadd1'
        assert producer['compiled_source_unchanged'] is True and len(source_matches) == 12
        assert producer['controller_sha'] == PRODUCER_COMMIT and str(producer['run_id']) == '45492064232'
        assert str(producer['run_attempt']) == '1'
        assert selected['private/source-metadata/native-custom-schema-checkpoint-delta-v1.json']['privateInMemoryValue'] == public['original-custom-schema-delta.json']
        commands = meta('private/commands.json')
        inspection_member = 'private/commands/native-custom-schema-inspect.stdout'
        inspection_command = [row for row in commands if row.get('label') == 'native-custom-schema-inspect']
        assert len(inspection_command) == 1 and inspection_command[0]['stdout_sha256'] == selected[inspection_member]['sha256']
        location = producer_location(commands, producer, meta(inspection_member))
        small = {}
        for name in [FIXTURE+'.anytype-locks/'+ACCOUNT+'.owner.json', FIXTURE+'native-custom-schema-capture-attempt-1.json']:
            value = meta(name)
            assert isinstance(value, dict)
            small[name] = {'fieldNames': sorted(value), 'credentialValuesExposed': False}
            candidates.extend({'member': name, **hit} for hit in json_candidates(value))
        config = next(row for row in classifications if row['relativePath'] == 'config.json')
        assert config['allFieldsInOriginalConfigurationSchema']
        stdout = selected['private/commands/native-custom-schema.stdout']['privateInMemoryValue']
        stdout_text = stdout.decode('utf-8')
        keywords = sorted({key for key in CREDENTIAL_KEYS if re.search(r'\b'+re.escape(key)+r'\s*[:=]', stdout_text, re.I)})
        candidates.extend({'member': 'private/commands/native-custom-schema.stdout', 'fieldKind': key,
                           'valuePresent': 'unparsed potential field', 'valueExposed': False} for key in keywords)
        # These source checks classify the serialization call chain. They are
        # neither a cryptographic test nor a decryption attempt on device.key.
        assert b'mnemonic, _, err := f.service.WalletCreate' in source_files['heart/core/application/loaded_witness_fixture_test.go']
        assert b'f.mnemonic = mnemonic' in source_files['heart/core/application/loaded_witness_fixture_test.go']
        assert b'pk.GetPublic().Encrypt(proto)' in source_files['heart/pkg/lib/core/wallet.go']
        assert b'r.accountKey.Decrypt(b)' in source_files['heart/core/wallet/wallet.go']
        assert b'if r.accountKey == nil' in source_files['heart/core/wallet/wallet.go']
        assert b'box.Seal(epk[:], msg' in source_files['sync/util/crypto/x25519.go']
        assert b'copy(epk[:], encrypted[:32])' in source_files['sync/util/crypto/x25519.go']
        assert b'Ed25519Private = 1;' in source_files['sync/util/crypto/cryptoproto/protos/crypto.proto']
        assert b'if req.Mnemonic == "" && req.AccountKey == ""' in source_files['heart/core/application/wallet_recover.go']
        result.update(originalAccountSHA256=ACCOUNT_SHA, originalSpaceSHA256=SPACE_SHA,
            originalAccountFiles=sorted(classifications, key=lambda row: row['relativePath']), originalAccountBytes=3225222,
            originalAccountFilesActuallyHashed=28, originalCredentialCandidates=candidates,
            smallOriginalMetadata=small, originalPublicSourceMatches=source_matches,
            originalCustomFixtureSourceMetadata=source_metadata_custom_rows, originalCustomFixtureDeltaMetadata=custom_deltas,
            originalExactCustomFixtureSource={'bytes': len(custom_source), 'sha256': CUSTOM_SOURCE_SHA,
                'gitBlobSHA1': custom_row['git_blob_sha1'], 'originalDeltaByteEquality': True,
                'derivedHeartCommit': expected_commit, 'laterOrdinaryPageKeyFixApplied': False},
            originalProducerPublicSource={'manifestSHA256': PUBLIC_PINS_SHA, 'commit': PRODUCER_COMMIT,
                'runID': workflow_run['id'], 'jobID': job['id'], 'labels': job['labels'],
                'runnerName': job['runner_name'], 'runnerGroup': job['runner_group_name'],
                'originalStatus': workflow_run['conclusion'], 'files': public_pins['files'],
                'sourceOnlyReadNotExecuted': True},
            originalProducerWalletRootAndCleanup=location,
            selectedMemberEvidence=[{k: v for k, v in row.items() if k != 'privateInMemoryValue'} for row in selected.values()],
            priorAuthorityReceiptRetainedUnchanged=PRIOR_SHA, originalArchiveRestored=False,
            sourceCustodyReceiptSHA256=E_CUSTODY_SHA, sourceInventorySHA256=SOURCE_INVENTORY_SHA,
            helperSHA256=HELPER_SHA, selectedHelperFunctions=['remote_command', 'read_frozen', 'finish_group', 'interrupted', 'absent'],
            originalApplicationAPICredentialRecovered=False, deviceEnvelopeAuthenticated=False,
            nativeAPIRecoveryFromDirectoryAttempted=False,
            broaderUnarchivedCredentialAbsenceProven=False)
        result['status'] = 'PASS_EXACT_ORIGINAL28_BYTE_INVENTORY_AUTHORITY_NOT_RECOVERED'
        if candidates:
            result['status'] = 'EXACT_ORIGINAL28_INVENTORY_HAS_UNRESOLVED_CREDENTIAL_CANDIDATE'
        if not location['walletRootPathExplicitlyBound'] or not location['sourceContainerCleanupExplicitlyBound']:
            result['remainingProducerLocationGate'] = 'Original command structure needs a focused path/cleanup follow-up; no global credential-absence claim.'
        guard(out, began, result)
        result['phase'] = 'read-only-inventory-completed'
    except BaseException as error:
        result['status'] = 'FAIL'
        # Do not interpolate an exception's possibly secret-bearing value.
        frames = traceback.extract_tb(error.__traceback__)
        result['errors'].append({'type': type(error).__name__,
            'frames': [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name} for frame in frames]})
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN); signal.signal(signal.SIGINT, signal.SIG_IGN)
        if process is not None and helper is not None:
            helper.finish_group(process, result, observed_absent)
        try:
            assert helper is not None and controller is not None
            assert helper.read_frozen(Path(__file__)) == controller
            assert sha(helper.read_frozen(Path(__file__).with_name('reviewed_stream_lifecycle.py'))) == HELPER_SHA
            for path, pin in frozen:
                assert sha(helper.read_frozen(path)) == pin
            result['allOriginalControlsSelectedSourcesAndControllerUnchanged'] = True
            (out/'controller.py').write_bytes(controller)
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'finalIntegrity': 'exact control/source/finalization check failed', 'type': type(error).__name__})
        result['seconds'] = round(time.monotonic()-began, 3)
        encoded = (json.dumps(result, sort_keys=True, indent=2)+'\n').encode()
        assert len(encoded) < 128*1024
        fd = os.open(out/'result.json', os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as receipt:
            receipt.write(encoded); receipt.flush(); os.fsync(receipt.fileno())
    print(json.dumps({'status': result['status'], 'result': str(out/'result.json'), 'sha256': sha(encoded),
                      'seconds': result['seconds'], 'errorCount': len(result['errors']),
                      'accountOpened': False, 'privateCredentialValuesExposed': False}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
