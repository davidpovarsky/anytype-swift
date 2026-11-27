#!/usr/bin/env python3
"""Read-only local source/artifact verification; never imports or runs a controller."""
import datetime, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUB = ROOT / 'published'
OUT = {'protocol': 'independent-original-evidence-review-v1', 'productExecution': False,
       'nativeCalls': 0, 'compilerCalls': 0, 'files': [], 'manifests': []}
def digest(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
def get(p): return json.loads(p.read_text())
def canonical(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def fact(p):
    b=p.read_bytes(); return {'bytes':len(b),'sha256':digest(b),'gitBlob':blob(b)}

index=get(ROOT/'complete-primary-source-index.json')
for row in index['files']:
    f=fact(PUB/row['path']); assert f['gitBlob']==row['gitBlob'],row['path']
    OUT['files'].append(dict(path=row['path'],**f))
dirs=['20261127-wave1-native-block-styles','20261127-wave1-cloud-quota-observation']
for name in dirs:
    manifest=get(PUB/'docs/validation'/name/'artifact-manifest.json')
    for row in manifest['files']:
        f=fact(PUB/row['path'])
        assert f['sha256']==row['sha256'] and f['bytes']==row['bytes'],row
    OUT['manifests'].append({'path':'docs/validation/'+name+'/artifact-manifest.json','entries':len(manifest['files']),'status':'PASS'})
probe=get(ROOT/'oracle-original-hash-result.json')
assert probe['status']=='PASS_ORIGINAL_HASHES' and len(probe['files'])==33
assert all(x['matches'] for x in probe['files'])
originals={x['path']:x for x in probe['files']}
qual=[]
for name in dirs:
    q=get(PUB/'docs/validation'/name/'qualification.json'); qual.append(q)
    for a in q['artifacts']:
        f=fact(PUB/a['repositoryPath']); o=originals[a['originalOraclePath']]
        assert a['copiedByteExact'] is True
        assert f['sha256']==a['sha256']==o['actualSHA256']
        assert f['bytes']==a['bytes']==o['actualBytes']
    c=fact(PUB/q['controller']['path']);assert c['sha256']==q['controller']['sha256']

np=PUB/'docs/validation'/dirs[0]/'original'
n=get(np/'result.json'); nq=qual[0]
assert n['status']=='PASS_ACTUAL_NATIVE_TWELVE_TYPED_BLOCK_CREATES_SIGKILL_COLD'
assert n['errors']==[] and n['actualNativeBlockAcceptance'] is True
assert n['nativeSourceBefore']==n['nativeSourceAfter']==nq['nativeSource']
assert n['originalArchiveUnchanged'] and n['originalAccountModified'] is False
assert n['hostCreationSource']['executed'] is False and n['hostIntentDispatchCalls']==0
assert [n[x] for x in ['appBuilds','goBuilds','swiftBuilds','coldNativeCreateCalls']]==[0,0,0,0]
assert n['original182Rerun'] is False and n['allOwnedGroupsAbsent'] is True
warmbytes=(np/'proof/warm-block-rows.json').read_bytes()
coldbytes=(np/'proof/cold-block-rows.json').read_bytes()
assert warmbytes==coldbytes
warm=json.loads(warmbytes); assert len(warm)==12
assert [x['id'] for x in warm]==n['blockIDs'] and len(set(n['blockIDs']))==12
assert len(n['mutations'])==13 and n['mutations'][0]['kind']=='page-create'
matrix=[]
for i,m in enumerate(n['mutations']):
    raw=(np/'http'/('response-'+str(i)+'.json')).read_bytes(); v=json.loads(raw)
    assert digest(raw)==m['httpReceipt']['rawSHA256']
    assert len(raw)==m['httpReceipt']['observedBytes']
    assert m['httpReceipt']['status']==201 and m['httpReceipt']['bodyMayBeTruncated'] is False
    assert m['dispatched'] and m['acknowledgementValidated']
    assert v==m['response']
    if i==0:
        assert v['objectId']==n['objectID']; continue
    assert len(v['recordIds'])==1 and v['recordIds'][0]==warm[i-1]['id']
    assert isinstance(v['versionId'],str) and v['versionId']
    assert isinstance(v['changeId'],str) and v['changeId']
    assert v.get('rejections',[])==[]
    row=warm[i-1]; req=m['request']
    assert row['type']==req['type'] and row['nav']==req['nav']
    if req['text']: assert row['text'].encode()==req['text'].encode()
    else: assert 'text' not in row
    if req['style']: assert canonical(row['style'])==canonical(req['style'])
    else: assert 'style' not in row
    assert digest(canonical(row))==m['currentRowSHA256']
    qr=nq['matrix'][i-1]
    assert qr=={'name':m['name'],'type':row['type'],'recordID':row['id'],
        'textUTF8Bytes':len(req['text'].encode()),'style':req['style'],'nav':req['nav']}
    matrix.append({'name':m['name'],'type':row['type'],'textUTF8Bytes':len(req['text'].encode()),
                   'style':req['style'],'emptyTextAbsent':not req['text'],'actualNonemptyChangeID':True})
assert matrix[-1]['textUTF8Bytes']==65536
assert set(x['type'] for x in matrix[:6])=={'paragraph','heading','quote','code','list_item','check_list_item'}
assert all(x['textUTF8Bytes']==0 for x in matrix[:6])
assert warm[10]['nav']['parentId']==warm[1]['id']
assert type(warm[4]['style']['ordered']) is bool and warm[4]['style']['ordered'] is False
assert type(warm[5]['style']['checked']) is bool and warm[5]['style']['checked'] is False
wp,cp=n['processes'];assert wp['pid']!=cp['pid']
assert wp['exitCode']==-9 and wp['intentionalCrash'] is True
assert cp['exitCode']==0 and cp['intentionalCrash'] is False
for p in [wp,cp]:
    assert p['groupAbsent'] is True and p['actualOSNetworkDenial'] is True
    assert p['seccomp']==2 and p['noNewPrivs']==1
    assert set(p['scope']['peerCounts'].values())=={0}
    assert originals[p['log']]['actualSHA256']==p['logSHA256']
assert wp['scope']==cp['scope']
OUT['native']={'status':n['status'],'seconds':n['seconds'],'originalResult':fact(np/'result.json'),
    'nativeSource':n['nativeSourceBefore'],'matrix':matrix,'warmColdBytesEqual':True,
    'originalRowsSHA256':digest(warmbytes),'originalArchiveSHA256':n['originalArchiveSHA256'],
    'warmPID':wp['pid'],'warmExit':wp['exitCode'],'coldPID':cp['pid'],'coldExit':cp['exitCode'],
    'coldCreateCalls':0,'hostIntentDispatchCalls':0,'privateCredentialsPublished':False}

cp=PUB/'docs/validation'/dirs[1]/'original'
c=get(cp/'result.json');cq=qual[1]
assert c['status']=='OBSERVED_CLOUD_ACCOUNT_LIMITS_NO_EXPLICIT_RETRY' and c['errors']==[]
assert c['sourceBefore']==c['sourceAfter']==cq['nativeSource']==nq['nativeSource']
assert c['sourceUnchanged'] and c['configUnchanged'] and c['carsBefore']==c['carsAfter']
assert c['cloudQuotaRecoveryAccepted'] is False and c['originalFourFileCloudCustodyAccepted'] is False
assert all(c[x]==0 for x in ['accountCreates','builds','fileCreates','fileRetryCalls','inviteCalls','offloadCalls'])
assert c['process']['exitCode']==0 and c['process']['groupAbsent'] and c['allOwnedGroupsAbsent']
assert len(c['requests'])==9
responses=[]
for i,req in enumerate(c['requests'],1):
    raw=(cp/'http'/('response-'+str(i)+'.json')).read_bytes()
    assert req['method']=='GET' and req['status']==200
    assert req['sha256']==digest(raw) and req['observedBytes']==len(raw)
    responses.append(json.loads(raw))
assert responses[3]==c['syncBefore'] and responses[4]==c['limits']
assert responses[5]['files']==c['files']
assert responses[6:8]==c['limitedFileStatuses'] and responses[8]==c['syncAfter']
assert c['limits']==cq['limits'] and c['files']==cq['files']
assert c['limitedFileStatuses']==cq['limitedFileStatuses']
storage=c['limits']['storage']
assert type(storage['limitBytes']) is int and storage['limitBytes']==0
assert type(storage['usageBytes']) is int and storage['usageBytes']==21070
assert c['reportedRemainingBytes']==0
assert all(f['cached'] is True for f in c['files'])
assert len(c['files'])==4 and sorted(f['durable'] for f in c['files'])==[False,False,True,True]
assert all(s['state']=='limited' and s['attempts']==1 and 'storage limit exceeded' in s['lastErr'] for s in c['limitedFileStatuses'])
assert all(s['fileId'] in {x['fileId'] for x in c['files'] if x['durable'] is False} for s in c['limitedFileStatuses'])
assert all(c[k]['localPeers']==c[k]['globalPeers']==0 for k in ['syncBefore','syncAfter'])
stamp=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
storage_time=stamp(storage['fetchedAt']); spaces_time=stamp(c['limits']['sharedSpaces']['fetchedAt'])
assert c['startedUnix']<=c['limitsObservedAtUnix']<=storage_time<=spaces_time<=c['startedUnix']+c['elapsedSeconds']+0.01
OUT['cloud']={'status':c['status'],'seconds':c['elapsedSeconds'],'originalResult':fact(cp/'result.json'),
    'limits':c['limits'],'limitRequestStartedAtUnix':c['limitsObservedAtUnix'],
    'storageFetchedAfterRequestStartSeconds':round(storage_time-c['limitsObservedAtUnix'],6),
    'nineActualGETRepliesChecked':True,'cachedOriginalFiles':4,'durableOriginalFiles':2,'limitedOriginalFiles':2,
    'originalCARsEqualBeforeAfter':True,'carRows':c['carsAfter'],'quotaRecoveryAccepted':False,
    'fourFileCloudCustodyAccepted':False,'noExplicitRetries':True,
    'ordinaryNativeBackgroundSyncNotRuledOut':True,'originalPriorFailure':c['priorQuotaFailure']}

creator='Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift'
after=(PUB/creator).read_bytes(); before=(ROOT/'original-creator.swift').read_bytes()
assert blob(before)==index['originalCreator']['gitBlob']
assert digest(before)==n['hostCreationSource']['sha256']
new=before.replace(b'              parentID.isEmpty || AnyEditorBlock.validID(parentID),',
    b'              parentID.utf8.count <= 256,\n              parentID.isEmpty || AnyEditorBlock.validID(parentID),',1)
new=new.replace(b'!position.isEmpty, position.utf8.count <= 1024,',b'!position.isEmpty, position.utf8.count <= 256,',1)
assert new==after
test=PUB/'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyNativeBlockLocationLimitTests.swift'
txt=test.read_text();assert txt.count('@Test')==2
successor=get(PUB/'docs/validation'/dirs[0]/'location-limit-source-successor.json')
assert digest(test.read_bytes()+b'\n')==successor['testWhitespaceOnlySuccessorFromSHA256']
first_failure=get(PUB/'docs/validation'/dirs[0]/'location-limit-publication-first-failure.json')
assert first_failure['commitWasCreated'] is False and first_failure['testsWereExecuted'] is False
assert first_failure['originalJob']['exit_code']==1 and 'new blank line at EOF' in first_failure['originalJob']['output']
OUT['hostSourceOnly']={'before':fact(ROOT/'original-creator.swift'),'after':fact(PUB/creator),
    'exactTwoGuardOperationsReconstructFullSource':True,'tests':fact(test),'authoredMethods':2,
    'compilerAndRuntimeStatus':'NOT_RUN','native256BoundaryAcceptance':False,
    'originalPublicationPreflightFailurePreserved':True,'testWhitespaceOnlyInverseVerified':True,
    'methodNames':['inclusiveNativeParentAndPositionLimitsSurviveEncoding','oversizedLocationsAreRefusedBeforeAnIntentCanBeDispatched']}
OUT['oracleOriginalHashChecks']={'count':33,'allMatch':True,'probe':fact(ROOT/'oracle-original-hash-probe.json'),
    'originalResult':fact(ROOT/'oracle-original-hash-result.json')}
OUT['status']='PASS_SOURCE_AND_ORIGINAL_EVIDENCE_REVIEW_ONLY'
target=ROOT/'independent-byte-semantic-proof.json'
target.write_text(json.dumps(OUT,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':OUT['status'],'primaryFiles':len(OUT['files']),'manifests':OUT['manifests'],
    'nativeCases':len(matrix),'oracleOriginalHashChecks':33,'proof':fact(target)},sort_keys=True))
