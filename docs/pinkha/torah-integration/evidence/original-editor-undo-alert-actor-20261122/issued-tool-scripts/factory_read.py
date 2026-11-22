import pathlib,subprocess,json,hashlib
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121');ref='56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793';out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122')
def git(*a):
 p=subprocess.run(['git','-C',str(w),*a],capture_output=True,timeout=50)
 if p.returncode not in [0,1]:p.check_returncode()
 return p.stdout
hits=git('grep','-n','-E','AlertModel|button.action\\(\\)|buttonModel.action|alertModel.buttons',ref,'--','Anytype/Sources/PresentationLayer/Common/Factories','Anytype/Sources/PresentationLayer/TextEditor','Anytype/Sources/PresentationLayer/Flows').decode('utf8')
(out/'ALERT_CALLSITES.txt').write_text(hits,encoding='utf8')
print(hits)
paths=[x for x in git('ls-tree','-r','--name-only',ref,'Anytype/Sources/PresentationLayer/Common/Factories').decode().splitlines() if 'Alert' in pathlib.Path(x).name]
rows=[]
for n,path in enumerate(paths):
 data=git('show',ref+':'+path);blob=git('rev-parse',ref+':'+path).decode().strip();snapshot='factory-'+str(n)+'-'+pathlib.Path(path).name;(out/snapshot).write_bytes(data)
 row={'path':path,'blob':blob,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'snapshot':snapshot};rows.append(row)
 if not path.endswith('/AlertModel.swift'):print('SOURCE '+path+'\n'+data.decode('utf8'))
(out/'ALERT_FACTORY_SOURCES.json').write_text(json.dumps({'ref':ref,'rows':rows},indent=2)+'\n',encoding='utf8')
print(json.dumps(rows,indent=2))
