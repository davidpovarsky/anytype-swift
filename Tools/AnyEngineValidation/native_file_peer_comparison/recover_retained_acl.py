import importlib.util,json,pathlib,os,time,signal,subprocess,shutil,socket,urllib.request,urllib.error

ROOT=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
OUT=ROOT/'retained-acl-recovery1'
PRIOR=ROOT/'retained-sync-diagnostic5'
BUILD=ROOT/'acl-refresh-native1'
REPO=pathlib.Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077);OUT.mkdir(exist_ok=False)
START=time.monotonic();children=[]
result={'protocol':'pinkha-retained-signed-acl-recovery-v1','status':'RUNNING','processes':[],'accountInitCalls':0,'joinCalls':0,'inviteCreateCalls':0,'grantCalls':0,'actualFilesV2Acceptance':False}
FLOOR=2*1024**3
def native_close_gate(rows):
    return bool(rows) and all(row.get('exitCode')==0 and row.get('groupPositivelyAbsent') is True and row.get('forcedKill',False) is False for row in rows)
def save():m.atomic(OUT/'result.json',result)
def guard():
    assert time.monotonic()-START<260,'bounded retained recovery deadline'
    assert shutil.disk_usage(OUT).free>=FLOOR,'2 GiB disk floor'
def interrupted(*_):raise RuntimeError('owned retained recovery interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
def req(peer,path,method='GET',body=None,headers=None):
    guard();assert peer['p'].poll() is None,'owned native process exited'
    headers=dict(headers or {})
    if isinstance(body,dict):body=json.dumps(body).encode();headers['Content-Type']='application/json'
    r=urllib.request.Request(peer['base']+path,data=body,method=method,headers=headers)
    try:
        with urllib.request.urlopen(r,timeout=8) as response:
            raw=response.read(1048577);assert len(raw)<=1048576
            return {'status':response.status,'bodyBytes':len(raw),'value':json.loads(raw) if raw else None}
    except urllib.error.HTTPError as e:
        raw=e.read(65537);assert len(raw)<=65536
        return {'status':e.code,'bodyBytes':len(raw),'value':json.loads(raw) if raw else None}
def start(name):
    data=ROOT/'attempt1'/name
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    stream=(OUT/(name+'.log')).open('xb');env={k:v for k,v in os.environ.items() if not k.startswith('ANY_')}
    env.update(ANY_DATA_DIR=str(data),GOMAXPROCS='2',GOMEMLIMIT='1GiB')
    command=[str(BUILD/'any'),'run','--config',str(OUT/'config.yml'),'--data-dir',str(data),'--addr','127.0.0.1:'+str(port)]
    p=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    row={'name':name,'pid':p.pid,'pgid':p.pid,'command':command,'log':str(OUT/(name+'.log'))}
    peer={'p':p,'row':row,'stream':stream,'base':'http://127.0.0.1:'+str(port)};children.append(peer);result['processes'].append(row);save()
    end=time.monotonic()+45
    while True:
        guard();assert p.poll() is None,'native startup exited'
        try:
            if req(peer,'/v1/health')['status']==200:break
        except (OSError,urllib.error.URLError):pass
        assert time.monotonic()<end,'native readiness deadline';time.sleep(.25)
    return peer
def wait_for(label,fn,seconds):
    end=time.monotonic()+seconds
    while True:
        guard();value=fn()
        if value:return value
        assert time.monotonic()<end,label;time.sleep(.4)
def native_inventory():
    expected=json.loads((BUILD/'source-manifest.json').read_text())['files']
    found={str(p.relative_to(BUILD/'source')):{'sha256':m.sha(p),'bytes':p.stat().st_size} for p in (BUILD/'source').rglob('*') if p.is_file()}
    assert found==expected,'new native source changed'
    return {'sourceManifestSHA256':m.sha(BUILD/'source-manifest.json'),'files':len(found),'binarySHA256':m.sha(BUILD/'any')}
try:
    guard();result['sourceBefore']=m.source_admission()
    build=json.loads((BUILD/'result.json').read_text())
    assert build['status']=='PASS_BUILD_ONLY' and build['isolatedSourceUnchanged'] and build['allOwnedGroupsPositivelyAbsent']
    assert build['patchSHA256']=='1d4213438a5d9e8024f5506309bd759ef6a72ef9d880ce9269392fc185f43f6c'
    assert build['sourceBefore']==build['sourceAfter']==result['sourceBefore']
    assert m.sha(BUILD/'any')==build['binary']['sha256'] and m.sha(BUILD/'source-manifest.json')==build['sourceManifestSHA256']
    result['nativeBefore']=native_inventory();result['nativeBuildReceiptSHA256']=m.sha(BUILD/'result.json')
    prior=json.loads(m.pinned(PRIOR/'result.json','412af4d6ee05bbf1051726ff8fc488fb4df33b5017b3206fff911577be638774',4*1024**2))
    custody=json.loads(m.pinned(PRIOR/'private-current-accounts.json','bfcc893ae6f7516441804365b2fac28be445c5468b1ee5d15c706746251b1621',4*1024**2))
    assert prior['status']=='OBSERVED_NOT_ACCEPTANCE' and prior['allOwnedGroupsPositivelyAbsent']
    assert prior['sourceBefore']==prior['sourceAfter']==result['sourceBefore']
    for name in ('alice','bob'):assert m.account_inventory(ROOT/'attempt1'/name)==custody[name]
    result['priorResultSHA256']=m.sha(PRIOR/'result.json');result['priorCustodySHA256']=m.sha(PRIOR/'private-current-accounts.json')
    diagnosis=json.loads(m.pinned(ROOT/'acl-refresh-overlay1/diagnosis.json','a0d862afa0ba3c8f9b5c187bc1c32641027608322fe9c7f35c049062bb6ccaee',1024**2))
    assert diagnosis['status']=='PASS_DIAGNOSIS_ONLY_NOT_FILE_ACCEPTANCE'
    result['diagnosisSHA256']=m.sha(ROOT/'acl-refresh-overlay1/diagnosis.json')
    result['spaceId']=sid=prior['spaceId'];result['accounts']=accounts=prior['accounts']
    result['objectId']=oid='bafyreicytuyyuw7nu6cklsgptni4k5xoyi3u4suijh6lp5moki2nvtpi7e'
    request_id='bafyreie4yiel6bub7hwamwnt5ohaqcnm3tng2hygjlxmb3xsqmec3fwwiq'
    m.pinned(m.NODECONF,m.NODECONF_SHA,65536)
    text='network:\n  nodeconfPath: '+str(m.NODECONF)+'\nindex:\n  embedder: none\np2p:\n  enabled: true\n  localDiscovery: true\n  serviceName: '+m.SERVICE+'\n  global:\n    enabled: false\n'
    (OUT/'config.yml').write_text(text);result['configSHA256']=m.sha(OUT/'config.yml')
    (OUT/'controller.py').write_bytes(pathlib.Path(__file__).read_bytes());result['controllerSHA256']=m.sha(OUT/'controller.py')
    a=start('alice');b=start('bob')
    for peer,name in ((a,'alice'),(b,'bob')):
        got=req(peer,'/v1/account');assert got['status']==200 and got['value']['id']==accounts[name]
    prefix='/v1/spaces/'+sid
    result['memberBefore']={'alice':req(a,prefix+'/members/me'),'bob':req(b,prefix+'/members/me')}
    assert result['memberBefore']['alice']['value']['permission']=='owner'
    assert result['memberBefore']['bob']['status']==409
    result['requestReads']=[]
    def pending():
        response=req(a,prefix+'/members/requests');result['requestReads'].append(response);save()
        assert response['status']==200
        rows=response['value']['requests'];matches=[r for r in rows if r.get('identity')==accounts['bob']]
        assert len(matches)<=1
        if not matches:return False
        assert matches[0]['recordId']==request_id,'recovery must use the original canonical request'
        return matches[0]
    result['recoveredOriginalRequest']=wait_for('signed pending request did not recover',pending,75)
    result['grantCalls']=1;save()
    result['grantResponse']=req(a,prefix+'/acl/accept','POST',{'requestRecordId':request_id,'permission':'reader'})
    assert result['grantResponse']['status']==204
    def active():
        response=req(b,prefix+'/members/me')
        if response['status']!=200:return False
        v=response['value'];assert v['identity']==accounts['bob']
        return v if v['status']=='active' and v['permission']=='reader' else False
    result['readerAfter']=wait_for('Reader grant did not materialize',active,90)
    result['ownerAfter']=req(a,prefix+'/members/me')
    assert result['ownerAfter']['status']==200 and result['ownerAfter']['value']['permission']=='owner'
    result['requestsAfter']=req(a,prefix+'/members/requests')
    assert result['requestsAfter']['status']==200
    assert not [r for r in result['requestsAfter']['value']['requests'] if r.get('identity')==accounts['bob']]
    result['readerWriteDenial']=req(b,prefix+'/objects/'+oid+'/files?name=denied-reader-acl-refresh.bin','POST',b'authorized regression fixture denied reader write',{'Content-Type':'application/octet-stream'})
    assert result['readerWriteDenial']['status']==403
    assert result['readerWriteDenial']['value']['error']['code'] in ('space.read_only','acl.forbidden')
    result['status']='PASS_RETAINED_REQUEST_REFRESH_AND_NATIVE_READER_GRANT'
except BaseException as e:result.update(status='FAIL_RETAINED_ACL_RECOVERY',error=repr(e))
finally:
    def final_failure(where,error):
        result['status']='FAIL_RETAINED_ACL_RECOVERY'
        result.setdefault('errors',[]).append({'phase':where,'error':repr(error)})
    for c in reversed(children):
        p=c['p'];row=c['row']
        try:
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    row['forcedKill']=True;os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
            row['exitCode']=p.returncode
            try:os.killpg(p.pid,0);row['groupPositivelyAbsent']=False
            except ProcessLookupError:row['groupPositivelyAbsent']=True
        except BaseException as e:final_failure('owned native cleanup '+row['name'],e)
        try:c['stream'].close();row['logSHA256']=m.sha(pathlib.Path(row['log']))
        except BaseException as e:final_failure('owned log finalization '+row['name'],e)
    result['allOwnedGroupsPositivelyAbsent']=all(c['row'].get('groupPositivelyAbsent',False) for c in children)
    if result['status'].startswith('PASS') and not native_close_gate([c['row'] for c in children]):
        final_failure('native clean close gate',RuntimeError('every leader must exit zero and its owned group must be positively absent'))
    try:result['sourceAfter']=m.source_admission()
    except BaseException as e:final_failure('original source custody',e)
    try:
        if (BUILD/'source-manifest.json').exists():result['nativeAfter']=native_inventory()
        if result.get('nativeBefore')!=result.get('nativeAfter'):raise RuntimeError('new native custody changed')
    except BaseException as e:final_failure('new native custody',e)
    try:
        assert result['allOwnedGroupsPositivelyAbsent'],'account custody requires owned process-group absence'
        current={name:m.account_inventory(ROOT/'attempt1'/name) for name in ('alice','bob')}
        for name in current:assert m.account_inventory(ROOT/'attempt1'/name)==current[name]
        m.atomic(OUT/'private-current-accounts.json',current);result['finalAccountInventorySHA256']=m.sha(OUT/'private-current-accounts.json')
    except BaseException as e:final_failure('retained account custody',e)
    result['seconds']=round(time.monotonic()-START,3);save();print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS_RETAINED_REQUEST_REFRESH_AND_NATIVE_READER_GRANT' else 1)
