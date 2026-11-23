import subprocess,json,hashlib,os,resource,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
w=Path('/mnt/development/projects/worktrees/anytype-otzaria-original-production-20261123')
d=w/'docs/pinkha/torah-integration/original-production-schema-composition-20261123/selected-source-controls'
out=Path('/mnt/development/projects/diagnostics/otzaria-original-production-selected-source-20261123')
out.mkdir(exist_ok=False)
os.chown(out,1001,1002)
source=d/'ActualSelectedSource.swift'
binary=out/'selected-source-controls'
rows=[]
def run(name,argv,timeout=45):
    started=time.time()
    with (d/(name+'.stdout.log')).open('xb') as stdout,(d/(name+'.stderr.log')).open('xb') as stderr:
        p=subprocess.run(['runuser','-u','ubuntu','--',*argv],stdout=stdout,stderr=stderr,timeout=timeout)
    for suffix in ['stdout.log','stderr.log']:os.chown(d/(name+'.'+suffix),1001,1002)
    row={'name':name,'argv':argv,'exit_code':p.returncode,'seconds':round(time.time()-started,6)}
    for suffix in ['stdout.log','stderr.log']:
        data=(d/(name+'.'+suffix)).read_bytes()
        row[suffix]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    rows.append(row)
    return p.returncode
before=hashlib.sha256(source.read_bytes()).hexdigest()
rc=run('compiler-version',['swiftc','--version'])
assert rc==0
rc=run('compile',['swiftc','-swift-version','6','-parse-as-library',str(source),'-o',str(binary)])
if rc==0:
    rc=run('controls',[str(binary)])
for path in ['Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift','OriginalEditorFramework/AnytypeOriginalEditorHost.swift']:
    name='parse-'+Path(path).stem
    prc=run(name,['swiftc','-frontend','-parse',str(w/path)])
    if prc!=0:rc=prc
result={'schema':1,'status':'PASS' if rc==0 else 'FAIL','source_sha256_before':before,'source_sha256_after':hashlib.sha256(source.read_bytes()).hexdigest(),'commands':rows,'native_calls':0,'Apple_UiKit':'NOT_RUN','historical_controls':'NOT_REPLAYED'}
if binary.exists():result['binary']={'path':str(binary),'bytes':binary.stat().st_size,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
if (d/'controls.stdout.log').exists():
    raw=(d/'controls.stdout.log').read_text()
    try:result['controls']=json.loads(raw)
    except json.JSONDecodeError:result['controls']='NO_JSON_RESULT'
(d/'EXECUTION.json').write_text(json.dumps(result,indent=2)+'\n')
os.chown(d/'EXECUTION.json',1001,1002)
print(json.dumps(result,indent=2))
if rc!=0:
    for row in rows:
        if row['exit_code']!=0:print('FAILURE_DIAGNOSTIC '+row['name']+'\n'+(d/(row['name']+'.stderr.log')).read_text()[:18000])
raise SystemExit(rc)
