import json, pathlib, subprocess, hashlib
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
dest=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
base="37f48119609747c01ee92cf597e4216f63b7bfa4"
branch="codex/otzaria-original-schema-native-20261122"
def git(*a):
 p=subprocess.run(["git","-C",str(repo),*a],capture_output=True,timeout=40)
 if p.returncode: raise RuntimeError(f"git {a}: {p.returncode}: {p.stderr.decode(errors='replace')}")
 return p.stdout
out={"target":str(dest),"target_exists":dest.exists(),"base":base,"base_commit":git("rev-parse",base+"^{commit}").decode().strip(),"base_tree":git("rev-parse",base+"^{tree}").decode().strip(),"branch":branch,"existing_refs":git("for-each-ref","--format=%(refname) %(objectname)","refs/heads/"+branch,"refs/remotes/origin/"+branch).decode(),"remote_candidate":git("ls-remote","--heads","origin",branch).decode(),"origin":git("remote","get-url","origin").decode().strip(),"worktree_records":[],"instructions":[]}
wt=git("worktree","list","--porcelain").decode()
for block in wt.strip().split("\n\n"):
 if str(dest).replace("\\","/").lower() in block.lower() or branch in block: out["worktree_records"].append(block)
for d in [pathlib.Path("C:/"),pathlib.Path(r"C:\Users"),pathlib.Path(r"C:\Users\DAVID"),pathlib.Path(r"C:\Users\DAVID\Code")]:
 f=d/"AGENTS.md"
 if f.exists(): out["instructions"].append({"path":str(f),"body":f.read_text(encoding="utf-8")})
paths=git("ls-tree","-r","--name-only",base).decode().splitlines()
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
anc={"AGENTS.md",".github/AGENTS.md",".github/workflows/AGENTS.md","docs/AGENTS.md","docs/pinkha/AGENTS.md","docs/pinkha/torah-integration/AGENTS.md",prefix+"/AGENTS.md"}
for p in paths:
 if p in anc: out["instructions"].append({"path":base+":"+p,"body":git("show",base+":"+p).decode()})
out["attributes"]=git("show",base+":.gitattributes").decode() if ".gitattributes" in paths else None
out["existing_destination_paths"]=[p for p in paths if p.startswith(prefix+"/") or p==".github/workflows/otzaria-original-schema-native.yml"]
out["workflow_headers"]=[]
for p in paths:
 if p.startswith(".github/workflows/") and p.endswith((".yml",".yaml")):
  body=git("show",base+":"+p).decode()
  out["workflow_headers"].append({"path":p,"head":"\n".join(body.splitlines()[:32])})
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
out["packet_indexes"]=[]
for folder,name in [("candidate-v5","SOURCE_REVIEW_INDEX.json"),("controls-v5-r2","REVIEW_INDEX.json")]:
 f=root/folder/name; b=f.read_bytes(); j=json.loads(b)
 out["packet_indexes"].append({"path":str(f),"sha256":hashlib.sha256(b).hexdigest(),"top_keys":list(j),"sample":{k:(v[:2] if isinstance(v,list) else v) for k,v in j.items() if k not in ("files","payloads","inputs")},"entries_sample":(j.get("files") or j.get("payloads") or j.get("inputs") or [])[:2]})
review=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-root-controls-review")
out["root_review_files"]=[{"name":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(review.iterdir()) if p.is_file()]
peer=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-heart-v5-r2-runner-independent-review-20261122.json")
out["peer_review"]={"bytes":peer.stat().st_size,"sha256":hashlib.sha256(peer.read_bytes()).hexdigest()}
print(json.dumps(out,ensure_ascii=False))
