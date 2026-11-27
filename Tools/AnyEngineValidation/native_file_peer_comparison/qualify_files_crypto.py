#!/usr/bin/env python3
"""Run unchanged native cipher/CID-integrity boundary tests, with explicit evidence."""
import importlib.util,json,os,pathlib,shutil,signal,subprocess,time

ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
OUT=ROOT/'files-crypto-integrity1'
SDK=ROOT/'acl-refresh-overlay1/sdk-source'
SOURCE=pathlib.Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/resume_linux_filesv2_invite.py')
spec=importlib.util.spec_from_file_location('fv2',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CACHE=pathlib.Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET=pathlib.Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
FLOOR=2*1024**3;DEV_FLOOR=512*1024**2
TEMP=pathlib.Path('/mnt/development/projects/caches/pinkha-w1-files-crypto-temp-20261127')
CASES={
 'github.com/anyproto/any-sync-sdk/internal/files/crypt':{'TestEncryptFormat','TestReaderSeek'},
 'github.com/anyproto/any-sync-sdk/internal/files/carfile':{'TestReadBlockDetectsCorruption','TestSparseWriteRejects'},
 'github.com/anyproto/any-sync-sdk/internal/files/fetch':{'TestLyingPeerFallsBackToHTTPAndBans'},
 'github.com/anyproto/any-sync-sdk/internal/files/store':{'TestCorruptBlockHeals','TestWriteBlockVerifiesWhenNotPersistable'},
 'github.com/anyproto/any-sync-sdk/internal/payloads':{'TestUnseal_WrongKeyFails','TestDeriveEncKey_DomainSeparated'},
}
os.umask(0o077);OUT.mkdir(exist_ok=False)
result={'protocol':'unchanged-native-files-cipher-cid-integrity-v1','status':'RUNNING','nativeAccountRuns':0,'nativeFileTransferAcceptance':False,'tests':[],'processes':[],'errors':[]}
expected=None
def save():m.atomic(OUT/'result.json',result)
def inventory():return {str(p.relative_to(SDK)):m.sha(p) for p in SDK.rglob('*') if p.is_file()}
def guard():
    root_free=shutil.disk_usage(OUT).free;dev_free=shutil.disk_usage(CACHE_TARGET).free
    result['minimumRootFreeBytes']=min(result.get('minimumRootFreeBytes',root_free),root_free)
    result['minimumDevelopmentFreeBytes']=min(result.get('minimumDevelopmentFreeBytes',dev_free),dev_free)
    assert root_free>=FLOOR,'2 GiB root emergency floor'
    assert dev_free>=DEV_FLOOR,'512 MiB development emergency floor'
    return root_free,dev_free
try:
    result['sourceBefore']=m.source_admission()
    expected=json.loads(m.pinned(ROOT/'acl-refresh-overlay1/sdk-overlay-manifest.json','81fb6bf29c672010f7fe98554ae562b7e75b6154f10e933ac5682fe3916c4a4a',4*1024**2))
    assert inventory()==expected
    result['overlayManifestSHA256']=m.sha(ROOT/'acl-refresh-overlay1/sdk-overlay-manifest.json')
    result['controllerSHA256']=m.sha(pathlib.Path(__file__))
    assert CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET
    root_free,dev_free=guard()
    mem={line.split(':')[0]:int(line.split(':')[1].split()[0])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemAvailable','SwapFree')}
    assert mem['MemAvailable']>=3*1024**3,'3 GiB available memory preflight'
    assert root_free>=FLOOR+64*1024**2 and dev_free>=DEV_FLOOR+512*1024**2,'focused test compile admission reserves'
    assert not TEMP.exists(),'dedicated test temporary directory must be new'
    TEMP.mkdir()
    assert TEMP.stat().st_dev==CACHE_TARGET.stat().st_dev and TEMP.stat().st_dev!=OUT.stat().st_dev
    result['resourcePolicy']={'rootEmergencyFloor':FLOOR,'rootReserveBytes':64*1024**2,'developmentEmergencyFloor':DEV_FLOOR,'developmentReserveBytes':512*1024**2,'rootFreeBefore':root_free,'developmentFreeBefore':dev_free,'cacheResolved':str(CACHE.resolve()),'tempResolved':str(TEMP.resolve()),'rootDevice':OUT.stat().st_dev,'tempDevice':TEMP.stat().st_dev,'memoryBefore':mem,'logCapBytes':16*1024**2,'workers':2,'reason':'Existing qualified SDK source and offline module cache; all Go test binaries and temporary intermediates on development alongside unchanged GOCACHE. Root stores bounded evidence only. Both emergency floors unchanged.'}
    env=os.environ.copy();env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE=str(CACHE),GOMODCACHE='/root/go/pkg/mod',GOTMPDIR=str(TEMP),TMPDIR=str(TEMP),CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
    names=sorted(set().union(*CASES.values()));pattern='^('+ '|'.join(names)+')$'
    cmd=['/usr/local/bin/go','test','-p=2','-count=1','-json','-timeout=120s','-run',pattern]+['./'+v.removeprefix('github.com/anyproto/any-sync-sdk/') for v in CASES]
    row={'label':'original-native-cipher-integrity-tests','command':cmd};result['processes'].append(row)
    started=time.monotonic()
    with (OUT/'tests.log').open('xb') as stream:
        p=subprocess.Popen(cmd,cwd=SDK,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        row.update(pid=p.pid,pgid=p.pid);save()
        try:
            while p.poll() is None:
                guard()
                assert (OUT/'tests.log').stat().st_size<16*1024**2,'bounded actual test log'
                assert time.monotonic()-started<300,'bounded native integrity test deadline'
                time.sleep(.5)
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
            row.update(exitCode=p.returncode,seconds=round(time.monotonic()-started,3))
            try:os.killpg(p.pid,0);row['groupPositivelyAbsent']=False
            except ProcessLookupError:row['groupPositivelyAbsent']=True
    row['logSHA256']=m.sha(OUT/'tests.log')
    events=[]
    for line in (OUT/'tests.log').read_text().splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    assert p.returncode==0 and row['groupPositivelyAbsent'],'actual native integrity tests failed'
    assert not any(e.get('Action') in ('fail','skip') for e in events)
    passes=[e for e in events if e.get('Action')=='pass' and e.get('Test') in CASES.get(e.get('Package'),set())]
    wanted={(package,name) for package,tests in CASES.items() for name in tests}
    assert {(e['Package'],e['Test']) for e in passes}==wanted and len(passes)==len(wanted)
    result['tests']=[{'package':e['Package'],'name':e['Test'],'seconds':e.get('Elapsed')} for e in passes]
    result['interpretation']={'fileCipher':'Heart-compatible fresh per-file-key AES-256-CFB; integrity provided by ciphertext Merkle CIDs','metadataCipher':'AES-GCM with domain-separated object/read-key context','newOriginalTests':len(wanted),'priorSignedACLTestsRerun':0,'wholeNetworkFileTransferClaimed':False}
    result['status']='PASS_ORIGINAL_NATIVE_CIPHER_CID_INTEGRITY_TESTS_ONLY'
except BaseException as e:result.update(status='FAIL_NATIVE_INTEGRITY_QUALIFICATION',error=repr(e))
finally:
    try:
        result['sourceAfter']=m.source_admission()
        assert result['sourceBefore']==result['sourceAfter']
    except BaseException as e:result['status']='FAIL_NATIVE_INTEGRITY_QUALIFICATION';result['errors'].append({'originalSource':repr(e)})
    try:
        result['overlaySourceUnchanged']=expected is not None and inventory()==expected
        assert result['overlaySourceUnchanged']
    except BaseException as e:result['status']='FAIL_NATIVE_INTEGRITY_QUALIFICATION';result['errors'].append({'qualifiedOverlaySource':repr(e)})
    result['allOwnedGroupsPositivelyAbsent']=all(v.get('groupPositivelyAbsent',False) for v in result['processes'])
    if not result['allOwnedGroupsPositivelyAbsent']:result['status']='FAIL_NATIVE_INTEGRITY_QUALIFICATION'
    result['rootFreeAfter']=shutil.disk_usage(OUT).free
    if CACHE_TARGET.exists():result['developmentFreeAfter']=shutil.disk_usage(CACHE_TARGET).free
    save();print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS_ORIGINAL_NATIVE_CIPHER_CID_INTEGRITY_TESTS_ONLY' else 1)
