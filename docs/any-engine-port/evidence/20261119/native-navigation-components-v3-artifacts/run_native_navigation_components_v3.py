from pathlib import Path
import hashlib,json,subprocess,datetime,os,re,traceback
r=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
work=r/'build/any-engine-port/native-navigation-components-v3';work.mkdir(parents=True,exist_ok=True)
swift=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe')
sdk=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk')
libraries=sdk.parents[1]/'Library'
prod=r/'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentNavigation.swift'
test=r/'Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeDocumentNavigationTests.swift'
driver=work/'Run.swift';driver.write_text('import Testing\n@main struct NavigationComponents {\n static func main() async { await Testing.__swiftPMEntryPoint() as Never }\n}\n',encoding='utf-8',newline='\n')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:p.relative_to(r).as_posix()
source_before={rel(p):digest(p) for p in [prod,test,driver]}
runner=Path(__file__)
expected=re.findall(r'@Test func (\w+)\(',test.read_text(encoding='utf-8'));assert len(expected)==8,expected
common=[str(swift),'-swift-version','6','-parse-as-library','-enable-testing','-I',str(work),'-module-cache-path',str(r/'build/any-engine-port/native-navigation-components-v1/ModuleCache'),'-sdk',str(sdk),'-use-ld=lld','-DSWIFT_PACKAGE','-DDEBUG']
runtime=[]
for family in ['XCTest','Testing']:
 d=libraries/(family+'-6.3.3')/'usr'
 path=d/'lib/swift/windows'
 common+=['-I',str(path),'-I',str(path/'x86_64'),'-L',str(path/'x86_64')]
 runtime.append(d/'bin64')
env=os.environ.copy();env['PATH']=os.pathsep.join([str(swift.parent)]+[str(p) for p in runtime]+[env.get('PATH','')])
results=[];error=None
def run(name,cmd,timeout):
 p=work/(name+'.log')
 with p.open('w',encoding='utf-8',newline='\n') as out:
  x=subprocess.run(cmd,cwd=r,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
 results.append({'name':name,'exitCode':x.returncode,'command':cmd,'log':rel(p),'sha256':digest(p)})
 if x.returncode:raise RuntimeError(name+' exit '+str(x.returncode))
 return p.read_text(encoding='utf-8')
try:
 run('compile',common+['-module-name','PinkhaAnyUI','-whole-module-optimization','-emit-module','-emit-module-path',str(work/'PinkhaAnyUI.swiftmodule'),'-emit-object','-o',str(work/'PinkhaAnyUI.o'),str(prod)],90)
 run('link',common+['-module-name','NativeNavigationComponents',str(driver),str(test),str(work/'PinkhaAnyUI.o'),'-o',str(work/'validation.exe')],90)
 output=run('tests',[str(work/'validation.exe')],45)
 assert all(re.search(r'Test '+re.escape(name)+r'\(\) passed',output) for name in expected),output
 assert re.search(r'Test run with 8 tests in 1 suite passed',output),output
except Exception as e:
 error=str(e)
source_after={rel(p):digest(p) for p in [prod,test,driver]}
evidence={'schema':'pinkha-native-navigation-components-v3','createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if error is None and source_before==source_after else 'FAIL','scope':'Exact production dismissal planner and single-use mounted-owner route state; no UIKit/SwiftUI presentation execution','sourceStable':source_before==source_after,'sources':source_before,'runnerSHA256':digest(runner),'testsExpected':expected,'testCount':8 if error is None else None,'results':results,'error':error,'executableSHA256':digest(work/'validation.exe') if (work/'validation.exe').exists() else None,'UIKitExecuted':False,'usesCachedHostModules':False,'preservedEarlierFailure':'docs/any-engine-port/evidence/20261119/native-navigation-components-v1.json'}
receipt=r/'docs/any-engine-port/evidence/20261119/native-navigation-components-v3.json';receipt.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
archive=receipt.parent/'native-navigation-components-v3-artifacts';archive.mkdir(exist_ok=True)
artifacts=[]
for p in [runner,driver]+[r/x['log'] for x in results]:
 dest=archive/p.name;dest.write_bytes(p.read_bytes());artifacts.append({'path':rel(dest),'sha256':digest(dest)})
(archive/'MANIFEST.json').write_text(json.dumps({'receiptSHA256':digest(receipt),'artifacts':artifacts},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'status':evidence['status'],'receipt':rel(receipt),'sourceStable':evidence['sourceStable'],'testCount':evidence['testCount'],'error':error,'results':[(x['name'],x['exitCode']) for x in results]},ensure_ascii=False))
