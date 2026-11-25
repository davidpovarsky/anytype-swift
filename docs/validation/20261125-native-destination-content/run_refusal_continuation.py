import pathlib,json,subprocess,socket,hashlib,time,os,signal
root=pathlib.Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
e=pathlib.Path('/mnt/development/projects/evidence/migration-final-20261125/native-destination-content/native-attempt2')
stage='refusal-attempt1';remote='/Users/m1/builds/pinkha-c-destination-content-20261125/refusal-continuation'
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','scaleway-mac','python3','-']
def remote_run(code):
 p=subprocess.run(ssh,input=code,text=True,capture_output=True,timeout=30)
 assert p.returncode==0,p.stderr[-500:]
 return p.stdout
deadline=time.monotonic()+60
while True:
 try:
  runtime=json.loads(remote_run("from pathlib import Path\nprint(Path("+repr(remote+'/runtime.json')+").read_text())\n"));break
 except Exception:
  assert time.monotonic()<deadline,'no continuation runtime';time.sleep(.5)
(e/'runtime-refusal-original.json').write_text(json.dumps(runtime,indent=2)+'\n')
port=int(runtime['baseURL'].rsplit(':',1)[1])
with socket.socket() as s:s.bind(('127.0.0.1',0));local=s.getsockname()[1]
cmd=['ssh','-N','-L','127.0.0.1:'+str(local)+':127.0.0.1:'+str(port),'-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','scaleway-mac']
(e/(stage+'-forward-command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
forwardlog=(e/(stage+'-forward.log')).open('wb')
forward=subprocess.Popen(cmd,stdout=forwardlog,stderr=subprocess.STDOUT,start_new_session=True)
result={'scope':'real retained native changed-content refusal','result':'RUNNING','forwardPID':forward.pid}
started=time.monotonic()
try:
 deadline=time.monotonic()+20
 while True:
  assert forward.poll() is None,'forward ended'
  try:socket.create_connection(('127.0.0.1',local),timeout=.3).close();break
  except OSError:assert time.monotonic()<deadline;time.sleep(.2)
 runtime['baseURL']='http://127.0.0.1:'+str(local)
 fixture=e/(stage+'-runtime.json');fixture.write_text(json.dumps(runtime,indent=2)+'\n')
 sources=json.loads((e/'reopen-attempt1-source.json').read_text())
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert all(sha(root/k)==v for k,v in sources.items()),'source changed before refusal'
 (e/(stage+'-source.json')).write_text(json.dumps(sources,indent=2)+'\n')
 command=json.loads((e/'reopen-attempt1-command.json').read_text())
 (e/(stage+'-command.json')).write_text(json.dumps(command,indent=2)+'\n')
 env=os.environ.copy();env.update(TMPDIR='/tmp/pinkha-c-swift-control-20261125',PINKHA_DESTINATION_NATIVE_FIXTURE=str(fixture),PINKHA_DESTINATION_NATIVE_WORK=str(e/'private-work'),PINKHA_DESTINATION_NATIVE_PHASE='refusal')
 with (e/(stage+'.log')).open('wb') as log:
  p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  (e/(stage+'-process.json')).write_text(json.dumps({'pid':p.pid})+'\n')
  try:code=p.wait(timeout=600)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20);raise
 result.update(returncode=code,sourceUnchanged=all(sha(root/k)==v for k,v in sources.items()),logSHA256=sha(e/(stage+'.log')))
 text=(e/(stage+'.log')).read_text(errors='replace')
 assert code==0 and result['sourceUnchanged'] and 'Executed 1 test, with 0 failures' in text and 'skipped' not in text.lower()
 assert (e/'private-work/refusal.txt').read_text()=='actual-native-modification-refused\n'
 result['result']='PASS'
except Exception as error:result.update(result='FAIL',errorType=type(error).__name__,error=str(error))
finally:
 try:
  remote_run("from pathlib import Path\np=Path("+repr(remote+'/finish')+")\np.write_text('refusal controller finished\\n')\n")
 except Exception as error:result['finishError']=str(error);result['result']='FAIL'
 if forward.poll() is None:
  os.killpg(forward.pid,signal.SIGTERM);forward.wait(timeout=20)
 forwardlog.close();result['forwardExitCode']=forward.returncode
 result['seconds']=round(time.monotonic()-started,3)
 (e/(stage+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['result']=='PASS' else 1)
