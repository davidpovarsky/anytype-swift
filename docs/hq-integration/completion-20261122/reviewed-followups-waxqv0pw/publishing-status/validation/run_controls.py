from pathlib import Path
import json,hashlib,base64,zipfile,io,subprocess,datetime,time,os,shutil

root=Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-native-followups-20261122')
transfer=json.loads((root/'publishing-controls-bae494-r2.transfer.json').read_text(encoding='utf-8'))
raw=base64.b64decode(transfer['zip_base64'],validate=True)
assert len(raw)==transfer['bytes'] and hashlib.sha256(raw).hexdigest()==transfer['sha256']
out=root/'publishing-controls-bae494-r2';assert not out.exists();out.mkdir()
(root/'publishing-controls-bae494-r2.zip').write_bytes(raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
    for member in z.infolist():
        assert '/' not in member.filename and '\\' not in member.filename
        (out/member.filename).write_bytes(z.read(member))
m=json.loads((out/'INPUTS.json').read_text(encoding='utf-8'))
for f in m['files']:
    assert hashlib.sha256((out/f['name']).read_bytes()).hexdigest()==f['staged_sha256']
swift=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE')
runtime=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin')
cache=Path(r'C:\Users\DAVID\Code\Maktabah-peek-overflow-20261121\build\anytype-snapshot-codec-draft\portable-real-types\codec\.build\x86_64-unknown-windows-msvc\debug')
assert (cache/'Modules/SwiftProtobuf.swiftmodule').is_file()
objects=sorted((cache/'SwiftProtobuf.build').glob('*.o'))+[cache/'Modules/SwiftProtobuf.o']
assert len(objects)>10 and all(p.is_file() for p in objects)
link_inputs=out/'objects';link_inputs.mkdir()
cached=[]
for index,original in enumerate(objects):
    target=link_inputs/f'sp{index:03}.o'
    shutil.copyfile(original,target)
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest()==original_hash
    cached.append({'original':str(original),'copy':str(target),'sha256':original_hash,'bytes':original.stat().st_size})
# Short copied object names avoid the Windows command-line/path limit. Existing
# dependency inputs remain untouched and no SwiftPM/dependency build is invoked.
rsp=out/'objects.rsp'
rsp.write_text('\n'.join('"'+x['copy']+'"' for x in cached)+'\n',encoding='utf-8')
env=os.environ.copy();env['PATH']=str(swift.parent)+os.pathsep+str(runtime)+os.pathsep+env.get('PATH','')
report={'scope':m['scope'],'source_patch':m['source_patch'],'archive_sha256':transfer['sha256'],'inputs':m,
        'compiler_jobs':1,'dependency_builds':0,'cached_dependency_objects':cached,
        'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':[],
        'native_lib_calls':0,'publishing_network_calls':0,'apple_native':'NOT_RUN'}
try:
    cmd=[str(swift),'-swift-version','5','-strict-concurrency=complete','-parse-as-library','-j','1',
         '-whole-module-optimization','-Onone','-I',str(cache/'Modules'),'-module-name','PublishingStatusQualification']
    cmd += [str(out/f['name']) for f in m['files']] + ['@'+str(rsp),'-o',str(out/'p.exe')]
    for label,argv,timeout in [('compile',cmd,180),('execute',[str(out/'p.exe')],45)]:
        t=time.monotonic();p=subprocess.run(argv,env=env,capture_output=True,timeout=timeout)
        result={'label':label,'argv':argv,'exit_code':p.returncode,'duration_s':time.monotonic()-t,
                'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace')}
        report['results'].append(result)
        (out/'RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        if p.returncode:raise RuntimeError(label+' failed '+str(p.returncode))
    actual=json.loads(report['results'][-1]['stdout'])
    assert actual['executed']==m['expected_controls'] and actual['passed']==m['expected_controls']
    report['status']='PASS_14_NEW_PUBLISHING_CONTROLS'
except BaseException as e:
    report['status']='FAIL';report['error']=type(e).__name__+': '+str(e)
finally:
    report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/'RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'checkpoint':str(out),'source_patch':report['source_patch'],
                  'compiler_jobs':1,'cached_object_count':len(cached),'dependency_builds':0,
                  'results':report['results'],'error':report.get('error')}))
if report['status'].startswith('FAIL'):raise SystemExit(1)
