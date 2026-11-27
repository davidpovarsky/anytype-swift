#!/usr/bin/env python3
"""Preserve exactly three handed-off component cache roots behind stable paths.

Storage custody only: no compiler, test, Native operation, source preparation,
Git mutation, or historical process probe. Source/receipt directories stay on
root. The unchanged 99dc compiler controller retains its root resource floor.
A distinct later read-only 99dc input qualification is mandatory; compiler
warmness is unproven. All new bulk data and evidence live on development.
"""
from pathlib import Path
import base64
import ctypes
import fcntl
import hashlib
import json
import os
import shutil
import signal
import stat
import sys
import time
import uuid

ROOT = Path('/var/lib/pinkha-wave2-native-block-menu-20261127')
PROPERTY_ROOT = Path('/var/lib/pinkha-wave2-property-lifecycle-20261127')
OUT = Path('/mnt/development/projects/evidence/pinkha-wave2-component-cache-preserved-20261127')
LOCK = OUT.parent / '.pinkha-wave2-component-cache-custody.lock'
CLAIM = OUT.parent / '.pinkha-wave2-component-cache-custody-active.json'
SCOPES = {
    'build': {'allocated':339099648, 'entries':6191, 'inode':2933637},
    'cache': {'allocated':27303936, 'entries':100, 'inode':2933636},
    'clang-module-cache': {'allocated':35536896, 'entries':24, 'inode':2933647},
}
NATIVE_PINS = {}  # No Native input or service is touched by this storage task.
CONTROL_PINS = {
    str(ROOT/'attempt1/cache-handoff.json'): '493a7d628bdce5642f54b3b3f99deedfe24b28f6d8e68267c18c7629f227367b',
    str(ROOT/'attempt1/receipt.json'): 'bbf101c3821fafca51f6d6e9a0bef009f1f415ff935ab4e2606ca0feb599e231',
    str(ROOT/'attempt1/dependency-sources-after.json'): '67c6696b3d3e760553acd6a9d493cb6190c8093e702fef1d8c2a8ae96a5f9f08',
    str(ROOT/'component/Package.swift'): '53d8a7d55d88531271b0d830cecda060ac0499eedbf848ab1ad211ab7dc287df',
    str(ROOT/'component/Package.resolved'): 'dd338df7aba015276d48f10bba2f6ad2487a21417e4e5b23116db94366926a4e',
    str(PROPERTY_ROOT/'inputs/run_component.py'): '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2',
    str(PROPERTY_ROOT/'inputs/AnyNativePropertyPresentation.swift'): 'aa40239c5ba749b20974735337c0af11ba477c9aac870261f4ae5ae76f76c731',
    str(PROPERTY_ROOT/'inputs/AnyNativePropertyPresentation.original.swift'): 'c5935470e1c515461ad11b764e0169297eeb645a3ba4a522d0a7111070437dfb',
    str(PROPERTY_ROOT/'inputs/AnyNativePropertyPresentationTests.swift'): '7df1a45aa85cd71bc7ec8353b98150609bc2d2fb07a2aa1ebf08f7fb40fdab61',
    str(PROPERTY_ROOT/'inputs/prepare_component_sources.py'): 'ef7b3195584ee599737ec86cef5da49bff1946f2fc0bc0a4d491915f1a829cff',
    str(PROPERTY_ROOT/'inputs/AnyUIErrorText.exact.swift'): '25d49c71f60b613cf3131b9e31d8c2a29b2743ff62d332873835e5a3341a42bb',
    str(PROPERTY_ROOT/'inputs/error-text-source.json'): 'e1257b04a74d8e68d3ff9e596e26b2d1b087764787ebf471bf304dcdb961e29e',
}
DEPENDENCY_ROOT = Path('/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127/Modules')
DEPENDENCIES = ('PinkhaAnyEngine','PinkhaAnyHost','PinkhaAnyIntegration','PinkhaKit')
PROTECTED_TREES = [ROOT/'component', ROOT/'attempt1', PROPERTY_ROOT/'inputs'] + [DEPENDENCY_ROOT/name for name in DEPENDENCIES]
MIB = 1024**2
ROOT_EMERGENCY = 256*MIB  # Storage recovery only; not compiler admission.
DEVELOPMENT_EMERGENCY = 512*MIB
FURTHER_COMPONENT_BUDGET = 256*MIB
TOTAL_ALLOCATION = 401940480
IDENTITY_FIELDS = ('device', 'inode', 'ctime_ns', 'allocated', 'nlink')
BUILD_LINK = 'out/Products/Debug-linux-aarch64'
COPIED_LINK_READ_RESTORATIONS = []


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
    kind = ('directory' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode)
            else 'symlink' if stat.S_ISLNK(s.st_mode) else 'unsupported')
    assert kind != 'unsupported', 'special entries are outside the exact cache custody'
    if kind == 'symlink': assert s.st_nlink == 1, 'no hardlinked symlink'
    if kind == 'file': assert s.st_nlink == 1, 'no source hardlink may escape the owned tree'
    row = {'kind':kind, 'mode':stat.S_IMODE(s.st_mode), 'uid':s.st_uid, 'gid':s.st_gid,
           'atime_ns':s.st_atime_ns, 'mtime_ns':s.st_mtime_ns, 'ctime_ns':s.st_ctime_ns,
           'device':s.st_dev, 'inode':s.st_ino, 'nlink':s.st_nlink, 'allocated':s.st_blocks*512,
           'xattrs':{k:base64.b64encode(os.getxattr(path,k,follow_symlinks=False)).decode()
                     for k in sorted(os.listxattr(path,follow_symlinks=False))}}
    if kind in ('file','symlink'): row['bytes'] = s.st_size
    assert sum(len(v) for v in row['xattrs'].values()) <= MIB
    return row


def inventory(root, guard=lambda:None, limit=10000, *, scope=None, copied=False):
    assert root.resolve()==root and not root.is_symlink()
    rows={}; device=root.stat().st_dev; stack=[root]
    while stack:
        path=stack.pop(); before=metadata(path); assert before['device']==device
        relative=str(path.relative_to(root))
        if before['kind']=='file': row=dict(before,sha256=sha_file(path,guard))
        elif before['kind']=='symlink':
            assert scope=='build' and relative=='debug', 'only the observed internal build/debug link is admitted'
            assert before['mode']==0o777 and before['uid']==1001 and before['gid']==1002
            target=os.readlink(path)
            assert target==BUILD_LINK and before['bytes']==len(os.fsencode(target))
            after_read=metadata(path)
            if copied and after_read['atime_ns']!=before['atime_ns']:
                # Linux readlink may advance relatime on the newly copied link.
                # Restore only the just-observed access change on OUR copy, not
                # prior drift or any original node. Ctime is nonportable.
                assert {k:v for k,v in after_read.items() if k!='atime_ns'}=={k:v for k,v in before.items() if k!='atime_ns'}
                os.utime(path,ns=(before['atime_ns'],before['mtime_ns']),follow_symlinks=False)
                restored=metadata(path)
                assert {k:v for k,v in restored.items() if k!='ctime_ns'}=={k:v for k,v in before.items() if k!='ctime_ns'}
                COPIED_LINK_READ_RESTORATIONS.append({'path':str(path),'inode':before['inode'],
                    'atimeBeforeReadNS':before['atime_ns'],'atimeAfterReadNS':after_read['atime_ns'],
                    'atimeRestoredNS':restored['atime_ns']})
                before=restored
            else: assert after_read==before, 'original link metadata changed during capture'
            row=dict(before,target=target,sha256=hashlib.sha256(os.fsencode(target)).hexdigest())
        else:
            children=directory_names(path); row=dict(before,children=children)
            stack.extend(path/name for name in reversed(children))
        assert metadata(path)==before, 'entry changed during noatime capture: '+relative
        rows[relative]=row
        assert len(rows)<=limit, 'bounded fixed-tree inventory'
        if len(rows)%64==0:guard()
    if scope=='build':
        assert rows['debug']['kind']=='symlink' and rows[BUILD_LINK]['kind']=='directory'
        # Every ancestor is represented in the same physical inventory.
        assert all(rows[str(p)]['kind']=='directory' for p in Path(BUILD_LINK).parents)
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
    if row['kind']=='symlink':
        assert row['mode']==0o777 and stat.S_IMODE(os.lstat(path).st_mode)==0o777
    else: os.chmod(path,row['mode'],follow_symlinks=False)
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


def read_json_noatime(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        data=b''
        while part:=os.read(fd,MIB):
            data+=part;assert len(data)<=4*MIB
    finally:os.close(fd)
    return json.loads(data)


def input_closure(manifests):
    handoff=read_json_noatime(ROOT/'attempt1/cache-handoff.json')
    assert handoff['status']=='TERMINAL_PASS_CACHE_RELEASED_TO_ROOT'
    assert handoff['nextOwner']=='wave2-root-properties' and handoff['noOwnedProcessGroupRemains'] is True
    assert handoff['sourceDependencyRoot']==str(DEPENDENCY_ROOT)
    assert handoff['componentRoot']==str(ROOT/'component')
    for field,name in [('scratchPath','build'),('cachePath','cache'),('clangModuleCachePath','clang-module-cache')]:
        assert handoff[field]==str(ROOT/name)
    closure=read_json_noatime(ROOT/'attempt1/dependency-sources-after.json')
    assert closure['baseCommit']=='8f2c11713fb8a40ae13444104723666ffef68afe'
    assert closure['dependencies']==list(DEPENDENCIES) and len(closure['files'])==370
    expected={row['path']:row for row in closure['files']};assert len(expected)==370
    actual={}
    for name in DEPENDENCIES:
        for relative,row in manifests[str(DEPENDENCY_ROOT/name)].items():
            if row['kind']!='directory':
                assert row['kind']=='file'
                actual['Modules/'+name+'/'+relative]=row
    assert set(actual)==set(expected), 'full 370-source physical input set must be exact'
    for path,want in expected.items():
        assert actual[path]['bytes']==want['bytes'] and actual[path]['sha256']==want['sha256'],path
    for row in handoff['originalComponentSourceCopies']:
        for tree,relative in [(ROOT/'component',row['path']),(ROOT/'attempt1','compiled-source/'+row['path'])]:
            got=manifests[str(tree)][relative]
            assert got['kind']=='file' and got['sha256']==row['sha256'] and got['bytes']==row['bytes']
    return {'exactLocalSourceFiles':370,'historicalHandoffAbsenceRetained':True,
            'historicalProcessGroupReprobed':False,'sourceDependencyRoot':str(DEPENDENCY_ROOT),
            'compilerInputQualificationAfterRelocation':'REQUIRED_UNCHANGED_99DC_370_AND_THREE_GIT_PHYSICAL_SETS',
            'compilerWarmness':'UNPROVEN'}


def main():
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert ROOT.resolve()==ROOT and OUT.parent.resolve()==OUT.parent
    lock=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        assert stat.S_ISREG(os.fstat(lock).st_mode) and os.fstat(lock).st_nlink==1
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not os.path.lexists(CLAIM), 'retained unresolved custody claim; no automatic replay'
        return relocate_locked()
    finally:os.close(lock)


def relocate_locked():
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert ROOT.resolve()==ROOT and OUT.parent.resolve()==OUT.parent
    os.umask(0o077)
    # Reservation is outside receipt-producing try/finally. A repeated caller
    # cannot modify any prior receipt or partially completed recovery directory.
    OUT.mkdir(mode=0o750,exist_ok=False)
    os.chown(OUT,0,1002);os.chmod(OUT,0o750)
    reserved=os.open(OUT/'result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.close(reserved);durable_directory(OUT)
    began=time.monotonic();token=uuid.uuid4().hex
    result={'protocol':'pinkha-three-owned-component-cache-directories-relocation-v1',
            'status':'RUNNING','phase':'admission','controllerSHA256':sha_file(Path(__file__)),
            'sourceRoot':str(ROOT),'destination':str(OUT),'token':token,'errors':[],
            'nativeInvocations':0,'compilerInvocations':0,'accountOpens':0,'ACLMutations':0,'testInvocations':0,
            'protectedOriginalSourceAndReceiptDirectories':[str(p) for p in PROTECTED_TREES],
            'copiedFiles':0,'retiredDuplicates':[],
            'resourcePolicy':{'recoveryOnlyRootEmergencyBytes':ROOT_EMERGENCY,
                'rootBulkOutputBytes':0,'rootControlBudgetBytes':4*MIB,
                'developmentEmergencyBytes':DEVELOPMENT_EMERGENCY,
                'nativeRootFloorUnchangedBytes':2*1024**3,
                'furtherComponentDestinationReserveBytes':FURTHER_COMPONENT_BUDGET,
                'compilerRootAdmissionUnchangedBytes':2*1024**3+256*MIB,
                'compilerResourcePathUnchanged':str(ROOT),
                'compilerWarmness':'UNPROVEN',
                'postCustodySourceQualificationRequired':True,
                'sourceAllocationExpectedBytes':TOTAL_ALLOCATION,
                'reason':'Only the three handed-off cache roots. The component and original receipts stay physically on root; 99dc is unchanged. No compiler admission or warm-cache credit is supplied.'}}
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
        assert dev>=DEVELOPMENT_EMERGENCY+FURTHER_COMPONENT_BUDGET,'development reserve including further component budget'
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
        assert result['developmentFreeBefore']>=DEVELOPMENT_EMERGENCY+FURTHER_COMPONENT_BUDGET+16*MIB
        protected_before=protected_files()
        protected_trees={str(path):inventory(path,guard) for path in PROTECTED_TREES}
        immutable_json(OUT/'protected-files-before.json',protected_before)
        immutable_json(OUT/'private-protected-trees-before.json',protected_trees)
        result['sourceInputCustody']=input_closure(protected_trees)
        for name,expected in SCOPES.items():
            source=ROOT/name;assert source.resolve()==source
            rows=inventory(source,guard,scope=name);assert len(rows)==expected['entries']
            assert sum(r['allocated'] for r in rows.values())==expected['allocated']
            assert rows['.']['device']==2049 and rows['.']['inode']==expected['inode']
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
        assert result['measuredDevelopmentFreeBeforeCopy']>=DEVELOPMENT_EMERGENCY+FURTHER_COMPONENT_BUDGET+upper+16*MIB
        no_users('before-copy',[ROOT/name for name in SCOPES],list(sources.values()))
        immutable_json(OUT/'private-source-manifests.json',sources)
        result['sourceManifestsSHA256']=sha_file(OUT/'private-source-manifests.json')
        result['entryCount']=sum(len(rows) for rows in sources.values())
        retained=OUT/'retained';retained.mkdir(mode=0o750)
        os.chown(retained,0,1002);os.chmod(retained,0o750);durable_directory(OUT)
        result['phase']='exact private destination copy';save()
        for name,rows in sources.items():
            source=ROOT/name;destination=retained/name;destination.mkdir(mode=0o700)
            directories=[]
            for relative,row in sorted(rows.items()):
                guard();src=source/relative;dst=destination/relative
                if row['kind']=='directory':
                    if relative!='.':dst.mkdir(mode=0o700)
                    directories.append((dst,row));continue
                if row['kind']=='symlink':
                    assert name=='build' and relative=='debug' and os.readlink(src)==BUILD_LINK
                    assert metadata(src)=={k:v for k,v in row.items() if k not in ('sha256','target')}
                    os.symlink(row['target'],dst);restore_metadata(dst,row)
                    result['copiedInternalSymlinks']=result.get('copiedInternalSymlinks',0)+1
                    continue
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
            copied=inventory(destination,guard,scope=name,copied=True);assert portable(copied)==portable(rows)
            assert inventory(source,guard,scope=name)==rows,'original changed during exact copy'
            copied_manifests[name]=copied
        no_users('after-copy',[ROOT/name for name in SCOPES]+[retained/name for name in SCOPES],list(sources.values())+list(copied_manifests.values()))
        assert protected_files()==protected_before
        assert {str(p):inventory(p,guard) for p in PROTECTED_TREES}==protected_trees
        immutable_json(OUT/'private-copied-manifests.json',copied_manifests)
        result['copiedManifestsSHA256']=sha_file(OUT/'private-copied-manifests.json')
        restore={'protocol':'three-owned-component-cache-stable-custody-map-v1',
                 'sourceManifests':str(OUT/'private-source-manifests.json'),
                 'sourceManifestsSHA256':result['sourceManifestsSHA256'],
                 'copiedManifestsSHA256':result['copiedManifestsSHA256'],
                 'controllerSHA256':result['controllerSHA256'],
                 'directories':{name:{'original':str(ROOT/name),'retained':str(retained/name),
                      'entries':SCOPES[name]['entries'],'originalAllocatedBytes':SCOPES[name]['allocated']} for name in SCOPES},
                 'handoffSHA256':CONTROL_PINS[str(ROOT/'attempt1/cache-handoff.json')],
                 'unchangedCompilerControllerSHA256':CONTROL_PINS[str(PROPERTY_ROOT/'inputs/run_component.py')],
                 'compilerWarmness':'UNPROVEN','noCompilerOrNativeAcceptance':True,
                 'postCustodyQualification':'Run only unchanged 99dc pinned_inputs as the original ubuntu/chatgpt-agent user. Retain separate source-location receipt for all 370 local and 135/211/919 Git/physical inputs, original component/lock/handoff, and stable alias identities. Ordinary reads may subsequently advance atime; they do not rewrite this completed custody proof.',
                 'physicalRestoration':'Under fresh storage capacity/no-live admission, make an exclusive exact copy beside each original alias, fsync and independently verify bytes/link target/mode/owner/timestamps/xattrs/topology against the immutable source manifest; atomically exchange only with that still-exact alias. Never delete the sole retained destination. No automatic restore is executed.',
                 'privateDataMustNotBePublished':True}
        immutable_json(OUT/'restoration-map.json',restore)
        result['restorationMapSHA256']=sha_file(OUT/'restoration-map.json')
        immutable_json(CLAIM,{'protocol':'pinkha-three-owned-cache-active-claim-v1',
            'controllerSHA256':result['controllerSHA256'],'output':str(OUT),'token':token,
            'restorationMapSHA256':result['restorationMapSHA256'],
            'sourceManifestsSHA256':result['sourceManifestsSHA256']})
        result['activeClaim']=str(CLAIM)
        result['phase']='atomic stable-path exchanges';save()
        for name,rows in sources.items():
            guard();source=ROOT/name;destination=retained/name
            exchange=ROOT/(name+'.verified-original-'+token);exchanges[name]=exchange
            assert not os.path.lexists(exchange) and inventory(source,guard,scope=name)==rows
            assert portable(inventory(destination,guard,scope=name,copied=True))==portable(rows)
            no_users('before-exchange-'+name,[source,destination],[rows,copied_manifests[name]])
            os.symlink(str(destination),exchange);durable_directory(ROOT)
            exchange_paths(source,exchange);durable_directory(ROOT);switched.add(name)
            assert source.is_symlink() and os.readlink(source)==str(destination) and source.resolve()==destination
            assert exchange.resolve()==exchange and not exchange.is_symlink()
            old=inventory(exchange,guard,scope=name)
            assert portable(old)==portable(rows)
            for relative,before in rows.items():
                actual=old[relative]
                assert all(actual[k]==before[k] for k in IDENTITY_FIELDS if not (relative=='.' and k=='ctime_ns'))
            assert portable(inventory(source.resolve(),guard,scope=name,copied=True))==portable(rows)
            no_users('after-exchange-'+name,[source,exchange,destination],[old,copied_manifests[name]])
            result.setdefault('atomicExchanges',[]).append({'name':name,'sourceNowStableSymlink':True,'verifiedOriginalDuplicate':str(exchange),'rootDirectoryCtimeAfterRename':old['.']['ctime_ns']})
            save()
        result['phase']='retire only complete verified original duplicates';save()
        for name,rows in sources.items():
            guard();source=ROOT/name;destination=retained/name;exchange=exchanges[name]
            old=inventory(exchange,guard,scope=name)
            assert portable(old)==portable(rows) and portable(inventory(destination,guard,scope=name,copied=True))==portable(rows)
            assert source.is_symlink() and os.readlink(source)==str(destination)
            no_users('immediately-before-retirement-'+name,[source,exchange,destination],[old,copied_manifests[name]])
            immutable_json(OUT/('verified-before-retirement-'+name+'.json'),{'sourceManifestsSHA256':result['sourceManifestsSHA256'],'destination':str(destination),'retiring':str(exchange),'exactPortableMetadataAndHashes':True,'noLiveUsers':True})
            # Every deletion here concerns only the just-verified duplicate.
            # The destination and stable source alias remain on any failure.
            for relative,row in sorted(old.items(),key=lambda item:len(Path(item[0]).parts),reverse=True):
                guard();path=exchange/relative
                if row['kind'] in ('file','symlink'):
                    if row['kind']=='symlink':
                        assert name=='build' and relative=='debug' and os.readlink(path)==BUILD_LINK
                        assert metadata(path)=={k:v for k,v in row.items() if k not in ('sha256','target')}
                    else:
                        assert metadata(path)=={k:v for k,v in row.items() if k!='sha256'}
                        assert sha_file(path)==row['sha256']
                    path.unlink()
                else:
                    assert not directory_names(path);path.rmdir()
            durable_directory(ROOT)
            assert not os.path.lexists(exchange)
            result['retiredDuplicates'].append({'name':name,'allocatedBytes':SCOPES[name]['allocated']});save()
            assert portable(inventory(destination,guard,scope=name,copied=True))==portable(rows)
        result['status']='PASS_EXACT_THREE_OWNED_COMPONENT_CACHE_ROOTS_RELOCATED_STABLE_ALIASES_NO_COMPILER_ACCEPTANCE'
        result['recoveredRootAllocatedBytes']=TOTAL_ALLOCATION
        result['allOriginalReceiptsAndPortableMetadataUnchanged']=True
        result['sourceLocationQualification']='NOT_RUN_REQUIRED_BEFORE_COMPILER'
        result['componentAndAttempt1RemainPhysicalOnRoot']=True
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
            result['protectedOriginalComponentReceiptsDependencySourcesAnd99dcUnchanged']=(protected_before is not None and protected_trees is not None)
            result['finalDirectoryStates']={name:{'sourceIsSymlink':(ROOT/name).is_symlink(),'sourceTarget':os.readlink(ROOT/name) if (ROOT/name).is_symlink() else None,'oldDuplicatePresent':os.path.lexists(exchanges[name]) if name in exchanges else False} for name in SCOPES}
            for name in switched:
                assert (ROOT/name).is_symlink() and os.readlink(ROOT/name)==str(OUT/'retained'/name)
                assert portable(inventory(OUT/'retained'/name,final_guard,scope=name,copied=True))==portable(sources[name])
        except BaseException as error:
            result['status']='FAIL_DIRECTORY_CUSTODY_FINAL_INTEGRITY'
            result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':'final integrity'})
        result['rootFreeAfter']=shutil.disk_usage('/').free
        result['developmentFreeAfter']=shutil.disk_usage(OUT).free
        result['copiedLinkReadAtimeRestorations']=COPIED_LINK_READ_RESTORATIONS
        success=result['status'].startswith('PASS')
        pass_status=result['status']
        if success:
            result['status']='FINALIZING_VERIFIED_CUSTODY_ACCESS_AND_CLAIM'
            result['phase']='final access and durable claim qualification'
        save()
        if success:
            try:
                # Only newly created evidence permissions change. The old
                # source/cache/receipts and 99dc stay byte/metadata identical.
                for evidence_name in ('restoration-map.json','private-copied-manifests.json'):
                    evidence_path=OUT/evidence_name
                    os.chown(evidence_path,0,1002);os.chmod(evidence_path,0o640)
                qualification=OUT/'source-qualification1'
                qualification.mkdir(mode=0o750,exist_ok=False)
                os.chown(qualification,1001,1002);os.chmod(qualification,0o750)
                durable_directory(OUT)
                claim=read_json_noatime(CLAIM)
                assert claim['controllerSHA256']==result['controllerSHA256'] and claim['token']==token
                assert claim['restorationMapSHA256']==sha_file(OUT/'restoration-map.json')
                result['status']=pass_status;result['phase']='completed'
                result['newEvidenceAccessQualified']=True
                save()
                os.chown(OUT/'result.json',0,1002);os.chmod(OUT/'result.json',0o640)
                durable_directory(OUT)
                # Consumers require BOTH this durable PASS and absent claim.
                # Any error below rewrites FAIL and retains/recreates the claim.
                CLAIM.unlink();durable_directory(CLAIM.parent)
            except BaseException as error:
                result['status']='FAIL_DIRECTORY_CUSTODY_FINAL_ACCESS_OR_CLAIM'
                result['phase']='final access or durable claim failure'
                result['errors'].append({'type':type(error).__name__,'message':str(error),'phase':result['phase']})
                if not os.path.lexists(CLAIM):
                    immutable_json(CLAIM,{'protocol':'pinkha-three-owned-cache-active-claim-v1',
                        'controllerSHA256':result['controllerSHA256'],'output':str(OUT),'token':token,
                        'restorationMapSHA256':result['restorationMapSHA256'],
                        'sourceManifestsSHA256':result['sourceManifestsSHA256'],
                        'unresolvedFinalization':True})
                save()
        print(json.dumps({'status':result['status'],'result':str(OUT/'result.json'),'sha256':sha_file(OUT/'result.json'),'seconds':result['seconds'],'retiredCount':len(result['retiredDuplicates']),'errors':result['errors'],'rootFree':result['rootFreeAfter'],'developmentFree':result['developmentFreeAfter']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
