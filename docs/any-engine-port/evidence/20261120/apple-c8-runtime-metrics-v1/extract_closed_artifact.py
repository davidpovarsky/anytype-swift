from pathlib import Path
import hashlib,json,re,subprocess,sys,zipfile
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
out=Path(__file__).parent
source='c8e648209e9b1eb021c807bd0faf0adf2f816e19'
producer_path='Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyEmbeddedRuntimeTests.swift'
extractor=root/'build/any-engine-port/runtime-http-metrics-analysis-v1/extract_runtime_metrics.py'
h=lambda b:hashlib.sha256(b).hexdigest()
assert h(extractor.read_bytes())=='000666ec5bf14df36374147507d18202fc76cb9ff9d8fa7c513babc6008042f5'
zip_bytes=(out/'private-lifecycle-diagnostic.zip').read_bytes()
assert h(zip_bytes)=='665d697a2000ed92b5622fa2d54c793c733e40289efcb0d7948ff32e52a237cb'
with zipfile.ZipFile(out/'private-lifecycle-diagnostic.zip') as z:
    assert z.read('source-sha.txt').decode('ascii').strip()==source
    log=z.read('runtime.log')
    assert log==(out/'private-runtime.log').read_bytes()
    native=z.read('native-source.json')
r=subprocess.run(['git','show',source+':'+producer_path],cwd=root,capture_output=True,timeout=15)
assert r.returncode==0
git_source=r.stdout
windows_source=(root/producer_path).read_bytes()
assert h(git_source)=='ef0a7a2b10dbbb7301483937ad8c17110980ed2814d787c29952234db4faca81'
assert h(windows_source)=='39cfc7ba724c407421fc0174b438f93d7807a2c02e986e079d522be982dc8585'
assert windows_source.replace(b'\r\n',b'\n')==git_source
assert git_source.replace(b'\n',b'\r\n')==windows_source
binding={'schemaVersion':1,'runId':44682744488,'jobId':136109778553,'artifactId':14607756181,
 'sourceCommit':source,'producerPath':producer_path,'executedGitProducerSHA256':h(git_source),
 'frozenWindowsProducerSHA256':h(windows_source),'rawBytesEqual':False,
 'exactTransformation':'CRLF_to_LF_only','exactTransformationReproducesGitBlob':True,'inverseReproducesFrozenWindowsBytes':True,
 'zipSHA256':h(zip_bytes),'runtimeLogSHA256':h(log),'runtimeLogBytes':len(log),
 'nativeSourceReceiptSHA256':h(native),'extractorSHA256':h(extractor.read_bytes()),
 'rawLogPrivate':True,'initialRawHashMismatchPreserved':True}
(out/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
(out/'executed-AnyEmbeddedRuntimeTests.swift').write_bytes(git_source)
methods=re.findall(r'func (test[A-Za-z0-9_]+)\(',git_source.decode('utf-8'))
assert len(methods)==3 and len(set(methods))==3
results=[]
for number,line in enumerate(log.decode('utf-8').splitlines(),1):
    if 'Test Case ' not in line: continue
    for name in methods:
        if name not in line: continue
        match=re.search(r'\b(passed|failed|skipped) \(([0-9.]+) seconds\)',line)
        if match: results.append({'line':number,'method':name,'outcome':match.group(1),'durationSeconds':float(match.group(2))})
named={'schemaVersion':1,'scope':'closed_runtime_log_named_method_outcomes_not_xcresult_gate',
 'expectedMethods':methods,'outcomes':results,'exactlyOneResultPerMethod':all(sum(r['method']==name for r in results)==1 for name in methods),
 'allThreePassed':len(results)==3 and all(r['outcome']=='passed' for r in results),
 'logSHA256':h(log),'xcresultGateEvaluated':False,'destinationReceiptEvaluated':False}
(out/'named-runtime-log-outcomes.json').write_text(json.dumps(named,indent=2)+'\n',encoding='utf-8')
command=[sys.executable,str(extractor),'--log',str(out/'private-runtime.log'),'--output-dir',str(out/'safe-metrics'),
 '--source-commit',source,'--run-id','44682744488','--job-id','136109778553']
r=subprocess.run(command,cwd=root,capture_output=True,timeout=25)
(out/'extractor.stdout.log').write_bytes(r.stdout)
(out/'extractor.stderr.log').write_bytes(r.stderr)
analysis_path=out/'safe-metrics/analysis.json'
a=json.loads(analysis_path.read_text(encoding='utf-8')) if analysis_path.exists() else None
receipt={'schemaVersion':1,'extractorExitCode':r.returncode,'extractorBeforeAfterStable':h(extractor.read_bytes())==binding['extractorSHA256'],
 'logBeforeAfterStable':h((out/'private-runtime.log').read_bytes())==binding['runtimeLogSHA256'],
 'analysisSHA256':h(analysis_path.read_bytes()) if analysis_path.exists() else None,
 'analysisStatus':a.get('status') if a else None,'analysisKeys':list(a) if a else None,
 'stdoutBytes':len(r.stdout),'stderrBytes':len(r.stderr),'runtimeRerun':False}
(out/'extraction-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'receipt':receipt,'namedMethods':named}))
