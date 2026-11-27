#!/usr/bin/env python3
"""Preserve four closed diagnostic directories behind stable original paths.

Recovery only: no native process, compiler, account open, ACL mutation or test.
The old private diagnostic DB/wallet and failed receipts remain private, intact
at the destination. All source duplicates remain until independent destination
verification and atomic directory/symlink exchange. An interrupted transition
keeps the verified destination and any remaining original duplicate.
"""
from pathlib import Path
import base64
import ctypes
import hashlib
import json
import os
import shutil
import signal
import stat
import sys
import time
import uuid

ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
OUT = Path('/mnt/development/projects/evidence/pinkha-w1-network-closed-diagnostics-relocated-20261127')
SCOPES = {
    'acl-verified-comparison8': {'allocated': 53841920, 'entries': 21, 'receipt': 'bcf18655d1b6cbca2c0916e097d5b6dc9a6e45a1d65ca97af2ec68d73dbfa8ad'},
    'acl-storage-diagnostic7': {'allocated': 30093312, 'entries': 11, 'receipt': 'de4d90f4a46e1724cdca4bed6b05facf0dfc8a13a51e951a357cc5563e4d1396'},
    'lan-progress-unit1': {'allocated': 8466432, 'entries': 774, 'receipt': '77e1d1ebc5f8c19c0427fdad78f88aa912659f56882f05323522ce17ce58b984'},
    'lan-progress-replay1': {'allocated': 8372224, 'entries': 773, 'receipt': '271248e4a09229cc52e7145625041be9aa052094a459f25d19753694ccd0527e'},
}
NATIVE_PINS = {
    '/var/lib/pinkha-root-t2-linux-20261126/build1/current/any': '1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636',
    str(ROOT/'lan-progress-native1/any'): '0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07',
    '/mnt/development/projects/caches/pinkha-e-cutover-rpc-core-attempt5-20261127/cutover-core.test': 'bbd8d9f28d7a948684d9771c5b0effe25abb00570ac0383b0324a56cb6ce1f75',
}
CONTROL_PINS = {
    str(ROOT/'retained-node-grant-comparison1/diagnostic-source-manifest.json'): '92e8799325e308a2c94db4a17482b3aecf726e145a2f8de82d297bc342215d87',
    str(ROOT/'retained-node-grant-comparison1/result.json'): 'b4ea294a8090cd867bae1246a635d0afba8a48e12ee073a9362f2598591321c6',
    str(ROOT/'original-native-authority1/result.json'): '70f6dd9f6ae6eb24e6d6eaced2387bdea8511a396981d66888dd7338a02a59bf',
    str(ROOT/'original-native-authority-continuation1/result.json'): '24d00c2cad87b9943050f453288c132406cf56267b145c83cbabeb2be7bc5c94',
    str(ROOT/'original-native-authority-continuation1/private-current-accounts.json'): '2d74afd5fc9ca535a357ae102d44df2519e391a4a4c7930ca965f228cb08c14a',
    str(ROOT/'lan-progress-native1/result.json'): 'c74e754d4f26b9ca9b3c9e681093e247fe2c54dd5360fe0677dca25c0282cda6',
    str(ROOT/'lan-progress-native1/source-manifest.json'): 'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a',
}
PROTECTED_TREES = [ROOT/'attempt1/alice', ROOT/'attempt1/bob', ROOT/'retained-node-grant-comparison1/sdk-source']
MIB = 1024**2
ROOT_EMERGENCY = 256*MIB
DEVELOPMENT_EMERGENCY = 512*MIB
TOTAL_ALLOCATION = 100773888
IDENTITY_FIELDS = ('device', 'inode', 'ctime_ns', 'allocated', 'nlink')


def directory_names(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        with os.scandir(fd) as entries: return sorted(e.name for e in entries)
    finally: os.close(fd)


def sha_file(path, guard=lambda:None):
    value = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        while part := os.read(fd, MIB):
            guard();value.update(part)
    finally: os.close(fd)
    return value.hexdigest()


def metadata(path):
    s = os.lstat(path)
    kind = 'directory' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'unsupported'
    assert kind != 'unsupported', 'symlink or special entry is outside the four admitted ordinary trees'
    if kind == 'file': assert s.st_nlink == 1, 'no source hardlink may escape the owned tree'
    row = {'kind':kind, 'mode':stat.S_IMODE(s.st_mode), 'uid':s.st_uid, 'gid':s.st_gid,
           'atime_ns':s.st_atime_ns, 'mtime_ns':s.st_mtime_ns, 'ctime_ns':s.st_ctime_ns,
           'device':s.st_dev, 'inode':s.st_ino, 'nlink':s.st_nlink, 'allocated':s.st_blocks*512,
           'xattrs':{k:base64.b64encode(os.getxattr(path,k,follow_symlinks=False)).decode()
                     for k in sorted(os.listxattr(path,follow_symlinks=False))}}
    if kind == 'file': row['bytes'] = s.st_size
    assert sum(len(v) for v in row['xattrs'].values()) <= MIB
    return row


def inventory(root, guard=lambda:None, limit=5000):
    assert root.resolve()==root and not root.is_symlink()
    rows={}; device=root.stat().st_dev; stack=[root]
    while stack:
        path=stack.pop(); before=metadata(path); assert before['device']==device
        relative=str(path.relative_to(root))
        if before['kind']=='file': row=dict(before,sha256=sha_file(path,guard))
        else:
            children=directory_names(path); row=dict(before,children=children)
            stack.extend(path/name for name in reversed(children))
        assert metadata(path)==before, 'entry changed during noatime capture: '+relative
        rows[relative]=row
        assert len(rows)<=limit, 'bounded fixed-tree inventory'
        if len(rows)%64==0:guard()
    return rows


def portable(rows):
    # Inode/device/ctime/allocation belong to the original filesystem, not the
    # portable copy. Directory nlink follows its preserved child topology.
    return {p:{k:v for k,v in row.items() if k not in IDENTITY_FIELDS}
            for p,row in rows.items()}


def durable_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
    try:os.fsync(fd)
    finally:os.close(fd)


def immutable_json(path, value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush();os.fsync(fd)
    finally:os.close(fd)
    durable_directory(path.parent)


def restore_metadata(path,row):
    os.chown(path,row['uid'],row['gid'],follow_symlinks=False)
    os.chmod(path,row['mode'],follow_symlinks=False)
    for key in set(os.listxattr(path,follow_symlinks=False))-set(row['xattrs']):
        os.removexattr(path,key,follow_symlinks=False)
    for key,value in row['xattrs'].items():
        os.setxattr(path,key,base64.b64decode(value,validate=True),follow_symlinks=False)
    os.utime(path,ns=(row['atime_ns'],row['mtime_ns']),follow_symlinks=False)


def live_users(roots, manifests):
    inodes={(row['device'],row['inode']) for rows in manifests for row in rows.values()}
    prefixes=[str(p) for p in roots]; hits=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:
            with (proc/'cmdline').open('rb') as stream:command=stream.read(128*1024+1)
            assert len(command)<=128*1024,'bounded process command identity'
            # Retain only matched target references, never credential-bearing
            # arguments or the complete command line in the custody receipt.
            matched=[p for p in prefixes if os.fsencode(p) in command]
            if matched:hits.append({'pid':int(proc.name),'reference':'cmdline','targetReferences':matched})
            refs=[proc/'cwd',proc/'exe']+list((proc/'fd').iterdir())
            for ref in refs:
                try:
                    s=ref.stat(); target=os.readlink(ref).removesuffix(' (deleted)')
                    if (s.st_dev,s.st_ino) in inodes or any(target==p or target.startswith(p+'/') for p in prefixes):
                        hits.append({'pid':int(proc.name),'reference':str(ref),'path':target})
                except (FileNotFoundError,ProcessLookupError):pass
            for line in (proc/'maps').read_text().splitlines():
                fields=line.split(None,5)
                if len(fields)<5:continue
                a,b=fields[3].split(':'); key=(os.makedev(int(a,16),int(b,16)),int(fields[4]))
                path=fields[5].removesuffix(' (deleted)') if len(fields)>5 else ''
                if key in inodes or any(path==p or path.startswith(p+'/') for p in prefixes):
                    hits.append({'pid':int(proc.name),'reference':'maps','path':path})
        except (FileNotFoundError,ProcessLookupError):pass
        # Permission/parse errors must fail closed, never imply absence.
    return hits


def protected_files(guard=lambda:None):
    result={}
    for text,want in (NATIVE_PINS|CONTROL_PINS).items():
        path=Path(text); assert path.resolve()==path and not path.is_symlink()
        before=metadata(path);actual=sha_file(path,guard)
        assert actual==want and metadata(path)==before, 'protected source/control changed'
        result[text]=dict(before,sha256=actual)
    return result


def exchange_paths(a,b):
    library=ctypes.CDLL(None,use_errno=True)
    op=library.renameat2
    op.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    op.restype=ctypes.c_int
    if op(-100,os.fsencode(a),-100,os.fsencode(b),2):
        error=ctypes.get_errno();raise OSError(error,os.strerror(error))


def main():
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert ROOT.resolve()==ROOT and OUT.parent.resolve()==OUT.parent
    os.umask(0o077)
    # Reservation is outside receipt-producing try/finally. A repeated caller
    # cannot modify any prior receipt or partially completed recovery directory.
    OUT.mkdir(mode=0o700,exist_ok=False)
    reserved=os.open(OUT/'result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.close(reserved);durable_directory(OUT)
    began=time.monotonic();token=uuid.uuid4().hex
    result={'protocol':'pinkha-four-closed-network-diagnostic-directories-relocation-v1',
            'status':'RUNNING','phase':'admission','controllerSHA256':sha_file(Path(__file__)),
            'sourceRoot':str(ROOT),'destination':str(OUT),'token':token,'errors':[],
            'nativeInvocations':0,'compilerInvocations':0,'accountOpens':0,'ACLMutations':0,'testInvocations':0,
            'protectedOriginalAccountDirectories':[str(p) for p in PROTECTED_TREES[:2]],
            'copiedFiles':0,'retiredDuplicates':[],
            'resourcePolicy':{'recoveryOnlyRootEmergencyBytes':ROOT_EMERGENCY,
                'rootBulkOutputBytes':0,'rootControlBudgetBytes':4*MIB,
                'developmentEmergencyBytes':DEVELOPMENT_EMERGENCY,
                'nativeRootFloorUnchangedBytes':2*1024**3,
                'nativeDevelopmentFloorUnchangedBytes':512*MIB,
                'sourceAllocationExpectedBytes':TOTAL_ALLOCATION,
                'reason':'Only exact dormant-directory custody. Every bulk copy/control manifest is on development; original root holds bounded alias/rename metadata. This does not admit a native or compiler run.'}}
    sources={};protected_before=None;protected_trees=None;copied_manifests={};exchanges={};switched=set()
    def save():
        result['seconds']=round(time.monotonic()-began,3)
        tmp=OUT/('result-'+uuid.uuid4().hex+'.writing')
        immutable_json(tmp,result);os.replace(tmp,OUT/'result.json');durable_directory(OUT)
    def guard():
        assert time.monotonic()-began<600,'bounded recovery deadline'
        root=shutil.disk_usage('/').free;dev=shutil.disk_usage(OUT).free
        result['minimumRootFreeBytes']=min(result.get('minimumRootFreeBytes',root),root)
        result['minimumDevelopmentFreeBytes']=min(result.get('minimumDevelopmentFreeBytes',dev),dev)
        assert root>=ROOT_EMERGENCY,'recovery root emergency floor'
        assert dev>=DEVELOPMENT_EMERGENCY,'development emergency floor'
        assert not (OUT/'abort').exists(),'owned recovery abort'
    def interrupt(*_):raise RuntimeError('owned directory recovery interrupted')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def no_users(stage,paths,manifests):
        found=live_users(paths,manifests)
        result.setdefault('liveUseChecks',[]).append({'stage':stage,'uses':found})
        assert not found,'active source/destination user; preserve every copy'
    try:
        guard();result['rootFreeBefore']=shutil.disk_usage('/').free
        result['developmentFreeBefore']=shutil.disk_usage(OUT).free
        assert result['rootFreeBefore']>=ROOT_EMERGENCY+4*MIB
        assert result['developmentFreeBefore']>=DEVELOPMENT_EMERGENCY+16*MIB
        protected_before=protected_files()
        protected_trees={str(path):inventory(path,guard) for path in PROTECTED_TREES}
        immutable_json(OUT/'protected-files-before.json',protected_before)
        immutable_json(OUT/'private-protected-trees-before.json',protected_trees)
        for name,expected in SCOPES.items():
            source=ROOT/name;assert source.resolve()==source
            rows=inventory(source,guard);assert len(rows)==expected['entries']
            assert sum(r['allocated'] for r in rows.values())==expected['allocated']
            assert rows['result.json']['sha256']==expected['receipt']
            assert rows['.']['mode']==0o700 and rows['.']['uid']==rows['.']['gid']==0
            sources[name]=rows
        assert sum(sum(r['allocated'] for r in rows.values()) for rows in sources.values())==TOTAL_ALLOCATION
        block=os.statvfs(OUT).f_frsize
        # Copying an allocated-light sparse original with ordinary writes can
        # consume its full logical size. Reserve rounded logical file sizes
        # plus one filesystem block per directory, not original allocation.
        upper=sum(((r['bytes']+block-1)//block)*block if r['kind']=='file' else block
                  for rows in sources.values() for r in rows.values())
        result['measuredLogicalCopyUpperBytes']=upper
        result['measuredDevelopmentFreeBeforeCopy']=shutil.disk_usage(OUT).free
        assert result['measuredDevelopmentFreeBeforeCopy']>=DEVELOPMENT_EMERGENCY+upper+16*MIB
        no_users('before-copy',[ROOT/name for name in SCOPES],list(sources.values()))
        immutable_json(OUT/'private-source-manifests.json',sources)
        result['sourceManifestsSHA256']=sha_file(OUT/'private-source-manifests.json')
        result['entryCount']=sum(len(rows) for rows in sources.values())
        retained=OUT/'retained';retained.mkdir(mode=0o700);durable_directory(OUT)
        result['phase']='exact private destination copy';save()
        for name,rows in sources.items():
            source=ROOT/name;destination=retained/name;destination.mkdir(mode=0o700)
            directories=[]
            for relative,row in sorted(rows.items()):
                guard();src=source/relative;dst=destination/relative
                if row['kind']=='directory':
                    if relative!='.':dst.mkdir(mode=0o700)
                    directories.append((dst,row));continue
                assert metadata(src)=={k:v for k,v in row.items() if k!='sha256'}
                in_fd=os.open(src,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
                out_fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                sha=hashlib.sha256();length=0
                try:
                    while part:=os.read(in_fd,MIB):
                        guard();sha.update(part);length+=len(part);view=memoryview(part)
                        while view:
                            n=os.write(out_fd,view);assert n>0;view=view[n:]
                    os.fsync(out_fd)
                finally:os.close(in_fd);os.close(out_fd)
                assert length==row['bytes'] and sha.hexdigest()==row['sha256']
                assert metadata(src)=={k:v for k,v in row.items() if k!='sha256'}
                restore_metadata(dst,row)
                fd=os.open(dst,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
                try:os.fsync(fd)
                finally:os.close(fd)
                result['copiedFiles']+=1
            for dst,row in sorted(directories,key=lambda item:len(item[0].parts),reverse=True):
                restore_metadata(dst,row);durable_directory(dst)
            durable_directory(retained)
            copied=inventory(destination,guard);assert portable(copied)==portable(rows)
            assert inventory(source,guard)==rows,'original changed during exact copy'
            copied_manifests[name]=copied
        no_users('after-copy',[ROOT/name for name in SCOPES]+[retained/name for name in SCOPES],list(sources.values())+list(copied_manifests.values()))
        assert protected_files()==protected_before
        assert {str(p):inventory(p,guard) for p in PROTECTED_TREES}==protected_trees
        immutable_json(OUT/'private-copied-manifests.json',copied_manifests)
        result['copiedManifestsSHA256']=sha_file(OUT/'private-copied-manifests.json')
        restore={'protocol':'four-closed-network-directories-stable-custody-map-v1',
                 'sourceManifests':str(OUT/'private-source-manifests.json'),
                 'sourceManifestsSHA256':result['sourceManifestsSHA256'],
                 'controllerSHA256':result['controllerSHA256'],
                 'directories':{name:{'original':str(ROOT/name),'retained':str(retained/name),'receiptSHA256':SCOPES[name]['receipt']} for name in SCOPES},
                 'privateDataMustNotBePublished':True,'noNativeAcceptance':True,
                 'historicalReplayPhysicalPathPrerequisite':'lan-progress-replay1/sdk-source becomes reachable through a stable alias. The completed source-replay receipt stays unchanged. apply.py requires resolve()==supplied source, so any future replay must use a fresh independent physical copy verified against this manifest, or restore the original physical directory before that old command. No current queued consumer invokes it.',
                 'physicalRestoration':'Under fresh original native/build capacity gates, require no inode/FD/cwd/maps users, make an exclusive exact copy beside the original alias, fsync and independently verify every file/hash/mode/uid/gid/atime/mtime/xattr and entry topology against the immutable manifest, then atomically exchange the copy with the still-exact alias. Never remove or overwrite the sole retained destination. Do not rerun the completed controllers or replay account/ACL operations.'}
        immutable_json(OUT/'restoration-map.json',restore)
        result['restorationMapSHA256']=sha_file(OUT/'restoration-map.json')
        result['phase']='atomic stable-path exchanges';save()
        for name,rows in sources.items():
            guard();source=ROOT/name;destination=retained/name
            exchange=ROOT/(name+'.verified-original-'+token);exchanges[name]=exchange
            assert not os.path.lexists(exchange) and inventory(source,guard)==rows
            assert portable(inventory(destination,guard))==portable(rows)
            no_users('before-exchange-'+name,[source,destination],[rows,copied_manifests[name]])
            os.symlink(str(destination),exchange);durable_directory(ROOT)
            exchange_paths(source,exchange);durable_directory(ROOT);switched.add(name)
            assert source.is_symlink() and os.readlink(source)==str(destination) and source.resolve()==destination
            assert exchange.resolve()==exchange and not exchange.is_symlink()
            old=inventory(exchange,guard)
            assert portable(old)==portable(rows)
            for relative,before in rows.items():
                actual=old[relative]
                assert all(actual[k]==before[k] for k in IDENTITY_FIELDS if not (relative=='.' and k=='ctime_ns'))
            assert portable(inventory(source.resolve(),guard))==portable(rows)
            no_users('after-exchange-'+name,[source,exchange,destination],[old,copied_manifests[name]])
            result.setdefault('atomicExchanges',[]).append({'name':name,'sourceNowStableSymlink':True,'verifiedOriginalDuplicate':str(exchange),'rootDirectoryCtimeAfterRename':old['.']['ctime_ns']})
            save()
        result['phase']='retire only complete verified original duplicates';save()
        for name,rows in sources.items():
            guard();source=ROOT/name;destination=retained/name;exchange=exchanges[name]
            old=inventory(exchange,guard)
            assert portable(old)==portable(rows) and portable(inventory(destination,guard))==portable(rows)
            assert source.is_symlink() and os.readlink(source)==str(destination)
            no_users('immediately-before-retirement-'+name,[source,exchange,destination],[old,copied_manifests[name]])
            immutable_json(OUT/('verified-before-retirement-'+name+'.json'),{'sourceManifestsSHA256':result['sourceManifestsSHA256'],'destination':str(destination),'retiring':str(exchange),'exactPortableMetadataAndHashes':True,'noLiveUsers':True})
            # Every deletion here concerns only the just-verified duplicate.
            # The destination and stable source alias remain on any failure.
            for relative,row in sorted(old.items(),key=lambda item:len(Path(item[0]).parts),reverse=True):
                guard();path=exchange/relative
                if row['kind']=='file':
                    assert metadata(path)=={k:v for k,v in row.items() if k!='sha256'}
                    assert sha_file(path)==row['sha256'];path.unlink()
                else:
                    assert not directory_names(path);path.rmdir()
            durable_directory(ROOT)
            assert not os.path.lexists(exchange)
            result['retiredDuplicates'].append({'name':name,'allocatedBytes':SCOPES[name]['allocated']});save()
            assert portable(inventory(destination,guard))==portable(rows)
        result['status']='PASS_EXACT_FOUR_CLOSED_PRIVATE_DIRECTORIES_RELOCATED_STABLE_ALIASES_NO_NATIVE_ACCEPTANCE'
        result['recoveredRootAllocatedBytes']=TOTAL_ALLOCATION
        result['allOriginalReceiptsAndPortableMetadataUnchanged']=True
    except BaseException as error:
        result['status']='FAIL_DIRECTORY_CUSTODY_NO_FURTHER_RETIREMENT'
        result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':result['phase']})
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        final_deadline=time.monotonic()+90
        def final_guard():
            assert time.monotonic()<final_deadline,'bounded final custody verification'
        try:
            assert sha_file(Path(__file__),final_guard)==result['controllerSHA256'],'controller source changed during custody'
            result['controllerSourceUnchanged']=True
            if protected_before is not None:assert protected_files(final_guard)==protected_before
            if protected_trees is not None:assert {str(p):inventory(p,final_guard) for p in PROTECTED_TREES}==protected_trees
            result['protectedOriginalAccountsHelperClosureControlsAndNativePinsUnchanged']=(protected_before is not None and protected_trees is not None)
            result['finalDirectoryStates']={name:{'sourceIsSymlink':(ROOT/name).is_symlink(),'sourceTarget':os.readlink(ROOT/name) if (ROOT/name).is_symlink() else None,'oldDuplicatePresent':os.path.lexists(exchanges[name]) if name in exchanges else False} for name in SCOPES}
            for name in switched:
                assert (ROOT/name).is_symlink() and os.readlink(ROOT/name)==str(OUT/'retained'/name)
                assert portable(inventory(OUT/'retained'/name,final_guard))==portable(sources[name])
        except BaseException as error:
            result['status']='FAIL_DIRECTORY_CUSTODY_FINAL_INTEGRITY'
            result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':'final integrity'})
        result['rootFreeAfter']=shutil.disk_usage('/').free
        result['developmentFreeAfter']=shutil.disk_usage(OUT).free
        result['phase']='completed' if result['status'].startswith('PASS') else result['phase'];save()
        print(json.dumps({'status':result['status'],'result':str(OUT/'result.json'),'sha256':sha_file(OUT/'result.json'),'seconds':result['seconds'],'retiredCount':len(result['retiredDuplicates']),'errors':result['errors'],'rootFree':result['rootFreeAfter'],'developmentFree':result['developmentFreeAfter']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
