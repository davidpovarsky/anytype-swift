"""Bounded source-bound native Go tests; preserve actual JSON events, zero skips."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
GO=Path(r'C:\Users\DAVID\go\pkg\mod\golang.org\toolchain@v0.0.1-go1.27.1.windows-amd64\bin\go.exe')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(root):
    command=['git','--no-optional-locks','-C',str(root)]
    paths=subprocess.check_output(command+['ls-files','--cached','--others','--exclude-standard'],encoding='utf8',timeout=20).splitlines()
    paths=sorted({p for p in paths if p.endswith('.go') or p in ('go.mod','go.sum')})
    return {'gitHEAD':subprocess.check_output(command+['rev-parse','HEAD'],encoding='utf8',timeout=20).strip(),
            'files':{p:sha(root/p) for p in paths},'goBinarySHA256':sha(GO)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--run',required=True)
    parser.add_argument('--packages',nargs='+',required=True);parser.add_argument('--timeout',type=int,default=240)
    args=parser.parse_args();root=args.root.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    helper_path=APP/'Tools/AnyEnginePort/run_live_provider_probe.py'
    spec=importlib.util.spec_from_file_location('bounded',helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    before=snapshot(root);helper.write_json(out/'source-before.json',before)
    shutil.copyfile(__file__,out/'executed-runner.py');shutil.copyfile(helper_path,out/'executed-process-helper.py')
    result={'status':'FAIL','scope':'actual_native_go_tests_no_skip','sourceRoot':str(root),'selector':args.run,'packages':args.packages,
            'runnerSHA256':sha(Path(__file__)),'processHelperSHA256':sha(helper_path)}
    os.environ['GOMAXPROCS']='2';os.environ['GOMEMLIMIT']='768MiB';os.environ['GOTOOLCHAIN']='go1.27.1'
    cache=Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119\.runtime-artifacts\go-build-v8');temporary=cache.parent/'go-tmp-v8'
    cache.mkdir(parents=True,exist_ok=True);temporary.mkdir(parents=True,exist_ok=True)
    os.environ['GOCACHE']=str(cache);os.environ['GOTMPDIR']=str(temporary)
    result['processOnlyEnvironment']={k:os.environ[k] for k in ('GOMAXPROCS','GOMEMLIMIT','GOTOOLCHAIN','GOCACHE','GOTMPDIR')}
    environment=subprocess.run([str(GO),'env','-json','GOROOT','GOTOOLDIR','GOCACHE','GOTMPDIR','GOOS','GOARCH','GOVERSION'],cwd=root,capture_output=True,text=True,timeout=20)
    result['goEnvironmentExitCode']=environment.returncode
    if environment.returncode==0:result['actualGoEnvironment']=json.loads(environment.stdout)
    stage=out/'run';stage.mkdir()
    try:
        command=[str(GO),'test','-json','-count=1','-p=2','-timeout='+str(max(30,args.timeout-20))+'s','-run',args.run]+args.packages
        result['process']=helper.run_process(command,root,stage,args.timeout)
        events=[]
        for line in (stage/'stdout.json').read_text(encoding='utf8',errors='strict').splitlines():
            if line.strip():events.append(json.loads(line))
        tested=[e for e in events if e.get('Test') and e.get('Action')=='run']
        passed=[e for e in events if e.get('Test') and e.get('Action')=='pass']
        failed=[e for e in events if e.get('Action')=='fail']
        skipped=[e for e in events if e.get('Action')=='skip']
        result.update(topLevelTests=sum('/' not in e['Test'] for e in tested),testCases=len(tested),passedCases=len(passed),failedEvents=len(failed),skippedEvents=len(skipped),
                      testNames=[e['Test'] for e in tested],jsonEventLogSHA256=sha(stage/'stdout.json'),stderrSHA256=sha(stage/'stderr.log'))
        if not tested or len(passed)!=len(tested) or failed or skipped:raise RuntimeError('actual_native_tests_incomplete_or_failed')
        p=result['process']
        if p.get('exitCode')!=0 or p.get('timedOut') or p.get('cleanupErrors') or p.get('runnerErrorType'):raise RuntimeError('actual_native_go_process_failed')
        result['status']='PASS'
    except Exception as error:
        result['errorType']=type(error).__name__
        if type(error) is RuntimeError:result['errorCode']=str(error)
    finally:
        after=snapshot(root);helper.write_json(out/'source-after.json',after)
        result['sourceStable']=before==after
        result['runnerStable']=sha(Path(__file__))==result['runnerSHA256'] and sha(helper_path)==result['processHelperSHA256']
        if not result['sourceStable'] or not result['runnerStable']:result['status']='FAIL'
        helper.write_json(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ('status','topLevelTests','testCases','passedCases','failedEvents','skippedEvents','sourceStable','errorType','errorCode') if k in result}))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
