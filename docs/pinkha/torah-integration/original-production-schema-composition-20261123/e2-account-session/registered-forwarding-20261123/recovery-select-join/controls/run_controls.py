from pathlib import Path
import subprocess,os,signal,hashlib,json,time,datetime
root=Path(__file__).resolve().parent
owner=root.parents[1]/'controls'
wt=Path('/mnt/development/projects/worktrees/anytype-otzaria-original-production-20261123')
out=root/'attempt-1'
out.mkdir(exist_ok=False)
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def run(name,args,limit):
    start=time.monotonic()
    with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
        child=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True)
        timeout=False
        try: child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timeout=True
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    try:os.killpg(child.pid,0);drained=False
    except ProcessLookupError:drained=True
    rec={'name':name,'argv':args,'exit':child.returncode,'timed_out':timeout,'child_reaped':True,'owned_group_drained':drained,'elapsed_seconds':time.monotonic()-start}
    for stream in ['stdout','stderr']:
        b=(out/(name+'.'+stream)).read_bytes();rec[stream]={'bytes':len(b),'sha256':sha(b)}
    commands.append(rec)
    (out/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
    if timeout or not drained or child.returncode:raise RuntimeError('command failed: '+name)
    return (out/(name+'.stdout')).read_text()
result={'status':'FAIL','scope':'Foundation exact-source control only; original surrounding native/Factory/bootstrap services are explicit doubles; no Combine, UIKit, native middleware, Apple or account-runtime credit','passed':[]}
try:
    union=json.loads((root.parents[1]/'FINAL_SOURCE_UNION.json').read_text())
    for row in union['rows']:
        b=(wt/row['path']).read_bytes()
        assert sha(b)==row['after_sha256']
    extraction=json.loads((root/'EXTRACTION.json').read_text())
    inputs=[]
    for name in [owner/'ExactSource.swift',root/'BoundaryDoubles.swift',root/'ExactRecoveryJoinControls.swift',root/'EXTRACTION.json']:
        b=name.read_bytes();inputs.append({'path':str(name),'bytes':len(b),'sha256':sha(b)})
    (out/'INPUTS.json').write_text(json.dumps({'source':union,'compiled_inputs':inputs},indent=2)+'\n')
    run('whole-source-syntax',['/usr/local/bin/swiftc','-frontend','-parse',*[str(wt/r['path']) for r in json.loads((root.parent/'SOURCE_MAP.json').read_text())['rows']]],60)
    run('swift-version',['/usr/local/bin/swiftc','--version'],10)
    run('portable-compile',['/usr/local/bin/swiftc','-swift-version','6','-parse-as-library',str(owner/'ExactSource.swift'),str(root/'BoundaryDoubles.swift'),str(root/'ExactRecoveryJoinControls.swift'),'-o',str(out/'controls')],90)
    stdout=run('portable-controls',[str(out/'controls')],90)
    record=[x.removeprefix('RESULT_JSON ') for x in stdout.splitlines() if x.startswith('RESULT_JSON ')]
    assert len(record)==1
    actual=json.loads(record[0]);assert actual['status']=='PASS' and actual['controls']==6 and len(set(actual['passed']))==6
    result.update(actual)
    result['binary_sha256']=sha((out/'controls').read_bytes())
except Exception as e:
    result['error']=str(e)
finally:
    result['commands']=commands
    result['recorded_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    print('RESULT_SHA256',sha((out/'RESULT.json').read_bytes()))
if result['status']!='PASS':raise SystemExit(1)
