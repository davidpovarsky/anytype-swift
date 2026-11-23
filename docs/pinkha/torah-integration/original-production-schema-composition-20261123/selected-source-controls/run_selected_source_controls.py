import subprocess,json,hashlib,os,resource,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
w=Path('/mnt/development/projects/worktrees/anytype-otzaria-original-production-20261123')
d=w/'docs/pinkha/torah-integration/original-production-schema-composition-20261123/selected-source-controls'
binary=Path('/mnt/development/projects/diagnostics/otzaria-original-production-selected-source-20261123/selected-source-controls')
assert not binary.exists()
source=d/'ActualSelectedSource.swift'
rows=[]
def run(name,argv,timeout=45):
    started=time.time()
    with (d/(name+'.stdout.log')).open('xb') as stdout,(d/(name+'.stderr.log')).open('xb') as stderr:
        p=subprocess.run(['runuser','-u','ubuntu','--',*argv],stdout=stdout,stderr=stderr,timeout=timeout)
    row={'name':name,'argv':argv,'exit_code':p.returncode,'seconds':round(time.time()-started,6)}
    for suffix in ['stdout.log','stderr.log']:
        path=d/(name+'.'+suffix);os.chown(path,1001,1002);data=path.read_bytes()
        row[suffix]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    rows.append(row)
    return p.returncode
before=hashlib.sha256(source.read_bytes()).hexdigest()
rc=run('compile-closure-corrected',['swiftc','-swift-version','6','-parse-as-library',str(source),'-o',str(binary)])
if rc==0:rc=run('controls',[str(binary)])
result={'schema':1,'status':'PASS' if rc==0 else 'FAIL','source_sha256_before':before,'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),'commands':rows,'native_calls':0,'Apple_UIKit':'NOT_RUN','historical_controls':'NOT_REPLAYED','compiler_version_and_unchanged_product_parses':'REUSED_FIRST_ATTEMPT_EXECUTION_WITH_EXACT_PRODUCT_HASHES','closure_correction':'SELECTION_CORRESPONDENCE.json'}
if binary.exists():result['binary']={'path':str(binary),'bytes':binary.stat().st_size,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
if (d/'controls.stdout.log').exists():
    raw=(d/'controls.stdout.log').read_text()
    try:result['controls']=json.loads(raw)
    except json.JSONDecodeError:result['controls']='NO_JSON_RESULT'
(d/'EXECUTION.json').write_text(json.dumps(result,indent=2)+'\n');os.chown(d/'EXECUTION.json',1001,1002)
print(json.dumps(result,indent=2))
if rc!=0:
    for row in rows:
        if row['exit_code']!=0:print('FAILURE_DIAGNOSTIC '+row['name']+'\n'+(d/(row['name']+'.stderr.log')).read_text()[:18000])
raise SystemExit(rc)
