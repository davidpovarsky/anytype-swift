import subprocess,json
from pathlib import Path
repo=Path(r"C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122")
base="d98420b1113536afd08cde6de9a5816f6d27ffff"
paths=subprocess.check_output(["git","ls-tree","-r","--name-only",base,"core/block/object/objectcreator","core/block/source/sourceimpl"],cwd=repo,text=True).splitlines()
out={}
for p in paths:
 if p.endswith("_test.go"):
  b=subprocess.check_output(["git","show",base+":"+p],cwd=repo);s=b.decode()
  lines=s.splitlines()
  hits=[{"line":i+1,"text":l} for i,l in enumerate(lines) if "func TestMain" in l or "func init()" in l or l.startswith("package ")]
  out[p]=hits
print(json.dumps(out))
