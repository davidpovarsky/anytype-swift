#!/usr/bin/env python3
"""SOURCE-ONLY DRAFT: GET-only continuation after a separately qualified fix.

The native app may open its existing stores through ordinary startup. This
controller never opens, inventories, copies or exports account-file contents.
No constructor, role, invitation, file upload, retry or restoration is exposed.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socket
import stat
import sys
import time

ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
OUTPUT_PARENT = ROOT/'current-authority-http-20261127'
BASELINE = ROOT/'original-native-authority-reader-continuation1/result.json'
BASELINE_SHA = 'ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab'
FILES_RECEIPT = ROOT/'original-files-lan-progress1/result.json'
FILES_SHA = '0c0d4622bff1075d7da331b3f2d393aa536ce688e05a92013defde153210c5da'
PRIOR_CUSTODY = '792268b4d7448d9c9b6665ee6388f26c18e5de0635aa05f1b390db7f20a5567d'
BASE_SOURCE = 'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a'
PATCH_SHA = '874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f'
CANDIDATE_SHA = 'ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896'
BASE_MANIFEST = ROOT/'lan-progress-native1/source-manifest.json'
CANDIDATE = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-lifetime-draft-20261127-attempt2')
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
FRESH_FIXTURE = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-source-20261127-attempt2/files_readguard_fresh_linux_test.go')
FRESH_FIXTURE_SHA = 'b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b'
FRESH_METHODS = ('TestFilesOpenFreshCachedReaderStopsAtSignedRemoval', 'TestFilesOpenFreshAwaitedFetchDiscardsAfterSignedRemoval')
QUALIFICATION_PARENTS = {
    'synthetic21': Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127'),
    'freshFilesOpen2': Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127'),
}
OWNER = 'A7MAdySTn1MR4Fb3gDr67ZeXEvt8fqNjtHEwB3b9kUGFZZya'
MEMBER = 'AAFSi1CkNvwiTLAkKWQF9K5GnLcfFaqvfYYCa1zmJWETjuyR'
SPACE = 'bafyreigwbj5ipsthay6xcrt6xcw5hpuagje2jiupq4zhidbevd4miqbrmu.qhz8hrb21y1l'
OBJECT = 'bafyreicytuyyuw7nu6cklsgptni4k5xoyi3u4suijh6lp5moki2nvtpi7e'
DATA_DIRS = {'owner': ROOT/'attempt1/alice', 'member': ROOT/'attempt1/bob'}
NODECONF = Path('/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network/mac-public-nodeconf.yml')
NODECONF_SHA = 'fc43639b27c8c7ab50897542a99ecddd3266e85eedf575625d20391684e476e0'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_LIBRARY_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OFFLINE_LIBRARY = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
PREFIX = '/v1/spaces/'+SPACE
FILE_PREFIX = PREFIX+'/files/'
DENIALS = (
    ('canary-full', 'E9ZfwB8Biag/content', None),
    ('canary-range', 'E9ZfwB8Biag/content', 'bytes=0-31'),
    ('large-cached-range', 'hs6LTsotxAY/content', 'bytes=200000-232767'),
    ('image-full', '9DSkw6W3eqv/content', None),
    ('thumbnail-direct', 'SbLLxZDbq59/content', None),
    ('thumbnail-resolution', '9DSkw6W3eqv/content?variant=thumb', None),
    ('member-authored', 'AEhbwaXwY7S/content', None),
)
OWNER_FILES = ('E9ZfwB8Biag', 'hs6LTsotxAY', '9DSkw6W3eqv', 'SbLLxZDbq59')
ALL_FILES = OWNER_FILES+('AEhbwaXwY7S',)
MIB = 1024**2
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
ROOT_RESERVE = 128*MIB
DEV_RESERVE = 32*MIB
OUTPUT_CAP = 32*MIB
LOG_CAP = 8*MIB


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def public_bytes(path, maximum=8*MIB):
    """Only caller-allowlisted public source/artifact/control paths use this."""
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical public input')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size<=maximum, 'bounded ordinary public input')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno())==before, 'public input identity changed')
        data = stream.read(maximum+1)
        require(os.fstat(stream.fileno())==before, 'public input changed during read')
    require(path.lstat()==before and len(data)==before.st_size, 'public input raced')
    return data


def json_object(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'JSON object required')
    return value


def physical_directory(path):
    # Metadata of the directory itself only; no account-member enumeration.
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical directory required')
    require(stat.S_ISDIR(path.lstat().st_mode), 'ordinary directory required')


@contextmanager
def absolute_http_deadline(seconds):
    """A complete GET must finish even if a peer trickles header/body bytes.

    Native commands have already been spawned before this main-thread scope;
    no child launch happens while its process-wide timer is active. Preserve
    the caller's handler/mask, refuse a pre-existing timer, and consume only a
    pending alarm from this owned timer before restoring the previous handler.
    """
    handoff_signals = {signal.SIGALRM, signal.SIGTERM, signal.SIGINT}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, handoff_signals)
    previous_handler = signal.getsignal(signal.SIGALRM)
    deadline = time.monotonic()+seconds
    timer_owned = False

    def expired(_number, _frame):
        raise TimeoutError('absolute HTTP request deadline')

    try:
        require(signal.getitimer(signal.ITIMER_REAL)==(0.0, 0.0), 'an existing timer prevents HTTP deadline ownership')
        require(signal.SIGALRM not in signal.sigpending(), 'an existing alarm is pending')
        signal.signal(signal.SIGALRM, expired)
        timer_owned = True
        signal.setitimer(signal.ITIMER_REAL, seconds)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask-{signal.SIGALRM})
        yield
        require(time.monotonic()<=deadline, 'absolute HTTP deadline expired at completion')
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, handoff_signals)
        if timer_owned:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if signal.SIGALRM in signal.sigpending():
                signal.sigtimedwait({signal.SIGALRM}, 0)
            signal.signal(signal.SIGALRM, previous_handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--producer-receipt', required=True, type=Path)
    parser.add_argument('--producer-sha256', required=True)
    args = parser.parse_args()
    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'fixed authorized Oracle host')
    require(args.output.parent==OUTPUT_PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', args.output.name), 'owned output scope')
    producer_dir = args.producer_receipt.parent
    require(producer_dir.parent==ROOT and re.fullmatch(r'readguard-native[1-9][0-9]{0,2}', producer_dir.name), 'future native producer scope')
    require(args.producer_receipt.name=='result.json' and re.fullmatch(r'[0-9a-f]{64}', args.producer_sha256), 'pinned producer receipt')
    physical_directory(ROOT)
    os.umask(0o077)
    if not OUTPUT_PARENT.exists():
        OUTPUT_PARENT.mkdir(mode=0o700)
    physical_directory(OUTPUT_PARENT)
    output = args.output
    output.mkdir(mode=0o700, exist_ok=False)
    # Exclusive reservation precedes every try/finally persistence path.
    with (output/'result.json').open('xb') as stream:
        stream.write(b'{}\n'); stream.flush(); os.fsync(stream.fileno())
    began = time.monotonic()
    public_inputs = {}
    expected_source = None
    source = None
    producer = None
    receipt_serial = 0
    result = {
        'protocol': 'pinkha-current-authority-get-only-v1', 'status': 'RUNNING',
        'historicalFailureSHA256': BASELINE_SHA, 'lastKnownClosedCustodySHA256': PRIOR_CUSTODY,
        'freshAccountByteCustodyClaim': False, 'independentSeventhRecordExportClaim': False,
        'accountFileReadsByController': 0, 'accountCopies': 0, 'privateRecordExports': 0,
        'domainMutationRequests': 0, 'accountInitializations': 0, 'roleRestorations': 0,
        'uploadCalls': 0, 'compilerInvocations': 0, 'previousInsecureGETReplayed': False,
        'nativeOperationalStoreWritesPossible': True, 'heldSDKReaderAcceptance': False,
        'historicalPayloadRoutesRequested': 0, 'processes': [], 'phases': [], 'requests': [],
        'errors': [], 'completionErrors': [], 'canaryCurrentlyUncachedClaim': False,
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
                           'rootAdmissionReserveBytes': ROOT_RESERVE, 'developmentAdmissionReserveBytes': DEV_RESERVE,
                           'ownedOutputCapBytes': OUTPUT_CAP, 'logCapPerProcessBytes': LOG_CAP,
                           'controllerDeadlineSeconds': 360, 'requiredOuterTimeoutSeconds': 480,
                           'workersPerNative': 2, 'memoryLimitPerNative': '512MiB',
                           'maximumConcurrentNativeProcesses': 1},
    }

    def save_json(path, value):
        nonlocal receipt_serial
        require(path.is_relative_to(output), 'owned receipt destination')
        # A signal may interrupt a prior private staging write. Preserve that
        # partial file and use a fresh exclusive name for the final FAIL.
        receipt_serial += 1
        temporary = path.with_name(path.name+'.next-'+str(receipt_serial))
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def save():
        result['seconds'] = round(time.monotonic()-began, 3)
        save_json(output/'result.json', result)

    def save_command(path, value):
        require(path.parent.parent==output and path.parent.name in ('owner-observation', 'member-online', 'member-offline'), 'owned native phase')
        require(path.name in ('started.json', 'result.json'), 'owned helper receipt')
        save_json(path, value); save()

    def guard(admit=False):
        require(time.monotonic()-began<360, '360-second current-authority deadline')
        require(not (output/'abort').exists(), 'owned controller abort')
        free = {name: shutil.disk_usage(path).free for name, path in [('root', '/'), ('development', '/mnt/development')]}
        for name, floor, reserve in [('root', ROOT_FLOOR, ROOT_RESERVE), ('development', DEV_FLOOR, DEV_RESERVE)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
            require(free[name]>=floor+(reserve if admit else 0), name+' unchanged storage gate')
        allocated = 0; count = 0
        for parent, directories, files in os.walk(output, followlinks=False):
            for name in directories:
                require(not (Path(parent)/name).is_symlink(), 'owned output directory alias')
            for name in files:
                path = Path(parent)/name; info = path.lstat()
                require(stat.S_ISREG(info.st_mode), 'owned output special file')
                allocated += max(info.st_size, info.st_blocks*512); count += 1
                if name=='original.log': require(info.st_size<=LOG_CAP, 'bounded native log')
        require(count<=1000 and allocated<=OUTPUT_CAP, 'owned output bound')
        result['peakOwnedBytes'] = max(allocated, result.get('peakOwnedBytes', 0))
        return free

    def pin(path, wanted, maximum=8*MIB):
        data = public_bytes(path, maximum)
        require(identity(data)['sha256']==wanted, 'public input pin differs: '+str(path))
        public_inputs[str(path)] = {'identity': identity(data), 'maximum': maximum}
        return data

    def source_inventory(root, expected):
        physical_directory(root)
        names = set()
        for parent, directories, files in os.walk(root, followlinks=False):
            for name in directories: physical_directory(Path(parent)/name)
            for name in files: names.add((Path(parent)/name).relative_to(root).as_posix())
        require(names==set(expected) and 1500<=len(names)<=5000, 'complete native source closure')
        for index, (name, wanted) in enumerate(sorted(expected.items())):
            relative = PurePosixPath(name)
            require(not relative.is_absolute() and str(relative)==name and '..' not in relative.parts, 'source manifest path')
            require(isinstance(wanted, dict) and set(wanted)=={'bytes', 'sha256'}, 'source member identity')
            require(identity(public_bytes(root/name, 256*MIB))==wanted, 'source member differs: '+name)
            if index%64==0: guard()

    def no_competing_account_process():
        # Read process metadata only. Never read any account file through /proc.
        found = []; started = time.monotonic(); examined = 0
        prefixes = [os.fsencode(str(path)) for path in DATA_DIRS.values()]
        for directory in Path('/proc').iterdir():
            if not directory.name.isdecimal() or int(directory.name)==os.getpid(): continue
            examined += 1
            require(examined<=100000 and time.monotonic()-started<10, 'bounded account process census')
            try:
                with (directory/'cmdline').open('rb') as stream: raw = stream.read(131073)
            except (FileNotFoundError, ProcessLookupError): continue
            require(len(raw)<=131072, 'bounded process metadata')
            if any(prefix in raw for prefix in prefixes): found.append(int(directory.name))
        require(not found, 'a process already references an original account directory')
        return {'processesExamined': examined, 'matchingProcesses': 0, 'accountContentsRead': False}

    def interrupted(number, _frame):
        raise RuntimeError('current-authority controller interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        own_path = Path(__file__).resolve()
        public_inputs[str(own_path)] = {'identity': identity(public_bytes(own_path)), 'maximum': 8*MIB}
        result['controller'] = public_inputs[str(own_path)]['identity']
        helper_path = own_path.with_name('owned_swift_commands.py')
        pin(helper_path, HELPER_SHA)
        pin(HELPER_PROOF, HELPER_PROOF_SHA)
        spec = importlib.util.spec_from_file_location('qualified_current_authority_owned', helper_path)
        owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
        result['ownershipHelperSHA256'] = HELPER_SHA
        result['reusedOwnershipFiveControlReceiptSHA256'] = HELPER_PROOF_SHA
        result['admissionFreeBytes'] = guard(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available>=2*1024**3, 'native memory admission')
        result['memAvailableBefore'] = available
        baseline = json_object(pin(BASELINE, BASELINE_SHA))
        previous_files = json_object(pin(FILES_RECEIPT, FILES_SHA))
        require(baseline['status']=='FAIL' and baseline['finalAccountInventorySHA256']==PRIOR_CUSTODY, 'published baseline custody')
        require(baseline['accounts']==previous_files['accounts']=={'alice': OWNER, 'bob': MEMBER}, 'public account lineage')
        require(baseline['spaceId']==previous_files['spaceId']==SPACE and baseline['objectId']==previous_files['objectId']==OBJECT, 'public Space/object lineage')
        require(baseline['removedMembership']=={'identity': MEMBER, 'permission': 'none', 'status': 'removed'}, 'original observed removal')
        require(baseline['restoreReaderAfterRevocationCalls']==0 and baseline['allOwnedGroupsPositivelyAbsent'], 'original failure remained closed and removed')
        require(len(baseline['mutations'])==1 and baseline['mutations'][0]['label']=='remove-original-bob' and baseline['mutations'][0]['status']==204, 'sole original removal')
        require(previous_files['actualFilesV2Acceptance'] is True, 'reuse actual prior file bindings')
        expected_files = {}
        for row in previous_files['files']:
            if row['fileId'] in ALL_FILES:
                expected_files[row['fileId']] = {'fileId': row['fileId'], 'objectId': OBJECT, 'rootCid': row['rootCid'],
                    'size': row['plaintextBytes'], 'name': row['name'], 'mime': row.get('storedMIME', row.get('mime', '')),
                    'inline': False, **{k: row[k] for k in ('variant', 'variantOf') if k in row}}
        for row in (baseline['revocationCanary']['metadata'], baseline['reusedConfirmedWriter']['attachment']['metadata']):
            expected_files[row['fileId']] = {k: row[k] for k in ('fileId', 'objectId', 'rootCid', 'size', 'name', 'inline')}
            expected_files[row['fileId']]['mime'] = row.get('mime', '')
        require(set(expected_files)==set(ALL_FILES), 'five fixed synthetic metadata bindings')
        result['syntheticFileBindings'] = expected_files

        # This producer contract has no qualifying instance yet. Its future
        # build is independent of this controller and must be reviewed/pinned.
        producer = json_object(pin(args.producer_receipt, args.producer_sha256))
        require(producer['protocol']=='pinkha-files-readguard-native-qualified-v1', 'future native producer protocol')
        require(producer['status']=='PASS_NATIVE_BUILD_AND_FRESH_FILES_OPEN2', 'full native producer not qualified')
        require(producer['baseSourceManifestSHA256']==BASE_SOURCE and producer['sdkReadguardPatchSHA256']==PATCH_SHA and producer['sdkReadguardCandidateSHA256']==CANDIDATE_SHA, 'exact production overlay composition')
        require(producer['commits']=={'any': '8fbd1e819fb132ac0e0a848d2ddf5c5714189b81', 'sdk': 'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9'}, 'Any/SDK producer versions')
        require(producer['syncModule']=='github.com/anyproto/any-sync@v0.13.8' and producer['productionOverlayApplications']==1, 'single standalone SDK overlay')
        require(producer['allOwnedGroupsPositivelyAbsent'] is True and producer['buildExitCode']==0, 'actual native producer closure')
        require(producer['errors']==[] and producer['completionErrors']==[], 'producer retained errors')
        # Reconstruct the exact complete source union independently of the
        # future producer's manifest. A header naming the correct patch does
        # not admit extra changes or a binary built from a different SDK.
        base_files = json_object(pin(BASE_MANIFEST, BASE_SOURCE))['files']
        require(len(base_files)==1599, 'qualified Any source member count')
        draft = json_object(pin(CANDIDATE/'manifest.json', CANDIDATE_SHA))
        require(draft['baseCurrentSourceManifestSHA256']==BASE_SOURCE and draft['patch']['sha256']==PATCH_SHA, 'source candidate base')
        require(len(draft['paths'])==10 and draft['productionPaths']==7 and draft['testPaths']==3, 'seven production paths and three synthetic test paths')
        pin(CANDIDATE/'sdk-files-readguard.patch', PATCH_SHA)
        union = dict(base_files)
        sdk_base = {name.removeprefix(SDK_PREFIX): value for name, value in base_files.items() if name.startswith(SDK_PREFIX)}
        require(len(sdk_base)==718, 'qualified SDK source member count')
        for name, change in sorted(draft['paths'].items()):
            relative = PurePosixPath(name)
            require(str(relative)==name and not relative.is_absolute() and '..' not in relative.parts and name.startswith('internal/'), 'candidate source path')
            key = SDK_PREFIX+name
            require(union.get(key)==change['before'], 'candidate before-image differs')
            actual = identity(pin(CANDIDATE/name, change['after']['sha256']))
            require(actual==change['after'], 'candidate after-image differs')
            union[key] = actual
        sdk_guard = {name.removeprefix(SDK_PREFIX): value for name, value in union.items() if name.startswith(SDK_PREFIX)}
        require(len(union)==1606 and len(sdk_guard)==725, 'guard source composition')
        fixture = identity(pin(FRESH_FIXTURE, FRESH_FIXTURE_SHA))
        fixture_key = SDK_PREFIX+FRESH_FIXTURE.name
        require(fixture_key not in union and producer['freshFilesFixture']==fixture, 'one fresh synthetic fixture')
        union[fixture_key] = fixture
        sdk_fresh = {name.removeprefix(SDK_PREFIX): value for name, value in union.items() if name.startswith(SDK_PREFIX)}
        require(len(union)==1607 and len(sdk_fresh)==726, 'fresh test composition')
        for name, expected_status in [('synthetic21', 'PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE'), ('freshFilesOpen2', 'PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2')]:
            reference = producer['qualifications'][name]
            qpath = Path(reference['path'])
            require(qpath.parent.parent==QUALIFICATION_PARENTS[name] and re.fullmatch(r'attempt[1-9][0-9]{0,2}', qpath.parent.name) and qpath.name=='result.json', 'fixed public qualification receipt location')
            value = json_object(pin(qpath, reference['sha256']))
            require(value['status']==expected_status and value['allOwnedGroupsPositivelyAbsent'], 'actual prerequisite receipt')
            require(value['errors']==[] and value['completionErrors']==[], 'prerequisite retained errors')
            if name=='synthetic21':
                admission = value['sourceAdmission']
                require(admission['baseManifestSHA256']==BASE_SOURCE and admission['candidateManifestSHA256']==CANDIDATE_SHA and admission['candidatePatchSHA256']==PATCH_SHA, 'synthetic qualification source binding')
                require(value['actualMethods']['totalRuns']==35 and value['actualMethods']['totalPasses']==35 and value['actualMethods']['skips']==0, 'all thirty-five signed unit events')
                qualified_manifest = json_object(pin(qpath.parent/'source-before.json', admission['sourceManifest']['sha256']))
                require(qualified_manifest==sdk_guard, 'actual synthetic source must equal this guard union')
            else:
                require(value['fixtureSource']==fixture and value['baseSourceManifestSHA256']==BASE_SOURCE and value['sdkReadguardCandidateSHA256']==CANDIDATE_SHA and value['sdkReadguardPatchSHA256']==PATCH_SHA, 'actual fresh SDK source binding')
                require(value['actualMethods']=={'names': sorted(FRESH_METHODS), 'totalRuns': 2, 'totalPasses': 2, 'skips': 0}, 'both actual Files.Open methods')
                require(value['retainedPrivateInputs']==0 and value['actualOSDenialVerified'] is True, 'fresh-only OS-isolated SDK qualification')
                qualified_manifest = json_object(pin(qpath.parent/'source-before.json', value['sourceManifestSHA256']))
                require(qualified_manifest==sdk_fresh, 'actual fresh SDK source must equal this producer subset')
        source = producer_dir/'source'
        manifest_path = producer_dir/'source-manifest.json'
        expected_source = json_object(pin(manifest_path, producer['sourceManifestSHA256']))['files']
        require(expected_source==union, 'native producer must contain exactly the qualified source union')
        source_inventory(source, expected_source)
        binary = producer_dir/'any'
        binary_identity = identity(pin(binary, producer['binarySHA256'], 128*MIB))
        require(producer['binaryBytes']==binary_identity['bytes'], 'native binary length')
        result['correctedNativeProducer'] = {'receiptSHA256': args.producer_sha256, 'binary': binary_identity,
            'sourceManifestSHA256': producer['sourceManifestSHA256'], 'sourceFiles': len(expected_source)}
        pin(NODECONF, NODECONF_SHA, 65536); pin(OFFLINE, OFFLINE_SHA, 65536)
        pin(OFFLINE_LIBRARY, OFFLINE_LIBRARY_SHA, 4*MIB)
        require(baseline['offlinePolicy']['helperSHA256']==OFFLINE_SHA and baseline['offlinePolicy']['actual']['librarySHA256']==OFFLINE_LIBRARY_SHA, 'prior actual OS policy binding')
        result['offlinePolicyReuse'] = {'actualPriorReceiptSHA256': BASELINE_SHA, 'helperSHA256': OFFLINE_SHA,
            'filterLibrarySHA256': OFFLINE_LIBRARY_SHA, 'unchangedProbeRerun': False}
        for directory in DATA_DIRS.values(): physical_directory(directory)
        result['closedPairProcessAdmission'] = no_competing_account_process()
        config = output/'network.yml'
        config_text = ('network:\n  nodeconfPath: '+str(NODECONF)+'\nindex:\n  embedder: none\np2p:\n'
                       '  enabled: true\n  localDiscovery: true\n  serviceName: _pinkha-fv2._tcp\n'
                       '  global:\n    enabled: false\n')
        with config.open('x') as stream: stream.write(config_text); stream.flush(); os.fsync(stream.fileno())
        public_inputs[str(config)] = {'identity': identity(config_text.encode()), 'maximum': 65536}

        metadata_paths = {'/v1/health', '/v1/account', PREFIX+'/members/me', PREFIX+'/members/'+MEMBER,
                          PREFIX+'/sync-status'}|{FILE_PREFIX+file_id for file_id in ALL_FILES}
        denial_paths = {(FILE_PREFIX+path, byte_range) for _, path, byte_range in DENIALS}

        def metadata_matches(value, file_id):
            wanted = expected_files[file_id]
            for key, desired in wanted.items():
                require(value.get(key, '')==desired if key=='mime' else value.get(key)==desired, 'synthetic file binding differs: '+key)
            require(isinstance(value.get('cached'), bool) and isinstance(value.get('durable'), bool), 'native file-state flags')
            return {k: value[k] for k in ('fileId', 'objectId', 'rootCid', 'size', 'cached', 'durable')}

        def run_phase(name, actor, offline):
            # There is at most one live native process. These checks inspect
            # only process metadata, public inputs and the directory itself.
            guard(); no_competing_account_process()
            for path in (binary, config, NODECONF, OFFLINE, OFFLINE_LIBRARY):
                admitted = public_inputs[str(path)]
                require(identity(public_bytes(path, admitted['maximum']))==admitted['identity'], 'phase input changed')
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
            argv = [str(binary), 'run', '--config', str(config), '--data-dir', str(DATA_DIRS[actor]), '--addr', '127.0.0.1:'+str(port)]
            if offline: argv = [sys.executable, '-B', str(OFFLINE), '--exec']+argv
            environment = {key: value for key, value in os.environ.items() if not key.startswith('ANY_')}
            environment.update(ANY_DATA_DIR=str(DATA_DIRS[actor]), GOMAXPROCS='2', GOMEMLIMIT='512MiB')
            phase = {'name': name, 'actor': actor, 'offline': offline, 'stepsCompleted': [], 'stopRequested': False,
                     'denials': [], 'membership': [], 'fileMetadata': []}
            result['phases'].append(phase); save()
            ledger_index = len(result['processes'])
            phase_started = time.monotonic(); state = {'readyAt': None, 'membershipWaitAt': None}
            phase_steps = [('health', None), ('identity', None), ('self-member', None)]
            if actor=='owner':
                phase_steps += [('removed-member', None)]+[('owner-file', f) for f in OWNER_FILES]+[('removed-member-final', None), ('self-member-final', None)]
            else:
                phase_steps += [('member-file', f) for f in ALL_FILES]
                if offline: phase_steps += [('offline-sync', None)]
                phase_steps += [('deny', check) for check in DENIALS]+[('self-member-final', None)]
            step_index = 0

            def request(path, byte_range=None, denial=False, optional_metadata=False, health=False):
                require((path, byte_range) in denial_paths if denial else path in metadata_paths and byte_range is None, 'GET allowlist')
                row = {'phase': name, 'method': 'GET', 'path': path, 'range': byte_range,
                       'stage': 'dispatching', 'bodyReadInvocations': 0, 'kind': 'content-denial' if denial else 'metadata'}
                result['requests'].append(row); save(); guard()
                # Only bounded transport work runs under the alarm. Persistence
                # happens after its handler/mask are restored, so an HTTP
                # deadline cannot interrupt the evidence-retention path.
                try:
                    with absolute_http_deadline(2 if health else 5):
                        raw = request_with_deadline(row, path, byte_range, denial, optional_metadata, health)
                    if health:
                        row['stage'] = 'ready-status'; save(); return {'ready': True}
                    row['response'] = identity(raw)
                    value = json_object(raw)
                    if row['status']==403:
                        error = value.get('error')
                        require(isinstance(error, dict) and error.get('code')=='acl.forbidden', 'exact current-authority error required')
                        row['errorCode'] = 'acl.forbidden'; row['stage'] = 'confirmed-typed-denial'; save()
                        return {'typedDenial': True}
                    row['stage'] = 'metadata-response'; save(); return value
                except BaseException as error:
                    row.setdefault('failure', {'type': type(error).__name__, 'message': str(error)})
                    save(); raise

            def request_with_deadline(row, path, byte_range, denial, optional_metadata, health):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2 if health else 5)
                response = None
                try:
                    headers = {'Connection': 'close'}
                    if byte_range is not None: headers['Range'] = byte_range
                    connection.request('GET', path, headers=headers)
                    response = connection.getresponse()
                    row['status'] = response.status
                    row['headers'] = {k: str(response.getheader(k) or '')[:1024] for k in ('Content-Type', 'Content-Length', 'Content-Range')}
                    allowed = (403,) if denial else ((200, 403) if optional_metadata else (200,))
                    if response.status not in allowed:
                        row['stage'] = 'unexpected-status-body-not-read'
                        raise AssertionError('unexpected HTTP status; content body not consumed')
                    if health:
                        return b''
                    maximum = 4096 if response.status==403 else 65536
                    row['bodyReadInvocations'] += 1
                    raw = response.read(maximum+1)
                    require(len(raw)<=maximum, 'bounded API envelope')
                    return raw
                finally:
                    # No redirects, proxy routing, retries or draining of an
                    # unexpected content body. http.client may buffer transport
                    # bytes while parsing headers; that is not a server PASS.
                    if response is not None: response.close()
                    connection.close()

            def observe():
                nonlocal step_index
                try:
                    guard()
                    if len(result['processes'])<=ledger_index: return None
                    process_row = result['processes'][ledger_index]
                    if process_row.get('exitCode') is not None or process_row.get('processGroupAbsent'):
                        # Final helper observation: never probe a historical PID.
                        return None
                    if 'pid' not in process_row: return None
                    if phase['stopRequested']: return None
                    pid = process_row['pid']
                    require(os.waitid(os.P_PID, pid, os.WEXITED|os.WNOHANG|os.WNOWAIT) is None, 'native exited before requested stop')
                    require(os.getpgid(pid)==pid and os.getsid(pid)==pid, 'owned live native group/session')
                    if step_index==len(phase_steps):
                        # The unchanged qualified helper still owns this exact
                        # unreaped child. Its PID cannot be recycled across
                        # this signal. No signal is sent after this latch.
                        phase['gracefulStopIntent'] = {'pid': pid, 'signal': int(signal.SIGTERM), 'leaderUnreaped': True}
                        save(); os.killpg(pid, signal.SIGTERM)
                        phase['stopRequested'] = True; process_row['expectedServiceShutdown'] = True
                        save(); return None
                    action, argument = phase_steps[step_index]
                    if action=='health':
                        try: request('/v1/health', health=True)
                        except (OSError, http.client.HTTPException):
                            require(time.monotonic()-phase_started<60, 'bounded native readiness'); return None
                        if offline:
                            fields = dict(line.split(':', 1) for line in Path('/proc/'+str(pid)+'/status').read_text().splitlines() if ':' in line)
                            require(fields['NoNewPrivs'].strip()=='1' and fields['Seccomp'].strip()=='2', 'actual inherited OS-denial state')
                            require(Path('/proc/'+str(pid)+'/exe').resolve()==binary, 'actual offline native executable')
                            phase['actualOSPolicy'] = {'noNewPrivileges': True, 'seccompFilterMode': 2, 'nativeExecutable': str(binary)}
                        state['readyAt'] = time.monotonic()
                    elif action=='identity':
                        value = request('/v1/account')
                        require(value.get('id')==({'owner': OWNER, 'member': MEMBER}[actor]), 'exact original native account')
                        phase['accountId'] = value['id']
                    elif action in ('self-member', 'self-member-final', 'removed-member', 'removed-member-final'):
                        self_owner = actor=='owner' and action.startswith('self-')
                        path = PREFIX+'/members/'+('me' if action.startswith('self-') else MEMBER)
                        wanted = {'identity': OWNER if self_owner else MEMBER, 'status': 'active' if self_owner else 'removed', 'permission': 'owner' if self_owner else 'none'}
                        value = request(path)
                        observed = {key: value.get(key) for key in wanted}
                        phase['membership'].append({'step': action, **observed}); save()
                        require(observed['identity']==wanted['identity'], 'membership identity differs')
                        if observed!=wanted:
                            if offline or action.endswith('-final') or self_owner:
                                raise AssertionError('current membership differs')
                            state['membershipWaitAt'] = state['membershipWaitAt'] or time.monotonic()
                            require(time.monotonic()-state['membershipWaitAt']<90, 'existing removal did not become current')
                            return None
                        state['membershipWaitAt'] = None
                    elif action in ('owner-file', 'member-file'):
                        value = request(FILE_PREFIX+argument, optional_metadata=action=='member-file')
                        observed = {'fileId': argument, 'typedMetadataRefusal': True} if value.get('typedDenial') else metadata_matches(value, argument)
                        phase['fileMetadata'].append(observed)
                    elif action=='offline-sync':
                        value = request(PREFIX+'/sync-status')
                        require(all(value.get(key)==0 for key in ('networkPeers', 'localPeers', 'globalPeers')), 'fresh OS-offline process has peers')
                        phase['offlineSync'] = {key: value[key] for key in ('state', 'networkPeers', 'localPeers', 'globalPeers')}
                    elif action=='deny':
                        label, route, byte_range = argument
                        value = request(FILE_PREFIX+route, byte_range, denial=True)
                        require(value=={'typedDenial': True}, 'content denial missing')
                        phase['denials'].append(label)
                    else: raise AssertionError('unknown fixed phase step')
                    phase['stepsCompleted'].append(action if argument is None else action+':'+str(argument))
                    step_index += 1; save(); return None
                except BaseException as error:
                    phase.setdefault('error', {'type': type(error).__name__, 'message': str(error)})
                    return type(error).__name__+': '+str(error)

            log, process_row = owned.run(output/name, argv, output, environment, 240, observe, save_command,
                lambda path: identity(public_bytes(path, LOG_CAP))['sha256'], result['processes'])
            require(phase['stopRequested'] and step_index==len(phase_steps), 'phase did not complete its fixed steps')
            require(process_row['exitCode']==0 and process_row['processGroupAbsent'] and not process_row['forcedCleanup'] and process_row['cleanupErrors']==[], 'clean native service closure')
            require(process_row['unreapedLeaderDuringGroupCleanup'], 'qualified process identity retention')
            if actor=='member': require(phase['denials']==[label for label, _, _ in DENIALS], 'all seven distinct denial decisions')
            phase['status'] = 'PASS_PHASE'; phase['logSHA256'] = process_row['logSHA256']; save()

        run_phase('owner-observation', 'owner', False)
        run_phase('member-online', 'member', False)
        run_phase('member-offline', 'member', True)
        require(len(result['processes'])==3 and len({p['pid'] for p in result['processes']})==3, 'three fresh native process identities')
        decisions = [row for row in result['requests'] if row['kind']=='content-denial']
        require(len(decisions)==14 and all(row['status']==403 and row.get('errorCode')=='acl.forbidden' and row['stage']=='confirmed-typed-denial' for row in decisions), 'fourteen strict content denials')
        require(Counter(row['phase'] for row in decisions)==Counter({'member-online': 7, 'member-offline': 7}), 'online and fresh OS-offline denial counts')
        result['contentDenialCount'] = 14
        result['status'] = 'PASS_ORIGINAL_CURRENT_AUTHORITY_HTTP14_ONLY'
    except BaseException as error:
        result['status'] = 'FAIL_CURRENT_AUTHORITY_HTTP_RETAINED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, signal.SIG_IGN)
        # owned.run has already retained/drained each command. Never re-probe
        # or signal its historical numeric process-group IDs here.
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') for row in result['processes'])
        try:
            for name, value in public_inputs.items():
                require(identity(public_bytes(Path(name), value['maximum']))==value['identity'], 'public input changed at finalization')
            result['publicInputsUnchanged'] = True
            if expected_source is not None and source is not None:
                source_inventory(source, expected_source); result['nativeSourceUnchanged'] = True
            if result['status'].startswith('PASS_'):
                require(len(result['processes'])==3 and result['allOwnedGroupsPositivelyAbsent'], 'complete native process closure')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['processes']), 'clean full lifecycle')
            result['freeAfter'] = guard()
        except BaseException as error:
            result['status'] = 'FAIL_CURRENT_AUTHORITY_HTTP_RETAINED'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        try: save()
        except BaseException as error:
            result['status'] = 'FAIL_CURRENT_AUTHORITY_HTTP_RETAINED'
            result['completionErrors'].append({'receiptRetention': type(error).__name__, 'message': str(error)})
    print(json.dumps({'status': result['status'], 'result': str(output/'result.json'),
                      'contentDenialCount': result.get('contentDenialCount', 0),
                      'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
