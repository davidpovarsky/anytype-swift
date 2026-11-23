from pathlib import Path
import hashlib,json,os,subprocess,datetime
base=Path('/mnt/development/projects');root=base/'worktrees/anytype-wave15-shared-20261123';d=base/'diagnostics/sdk-ui-page-composition-20261123'
head='ec9839bd0985a7dc392bf511d2c0b25629c9c857'
commits=['46c03ec8692bee4ffe6304b041a4a4425d08e2dc','cf70fdf165586baffd257fdb135cea06f64e745d','44aa9d3c64275917a79e6392ef619554d1af2990','a4d46b543d99b38181d087d5b5cdd6d84efad57e','9debe65b3964b0f7d72d0bdd675e5cb06dc57fe9','2370d9ba047d26d6d9bc7f1c7bcb49b9c98e886e','ae5182b3780c27006a280e21939e1b0d87fa079d','6fac48c8151c0e0cf0e34c2f7961f7afa90642cd','1a710285102077f8be7b3180a6685fbed1dc7cd9','ec5c0083e6b78948a7adb26bf3d3844215c922d3','3f37e8b39e1857f71bcffe6be8394d76958c5284']
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*a],timeout=30)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
 with (d/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
assert git('rev-parse','HEAD').decode().strip()==head and not git('status','--porcelain')
s=os.statvfs(base);assert s.f_bavail*s.f_frsize>=2_500_000_000+32*1024**2
checks=[('anytype-wave15-sdk06-original-native-20261123','a4d46b543d99b38181d087d5b5cdd6d84efad57e','docs/validation/20261123-sdk06-original-native-continuation/qualification.json','7f84d80dfeec8409eb38cc22d142a8ca243794292896322f03c2216bd24ae587'),('anytype-wave15-native-ui-transition-candidate-20261123','3f37e8b39e1857f71bcffe6be8394d76958c5284','docs/validation/20261123-native-ui-transition-candidate/qualification.json','3f6b4db74295833e9704104c87460f4ac2eef921da501f6d8989512d5e708513')]
for writer,ref,path,digest in checks:
 p=base/'worktrees'/writer
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()==ref
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=p)
 b=(p/path).read_bytes();assert sha(b)==digest and b==git('show',ref+':'+path)
d.mkdir(mode=0o700,exist_ok=True)
save('sdk-ui-integration-intent.json',{'before':head,'commits':commits,'excludedAlreadyIntegratedSupervisor':'4a4848c996f5681b89988480dd742311146b996c','createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'oldOrPassingTestsReplayed':0,'scope':'Exact qualified SDK/UI source and evidence; UI central route and SDK single central-contract row are composed separately before final publication.'})
args=['git','-c','gc.auto=0','-C',str(root),'cherry-pick','--no-commit',*commits]
r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
for n,b in [('sdk-ui-cherry-pick.stdout',r.stdout),('sdk-ui-cherry-pick.stderr',r.stderr)]:
 with (d/n).open('xb') as f:f.write(b)
save('sdk-ui-cherry-pick-command.json',{'argv':args,'exit':r.returncode,'stdoutSHA256':sha(r.stdout),'stderrSHA256':sha(r.stderr)})
assert r.returncode==0,r.stderr.decode()
paths=git('diff','--cached','--name-only').decode().splitlines()
assert paths and not git('diff','--name-only')
r=subprocess.run(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','commit','-m','Integrate qualified original-native SDK and five-scope UI candidates'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
for n,b in [('sdk-ui-commit.stdout',r.stdout),('sdk-ui-commit.stderr',r.stderr)]:
 with (d/n).open('xb') as f:f.write(b)
assert r.returncode==0,r.stderr.decode()
assert not git('status','--porcelain')
result={'status':'PASS','before':head,'after':git('rev-parse','HEAD').decode().strip(),'paths':len(paths),'sourceCommits':commits,'testsExecuted':0,'freeBytes':os.statvfs(base).f_bavail*os.statvfs(base).f_frsize}
save('sdk-ui-integration-result.json',result)
print(json.dumps(result))
