#!/usr/bin/env python3
"""One bounded continuation of the exact failed 897cb cache custody.

No recopy, replay, compiler, Native call, historical process probe or source
metadata repair. Only the observed retained-copy atimes may be restored once,
after complete content/other-metadata verification. Any new drift stops work.
"""
from pathlib import Path
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import stat
import sys
import time
import traceback

sys.dont_write_bytecode=True
ORIGINAL=Path('/mnt/development/projects/evidence/pinkha-wave2-component-cache-controller-20261127/preserve_owned_component_cache.py')
ORIGINAL_SHA='897cb0a96f82d9fe079059088e847c0fe81ab32fe8ea483f4f9d0aced3acd5b9'
OUT=Path('/mnt/development/projects/evidence/pinkha-wave2-component-cache-preserved-20261127')
RECOVERY=OUT/'recovery1'
ROOT=Path('/var/lib/pinkha-wave2-native-block-menu-20261127')
TOKEN='42c71f7f1a754e0da0ac5033fce320bf'
PINS={
 'result.json':'3f34a5660153431980012d1bd6f88c27727eb62e2067ada4e47426ace618210b',
 'restoration-map.json':'95d9488413158c0da62338e277eeca0a0333f740ea8e3375219a214b8fa0c880',
 'protected-files-before.json':'0fff4d81264fbd2d7c9f566dd57fd750f4ea97cec70340b7df19071565bb4180',
 'private-protected-trees-before.json':'ca219c922e1aec624df2a4c17185f8f9f74530d585bbf91b119e7d808c773c49',
 'private-source-manifests.json':'f0a895e98d7693a264486867f613447fb7fae5c5b2183b58eb1090912fff9a98',
 'private-copied-manifests.json':'437ec66425f021dedf51eb4d52ede0a098fd96ba6aea27006af19ab944910c0b',
}
CLAIM_SHA='61a99b41950f9975b630cde3c82ebc68399ebff15a295c2e416ad78551accccc'
EXPECTED_ATIME_COUNTS={'build':1012,'cache':33,'clang-module-cache':3}
PASS='PASS_EXACT_THREE_CACHE_CUSTODY_RECOVERED_ORIGINAL_FAILURE_RETAINED_NO_COMPILER_ACCEPTANCE'


def require(ok,message):
    if not ok:raise AssertionError(message)


def metadata_only(row):
    return {k:v for k,v in row.items() if k not in ('sha256','target','children')}


def destination_inventory(c,root,scope,guard):
    """No timestamp setter: retain any atime incurred by reading the one link."""
    require(root.resolve()==root and not root.is_symlink(),'canonical retained root')
    rows={};effects=[];device=root.stat().st_dev;stack=[root]
    while stack:
        path=stack.pop();before=c.metadata(path);relative=str(path.relative_to(root))
        require(before['device']==device,'retained mount changed: '+relative)
        if before['kind']=='file':row=dict(before,sha256=c.sha_file(path,guard))
        elif before['kind']=='directory':
            children=c.directory_names(path);row=dict(before,children=children)
            stack.extend(path/name for name in reversed(children))
        else:
            require(scope=='build' and relative=='debug','only observed copied build/debug link')
            target=os.readlink(path);after=c.metadata(path)
            require(target==c.BUILD_LINK and before['bytes']==len(os.fsencode(target)),'copied debug target changed')
            require({k:v for k,v in after.items() if k!='atime_ns'}=={k:v for k,v in before.items() if k!='atime_ns'},'metadata changed during link read')
            if after['atime_ns']!=before['atime_ns']:
                effects.append({'relative':relative,'atimeBeforeReadNS':before['atime_ns'],
                                'atimeAfterReadNS':after['atime_ns']})
            before=after;row=dict(before,target=target,sha256=hashlib.sha256(os.fsencode(target)).hexdigest())
        require(c.metadata(path)==before,'retained node changed during capture: '+relative)
        rows[relative]=row
        require(len(rows)<=10000,'bounded retained inventory')
        if len(rows)%64==0:guard()
    return rows,effects


def original_inventory(c,name,sources,guard):
    path=ROOT/(name+'.verified-original-'+TOKEN) if name=='build' or (ROOT/name).is_symlink() else ROOT/name
    require(path.resolve()==path and not path.is_symlink(),'original duplicate must remain physical: '+name)
    current=c.inventory(path,guard,scope=name)
    expected=sources[name]
    require(c.portable(current)==c.portable(expected),'original portable metadata/content drift: '+name)
    require(set(current)==set(expected),'original path set drift: '+name)
    for relative,row in current.items():
        for field in c.IDENTITY_FIELDS:
            if relative=='.' and field=='ctime_ns' and path!=ROOT/name:continue
            require(row[field]==expected[relative][field],f'original identity drift: {name}/{relative}:{field}')
    return path,current


def strict_destination(c,name,sources,copied,guard):
    path=OUT/'retained'/name
    current=c.inventory(path,guard,scope=name,copied=True)
    require(c.portable(current)==c.portable(sources[name]),'retained portable metadata/content drift: '+name)
    for relative,row in current.items():
        for field in ('device','inode','allocated','nlink'):
            require(row[field]==copied[name][relative][field],f'retained identity drift: {name}/{relative}:{field}')
    return current


def main():
    require(not sys.flags.optimize and os.geteuid()==0 and os.uname().nodename=='torah-social','exact host/root/assertions required')
    require(ROOT.resolve()==ROOT and OUT.resolve()==OUT,'fixed canonical recovery roots')
    # Read exact controller without changing its access time; import executes no main.
    fd=os.open(ORIGINAL,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        raw=b''
        while part:=os.read(fd,65536):raw+=part;require(len(raw)<=65536,'bounded original controller')
    finally:os.close(fd)
    require(hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA,'original reviewed controller changed')
    spec=importlib.util.spec_from_file_location('exact_897cb_custody',ORIGINAL)
    c=importlib.util.module_from_spec(spec)
    # Compile the exact noatime bytes; do not trigger importer source reads or pycache.
    c.__file__=str(ORIGINAL);exec(compile(raw,str(ORIGINAL),'exec'),c.__dict__)
    lock=os.open(c.LOCK,os.O_RDWR|os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(lock).st_mode) and os.fstat(lock).st_nlink==1,'fixed custody lock identity')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return recover_locked(c)
    finally:os.close(lock)


def recover_locked(c):
    require(not os.path.lexists(RECOVERY),'never replay the bounded recovery')
    original={}
    for relative,want in PINS.items():
        require(c.sha_file(OUT/relative)==want,'retained original pin changed: '+relative)
        original[relative]=c.read_json_noatime(OUT/relative)
    require(c.sha_file(c.CLAIM)==CLAIM_SHA,'original active claim changed')
    claim=c.read_json_noatime(c.CLAIM)
    require(claim['token']==TOKEN and claim['controllerSHA256']==ORIGINAL_SHA and claim['output']==str(OUT),'exact failed custody claim')
    failed=original['result.json'];sources=original['private-source-manifests.json'];copied=original['private-copied-manifests.json']
    require(failed['status']=='FAIL_DIRECTORY_CUSTODY_FINAL_INTEGRITY' and failed['retiredDuplicates']==[],'only exact zero-retirement failure')
    require(failed['token']==TOKEN and failed['controllerSHA256']==ORIGINAL_SHA,'failed custody source/token')
    require(failed['sourceManifestsSHA256']==PINS['private-source-manifests.json'] and failed['copiedManifestsSHA256']==PINS['private-copied-manifests.json'],'failed manifests linkage')
    require(failed['restorationMapSHA256']==PINS['restoration-map.json'],'failed restore map linkage')
    require((ROOT/'build').is_symlink() and os.readlink(ROOT/'build')==str(OUT/'retained/build'),'observed existing build alias')
    require(all(not (ROOT/name).is_symlink() for name in ('cache','clang-module-cache')),'only two remaining physical originals')
    for name in ('cache','clang-module-cache'):
        require(not os.path.lexists(ROOT/(name+'.verified-original-'+TOKEN)),'unobserved original duplicate')
    RECOVERY.mkdir(mode=0o750);os.chown(RECOVERY,0,1002);os.chmod(RECOVERY,0o750)
    active=RECOVERY/'active-recovery.json'
    c.immutable_json(RECOVERY/'original-active-claim.json',claim)
    require(c.sha_file(RECOVERY/'original-active-claim.json')==CLAIM_SHA,'original claim copy must remain exact')
    started=time.monotonic()
    result={'protocol':'pinkha-exact-failed-component-cache-custody-continuation-v1','status':'RUNNING','phase':'full qualification',
      'controllerSHA256':c.sha_file(Path(__file__)),'originalControllerSHA256':ORIGINAL_SHA,
      'originalFailedReceiptSHA256':PINS['result.json'],'originalInputPins':PINS,'originalClaimSHA256':CLAIM_SHA,
      'token':TOKEN,'errors':[],'restoredDestinationAtimes':[],'retiredDuplicates':[],
      'compilerInvocations':0,'nativeInvocations':0,'testInvocations':0,'historicalProcessGroupReprobed':False,
      'copiedBytes':0,'originalSourceMetadataRepaired':False,'compilerWarmness':'UNPROVEN',
      'sourceLocationQualification':'NOT_RUN_REQUIRED','originalFailureOverwritten':False}
    def save():
        result['seconds']=round(time.monotonic()-started,3)
        tmp=RECOVERY/'result.writing'
        c.immutable_json(tmp,result);os.replace(tmp,RECOVERY/'result.json');c.durable_directory(RECOVERY)
    def guard():
        require(time.monotonic()-started<600,'single bounded recovery deadline')
        require(shutil.disk_usage('/').free>=c.ROOT_EMERGENCY,'unchanged recovery root floor')
        require(shutil.disk_usage(OUT).free>=c.DEVELOPMENT_EMERGENCY+c.FURTHER_COMPONENT_BUDGET,'unchanged development reserve')
        require(not (RECOVERY/'abort').exists(),'owned recovery abort')
    def interrupted(*_):raise RuntimeError('owned recovery interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def protected():
        require(c.protected_files(guard)==original['protected-files-before.json'],'protected original file drift')
        require({str(p):c.inventory(p,guard) for p in c.PROTECTED_TREES}==original['private-protected-trees-before.json'],'protected original tree drift')
    def no_users(stage,originals,destinations):
        paths=[ROOT/name for name in c.SCOPES]+[p for p,_ in originals.values()]+[OUT/'retained'/name for name in c.SCOPES]
        found=c.live_users(paths,[rows for _,rows in originals.values()]+list(destinations.values()))
        result.setdefault('liveUseChecks',[]).append({'stage':stage,'uses':found})
        require(not found,'live original/retained cache user; stop without retry')
    try:
        guard();protected()
        olds={name:original_inventory(c,name,sources,guard) for name in c.SCOPES}
        observed={};effects={};repairs={};external_diffs={}
        for name in c.SCOPES:
            observed[name],effects[name]=destination_inventory(c,OUT/'retained'/name,name,guard)
            require(set(observed[name])==set(copied[name]),'retained complete topology changed: '+name)
            before_link={r['relative']:r['atimeBeforeReadNS'] for r in effects[name]}
            external_diffs[name]=[];repairs[name]=[]
            for relative,row in observed[name].items():
                expected=copied[name][relative]
                ignored={'atime_ns'}|({'ctime_ns'} if name=='build' and relative=='debug' else set())
                require({k:v for k,v in row.items() if k not in ignored}=={k:v for k,v in expected.items() if k not in ignored},'non-atime retained drift: '+name+'/'+relative)
                before_atime=before_link.get(relative,row['atime_ns'])
                if before_atime!=expected['atime_ns']:
                    external_diffs[name].append({'relative':relative,'originalAtimeNS':expected['atime_ns'],'observedAtimeNS':before_atime})
                if row['atime_ns']!=expected['atime_ns']:repairs[name].append(relative)
            require(len(external_diffs[name])==EXPECTED_ATIME_COUNTS[name],'new or different retained atime scope: '+name)
        c.immutable_json(RECOVERY/'private-complete-before.json',{'originals':{n:r for n,(_,r) in olds.items()},'destinations':observed,'externalAtimeDifferences':external_diffs,'linkReadAtimeEffects':effects})
        result['completeBeforeSHA256']=c.sha_file(RECOVERY/'private-complete-before.json')
        result['observedExternalAtimeCounts']={n:len(v) for n,v in external_diffs.items()}
        no_users('qualified-before-single-restoration',olds,observed)
        c.immutable_json(active,{'controllerSHA256':result['controllerSHA256'],'originalClaimSHA256':CLAIM_SHA,
            'originalFailedReceiptSHA256':PINS['result.json'],'completeBeforeSHA256':result['completeBeforeSHA256'],'token':TOKEN})
        result['phase']='restore only observed destination atimes once';save()
        for name in c.SCOPES:
            for relative in repairs[name]:
                guard();path=OUT/'retained'/name/relative;before=metadata_only(observed[name][relative]);expected=copied[name][relative]
                require(c.metadata(path)==before,'destination drift immediately before one atime restore: '+name+'/'+relative)
                os.utime(path,ns=(expected['atime_ns'],before['mtime_ns']),follow_symlinks=False)
                after=c.metadata(path)
                require({k:v for k,v in after.items() if k not in ('atime_ns','ctime_ns')}=={k:v for k,v in before.items() if k not in ('atime_ns','ctime_ns')} and after['atime_ns']==expected['atime_ns'],'atime restoration changed another field')
                result['restoredDestinationAtimes'].append({'scope':name,'relative':relative,'beforeNS':before['atime_ns'],'afterNS':after['atime_ns'],'ctimeAfterNS':after['ctime_ns']})
        destinations={name:strict_destination(c,name,sources,copied,guard) for name in c.SCOPES}
        olds={name:original_inventory(c,name,sources,guard) for name in c.SCOPES}
        no_users('after-single-restoration',olds,destinations);protected()
        c.immutable_json(RECOVERY/'private-restored-manifests.json',destinations)
        result['restoredManifestsSHA256']=c.sha_file(RECOVERY/'private-restored-manifests.json')
        result['phase']='remaining two original stable-path exchanges';save()
        for name in ('cache','clang-module-cache'):
            guard();source=ROOT/name;destination=OUT/'retained'/name;duplicate=ROOT/(name+'.verified-original-'+TOKEN)
            original_inventory(c,name,sources,guard);strict_destination(c,name,sources,copied,guard)
            no_users('before-exchange-'+name,olds,destinations)
            require(not os.path.lexists(duplicate),'fresh exact duplicate slot')
            os.symlink(str(destination),duplicate);c.durable_directory(ROOT)
            c.exchange_paths(source,duplicate);c.durable_directory(ROOT)
            require(source.is_symlink() and os.readlink(source)==str(destination) and source.resolve()==destination,'new stable alias mismatch')
            olds[name]=original_inventory(c,name,sources,guard)
            destinations[name]=strict_destination(c,name,sources,copied,guard)
            no_users('after-exchange-'+name,olds,destinations)
            result.setdefault('completedExchanges',[]).append(name);save()
        result['phase']='retire only three freshly verified original duplicates';save()
        for name in c.SCOPES:
            guard();duplicate,rows=original_inventory(c,name,sources,guard)
            destinations[name]=strict_destination(c,name,sources,copied,guard)
            require((ROOT/name).is_symlink() and os.readlink(ROOT/name)==str(OUT/'retained'/name),'exact alias before retirement')
            no_users('immediately-before-retirement-'+name,olds,destinations)
            c.immutable_json(RECOVERY/('verified-before-retirement-'+name+'.json'),{'originalFailedReceiptSHA256':PINS['result.json'],
                'completeBeforeSHA256':result['completeBeforeSHA256'],'restoredManifestsSHA256':result['restoredManifestsSHA256'],
                'retiring':str(duplicate),'soleRetained':str(OUT/'retained'/name),'fullContentPortableMetadataAndIdentityVerified':True,'noLiveUsers':True})
            for relative,row in sorted(rows.items(),key=lambda item:len(Path(item[0]).parts),reverse=True):
                guard();path=duplicate/relative
                if row['kind'] in ('file','symlink'):
                    if row['kind']=='file':require(c.sha_file(path)==row['sha256'],'duplicate bytes changed before unlink')
                    else:require(name=='build' and relative=='debug' and os.readlink(path)==c.BUILD_LINK,'duplicate link changed before unlink')
                    require(c.metadata(path)==metadata_only(row),'duplicate metadata changed before unlink')
                    path.unlink()
                else:
                    require(not c.directory_names(path),'duplicate directory not empty');path.rmdir()
            c.durable_directory(ROOT);require(not os.path.lexists(duplicate),'original duplicate remains')
            result['retiredDuplicates'].append({'name':name,'allocatedBytes':c.SCOPES[name]['allocated']});save()
            destinations[name]=strict_destination(c,name,sources,copied,guard)
            olds.pop(name)
        result['phase']='final unchanged originals and strict retained manifests';protected()
        for relative,want in PINS.items():require(c.sha_file(OUT/relative)==want,'original failed custody evidence changed: '+relative)
        require(c.sha_file(c.CLAIM)==CLAIM_SHA,'original claim changed before finalization')
        require(c.sha_file(ORIGINAL)==ORIGINAL_SHA and c.sha_file(Path(__file__))==result['controllerSHA256'],'controller bytes changed')
        final={name:strict_destination(c,name,sources,copied,guard) for name in c.SCOPES}
        c.immutable_json(RECOVERY/'private-final-manifests.json',final)
        result['finalManifestsSHA256']=c.sha_file(RECOVERY/'private-final-manifests.json')
        result['copiedLinkReadAtimeRestorations']=c.COPIED_LINK_READ_RESTORATIONS
        result['originalFailureRetained']=True;result['protectedOriginalInputsUnchanged']=True
        result['recoveredRootAllocatedBytes']=c.TOTAL_ALLOCATION
        result['phase']='final access and claim release';save()
        qualification=RECOVERY/'source-qualification1';qualification.mkdir(mode=0o750)
        os.chown(qualification,1001,1002);os.chmod(qualification,0o750)
        result['status']=PASS;result['phase']='completed';save()
        os.chown(RECOVERY/'result.json',0,1002);os.chmod(RECOVERY/'result.json',0o640)
        for name in ('private-final-manifests.json','original-active-claim.json'):
            os.chown(RECOVERY/name,0,1002);os.chmod(RECOVERY/name,0o640)
        c.durable_directory(RECOVERY)
        # Both completed recovery and absent durable claims are mandatory.
        active.unlink();c.durable_directory(RECOVERY)
        c.CLAIM.unlink();c.durable_directory(c.CLAIM.parent)
    except BaseException as error:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        result['status']='FAIL_EXACT_CUSTODY_CONTINUATION_NO_RETRY'
        result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':result['phase'],'traceback':traceback.format_exc()})
        try:
            if not os.path.lexists(c.CLAIM):c.immutable_json(c.CLAIM,claim)
            if not os.path.lexists(active):c.immutable_json(active,{'controllerSHA256':result['controllerSHA256'],'token':TOKEN,'unresolvedFailure':True,'originalFailedReceiptSHA256':PINS['result.json']})
            save()
        except BaseException as cleanup_error:
            result['errors'].append({'type':type(cleanup_error).__name__,'message':str(cleanup_error),'phase':'retaining failure/claim','traceback':traceback.format_exc()})
            print(json.dumps({'status':'FAIL_CUSTODY_RECOVERY_EVIDENCE_INCOMPLETE','errors':result['errors']}));return 1
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
    print(json.dumps({'status':result['status'],'result':str(RECOVERY/'result.json'),'sha256':c.sha_file(RECOVERY/'result.json'),
        'seconds':round(time.monotonic()-started,3),'retiredCount':len(result['retiredDuplicates']),'errors':result['errors'],
        'rootFree':shutil.disk_usage('/').free,'developmentFree':shutil.disk_usage(OUT).free}))
    return 0 if result['status']==PASS else 1

if __name__=='__main__':raise SystemExit(main())
