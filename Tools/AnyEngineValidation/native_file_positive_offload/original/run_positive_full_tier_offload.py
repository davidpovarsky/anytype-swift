#!/usr/bin/env python3
"""SOURCE ONLY: one backed full-tier Offload, cold refusal, cloud refetch and cold read.

The native app may open its existing stores through ordinary startup. This
controller never opens, inventories, copies or exports account-file contents.
Exactly one fixed Offload POST is exposed. No init, role, invite, upload or retry exists.
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
CLOUD = Path('/var/lib/pinkha-w1-cloud-filesv2-20261127')
OUTPUT_PARENT = ROOT/'positive-full-tier-offload-20261127'
HERE = Path(__file__).absolute().parent
ADMISSION = HERE/'final_product_admission.py'
ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'
PRODUCER_SOURCE_SHA = '9f335c8402b566384f3b4d980178ebb5363205f6d9e9d0e0e05212c2a632da78'
PRODUCER_RECEIPT_SHA = '9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602'
CLOUD_RECEIPT = CLOUD/'attempt6-small-cloud/result.json'
CLOUD_RECEIPT_SHA = 'e6446c4ff820e0dcdf80ba298a977368a7a5c19ada0eea9dab1280998a6937ba'
DEADLINE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127/attempt1/result.json')
DEADLINE_RECEIPT_SHA = '0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6'
DEADLINE_SOURCE = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127-source1/verify_current_authority_http.py')
DEADLINE_SOURCE_SHA = '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84'
DEADLINE_FUNCTION_SHA = 'b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81'
OWNER = 'AAgW9UF9iqUH1KrjQcAz5K2FDCc9kQgniwmnK2rei1M5ah2H'
MEMBER = 'A7zf8i42qUR8rZJwHrztRqFPifD3upr1fkyN9V3pF72AAaGi'
SPACE = 'bafyreiet62u77nehvmtgn45ltxrk6itepoighks3u4y2f3pjjotaczcsfi.361psf76ieku2'
OBJECT = 'bafyreid5n5gg366h3lsqdolu5wi6hffwtqfyhzb53ylneh626bnapnzj6q'
DATA_DIRS = {'owner': CLOUD/'attempt2/alice', 'member': CLOUD/'attempt2/bob'}
NODECONF_SHA = '6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_LIBRARY_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OFFLINE_LIBRARY = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
FILE_ID = 'BEaHYwGfZiM'
PROTECTED_FILE_ID = 'ahKeFKn7uta'
EXPECTED = {
    FILE_ID: {'rootCid':'bafybeibfvxnwxvg6mufc4lksm4t544hwm3233ph3asn4lgdhjjifmj567i',
              'bytes':8192,'name':'cloud-binary.bin','mime':'application/octet-stream',
              'plaintextSHA256':'5b3ad191f3c210b61bd5d1ef5ffc838b7fbabe38e8b42207fa04bf2388831313'},
    PROTECTED_FILE_ID: {'rootCid':'bafybeighhcuudwqvbo36hmty4mrfdkp4cuuvzn3ddzspi7vjt7klnugg7e',
              'bytes':12420,'name':'cloud-thumb.png','mime':'image/png',
              'plaintextSHA256':'710df0c12429ecca0af68e5217edf5a1d82176869b0c4a30ee52082c858e21c1'},
}
PREFIX = '/v1/spaces/'+SPACE
FILE_PREFIX = PREFIX+'/files/'
CONTENT_PATH = FILE_PREFIX+FILE_ID+'/content'
OFFLOAD_PATH = FILE_PREFIX+FILE_ID+'/offload'
PHASE_NAMES = ('member-offload', 'member-offline-miss', 'member-cloud-refetch', 'member-offline-restored')
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
    require(args.output==OUTPUT_PARENT/'attempt1', 'single exclusive Offload attempt; no blind continuation/replay')
    producer_dir = args.producer_receipt.parent
    require(producer_dir.parent==ROOT and re.fullmatch(r'final-authority-native[1-9][0-9]{0,2}', producer_dir.name), 'future native producer scope')
    require(args.producer_receipt.name=='result.json' and re.fullmatch(r'[0-9a-f]{64}', args.producer_sha256), 'pinned producer receipt')
    require(args.producer_sha256==PRODUCER_RECEIPT_SHA, 'only the already qualified final product')
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
        'protocol':'pinkha-backed-full-tier-offload-cloud-refetch-v1', 'status':'RUNNING',
        'historicalTwoFileCloudReceiptSHA256':CLOUD_RECEIPT_SHA,
        'accountFileReadsByController':0, 'accountCopies':0, 'privateRecordExports':0,
        'accountInitializations':0, 'roleMutations':0, 'inviteMutations':0, 'uploadCalls':0,
        'retryCalls':0, 'pinCalls':0, 'compilerInvocations':0, 'oldMethodsReexecuted':0,
        'privateAccountByteCustodyClaim':False, 'retainedCARFilesReadByController':0,
        'nativeOperationalStoreWritesPossible':True, 'selectedFileCacheMutationRequired':True,
        'allFourCloudFilesDurableClaim':False, 'quotaBypass':False,
        'callerPlaintextFilesWritten':0, 'cloudProviderInternalTraceClaim':False,
        'processes':[], 'phases':[], 'requests':[], 'offloadDispatches':[],
        'errors':[], 'completionErrors':[],
        'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR,
            'rootAdmissionReserveBytes':ROOT_RESERVE,'developmentAdmissionReserveBytes':DEV_RESERVE,
            'ownedOutputCapBytes':OUTPUT_CAP,'logCapPerProcessBytes':LOG_CAP,
            'controllerDeadlineSeconds':360,'finalVerificationSeconds':60,
            'maximumPhaseSeconds':120,'requiredOuterTimeoutSeconds':480,
            'outputAllocationSampleSeconds':1,'workersPerNative':2,
            'memoryLimitPerNative':'512MiB','maximumConcurrentNativeProcesses':1},
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
        require(path.parent.parent==output and path.parent.name in PHASE_NAMES, 'owned native phase')
        require(path.name in ('started.json', 'result.json'), 'owned helper receipt')
        save_json(path, value); save()

    def guard(admit=False, force_allocation=False):
        nonlocal last_allocation
        if final_deadline is None:
            require(time.monotonic()-began<360, '360-second positive Offload deadline')
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

    def no_competing_account_process(allowed_pid=None):
        # Read process metadata only. Never read any account file through /proc.
        found = []; started = time.monotonic(); examined = 0
        prefixes = [os.fsencode(str(path)) for path in DATA_DIRS.values()]
        for directory in Path('/proc').iterdir():
            if not directory.name.isdecimal() or int(directory.name) in (os.getpid(), allowed_pid): continue
            examined += 1
            require(examined<=100000 and time.monotonic()-started<10, 'bounded account process census')
            try:
                with (directory/'cmdline').open('rb') as stream: raw = stream.read(131073)
            except (FileNotFoundError, ProcessLookupError): continue
            require(len(raw)<=131072, 'bounded process metadata')
            if any(prefix in raw for prefix in prefixes): found.append(int(directory.name))
        require(not found, 'a process already references an original account directory')
        return {'processesExamined': examined, 'matchingProcesses': 0, 'allowedOwnedPID':allowed_pid, 'accountContentsRead': False}

    def interrupted(number, _frame):
        raise RuntimeError('positive Offload controller interrupted by signal '+str(number))
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
        previous = json_object(pin(CLOUD_RECEIPT, CLOUD_RECEIPT_SHA))
        require(previous['status']=='PASS_TWO_DURABLE_CLOUD_FILES_AND_RECIPIENT_OFFLINE_ONLY' and previous['errors']==[], 'actual original two-file cloud acceptance')
        require(previous['accounts']=={'alice':OWNER,'bob':MEMBER} and previous['spaceID']==SPACE and previous['objectID']==OBJECT, 'same public synthetic account/Space/object lineage')
        require(previous['selectedFilesCloudCustodyAccepted'] and previous['selectedFilesCrossAccountBytesAccepted'] and previous['selectedFilesOfflineAccepted'], 'original selected-file custody, bytes and cold reopen passed')
        require(previous['allFourFilesAccepted'] is False and previous['explicitQuotaRetries']==[], 'no all-four or quota recovery inference')
        historical_groups = previous['processes']
        require(len(historical_groups)==2 and len({row['pid'] for row in historical_groups})==2 and all(row['exitCode']==0 and row['groupPositivelyAbsent'] and not row['forcedKill'] for row in historical_groups), 'original ordinary cloud fixture groups already closed')
        require(previous['sourceBefore']==previous['sourceAfter'] and previous['sourceAfter']['sourceUnchanged'], 'original cloud receipt retains its source closure')
        old_files = {row['fileId']:row for row in previous['files']}
        require(set(old_files)==set(EXPECTED), 'two exact already durable original files')
        for file_id, expected in EXPECTED.items():
            require(all(old_files[file_id].get(key)==value for key,value in expected.items()), 'exact prior synthetic file binding')
            require(old_files[file_id]['durableBeforeRead'] is True and old_files[file_id]['initiallyCached'] is False and expected['rootCid'], 'actual full-tier backed cloud file, not size inference')
        result['originalCloudProof'] = {'receiptSHA256':CLOUD_RECEIPT_SHA,'sourceManifestSHA256':previous['sourceAfter']['sourceManifestSHA256'],
            'historicalGroupCount':2,'historicalProcessIDsProbed':False,'twoFiles':EXPECTED,'originalGroupsReexecuted':0}
        pin(ADMISSION,ADMISSION_SHA)
        spec = importlib.util.spec_from_file_location('positive_offload_final_product_admission',ADMISSION)
        admission = importlib.util.module_from_spec(spec); spec.loader.exec_module(admission)
        joined = admission.admit_product(pin,source_inventory,args.producer_receipt,args.producer_sha256,guard,PRODUCER_SOURCE_SHA,ADMISSION_SHA)
        producer = joined['producer']; source = joined['source']; expected_source = joined['files']; binary = joined['binary']
        require(binary.lstat().st_mode&0o111, 'actual qualified native executable')
        result['correctedNativeProducer'] = {'receiptSHA256':args.producer_sha256,'binary':joined['binaryIdentity'],
            'sourceManifestSHA256':producer['sourceManifestSHA256'],'sourceFiles':len(expected_source),
            'finalAuthorityQualification':producer['qualification']}
        nodeconf = source/'internal/config/nodeconf-prod.yml'
        pin(nodeconf,NODECONF_SHA,65536)
        require(previous['productionNodeconfSHA256']==NODECONF_SHA, 'same exact original production network descriptor')
        pin(OFFLINE,OFFLINE_SHA,65536); pin(OFFLINE_LIBRARY,OFFLINE_LIBRARY_SHA,4*MIB)
        # Bind the current original transport/error implementations through the
        # already checked full1616 manifest. No source or account store changes.
        contracts = {
            'internal/server/handlers_common.go':'e666fc600dd92d32f99ef70c3a729c9ea9b11bf43f9cedb9d02a195f5decbdd6',
            'internal/server/handlers_files.go':'a7e299282612adcdb76f2b8f3c64553a92770edcf6ba2bab4ab91e3bb9786658',
            '.runtime-artifacts/sdk-source/internal/files/fetch/remote.go':'0240d29ddf60a130bd8e325b55598570c182dbdc687f62c77d7b24be9d6d2d7e',
        }
        for relative,wanted in contracts.items():
            require(expected_source[relative]['sha256']==wanted, 'unchanged original HTTP/fetch contract source')
            pin(source/relative,wanted,65536)
        result['publicTransportContractSHA256'] = contracts
        result['offlinePolicy'] = {'helperSHA256':OFFLINE_SHA,'librarySHA256':OFFLINE_LIBRARY_SHA,
            'unchangedControlMethodsReexecuted':0,'actualProcessInheritanceRequired':True}
        for directory in DATA_DIRS.values(): physical_directory(directory)
        result['closedPairProcessAdmission'] = no_competing_account_process()
        config = output/'network.yml'
        config_text = ('network:\n  nodeconfPath: '+str(nodeconf)+'\nindex:\n  embedder: none\np2p:\n'
                       '  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n')
        with config.open('x') as stream: stream.write(config_text); stream.flush(); os.fsync(stream.fileno())
        public_inputs[str(config)] = {'identity':identity(config_text.encode()),'maximum':65536}
        result['networkPolicy'] = {'productionNodeconfSHA256':NODECONF_SHA,'config':identity(config_text.encode()),
            'P2PEnabled':False,'localDiscoveryEnabled':False,'globalP2PEnabled':False,
            'senderNativeProcessStarted':False,'currentSenderAbsenceCheckedBeforeEveryPhaseAndContent':True}
        metadata_paths = {'/v1/health','/v1/account',PREFIX+'/members/me',PREFIX+'/sync-status',
                          FILE_PREFIX+FILE_ID,FILE_PREFIX+PROTECTED_FILE_ID,FILE_PREFIX+FILE_ID+'/status'}
        first_metadata = {}

        def metadata_matches(value,file_id,cached):
            expected = EXPECTED[file_id]
            require(value.get('fileId')==file_id and value.get('objectId')==OBJECT and
                    value.get('rootCid')==expected['rootCid'] and value.get('size')==expected['bytes'] and
                    value.get('name')==expected['name'] and value.get('inline') is False and
                    value.get('durable') is True and value.get('cached') is cached, 'exact full-tier durable cache state')
            require((value.get('mime') or 'application/octet-stream')==expected['mime'], 'original MIME omission/default contract')
            require(not value.get('variant') and not value.get('variantOf'), 'original file, not a variant redirection')
            binding = {key:item for key,item in value.items() if key!='cached'}
            if file_id in first_metadata:
                require(binding==first_metadata[file_id], 'all original file metadata except local cache bit preserved')
            else:
                first_metadata[file_id] = binding
            return value

        def run_phase(name,offline):
            guard(force_allocation=True); no_competing_account_process()
            for path in (binary,config,nodeconf,OFFLINE,OFFLINE_LIBRARY):
                admitted = public_inputs[str(path)]
                require(identity(public_bytes(path,admitted['maximum']))==admitted['identity'], 'phase public input changed')
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1',0)); port = reservation.getsockname()[1]
            argv = [str(binary),'run','--config',str(config),'--data-dir',str(DATA_DIRS['member']),'--addr','127.0.0.1:'+str(port)]
            if offline: argv = [sys.executable,'-B',str(OFFLINE),'--exec']+argv
            environment = {key:value for key,value in os.environ.items() if not key.startswith('ANY_')}
            environment.update(ANY_DATA_DIR=str(DATA_DIRS['member']),GOMAXPROCS='2',GOMEMLIMIT='512MiB')
            phase = {'name':name,'actor':'member','offline':offline,'stepsCompleted':[],
                     'stopRequested':False,'membership':[],'fileMetadata':[],'content':[]}
            result['phases'].append(phase); save()
            ledger_index = len(result['processes']); phase_started = time.monotonic(); step_index = 0
            initial_cached = name in ('member-offload','member-offline-restored')
            phase_steps = [('health',None),('identity',None),('self-member',None),('sync',None),
                           ('file-before',initial_cached),('protected-before',True),('status-before',initial_cached)]
            if name=='member-offload': phase_steps += [('offload',None),('file-after',False),('status-after',False)]
            elif name=='member-offline-miss': phase_steps += [('offline-miss',None),('file-after',False),('status-after',False)]
            else: phase_steps += [('content',None),('file-after',True),('status-after',True)]
            phase_steps += [('protected-after',True),('self-member-final',None),('sync-final',None)]

            def retain_response(raw,request_row):
                # This contains only the single empty Offload ACK or its bounded
                # error response. Plaintext file bytes are never written here.
                path = output/('offload-response-'+str(len(result['offloadDispatches']))+'.bin')
                with path.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                fd = os.open(output,os.O_RDONLY|os.O_DIRECTORY)
                try: os.fsync(fd)
                finally: os.close(fd)
                request_row['retainedResponse'] = {'path':str(path),**identity(raw)}

            def request(path,kind='metadata'):
                method = 'POST' if kind=='offload' else 'GET'
                require((kind=='offload' and path==OFFLOAD_PATH) or
                        (kind in ('content','offline-miss') and path==CONTENT_PATH) or
                        (kind in ('metadata','health') and path in metadata_paths), 'fixed normal API allowlist')
                row = {'phase':name,'method':method,'path':path,'kind':kind,'stage':'dispatching',
                       'bodyReadInvocations':0,'callerFilePlaintextBytesRetained':0}
                if kind=='offload':
                    require(name=='member-offload' and not result['offloadDispatches'], 'one original Offload dispatch only')
                    row['effectOutcome'] = 'unknown-until-original-response-and-cache-check'
                    result['offloadDispatches'].append(row)
                result['requests'].append(row); save(); guard()
                raw = None
                try:
                    remaining = min(360-(time.monotonic()-began),120-(time.monotonic()-phase_started))
                    require(remaining>0, 'complete request has no controller/phase budget')
                    budget = 2 if kind=='health' else (30 if kind in ('content','offline-miss') else (10 if kind=='offload' else 5))
                    with absolute_http_deadline(min(budget,remaining)):
                        connection = http.client.HTTPConnection('127.0.0.1',port,timeout=budget)
                        response = None
                        try:
                            connection.request(method,path,body=b'' if method=='POST' else None,
                                               headers={'Connection':'close'})
                            response = connection.getresponse()
                            row['status'] = response.status
                            row['headers'] = {key:str(response.getheader(key) or '')[:1024]
                                              for key in ('Content-Type','Content-Length','Content-Range')}
                            expected_status = 204 if kind=='offload' else (500 if kind=='offline-miss' else 200)
                            if kind!='offload' and response.status!=expected_status:
                                row['stage'] = 'unexpected-status-body-not-read'
                                raise AssertionError('unexpected native response; body not consumed')
                            if kind=='health': raw = b''
                            else:
                                maximum = EXPECTED[FILE_ID]['bytes'] if kind=='content' else (4096 if kind in ('offload','offline-miss') else 65536)
                                row['bodyReadInvocations'] += 1
                                raw = response.read(maximum+1)
                                row['response'] = identity(raw)
                                row['responseTruncatedAtBound'] = len(raw)>maximum
                                if kind=='offload':
                                    # Retain the original response before even
                                    # transport shutdown can raise. A later
                                    # close/deadline/shape failure never erases
                                    # these bytes or permits resending the POST.
                                    retain_response(raw,row); save()
                        finally:
                            if response is not None: response.close()
                            connection.close()
                    if kind=='offload':
                        # Persist actual bounded ACK bytes before status/shape
                        # validation. Any failure retains unknown effects; never
                        # resend the operation or perform cleanup Offload.
                        require(row.get('retainedResponse') is not None and
                                row['retainedResponse']['bytes']==len(raw) and
                                row['retainedResponse']['sha256']==identity(raw)['sha256'],
                                'original response retained before transport closure')
                        require(row['status']==204 and raw==b'' and
                                row['headers']['Content-Length'] in ('','0') and
                                row['headers']['Content-Range']=='', 'original empty Offload204 ACK')
                        row['stage'] = 'original-204-ack-retained'
                        row['effectOutcome'] = 'acknowledged-cache-state-pending'
                        save(); return None
                    if kind=='health': row['stage']='ready-status'; save(); return None
                    require(not row['responseTruncatedAtBound'], 'bounded native response')
                    if kind=='content':
                        require(len(raw)==EXPECTED[FILE_ID]['bytes'] and
                                identity(raw)['sha256']==EXPECTED[FILE_ID]['plaintextSHA256'] and
                                row['headers']['Content-Type']=='application/octet-stream' and
                                row['headers']['Content-Length']==str(EXPECTED[FILE_ID]['bytes']) and
                                row['headers']['Content-Range']=='', 'exact full synthetic plaintext with original MIME')
                        row['stage'] = 'exact-original-plaintext-verified'
                        phase['content'].append({'status':200,**identity(raw)}); save(); return None
                    value = json_object(raw)
                    if kind=='offline-miss':
                        require(value=={'error':{'code':'internal','message':'internal error',
                                                 'details':{'spaceId':SPACE,'fileId':FILE_ID}}},
                                'unchanged native network-error envelope; no invented resource error')
                        require(row['headers']['Content-Type'].split(';')[0]=='application/json', 'error response is not file content')
                        row['errorCode']='internal'; row['stage']='uncached-offline-no-content-error'
                        phase['content'].append({'status':500,'errorCode':'internal','filePlaintextBytesDelivered':0,
                                                'errorEnvelope':identity(raw)})
                        save(); return None
                    row['stage']='metadata-response'; save(); return value
                except BaseException as error:
                    row.setdefault('failure',{'type':type(error).__name__,'message':str(error)})
                    if kind=='offload': row['effectOutcome']='unknown-effects-no-retry'
                    save(); raise

            def observe():
                nonlocal step_index
                try:
                    guard()
                    if len(result['processes'])<=ledger_index: return None
                    process_row = result['processes'][ledger_index]
                    if process_row.get('exitCode') is not None or process_row.get('processGroupAbsent'): return None
                    if 'pid' not in process_row or phase['stopRequested']: return None
                    pid = process_row['pid']
                    require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None, 'native exited before requested stop')
                    require(os.getpgid(pid)==pid and os.getsid(pid)==pid, 'current unreaped native group/session')
                    if step_index==len(phase_steps):
                        phase['gracefulStopIntent']={'pid':pid,'signal':int(signal.SIGTERM),'leaderUnreaped':True}
                        save(); os.killpg(pid,signal.SIGTERM)
                        phase['stopRequested']=True; process_row['expectedServiceShutdown']=True
                        save(); return None
                    action,argument = phase_steps[step_index]
                    if action=='health':
                        try: request('/v1/health','health')
                        except (OSError,http.client.HTTPException):
                            require(time.monotonic()-phase_started<60, 'bounded native readiness'); return None
                        if offline:
                            fields=dict(line.split(':',1) for line in Path('/proc/'+str(pid)+'/status').read_text().splitlines() if ':' in line)
                            require(fields['NoNewPrivs'].strip()=='1' and fields['Seccomp'].strip()=='2', 'actual inherited OS-denial state')
                            require(Path('/proc/'+str(pid)+'/exe').resolve()==binary, 'actual offline native executable')
                            phase['actualOSPolicy']={'noNewPrivileges':True,'seccompFilterMode':2,'nativeExecutable':str(binary)}
                    elif action=='identity':
                        value=request('/v1/account'); require(value.get('id')==MEMBER, 'exact existing synthetic Bob')
                        phase['accountId']=value['id']
                    elif action in ('self-member','self-member-final'):
                        value=request(PREFIX+'/members/me')
                        observed={key:value.get(key) for key in ('identity','status','permission')}
                        phase['membership'].append({'step':action,**observed}); save()
                        require(observed=={'identity':MEMBER,'status':'active','permission':'reader'}, 'current native Reader authority before/after')
                    elif action in ('sync','sync-final'):
                        value=request(PREFIX+'/sync-status')
                        require(value.get('localPeers')==0 and value.get('globalPeers')==0, 'P2P remains disabled')
                        if offline: require(value.get('networkPeers')==0 and value.get('state')=='offline', 'OS-offline process has no network peers')
                        phase.setdefault('syncObservations',[]).append({key:value[key] for key in ('state','networkPeers','localPeers','globalPeers')})
                    elif action.startswith(('file-','protected-')):
                        file_id=PROTECTED_FILE_ID if action.startswith('protected-') else FILE_ID
                        value=metadata_matches(request(FILE_PREFIX+file_id),file_id,argument)
                        phase['fileMetadata'].append({'step':action,**value})
                        if action=='file-after' and name=='member-offload':
                            result['offloadDispatches'][0]['effectOutcome']='confirmed-cached-true-to-false'
                            result['offloadDispatches'][0]['stage']='204-and-full-tier-cache-eviction-confirmed'
                    elif action.startswith('status-'):
                        value=request(FILE_PREFIX+FILE_ID+'/status')
                        require(value.get('fileId')==FILE_ID and value.get('objectId')==OBJECT and
                                value.get('state')=='durable' and value.get('cached') is argument, 'durable native status matches exact cache state')
                        phase.setdefault('fileStatus',[]).append({'step':action,**value})
                    elif action in ('offload','offline-miss','content'):
                        phase.setdefault('senderAbsence',[]).append(no_competing_account_process(pid))
                        request(OFFLOAD_PATH if action=='offload' else CONTENT_PATH,action)
                        phase.setdefault('senderAbsence',[]).append(no_competing_account_process(pid))
                    else: raise AssertionError('unknown fixed phase step')
                    phase['stepsCompleted'].append(action); step_index+=1; save(); return None
                except BaseException as error:
                    phase.setdefault('error',{'type':type(error).__name__,'message':str(error)})
                    return type(error).__name__+': '+str(error)

            _,process_row=owned.run(output/name,argv,output,environment,120,observe,save_command,
                lambda path:identity(public_bytes(path,LOG_CAP))['sha256'],result['processes'])
            require(phase['stopRequested'] and step_index==len(phase_steps), 'complete finite API phase')
            require(process_row['exitCode']==0 and process_row['processGroupAbsent'] and
                    not process_row['forcedCleanup'] and process_row['cleanupErrors']==[] and
                    process_row['unreapedLeaderDuringGroupCleanup'], 'normal positively closed native group')
            phase['closedPairObservation']=no_competing_account_process()
            guard(force_allocation=True); phase['status']='PASS_PHASE'; save()

        for name in PHASE_NAMES:
            run_phase(name,name in ('member-offline-miss','member-offline-restored'))
        require(len(result['processes'])==4 and len({row['pid'] for row in result['processes']})==4, 'four distinct fresh native processes')
        require(len(result['offloadDispatches'])==1 and result['offloadDispatches'][0]['effectOutcome']=='confirmed-cached-true-to-false', 'one actual positive full-tier Offload')
        require(Counter(row['method'] for row in result['requests'])['POST']==1, 'no additional mutation or quota retry')
        require(Counter(row['kind'] for row in result['requests'])['content']==2 and
                Counter(row['kind'] for row in result['requests'])['offline-miss']==1, 'one cold miss plus exact cloud and cold-restored reads')
        result['positiveFullTierOffloadAccepted']=True
        result['coldUncachedNoContentAccepted']=True
        result['sameCloudCIDRedownloadAccepted']=True
        result['coldRestoredExactBytesAccepted']=True
        result['protectedOtherFileMetadataUnchanged']=True
        result['offlineFailurePresentation']='Original native500/internal; no typed offline-resource UX claim'
        result['status']='PASS_ONE_BACKED_FULL_TIER_OFFLOAD_CLOUD_REFETCH_AND_COLD_READ_ONLY'
    except BaseException as error:
        result['status'] = 'FAIL_BACKED_FULL_TIER_OFFLOAD_RETAINED'
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
                require(len(result['processes'])==4 and result['allOwnedGroupsPositivelyAbsent'], 'complete native process closure')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['processes']), 'clean full lifecycle')
            result['freeAfter'] = guard(force_allocation=True)
        except BaseException as error:
            result['status'] = 'FAIL_BACKED_FULL_TIER_OFFLOAD_RETAINED'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        try: save()
        except BaseException as error:
            result['status'] = 'FAIL_BACKED_FULL_TIER_OFFLOAD_RETAINED'
            result['completionErrors'].append({'receiptRetention': type(error).__name__, 'message': str(error)})
    print(json.dumps({'status': result['status'], 'result': str(output/'result.json'),
                      'offloadDispatches': len(result['offloadDispatches']),
                      'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
