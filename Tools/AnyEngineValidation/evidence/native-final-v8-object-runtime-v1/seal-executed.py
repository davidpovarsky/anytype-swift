from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, shutil, sys

APP = Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
ANY = Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119')
OUT = APP/'build/any-engine-port/native-final-v8-object-runtime-v1'
DEST = APP/'Tools/AnyEngineValidation/evidence/native-final-v8-object-runtime-v1'
PROP = APP/'build/any-engine-port/native-v8-property15-v1'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

raw = json.loads((OUT/'native-runtime-result.json').read_text(encoding='utf-8'))
wrapper = json.loads((OUT/'result.json').read_text(encoding='utf-8'))
assert raw['status'] == 'FAIL'
assert len(raw['checks']) == 14 and all(x['status']=='PASS' for x in raw['checks'][:13])
assert raw['checks'][-1]['name'] == 'scoped_watch_reports_cross_peer_native_append'
assert raw['checks'][-1]['error'] == 'ContractFailure: HTTP 400: dataset.validation'
assert len(raw['firewallRules']) == 2 and all(x['activeVerified'] and x['removalVerified'] for x in raw['firewallRules'])
assert wrapper['independentOwnedCleanup']['remainingOwnedRules'] == 0
assert wrapper['independentOwnedCleanup']['remainingOwnedProcesses'] == 0
sys.path.insert(0, str(OUT/'harness'))
spec = importlib.util.spec_from_file_location('native_frozen_v8', OUT/'harness/run_native_validation.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
after = {'any': helper.source_manifest(ANY), 'sdk': helper.source_manifest(ANY/'.runtime-artifacts/sdk-source')}
assert after['any'] == raw['anySource'] and after['sdk'] == raw['sdkSource']
DEST.mkdir(parents=True, exist_ok=False)
names = ['executed-process-helper.py','executed-wrapper.py','native-runtime-result.json','prepared.json','process.json','provenance-only.diff','result.json','harness/run_native_object_validation.py','harness/run_native_validation.py','harness/run_runtime_validation.py','harness/source-pins.json','run/stdout.json','run/stderr.log']
for name in names:
    target=DEST/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(OUT/name,target)
write(DEST/'source-after-failure.json',after)
analysis = {'status':'FAIL_PRESERVED','checksPassed':13,'checksFailed':1,'checksNotExecuted':2,
 'failure':raw['checks'][-1],'sourceStableAfterFailure':True,
 'nativeBinarySHA256':wrapper['nativeBinarySHA256'],'nativeManifestSHA256':wrapper['nativeManifestSHA256'],
 'independentOwnedCleanup':wrapper['independentOwnedCleanup'],
 'diagnosis':'Inference from executed ordering: peer A restores bin eligibility and immediately invokes peer B append without waiting for peer B eligibility convergence. Saved HTTP error does not contain detailed native rejection; causality is not proven.',
 'followup':'One bounded native eligibility convergence barrier before a single business append in a fresh v9 run; no retry of this failed Space.',
 'rawReceiptsUnmodified':True,'privateLogsOrCredentialsArchived':False,
 'capturedAtUTC':datetime.now(timezone.utc).isoformat()}
write(DEST/'analysis.json', analysis)
shutil.copyfile(__file__,DEST/'seal-executed.py')
manifest={str(p.relative_to(DEST)).replace('\\','/'):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file()}
write(DEST/'archive.json',{'scope':'Immutable failed exact-v8 peer16 attempt, 13 pass / 1 fail / 2 not executed','files':manifest})

# Preserve exact failed public wire source before any v9 edit. No SDK source changes.
build=json.loads((APP/'Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-build/result.json').read_text(encoding='utf-8'))
nativefiles=['internal/api/properties.go','internal/api/modify.go','internal/server/handlers_common.go','internal/server/pinkha_property_condition.go']
source={}
for name in nativefiles:
    path=ANY/name; actual=sha(path); assert actual==build['sourceAfter']['any']['files'][name]
    target=PROP/'native-source'/name; target.parent.mkdir(parents=True,exist_ok=True); assert not target.exists(); shutil.copyfile(path,target); source[name]=actual
write(PROP/'native-source/manifest.json',{'scope':'Exact immutable v8 failed HTTP response source before v9 edit','files':source})

# Metadata-only projection from the owned existing Info logs. Never archive raw logs.
private=ANY/'.runtime-artifacts/peer-native-v8-guarded-hierarchy-v2'
rows=[]; logs=[]
for path in (private/'stdout.private.log',private/'stderr.private.log'):
    data=path.read_bytes()
    logs.append({'path':str(path),'bytesRead':len(data),'readSnapshotSHA256':hashlib.sha256(data).hexdigest(),'rawContentArchived':False})
    for line in data.decode('utf-8',errors='replace').splitlines():
        try: value=json.loads(line)
        except (ValueError,TypeError): continue
        if not isinstance(value,dict) or value.get('logger')!='http' or value.get('msg')!='http':continue
        try: stamp=datetime.fromisoformat(value['ts']).astimezone(timezone.utc)
        except (ValueError,TypeError,KeyError):continue
        if datetime(2026,11,20,4,27,15,tzinfo=timezone.utc)<=stamp<=datetime(2026,11,20,4,27,30,tzinfo=timezone.utc):
            rows.append({key:value.get(key) for key in ('method','path','status','duration','ts')})
rows.sort(key=lambda x:x['ts'])
meta={'scope':'Metadata-only completed HTTP requests around first immutable v8 property15 failure; no network request performed by this extraction','capturedAtUTC':datetime.now(timezone.utc).isoformat(),'nativeSourceFiles':source,'sourceLogs':logs,'allowedFields':['method','path','status','duration','ts'],'rows':rows}
assert not (PROP/'native-http-metadata.json').exists()
write(PROP/'native-http-metadata.json',meta)
print(json.dumps({'status':'SEALED','archive':str(DEST),'archiveSHA256':sha(DEST/'archive.json'),'analysisSHA256':sha(DEST/'analysis.json'),'provenanceDiffSHA256':sha(DEST/'provenance-only.diff'),'sourceStable':True,'checksPassed':13,'checksFailed':1,'checksNotExecuted':2,'propertyMetadataPath':str(PROP/'native-http-metadata.json'),'propertyMetadataSHA256':sha(PROP/'native-http-metadata.json'),'propertyMetadataRows':len(rows)}))
