from pathlib import Path
import datetime,hashlib,json,os,subprocess,re
r=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
base=r/'docs/any-engine-port/evidence/20261119'
prior=base/'native-inspector-ui-source-v2.json'
previous=json.loads(prior.read_text(encoding='utf-8'))
paths=list(previous['sources'])
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p:digest(r/p) for p in paths}
swift=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe')
env=os.environ.copy();env['PATH']=str(swift.parent)+os.pathsep+env.get('PATH','')
results=[]
for p in paths:
 x=subprocess.run([str(swift),'-frontend','-parse',str(r/p)],cwd=r,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
 results.append({'path':p,'exitCode':x.returncode,'diagnostics':x.stdout+x.stderr})
after={p:digest(r/p) for p in paths}
ui='NativeApp/UITests/NativeLaunchTests.swift'
preserved=previous['preservedEarlierFourTests'] and before[ui]==previous['sources'][ui]
pin={}
for name in previous['pinnedInspectorSources']:
 files=list((r/'Modules/PinkhaAnyHost/.build/checkouts/TorahInspectorKit').rglob(name));assert len(files)==1,(name,files)
 pin[name]=digest(files[0])
d=subprocess.run(['git','diff','--check','--']+paths,cwd=r,capture_output=True,text=True,encoding='utf-8',timeout=20)
nav=json.loads((base/'native-navigation-components-v3.json').read_text(encoding='utf-8'))
for path,h in nav['sources'].items():
 if path in before:assert before[path]==h
titles={}
for path in ['Anytype/Sources/Pinkha/Torah/UI/AnytypeTorahNotesService.swift','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyTorahPresentationBridge.swift']:
 t=(r/path).read_text(encoding='utf-8');assert 'הערה על \\(selection.relationshipRef)' in t
 titles[path]=digest(r/path)
receipt={'schema':'pinkha-native-inspector-ui-source-v3','createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(x['exitCode']==0 for x in results) and before==after and d.returncode==0 and preserved and pin==previous['pinnedInspectorSources'] else 'FAIL','scope':'Final ten-file Swift parser plus unchanged earlier four UI test bodies, whitespace, pinned Inspector source identity and exact baseline/native Note title rule. No UIKit semantic compile or Apple interaction execution.','sourceStable':before==after,'sources':before,'parse':results,'executedUIKitTests':0,'diffCheck':{'exitCode':d.returncode,'output':d.stdout+d.stderr},'preservedEarlierFourTests':preserved,'preservationProof':{'previousReceipt':str(prior.relative_to(r)).replace('\\','/'),'sha256':digest(prior),'currentUITestFileUnchangedSincePriorProof':before[ui]==previous['sources'][ui]},'uiTestMethods':re.findall(r'func (test\w+)\(', (r/ui).read_text(encoding='utf-8')),'newPureRouteTestCount':nav['testCount'],'routeReceipt':'docs/any-engine-port/evidence/20261119/native-navigation-components-v3.json','pinnedInspectorSources':pin,'pinnedInspectorSourcesUnchanged':pin==previous['pinnedInspectorSources'],'noteTitleRule':{'rule':'הערה על '+r'\(selection.relationshipRef)','sources':titles},'limitations':['Actual five NativeLaunch scenarios and eleven marked-text/focus UIKit methods remain pending Apple execution.','The parser does not semantically validate UIKit/SwiftUI branches.','The separate eight-case receipt exercises production pure planning/owner/presentation policy, not UIKit dismissal.']}
out=base/'native-inspector-ui-source-v3.json';out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
archive=base/'native-inspector-ui-source-v3-artifacts';archive.mkdir(exist_ok=True)
runner=Path(__file__);dest=archive/runner.name;dest.write_bytes(runner.read_bytes())
(archive/'MANIFEST.json').write_text(json.dumps({'receiptSHA256':digest(out),'runner':{'path':str(dest.relative_to(r)).replace('\\','/'),'sha256':digest(dest)}},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'status':receipt['status'],'files':len(paths),'sourceStable':receipt['sourceStable'],'preservedEarlierFourTests':preserved,'pinnedInspectorSourcesUnchanged':receipt['pinnedInspectorSourcesUnchanged'],'receipt':str(out.relative_to(r)).replace('\\','/')},ensure_ascii=False),flush=True)
assert receipt['status']=='PASS',receipt
