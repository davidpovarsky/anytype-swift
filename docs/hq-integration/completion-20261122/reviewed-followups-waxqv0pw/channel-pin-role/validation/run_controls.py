from pathlib import Path
import json,hashlib,base64,zipfile,io,subprocess,datetime,time,os
root=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-native-followups-20261122')
transfer=json.loads((root/'pin-controls-c201.transfer.json').read_text(encoding='utf-8'))
raw=base64.b64decode(transfer['zip_base64'],validate=True)
assert len(raw)==transfer['bytes'] and hashlib.sha256(raw).hexdigest()==transfer['sha256']
out=root/'pin-controls-c201';assert not out.exists();out.mkdir()
(root/'pin-controls-c201.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 for member in z.infolist():
  assert '/' not in member.filename and '\\' not in member.filename
  (out/member.filename).write_bytes(z.read(member))
m=json.loads((out/'INPUTS.json').read_text(encoding='utf-8'))
for f in m['files']:
 assert hashlib.sha256((out/f['name']).read_bytes()).hexdigest()==f['staged_sha256']
swift=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE')
env=os.environ.copy();env['PATH']=str(swift.parent)+os.pathsep+env.get('PATH','')
report={'scope':m['scope'],'patch_sha256':m['patch_sha256'],'archive_sha256':transfer['sha256'],'inputs':m,'compiler_jobs':1,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':[],'native_rpc_calls':0,'apple_native':'NOT_RUN'}
try:
 cmd=[str(swift),'-swift-version','5','-strict-concurrency=complete','-parse-as-library','-j','1','-whole-module-optimization','-Onone']+[str(out/f['name']) for f in m['files']]+['-o',str(out/'p.exe')]
 for label,argv,timeout in [('compile',cmd,180),('execute',[str(out/'p.exe')],45)]:
  t=time.monotonic();p=subprocess.run(argv,env=env,capture_output=True,timeout=timeout)
  result={'label':label,'argv':argv,'exit_code':p.returncode,'duration_s':time.monotonic()-t,'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace')}
  report['results'].append(result)
  (out/'RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  if p.returncode:raise RuntimeError(label+' failed '+str(p.returncode))
 actual=json.loads(report['results'][-1]['stdout'])
 assert actual['executed']==m['expected_controls'] and actual['passed']==m['expected_controls']
 report['status']='PASS_18_NEW_ROLE_CONTROLS'
except BaseException as e:
 report['status']='FAIL';report['error']=type(e).__name__+': '+str(e)
finally:
 report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (out/'RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if report['status'].startswith('FAIL'):raise SystemExit(1)

