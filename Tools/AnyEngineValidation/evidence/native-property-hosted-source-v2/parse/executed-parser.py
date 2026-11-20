from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,shutil

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
SWIFTC=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe')
SOURCE=APP/'Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativePropertyWorkflowTests.swift'
PREP=APP/'build/any-engine-port/native-property-hosted-source-v2'
OUT=APP/'build/any-engine-port/native-property-hosted-parse-v2'
HELPER=APP/'Tools/AnyEnginePort/run_live_provider_probe.py'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

proof=json.loads((PREP/'source-proof.json').read_text(encoding='utf-8'))
assert sha(SOURCE)==proof['testSHA256']
assert all(sha(APP/p)==entry['sha256'] for p,entry in proof['sourceInputs'].items())
OUT.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('bounded',HELPER);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
shutil.copyfile(__file__,OUT/'executed-parser.py');shutil.copyfile(HELPER,OUT/'executed-process-helper.py')
before={'testSHA256':sha(SOURCE),'sourceInputs':{p:sha(APP/p) for p in proof['sourceInputs']},'swiftcSHA256':sha(SWIFTC),'runnerSHA256':sha(Path(__file__)),'processHelperSHA256':sha(HELPER)}
result={'status':'FAIL','scope':'Swift syntax parsing only for the iOS-conditional source; no semantic compile, link, module/cache emission or native runtime execution','before':before,'startedAtUTC':datetime.now(timezone.utc).isoformat()}
stage=OUT/'run';stage.mkdir()
try:
    # The explicit Apple target makes the #if os(iOS) body active even though
    # this frontend is hosted on Windows. Parsing does not require SDK modules.
    command=[str(SWIFTC),'-frontend','-parse','-target','arm64-apple-ios27.0-simulator',str(SOURCE)]
    result['process']=helper.run_process(command,APP,stage,45)
    process=result['process']
    assert process.get('exitCode')==0 and not process.get('timedOut') and not process.get('cleanupErrors') and not process.get('runnerErrorType')
    warnings=(stage/'stderr.log').read_text(encoding='utf-8').replace('\r\n','\n').splitlines()
    expected=["<unknown>:0: warning: SDK settings were ignored as 'SDKSettings.json' could not be parsed", "<unknown>:0: warning: using sysroot for 'Windows' but targeting 'iPhone'"]
    assert not warnings or warnings==expected
    result['hostPlatformWarnings']=warnings
    result['status']='PASS_SYNTAX_ONLY_WITH_HOST_PLATFORM_WARNINGS' if warnings else 'PASS_SYNTAX_ONLY'
except Exception as error:result['errorType']=type(error).__name__
finally:
    after={'testSHA256':sha(SOURCE),'sourceInputs':{p:sha(APP/p) for p in proof['sourceInputs']},'swiftcSHA256':sha(SWIFTC),'runnerSHA256':sha(Path(__file__)),'processHelperSHA256':sha(HELPER)}
    result['sourceStable']=before==after;result['after']=after
    if not result['sourceStable']:result['status']='FAIL'
    result['finishedAtUTC']=datetime.now(timezone.utc).isoformat();write(OUT/'result.json',result)
print(json.dumps({'status':result['status'],'sourceStable':result['sourceStable'],'result':str(OUT/'result.json'),'resultSHA256':sha(OUT/'result.json'),'exitCode':result.get('process',{}).get('exitCode'),'timedOut':result.get('process',{}).get('timedOut')}))
raise SystemExit(0 if result['status'] in ('PASS_SYNTAX_ONLY','PASS_SYNTAX_ONLY_WITH_HOST_PLATFORM_WARNINGS') else 1)
