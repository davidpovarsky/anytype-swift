from pathlib import Path
import hashlib,json,subprocess,datetime,shutil
repo=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
temp=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-held-read-seal-20261122")
temp.mkdir(exist_ok=True)
target="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift"
base="18ac6d39dfe76b12e5dead9627c831c6a88d073c"
expected="dcb942bbbdc799989134da1f84256641ac750437749ca67d4412e352a0f0a252"
log=[]
def git(*a,check=True):
 p=subprocess.run(["git",*a],cwd=repo,capture_output=True,timeout=60)
 log.append({"args":["git",*a],"returncode":p.returncode,"stdout":p.stdout.decode("utf8",errors="replace"),"stderr":p.stderr.decode("utf8",errors="replace")})
 if check and p.returncode:raise RuntimeError(log[-1])
 return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==base
assert git("branch","--show-current").decode().strip()=="codex/otzaria-original-held-read-adapter-20261122"
assert not git("diff","--cached","--name-only").strip()
assert git("diff","--name-only").decode().splitlines()==[target]
assert sha((repo/target).read_bytes())==expected
pre=git("show",base+":"+target);assert sha(pre)=="0d007b5d2ee2bab38218cbdc36b0385f17b8ee95d8579ddaa23626081c602526"
diff=git("diff","--",target);(temp/"SOURCE.patch").write_bytes(diff)
git("-c","core.autocrlf=false","add","--",target)
assert git("diff","--cached","--name-only").decode().splitlines()==[target]
assert sha(git("show",":"+target))==expected
git("diff","--cached","--check")
git("commit","-m","fix: consume fresh annotation observation inside original owner read")
source=git("rev-parse","HEAD").decode().strip()
assert git("rev-parse","HEAD^").decode().strip()==base
assert git("diff-tree","--no-commit-id","--name-only","-r",source).decode().splitlines()==[target]
assert sha(git("show",source+":"+target))==expected
receipt={"schema":"otzaria.held-read-source-seal/1","status":"PASS","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"base":base,"sourceCommit":source,"productPath":target,"productSHA256":expected,"productBytes":len((repo/target).read_bytes()),"onlyChangedSource":target,"sourceDiffSHA256":sha(diff),"sourceDiffBytes":len(diff),"stagedAndCommittedBytesVerified":True,"commands":log}
(temp/"SOURCE_SEAL.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf8",newline="\n")
actual=Path(__file__).read_bytes();(temp/"actual-source-seal.py").write_bytes(actual)
print(json.dumps({"status":"PASS","sourceCommit":source,"parent":base,"receipt":str(temp/"SOURCE_SEAL.json"),"receiptSHA256":sha((temp/"SOURCE_SEAL.json").read_bytes()),"sourcePatchSHA256":sha(diff),"statusAfter":git("status","--short").decode(),"actualScriptSHA256":sha(actual)},ensure_ascii=False))