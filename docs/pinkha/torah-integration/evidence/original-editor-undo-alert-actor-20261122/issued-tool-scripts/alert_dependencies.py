import subprocess,pathlib,json,hashlib
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121')
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122')
ref='56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793'
def git(*a):
 p=subprocess.run(['git','-C',str(w),*a],capture_output=True,timeout=45)
 if p.returncode not in [0,1]:p.check_returncode()
 return p
p=git('grep','-n','-E','undoAlertModel|struct AnytypeAlertModel|class AnytypeAlertModel|enum AnytypeAlertModel',ref,'--','Anytype','Modules')
hits=p.stdout.decode('utf8')
paths=sorted(set(x.split(':',2)[1] for x in hits.splitlines()))
paths.append('Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionHandlerProtocol.swift')
rows=[]
for n,path in enumerate(paths):
 data=git('show',ref+':'+path).stdout
 local='dependency-'+str(n)+'-'+pathlib.Path(path).name
 (out/local).write_bytes(data)
 rows.append({'path':path,'blob':git('rev-parse',ref+':'+path).stdout.decode().strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'snapshot':local,'source':data.decode('utf8')})
(out/'ALERT_DEPENDENCIES.json').write_text(json.dumps({'ref':ref,'hits':hits,'rows':rows},indent=2)+'\n',encoding='utf8')
print(json.dumps({'hits':hits,'rows':[dict((k,v) for k,v in x.items() if k!='source') for x in rows]},indent=2))
for x in rows:
 if not x['path'].endswith('/EditorPageViewModel.swift'):
  print('SOURCE '+x['path']+'\n'+x['source'])
