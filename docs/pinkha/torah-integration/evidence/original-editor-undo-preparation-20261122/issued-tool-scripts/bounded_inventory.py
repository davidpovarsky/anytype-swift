import pathlib,subprocess,json,hashlib
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121')
h='925b7e3cc687dcccad7703f57bd0a6b374dc1919'
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-undo-inference-compile-20261122')
targets=[
'Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettingsMenu/ObjectSettingsMenuView.swift',
'Anytype/Sources/PresentationLayer/Modules/PublishToWeb/PublishToWebInternalView.swift',
'Modules/DesignKit/Sources/DesignKit/Components/AsyncButton/AsyncStandardButton.swift',
'Modules/DesignKit/Sources/DesignKit/Components/BottomAlert/BottomAlertButtonView.swift',
'Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectSettings/Alerts/ObjectSettingsResolveConflictAlert.swift']
rows=[]
for i,path in enumerate(targets):
 r=subprocess.run(['git','-C',str(w),'show',h+':'+path],capture_output=True,timeout=90);assert r.returncode==0,r.stderr.decode('utf8','replace')
 data=r.stdout
 name=f'PREPARATION_SITE_{i}.swift';assert not (out/name).exists();(out/name).write_bytes(data)
 row={'path':path,'snapshot':name,'source_head':h,'sha256':hashlib.sha256(data).hexdigest(),'content':data.decode('utf8')};rows.append(row);print(json.dumps(row))
(out/'BOUNDED_PREPARATION_INVENTORY.json').write_text(json.dumps([{k:v for k,v in row.items() if k!='content'} for row in rows],indent=2),encoding='utf8')
