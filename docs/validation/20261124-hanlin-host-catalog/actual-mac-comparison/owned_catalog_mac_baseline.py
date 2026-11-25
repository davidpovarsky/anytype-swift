import pathlib,subprocess,json,hashlib,os,signal,datetime,time,shutil
import xml.etree.ElementTree as ET
root=pathlib.Path('/Users/m1/builds/hanlin-f48bfc6596ee-anytype-catalog');src=root/'host-harness';ev=root/'host-baseline-evidence';manifest=json.loads((root/'source-manifest.json').read_bytes());assert manifest['baselineCommit']=='f48bfc6596eebe491c982bbecbd01939bbce1ed1'
def source_ok():return all(hashlib.sha256((root/'source'/p).read_bytes()).hexdigest()==r['sha256'] for p,r in manifest['baselineFiles'].items()) and all(hashlib.sha256((root/'host-harness'/p).read_bytes()).hexdigest()==h for p,h in json.loads((root/'host-harness-manifest.json').read_text())['files'].items())
def capacity():
 raw=subprocess.check_output(['vm_stat'],text=True);page=int(raw.split('page size of ')[1].split(' bytes')[0]);v={line.split(':',1)[0].strip():int(line.split(':',1)[1].strip().rstrip('.')) for line in raw.splitlines()[1:] if ':' in line};available=sum(v.get(k,0) for k in ['Pages free','Pages inactive','Pages speculative'])*page
 return {'availableAndReclaimableBytes':available,'pageBytes':page,'freePages':v['Pages free'],'inactivePages':v['Pages inactive'],'speculativePages':v['Pages speculative']}
probe_env=dict(os.environ);probe_env['DEVELOPER_DIR']='/Applications/Xcode.app/Contents/Developer'
help_text=subprocess.check_output(['xcrun','swift','test','--help'],env=probe_env,text=True);assert '--verbose' in help_text
toolchain=subprocess.check_output(['xcrun','swift','--version'],env=probe_env,text=True).strip();xcode=subprocess.check_output(['xcodebuild','-version'],env=probe_env,text=True).strip()
expected_pins={'swift-ai-sdk':'e7bf34111e603ca977becd007dd4e5bb109af857','swift-argument-parser':'6a52f3251125d74daf04fcbd5e6f08a75d074382','swiftyjson':'b3dcd7dbd0d488e1a7077cb33b00f2083e382f07','zipfoundation':'02b6abe5f6eef7e3cbd5f247c5cc24e246efcfe0'}
def check_dependencies():
 actual={p['identity']:p['state']['revision'] for p in json.loads((src/'Package.resolved').read_text())['pins']};assert actual==expected_pins
 for name,sha in expected_pins.items():
  checkout=root/'host-build/checkouts'/name
  assert subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()==sha
  assert not subprocess.check_output(['git','-C',str(checkout),'status','--porcelain'],text=True).strip()
 return actual
pins=check_dependencies()
assert source_ok();cap=capacity();assert cap['availableAndReclaimableBytes']>=6*1024**3,cap;assert shutil.disk_usage(root).free>8*1024**3
rows=[]
for line in subprocess.check_output(['ps','-axo','pid=,pgid=,%cpu=,rss=,comm='],text=True).splitlines():
 a=line.split(None,4)
 if len(a)==5 and pathlib.Path(a[4]).name in {'swift-frontend','clang','clang++','ld','ld64.lld','swiftc','xcodebuild','Runner.Worker'}:rows.append({'pid':int(a[0]),'pgid':int(a[1]),'cpu':float(a[2]),'rssKB':int(a[3]),'exe':a[4]})
assert sum(r['cpu'] for r in rows)<600, 'insufficient_cpu_headroom'
scope='HanlinTransientToolCatalogTests';method='restoredCatalogContinuesTheOriginalEmptyToolResult';derived=str(root/'host-build');result=ev/'baseline.xml';cmd=['xcrun','swift','test','--package-path',str(src),'--scratch-path',derived,'--cache-path',str(root/'host-cache'),'--force-resolved-versions','--skip-update','--verbose','-j','1','--disable-xctest','--enable-swift-testing','--no-parallel','--filter',scope,'--xunit-output',str(result)]
receipt={'mode':'LOCAL_MACOS_ENGINE_REGRESSION','phase':'baseline','sourceCommit':manifest['baselineCommit'],'originalProductionCommit':'116cc6be0654a5d11bc56ba00e0310031107ee36','sourceManifestSHA256':hashlib.sha256((root/'source-manifest.json').read_bytes()).hexdigest(),'expectedOriginalMethod':method,'selectedSuite':scope,'appBuilds':0,'simulatorCreations':0,'providerIsMockFetch':True,'command':cmd,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'capacity':cap,'externalAppleActivity':rows,'overlapDeclared':bool(rows),'throughputComparison':False,'capacityObservations':[],'toolchain':toolchain,'xcode':xcode,'dependencyPins':pins,'controllerSHA256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
with (ev/'baseline-launch.json').open('x') as f:json.dump(receipt,f,indent=2)
env=dict(os.environ);env['DEVELOPER_DIR']='/Applications/Xcode.app/Contents/Developer';assert not any(k.startswith('GITHUB_') for k in env);p=None
try:
 with (ev/'baseline.log').open('wb') as output:
  p=subprocess.Popen(cmd,cwd=src,env=env,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True);receipt['pid']=p.pid;receipt['pgid']=os.getpgid(p.pid);(ev/'baseline-active.json').write_text(json.dumps(receipt,indent=2)+'\n');deadline=time.monotonic()+1700;next_check=time.monotonic()+20;low=0
  while p.poll() is None:
   if time.monotonic()>deadline:raise TimeoutError('owned_baseline_1700s')
   if time.monotonic()>=next_check:
    c=capacity();receipt['capacityObservations'].append({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),**c});next_check=time.monotonic()+20;low=low+1 if c['availableAndReclaimableBytes']<1024**3 else 0
    if low>=2:raise RuntimeError('owned_capacity_interruption_after_two_low_memory_observations')
   time.sleep(5)
  receipt['commandExit']=p.returncode
 xml=result.read_text();cases=list(ET.fromstring(xml).iter('testcase'));log=(ev/'baseline.log').read_text(errors='replace');receipt['counts']={'totalTestCount':len(cases),'passedTests':sum(1 for t in cases if t.find('failure') is None and t.find('error') is None and t.find('skipped') is None),'failedTests':sum(1 for t in cases if t.find('failure') is not None or t.find('error') is not None),'skippedTests':sum(1 for t in cases if t.find('skipped') is not None)};receipt['methodCases']=[t.attrib for t in cases];receipt['expectedMethodPresent']=method in xml or (len(cases)==1 and 'A catalog restored after the stop decision still delivers the original empty tool result' in xml);receipt['observedMissingSecondRequest']='observations.requests' in log and '→ 1' in log;receipt['testability']={'unchangedTestableImport': '@testable import HanlinChatCore' in (src/'Tests/HanlinChatCoreTests/HanlinTransientToolCatalogTests.swift').read_text(), 'compilerFlagObserved':any('-module-name HanlinChatCore' in line and '-enable-testing' in line for line in log.splitlines()),'actualOriginalMethodExecuted':receipt['expectedMethodPresent'] and len(cases)==1};receipt['status']='ACTUAL_BASELINE_FAILED_AS_EXPECTED' if receipt['commandExit']!=0 and receipt['counts']=={'totalTestCount':1,'passedTests':0,'failedTests':1,'skippedTests':0} and receipt['expectedMethodPresent'] and receipt['observedMissingSecondRequest'] else 'BASELINE_REQUIRES_REVIEW'
except BaseException as e:receipt['status']='BASELINE_EXECUTION_FAILED';receipt['error']={'type':type(e).__name__,'message':str(e)[:1500]}
finally:
 if p is not None and p.poll() is None:
  assert os.getpgid(p.pid)==p.pid;os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
 receipt['ownedCommandExited']=p is None or p.poll() is not None;receipt['sourceUnchanged']=source_ok();receipt['dependencyPinsAfter']=check_dependencies();receipt['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();(ev/'baseline-result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt.get(k) for k in ['status','commandExit','counts','expectedMethodPresent','sourceUnchanged','ownedCommandExited','finishedAt','error']}))
