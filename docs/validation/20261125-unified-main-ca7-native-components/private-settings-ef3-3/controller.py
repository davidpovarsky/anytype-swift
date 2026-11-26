import pathlib,json,hashlib,subprocess,time,os,shutil,re,signal
p=pathlib.Path(__file__).parent;project=p/'projection';manifest=json.loads((p/'original/source.json').read_text());names=re.findall(r'    func (test[A-Za-z0-9_]+)\(', (project/'Tests/PinkhaKitTests/PinkhaPrivateDirectoryMigrationTests.swift').read_text());assert len(names)==7
argv=['swift','test','--package-path',str(project),'--scratch-path',str(p/'build'),'--disable-sandbox','--jobs','2','--filter','PinkhaPrivateDirectoryMigrationTests'];start=time.time();log=p/'original-swift-test.log';f=log.open('xb');proc=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'));f.close();(p/'active.json').write_text(json.dumps({'pid':proc.pid,'pgid':os.getpgid(proc.pid),'argv':argv,'started':start},indent=2));minimum=shutil.disk_usage(p).free;reason=None
while proc.poll() is None:
 minimum=min(minimum,shutil.disk_usage(p).free)
 if minimum<2*1024**3 or time.time()-start>300:
  reason='owned-resource-or-time-bound';os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=15);break
 time.sleep(1)
rc=proc.wait();text=log.read_text();cases=re.findall(r"Test Case '([^']+)' passed",text);actual=[]
for c in cases:
 actual.append(c.rstrip(']').split()[-1] if c.startswith('-[') else c.split('.')[-1])
unchanged=True
for row,dest in zip(manifest['files'],['Sources/PinkhaKit/PinkhaPrivateDirectoryMigration.swift','Tests/PinkhaKitTests/PinkhaPrivateDirectoryMigrationTests.swift']):unchanged=unchanged and hashlib.sha256((project/dest).read_bytes()).hexdigest()==row['sha256']
status='PASS' if rc==0 and len(actual)==7 and set(actual)==set(names) and unchanged and reason is None and not re.search(r"Test Case '[^']+' (failed|skipped)",text) else 'FAIL'
r={'status':status,'sourceCommit':manifest['commit'],'sourceUnchanged':unchanged,'scope':'actual-macOS-APFS-settings-migration-components-not-app-acceptance','exitCode':rc,'elapsedSeconds':time.time()-start,'passedMethods':actual,'expectedMethods':names,'skippedMethods':0,'originalLogSHA256':hashlib.sha256(log.read_bytes()).hexdigest(),'minimumFreeBytes':minimum,'stopReason':reason,'argv':argv};(p/'receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');assert status=='PASS',r
