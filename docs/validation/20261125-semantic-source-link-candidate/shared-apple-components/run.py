from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,time,signal,xml.etree.ElementTree as ET
root=Path('/Users/m1/builds/semantic-sources-20261125/shared-components-2b2a-attempt1')
evidence=root/'evidence'
manifest=json.loads((root/'inputs/semantic-shared-2b2a5611-source.json').read_text())
def verify_source():
    result=[]
    for f in manifest['files']:
        p=root/f['path'];h=hashlib.sha256(p.read_bytes()).hexdigest()
        result.append({'path':f['path'],'sha256':h,'matches':h==f['sha256']})
    return result
before=verify_source()
assert all(x['matches'] for x in before)
assert shutil.disk_usage(root).free>6*1024**3
assert not (evidence/'started.json').exists()
(root/'work/tmp').mkdir()
command=['xcrun','swift','test','--package-path',str(root/'source/Modules/PinkhaTorahPresentation'),
         '--scratch-path',str(root/'work/build'),'--cache-path',str(root/'work/cache'),
         '--force-resolved-versions','--skip-update','--jobs','2','--filter','SharedSemanticSourceLinkTests',
         '--xunit-output',str(evidence/'original.xml')]
env=os.environ|{'TMPDIR':str(root/'work/tmp')+'/',
                'GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}
started=time.time()
(evidence/'toolchain.txt').write_text(subprocess.check_output(['xcrun','swift','--version'],text=True)+
                                     subprocess.check_output(['xcodebuild','-version'],text=True))
(evidence/'source-before.json').write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
with (evidence/'original.log').open('w') as log:
    process=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    assert os.getpgid(process.pid)==process.pid
    (evidence/'started.json').write_text(json.dumps({'schema':'owned-shared-components/v1',
        'source_commit':manifest['source_commit'],'pid':process.pid,'pgid':process.pid,
        'command':command,'started':started,'reserve_bytes':6*1024**3,'max_seconds':1200},sort_keys=True,indent=2)+'\n')
    stop=None
    while process.poll() is None:
        free=shutil.disk_usage(root).free
        (evidence/'state.json').write_text(json.dumps({'pid':process.pid,'free_bytes':free,'elapsed':time.time()-started})+'\n')
        if free<6*1024**3: stop='capacity_reserve'
        if time.time()-started>1200: stop='owned_deadline'
        if stop:
            assert os.getpgid(process.pid)==process.pid
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                assert os.getpgid(process.pid)==process.pid
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
            break
        time.sleep(1)
after=verify_source()
(evidence/'source-after.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
tests=[]
if (evidence/'original.xml').exists():
    tree=ET.parse(evidence/'original.xml')
    for c in tree.iter('testcase'):
        tests.append({'class':c.get('classname'),'name':c.get('name'),
                      'failed':c.find('failure') is not None or c.find('error') is not None,
                      'skipped':c.find('skipped') is not None})
log=(evidence/'original.log').read_text(errors='replace')
dependency=root/'work/build/checkouts/TorahInspectorKit'
dephead=None
if dependency.exists():
    p=subprocess.run(['git','-C',str(dependency),'rev-parse','HEAD'],text=True,capture_output=True)
    if p.returncode==0:dephead=p.stdout.strip()
ps=subprocess.check_output(['ps','-axo','pid,pgid,args'],text=True)
owned=[line for line in ps.splitlines()[1:] if len(line.split(None,2))>=2 and line.split(None,2)[1]==str(process.pid)]
result={'schema':'shared-semantic-source-components/v1','source_commit':manifest['source_commit'],
        'scope':'controlled provider/controller boundary tests; not native engine, UI or device acceptance',
        'returncode':process.returncode,'stop_reason':stop,'tests':tests,'dependency_commit':dephead,
        'source_unchanged':all(x['matches'] for x in after),'owned_process_rows':owned,
        'elapsed_seconds':time.time()-started,'free_bytes':shutil.disk_usage(root).free,
        'log_sha256':hashlib.sha256((evidence/'original.log').read_bytes()).hexdigest()}
result['status']='PASS' if (process.returncode==0 and stop is None and len(tests)==5 and
   all(not x['failed'] and not x['skipped'] for x in tests) and result['source_unchanged'] and
   dephead=='511454e49450cb2581ddf77f644146ff3e30dbef' and not owned) else 'FAIL'
(evidence/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result))
print(log[-16000:])
sys.exit(0 if result['status']=='PASS' else 1)
