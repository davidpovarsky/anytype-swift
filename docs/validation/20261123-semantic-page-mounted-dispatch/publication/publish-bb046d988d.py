import os,sys,subprocess,json,pathlib,datetime,hashlib
w=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123')
d=pathlib.Path(__file__).parent
head='bb046d988d57bf5f530f71b8b86588b21ab7ded2'
branch='codex/chatgpt-wave15-page154-mounted-admission-20261123'
token=sys.stdin.read().strip();assert token and '\n' not in token
env=os.environ.copy();env['GH_TOKEN']=token
def command(args,timeout=25):return subprocess.run(args,cwd=w,env=env,capture_output=True,text=True,timeout=timeout)
def checked(args):
 p=command(args);assert p.returncode==0,p.stderr;return p.stdout.strip()
assert checked(['git','rev-parse','HEAD'])==head and not checked(['git','status','--porcelain=v1'])
assert checked(['git','branch','--show-current'])==branch
assert checked(['git','remote','get-url','origin'])=='https://github.com/davidpovarsky/anytype-swift.git'
assert checked(['gh','api','user','--jq','.login'])=='davidpovarsky'
prefix=['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','-c','remote.origin.mirror=false']
before=checked(prefix+['ls-remote','--heads','origin','refs/heads/'+branch]).split()
assert before==[],before
gp='docs/validation/20261123-semantic-page-mounted-dispatch/source-retention-before-publication.json'
g=json.loads((w/gp).read_text());assert g['sourceRetentionPassed'] and not g['inventoryErrors'] and not g['unreviewedChangedExistingFiles']
delta=checked(['git','diff','--name-only',g['checkedTree'],head]).splitlines();assert delta==[gp],delta
p=command(prefix+['push','origin','HEAD:refs/heads/'+branch],120)
(d/'publication.stdout').write_text(p.stdout);(d/'publication.stderr').write_text(p.stderr);assert p.returncode==0,p.stderr
after=checked(prefix+['ls-remote','--heads','origin','refs/heads/'+branch]).split();assert after==[head,'refs/heads/'+branch]
r={'status':'PUBLISHED_EXACT_SOURCE','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':head,'branch':branch,'remoteBefore':None,'remoteAfter':after[0],'sourceGateSHA256':hashlib.sha256((w/gp).read_bytes()).hexdigest(),'postGateDocumentationOnly':delta,'forced':False}
with (d/'publication.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
