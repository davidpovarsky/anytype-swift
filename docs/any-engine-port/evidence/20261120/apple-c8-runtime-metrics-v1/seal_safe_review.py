from pathlib import Path
import hashlib,json,shutil
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
base=Path(__file__).parent
out=base/'sealed-safe-review'
out.mkdir(exist_ok=False)
items={
 'artifact-inventory.json':base/'artifact-inventory.json',
 'source-binding.json':base/'source-binding.json',
 'named-runtime-log-outcomes.json':base/'named-runtime-log-outcomes.json',
 'producer-binding-initial-failure.json':base/'producer-binding-initial-failure.json',
 'extraction-receipt.json':base/'extraction-receipt.json',
 'interpretation.json':base/'interpretation.json',
 'analysis.json':base/'safe-metrics/analysis.json',
 'events.sanitized.log':base/'safe-metrics/events.sanitized.jsonl',
 'executed-AnyEmbeddedRuntimeTests.swift':base/'executed-AnyEmbeddedRuntimeTests.swift',
 'extract_runtime_metrics.py':root/'build/any-engine-port/runtime-http-metrics-analysis-v1/extract_runtime_metrics.py',
 'extract_closed_artifact.py':base/'extract_closed_artifact.py',
 'inspect_producer_binding.py':base/'inspect_producer_binding.py',
 'seal_safe_review.py':Path(__file__)
}
h=lambda b:hashlib.sha256(b).hexdigest()
files={}
for name,source in items.items():
    data=source.read_bytes()
    (out/name).write_bytes(data)
    assert (out/name).read_bytes()==source.read_bytes()
    files[name]={'sha256':h(data),'bytes':len(data)}
manifest={'schemaVersion':1,'status':'SEALED_SAFE_METADATA_AND_SOURCE_REVIEW','scope':'closed_c8_Runtime_log_and_schema2_metadata_only',
 'sourceCommit':'c8e648209e9b1eb021c807bd0faf0adf2f816e19','runId':44682744488,'jobId':136109778553,'artifactId':14607756181,
 'files':files,'rawZipOrRuntimeLogIncluded':False,'runtimeRerun':False,'productionChanged':False,
 'xcresultGateEvaluated':False,'destinationReceiptEvaluated':False,
 'rawPrivateFilesRetainedOutsideArchive':['private-lifecycle-diagnostic.zip','private-runtime.log']}
data=(json.dumps(manifest,indent=2)+'\n').encode()
(out/'MANIFEST.json').write_bytes(data)
print(json.dumps({'status':manifest['status'],'directory':str(out),'manifestSHA256':h(data),'files':len(files),'bytes':sum(x['bytes'] for x in files.values()),'interpretationSHA256':files['interpretation.json']['sha256'],'namedOutcomesSHA256':files['named-runtime-log-outcomes.json']['sha256'],'analysisSHA256':files['analysis.json']['sha256']}))
