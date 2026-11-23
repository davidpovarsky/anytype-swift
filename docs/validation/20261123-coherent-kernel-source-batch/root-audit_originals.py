import pathlib, subprocess, json, hashlib, datetime
B=pathlib.Path('/mnt/development/projects')
W=B/'worktrees/anytype-wave15-coherent-kernel-20261123'
D=B/'evidence/coherent-kernel-source-batch-20261123/attempt1'
V=W/'docs/validation/20261123-coherent-kernel-source-batch'
O=B/'diagnostics/coherent-kernel-source-batch-root-review-20261123'
O.mkdir(exist_ok=True)
SHA=lambda x:hashlib.sha256(x).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=W)
assert git('rev-parse','HEAD').decode().strip()=='0976cc8575313ccd0360f7fddbedc27ddacae9' if False else True
head=git('rev-parse','HEAD').decode().strip()
assert head=='0976cc8575313ccd0360f7fddbedc27cbddacae9',head
assert not git('status','--porcelain=v1')
qraw=(V/'qualification.json').read_bytes()
assert SHA(qraw)=='5b24bb7e68e5246c11a707498b58078f8f66f3afa79dcf899695546d7043c6a4'
q=json.loads(qraw);ref=q['sourceCommit']
copies={}
for name,sha in q['originals'].items():
 a=(D/name).read_bytes();c=(V/'attempt1'/name).read_bytes()
 assert a==c and SHA(a)==sha,name
 copies[name]={'bytes':len(a),'sha256':sha}
transport={}
for name,sha in q['transportOriginals'].items():
 raw=(V/'transport'/name).read_bytes();assert SHA(raw)==sha,name
 transport[name]={'bytes':len(raw),'sha256':sha}
before=(D/'source-before.json').read_bytes();after=(D/'source-after.json').read_bytes()
assert before==after
sources=json.loads(before);assert len(sources)==300
names=sorted(sources)
request=b''.join((ref+':'+p+'\n').encode() for p in names)
raw=subprocess.check_output(['git','cat-file','--batch'],cwd=W,input=request,timeout=20)
pos=0;verified={}
for p in names:
 end=raw.index(b'\n',pos);oid,kind,n=raw[pos:end].split();n=int(n);pos=end+1
 val=raw[pos:pos+n];pos+=n;assert raw[pos:pos+1]==b'\n';pos+=1
 m=sources[p]
 assert kind==b'blob' and SHA(val)==m['sha256'] and n==m['bytes']
 assert oid.decode()==m['gitBlobSHA1']
 assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+val).hexdigest()==oid.decode()
 assert (W/p).read_bytes()==val,p
 verified[p]={'sha256':SHA(val),'gitBlobSHA1':oid.decode(),'bytes':n}
assert pos==len(raw)
r=json.loads((D/'result.json').read_bytes())
assert r['passed'] and r['testsRun']==2 and r['errors']==r['failures']==r['skips']==0
assert r['oldControllerMethodsExecuted']==r['AppleMethodsExecuted']==r['newBuilds']==0
loaded=r['loadedRepositoryModules'];assert len(loaded)==9
for p,m in loaded.items():
 assert p in sources and m['sha256']==sources[p]['sha256']==m['gitSHA256']
 assert pathlib.Path(m['modulePath']).resolve()==(W/p).resolve()
intent=json.loads((D/'intent.json').read_bytes());events=json.loads((D/'events.json').read_bytes())
expected=[]
for m in intent['methods']:expected.extend([('START','test_coherent_kernel_sources.'+m),('PASS','test_coherent_kernel_sources.'+m)])
assert [(e['event'],e['method']) for e in events]==expected
log=(D/'controls.log').read_text();assert '\nRan 2 tests in 0.102s\n\nOK\n' in log and 'FAILED' not in log and 'ERROR' not in log
cmd=json.loads((D/'owned-command-originals/new-coherent-command.command.json').read_bytes())
original=(D/'owned-command-originals'/cmd['original_owned_command']).read_bytes()
orig=json.loads(original);obs=cmd['owned_group_quiescence'];k=obs['kernel_group_observation']
assert cmd['original_owned_command_sha256']==SHA(original)
assert cmd['controller_process_id']==orig['worker_pid']==obs['pgid']==k['pgid']==2271599
assert cmd['argv']==orig['argv'] and cmd['cwd']==orig['cwd']
assert cmd['cleanup_profile']=='coherent-heart-release'
assert cmd['status']=='SUCCESS' and orig['status']=='COMPLETE' and cmd['return_code']==orig['return_code']==0
assert orig['owned_group_cleanup']=='TERM_THEN_KILL'
assert obs['status']=='PASS' and obs['absence_source']=='KERNEL_ESRCH' and obs['budget_seconds']==10
assert obs['observations']==obs['live_members']==0 and obs['timeout_observations']==[]
assert k['operation']=='os.killpg' and k['signal']==0 and k['errno']==3 and k['outcome']=='ABSENT_ESRCH'
assert k['before_monotonic']<=k['after_monotonic']<=k['deadline_monotonic']
assert (D/'owned-command-originals/new-coherent-command.log').read_bytes()==b'COHERENT_NEW_SCOPE\n'
review=json.loads((V/'source-review.json').read_bytes());inverse={}
for p,x in review['sourceChanges'].items():
 current=git('show',ref+':'+p);prior=git('show',review['base']+':'+p)
 assert SHA(current)==x['afterSHA256'] and SHA(prior)==x['beforeSHA256']
 assert current.count(x['new'].encode())==1
 assert current.replace(x['new'].encode(),x['old'].encode(),1)==prior
 inverse[p]=x
for p,h in review['newFiles'].items():assert verified[p]['sha256']==h
out={'schemaVersion':1,'status':'INDEPENDENT_ROOT_REVIEW_PASS','reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'qualificationSHA256':SHA(qraw),'reviewedHead':head,'sourceCommit':ref,'sourceInputs':len(sources),
 'sourceBeforeAfterSHA256':SHA(before),'allSourcePhysicalAndFrozenGitMatch':True,'loadedRepositoryModules':loaded,
 'originalCopies':copies,'transportOriginals':transport,'events':events,'actualOwnedCommand':cmd,
 'exactInverseSourceChanges':inverse,'sourceReviewSHA256':SHA((V/'source-review.json').read_bytes()),
 'actualNewMethods':2,'oldControlsRerun':0,'productMethodsRerun':0,'newBuilds':0,
 'scope':'Two newly executed coherent controller controls; exact original kernel helper and unaffected source recovered. Apple/Release acceptance remains NOT_RUN.'}
raw=(json.dumps(out,indent=2,sort_keys=True)+'\n').encode()
(O/'root-review.json').write_bytes(raw)
print(json.dumps({'status':out['status'],'sha256':SHA(raw),'sourceInputs':len(sources),'loadedInputs':len(loaded),'originalCopies':len(copies),'transportOriginals':len(transport),'ownedPID':2271599,'newMethods':2,'reruns':0}))
