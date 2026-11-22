from pathlib import Path
import json,hashlib,subprocess,shutil,datetime,difflib
p=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122\repair-proposal-v1")
o=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\auth-release-seam-root-review")
o.mkdir(parents=True,exist_ok=False)
swift=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
heart=Path(r"C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122")
def sha(b):return hashlib.sha256(b).hexdigest()
def git(repo,*args,data=None):
 c=subprocess.run(["git",*args],cwd=repo,input=data,capture_output=True,timeout=30)
 assert c.returncode==0,(args,c.stderr.decode("utf-8","replace"));return c.stdout
indexraw=(p/"INDEX.json").read_bytes();assert sha(indexraw)=="ac3a98c43bc915a117f779d638e53b629990d01c93b686df6182500c4cf7e372"
idx=json.loads(indexraw)
for x in idx["files"]:
 b=(p/x["path"]).read_bytes();assert sha(b)==x["sha256"] and len(b)==x["bytes"]
inputs=json.loads((p/"SOURCE_INPUTS.json").read_bytes())["inputs"]
bindings=[]
for repo,commit in [(swift,"37f48119609747c01ee92cf597e4216f63b7bfa4"),(heart,"d98420b1113536afd08cde6de9a5816f6d27ffff")]:
 members=[x for x in inputs if x["commit"]==commit]
 tree={}
 for row in git(repo,"ls-tree","-r","-z",commit).split(b"\0"):
  if row:
   metadata,path=row.split(b"\t",1);tree[path.decode()]=metadata.split()[2].decode()
 for x in members:assert tree[x["path"]]==x["git_blob"]
 raw=git(repo,"cat-file","--batch",data=("\n".join(x["git_blob"] for x in members)+"\n").encode());offset=0
 for x in members:
  end=raw.index(b"\n",offset);hdr=raw[offset:end].decode().split();n=int(hdr[2]);offset=end+1;b=raw[offset:offset+n];offset+=n+1
  assert hdr[0]==x["git_blob"] and hdr[1]=="blob" and n==x["bytes"] and sha(b)==x["sha256"],x["path"]
  bindings.append({"repository":str(repo),"commit":commit,"path":x["path"],"git_blob":hdr[0],"sha256":sha(b),"bytes":n})
 assert offset==len(raw)
pre=(p/"EditorAccountWriteTransition.preimage.swift").read_bytes();candidate=(p/"EditorAccountWriteTransition.candidate.swift").read_bytes()
path="Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift"
assert pre==git(swift,"show","37f48119609747c01ee92cf597e4216f63b7bfa4:"+path)
patch="".join(difflib.unified_diff(pre.decode().splitlines(True),candidate.decode().splitlines(True),fromfile="a/"+path,tofile="b/"+path))
assert patch.encode()==(p/"TRANSITION_WAITER_DRAFT.patch").read_bytes()
assert sha(candidate)=="65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e"
body=candidate.decode()
assert body.index("closing.cancel()")<body.index("if verify?() == true { lifetime.confirmOpened() }")<body.index("releaseCompleted = true")<body.index("for waiter in waiters { waiter.resume() }")
assert body.count("func finishAndWaitForRelease(")==1 and "private var releaseWaiters: [CheckedContinuation<Void, Never>] = []" in body
assert "guard !outerFinished else { return false }" in body
shutil.copyfile(__file__,o/"root_source_review.py")
(o/"ORIGINAL_GIT_BINDINGS.json").write_bytes((json.dumps(bindings,indent=2)+"\n").encode())
result={"schema":"otzaria.original-auth-release-seam-root-review/1","status":"PASS_FOR_EXACT_SEAM_IMPLEMENTATION_AND_NEW_FOCUSED_CONTROLS","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_packet":str(p),"source_index_sha256":sha(indexraw),"original_git_inputs_verified":len(bindings),"original_swift_inputs":len([x for x in bindings if x["commit"].startswith("37f")]),"original_heart_inputs":len([x for x in bindings if x["commit"].startswith("d984")]),
 "product_path":path,"preimage_sha256":sha(pre),"candidate_sha256":sha(candidate),"exact_patch_sha256":sha(patch.encode()),
 "review":["Full source, preimage, patch and proposal read by root.","Original released claim remains separate from completed release effects.","Atomic registration/completion using existing State lock; continuations resume outside lock.","Actual native operation drain, closing cancellation and optional verified confirmOpened all precede waiter completion.","First finish owns verification; duplicate calls cannot upgrade it.","Void return creates no current-account, subscription, selected-Space or body authority.","Cancellation does not synthesize release of an admitted original native body."],
 "new_control_scope":["no admitted RPC","admitted body held until actual completion","second waiter registered during verification after release claim","other closing lease keeps token unavailable","cancelled waiter does not release admitted body","first unverified finish cannot be upgraded"],
 "limits":["This approves only the original transition completion seam.","Exact-attempt Auth/LoginState/Hanlin decorator cancellation changes need concrete implementation review.","No normal logout serialization, global queue, new authentication selector or generated native readiness.","No compile, native execution or prior passed test replay by root."]}
raw=(json.dumps(result,indent=2)+"\n").encode();(o/"ROOT_REVIEW.json").write_bytes(raw)
print(json.dumps({"status":result["status"],"path":str(o/"ROOT_REVIEW.json"),"sha256":sha(raw),"original_git_inputs":len(bindings),"observed_at":result["observed_at"]}))
