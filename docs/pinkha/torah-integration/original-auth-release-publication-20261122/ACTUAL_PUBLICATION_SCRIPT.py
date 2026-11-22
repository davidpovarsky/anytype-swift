import pathlib,json,hashlib,shutil,subprocess,re,datetime
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122")
packet=root/"final-evidence-v2";repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-auth-startup-20261122")
branch="codex/otzaria-original-auth-startup-20261122";source="15ea8755a4e1cebf63314ab415fd809fbe9e8e84"
prefix="docs/pinkha/torah-integration/original-auth-release-20261122"
proof=root/"neutral-publication-v2";proof.mkdir(exist_ok=False);shutil.copyfile(__file__,proof/"ACTUAL_PUBLICATION_SCRIPT.py")
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout=60,input_bytes=None):
 row={"label":label,"argv":args,"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 op=proof/(label+".stdout");ep=proof/(label+".stderr")
 with op.open("wb") as o,ep.open("wb") as e:
  p=subprocess.Popen(args,cwd=repo,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:p.communicate(input=input_bytes,timeout=timeout);rc=p.returncode
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save();subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=20);p.communicate(timeout=20);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=rc,stdout_sha256=sha(op.read_bytes()),stderr_sha256=sha(ep.read_bytes()));save()
 assert rc==0,(label,ep.read_text(errors="replace"))
 return op.read_bytes()
assert run("source-head",["git","rev-parse","HEAD"]).decode().strip()==source
assert run("branch",["git","branch","--show-current"]).decode().strip()==branch
assert not run("initial-status",["git","status","--porcelain","--untracked-files=all"])
index_bytes=(packet/"EVIDENCE_INDEX.json").read_bytes();assert sha(index_bytes)=="cf221fcbce1d5cf0b3bfc2fbda64daa950a065ec19fe6d2fdfccd6290e2a654f"
index=json.loads(index_bytes);destination=repo/prefix;assert not destination.exists();shutil.copytree(packet,destination)
paths=[]
for e in index["files"]:
 p=destination/e["path"];assert p.stat().st_size==e["bytes"] and sha(p.read_bytes())==e["sha256"]
 paths.append(prefix+"/"+e["path"])
paths.append(prefix+"/EVIDENCE_INDEX.json")
attributes=repo/".gitattributes";old=attributes.read_bytes() if attributes.exists() else b""
rules=[prefix+"/** -text whitespace=cr-at-eol"]
for rel in paths:
 raw=(repo/rel).read_bytes()
 try:raw.decode("utf-8")
 except UnicodeDecodeError:continue
 lines=raw.splitlines()
 if any(line.endswith((b" ",b"\t")) or re.match(rb" +\t",line) for line in lines) or raw.endswith((b"\n\n",b"\r\n\r\n")):
  rules.append(rel+" -whitespace")
new=old+(b"" if not old or old.endswith(b"\n") else b"\n")+b"".join((r+"\n").encode() for r in rules if r.encode() not in old)
attributes.write_bytes(new)
run("stage-evidence-and-exact-attributes",["git","add","--",prefix,".gitattributes"])
run("diff-check",["git","diff","--cached","--check"])
staged=run("staged-paths",["git","diff","--cached","--name-only"]).decode().splitlines()
assert set(staged)==set(paths)|{".gitattributes"}
raw=run("verify-staged-blobs",["git","cat-file","--batch"],input_bytes=b"".join((":"+p+"\n").encode() for p in staged))
offset=0;verified=[]
for rel in staged:
 end=raw.index(b"\n",offset);oid,kind,size=raw[offset:end].decode().split();size=int(size);assert kind=="blob"
 data=raw[end+1:end+1+size];offset=end+2+size
 working=(repo/rel).read_bytes()
 assert data==(working.replace(b"\r\n",b"\n") if rel==".gitattributes" else working),rel
 verified.append({"path":rel,"git_blob":oid,"bytes":size,"sha256":sha(data)})
assert offset==len(raw)
(proof/"GIT_BLOB_BINDINGS.json").write_text(json.dumps(verified,indent=2)+"\n",encoding="utf-8")
run("commit-evidence",["git","commit","-m","docs: retain six original account release controls [skip ci]"],120)
head=run("published-candidate-head",["git","rev-parse","HEAD"]).decode().strip()
assert not run("source-scope-check",["git","diff","--name-only",source,"HEAD","--","Anytype","Modules","OriginalEditorFramework"])
assert not run("prepush-clean",["git","status","--porcelain","--untracked-files=all"])
run("ONE-normal-neutral-push",["git","push","-u","origin","HEAD:refs/heads/"+branch],120)
remote=run("remote-head",["git","ls-remote","--heads","origin","refs/heads/"+branch]).decode().split();assert remote[0]==head
assert not run("final-clean",["git","status","--porcelain","--untracked-files=all"])
result={"status":"PUBLISHED_EXACT_SOURCE_AND_SIX_PASS_EVIDENCE","source_commit":source,"evidence_head":head,"branch":branch,"remote_verified":True,"product_source_sha256":"65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e","packet_path":prefix,"index_sha256":sha(index_bytes),"payload_count":index["payload_count"],"payload_bytes":index["payload_bytes"],"git_blobs_verified":len(verified),"normal_pushes":1,"test_runs_replayed":0,"native_auth_integration_complete":False,"staged_paths":staged,"raw_evidence_attribute_rules":rules}
p=proof/"PUBLICATION_RESULT.json";p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("staged_paths","raw_evidence_attribute_rules")}))
