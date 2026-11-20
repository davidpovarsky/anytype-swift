from pathlib import Path
import hashlib,json,re,subprocess
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
base=Path(__file__).parent
out=base/'sealed-safe-review'
out.mkdir(exist_ok=False)
h=lambda b:hashlib.sha256(b).hexdigest()
source='c8e648209e9b1eb021c807bd0faf0adf2f816e19'
report=json.loads((base/'initial-log-analysis.json').read_text(encoding='utf-8'))
assert report['sourceCommit']==source and report['caseStartCount']==9 and report['caseOutcomeCount']==9
assert sum(x['outcome']=='passed' for x in report['outcomes'])==8
assert sum(x['outcome']=='failed' for x in report['outcomes'])==1
assert len(report['diagnostics'])==4
assert any('Executed 9 tests, with 4 failures (0 unexpected)' in x['message'] for x in report['testSummaries'])
log=(base/'private-application.log').read_bytes()
assert h(log)==report['logSHA256']
line_list=log.decode('utf-8-sig').splitlines()
joined='\n'.join(x['message'] for x in report['diagnostics'])
tokens=[]
for match in re.finditer(r'\\?"([A-Za-z0-9]{8,20})\\?"',joined):
    token=match.group(1)
    if token not in tokens: tokens.append(token)
redactions={token:'<synthetic-block-'+chr(65+i)+'>' for i,token in enumerate(tokens)}
def clean(value):
    for old,new in redactions.items(): value=value.replace(old,new)
    return value
numbers=sorted({x['line'] for key in ['outcomes','diagnostics','testSummaries'] for x in report[key]})
excerpt='\n'.join(str(number)+': '+clean(line_list[number-1]) for number in numbers)+'\n'
(out/'application-outcomes-and-failure.sanitized.log').write_text(excerpt,encoding='utf-8',newline='\n')
source_paths={
 'c8-NativeDocumentPublicationTests.swift':'Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeDocumentPublicationTests.swift',
 'c8-AnyDocumentPresentation.swift':'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift',
 'c8-NativePropertyWorkflowTests.swift':'Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativePropertyWorkflowTests.swift'
}
source_pins={}
for name,path in source_paths.items():
    result=subprocess.run(['git','show',source+':'+path],cwd=root,capture_output=True,timeout=15)
    assert result.returncode==0
    (out/name).write_bytes(result.stdout)
    source_pins[path]={'safeCopy':name,'gitBlobBytesSHA256':h(result.stdout)}
publication=(out/'c8-NativeDocumentPublicationTests.swift').read_text(encoding='utf-8').splitlines()
assert 'acknowledgedIDs.count, 2' in publication[67]
assert 'insertedID, blockID' in publication[69]
assert 'acknowledgedIDs' in publication[73] and 'acknowledgedIDs' in publication[76]
safe_report=dict(report)
safe_report['diagnostics']=[dict(x,message=clean(x['message'])) for x in report['diagnostics']]
safe_report.update(status='ACTUAL_APPLE_EXECUTED_TEST_FAILURE',testMethodCounts={'executed':9,'passed':8,'failed':1,'skipped':0},
 assertionFailures=4,unexpectedFailures=0,compilerFailure=False,xcresultNamedGateEvaluated=False,
 sourcePins=source_pins,redactedSyntheticIdentifierCount=len(redactions),
 failureScope='One acknowledged document insertion/publication scenario; no timeout or compiler error in this failure.',
 noSourceChanges=True,noRuntimeRerun=True,noFurtherPolling=True)
(out/'application-review.json').write_text(json.dumps(safe_report,indent=2)+'\n',encoding='utf-8')
binding={'schemaVersion':1,'runId':44682744488,'jobId':136109778553,'artifactId':14608726465,
 'sourceCommit':source,'zipSHA256':h((base/'private-application-diagnostic.zip').read_bytes()),
 'closedLogSHA256':h(log),'closedLogBytes':len(log),
 'nativeSourceReceiptSHA256':h((base/'native-source.json').read_bytes()),
 'simulatorReceiptSHA256':h((base/'simulator.json').read_bytes()),
 'sourcePins':source_pins,'rawZipAndLogRetainedPrivatelyOutsideSafeArchive':True}
(out/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
(out/'artifact-inventory.json').write_bytes((base/'artifact-inventory.json').read_bytes())
(out/'seal_safe_application.py').write_bytes(Path(__file__).read_bytes())
files={p.name:{'sha256':h(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
manifest={'schemaVersion':1,'status':'SEALED_SOURCE_BOUND_HOSTED_APPLICATION_DIAGNOSTIC',
 'sourceCommit':source,'runId':44682744488,'jobId':136109778553,'artifactId':14608726465,'files':files,
 'testMethodCounts':{'executed':9,'passed':8,'failed':1,'skipped':0},
 'assertionFailures':4,'unexpectedFailures':0,'xcresultNamedGateEvaluated':False,'rawLogIncluded':False,'noSourceChanges':True}
data=(json.dumps(manifest,indent=2)+'\n').encode()
(out/'MANIFEST.json').write_bytes(data)
print(json.dumps({'directory':str(out),'manifestSHA256':h(data),'files':len(files),
 'sourcePins':source_pins,'safeExcerptSHA256':files['application-outcomes-and-failure.sanitized.log']['sha256'],
 'redactedSyntheticIdentifierCount':len(redactions),'testMethodCounts':manifest['testMethodCounts'],
 'assertionFailures':4,'unexpectedFailures':0}))
