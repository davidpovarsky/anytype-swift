import pathlib,json,hashlib,subprocess,re
f=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-45003378181-failure')
e=f/'inner-0'
w=pathlib.Path(r'C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121')
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122')
assert not out.exists();out.mkdir()
ref='56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793'
path='Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageViewModel.swift'
def git(*a):
 p=subprocess.run(['git','-C',str(w),*a],capture_output=True,timeout=60);p.check_returncode();return p.stdout
b=git('show',ref+':'+path);(out/'EditorPageViewModel.before.swift').write_bytes(b)
lines=b.decode('utf8').splitlines()
source={'ref':ref,'path':path,'blob':git('rev-parse',ref+':'+path).decode().strip(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'lines':len(lines)}
(out/'SOURCE_PROVENANCE.json').write_text(json.dumps(source,indent=2)+'\n',encoding='utf8')
log=(e/'framework-build.stdout.log').read_text(encoding='utf8',errors='replace').splitlines()
actual=[]
for i,line in enumerate(log):
 if re.search(r'\.swift:\d+:\d+: (?:fatal )?error:',line):
  actual.append({'line':i+1,'diagnostic':line,'context':[x if len(x)<1500 else '[long unrelated build command omitted from display; raw log retained]' for x in log[max(0,i-8):i+24]]})
command=json.loads((e/'framework-build.command.json').read_bytes())
execution=json.loads((e/'execution.json').read_bytes())
controls=json.loads((e/'source-controls-result.json').read_bytes())
summary={'source_diagnostics':actual,'command':command,'source_before_after_bytes_equal':(e/'source-before.json').read_bytes()==(e/'source-after.json').read_bytes(),'source_before_sha256':hashlib.sha256((e/'source-before.json').read_bytes()).hexdigest(),'macro_restoration':json.loads((e/'macro-trust/macro-restoration.json').read_bytes()),'execution_keys':list(execution),'execution_status':execution.get('status'),'execution_error':execution.get('error'),'controls_keys':list(controls),'controls_status':controls.get('status'),'controls_summary':controls.get('summary'),'source':source}
(f/'DIAGNOSTIC_DETAIL.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,indent=2))
print('SOURCE_DECLARATION\n'+'\n'.join(f'{i+1}: {v}' for i,v in enumerate(lines[:130])))
print('SOURCE_CONTEXT\n'+'\n'.join(f'{i+1}: {lines[i]}' for i in range(475,min(645,len(lines)))))
