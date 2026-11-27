#!/usr/bin/env python3
"""Compare the already accepted signed grant using the existing verified native reader."""
import importlib.util,json,os,pathlib,shutil,signal,subprocess,time
ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
OUT=ROOT/'retained-grant-comparison1'
PRIOR=ROOT/'retained-acl-recovery1'
SOURCE=pathlib.Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison/resume_linux_filesv2_invite.py')
spec=importlib.util.spec_from_file_location('fv2',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077);OUT.mkdir(exist_ok=False)
result={'protocol':'retained-reader-grant-signed-network-comparison-v1','status':'RUNNING','nativeBuilds':0,'originalAccountProcesses':0,'mutatingHTTPCalls':0,'grantCalls':0,'joinCalls':0,'processes':[],'errors':[]}
expected=None;p=None;stream=None
def save():m.atomic(OUT/'result.json',result)
def custody():return {name:m.account_inventory(ROOT/'attempt1'/name) for name in ('alice','bob')}
try:
    assert shutil.disk_usage(OUT).free>=2*1024**3+64*1024**2
    result['sourceBefore']=m.source_admission()
    prev=json.loads(m.pinned(PRIOR/'result.json','8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d',1024**2))
    assert prev['status']=='FAIL_RETAINED_ACL_RECOVERY' and prev['error']=="AssertionError('Reader grant did not materialize')"
    assert prev['grantCalls']==1 and prev['grantResponse']['status']==204 and prev['allOwnedGroupsPositivelyAbsent']
    assert prev['accountInitCalls']==prev['joinCalls']==prev['inviteCreateCalls']==0
    assert prev['sourceBefore']==prev['sourceAfter']==result['sourceBefore']
    expected=json.loads(m.pinned(PRIOR/'private-current-accounts.json','9e0719b6bf2837c9717de89e61e5d49cf9b7478458e34a2117a61fbf4e95025c',4*1024**2))
    assert custody()==expected
    result['priorReceiptSHA256']=m.sha(PRIOR/'result.json');result['priorCustodySHA256']=m.sha(PRIOR/'private-current-accounts.json')
    aid=prev['accounts']['alice'];sid=prev['spaceId']
    src=ROOT/'attempt1/alice'/aid/'sdk/anysync'/str(sid+'.db');dst=OUT/src.name
    result['copiedDatabaseAndSidecars']=[]
    for suffix in ('','-wal','-shm'):
        original=pathlib.Path(str(src)+suffix)
        if original.exists():
            target=pathlib.Path(str(dst)+suffix);shutil.copyfile(original,target)
            assert m.sha(original)==m.sha(target)
            result['copiedDatabaseAndSidecars'].append({'name':original.name,'bytes':original.stat().st_size,'sha256':m.sha(original)})
    wallet=ROOT/'attempt1/alice'/aid/'wallet.key';copy_wallet=OUT/'wallet.key'
    wallet_row=next(v for v in expected['alice']['rows'] if v['path']==aid+'/wallet.key')
    m.pinned(wallet,wallet_row['sha256'],1024**2);shutil.copyfile(wallet,copy_wallet)
    assert m.sha(copy_wallet)==wallet_row['sha256'];assert custody()==expected
    binary=ROOT/'acl-verified-comparison8/comparer'
    assert m.sha(binary)=='f7f6d1d42cb6d2e67e5bac3603228c33d809dd1099295fddf0a6ea1e46ba8c45'
    m.pinned(m.NODECONF,m.NODECONF_SHA,65536)
    result['reusedSignedVerifierBinarySHA256']=m.sha(binary)
    command=[str(binary),str(copy_wallet),str(dst),sid,str(m.NODECONF),str(OUT/'isolated-app-state'),aid]
    row={'command':command};result['processes'].append(row)
    stream=(OUT/'compare.log').open('xb');started=time.monotonic()
    env=os.environ.copy();env.update(GOMAXPROCS='2',GOMEMLIMIT='1GiB')
    p=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    row.update(pid=p.pid,pgid=p.pid);save()
    while p.poll() is None:
        assert time.monotonic()-started<75,'bounded existing comparison deadline'
        assert shutil.disk_usage(OUT).free>=2*1024**3,'2 GiB root floor'
        time.sleep(.2)
    assert p.returncode==0,'signed chain reader failed; original log retained'
    stream.close();stream=None
    events=[]
    for line in (OUT/'compare.log').read_text().splitlines():
        try:v=json.loads(line)
        except json.JSONDecodeError:continue
        if isinstance(v,dict) and v.get('status')=='VERIFIED_ACL_DIAGNOSTIC_NOT_FILE_ACCEPTANCE':events.append(v)
    assert len(events)==1,'one exact signed-chain comparison is required'
    observed=events[0];assert observed['account']==aid and observed['space']==sid and observed['sameACLRoot']
    result['comparison']=observed
    result['status']='OBSERVED_SIGNED_GRANT_CHAINS_NOT_JOIN_ACCEPTANCE'
except BaseException as e:result.update(status='FAIL_SIGNED_GRANT_DIAGNOSTIC',error=repr(e))
finally:
    if p is not None:
        try:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5);row['forcedKill']=True
            row.update(exitCode=p.returncode,seconds=round(time.monotonic()-started,3))
            try:os.killpg(p.pid,0);row['groupPositivelyAbsent']=False
            except ProcessLookupError:row['groupPositivelyAbsent']=True
            assert p.returncode==0 and row['groupPositivelyAbsent'] and not row.get('forcedKill',False)
        except BaseException as e:result['status']='FAIL_SIGNED_GRANT_DIAGNOSTIC';result['errors'].append({'cleanup':repr(e)})
    if stream is not None:stream.close()
    if (OUT/'compare.log').exists():result['logSHA256']=m.sha(OUT/'compare.log')
    try:
        result['sourceAfter']=m.source_admission()
        assert result['sourceBefore']==result['sourceAfter']
        result['originalAccountsUnchanged']=expected is not None and custody()==expected
        assert result['originalAccountsUnchanged']
    except BaseException as e:result['status']='FAIL_SIGNED_GRANT_DIAGNOSTIC';result['errors'].append({'custody':repr(e)})
    save();print(json.dumps(result))
raise SystemExit(0 if result['status']=='OBSERVED_SIGNED_GRANT_CHAINS_NOT_JOIN_ACCEPTANCE' else 1)
