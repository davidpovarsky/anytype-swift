import importlib.util,json,pathlib,os,time,signal,subprocess,shutil

ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
OUT=ROOT/'acl-refresh-native1'
BASE=pathlib.Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current')
OVERLAY=ROOT/'acl-refresh-overlay1'
REPO=pathlib.Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077);OUT.mkdir(exist_ok=False)
FLOOR=2*1024**3;DEV_FLOOR=512*1024**2
CACHE=pathlib.Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET=pathlib.Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
DEV_TMP=CACHE_TARGET.parent/'pinkha-w1-t2-native-build-tmp-20261127'
result={'protocol':'pinkha-acl-refresh-qualified-native-build-v2','status':'RUNNING','actualFilesV2Acceptance':False,'nativeAccountRuns':0,'floorBytes':FLOOR,'developmentFloorBytes':DEV_FLOOR,'estimatedNewBytesAcrossBothMounts':512*1024**2,'processes':[],'errors':[]}
before=None

def save():m.atomic(OUT/'result.json',result)
def resources():
    root_free=shutil.disk_usage(OUT).free;dev_free=shutil.disk_usage(CACHE_TARGET).free
    result['minimumFreeBytes']=min(result.get('minimumFreeBytes',root_free),root_free)
    result['minimumDevelopmentFreeBytes']=min(result.get('minimumDevelopmentFreeBytes',dev_free),dev_free)
    assert root_free>=FLOOR,'2 GiB root floor reached'
    assert dev_free>=DEV_FLOOR,'512 MiB development floor reached'
    return root_free,dev_free
def inventory(root):
    out={}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file():
            assert p.stat().st_nlink==1,str(p)
            out[str(p.relative_to(root))]={'sha256':m.sha(p),'bytes':p.stat().st_size}
    return out

try:
    result['sourceBefore']=m.source_admission()
    unit=json.loads(m.pinned(ROOT/'acl-refresh-hook1/result.json','bd35ba50a31ba7cc82c73a20a19fa7eeb96f4e5027d957976d46eba744425d5d',1024**2))
    assert unit['status']=='PASS_FOCUSED_SDK_TESTS_NOT_NATIVE_ACCEPTANCE'
    assert unit['allOwnedGroupsPositivelyAbsent'] and unit['overlaySourceUnchanged'] and len(unit['tests'])==6
    result['focusedTestReceiptSHA256']=m.sha(ROOT/'acl-refresh-hook1/result.json')
    replay=json.loads(m.pinned(ROOT/'acl-refresh-replay2/result.json','316aa607523802417380357481bca061d6dfe33d5f1557f0d25eeb23695f5b14',1024**2))
    assert replay['status']=='PASS_SOURCE_REPLAY_ONLY' and replay['originalSourceUnchanged']
    assert replay['overlayManifestSHA256']==unit['overlayManifestSHA256']=='81fb6bf29c672010f7fe98554ae562b7e75b6154f10e933ac5682fe3916c4a4a'
    result['sourceReplayReceiptSHA256']=m.sha(ROOT/'acl-refresh-replay2/result.json')
    relocation=json.loads(m.pinned(ROOT/'t2-cache-relocation1/move.json','3ba3f726836b48910391cf26bdbca3430223cb274fdc583691f17ae54d6a11e9',1024**2))
    assert relocation['status']=='PASS_CACHE_RELOCATED_AND_BYTES_MODES_PRESERVED'
    assert relocation['allFilesHashModeOwnerMtimePreserved'] and relocation['copiedFiles']==7862
    assert CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET and CACHE_TARGET.resolve()==CACHE_TARGET
    assert OUT.stat().st_dev!=CACHE_TARGET.stat().st_dev,'expected distinct root and development volumes'
    root_free,dev_free=resources()
    # Keep the total reserved envelope at 512 MiB. Only the location of the
    # 256 MiB temporary-work allowance changes; source/product and cache-growth
    # reserves remain 128 MiB each. Both emergency floors are unchanged.
    concurrent_root_reserve=128*1024**2
    mem_available=int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    assert mem_available>=3*1024**3,'insufficient available RAM for coordinated native and Swift slots'
    if root_free>=FLOOR+384*1024**2+concurrent_root_reserve and dev_free>=DEV_FLOOR+128*1024**2:
        tmp=OUT/'tmp';root_reserve=384*1024**2;dev_reserve=128*1024**2
    else:
        assert root_free>=FLOOR+128*1024**2+concurrent_root_reserve and dev_free>=DEV_FLOOR+384*1024**2,'insufficient native build reserves on actual mounts'
        tmp=DEV_TMP;root_reserve=128*1024**2;dev_reserve=384*1024**2
    result['resourcePolicy']={'rootReserveBytes':root_reserve,'developmentReserveBytes':dev_reserve,'temporaryWorkPath':str(tmp),'cachePath':str(CACHE),'cacheResolvedPath':str(CACHE.resolve()),'rootDevice':OUT.stat().st_dev,'developmentDevice':CACHE_TARGET.stat().st_dev,'rootFreeBefore':root_free,'developmentFreeBefore':dev_free,'sourceProductReserveBytes':128*1024**2,'cacheGrowthReserveBytes':128*1024**2,'temporaryWorkReserveBytes':256*1024**2}
    result['relocationReceiptSHA256']=m.sha(ROOT/'t2-cache-relocation1/move.json')
    result['resourcePolicy'].update(coordinatedOtherRootReserveBytes=concurrent_root_reserve,memAvailableBefore=mem_available,minimumAdmissionMemAvailableBytes=3*1024**3)
    manifest=json.loads(m.pinned(BASE/'source-manifest.json','12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c',8*1024**2))
    baseExpected={k:{'sha256':v['sha256'],'bytes':v['bytes']} for k,v in manifest['files'].items()}
    cache_manifest=json.loads(m.pinned(ROOT/'t2-cache-relocation1/manifest.json','6acb9b65bed461078eefbfae482be254884b0c0dcdbd14c0f1068149aa37559d',8*1024**2))['files']
    touched=[v for v in cache_manifest.values() if 1795739147.0388591<=v['mtimeNs']/1e9<=1795739171.0388591]
    assert len(touched)==198 and sum(v['allocatedBytes'] for v in touched)==51154944
    result['resourceEstimateEvidence']={'qualifiedProductionHookSeconds':23.028,'preservedCacheManifestSHA256':'6acb9b65bed461078eefbfae482be254884b0c0dcdbd14c0f1068149aa37559d','productionHookTouchedCacheEntries':len(touched),'productionHookTouchedAllocatedBytes':sum(v['allocatedBytes'] for v in touched),'cacheWindowIncludesTouchedHits':True,'baseNativeBinaryBytes':(BASE/'any').stat().st_size,'exactOriginalSourceBytes':sum(v['bytes'] for v in baseExpected.values()),'estimateIsNotMeasuredPeakForThisBuild':True}
    assert sum(v['bytes'] for v in baseExpected.values())+(BASE/'any').stat().st_size<128*1024**2
    source=OUT/'source';shutil.copytree(BASE/'source',source)
    assert inventory(source)==baseExpected
    patch=json.loads((REPO/'acl_refresh/manifest.json').read_text())
    assert patch['patchSHA256']=='1d4213438a5d9e8024f5506309bd759ef6a72ef9d880ce9269392fc185f43f6c'
    assert patch['patchSHA256']==replay['patchSHA256']
    sdk=source/'.runtime-artifacts/sdk-source'
    result['patchSHA256']=patch['patchSHA256']
    for row in patch['changes']:
        src=OVERLAY/'sdk-source'/row['path'];dst=sdk/row['path']
        assert m.sha(src)==row['afterSHA256']
        assert (m.sha(dst) if dst.exists() else None)==row['beforeSHA256']
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    before=inventory(source)
    delta={k for k in before.keys()|baseExpected.keys() if before.get(k)!=baseExpected.get(k)}
    assert delta=={'.runtime-artifacts/sdk-source/'+v['path'] for v in patch['changes']}
    result['sourceChanges']=sorted(delta)
    result['sourceFiles']=len(before)
    m.atomic(OUT/'source-manifest.json',{'protocol':'qualified-any-source-with-signed-acl-overlay-v1','baseAnyCommit':patch['baseNativeAnyCommit'],'baseSDKCommit':patch['baseNativeSDKCommit'],'patchSHA256':patch['patchSHA256'],'files':before})
    result['sourceManifestSHA256']=m.sha(OUT/'source-manifest.json')
    tmp.mkdir(mode=0o700,exist_ok=False)
    assert tmp.resolve()==tmp and tmp.stat().st_dev==(OUT.stat().st_dev if tmp.parent==OUT else CACHE_TARGET.stat().st_dev)
    env=os.environ.copy();env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE=str(CACHE),GOMODCACHE='/root/go/pkg/mod',GOTMPDIR=str(tmp),TMPDIR=str(tmp),CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
    result['environment']={k:env[k] for k in ['GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB']}
    resources()
    cmd=['/usr/local/bin/go','build','-p','2','-o',str(OUT/'any'),'./cmd/any']
    row={'label':'native-build','command':cmd};result['processes'].append(row);start=time.monotonic()
    with (OUT/'build.log').open('xb') as stream:
        p=subprocess.Popen(cmd,cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        row.update(pid=p.pid,pgid=p.pid);save()
        try:
            while p.poll() is None:
                try:resources()
                except AssertionError:row['resourceGuard']=True;raise
                if time.monotonic()-start>360:row['timeout']=True;raise RuntimeError('bounded native build deadline')
                time.sleep(.5)
        finally:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
            row.update(exitCode=p.returncode,seconds=round(time.monotonic()-start,3))
            try:os.killpg(p.pid,0);row['groupPositivelyAbsent']=False
            except ProcessLookupError:row['groupPositivelyAbsent']=True
    row['logSHA256']=m.sha(OUT/'build.log')
    assert p.returncode==0 and row['groupPositivelyAbsent'],'native build failed; see retained log'
    result['binary']={'path':str(OUT/'any'),'sha256':m.sha(OUT/'any'),'bytes':(OUT/'any').stat().st_size}
    result['status']='PASS_BUILD_ONLY'
except BaseException as e:result.update(status='FAIL_NATIVE_BUILD',error=repr(e))
finally:
    try:
        result['sourceAfter']=m.source_admission()
        assert result['sourceBefore']==result['sourceAfter']
    except BaseException as e:result['status']='FAIL_NATIVE_BUILD';result['errors'].append({'sourceRetention':repr(e)})
    try:
        result['isolatedSourceUnchanged']=before is not None and inventory(OUT/'source')==before
        if result['processes']:assert result['isolatedSourceUnchanged']
    except BaseException as e:result['status']='FAIL_NATIVE_BUILD';result['errors'].append({'isolatedSourceRetention':repr(e)})
    result['allOwnedGroupsPositivelyAbsent']=all(p.get('groupPositivelyAbsent',False) for p in result['processes'])
    if not result['allOwnedGroupsPositivelyAbsent']:result['status']='FAIL_NATIVE_BUILD'
    result['freeBytesAfter']=shutil.disk_usage(OUT).free
    if CACHE_TARGET.exists():result['developmentFreeBytesAfter']=shutil.disk_usage(CACHE_TARGET).free
    save();print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS_BUILD_ONLY' else 1)
