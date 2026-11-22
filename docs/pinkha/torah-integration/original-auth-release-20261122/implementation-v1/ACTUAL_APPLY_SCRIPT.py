import pathlib,subprocess,json,hashlib,datetime,shutil
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
dest=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-auth-startup-20261122")
branch="codex/otzaria-original-auth-startup-20261122";base="37f48119609747c01ee92cf597e4216f63b7bfa4"
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122")
out=root/"implementation-v1";out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/"ACTUAL_APPLY_SCRIPT.py")
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def run(label,args,cwd=repo,timeout=60,allowed=(0,)):
 p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=timeout)
 (out/(label+".stdout")).write_bytes(p.stdout);(out/(label+".stderr")).write_bytes(p.stderr)
 commands.append({"label":label,"argv":args,"cwd":str(cwd),"exit_code":p.returncode,"stdout_sha256":sha(p.stdout),"stderr_sha256":sha(p.stderr)})
 (out/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
 assert p.returncode in allowed,(label,p.returncode,p.stderr.decode(errors="replace"))
 return p
assert not dest.exists(),str(dest)
assert run("branch-must-not-exist",["git","show-ref","--verify","--quiet","refs/heads/"+branch],allowed=(1,)).returncode==1
usage=shutil.disk_usage(repo);assert usage.free>3*1024**3,usage.free
path="Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift"
original=run("exact-original-preimage",["git","show",base+":"+path]).stdout
assert sha(original)=="25d37aa7d7dfe1b018c3161eca54c42bb6f0e7394bfdbf6ea6af3182c429c6dc"
run("create-owned-worktree",["git","worktree","add","-b",branch,str(dest),base],timeout=150)
assert not run("new-worktree-status",["git","status","--porcelain","--untracked-files=all"],cwd=dest).stdout
candidate=(root/"repair-proposal-v1"/"EditorAccountWriteTransition.candidate.swift").read_bytes()
assert sha(candidate)=="65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e"
pre_work=(dest/path).read_bytes();assert pre_work.replace(b"\r\n",b"\n")==original
(dest/path).write_bytes(candidate)
run("diff-check",["git","diff","--check"],cwd=dest)
diff=run("exact-source-diff",["git","diff","--",path],cwd=dest).stdout
assert run("changed-paths",["git","diff","--name-only"],cwd=dest).stdout.decode().splitlines()==[path]
result={"status":"EXACT_REVIEWED_SOURCE_APPLIED_NO_TEST","worktree":str(dest),"branch":branch,"base":base,"path":path,"preimage_sha256":sha(original),"checkout_preimage_sha256":sha(pre_work),"candidate_sha256":sha(candidate),"patch_sha256":sha(diff),"root_review_sha256":"17ce2a6b681d034b453e6c3b94d9e7c566aae172eaeef7291a1db427a549d157","tests":0,"native_calls":0,"pushes":0}
p=out/"SOURCE_APPLIED.json";p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
