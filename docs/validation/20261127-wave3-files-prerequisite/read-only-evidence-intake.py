import pathlib,subprocess,json,hashlib,ast,datetime
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
BASE=pathlib.Path('/var/lib/pinkha-c-filesv2-20261126')
G=['sudo','-n','-u','ubuntu','-g','chatgpt-agent','git','-c','gc.auto=0','-C',str(ROOT)]
SHA='02a5a16ea10f71959fcc733a9e41c7ca56d0219c'
PREFIX='Tools/AnyEngineValidation/native_file_peer_comparison/'
OUT=pathlib.Path('/tmp/pinkha-wave3-files-parent02-evidence-intake.json')
def h(b):return hashlib.sha256(b).hexdigest()
def git(p):return subprocess.check_output(G+['show',SHA+':'+PREFIX+p])
def exact(p,d):
 b=p.read_bytes();assert h(b)==d,(str(p),h(b),d)
 return b
assert not OUT.exists()
result={'sourceCommit':SHA,'timeUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'testsExecuted':0,'nativeAccountStoresOpened':0,'originals':[],'controllers':[]}
for name,digest in [('production-lan-files2','c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692'),('files-crypto-integrity1','99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac')]:
 original=exact(BASE/name/'result.json',digest);assert original==git('receipts/'+name+'.json')
 d=json.loads(original)
 assert not d['errors'] and d['allOwnedGroupsPositivelyAbsent']
 row={'path':str(BASE/name/'result.json'),'sha256':digest,'bytes':len(original),'status':d['status'],'rawLogs':[]}
 if name=='production-lan-files2':
  assert d['status']=='PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES'
  assert len(d['files'])==4 and len(d['coldFiles'])==4 and d['partialCrash']['actualOwnedCrash']
  assert not d['cloudCustodyAccepted'] and not d['wholeSpaceMigrationAccepted']
  assert d['sourcesBefore']==d['sourcesAfter']==d['finalSourceAdmission']
  assert d['nativeBefore']==d['nativeAfter']==d['finalNativeAdmission']
  assert len(d['processes'])==7 and sum(p['intentionalCrash'] for p in d['processes'])==1
  assert all(p['groupPositivelyAbsent'] and not p['forcedKill'] and p['exitCode']==(-9 if p['intentionalCrash'] else 0) for p in d['processes'])
  for log in d['retainedPrivateLogs']:
   raw=exact(BASE/name/'private-logs'/log['name'],log['sha256']);assert len(raw)==log['bytes'];row['rawLogs'].append(log)
  assert git('resume_production_lan_files.py')==exact(BASE/name/'controller.py',d['controllerSHA256'])
  row['actualDeniedAttachmentPOSTAttempts']=1
  row['successfulAttachments']=0
  row['counterClarification']='Original attachmentCalls=0 is preserved, while offlineReaderWriteDenial records one real POST returning403; zero successful attachments does not mean zero attempts.'
  assert d['offlineReaderWriteDenial']['status']==403
  row['nativeInputs']=d['nativeBefore'];row['originalSourceInputs']=d['sourcesBefore']
 else:
  assert d['status']=='PASS_ORIGINAL_NATIVE_CIPHER_CID_INTEGRITY_TESTS_ONLY'
  assert len(d['tests'])==9 and len(d['processes'])==1 and d['sourceBefore']==d['sourceAfter']
  p=d['processes'][0];assert p['exitCode']==0 and p['groupPositivelyAbsent']
  raw=exact(BASE/name/'tests.log',p['logSHA256']);events=[]
  for line in raw.splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  wanted={(x['package'],x['name']) for x in d['tests']}
  assert not any(e.get('Action') in ('fail','skip') for e in events)
  passed=[(e.get('Package'),e.get('Test')) for e in events if e.get('Action')=='pass' and e.get('Test')]
  assert set(passed)==wanted and len(passed)==9
  assert h(git('qualify_files_crypto.py'))==d['controllerSHA256']
  row['rawLogs']=[{'path':str(BASE/name/'tests.log'),'sha256':p['logSHA256'],'bytes':len(raw),'methodsPassed':9,'failedOrSkipped':0}]
  row['originalSourceInputs']=d['sourceBefore']
 result['originals'].append(row)
for p,d in [('production-lan-custody1/result.json','2de21c6aefc8b6b2e79cf831bb8c5ee53c2eafb1454651402584f6cb09a32468'),('production-lan-files1/result.json','eaca0b1c09dccf5930b03e2dd6c580658d4c5ce8ca8f7a7e98bb2a81542763be'),('acl-refresh-native1/result.json','bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380'),('retained-acl-recovery1/result.json','8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d')]:
 b=exact(BASE/p,d);value=json.loads(b);result['originals'].append({'path':str(BASE/p),'sha256':d,'bytes':len(b),'status':value['status']})
manifest=BASE/'acl-refresh-native1/source-manifest.json'
inventory=json.loads(exact(manifest,'44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68'))['files']
root=BASE/'acl-refresh-native1/source'
actual={str(p.relative_to(root)):{'sha256':h(p.read_bytes()),'bytes':p.stat().st_size} for p in root.rglob('*') if p.is_file()}
assert len(actual)==1597 and actual==inventory
exact(BASE/'acl-refresh-native1/any','79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857')
result['actualNativeSourceAndBinaryVerified']=True
for path in subprocess.check_output(G+['diff-tree','--no-commit-id','--name-only','-r',SHA],text=True).splitlines():
 if path.endswith('.py'):
  raw=subprocess.check_output(G+['show',SHA+':'+path]);ast.parse(raw,filename=path)
  result['controllers'].append({'path':path,'sha256':h(raw),'bytes':len(raw),'syntax':'PASS_PARSE_ONLY','executed':False})
result['status']='PASS_ORIGINAL_EVIDENCE_INTAKE_NO_RERUN'
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'path':str(OUT),'sha256':h(OUT.read_bytes()),'status':result['status'],'originals':len(result['originals']),'nativeFiles':len(actual),'actualDeniedAttachmentPOSTAttempts':1,'testsRerun':0}))
