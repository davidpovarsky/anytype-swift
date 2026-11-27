#!/usr/bin/env python3
"""Read exact producer closures and derive manifests without applying source."""
from pathlib import Path
import hashlib,json,os,shutil,signal,stat,subprocess,sys,time

BASE=Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current')
CURRENT=Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1')
NREPO=Path('/mnt/development/projects/worktrees/anytype-network-final-20261127')
EREPO=Path('/mnt/development/projects/worktrees/anytype-cutover-final-20261127')
RREPO=Path('/mnt/development/projects/worktrees/anytype-engine-contracts-20261127')
NP=NREPO/'Tools/AnyEngineValidation/native_file_peer_comparison'
EP=EREPO/'Tools/TorahNativeOperations/legacy_cutover'
ER=Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127')
ES=ER/'retained/current8ac/attempt2/source'
RAW_E=Path('/mnt/development/projects/evidence/native-d-final-20261125/native-permission-20261126/source-manifest.json')
OUT=Path('/mnt/development/projects/evidence/pinkha-w1-two-product-source-ledger-20261127-attempt2')
PRIOR=Path('/mnt/development/projects/evidence/pinkha-w1-two-product-source-ledger-20261127/result.json')
PRIOR_SHA='8ac895c3139b7b28ccd64c2e936f0bbb95e5d8f91e4eb300b714ad1cc1dd766f'
PINS={BASE/'source-manifest.json':'12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c',
 CURRENT/'source-manifest.json':'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a',
 BASE/'BUILD.json':'6d0f00da205846575bfd49e3fba8121aa1570a940ea3e13cc571aa4b4734e2f0',
 CURRENT/'result.json':'c74e754d4f26b9ca9b3c9e681093e247fe2c54dd5360fe0677dca25c0282cda6',
 RAW_E:'8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b',
 EP/'native-core-current8ac-qualified.json':'0ea2bbfff9fd1faef02337ae247bb6706c5517c971d1346b762467b854782a20',
 EP/'rpc-source-candidate.json':'b98c93ff11e492e173ca2a0b93548ed4cdfb275bb4b345bd82468e55c6e481ac',
 ES.parent/'source-before.json':'ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28',
 ER/'attempt1/result.json':'331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772',
 NP/'acl_refresh/manifest.json':'1a8b82992598a25bce7e439e272ba64e63f659c17a36d4005c37b5b74c9e806c',
 NP/'lan_progress/manifest.json':'ac76106c77fbeb06e4b519ac41c0da1bfc30b30dc904ffe172af399e4135b55f'}

def read(p,limit=4*1024**2):
    before=p.lstat();assert stat.S_ISREG(before.st_mode) and before.st_size<=limit
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd,'rb') as f:raw=f.read(limit+1)
    assert len(raw)==before.st_size and p.lstat()==before
    return raw

def sha(p):
    before=p.lstat();h=hashlib.sha256()
    with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as f:
        for part in iter(lambda:f.read(1024**2),b''):h.update(part)
    assert p.lstat()==before
    return h.hexdigest()

def inv(root):
    assert root.resolve()==root and not root.is_symlink()
    result={};stack=[root]
    while stack:
        path=stack.pop();s=path.lstat()
        assert not stat.S_ISLNK(s.st_mode)
        if stat.S_ISDIR(s.st_mode):
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
            try:
                with os.scandir(fd) as entries:names=sorted(x.name for x in entries)
            finally:os.close(fd)
            stack.extend(path/name for name in reversed(names))
        else:
            assert stat.S_ISREG(s.st_mode)
            result[str(path.relative_to(root))]={'bytes':s.st_size,'sha256':sha(path)}
        assert path.lstat()==s
        assert len(result)<=6000
    return result

def normalized(rows):return {p:{'bytes':v['bytes'],'sha256':v['sha256']} for p,v in rows.items()}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def json_bytes(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def put(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return {'path':str(path),'bytes':len(raw),'sha256':digest(raw)}
def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+str(repo),'-C',str(repo),*args],text=True,timeout=20,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).strip()

def main():
    if sys.flags.optimize:raise RuntimeError('source acceptance assertions must be enabled')
    assert os.uname().nodename=='torah-social' and os.geteuid()==0
    assert OUT.parent.resolve()==OUT.parent
    os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
    started=time.monotonic();result={'protocol':'pinkha-two-product-source-tuple-audit-v2','status':'RUNNING','phase':'pinned source admission','nativeProductRuns':0,'compilerRuns':0,'testReruns':0,'sourceFilesChanged':0,'sourceOverlayApplications':0,'controllerSHA256':sha(Path(__file__)),'errors':[]}
    captured={};p=None;owned=None
    def interrupted(*_):raise RuntimeError('owned source-only audit interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    try:
        assert shutil.disk_usage(OUT).free>=512*1024**2+16*1024**2
        assert sha(PRIOR)==PRIOR_SHA
        prior=json.loads(read(PRIOR));assert prior['status']=='FAIL_SOURCE_TUPLE_AUDIT'
        result['retainedPriorAuditFailureSHA256']=PRIOR_SHA
        for path,want in PINS.items():
            raw=read(path);assert digest(raw)==want,str(path);captured[path]=raw
        data={p:json.loads(raw) for p,raw in captured.items()}
        before=normalized(data[BASE/'source-manifest.json']['files']);current=normalized(data[CURRENT/'source-manifest.json']['files'])
        assert len(before)==1594 and len(current)==1599
        result['phase']='actual Any source inventories'
        assert inv(BASE/'source')==before and inv(CURRENT/'source')==current
        e_original=normalized(data[RAW_E]['files']);e_materialized=data[ES.parent/'source-before.json']
        assert len(e_original)==4868 and len(e_materialized)==4893
        e_any={k.removeprefix('any/'):v for k,v in e_materialized.items() if k.startswith('any/')}
        assert e_any==before and inv(ES/'any')==before
        assert {k.removeprefix('any/'):v for k,v in e_original.items() if k.startswith('any/')}==before
        custody=data[ER/'attempt1/result.json'];assert custody['status'].startswith('PASS') and custody['allCopiesVerified'] and not custody['errors']
        core=data[EP/'native-core-current8ac-qualified.json'];rpc=data[EP/'rpc-source-candidate.json']
        acl=data[NP/'acl_refresh/manifest.json'];lan=data[NP/'lan_progress/manifest.json']
        assert core['baseManifestSHA256']==PINS[RAW_E] and rpc['coreManifestSHA256']==PINS[EP/'native-core-current8ac-qualified.json']
        assert len(core['sourceFiles'])==40 and len(rpc['files'])==11
        result['phase']='seven network paths and forty plus eleven Heart overlays'
        network_changes=acl['changes']+lan['changes'];assert len(network_changes)==7
        actual_changes={k for k in before.keys()|current.keys() if before.get(k)!=current.get(k)}
        assert actual_changes=={'.runtime-artifacts/sdk-source/'+r['path'] for r in network_changes}
        mapping=[]
        for r in network_changes:
            rel='.runtime-artifacts/sdk-source/'+r['path'];old=before.get(rel)
            assert (old['sha256'] if old else None)==r['beforeSHA256'] and current[rel]['sha256']==r['afterSHA256']
            mapping.append({'sdkRelativePath':r['path'],'anyRelativePath':rel,'workspaceRelativePath':'any/'+rel,'before':old,'after':current[rel]})
        assert sha(NP/'acl_refresh/sdk-acl-refresh.patch')==acl['patchSHA256']
        assert sha(NP/'lan_progress/sdk-lan-progress.patch')==lan['patchSHA256']
        assert sha(EREPO/'docs/architecture/20261127-heart-cutover-native-core/current8ac-native-core.patch')==core['patch']['sha256']
        final_heart=dict(e_original)
        for rel,row in core['sourceFiles'].items():
            expected=core['originalReplacements'].get(rel)
            assert final_heart.get('heart/'+rel)==expected
            file=EP/'overlay'/rel;assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
            final_heart['heart/'+rel]=row
        work_sum=ES/'go.work.sum';assert sha(work_sum)==core['goWorkSumSHA256']
        final_heart['go.work.sum']={'bytes':work_sum.stat().st_size,'sha256':sha(work_sum)}
        for rel,row in rpc['files'].items():
            assert final_heart.get('heart/'+rel)==row['before']
            file=EP/'overlay'/rel;expected=row['after']
            assert file.stat().st_size==expected['bytes'] and sha(file)==expected['sha256']
            final_heart['heart/'+rel]=expected
        assert len(final_heart)==4900,'4868+24 core new files+8 RPC new files; go.work.sum is replaced'
        full_union=dict(final_heart)
        for r in mapping:
            assert full_union.get(r['workspaceRelativePath'])==r['before']
            full_union[r['workspaceRelativePath']]=r['after']
        assert len(full_union)==4905,'five new SDK files plus two changed SDK files'
        assert not {r['workspaceRelativePath'] for r in mapping}&{'heart/'+p for p in core['sourceFiles']|rpc['files']}
        # The qualified retained Linux materialization also contains one native
        # linker archive. It is not portable source and is not an Apple library.
        library_rel='heart/deps/libs/linux-arm64-musl/libtantivy_go.a'
        library=e_materialized[library_rel]
        assert library_rel not in e_original and library_rel not in final_heart
        assert library=={'bytes':51291066,'sha256':core['librarySHA256']}
        assert sha(ES/library_rel)==library['sha256'] and (ES/library_rel).stat().st_size==library['bytes']
        linux_heart=dict(final_heart);linux_heart[library_rel]=library
        linux_union=dict(full_union);linux_union[library_rel]=library
        assert len(linux_heart)==4901 and len(linux_union)==4906
        result['phase']='native build metadata read and immutable expected manifests'
        immutable_products={'baseline':data[BASE/'BUILD.json']['binary'],'network':data[CURRENT/'result.json']['binary']}
        for row in immutable_products.values():assert sha(Path(row['path']))==row['sha256']
        command=['/usr/local/bin/go','version','-m',str(CURRENT/'any')]
        env=dict(os.environ,GOTOOLCHAIN='local',GOWORK='off',GOPROXY='off',GOSUMDB='off')
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
        owned=p.pid;stdout,stderr=p.communicate(timeout=30)
        assert p.returncode==0 and not stderr and len(stdout)<128*1024
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        assert absent;owned=None
        text=stdout.decode();assert 'github.com/anyproto/any/cmd/any' in text and 'github.com/anyproto/anytype-heart' not in text
        assert '\tdep\tgithub.com/anyproto/any-sync\tv0.13.8\t' in text and 'go1.27.4' in text
        module_info=put(OUT/'current-any-go-build-info.txt',stdout)
        artifacts={
            'anyBaselineManifest':put(OUT/'any-baseline1594-source-manifest.json',captured[BASE/'source-manifest.json']),
            'anyNetworkManifest':put(OUT/'any-network1599-source-manifest.json',captured[CURRENT/'source-manifest.json']),
            'rawCombinedManifest':put(OUT/'original8ac-source-manifest.json',captured[RAW_E]),
            'heartFinalExpectedManifest':put(OUT/'heart-core40-rpc11-expected-manifest.json',json_bytes(final_heart)),
            'prospectiveSharedWorkspaceManifest':put(OUT/'two-products-shared-workspace-expected-manifest.json',json_bytes(full_union)),
            'heartLinuxLinkExpectedManifest':put(OUT/'heart-linux-link-expected-manifest.json',json_bytes(linux_heart)),
            'sharedLinuxLinkExpectedManifest':put(OUT/'two-products-linux-link-expected-manifest.json',json_bytes(linux_union)),
            'readOnlyNativeBuildInfo':module_info}
        root_commits={short:git(RREPO,'rev-parse',short) for short in ('2cdc1c99','2619d5b','526d4bb','60d32628')}
        assert root_commits['60d32628']=='60d32628f44f334063b756bad29b8861201287b7'
        result.update(status='PASS_SOURCE_INVENTORY_AND_UNAPPLIED_COMPOSITION_ONLY',artifacts=artifacts,
            any={'baseAnyCommit':acl['baseNativeAnyCommit'],'baseSDKCommit':acl['baseNativeSDKCommit'],'sdkBaselineFiles':sum(k.startswith('.runtime-artifacts/sdk-source/') for k in before),'sdkCurrentFiles':sum(k.startswith('.runtime-artifacts/sdk-source/') for k in current),'standaloneSyncModule':'github.com/anyproto/any-sync@v0.13.8','standaloneGoWork':'off','goToolchain':'go1.27.4','binary':immutable_products['network'],'baseBinary':immutable_products['baseline'],'baseSourceFiles':1594,'currentSourceFiles':1599,'onlySourceChanges':mapping,'aclPatchSHA256':acl['patchSHA256'],'lanPatchSHA256':lan['patchSHA256'],'containsHeartProduct':False,'bodyBlocksSourceUnchanged':before['internal/editor/blocks.go']==current['internal/editor/blocks.go'],'bodyBlocksSource':current['internal/editor/blocks.go']},
            heart={'sourceCommit':'834a6bced7b922a18f291add1bcc6e82d5bba61f','baseSourcePins':core['baseSourcePins'],'baseFiles':4868,'baseManifestSHA256':PINS[RAW_E],'baseArchive':str(RAW_E.with_name('native-source-8ac407e75a4b.tar.gz')),'baseArchiveSHA256':core['baseArchiveSHA256'],'coreOverlayFiles':40,'coreManifestSHA256':PINS[EP/'native-core-current8ac-qualified.json'],'corePatchSHA256':core['patch']['sha256'],'rpcOverlayFiles':11,'rpcManifestSHA256':PINS[EP/'rpc-source-candidate.json'],'originalMaterializedSource':str(ES),'materializedFiles':4893,'materializedManifestSHA256':PINS[ES.parent/'source-before.json'],'materializedInputIsFinal834Union':False,'physicalSourceCustodySHA256':PINS[ER/'attempt1/result.json'],'coreThenRPCExpectedSourceFiles':4900,'linuxLinkClosureFiles':4901,'linuxLinkerArtifact':dict(library,path=library_rel),'goWork':read(ES/'go.work').decode(),'qualifiedGoWorkSumSHA256':core['goWorkSumSHA256'],'fullSpaceDraftIncluded':False},
            composition={'sourceFilesApplied':0,'expectedSharedWorkspaceSourceFiles':4905,'expectedSharedLinuxLinkClosureFiles':4906,'heartAndSDKPathsDisjoint':True,'eRawAnySubtreeEqualsStandalone1594':True,'eRetainedAnySubtreeEqualsStandalone1594':True,'sharedWorkspaceUsesLocalSyncCommit':core['baseSourcePins']['sync'],'standalone0796UsesVersionedSync':'v0.13.8','syncClosureEquivalenceClaimed':False,'newCombinedBinaryProduced':False,'newCombinedRuntimeAcceptance':False},
            rootSwift={'commits':root_commits,'nativeBodySourceDelta':False,'qualifiedNativeReference':'1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636','scope':'typed adapters, source validation, tests and controllers; separate from native SDK/Heart production overlays'},
            apple={'rawManifestPurpose':data[RAW_E]['purpose'],'packages':data[RAW_E]['packages'],'tags':data[RAW_E]['tags'],'deploymentTarget':data[RAW_E]['deploymentTarget'],'gomobileVersion':data[RAW_E]['gomobileVersion'],'current0796AppleBindingQualified':False,'newCore40RPC11AppleBindingQualified':False,'newCombinedProducerQualified':False,'linuxCLIIsAppleBoundRuntime':False},
            metadataReadCommand={'command':command,'exitCode':0,'ownedGroupAbsent':True,'notACompile':True},
            excludedPending=['FilesV2 held-reader draft','independent-device diagnostic helper is not product code','unpublished FullSpace35/enqueue drafts','unqualified generated Swift/client17 acceptance'])
        assert inv(BASE/'source')==before and inv(CURRENT/'source')==current and inv(ES/'any')==before
        for path,raw in captured.items():assert read(path)==raw
        result['allPinnedInputsAndInventoriedSourceBytesUnchanged']=True;result['phase']='completed'
        assert sha(Path(__file__))==result['controllerSHA256']
    except BaseException as error:
        result['status']='FAIL_SOURCE_TUPLE_AUDIT';result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':result['phase']})
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        if owned is not None:
            try:
                os.killpg(owned,signal.SIGTERM)
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(owned,signal.SIGKILL);p.wait(timeout=3)
                try:os.killpg(owned,0);raise RuntimeError('metadata-read group remains')
                except ProcessLookupError:pass
            except ProcessLookupError:pass
            except BaseException as error:result['errors'].append({'cleanup':str(error)});result['status']='FAIL_SOURCE_TUPLE_CLEANUP'
        result['seconds']=round(time.monotonic()-started,3)
        put(OUT/'result.json',json_bytes(result))
        fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOATIME);os.fsync(fd);os.close(fd)
        print(json.dumps({'status':result['status'],'receipt':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'seconds':result['seconds'],'errors':result['errors']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
