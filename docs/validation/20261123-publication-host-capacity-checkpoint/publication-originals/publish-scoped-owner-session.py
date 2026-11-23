from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
root=Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123');d=Path('/mnt/development/projects/diagnostics/sdk-ui-page-composition-20261123')
head='e4edea19ce716280f4087f8b9571ad2b4f6f94c5';previous='c0c1f851f80322c9f532e86505047498dfaf1adf';branch='codex/chatgpt-wave15-shared-20261121'
request=json.load(sys.stdin);assert set(request)=={'token'} and isinstance(request['token'],str) and 10<len(request['token'])<1024
env=dict(os.environ);env['GH_TOKEN']=request.pop('token')
for name in ['GIT_TRACE','GIT_TRACE_CURL','GIT_CURL_VERBOSE','GIT_TRACE_PACKET']:env.pop(name,None)
prefix=['git','-c','gc.auto=0','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','-c','remote.origin.mirror=false']
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*a],timeout=90)
def remote(*a):return subprocess.check_output(prefix+list(a),cwd=root,env=env,timeout=90)
def save(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
assert git('remote','get-url','origin').decode().strip()=='https://github.com/davidpovarsky/anytype-swift.git'
assert os.statvfs(root).f_bavail*os.statvfs(root).f_frsize>=2516777216
seal=json.loads((d/'source-gate-seal.json').read_bytes());assert seal['publishedCandidate']==head and seal['status']=='PASS_SOURCE_GATE'
assert hashlib.sha256((d/'source-retention-before-dispatch.json').read_bytes()).hexdigest()==seal['sourceGateSHA256']
meta=subprocess.check_output(['gh','api','-i','user'],cwd=root,env=env,text=True,timeout=45)
login=json.loads(meta[meta.index('{'):])['login']
scopes=[line.split(':',1)[1].strip() for line in meta.splitlines() if line.lower().startswith('x-oauth-scopes:')]
assert login=='davidpovarsky' and len(scopes)==1 and 'workflow' in [x.strip() for x in scopes[0].split(',')]
before=remote('ls-remote','--heads','origin','refs/heads/'+branch).decode().split();assert before==[previous,'refs/heads/'+branch],before
save(d/'publication-v3-intent.json',{'source':head,'expectedRemoteBefore':previous,'branch':branch,'sourceGateSHA256':seal['sourceGateSHA256'],'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'force':False,'authenticatedLogin':login,'scopes':scopes[0],'credentialOrigin':'Existing authorized Windows owner gh session; passed over existing SSH stdin to process-local GH_TOKEN only. Token not stored. Git/source operation runs on Oracle.','persistentCredentialOrGitConfigurationChanged':False,'priorMirrorAndOAuthScopeFailuresPreserved':True})
start=time.monotonic();p=subprocess.run(prefix+['push','origin','HEAD:refs/heads/'+branch],cwd=root,env=env,capture_output=True,timeout=180)
for name,b in [('publication-v3.stdout',p.stdout),('publication-v3.stderr',p.stderr)]:
 with (d/name).open('xb') as f:f.write(b)
assert p.returncode==0,p.stderr.decode()
after=remote('ls-remote','--heads','origin','refs/heads/'+branch).decode().split();assert after==[head,'refs/heads/'+branch]
env.pop('GH_TOKEN',None)
result={'status':'PASS_PUBLISHED_EXACT_GATED_SOURCE','source':head,'remoteBefore':previous,'remoteAfter':head,'branch':branch,'sourceGateSHA256':seal['sourceGateSHA256'],'verifiedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-start,'forced':False,'testsReplayed':0,'authenticatedLogin':login,'scopes':scopes[0],'persistentConfigChanged':False,'GitExecutedOnOracle':True,'tokenStored':False}
save(d/'publication.json',result);print(json.dumps(result))
