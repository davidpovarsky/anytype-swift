#!/usr/bin/env python3
"""Re-run the exact saved prior64 top-level native acceptance tests on frozen v8."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,shutil,subprocess

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
ANY=Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119');SDK=ANY/'.runtime-artifacts/sdk-source'
EVIDENCE=APP/'Tools/AnyEngineValidation/evidence'
OUT=APP/'build/any-engine-port/native-final-v8-go-regression-v2'
BASELINE=EVIDENCE/'native-final-v7-go-regression.json'
BASELINE_SHA='0c80620bd4259aa3b323a4e87500685a307f7f5d5ab2dd707e7d124a1fa6a5ec'
MANIFEST=EVIDENCE/'native-conditional-properties-v8-source.json'
MANIFEST_SHA='484d377a89b3e53ccab28bbf8defe223441e85db398c40ee5626d71ddc521289'
BINARY=ANY/'.runtime-artifacts/any-native-properties-v8.exe'
BINARY_SHA='4856c7214f56dded249095624ea63e3f99b4b340483e8e6f2785163d16a98089'
GO=Path(r'C:\Users\DAVID\go\pkg\mod\golang.org\toolchain@v0.0.1-go1.27.1.windows-amd64\bin\go.exe')
HELPER=APP/'Tools/AnyEnginePort/run_live_provider_probe.py'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def git(root,*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*args],encoding='utf8',timeout=30).strip()
def snapshot(root):
    paths=sorted({p for p in git(root,'ls-files','--cached','--others','--exclude-standard').splitlines() if p.endswith('.go') or p in ('go.mod','go.sum')})
    return {'gitHEAD':git(root,'rev-parse','HEAD'),'files':{p:sha(root/p) for p in paths},'goBinarySHA256':sha(GO)}

def run_suite(selected,helper):
    name=selected['name'];root=SDK if name=='sdk_native_guards' else ANY
    module=re.search(r'^module\s+(\S+)',(root/'go.mod').read_text(encoding='utf8'),re.M).group(1)
    groups=selected['selectedTests'];names=sorted({n for g in groups for n in g['tests']})
    expected={(module+g['package'][1:],n) for g in groups for n in g['tests']}
    assert len(expected)==selected['expectedTopLevelTests']
    stage=OUT/name;stage.mkdir()
    command=[str(GO),'test','-json','-count=1','-p','2','-timeout','240s','-run','^('+'|'.join(names)+')$',*[g['package'] for g in groups]]
    process=helper.run_process(command,root,stage,650)
    write(stage/'process.json',process)
    ran=set();passed=set();failed=set();skipped=set();failed_events=[];diagnostics=0
    for line in (stage/'stdout.json').read_text(encoding='utf-8-sig',errors='replace').splitlines():
        try:e=json.loads(line)
        except json.JSONDecodeError:diagnostics+=1;continue
        test=e.get('Test');identity=(e.get('Package'),test)
        if e.get('Action')=='fail':failed_events.append(identity)
        if not test:continue
        if e.get('Action')=='run':ran.add(identity)
        elif e.get('Action')=='pass':passed.add(identity)
        elif e.get('Action')=='fail':failed.add(identity)
        elif e.get('Action')=='skip':skipped.add(identity)
    missing=expected-passed
    unexpected={x for x in ran if '/' not in x[1]}-expected
    okay=process.get('exitCode')==0 and not process.get('timedOut') and not process.get('cleanupErrors') and not process.get('runnerErrorType') and not missing and not failed_events and not skipped and not unexpected
    result={'name':name,'status':'PASS' if okay else 'FAIL','command':command,'process':process,'selectedTests':groups,
      'expectedTopLevelTests':len(expected),'passedTopLevelTests':len(expected&passed),'passedIncludingSubtests':len(passed),'skippedIncludingSubtests':len(skipped),'failedIncludingSubtests':len(failed),
      'missingPasses':[list(x) for x in sorted(missing)],'unexpectedTopLevelTests':[list(x) for x in sorted(unexpected)],'failedEvents':[list(x) for x in failed_events],
      'rawLogSHA256':sha(stage/'stdout.json'),'stderrSHA256':sha(stage/'stderr.log'),'nonJSONDiagnosticLines':diagnostics}
    write(stage/'suite.json',result)
    print(json.dumps({k:result[k] for k in ('name','status','expectedTopLevelTests','passedTopLevelTests','passedIncludingSubtests','skippedIncludingSubtests','failedIncludingSubtests')}),flush=True)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    result={'status':'FAIL','scope':'The exact prior64 native SDK authority/creation/claims/block/property/HTTP top-level test names, executed once against frozen v8 source. Not a device UI or network-reliability claim.',
      'startedAtUTC':datetime.now(timezone.utc).isoformat(),'suites':[]}
    before=None
    try:
        assert sha(BASELINE)==BASELINE_SHA and sha(MANIFEST)==MANIFEST_SHA and sha(BINARY)==BINARY_SHA
        baseline=json.loads(BASELINE.read_text(encoding='utf8'));assert baseline['status']=='PASS_FINAL_NATIVE_V7_GO_REGRESSION'
        assert sum(s['expectedTopLevelTests'] for s in baseline['suites'])==64
        result.update(baselineReceiptSHA256=BASELINE_SHA,binarySHA256=BINARY_SHA,nativeManifestSHA256=MANIFEST_SHA,harnessSHA256=sha(Path(__file__)),processHelperSHA256=sha(HELPER))
        before={'sdk':snapshot(SDK),'any':snapshot(ANY)}
        build=json.loads((EVIDENCE/'native-conditional-properties-v8-build/result.json').read_text(encoding='utf8'))
        assert build['status']=='PASS' and build['sourceStable'] and before==build['sourceAfter']
        write(OUT/'source-before.json',before)
        shutil.copyfile(__file__,OUT/'executed-runner.py');shutil.copyfile(HELPER,OUT/'executed-process-helper.py')
        selected=[{'name':s['name'],'expectedTopLevelTests':s['expectedTopLevelTests'],'selectedTests':s['selectedTests']} for s in baseline['suites']]
        write(OUT/'selected-prior64-tests.json',selected)
        old_names={n for s in selected for g in s['selectedTests'] for n in g['tests']}
        narrow=[]
        for rel in ('native-conditional-properties-v8-sdk-tests/result.json','native-conditional-properties-v8-server-tests/result.json'):
            d=json.loads((EVIDENCE/rel).read_text(encoding='utf8'));narrow += [n for n in d['testNames'] if '/' not in n]
        result['coverageComparison']={'priorTopLevelNames':64,'coveredByNarrowV8Suites':len(old_names&set(narrow)),'remainingPriorNames':sorted(old_names-set(narrow)),
          'baselineCaseCount':134,'preservedAssertions':'Same64 top-level names; existing HTTP malformed-guard test now adds six required applySeq cases, which remain enabled.'}
        os.environ.update(GOMAXPROCS='2',GOMEMLIMIT='768MiB',GOTOOLCHAIN='go1.27.1',GOCACHE=str(ANY/'.runtime-artifacts/go-build-v8'),GOTMPDIR=str(ANY/'.runtime-artifacts/go-tmp-v8'))
        result['processOnlyEnvironment']={k:os.environ[k] for k in ('GOMAXPROCS','GOMEMLIMIT','GOTOOLCHAIN','GOCACHE','GOTMPDIR')}
        spec=importlib.util.spec_from_file_location('bounded',HELPER);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        for suite in baseline['suites']:
            result['suites'].append(run_suite(suite,helper));write(OUT/'in-progress.json',result)
        result['passedTopLevelTests']=sum(s['passedTopLevelTests'] for s in result['suites'])
        result['passedIncludingSubtests']=sum(s['passedIncludingSubtests'] for s in result['suites'])
        result['skippedIncludingSubtests']=sum(s['skippedIncludingSubtests'] for s in result['suites'])
        if all(s['status']=='PASS' for s in result['suites']) and result['passedTopLevelTests']==64:result['status']='PASS_FINAL_NATIVE_V8_GO_REGRESSION'
    except Exception as error:result['fatalFailureType']=type(error).__name__
    finally:
        after={'sdk':snapshot(SDK),'any':snapshot(ANY)};write(OUT/'source-after.json',after)
        result['sourceStable']=before==after;result['binaryStable']=sha(BINARY)==BINARY_SHA;result['manifestStable']=sha(MANIFEST)==MANIFEST_SHA
        result['harnessStable']=sha(Path(__file__))==result.get('harnessSHA256') and sha(HELPER)==result.get('processHelperSHA256')
        if not all(result[k] for k in ('sourceStable','binaryStable','manifestStable','harnessStable')):result['status']='FAIL'
        result['finishedAtUTC']=datetime.now(timezone.utc).isoformat();write(OUT/'result.json',result)
    print(json.dumps({k:result.get(k) for k in ('status','passedTopLevelTests','passedIncludingSubtests','skippedIncludingSubtests','sourceStable','binaryStable','manifestStable','harnessStable','fatalFailureType')}),flush=True)
    return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
