import pathlib,subprocess,json,hashlib,difflib
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121');ref='56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793';out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122')
def git(*a):
 p=subprocess.run(['git','-C',str(w),*a],capture_output=True,timeout=50)
 if p.returncode not in [0,1]:p.check_returncode()
 return p.stdout
hits=git('grep','-n','-E','AlertModel|undoAlertModel',ref,'--','Anytype','Modules','OriginalEditorFramework').decode('utf8')
(out/'ALL_ALERT_MODEL_CALLSITES.txt').write_text(hits,encoding='utf8')
print(hits)
paths=['Anytype/Sources/PresentationLayer/TextEditor/Routing/Editor/EditorRouterProtocol.swift','Anytype/Sources/PresentationLayer/TextEditor/Routing/Editor/EditorRouter.swift']
rows=[]
for n,path in enumerate(paths):
 data=git('show',ref+':'+path);snapshot='routing-'+str(n)+'-'+pathlib.Path(path).name;(out/snapshot).write_bytes(data)
 row={'path':path,'blob':git('rev-parse',ref+':'+path).decode().strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'snapshot':snapshot};rows.append(row)
 print('SOURCE '+path+'\n'+data.decode('utf8'))
path='Anytype/Sources/PresentationLayer/Common/Factories/AlertModel.swift';before=(out/'dependency-0-AlertModel.swift').read_bytes();assert hashlib.sha256(before).hexdigest()=='7944356e1b56bbd22fb08e7bc20b4bf2e966acdb1844e87ca569628ce40a8421'
text=before.decode();assert text.count('let action: @Sendable () -> Void')==1 and text.count('undoAction: @escaping @Sendable () -> Void')==1
candidate=text.replace('let action: @Sendable () -> Void','let action: @MainActor @Sendable () -> Void').replace('undoAction: @escaping @Sendable () -> Void','undoAction: @escaping @MainActor @Sendable () -> Void')
(out/'AlertModel.candidate.swift').write_bytes(candidate.encode())
patch=''.join(difflib.unified_diff(text.splitlines(keepends=True),candidate.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
(out/'ALERT_CALLBACK_ACTOR.patch').write_bytes(patch.encode())
provenance={'ref':ref,'path':path,'before_sha256':hashlib.sha256(before).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'product_apply':False,'routing_sources':rows,'changes':'Two @MainActor function-type annotations only; bodies, scheduler, imports, UIKit presentation, legacy behavior unchanged.'}
(out/'CANDIDATE_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf8')
print('PATCH\n'+patch)
print(json.dumps(provenance,indent=2))
