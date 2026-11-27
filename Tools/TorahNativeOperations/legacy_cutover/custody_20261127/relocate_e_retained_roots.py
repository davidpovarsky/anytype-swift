#!/usr/bin/env python3
"""Exact on-Oracle custody of three closed E roots, including retained private fixtures.

All new payload bytes are written on development; no account is opened, no data
is transferred off host, and no compiler/native method is dispatched. Historical
controllers stay unchanged. Only a separately qualified successor may consume
the explicitly mapped PHYSICAL source destination; an old alias is not admission.
"""
import base64, collections, ctypes, hashlib, json, os, shutil, signal, stat, sys, time
from pathlib import Path

PARENT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127')
DEST = PARENT/'retained'
OUT = PARENT/'attempt1'
ROOTS = [('current8ac', Path('/var/tmp/pinkha-e-cutover-current8ac-20261127')),
         ('llvm-native', Path('/var/tmp/pinkha-e-cutover-llvm-native-20261126')),
         ('core-dryrun', Path('/var/tmp/pinkha-e-cutover-core-dryrun-20261126'))]
EXPECTED_COUNTS = {'current8ac': 7927, 'llvm-native': 13, 'core-dryrun': 9}
EXPECTED_ALLOCATED = {'current8ac': 340316160, 'llvm-native': 112365568, 'core-dryrun': 6537216}
SOURCE_MANIFEST_SHA = 'ccd8659be20d4f7e45ec311195be9211be79b1af17aa9f031374de4ca53ada28'
RETAINED_RECEIPT_PINS = {
 'attempt2/receipt.json': 'fbae1f7a1a628ab75317e2812613a6c96682c6bceef9d8f3187ab13cf5e7e3e6',
 'attempt2/source-before.json': SOURCE_MANIFEST_SHA,
 'rpc-core-attempt5/receipt.json': '73478d7b445484746b2504cd0e0136735a3893143e83230ced242394fdbc7bfb',
 'rpc-host-attempt2/receipt.json': 'ad68dc512105c751c6971e31702452f7f3ebebb73b1ecc1b3911c67b9dde01ea',
 'rpc-generated-qualification1/receipt.json': 'b02f58b6a9c341bcc2c0820c599e0f6ed1cb699d457e936375aea8495865ee62'}
PINS = {
 '/var/lib/pinkha-root-t2-linux-20261126/build1/current/any': '1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636',
 '/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/any': '0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07',
 '/mnt/development/projects/caches/pinkha-e-cutover-rpc-core-attempt5-20261127/cutover-core.test': 'bbd8d9f28d7a948684d9771c5b0effe25abb00570ac0383b0324a56cb6ce1f75'}
MIB = 1024**2
MAX_COPY = 460009472
DEV_FLOOR = 512*MIB
CONTROL_ALLOWANCE = 8*MIB
started = time.monotonic()
root_before = shutil.disk_usage('/').free
phase = 'admission'
final_deadline = None
result = {'status': 'RUNNING', 'protocol': 'pinkha-three-e-roots-physical-custody-v1',
          'compilerInvocations': 0, 'nativeInvocations': 0, 'uniqueBytesRetired': 0,
          'originalAbsolutePathsPreserved': False, 'allCopiesVerified': False,
          'duplicateDirectoriesRetired': [], 'rootBefore': root_before,
          'resourcePolicy': {'purpose': 'closed-product capacity recovery only',
            'allNewBytesOnDevelopment': True, 'rootEmergencyFloor': 256*MIB, 'ambientRootDeltasObservedNotAttributed': True,
            'destinationLiveFloor': DEV_FLOOR, 'measuredCopyUpperBytes': MAX_COPY,
            'destinationAdmissionControlReserve': 64*MIB,
            'nativeAndCompilerRootFloorUnchanged': 2*1024**3}, 'errors': []}

def interrupted(*_): raise RuntimeError('owned custody interrupted')

def free(): return {p: shutil.disk_usage(p).free for p in ('/', '/mnt/development')}

def guard():
    if final_deadline is not None:
        assert time.monotonic() < final_deadline, 'bounded final custody verification'
        return
    assert time.monotonic()-started < 900, 'bounded custody deadline'
    current = free()
    result['ambientRootFreeDeltaBytes'] = current['/']-root_before
    assert current['/'] >= 256*MIB, 'recovery-only root emergency floor'
    assert current['/mnt/development'] >= DEV_FLOOR, 'development emergency reserve'
    assert not (OUT/'abort').exists(), 'owned custody abort'
    assert sum(p.lstat().st_blocks*512 for p in OUT.rglob('*')) <= 24*MIB, 'owned control output bound'

def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOATIME)
    try: os.fsync(fd)
    finally: os.close(fd)

def write(name, value):
    path = OUT/name
    temp = path.with_name(path.name+'.new')
    with temp.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,path);fsync_dir(path.parent)

def save():
    result.update(phase=phase,seconds=round(time.monotonic()-started,3))
    write('result.json',result)

def sha(path):
    digest=hashlib.sha256()
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        while data:=os.read(fd,MIB): guard();digest.update(data)
    finally:os.close(fd)
    return digest.hexdigest()

def stamp(info, with_atime=False):
    values=[info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink]
    if with_atime: values.append(info.st_atime_ns)
    return values

def manifest(root, known_symlinks=None):
    rows=[];identities={};symlinks={};hardlinks=collections.defaultdict(list);stack=[root]
    while stack:
        path=stack.pop();before=path.lstat();relative=path.relative_to(root).as_posix()
        kind='directory' if stat.S_ISDIR(before.st_mode) else 'file' if stat.S_ISREG(before.st_mode) else 'symlink' if stat.S_ISLNK(before.st_mode) else 'special'
        assert kind!='special','nonpreservable entry: '+relative
        row={'path':relative,'kind':kind,'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,'gid':before.st_gid,
             'atimeNS':before.st_atime_ns,'mtimeNS':before.st_mtime_ns,
             'xattrs':{key:base64.b64encode(os.getxattr(path,key,follow_symlinks=False)).decode() for key in sorted(os.listxattr(path,follow_symlinks=False))}}
        assert sum(len(value) for value in row['xattrs'].values())<=MIB
        if kind=='file':
            row.update(bytes=before.st_size,sha256=sha(path),nlink=before.st_nlink)
            if before.st_nlink>1:hardlinks[(before.st_dev,before.st_ino)].append(relative)
        elif kind=='symlink':
            if known_symlinks is None:target=os.readlink(path)
            else:
                witness=known_symlinks[relative]
                assert stamp(before,True)==witness['stamp'],'verified symlink changed: '+relative
                target=witness['target']
            row.update(target=target,bytes=before.st_size)
        else:
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOATIME)
            try:
                with os.scandir(fd) as entries:children=sorted(entry.name for entry in entries)
            finally:os.close(fd)
            stack.extend(path/name for name in reversed(children))
        after=path.lstat();assert stamp(before)==stamp(after),'source race: '+relative
        if before.st_atime_ns != after.st_atime_ns:
            assert kind=='symlink' and known_symlinks is None, 'unexpected source access metadata change'
            result.setdefault('firstSymlinkReadAccessObservations',[]).append({
                'root':str(root),'path':relative,'beforeAtimeNS':before.st_atime_ns,
                'afterAtimeNS':after.st_atime_ns})
        row['atimeNS']=after.st_atime_ns
        if kind=='symlink':symlinks[relative]={'target':row['target'],'stamp':stamp(after,True)}
        identities[relative]=stamp(after);rows.append(row)
        assert len(rows)<=10000,'entry bound'
        if len(rows)%64==0:guard()
    rows.sort(key=lambda row:row['path'])
    topology=sorted(sorted(paths) for paths in hardlinks.values())
    by_path={row['path']:row for row in rows}
    for paths in topology:assert all(by_path[path]['nlink']==len(paths) for path in paths),'external hardlink'
    return {'entries':rows,'hardlinkTopology':topology},identities,symlinks

def live_uses(manifests):
    inodes={(identity[0],identity[1]) for _,identities,_ in manifests.values() for identity in identities.values()}
    prefixes=[str(root) for _,root in ROOTS]+[str(DEST/label) for label,_ in ROOTS]+[
        str(root.with_name(root.name+'.verified-custody-exchange-20261127')) for _,root in ROOTS]
    found=[];inspected=0;start=time.monotonic()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name)==os.getpid():continue
        assert time.monotonic()-start<40, 'bounded no-live census'
        try:
            with (proc/'cmdline').open('rb') as stream:command=stream.read(128*1024+1)
            assert len(command)<=128*1024, 'bounded process command identity'
            # Record only the admitted target references, never other arguments
            # or a credential-bearing complete command line.
            matched=[prefix for prefix in prefixes if os.fsencode(prefix) in command]
            if matched:found.append({'pid':int(proc.name),'reference':'cmdline','targetReferences':matched})
            refs=[proc/'cwd',proc/'exe']+list((proc/'fd').iterdir())
            for ref in refs:
                inspected+=1;assert inspected<=250000
                try:info=ref.stat()
                except (FileNotFoundError,ProcessLookupError):continue
                if (info.st_dev,info.st_ino) in inodes:found.append({'pid':int(proc.name),'reference':str(ref)})
            with (proc/'maps').open('rb') as stream:data=stream.read(4*MIB+1)
            assert len(data)<=4*MIB
            for line in data.splitlines():
                fields=line.split(None,5)
                if len(fields)<5 or not fields[4].isdigit():continue
                major,minor=fields[3].split(b':')
                identity=(os.makedev(int(major,16),int(minor,16)),int(fields[4]))
                if identity in inodes:found.append({'pid':int(proc.name),'reference':'mapped inode'})
        except (FileNotFoundError,ProcessLookupError):continue
    return found


def physical_source_admission(root,wanted):
    source=root/'attempt2/source'
    assert source.resolve()==source and source.is_dir() and not source.is_symlink(), 'exact physical source required'
    rows={row['path']:row for row in wanted['entries']}
    for rel,pin in RETAINED_RECEIPT_PINS.items():
        assert rows[rel]['kind']=='file' and rows[rel]['sha256']==pin and sha(root/rel)==pin, 'retained receipt/source identity differs'
    with os.fdopen(os.open(root/'attempt2/source-before.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as stream:
        expected=json.load(stream)
    actual={}
    prefix='attempt2/source/'
    for rel,row in rows.items():
        if not rel.startswith(prefix):continue
        assert row['kind'] in ('file','directory'), 'original source alias is forbidden'
        if row['kind']=='file':actual[rel[len(prefix):]]={'bytes':row['bytes'],'sha256':row['sha256']}
    assert actual==expected, 'complete qualified source inventory differs'
    return {'physicalSource':str(source),'originalSource':str(ROOTS[0][1]/'attempt2/source'),
            'sourceManifestSHA256':SOURCE_MANIFEST_SHA,'files':len(expected),
            'allSourceBytesAndPathsMatchOriginalInventory':True,'retainedReceiptPins':RETAINED_RECEIPT_PINS}


def pin_without_guard(path):
    h=hashlib.sha256()
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    try:
        while data:=os.read(fd,MIB):
            if final_deadline is not None:guard()
            h.update(data)
    finally:os.close(fd)
    return h.hexdigest()

def restore_metadata(path,row):
    os.chown(path,row['uid'],row['gid'],follow_symlinks=False)
    if row['kind']!='symlink':os.chmod(path,row['mode'],follow_symlinks=False)
    else:assert stat.S_IMODE(path.lstat().st_mode)==row['mode']
    for key in set(os.listxattr(path,follow_symlinks=False))-set(row['xattrs']):os.removexattr(path,key,follow_symlinks=False)
    for key,value in row['xattrs'].items():os.setxattr(path,key,base64.b64decode(value),follow_symlinks=False)
    os.utime(path,ns=(row['atimeNS'],row['mtimeNS']),follow_symlinks=False)

def copy_root(source,destination,wanted):
    destination.mkdir(mode=0o700)
    first={path:paths[0] for paths in wanted['hardlinkTopology'] for path in paths[1:]}
    directories=[]
    for row in wanted['entries']:
        guard();src,dst=source/row['path'],destination/row['path']
        if row['kind']=='directory':
            if row['path']!='.':dst.mkdir(mode=0o700)
            directories.append((dst,row));continue
        if row['kind']=='symlink':os.symlink(row['target'],dst)
        elif row['path'] in first:os.link(destination/first[row['path']],dst)
        else:
            source_fd=os.open(src,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
            target_fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            digest=hashlib.sha256();length=0
            try:
                while data:=os.read(source_fd,MIB):
                    guard();digest.update(data);length+=len(data);view=memoryview(data)
                    while view:
                        amount=os.write(target_fd,view);assert amount>0;view=view[amount:]
                os.fsync(target_fd)
            finally:os.close(source_fd);os.close(target_fd)
            assert length==row['bytes'] and digest.hexdigest()==row['sha256']
        restore_metadata(dst,row)
        if row['kind']=='file':
            fd=os.open(dst,os.O_RDONLY|os.O_NOATIME)
            try:os.fsync(fd)
            finally:os.close(fd)
    for path,row in sorted(directories,key=lambda pair:len(pair[0].parts),reverse=True):restore_metadata(path,row);fsync_dir(path)
    fsync_dir(destination.parent)
    # readlink is allowed to update destination atime. Verify the target once,
    # restore only its copied access metadata, then use lstat+captured target.
    witnesses={}
    for row in wanted['entries']:
        if row['kind']=='symlink':
            p=destination/row['path'];assert os.readlink(p)==row['target']
            os.utime(p,ns=(row['atimeNS'],row['mtimeNS']),follow_symlinks=False)
            witnesses[row['path']]={'target':row['target'],'stamp':stamp(p.lstat(),True)}
    fsync_dir(destination)
    return witnesses

def exchange_paths(a,b):
    libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];rename.restype=ctypes.c_int
    assert rename(-100,os.fsencode(a),-100,os.fsencode(b),2)==0,os.strerror(ctypes.get_errno())
    fsync_dir(a.parent)

def main():
    global phase, final_deadline
    if sys.flags.optimize: raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    os.umask(0o077)
    assert PARENT.parent.resolve()==PARENT.parent and not PARENT.exists() and not PARENT.is_symlink()
    PARENT.mkdir(mode=0o700)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    assert OUT.parent.resolve()==OUT.parent and DEST.parent.resolve()==DEST.parent
    OUT.mkdir(mode=0o700,exist_ok=False)
    before={};copied={};exchanges={};copy_started=[];switched=[]
    controller_before=None
    try:
        controller_before=sha(Path(__file__))
        result['controllerSHA256']=controller_before
        journal = {'scope': 'tiny-owned-journal-roundtrip', 'unicode': 'בדיקת יומן', 'nested': {'value': 1}, 'bytes': 0}
        write('journal-roundtrip.json', journal)
        with (OUT/'journal-roundtrip.json').open('r', encoding='utf-8') as stream:
            assert json.load(stream) == journal, 'journal roundtrip differs'
        result['journalSerializationReadback'] = True
        guard();assert free()['/mnt/development']>=DEV_FLOOR+MAX_COPY+64*MIB,'complete measured copy reserve'
        assert not DEST.exists() and not DEST.is_symlink()
        for p,pin in PINS.items():assert sha(Path(p))==pin
        result['protectedQualificationPins']=PINS
        for label,root in ROOTS:
            assert root.parent.resolve()==root.parent and root.is_dir() and not root.is_symlink()
            before[label]=manifest(root)
            assert len(before[label][0]['entries'])==EXPECTED_COUNTS[label], 'retained root census changed'
            allocated=sum((root/row['path']).lstat().st_blocks*512 for row in before[label][0]['entries'])
            assert allocated==EXPECTED_ALLOCATED[label], 'retained allocation changed'
            write(label+'-source-before.json',before[label][0]);write(label+'-source-identities.json',before[label][1])
        result['originalPhysicalSourceAdmission']=physical_source_admission(ROOTS[0][1],before['current8ac'][0])
        result['usersBefore']=live_uses(before);assert not result['usersBefore']
        block=os.statvfs(DEST.parent).f_frsize
        upper=sum(((row['bytes']+block-1)//block)*block if row['kind']=='file' else block for wanted,_,_ in before.values() for row in wanted['entries'])
        assert upper<=MAX_COPY,'owned roots grew beyond approved exact copy allocation'
        result['actualMeasuredCopyUpperBytes']=upper
        result['entryCounts']={label:len(value[0]['entries']) for label,value in before.items()}
        result['sourceManifestSHA256']={label:sha(OUT/(label+'-source-before.json')) for label in before}
        phase='fsynced exact destination copies';save();DEST.mkdir(mode=0o700)
        for label,root in ROOTS:
            wanted,identity,witnesses=before[label];destination=DEST/label
            copy_started.append(label)
            target_links=copy_root(root,destination,wanted)
            current,current_identity,_=manifest(root,witnesses)
            assert current==wanted and current_identity==identity,'original bytes or metadata changed'
            actual,actual_identity,actual_links=manifest(destination,target_links)
            assert actual==wanted,'destination bytes/metadata/topology mismatch'
            copied[label]=(actual,actual_identity,actual_links)
            write(label+'-verified-copy.json',actual)
        assert not live_uses(before) and not live_uses(copied)
        result['allCopiesVerified']=True
        result['relocatedPhysicalSourceAdmission']=physical_source_admission(DEST/'current8ac',copied['current8ac'][0])
        result['exactOriginalToPhysicalRoots']={str(root):str(DEST/label) for label,root in ROOTS}
        result['allPortableMetadataAndTopologyRetained']=True
        write('restore.json',{'roots':{str(root):str(DEST/label) for label,root in ROOTS},
            'manifests':{label:str(OUT/(label+'-source-before.json')) for label,_ in ROOTS},
            'instructions':'Original absolute paths are stable symlinks for historical reads, not physical-source admission. New successor controllers require this pinned custody receipt and the exact physical destination. To restore original physical directories for an unchanged historical controller, require no live users and enough root capacity; copy each retained directory to an exclusive original-parent staging directory preserving every manifest byte, mode, owner, xattr, mtime, atime, symlink target and hardlink group; verify and fsync; atomically exchange with the stable symlink. Keep the sole retained copy until all paths are verified. Original compiler logs and acceptance outcomes are unchanged.'})
        phase='atomic stable original paths';save()
        for label,root in ROOTS:
            guard();wanted,identity,witnesses=before[label]
            current,current_identity,_=manifest(root,witnesses)
            assert current==wanted and current_identity==identity
            assert not live_uses(before) and not live_uses(copied)
            temporary=root.with_name(root.name+'.verified-custody-exchange-20261127')
            assert not temporary.exists() and not temporary.is_symlink()
            exchanges[label]=temporary
            temporary.symlink_to(DEST/label,target_is_directory=True);fsync_dir(root.parent)
            exchange_paths(root,temporary)
            assert root.is_symlink() and root.resolve()==DEST/label
            switched.append(label)
        for label,root in ROOTS:
            actual,_,_=manifest(root.resolve(),copied[label][2]);assert actual==before[label][0]
            original,_,_=manifest(exchanges[label],before[label][2]);assert original==before[label][0]
        for p,pin in PINS.items():assert sha(Path(p))==pin
        assert not live_uses(before) and not live_uses(copied)
        result['originalAbsolutePathsPreserved']=True
        phase='verified duplicate retirement';save()
        for label,root in ROOTS:
            guard();original=exchanges[label]
            current,_,_=manifest(original,before[label][2]);assert current==before[label][0]
            actual,_,_=manifest(DEST/label,copied[label][2]);assert actual==before[label][0]
            assert not live_uses(before) and not live_uses(copied)
            # Each retiring entry now has a byte-exact durable retained twin.
            for row in sorted(before[label][0]['entries'],key=lambda row:len(Path(row['path']).parts),reverse=True):
                p=original/row['path']
                if row['kind']=='directory':p.rmdir()
                else:p.unlink()
            fsync_dir(root.parent);result['duplicateDirectoriesRetired'].append(label);save()
        result['status']='PASS_THREE_E_ROOTS_EXACT_PHYSICAL_CUSTODY_STABLE_ORIGINAL_ALIASES'
        result['retainedPhysicalSourceRequalified']=True
    except BaseException as error:
        result['status']='FAIL_CUSTODY_ORIGINAL_OR_VERIFIED_COPY_RETAINED'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        final_deadline=time.monotonic()+90
        after={}
        for path,pin in PINS.items():
            try:after[path]=pin_without_guard(Path(path))
            except BaseException as e:result['errors'].append({'phase':'final-protected-pin','path':path,'type':type(e).__name__,'message':str(e)})
        result['protectedPinsAfter']=after;result['protectedPinsAfterEqual']=after==PINS
        if after!=PINS:result['status']='FAIL_CURRENT_PRODUCT_PIN_CHANGED'
        try:
            assert controller_before is not None and sha(Path(__file__))==controller_before, 'controller source changed during custody'
            result['controllerSourceUnchanged']=True
            result['copyStartedRoots']=copy_started
            result['verifiedCopyRoots']=list(copied)
            result['switchedRoots']=switched
            result['finalRootStates']={label:{
                'sourceIsSymlink':root.is_symlink(),
                'sourceTarget':os.readlink(root) if root.is_symlink() else None,
                'destinationPresent':os.path.lexists(DEST/label),
                'oldDuplicatePresent':os.path.lexists(exchanges[label]) if label in exchanges else False
            } for label,root in ROOTS}
            verified_destinations={}
            for label in copied:
                destination=DEST/label
                assert destination.resolve()==destination and not destination.is_symlink()
                actual,_,_=manifest(destination,copied[label][2])
                assert actual==before[label][0], 'verified destination changed after transition'
                verified_destinations[label]=True
            result['verifiedDestinationsAfterEqual']=verified_destinations
            # Source/receipt bytes are verified at every complete surviving
            # physical location. A partial unverified destination is retained,
            # but is never described as an admitted source.
            receipt_locations=[]
            original=ROOTS[0][1]
            if original.is_dir() and not original.is_symlink():receipt_locations.append(original)
            old=exchanges.get('current8ac')
            if old is not None and old.is_dir() and not old.is_symlink():receipt_locations.append(old)
            if 'current8ac' in copied:receipt_locations.append(DEST/'current8ac')
            captured=before.get('current8ac')
            if captured is not None:
                captured_rows={row['path']:row for row in captured[0]['entries']}
                assert receipt_locations, 'captured receipt source has no surviving complete location'
                retained_after={}
                for location in receipt_locations:
                    pins={rel:sha(location/rel) for rel in RETAINED_RECEIPT_PINS}
                    assert pins==RETAINED_RECEIPT_PINS
                    assert all(captured_rows[rel]['sha256']==pin for rel,pin in pins.items())
                    retained_after[str(location)]=pins
                result['retainedReceiptPinsAfter']=retained_after
                result['capturedRetainedReceiptBytesUnchanged']=True
            for label in switched:
                original=dict(ROOTS)[label]
                assert original.is_symlink() and os.readlink(original)==str(DEST/label)
            result['finalIntegrityVerificationComplete']=True
        except BaseException as error:
            result['status']='FAIL_CUSTODY_FINAL_INTEGRITY'
            result['errors'].append({'phase':'final custody integrity','type':type(error).__name__,'message':str(error)})
        result['freeAfter']=free();result['completedUTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    print(json.dumps({key:result.get(key) for key in ('status','phase','seconds','errors','entryCounts','duplicateDirectoriesRetired','freeAfter')},sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1

if __name__=='__main__':raise SystemExit(main())
