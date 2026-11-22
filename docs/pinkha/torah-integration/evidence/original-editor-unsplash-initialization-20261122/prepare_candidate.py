import pathlib,json,subprocess,hashlib,difflib,re
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
head="568d69f55a4b1b1bc318b8ee20144c720c8c16a5"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-unsplash-init-20261122")
assert not out.exists(),"Owned candidate directory exists"
out.mkdir()
def git(*a):
 r=subprocess.run(["git",*a],cwd=w,capture_output=True,timeout=45);r.check_returncode();return r.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
path="Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Cover/Unsplash/UnsplashItemsViewModel.swift"
base=git("show",head+":"+path);assert sha(base)=="badfaab8433033cae78004bf343207104514540ff47c62b620b96dc8889a95fe"
before=b"        self.unsplashService = unsplashService\n        self.documentWriteOwner = documentWriteOwner\n"
after=b"        self.documentWriteOwner = documentWriteOwner\n        self.unsplashService = unsplashService\n"
assert base.count(before)==1
candidate=base.replace(before,after)
patch="".join(difflib.unified_diff(base.decode().splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile="a/"+path,tofile="b/"+path))
(out/"UNSPLASH_BASE.swift").write_bytes(base);(out/"UNSPLASH_CANDIDATE.swift").write_bytes(candidate);(out/"UNSPLASH_INIT.patch").write_bytes(patch.encode())
upstream="d857b23ea540be33d6faab4f7a7a1a260ab578c1"
r=subprocess.run(["git","show",upstream+":"+path],cwd=w,capture_output=True,timeout=45)
up={"head":upstream,"returncode":r.returncode}
if r.returncode==0:
 (out/"UNSPLASH_UPSTREAM.swift").write_bytes(r.stdout);up.update({"sha256":sha(r.stdout),"content":r.stdout.decode()})
else:up["stderr"]=r.stderr.decode()
tracked=git("ls-files").decode().splitlines()
resolved=[p for p in tracked if p.endswith("Package.resolved")]
pins=[]
for p in resolved:
 try:
  lock=json.loads(git("show",head+":"+p))
  pp=lock.get("pins",lock.get("object",{}).get("pins",[]))
  for x in pp:
   if "factory" in (x.get("identity","")+x.get("location","")+x.get("package","")+x.get("repositoryURL","")).lower():pins.append({"path":p,"pin":x})
 except json.JSONDecodeError:pass
services=[p for p in tracked if "Unsplash" in p and p.endswith(".swift")]
dep=[]
for p in services:
 data=git("show",head+":"+p)
 if p==path:continue
 dst=out/("dependency-"+str(len(dep))+".swift");dst.write_bytes(data)
 dep.append({"path":p,"snapshot":dst.name,"sha256":sha(data),"blob":git("rev-parse",head+":"+p).decode().strip(),"content":data.decode()})
record={"schema":1,"head":head,"path":path,"blob":git("rev-parse",head+":"+path).decode().strip(),"base_sha256":sha(base),"candidate_sha256":sha(candidate),"patch_sha256":sha(patch.encode()),"patch":patch,"upstream":up,"factory_pins":pins,"dependencies":dep,"inverse_verified":candidate.replace(after,before)==base,"product_worktree_not_modified":True}
(out/"CANDIDATE_PROVENANCE.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
(out/"prepare_candidate.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps(record))
