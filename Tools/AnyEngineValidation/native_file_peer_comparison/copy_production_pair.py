#!/usr/bin/env python3
"""Preserve an exact independent-account copy for OS-isolated LAN qualification."""
import importlib.util,json,os,pathlib,shutil,stat,time
ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
CLOUD=pathlib.Path('/var/lib/pinkha-w1-cloud-filesv2-20261127')
OUT=ROOT/'production-lan-custody1'
SOURCE=pathlib.Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/resume_linux_filesv2_invite.py')
spec=importlib.util.spec_from_file_location('fv2',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077);OUT.mkdir(exist_ok=False)
result={'protocol':'exact-production-test-pair-isolated-lan-custody-v1','status':'RUNNING','nativeRuns':0,'accountInitCalls':0,'joinCalls':0,'grantCalls':0,'attachments':0,'originalAccountsModified':False,'actualFilesV2Acceptance':False,'errors':[]}
before=None
def save():m.atomic(OUT/'result.json',result)
def guard():assert shutil.disk_usage(OUT).free>=2*1024**3,'2 GiB root emergency floor'
def stopped():
    matches=[]
    wanted={str(CLOUD/'attempt2'/name).encode() for name in ('alice','bob')}
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except (OSError,ProcessLookupError):continue
        if b'run' in args and any(v in args for v in wanted):matches.append(int(entry.name))
    assert matches==[],'original production pair still has a native process'
def inventory():return {name:m.account_inventory(CLOUD/'attempt2'/name) for name in ('alice','bob')}
def copy_file(src,dst):
    guard();shutil.copy2(src,dst);s=os.stat(src,follow_symlinks=False);os.chown(dst,s.st_uid,s.st_gid);return dst
try:
    prior=json.loads(m.pinned(CLOUD/'attempt5/result.json','84810888ba0be79546278f90286ff4da9e0a6052daf83922e787132ad628b59c',2*1024**2))
    assert prior['status']=='FAIL' and prior['failure']=='cloud quota recovery still lacks a real fileV2 verified custody receipt'
    assert prior['nativeACLAccepted'] and prior['quotaLocalPreservationAccepted']
    assert len(prior['processes'])==3 and all(p['exitCode']==0 and p['groupPositivelyAbsent'] and not p['forcedKill'] for p in prior['processes'])
    result['sourceBefore']=m.source_admission();assert prior['sourceBefore']==prior['sourceAfter']==result['sourceBefore']
    result['priorQuotaReceiptSHA256']=m.sha(CLOUD/'attempt5/result.json')
    result['accounts']=prior['accounts'];assert set(result['accounts'])=={'alice','bob'} and len(set(result['accounts'].values()))==2
    result['spaceId']=prior['spaceID'];result['objectId']=prior['objectID']
    stopped();before=inventory();m.atomic(OUT/'private-original-custody-before.json',before)
    size=sum(v.get('bytes',0) for item in before.values() for v in item['rows'])
    result['originalLogicalBytes']=size
    assert shutil.disk_usage(OUT).free>=2*1024**3+size+64*1024**2,'exact account copies do not fit'
    result['freeBefore']=shutil.disk_usage(OUT).free
    for name in ('alice','bob'):
        src=CLOUD/'attempt2'/name;dst=OUT/name
        shutil.copytree(src,dst,copy_function=copy_file)
        for p in [src]+sorted(src.rglob('*')):
            target=dst if p==src else dst/p.relative_to(src);s=p.lstat();d=target.lstat()
            assert (d.st_dev,d.st_ino)!=(s.st_dev,s.st_ino)
            os.chown(target,s.st_uid,s.st_gid)
            assert stat.S_IMODE(d.st_mode)==stat.S_IMODE(s.st_mode)
        current=m.account_inventory(dst);assert current['rows']==before[name]['rows']
    stopped();after=inventory();assert before==after
    clones={name:m.account_inventory(OUT/name) for name in ('alice','bob')}
    m.atomic(OUT/'private-clone-custody.json',clones)
    result['originalCustodySHA256']=m.sha(OUT/'private-original-custody-before.json')
    result['cloneCustodySHA256']=m.sha(OUT/'private-clone-custody.json')
    result['copiedEvidence']=[]
    for rel in ('attempt2/result.json','attempt5/result.json','attempt3/owner-files-before.json','attempt5/quota-offline-preservation.json','attempt2/public-nodeconf.yml'):
        src=CLOUD/rel;dst=OUT/'source-evidence'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst);assert m.sha(src)==m.sha(dst)
        result['copiedEvidence'].append({'source':str(src),'copy':str(dst),'sha256':m.sha(dst),'bytes':dst.stat().st_size})
    assert m.sha(OUT/'source-evidence/attempt2/public-nodeconf.yml')==prior['productionNodeconfSHA256']=='6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060'
    result['productionNodeconfSHA256']=prior['productionNodeconfSHA256']
    result['originalAccountsUnchanged']=True;result['allCopiesByteAndModeIdentical']=True
    result['status']='PASS_EXACT_COPY_CUSTODY_NOT_LAN_ACCEPTANCE'
except BaseException as e:result.update(status='FAIL_COPY_CUSTODY',error=repr(e))
finally:
    try:
        stopped()
        result['originalAccountsUnchanged']=before is not None and inventory()==before
        assert result['originalAccountsUnchanged']
        result['sourceAfter']=m.source_admission();assert result['sourceAfter']==result['sourceBefore']
    except BaseException as e:result['status']='FAIL_COPY_CUSTODY';result['errors'].append({'finalCustody':repr(e)})
    result['freeAfter']=shutil.disk_usage(OUT).free;save();print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS_EXACT_COPY_CUSTODY_NOT_LAN_ACCEPTANCE' else 1)
