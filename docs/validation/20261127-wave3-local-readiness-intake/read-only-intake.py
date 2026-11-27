import pathlib,subprocess,json,hashlib,datetime
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
G=['sudo','-n','-u','ubuntu','-g','chatgpt-agent','git','-c','gc.auto=0','-C',str(ROOT)]
DONOR='2cdc1c99783cc90d8e867350c23587fcdc74a2ad'
PREFIX='docs/validation/20261127-wave1-native-related-readiness/'
OUT=pathlib.Path('/tmp/pinkha-wave3-local-readiness-intake.json')
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def h(data):return hashlib.sha256(data).hexdigest()
def sha(path):
    with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert not OUT.exists()
head=b('rev-parse','HEAD').decode().strip()
if subprocess.run(G+['cat-file','-e',DONOR+'^{commit}'],capture_output=True).returncode:b('fetch','--no-tags','--refmap=','origin',DONOR)
qraw=b('show',DONOR+':'+PREFIX+'qualification.json');assert h(qraw)=='f1d9994a063928b6b85c8afa77e8dea00d3aa461ff578451266822ab85b63ec6'
q=json.loads(qraw);assert q['status']=='PASS_NATIVE_CURRENT_LOCAL_SPACE_COMPLETENESS_LIMITS_OPAQUE_CRASH'
for row in q['evidenceFiles']:
    raw=b('show',DONOR+':'+PREFIX+row['path']);assert h(raw)==row['sha256'] and len(raw)==row['bytes']
for row in q['controllers']+[q['contract']]:assert h(b('show',DONOR+':'+row['path']))==row['sha256']
path=pathlib.Path(q['originalResult']['path']);raw=path.read_bytes();assert h(raw)==q['originalResult']['sha256']
assert raw==b('show',DONOR+':'+PREFIX+'native/observed-result.json')
r=json.loads(raw);assert r['errors']==[] and r['allOwnedGroupsAbsent'] and r['nativeSourceBefore']==r['nativeSourceAfter']==q['native']
assert r['appBuilds']==r['goBuilds']==r['swiftBuilds']==0 and r['original182Rerun'] is False
assert r['baselineClaimCount']==3 and r['finalClaimCount']==5 and r['newTargetCreates']==r['probeBundleEnsureCalls']==2
assert r['newCanonicalClaims']==r['newOpaqueClaims']==1 and r['readinessGenerationChangedAcrossProcess'] is False
logs=[]
for row in r['processes']:
    assert sha(row['log'])==row['logSHA256'];assert row['groupAbsent'] is True
    assert row['exitCode']==(-9 if row['intentionalCrash'] else 0)
    if row['name'] in ['related-warm','related-cold']:
        assert row['noNewPrivs']==1 and row['seccomp']==2 and all(x==0 for x in row['scope']['peerCounts'].values())
    logs.append({'name':row['name'],'path':row['log'],'sha256':row['logSHA256']})
assert len(logs)==8
for row in r['phases']:
    f=path.parent/'proof'/(row['name']+'.json');assert sha(f)==row['sha256']
    assert f.read_bytes()==b('show',DONOR+':'+PREFIX+'native/proof/'+f.name)
assert len(r['phases'])==19
source=[]
for relative,expected in r['swiftSources'].items():
    assert h(b('show',head+':'+relative))==expected
    assert h(b('show',DONOR+':'+relative))==expected
    source.append({'path':relative,'sha256':expected})
qualified=r['retainedSwiftProductQualification'];assert sha(qualified['sourceReceipt'])==qualified['sourceReceiptSHA256']
component=json.loads(pathlib.Path(qualified['sourceReceipt']).read_bytes());assert component['sourceAfter']==r['swiftSources']
compilelog=path.parent.parent/'markdown-body-components1/swift.log';assert sha(compilelog)==qualified['originalCompileLogSHA256']
assert 'PinkhaAnyEngineProbe-product' in compilelog.read_text()
assert sha(path.parent.parent/'markdown-body-native1/result.json')==r['reusedOSDenialProbe']['resultSHA256']
assert sha(path.parent/'private-copy-inventory.json')==r['retainedCopy']['inventorySHA256']
assert sha(path.parent/'offline-native-config.yml')==r['configSHA256']
discovery=path.parent.parent/'native-related-snapshot1/result.json'
assert sha(discovery)==q['retainedDiscoveryOnly']['sha256']
assert b('rev-parse','HEAD').decode().strip()==head
receipt={'status':'PASS_ROOT_ORIGINAL_LOCAL_READINESS_EVIDENCE_AND_SOURCE_INTAKE_NO_RERUN','reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootHead':head,'candidate':DONOR,'originalResult':q['originalResult'],'sourceClosure':source,'originalPrivateLogsVerified':logs,'exactNativeResponseProofs':19,'allPublicEvidenceHashesVerified':len(q['evidenceFiles']),'nativeSourceIdentity':q['native'],'originalQualifiedComponentReceipt':qualified,'actualCounts':q['counts'],'noAccountOpened':True,'newTestsOrBuilds':0,'scope':'Current local signed-claims snapshot, native related generation/completeness/409 bounds/global unsupported claim and actual denied cold-process persistence. Not peer convergence, Heart projection, Swift related UI adapter, Apple native8ac or UI qualification. Readiness generation is not a lease or future write authorization.'}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'path':str(OUT),'sha256':sha(OUT),'status':receipt['status'],'sourceFiles':len(source),'nativeProofs':19,'logs':8,'newTestsOrBuilds':0}))
