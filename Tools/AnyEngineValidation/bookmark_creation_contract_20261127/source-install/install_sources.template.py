"""Install one immutable, exclusive Bookmark and recovery source packet; no runtime."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import sys
import time

PAYLOAD_BASE64 = '__PAYLOAD_BASE64__'
PAYLOAD_SHA256 = '__PAYLOAD_SHA256__'
PARENT = Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127')
PREPARED = PARENT/'prepared1'
OUT = PARENT/'prepared1-install-attempt1'
CONTROL = 'qualification/'
EXPECTED_CONTROLLER = '6e715e0dc316f3b08ded6322121339a61f2044b55a909cb61dca4fa72852d9e0'
EXPECTED_MANIFEST = 'eb2b91a339f9f2f9ccaf30220fc1fc52781d960e3efdc5d68a8ae270dcb9ef83'
EXPECTED_PATHS = {
    'Sources/AnyNativeBookmarkCreationFrame.swift',
    'Sources/AnyNativeObjectCreator.swift',
    'Tests/AnyNativeBookmarkCreationFrameTests.swift',
    'Tests/AnyNativeFileAttachmentPostCloseTests.swift',
    'Tests/AnyNativeObjectCreationExactValueTests.swift',
    'qualification/bookmark-component-inputs.json',
    'qualification/crypto-header-source-manifest.json',
    'qualification/owned_swift_commands.py',
    'qualification/qualify_bookmark_crypto_c3.py',
    'qualification/qualify_current_c3_crypto.py',
    'qualification/run_bookmark_components.py',
}

MIB = 1024**2
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
started = time.monotonic()
owned_out = False
owned_prepared = False
owned_parent = False
controller_raw = None
final_deadline = None
result = {'status':'RUNNING_SOURCE_INSTALL_ONLY', 'compilerInvocations':0,
    'nativeInvocations':0, 'accountInputs':0, 'testMethodsExecuted':0,
    'preparedRoot':str(PREPARED), 'payloadSHA256':PAYLOAD_SHA256,
    'originalPathsReplaced':0, 'installedFiles':{}, 'errors':[]}

def require(value, message):
    if not value:
        raise RuntimeError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def physical(path):
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical source path required')

def frozen(path):
    physical(path)
    before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=MIB,
            'bounded ordinary source file')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as stream:
        require(os.fstat(stream.fileno())==before,'exact opened source identity')
        raw=stream.read(MIB+1)
        require(os.fstat(stream.fileno())==before,'source unchanged during read')
    require(path.lstat()==before and len(raw)==before.st_size,'complete unchanged source read')
    return raw

def sync_directory(path):
    physical(path)
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def write_new(path, raw):
    physical(path)
    physical(path.parent)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    require(frozen(path)==raw,'exclusive complete retention readback')
    sync_directory(path.parent)

def allocated(root):
    if not root.exists():
        return 0
    total = root.lstat().st_blocks*512
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path=Path(directory)/name
            require(not path.is_symlink(), 'no source aliases')
            total+=path.lstat().st_blocks*512
    return total

def guard():
    require(time.monotonic()<(final_deadline if final_deadline is not None else started+45),
            'source installer/final retention deadline')
    require(shutil.disk_usage('/').free>=ROOT_FLOOR, 'root emergency floor')
    require(shutil.disk_usage('/mnt/development').free>=DEV_FLOOR, 'development emergency floor')
    require(allocated(PREPARED)+allocated(OUT)<=8*MIB, 'bounded source and install receipt allocation')

def interrupted(number, _frame):
    raise RuntimeError('source installation interrupted by signal '+str(number))

try:
    require(not sys.flags.optimize, 'all guards enabled')
    os.umask(0o077)
    for number in (signal.SIGTERM,signal.SIGINT):
        signal.signal(number,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    for path in (PARENT,PREPARED,OUT):
        physical(path)
    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'authorized Oracle host')
    physical(PARENT.parent)
    require(PARENT.parent.is_dir() and not os.path.lexists(PARENT), 'exclusive complete Host preparation namespace')
    controller_raw=frozen(Path(__file__).absolute())
    result['installerSHA256']=digest(controller_raw)
    result['resourcePolicy']={'activeSeconds':45,'finalVerificationSeconds':15,
        'requiredOuterSeconds':90,'ownedOutputCapBytes':8*MIB,
        'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR}
    result['freeBefore']={p:shutil.disk_usage(p).free for p in ('/','/mnt/development')}
    require(result['freeBefore']['/']>=ROOT_FLOOR+32*MIB and
            result['freeBefore']['/mnt/development']>=DEV_FLOOR+32*MIB, 'fresh source admission')
    raw=base64.b64decode(PAYLOAD_BASE64,validate=True)
    require(len(raw)<=MIB and digest(raw)==PAYLOAD_SHA256, 'exact bounded prepared payload')
    payload=json.loads(raw)
    require(payload['status']=='PREPARATION_PAYLOAD_ONLY_NOT_INSTALLED_COMPILED_OR_RUN', 'source-only payload')
    require(payload['preparedRoot']==str(PREPARED), 'fixed prepared root')
    require(payload['controllerSHA256']==EXPECTED_CONTROLLER and payload['inputManifestSHA256']==EXPECTED_MANIFEST,
            'final component source pins')
    require(payload['expectedComponentMethodCount']==31 and payload['compiledExcludedNativeMethods']==0 and
            payload['excludedNativeStatus']=='NOT_RUN', 'finite component/native selection')
    rows=payload['files']
    require(len(rows)==11 and len({row['path'] for row in rows})==11 and
            {row['path'] for row in rows}==EXPECTED_PATHS, 'exact fixed Host source members')
    decoded={}
    for row in rows:
        rel=PurePosixPath(row['path'])
        require(not rel.is_absolute() and '..' not in rel.parts and str(rel)==row['path'], 'safe source member')
        data=base64.b64decode(row['contentBase64'],validate=True)
        require(len(data)==row['bytes'] and digest(data)==row['sha256'], 'source member identity')
        decoded[row['path']]=data
    require(sum(len(data) for data in decoded.values())<=MIB, 'bounded total source size')
    require(digest(decoded[CONTROL+'run_bookmark_components.py'])==EXPECTED_CONTROLLER and
            digest(decoded[CONTROL+'bookmark-component-inputs.json'])==EXPECTED_MANIFEST, 'embedded controller/input identity')
    manifest=json.loads(decoded[CONTROL+'bookmark-component-inputs.json'])
    methods=manifest['methods']
    require({name:len(values) for name,values in methods.items()}=={'AnyNativeBookmarkCreationFrameTests': 20, 'AnyNativeFileAttachmentPostCloseTests': 4, 'AnyNativeObjectCreationExactValueTests': 7},
            'exact named new Host suite sizes')
    require(len({name+'.'+method for name,values in methods.items() for method in values})==31,
            'exact distinct new methods; original upload35 not selected')
    require(manifest['expectedCounts']['httpFixtureInstances']==17 and
            manifest['expectedCounts']['httpRequests']==76 and
            manifest['expectedCounts']['objectCreatePOSTs']==0,
            'original finite Bookmark HTTP obligations')
    PARENT.mkdir(mode=0o700)
    owned_parent = True
    physical(PARENT)
    sync_directory(PARENT.parent)
    OUT.mkdir(mode=0o700)
    owned_out = True
    sync_directory(PARENT)
    write_new(OUT/'original-payload.json',raw)
    write_new(OUT/'original-installer.py',controller_raw)
    PREPARED.mkdir(mode=0o700)
    owned_prepared = True
    sync_directory(PARENT)
    for name,data in sorted(decoded.items()):
        guard()
        path=PREPARED/name
        physical(path)
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        require(stat.S_ISREG(path.lstat().st_mode) and path.lstat().st_nlink==1 and path.read_bytes()==data,
                'exclusive physical source readback')
        result['installedFiles'][name]={'bytes':len(data),'sha256':digest(data),'mode':stat.S_IMODE(path.stat().st_mode)}
        sync_directory(path.parent)
    actual={path.relative_to(PREPARED).as_posix() for path in PREPARED.rglob('*') if path.is_file()}
    require(actual==EXPECTED_PATHS, 'complete installed source inventory')
    for name,data in decoded.items():
        guard()
        require((PREPARED/name).read_bytes()==data, 'all installed sources unchanged')
    for directory,_,_ in os.walk(PREPARED,topdown=False):
        guard()
        sync_directory(Path(directory))
    sync_directory(PARENT)
    sync_directory(PARENT.parent)
    guard()
    result['status']='PASS_EXACT_SOURCE_INSTALL_ONLY_NOT_COMPILED_OR_RUN'
except BaseException as error:
    result['status']='FAIL_SOURCE_INSTALL_PRESERVED'
    result['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
    for number in (signal.SIGTERM,signal.SIGINT):
        signal.signal(number,signal.SIG_IGN)
    final_deadline=min(started+60,time.monotonic()+15)
    try:
        guard()
        result['freeAfter']={p:shutil.disk_usage(p).free for p in ('/','/mnt/development')}
        if controller_raw is not None:
            require(frozen(Path(__file__).absolute())==controller_raw,'installer unchanged at completion')
            result['installerUnchangedAtCompletion']=True
        if owned_prepared:
            for name,wanted in result['installedFiles'].items():
                guard()
                path=PREPARED/name
                data=frozen(path)
                require(len(data)==wanted['bytes'] and digest(data)==wanted['sha256'] and
                        stat.S_IMODE(path.lstat().st_mode)==wanted['mode'],
                        'installed source and mode unchanged at completion')
            if result['status'].startswith('PASS_'):
                require(set(result['installedFiles'])==EXPECTED_PATHS and
                        {p.relative_to(PREPARED).as_posix() for p in PREPARED.rglob('*') if p.is_file()}==EXPECTED_PATHS,
                        'complete final source membership')
            result['installedSourceBytesAndModesUnchanged']=True
            for directory,_,_ in os.walk(PREPARED,topdown=False):
                guard()
                sync_directory(Path(directory))
        if owned_out:
            sync_directory(OUT)
        if owned_parent:
            sync_directory(PARENT)
            sync_directory(PARENT.parent)
        result['ownedAllocatedBytes']=(allocated(PREPARED) if owned_prepared else 0)+(allocated(OUT) if owned_out else 0)
        guard()
    except BaseException as error:
        result['status']='FAIL_SOURCE_INSTALL_PRESERVED'
        result['errors'].append({'phase':'final-source-and-resources','type':type(error).__name__,'message':str(error)})
    result['seconds']=time.monotonic()-started
    persisted=False
    if owned_out:
        try:
            require(time.monotonic()<final_deadline,'bounded terminal receipt retention')
            encoded=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
            require(len(encoded)<=MIB,'bounded source installation receipt')
            write_new(OUT/'result.json',encoded)
            sync_directory(PARENT)
            sync_directory(PARENT.parent)
            readback=frozen(OUT/'result.json')
            require(readback==encoded,'original installation receipt readback')
            persisted=True
        except BaseException as error:
            result['status']='FAIL_SOURCE_INSTALL_PRESERVED'
            result['errors'].append({'phase':'terminal-retention','type':type(error).__name__,'message':str(error)})
    if persisted:
        print(json.dumps({'status':result['status'],'receiptPath':str(OUT/'result.json'),
            'receiptSHA256':digest(readback),'installedFiles':len(result['installedFiles']),'errors':result['errors']}))
    else:
        result['terminalReceiptVerified']=False
        print(json.dumps(result))
if result['status'].startswith('FAIL'):
    raise SystemExit(1)
