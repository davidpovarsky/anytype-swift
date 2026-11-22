import subprocess,pathlib,json,hashlib
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
head="d5df214b50faafbae4b8eb3edcf8b27bcdc930b8"
p=subprocess.run(["rg","--json","-n",r"await\s+(?:[A-Za-z_][A-Za-z0-9_.?]*\.)?withCurrent\s*(?:\(|\{)","Anytype/Sources"],cwd=repo,capture_output=True,timeout=60)
assert p.returncode in (0,1),p.stderr.decode("utf-8","replace")
matches=[json.loads(x)["data"] for x in p.stdout.decode().splitlines() if json.loads(x)["type"]=="match"]
paths=sorted({x["path"]["text"].replace("\\","/") for x in matches})
assert len(paths)<40
rows=[]
for i,path in enumerate(paths):
 g=subprocess.run(["git","show",head+":"+path],cwd=repo,capture_output=True,timeout=40);g.check_returncode()
 data=g.stdout;file=out/f"AWAIT_WITHCURRENT_{i}.swift";file.write_bytes(data)
 lines=data.decode().splitlines()
 hits=[x for x in matches if x["path"]["text"].replace("\\","/")==path]
 contexts=[{"line":x["line_number"],"text":x["lines"]["text"],"context":"\n".join(f"{j+1}: {lines[j]}" for j in range(max(0,x["line_number"]-9),min(len(lines),x["line_number"]+7)))} for x in hits]
 rows.append({"path":path,"snapshot":file.name,"source_head":head,"sha256":hashlib.sha256(data).hexdigest(),"lines":len(lines),"contexts":contexts})
record={"source_head":head,"pattern":"await (optional receiver) withCurrent(...) or withCurrent {","file_count":len(rows),"match_count":len(matches),"scope":"New bounded read-only compiler-pattern discovery, not semantic typecheck or exhaustive isolation certification; no old weak-self/constructor/actor inventory rerun.","files":rows}
(out/"AWAIT_WITHCURRENT_DISCOVERY.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
