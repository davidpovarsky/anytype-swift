#!/usr/bin/env python3
"""SOURCE ONLY: eighteen current-member metadata denials after final qualification.

The native app may open its existing stores through ordinary startup. This
controller never opens, inventories, copies or exports account-file contents.
No constructor, role, invitation, file upload, retry or restoration is exposed.
"""
import argparse
import ast
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
OUTPUT_PARENT = ROOT/'metadata-authority-http-20261127'
BASELINE = ROOT/'original-native-authority-reader-continuation1/result.json'
BASELINE_SHA = 'ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab'
FILES_RECEIPT = ROOT/'original-files-lan-progress1/result.json'
FILES_SHA = '0c0d4622bff1075d7da331b3f2d393aa536ce688e05a92013defde153210c5da'
PRIOR_CUSTODY = '792268b4d7448d9c9b6665ee6388f26c18e5de0635aa05f1b390db7f20a5567d'
HERE = Path(__file__).absolute().parent
ADMISSION = HERE/'final_product_admission.py'
ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'
PRODUCER_SOURCE_SHA = '9f335c8402b566384f3b4d980178ebb5363205f6d9e9d0e0e05212c2a632da78'
CONTENT_RECEIPT = ROOT/'current-authority-http-20261127/attempt1/result.json'
CONTENT_SHA = '7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099'
DEADLINE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127/attempt1/result.json')
DEADLINE_RECEIPT_SHA = '0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6'
DEADLINE_SOURCE = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127-source1/verify_current_authority_http.py')
DEADLINE_SOURCE_SHA = '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84'
DEADLINE_FUNCTION_SHA = 'b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81'
PREDECESSOR_SOURCE_SHA = '2bbda0f4d389aef369d1df1459d2e5d03ba9648121211619aa028b99a0990ac5'
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
OWNER_FILES = ('E9ZfwB8Biag', 'hs6LTsotxAY', '9DSkw6W3eqv', 'SbLLxZDbq59')
ALL_FILES = OWNER_FILES+('AEhbwaXwY7S',)
DENIALS = tuple(('get-'+file_id,FILE_PREFIX+file_id) for file_id in ALL_FILES)+(
    ('object-list',PREFIX+'/files?objectId='+OBJECT),
    ('space-list',PREFIX+'/files'),
    ('file-status',FILE_PREFIX+'hs6LTsotxAY/status'),
    ('space-stats',PREFIX+'/files/stats'),
)
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
    require(producer_dir.parent==ROOT and re.fullmatch(r'final-authority-native[1-9][0-9]{0,2}', producer_dir.name), 'future native producer scope')
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
    final_deadline = None
    last_allocation = 0.0
    public_inputs = {}
    expected_source = None
    source = None
    producer = None
    joined = None
    receipt_serial = 0
    result = {
        'protocol': 'pinkha-current-metadata-authority-get-only-v1', 'status': 'RUNNING',
        'historicalFailureSHA256': BASELINE_SHA, 'lastKnownClosedCustodySHA256': PRIOR_CUSTODY,
        'reusedContentOnlyHTTP14SHA256': CONTENT_SHA, 'replayedContentDenials': 0,
        'SSEHTTP403Claim': False, 'cacheMutatorRequests': 0,
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
                           'controllerDeadlineSeconds': 360, 'finalVerificationSeconds': 60,
                           'maximumPhaseSeconds': 240, 'requiredOuterTimeoutSeconds': 480,
                           'outputAllocationSampleSeconds': 1,
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

    def guard(admit=False, force_allocation=False):
        nonlocal last_allocation
        if final_deadline is None:
            require(time.monotonic()-began<360, '360-second metadata-authority deadline')
        else:
            require(time.monotonic()<final_deadline, '60-second final public verification deadline')
        require(not (output/'abort').exists(), 'owned controller abort')
        free = {name: shutil.disk_usage(path).free for name, path in [('root', '/'), ('development', '/mnt/development')]}
        for name, floor, reserve in [('root', ROOT_FLOOR, ROOT_RESERVE), ('development', DEV_FLOOR, DEV_RESERVE)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
            require(free[name]>=floor+(reserve if admit else 0), name+' unchanged storage gate')
        # Source/hash/deadline/floor checks remain per input. Repeated full
        # output censuses are bounded to one per second, with explicit phase
        # and final fences; they are not repeated for each immutable row.
        if force_allocation or time.monotonic()-last_allocation>=1:
            last_allocation = time.monotonic()
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

    def source_inventory(root, check):
        physical_directory(root)
        found = {}; stack = [root]; count = 0
        while stack:
            check()
            directory = stack.pop()
            fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
            try:
                with os.scandir(fd) as entries: names = sorted(entry.name for entry in entries)
            finally: os.close(fd)
            for name in names:
                check()
                path = directory/name; info = path.lstat(); count += 1
                require(count<=10000 and not stat.S_ISLNK(info.st_mode), 'bounded physical public source')
                if stat.S_ISDIR(info.st_mode): stack.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode), 'ordinary public source member')
                    found[path.relative_to(root).as_posix()] = identity(public_bytes(path,128*MIB))
        return found

    def deadline_function(raw):
        text = raw.decode('utf-8')
        tree = ast.parse(text)
        nodes = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='absolute_http_deadline']
        require(len(nodes)==1 and len(nodes[0].decorator_list)==1, 'one exact decorated deadline function')
        node = nodes[0]
        return ''.join(text.splitlines(keepends=True)[node.decorator_list[0].lineno-1:node.end_lineno]).encode()

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
        ownership = json_object(pin(HELPER_PROOF, HELPER_PROOF_SHA))
        require(ownership['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and ownership['helperSHA256']==HELPER_SHA and ownership['allOwnedGroupsPositivelyAbsent'], 'qualified helper proof')
        require(len(ownership['methods'])==5 and all(row['status']=='PASS' for row in ownership['methods']), 'five original lifecycle controls')
        spec = importlib.util.spec_from_file_location('qualified_current_authority_owned', helper_path)
        owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
        result['ownershipHelperSHA256'] = HELPER_SHA
        result['reusedOwnershipFiveControlReceiptSHA256'] = HELPER_PROOF_SHA
        result['admissionFreeBytes'] = guard(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available>=2*1024**3, 'native memory admission')
        result['memAvailableBefore'] = available
        original_deadline_source = pin(DEADLINE_SOURCE,DEADLINE_SOURCE_SHA)
        old_function = deadline_function(original_deadline_source)
        current_function = deadline_function(public_bytes(own_path))
        require(old_function==current_function and len(current_function)==1745 and identity(current_function)['sha256']==DEADLINE_FUNCTION_SHA, 'unchanged actual-qualified absolute deadline')
        deadline_proof = json_object(pin(DEADLINE_RECEIPT,DEADLINE_RECEIPT_SHA))
        require(deadline_proof['status']=='PASS_TWO_ACTUAL_HTTP_DEADLINES_AND_OWNED_CLOSURE' and deadline_proof['allOwnedGroupsPositivelyAbsent'] and deadline_proof['errors']==deadline_proof['completionErrors']==[], 'actual original deadline2 receipt')
        actual = deadline_proof['actualControls']
        require(actual['controllerSHA256']==DEADLINE_SOURCE_SHA and actual['actualMethods']=={'runs':2,'failures':0,'errors':0,'skips':0}, 'two original deadline controls')
        require(actual['sourceUnchanged'] and actual['errors']==[] and len(actual['controls'])==2, 'unchanged actual timer control source')
        require({row['name'] for row in actual['controls']}=={'slow-body','slow-header'} and all(row['status']=='PASS' and row['threadJoined'] and row['ownedTimerCleared'] and row['previousHandlerRestored'] and row['previousMaskRestored'] and not row['pendingAlarmAfter'] for row in actual['controls']), 'timer lifecycle controls')
        result['absoluteDeadlineReuse'] = {'receiptSHA256':DEADLINE_RECEIPT_SHA,'originalControllerSHA256':DEADLINE_SOURCE_SHA,'function':identity(current_function),'controlsReexecuted':0}
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

        content = json_object(pin(CONTENT_RECEIPT,CONTENT_SHA))
        require(content['status']=='PASS_ORIGINAL_CURRENT_AUTHORITY_HTTP14_ONLY' and content['controller']['sha256']==PREDECESSOR_SOURCE_SHA, 'actual content-only predecessor')
        require(content['contentDenialCount']==14 and content['allOwnedGroupsPositivelyAbsent'] and content['errors']==content['completionErrors']==[], 'fourteen prior content decisions retained without replay')
        require(content['syntheticFileBindings']==expected_files, 'same five originally authorized synthetic file bindings')
        for phase in content['phases']:
            if phase['actor']=='member':
                require(len(phase['fileMetadata'])==5 and {row['fileId'] for row in phase['fileMetadata']}==set(ALL_FILES), 'actual five cached metadata observations')
                require(all(row.get('cached') is True and not row.get('typedMetadataRefusal',False) for row in phase['fileMetadata']), 'prior metadata GET200 remains an observed gap')
        result['priorMetadataExposurePreserved'] = {'receiptSHA256':CONTENT_SHA,'cachedMetadataRowsPerMemberPhase':5,'reportedAsProtected':False}
        pin(ADMISSION,ADMISSION_SHA)
        spec = importlib.util.spec_from_file_location('metadata_http_final_product_admission',ADMISSION)
        admission = importlib.util.module_from_spec(spec); spec.loader.exec_module(admission)
        joined = admission.admit_product(pin,source_inventory,args.producer_receipt,args.producer_sha256,guard,PRODUCER_SOURCE_SHA,ADMISSION_SHA)
        producer = joined['producer']; source = joined['source']; expected_source = joined['files']; binary = joined['binary']
        require(binary.lstat().st_mode&0o111, 'actual qualified native executable')
        result['correctedNativeProducer'] = {'receiptSHA256':args.producer_sha256,'binary':joined['binaryIdentity'],
            'sourceManifestSHA256':producer['sourceManifestSHA256'],'sourceFiles':len(expected_source),
            'finalAuthorityQualification':producer['qualification']}
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
                          PREFIX+'/sync-status'}|{FILE_PREFIX+file_id for file_id in OWNER_FILES}
        denial_paths = {path for _,path in DENIALS}
        require(len(DENIALS)==len(denial_paths)==9, 'nine distinct fixed metadata routes')

        def metadata_matches(value, file_id):
            wanted = expected_files[file_id]
            for key, desired in wanted.items():
                require(value.get(key, '')==desired if key=='mime' else value.get(key)==desired, 'synthetic file binding differs: '+key)
            require(isinstance(value.get('cached'), bool) and isinstance(value.get('durable'), bool), 'native file-state flags')
            return {k: value[k] for k in ('fileId', 'objectId', 'rootCid', 'size', 'cached', 'durable')}

        def run_phase(name, actor, offline):
            # There is at most one live native process. These checks inspect
            # only process metadata, public inputs and the directory itself.
            guard(force_allocation=True); no_competing_account_process()
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
                if offline: phase_steps += [('offline-sync', None)]
                phase_steps += [('deny', check) for check in DENIALS]+[('self-member-final', None)]
            step_index = 0

            def request(path, denial=False, health=False):
                require(path in denial_paths if denial else path in metadata_paths, 'GET-only metadata allowlist')
                row = {'phase': name, 'method': 'GET', 'path': path, 'range': None,
                       'stage': 'dispatching', 'bodyReadInvocations': 0, 'kind': 'metadata-denial' if denial else 'identity-or-owner-metadata'}
                result['requests'].append(row); save(); guard()
                # Only bounded transport work runs under the alarm. Persistence
                # happens after its handler/mask are restored, so an HTTP
                # deadline cannot interrupt the evidence-retention path.
                try:
                    remaining = min(360-(time.monotonic()-began), 240-(time.monotonic()-phase_started))
                    require(remaining>0, 'complete request has no controller or phase budget')
                    with absolute_http_deadline(min(2 if health else 5, remaining)):
                        raw = request_with_deadline(row, path, denial, health)
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

            def request_with_deadline(row, path, denial, health):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2 if health else 5)
                response = None
                try:
                    headers = {'Connection': 'close'}
                    connection.request('GET', path, headers=headers)
                    response = connection.getresponse()
                    row['status'] = response.status
                    row['headers'] = {k: str(response.getheader(k) or '')[:1024] for k in ('Content-Type', 'Content-Length', 'Content-Range')}
                    allowed = (403,) if denial else (200,)
                    if response.status not in allowed:
                        row['stage'] = 'unexpected-status-body-not-read'
                        raise AssertionError('unexpected HTTP status; metadata body not consumed')
                    if health:
                        return b''
                    maximum = 4096 if response.status==403 else 65536
                    row['bodyReadInvocations'] += 1
                    raw = response.read(maximum+1)
                    require(len(raw)<=maximum, 'bounded API envelope')
                    return raw
                finally:
                    # No redirects, proxy routing, retries or draining of an
                    # unexpected metadata body. http.client may buffer transport
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
                    elif action=='owner-file':
                        value = request(FILE_PREFIX+argument)
                        phase['fileMetadata'].append(metadata_matches(value,argument))
                    elif action=='offline-sync':
                        value = request(PREFIX+'/sync-status')
                        require(all(value.get(key)==0 for key in ('networkPeers', 'localPeers', 'globalPeers')), 'fresh OS-offline process has peers')
                        phase['offlineSync'] = {key: value[key] for key in ('state', 'networkPeers', 'localPeers', 'globalPeers')}
                    elif action=='deny':
                        label,route = argument
                        value = request(route,denial=True)
                        require(value=={'typedDenial':True}, 'current metadata denial missing')
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
            if actor=='member': require(phase['denials']==[label for label,_ in DENIALS], 'all nine distinct metadata denial decisions')
            guard(force_allocation=True)
            phase['status'] = 'PASS_PHASE'; phase['logSHA256'] = process_row['logSHA256']; save()

        run_phase('owner-observation', 'owner', False)
        run_phase('member-online', 'member', False)
        run_phase('member-offline', 'member', True)
        require(len(result['processes'])==3 and len({p['pid'] for p in result['processes']})==3, 'three fresh native process identities')
        decisions = [row for row in result['requests'] if row['kind']=='metadata-denial']
        require(len(decisions)==18 and all(row['status']==403 and row.get('errorCode')=='acl.forbidden' and row['stage']=='confirmed-typed-denial' for row in decisions), 'eighteen strict metadata denials')
        require(Counter(row['phase'] for row in decisions)==Counter({'member-online': 9, 'member-offline': 9}), 'online and fresh OS-offline denial counts')
        result['metadataDenialCount'] = 18
        result['status'] = 'PASS_ORIGINAL_CURRENT_METADATA_AUTHORITY_HTTP18_ONLY'
    except BaseException as error:
        result['status'] = 'FAIL_CURRENT_METADATA_AUTHORITY_HTTP_RETAINED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, signal.SIG_IGN)
        # owned.run has already retained/drained each command. Never re-probe
        # or signal its historical numeric process-group IDs here.
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') for row in result['processes'])
        final_deadline = time.monotonic()+60
        try:
            guard(force_allocation=True)
            for name, value in public_inputs.items():
                guard()
                require(identity(public_bytes(Path(name), value['maximum']))==value['identity'], 'public input changed at finalization')
            result['publicInputsUnchanged'] = True
            if expected_source is not None and source is not None:
                require(source_inventory(source,guard)==expected_source, 'new native source unchanged'); result['nativeSourceUnchanged'] = True
            if joined is not None:
                require(source_inventory(admission.BASE/'source',guard)==joined['baseFiles'], 'retained public base source unchanged')
                require(source_inventory(joined['qualifiedSDKSource'],guard)==joined['sdkFiles'], 'qualified final SDK source unchanged')
                result['qualifiedPublicSourcesUnchanged'] = True
            if result['status'].startswith('PASS_'):
                require(len(result['processes'])==3 and result['allOwnedGroupsPositivelyAbsent'], 'complete native process closure')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['processes']), 'clean full lifecycle')
            result['freeAfter'] = guard(force_allocation=True)
        except BaseException as error:
            result['status'] = 'FAIL_CURRENT_METADATA_AUTHORITY_HTTP_RETAINED'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        try: save()
        except BaseException as error:
            result['status'] = 'FAIL_CURRENT_METADATA_AUTHORITY_HTTP_RETAINED'
            result['completionErrors'].append({'receiptRetention': type(error).__name__, 'message': str(error)})
    print(json.dumps({'status': result['status'], 'result': str(output/'result.json'),
                      'metadataDenialCount': result.get('metadataDenialCount', 0),
                      'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
