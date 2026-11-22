import pathlib,subprocess,json,hashlib
repo=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121');ref='56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793';out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122')
p=subprocess.run(['git','-C',str(repo),'grep','-n','-E','func undo\\(objectId:',ref,'--','Anytype','Modules'],capture_output=True,timeout=45);assert p.returncode==0
hits=p.stdout.decode('utf8');paths=sorted(set(x.split(':',2)[1] for x in hits.splitlines()));rows=[]
for i,path in enumerate(paths):
 b=subprocess.run(['git','-C',str(repo),'show',ref+':'+path],capture_output=True,timeout=35,check=True).stdout
 blob=subprocess.run(['git','-C',str(repo),'rev-parse',ref+':'+path],capture_output=True,timeout=35,check=True).stdout.decode().strip()
 snapshot='undo-service-'+str(i)+'-'+pathlib.Path(path).name;(out/snapshot).write_bytes(b)
 rows.append({'path':path,'blob':blob,'sha256':hashlib.sha256(b).hexdigest(),'snapshot':snapshot,'declarations':[x for x in b.decode().splitlines() if 'func undo(objectId:' in x]})
summary={'ref':ref,'hits':hits,'rows':rows,'compiled_inputs_changed':False}
(out/'UNDO_SIGNATURE_REFERENCE.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,indent=2))
