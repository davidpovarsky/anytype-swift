from pathlib import Path
import json,hashlib,subprocess
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
p='Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyEmbeddedRuntimeTests.swift'
r=subprocess.run(['git','show','c8e648209e9b1eb021c807bd0faf0adf2f816e19:'+p],cwd=root,capture_output=True,timeout=15)
assert r.returncode==0
b=r.stdout
c=(root/p).read_bytes()
h=lambda v:hashlib.sha256(v).hexdigest()
x={'gitSHA256':h(b),'workingFileSHA256':h(c),'gitCRLFCount':b.count(b'\r\n'),'gitLFCount':b.count(b'\n'),'workingCRLFCount':c.count(b'\r\n'),'workingLFCount':c.count(b'\n'),'bytesEqual':b==c,'equalAfterOnlyCRLFToLF':b.replace(b'\r\n',b'\n')==c.replace(b'\r\n',b'\n'),'gitConvertedToCRLFSHA256':h(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))}
(root/'build/any-engine-port/apple-c8-runtime-metrics-job136109778553-v1/producer-binding-initial-failure.json').write_text(json.dumps({'status':'FAILED_PRE_EXTRACTION_EXPECTED_RAW_HASH','extractorExecuted':False,'expectedWindowsProducerSHA256':'39cfc7ba724c407421fc0174b438f93d7807a2c02e986e079d522be982dc8585','observed':x},indent=2)+'\n',encoding='utf-8')
print(json.dumps(x))
