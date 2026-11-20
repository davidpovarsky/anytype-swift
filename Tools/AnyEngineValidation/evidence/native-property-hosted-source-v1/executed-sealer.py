from pathlib import Path
import hashlib,json,shutil
APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
PREP=APP/'build/any-engine-port/native-property-hosted-source-v1'
PARSE=APP/'build/any-engine-port/native-property-hosted-parse-v1'
OUT=APP/'Tools/AnyEngineValidation/evidence/native-property-hosted-source-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
proof=load(PREP/'source-proof.json');parse=load(PARSE/'result.json')
assert sha(APP/proof['testPath'])==proof['testSHA256']
assert all(sha(APP/path)==entry['sha256'] for path,entry in proof['sourceInputs'].items())
assert parse['sourceStable'] and parse['process']['exitCode']==0 and not parse['process']['timedOut']
warnings=(PARSE/'run/stderr.log').read_text(encoding='utf-8').replace('\r\n','\n').splitlines()
expected=["<unknown>:0: warning: SDK settings were ignored as 'SDKSettings.json' could not be parsed", "<unknown>:0: warning: using sysroot for 'Windows' but targeting 'iPhone'"]
assert warnings==expected
OUT.mkdir(parents=True,exist_ok=False)
files=[]
for prefix,root in [('source',PREP),('parse',PARSE)]:
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(root)
        assert path.suffix in ('.json','.txt','.py','.log')
        saved=Path(prefix)/rel
        if saved.as_posix()=='parse/run/stdout.json':saved=Path('parse/run/stdout.log')
        target=OUT/saved;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        files.append({'path':saved.as_posix(),'sha256':sha(target),'bytes':target.stat().st_size})
assessment={'status':'PASS_SYNTAX_ONLY_WITH_HOST_PLATFORM_WARNINGS','testPath':proof['testPath'],'testSHA256':proof['testSHA256'],
 'orderedCheckCount':15,'mechanicalExtractionVerified':all(proof['mechanicalComparisons'].values()),
 'rawParserHarnessStatus':parse['status'],'compilerExitCode':0,'sourceStable':True,
 'activeConditionalTarget':'arm64-apple-ios27.0-simulator','warningLines':warnings,
 'interpretation':'The actual frontend parsed the active iOS source and exited0. The raw wrapper FAIL is retained because its blanket empty-stderr assertion rejected two cross-host SDK warnings. This assessment does not claim SDK resolution, Swift semantic checking, linking, or Apple runtime execution.',
 'appleSemanticAndRuntimeStatus':'PENDING','noRerun':True,'files':files}
(OUT/'assessment.json').write_text(json.dumps(assessment,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(__file__,OUT/'executed-sealer.py')
print(json.dumps({'status':assessment['status'],'path':str(OUT),'assessmentSHA256':sha(OUT/'assessment.json'),'testSHA256':proof['testSHA256'],'orderedCheckCount':15,'files':len(files)}))
