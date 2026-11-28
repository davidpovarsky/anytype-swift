#!/usr/bin/env python3
"""SOURCE ONLY: owner2/removedBob2 on the two new runtime GET endpoints.

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
import types

sys.dont_write_bytecode = True

ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
OUTPUT_PARENT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-http-20261127')
PRODUCER_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
BASELINE = ROOT/'original-native-authority-reader-continuation1/result.json'
BASELINE_SHA = 'ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab'
PRIOR_CUSTODY = '792268b4d7448d9c9b6665ee6388f26c18e5de0635aa05f1b390db7f20a5567d'
CONTENT_RECEIPT = ROOT/'current-authority-http-20261127/attempt1/result.json'
CONTENT_SHA = '7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099'
METADATA_RECEIPT = ROOT/'metadata-authority-http-20261127/attempt1/result.json'
METADATA_SHA = '8aaaf6fd04eb535bea79116ceaeac5a0dab6293d2d40bb1202616a6cef1c94ee'
HERE = Path(__file__).absolute().parent
ADMISSION_SHA = 'f1755272ea4afd1a50d95ba9f085c9f61f25080b389b35359c6cc74337fcb496'
WIRE_VALIDATOR_SHA = 'dde0784eeda0182bf0d0a8ff71aad5f5219fe0856223cc93e6f736e0e2d5a876'
DEADLINE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127/attempt1/result.json')
DEADLINE_RECEIPT_SHA = '0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6'
DEADLINE_SOURCE = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127-source1/verify_current_authority_http.py')
DEADLINE_SOURCE_SHA = '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84'
DEADLINE_FUNCTION_SHA = 'b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81'
OWNER = 'A7MAdySTn1MR4Fb3gDr67ZeXEvt8fqNjtHEwB3b9kUGFZZya'
MEMBER = 'AAFSi1CkNvwiTLAkKWQF9K5GnLcfFaqvfYYCa1zmJWETjuyR'
SPACE = 'bafyreigwbj5ipsthay6xcrt6xcw5hpuagje2jiupq4zhidbevd4miqbrmu.qhz8hrb21y1l'
OBJECT = 'bafyreicytuyyuw7nu6cklsgptni4k5xoyi3u4suijh6lp5moki2nvtpi7e'
NETWORK = 'N72HQKYajADVPoyw2XXtyTScBYR7SwkudRULgED4CYyHdphU'
DATA_DIRS = {'owner': ROOT/'attempt1/alice', 'member': ROOT/'attempt1/bob'}
NODECONF = Path('/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network/mac-public-nodeconf.yml')
NODECONF_SHA = 'fc43639b27c8c7ab50897542a99ecddd3266e85eedf575625d20391684e476e0'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
PREFIX = '/v1/spaces/'+SPACE
RUNTIME_ROUTES = (('space', PREFIX+'/runtime-state'), ('object', PREFIX+'/objects/'+OBJECT+'/runtime-state'))
MIB = 1024**2
ROOT_FLOOR, DEV_FLOOR = 2*1024**3, 512*MIB
ROOT_RESERVE, DEV_RESERVE = 128*MIB, 32*MIB
OUTPUT_CAP, LOG_CAP = 32*MIB, 8*MIB


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
    require(args.output.parent==OUTPUT_PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', args.output.name), 'new owned HTTP output')
    require(args.producer_receipt.parent.parent==PRODUCER_PARENT and args.producer_receipt.name=='result.json' and
            re.fullmatch(r'attempt[1-9][0-9]{0,2}',args.producer_receipt.parent.name) and
            int(args.producer_receipt.parent.name.removeprefix('attempt'))>=7 and
            re.fullmatch(r'[0-9a-f]{64}',args.producer_sha256), 'future exact runtime18 native producer')
    own_path = Path(__file__).absolute()
    own_raw = public_bytes(own_path)
    physical_directory(ROOT)
    physical_directory(OUTPUT_PARENT.parent)
    os.umask(0o077)
    if not OUTPUT_PARENT.exists():
        OUTPUT_PARENT.mkdir(mode=0o700)
        os.chmod(OUTPUT_PARENT,0o700)
    physical_directory(OUTPUT_PARENT)
    output = args.output
    output.mkdir(mode=0o700,exist_ok=False)
    os.chmod(output,0o700)
    for path in (OUTPUT_PARENT.parent,OUTPUT_PARENT,output):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    with (output/'result.json').open('xb') as stream:
        stream.write(b'{}\n');stream.flush();os.fsync(stream.fileno())
    began=time.monotonic();final_deadline=None;last_allocation=0.0;receipt_serial=0
    public_inputs={str(own_path):{'identity':identity(own_raw),'maximum':8*MIB}}
    source=None;expected_source=None;producer=None;joined=None
    result={
        'protocol':'pinkha-native-runtime-state-http-four-v1','status':'RUNNING','controller':identity(own_raw),
        'historicalRemovalFailureSHA256':BASELINE_SHA,'lastKnownClosedCustodySHA256':PRIOR_CUSTODY,
        'reusedContentHTTP14SHA256':CONTENT_SHA,'reusedMetadataHTTP18SHA256':METADATA_SHA,
        'oldContentOrMetadataRoutesReexecuted':0,'accountFileReadsByController':0,'accountCopies':0,
        'privateRecordExports':0,'domainMutationRequests':0,'accountInitializations':0,'roleRestorations':0,
        'uploadCalls':0,'compilerInvocations':0,'newNativeBuilds':0,
        'freshAccountByteCustodyClaim':False,'independentSignedRecordExportClaim':False,
        'nativeOperationalStoreWritesPossible':True,'nativeObjectExistenceClaim':False,
        'heartSyncDateClaim':False,'PersonalSpaceProvenanceClaim':False,
        'newRuntimeRouteOfflineHTTPAcceptance':False,'cloudQuotaActivationCalls':0,
        'processes':[],'phases':[],'requests':[],'errors':[],'completionErrors':[],
        'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR,
            'rootAdmissionReserveBytes':ROOT_RESERVE,'developmentAdmissionReserveBytes':DEV_RESERVE,
            'ownedOutputCapBytes':OUTPUT_CAP,'logCapPerProcessBytes':LOG_CAP,'controllerDeadlineSeconds':360,
            'finalVerificationSeconds':60,'maximumPhaseSeconds':240,'requiredOuterTimeoutSeconds':480,
            'outputAllocationSampleSeconds':1,'workersPerNative':2,'memoryLimitPerNative':'512MiB',
            'maximumConcurrentNativeProcesses':1,'maximumRuntimeGETSeconds':15},
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
        require(path.parent.parent==output and path.parent.name in ('owner-runtime', 'member-runtime'), 'owned native phase')
        require(path.name in ('started.json', 'result.json'), 'owned helper receipt')
        save_json(path, value); save()

    def guard(admit=False, force_allocation=False):
        nonlocal last_allocation
        if final_deadline is None:
            require(time.monotonic()-began<360, '360-second runtime GET deadline')
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
        guard()
        data = public_bytes(path, maximum)
        require(identity(data)['sha256']==wanted, 'public input pin differs: '+str(path))
        public_inputs[str(path)] = {'identity': identity(data), 'maximum': maximum}
        return data

    def source_inventory(root, check):
        physical_directory(root)
        found = {}; modes = {}; stack = [root]; count = 0
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
                    name = path.relative_to(root).as_posix()
                    found[name] = identity(public_bytes(path,128*MIB))
                    modes[name] = stat.S_IMODE(info.st_mode)
        return {'files':found,'modes':modes}

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

    def checked_inputs():
        for name,value in public_inputs.items():
            guard()
            yield name,value

    def interrupted(number, _frame):
        raise RuntimeError('current-authority controller interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        result['admissionFreeBytes']=guard(True,force_allocation=True)
        available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available>=2*1024**3,'unchanged native memory admission')
        result['memAvailableBefore']=available
        def load_pinned(name,sha):
            path=HERE/name;raw=pin(path,sha)
            module=types.ModuleType('runtime_http_'+path.stem)
            module.__file__=str(path)
            exec(compile(raw,str(path),'exec'),module.__dict__)
            return module
        owned=load_pinned('owned_swift_commands.py',HELPER_SHA)
        admission=load_pinned('runtime_product_admission.py',ADMISSION_SHA)
        wire=load_pinned('runtime_wire_validation.py',WIRE_VALIDATOR_SHA)
        ownership=json_object(pin(HELPER_PROOF,HELPER_PROOF_SHA))
        require(ownership['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and ownership['helperSHA256']==HELPER_SHA and
                ownership['allOwnedGroupsPositivelyAbsent'] is True and len(ownership['methods'])==5 and
                all(row['status']=='PASS' for row in ownership['methods']),'actual qualified owner helper')
        result['ownershipHelperSHA256']=HELPER_SHA
        result['reusedOwnershipFiveControlReceiptSHA256']=HELPER_PROOF_SHA
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
        baseline=json_object(pin(BASELINE,BASELINE_SHA))
        content=json_object(pin(CONTENT_RECEIPT,CONTENT_SHA))
        metadata=json_object(pin(METADATA_RECEIPT,METADATA_SHA))
        require(baseline['status']=='FAIL' and baseline['finalAccountInventorySHA256']==PRIOR_CUSTODY and
                baseline['accounts']=={'alice':OWNER,'bob':MEMBER} and baseline['spaceId']==SPACE and baseline['objectId']==OBJECT,
                'exact existing synthetic pair lineage without new byte-custody claim')
        require(baseline['removedMembership']=={'identity':MEMBER,'permission':'none','status':'removed'} and
                baseline['restoreReaderAfterRevocationCalls']==0 and baseline['allOwnedGroupsPositivelyAbsent'] is True and
                len(baseline['mutations'])==1 and baseline['mutations'][0]['label']=='remove-original-bob' and
                baseline['mutations'][0]['status']==204,'sole original removal retained with no restore/replay')
        require(content['status']=='PASS_ORIGINAL_CURRENT_AUTHORITY_HTTP14_ONLY' and content['contentDenialCount']==14 and
                content['allOwnedGroupsPositivelyAbsent'] is True and content['errors']==content['completionErrors']==[],
                'original content14 proof retained without reexecution')
        require(metadata['status']=='PASS_ORIGINAL_CURRENT_METADATA_AUTHORITY_HTTP18_ONLY' and metadata['metadataDenialCount']==18 and
                metadata['allOwnedGroupsPositivelyAbsent'] is True and metadata['errors']==metadata['completionErrors']==[] and
                metadata['publicInputsUnchanged'] is True and metadata['nativeSourceUnchanged'] is True and
                metadata['qualifiedPublicSourcesUnchanged'] is True and len(metadata['processes'])==3 and
                all(row['exitCode']==0 and row['processGroupAbsent'] is True and not row['forcedCleanup'] and
                    row['cleanupErrors']==[] for row in metadata['processes']),'original metadata18 actual scope/closure retained')
        for phase in metadata['phases']:
            require(phase['status']=='PASS_PHASE' and phase['accountId']==({'owner':OWNER,'member':MEMBER}[phase['actor']]),
                    'last observed exact pair authority')
            for row in phase['membership']:
                if row['identity']==MEMBER:
                    require(row['status']=='removed' and row['permission']=='none','preserved removed/none observation')
        joined=admission.admit_product(pin,source_inventory,args.producer_receipt,args.producer_sha256,guard)
        producer=joined['producer'];source=joined['source'];expected_source=joined['sourceInventory'];binary=joined['binary']
        result['runtimeNativeProducer']={'receiptPath':str(args.producer_receipt),'receiptSHA256':args.producer_sha256,
            'binary':joined['binaryIdentity'],'compiledSourceInputSHA256':producer['compiledSourceInputSHA256'],
            'sourceManifestSHA256':producer['sourceManifestSHA256'],'sourceFiles':1638,'sdkSourceFiles':750,
            'newQualificationEvents':18,'C13RetainedActualMethods':13,'oldMethodsReexecuted':0}
        public_nodeconf=pin(NODECONF,NODECONF_SHA,65536)
        require(re.findall(rb'^networkId: ([^\r\n]+)$',public_nodeconf,re.MULTILINE)==[NETWORK.encode()],
                'exact public original network identity')
        for directory in DATA_DIRS.values():physical_directory(directory)
        result['closedPairProcessAdmission']=no_competing_account_process()
        config=output/'network.yml'
        config_text=('network:\n  nodeconfPath: '+str(NODECONF)+'\nindex:\n  embedder: none\np2p:\n'
                     '  enabled: true\n  localDiscovery: true\n  serviceName: _pinkha-fv2._tcp\n'
                     '  global:\n    enabled: false\n')
        with config.open('x') as stream:stream.write(config_text);stream.flush();os.fsync(stream.fileno())
        public_inputs[str(config)]={'identity':identity(config_text.encode()),'maximum':65536}
        responses=output/'responses';responses.mkdir(mode=0o700);os.chmod(responses,0o700)
        runtime_paths={path for _,path in RUNTIME_ROUTES}
        metadata_paths={'/v1/health','/v1/account',PREFIX+'/members/me',PREFIX+'/members/'+MEMBER}|runtime_paths
        denial_paths=runtime_paths
        require(len(RUNTIME_ROUTES)==len(runtime_paths)==2,'two distinct new runtime GET routes only')
        def run_phase(name, actor):
            # There is at most one live native process. These checks inspect
            # only process metadata, public inputs and the directory itself.
            guard(force_allocation=True); no_competing_account_process()
            for path in (binary, config, NODECONF):
                admitted = public_inputs[str(path)]
                require(identity(public_bytes(path, admitted['maximum']))==admitted['identity'], 'phase input changed')
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
            argv = [str(binary), 'run', '--config', str(config), '--data-dir', str(DATA_DIRS[actor]), '--addr', '127.0.0.1:'+str(port)]
            environment = {key: value for key, value in os.environ.items() if not key.startswith('ANY_')}
            environment.update(ANY_DATA_DIR=str(DATA_DIRS[actor]), GOMAXPROCS='2', GOMEMLIMIT='512MiB')
            phase = {'name': name, 'actor': actor, 'offline': False, 'stepsCompleted': [], 'stopRequested': False,
                     'denials': [], 'membership': [], 'observations': []}
            result['phases'].append(phase); save()
            ledger_index = len(result['processes'])
            phase_started = time.monotonic(); state = {'readyAt': None, 'membershipWaitAt': None}
            phase_steps = [('health', None), ('identity', None), ('self-member', None)]
            if actor=='owner':
                phase_steps += [('removed-member', None)]+[('runtime', row) for row in RUNTIME_ROUTES]+[('removed-member-final', None), ('self-member-final', None)]
            else:
                phase_steps += [('deny', row) for row in RUNTIME_ROUTES]+[('self-member-final', None)]
            step_index = 0

            def request(path, denial=False, health=False):
                require(path in denial_paths if denial else path in metadata_paths, 'GET-only fixed authority/runtime allowlist')
                row = {'phase': name, 'method': 'GET', 'path': path, 'range': None,
                       'stage': 'dispatching', 'bodyReadInvocations': 0, 'kind': 'runtime-denial' if denial else 'runtime-observation' if path in runtime_paths else 'identity-or-membership'}
                result['requests'].append(row); save(); guard()
                # Only bounded transport work runs under the alarm. Persistence
                # happens after its handler/mask are restored, so an HTTP
                # deadline cannot interrupt the evidence-retention path.
                try:
                    remaining = min(360-(time.monotonic()-began), 240-(time.monotonic()-phase_started))
                    require(remaining>0, 'complete request has no controller or phase budget')
                    with absolute_http_deadline(min(2 if health else 15 if path in runtime_paths else 5, remaining)):
                        raw = request_with_deadline(row, path, denial, health)
                    if health:
                        row['stage'] = 'ready-status'; save(); return {'ready': True}
                    row['response'] = identity(raw)
                    if path in runtime_paths:
                        evidence=responses/(str(len(result['requests'])).zfill(3)+'.json')
                        with evidence.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                        require(public_bytes(evidence,65536)==raw,'complete bounded runtime response retained')
                        fd=os.open(responses,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                        try:os.fsync(fd)
                        finally:os.close(fd)
                        row['responsePath']=str(evidence)
                    value = json_object(raw)
                    if row['status']==403:
                        wire.denial(value,SPACE,OBJECT if path==RUNTIME_ROUTES[1][1] else None)
                        row['errorCode'] = 'acl.forbidden'; row['stage'] = 'confirmed-typed-denial'; save()
                        return {'typedDenial': True}
                    row['stage'] = 'metadata-response'; save(); return value
                except BaseException as error:
                    row.setdefault('failure', {'type': type(error).__name__, 'message': str(error)})
                    save(); raise

            def request_with_deadline(row, path, denial, health):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2 if health else 15 if path in runtime_paths else 5)
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
                        raise AssertionError('unexpected HTTP status; runtime body not consumed')
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
                            if action.endswith('-final') or self_owner:
                                raise AssertionError('current membership differs')
                            state['membershipWaitAt'] = state['membershipWaitAt'] or time.monotonic()
                            require(time.monotonic()-state['membershipWaitAt']<90, 'existing removal did not become current')
                            return None
                        state['membershipWaitAt'] = None
                    elif action=='runtime':
                        label,route=argument
                        value=request(route)
                        if label=='space':
                            captured=wire.owner_space(value,OWNER,NETWORK,SPACE,OWNER)
                        else:
                            captured=wire.owner_object(value,OWNER,NETWORK,SPACE,OWNER,OBJECT)
                        if 'runtimeScope' not in phase:phase['runtimeScope']=captured
                        require(captured==phase['runtimeScope'],'same exact authority/head stamp across the two owner observations')
                        phase['observations'].append({'label':label,'route':route,'value':value})
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
            if actor=='member': require(phase['denials']==[label for label,_ in RUNTIME_ROUTES], 'both distinct new runtime denial decisions')
            else:require([row['label'] for row in phase['observations']]==[label for label,_ in RUNTIME_ROUTES],'both scoped owner observations')
            guard(force_allocation=True)
            phase['status'] = 'PASS_PHASE'; phase['logSHA256'] = process_row['logSHA256']; save()

        run_phase('owner-runtime','owner')
        run_phase('member-runtime','member')
        require(len(result['processes'])==2 and len({row['pid'] for row in result['processes']})==2,
                'two sequential fresh native process identities')
        observations=[row for row in result['requests'] if row['kind']=='runtime-observation']
        denials=[row for row in result['requests'] if row['kind']=='runtime-denial']
        require(len(observations)==2 and all(row['phase']=='owner-runtime' and row['status']==200 and
                row['stage']=='metadata-response' and row.get('responsePath') for row in observations),'two actual owner observations')
        require(len(denials)==2 and all(row['phase']=='member-runtime' and row['status']==403 and
                row.get('errorCode')=='acl.forbidden' and row['stage']=='confirmed-typed-denial' and row.get('responsePath')
                for row in denials),'two actual revoked-reader typed no-payload denials')
        require(Counter(row['path'] for row in observations)==Counter(runtime_paths) and
                Counter(row['path'] for row in denials)==Counter(runtime_paths),'each new route exactly once per authority')
        result['ownerObservationCount']=2;result['removedMemberDenialCount']=2
        result['status']='PASS_CURRENT_AUTHORITY_RUNTIME_GET4_ONLY'
    except BaseException as error:
        result['status']='FAIL_RUNTIME_GET4_PRESERVED'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent']=bool(result['processes']) and all(row.get('processGroupAbsent') is True for row in result['processes'])
        final_deadline=time.monotonic()+60
        audits=[('publicInputsUnchanged',True,lambda:all(
            identity(public_bytes(Path(name),value['maximum']))==value['identity']
            for name,value in checked_inputs())),
            ('nativeSourceUnchanged',expected_source is not None,lambda:source_inventory(source,guard)==expected_source),
            ('originalC13SourceUnchanged',joined is not None,lambda:source_inventory(joined['baseSource'],guard)==joined['baseInventory'])]
        for label,available,action in audits:
            if not available:
                result[label]='NOT_ADMITTED';continue
            try:
                guard();require(action(),label+' failed');result[label]=True
            except BaseException as error:
                result['status']='FAIL_RUNTIME_GET4_PRESERVED'
                result['completionErrors'].append({'scope':label,'type':type(error).__name__,'message':str(error)})
        try:
            if producer is not None:
                require(stat.S_IMODE(binary.lstat().st_mode)==producer['nativeBinary']['mode'],'native executable mode unchanged')
                for tool in producer['currentNativeCompilerObservation']['tools'].values():
                    guard();require(stat.S_IMODE(Path(tool['path']).lstat().st_mode)==tool['mode'],'admitted compiler mode unchanged')
                result['productAndCompilerModesUnchanged']=True
            for row in result['requests']:
                if 'responsePath' in row:
                    guard();require(identity(public_bytes(Path(row['responsePath']),65536))==row['response'],'retained runtime response changed')
            result['runtimeResponsesUnchanged']=True
            if result['status'].startswith('PASS_'):
                require(len(result['processes'])==2 and result['allOwnedGroupsPositivelyAbsent'] and
                        all(row['exitCode']==0 and row['forcedCleanup'] is False and row['cleanupErrors']==[] and row['signals']==[]
                            for row in result['processes']) and result['errors']==result['completionErrors']==[],
                        'both normal native closures and complete final integrity')
            result['freeAfter']=guard(force_allocation=True)
        except BaseException as error:
            result['status']='FAIL_RUNTIME_GET4_PRESERVED'
            result['completionErrors'].append({'scope':'final-resources-and-closure','type':type(error).__name__,'message':str(error)})
        try:save()
        except BaseException as error:
            result['status']='FAIL_RUNTIME_GET4_PRESERVED'
            result['completionErrors'].append({'scope':'receipt-retention','type':type(error).__name__,'message':str(error)})
            print(json.dumps(result,sort_keys=True),flush=True)
            raise
    retained=public_bytes(output/'result.json')
    print(json.dumps({'status':result['status'],'result':str(output/'result.json'),**identity(retained),
        'allOwnedGroupsPositivelyAbsent':result['allOwnedGroupsPositivelyAbsent'],
        'ownerObservationCount':result.get('ownerObservationCount',0),'removedMemberDenialCount':result.get('removedMemberDenialCount',0),
        'errors':result['errors'],'completionErrors':result['completionErrors']},sort_keys=True),flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
