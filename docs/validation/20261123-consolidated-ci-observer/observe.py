import pathlib,json,subprocess,datetime,time,gzip,hashlib,os
root=pathlib.Path(__file__).parent
assert not (root/'observer-start.json').exists(),'Existing observer journal: do not duplicate'
targets=json.loads((root/'targets.json').read_text())
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,o):
 temporary=p.with_name(p.name+'.tmp')
 temporary.write_text(json.dumps(o,indent=2)+'\n')
 os.replace(temporary,p)
save(root/'observer-start.json',{'started_at':now(),'pid':os.getpid(),'maximum_seconds':3300,'interval_seconds':120,'targets':targets,'prior_observers_confirmed_stopped':True})
deadline=time.monotonic()+3300;latest={};count=0;reason='TIME_BUDGET';errors=0;api_calls=0
def wait_until(t):
 while time.monotonic()<min(t,deadline) and not (root/'stop-observer').exists():
  time.sleep(min(30,max(0,min(t,deadline)-time.monotonic())))
def call(endpoint):
 global api_calls
 api_calls+=1
 try:
  p=subprocess.run(['gh','api',endpoint],capture_output=True,text=True,timeout=30)
  return p.returncode,p.stdout,p.stderr
 except subprocess.TimeoutExpired as e:
  output=e.stdout or ''
  if isinstance(output,bytes):output=output.decode('utf-8','replace')
  return 124,output,str(e)
while time.monotonic()<deadline and not (root/'stop-observer').exists():
 count+=1;directory=root/('poll-%03d'%count);directory.mkdir()
 code,stdout,stderr=call('repos/davidpovarsky/anytype-swift/actions/runs?per_page=100')
 if isinstance(stdout,bytes):stdout=stdout.decode('utf-8','replace')
 (directory/'api.stderr').write_text(stderr)
 with gzip.open(directory/'original-api-response.json.gz','wb') as f:f.write(stdout.encode())
 save(directory/'request.json',{'observed_at':now(),'returncode':code,'endpoint':'repos/davidpovarsky/anytype-swift/actions/runs?per_page=100','uncompressed_sha256':hashlib.sha256(stdout.encode()).hexdigest()})
 if code:
  errors+=1;backoff=120
  if 'rate limit' in stderr.lower():
   rc,raw,err=call('rate_limit')
   (directory/'rate-limit.json').write_text(raw);(directory/'rate-limit.stderr').write_text(err)
   if rc==0:
    core=json.loads(raw)['resources']['core']
    backoff=max(120,core['reset']-time.time()+5)
   else:backoff=300
  elif '403' in stderr or '401' in stderr:
   reason='API_AUTHORIZATION_FAILED';break
  save(root/'observer-health.json',{'status':'API_ERROR_NO_CI_OUTCOME_INFERRED','observed_at':now(),'consecutive_errors':errors,'next_delay_seconds':backoff,'poll':count,'api_calls':api_calls})
  if errors>=3:reason='REPEATED_API_FAILURE';break
  wait_until(time.monotonic()+backoff);continue
 errors=0
 try:runs={r['id']:r for r in json.loads(stdout)['workflow_runs']}
 except Exception as error:
  save(directory/'parse-failure.json',{'type':type(error).__name__,'message':str(error)});reason='API_SCHEMA_FAILED';break
 states=[];failure=None
 for target in targets:
  r=runs.get(target['id'])
  if r is None:
   # A single exact fallback only if the bounded current-run list omitted this ID.
   rc,raw,err=call('repos/davidpovarsky/anytype-swift/actions/runs/'+str(target['id']))
   (directory/(str(target['id'])+'-fallback.json')).write_text(raw)
   (directory/(str(target['id'])+'-fallback.stderr')).write_text(err)
   if rc:failure='EXACT_RUN_LOOKUP_FAILED';break
   r=json.loads(raw)
  if not (r['id']==target['id'] and r['head_sha']==target['source'] and r['head_branch']==target['branch'] and r['run_attempt']==target['attempt'] and r['event']=='workflow_dispatch'):
   save(directory/(str(target['id'])+'-identity-mismatch.json'),r);failure='RUN_IDENTITY_MISMATCH';break
  state={**target,'status':r['status'],'conclusion':r['conclusion'],'created_at':r['created_at'],'updated_at':r['updated_at'],'url':r['html_url'],'observed_at':now()}
  states.append(state);save(directory/(str(target['id'])+'.json'),r)
  old=latest.get(target['id'])
  if old is None or (old['status'],old['conclusion'])!=(state['status'],state['conclusion']):
   with (root/'transitions.jsonl').open('a') as f:f.write(json.dumps(state)+'\n')
   print(json.dumps({'transition':state}),flush=True)
  if state['status']=='completed':
   terminal=root/('terminal-'+str(target['id'])+'.json')
   if not terminal.exists():save(terminal,r)
  latest[target['id']]=state
 if failure:reason=failure;break
 save(root/'latest.json',{'status':'IDENTITIES_VERIFIED','observed_at':now(),'poll':count,'api_calls':api_calls,'runs':states})
 save(root/'observer-health.json',{'status':'OBSERVING','observed_at':now(),'poll':count,'api_calls':api_calls,'interval_seconds':120})
 if all(s['status']=='completed' for s in states):reason='ALL_TARGETS_TERMINAL';break
 wait_until(time.monotonic()+120)
if (root/'stop-observer').exists():reason='OWNED_OBSERVER_STOP_REQUESTED'
save(root/'observer-end.json',{'ended_at':now(),'reason':reason,'polls':count,'api_calls':api_calls,'latest':list(latest.values())})
print(json.dumps({'observer_end':reason,'api_calls':api_calls,'directory':str(root)}),flush=True)
