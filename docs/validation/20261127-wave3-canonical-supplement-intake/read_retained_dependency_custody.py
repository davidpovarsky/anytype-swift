from pathlib import Path
import json,stat,hashlib,datetime
base=Path("/var/lib/pinkha-w1-functional-migration-20261127")
observations=[]
def read(rel,size,sha):
 p=base/rel;a=p.lstat();assert stat.S_ISREG(a.st_mode) and not p.is_symlink() and a.st_size==size
 data=p.read_bytes();b=p.lstat();identity=lambda x:[x.st_dev,x.st_ino,x.st_size,x.st_mode,x.st_mtime_ns,x.st_ctime_ns]
 assert identity(a)==identity(b) and len(data)==size and hashlib.sha256(data).hexdigest()==sha
 observations.append({"path":str(p),"bytes":size,"sha256":sha,"beforeAfterIdentityEqual":True,"identity":identity(a)})
 return json.loads(data)
source=read("dependency-locator-repair1/source-before.json",264512,"a92e4fa284108efa9fc2a7b600f6d2de5ddf05e5db87abc10db15ab1cea80d52")
after=read("dependency-locator-repair1/source-after.json",264512,"a92e4fa284108efa9fc2a7b600f6d2de5ddf05e5db87abc10db15ab1cea80d52")
assert source==after
cache=read("swift-cache-relocation-continuation1/source-before.json",2760703,"a98bab098d0f9f091bd8c280f23cc1863d76264f180474a00417deae810858a1")
entries=cache["entries"];assert len(entries)==6906
assert len({r["path"] for r in entries})==len(entries)
deps={r["path"]:{k:r[k] for k in ["bytes","mode","sha256"]} for r in entries if r["kind"]=="file" and r["path"].startswith("checkouts/") and ".git" not in Path(r["path"]).parts}
missing=sorted(set(source)-set(deps));extra=sorted(set(deps)-set(source));different=[k for k in source if k in deps and source[k]!=deps[k]]
groups={}
for name in source:
 key=name.split("/")[1];groups[key]=groups.get(key,0)+1
print(json.dumps({"protocol":"independent-retained-dependency-source-custody-join-v1","readAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"inputObservations":observations,"sourceBeforeAfterEqual":True,"recordedCacheEntries":len(entries),"recordedDependencySourceFiles":len(source),"postBuildCustodyDependencyFiles":len(deps),"dependencyGroups":groups,"missingInPostBuildCustody":missing,"extraInPostBuildCustody":extra,"differentBytesModeHash":different,"exactSourceFilesAndModesEqual":source==deps,"liveCacheScanned":False,"testsExecuted":0},sort_keys=True))
