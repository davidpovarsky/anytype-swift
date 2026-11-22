from pathlib import Path
import json,hashlib,shutil,subprocess,datetime
root=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
repo=Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
base="e5fbd525bca1666504ed73cf8b96cce752907b3e";oldhead="d8ea2be0f42e51b35001c35509dd27c9035c3c66"
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
proof=root/"final-v7-git-seal"/"nested-index-correction";proof.mkdir(exist_ok=False);shutil.copyfile(__file__,proof/"ACTUAL_CORRECTION_SCRIPT.py")
sha=lambda b:hashlib.sha256(b).hexdigest()
cmd=[]
def run(label,args,input_bytes=None):
 p=subprocess.run(args,cwd=repo,input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 (proof/(label+".stdout")).write_bytes(p.stdout);(proof/(label+".stderr")).write_bytes(p.stderr)
 cmd.append({"label":label,"argv":args,"exit_code":p.returncode,"stdout_sha256":sha(p.stdout),"stderr_sha256":sha(p.stderr)})
 (proof/"COMMANDS.json").write_text(json.dumps(cmd,indent=2)+"\n",encoding="utf-8");assert p.returncode==0,(label,p.stderr.decode(errors="replace"));return p.stdout
assert run("exact-unpushed-seal-head",["git","rev-parse","HEAD"]).decode().strip()==base
assert not run("initial-clean",["git","status","--porcelain","--untracked-files=all"])
correction=repo/prefix/"v7-result-index-correction";assert not correction.exists();correction.mkdir()
shutil.copyfile(root/"final-v7-git-seal/ACTUAL_SEAL_SCRIPT.py",correction/"ACTUAL_INITIAL_SEAL_SCRIPT.py")
shutil.copyfile(__file__,correction/"ACTUAL_CORRECTION_SCRIPT.py")
changes=[]
for folder,indexname in (("second-native-run-45012913358","EVIDENCE_INDEX.json"),("final-v7-review","INDEX.json")):
 d=repo/prefix/folder;p=d/indexname;b=p.read_bytes();index=json.loads(b)
 declared={e["path"] for e in index["files"]}
 actual={f.relative_to(d).as_posix() for f in d.rglob("*") if f.is_file() and f!=p}
 missing=sorted(actual-declared);extra=sorted(declared-actual);assert not extra
 if not missing:continue
 assert all(Path(s).name==indexname for s in missing)
 (correction/(folder+"-ORIGINAL-"+indexname)).write_bytes(b)
 files=[{"path":f.relative_to(d).as_posix(),"bytes":f.stat().st_size,"sha256":sha(f.read_bytes())} for f in sorted(d.rglob("*")) if f.is_file() and f!=p]
 corrected={"payload_count":len(files),"payload_bytes":sum(e["bytes"] for e in files),"files":files}
 nb=(json.dumps(corrected,indent=2)+"\n").encode();p.write_bytes(nb)
 changes.append({"path":p.relative_to(repo).as_posix(),"before_sha256":sha(b),"after_sha256":sha(nb),"added_existing_payloads":missing,"payload_count":len(files),"payload_bytes":corrected["payload_bytes"]})
assert len(changes)==1 and changes[0]["added_existing_payloads"]==["selected-extracted/EVIDENCE_INDEX.json"],changes
note={"status":"DOCS_ONLY_INDEX_COMPLETENESS_CORRECTION","original_seal_head":base,"test_runs":0,"payload_bytes_changed":0,"cause":"Initial helper excluded every basename EVIDENCE_INDEX.json; correction excludes only the index being written. All255 initial Git blobs had already been byte-verified; the nested artifact index was committed but not listed by the result index.","changes":changes}
(correction/"CORRECTION.json").write_text(json.dumps(note,indent=2)+"\n",encoding="utf-8")
files=[{"path":p.relative_to(correction).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(correction.rglob("*")) if p.is_file()]
(correction/"INDEX.json").write_text(json.dumps({"files":files,"payload_count":len(files)},indent=2)+"\n",encoding="utf-8")
attrs=repo/".gitattributes";b=attrs.read_bytes();rule=(prefix+"/v7-result-index-correction/** -text whitespace=cr-at-eol\n").encode();assert rule not in b;attrs.write_bytes(b+rule)
paths=[e["path"] for e in changes]+[correction.relative_to(repo).as_posix(),".gitattributes"]
run("stage-docs-only-index-correction",["git","add","--",*paths])
run("diff-check",["git","diff","--cached","--check"])
run("ONE-docs-correction-commit",["git","commit","-m","docs: include retained nested native artifact index"])
head=run("corrected-final-head",["git","rev-parse","HEAD"]).decode().strip()
assert not run("frozen-v7-and-workflow-unchanged",["git","diff","--name-only",base,"HEAD","--",prefix+"/controls-v7-r1",".github/workflows/otzaria-original-schema-native.yml","Anytype","Modules","OriginalEditorFramework"])
assert not run("final-clean",["git","status","--porcelain","--untracked-files=all"])
staged=run("all-final-paths-since-d8ea",["git","diff","--name-only",oldhead,"HEAD"]).decode().splitlines()
data=run("all-final-git-blobs",["git","cat-file","--batch"],b"".join(("HEAD:"+p+"\n").encode() for p in staged))
offset=0;bindings=[]
for rel in staged:
 end=data.index(b"\n",offset);oid,kind,size=data[offset:end].decode().split();size=int(size);assert kind=="blob"
 b=data[end+1:end+1+size];offset=end+2+size;working=(repo/rel).read_bytes()
 assert b==(working.replace(b"\r\n",b"\n") if rel==".gitattributes" else working),rel
 bindings.append({"path":rel,"git_blob":oid,"bytes":len(b),"sha256":sha(b)})
assert offset==len(data)
(proof/"ALL_FINAL_GIT_BLOB_BINDINGS.json").write_text(json.dumps(bindings,indent=2)+"\n",encoding="utf-8")
result={"status":"SEALED_FINAL_NO_PUSH","head":head,"initial_seal_head":base,"baseline_control_head":oldhead,"branch":"codex/otzaria-original-schema-native-20261122","git_blobs":len(bindings),"git_payload_bytes":sum(e["bytes"] for e in bindings),"v7_index_sha256":"6cff458c0b945e755325d906add452e0b0fa676291f9391276dd8237c38d5e64","workflow_sha256":"53414fb807fd95d1526da6881be9979c90dbc9340adb187cce646fe7da9cce82","result_index":changes[0],"v7_final_review_index_sha256":sha((repo/prefix/"final-v7-review/INDEX.json").read_bytes()),"normal_pushes":0,"native_runs":0,"tests_replayed":0}
(proof/"FINAL_GIT_ADMISSION.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
